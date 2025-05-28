from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime


class Introduction(TypedDict):
    hook: str
    context: str
    thesis: str


class Subsection(TypedDict):
    subheading: str
    content: str


class MainContentSection(TypedDict):
    heading: str
    content: str
    subsections: List[Subsection]


class Conclusion(TypedDict):
    summary: str
    call_to_action: str


class Source(TypedDict):
    citation: str
    url: Optional[str]


class AdditionalResource(TypedDict):
    title: str
    url: str


class References(TypedDict):
    sources: List[Source]
    additional_resources: List[AdditionalResource]


class Metadata(TypedDict):
    title: str
    author: Optional[str]
    description: Optional[str]
    date: str
    tags: List[str]
    word_count: Optional[str]
    draft: Optional[bool]


class Content(TypedDict):
    introduction: Introduction
    main_content: List[MainContentSection]
    conclusion: Conclusion


class ResearchState(TypedDict):
    # Required core components
    metadata: Metadata
    content: Content
    references: References

    # Task parameters
    task: Dict[str, Any]

    # Research components
    initial_research: Optional[str]
    research_data: Optional[List[Dict]]
    human_feedback: Optional[str]

    # Intermediate components
    table_of_contents: Optional[str]
    report: Optional[str]

    review: Optional[Dict]  # Added for review feedback
    revision_notes: Optional[str]  # Added for revision tracking
    human_feedback: Optional[str]  # For human-in-the-loop