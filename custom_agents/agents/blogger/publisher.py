import os
import sys
import traceback
import logging
import frontmatter
import json5 as json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote
from jsonschema import validate, ValidationError
from custom_agents.agents.utils.file_formats import (
    write_md_to_pdf,
    write_md_to_word,
    write_to_json
)
from custom_agents.agents.utils.views import print_agent_output
from custom_agents.config.shared_constants import SAMPLE_JSON, JSON_SCHEMA

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXPORT_FORMATS = ["md", "pdf", "docx", "json"]


class PublisherAgent:
    def __init__(self, output_dir: str, websocket=None, stream_output=None,
                 headers: Optional[Dict] = None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.output_dir = output_dir.strip()
        self.headers = headers or {}

    def _validate_research_state(self, research_state: dict) -> None:
        """Validate research state against JSON schema"""
        try:
            validate(instance=research_state, schema=JSON_SCHEMA)
        except ValidationError as e:
            logger.error(f"Research state validation failed: {e.message}")
            raise ValueError(f"Invalid research state structure: {e.message}")

    def _slugify_filename(self, filename: str) -> str:
        """Convert a string to a safe filename"""
        safe_chars = ('-', '_', '.')
        filename = ''.join(
            c if c.isalnum() or c in safe_chars else '-'
            for c in filename
        )
        # Remove consecutive dashes and leading/trailing dashes
        filename = '-'.join(filter(None, filename.split('-')))
        return filename.strip('-')

    def generate_layout(self, research_state: dict) -> str:
        """Generates markdown content from the new JSON structure."""
        # Early content validation
        if not research_state.get("content"):
            raise ValueError("Research state is missing required 'content' section")

        layout_parts = []
        content = research_state["content"]
        metadata = research_state.get("metadata", {})

        # Introduction section
        if content.get("introduction"):
            intro = content["introduction"]
            if not intro.get("hook") or not intro.get("thesis"):
                raise ValueError("Introduction section requires both 'hook' and 'thesis'")

            layout_parts.append(
                f"# {metadata.get('title', 'Untitled')}\n\n"
                f"**{intro.get('hook', '')}**\n\n"
                f"{intro.get('context', '')}\n\n"
                f"*{intro.get('thesis', '')}*"
            )

        # Main content sections
        for section in content.get("main_content", []):
            if not section.get("heading") or not section.get("content"):
                raise ValueError("Main content sections require both 'heading' and 'content'")

            layout_parts.append(f"\n## {section['heading']}\n{section['content']}")

            for subsection in section.get("subsections", []):
                if not subsection.get("subheading") or not subsection.get("content"):
                    continue  # Skip invalid subsections rather than failing
                layout_parts.append(f"\n### {subsection['subheading']}\n{subsection['content']}")

        # Conclusion
        if content.get("conclusion"):
            conclusion = content["conclusion"]
            layout_parts.append(
                f"\n## Conclusion\n"
                f"{conclusion.get('summary', '')}\n\n"
                f"*{conclusion.get('call_to_action', '')}*"
            )

        # References
        if research_state.get("references"):
            refs = research_state["references"]
            layout_parts.append("\n## References")

            if refs.get("sources"):
                layout_parts.append("\n### Sources")
                layout_parts.extend([f"- {src['citation']}" for src in refs["sources"]])

            if refs.get("additional_resources"):
                layout_parts.append("\n### Further Reading")
                layout_parts.extend([f"- [{res['title']}]({res['url']})" for res in refs["additional_resources"]])

        return '\n\n'.join(filter(None, layout_parts))

    def generate_frontmatter(self, research_state: dict) -> dict:
        """Generates comprehensive frontmatter metadata from new structure."""
        metadata = research_state.get("metadata", {})
        task = research_state.get("task", {})

        frontmatter_data = {
            "title": metadata.get("title", "Untitled"),
            "date": metadata.get("date", datetime.now().strftime("%Y-%m-%d")),
            "draft": metadata.get("draft", False),
            "tags": metadata.get("tags", []),
            "description": metadata.get("description", ""),
            "word_count": metadata.get("word_count", ""),
            "params": {
                "author": task.get("author", metadata.get("author")),
                "tone": task.get("tone"),
                "guidelines": task.get("guidelines"),
                "avatar": task.get("avatar", ""),
                "bio": task.get("bio", ""),
                "created": datetime.now().isoformat()
            }
        }

        # Validate required fields
        # missing_fields = [field for field in SAMPLE_JSON if not frontmatter_data.get(field)]
        # if missing_fields:
        #     raise ValueError(f"Missing required frontmatter fields: {', '.join(missing_fields)}")

        return frontmatter_data

    def write_markdown_with_frontmatter(self, layout: str, metadata: dict, filename: str) -> str:
        """Writes markdown content with proper frontmatter."""
        os.makedirs(self.output_dir, exist_ok=True)

        # Sanitize filename
        safe_filename = self._slugify_filename(filename)
        if not safe_filename.lower().endswith('.md'):
            safe_filename += '.md'

        output_path = os.path.join(self.output_dir, safe_filename)

        try:
            post = frontmatter.Post(layout, **metadata)
            with open(output_path, "wb") as f:
                frontmatter.dump(post, f)

            logger.info(f"Successfully wrote markdown to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to write markdown file: {e}")
            raise

    async def write_report_by_formats(self, layout: str, research_state: dict, publish_formats: dict) -> dict:
        """Handles writing reports in all requested formats."""
        file_paths = {}
        metadata = self.generate_frontmatter(research_state)

        # Generate a safe filename from the title
        base_filename = self._slugify_filename(metadata["title"])

        max_retries = 3
        for format_name in publish_formats:
            if not publish_formats[format_name]:
                continue

            for attempt in range(max_retries):
                try:
                    if format_name in ("md", "markdown"):
                        md_filename = f"{base_filename}.md"
                        md_path = self.write_markdown_with_frontmatter(layout, metadata, md_filename)
                        file_paths["md"] = md_path

                    elif format_name == "pdf":
                        pdf_path = await write_md_to_pdf(layout, self.output_dir, filename=f"{base_filename}.pdf")
                        file_paths["pdf"] = pdf_path

                    elif format_name == "docx":
                        docx_path = await write_md_to_word(layout, self.output_dir, filename=f"{base_filename}.docx")
                        file_paths["docx"] = docx_path

                    elif format_name == "json":
                        json_path = write_to_json(
                            {**research_state, "content": layout, "metadata": metadata},
                            self.output_dir,
                            filename=f"{base_filename}.json"
                        )
                        file_paths["json"] = json_path

                    break  # Success, exit retry loop

                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to write {format_name} after {max_retries} attempts: {e}")
                        if self.websocket and self.stream_output:
                            await self.stream_output("error", "publishing",
                                                     f"Failed to generate {format_name}: {str(e)}",
                                                     self.websocket)
                    else:
                        logger.warning(f"Retry {attempt + 1} for {format_name} due to: {e}")
                        continue

        return file_paths

    async def publish_research_report(self, research_state: dict, publish_formats: dict) -> str:
        """Main method to publish the research report with robust validation"""
        try:
            # Validate input structure first
            self._validate_research_state(research_state)

            # Generate layout with content validation
            layout = self.generate_layout(research_state)

            if not layout or not layout.strip():
                raise ValueError("Generated layout is empty. Check content structure.")

            # Proceed with publishing
            written_files = await self.write_report_by_formats(layout, research_state, publish_formats)
            logger.info("Successfully published files: %s", list(written_files.keys()))

            return layout

        except Exception as e:
            error_info = {
                "error": str(e),
                "type": type(e).__name__,
                "research_state_keys": list(research_state.keys()) if research_state else None,
            }
            logger.error("Publishing failed: %s", json.dumps(error_info, indent=2))

            if self.websocket:
                await self.stream_output(
                    "error",
                    "publishing",
                    f"Publishing failed: {type(e).__name__} - {str(e)}",
                    self.websocket
                )
            raise

    async def run(self, research_state: dict) -> dict:
        """Entry point with enhanced error logging and retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                task = research_state.get("task", {})
                publish_formats = task.get("publish_formats", {"md": True})

                if self.websocket and self.stream_output:
                    await self.stream_output(
                        "logs", "publishing",
                        "Publishing final research report...",
                        self.websocket
                    )

                final_research_report = await self.publish_research_report(research_state, publish_formats)
                return {
                    "report": final_research_report,
                    "metadata": self.generate_frontmatter(research_state),
                    "success": True
                }

            except Exception as e:
                if attempt == max_retries - 1:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    tb = traceback.extract_tb(exc_tb)[-1]
                    error_details = {
                        "error": str(e),
                        "type": exc_type.__name__,
                        "file": tb.filename,
                        "line": tb.lineno,
                        "function": tb.name,
                    }

                    logger.error(
                        f"PublisherAgent failed after {max_retries} attempts at {error_details['file']}:{error_details['line']} "
                        f"(function: {error_details['function']})\n"
                        f"Error: {error_details['type']} - {error_details['error']}",
                        exc_info=True
                    )

                    if self.websocket:
                        await self.stream_output(
                            "error",
                            "publishing",
                            f"Failed after {max_retries} attempts at line {error_details['line']}: {error_details['error']}",
                            self.websocket
                        )

                    return {
                        "error": error_details,
                        "success": False
                    }
                else:
                    logger.warning(f"Retry {attempt + 1} due to: {e}")
                    continue
