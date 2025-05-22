import aiofiles
import urllib
import uuid
import mistune
import os
import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def write_to_file(filename: str, text: str) -> None:
    """Asynchronously write text to a file in UTF-8 encoding."""
    text_utf8 = text.encode('utf-8', errors='replace').decode('utf-8')
    try:
        async with aiofiles.open(filename, "w", encoding='utf-8') as file:
            await file.write(text_utf8)
        logger.info(f"Text written to file: {filename}")
    except Exception as e:
        logger.error(f"Failed to write to {filename}: {e}")


async def write_text_to_md(text: str, path: str) -> str:
    """Writes text to a Markdown file and returns its path."""
    task_id = uuid.uuid4().hex
    file_path = os.path.join(path, f"{task_id}.md")
    await write_to_file(file_path, text)
    return file_path


async def write_md_to_pdf(text: str, path: str) -> str:
    """Converts Markdown text to PDF and returns encoded file path."""
    task_id = uuid.uuid4().hex
    file_path = os.path.join(path, f"{task_id}.pdf")

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        css_path = os.path.join(current_dir, "pdf_styles.css")

        from md2pdf.core import md2pdf
        md2pdf(file_path, md_content=text, css_file_path=css_path, base_url=None)
        logger.info(f"PDF created at {file_path}")
    except Exception as e:
        logger.error(f"Error converting Markdown to PDF: {e}")
        return ""

    return file_path


async def write_md_to_word(text: str, path: str) -> str:
    """Converts Markdown to DOCX and returns encoded file path."""
    task_id = uuid.uuid4().hex
    file_path = os.path.join(path, f"{task_id}.docx")

    try:
        from htmldocx import HtmlToDocx
        from docx import Document

        html = mistune.html(text)
        doc = Document()
        HtmlToDocx().add_html_to_document(html, doc)
        doc.save(file_path)
        logger.info(f"DOCX created at {file_path}")
    except Exception as e:
        logger.error(f"Error converting Markdown to DOCX: {e}")
        return ""

    return file_path

def write_to_json(research_state: dict, output_dir: str, filename: str = "report.json") -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(research_state, f, indent=2, ensure_ascii=False)

    return output_path