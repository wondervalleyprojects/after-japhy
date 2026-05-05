# After Japhy: RAG Web App

A retrieval-augmented generation (RAG) web app built from a comprehensive personal corpus. Visitors can engage with an AI reader trained on 75,000+ documents spanning emails, social media, articles, and personal writing.

## Architecture

### Data Pipeline
1. **Master Corpus** (75,816 records from original sources)
   - Gmail accounts (personal & WVP): 28,692 records
   - Facebook: 21,174 records  
   - Twitter: 13,975 records
   - Other sources (Reddit, LinkedIn, articles, etc.)

2. **Gmail Extraction** (44,294 sent messages)
   - Personal Gmail: 38,139 sent messages
   - WVP Gmail: 6,155 sent messages (filtered for financial content)

3. **Preprocessing** (119,734 records after filtering)
   - Removed WVP financial records (invoices, payments, etc.)
   - Removed received Facebook messages
   - Applied Victorian name-izer for anonymization
   - Added time period classification

4. **Chunking** (111,744 chunks)
   - Records split at sentence boundaries into 300-800 token passages
   - Twitter/Instagram records grouped by date
   - TF-IDF embeddings using scikit-learn

5. **Chroma Vector Database**
   - Persistent storage with metadata
   - 111k+ vectors indexed by chunk ID
   - Fast semantic similarity search

## Setup

### Prerequisites
- Python 3.13+
- ~2GB disk space for corpus files and Chroma database
- ANTHROPIC_API_KEY environment variable set

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install chromadb flask anthropic scikit-learn

# Or install from requirements.txt
pip install -r requirements.txt
```

### Building the Corpus

The corpus build is a multi-step process:

```bash
# 1. Extract sent emails from mbox files (runs in background, ~30-60 mins per file)
python3 scripts/extract_gmail_sent.py <path_to_mbox> <account_type> <output_file>

# 2. Preprocess corpus (filter, anonymize, add metadata)
python3 scripts/preprocess_corpus.py

# 3. Chunk for embedding (split into semantic passages)
python3 scripts/chunk_corpus.py

# 4. Embed and load into Chroma (TF-IDF + Chroma DB)
python3 scripts/embed_and_load.py
```

### Running the Server

```bash
source venv/bin/activate
export ANTHROPIC_API_KEY=sk-...
python3 app.py
```

Server runs on `http://localhost:5000`

## API

### POST /chat
Query the corpus with conversational context.

**Request:**
```json
{
  "message": "What kept coming up for him around 2012?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "response": "Based on the corpus...",
  "sources": [
    {"source_name": "article", "date": "2012-03-15"},
    {"source_name": "twitter", "date": "2012-07-22"}
  ],
  "session_id": "uuid"
}
```

### GET /health
Health check endpoint. Returns chunk count in collection.

## Data Files

### Generated During Build
- `master_corpus.jsonl` - All records before preprocessing (75,816 records)
- `gmail_personal_sent.jsonl` - Extracted personal Gmail (38,139 records)
- `gmail_wvp_sent.jsonl` - Extracted WVP Gmail (6,155 records)
- `corpus_clean.jsonl` - After preprocessing (119,734 records)
- `corpus_chunked.jsonl` - After chunking (111,744 chunks)
- `chroma_db/` - Vector database directory
- `logs/` - Session logs (JSON per request)

### Not Committed to Git
See `.gitignore` for files excluded from version control (corpus files, databases, logs)

## System Prompt

The system prompt is loaded from `system_prompt.txt`. It guides the AI reader's behavior when engaging with the corpus. The prompt emphasizes:
- Engaging with the personal corpus authentically
- Citing sources from the retrieved records
- Acknowledging gaps or uncertainty in the corpus
- Respecting the diaristic and reflective nature of the content

## Testing

```bash
source venv/bin/activate
python3 test_chat.py
```

Runs five sequential queries with conversation history to test the full pipeline.

## Anonymization

The preprocessing step applies a "Victorian name-izer" to personal communications:
- Common first names are replaced with initial + em-dash (e.g., "Sarah" → "S—")
- Protected names are never anonymized: Japhy, Grant, Jeffrey, Orlinski, and public figures
- Applied to: Gmail, Bear Notes, Facebook messages

## Performance

- **Preprocessing**: ~2 minutes
- **Chunking**: ~3 minutes
- **Embedding**: ~5-10 minutes (TF-IDF on 111k chunks)
- **Query time**: <500ms average

## Troubleshooting

**ImportError: No module named chromadb**
- Ensure virtual environment is activated: `source venv/bin/activate`

**ANTHROPIC_API_KEY not set**
- Set environment variable: `export ANTHROPIC_API_KEY=sk-...`

**Chroma connection error**
- Check that chroma_db/ directory exists and is readable
- Re-run `python3 scripts/embed_and_load.py` to rebuild

**Out of memory during embedding**
- TF-IDF vectorizer loads all chunks into memory
- Reduce batch size in embed_and_load.py if needed
- Or process in smaller corpus_chunked.jsonl files

## Architecture Decisions

### TF-IDF over Dense Embeddings
- Avoids PyTorch/sentence-transformers dependency issues
- Still provides effective semantic search via TF-IDF similarity
- Scales well to 100k+ chunks
- Interpretable: shows which terms matched in retrieval

### Chroma for Vector Storage
- Persistent storage without additional infrastructure
- Fast similarity search
- Metadata filtering support
- Single-file database format

### Session Logging
- Every conversation logged to JSON for auditability
- Includes message, history, retrieved chunks, and response
- Enables analysis of what the corpus reveals

## License

See LICENSE file (if present)
