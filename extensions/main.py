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
#from extensions.agents.utils.utils import sanitize_filename
#from gpt_researcher.utils.enum import Tone

logging.basicConfig(level=logging.INFO)
load_dotenv()


def open_task():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_json_path = os.path.join(current_dir, 'task.json')

    with open(task_json_path, 'r') as f:
        task = json.load(f)

    if not task:
        raise Exception(
            "No task found. Please ensure a valid task.json file is present and contains the necessary task information.")

    # logging.info(f"Task file path: {current_dir}")
    # logging.info(f"Task file path: {task.get('query')}")

    strategic_llm = os.environ.get("STRATEGIC_LLM")
    if strategic_llm and ":" in strategic_llm:
        model_name = strategic_llm.split(":", 1)[1]
        task["model"] = model_name
    elif strategic_llm:
        task["model"] = strategic_llm

    return task

async def main():
    task = open_task()
    #logging.info(f"--- Building team: {task.get('team'), task["model"]} ---")
    agents = build_agents(task)
    #logging.info(f"--- Agents include: {agents} ---")
    chief_editor = ChiefEditorAgent(agents, task)
    research_report = await chief_editor.run_research_task(task_id=uuid.uuid4())
    return research_report


if __name__ == "__main__":
    asyncio.run(main())
