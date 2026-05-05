#!/bin/bash

# run_tests.sh: Run the test suite after embedding completes

cd /Users/jeffreyorlinski/Desktop/WVP/Apps/After_Japhy

# Check requirements
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    echo "Set it with: export ANTHROPIC_API_KEY=sk-..."
    exit 1
fi

echo "========================================"
echo "AFTER JAPHY TEST SUITE"
echo "========================================"
echo ""

# Check embedding status
echo "Checking Chroma database status..."
source venv/bin/activate

python3 -c "
import chromadb
try:
    client = chromadb.PersistentClient(path='chroma_db')
    collection = client.get_or_create_collection(name='after_japhy')
    count = collection.count()
    print(f'✅ Chroma database ready with {count:,} chunks')
    if count < 100000:
        print('⚠️  WARNING: Fewer than 100k chunks. Embedding may not be complete.')
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"

echo ""
echo "Running conversation test..."
echo "This will make 5 sequential queries to test the full pipeline."
echo ""

# Run the test
python3 test_chat.py

echo ""
echo "========================================"
echo "TEST COMPLETE"
echo "========================================"
echo ""
echo "Session logs saved to: logs/"
echo "Check BUILD_REPORT.txt for full build statistics"
