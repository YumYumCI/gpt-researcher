def build_agents(task, websocket=None, stream_output=None, tone=None, headers=None):
    task_team = task.get("team", "default")
    output_dir = task.get("output_dir", "./extensions/outputs")

    if task_team == "blogger":
        from agents.blogger import EditorAgent, WriterAgent, PublisherAgent
    elif task_team == "journalist":
        from agents.journalist import EditorAgent, WriterAgent, PublisherAgent
    else:
        from agents import EditorAgent, WriterAgent, PublisherAgent

    from agents import ResearchAgent, HumanAgent

    return {
        "writer": WriterAgent(websocket, stream_output, headers),
        "editor": EditorAgent(websocket, stream_output, tone, headers),
        "research": ResearchAgent(websocket, stream_output, tone, headers),
        "publisher": PublisherAgent(output_dir, websocket, stream_output, headers),
        "human": HumanAgent(websocket, stream_output, headers)
    }