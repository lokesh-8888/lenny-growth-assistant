-- =============================================================================
-- The Lenny Growth Assistant — Database Initialization & Schema
-- =============================================================================

-- 1. Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Chunks table for vector embeddings and transcript excerpts
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768),
    episode_title TEXT,
    guest TEXT,
    source_url TEXT,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Cosine similarity index for pgvector (HNSW)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON chunks USING hnsw (embedding vector_cosine_ops);

-- 3. Idempotent processed files ledger
CREATE TABLE IF NOT EXISTS processed_files (
    file_path TEXT PRIMARY KEY,
    file_hash VARCHAR(64) NOT NULL,
    chunk_count INT NOT NULL DEFAULT 0,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 5. Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    served_by VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

-- 6. Artifacts table
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INT,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session_id ON artifacts(session_id);
