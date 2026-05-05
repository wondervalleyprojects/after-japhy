#!/usr/bin/env python3

import json
import re
import uuid
from collections import defaultdict
from datetime import datetime

TOKENS_PER_WORD = 1.3

def estimate_tokens(text):
    """Estimate token count as word_count * 1.3."""
    word_count = len(text.split())
    return int(word_count * TOKENS_PER_WORD)

def split_sentences(text):
    """Split text into sentences, handling common cases."""
    # Add spaces after sentence-ending punctuation
    text = re.sub(r'([.!?])\s+', r'\1 ', text)
    # Split on periods, question marks, and exclamation marks
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_text(text, min_tokens=300, max_tokens=800):
    """Chunk text at sentence boundaries into passages of specified token size."""
    if estimate_tokens(text) < min_tokens:
        # Keep as single chunk
        return [text]

    sentences = split_sentences(text)
    if not sentences:
        return [text] if text else []

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)

        if current_tokens + sentence_tokens <= max_tokens:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_tokens = sentence_tokens

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def group_twitter_instagram(records):
    """Group consecutive records sharing the same date into windows."""
    records = sorted(records, key=lambda r: (r.get('source_name'), r.get('date') or ''))

    grouped = []
    temp_group = []
    last_date = None
    last_source = None
    current_tokens = 0

    for record in records:
        source = record.get('source_name')
        if source not in ['twitter', 'instagram']:
            grouped.append(record)
            continue

        date = record.get('date')

        # If same source and date, accumulate
        if source == last_source and date == last_date:
            content_tokens = estimate_tokens(record.get('content', ''))
            if current_tokens + content_tokens <= 600:
                temp_group.append(record)
                current_tokens += content_tokens
                continue
            else:
                # Flush group
                if temp_group:
                    # Merge content
                    merged = {
                        'id': temp_group[0]['id'],
                        'source_name': source,
                        'date': date,
                        'content': ' '.join([r.get('content', '') for r in temp_group]),
                        'url': temp_group[0].get('url'),
                        'word_count': sum([r.get('word_count', 0) for r in temp_group]),
                        'time_period': temp_group[0].get('time_period'),
                        'content_anonymized': temp_group[0].get('content_anonymized'),
                        'metadata': temp_group[0].get('metadata', {})
                    }
                    grouped.append(merged)
                temp_group = [record]
                current_tokens = content_tokens
        else:
            # Different source or date, flush and start new
            if temp_group:
                if len(temp_group) > 1:
                    merged = {
                        'id': temp_group[0]['id'],
                        'source_name': temp_group[0]['source_name'],
                        'date': temp_group[0].get('date'),
                        'content': ' '.join([r.get('content', '') for r in temp_group]),
                        'url': temp_group[0].get('url'),
                        'word_count': sum([r.get('word_count', 0) for r in temp_group]),
                        'time_period': temp_group[0].get('time_period'),
                        'content_anonymized': temp_group[0].get('content_anonymized'),
                        'metadata': temp_group[0].get('metadata', {})
                    }
                    grouped.append(merged)
                else:
                    grouped.append(temp_group[0])

            temp_group = [record]
            current_tokens = estimate_tokens(record.get('content', ''))
            last_source = source
            last_date = date

    # Flush remaining
    if temp_group:
        if len(temp_group) > 1:
            merged = {
                'id': temp_group[0]['id'],
                'source_name': temp_group[0]['source_name'],
                'date': temp_group[0].get('date'),
                'content': ' '.join([r.get('content', '') for r in temp_group]),
                'url': temp_group[0].get('url'),
                'word_count': sum([r.get('word_count', 0) for r in temp_group]),
                'time_period': temp_group[0].get('time_period'),
                'content_anonymized': temp_group[0].get('content_anonymized'),
                'metadata': temp_group[0].get('metadata', {})
            }
            grouped.append(merged)
        else:
            grouped.append(temp_group[0])

    return grouped

def main():
    print("Loading corpus_clean.jsonl...")
    records = []
    with open('corpus_clean.jsonl') as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Loaded {len(records)} records")

    # Group Twitter and Instagram
    print("Grouping Twitter and Instagram records by date...")
    records = group_twitter_instagram(records)
    print(f"After grouping: {len(records)} records")

    # Chunk all records
    print("Chunking records...")
    chunks = []
    source_chunk_counts = defaultdict(int)

    for i, record in enumerate(records):
        if i % 1000 == 0 and i > 0:
            print(f"  Processed {i} records, {len(chunks)} chunks so far...")

        content = record.get('content', '')
        if not content:
            continue

        # Chunk the content
        text_chunks = chunk_text(content)

        for chunk_content in text_chunks:
            chunk_id = str(uuid.uuid4())
            chunk = {
                'chunk_id': chunk_id,
                'source_id': record.get('id'),
                'source_name': record.get('source_name'),
                'date': record.get('date'),
                'time_period': record.get('time_period'),
                'url': record.get('url'),
                'content': chunk_content,
                'approx_tokens': estimate_tokens(chunk_content),
                'content_anonymized': record.get('content_anonymized', False),
                'metadata': record.get('metadata', {})
            }
            chunks.append(chunk)
            source_chunk_counts[record.get('source_name')] += 1

    # Write output
    print(f"Writing {len(chunks)} chunks to corpus_chunked.jsonl...")
    with open('corpus_chunked.jsonl', 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')

    # Report
    avg_tokens = sum(c.get('approx_tokens', 0) for c in chunks) / len(chunks) if chunks else 0
    print(f"\n=== CHUNKING REPORT ===")
    print(f"Total chunks: {len(chunks)}")
    print(f"Average token size: {avg_tokens:.1f}")
    print(f"\nChunks by source_name:")
    for source, count in sorted(source_chunk_counts.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")

if __name__ == '__main__':
    main()
