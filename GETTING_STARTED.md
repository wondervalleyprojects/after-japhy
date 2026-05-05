# Getting Started with After Japhy

## Quick Start

### 1. Activate Virtual Environment
```bash
cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy
source venv/bin/activate
```

### 2. Set Your API Key
```bash
export ANTHROPIC_API_KEY=sk-your-actual-key-here
```

### 3. Start the Server
```bash
python3 app.py
```

Server will be available at `http://localhost:5000`

### 4. Test the Server
In another terminal:
```bash
cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy
source venv/bin/activate
python3 test_chat.py
```

## Understanding the Pipeline

### Step 1: Gmail Extraction (~3-4 hours)
Both mbox files are huge (69GB+ combined), so extraction takes time. This only needs to happen once.
```bash
python3 scripts/extract_gmail_sent.py <mbox_file> <personal|wvp> <output_file>
```

### Step 2: Preprocessing (~2 minutes)
Filters financial content, anonymizes names, adds metadata.
```bash
python3 scripts/preprocess_corpus.py
```

Output: `corpus_clean.jsonl` (119,734 records)

### Step 3: Chunking (~3 minutes)
Breaks records into semantic chunks at sentence boundaries (300-800 tokens).
```bash
python3 scripts/chunk_corpus.py
```

Output: `corpus_chunked.jsonl` (111,744 chunks)

### Step 4: Embedding (~5-10 minutes)
Creates TF-IDF vectorization and loads documents into Chroma vector database.
```bash
python3 scripts/embed_and_load.py
```

Output: `chroma_db/` (1.7GB)

## API Usage

### How the Retrieval Works

The system uses **hybrid semantic + keyword search**:

1. **Semantic Query Expansion**: Claude analyzes your question to understand intent
   - Example: "happiest moments" → ["happiness", "joy", "contentment", "celebration"]

2. **Keyword Matching**: Documents are scored by how many expanded keywords they contain
   - Documents with zero matches: filtered out
   - Documents with 1+ matches: ranked by match count and semantic relevance

3. **Result Ranking**: Most relevant documents appear first in sources

This hybrid approach finds conceptually related material instead of just statistically similar documents.

### Query the Corpus
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What did he think about technology?",
    "history": [],
    "session_id": "my-session-id"
  }'
```

### Response Format
```json
{
  "response": "Based on the corpus, he thought...",
  "opening_reflection": "...the same question, again.",
  "sources": [
    {"source_name": "blog", "date": "2015-03-22"},
    {"source_name": "article", "date": "2016-08-15"}
  ],
  "session_id": "my-session-id"
}
```

## Corpus Breakdown

### Records by Source
- **gmail_personal**: 65,265 chunks (Gmail sent emails)
- **facebook**: 21,180 chunks (Posts, messages, checkins)
- **gmail_wvp**: 9,390 chunks (Work emails, filtered for confidentiality)
- **chatgpt**: 4,547 chunks (ChatGPT conversations)
- **twitter**: 3,455 chunks (Tweets)
- **instagram**: 1,662 chunks (Instagram captions)
- **queerty**: 1,511 chunks (News articles)
- **reddit**: 1,311 chunks (Reddit comments)
- **blog**: 1,076 chunks (Blog posts)
- **linkedin**: 1,072 chunks (LinkedIn posts)
- **bear_notes**: 955 chunks (Personal notes)
- **scrivener**: 172 chunks (Drafts, essays)
- **article**: 126 chunks (Published articles)
- **youtube**: 22 chunks (Video transcripts)

### Time Periods
- **early_2000s**: Pre-2010 content
- **the_2010s**: 2010-2019 content
- **recent**: 2020+ content

## Session Logging

Every conversation is logged to `logs/` directory as JSON files with:
- Timestamp
- Session ID
- User message
- Conversation history
- Retrieved chunks (with content, keyword match counts, and relevance scores)
- AI response

Use these logs to understand:
- What the corpus revealed about a query
- Which keywords triggered specific matches
- How many keyword matches each retrieved document had
- The relevance scoring from the hybrid search

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
Make sure to activate the virtual environment first:
```bash
source venv/bin/activate
```

### "ANTHROPIC_API_KEY environment variable is not set"
Set your API key:
```bash
export ANTHROPIC_API_KEY=sk-your-key
```

### "Connection refused" when testing
Make sure the Flask server is running in another terminal:
```bash
python3 app.py
```

### "Chroma connection error"
Rebuild the Chroma database:
```bash
python3 scripts/embed_and_load.py
```

### Memory issues during embedding
The TF-IDF vectorizer loads all chunks into RAM. If you run out of memory:
1. Close other applications
2. Try again (vectorizer will resume from last checkpoint)

## Understanding Anonymization

The system applies a "Victorian name-izer" to Gmail, Bear Notes, and Facebook messages:

### Names That Get Anonymized
- Common first names are replaced with initial + em-dash
- Example: "Spencer asked me..." becomes "S— asked me..."

### Names That Remain Protected
Never anonymized because they're identifiable public content:
- Japhy, Grant, Jeffrey, Orlinski (the person)
- Barack Obama, Hillary Clinton, Donald Trump, etc. (public figures)
- Historical/literary figures (Octavia Butler, Nabokov, etc.)

This helps preserve privacy while maintaining readability of the corpus.

## Performance Notes

- **Typical query time**: <1000ms (query expansion via Claude + hybrid search + response generation)
- **Query expansion**: ~200-300ms (Claude API call to understand semantic intent)
- **Hybrid search**: ~50-100ms (keyword matching across corpus)
- **Response generation**: ~500-700ms (Claude API generating response)
- **Concurrent users**: Single-threaded Flask app (use Gunicorn for production)
- **Database size**: ~1.7GB on disk
- **Memory usage**: ~500MB at idle, 1.5GB+ during embedding

## Next Steps

1. Make sure the full pipeline has completed (check `chroma_db/` size)
2. Set your `ANTHROPIC_API_KEY`
3. Start the server with `python3 app.py`
4. Query it with `python3 test_chat.py` or via curl
5. Check `logs/` directory to see what the corpus revealed

For detailed API documentation, see README.md
