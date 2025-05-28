SAMPLE_JSON = {
  "metadata": {
    "title": "A catchy, SEO-friendly title (under 60 characters)",
    "author": "Optional author name or organization",
    "description": "A 1-2 sentence meta description (under 160 characters) summarizing key points for SEO.",
    "date": "YYYY-MM-DD",
    "tags": ["primary-tag", "secondary-tag", "tertiary-tag"],
    "word_count": "Optional estimated word count"
  },
  "content": {
    "introduction": {
      "hook": "A compelling opening sentence/question/statistic to grab attention.",
      "context": "Brief background (1-2 sentences) explaining why the topic matters.",
      "thesis": "Clear statement of the article's purpose or main argument."
    },
    "main_content": [
      {
        "heading": "H2 Header: Key Topic or Argument",
        "content": "Markdown-formatted paragraph(s) with **bold key terms**, [hyperlinks](https://example.com), and:\n- Bullet points\n- Numbered steps (if tutorial)\n- Blockquotes for emphasis\n\nAvoid walls of text (max 3-4 sentences per paragraph).",
        "subsections": [
          {
            "subheading": "H3 Subheader: Supporting Detail",
            "content": "Data, examples, or analysis. Use:\n- Tables for comparisons (if applicable)\n- `Code snippets` (for technical guides)\n- Embedded media (e.g., ![image](url))",
          }
        ]
      }
    ],
    "conclusion": {
      "summary": "Concise recap of key points (bullet points or 1-2 sentences).",
      "call_to_action": "Optional question/prompt (e.g., \"What's your take? Comment below!\") or further reading suggestion."
    }
  },
  "references": {
    "sources": [
      {
        "citation": "APA/MLA-style citation (e.g., Author, A. (Year). *Title*. Publisher).",
        "url": "Optional [link](https://example.com)"
      }
    ],
    "additional_resources": [
      {
        "title": "Optional related articles/books",
        "url": "[Link](https://example.com)"
      }
    ]
  }
}

# JSON Schema for validation
JSON_SCHEMA = {
    "type": "object",
    "required": ["metadata", "content"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "author": {"type": "string"},
                "description": {"type": "string"},
                "date": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "word_count": {"type": "string"}
            }
        },
        "content": {
            "type": "object",
            "required": ["introduction", "main_content"],
            "properties": {
                "introduction": {
                    "type": "object",
                    "required": ["hook", "thesis"],
                    "properties": {
                        "hook": {"type": "string"},
                        "context": {"type": "string"},
                        "thesis": {"type": "string"}
                    }
                },
                "main_content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["heading", "content"],
                        "properties": {
                            "heading": {"type": "string"},
                            "content": {"type": "string"},
                            "subsections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["subheading", "content"],
                                    "properties": {
                                        "subheading": {"type": "string"},
                                        "content": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "conclusion": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "call_to_action": {"type": "string"}
                    }
                }
            }
        },
        "references": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["citation"],
                        "properties": {
                            "citation": {"type": "string"},
                            "url": {"type": "string"}
                        }
                    }
                },
                "additional_resources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}

REQUIRED_FRONTMATTER_FIELDS = ["title", "date", "description"]