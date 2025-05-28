import logging
import ast
import json
from datetime import datetime
from gpt_researcher import GPTResearcher
from colorama import Fore, Style
from typing import Dict, Optional, Any, List
from .utils.views import print_agent_output

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.tone = tone
        # self.min_subtopics = 3  # Default minimum subtopics per section

    # section_context: Optional[Dict] = None,
    async def research(self, query: str, research_type: str = "research_report",
                       parent_query: str = "", verbose=True, source="web", tone=None, headers=None):
        """Conduct research for a content section."""
        # Initialize researcher with context
        researcher = GPTResearcher(
            query=query,
            report_type=research_type,
            parent_query=parent_query,
            verbose=verbose,
            report_source=source,
            tone=tone,
            websocket=self.websocket,
            headers=self.headers
        )
        # researcher = GPTResearcher(
        #     parent_query=section_context.get("article_title", "") if section_context else "",
        #     context=section_context)

        # Conduct research on the given query
        await researcher.conduct_research()
        # Write the report
        report = await researcher.write_report()

        #print_agent_output(f"Research report: {report}", agent="RESEARCHER")
        return report

        # return {
        #     "content": report,
        #     "metadata": {
        #         "query": query,
        #         "source": source,
        #         "timestamp": datetime.now().isoformat()
        #     }
        # }

    # async def run_section_research(
    #         self,
    #         #section: Dict,
    #         article_metadata: Dict,
    #         previous_sections: List[Dict],
    #         verbose: bool = True,
    #         source: str = "web"
    # ) -> Dict:
    #     """Research for a specific content section with context."""
    #     try:
    #         section_context = {
    #             "article_title": article_metadata.get("title", ""),
    #             "section_heading": section.get("heading", ""),
    #             "previous_sections": [s.get("heading", "") for s in previous_sections],
    #             "target_wordcount": article_metadata.get("target_wordcount", 0),
    #             "tone": self.tone
    #         }
    #
    #         if self.websocket and self.stream_output:
    #             await self.stream_output(
    #                 "logs",
    #                 "section_research",
    #                 f"Researching section: {section.get('heading')}",
    #                 self.websocket
    #             )
    #
    #         research_result = await self.research(
    #             query=section.get("heading", ""),
    #             section_context=section_context,
    #             research_type="subtopic_report",
    #             verbose=verbose,
    #             source=source
    #         )
    #
    #         return {
    #             **section,
    #             "research": research_result,
    #             "subsections": await self._research_subsections(
    #                 section,
    #                 article_metadata,
    #                 verbose,
    #                 source
    #             )
    #         }
    #
    #     except Exception as e:
    #         error_msg = f"Error researching section {section.get('heading')}: {str(e)}"
    #         print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
    #         if self.websocket and self.stream_output:
    #             await self.stream_output("error", "research", error_msg, self.websocket)
    #         return {
    #             **section,
    #             "error": error_msg
    #         }

    # async def _research_subsections(
    #         self,
    #         section: Dict,
    #         article_metadata: Dict,
    #         verbose: bool,
    #         source: str
    # ) -> List[Dict]:
    #     """Handle subsection research if needed."""
    #     if not section.get("subsections"):
    #         return []
    #
    #     return [
    #         await self.run_section_research(
    #             subsection,
    #             article_metadata,
    #             [],
    #             verbose,
    #             source
    #         )
    #         for subsection in section.get("subsections", [])
    #     ]

    async def run_subtopic_research(self, parent_query: str, subtopic: str, verbose: bool = True, source="web",
                                    headers=None):
        try:
            report = await self.research(
                parent_query=parent_query,
                query=subtopic,
                research_type="subtopic_report",
                verbose=verbose,
                source=source,
                tone=self.tone,
                headers=None
            )
        except Exception as e:
            print(f"{Fore.RED}Error in researching topic {subtopic}: {e}{Style.RESET_ALL}")
            report = None
        return {subtopic: report}

    async def run_initial_research(self, research_state: dict):
        task = research_state.get("task")
        query = task.get("query")
        source = task.get("source", "web")

        if self.websocket and self.stream_output:
            await self.stream_output("logs", "initial_research",
                                     f"Running initial research on the following query: {query}", self.websocket)
        else:
            print_agent_output(f"Running initial research on the following query: {query}", agent="RESEARCHER")
        return {"task": task, "initial_research": await self.research(
            query=query,
            verbose=task.get("verbose"),
            source=source,
            tone=self.tone,
            headers=self.headers
        )}

    # research_state = json.dumps(research_state)
    # research_state = ast.literal_eval(research_state)

    async def run_depth_research(self, draft_state: dict):
        """Conduct in-depth research for a specific section."""
        task = draft_state.get("task")
        topic = draft_state.get("topic")
        parent_query = task.get("query")
        source = task.get("source", "web")
        verbose = task.get("verbose")
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "depth_research",
                                     f"Running in depth research on the following report topic: {topic}",
                                     self.websocket)
        else:
            print_agent_output(f"Running in depth research on the following report topic: {topic}", agent="RESEARCHER")
        research_draft = await self.run_subtopic_research(
            parent_query=parent_query,
            subtopic=topic,
            verbose=verbose,
            source=source,
            headers=self.headers
        )

        return {"draft": research_draft}
