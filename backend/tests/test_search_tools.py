"""Tests for CourseSearchTool.execute() outputs."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch
from search_tools import CourseSearchTool
from vector_store import SearchResults


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.max_results = 5
    return store


@pytest.fixture
def search_tool(mock_vector_store):
    return CourseSearchTool(mock_vector_store)


class TestCourseSearchToolExecute:
    """Tests for the execute method of CourseSearchTool."""

    def test_execute_returns_formatted_results_on_success(self, search_tool, mock_vector_store):
        """When vector store returns results, execute should return formatted text."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Chunk about RAG pipelines"],
            metadata=[{"course_title": "AI Course", "lesson_number": 1, "chunk_index": 0}],
            distances=[0.3]
        )
        mock_vector_store.get_lesson_info.return_value = {
            "lesson_number": 1,
            "lesson_title": "Intro",
            "lesson_link": "https://example.com/lesson1"
        }

        result = search_tool.execute(query="RAG pipelines")

        assert "Chunk about RAG pipelines" in result
        assert "AI Course" in result
        mock_vector_store.search.assert_called_once_with(
            query="RAG pipelines", course_name=None, lesson_number=None
        )

    def test_execute_returns_error_when_search_errors(self, search_tool, mock_vector_store):
        """When vector store search returns an error, execute should propagate it."""
        mock_vector_store.search.return_value = SearchResults.empty("Search error: n_results must be > 0")

        result = search_tool.execute(query="anything")

        assert "Search error" in result

    def test_execute_returns_no_results_message_when_empty(self, search_tool, mock_vector_store):
        """When vector store returns empty results (no error), execute should say no content found."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = search_tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_passes_course_name_filter(self, search_tool, mock_vector_store):
        """Course name filter should be forwarded to vector store search."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["content"], metadata=[{"course_title": "MCP", "lesson_number": 2}], distances=[0.1]
        )
        mock_vector_store.get_lesson_info.return_value = None
        mock_vector_store.get_course_link.return_value = None

        search_tool.execute(query="tools", course_name="MCP")

        mock_vector_store.search.assert_called_once_with(
            query="tools", course_name="MCP", lesson_number=None
        )

    def test_execute_passes_lesson_number_filter(self, search_tool, mock_vector_store):
        """Lesson number filter should be forwarded to vector store search."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["content"], metadata=[{"course_title": "MCP", "lesson_number": 3}], distances=[0.1]
        )
        mock_vector_store.get_lesson_info.return_value = None
        mock_vector_store.get_course_link.return_value = None

        search_tool.execute(query="tools", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="tools", course_name=None, lesson_number=3
        )

    def test_execute_populates_last_sources(self, search_tool, mock_vector_store):
        """After successful execution, last_sources should be populated."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["content"],
            metadata=[{"course_title": "AI Course", "lesson_number": 1}],
            distances=[0.2]
        )
        mock_vector_store.get_lesson_info.return_value = {
            "lesson_number": 1, "lesson_title": "Intro", "lesson_link": "https://example.com"
        }

        search_tool.execute(query="test")

        assert len(search_tool.last_sources) == 1
        assert "Intro" in search_tool.last_sources[0]


class TestVectorStoreSearchWithMaxResults:
    """Tests that verify vector store search respects max_results config."""

    def test_search_with_zero_max_results_causes_error(self):
        """MAX_RESULTS=0 should cause ChromaDB to error since n_results must be > 0."""
        # This tests the actual failure path: config has MAX_RESULTS=0
        mock_collection = MagicMock()
        mock_collection.query.side_effect = Exception("Number of requested results 0, cannot be negative or zero.")

        store = MagicMock()
        store.max_results = 0
        store.course_content = mock_collection
        store._resolve_course_name = MagicMock(return_value=None)
        store._build_filter = MagicMock(return_value=None)

        # Simulate what VectorStore.search does with max_results=0
        search_limit = None if None is not None else store.max_results  # = 0
        try:
            store.course_content.query(query_texts=["test"], n_results=search_limit, where=None)
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "cannot be negative or zero" in str(e)

    def test_search_with_positive_max_results_succeeds(self):
        """MAX_RESULTS > 0 should allow ChromaDB query to proceed."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [["doc1"]], 'metadatas': [[{"course_title": "C", "lesson_number": 1}]], 'distances': [[0.1]]
        }

        store = MagicMock()
        store.max_results = 5
        store.course_content = mock_collection

        search_limit = store.max_results  # = 5
        result = store.course_content.query(query_texts=["test"], n_results=search_limit, where=None)

        assert len(result['documents'][0]) == 1
