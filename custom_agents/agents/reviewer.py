from .utils.views import print_agent_output
from .utils.llms import call_model

TEMPLATE = """You are an expert article reviewer. \
Your goal is to review research drafts and provide feedback to the reviser only based on specific guidelines. \
"""


class ReviewerAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def review_draft(self, draft_state: dict):
        """
        Review a draft article
        :param draft_state:
        :return:
        """
        task = draft_state.get("task")
        guidelines = "- ".join(guideline for guideline in task.get("guidelines"))
        revision_notes = draft_state.get("revision_notes")

        revise_prompt = f"""
        The reviser has already revised the draft based on your previous feedback: {revision_notes}\n
        
        **Provide additional feedback ONLY if:**  
        - Critical issues remain (e.g., factual errors, tone mismatch).  
        - The revisions failed to address your original notes. 
        
        If the article is now sufficient or only minor tweaks are needed, return `None`.
        
        You have been tasked with reviewing the draft which was written by a non-expert based on specific guidelines.
Please accept the draft if it is good enough to publish, or send it for revision, along with your notes to guide the revision.
If not all of the guideline criteria are met, you should send appropriate revision notes.
If the draft meets all the guidelines, please return None.
        """

        review_prompt = f"""
        You are an article reviewer. Your task is to evaluate a draft based on the following criteria:  
        
        **Key Evaluation Factors:**  
        1. **Clarity & Structure** – Is the article logically organized with smooth transitions?  
        2. **Audience Fit** – Does the tone (casual, professional, technical) match the target readers?  
        3. **Engagement** – Does it hold interest with storytelling, examples, or persuasive techniques?  
        4. **Accuracy** – Are claims supported by evidence (if research-based)?  
        5. **Guideline Adherence** – Does it follow the specified format (blog, news, tutorial, etc.)?  

        **Decision Rules:**  
        - ✅ **Accept** if the draft meets all criteria (return `None`).  
        - 🔄 **Revise** if improvements are needed (provide clear, actionable notes).  

        **Input:** Article draft, target audience, and guidelines.  
        **Output:** Revision notes (if needed) or `None`.  
        {revise_prompt if revision_notes else ""}

        Guidelines: {guidelines}\nDraft: {draft_state.get("draft")}\n
        """
        prompt = [
            {"role": "system", "content": TEMPLATE},
            {"role": "user", "content": review_prompt},
        ]

        response = await call_model(prompt, model=task.get("model"))

        if task.get("verbose"):
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "review_feedback",
                    f"Review feedback is: {response}...",
                    self.websocket,
                )
            else:
                print_agent_output(
                    f"Review feedback is: {response}...", agent="REVIEWER"
                )

        if "None" in response:
            return None
        return response

    async def run(self, draft_state: dict):
        task = draft_state.get("task")
        guidelines = task.get("guidelines")
        to_follow_guidelines = task.get("follow_guidelines")
        review = None
        if to_follow_guidelines:
            print_agent_output(f"Reviewing draft...", agent="REVIEWER")

            if task.get("verbose"):
                print_agent_output(
                    f"Following guidelines {guidelines}...", agent="REVIEWER"
                )

            review = await self.review_draft(draft_state)
        else:
            print_agent_output(f"Ignoring guidelines...", agent="REVIEWER")
        return {"review": review}
