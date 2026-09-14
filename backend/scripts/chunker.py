"""
Transcript Chunker module for The Lenny Growth Assistant.

Splits podcast transcripts by headings and speaker-turns into ~600-800 token
chunks with ~100-token overlap between adjacent chunks.
"""

from dataclasses import dataclass
import hashlib
import re
from typing import List, Optional, Tuple

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    _ENCODER = None


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken cl100k_base or a robust fallback."""
    if _TIKTOKEN_AVAILABLE and _ENCODER is not None:
        return len(_ENCODER.encode(text, disallowed_special=()))
    # Fallback heuristic: ~1.3 tokens per whitespace-separated word
    words = text.split()
    return max(1, int(len(words) * 1.33))


@dataclass
class TranscriptMetadata:
    title: str = "Unknown Episode"
    guest: str = "Unknown Guest"
    source_url: str = ""
    date: str = ""


@dataclass
class Chunk:
    content: str
    token_count: int
    content_hash: str
    episode_title: str
    guest: str
    source_url: str
    chunk_index: int


# Regex matching speaker turns (e.g., "**Lenny:**", "Lenny Rachitsky (01:23):", "Lenny (00:00):")
SPEAKER_TURN_PATTERN = re.compile(
    r"^(?:#{1,6}\s+.*|\*{0,2}[A-Za-z0-9\s\.\-—']+(?:\s*\([^)]*\))?\*{0,2}:)",
    re.MULTILINE,
)


def split_into_segments(body: str) -> List[str]:
    """
    Split a transcript markdown body into atomic segments based on headings
    and speaker turns.
    """
    lines = body.strip().splitlines()
    segments: List[str] = []
    current_segment: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_segment:
                current_segment.append("")
            continue

        # Check if line is a heading or speaker turn indicator
        is_boundary = (
            stripped.startswith("#")
            or bool(re.match(r"^\*{0,2}[A-Z][A-Za-z0-9\s\.\-—']*(?:\s*\([^)]+\))?\*{0,2}:", stripped))
        )

        if is_boundary and current_segment:
            seg_text = "\n".join(current_segment).strip()
            if seg_text:
                segments.append(seg_text)
            current_segment = [line]
        else:
            current_segment.append(line)

    if current_segment:
        seg_text = "\n".join(current_segment).strip()
        if seg_text:
            segments.append(seg_text)

    # Fallback: if no boundaries detected, split by double newlines
    if len(segments) <= 1 and "\n\n" in body:
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            return paragraphs

    return segments if segments else [body.strip()]


def split_large_segment(segment: str, max_tokens: int = 700) -> List[str]:
    """Split an oversized segment across sentence boundaries."""
    tokens = count_tokens(segment)
    if tokens <= max_tokens:
        return [segment]

    sentences = re.split(r"(?<=[.?!])\s+", segment)
    sub_segments: List[str] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = count_tokens(sentence)
        if current_tokens + s_tokens > max_tokens and current_sentences:
            sub_segments.append(" ".join(current_sentences))
            current_sentences = [sentence]
            current_tokens = s_tokens
        else:
            current_sentences.append(sentence)
            current_tokens += s_tokens

    if current_sentences:
        sub_segments.append(" ".join(current_sentences))

    return sub_segments


def chunk_transcript(
    body: str,
    metadata: Optional[TranscriptMetadata] = None,
    min_tokens: int = 550,
    target_tokens: int = 700,
    max_tokens: int = 850,
    overlap_tokens: int = 100,
) -> List[Chunk]:
    """
    Chunks a transcript into ~600-800 token chunks with ~100 token overlap.
    Preserves speaker turns and headings.
    """
    if metadata is None:
        metadata = TranscriptMetadata()

    raw_segments = split_into_segments(body)
    # Break down any segments that individually exceed max_tokens
    segments: List[str] = []
    for seg in raw_segments:
        segments.extend(split_large_segment(seg, max_tokens=target_tokens))

    if not segments:
        return []

    chunks: List[Chunk] = []
    current_segments: List[str] = []
    current_tokens = 0
    chunk_index = 0

    i = 0
    while i < len(segments):
        seg = segments[i]
        seg_tokens = count_tokens(seg)

        # If adding this segment would exceed max_tokens and we already have at least min_tokens
        if (current_tokens + seg_tokens > max_tokens) and (current_tokens >= min_tokens):
            # Finalize current chunk
            chunk_text = "\n\n".join(current_segments).strip()
            total_tok = count_tokens(chunk_text)
            c_hash = hashlib.sha256(
                f"{metadata.title}:{chunk_index}:{chunk_text}".encode("utf-8")
            ).hexdigest()

            chunks.append(
                Chunk(
                    content=chunk_text,
                    token_count=total_tok,
                    content_hash=c_hash,
                    episode_title=metadata.title,
                    guest=metadata.guest,
                    source_url=metadata.source_url,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

            # Build overlap from the end of current_segments
            overlap_segments: List[str] = []
            overlap_count = 0
            for prev_seg in reversed(current_segments):
                p_tok = count_tokens(prev_seg)
                if overlap_count + p_tok <= overlap_tokens * 1.5:
                    overlap_segments.insert(0, prev_seg)
                    overlap_count += p_tok
                else:
                    break

            current_segments = list(overlap_segments)
            current_tokens = sum(count_tokens(s) for s in current_segments)

        current_segments.append(seg)
        current_tokens += seg_tokens
        i += 1

    # Emit trailing segments as final chunk
    if current_segments:
        chunk_text = "\n\n".join(current_segments).strip()
        total_tok = count_tokens(chunk_text)
        c_hash = hashlib.sha256(
            f"{metadata.title}:{chunk_index}:{chunk_text}".encode("utf-8")
        ).hexdigest()

        chunks.append(
            Chunk(
                content=chunk_text,
                token_count=total_tok,
                content_hash=c_hash,
                episode_title=metadata.title,
                guest=metadata.guest,
                source_url=metadata.source_url,
                chunk_index=chunk_index,
            )
        )

    return chunks
