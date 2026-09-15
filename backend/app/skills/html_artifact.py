"""
HTML Standalone Artifact generation skill.
Generates self-contained, interactive HTML documents (calculators, teardowns, dashboards)
with mandatory Content Security Policy (CSP) enforcement.
"""

import re
from typing import Any, Dict, List, Optional

from app.services.llm.router import LLMRouter, get_llm_router
from app.schemas import StructureValidation
from app.skills.base import BaseSkill

RESTRICTIVE_CSP_TAG = (
    '<meta http-equiv="Content-Security-Policy" '
    'content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; script-src \'unsafe-inline\';">'
)

HTML_ARTIFACT_SYSTEM_PROMPT = """You are an elite Frontend Web Designer and Growth Engineer.
Your task is to generate a complete, self-contained, and interactive single-page HTML artifact
based on podcast transcript context from Lenny's Podcast.

Examples of artifacts you can generate:
- Interactive Growth Calculators (e.g., CAC/LTV, payback period, referral loop modelers).
- Visual Strategy Dashboards or Framework Cards.
- Interactive Self-Assessment Audits or Maturity Grids.

Design & Architectural Requirements:
1. Completely Self-Contained:
   - ALL CSS must be inline inside `<style>...</style>`.
   - ALL JavaScript must be inline inside `<script>...</script>`.
   - NO external dependencies (NO external CDNs, NO external fonts or script tags). External resources will be strictly blocked by the browser CSP sandbox.
2. Premium Visual Aesthetics:
   - Dark theme or modern high-contrast sleek styling (e.g., #0f172a background, #1e293b cards, #38bdf8 accents).
   - System typography (-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif).
   - Polished buttons, range sliders, cards with subtle borders and shadows.
3. Interactive Functionality:
   - Include interactive inputs (e.g., sliders, number inputs, tab switchers) and dynamic output recalculations using vanilla JavaScript.
4. Security & Structure:
   - Produce a valid, complete HTML5 document starting with `<!DOCTYPE html>`.
   - Include `<head>` with the mandatory Content Security Policy meta tag:
     <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">
   - Output ONLY the raw HTML document without markdown fences (no ```html ... ```).
"""


def ensure_csp_in_html(html: str) -> str:
    """
    Ensures that the mandatory restrictive Content Security Policy meta tag
    is injected into the <head> of the HTML document.
    """
    cleaned = html.strip()
    # Strip markdown code blocks if the LLM wrapped it
    if cleaned.startswith("```html"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Check if CSP meta tag already exists
    csp_pattern = re.compile(r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*>', re.IGNORECASE)
    if csp_pattern.search(cleaned):
        # Already has CSP
        return cleaned

    # Inject into <head>
    if re.search(r"<head\b[^>]*>", cleaned, re.IGNORECASE):
        cleaned = re.sub(
            r"(<head\b[^>]*>)",
            r"\1\n    " + RESTRICTIVE_CSP_TAG,
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )
    elif re.search(r"<html\b[^>]*>", cleaned, re.IGNORECASE):
        cleaned = re.sub(
            r"(<html\b[^>]*>)",
            r"\1\n<head>\n    " + RESTRICTIVE_CSP_TAG + "\n</head>",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        # Wrap with bare HTML skeleton if completely missing
        cleaned = (
            f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    "
            f"{RESTRICTIVE_CSP_TAG}\n    <title>Growth Artifact</title>\n</head>\n<body>\n{cleaned}\n</body>\n</html>"
        )

    return cleaned


class HtmlArtifactSkill(BaseSkill):
    """
    Skill module generating standalone, interactive HTML artifacts with mandatory CSP enforcement.
    """

    def __init__(self, router: Optional[LLMRouter] = None):
        self.router = router or get_llm_router()

    @property
    def name(self) -> str:
        return "html"

    @property
    def description(self) -> str:
        return "Generates complete, self-contained interactive HTML documents with enforced CSP."

    def validate(self, content: str) -> StructureValidation:
        """
        Programmatically evaluates HTML validity, CSP injection, and styling.
        """
        words = re.findall(r"\b\w+\b", content)
        count = len(words)

        has_html_root = bool(re.search(r"<!DOCTYPE\s+html|<html", content, re.IGNORECASE))
        has_head = bool(re.search(r"<head\b[^>]*>", content, re.IGNORECASE))
        has_body = bool(re.search(r"<body\b[^>]*>", content, re.IGNORECASE))
        has_style = bool(re.search(r"<style\b[^>]*>", content, re.IGNORECASE))
        has_csp = bool(re.search(r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\']', content, re.IGNORECASE))
        has_script = bool(re.search(r"<script\b[^>]*>", content, re.IGNORECASE))

        issues: List[str] = []
        if not has_html_root:
            issues.append("Missing <!DOCTYPE html> or <html> root tag.")
        if not has_csp:
            issues.append("Missing mandatory Content-Security-Policy meta tag in <head>.")
        if not has_style:
            issues.append("Missing inline CSS styling (<style>...</style>).")

        checks = [has_html_root, has_head, has_body, has_csp, has_style]
        score = round(sum(1.0 for c in checks if c) / len(checks), 2)
        is_valid = len(issues) == 0

        return StructureValidation(
            is_valid=is_valid,
            word_count=count,
            target_word_count=count,
            has_hook=has_html_root,
            has_headings=has_head,
            has_bullets=has_body,
            has_bold=has_style,
            has_takeaway=has_csp,
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
        Generates a standalone interactive HTML artifact with CSP enforcement.
        """
        resolved_title = topic or "Interactive Growth Framework"
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
            f"INSTRUCTION: Create a complete, self-contained interactive HTML document based on this context. "
            f"Include modern embedded CSS, interactive inputs/widgets with vanilla JavaScript, and the mandatory CSP meta tag. "
            f"Output ONLY the complete HTML5 document."
        )

        messages = [
            {"role": "system", "content": HTML_ARTIFACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        llm_resp = await self.router.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=2500,
            model=chosen_model,
        )
        raw_content = llm_resp.content.strip()

        # Enforce CSP injection
        content = ensure_csp_in_html(raw_content)

        # Extract title from <title> tag if present
        title_match = re.search(r"<title>([^<]+)</title>", content, re.IGNORECASE)
        if title_match and title_match.group(1).strip():
            candidate_title = title_match.group(1).strip()
            if candidate_title.lower() != "growth artifact" and candidate_title.lower() != "untitled":
                resolved_title = candidate_title

        validation = self.validate(content)

        return {
            "title": resolved_title,
            "content": content,
            "word_count": validation.word_count,
            "validation": validation,
            "citations": citations or [],
            "served_by": llm_resp.served_by,
        }


_html_instance: Optional[HtmlArtifactSkill] = None


def get_html_skill() -> HtmlArtifactSkill:
    """Singleton accessor for HtmlArtifactSkill."""
    global _html_instance
    if _html_instance is None:
        _html_instance = HtmlArtifactSkill()
    return _html_instance
