#!/usr/bin/env python3

import mailbox
import email
import json
import sys
import re
import uuid
from datetime import datetime
from email.utils import parsedate_to_datetime

def strip_quoted_content(text):
    """Remove quoted replies, forwarded content, and signatures."""
    lines = text.split('\n')
    result = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip lines starting with >
        if line.strip().startswith('>'):
            i += 1
            continue

        # Skip quoted blocks starting with "On [date] wrote:"
        if re.match(r'On\s+.+\s+wrote:', line):
            # Skip this line and following quoted lines
            i += 1
            while i < len(lines) and (lines[i].strip().startswith('>') or lines[i].strip() == ''):
                i += 1
            continue

        # Skip forwarded message headers
        if re.match(r'^------+\s*(Forwarded|Original)\s+Message', line, re.IGNORECASE):
            i += 1
            # Skip forwarded header block
            while i < len(lines) and lines[i].strip() != '':
                i += 1
            continue

        # Stop at signature (line with just two dashes)
        if line.strip() == '--':
            break

        result.append(line)
        i += 1

    # Clean up excessive blank lines
    text = '\n'.join(result).strip()
    text = re.sub(r'\n\n\n+', '\n\n', text)
    return text

def extract_text_body(msg):
    """Extract plain text body, falling back to HTML if needed."""
    text_part = None
    html_part = None

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and text_part is None:
                text_part = part.get_payload(decode=True)
                try:
                    return text_part.decode('utf-8', errors='ignore')
                except:
                    pass
            elif part.get_content_type() == 'text/html' and html_part is None:
                html_part = part.get_payload(decode=True)

    if html_part:
        return html_part.decode('utf-8', errors='ignore')

    if text_part is not None:
        return text_part.decode('utf-8', errors='ignore')

    return msg.get_payload(decode=True).decode('utf-8', errors='ignore') if msg.get_payload() else ""

def process_mbox(mbox_path, account_type):
    """Process mbox file and extract sent emails."""
    records = []

    try:
        mbox = mailbox.mboxMessage if hasattr(mailbox, 'mboxMessage') else mailbox.Message
        mailbox_reader = mailbox.mbox(mbox_path)
    except Exception as e:
        print(f"Error opening mbox file: {e}", file=sys.stderr)
        return records

    gmail_labels = "Gmail_Labels" if account_type == "wvp" else "X-Gmail-Labels"

    for i, msg in enumerate(mailbox_reader):
        if i % 5000 == 0:
            print(f"  Processed {i} messages...", file=sys.stderr)

        # Check if message has Sent label
        labels_header = msg.get('X-Gmail-Labels', '')
        if 'Sent' not in labels_header:
            continue

        # Extract fields
        subject = msg.get('Subject', '')
        to_field = msg.get('To', '')
        date_str = msg.get('Date', '')

        # Parse date
        try:
            if date_str:
                dt = parsedate_to_datetime(date_str)
                date = dt.strftime('%Y-%m-%d')
            else:
                date = None
        except:
            date = None

        # Extract body
        body = extract_text_body(msg)
        body = strip_quoted_content(body)
        body = body.strip()

        # Skip if too short
        word_count = len(body.split())
        if word_count < 10:
            continue

        # Create record
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "source_name": "gmail_personal" if account_type == "personal" else "gmail_wvp",
            "date": date,
            "content": body,
            "url": None,
            "word_count": word_count,
            "metadata": {
                "subject": subject,
                "to": to_field
            }
        }
        records.append(record)

    return records

def main():
    if len(sys.argv) < 3:
        print("Usage: extract_gmail_sent.py <mbox_path> <account_type> <output_path>")
        sys.exit(1)

    mbox_path = sys.argv[1]
    account_type = sys.argv[2]
    output_path = sys.argv[3]

    print(f"Extracting sent emails from {mbox_path} ({account_type})...", file=sys.stderr)
    records = process_mbox(mbox_path, account_type)

    print(f"Writing {len(records)} records to {output_path}...", file=sys.stderr)
    with open(output_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    print(f"Done. Extracted {len(records)} sent emails.", file=sys.stderr)

if __name__ == '__main__':
    main()
