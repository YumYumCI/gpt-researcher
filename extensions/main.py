from dotenv import load_dotenv
import os
import sys
import uuid
import asyncio
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from extensions.team_builder import build_agents
from extensions.agents.orchestrator import ChiefEditorAgent

logging.basicConfig(level=logging.INFO)
load_dotenv()


def open_task(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Task file not found: {filepath}")

    with open(filepath, 'r') as f:
        task = json.load(f)

    if not task:
        raise Exception("No task found in the file.")

    # Extract model from STRATEGIC_LLM
    strategic_llm = os.getenv("STRATEGIC_LLM")
    if strategic_llm:
        task["model"] = strategic_llm.split(":", 1)[1] if ":" in strategic_llm else strategic_llm

    return task


async def main():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_path = os.path.join(current_dir, 'task.json')
    task = open_task(task_path)
    logging.info(f"Loaded task: {task}")

    agents = build_agents(task)
    logging.info(f"Agents built for team: {task.get('team')} using model: {task.get('model')}")

    chief_editor = ChiefEditorAgent(agents, task)
    research_report = await chief_editor.run_research_task(task_id=uuid.uuid4())

    return research_report


if __name__ == "__main__":
    try:
        asyncio.run(main())
        logging.info("Research task completed successfully.")
    except Exception as e:
        logging.error(f"Error during execution: {e}", exc_info=True)
