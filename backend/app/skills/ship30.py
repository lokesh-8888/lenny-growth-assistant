"""
Ship 30 for 30 essay generation skill with programmatic structural and word count validation.
"""

import re
import time
from typing import Any, Dict, List, Optional
from app.config import settings
from app.schemas import StructureValidation
from app.services.llm.router import LLMRouter, get_llm_router
from app.skills.base import BaseSkill

SHIP30_SYSTEM_PROMPT = """You are an elite growth essayist trained in the Ship 30 for 30 writing framework and grounded exclusively in insights from Lenny's Podcast.

Your mission is to transform tactical operator advice and interview transcripts into an authoritative, highly skimmable, viral-grade growth essay of approximately 1,250 words.

MANDATORY SHIP 30/30 EDITORIAL RULES:
1. STRONG OPENING HOOK:
   - Begin immediately with a compelling question, a counter-intuitive observation, or a vivid operator scenario.
   - Do NOT start with throat-clearing like "In this article..." or "Today we will discuss...".
2. CLEAR NARRATIVE ARC:
   - Setup: Define the status quo, the conventional wisdom, and why it fails.
   - Tension / Core Insight: Reveal what top 1% growth leaders and operators do differently.
   - Resolution: Break down actionable implementation playbooks, step-by-step frameworks, and operational guardrails.
3. VISUALLY SKIMMABLE FORMATTING:
   - Use descriptive Markdown headings (## and ###) to structure the essay.
   - Use bullet points (- or *) and numbered steps (1., 2.) for frameworks and tactics.
   - Use selective **bolding** on key phrases, metrics, and mental models so busy executives can skim and extract 80% of value in 60 seconds.
4. ONE CENTRAL RESTATED TAKEAWAY:
   - Conclude with a dedicated section (e.g., '## The One Takeaway' or '## The Core Rule of Thumb') that crystallizes the single most important actionable principle.
5. SOURCE PROVENANCE & CITATIONS:
   - Every key framework, counter-intuitive insight, and anecdote MUST explicitly cite the guest name and podcast episode.
   - Conclude with a '## Sources & References' section listing the episodes cited.
6. TARGET LENGTH:
   - Target length is ~1,250 words. Provide thorough, operator-grade tactical depth, concrete scenarios, and detailed execution steps to fulfill this depth.
"""

REFINEMENT_PROMPT_TEMPLATE = """The following Ship 30 essay needs refinement to meet our strict publishing standards.

CURRENT ISSUES DETECTED:
{issues}

ORIGINAL ESSAY:
{content}

TASK:
Rewrite and expand this essay so that:
1. It reaches the target length of ~1,250 words (currently {word_count} words). Provide comprehensive, deep tactical breakdowns, operational examples, and concrete step-by-step methodologies from the cited operators.
2. It includes clear Markdown headings (##, ###), bullet lists, bold text for visual skimming, and a dedicated '## The One Takeaway' conclusion.
3. Every insight cites the specific guest name and episode.

Produce the full revised essay now in Markdown:"""


class Ship30Skill(BaseSkill):
    """
    Skill module producing Ship 30 for 30 essays grounded in Lenny's Podcast transcripts.
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        target_word_count: Optional[int] = None,
        tolerance: Optional[float] = None,
    ):
        self.router = llm_router or get_llm_router()
        self.target_word_count = (
            target_word_count
            if target_word_count is not None
            else settings.ship30_target_word_count
        )
        self.tolerance = (
            tolerance if tolerance is not None else settings.ship30_word_count_tolerance
        )

    @property
    def name(self) -> str:
        return "ship30"

    @property
    def description(self) -> str:
        return "Generates structured 1,250-word Ship 30 for 30 growth essays with hook, narrative arc, and skimmable formatting."

    def validate(self, content: str) -> StructureValidation:
        """
        Validates word count boundaries and structural Ship 30 components.
        """
        words = re.findall(r"\b\w+\b", content)
        count = len(words)

        min_words = int(self.target_word_count * (1.0 - self.tolerance))
        max_words = int(self.target_word_count * (1.0 + self.tolerance))

        has_headings = bool(re.search(r"^##\s+.+", content, re.MULTILINE))
        has_bullets = bool(re.search(r"^\s*[\*\-]\s+.+", content, re.MULTILINE) or re.search(r"^\s*\d+\.\s+.+", content, re.MULTILINE))
        has_bold = bool(re.search(r"\*\*[^*]+\*\*", content))
        has_takeaway = bool(re.search(r"(##\s*.*takeaway|##\s*.*rule of thumb|##\s*.*bottom line|the one takeaway)", content, re.IGNORECASE))
        has_hook = bool(content.strip() and not content.strip().startswith("In this article") and not content.strip().startswith("Today we"))

        issues: List[str] = []
        if count < min_words:
            issues.append(f"Word count ({count}) is below minimum target of {min_words} words.")
        elif count > max_words:
            issues.append(f"Word count ({count}) exceeds maximum target of {max_words} words.")

        if not has_headings:
            issues.append("Missing Markdown section headings (## Heading).")
        if not has_bullets:
            issues.append("Missing structured bullet points or numbered lists.")
        if not has_bold:
            issues.append("Missing bold highlights (**key concepts**) for rapid skimming.")
        if not has_takeaway:
            issues.append("Missing dedicated takeaway section ('## The One Takeaway').")

        # Score calculation
        checks = [
            min_words <= count <= max_words,
            has_headings,
            has_bullets,
            has_bold,
            has_takeaway,
            has_hook,
        ]
        score = round(sum(1.0 for c in checks if c) / len(checks), 2)
        is_valid = len(issues) == 0

        return StructureValidation(
            is_valid=is_valid,
            word_count=count,
            target_word_count=self.target_word_count,
            has_headings=has_headings,
            has_bullets=has_bullets,
            has_bold=has_bold,
            has_takeaway=has_takeaway,
            score=score,
            issues=issues,
        )

    async def generate(
        self,
        context: str,
        topic: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        auto_refine: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generates a Ship 30 essay grounded in the given transcript context.
        """
        resolved_title = topic or "Tactical Growth Principles from Lenny's Podcast"

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
            f"INSTRUCTION: Write a comprehensive, tactical ~1,250-word Ship 30 for 30 essay based strictly on the provided context. "
            f"Fulfill all 5 editorial pillars: strong opening hook, narrative arc, skimmable headings and bullets with selective **bolding**, "
            f"provenance citations, and '## The One Takeaway'."
        )

        messages = [
            {"role": "system", "content": SHIP30_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # 1. Primary Generation Pass
        llm_resp = await self.router.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=2500,
        )
        content = llm_resp.content.strip()
        served_by = llm_resp.served_by

        # Extract title from content if present in first heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            resolved_title = title_match.group(1).strip()

        # 2. Validation Pass
        validation = self.validate(content)

        # 3. Automated Refinement Pass if severe deficiency and auto_refine is enabled
        if not validation.is_valid and auto_refine and (validation.word_count < int(self.target_word_count * 0.70) or not validation.has_takeaway):
            refinement_prompt = REFINEMENT_PROMPT_TEMPLATE.format(
                issues="\n".join(f"- {i}" for i in validation.issues),
                content=content,
                word_count=validation.word_count,
            )
            refinement_messages = [
                {"role": "system", "content": SHIP30_SYSTEM_PROMPT},
                {"role": "user", "content": refinement_prompt},
            ]
            refined_resp = await self.router.complete(
                messages=refinement_messages,
                temperature=temperature,
                max_tokens=3000,
            )
            if refined_resp.content.strip():
                content = refined_resp.content.strip()
                served_by = refined_resp.served_by
                validation = self.validate(content)
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if title_match:
                    resolved_title = title_match.group(1).strip()

        return {
            "title": resolved_title,
            "content": content,
            "word_count": validation.word_count,
            "validation": validation,
            "citations": citations or [],
            "served_by": served_by,
        }


_ship30_instance: Optional[Ship30Skill] = None


def get_ship30_skill() -> Ship30Skill:
    """Singleton accessor for Ship30Skill."""
    global _ship30_instance
    if _ship30_instance is None:
        _ship30_instance = Ship30Skill()
    return _ship30_instance
