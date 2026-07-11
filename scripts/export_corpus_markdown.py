#!/usr/bin/env python3
"""Export the master corpus to plain markdown files.

The corpus is a personal archive first and an index second. This export
makes it readable and portable with no product installed: one markdown
file per source per year, every record carrying a small provenance
header (source, era/date, tier).

Usage:
    python scripts/export_corpus_markdown.py                 # full export
    python scripts/export_corpus_markdown.py --limit 500     # dry run
    python scripts/export_corpus_markdown.py --anon          # anonymized corpus
    python scripts/export_corpus_markdown.py --outdir /path  # custom target

Default input:  master_corpus.jsonl (the source of truth, real names)
Default output: <corpus dir>/corpus_markdown/<source>/<year>.md
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

CORPUS_DIR = Path(
    "/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/After Japhy Corpus/master_corpus"
)

# Tier assignments follow the project brief's corpus section:
# Tier 1 = public voice, no consent issues. Tier 2 = private material
# (sent mail, own posts, notes, drafts) — informs the portrait.
TIER_2_SOURCES = {"gmail_personal", "gmail_wvp", "facebook", "bear_notes", "scrivener"}


def era_of(date_str):
    if not date_str:
        return "undated"
    year = date_str[:4]
    if not year.isdigit():
        return "undated"
    y = int(year)
    if y < 2010:
        return "early 2000s"
    if y < 2020:
        return "2010s"
    return "2020s"


def tier_of(source_name):
    return "2 (private)" if source_name in TIER_2_SOURCES else "1 (public)"


def record_markdown(rec):
    source = rec.get("source_name", "unknown")
    date = rec.get("date") or "undated"
    header = [
        "---",
        f"source: {source}",
        f"date: {date}",
        f"era: {era_of(rec.get('date'))}",
        f"tier: {tier_of(source)}",
        f"id: {rec.get('id', '')[:16]}",
        f"words: {rec.get('word_count', '')}",
    ]
    url = rec.get("url") or ""
    if url:
        header.append(f"url: {url}")
    header.append("---")
    return "\n".join(header) + "\n\n" + (rec.get("content") or "").strip() + "\n\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="export only the first N records (dry run)")
    parser.add_argument("--anon", action="store_true", help="export the anonymized corpus instead of the master")
    parser.add_argument("--outdir", type=Path, default=None, help="output directory override")
    args = parser.parse_args()

    infile = CORPUS_DIR / ("master_corpus_anon.jsonl" if args.anon else "master_corpus.jsonl")
    outdir = args.outdir or (CORPUS_DIR.parent / ("corpus_markdown_anon" if args.anon else "corpus_markdown"))

    if not infile.exists():
        sys.exit(f"Input not found: {infile}")

    # Group records into (source, year) buckets, sorted by date within each
    buckets = {}
    counts = Counter()
    total = 0

    with open(infile) as f:
        for line in f:
            if args.limit is not None and total >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1
            source = rec.get("source_name", "unknown")
            date = rec.get("date") or ""
            year = date[:4] if date[:4].isdigit() else "undated"
            buckets.setdefault((source, year), []).append(rec)
            counts[source] += 1

    outdir.mkdir(parents=True, exist_ok=True)
    files_written = 0
    for (source, year), records in sorted(buckets.items()):
        records.sort(key=lambda r: r.get("date") or "")
        target_dir = outdir / source
        target_dir.mkdir(exist_ok=True)
        with open(target_dir / f"{year}.md", "w") as f:
            f.write(f"# {source} — {year}\n\n")
            for rec in records:
                f.write(record_markdown(rec))
        files_written += 1

    print(f"Input:  {infile}")
    print(f"Output: {outdir}")
    print(f"Records exported: {total}")
    print(f"Files written:    {files_written}")
    for source, n in counts.most_common():
        print(f"  {source}: {n}")


if __name__ == "__main__":
    main()
