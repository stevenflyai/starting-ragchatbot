"""Tests for FastAPI API endpoints.

Defines a standalone test app to avoid the static file mount in app.py
which requires a ../frontend directory that doesn't exist in tests.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Lightweight test app mirroring the real endpoints from app.py
# ---------------------------------------------------------------------------

_mock_rag = MagicMock()

test_app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


@test_app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    try:
        session_id = request.session_id
        if not session_id:
            session_id = _mock_rag.session_manager.create_session()
        answer, sources = _mock_rag.query(request.query, session_id)
        return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    try:
        analytics = _mock_rag.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@test_app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    _mock_rag.session_manager.clear_session(session_id)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_mock_rag():
    """Reset the module-level mock before each test."""
    _mock_rag.reset_mock()
    _mock_rag.query.side_effect = None
    _mock_rag.query.return_value = ("Test answer", ["Source 1"])
    _mock_rag.get_course_analytics.side_effect = None
    _mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    _mock_rag.session_manager.create_session.return_value = "session_1"


@pytest.fixture
def client():
    return TestClient(test_app)


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    """Tests for POST /api/query."""

    def test_query_returns_200_with_valid_request(self, client):
        resp = client.post("/api/query", json={"query": "What is RAG?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Test answer"
        assert data["sources"] == ["Source 1"]
        assert data["session_id"] == "session_1"

    def test_query_creates_session_when_not_provided(self, client):
        client.post("/api/query", json={"query": "hello"})
        _mock_rag.session_manager.create_session.assert_called_once()

    def test_query_reuses_provided_session_id(self, client):
        resp = client.post("/api/query", json={"query": "hello", "session_id": "existing_session"})
        data = resp.json()
        assert data["session_id"] == "existing_session"
        _mock_rag.session_manager.create_session.assert_not_called()

    def test_query_passes_query_and_session_to_rag(self, client):
        client.post("/api/query", json={"query": "test q", "session_id": "s1"})
        _mock_rag.query.assert_called_once_with("test q", "s1")

    def test_query_returns_500_on_rag_error(self, client):
        _mock_rag.query.side_effect = RuntimeError("model failed")
        resp = client.post("/api/query", json={"query": "boom"})
        assert resp.status_code == 500
        assert "model failed" in resp.json()["detail"]

    def test_query_missing_body_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_query_empty_string_is_accepted(self, client):
        resp = client.post("/api/query", json={"query": ""})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    """Tests for GET /api/courses."""

    def test_courses_returns_200(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Course A", "Course B"]

    def test_courses_returns_empty_when_no_courses(self, client):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_returns_500_on_error(self, client):
        _mock_rag.get_course_analytics.side_effect = RuntimeError("db down")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
        assert "db down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:
    """Tests for DELETE /api/sessions/{session_id}."""

    def test_delete_session_returns_ok(self, client):
        resp = client.delete("/api/sessions/s1")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_delete_session_calls_clear(self, client):
        client.delete("/api/sessions/my_session")
        _mock_rag.session_manager.clear_session.assert_called_once_with("my_session")


# ---------------------------------------------------------------------------
# GET / (root) — should 404 since no static files mounted in test app
# ---------------------------------------------------------------------------

class TestRootPath:
    """Verify the test app has no static file mount (unlike the real app)."""

    def test_root_returns_404_in_test_app(self, client):
        resp = client.get("/")
        assert resp.status_code == 404
