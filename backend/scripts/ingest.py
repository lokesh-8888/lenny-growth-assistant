#!/usr/bin/env python3
"""
Data Ingestion Pipeline for The Lenny Growth Assistant.

- Clones/downloads transcript archive from ChatPRD/lennys-podcast-transcripts
- Parses frontmatter and markdown body
- Chunks text into ~600-800 token chunks with ~100-token overlap
- Hashing for idempotency and changed-file tracking (--refresh)
- Generates 768-dim embeddings via local Ollama nomic-embed-text
- Upserts into PostgreSQL pgvector chunks table
- Prints execution summary
"""

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
import frontmatter
import httpx
import psycopg2
from psycopg2.extras import execute_batch
from tqdm import tqdm

# Ensure scripts directory is in sys.path so chunker can be imported
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chunker import TranscriptMetadata, chunk_transcript, count_tokens

# Load environment variables from .env if present
load_dotenv(REPO_ROOT / ".env")

DEFAULT_REPO_URL = os.getenv(
    "TRANSCRIPT_REPO_URL",
    "https://github.com/ChatPRD/lennys-podcast-transcripts.git",
)
DEFAULT_RAW_PATH = REPO_ROOT / os.getenv("RAW_DATA_PATH", "data/raw/lennys-podcast-transcripts")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lenny_growth",
)


@dataclass
class IngestionSummary:
    files_found: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    parse_errors: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    def print_summary(self):
        duration = self.end_time - self.start_time
        print("\n" + "=" * 60)
        print("           INGESTION PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  Files found:         {self.files_found}")
        print(f"  Files processed:     {self.files_processed}")
        print(f"  Files skipped:       {self.files_skipped}")
        print(f"  Chunks created:      {self.chunks_created}")
        print(f"  Chunks skipped:      {self.chunks_skipped}")
        print(f"  Parse errors:        {self.parse_errors}")
        print(f"  Elapsed time:        {duration:.2f} seconds")
        print("=" * 60 + "\n")


def get_db_connection(db_url: str = DATABASE_URL):
    """Establishes connection to PostgreSQL database."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def ensure_raw_transcripts(raw_path: Path, repo_url: str = DEFAULT_REPO_URL) -> Path:
    """
    Ensures raw transcripts directory exists and is populated.
    If absent or empty, clones the transcript repository.
    """
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    # If raw_path already exists and has markdown files, use it
    if raw_path.exists() and any(raw_path.rglob("*.md")):
        print(f"[Ingest] Found existing transcripts in: {raw_path}")
        return raw_path

    print(f"[Ingest] Transcripts not found locally. Cloning from {repo_url}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(raw_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"[Ingest] Successfully cloned transcripts into: {raw_path}")
    except Exception as e:
        print(f"[Ingest] Error cloning repository: {e}", file=sys.stderr)
        raise
    return raw_path


def compute_file_hash(file_path: Path) -> str:
    """Computes SHA-256 hash of a file's raw contents."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_processed_files(conn) -> Dict[str, Tuple[str, int]]:
    """Fetches dictionary of {file_path: (file_hash, chunk_count)} from database."""
    with conn.cursor() as cur:
        cur.execute("SELECT file_path, file_hash, chunk_count FROM processed_files;")
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}


def save_processed_file(conn, file_path: str, file_hash: str, chunk_count: int):
    """Updates or inserts the processed_files record for a file."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO processed_files (file_path, file_hash, chunk_count, processed_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (file_path) DO UPDATE SET
                file_hash = EXCLUDED.file_hash,
                chunk_count = EXCLUDED.chunk_count,
                processed_at = CURRENT_TIMESTAMP;
            """,
            (file_path, file_hash, chunk_count),
        )


def parse_transcript_file(file_path: Path) -> Tuple[TranscriptMetadata, str]:
    """
    Parses YAML frontmatter and body from a transcript markdown file.
    Infuses fallbacks for title, guest, and URL based on filenames/headings.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        post = frontmatter.load(f)

    meta = post.metadata or {}
    body = post.content or ""

    # Determine title
    title = meta.get("title") or meta.get("episode") or meta.get("episode_title")
    if not title:
        # Fallback to first H1 or filename
        for line in body.splitlines():
            if line.strip().startswith("# "):
                title = line.strip().lstrip("# ").strip()
                break
        if not title:
            title = file_path.stem.replace("-", " ").replace("_", " ").title()

    # Determine guest
    guest = meta.get("guest") or meta.get("guests")
    if not guest:
        # Infer from parent folder or filename
        parent_name = file_path.parent.name
        if parent_name and parent_name not in ("raw", "lennys-podcast-transcripts"):
            guest = parent_name.replace("-", " ").replace("_", " ").title()
        else:
            guest = file_path.stem.split("-")[0].replace("_", " ").title()

    # Determine source URL
    url = meta.get("url") or meta.get("source_url") or meta.get("link") or ""
    if not url:
        url = f"https://www.lennyspodcast.com/{file_path.stem}"

    date_val = str(meta.get("date") or meta.get("publish_date") or "")

    metadata = TranscriptMetadata(
        title=str(title).strip(),
        guest=str(guest).strip(),
        source_url=str(url).strip(),
        date=date_val,
    )
    return metadata, body


def get_embedding(
    text: str,
    client: httpx.Client,
    base_url: str = OLLAMA_BASE_URL,
    model: str = EMBEDDING_MODEL,
    max_retries: int = 3,
) -> List[float]:
    """
    Calls Ollama HTTP API to generate embeddings for a chunk of text.
    Retries on transient connection issues.
    """
    endpoint = f"{base_url.rstrip('/')}/api/embeddings"
    payload = {"model": model, "prompt": text}

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.post(endpoint, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if embedding and isinstance(embedding, list):
                return embedding
            raise ValueError(f"No valid embedding array in Ollama response: {data}")
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as err:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to obtain embedding from Ollama after {max_retries} attempts: {err}"
                )
            time.sleep(0.5 * attempt)
    return []


def upsert_chunk(
    conn,
    content: str,
    embedding: List[float],
    episode_title: str,
    guest: str,
    source_url: str,
    content_hash: str,
) -> bool:
    """
    Upserts a chunk into PostgreSQL chunks table.
    Returns True if a new row was inserted, False if conflict occurred.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chunks (
                content, embedding, episode_title, guest, source_url, content_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (content_hash) DO NOTHING
            RETURNING id;
            """,
            (content, embedding, episode_title, guest, source_url, content_hash),
        )
        row = cur.fetchone()
        return row is not None


def run_ingestion(
    raw_path: Optional[Path] = None,
    refresh: bool = False,
    force: bool = False,
    limit: Optional[int] = None,
    batch_commit: bool = True,
) -> IngestionSummary:
    """
    Executes the ingestion pipeline.
    """
    summary = IngestionSummary(start_time=time.time())

    # 1. Acquire raw data
    target_raw_path = raw_path or DEFAULT_RAW_PATH
    actual_path = ensure_raw_transcripts(target_raw_path)

    # 2. Collect markdown transcript files (exclude README, LICENSE, index)
    candidate_files = sorted(actual_path.rglob("*.md"))
    valid_files = [
        f for f in candidate_files
        if f.is_file() and f.name.lower() not in ("readme.md", "license.md", "index.md", "contributing.md")
    ]
    summary.files_found = len(valid_files)

    if limit is not None and limit > 0:
        valid_files = valid_files[:limit]
        print(f"[Ingest] Limiting ingestion to {len(valid_files)} file(s).")

    # 3. Connect to DB and fetch existing processed files
    conn = get_db_connection()
    processed_map = get_processed_files(conn)

    print(f"[Ingest] Found {summary.files_found} files. Beginning processing...")

    with httpx.Client() as http_client:
        for file_path in tqdm(valid_files, desc="Ingesting Transcripts"):
            rel_path = str(file_path.relative_to(actual_path)).replace("\\", "/")
            current_hash = compute_file_hash(file_path)

            # Check if file has changed
            is_processed = rel_path in processed_map
            prev_hash, prev_count = processed_map.get(rel_path, ("", 0))

            if not force and is_processed and (prev_hash == current_hash):
                # Unchanged file
                summary.files_skipped += 1
                summary.chunks_skipped += prev_count
                continue

            # Parse frontmatter and body
            try:
                meta, body = parse_transcript_file(file_path)
            except Exception as e:
                print(f"[Ingest] Parse error in {file_path.name}: {e}", file=sys.stderr)
                summary.parse_errors += 1
                continue

            # Chunk body
            chunks = chunk_transcript(body, metadata=meta)
            if not chunks:
                summary.files_processed += 1
                save_processed_file(conn, rel_path, current_hash, 0)
                conn.commit()
                continue

            file_created = 0
            file_skipped = 0

            for chunk in chunks:
                # Fast check if chunk content_hash exists in chunks
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM chunks WHERE content_hash = %s;", (chunk.content_hash,))
                    if cur.fetchone():
                        file_skipped += 1
                        summary.chunks_skipped += 1
                        continue

                # Generate embedding
                try:
                    embedding = get_embedding(
                        chunk.content,
                        client=http_client,
                        base_url=OLLAMA_BASE_URL,
                        model=EMBEDDING_MODEL,
                    )
                except Exception as e:
                    print(f"[Ingest] Embedding error for chunk in {file_path.name}: {e}", file=sys.stderr)
                    summary.parse_errors += 1
                    continue

                # Upsert into database
                inserted = upsert_chunk(
                    conn=conn,
                    content=chunk.content,
                    embedding=embedding,
                    episode_title=chunk.episode_title,
                    guest=chunk.guest,
                    source_url=chunk.source_url,
                    content_hash=chunk.content_hash,
                )
                if inserted:
                    file_created += 1
                    summary.chunks_created += 1
                else:
                    file_skipped += 1
                    summary.chunks_skipped += 1

            summary.files_processed += 1
            save_processed_file(conn, rel_path, current_hash, len(chunks))
            conn.commit()

    conn.close()
    summary.end_time = time.time()
    summary.print_summary()
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Lenny's Podcast transcripts into Postgres vector database."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Only process transcripts that are new or whose contents have changed.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-chunking and re-embedding of all files regardless of stored hashes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files to process (useful for quick evaluation/tests).",
    )
    parser.add_argument(
        "--raw-path",
        type=str,
        default=None,
        help="Override path to raw transcript files directory.",
    )

    args = parser.parse_args()
    raw_override = Path(args.raw_path) if args.raw_path else None

    run_ingestion(
        raw_path=raw_override,
        refresh=args.refresh,
        force=args.force,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
