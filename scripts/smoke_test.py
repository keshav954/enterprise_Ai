#!/usr/bin/env python3
"""
Container and Deployment Smoke Test for Enterprise AI Employee.
Usage:
    python scripts/smoke_test.py --base-url http://localhost:8000 --api-key <key>
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid


def make_request(url, method="GET", headers=None, data=None):
    req_headers = headers or {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body


def main():
    parser = argparse.ArgumentParser(description="Enterprise AI Employee Smoke Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of application")
    parser.add_argument("--api-key", default="", help="APP_API_KEY for authentication")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    api_key = args.api_key
    auth_headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    print(f"=== Starting Smoke Test against {base_url} ===")

    # 1. Health check (unauthenticated)
    print("\n[1/6] Testing GET /health...")
    status, body = make_request(f"{base_url}/health")
    assert status == 200, f"Expected 200 from /health, got {status}: {body}"
    health_data = json.loads(body)
    assert health_data.get("status") == "healthy", f"Unexpected health status: {health_data}"
    print(f"  PASS: Service is healthy. Model: {health_data.get('model')}")

    # 2. Static dashboard endpoint (unauthenticated)
    print("\n[2/6] Testing GET /dashboard...")
    status, body = make_request(f"{base_url}/dashboard")
    assert status == 200, f"Expected 200 from /dashboard, got {status}"
    assert "<!DOCTYPE html>" in body or "Enterprise AI Employee" in body, "Dashboard HTML missing"
    print("  PASS: Dashboard HTML rendered successfully.")

    # 3. Auth enforcement test (if api-key is configured)
    if api_key:
        print("\n[3/6] Testing Auth Enforcement (expect 401 without key)...")
        status, body = make_request(f"{base_url}/tools")
        assert status == 401, f"Expected 401 Unauthorized for /tools without key, got {status}"
        print("  PASS: Protected endpoint correctly refused unauthenticated request.")

    # 4. List tools
    print("\n[4/6] Testing GET /tools (with authentication)...")
    status, body = make_request(f"{base_url}/tools", headers=auth_headers)
    assert status == 200, f"Expected 200 from /tools, got {status}: {body}"
    tools_data = json.loads(body)
    total_tools = tools_data.get("total_tools", 0)
    assert total_tools >= 30, f"Expected at least 30 registered tools, got {total_tools}"
    print(f"  PASS: {total_tools} tools registered.")

    # 5. Chat Turn & Memory
    sess_id = f"smoke-test-{uuid.uuid4().hex[:12]}"
    print(f"\n[5/6] Testing POST /chat with session {sess_id}...")
    chat_payload = {
        "message": "Smoke test automated ping.",
        "session_id": sess_id,
    }
    status, body = make_request(f"{base_url}/chat", method="POST", headers=auth_headers, data=chat_payload)
    if status == 503:
        print("  NOTICE: /chat returned 503 (Gemini unconfigured in container). Expected if no GEMINI_API_KEY provided.")
    else:
        assert status == 200, f"Expected 200 from /chat, got {status}: {body}"
        chat_data = json.loads(body)
        assert "reply" in chat_data, "Missing reply in chat response"
        print(f"  PASS: Chat completed. Reply snippet: {chat_data['reply'][:60]}...")

        # 6. Session History & Cleanup
        print("\n[6/6] Testing GET /chat/{id}/history and DELETE...")
        h_status, h_body = make_request(f"{base_url}/chat/{sess_id}/history", headers=auth_headers)
        assert h_status == 200, f"Expected 200 from history, got {h_status}"
        del_status, _ = make_request(f"{base_url}/chat/{sess_id}", method="DELETE", headers=auth_headers)
        assert del_status == 200, f"Expected 200 from session delete, got {del_status}"
        print("  PASS: History retrieved and session cleaned up.")

    print("\n==========================================")
    print("  ALL SMOKE CHECKS PASSED SUCCESSFULLY!  ")
    print("==========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())

