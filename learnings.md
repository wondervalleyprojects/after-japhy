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
