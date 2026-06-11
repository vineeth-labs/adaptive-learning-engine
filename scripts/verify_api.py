#!/usr/bin/env python3
import asyncio
import sys
import uuid
import httpx
from backend.main import app

async def main():
    print("Initializing API verification tests...")
    
    # httpx no longer accepts the `app=` keyword in AsyncClient in newer versions.
    # Use ASGITransport to run the FastAPI/Starlette `app` in-process for tests.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Test 1: Health check
        print("Testing: GET /health")
        response = await client.get("/health")
        if response.status_code != 200:
            print(f"FAIL: Health check returned status {response.status_code}", file=sys.stderr)
            sys.exit(1)
        print("PASS: Health check returned 200 OK")
        
        # Test 2: Get list of domains
        print("\nTesting: GET /api/v1/domains")
        response = await client.get("/api/v1/domains")
        if response.status_code != 200:
            print(f"FAIL: /api/v1/domains returned status {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            sys.exit(1)
        
        domains = response.json()
        print(f"PASS: /api/v1/domains returned {len(domains)} domain(s)")
        for d in domains:
            print(f"  - Domain ID: {d['id']}, Name: '{d['name']}', Version: '{d['version']}'")
            
        if not domains:
            print("FAIL: No domains found in database. Cannot run concept tests.", file=sys.stderr)
            sys.exit(1)
            
        target_domain_id = domains[0]["id"]
        
        # Test 3: Get concepts for valid domain
        print(f"\nTesting: GET /api/v1/domains/{target_domain_id}/concepts")
        response = await client.get(f"/api/v1/domains/{target_domain_id}/concepts")
        if response.status_code != 200:
            print(f"FAIL: GET concepts returned status {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            sys.exit(1)
            
        concepts = response.json()
        print(f"PASS: Returned {len(concepts)} concepts for domain '{domains[0]['name']}'")
        if concepts:
            print("Example concept:")
            print(f"  - ID: {concepts[0]['id']}")
            print(f"  - Name: '{concepts[0]['name']}'")
            print(f"  - Path: '{concepts[0]['path']}'")
            print(f"  - Difficulty: {concepts[0]['difficulty']}")
            print(f"  - Metadata: {concepts[0]['metadata']}")
            
        # Test 4: Get concepts for non-existent domain
        fake_id = str(uuid.uuid4())
        print(f"\nTesting: GET /api/v1/domains/{fake_id}/concepts (Non-existent)")
        response = await client.get(f"/api/v1/domains/{fake_id}/concepts")
        if response.status_code != 404:
            print(f"FAIL: GET concepts for fake domain returned status {response.status_code} (expected 404)", file=sys.stderr)
            sys.exit(1)
        print("PASS: Correctly returned 404 for non-existent domain")

    print("\nAPI VERIFICATION SUCCESSFUL!")

if __name__ == "__main__":
    asyncio.run(main())
