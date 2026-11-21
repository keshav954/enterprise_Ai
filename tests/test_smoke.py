"""
Smoke test runner test: verifies that scripts/smoke_test.py runs cleanly against the application.
"""
import os
import socket
import subprocess
import sys
import time

import pytest


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_smoke_test_script_execution():
    port = get_free_port()
    api_key = "smoke-test-key-999"

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["HOST"] = "127.0.0.1"
    env["APP_API_KEY"] = api_key
    env["GEMINI_FAKE"] = "1"
    env["ENV"] = "development"

    # Start uvicorn server in subprocess
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait up to 10 seconds for server to bind
    ready = False
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                ready = True
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)

    if not ready:
        proc.terminate()
        pytest.fail("Test server failed to start within 10 seconds")

    try:
        # Run scripts/smoke_test.py against the live local server
        res = subprocess.run(
            [
                sys.executable,
                "scripts/smoke_test.py",
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--api-key",
                api_key,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        print("Smoke test stdout:\n", res.stdout)
        print("Smoke test stderr:\n", res.stderr)
        assert res.returncode == 0, f"Smoke test failed with return code {res.returncode}:\n{res.stdout}\n{res.stderr}"
        assert "ALL SMOKE CHECKS PASSED SUCCESSFULLY!" in res.stdout
    finally:
        proc.terminate()
        proc.wait(timeout=5)
