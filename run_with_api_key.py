#!/usr/bin/env python3

import os
import sys

# Set API key from command line or environment
api_key = "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"
os.environ['ANTHROPIC_API_KEY'] = api_key

# Now run the test
from test_chat import run_test
success = run_test()
sys.exit(0 if success else 1)
