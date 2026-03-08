"""Quick PostHog connection test — run with: dotenvx run -- uv run python scripts/test_posthog_connection.py"""

import os
import sys

import httpx

api_key = os.getenv("POSTHOG_API_KEY", "")
project_id = os.getenv("POSTHOG_PROJECT_ID", "")
host = os.getenv("POSTHOG_HOST", "https://eu.posthog.com").rstrip("/")

print(f"Host:       {host}")
print(f"Project ID: {project_id or '(empty)'}")
print(f"API Key:    {api_key[:8]}****" if len(api_key) > 8 else f"API Key:    {api_key or '(empty)'}")
print()

if not api_key:
    print("FAIL: POSTHOG_API_KEY is not set")
    sys.exit(1)

if not project_id:
    print("FAIL: POSTHOG_PROJECT_ID is not set")
    sys.exit(1)

headers = {"Authorization": f"Bearer {api_key}"}

# Test 1: Project endpoint
print(f"GET {host}/api/projects/{project_id}/ ...")
try:
    resp = httpx.get(f"{host}/api/projects/{project_id}/", headers=headers, timeout=30.0)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Project name: {data.get('name', '?')}")
        print(f"  Project ID:   {data.get('id', '?')}")
    else:
        print(f"  Response: {resp.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")

print()

# Test 2: Events endpoint
print(f"GET {host}/api/projects/{project_id}/events/?event=$exception&limit=3 ...")
try:
    resp = httpx.get(
        f"{host}/api/projects/{project_id}/events/",
        headers=headers,
        params={"event": "$exception", "limit": 3},
        timeout=30.0,
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        results = data.get("results", [])
        print(f"  Events returned: {len(results)}")
        for evt in results[:3]:
            props = evt.get("properties", {})
            print(f"    - {props.get('$exception_type', '?')}: {props.get('$exception_message', '?')[:80]}")
    else:
        print(f"  Response: {resp.text[:500]}")
except Exception as e:
    print(f"  Error: {e}")
