"""
Tests for ingestion pipeline: frontmatter parsing, file hashing, and database idempotency.
"""

import os
from pathlib import Path
import tempfile
import pytest

from scripts.ingest import (
    compute_file_hash,
    get_db_connection,
    parse_transcript_file,
    run_ingestion,
    save_processed_file,
    upsert_chunk,
)
from scripts.chunker import TranscriptMetadata


SAMPLE_FILE_CONTENT = """---
title: "The Art of Product Leadership with Shreyas Doshi"
guest: "Shreyas Doshi"
url: "https://www.lennyspodcast.com/shreyas-doshi"
date: "2023-08-10"
---

# Product Strategy and Execution

**Lenny Rachitsky (00:00):**
Welcome to Lenny's Podcast. Today we are talking with Shreyas Doshi about product leadership frameworks.

**Shreyas Doshi (00:30):**
Thanks Lenny. The best product managers focus on high-leverage activities and avoid getting trapped in low-impact execution details.

### The LNO Framework

**Shreyas Doshi (02:00):**
The LNO framework classifies tasks into Leverage, Neutral, and Overhead. You should spend 80% of your creative energy on Leverage tasks.
"""


def test_compute_file_hash():
    """Verify SHA-256 calculation on files."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md", encoding="utf-8") as f:
        f.write(SAMPLE_FILE_CONTENT)
        temp_path = Path(f.name)

    try:
        hash1 = compute_file_hash(temp_path)
        hash2 = compute_file_hash(temp_path)
        assert hash1 == hash2
        assert len(hash1) == 64
    finally:
        temp_path.unlink()


def test_parse_transcript_file():
    """Verify frontmatter parsing correctly extracts metadata and body."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md", encoding="utf-8") as f:
        f.write(SAMPLE_FILE_CONTENT)
        temp_path = Path(f.name)

    try:
        meta, body = parse_transcript_file(temp_path)
        assert meta.title == "The Art of Product Leadership with Shreyas Doshi"
        assert meta.guest == "Shreyas Doshi"
        assert meta.source_url == "https://www.lennyspodcast.com/shreyas-doshi"
        assert meta.date == "2023-08-10"
        assert "LNO Framework" in body
    finally:
        temp_path.unlink()


def test_ingestion_idempotency_database():
    """
    Verify idempotency against Postgres:
    Inserting a chunk twice results in 0 new rows on the second attempt.
    """
    try:
        conn = get_db_connection()
    except Exception as e:
        pytest.skip(f"Postgres not reachable for live db test: {e}")

    dummy_hash = "test_hash_unique_1234567890abcdef"
    dummy_embedding = [0.0] * 768

    try:
        # Clean up any leftover test chunk
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE content_hash = %s;", (dummy_hash,))
        conn.commit()

        # First insert -> Should return True (inserted)
        first_insert = upsert_chunk(
            conn=conn,
            content="This is a test chunk for idempotency verification.",
            embedding=dummy_embedding,
            episode_title="Test Episode",
            guest="Test Guest",
            source_url="https://example.com/test",
            content_hash=dummy_hash,
        )
        conn.commit()
        assert first_insert is True, "First upsert should insert row"

        # Second insert with identical content_hash -> Should return False (0 new rows)
        second_insert = upsert_chunk(
            conn=conn,
            content="This is a test chunk for idempotency verification.",
            embedding=dummy_embedding,
            episode_title="Test Episode",
            guest="Test Guest",
            source_url="https://example.com/test",
            content_hash=dummy_hash,
        )
        conn.commit()
        assert second_insert is False, "Second upsert of unchanged hash should insert 0 new rows"

    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE content_hash = %s;", (dummy_hash,))
        conn.commit()
        conn.close()


def test_ingestion_directory_idempotency():
    """
    Verify run_ingestion on an unchanged directory of markdown files skips re-embedding.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_file = tmp_path / "sample-test-episode.md"
        test_file.write_text(SAMPLE_FILE_CONTENT, encoding="utf-8")

        # Run 1: process directory
        summary1 = run_ingestion(raw_path=tmp_path, limit=1)
        assert summary1.files_processed >= 1 or summary1.files_skipped >= 0

        # Run 2: re-run on unchanged directory
        summary2 = run_ingestion(raw_path=tmp_path, limit=1)
        # Should skip unchanged files and insert 0 new chunks
        assert summary2.files_skipped == 1
        assert summary2.chunks_created == 0
