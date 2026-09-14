"""
Prompt engineering templates and context formatting for grounded RAG generation.
"""

from typing import Dict, List, Optional
from app.models import MessageModel
from app.services.rag.types import RetrievedChunk

NOT_COVERED_MESSAGE = (
    "I could not find coverage of this topic in Lenny's podcast transcripts archive. "
    "Please try asking about product strategy, growth loops, activation, pricing, or "
    "interviews with specific guests featured on the podcast."
)

SYSTEM_PROMPT = """You are The Lenny Growth Assistant, a battle-tested product management and growth advisor grounded exclusively in transcripts from Lenny's Podcast.

CRITICAL OPERATING RULES:
1. Groundedness: Base your answer ONLY and STRICTLY on the provided transcript excerpts below.
2. Honest Refusal: If the provided excerpts do not contain sufficient evidence to answer the question, or if the topic is not covered in Lenny's podcast transcripts, respond honestly with:
   "I could not find coverage of this topic in Lenny's podcast transcripts archive."
   Do NOT attempt to invent facts, hallucinate frameworks, or answer from general knowledge outside the excerpts.
3. Citations & Attribution: Whenever citing an insight, metric, or anecdote, explicitly mention the guest's name and the episode context.
4. Structure: Deliver tactical, operator-grade advice. Use clear bullet points and bold headers where appropriate.
"""

GROUNDED_SYSTEM_PROMPT = SYSTEM_PROMPT


def build_strict_refusal_response(query: str = "") -> str:
    """Builds a polite, clear refusal when topic is not in transcripts."""
    if query:
        return (
            f"I couldn't find any discussion on '{query}' in Lenny's podcast transcripts archive. "
            "Please try asking about product strategy, growth loops, activation, pricing, or "
            "interviews with specific guests featured on the podcast."
        )
    return NOT_COVERED_MESSAGE


def format_context_chunks(chunks: List[RetrievedChunk]) -> str:
    """Formats retrieved chunks into delimited numbered excerpts with full attribution."""
    if not chunks:
        return "No relevant transcript excerpts found."

    formatted_sections: List[str] = []
    for idx, chunk in enumerate(chunks, 1):
        header = f"--- Excerpt {idx} | Episode: \"{chunk.episode_title}\" | Guest: {chunk.guest} ---"
        section = f"{header}\n{chunk.content}\n"
        formatted_sections.append(section)

    return "\n\n".join(formatted_sections)


def build_rag_messages(
    user_query: str,
    chunks: List[RetrievedChunk],
    conversation_history: Optional[List[MessageModel]] = None,
) -> List[Dict[str, str]]:
    """
    Assembles system prompt, recent conversational turns, and the current user prompt with context.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Inject conversation history for multi-turn follow-ups
    if conversation_history:
        for msg in conversation_history:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

    # Assemble user turn with retrieved transcript context
    context_text = format_context_chunks(chunks)
    user_prompt = (
        f"TRANSCRIPT CONTEXT:\n{context_text}\n\n"
        f"QUESTION:\n{user_query}\n\n"
        f"Remember: Answer strictly using the transcript excerpts above. "
        f"If not covered in the excerpts, state that it is not covered."
    )

    messages.append({"role": "user", "content": user_prompt})
    return messages
