#!/usr/bin/env python3
"""Display corpus statistics and build summary."""

import json
import os
from collections import defaultdict

def show_stats():
    print("=" * 70)
    print("AFTER JAPHY: CORPUS STATISTICS")
    print("=" * 70)

    # Master corpus stats
    if os.path.exists('master_corpus.jsonl'):
        master_count = sum(1 for _ in open('master_corpus.jsonl'))
        print(f"\n📦 Master Corpus: {master_count:,} records")

    # Gmail extractions
    if os.path.exists('gmail_personal_sent.jsonl'):
        personal_count = sum(1 for _ in open('gmail_personal_sent.jsonl'))
        print(f"📧 Gmail Personal (sent): {personal_count:,} records")

    if os.path.exists('gmail_wvp_sent.jsonl'):
        wvp_count = sum(1 for _ in open('gmail_wvp_sent.jsonl'))
        print(f"📧 Gmail WVP (sent): {wvp_count:,} records")

    # Cleaned corpus
    if os.path.exists('corpus_clean.jsonl'):
        clean_count = sum(1 for _ in open('corpus_clean.jsonl'))
        source_counts = defaultdict(int)
        time_counts = defaultdict(int)

        with open('corpus_clean.jsonl') as f:
            for line in f:
                record = json.loads(line)
                source_counts[record.get('source_name')] += 1
                time_counts[record.get('time_period')] += 1

        print(f"\n✨ Cleaned Corpus: {clean_count:,} records")
        print("  By source:")
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            print(f"    {source}: {count:,}")
        print("  By time period:")
        for period in ['early_2000s', 'the_2010s', 'recent', 'unknown']:
            if period in time_counts:
                print(f"    {period}: {time_counts[period]:,}")

    # Chunked corpus
    if os.path.exists('corpus_chunked.jsonl'):
        chunk_count = sum(1 for _ in open('corpus_chunked.jsonl'))
        avg_tokens = 0
        chunk_sources = defaultdict(int)

        with open('corpus_chunked.jsonl') as f:
            for line in f:
                chunk = json.loads(line)
                avg_tokens += chunk.get('approx_tokens', 0)
                chunk_sources[chunk.get('source_name')] += 1

        avg_tokens = avg_tokens / chunk_count if chunk_count else 0
        print(f"\n🔀 Chunked Corpus: {chunk_count:,} chunks")
        print(f"   Average size: {avg_tokens:.0f} tokens")
        print("  Chunks by source:")
        for source, count in sorted(chunk_sources.items(), key=lambda x: -x[1])[:5]:
            print(f"    {source}: {count:,}")

    # Chroma database
    try:
        import chromadb
        client = chromadb.PersistentClient(path='chroma_db')
        collection = client.get_or_create_collection(name='after_japhy')
        chroma_count = collection.count()
        chroma_size = os.path.getsize('chroma_db') if os.path.isdir('chroma_db') else 0

        print(f"\n🗄️  Chroma Vector Database: {chroma_count:,} chunks")
        if chroma_size > 0:
            size_mb = chroma_size / (1024 ** 2)
            print(f"   Size on disk: {size_mb:.1f} MB")
    except Exception as e:
        print(f"\n🗄️  Chroma Vector Database: Error - {e}")

    # Status
    print("\n" + "=" * 70)

    # Check if ready to run
    is_ready = all([
        os.path.exists('app.py'),
        os.path.exists('venv'),
        os.path.exists('chroma_db'),
        os.path.exists('system_prompt.txt'),
    ])

    if is_ready:
        print("✅ System is ready to run!")
        print("\nTo start the server:")
        print("  cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy")
        print("  source venv/bin/activate")
        print("  export ANTHROPIC_API_KEY=sk-your-key")
        print("  python3 app.py")
    else:
        print("⏳ System is still being built...")
        missing = []
        if not os.path.exists('app.py'): missing.append("app.py")
        if not os.path.exists('venv'): missing.append("venv")
        if not os.path.exists('chroma_db'): missing.append("chroma_db")
        if not os.path.exists('system_prompt.txt'): missing.append("system_prompt.txt")
        print(f"Missing: {', '.join(missing)}")

    print("=" * 70)

if __name__ == '__main__':
    show_stats()
