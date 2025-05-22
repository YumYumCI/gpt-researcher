from datetime import datetime
import json as json
from extensions.agents.utils.views import print_agent_output
from extensions.agents.utils.llms import call_model

sample_json = """
{
  "title": "A catchy, SEO-friendly title for the blog post",
  "author": "Name of the researcher or author (optional)",
  "date": "YYYY-MM-DD",
  "tags": ["tag1", "tag2", "tag3"],

  "table_of_contents": "A table of contents in markdown syntax (using '-') that reflects the main blog sections and nested subsections, if any.",

  "introduction": "A compelling, markdown-formatted introduction that hooks the reader, clearly explains the purpose of the blog, and includes relevant hyperlink references to sources.",

  "main_content": [
    {
      "heading": "Main Section 1",
      "content": "Markdown-formatted paragraph(s) explaining this section in detail with embedded hyperlinks and optional bullet points or numbered lists.",
      "subsections": [
        {
          "subheading": "Subsection A",
          "content": "Detailed explanation in markdown with references."
        },
        {
          "subheading": "Subsection B",
          "content": "Another detailed explanation."
        }
      ]
    }
  ],

  "conclusion": "A markdown-formatted conclusion that summarizes key takeaways, adds a personal or insightful touch, and includes hyperlink references to key sources.",

  "sources": [
    "- Author, Year. *Title of the Source*. [source name](https://source-url.com)"
  ]
}
"""

class WriterAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers

    def get_headers(self, research_state: dict):
        return {
            "title": research_state.get("title"),
            "author": research_state.get("author", "Unknown Author"),
            "date": "Date",
            "tags": research_state.get("tags", [])
        }

    async def write_sections(self, research_state: dict):
        query = research_state.get("title")
        data = research_state.get("research_data")
        task = research_state.get("task")
        follow_guidelines = task.get("follow_guidelines")
        guidelines = task.get("guidelines")

        prompt = [
            {
                "role": "system",
                "content": "You are a research writer. Your task is to write a blog-style research article "
                           "using provided research data in a clear, structured, engaging format."
                           "Crafting compelling narratives that keep readers engaged"
                           "Structuring content for optimal readability"
                           "Adapting tone and style to match the target audience"
                           "Incorporating storytelling techniques"
                           "Using persuasive language without being salesy"
            },
            {
                "role": "user",
                "content": f"""Today's date is {datetime.now().strftime('%Y-%m-%d')}.
Topic: {query}

Research data:
{json.dumps(data, indent=2)}

Your task:
Write a detailed, markdown-formatted blog article that includes a title, author, date, tags, introduction, 
detailed main content sections with subsections, a conclusion, and a list of sources in APA style.

Each section should be engaging and informative, including markdown hyperlinks where appropriate.
If guidelines are provided, follow them strictly: {guidelines if follow_guidelines else 'No specific guidelines'}.

Return only a valid JSON structure that conforms to this format:
{sample_json}
"""
            }
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json"
        )
        return response

    async def revise_headers(self, task: dict, headers: dict):
        prompt = [
            {
                "role": "system",
                "content": "You are a research writer. Your task is to revise headers based on provided guidelines."
            },
            {
                "role": "user",
                "content": f"""Revise the following metadata headers according to these guidelines:
Guidelines: {task.get("guidelines")}

Headers:
{json.dumps(headers, indent=2)}

Respond with a corrected JSON.
"""
            }
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json"
        )
        return {"headers": response}

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "writing_report", "Writing final blog-style research report...", self.websocket)
        else:
            print_agent_output("Writing final blog-style research report...", agent="WRITER")

        blog_json = await self.write_sections(research_state)

        if research_state.get("task").get("verbose"):
            blog_json_str = json.dumps(blog_json, indent=2)
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "blog_content", blog_json_str, self.websocket)
            else:
                print_agent_output(blog_json_str, agent="WRITER")

        headers = self.get_headers(research_state)
        if research_state.get("task").get("follow_guidelines"):
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "revising_headers", "Revising blog headers based on guidelines...", self.websocket)
            else:
                print_agent_output("Revising blog headers based on guidelines...", agent="WRITER")
            headers = await self.revise_headers(research_state.get("task"), headers)
            headers = headers.get("headers")

        return {**blog_json, "headers": headers}