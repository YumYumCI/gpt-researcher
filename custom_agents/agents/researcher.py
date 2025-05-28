from datetime import datetime
import logging
from gpt_researcher import GPTResearcher
from colorama import Fore, Style
from typing import Dict, Optional, List, Union
from .utils.views import print_agent_output

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.tone = tone or "neutral"
        self.min_subtopics = 3  # Default minimum subtopics per section

    async def research(
            self,
            query: str,
            section_context: Optional[Dict] = None,
            research_type: str = "deep",
            verbose: bool = True,
            source: str = "web"
    ) -> Dict:
        """Conduct research for a content section."""
        # Initialize researcher with context
        researcher = GPTResearcher(
            query=query,
            report_type=research_type,
            parent_query=section_context.get("article_title", "") if section_context else "",
            verbose=verbose,
            report_source=source,
            tone=self.tone,
            websocket=self.websocket,
            headers=self.headers,
            context=section_context
        )

        await researcher.conduct_research()
        report = await researcher.write_report()

        return {
            "content": report,
            "metadata": {
                "query": query,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def run_section_research(
            self,
            parent_query: str,
            section: Union[str, Dict],  # Document both formats
            article_metadata: Dict,
            previous_sections: List[Dict],
            verbose: bool,
            source: str
    ) -> Dict:
        try:
            # Normalize a section to get a heading
            section_heading = section if isinstance(section, str) else section.get('heading', '')

            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "section_research",
                    f"Researching section: {section_heading}",  # Use normalized heading
                    self.websocket
                )

            section_context = {
                "article_title": article_metadata.get("title", ""),
                "section_heading": section_heading,
                "previous_sections": [s.get('heading', '') if isinstance(s, dict) else str(s)
                                      for s in previous_sections],
                "target_wordcount": article_metadata.get("target_wordcount", 0),
                "tone": self.tone
            }

            research_result = await self.research(
                query=section_heading,  # Use heading as a query
                section_context=section_context,
                research_type="subtopic_report",
                verbose=verbose,
                source=source
            )

            return {
                "heading": section_heading,
                "content": "",
                "research": research_result,
                "subsections": await self._research_subsections(
                    {"heading": section_heading} if isinstance(section, str) else section,
                    article_metadata,
                    verbose,
                    source
                )
            }

        except Exception as e:
            error_msg = f"Error researching section {section_heading}: {str(e)}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            if self.websocket and self.stream_output:
                await self.stream_output("error", "research", error_msg, self.websocket)
            return {
                "heading": section_heading,
                "error": error_msg
            }

    async def _research_subsections(
            self,
            section: Dict,  # Changed from str to Dict
            article_metadata: Dict,
            verbose: bool,
            source: str
    ) -> List[Dict]:
        """Handle subsection research if needed.

        Args:
            section: Dictionary containing section data with:
                - heading: str
                - subsections: List[Dict] (optional)
            article_metadata: Article metadata dict
            verbose: bool for verbosity
            source: str source identifier

        Returns:
            List of researched subsection dictionaries
        """
        if not section or not isinstance(section, dict):
            return []

        # Get subsections if they exist, default to an empty list
        subsections = section.get("subsections", [])

        if not isinstance(subsections, list):
            logger.warning(f"Unexpected subsections type: {type(subsections)}")
            return []

        results = []
        for subsection in subsections:
            try:
                # Ensure we have a heading to research
                if isinstance(subsection, dict):
                    subsection_heading = subsection.get("heading", "")
                else:
                    subsection_heading = str(subsection)

                if not subsection_heading:
                    continue

                # Research the subsection
                result = await self.run_section_research(
                    parent_query=article_metadata.get("title", ""),
                    section=subsection_heading,  # Pass string heading
                    article_metadata=article_metadata,
                    previous_sections=[],
                    verbose=verbose,
                    source=source
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to research subsection: {str(e)}")
                continue

        return results

    async def run_initial_research(self, research_state: Dict) -> Dict:
        """Conduct initial high-level research."""
        task = research_state.get("task", {})
        query = task.get("query", "")
        source = task.get("source", "web")

        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "initial_research",
                f"Running initial research on: {query}",
                self.websocket
            )

        initial_research = await self.research(
            query=query,
            research_type="subtopic_report",
            verbose=task.get("verbose", True),
            source=source
        )

        return {
            **research_state,
            "initial_research": initial_research,
            "metadata": {
                "title": query,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        }

    async def run_depth_research(self, draft_state: dict):
        #print_agent_output(f"Raw draft state received: {draft_state}", agent="RESEARCHER")

        # First, try to get the topic from the explicit field
        topic = draft_state.get("topic")

        # If not found, try to get it from the section structure
        if not topic:
            section = draft_state.get("section", {})
            topic = section.get("heading")

        # Final fallback to the old format
        if not topic:
            topic = draft_state.get("topic", "")

        if not topic:
            raise ValueError("No research topic provided in: " + str(draft_state.keys()))

        task = draft_state.get("task", {})
        article_metadata = draft_state.get("metadata", {})
        previous_sections = draft_state.get("previous_sections", [])

        return {
            "draft": await self.run_section_research(
                parent_query=task.get("query", ""),
                section=topic,  # Pass the extracted topic
                article_metadata=article_metadata,
                previous_sections=previous_sections,
                verbose=task.get("verbose", True),
                source=task.get("source", "web")
            ),
            "metadata": article_metadata
        }
