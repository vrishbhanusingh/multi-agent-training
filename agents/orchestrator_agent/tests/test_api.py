"""
Integration tests for orchestrator agent API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from agents.orchestrator_agent.controllers.api import app

client = TestClient(app)

def test_create_query_and_get_status():
    # Test POST /api/queries
    payload = {
        "content": "Test workflow query",
        "meta": {"source": "test"},
        "sync": True
    }
    response = client.post("/api/queries", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "query_id" in data
    assert data["status"] in ("pending", "created", "processing", "complete")

    # Test GET /api/queries/{id}
    query_id = data["query_id"]
    response = client.get(f"/api/queries/{query_id}")
    assert response.status_code == 200, response.text
    data2 = response.json()
    assert data2["query_id"] == query_id
    assert data2["status"] in ("pending", "created", "processing", "complete")
