import os
import time
import datetime
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver
from .utils.views import print_agent_output
from custom_agents.memory.research import ResearchState
from .utils.utils import sanitize_filename

import uuid
from typing import Optional, Dict, Any


class ChiefEditorAgent:
    """Agent responsible for managing and coordinating editing tasks."""

    def __init__(
        self,
        agents: Dict[str, Any],
        task: Dict[str, Any],
        websocket: Optional[Any] = None,
        stream_output: Optional[Any] = None,
        tone: Optional[Any] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        self.task = task
        self.agents = agents
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.tone = tone
        self.task_id = self._generate_task_id()
        self.output_dir = self._create_output_directory()
        self.agents["publisher"].output_dir = self.output_dir

    def _generate_task_id(self) -> str:
        """Generate a unique task ID using UUID."""
        return str(uuid.uuid4())

    def _create_output_directory(self):

        query = self.task.get("query") or "no_query"
        query_snippet = query[:40] if isinstance(query, str) else "no_query"

        output_dir = os.path.join("custom_agents", "reports", sanitize_filename(
            f"run_{self.task_id}_{query_snippet}"
        ))

        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _initialize_agents(self):
        """Create the workflow graph using the provided agents."""
        return self._create_workflow(self.agents)

    def _create_workflow(self, agents):
        workflow = StateGraph(ResearchState)

        # Add nodes
        workflow.add_node("browser", agents["research"].run_initial_research)
        workflow.add_node("planner", agents["editor"].plan_research)
        workflow.add_node("researcher", agents["editor"].run_parallel_research)
        workflow.add_node("writer", agents["writer"].run)
        workflow.add_node("publisher", agents["publisher"].run)
        workflow.add_node("human", agents["human"].review_plan)

        # Add edges
        self._add_workflow_edges(workflow)

        return workflow

    def _add_workflow_edges(self, workflow):
        workflow.add_edge("browser", "planner")
        workflow.add_edge("planner", "human")
        workflow.add_edge("researcher", "writer")
        workflow.add_edge("writer", "publisher")
        workflow.set_entry_point("browser")
        workflow.add_edge("publisher", END)

        # Human-in-the-loop conditional edge
        workflow.add_conditional_edges(
            "human",
            lambda review: "accept" if review["human_feedback"] is None else "revise",
            {"accept": "researcher", "revise": "planner"}
        )

    def init_research_team(self):
        """Initialize the research team workflow."""
        return self._initialize_agents()

    async def _log_research_start(self):
        message = f"Starting the research process for query '{self.task.get('query')}'..."
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "starting_research", message, self.websocket)
        else:
            print_agent_output(message, "MASTER")

    async def run_research_task(self, task_id=None):
        """
        Execute the research task using the defined agent workflow.

        Args:
            task_id (str): Optional unique identifier for the task.

        Returns:
            Dict: Final output from the research pipeline.
        """
        research_team = self.init_research_team()
        chain = research_team.compile()

        await self._log_research_start()

        config = {
            "configurable": {
                "thread_id": task_id or self.task_id,
                "thread_ts": datetime.datetime.utcnow()
            }
        }

        result = await chain.ainvoke({"task": self.task}, config=config)
        return result