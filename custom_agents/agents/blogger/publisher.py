import os
import logging
from custom_agents.agents.utils.file_formats import (
    write_md_to_pdf,
    write_md_to_word,
    write_text_to_md,
    write_to_json
)
from custom_agents.agents.utils.views import print_agent_output

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXPORT_FORMATS = ["md", "pdf", "docx", "json"]


class PublisherAgent:
    def __init__(self, output_dir: str, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.output_dir = output_dir.strip()
        self.headers = headers or {}

    def generate_layout(self, research_state: dict) -> str:
        layout_parts = []
        headers = research_state.get("headers", {})
        title = headers.get("title", research_state.get("title", "Untitled"))
        date = research_state.get("date", "Unknown Date")

        # Header & intro
        layout_parts.append(f"# {title}")
        layout_parts.append(f"#### {headers.get('date', 'Date')}: {date}\n")

        layout_parts.append(f"## {headers.get('introduction', 'Introduction')}")
        layout_parts.append(research_state.get("introduction", ""))

        layout_parts.append(f"## {headers.get('table_of_contents', 'Table of Contents')}")
        layout_parts.append(research_state.get("table_of_contents", ""))

        # Main content with subsections
        for section in research_state.get("main_content", []):
            heading = section.get("heading", "")
            content = section.get("content", "")
            layout_parts.append(f"\n## {heading}\n{content}")

            for subsection in section.get("subsections", []):
                subheading = subsection.get("subheading", "")
                subcontent = subsection.get("content", "")
                layout_parts.append(f"\n### {subheading}\n{subcontent}")

        # Conclusion
        layout_parts.append(f"\n## {headers.get('conclusion', 'Conclusion')}")
        layout_parts.append(research_state.get("conclusion", ""))

        # References
        layout_parts.append(f"\n## {headers.get('references', 'References')}")
        sources = research_state.get("sources", [])
        layout_parts.extend(sources)

        return '\n\n'.join(layout_parts)

    async def write_report_by_formats(self, layout: str, research_state: dict, publish_formats: dict) -> dict:
        file_paths = {}

        if publish_formats.get("pdf"):
            try:
                pdf_path = await write_md_to_pdf(layout, self.output_dir)
                file_paths["pdf"] = pdf_path
            except Exception as e:
                logger.error(f"Failed to write PDF: {e}")

        if publish_formats.get("docx"):
            try:
                docx_path = await write_md_to_word(layout, self.output_dir)
                file_paths["docx"] = docx_path
            except Exception as e:
                logger.error(f"Failed to write DOCX: {e}")

        if publish_formats.get("md") or publish_formats.get("markdown"):
            try:
                md_path = await write_text_to_md(layout, self.output_dir)
                file_paths["md"] = md_path
            except Exception as e:
                logger.error(f"Failed to write Markdown: {e}")

        if publish_formats.get("json"):
            try:
                json_path = write_to_json(research_state, self.output_dir)
                file_paths["json"] = json_path
            except Exception as e:
                logger.error(f"Failed to write JSON: {e}")

        return file_paths

    async def publish_research_report(self, research_state: dict, publish_formats: dict) -> str:
        layout = self.generate_layout(research_state)
        written_files = await self.write_report_by_formats(layout, research_state, publish_formats)
        logger.info(f"Files published: {written_files}")
        return layout

    async def run(self, research_state: dict) -> dict:
        task = research_state.get("task", {})
        publish_formats = task.get("publish_formats", {"md": True})

        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs", "publishing",
                "Publishing final research report based on retrieved data...",
                self.websocket
            )
        else:
            print_agent_output(output="Publishing final research report based on retrieved data...", agent="PUBLISHER")

        final_research_report = await self.publish_research_report(research_state, publish_formats)

        return {"report": final_research_report}