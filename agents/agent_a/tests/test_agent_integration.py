import subprocess
import sys
import time
import os

import pytest

def test_launch_agent_b_and_wait_ready():
    agent_b_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../agent_b/agent.py'))
    
    # Start agent_b as a subprocess
    proc = subprocess.Popen(
        [sys.executable, agent_b_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=os.environ.copy(),
    )

    try:
        # Wait for 'Waiting for messages...' in output (max 10 seconds)
        ready = False
        start = time.time()
        while time.time() - start < 10:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            print(f"[agent_b output] {line.strip()}")
            if "Waiting for messages..." in line:
                ready = True
                break
        assert ready, "agent_b did not become ready in time"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill() 