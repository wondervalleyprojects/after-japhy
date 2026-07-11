#!/usr/bin/env python3

import os
import json
import uuid
import pickle
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from anthropic import Anthropic
import networkx as nx
from rank_bm25 import BM25Okapi

app = Flask(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent
INDEX_DIR = PROJECT_ROOT / "index"
LOGS_DIR = PROJECT_ROOT / "logs"
STATIC_DIR = PROJECT_ROOT / "static"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)

# Load system prompt
def load_system_prompt():
    prompt_path = PROJECT_ROOT / "system_prompt.txt"
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "You are The Incomplete Reader."

SYSTEM_PROMPT = load_system_prompt()

# Load indexes
def load_indexes():
    """Load BM25 index and chunks lookup from pickle files."""
    bm25_path = INDEX_DIR / "bm25_index.pkl"
    chunks_path = INDEX_DIR / "chunks_lookup.pkl"

    if not bm25_path.exists() or not chunks_path.exists():
        print("WARNING: Index files not found. Build indexes first with scripts/build_index.py")
        return None, None

    with open(bm25_path, 'rb') as f:
        bm25_index = pickle.load(f)

    with open(chunks_path, 'rb') as f:
        chunks_lookup = pickle.load(f)

    return bm25_index, chunks_lookup

# Load database
def load_database():
    """Load SQLite database with FTS5 index."""
    db_path = INDEX_DIR / "corpus.db"
    if not db_path.exists():
        print("WARNING: corpus.db not found. Build index first with scripts/build_index.py")
        return None

    return sqlite3.connect(str(db_path), check_same_thread=False)

BM25_INDEX, CHUNKS_LOOKUP = load_indexes()
DB = load_database()

def get_chunk_text(chunk_id):
    """Get chunk text from lookup dictionary."""
    if CHUNKS_LOOKUP is None:
        return ""
    return CHUNKS_LOOKUP.get(chunk_id, "")

def bm25_search(query, top_k=20):
    """BM25 search over chunks."""
    if BM25_INDEX is None or CHUNKS_LOOKUP is None:
        return []

    # Query is tokenized the same way corpus was tokenized
    query_tokens = query.lower().split()
    scores = BM25_INDEX.get_scores(query_tokens)

    # Get top-k by score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    # Map back to chunk IDs
    chunk_ids = list(CHUNKS_LOOKUP.keys())
    results = [(chunk_ids[i], scores[i]) for i in top_indices if scores[i] > 0]

    return results

def fts5_search(query, top_k=10):
    """Full-text search via SQLite FTS5."""
    if DB is None:
        return []

    try:
        cursor = DB.cursor()
        # FTS5 query syntax
        cursor.execute("""
            SELECT chunk_id, rank FROM corpus_fts
            WHERE corpus_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, top_k))

        results = cursor.fetchall()
        return [(chunk_id, 1.0 / (abs(rank) + 1)) for chunk_id, rank in results]
    except Exception as e:
        print(f"FTS5 search error: {e}")
        return []

def retrieve_top_chunks(query, top_k=15):
    """Retrieve top chunks via BM25 + FTS5 hybrid."""
    bm25_results = bm25_search(query, top_k=20)
    fts5_results = fts5_search(query, top_k=10)

    # Combine by chunk_id, merge scores
    combined = {}
    for chunk_id, score in bm25_results:
        combined[chunk_id] = combined.get(chunk_id, 0) + score
    for chunk_id, score in fts5_results:
        combined[chunk_id] = combined.get(chunk_id, 0) + score

    # Sort by combined score, keep top-k
    sorted_chunks = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [chunk_id for chunk_id, _ in sorted_chunks]

def extract_entities_and_relationships(chunks, api_key):
    """Use Claude Haiku to extract entities and relationships from passages."""
    client = Anthropic(api_key=api_key)

    # Format chunks for extraction
    passages_text = "\n\n".join([f"[{chunk}]" for chunk in chunks])

    prompt = f"""Extract entities and relationships from these passages.

Return JSON with this structure:
{{"entities": [{{"name": "...", "type": "...", "weight": N}}], "relationships": [{{"from": "...", "to": "...", "label": "...", "strength": N}}]}}

Entity types: THEME, PERSON, PLACE, PERIOD, EMOTION, BELIEF, PROJECT
Weight: 1-5 scale (frequency × significance)
Relationships: co-occurrence, contradiction, evolution, cause, recurrence

Passages:
{passages_text}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        # Extract JSON from response
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "{" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            return json.loads(text)
        except:
            return {"entities": [], "relationships": []}

    except Exception as e:
        print(f"Entity extraction error: {e}")
        return {"entities": [], "relationships": []}

def build_mini_graph(extracted_data):
    """Build a mini-graph from extracted entities and relationships."""
    g = nx.DiGraph()

    # Add nodes with weights
    entities = extracted_data.get("entities", [])
    for entity in entities:
        weight = entity.get("weight", 1)
        g.add_node(entity["name"], type=entity.get("type", ""), weight=weight)

    # Add edges with weights
    relationships = extracted_data.get("relationships", [])
    for rel in relationships:
        g.add_edge(rel["from"], rel["to"], label=rel.get("label", ""), strength=rel.get("strength", 1))

    # Get top nodes by weighted degree centrality
    if g.number_of_nodes() > 0:
        centrality = nx.degree_centrality(g)
        top_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]

        # Format as text
        thematic_web = "Thematic web: "
        for node, _ in top_nodes:
            successors = list(g.successors(node))
            predecessors = list(g.predecessors(node))

            relations = []
            for succ in successors:
                edge_label = g[node][succ].get("label", "→")
                relations.append(f"{node} —{edge_label}→ {succ}")
            for pred in predecessors:
                edge_label = g[pred][node].get("label", "←")
                relations.append(f"{pred} —{edge_label}→ {node}")

            thematic_web += " · ".join(relations[:2]) + " "

        return thematic_web.strip()

    return "Thematic web: (sparse)"

def get_chunk_metadata(chunk_id):
    """Get metadata (source_name, date) for a chunk from database."""
    if DB is None:
        return None

    try:
        cursor = DB.cursor()
        cursor.execute("""
            SELECT source_name, date FROM chunks
            WHERE chunk_id = ?
        """, (chunk_id,))

        result = cursor.fetchone()
        if result:
            return {"source_name": result[0], "date": result[1]}
    except Exception as e:
        print(f"Error fetching metadata: {e}")

    return None

def synthesize_response(query, context_passages, thematic_web, conversation_history, api_key):
    """Use Claude Haiku to synthesize a response."""
    client = Anthropic(api_key=api_key)

    # Format context
    context_text = "\n\n".join(context_passages[:10])  # Limit context

    # Build system message with context
    system_with_context = f"""{SYSTEM_PROMPT}

## CORPUS PASSAGES (this turn)

{context_text}

## THEMATIC WEB

{thematic_web}
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=system_with_context,
            messages=conversation_history
        )

        return response.content[0].text
    except Exception as e:
        print(f"Synthesis error: {e}")
        return f"Something obstructed the reading. ({str(e)})"

def get_opening_reflection(api_key):
    """Generate opening reflection from a random chunk."""
    if CHUNKS_LOOKUP is None or DB is None:
        return "The record awaits.", []

    import random

    # Pick a random chunk
    random_chunk_id = random.choice(list(CHUNKS_LOOKUP.keys()))
    chunk_text = get_chunk_text(random_chunk_id)
    metadata = get_chunk_metadata(random_chunk_id)

    # Get reflection from Haiku on this chunk
    client = Anthropic(api_key=api_key)

    prompt = f"""Given this excerpt from a personal record, write a single reflective sentence (under 30 words) that captures what matters in it. Do not explain. Just notice.

Excerpt: {chunk_text[:300]}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        reflection = response.content[0].text.strip()
        sources = [metadata] if metadata else []

        return reflection, sources
    except Exception as e:
        print(f"Opening reflection error: {e}")
        return "The record awaits.", []

def log_session(session_id, turn_data):
    """Log a conversation turn to JSONL file."""
    log_file = LOGS_DIR / f"{session_id}.jsonl"

    with open(log_file, 'a') as f:
        f.write(json.dumps(turn_data) + "\n")

@app.route('/')
def index():
    """Serve the frontend HTML."""
    frontend_path = STATIC_DIR / "index.html"
    if frontend_path.exists():
        with open(frontend_path, 'r') as f:
            return f.read()
    return "Frontend not found", 404

@app.route('/health')
def health():
    """Health check endpoint."""
    if DB is None or BM25_INDEX is None:
        return jsonify({"status": "error", "message": "Indexes not loaded"}), 500

    try:
        cursor = DB.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]

        record_count = len(CHUNKS_LOOKUP) if CHUNKS_LOOKUP else 0

        return jsonify({
            "status": "ok",
            "records": record_count,
            "chunks": chunk_count
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Main conversation endpoint (LazyGraphRAG)."""
    data = request.json
    session_id = data.get('session_id', str(uuid.uuid4()))
    conversation_history = data.get('conversation_history', [])
    is_opening = data.get('is_opening', False)

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set"}), 500

    # Opening reflection
    if is_opening:
        reflection, sources = get_opening_reflection(api_key)
        return jsonify({
            "opening_reflection": reflection,
            "sources": sources,
            "session_id": session_id
        })

    # Regular turn
    if not conversation_history or len(conversation_history) == 0:
        return jsonify({"error": "No user message"}), 400

    user_message = conversation_history[-1]['content']

    # Step 1: Retrieve top chunks
    top_chunks = retrieve_top_chunks(user_message, top_k=15)
    context_passages = [get_chunk_text(chunk_id) for chunk_id in top_chunks]

    # Step 2: Entity extraction
    extracted = extract_entities_and_relationships(context_passages[:10], api_key)

    # Step 3: Mini-graph construction
    thematic_web = build_mini_graph(extracted)

    # Step 4: Synthesis
    response_text = synthesize_response(
        user_message,
        context_passages,
        thematic_web,
        conversation_history,
        api_key
    )

    # Get sources
    sources = []
    for chunk_id in top_chunks[:5]:
        metadata = get_chunk_metadata(chunk_id)
        if metadata:
            sources.append(metadata)

    # Log turn
    log_session(session_id, {
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "response": response_text,
        "sources": sources,
        "chunk_count": len(top_chunks)
    })

    return jsonify({
        "response": response_text,
        "sources": sources,
        "session_id": session_id
    })

@app.route('/test/retrieve', methods=['POST'])
def test_retrieve():
    """Test retrieval without LLM call."""
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "No query provided"}), 400

    top_chunks = retrieve_top_chunks(query, top_k=10)

    results = []
    for chunk_id in top_chunks:
        text = get_chunk_text(chunk_id)
        metadata = get_chunk_metadata(chunk_id)
        results.append({
            "chunk_id": chunk_id,
            "text": text[:200] + "..." if len(text) > 200 else text,
            "metadata": metadata
        })

    return jsonify({"results": results})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
