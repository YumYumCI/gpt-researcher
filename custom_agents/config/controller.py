from typing import Dict, Any

from custom_agents.agents import ResearchAgent, ReviserAgent, ReviewerAgent, HumanAgent
from custom_agents.agents.blogger import EditorAgent, WriterAgent, PublisherAgent


def initialize_agents(config: Dict) -> Dict[str, Any]:
    """Initialize all agents with shared dependencies"""
    websocket = config.get('websocket')
    stream_output = config.get('stream_output')
    headers = config.get('headers', {})

    return {
        "research": ResearchAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "editor": EditorAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "reviewer": ReviewerAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "reviser": ReviserAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "writer": WriterAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "publisher": PublisherAgent(
            output_dir=config['output_dir'],
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        ),
        "human": HumanAgent(
            websocket=websocket,
            stream_output=stream_output,
            headers=headers
        )
    }