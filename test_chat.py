#!/usr/bin/env python3

import subprocess
import time
import requests
import json
import uuid
import sys

def run_test():
    # Start Flask app in background
    print("Starting Flask app...")
    import os as os_module
    import shutil

    # Use venv python if available
    venv_python = shutil.which('python3')
    if os_module.path.exists('venv/bin/python3'):
        venv_python = os_module.path.abspath('venv/bin/python3')

    env = os_module.environ.copy()
    # Ensure ANTHROPIC_API_KEY is available if it was passed to the test
    if 'ANTHROPIC_API_KEY' not in env:
        # Try to get it from the shell environment
        api_key = os_module.getenv('ANTHROPIC_API_KEY')
        if api_key:
            env['ANTHROPIC_API_KEY'] = api_key

    process = subprocess.Popen(
        [venv_python, 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    # Wait for server to start
    time.sleep(5)

    # Check if server is running
    for attempt in range(10):
        try:
            response = requests.get('http://localhost:8000/health', timeout=2)
            data = response.json()
            print(f"✅ Server started. Collection has {data.get('chunks_in_collection', '?')} chunks.\n")
            break
        except Exception as e:
            if attempt < 9:
                time.sleep(1)
                continue
            else:
                print(f"Failed to connect to server after {attempt+1} attempts: {e}")
                process.terminate()
                return False

    # Test messages
    session_id = str(uuid.uuid4())
    messages = [
        "...",
        "What kept coming up for him around 2012?",
        "Can you help me write something?",
        "Did he ever talk about a person named Spencer?",
        "What do you think he was actually afraid of?"
    ]

    history = []
    all_success = True

    for i, message in enumerate(messages):
        print(f"\n{'='*60}")
        print(f"REQUEST {i+1}: {message}")
        print('='*60)

        try:
            response = requests.post(
                'http://localhost:8000/chat',
                json={
                    'message': message,
                    'history': history,
                    'session_id': session_id
                }
            )

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(response.text)
                all_success = False
                continue

            data = response.json()
            response_text = data.get('response', '')
            sources = data.get('sources', [])

            print(f"\nRESPONSE:")
            print(response_text)

            if sources:
                print(f"\nSOURCES:")
                for source in sources:
                    print(f"  - {source['source_name']} ({source['date']})")

            # Add to history for next message
            history.append({'role': 'user', 'content': message})
            history.append({'role': 'assistant', 'content': response_text})

        except Exception as e:
            print(f"Request failed: {e}")
            all_success = False

    # Shutdown
    print(f"\n{'='*60}")
    print("Shutting down Flask app...")
    process.terminate()
    process.wait(timeout=5)
    print("Done.")

    return all_success

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
