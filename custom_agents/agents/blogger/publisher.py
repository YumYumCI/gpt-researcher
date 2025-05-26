import os
import logging
import frontmatter
from datetime import datetime
from typing import Dict, List, Optional
from custom_agents.agents.utils.file_formats import (
    write_md_to_pdf,
    write_md_to_word,
    write_to_json
)
from custom_agents.agents.utils.views import print_agent_output

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXPORT_FORMATS = ["md", "pdf", "docx", "json"]


class PublisherAgent:
    def __init__(self, output_dir: str, name: str, bio: str, avatar: str, websocket=None, stream_output=None, headers: Optional[Dict] = None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.output_dir = output_dir.strip()
        self.headers = headers or {}

    def generate_layout(self, research_state: dict) -> str:
        """Generates the full markdown content structure from research state."""
        layout_parts = []
        headers = research_state.get("headers", {})

        # Introduction section
        if research_state.get("introduction"):
            #layout_parts.append(f"## {headers.get('introduction', 'Introduction')}")
            layout_parts.append(research_state["introduction"])

        # Main content sections
        for section in research_state.get("main_content", []):
            heading = section.get("heading", "")
            content = section.get("content", "")
            if heading and content:
                layout_parts.append(f"\n## {heading}\n{content}")

                for subsection in section.get("subsections", []):
                    subheading = subsection.get("subheading", "")
                    subcontent = subsection.get("content", "")
                    if subheading and subcontent:
                        layout_parts.append(f"\n### {subheading}\n{subcontent}")

        # Conclusion
        if research_state.get("conclusion"):
            #layout_parts.append(f"\n## {headers.get('conclusion', 'Conclusion')}")
            layout_parts.append(research_state["conclusion"])

        # References
        if research_state.get("sources"):
            layout_parts.append(f"\n## {headers.get('references', 'References')}")
            sources = research_state.get("sources", [])
            if isinstance(sources, list):
                layout_parts.extend(sources)
            elif isinstance(sources, str):
                layout_parts.append(sources)

        return '\n\n'.join(filter(None, layout_parts))

    def generate_frontmatter(self, research_state: dict) -> dict:

        task = research_state.get("task", {})
        """Generates comprehensive frontmatter metadata."""
        headers = research_state.get("headers", {})

        return {
            "title": headers.get("title", research_state.get("title", "Untitled")),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "draft": headers.get("draft", False),
            "tags": headers.get("tags", []),
            "description": headers.get("description", ""),
            "params": {
                "author": task.get("author"),
                "tone": task.get("tone"),
                "guidelines": task.get("guidelines"),
                "avatar": task.get("avatar", ""),
                #"thumbnail": task.get("", ""),
                "bio": task.get("bio", ""),
                "created": datetime.now().isoformat()
            }
        }

    def write_markdown_with_frontmatter(self, layout: str, metadata: dict, filename: str) -> str:
        """Writes markdown content with proper frontmatter."""
        os.makedirs(self.output_dir, exist_ok=True)

        # Ensure filename is safe and has .md extension
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_filename.lower().endswith('.md'):
            safe_filename += '.md'

        output_path = os.path.join(self.output_dir, safe_filename)

        try:
            # Create and dump the post with frontmatter
            post = frontmatter.Post(layout, **metadata)
            with open(output_path, "wb") as f:  # Use binary mode for frontmatter.dump
                frontmatter.dump(post, f)

            logger.info(f"Successfully wrote markdown to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to write markdown file: {e}")
            raise

    async def write_report_by_formats(self, layout: str, research_state: dict, publish_formats: dict) -> dict:
        """Handles writing reports in all requested formats."""
        file_paths = {}
        metadata = self.generate_frontmatter(research_state)

        # Generate a safe filename from the title
        base_filename = metadata["title"].lower().replace(" ", "-")
        base_filename = "".join(c for c in base_filename if c.isalnum() or c == '-')

        try:
            if publish_formats.get("md") or publish_formats.get("markdown"):
                md_filename = f"{base_filename}.md"
                md_path = self.write_markdown_with_frontmatter(layout, metadata, md_filename)
                file_paths["md"] = md_path

            if publish_formats.get("pdf"):
                pdf_path = await write_md_to_pdf(layout, self.output_dir, filename=f"{base_filename}.pdf")
                file_paths["pdf"] = pdf_path

            if publish_formats.get("docx"):
                docx_path = await write_md_to_word(layout, self.output_dir, filename=f"{base_filename}.docx")
                file_paths["docx"] = docx_path

            if publish_formats.get("json"):
                json_path = write_to_json(
                    {**research_state, "content": layout, "metadata": metadata},
                    self.output_dir,
                    filename=f"{base_filename}.json"
                )
                file_paths["json"] = json_path

        except Exception as e:
            logger.error(f"Error during report generation: {e}")
            if self.websocket and self.stream_output:
                await self.stream_output("error", "publishing", str(e), self.websocket)

        return file_paths

    async def publish_research_report(self, research_state: dict, publish_formats: dict) -> str:
        """Main method to publish the research report."""
        try:
            layout = self.generate_layout(research_state)
            if not layout.strip():
                raise ValueError("Generated layout is empty")

            written_files = await self.write_report_by_formats(layout, research_state, publish_formats)
            logger.info(f"Successfully published files: {written_files}")

            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "publishing",
                    f"Published files: {', '.join(written_files.keys())}",
                    self.websocket
                )

            return layout
        except Exception as e:
            logger.error(f"Failed to publish research report: {e}")
            if self.websocket and self.stream_output:
                await self.stream_output("error", "publishing", str(e), self.websocket)
            raise

    async def run(self, research_state: dict) -> dict:
        """Entry point for the publisher agent."""
        task = research_state.get("task", {})
        publish_formats = task.get("publish_formats", {"md": True})

        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs", "publishing",
                "Publishing final research report based on retrieved data...",
                self.websocket
            )
        else:
            print_agent_output("Publishing final research report based on retrieved data...", agent="PUBLISHER")

        try:
            final_research_report = await self.publish_research_report(research_state, publish_formats)
            return {
                "report": final_research_report,
                "metadata": self.generate_frontmatter(research_state),
                "success": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
