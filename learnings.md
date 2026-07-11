# After Japhy v2 — Build Learnings

Maintained during development. Logged after each script execution, unexpected result, or design decision change.

---

## 2026-05-15 10:00 Corpus Verification
What happened: verify_corpus.py completed — all sources verified.
Result: Total 75,816 records. All sources within 5% of manifest. No empty content detected.
Impact on architecture: Green light to proceed to Phase 2 (anonymization).

## 2026-05-15 10:15 Phase 2 — Corpus Anonymization Complete
What happened: anonymize_corpus.py processed all 75,816 records with spaCy NER and Victorian name replacement.
Result: 
- 75,816 records processed (100% success rate, no errors)
- 13,732 unique private names identified and mapped to [Initial—] format
- Output: master_corpus_anon.jsonl (53M)
- Mapping log: name_mapping_log.json (396K)
Impact on architecture: Anonymized corpus ready for deployment. All private personal names replaced with initials, while preserving Japhy, public figures, place names, and brands. Green light to proceed to Phase 3 (index build).

## 2026-05-15 10:30 Phase 3 — Index Build Complete
What happened: build_index.py processed master_corpus_anon.jsonl, created 26,860 chunks, built BM25 index.
Result:
- 18,665 records chunked (24.6% of corpus)
- 57,151 records skipped (too short, < 50 words minimum)
- Total chunks created: 26,860
- Average chunk size: 214 words
- SQLite database: 64.0 MB (FTS5 enabled)
- BM25 index: 33.4 MB
- chunks_lookup: 31.1 MB
What fixed it: Short records (tweets, brief notes, email fragments) are skipped; only records ≥50 words chunked. This is acceptable for retrieval — brief records will be filtered during BM25 search anyway.
Impact on architecture: Retrieval index ready. Phase 4 (core Flask application) can now proceed with working BM25 and SQLite.

## 2026-07-11 — Deploy sizing: measure loaded RAM, not disk
What happened: Deployment planning initially feared corpus size (53MB) and index size (128MB). Neither mattered. The BM25 pickle (33MB on disk) inflates to 321MB in RAM — ~450MB total app footprint, 3.5× disk. The old render.yaml's `--workers 2` would have doubled that to ~900MB, past any small host's limit.
What fixed it: Measured RSS directly before choosing a host. Fly.io 1GB machine, 1 gunicorn worker + 4 threads.
Impact on architecture: Host choice (Fly over Render free/starter tiers) driven entirely by the loaded-RAM number. Fallback lever documented: FTS5's native bm25() could replace the pickle and cut RAM to ~60MB if cost ever matters.

## 2026-07-11 — Spend caps expressed as The Stillness
What happened: Turn/daily caps needed a visitor-facing behavior. An error message would break the room.
What fixed it: Cap hit → server returns a non-response (`stillness: true`, empty response, no model call); the client's existing Stillness choreography dims the room. Canon-compliant: the brief lists "simple non-response" as a Stillness trigger, and the model never narrates its own disengagement.
Impact on architecture: Infrastructure limits absorbed into the piece's own disengagement vocabulary. Generalizable to the Remains series.
