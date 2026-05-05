#!/usr/bin/env python3

import json
import re
from collections import defaultdict
from datetime import datetime

COMMON_FIRST_NAMES = {
    'james', 'john', 'robert', 'michael', 'william', 'david', 'richard', 'joseph', 'charles', 'thomas',
    'christopher', 'daniel', 'matthew', 'anthony', 'mark', 'donald', 'steven', 'paul', 'andrew', 'joshua',
    'kenneth', 'kevin', 'brian', 'george', 'edward', 'ronald', 'timothy', 'jason', 'jeffrey', 'ryan',
    'jacob', 'gary', 'nicholas', 'eric', 'jonathan', 'stephen', 'larry', 'justin', 'scott', 'brandon',
    'benjamin', 'samuel', 'raymond', 'gregory', 'alexander', 'patrick', 'frank', 'dennis', 'jerry', 'tyler',
    'aaron', 'jose', 'adam', 'henry', 'douglas', 'zachary', 'peter', 'kyle', 'walter', 'harold',
    'carlos', 'mary', 'patricia', 'jennifer', 'linda', 'barbara', 'elizabeth', 'susan', 'jessica', 'sarah',
    'karen', 'nancy', 'betty', 'margaret', 'sandra', 'ashley', 'kimberly', 'emily', 'donna', 'michelle',
    'dorothy', 'carol', 'amanda', 'melissa', 'deborah', 'stephanie', 'rebecca', 'sharon', 'laura', 'cynthia',
    'kathleen', 'amy', 'angela', 'shirley', 'anna', 'brenda', 'pamela', 'emma', 'nicole', 'helen',
    'samantha', 'katherine', 'christine', 'debra', 'rachel', 'catherine', 'carolyn', 'janet', 'ruth', 'maria',
    'heather', 'diane', 'virginia', 'julie', 'joyce', 'victoria', 'kelly', 'christina', 'joan', 'evelyn',
    'judith', 'megan', 'andrea', 'cheryl', 'hannah', 'jacqueline', 'martha', 'gloria', 'teresa', 'ann',
    'ann', 'sara', 'madison', 'frances', 'kathryn', 'janice', 'jean', 'alice', 'abigail', 'olivia',
    'sophia', 'isabella', 'ava', 'mia', 'harper', 'amelia', 'emily', 'elizabeth', 'charlotte', 'avery',
    'spencer', 'liam', 'noah', 'oliver', 'elijah', 'james', 'benjamin', 'lucas', 'henry', 'alexander',
    'jane', 'charlotte', 'anne', 'margaret', 'helen', 'louise', 'catherine', 'virginia', 'marie', 'claire',
}

PROTECTED_NAMES = {
    'japhy', 'grant', 'jeffrey', 'orlinski',
    'barack', 'obama', 'hillary', 'clinton', 'trump', 'biden', 'bernie', 'sanders', 'kamala', 'harris',
    'rachel', 'maddow', 'anderson', 'cooper', 'jake', 'tapper',
    'beyonce', 'kanye', 'taylor', 'swift', 'rihanna', 'madonna',
    'octavia', 'butler', 'ursula', 'borges', 'nabokov',
    'elon', 'musk', 'zuckerberg', 'gates', 'jobs',
    'jesus', 'buddha', 'lincoln', 'martin', 'luther', 'eleanor', 'roosevelt'
}

def anonymize_names(text):
    """Replace first names with initial and em-dash."""
    words = text.split()
    result = []

    for word in words:
        # Remove punctuation for checking
        clean_word = word.lower().strip('.,!?;:\'"')

        # Check if it's a protected name
        if clean_word in PROTECTED_NAMES:
            result.append(word)
        # Check if it's a common first name
        elif clean_word in COMMON_FIRST_NAMES:
            # Preserve original capitalization
            if word[0].isupper():
                replacement = word[0] + '—'
            else:
                replacement = word[0].lower() + '—'
            # Handle punctuation
            trailing = ''.join(c for c in word[len(word.rstrip('.,!?;:\'"')):])
            result.append(replacement + trailing)
        else:
            result.append(word)

    return ' '.join(result)

def filter_wvp_gmail(content, metadata):
    """Filter out financial content from WVP gmail."""
    financial_terms = [
        'invoice', 'payment', 'statement of work', 'sow', 'retainer', 'hourly rate',
        'bank account', 'routing number', 'wire transfer', 'net 30', 'net 60'
    ]

    # Check subject
    subject = metadata.get('subject', '').lower()
    for term in financial_terms:
        if term in subject:
            return False

    # Check content
    content_lower = content.lower()
    for term in financial_terms:
        if term in content_lower:
            return False

    # Check for dollar amounts > 500
    dollar_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
    matches = re.findall(dollar_pattern, content)
    for match in matches:
        amount = float(match.replace(',', ''))
        if amount > 500:
            return False

    return True

def drop_received_facebook_messages(record):
    """Drop Facebook messages Japhy received."""
    if record['source_name'] != 'facebook':
        return True

    context = record.get('metadata', {}).get('context', '')
    if context.startswith('From:'):
        return False

    return True

def filter_queerty(content):
    """Remove Queerty-specific patterns."""
    lines = content.split('\n')
    result = []

    for line in lines:
        # Skip reader tip lines
        if re.match(r'^\s*Reader\s+\w+\s+tells\s+us', line, re.IGNORECASE):
            continue
        # Skip [flv: and [youtube
        if '[flv:' in line or '[youtube' in line:
            continue
        # Skip bare URLs
        if re.match(r'^\s*https?://\S+\s*$', line):
            continue
        # Skip "via @" lines
        if re.match(r'^\s*via\s+@\w+', line):
            continue

        result.append(line)

    return '\n'.join(result).strip()

def get_time_period(date_str):
    """Determine time period from date."""
    if not date_str:
        return 'unknown'

    try:
        year = int(date_str.split('-')[0])
        if year < 2010:
            return 'early_2000s'
        elif year < 2020:
            return 'the_2010s'
        else:
            return 'recent'
    except:
        return 'unknown'

def main():
    print("Loading master_corpus.jsonl...")
    master_records = []
    with open('master_corpus.jsonl') as f:
        for line in f:
            master_records.append(json.loads(line))

    print(f"Loaded {len(master_records)} records from master_corpus.jsonl")

    print("Loading gmail_personal_sent.jsonl...")
    try:
        with open('gmail_personal_sent.jsonl') as f:
            for line in f:
                master_records.append(json.loads(line))
        print(f"Added personal Gmail sent records")
    except FileNotFoundError:
        print("gmail_personal_sent.jsonl not found, skipping")

    print("Loading gmail_wvp_sent.jsonl...")
    try:
        with open('gmail_wvp_sent.jsonl') as f:
            for line in f:
                master_records.append(json.loads(line))
        print(f"Added WVP Gmail sent records")
    except FileNotFoundError:
        print("gmail_wvp_sent.jsonl not found, skipping")

    total_in = len(master_records)
    print(f"Total records before filtering: {total_in}")

    # Apply filters
    filtered_records = []
    drop_reasons = defaultdict(int)

    for record in master_records:
        source = record.get('source_name')
        content = record.get('content', '')
        metadata = record.get('metadata', {})

        # Filter WVP gmail
        if source == 'gmail_wvp' and not filter_wvp_gmail(content, metadata):
            drop_reasons['wvp_gmail_financial'] += 1
            continue

        # Filter received Facebook messages
        if not drop_received_facebook_messages(record):
            drop_reasons['facebook_received'] += 1
            continue

        # Apply Queerty filtering
        if source == 'queerty':
            content = filter_queerty(content)

        # Apply name anonymization
        if source in ['gmail_personal', 'gmail_wvp', 'bear_notes'] or \
           (source == 'facebook' and metadata.get('facebook_source_type') == 'facebook_message'):
            content = anonymize_names(content)
            record['content_anonymized'] = True
        else:
            record['content_anonymized'] = False

        # Update content
        record['content'] = content

        # Add time_period
        record['time_period'] = get_time_period(record.get('date'))

        # Skip empty content
        if not content or not content.strip():
            drop_reasons['empty_content'] += 1
            continue

        filtered_records.append(record)

    # Write output
    print(f"Writing {len(filtered_records)} records to corpus_clean.jsonl...")
    with open('corpus_clean.jsonl', 'w') as f:
        for record in filtered_records:
            f.write(json.dumps(record) + '\n')

    # Report
    print(f"\n=== PREPROCESSING REPORT ===")
    print(f"Total records in: {total_in}")
    print(f"Total records out: {len(filtered_records)}")
    print(f"Records dropped: {total_in - len(filtered_records)}")
    print(f"\nDrop reasons:")
    for reason, count in sorted(drop_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    # Breakdown by source
    print(f"\nBreakdown by source_name:")
    source_counts = defaultdict(int)
    for record in filtered_records:
        source_counts[record['source_name']] += 1

    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")

    # Breakdown by time_period
    print(f"\nBreakdown by time_period:")
    time_counts = defaultdict(int)
    for record in filtered_records:
        time_counts[record['time_period']] += 1

    for period, count in sorted(time_counts.items()):
        print(f"  {period}: {count}")

if __name__ == '__main__':
    main()
