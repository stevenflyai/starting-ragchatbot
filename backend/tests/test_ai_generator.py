"""Tests for AIGenerator tool-calling behavior."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import MagicMock, patch
from ai_generator import AIGenerator


def make_mock_response(stop_reason="end_turn", content=None):
    """Helper to create a mock Anthropic API response."""
    response = MagicMock()
    response.stop_reason = stop_reason
    if content is None:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Here is the answer."
        response.content = [text_block]
    else:
        response.content = content
    return response


def make_text_block(text):
    """Helper to create a mock text content block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(tool_name, tool_input, tool_id="tool_123"):
    """Helper to create a mock tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    return block


SAMPLE_TOOLS = [{"name": "search_course_content", "description": "search", "input_schema": {}}]


@pytest.fixture
def ai_generator():
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="test-model")
        gen.client = mock_client
        yield gen


class TestToolPassthrough:
    """Tests that tools and tool_manager are correctly wired to the API."""

    def test_passes_tools_to_api_call(self, ai_generator):
        """When tools are provided, they should be included in the API call."""
        ai_generator.client.messages.create.return_value = make_mock_response()

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS)

        call_kwargs = ai_generator.client.messages.create.call_args[1]
        assert call_kwargs["tools"] == SAMPLE_TOOLS
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_does_not_include_tools_when_none(self, ai_generator):
        """When no tools are provided, tools should not be in the API call."""
        ai_generator.client.messages.create.return_value = make_mock_response()

        ai_generator.generate_response(query="test", tools=None)

        call_kwargs = ai_generator.client.messages.create.call_args[1]
        assert "tools" not in call_kwargs

    def test_does_not_call_tool_manager_when_no_tool_use(self, ai_generator):
        """When Claude returns end_turn, tool_manager should not be called."""
        ai_generator.client.messages.create.return_value = make_mock_response()

        tool_manager = MagicMock()
        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        tool_manager.execute_tool.assert_not_called()

    def test_no_tool_execution_without_tool_manager(self, ai_generator):
        """When tool_manager is None, tool_use response should return first text block."""
        text_block = make_text_block("I want to search")
        tool_block = make_tool_use_block("search_course_content", {"query": "test"})
        response = make_mock_response(stop_reason="tool_use", content=[text_block, tool_block])
        ai_generator.client.messages.create.return_value = response

        result = ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=None)

        assert result == "I want to search"


class TestSingleToolRound:
    """Tests for queries that need exactly one tool call."""

    def test_executes_tool_and_returns_final_answer(self, ai_generator):
        """Single tool round: Claude calls tool, gets results, gives text answer."""
        tool_block = make_tool_use_block("search_course_content", {"query": "RAG", "course_name": "MCP"})
        first_response = make_mock_response(stop_reason="tool_use", content=[tool_block])
        final_response = make_mock_response(stop_reason="end_turn")

        ai_generator.client.messages.create.side_effect = [first_response, final_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search results here"

        result = ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        tool_manager.execute_tool.assert_called_once_with("search_course_content", query="RAG", course_name="MCP")
        assert result == "Here is the answer."

    def test_two_api_calls_made(self, ai_generator):
        """Single tool round should make exactly 2 API calls."""
        tool_block = make_tool_use_block("search_course_content", {"query": "RAG"})
        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool_block]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        assert ai_generator.client.messages.create.call_count == 2

    def test_second_call_includes_tools(self, ai_generator):
        """After one tool round, the follow-up call should still include tools."""
        tool_block = make_tool_use_block("search_course_content", {"query": "RAG"})
        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool_block]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        second_call_kwargs = ai_generator.client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs

    def test_second_call_has_tool_results_in_messages(self, ai_generator):
        """The follow-up API call should include tool results in message history."""
        tool_block = make_tool_use_block("search_course_content", {"query": "RAG"})
        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool_block]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "found content about RAG"

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        second_call_kwargs = ai_generator.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["content"] == "found content about RAG"


class TestTwoSequentialToolRounds:
    """Tests for queries that need two sequential tool calls."""

    def test_two_tools_three_api_calls(self, ai_generator):
        """Two tool rounds should produce exactly 3 API calls."""
        tool1 = make_tool_use_block("get_course_outline", {"course_name": "MCP"}, tool_id="t1")
        tool2 = make_tool_use_block("search_course_content", {"query": "topic"}, tool_id="t2")

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool1]),
            make_mock_response(stop_reason="tool_use", content=[tool2]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline data", "search data"]

        result = ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        assert ai_generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert result == "Here is the answer."

    def test_both_tools_called_with_correct_args(self, ai_generator):
        """Each tool should be called with its specific arguments."""
        tool1 = make_tool_use_block("get_course_outline", {"course_name": "MCP"}, tool_id="t1")
        tool2 = make_tool_use_block("search_course_content", {"query": "Lesson 4 topic"}, tool_id="t2")

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool1]),
            make_mock_response(stop_reason="tool_use", content=[tool2]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline", "search results"]

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        calls = tool_manager.execute_tool.call_args_list
        assert calls[0] == (("get_course_outline",), {"course_name": "MCP"})
        assert calls[1] == (("search_course_content",), {"query": "Lesson 4 topic"})

    def test_final_call_strips_tools_after_two_rounds(self, ai_generator):
        """After 2 tool rounds, the final API call must NOT include tools."""
        tool1 = make_tool_use_block("get_course_outline", {"course_name": "MCP"}, tool_id="t1")
        tool2 = make_tool_use_block("search_course_content", {"query": "topic"}, tool_id="t2")

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool1]),
            make_mock_response(stop_reason="tool_use", content=[tool2]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline", "search"]

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        third_call_kwargs = ai_generator.client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_message_accumulation_across_two_rounds(self, ai_generator):
        """The final API call should contain the full message history from both rounds."""
        tool1 = make_tool_use_block("get_course_outline", {"course_name": "MCP"}, tool_id="t1")
        tool2 = make_tool_use_block("search_course_content", {"query": "topic"}, tool_id="t2")

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool1]),
            make_mock_response(stop_reason="tool_use", content=[tool2]),
            make_mock_response(stop_reason="end_turn"),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline data", "search data"]

        ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        third_call_kwargs = ai_generator.client.messages.create.call_args_list[2][1]
        messages = third_call_kwargs["messages"]
        # user, assistant(tool1), user(result1), assistant(tool2), user(result2)
        assert len(messages) == 5
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"
        # Verify tool result contents
        assert messages[2]["content"][0]["content"] == "outline data"
        assert messages[2]["content"][0]["tool_use_id"] == "t1"
        assert messages[4]["content"][0]["content"] == "search data"
        assert messages[4]["content"][0]["tool_use_id"] == "t2"


class TestToolErrorHandling:
    """Tests for graceful error handling during tool execution."""

    def test_first_tool_error_sends_error_and_gets_final_answer(self, ai_generator):
        """Tool error on first round should send is_error result and get a final answer."""
        tool_block = make_tool_use_block("search_course_content", {"query": "test"})

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool_block]),
            make_mock_response(stop_reason="end_turn", content=[make_text_block("Sorry, I encountered an issue.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = Exception("Tool crashed")

        result = ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        assert ai_generator.client.messages.create.call_count == 2
        assert result == "Sorry, I encountered an issue."
        # Final call should have no tools (error breaks the loop)
        final_call_kwargs = ai_generator.client.messages.create.call_args_list[1][1]
        assert "tools" not in final_call_kwargs
        # Verify error was sent as tool_result
        messages = final_call_kwargs["messages"]
        tool_result = messages[2]["content"][0]
        assert tool_result["is_error"] is True
        assert "Tool crashed" in tool_result["content"]

    def test_second_tool_error_preserves_first_result(self, ai_generator):
        """Error on second tool should still include first tool's successful result."""
        tool1 = make_tool_use_block("get_course_outline", {"course_name": "MCP"}, tool_id="t1")
        tool2 = make_tool_use_block("search_course_content", {"query": "topic"}, tool_id="t2")

        ai_generator.client.messages.create.side_effect = [
            make_mock_response(stop_reason="tool_use", content=[tool1]),
            make_mock_response(stop_reason="tool_use", content=[tool2]),
            make_mock_response(stop_reason="end_turn", content=[make_text_block("Partial answer.")]),
        ]

        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["outline data", Exception("Second tool failed")]

        result = ai_generator.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

        assert ai_generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert result == "Partial answer."
        # Verify first result is intact and second has error
        final_messages = ai_generator.client.messages.create.call_args_list[2][1]["messages"]
        assert final_messages[2]["content"][0]["content"] == "outline data"
        assert final_messages[4]["content"][0]["is_error"] is True


class TestMaxToolRoundsConfig:
    """Tests for MAX_TOOL_ROUNDS enforcement and constructor override."""

    def test_max_rounds_defaults_to_class_constant(self):
        """Default max_tool_rounds should be the class constant."""
        with patch("ai_generator.anthropic.Anthropic"):
            gen = AIGenerator(api_key="test", model="test")
            assert gen.max_tool_rounds == AIGenerator.MAX_TOOL_ROUNDS

    def test_constructor_override(self):
        """Constructor param should override the class constant."""
        with patch("ai_generator.anthropic.Anthropic"):
            gen = AIGenerator(api_key="test", model="test", max_tool_rounds=1)
            assert gen.max_tool_rounds == 1

    def test_max_rounds_one_strips_tools_after_single_round(self):
        """With max_tool_rounds=1, tools should be stripped after one tool call."""
        with patch("ai_generator.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            gen = AIGenerator(api_key="test", model="test", max_tool_rounds=1)
            gen.client = mock_client

            tool_block = make_tool_use_block("search_course_content", {"query": "test"})
            gen.client.messages.create.side_effect = [
                make_mock_response(stop_reason="tool_use", content=[tool_block]),
                make_mock_response(stop_reason="end_turn"),
            ]

            tool_manager = MagicMock()
            tool_manager.execute_tool.return_value = "results"

            gen.generate_response(query="test", tools=SAMPLE_TOOLS, tool_manager=tool_manager)

            assert gen.client.messages.create.call_count == 2
            # Second call should NOT have tools (max rounds = 1, exhausted)
            second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
            assert "tools" not in second_call_kwargs
