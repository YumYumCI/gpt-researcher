from typing import TypedDict, List, Annotated, Optional
import operator

class Subsection(TypedDict):
    subheading: str
    content: str


class MainContentSection(TypedDict):
    heading: str
    content: str
    subsections: List[Subsection]


class ResearchState(TypedDict):
    task: dict
    initial_research: str
    sections: List[str]
    research_data: List[dict]
    human_feedback: str
    # Report layout
    title: str
    headers: dict
    date: str
    table_of_contents: str
    introduction: str
    main_content: List[MainContentSection]
    conclusion: str
    sources: List[str]
    report: str
