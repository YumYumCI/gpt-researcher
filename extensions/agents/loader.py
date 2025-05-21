from blogger import editor
from blogger import writer
from blogger import publisher


from multi_agents.agent_researcher import ResearcherAgent
from multi_agents.agent_reviewer import ReviewerAgent
from multi_agents.agent_publisher import PublisherAgent

AGENT_REGISTRY = {
    "blogger": {
        "editor":       editor,
        "writer":       writer,
        "publisher":    publisher,
    },
    "tech": {
        "editor":       editor,
        "writer":       writer,
        "publisher":    publisher,
    }
}


def build_agents(task):
    task_type = task.get("type")
    if task_type not in AGENT_REGISTRY:
        raise ValueError(f"Unsupported task type: {task_type}")

    editor_cls = AGENT_REGISTRY[task_type]["editor"]
    writer_cls = AGENT_REGISTRY[task_type]["writer"]
    publisher_cls = AGENT_REGISTRY[task_type]["writer"]

    return {
        "editor": editor_cls(task),
        "writer": writer_cls(task),
        "researcher": ResearcherAgent(task),
        "reviewer": ReviewerAgent(task),
        "publisher": PublisherAgent(task)
    }