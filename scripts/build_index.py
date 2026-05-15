#!/usr/bin/env python3
"""
Build LazyGraphRAG retrieval index.

- Chunks corpus into ~400 word passages with 80 word overlap
- Stores chunks in SQLite with FTS5
- Builds BM25 index
- Serializes indices to pickle files
"""

import json
import sqlite3
import pickle
import hashlib
from pathlib import Path
from collections import defaultdict
from rank_bm25 import BM25Okapi
import re

# Paths
CORPUS_PATH = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/After Japhy Corpus/master_corpus/master_corpus_anon.jsonl")
INDEX_DIR = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/AfterJaphy/index")
DB_PATH = INDEX_DIR / "corpus.db"
BM25_PATH = INDEX_DIR / "bm25_index.pkl"
LOOKUP_PATH = INDEX_DIR / "chunks_lookup.pkl"

# Chunking parameters
TARGET_CHUNK_SIZE = 400  # words
OVERLAP_SIZE = 80  # words
MIN_CHUNK_SIZE = 50  # words


def tokenize(text):
    """Simple word tokenization."""
    return re.findall(r'\b\w+\b', text.lower())


def create_chunks(content, record_id, source_name, date):
    """
    Split content into overlapping chunks of ~400 words.
    Yields (chunk_id, record_id, source_name, date, content, word_count) tuples.
    """
    if not content or len(content.strip()) == 0:
        return

    words = tokenize(content)
    if len(words) < MIN_CHUNK_SIZE:
        return

    chunk_num = 0
    pos = 0

    while pos < len(words):
        # Extract chunk of TARGET_CHUNK_SIZE words
        chunk_end = min(pos + TARGET_CHUNK_SIZE, len(words))
        chunk_words = words[pos:chunk_end]

        # Skip if too small (unless it's the last chunk)
        if len(chunk_words) < MIN_CHUNK_SIZE:
            break

        # Reconstruct chunk text (approximate, since we tokenized)
        # For accurate reconstruction, work with original text using character positions
        # For now, use word-based approximation
        chunk_text = ' '.join(chunk_words)

        chunk_id = f"{record_id}_chunk_{chunk_num}"
        word_count = len(chunk_words)

        yield (chunk_id, record_id, source_name, date, chunk_text, word_count)

        # Move position by TARGET_CHUNK_SIZE - OVERLAP_SIZE
        pos += TARGET_CHUNK_SIZE - OVERLAP_SIZE
        chunk_num += 1


def word_count(text):
    """Count words in text."""
    return len(tokenize(text))


def build_index():
    """Main index building process."""
    print(f"Building LazyGraphRAG index...")
    print(f"Target chunk size: {TARGET_CHUNK_SIZE} words")
    print(f"Overlap: {OVERLAP_SIZE} words")
    print(f"Min chunk size: {MIN_CHUNK_SIZE} words")
    print()

    if not CORPUS_PATH.exists():
        print(f"ERROR: Corpus not found at {CORPUS_PATH}")
        return

    if not INDEX_DIR.exists():
        INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize SQLite database
    print("Initializing SQLite database...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Create main table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            record_id TEXT,
            source_name TEXT,
            date TEXT,
            content TEXT,
            word_count INTEGER
        )
    """)

    # Create FTS5 virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS corpus_fts USING fts5(
            content,
            content=chunks,
            content_rowid=rowid
        )
    """)

    conn.commit()

    # Process corpus
    print(f"Processing corpus from {CORPUS_PATH}...")
    chunks_processed = 0
    records_processed = 0
    records_skipped = 0
    skip_reasons = defaultdict(int)
    chunk_sizes = []
    chunks_lookup = {}  # chunk_id -> content
    chunk_texts_for_bm25 = []  # List of chunk texts for BM25

    try:
        with open(CORPUS_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    records_skipped += 1
                    skip_reasons["json_error"] += 1
                    continue

                record_id = record.get("id")
                source_name = record.get("source_name", "unknown")
                date = record.get("date", "")
                content = record.get("content", "")

                if not content:
                    records_skipped += 1
                    skip_reasons["empty_content"] += 1
                    continue

                if word_count(content) < MIN_CHUNK_SIZE:
                    records_skipped += 1
                    skip_reasons["too_short"] += 1
                    continue

                # Create chunks for this record
                chunks_created = 0
                for chunk_id, rec_id, src, dt, chunk_content, wc in create_chunks(
                    content, record_id, source_name, date
                ):
                    # Insert into SQLite
                    cursor.execute(
                        """
                        INSERT INTO chunks (chunk_id, record_id, source_name, date, content, word_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (chunk_id, rec_id, src, dt, chunk_content, wc)
                    )

                    # Insert into FTS5
                    cursor.execute(
                        "INSERT INTO corpus_fts (content, rowid) SELECT content, rowid FROM chunks WHERE chunk_id = ?",
                        (chunk_id,)
                    )

                    # Store for BM25
                    chunks_lookup[chunk_id] = chunk_content
                    chunk_texts_for_bm25.append(chunk_content)
                    chunk_sizes.append(wc)

                    chunks_processed += 1
                    chunks_created += 1

                    if chunks_processed % 10000 == 0:
                        print(f"  Processed {chunks_processed} chunks from {records_processed} records...")
                        conn.commit()

                if chunks_created > 0:
                    records_processed += 1

    except Exception as e:
        print(f"ERROR: {e}")
        return

    conn.commit()
    print()
    print(f"Total records processed: {records_processed:,}")
    print(f"Total records skipped: {records_skipped:,}")
    if skip_reasons:
        print("Skip reasons:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
    print()

    # Build BM25 index
    print("Building BM25 index...")
    tokenized_chunks = [tokenize(text) for text in chunk_texts_for_bm25]
    bm25 = BM25Okapi(tokenized_chunks)
    print(f"✓ BM25 index built over {len(tokenized_chunks):,} chunks")
    print()

    # Serialize indices
    print(f"Serializing indices...")

    # Serialize BM25
    with open(BM25_PATH, 'wb') as f:
        pickle.dump(bm25, f)
    print(f"✓ Serialized BM25 to {BM25_PATH}")

    # Serialize chunks_lookup
    with open(LOOKUP_PATH, 'wb') as f:
        pickle.dump(chunks_lookup, f)
    print(f"✓ Serialized chunks_lookup to {LOOKUP_PATH}")

    # Close database
    conn.close()
    print(f"✓ Closed SQLite database")
    print()

    # Final statistics
    avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
    db_size = DB_PATH.stat().st_size / (1024 * 1024)  # MB
    bm25_size = BM25_PATH.stat().st_size / (1024 * 1024)  # MB
    lookup_size = LOOKUP_PATH.stat().st_size / (1024 * 1024)  # MB

    print("=" * 80)
    print("INDEX BUILD COMPLETE")
    print("=" * 80)
    print(f"Total chunks created: {chunks_processed:,}")
    print(f"Average chunk size: {avg_chunk_size:.0f} words")
    print(f"Min chunk size: {min(chunk_sizes) if chunk_sizes else 0} words")
    print(f"Max chunk size: {max(chunk_sizes) if chunk_sizes else 0} words")
    print()
    print("File sizes:")
    print(f"  {DB_PATH.name:<30} {db_size:>8.1f} MB")
    print(f"  {BM25_PATH.name:<30} {bm25_size:>8.1f} MB")
    print(f"  {LOOKUP_PATH.name:<30} {lookup_size:>8.1f} MB")
    print()
    print(f"Files written to: {INDEX_DIR}")
    print("=" * 80)

    return {
        "chunks_created": chunks_processed,
        "records_processed": records_processed,
        "records_skipped": records_skipped,
        "avg_chunk_size": avg_chunk_size,
        "db_size_mb": db_size,
        "bm25_size_mb": bm25_size,
    }


if __name__ == "__main__":
    build_index()
