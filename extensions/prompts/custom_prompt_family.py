from datetime import datetime, timezone
from typing import List, Dict, Any
from enum import Enum

from gpt_researcher.prompts import PromptFamily
from gpt_researcher.utils.enum import ReportSource, ReportType, Tone


class CustomPromptFamily(PromptFamily):
    """Custom prompt family with specialized blog writer and SEO expert prompts"""

    def __init__(self, config):
        super().__init__(config)
        # Add any custom initialization here

    # --------------------------
    # Blog Writer Prompts
    # --------------------------

    @staticmethod
    def blog_writer_context_prompt() -> str:
        """Context prompt for the blog writer role"""
        return """You are an expert blog writer with 10+ years of experience creating engaging, informative content. 
Your specialties include:
- Crafting compelling narratives that keep readers engaged
- Structuring content for optimal readability
- Adapting tone and style to match the target audience
- Incorporating storytelling techniques
- Using persuasive language without being salesy

Guidelines for your writing:
1. Always start with a hook that grabs attention
2. Use subheadings every 200-300 words
3. Include examples, anecdotes, and case studies
4. Break up content with bullet points and numbered lists
5. End with a strong conclusion and call-to-action
6. Maintain a conversational yet professional tone
7. Optimize for readability (Flesch-Kincaid grade 8-10)
"""

    @staticmethod
    def generate_blog_post_prompt(
            topic: str,
            context: str,
            tone: Tone = Tone.Conversational,
            word_count: int = 1500,
            language: str = "english"
    ) -> str:
        """Generates a comprehensive blog post prompt"""
        return f"""
{BlogPromptFamily.blog_writer_context_prompt()}

TOPIC: {topic}
CONTEXT: {context}

Write a comprehensive blog post that:
- Is approximately {word_count} words
- Uses {tone.value} tone
- Follows best practices for online readability
- Includes at least 3 subheadings
- Contains 1-2 relevant examples or case studies
- Uses markdown formatting (headings, bold, lists)
- Ends with a conclusion and call-to-action

Structure:
# [Catchy Title]

[Engaging introduction with hook]

## [First Subheading]
[Content]

## [Second Subheading] 
[Content]

## [Third Subheading]
[Content]

[Conclusion summarizing key points]
[Call-to-action encouraging engagement]

Write in {language} language.
Current date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}
"""

    # --------------------------
    # SEO Expert Prompts
    # --------------------------

    @staticmethod
    def seo_expert_context_prompt() -> str:
        return """You are an SEO Content Optimization Specialist. Your expertise includes:
    - Natural keyword integration (1-2% density)
    - Semantic keyword variations
    - Heading hierarchy optimization (H2-H4)
    - Featured snippet opportunities
    - Readability enhancements (Flesch-Kincaid 8-10)
    - E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) signals
    - Mobile-first content structuring
    """

    @staticmethod
    def generate_seo_content_prompt(
            topic: str,
            keywords: List[str],
            context: str,
            word_count: int = 2000,
            language: str = "english"
    ) -> str:
        return f"""
    {CustomPromptFamily.seo_expert_context_prompt()}

    PRIMARY KEYWORD: {keywords[0] if keywords else topic}
    SECONDARY KEYWORDS: {keywords[1:] if len(keywords) > 1 else "N/A"}
    RESEARCH CONTEXT: {context}

    Create SEO-optimized content that:

    1. Naturally incorporates keywords without stuffing
    2. Uses semantic variations (e.g., "email marketing" → "campaign emails")
    3. Includes 3-5 H2 headings and 2-3 H3s per H2
    4. Contains at least:
       - 1 bulleted list
       - 1 comparison table
       - 2 internal link placeholders [INTERNAL:relevant_page]
    5. Scores >80 on Yoast SEO content analysis
    6. Targets {word_count} words

    Structure:
    # [Title With Primary Keyword]

    [Introduction with keyword in first paragraph]

    ## [H2: Question Format]
    [Answer with semantic keywords]

    ### [H3: Detailed Aspect]
    [Supporting data]

    ## [H2: Comparison]
    {table}

    [Conclusion with CTA]
    Current date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}
    Language: {language}
    """

    # --------------------------
    # Override Base Methods
    # --------------------------

    @staticmethod
    def generate_report_prompt(
            question: str,
            context: str,
            report_source: str,
            report_format="apa",
            tone=None,
            total_words=1000,
            language="english",
    ) -> str:
        """Override default report prompt to handle blog/SEO cases"""
        if "blog post" in question.lower():
            return CustomPromptFamily.generate_blog_post_prompt(
                topic=question,
                context=context,
                tone=tone or Tone.Conversational,
                word_count=total_words,
                language=language
            )
        elif "seo" in question.lower() or "optimize" in question.lower():
            # Extract keywords from question
            keywords = [word for word in question.split() if word.startswith("#")]
            return CustomPromptFamily.generate_seo_optimized_prompt(
                topic=question,
                keywords=keywords or [question.split()[0]],
                context=context,
                tone=tone or Tone.Professional,
                word_count=total_words,
                language=language
            )

        # Fall back to default for other report types
        return super().generate_report_prompt(
            question,
            context,
            report_source,
            report_format,
            tone,
            total_words,
            language
        )

    @staticmethod
    def auto_agent_instructions():
        """Extend auto agent instructions with blog/SEO roles"""
        base_instructions = super().auto_agent_instructions()
        return f"""{base_instructions}

Additional examples:
task: "write a blog post about sustainable gardening"
response:
{{
    "server": "✍️ Blog Writer Agent",
    "agent_role_prompt": "{CustomPromptFamily.blog_writer_context_prompt()}"
}}

task: "create SEO-optimized content for a digital marketing agency"
response:
{{
    "server": "🔍 SEO Expert Agent", 
    "agent_role_prompt": "{CustomPromptFamily.seo_expert_context_prompt()}"
}}
"""

    # Add any other base method overrides as needed