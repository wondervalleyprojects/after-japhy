#!/usr/bin/env python3
"""
Victorian Name Anonymizer for After Japhy corpus.

Replaces private personal names with [Initial—] format while preserving:
- Japhy and Japhy Grant (the subject)
- Place names, brands, companies
- Famous public figures
- Names in URLs
"""

import json
import spacy
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

# Paths
CORPUS_PATH = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/After Japhy Corpus/master_corpus/master_corpus.jsonl")
OUTPUT_CORPUS_PATH = CORPUS_PATH.parent / "master_corpus_anon.jsonl"
MAPPING_LOG_PATH = Path("/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/AfterJaphy/name_mapping_log.json")

# Famous/public figures safelist (celebrities, politicians, historical figures, authors, musicians, etc.)
FAMOUS_NAMES = {
    # U.S. Presidents & First Families
    "Obama", "Barack",
    "Trump", "Donald",
    "Biden", "Joe", "Joseph",
    "Clinton", "Bill", "Hillary",
    "Bush", "George", "Laura",
    "Carter", "Jimmy", "James",
    "Reagan", "Ronald",
    "Kennedy", "John", "JFK",
    "Lincoln", "Abraham",
    "Washington", "George",
    "Jefferson", "Thomas",
    "Franklin", "Benjamin",

    # 2008 Election & Political figures
    "McCain", "John",
    "Palin", "Sarah",
    "Wright", "Jeremiah",
    "Richardson", "Bill",
    "Spitzer", "Eliot",
    "Rendell", "Ed", "Edward",
    "McAuliffe", "Terry",
    "Heston", "Charlton",
    "Cheney", "Dick", "Richard",
    "Ferraro", "Geraldine",
    "Gore", "Al", "Albert",

    # News & Media personalities
    "Chris", "Matthews",
    "Olbermann", "Keith",
    "Limbaugh", "Rush",
    "Hannity", "Sean",
    "Maddow", "Rachel",
    "Couric", "Katie",
    "Williams", "Brian",
    "Lauer", "Matt",
    "Vieira", "Meredith",
    "Cohen", "Andy",
    "Winfrey", "Oprah",
    "Ellen", "DeGeneres",
    "Letterman", "David",
    "Leno", "Jay",
    "Walters", "Barbara",
    "Serling", "Rod",
    "Russert", "Tim",
    "Carlson", "Tucker",
    "Carville", "James",
    "Begala", "Paul",
    "Blitzer", "Wolf",
    "Brown", "Campbell",
    "Rather", "Dan",
    "Brokaw", "Tom",
    "Rose", "Charlie",
    "Stephanopoulos", "George",
    "Sawyer", "Diane",
    "Gibson", "Charles",
    "Donaldson", "Sam",
    "Robinson", "Eugene",
    "Scarborough", "Joe",
    "Brzezinski", "Mika",

    # Celebrities & Entertainment
    "Lady Gaga", "Gaga", "Germanotta",
    "Beyoncé", "Beyonce",
    "Rihanna",
    "Taylor", "Swift",
    "Kanye", "West",
    "Jay-Z", "Hov",
    "Britney", "Spears",
    "Eminem", "Marshall",
    "Madonna",
    "Prince",
    "David", "Bowie",
    "Michael", "Jackson",
    "Whitney", "Houston",
    "Mariah", "Carey",
    "Springsteen", "Bruce",
    "Jagger", "Mick",
    "Lennon", "John",
    "McCartney", "Paul",
    "Cruise", "Tom",
    "DiCaprio", "Leo", "Leonardo",
    "Pitt", "Brad", "Bradley",
    "Jolie", "Angelina",
    "Kardashian", "Kardashians", "Kim", "Kourtney", "Khloé",
    "Streep", "Meryl",
    "Hanks", "Tom",
    "Spacey", "Kevin",
    "Dempsey", "Patrick",
    "Wilson", "Luke",
    "Zellweger", "Renée", "Renee",
    "Swinton", "Tilda",
    "Warhol", "Andy",
    "Weil", "Kurt",
    "Odets", "Clifford",

    # Musicians
    "Gaga", "Lady",
    "Knowles", "Beyoncé",
    "Sinatra", "Frank",
    "Elvis", "Presley",
    "The Beatles", "Beatles",
    "Parton", "Dolly",
    "Dylan", "Bob",
    "Diamond", "Neil",

    # Authors/Philosophers/Artists
    "Borges", "Jorge Luis",
    "Kerouac", "Jack", "Jean-Louis",
    "Foucault", "Michel",
    "Derrida", "Jacques",
    "Butler", "Judith",
    "Sedgwick", "Eve",
    "Proust", "Marcel",
    "Joyce", "James",
    "Fitzgerald", "F. Scott",
    "Hemingway", "Ernest",
    "Orwell", "George",

    # Tech/Business
    "Jobs", "Steve", "Steven",
    "Musk", "Elon",
    "Gates", "Bill", "William",
    "Zuckerberg", "Mark",
    "Bezos", "Jeff", "Jeffrey",
    "Page", "Larry",
    "Brin", "Sergey",

    # Sports
    "Jordan", "Michael",
    "Brady", "Tom",
    "Federer", "Roger",
    "Woods", "Tiger",

    # Other famous figures
    "Schwarzenegger", "Arnold",
    "Stallone", "Sylvester",
    "Willis", "Bruce",
    "Gibson", "Mel",
    "Ford", "Harrison",
    "Spielberg", "Steven",
    "Scorsese", "Martin",
    "Tarantino", "Quentin",
    "Cameron", "James",
}

# Common place names to preserve
PLACE_NAMES = {
    "Los Angeles", "LA",
    "New York", "NYC",
    "San Francisco", "SF",
    "Las Vegas",
    "Chicago",
    "Miami",
    "Boston",
    "Seattle",
    "Portland",
    "Denver",
    "Austin",
    "Austin",
    "Nashville",
    "London",
    "Paris",
    "Berlin",
    "Tokyo",
    "Bangkok",
    "Mexico",
    "Canada",
    "Europe",
    "America",
    "California",
    "Texas",
    "New York",
    "Florida",
    "Washington",
    "Oregon",
    "Nevada",
    "Utah",
    "Arizona",
    "Colorado",
    "Hawaii",
    "Wonder Valley",  # Specifically preserve this one
}

# Brand/company names to preserve
BRAND_NAMES = {
    "Google",
    "Apple",
    "Facebook", "Meta",
    "Amazon",
    "Twitter", "X",
    "Instagram",
    "TikTok",
    "YouTube",
    "Netflix",
    "Spotify",
    "Slack",
    "Zoom",
    "Microsoft",
    "Tesla",
    "OpenAI",
    "Anthropic",
    "ChatGPT",
    "GPT",
    "Logo",
    "Equinox",
    "Technorati",
    "Adidas",
    "Nike",
    "Prada",
    "Gucci",
    "CNN",
    "BBC",
    "NBC",
    "ABC",
    "CBS",
    "Fox",
    "PBS",
    "HBO",
    "Showtime",
    "Bravo",
}

# Subject preservation
SUBJECT_NAMES = {"Japhy", "Grant"}


def build_safelist():
    """Combine all preserved names into one safelist."""
    safelist = set()
    safelist.update(FAMOUS_NAMES)
    safelist.update(PLACE_NAMES)
    safelist.update(BRAND_NAMES)
    safelist.update(SUBJECT_NAMES)
    return safelist


def should_preserve_name(name, safelist, url=""):
    """Decide if a name should be preserved."""
    name_clean = name.strip()

    # Exact matches in safelist
    if name_clean in safelist:
        return True

    # Check for multi-word matches (e.g., "Lady Gaga")
    for safe_name in safelist:
        if safe_name.lower() in name_clean.lower():
            return True

    # Preserve if name appears in URL
    if url and name_clean in url:
        return True

    # Preserve "Japhy" and "Japhy Grant" explicitly
    if "Japhy" in name_clean:
        return True

    return False


def extract_names_from_content(nlp, content):
    """Use spaCy to extract PERSON entities."""
    doc = nlp(content)
    names = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            names.append(ent.text)
    return names


def anonymize_name(name, mapping):
    """
    Convert name to [Initial—] format, maintaining consistency.
    Returns (anonymized_form, was_new_mapping).
    """
    name_lower = name.lower()

    if name_lower in mapping:
        return mapping[name_lower], False

    # Generate [X—] where X is first letter of first word
    first_letter = name[0].upper() if name else "?"
    anon_form = f"[{first_letter}—]"
    mapping[name_lower] = anon_form
    return anon_form, True


def anonymize_content(content, names_to_replace, mapping, safelist, url=""):
    """
    Replace names in content with anonymized forms.
    Handle case-insensitive matching while preserving some context.
    """
    result = content
    replacements_made = []

    for name in names_to_replace:
        if not name or len(name.strip()) == 0:
            continue

        # Check if should preserve
        if should_preserve_name(name, safelist, url):
            continue

        # Get anonymized form
        anon_form, _ = anonymize_name(name, mapping)

        # Replace in content (case-insensitive, word boundaries)
        # Use word boundary to avoid partial matches
        pattern = r'\b' + re.escape(name) + r'\b'
        before = result
        result = re.sub(pattern, anon_form, result, flags=re.IGNORECASE)

        if before != result:
            replacements_made.append((name, anon_form))

    return result, replacements_made


def anonymize_corpus(max_records=None, dry_run=False):
    """
    Main anonymization process.
    If max_records is set, only process that many.
    If dry_run is True, don't write output.
    """
    print("Loading spaCy model...")
    nlp = spacy.load("en_core_web_sm")

    safelist = build_safelist()
    name_mapping = {}  # {name_lower: "[X—]"}
    name_frequency = Counter()  # Track how often each name appears
    anonymized_records = []
    records_processed = 0

    print(f"Processing corpus from {CORPUS_PATH}...")
    print()

    if not CORPUS_PATH.exists():
        print(f"ERROR: Corpus not found at {CORPUS_PATH}")
        return

    try:
        with open(CORPUS_PATH, 'r') as f:
            for line in f:
                if max_records and records_processed >= max_records:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"WARNING: Could not parse JSON")
                    continue

                # Extract entities from content
                content = record.get("content", "")
                url = record.get("url", "")

                if content:
                    names = extract_names_from_content(nlp, content)

                    # Track frequency
                    for name in names:
                        if not should_preserve_name(name, safelist, url):
                            name_frequency[name.lower()] += 1

                    # Anonymize
                    anonymized_content, replacements = anonymize_content(
                        content, names, name_mapping, safelist, url
                    )
                    record["content"] = anonymized_content

                anonymized_records.append(record)
                records_processed += 1

                if (records_processed + 1) % 100 == 0:
                    print(f"  Processed {records_processed} records...")

    except Exception as e:
        print(f"ERROR: {e}")
        return

    print(f"\nProcessed {records_processed} records total.")
    print(f"Unique names mapped: {len(name_mapping)}")
    print()

    # Write output if not dry run
    if not dry_run:
        print(f"Writing anonymized corpus to {OUTPUT_CORPUS_PATH}...")
        with open(OUTPUT_CORPUS_PATH, 'w') as f:
            for record in anonymized_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"✓ Wrote {records_processed} records to {OUTPUT_CORPUS_PATH}")

        # Write mapping log
        print(f"Writing name mapping log to {MAPPING_LOG_PATH}...")
        mapping_log = {
            "timestamp": datetime.now().isoformat(),
            "records_processed": records_processed,
            "unique_names_mapped": len(name_mapping),
            "name_mapping": name_mapping,
            "name_frequency": dict(name_frequency.most_common(100))  # Top 100 by frequency
        }
        with open(MAPPING_LOG_PATH, 'w') as f:
            json.dump(mapping_log, f, indent=2, ensure_ascii=False)
        print(f"✓ Wrote mapping log to {MAPPING_LOG_PATH}")

    return {
        "records": anonymized_records,
        "mapping": name_mapping,
        "frequency": name_frequency,
        "records_processed": records_processed
    }


def print_samples(result, num_samples=10):
    """Print before/after samples for review."""
    print()
    print("=" * 100)
    print(f"SAMPLE ANONYMIZATIONS (showing {num_samples} random records)")
    print("=" * 100)
    print()

    # Reload original corpus to show before/after
    original_records = {}
    with open(CORPUS_PATH, 'r') as f:
        for i, line in enumerate(f):
            if i >= len(result["records"]):
                break
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    original_records[i] = record
                except:
                    pass

    # Show samples
    import random
    sample_indices = random.sample(range(len(result["records"])), min(num_samples, len(result["records"])))

    for idx, orig_idx in enumerate(sample_indices, 1):
        if orig_idx not in original_records:
            continue

        orig = original_records[orig_idx]
        anon = result["records"][orig_idx]

        print(f"Sample {idx}:")
        print(f"  Source: {orig.get('source_name')} | Date: {orig.get('date')}")
        print(f"  BEFORE: {orig.get('content', '')[:150]}...")
        print(f"  AFTER:  {anon.get('content', '')[:150]}...")
        print()


def print_top_names(result, num_names=30):
    """Print top N names being anonymized by frequency."""
    print()
    print("=" * 100)
    print(f"TOP {num_names} NAMES BEING ANONYMIZED (by frequency in {result['records_processed']} records)")
    print("=" * 100)
    print()

    top = result["frequency"].most_common(num_names)
    print(f"{'Rank':<5} {'Name':<30} {'Count':<10} {'Anonymized To':<15}")
    print("-" * 60)

    for rank, (name, count) in enumerate(top, 1):
        anon_form = result["mapping"].get(name, "?")
        print(f"{rank:<5} {name:<30} {count:<10} {anon_form:<15}")

    print()


if __name__ == "__main__":
    import sys

    # Parse arguments
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    max_records = 500 if (dry_run or "--sample" in sys.argv) else None

    if dry_run or "--sample" in sys.argv:
        print(f"DRY RUN MODE - Processing first {max_records} records only")
        print()

    result = anonymize_corpus(max_records=max_records, dry_run=dry_run)

    if result:
        print_samples(result, num_samples=10)
        print_top_names(result, num_names=30)

        if dry_run:
            print("DRY RUN COMPLETE - No files written.")
            print("Review the samples and top names above, then run with --full to process entire corpus.")
        else:
            print("Anonymization complete!")
