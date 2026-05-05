#!/bin/bash
set -e

echo "=== After Japhy RAG Pipeline ==="
echo ""

# Check if Gmail extractions are done
echo "Checking for Gmail extracted files..."
if [ ! -f "gmail_personal_sent.jsonl" ]; then
    echo "ERROR: gmail_personal_sent.jsonl not found. Run extract_gmail_sent.py first."
    exit 1
fi
if [ ! -f "gmail_wvp_sent.jsonl" ]; then
    echo "ERROR: gmail_wvp_sent.jsonl not found. Run extract_gmail_sent.py first."
    exit 1
fi

echo "Step 3: Preprocessing corpus..."
python3 scripts/preprocess_corpus.py
echo ""

echo "Step 4: Chunking corpus..."
python3 scripts/chunk_corpus.py
echo ""

echo "Step 5: Installing dependencies..."
python3 -m pip install --break-system-packages -q chromadb sentence-transformers flask anthropic
echo "Dependencies installed"
echo ""

echo "Step 6: Embedding and loading into Chroma..."
python3 scripts/embed_and_load.py
echo ""

echo "=== Pipeline Complete ==="
echo "You can now run the Flask app with: python3 app.py"
echo "Or run tests with: python3 test_chat.py"
