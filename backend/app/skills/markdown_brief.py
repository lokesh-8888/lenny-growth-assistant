"""
Markdown Executive Brief & Checklist generation skill.
Generates structured strategic playbooks, teardowns, and actionable checklists.
"""

import re
from typing import Any, Dict, List, Optional

from app.services.llm.router import LLMRouter, get_llm_router
from app.schemas import StructureValidation
from app.skills.base import BaseSkill

MARKDOWN_BRIEF_SYSTEM_PROMPT = """You are an elite VP of Growth and Product Strategist.
Your mission is to synthesize podcast transcript context from Lenny's Podcast into a high-impact,
executive-ready Markdown Brief, Strategic Teardown, or Tactical Checklist.

Editorial Standards:
1. Executive Summary: Start with a concise, punchy 2-3 sentence overview of the core operational insight.
2. Strategic Framework / Pillars: Break down the core methodology into clear, named pillars using `##` and `###` headers.
3. Tactical Implementation Checklist: Provide a concrete, numbered or bulleted list of immediate operational steps.
4. Key Metrics & KPIs: Highlight the quantifiable metrics that matter most.
5. Grounded Provenance: Attribute key assertions directly to the guests and episodes cited in the context.

Formatting Requirements:
- Use clean GitHub-flavored Markdown.
- Use `##` for major sections and `###` for sub-components.
- Use selective bolding (**key concepts**) to make the brief rapidly skimmable.
- Do not include conversational filler ("Sure, here is your brief", "I hope this helps"). Start directly with the title and executive summary.
"""


class MarkdownBriefSkill(BaseSkill):
    """
    Skill module generating executive briefs, playbooks, and checklists in Markdown.
    """

    def __init__(self, router: Optional[LLMRouter] = None, target_word_count: int = 750):
        self.router = router or get_llm_router()
        self.target_word_count = target_word_count

    @property
    def name(self) -> str:
        return "markdown"

    @property
    def description(self) -> str:
        return "Generates structured executive playbooks, teardowns, and tactical checklists in clean Markdown."

    def validate(self, content: str) -> StructureValidation:
        """
        Validates Markdown structure: headings, bullets, bolding, and summary.
        """
        words = re.findall(r"\b\w+\b", content)
        count = len(words)

        has_headings = bool(re.search(r"^##\s+.+", content, re.MULTILINE))
        has_bullets = bool(re.search(r"^\s*[\*\-]\s+.+", content, re.MULTILINE) or re.search(r"^\s*\d+\.\s+.+", content, re.MULTILINE))
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", content))
        has_summary = bool(re.search(r"(##\s*.*executive summary|##\s*.*summary|##\s*.*overview)", content, re.IGNORECASE))
        has_next_steps = bool(re.search(r"(##\s*.*checklist|##\s*.*implementation|##\s*.*action|##\s*.*next steps|##\s*.*metrics)", content, re.IGNORECASE))

        issues: List[str] = []
        if count < 100:
            issues.append(f"Word count ({count}) is too brief for an executive brief.")
        if not has_headings:
            issues.append("Missing Markdown section headings (## Heading).")
        if not has_bullets:
            issues.append("Missing structured bullet points or numbered checklists.")
        if not has_bold:
            issues.append("Missing bold highlights (**key concepts**) for rapid skimming.")

        checks = [count >= 100, has_headings, has_bullets, has_bold, has_summary or has_next_steps]
        score = round(sum(1.0 for c in checks if c) / len(checks), 2)
        is_valid = len(issues) == 0

        return StructureValidation(
            is_valid=is_valid,
            word_count=count,
            target_word_count=self.target_word_count,
            has_hook=has_summary,
            has_headings=has_headings,
            has_bullets=has_bullets,
            has_bold=has_bold,
            has_takeaway=has_next_steps,
            score=score,
            issues=issues,
        )

    async def generate(
        self,
        context: str,
        topic: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generates a structured Markdown brief grounded in the podcast context.
        """
        resolved_title = topic or "Executive Growth Brief"
        chosen_model = model or kwargs.get("model")

        citations_str = ""
        if citations:
            citations_str = "\nPROVENANCE CITATIONS:\n" + "\n".join(
                f"- Episode: {c.get('episode_title', 'Unknown')} | Guest: {c.get('guest', 'Unknown')} | URL: {c.get('source_url', '')}"
                for c in citations
            )

        user_prompt = (
            f"TOPIC / TITLE: {resolved_title}\n\n"
            f"GROUNDED PODCAST CONTEXT:\n{context}\n"
            f"{citations_str}\n\n"
            f"INSTRUCTION: Write an authoritative, executive-ready Markdown growth brief based strictly on the provided context. "
            f"Format with structured Markdown headings, executive summary, bullet points, checklists, bolding, and citations."
        )

        messages = [
            {"role": "system", "content": MARKDOWN_BRIEF_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        llm_resp = await self.router.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
            model=chosen_model,
        )
        content = llm_resp.content.strip()

        # Extract title if present in first heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            resolved_title = title_match.group(1).strip()

        validation = self.validate(content)

        return {
            "title": resolved_title,
            "content": content,
            "word_count": validation.word_count,
            "validation": validation,
            "citations": citations or [],
            "served_by": llm_resp.served_by,
        }


_markdown_instance: Optional[MarkdownBriefSkill] = None


def get_markdown_skill() -> MarkdownBriefSkill:
    """Singleton accessor for MarkdownBriefSkill."""
    global _markdown_instance
    if _markdown_instance is None:
        _markdown_instance = MarkdownBriefSkill()
    return _markdown_instance
