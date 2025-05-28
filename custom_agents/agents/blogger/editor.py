from datetime import datetime
import asyncio
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
from custom_agents.agents.utils.views import print_agent_output
from custom_agents.agents.utils.llms import call_model
from custom_agents.memory.draft import DraftState
from custom_agents.agents import ResearchAgent, ReviewerAgent, ReviserAgent


class EditorAgent:
    """Agent responsible for editing and managing content creation workflow."""

    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.tone = tone
        self.headers = headers or {}
        self.required_sections = ["introduction", "main_content", "conclusion"]

    def _convert_old_to_new_state(slef, old_state: Dict) -> Dict:
        """Convert old flat structure to new hierarchical one"""
        return {
            "metadata": {
                "title": old_state.get("title"),
                "date": old_state.get("date", datetime.now().strftime("%Y-%m-%d"))
            },
            "content": {
                "main_content": [
                    {"heading": section, "content": ""}
                    for section in old_state.get("sections", [])
                ]
            }
        }

    async def plan_research(self, research_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan the research outline using a new content structure.

        Returns:
            {
                "metadata": {
                    "title": str,
                    "date": str,
                    "description": str,
                    "tags": List[str]
                },
                "content": {
                    "introduction": {"hook": str, "context": str, "thesis": str},
                    "main_content": List[{"heading": str}],
                    "conclusion": {"summary": str, "call_to_action": str}
                }
            }
        """

        task = research_state.get("task", {})
        prompt = self._create_planning_prompt(research_state)

        print_agent_output("Planning research content structure...", agent="EDITOR")
        plan = await call_model(
            prompt=prompt,
            model=task.get("model"),
            response_format="json",
        )

        # Validate basic structure
        if not all(section in plan.get("content", {}) for section in self.required_sections):
            raise ValueError("Generated plan missing required sections")

        return {
            "metadata": {
                "title": plan.get("metadata", {}).get("title", "Untitled"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": plan.get("metadata", {}).get("description", ""),
                "tags": plan.get("metadata", {}).get("tags", [])
            },
            "content": plan["content"]
        }

    async def run_parallel_research(self, research_state: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Execute parallel research for each main content section."""
        # 1. Initialize workflow
        agents = self._initialize_agents()
        workflow = self._create_workflow()  # This creates the StateGraph
        chain = workflow.compile()  # This compiles the executable workflow

        # 2. Get sections to research
        main_content = research_state.get("content", {}).get("main_content", [])
        if not main_content:
            raise ValueError("No main content sections found for research")

        self._log_parallel_research([section.get("heading", "") for section in main_content])

        # 3. Execute research for each section
        research_tasks = [
            chain.ainvoke({
                "task": research_state.get("task"),
                "section": {
                    "heading": section["heading"],  # Explicit heading
                    "content": section.get("content", "")
                },
                "metadata": research_state.get("metadata"),
                "headers": self.headers,
                "section_context": {
                    "article_title": research_state.get("metadata", {}).get("title"),
                    "previous_sections": [s["heading"] for s in main_content[:idx]]
                },
                "topic": section["heading"]  # Explicitly pass the topic
            })
            for idx, section in enumerate(main_content)
        ]

        results = await asyncio.gather(*research_tasks)

        return {
            "research_data": [result["draft"] for result in results],
            "content": {
                "main_content": [
                    {**section, "research": result["draft"]}
                    for section, result in zip(main_content, results)
                ]
            }
        }

    #def _create_planning_prompt(self, initial_research: str, include_human_feedback: bool, human_feedback: Optional[str], max_sections: int) -> List[Dict[str, str]]:

    def _create_planning_prompt(self, research_state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create prompt for structured content planning."""
        task = research_state.get("task", {})
        initial_research = research_state.get("initial_research", "")
        human_feedback = research_state.get("human_feedback", "")

        return [
            {
                "role": "system",
                "content": """You are a content architect. Create a comprehensive content structure including:
                
                 You are an editor. Your goal is to oversee the article creation process from inception to completion.
                Your main task is to plan a clear and engaging article structure based on the topic, target audience, 
                and purpose (e.g., informative, persuasive, tutorial).
                
                Key Responsibilities:  
                1. **Define Structure**: Outline sections (e.g., introduction, key points, conclusion) tailored to the article type (blog post, news piece, guide, etc.).  
                2. **Audience Alignment**: Ensure the tone and depth match the readers' expertise (casual, technical, general public).  
                3. **Purpose Clarity**: Highlight whether the article aims to inform, persuade, entertain, or instruct.  
                4. **SEO/Readability**: Suggest headings and subheadings for clarity and search engine optimization if applicable.  
                5. **Content Structure**: Provide a detailed description of the article's content, including key points, key ideas, and key questions.  
                6. **Content Quality**: Ensure the content is well-structured, engaging, and informative.  
                
1. Metadata (title, description, tags)
2. Introduction (hook, context, thesis) 
3. Main content sections with headings
4. Conclusion (summary, call-to-action)

Return JSON matching this structure:
{
  "metadata": {
    "title": "string",
    "description": "string", 
    "tags": ["string"]
  },
  "content": {
    "introduction": {
      "hook": "string",
      "context": "string",
      "thesis": "string"
    },
    "main_content": [
      {
        "heading": "string"
      }
    ],
    "conclusion": {
      "summary": "string",
      "call_to_action": "string"
    }
  }
}"""
            },
            {
                "role": "user",
                "content": f"""Task Parameters:
- Audience: {task.get('audience', 'general')}
- Tone: {task.get('tone', 'neutral')}
- Word Count: {task.get('word_count', 'flexible')}
- Guidelines: {task.get('guidelines', 'None')}

Initial Research:
{initial_research}

Human Feedback:
{human_feedback if task.get('include_human_feedback') else 'None'}

Generate a content structure with {task.get('max_sections', 3)} main sections."""
            }
        ]
#   def _format_planning_instructions ---------------------------------------------------

    def _create_section_input(self, research_state: Dict[str, Any], section: Dict) -> Dict[str, Any]:
        """Create input for a single section research task."""
        return {
            "task": research_state.get("task"),
            "section": section,  # Pass the whole section now
            "metadata": research_state.get("metadata"),
            "headers": self.headers,
            "section_context": {
                "article_title": research_state.get("metadata", {}).get("title"),
                "previous_sections": [
                    s["heading"] for s in research_state.get("content", {}).get("main_content", [])
                    if s != section
                ]
            }
        }

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
