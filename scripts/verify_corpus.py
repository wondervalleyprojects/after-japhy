#!/usr/bin/env python3
"""
Verify master_corpus.jsonl against expected manifest.
Reports counts, mismatches, null/empty content, and date coverage.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Expected counts from CLAUDE.md manifest
EXPECTED_COUNTS = {
    "gmail_personal": 25_559,
    "facebook": 21_174,
    "twitter": 13_975,
    "instagram": 3_601,
    "gmail_wvp": 3_133,
    "chatgpt": 3_062,
    "reddit": 1_294,
    "queerty": 1_177,
    "linkedin": 1_068,
    "blog": 925,
    "bear_notes": 659,
    "scrivener": 87,
    "article": 83,
    "youtube": 19,
}

EXPECTED_TOTAL = 75_816

# Paths
CORPUS_PATH = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/After Japhy Corpus/master_corpus/master_corpus.jsonl")
LEARNINGS_PATH = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/AfterJaphy/learnings.md")


def verify_corpus():
    """Main verification."""
    print(f"Loading corpus from: {CORPUS_PATH}")
    print()

    if not CORPUS_PATH.exists():
        print(f"ERROR: Corpus file not found at {CORPUS_PATH}")
        return

    # Track per source
    actual_counts = defaultdict(int)
    empty_content_count = defaultdict(int)
    date_ranges = defaultdict(lambda: {"min": None, "max": None})
    total_records = 0
    mismatches = []

    # Load and analyze
    try:
        with open(CORPUS_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"WARNING: Could not parse JSON line: {line[:100]}")
                    continue

                source = record.get("source_name", "unknown")
                date = record.get("date")
                content = record.get("content", "")

                actual_counts[source] += 1
                total_records += 1

                # Check for null/empty content
                if not content or content.strip() == "":
                    empty_content_count[source] += 1

                # Track date ranges
                if date:
                    try:
                        date_obj = datetime.strptime(date, "%Y-%m-%d")
                        if date_ranges[source]["min"] is None or date_obj < date_ranges[source]["min"]:
                            date_ranges[source]["min"] = date_obj
                        if date_ranges[source]["max"] is None or date_obj > date_ranges[source]["max"]:
                            date_ranges[source]["max"] = date_obj
                    except ValueError:
                        pass  # Skip unparseable dates

    except Exception as e:
        print(f"ERROR reading corpus: {e}")
        return

    print("=" * 100)
    print(f"CORPUS VERIFICATION REPORT")
    print(f"Total records processed: {total_records:,}")
    print(f"Expected total: {EXPECTED_TOTAL:,}")
    print("=" * 100)
    print()

    # Build report
    print(f"{'Source':<20} {'Expected':>12} {'Actual':>12} {'Diff %':>8} {'Status':<15} {'Empty Content':>15}")
    print("-" * 100)

    for source in sorted(EXPECTED_COUNTS.keys()):
        expected = EXPECTED_COUNTS[source]
        actual = actual_counts.get(source, 0)
        empty = empty_content_count.get(source, 0)

        if expected == 0:
            diff_pct = 0
        else:
            diff_pct = ((actual - expected) / expected) * 100

        status = "OK"
        if abs(diff_pct) > 5:
            status = "⚠ MISMATCH"
            mismatches.append({
                "source": source,
                "expected": expected,
                "actual": actual,
                "diff_pct": diff_pct,
            })

        print(f"{source:<20} {expected:>12,} {actual:>12,} {diff_pct:>7.1f}% {status:<15} {empty:>15,}")

    print("-" * 100)
    print()

    # Date coverage report
    print("DATE COVERAGE BY SOURCE:")
    print("-" * 100)
    print(f"{'Source':<20} {'Min Date':<15} {'Max Date':<15}")
    print("-" * 100)
    for source in sorted(EXPECTED_COUNTS.keys()):
        min_date = date_ranges[source]["min"]
        max_date = date_ranges[source]["max"]
        min_str = min_date.strftime("%Y-%m-%d") if min_date else "N/A"
        max_str = max_date.strftime("%Y-%m-%d") if max_date else "N/A"
        print(f"{source:<20} {min_str:<15} {max_str:<15}")
    print()

    # Empty content summary
    print("EMPTY/NULL CONTENT CHECK:")
    print("-" * 100)
    total_empty = sum(empty_content_count.values())
    if total_empty > 0:
        print(f"Total records with empty/null content: {total_empty:,}")
        print()
        for source in sorted(empty_content_count.keys()):
            count = empty_content_count[source]
            if count > 0:
                pct = (count / actual_counts[source]) * 100 if actual_counts[source] > 0 else 0
                print(f"  {source:<20} {count:>8,} ({pct:>5.2f}%)")
    else:
        print("No empty/null content detected.")
    print()

    # Mismatches summary
    if mismatches:
        print("⚠ MISMATCHES (difference > 5%):")
        print("-" * 100)
        for m in mismatches:
            print(f"  {m['source']:<20} Expected: {m['expected']:>8,} | Actual: {m['actual']:>8,} | Diff: {m['diff_pct']:>6.1f}%")
        print()
    else:
        print("✓ All sources within 5% of expected counts.")
        print()

    # Write anomalies to learnings.md
    if mismatches or total_empty > 0:
        log_entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} Corpus Verification\n"
        log_entry += f"What happened: verify_corpus.py ran against master_corpus.jsonl\n"
        log_entry += f"Impact on architecture: Flags any record count discrepancies or data quality issues\n\n"

        if mismatches:
            log_entry += "**Mismatches (> 5% variance):**\n"
            for m in mismatches:
                log_entry += f"- {m['source']}: expected {m['expected']:,}, actual {m['actual']:,} ({m['diff_pct']:+.1f}%)\n"
            log_entry += "\n"

        if total_empty > 0:
            log_entry += f"**Empty/null content detected:** {total_empty:,} records total\n"
            for source in sorted(empty_content_count.keys()):
                count = empty_content_count[source]
                if count > 0:
                    pct = (count / actual_counts[source]) * 100 if actual_counts[source] > 0 else 0
                    log_entry += f"- {source}: {count:,} ({pct:.2f}%)\n"
            log_entry += "\n"

        log_entry += "What fixed it: Continue to Phase 1. Do not rebuild corpus at this time.\n"

        with open(LEARNINGS_PATH, 'a') as f:
            f.write(log_entry)
        print(f"Logged anomalies to {LEARNINGS_PATH}")
    else:
        log_entry = f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} Corpus Verification\n"
        log_entry += f"What happened: verify_corpus.py completed — all sources verified.\n"
        log_entry += f"Result: Total {total_records:,} records. All sources within 5% of manifest. No empty content detected.\n"
        log_entry += f"Impact on architecture: Green light to proceed to Phase 2 (anonymization).\n"
        with open(LEARNINGS_PATH, 'a') as f:
            f.write(log_entry)
        print(f"Logged clean verification to {LEARNINGS_PATH}")


if __name__ == "__main__":
    verify_corpus()
