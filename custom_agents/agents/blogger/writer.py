import logging
from datetime import datetime
import json
import sys
import traceback
from typing import Dict, List, Any, Optional
from jsonschema import validate, ValidationError
from pydash import get as pydash_get
from custom_agents.agents.utils.views import print_agent_output
from custom_agents.agents.utils.llms import call_model
from custom_agents.config.shared_constants import SAMPLE_JSON, JSON_SCHEMA

logger = logging.getLogger(__name__)


class WriterAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.max_retries = 3  # For transient error retries

    async def _log_error(self, e: Exception, context: dict = None) -> dict:
        """Enhanced error logging with traceback and context"""
        exc_type, exc_obj, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)[-1] if exc_tb else None

        error_info = {
            "error": str(e),
            "type": exc_type.__name__ if exc_type else "UnknownError",
            "location": f"{tb.filename}:{tb.lineno}" if tb else "unknown",
            "function": tb.name if tb else "unknown",
            "context": context or {}
        }

        logger.error(
            f"WriterAgent error in {error_info['function']} (line {tb.lineno if tb else '?'}): {error_info['error']}\n"
            f"Context: {json.dumps(error_info['context'], indent=2)}",
            exc_info=True
        )

        if self.websocket and self.stream_output:
            error_msg = (f"Error at {error_info['location']} - "
                         f"{error_info['type']}: {error_info['error']}")
            await self.stream_output("error", "writing", error_msg, self.websocket)

        return error_info

    def safe_get(self, data, path, default=None):
        """Robust nested data access using pydash.get with error handling"""
        try:
            if data is None:
                return default
            return pydash_get(data, path, default)
        except Exception as e:
            error_context = {
                "data_type": type(data).__name__,
                "path": path,
                "default": default
            }
            self._log_error(e, error_context)
            return default

    def _validate_response(self, response: dict) -> None:
        """Validate LLM response against JSON schema"""
        try:
            validate(instance=response, schema=JSON_SCHEMA)
        except ValidationError as e:
            error_context = {
                "validation_error": e.message,
                "response_keys": list(response.keys()) if response else None
            }
            logger.error("Response validation failed: %s", json.dumps(error_context, indent=2))
            raise ValueError(f"Invalid response structure: {e.message}") from e

    def get_headers(self, research_state: dict) -> dict:
        """Extract headers with validation"""
        headers = {
            "title": self.safe_get(research_state, "metadata.title", "Untitled"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": self.safe_get(research_state, "metadata.description", ""),
            "tags": self.safe_get(research_state, "metadata.tags", [])
        }

        if not headers["title"]:
            raise ValueError("Title is required in research state metadata")

        return headers

    async def _call_llm_with_retry(self, prompt: List[Dict], model: str) -> Dict:
        """Call LLM with retry logic for transient failures"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await call_model(
                    prompt,
                    model,
                    response_format="json"
                )

                if not isinstance(response, dict):
                    raise ValueError("LLM returned non-dict response")

                self._validate_response(response)
                return response

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Retry {attempt + 1} for LLM call due to: {str(e)}")
                    continue
                raise last_error

    async def write_sections(self, research_state: dict) -> dict:
        """Generate content sections with enhanced validation and error handling"""
        try:
            query = self.safe_get(research_state, "metadata.title", "Untitled")
            data = self.safe_get(research_state, "research_data")
            task = self.safe_get(research_state, "task", {})
            follow_guidelines = self.safe_get(task, "follow_guidelines", False)
            guidelines = self.safe_get(task, "guidelines", {})
            model = self.safe_get(task, "model", "gpt-4")

            prompt = [
                {
                    "role": "system",
                    "content": """
                    You are a research writer. Your task is to write a blog-style research article "
                           "using provided research data in a clear, structured, engaging format."
                           "Crafting compelling narratives that keep readers engaged"
                           "Structuring content for optimal readability"
                           "Adapting tone and style to match the target audience"
                           "Incorporating storytelling techniques"
                           "Using persuasive language without being salesy.
                    """
                },
                {
                    "role": "user",
                    "content": f"""Today's date is {datetime.now().strftime('%Y-%m-%d')}.
                    Topic: {query}
                    
                    Your task:
Write a detailed, markdown-formatted blog article that includes a title, author, date, tags, introduction, description, 
detailed main content sections with subsections, a conclusion, and a list of sources in APA style.

Each section should be engaging and informative, including markdown hyperlinks where appropriate.
If guidelines are provided, follow them strictly: {guidelines if follow_guidelines else 'No specific guidelines'}.

                    Research data (if provided):
                    {json.dumps(data, indent=2) if data else "No additional research data provided."}

                    Guidelines:
                    {guidelines if follow_guidelines else 'No strict guidelines. Prioritize clarity and engagement.'}

                    Return only a valid JSON structure conforming to this format:
                    {json.dumps(SAMPLE_JSON, indent=2)}
                    """
                }
            ]

            response = await self._call_llm_with_retry(prompt, model)
            return response

        except Exception as e:
            error_context = {
                "research_state_keys": list(research_state.keys()),
                "task": self.safe_get(research_state, "task", {}),
                "llm_prompt": prompt[-1]["content"][:500] + "..." if prompt else None
            }
            error_info = await self._log_error(e, error_context)
            raise RuntimeError(f"Failed to write sections: {error_info['error']}") from e

    async def revise_headers(self, task: dict, headers: dict) -> dict:
        """Revise headers with SEO optimization and validation"""
        try:
            prompt = [
                {
                    "role": "system",
                    "content": "You are an SEO editor optimizing article metadata."
                },
                {
                    "role": "user",
                    "content": f"""
                    Current Headers:
                    {json.dumps(headers, indent=2)}

                    Guidelines:
                    {self.safe_get(task, 'guidelines', 'None')}

                    Return only the revised JSON headers.
                    """
                }
            ]

            response = await self._call_llm_with_retry(
                prompt,
                self.safe_get(task, "model", "gpt-4")
            )

            # Validate revised headers
            if not isinstance(response, dict):
                raise ValueError("LLM returned invalid header format")
            if not response.get("title"):
                raise ValueError("Revised headers must include a title")

            return {"headers": response}

        except Exception as e:
            error_context = {
                "original_headers": headers,
                "task_guidelines": self.safe_get(task, "guidelines")
            }
            await self._log_error(e, error_context)
            raise RuntimeError(f"Header revision failed: {str(e)}") from e

    def _safe_serialize(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable formats safely"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: self._safe_serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._safe_serialize(item) for item in obj]
        if hasattr(obj, '__dict__'):
            return self._safe_serialize(obj.__dict__)
        return str(obj)

    async def run(self, research_state: dict) -> dict:
        """Main execution method with comprehensive error handling"""
        try:
            # Initial validation
            if not research_state or not isinstance(research_state, dict):
                raise ValueError("Invalid research_state: must be non-empty dictionary")

            # Notify start
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "writing_report",
                    "Writing final research report...",
                    self.websocket
                )

            # Generate content
            blog_json = await self.write_sections(research_state)
            headers = self.get_headers(research_state)

            # Optionally revise headers
            if self.safe_get(research_state, "task.follow_guidelines", False):
                if self.websocket and self.stream_output:
                    await self.stream_output(
                        "logs",
                        "revising_headers",
                        "Optimizing headers...",
                        self.websocket
                    )
                revised = await self.revise_headers(
                    self.safe_get(research_state, "task", {}),
                    headers
                )
                headers = revised["headers"]

            # Debug output if verbose
            if self.safe_get(research_state, "task.verbose", False):
                debug_output = json.dumps(
                    self._safe_serialize(blog_json),
                    indent=2,
                    ensure_ascii=False
                )
                if self.websocket:
                    await self.stream_output(
                        "logs",
                        "blog_content",
                        debug_output,
                        self.websocket
                    )

            return {
                **blog_json,
                "headers": headers,
                "success": True
            }

        except Exception as e:
            error_info = await self._log_error(e, {
                "research_state_types": {
                    k: type(v).__name__
                    for k, v in research_state.items()
                } if research_state else None
            })

            return {
                "error": error_info,
                "success": False
            }