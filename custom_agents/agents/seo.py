from typing import Dict, Any
from gpt_researcher.agent import BaseAgent
from custom_agents.prompts.custom_prompt_family import CustomPromptFamily
from ..utils.views import print_agent_output
from ..utils.llms import call_model

class SEOAgent(BaseAgent):
    """Specialized agent for SEO content and metadata generation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_family = CustomPromptFamily(self.config)

    async def generate_metadata(self, topic: str, context: str) -> Dict[str, str]:
        """Generate comprehensive SEO metadata"""
        prompt = f"""
{CustomPromptFamily.seo_expert_context_prompt()}

TOPIC: {topic}
CONTEXT: {context}

Generate complete SEO metadata including:

1. **Slug**: URL-friendly version (lowercase, hyphens)
2. **Focus Keyword**: Primary keyword (1-2 words)
3. **Secondary Keywords**: 3-5 related terms  
4. **Meta Title**: <60 chars with keyword
5. **Meta Description**: 150-160 chars with keyword
6. **Schema Markup**: JSON-LD schema type recommendation
7. **Internal Links**: 3 suggested internal links
8. **Image Alt Texts**: 2 generic alt text templates

Respond ONLY in this JSON format:
{{
    "slug": "example-slug",
    "focus_keyword": "main keyword",
    "secondary_keywords": ["kw1", "kw2"],
    "meta_title": "Title",
    "meta_description": "Description",
    "schema_type": "Article/BlogPosting/Product",
    "internal_links": ["/link1", "/link2"],
    "alt_texts": ["Alt text 1", "Alt text 2"]
}}
"""
        response = await self.llm.aresearch(prompt)
        return self._validate_metadata(response)

    async def run(self, research_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute full SEO optimization pipeline"""
        # Generate metadata first
        metadata = await self.generate_metadata(
            research_state.get("task", ""),
            research_state.get("context", "")
        )

        # Then create optimized content
        research_state["seo_metadata"] = metadata
        report = await self.report_generator.generate_report(research_state)

        return {
            **research_state,
            "final_report": report,
            "seo_metadata": metadata
        }

    def _validate_metadata(self, metadata: str) -> Dict[str, Any]:
        """Clean and validate metadata output"""
        # Add parsing/validation logic here
        return metadata