#!/usr/bin/env python3

import os
import json
import uuid
import pickle
from datetime import datetime
from flask import Flask, request, jsonify
import chromadb
from anthropic import Anthropic
import numpy as np

app = Flask(__name__)

# Load system prompt
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "You are an AI reader engaging with a corpus of personal writing."

# Load TF-IDF vectorizer for query embedding
def load_vectorizer():
    vectorizer_path = os.path.join(os.path.dirname(__file__), 'tfidf_vectorizer.pkl')
    try:
        with open(vectorizer_path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print("WARNING: tfidf_vectorizer.pkl not found. Queries will fail.")
        return None

# Load system prompt at startup
SYSTEM_PROMPT = load_system_prompt()
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), 'chroma_db'))
collection = chroma_client.get_or_create_collection(name='after_japhy')
vectorizer = load_vectorizer()

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

def get_opening_reflection(api_key):
    """Get a random corpus chunk and generate an opening reflection on it."""
    try:
        # Get a random chunk by querying with a random vector
        # Generate random vector matching TF-IDF dimensions
        random_vector = np.random.random(vectorizer.transform(['test']).shape[1]).tolist()

        search_results = collection.query(
            query_embeddings=[random_vector],
            n_results=1
        )

        if not search_results or not search_results.get('documents') or not search_results['documents'][0]:
            print("Warning: No random chunk found")
            return None

        chunk_content = search_results['documents'][0][0] if search_results['documents'][0] else None
        if not chunk_content:
            print("Warning: No chunk content found")
            return None

        # Generate a reflection on this chunk
        reflection_prompt = f"""You are mid-thought about this passage from the record:

"{chunk_content}"

Generate a brief, internal reflection—something you're turning over in your mind about this passage. Not an analysis. A fragment of thinking. Start with "..." as if you've been reading already.

Keep it to 2-3 sentences. Something like:
- "...the same question, again. Hard to say when."
- "...I keep finding this word."
- "...what was he reaching for in this moment"

Start with "..." and make it sound like you're in the middle of something."""

        client = Anthropic(api_key=api_key)
        reflection_response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=150,
            system="You are generating internal monologue—a reader's brief reflection. Minimal, literary, in media res. No punctuation flourishes. Just thinking.",
            messages=[{'role': 'user', 'content': reflection_prompt}]
        )

        text = reflection_response.content[0].text
        print(f"Generated opening reflection: {text[:50]}...")
        return text
    except Exception as e:
        print(f"Error generating opening reflection: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Get API key from environment at request time
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'error': 'ANTHROPIC_API_KEY environment variable is not set'}), 500

        # Create Anthropic client
        client = Anthropic(api_key=api_key)

        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        message = data.get('message')
        if not message:
            return jsonify({'error': 'message field is required'}), 400

        history = data.get('history', [])
        session_id = data.get('session_id') or str(uuid.uuid4())

        # Embed query using the same TF-IDF vectorizer - retrieve on EVERY turn
        if not vectorizer:
            return jsonify({'error': 'TF-IDF vectorizer not loaded'}), 500

        try:
            query_embedding = vectorizer.transform([message]).toarray()[0]
            search_results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=8,
                include=['documents', 'metadatas', 'distances']
            )
        except Exception as e:
            print(f"Query error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Query failed: {str(e)}'}), 500

        # Extract retrieved chunks with metadata - these go into EVERY response
        retrieved_chunks = []
        if search_results and search_results.get('documents'):
            documents = search_results['documents'][0] if search_results['documents'] else []
            metadatas = search_results.get('metadatas', [[]])[0] if search_results.get('metadatas') else [{}] * len(documents)

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                retrieved_chunks.append({
                    'source_name': metadata.get('source_name', 'unknown'),
                    'date': metadata.get('date', 'unknown'),
                    'content': doc
                })

        # Build Claude API request
        messages = []

        # Check if this is the first turn
        is_first_turn = len(history) == 0
        opening_reflection = None

        if is_first_turn:
            # Generate opening reflection from corpus
            opening_reflection = get_opening_reflection(api_key)
            if opening_reflection:
                # Add opening as initial context
                messages.append({
                    'role': 'assistant',
                    'content': opening_reflection
                })

        # Add conversation history (excludes opening reflection)
        for hist_msg in history:
            messages.append(hist_msg)

        # Always include retrieved chunks as context with the current message
        # This ensures the reader is always grounded in the corpus
        context_parts = ["FROM THE RECORD:\n"]
        for chunk in retrieved_chunks:
            context_parts.append(f"[{chunk['source_name']}, {chunk['date']}]\n{chunk['content']}\n")

        context_text = "\n".join(context_parts)

        # Add current message with corpus context
        messages.append({
            'role': 'user',
            'content': f"{context_text}\n---\n\n{message}"
        })

        # Call Claude API
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        response_text = response.content[0].text

        # Log the session
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'message': message,
            'history': history,
            'retrieved_chunks': retrieved_chunks,
            'response': response_text
        }

        log_file = os.path.join(LOGS_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_id}.json")
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

        # Return response
        return jsonify({
            'response': response_text,
            'opening_reflection': opening_reflection,
            'sources': [{'source_name': c['source_name'], 'date': c['date']} for c in retrieved_chunks],
            'session_id': session_id
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Simple HTML interface for testing the chat endpoint."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>After Japhy - RAG Chat Interface</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .container { background: #f5f5f5; padding: 20px; border-radius: 8px; }
            h1 { color: #333; }
            .chat-box { height: 400px; border: 1px solid #ccc; overflow-y: auto; padding: 10px; background: white; margin: 10px 0; border-radius: 4px; }
            .message { margin: 10px 0; padding: 8px; border-radius: 4px; }
            .user { background: #e3f2fd; text-align: right; }
            .assistant { background: #f1f8e9; }
            .sources { font-size: 0.9em; color: #666; margin-top: 5px; }
            input, textarea, button { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
            button { background: #2196F3; color: white; border: none; cursor: pointer; border-radius: 4px; }
            button:hover { background: #1976D2; }
            .error { background: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; margin: 10px 0; }
            .loading { color: #666; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>After Japhy - AI Reader Chat</h1>
            <p>Ask questions about the corpus of personal writing.</p>

            <div class="chat-box" id="chatBox"></div>

            <textarea id="messageInput" placeholder="Ask a question..." rows="3"></textarea>
            <button onclick="sendMessage()">Send</button>

            <div id="error"></div>
        </div>

        <script>
            let history = [];
            let sessionId = generateUUID();

            function generateUUID() {
                return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                    return v.toString(16);
                });
            }

            function sendMessage() {
                const message = document.getElementById('messageInput').value.trim();
                if (!message) return;

                // Display user message
                addMessage('user', message);
                document.getElementById('messageInput').value = '';
                addMessage('loading', 'Thinking...');

                // Send to API
                fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        history: history,
                        session_id: sessionId
                    })
                })
                .then(r => r.json())
                .then(data => {
                    removeLoading();
                    if (data.response) {
                        // Show opening reflection if this is the first turn
                        if (data.opening_reflection && history.length === 0) {
                            addMessage('assistant', data.opening_reflection);
                        }

                        addMessage('assistant', data.response);

                        // Show sources
                        if (data.sources && data.sources.length > 0) {
                            let sourcesText = 'Sources: ' + data.sources.map(s => `${s.source_name} (${s.date})`).join(', ');
                            addMessage('sources', sourcesText);
                        }

                        // Update history
                        history.push({role: 'user', content: message});
                        history.push({role: 'assistant', content: data.response});
                    } else {
                        showError('Error: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(e => {
                    removeLoading();
                    showError('Network error: ' + e.message);
                });
            }

            function addMessage(role, text) {
                const box = document.getElementById('chatBox');
                const div = document.createElement('div');
                div.className = 'message ' + role;
                if (role === 'sources') {
                    div.className = 'message sources';
                    div.textContent = text;
                } else if (role === 'loading') {
                    div.className = 'message loading';
                    div.textContent = text;
                } else if (role === 'user') {
                    div.textContent = 'You: ' + text;
                } else {
                    div.textContent = 'Assistant: ' + text;
                }
                box.appendChild(div);
                box.scrollTop = box.scrollHeight;
            }

            function removeLoading() {
                const box = document.getElementById('chatBox');
                const loading = box.querySelector('.loading');
                if (loading) loading.remove();
            }

            function showError(msg) {
                document.getElementById('error').innerHTML = '<div class="error">' + msg + '</div>';
            }

            // Allow Enter key to send
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """
    return html

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'After Japhy RAG server running'})

@app.route('/test/retrieve', methods=['POST'])
def test_retrieve():
    """Test endpoint that retrieves chunks without calling Claude API"""
    try:
        data = request.get_json()
        message = data.get('message', 'test')

        if not vectorizer:
            return jsonify({'error': 'TF-IDF vectorizer not loaded'}), 500

        query_embedding = vectorizer.transform([message]).toarray()[0]
        search_results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=3,
            include=['documents', 'metadatas']
        )

        chunks = []
        if search_results and search_results.get('documents'):
            docs = search_results['documents'][0] if search_results['documents'] else []
            metas = search_results.get('metadatas', [[]])[0] if search_results.get('metadatas') else [{}] * len(docs)

            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                chunks.append({
                    'source': meta.get('source_name', 'unknown'),
                    'date': meta.get('date', 'unknown'),
                    'content': doc[:200] + '...' if len(doc) > 200 else doc
                })

        return jsonify({
            'message': message,
            'chunks_retrieved': len(chunks),
            'chunks': chunks
        })
    except Exception as e:
        print(f"Test retrieve error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    api_key_on_startup = os.getenv('ANTHROPIC_API_KEY')
    if api_key_on_startup:
        print(f"✓ ANTHROPIC_API_KEY is set on startup", flush=True)
    else:
        print(f"✗ ANTHROPIC_API_KEY is NOT set on startup", flush=True)
    app.run(debug=False, port=8000)
