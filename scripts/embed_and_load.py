#!/usr/bin/env python3

import json
import chromadb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_embeddings(texts, vectorizer):
    """Get TF-IDF embeddings."""
    return vectorizer.transform(texts).toarray()

def main():
    print("Creating Chroma client...")
    client = chromadb.PersistentClient(path='chroma_db')
    collection = client.get_or_create_collection(name='after_japhy')

    print(f"Collection has {collection.count()} documents before loading")

    print("Loading corpus_chunked.jsonl...")
    chunks = []
    with open('corpus_chunked.jsonl') as f:
        for line in f:
            chunks.append(json.loads(line))

    print(f"Loaded {len(chunks)} chunks")

    # Check which chunks already exist
    existing_ids = set()
    try:
        results = collection.get()
        if results and 'ids' in results:
            existing_ids = set(results['ids'])
    except:
        pass

    print(f"Collection already has {len(existing_ids)} documents")

    # Create vectorizer on all new content
    new_chunks = [c for c in chunks if c['chunk_id'] not in existing_ids]

    # If no new chunks, still create and save vectorizer for all chunks (for app.py to use)
    if not new_chunks:
        print("No new chunks to add. Creating vectorizer for query embedding...")
        all_contents = [c['content'] for c in chunks]
        vectorizer = TfidfVectorizer(
            max_features=5000,
            min_df=1,
            max_df=0.8,
            ngram_range=(1, 2),
            stop_words='english'
        )
        vectorizer.fit(all_contents)

        import pickle
        with open('tfidf_vectorizer.pkl', 'wb') as f:
            pickle.dump(vectorizer, f)
        print(f"Saved TF-IDF vectorizer to tfidf_vectorizer.pkl")
        return

    print(f"Creating TF-IDF vectorizer for {len(new_chunks)} chunks...")
    contents = [c['content'] for c in new_chunks]

    # Create vectorizer with reasonable parameters
    vectorizer = TfidfVectorizer(
        max_features=5000,
        min_df=1,
        max_df=0.8,
        ngram_range=(1, 2),
        stop_words='english'
    )
    embeddings = vectorizer.fit_transform(contents).toarray()

    # Process in batches
    batch_size = 64
    new_count = 0

    for batch_start in range(0, len(new_chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(new_chunks))
        batch = new_chunks[batch_start:batch_end]
        batch_embeddings = embeddings[batch_start:batch_end]

        if batch_start % 500 == 0 and batch_start > 0:
            print(f"  Added {new_count} chunks so far...")

        # Prepare data for Chroma
        ids = [c['chunk_id'] for c in batch]
        metadatas = [
            {
                'source_name': c['source_name'],
                'date': c.get('date') or 'unknown',
                'time_period': c.get('time_period') or 'unknown',
                'source_id': c['source_id']
            }
            for c in batch
        ]

        # Add to collection
        collection.add(
            ids=ids,
            embeddings=batch_embeddings.tolist(),
            metadatas=metadatas,
            documents=[c['content'] for c in batch]
        )

        new_count += len(batch)

    # Save the vectorizer for use in app.py
    import pickle
    with open('tfidf_vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
    print(f"Saved TF-IDF vectorizer to tfidf_vectorizer.pkl")

    print(f"\n=== EMBEDDING REPORT ===")
    print(f"Total chunks processed: {len(chunks)}")
    print(f"New chunks added: {new_count}")
    print(f"Total chunks in collection: {collection.count()}")
    print(f"Embedding dimension: {embeddings.shape[1]}")

if __name__ == '__main__':
    main()
