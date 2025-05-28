from datetime import datetime
import asyncio
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
from custom_agents.agents.utils.views import print_agent_output
from custom_agents.agents.utils.llms import call_model
from custom_agents.memory.draft import DraftState
from custom_agents.agents import ResearchAgent, ReviewerAgent, ReviserAgent
import logging
import json5 as json
import re

logger = logging.getLogger(__name__)


class EditorAgent:
    """Agent responsible for editing and managing code."""

    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.tone = tone
        self.headers = headers or {}

    # self.required_sections = ["introduction", "main_content", "conclusion"]

    async def plan_research(self, research_state: Dict[str, any]) -> Dict[str, any]:
        initial_research = research_state.get("initial_research")
        task = research_state.get("task")
        include_human_feedback = task.get("include_human_feedback")
        human_feedback = research_state.get("human_feedback")
        max_sections = task.get("max_sections")

        prompt = self._create_planning_prompt(initial_research, include_human_feedback, human_feedback, max_sections)

        print_agent_output("Planning an outline layout based on initial research...", agent="EDITOR")

        # try:
        # Call model with timeout and retry
        plan = await call_model(
            prompt=prompt,
            model=task.get("model"),
            response_format="json",
        )

        #print_agent_output(f"PLAN JSON OUTPUT...: {plan}", agent="EDITOR")

        return {
            "title": plan.get("title"),
            "date": plan.get("date"),
            "sections": plan.get("sections"),
        }


    # Convert single quotes to double quotes if needed
    # if isinstance(plan, str):
    #     try:
    #         plan = json.loads(plan)
    #     except json.JSONDecodeError:
    #         # If that fails, try converting single quotes
    #         normalized_json = re.sub(r"(?<!\\)'", '"', plan)
    #         plan = json.loads(normalized_json)
    # else:
    #     plan = plan
    # # Validate basic response structure
    # if not isinstance(plan, dict):
    #     raise ValueError("Model did not return a valid JSON object")
    #
    # logger.info(f"Raw model response: {plan}")

    # if "content" not in plan:
    #   raise ValueError("Model response missing required 'content' field")
    # if not all(section in plan.get("content", {}) for section in self.required_sections):
    #   raise ValueError("Generated plan missing required sections")

    # except Exception as e:
    #     error_msg = f"Failed to generate plan: {str(e)}"
    #     if self.websocket and self.stream_output:
    #         await self.stream_output("error", "planning", error_msg, self.websocket)
    #     logger.error(error_msg)
    #     raise  # Re-raise after logging

    # Validate basic structure
    # First get the metadata once
    # metadata = plan.get("metadata", {})
    # content = plan.get("content", {})

    # Validate content structure
    # if not isinstance(content, dict):
    #   raise ValueError("Content must be a dictionary")

    # missing_sections = [
    #     section for section in self.required_sections
    #     if section not in content or not isinstance(content[section], dict)
    # ]

    # if missing_sections:
    #     raise ValueError(
    #         f"Generated plan missing or invalid required sections: {', '.join(missing_sections)}"
    #     )

    # Validate metadata types
    # title = metadata.get("title", "Untitled")
    # if not isinstance(title, str):
    #     raise ValueError("Title must be a string")
    #
    # tags = metadata.get("tags", [])
    # if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
    #     raise ValueError("Tags must be a list of strings")

    # return {
    #     "metadata": {
    #         "title": title,
    #         "date": datetime.now().strftime("%Y-%m-%d"),
    #         "description": metadata.get("description", ""),
    #         "tags": tags
    #     },
    #     "content": content  # Now guaranteed to exist and be a dict
    # }

    async def run_parallel_research(self, research_state: Dict[str, any]) -> Dict[str, List[str]]:
        """
          Execute parallel research for each main content section.

          Returns:
              {"research_data": List[Dict]}  # Research results for each section
          """

        agents = self._initialize_agents()
        workflow = self._create_workflow()
        chain = workflow.compile()

        queries = research_state.get("content", {}).get("main_content", [])
        #queries = research_state["content"]["main_content"]["subsections"]["subheading"]
        title = research_state

        print_agent_output(f"Running parallel research for the following Title and Queries ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^: {title} /n/n {queries}", agent="EDITOR")

        self._log_parallel_research(queries)

        final_drafts = [
            chain.ainvoke(self._create_task_input(
                research_state, query, title))
            for query in queries
        ]

        research_results = [
            result["draft"] for result in await asyncio.gather(*final_drafts)
        ]

        return {"research_data": research_results}

    # main_content = research_state.get("content", {}).get("main_content", [])
    # if not main_content:
    #     raise ValueError("No main content sections found for research")
    #
    # self._log_parallel_research([section.get("heading", "") for section in main_content])

    # Execute research for each section
    # research_tasks = [
    #     chain.ainvoke(self._create_section_input(research_state, section))
    #     for section in main_content
    # ]
    # results = await asyncio.gather(*research_tasks)
    # return {
    #     "research_data": [result["draft"] for result in results],
    #     "content": {
    #         "main_content": [
    #             {**section, "research": result["draft"]}
    #             for section, result in zip(main_content, results)
    #         ]
    #     } }

    def _create_planning_prompt(self, initial_research: str, include_human_feedback: bool,
                                human_feedback: Optional[str], max_sections: int) -> List[Dict[str, str]]:
        """Create a prompt for structured content planning."""
        return [
            {
                "role": "system",
                "content": f""" 
                You are an editor. Your goal is to oversee the article creation process from inception to completion.
                Your main task is to plan a clear and engaging article structure based on the topic, target audience, 
                and purpose (e.g., informative, persuasive, tutorial).
                
                Key Responsibilities:  
                1. **Define Structure**: Outline sections (e.g., introduction, key points, conclusion) tailored to the article type (blog post, news piece, guide, etc.).  
                2. **Audience Alignment**: Ensure the tone and depth match the readers' expertise (casual, technical, general public).  
                3. **Purpose Clarity**: Highlight whether the article aims to inform, persuade, entertain, or instruct.  
                4. **SEO/Readability**: Suggest headings and subheadings for clarity and search engine optimization if applicable.  
                """
            },
            {
                "role": "user",
                "content": self._format_planning_instructions(
                    initial_research,
                    include_human_feedback,
                    human_feedback,
                    max_sections),
            }
        ]

    # def _create_section_input(self, research_state: Dict[str, Any], section: Dict) -> Dict[str, Any]:
    #     """Create input for a single section research task with proper null checks"""
    #     if not isinstance(section, dict):
    #         raise ValueError("Section must be a dictionary")
    #
    #     task = research_state.get("task", {})
    #     metadata = research_state.get("metadata", {})
    #     content = research_state.get("content", {}).get("main_content", [])
    #
    #     return {
    #         "task": task,
    #         "topic": section.get("heading", ""),
    #         "metadata": metadata,
    #         "headers": self.headers,
    #         "section_context": {
    #             "article_title": metadata.get("title", ""),
    #             "previous_sections": [
    #                 s.get("heading", "")
    #                 for s in content
    #                 if isinstance(s, dict) and s != section
    #             ]
    #         }
    #     }

    def _format_planning_instructions(self, initial_research: str, include_human_feedback: bool,
                                      human_feedback: Optional[str], max_sections: int) -> str:
        """Format the instructions for research planning."""
        today = datetime.now().strftime('%Y-%m-%d')
        feedback_instruction = (
            f"Human feedback: {human_feedback}. You must plan the sections based on the human feedback."
            if include_human_feedback and human_feedback and human_feedback != 'no'
            else ''
        )

        return f"""Today's date is {today}
                   summary report: '{initial_research}'
                   {feedback_instruction}
                   \nYour task is to generate an outline of sections headers for the project
                   based on the summary report above.
                   You must generate a maximum of {max_sections} section headers.
                   You must focus ONLY on related topics for subheaders and do NOT include introduction, conclusion and references.
                   You must return nothing but a JSON with the fields 'title' (str) and 
                   'sections' (maximum {max_sections} section headers) with the following structure:
                   '{{title: string research title, date: today's date, 
                   sections: ['section header 1', 'section header 2', 'section header 3' ...]}}'."""

    def _initialize_agents(self) -> Dict[str, any]:
        """Initialize the research, reviewer, and reviser skills."""
        return {
            "research": ResearchAgent(self.websocket, self.stream_output, self.tone, self.headers),
            "reviewer": ReviewerAgent(self.websocket, self.stream_output, self.headers),
            "reviser": ReviserAgent(self.websocket, self.stream_output, self.headers),
        }

    def _create_workflow(self) -> StateGraph:

        """Create the workflow for the research process."""
        agents = self._initialize_agents()
        workflow = StateGraph(DraftState)

        workflow.add_node("researcher", agents["research"].run_depth_research)
        workflow.add_node("reviewer", agents["reviewer"].run)
        workflow.add_node("reviser", agents["reviser"].run)

        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "reviewer")
        workflow.add_edge("reviser", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            lambda draft: "accept" if draft["review"] is None else "revise",
            {"accept": END, "revise": "reviser"},
        )

        return workflow

    def _log_parallel_research(self, queries: List[str]) -> None:
        """Log the start of parallel research tasks."""
        if self.websocket and self.stream_output:
            asyncio.create_task(self.stream_output(
                "logs",
                "parallel_research",
                f"Running parallel research for the following queries: {queries}",
                self.websocket,
            ))
        else:
            print_agent_output(
                f"Running the following research tasks in parallel: {queries}...",
                agent="EDITOR",
            )

    def _create_task_input(self, research_state: Dict[str, any], query: str, title: str) -> Dict[str, any]:
        """Create the input for a single research task."""
        return {
            "task": research_state.get("task"),
            "topic": query,
            "title": title,
            "headers": self.headers,
        }
