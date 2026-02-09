"""Shared fixtures for RAG system tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock
from vector_store import SearchResults


@dataclass
class MockConfig:
    """Test configuration that mirrors the real Config."""
    ANTHROPIC_API_KEY: str = "test-key"
    ANTHROPIC_BASE_URL: str = ""
    ANTHROPIC_MODEL: str = "test-model"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma"


@pytest.fixture
def mock_config():
    return MockConfig()


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.max_results = 5
    return store


@pytest.fixture
def mock_rag_system():
    """A mock RAGSystem with pre-configured return values."""
    rag = MagicMock()
    rag.query.return_value = ("Test answer", ["Source 1"])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    rag.session_manager.create_session.return_value = "session_1"
    return rag
