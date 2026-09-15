"""
Transcript Chunker module for The Lenny Growth Assistant.

Splits podcast transcripts by headings and speaker-turns into ~600-800 token
chunks with ~100-token overlap between adjacent chunks.
Captures and preserves timestamps (e.g. [14:32], (00:01:27), **Lenny (04:15):**)
and speaker metadata for each chunk.
"""

from collections import Counter
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
    timestamp: str = ""
    speaker: str = ""


@dataclass
class Segment:
    text: str
    speaker: str = ""
    timestamp: str = ""


# Regular expressions for turn headers and timestamps
# Matches:
# 1. "Brian Chesky (00:00:00):" or "**Lenny (04:15):**"
P1_NAME_PAREN_TS = re.compile(
    r"^\*{0,2}(?P<speaker>[A-Za-z0-9\s\.\-—']+?)\s*\((?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})\)\*{0,2}:",
    re.IGNORECASE,
)
# 2. "(00:01:27):" or "(04:15):" (continuation timestamp turn)
P2_PAREN_TS_ONLY = re.compile(
    r"^\s*\((?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})\):",
)
# 3. "[12:30] Guest Name:" or "[01:04:12] Lenny:"
P3_BRACKET_TS_NAME = re.compile(
    r"^\s*\[(?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})\]\s*\*{0,2}(?P<speaker>[A-Za-z0-9\s\.\-—']+?)\*{0,2}:",
    re.IGNORECASE,
)
# 4. "Guest Name [12:30]:"
P4_NAME_BRACKET_TS = re.compile(
    r"^\*{0,2}(?P<speaker>[A-Za-z0-9\s\.\-—']+?)\*{0,2}\s*\[(?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})\]:",
    re.IGNORECASE,
)
# 5. "**Lenny:**" or "Brian Chesky:" (speaker turn without timestamp)
P5_NAME_COLON = re.compile(
    r"^\*{0,2}(?P<speaker>[A-Z][A-Za-z0-9\s\.\-—']+?)\*{0,2}:",
)
# 6. Standalone timestamp on a line: "[14:25]" or "(00:01:27)"
P6_STANDALONE_TS = re.compile(
    r"^\s*[\[\(](?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})[\]\)]\s*$",
)


def parse_turn_header(line: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """
    Inspects a stripped line to detect if it is a speaker turn header or timestamp.
    Returns (speaker, timestamp) where either may be None, or None if not a turn header.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Exclude common markdown links and non-speaker colons
    if stripped.startswith("http:") or stripped.startswith("https:") or stripped.startswith(">"):
        return None

    m = P1_NAME_PAREN_TS.match(stripped)
    if m:
        spk = m.group("speaker").strip().strip("*").strip()
        ts = m.group("timestamp").strip()
        return (spk, ts)

    m = P2_PAREN_TS_ONLY.match(stripped)
    if m:
        ts = m.group("timestamp").strip()
        return (None, ts)

    m = P3_BRACKET_TS_NAME.match(stripped)
    if m:
        ts = m.group("timestamp").strip()
        spk = m.group("speaker").strip().strip("*").strip()
        return (spk, ts)

    m = P4_NAME_BRACKET_TS.match(stripped)
    if m:
        spk = m.group("speaker").strip().strip("*").strip()
        ts = m.group("timestamp").strip()
        return (spk, ts)

    m = P6_STANDALONE_TS.match(stripped)
    if m:
        ts = m.group("timestamp").strip()
        return (None, ts)

    m = P5_NAME_COLON.match(stripped)
    if m:
        candidate_speaker = m.group("speaker").strip().strip("*").strip()
        lower = candidate_speaker.lower()
        if lower not in ("note", "warning", "tip", "caution", "step", "summary", "takeaway", "key takeaways"):
            return (candidate_speaker, None)

    return None


def split_into_segments(body: str, initial_speaker: str = "", initial_timestamp: str = "00:00") -> List[Segment]:
    """
    Split a transcript markdown body into atomic segments based on headings
    and speaker turns, tagging each segment with active speaker and timestamp.
    """
    lines = body.strip().splitlines()
    segments: List[Segment] = []
    current_lines: List[str] = []

    active_speaker = initial_speaker
    active_timestamp = initial_timestamp

    seg_speaker = active_speaker
    seg_timestamp = active_timestamp

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        turn_info = parse_turn_header(stripped)
        is_heading = stripped.startswith("#")

        if turn_info is not None or is_heading:
            # Finalize previous segment
            if current_lines:
                seg_text = "\n".join(current_lines).strip()
                if seg_text:
                    segments.append(
                        Segment(
                            text=seg_text,
                            speaker=seg_speaker,
                            timestamp=seg_timestamp,
                        )
                    )
                current_lines = []

            # Update speaker and timestamp state if a turn header was found
            if turn_info is not None:
                new_speaker, new_ts = turn_info
                if new_speaker:
                    active_speaker = new_speaker
                if new_ts:
                    active_timestamp = new_ts
                seg_speaker = active_speaker
                seg_timestamp = active_timestamp
            elif is_heading:
                # Retain active speaker / timestamp for heading segment
                seg_speaker = active_speaker
                seg_timestamp = active_timestamp

            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        seg_text = "\n".join(current_lines).strip()
        if seg_text:
            segments.append(
                Segment(
                    text=seg_text,
                    speaker=seg_speaker,
                    timestamp=seg_timestamp,
                )
            )

    # Fallback if no turn boundaries were detected
    if not segments:
        if "\n\n" in body:
            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
            return [
                Segment(text=p, speaker=initial_speaker, timestamp=initial_timestamp)
                for p in paragraphs
            ]
        return [Segment(text=body.strip(), speaker=initial_speaker, timestamp=initial_timestamp)]

    return segments


def split_large_segment(segment: Segment, max_tokens: int = 700) -> List[Segment]:
    """Split an oversized segment across sentence boundaries while preserving metadata."""
    tokens = count_tokens(segment.text)
    if tokens <= max_tokens:
        return [segment]

    sentences = re.split(r"(?<=[.?!])\s+", segment.text)
    sub_segments: List[Segment] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = count_tokens(sentence)
        if current_tokens + s_tokens > max_tokens and current_sentences:
            sub_segments.append(
                Segment(
                    text=" ".join(current_sentences),
                    speaker=segment.speaker,
                    timestamp=segment.timestamp,
                )
            )
            current_sentences = [sentence]
            current_tokens = s_tokens
        else:
            current_sentences.append(sentence)
            current_tokens += s_tokens

    if current_sentences:
        sub_segments.append(
            Segment(
                text=" ".join(current_sentences),
                speaker=segment.speaker,
                timestamp=segment.timestamp,
            )
        )

    return sub_segments


def determine_primary_speaker(segments: List[Segment], fallback: str = "Unknown") -> str:
    """Determines the primary speaker for a chunk based on character length."""
    counts = Counter()
    for s in segments:
        if s.speaker:
            counts[s.speaker] += len(s.text)
    if counts:
        return counts.most_common(1)[0][0]
    return fallback


def determine_starting_timestamp(segments: List[Segment], fallback: str = "00:00") -> str:
    """Finds the first non-empty timestamp in the segment sequence."""
    for s in segments:
        if s.timestamp:
            return s.timestamp
    return fallback


def chunk_transcript(
    body: str,
    metadata: Optional[TranscriptMetadata] = None,
    min_tokens: int = 550,
    target_tokens: int = 700,
    max_tokens: int = 850,
    overlap_tokens: int = 100,
) -> List[Chunk]:
    """
    Chunks a transcript into ~600-800 token blocks with ~100-token overlap.
    Preserves speaker turns and headings, and tags each chunk with its starting
    timestamp and primary speaker.
    """
    if metadata is None:
        metadata = TranscriptMetadata()

    initial_spk = metadata.guest if metadata.guest and metadata.guest != "Unknown Guest" else "Lenny"
    raw_segments = split_into_segments(body, initial_speaker=initial_spk, initial_timestamp="00:00")

    # Break down any segments that individually exceed max_tokens
    segments: List[Segment] = []
    for seg in raw_segments:
        segments.extend(split_large_segment(seg, max_tokens=target_tokens))

    if not segments:
        return []

    chunks: List[Chunk] = []
    current_segments: List[Segment] = []
    current_tokens = 0
    chunk_index = 0

    i = 0
    while i < len(segments):
        seg = segments[i]
        seg_tokens = count_tokens(seg.text)

        # If adding this segment would exceed max_tokens and we already have at least min_tokens
        if (current_tokens + seg_tokens > max_tokens) and (current_tokens >= min_tokens):
            # Finalize current chunk
            chunk_text = "\n\n".join(s.text for s in current_segments).strip()
            total_tok = count_tokens(chunk_text)
            c_hash = hashlib.sha256(
                f"{metadata.title}:{chunk_index}:{chunk_text}".encode("utf-8")
            ).hexdigest()

            starting_ts = determine_starting_timestamp(current_segments, fallback="00:00")
            primary_spk = determine_primary_speaker(current_segments, fallback=initial_spk)

            chunks.append(
                Chunk(
                    content=chunk_text,
                    token_count=total_tok,
                    content_hash=c_hash,
                    episode_title=metadata.title,
                    guest=metadata.guest,
                    source_url=metadata.source_url,
                    chunk_index=chunk_index,
                    timestamp=starting_ts,
                    speaker=primary_spk,
                )
            )
            chunk_index += 1

            # Build overlap from the end of current_segments
            overlap_segments: List[Segment] = []
            overlap_count = 0
            for prev_seg in reversed(current_segments):
                p_tok = count_tokens(prev_seg.text)
                if overlap_count + p_tok <= overlap_tokens * 1.5:
                    overlap_segments.insert(0, prev_seg)
                    overlap_count += p_tok
                else:
                    break

            current_segments = list(overlap_segments)
            current_tokens = sum(count_tokens(s.text) for s in current_segments)

        current_segments.append(seg)
        current_tokens += seg_tokens
        i += 1

    # Emit trailing segments as final chunk
    if current_segments:
        chunk_text = "\n\n".join(s.text for s in current_segments).strip()
        total_tok = count_tokens(chunk_text)
        c_hash = hashlib.sha256(
            f"{metadata.title}:{chunk_index}:{chunk_text}".encode("utf-8")
        ).hexdigest()

        starting_ts = determine_starting_timestamp(current_segments, fallback="00:00")
        primary_spk = determine_primary_speaker(current_segments, fallback=initial_spk)

        chunks.append(
            Chunk(
                content=chunk_text,
                token_count=total_tok,
                content_hash=c_hash,
                episode_title=metadata.title,
                guest=metadata.guest,
                source_url=metadata.source_url,
                chunk_index=chunk_index,
                timestamp=starting_ts,
                speaker=primary_spk,
            )
        )

    return chunks
