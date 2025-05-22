from backend.report_type.detailed_report import detailed_report
from multi_agents.agent import ChiefEditorAgent
from typing import Dict, Any


class BlogReport(ChiefEditorAgent):
    """Custom report format with modified layout structure"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def generate_report(self, research_state: Dict[str, Any]) -> str:
        """Generate a report with custom layout"""

        # Customize this structure as needed
        report_structure = {
            "title": research_state.get("title", "Untitled Report"),
            "date": "Creation Date",  # Changed from "Date"
            "summary": "Executive Summary",  # New section
            "introduction": "Overview",  # Changed from "Introduction"
            "key_findings": "Main Discoveries",  # New section
            "table_of_contents": "Document Structure",  # Changed from "Table of Contents"
            "detailed_analysis": "In-Depth Examination",  # New section
            "conclusion": "Final Thoughts",  # Changed from "Conclusion"
            "recommendations": "Suggested Actions",  # New section
            "references": "Sources Cited"  # Changed from "References"
        }

        # Generate content for each section
        report_content = {}
        for section, heading in report_structure.items():
            if section in research_state:
                report_content[section] = research_state[section]
            else:
                # Generate content for the section using LLM
                report_content[section] = await self._generate_section_content(
                    section_name=heading,
                    research_state=research_state
                )

        # Format the final report (you can customize this formatting)
        formatted_report = self._format_report(report_content, report_structure)
        return formatted_report

    def _format_report(self, content: Dict[str, str], structure: Dict[str, str]) -> str:
        """Format the report content into the desired output format"""
        report_lines = []

        # Add title and date first
        report_lines.append(f"# {content.get('title', '')}\n")
        report_lines.append(f"**{structure['date']}**: {content.get('date', '')}\n")

        # Add other sections
        for section, heading in structure.items():
            if section not in ['title', 'date'] and content.get(section):
                report_lines.append(f"## {heading}\n")
                report_lines.append(f"{content[section]}\n")

        return "\n".join(report_lines)

    async def _generate_section_content(self, section_name: str, research_state: Dict[str, Any]) -> str:
        """Generate content for a specific section using LLM"""
        prompt = f"""Generate detailed content for the '{section_name}' section of a research report.
        Base this on the following research: {research_state.get('research_data', '')}
        The content should be comprehensive and well-structured."""

        return await self.llm.aresearch(
            query=prompt,
            context=research_state.get("context", "")
        )