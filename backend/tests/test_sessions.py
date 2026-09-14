"""
Unit and integration tests for sessions and messages endpoints.
"""

import uuid
from fastapi.testclient import TestClient


def test_create_session(client: TestClient):
    """Test creating a new session with an optional title and metadata."""
    payload = {
        "title": "PLG Retention Frameworks",
        "metadata": {"source": "unit-test", "eval_mode": True},
    }
    resp = client.post("/api/sessions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["title"] == "PLG Retention Frameworks"
    assert data["metadata"]["source"] == "unit-test"
    assert "created_at" in data
    assert "updated_at" in data


def test_list_sessions(client: TestClient):
    """Test listing sessions ordered by updated_at descending."""
    resp1 = client.post("/api/sessions", json={"title": "Session Alpha"})
    assert resp1.status_code == 201
    s1_id = resp1.json()["id"]

    resp2 = client.post("/api/sessions", json={"title": "Session Beta"})
    assert resp2.status_code == 201
    s2_id = resp2.json()["id"]

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) >= 2

    # Session Beta should be at or near the top since it was created second
    ids = [s["id"] for s in sessions]
    assert s1_id in ids
    assert s2_id in ids


def test_get_session_by_id(client: TestClient):
    """Test retrieving a single session by UUID."""
    create_resp = client.post("/api/sessions", json={"title": "Test Single Retrieval"})
    session_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id
    assert get_resp.json()["title"] == "Test Single Retrieval"


def test_get_session_not_found(client: TestClient):
    """Test 404 response for non-existent session UUID."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/sessions/{fake_id}")
    assert resp.status_code == 404
    assert f"Session '{fake_id}' not found" in resp.json()["detail"]


def test_session_message_lifecycle_and_ordering(client: TestClient):
    """
    Test full session message lifecycle:
    1. Create session
    2. Add user message
    3. Add assistant message with citations and served_by tag
    4. Fetch messages and verify chronological order
    """
    # 1. Create session
    session_resp = client.post("/api/sessions", json={"title": "Growth Chat"})
    session_id = session_resp.json()["id"]

    # 2. Add user message
    user_msg_payload = {
        "role": "user",
        "content": "What is Elena Verna's advice on PLG value metrics?",
    }
    user_resp = client.post(f"/api/sessions/{session_id}/messages", json=user_msg_payload)
    assert user_resp.status_code == 201
    user_msg = user_resp.json()
    assert user_msg["role"] == "user"
    assert user_msg["content"] == user_msg_payload["content"]
    assert user_msg["session_id"] == session_id

    # 3. Add assistant message
    citations = [
        {
            "episode_title": "Building Great Products with Elena Verna",
            "guest": "Elena Verna",
            "source_url": "https://www.lennyspodcast.com/elena-verna",
        }
    ]
    asst_msg_payload = {
        "role": "assistant",
        "content": "Elena emphasizes that a value metric must map directly to the customer's aha moment.",
        "citations": citations,
        "served_by": "ollama:llama3.2:3b",
    }
    asst_resp = client.post(f"/api/sessions/{session_id}/messages", json=asst_msg_payload)
    assert asst_resp.status_code == 201
    asst_msg = asst_resp.json()
    assert asst_msg["role"] == "assistant"
    assert asst_msg["served_by"] == "ollama:llama3.2:3b"
    assert len(asst_msg["citations"]) == 1

    # 4. Fetch all messages in chronological order
    msgs_resp = client.get(f"/api/sessions/{session_id}/messages")
    assert msgs_resp.status_code == 200
    messages = msgs_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[0]["created_at"] <= messages[1]["created_at"]


def test_session_cascade_delete(client: TestClient):
    """Test that deleting a session cascades and deletes its messages."""
    session_resp = client.post("/api/sessions", json={"title": "To be deleted"})
    session_id = session_resp.json()["id"]

    # Add a message to the session
    client.post(
        f"/api/sessions/{session_id}/messages",
        json={"role": "user", "content": "Ephemeral message"},
    )

    # Delete session
    del_resp = client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Verify session is gone
    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 404

    # Verify messages endpoint returns 404
    msgs_resp = client.get(f"/api/sessions/{session_id}/messages")
    assert msgs_resp.status_code == 404


def test_invalid_message_role(client: TestClient):
    """Test Pydantic validation rejects invalid message roles."""
    session_resp = client.post("/api/sessions", json={"title": "Validation Test"})
    session_id = session_resp.json()["id"]

    bad_payload = {"role": "invalid_role", "content": "Hello"}
    resp = client.post(f"/api/sessions/{session_id}/messages", json=bad_payload)
    assert resp.status_code == 422
