"""Tests for RAGSystem query handling with content-related questions."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass


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


class TestRAGSystemConfigPropagation:
    """Tests that config values are correctly propagated through the system."""

    def test_max_results_is_positive(self):
        """MAX_RESULTS in config must be > 0 for ChromaDB queries to work."""
        from config import config as real_config
        assert real_config.MAX_RESULTS > 0, (
            f"MAX_RESULTS must be > 0, got {real_config.MAX_RESULTS}"
        )

    def test_max_results_zero_means_no_search_results(self):
        """When MAX_RESULTS=0, VectorStore.search passes n_results=0 to ChromaDB."""
        # Simulate VectorStore.search logic with max_results=0
        max_results = 0
        limit = None  # No explicit limit passed by CourseSearchTool

        search_limit = limit if limit is not None else max_results
        assert search_limit == 0, "search_limit should be 0 when MAX_RESULTS=0 and no explicit limit"

    def test_max_results_positive_allows_results(self):
        """When MAX_RESULTS > 0, search_limit should be positive."""
        max_results = 5
        limit = None

        search_limit = limit if limit is not None else max_results
        assert search_limit == 5


class TestRAGSystemQueryFlow:
    """Tests for the full query flow through RAGSystem."""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_query_passes_tools_to_ai_generator(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """RAGSystem.query should pass tool definitions to ai_generator."""
        from rag_system import RAGSystem

        mock_ai = MagicMock()
        mock_ai.generate_response.return_value = "test answer"
        mock_ai_cls.return_value = mock_ai

        config = MockConfig()
        rag = RAGSystem(config)

        answer, sources = rag.query("What is RAG?")

        # ai_generator.generate_response should have been called with tools
        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) > 0

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_query_passes_tool_manager(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """RAGSystem.query should pass tool_manager so tools can be executed."""
        from rag_system import RAGSystem

        mock_ai = MagicMock()
        mock_ai.generate_response.return_value = "test answer"
        mock_ai_cls.return_value = mock_ai

        config = MockConfig()
        rag = RAGSystem(config)

        rag.query("What is RAG?")

        call_kwargs = mock_ai.generate_response.call_args[1]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is not None

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_query_returns_answer_and_sources(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """RAGSystem.query should return a (response, sources) tuple."""
        from rag_system import RAGSystem

        mock_ai = MagicMock()
        mock_ai.generate_response.return_value = "The answer is 42"
        mock_ai_cls.return_value = mock_ai

        config = MockConfig()
        rag = RAGSystem(config)

        answer, sources = rag.query("What is the meaning?")

        assert answer == "The answer is 42"
        assert isinstance(sources, list)

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_both_tools_registered(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """RAGSystem should register both search and outline tools."""
        from rag_system import RAGSystem

        mock_ai = MagicMock()
        mock_ai_cls.return_value = mock_ai

        config = MockConfig()
        rag = RAGSystem(config)

        tool_names = list(rag.tool_manager.tools.keys())
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_max_results_propagated_to_vector_store(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """MAX_RESULTS from config should be passed to VectorStore constructor."""
        from rag_system import RAGSystem

        config = MockConfig(MAX_RESULTS=10)
        rag = RAGSystem(config)

        mock_vs_cls.assert_called_once_with(config.CHROMA_PATH, config.EMBEDDING_MODEL, 10)

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    def test_zero_max_results_propagated(self, mock_dp, mock_ai_cls, mock_vs_cls):
        """MAX_RESULTS=0 from config gets passed to VectorStore, which is the bug."""
        from rag_system import RAGSystem

        config = MockConfig(MAX_RESULTS=0)
        rag = RAGSystem(config)

        # This confirms the bug path: VectorStore gets max_results=0
        mock_vs_cls.assert_called_once_with(config.CHROMA_PATH, config.EMBEDDING_MODEL, 0)
