class AgentFactory:
    @staticmethod
    def create_agent(agent_type: str, config: Dict) -> Any:
        if agent_type == "research":
            return ResearchAgent(**config)
        elif agent_type == "editor":
            return EditorAgent(**config)
        # ... other agents