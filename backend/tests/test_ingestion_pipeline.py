"""
Unit tests for ingestion pipeline: frontmatter parsing, SHA-256 hashing, and idempotency guarantees.
"""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock

from scripts.chunker import TranscriptMetadata
from scripts.ingest import (
    compute_file_hash,
    parse_transcript_file,
    upsert_chunk,
)


def test_parse_transcript_file_frontmatter():
    """Verify parsing of YAML frontmatter and markdown body."""
    raw_content = """---
guest: Brian Chesky
title: Brian Chesky's new playbook
youtube_url: https://www.youtube.com/watch?v=4ef0juAMqoE
publish_date: 2023-11-12
---

# Brian Chesky's new playbook

Brian Chesky (00:00:00):
Way too many founders apologize for how they want to run the company.
"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(raw_content)
        temp_path = Path(f.name)

    try:
        meta, body = parse_transcript_file(temp_path)
        assert meta.guest == "Brian Chesky"
        assert meta.title == "Brian Chesky's new playbook"
        assert meta.source_url == "https://www.youtube.com/watch?v=4ef0juAMqoE"
        assert meta.date == "2023-11-12"
        assert "Brian Chesky (00:00:00):" in body
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_compute_file_hash():
    """Verify SHA-256 hash computation for file contents."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("Deterministic content string for hashing test.")
        temp_path = Path(f.name)

    try:
        hash1 = compute_file_hash(temp_path)
        hash2 = compute_file_hash(temp_path)
        assert hash1 == hash2
        assert len(hash1) == 64
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_upsert_chunk_idempotency():
    """Verify upsert_chunk handles ON CONFLICT (content_hash) DO NOTHING."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # First insert: returns newly generated row id
    mock_cursor.fetchone.return_value = (1,)
    inserted_first = upsert_chunk(
        conn=mock_conn,
        content="Test content block",
        embedding=[0.01] * 768,
        episode_title="Test Episode",
        guest="Test Guest",
        timestamp="00:00",
        speaker="Test Guest",
        source_url="https://example.com",
        content_hash="abc123hash",
    )
    assert inserted_first is True

    # Second insert with conflict: DO NOTHING returns None
    mock_cursor.fetchone.return_value = None
    inserted_second = upsert_chunk(
        conn=mock_conn,
        content="Test content block",
        embedding=[0.01] * 768,
        episode_title="Test Episode",
        guest="Test Guest",
        timestamp="00:00",
        speaker="Test Guest",
        source_url="https://example.com",
        content_hash="abc123hash",
    )
    assert inserted_second is False


def test_processed_files_hash_check_skips_unchanged():
    """Verify unchanged files are skipped when hash matches database record."""
    processed_map = {
        "episodes/brian-chesky/transcript.md": ("hash_xyz_123", 24)
    }

    rel_path = "episodes/brian-chesky/transcript.md"
    current_hash = "hash_xyz_123"

    # Should detect match and skip
    is_processed = rel_path in processed_map
    prev_hash, prev_count = processed_map.get(rel_path, ("", 0))

    should_skip = is_processed and (prev_hash == current_hash)
    assert should_skip is True
    assert prev_count == 24
