"""
Unit tests for transcript chunking with timestamp and speaker preservation.
"""

from scripts.chunker import (
    Chunk,
    Segment,
    TranscriptMetadata,
    chunk_transcript,
    count_tokens,
    determine_primary_speaker,
    determine_starting_timestamp,
    parse_turn_header,
    split_into_segments,
)


def test_parse_turn_header_formats():
    """Verify regex extraction of speaker and timestamp across supported formats."""
    # 1. Name with paren timestamp: "Brian Chesky (00:00:00):"
    res1 = parse_turn_header("Brian Chesky (00:00:00):")
    assert res1 == ("Brian Chesky", "00:00:00")

    # 2. Markdown bold with paren timestamp: "**Lenny (04:15):**"
    res2 = parse_turn_header("**Lenny (04:15):**")
    assert res2 == ("Lenny", "04:15")

    # 3. Continuation timestamp only: "(00:01:27):"
    res3 = parse_turn_header("(00:01:27):")
    assert res3 == (None, "00:01:27")

    # 4. Bracket timestamp preceding speaker: "[12:30] Shreyas Doshi:"
    res4 = parse_turn_header("[12:30] Shreyas Doshi:")
    assert res4 == ("Shreyas Doshi", "12:30")

    # 5. Speaker preceding bracket timestamp: "Elena Verna [01:04:12]:"
    res5 = parse_turn_header("Elena Verna [01:04:12]:")
    assert res5 == ("Elena Verna", "01:04:12")

    # 6. Speaker without timestamp: "**Lenny:**" or "Brian Chesky:"
    res6 = parse_turn_header("**Lenny:**")
    assert res6 == ("Lenny", None)

    # 7. Non-speaker line: regular text
    assert parse_turn_header("Just regular narrative text without colons.") is None
    assert parse_turn_header("https://www.lennyspodcast.com") is None


def test_split_into_segments_metadata_inheritance():
    """Verify segments retain speaker turn information and handle continuation turns."""
    body = """# Episode Title

Brian Chesky (00:00:00):
First thought on company leadership and product vision.

(00:01:27):
Second thought continuing from Brian without repeating the name.

Lenny (00:02:15):
Thank you Brian for that context.
"""
    segments = split_into_segments(body, initial_speaker="Lenny")
    assert len(segments) >= 3

    # Segment 1 should be Brian with starting timestamp 00:00:00
    seg1 = [s for s in segments if "First thought" in s.text][0]
    assert seg1.speaker == "Brian Chesky"
    assert seg1.timestamp == "00:00:00"

    # Continuation segment should inherit Brian Chesky with updated timestamp 00:01:27
    seg2 = [s for s in segments if "Second thought" in s.text][0]
    assert seg2.speaker == "Brian Chesky"
    assert seg2.timestamp == "00:01:27"

    # Next turn switches to Lenny at 00:02:15
    seg3 = [s for s in segments if "Thank you Brian" in s.text][0]
    assert seg3.speaker == "Lenny"
    assert seg3.timestamp == "00:02:15"


def test_chunk_transcript_preserves_timestamp_and_speaker():
    """Verify chunks are tagged with starting timestamp and primary speaker."""
    transcript = """Brian Chesky (00:00:00):
Way too many founders apologize for how they want to run the company. They find some midpoint between how they want to run a company and how the people they lead want to run the company. That's a good way to make everyone miserable. Because what everyone really wants is clarity. And what everyone really wants is to be able to row in the same direction really quickly.

Lenny (00:01:01):
Today my guest is Brian Chesky. Brian is the CEO and co-founder of Airbnb. I was very lucky to get to work with Brian for many years, and my sense is if you ask people who they consider the most inspiring tech or business leaders today, Brian would be right near the top of that list.

(00:01:27):
In our conversation, Brian shares an in-depth explanation of what's happening with product management at Airbnb. We also get deep into Brian's new approach of how he runs Airbnb, including shifting away from traditional growth channels like paid growth.
"""
    meta = TranscriptMetadata(
        title="Brian Chesky's New Playbook",
        guest="Brian Chesky",
        source_url="https://www.youtube.com/watch?v=4ef0juAMqoE",
    )

    chunks = chunk_transcript(
        body=transcript,
        metadata=meta,
        min_tokens=20,
        max_tokens=300,
    )

    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert first_chunk.timestamp == "00:00:00"
    assert first_chunk.speaker in ("Brian Chesky", "Lenny")
    assert first_chunk.episode_title == "Brian Chesky's New Playbook"
    assert first_chunk.guest == "Brian Chesky"
    assert first_chunk.source_url == "https://www.youtube.com/watch?v=4ef0juAMqoE"
    assert first_chunk.content_hash is not None
    assert len(first_chunk.content_hash) == 64


def test_chunk_transcript_bracket_format():
    """Verify chunks preserve timestamp and speaker for bracket format [12:30] Guest:"""
    transcript = """**Lenny (04:15):**
Welcome to the podcast. Let's talk about PM frameworks.

[12:30] Shreyas Doshi:
The three levels of product work are execution, strategy, and vision. Most teams over-index on execution while neglecting strategy.
"""
    meta = TranscriptMetadata(
        title="The Art of Product Management",
        guest="Shreyas Doshi",
        source_url="https://www.youtube.com/watch?v=YP_QghPLG-8",
    )

    chunks = chunk_transcript(
        body=transcript,
        metadata=meta,
        min_tokens=10,
        max_tokens=200,
    )

    assert len(chunks) >= 1
    assert chunks[0].timestamp == "04:15"
    assert "**Lenny (04:15):**" in chunks[0].content
    assert "[12:30] Shreyas Doshi:" in chunks[0].content
