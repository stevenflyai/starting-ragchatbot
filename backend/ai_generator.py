import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Usage:
- **search_course_content**: Use for questions about specific course content or detailed educational materials
- **get_course_outline**: Use for questions about course structure, syllabus, outlines, or what topics/lessons a course covers. When returning an outline, include the course title, course link, and the full lesson list with each lesson's number and title.
- **Up to two sequential tool calls per query** — you may call a tool, receive results, then call another tool if needed before giving your final answer
- Use the minimum number of tool calls necessary to answer the question
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline/structure questions**: Use get_course_outline, then present the course title, course link, and all lessons (number and title)
- **Course content questions**: Use search_course_content, then answer
- **Multi-step questions** (e.g. comparing courses, finding related content across lessons): Use one tool to gather initial info, then a second tool to complete the search
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str, base_url: str = "", max_tool_rounds: int = None):
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**client_kwargs)
        self.model = model
        self.max_tool_rounds = max_tool_rounds if max_tool_rounds is not None else self.MAX_TOOL_ROUNDS

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional sequential tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Sequential tool-calling loop
        tool_error = False
        for round_num in range(self.max_tool_rounds):
            response = self.client.messages.create(**api_params)

            # Claude gave a text answer or we can't execute tools — done
            if response.stop_reason != "tool_use" or not tool_manager:
                return self._extract_text(response)

            # Execute tools and extend message history
            tool_error = self._execute_tool_round(response, api_params["messages"], tool_manager)
            if tool_error:
                break

        # Final call: max rounds exhausted or tool error — strip tools to force text response
        api_params.pop("tools", None)
        api_params.pop("tool_choice", None)
        final_response = self.client.messages.create(**api_params)
        return self._extract_text(final_response)

    def _execute_tool_round(self, response, messages: list, tool_manager) -> bool:
        """
        Execute tool calls from a response and append results to messages.

        Args:
            response: API response containing tool_use blocks
            messages: The messages list to extend (mutated in-place)
            tool_manager: Manager to execute tools

        Returns:
            True if a tool error occurred, False if all tools succeeded
        """
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        error_occurred = False
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(e),
                        "is_error": True
                    })
                    error_occurred = True

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        return error_occurred

    def _extract_text(self, response) -> str:
        """Extract the first text block from a response."""
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text
        return response.content[0].text
