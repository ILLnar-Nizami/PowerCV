"""Debug script to inspect 500 error responses."""
from app.main import app
from bson.objectid import ObjectId
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, "/home/illnar/Projects/PowerCV")


client = TestClient(app)

# Test 1: test_comp_opt
print("=" * 80)
print("TEST: test_comp_opt")
print("=" * 80)
response = client.post(
    "/api/comprehensive/optimize/master",
    json={"target_role": "R", "job_description": "J", "resume_text": "R"},
)
print(f"Status: {response.status_code}")
print(f"Response body: {response.text}")
print()

# Test 2: test_create_cl
print("=" * 80)
print("TEST: test_create_cl")
print("=" * 80)
response = client.post(
    "/api/cover-letter/",
    json={
        "title": "CL",
        "resume_id": str(ObjectId()),
        "target_company": "C",
        "target_role": "R",
        "job_description": "J",
        "sender_name": "S",
        "sender_email": "s@s.com",
    },
)
print(f"Status: {response.status_code}")
print(f"Response body: {response.text}")
