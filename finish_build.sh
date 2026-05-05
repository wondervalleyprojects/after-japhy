#!/bin/bash
set -e

cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy

echo "Waiting for WVP Gmail extraction to complete..."
while [ ! -f gmail_wvp_sent.jsonl ] || pgrep -f "extract_gmail_sent" > /dev/null; do
    sleep 5
done

echo ""
echo "=== Gmail Extraction Complete ==="
wc -l gmail_*.jsonl
echo ""

echo "Step 3: Preprocessing corpus..."
source venv/bin/activate
python3 scripts/preprocess_corpus.py
echo ""

echo "Step 4: Chunking corpus..."
python3 scripts/chunk_corpus.py
echo ""

echo "Step 6: Embedding and loading into Chroma..."
python3 scripts/embed_and_load.py
echo ""

echo "=== Build Complete ==="
echo ""
echo "To start the Flask server, run:"
echo "  cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy"
echo "  source venv/bin/activate"
echo "  ANTHROPIC_API_KEY=your_key python3 app.py"
echo ""
echo "Or to run tests (after setting ANTHROPIC_API_KEY):"
echo "  python3 test_chat.py"
