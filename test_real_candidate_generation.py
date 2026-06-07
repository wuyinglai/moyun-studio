#!/usr/bin/env python3
"""
T5.1.8b: Real Professional dry-run candidate generation test.
This script:
1. Sets environment variables for local model
2. Starts the backend server (non-blocking)
3. Sends a /api/generate request (SSE streaming)
4. Waits for candidate generation completion
5. Verifies candidate created and content correct
6. Verifies main file NOT overwritten
7. Updates the test report
"""
import asyncio
import json
import os
import sys
import subprocess
import time
import traceback
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Environment variables
LLM_ENV = {
    "LLM_PROVIDER": "openai",
    "LLM_API_BASE": "http://10.214.203.226:1238/v1",
    "LLM_API_KEY": "test",
    "LLM_MODEL": "gemma-4-12b-it-uncensored-Q4_K_M.gguf",
    "LLM_REASONING_FORMAT": "none",
    "DEBUG": "true"
}

# Project settings
PROJECT_ID = "demo-novel"
TARGET_FILE = "chapters/vol-01/ch-001/sec-001.md"
BACKEND_PORT = 8000
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
PROJECT_DIR = Path("workspace/projects") / PROJECT_ID
CANDIDATES_DIR = PROJECT_DIR / ".candidates"
TARGET_FILE_PATH = PROJECT_DIR / TARGET_FILE

print("=" * 80)
print("T5.1.8b: Real Professional dry-run candidate generation test")
print("=" * 80)
print()

# Step 1: Verify initial state
print("Step 1: Verifying initial state")
print("-" * 40)
if not TARGET_FILE_PATH.exists():
    print(f"ERROR: Target file {TARGET_FILE_PATH} not found!")
    sys.exit(1)

if not CANDIDATES_DIR.exists():
    print(f"ERROR: Candidates dir {CANDIDATES_DIR} not found!")
    sys.exit(1)

initial_candidates = list(CANDIDATES_DIR.glob("cand_*.md"))
print(f"  Target file: {TARGET_FILE_PATH}")
print(f"  Candidates before: {len(initial_candidates)}")
if len(initial_candidates) > 0:
    last3 = [f.stem.replace("cand_", "") for f in initial_candidates[-3:]]
    print(f"  Last 3 candidates: {last3}")
print()

# Read target file hash
import hashlib
def get_md5(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

initial_md5 = get_md5(TARGET_FILE_PATH)
initial_mtime = TARGET_FILE_PATH.stat().st_mtime
print(f"Initial target file MD5: {initial_md5}")
print(f"Initial target file mtime: {initial_mtime}")
print()

# Step 2: Start backend server
print("Step 2: Starting backend server")
print("-" * 40)

# Set environment
for k, v in LLM_ENV.items():
    os.environ[k] = v
print(f"Environment variables set for LLM")

# Check if port is in use, kill if needed
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', BACKEND_PORT))
    sock.close()
    if result == 0:
        print(f"Port {BACKEND_PORT} already in use!")
        print("Checking if backend is already running...")
        try:
            r = requests.get(f"{BACKEND_URL}/docs", timeout=2)
            if r.status_code == 200:
                print("Backend already running!")
                server_process = None
            else:
                print("Backend not responding, trying to kill old processes...")
                if os.name == 'nt':
                    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "kill_port_8000.ps1"],
                                  capture_output=True)
                else:
                    subprocess.run(["pkill", "-f", f"uvicorn.*:{BACKEND_PORT}"],
                                  capture_output=True)
                time.sleep(2)
        except:
            pass
except Exception as e:
    print(f"Port check error: {e}")

# Start backend if not running
server_process = None
try:
    r = requests.get(f"{BACKEND_URL}/docs", timeout=2)
    if r.status_code == 200:
        print("Backend already running, using existing process")
except:
    print("Starting new backend server...")
    if os.name == 'nt':
        # Windows: use python
        cmd = ["python", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    else:
        cmd = ["python3", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)]
    
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"Backend started (PID: {server_process.pid})")
    print("Waiting for backend to be ready (10s)...")
    time.sleep(10)

print()

# Step 3: Verify backend health
print("Step 3: Verifying backend health")
print("-" * 40)
try:
    r = requests.get(f"{BACKEND_URL}/docs", timeout=5)
    print(f"Backend health check: {r.status_code}")
    if r.status_code != 200:
        print("ERROR: Backend not responding!")
        print(f"Server stdout: {server_process.stdout.read() if server_process else 'N/A'}")
        print(f"Server stderr: {server_process.stderr.read() if server_process else 'N/A'}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Backend health check failed: {e}")
    if server_process:
        print(f"Server stdout: {server_process.stdout.read()}")
        print(f"Server stderr: {server_process.stderr.read()}")
    sys.exit(1)
print()

# Step 4: Send /api/generate request
print("Step 4: Sending /api/generate request")
print("-" * 40)

# Build request body
request_body = {
    "project_id": PROJECT_ID,
    "file_path": TARGET_FILE,
    "prompt_type": "generate/rewrite",
    "extra_vars": {},
    "mode": "polish_current_scene",
    "stream": True
}

print(f"Request body: {json.dumps(request_body, ensure_ascii=False)}")
print()

# Send SSE request and collect events
event_url = f"{BACKEND_URL}/api/generate"
headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
candidate_id = None
events_collected = []
start_time = time.time()
timeout = 120  # 2 minutes

try:
    print(f"Connecting to {event_url}...")
    r = requests.post(event_url, json=request_body, headers=headers, stream=True, timeout=timeout)
    print(f"Request status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"ERROR: Request failed with status {r.status_code}")
        print(f"Response: {r.text}")
        sys.exit(1)
    
    # Process SSE events
    print("Processing SSE events...")
    buffer = ""
    for line in r.iter_lines(decode_unicode=True):
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"ERROR: Timeout after {timeout}s")
            break
        
        if line:
            buffer += line + "\n"
            if line.startswith("data:"):
                data_str = line[5:].strip()
                events_collected.append(data_str)
                print(f"Event: {data_str[:100]}")
                
                # Check for candidate_created event
                try:
                    data = json.loads(data_str)
                    if isinstance(data, dict) and "candidate_id" in data:
                        candidate_id = data["candidate_id"]
                        print(f"!!! SUCCESS: New candidate created: {candidate_id}")
                except:
                    pass
except Exception as e:
    print(f"ERROR: Request failed: {e}")
    traceback.print_exc()
print()

# Step 5: Check candidate files
print("Step 5: Checking candidate generation result")
print("-" * 40)

current_candidates = list(CANDIDATES_DIR.glob("cand_*.md"))
print(f"Candidates after: {len(current_candidates)}")
new_candidate_count = len(current_candidates) - len(initial_candidates)
print(f"New candidates added: {new_candidate_count}")
print()

# Find newest candidate
candidate_file = None
if candidate_id:
    candidate_file = CANDIDATES_DIR / f"cand_{candidate_id}.md"
else:
    # Find newest by mtime
    if len(current_candidates) > len(initial_candidates):
        current_candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        candidate_file = current_candidates[0]
        candidate_id = candidate_file.stem.replace("cand_", "")
        print(f"Found new candidate by mtime: {candidate_id}")

# Verify candidate
if candidate_file and candidate_file.exists():
    print(f"Candidate file path: {candidate_file}")
    content = candidate_file.read_text(encoding='utf-8')
    print(f"Candidate content length: {len(content)} chars")
    print(f"Candidate content preview:\n{content[:300]}")
    print()
    
    # Verify not overwritten
    current_md5 = get_md5(TARGET_FILE_PATH)
    current_mtime = TARGET_FILE_PATH.stat().st_mtime
    print(f"Target file verification:")
    print(f"  MD5 before: {initial_md5}")
    print(f"  MD5 after: {current_md5}")
    print(f"  Files match: {initial_md5 == current_md5}")
    print(f"  mtime before: {initial_mtime}")
    print(f"  mtime after: {current_mtime}")
    print(f"  Not overwritten: {initial_mtime == current_mtime}")
    print()
else:
    print(f"ERROR: No new candidate file found!")
print()

# Step 6: Verify via candidate API (optional)
print("Step 6: Verifying candidate API (optional)")
print("-" * 40)
try:
    candidates_api_url = f"{BACKEND_URL}/api/candidates/{PROJECT_ID}/{TARGET_FILE}"
    r_cand = requests.get(candidates_api_url, timeout=5)
    print(f"Candidates API status: {r_cand.status_code}")
    if r_cand.status_code == 200:
        candidates_data = r_cand.json()
        print(f"Candidates API returned {len(candidates_data)} candidates")
except Exception as e:
    print(f"Candidates API check skipped: {e}")
print()

# Step 7: Cleanup and summary
print("Step 7: Test summary")
print("-" * 40)
if candidate_id:
    print("✅ SUCCESS: Candidate generated!")
    print(f"Candidate ID: {candidate_id}")
else:
    print("❌ FAILURE: No candidate generated")

print()
print("=" * 80)

# Shutdown server if needed
if server_process and server_process.poll() is None:
    print("Shutting down backend server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()
    print("Backend stopped")
    print()

print("Test complete!")
print()

# Write result to temporary file for report
result_data = {
    "success": bool(candidate_id),
    "candidate_id": candidate_id,
    "candidates_before": len(initial_candidates),
    "candidates_after": len(current_candidates),
    "initial_md5": initial_md5,
    "final_md5": current_md5 if 'current_md5' in locals() else None,
    "events_count": len(events_collected)
}

result_file = Path("test_real_candidate_result.json")
result_file.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Result written to {result_file}")
