# After Japhy — The Incomplete Reader

*Wonder Valley Projects — Companion Lab No. 1. Remains, No. 1.*

Not a simulation. Not a recreation. Not a portrait. A reader of one
record — the traces a person left behind — and nothing else.

This repository holds the v2 application: a Flask web app that deploys
the reader against a 75,816-record personal corpus using a LazyGraphRAG
retrieval architecture. The corpus itself, the retrieval index, and all
session logs are private and never enter git.

## Architecture (v2 — LazyGraphRAG)

No embeddings, no vector database, no upfront knowledge graph.

**Index build** (one-time, zero model calls): the anonymized corpus is
chunked (~400 words, 80-word overlap) into SQLite with an FTS5 full-text
index, plus a BM25 index (`rank_bm25`) serialized to pickle. 26,860
chunks, ~128MB on disk, ~450MB in RAM when loaded.

**Per conversation turn** (2 Haiku calls):

1. **Retrieve** — BM25 top-20 merged with FTS5 top-10, keep top 15
2. **Extract** — model call #1 pulls entities/relationships from the passages
3. **Graph** — NetworkX mini-graph built per query; top nodes by degree
   centrality become a plain-text "thematic web"
4. **Synthesize** — model call #2: system prompt + passages + thematic
   web + conversation history → the reader speaks

All model calls pass through `model_seam.py` — provider, endpoint, and
model name live in that one file only (WVP vendor-independence ruling,
July 10 2026). Current model: Claude Haiku 4.5.

## Access model

- Unlisted URL + a single shared access word (`GATE_WORD` env var),
  published inside a paid Substack post. Typed into the threshold page.
- No user accounts, no email capture, no analytics, no tracking.
- The reader has no memory of visitors. Neither does the infrastructure,
  beyond private server-side JSON session logs (`logs/`, or the mounted
  volume in production).
- Spend guards: `MAX_TURNS_PER_SESSION` (default 30) and
  `MAX_REQUESTS_PER_DAY` (default 500). At a cap the reader simply stops
  responding; the client's Stillness choreography handles the rest.

## Running locally

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# .env: ANTHROPIC_API_KEY=... (GATE_WORD optional; gate stands open if unset)
python app.py                      # http://localhost:5000
# or, with a test gate word:
bash scripts/dev_server.sh         # http://localhost:5059, word: mojave
```

Requires `index/` (corpus.db, bm25_index.pkl, chunks_lookup.pkl), built
via `scripts/build_index.py` from the anonymized corpus.

## Endpoints

| Route | What |
|---|---|
| `GET /` | The threshold, then the encounter |
| `POST /gate` | `{"word": "..."}` → signed session cookie |
| `POST /chat` | Gated. Conversation turn or opening reflection |
| `POST /test/retrieve` | Gated. Retrieval-only, no model calls |
| `GET /health` | `{"status": "ok", "records": N, "chunks": N}` |

## Deployment

Fly.io, one always-on 1GB machine, ~$6/month, index baked into the
image at deploy time. Full walkthrough, secrets setup, cost table, and
the rotate-word / rotate-key / take-down runbook: **[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)**.

Shape rationale and rejected alternatives: **[ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md)**.

## Corpus custody

The corpus is a personal archive first and an index second.
`scripts/export_corpus_markdown.py` exports all 75,816 records to plain
markdown files (one per source per year), each record under a provenance
header (source, date, era, tier). The export lives alongside the master
corpus, readable with nothing installed.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/verify_corpus.py` | Count records against the manifest |
| `scripts/anonymize_corpus.py` | Victorian name anonymizer (spaCy; needs `requirements-local.txt`) |
| `scripts/build_index.py` | Chunk + FTS5 + BM25 index build |
| `scripts/export_corpus_markdown.py` | Portable markdown archive export |
| `scripts/dev_server.sh` | Local server with a test gate word |

## Never in git

`.env`, the corpus (`master_corpus*.jsonl`), the index (`index/`,
`*.pkl`, `*.db`), session logs (`logs/`), and the name mapping
(`name_mapping_log.json`). See `.gitignore`.
