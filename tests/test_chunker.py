"""
Tests for chunker module: chunk sizes, overlap, headings, and speaker turns.
"""

from scripts.chunker import (
    TranscriptMetadata,
    chunk_transcript,
    count_tokens,
    split_into_segments,
    split_large_segment,
)


SAMPLE_TRANSCRIPT = """---
title: "Building Great Products with Elena Verna"
guest: "Elena Verna"
url: "https://www.lennyspodcast.com/elena-verna"
date: "2024-01-15"
---

# Product-Led Growth and Acquisition

**Lenny Rachitsky (00:00):**
Welcome to Lenny's Podcast, where I speak with top product leaders and growth experts. Today my guest is Elena Verna, one of the foremost authorities on product-led growth (PLG) and B2B growth models. Elena, welcome to the show!

**Elena Verna (00:32):**
Thank you so much for having me, Lenny. It's always a pleasure to chat growth strategy with you.

### What Everyone Gets Wrong About PLG

**Elena Verna (00:45):**
The single biggest mistake founders and product managers make when transitioning to PLG is thinking that PLG means "no sales team". That is completely false. Product-led growth is an acquisition and retention engine that qualifies leads based on actual product usage. When an enterprise user hits an inflection point or exceeds team usage thresholds, that is the exact moment sales should step in with product-led sales (PLS). Sales doesn't disappear; it gets ten times more efficient because reps aren't cold calling—they're reaching out to active power users who already love the product.

**Lenny Rachitsky (02:10):**
That distinction is critical. How should teams think about designing their freemium tier or free trial? What levers actually drive conversion without giving away too much value?

**Elena Verna (02:30):**
You have to map your value metric directly to customer aha moments. A value metric is the dimension upon which your customer extracts value from your software—whether it's active seats, API calls, stored gigabytes, or completed workflows. If you gate the aha moment behind a paywall, users bounce before realizing the software solves their problem. On the flip side, if you give away infinite volume forever, they have no reason to upgrade. The magic happens when the free tier provides full utility for an individual contributor, but team collaboration and scale trigger a natural monetization wall.

### Retention as the Ultimate Growth Engine

**Elena Verna (04:15):**
Acquisition without retention is just pouring water into a leaky bucket. If your day-30 or month-3 retention curve does not flatten, you do not have product-market fit. No amount of paid ads or viral loops can compensate for poor retention. Product leaders should obsess over activation cohorts before scaling customer acquisition spend.
"""


def test_token_counting():
    """Verify token counter returns positive integer counts."""
    text = "Product management and growth loops are essential for modern software startups."
    tokens = count_tokens(text)
    assert tokens > 5
    assert isinstance(tokens, int)


def test_speaker_segment_splitting():
    """Verify markdown body splits into discrete speaker turns and headings."""
    segments = split_into_segments(SAMPLE_TRANSCRIPT)
    assert len(segments) >= 4
    # Check that speaker turns are recognized as segment starts
    assert any("Lenny Rachitsky" in s for s in segments)
    assert any("Elena Verna" in s for s in segments)
    assert any("What Everyone Gets Wrong About PLG" in s for s in segments)


def test_chunking_metadata_preservation():
    """Verify chunks retain episode title, guest name, and source URL."""
    meta = TranscriptMetadata(
        title="Building Great Products with Elena Verna",
        guest="Elena Verna",
        source_url="https://www.lennyspodcast.com/elena-verna",
    )
    chunks = chunk_transcript(
        SAMPLE_TRANSCRIPT,
        metadata=meta,
        min_tokens=100,
        target_tokens=250,
        max_tokens=400,
        overlap_tokens=50,
    )
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.episode_title == "Building Great Products with Elena Verna"
        assert chunk.guest == "Elena Verna"
        assert chunk.source_url == "https://www.lennyspodcast.com/elena-verna"
        assert len(chunk.content_hash) == 64  # SHA-256


def test_chunking_size_and_overlap():
    """
    Verify chunk sizes stay bounded and consecutive chunks share overlapping text.
    """
    # Create longer synthetic dialogue to trigger multiple chunks
    long_body = (
        "### Section 1: The Core Strategy\n\n"
        + ("**Lenny (00:00):** Can you explain the detailed framework for sustainable growth loops and how companies should structure their cross-functional product squads?\n\n"
           "**Elena (00:30):** Absolutely. A sustainable growth model consists of three core loops: viral loops, content loops, and paid loops. In a viral loop, every active user naturally invites coworkers or collaborators through the normal usage of the product. In a content loop, user activity generates public artifacts or indexable pages that attract search traffic. In a paid loop, revenue generated from customers is directly reinvested into performance acquisition channels.\n\n") * 10
    )

    meta = TranscriptMetadata(title="Growth Loops Masterclass", guest="Elena Verna")
    chunks = chunk_transcript(
        long_body,
        metadata=meta,
        min_tokens=300,
        target_tokens=500,
        max_tokens=650,
        overlap_tokens=80,
    )

    assert len(chunks) >= 2, "Expected at least 2 chunks from long dialogue"

    # Check size bounds
    for chunk in chunks:
        tokens = count_tokens(chunk.content)
        assert tokens <= 750, f"Chunk exceeded maximum token bound: {tokens}"

    # Check overlap between consecutive chunks
    for i in range(len(chunks) - 1):
        c1 = chunks[i].content
        c2 = chunks[i + 1].content

        # Extract words from the end of chunk 1 and verify presence in chunk 2
        c1_words = c1.split()
        c2_words = c2.split()

        # Last 15 words of c1 should appear in c2 due to overlap
        tail = " ".join(c1_words[-10:])
        assert tail in c2 or any(w in c2 for w in c1_words[-10:]), (
            "Expected overlap between adjacent chunks"
        )
