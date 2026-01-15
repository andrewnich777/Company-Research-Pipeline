"""
Base agent class for Claude API interactions with tool use.
"""

import asyncio
import json
import os
import anthropic
from abc import ABC, abstractmethod
from typing import Any

from tools.tool_definitions import TOOL_DEFINITIONS, execute_tool, get_tools_for_agent


# Rate limit retry settings
MAX_RETRIES = 5
INITIAL_BACKOFF = 30  # seconds


# Global API key storage - set once at startup
_API_KEY: str | None = None


def set_api_key(key: str):
    """Set the API key globally for all agents."""
    global _API_KEY
    _API_KEY = key
    os.environ["ANTHROPIC_API_KEY"] = key


def get_api_key() -> str | None:
    """Get the current API key."""
    return _API_KEY or os.environ.get("ANTHROPIC_API_KEY")


class BaseAgent(ABC):
    """
    Base class for all research agents.

    Handles Claude API communication and tool use loops.
    Subclasses define the system prompt and which tools to use.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        max_tool_calls: int = 20,
        api_key: str | None = None,
    ):
        # Use provided key, global key, or environment variable
        key = api_key or get_api_key()
        if key:
            self.client = anthropic.Anthropic(api_key=key)
        else:
            self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.max_tool_calls = max_tool_calls

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent."""
        pass

    @property
    @abstractmethod
    def tools(self) -> list[str]:
        """List of tool names this agent can use."""
        pass

    def get_tool_definitions(self) -> list[dict]:
        """Get Claude API tool definitions for this agent's tools."""
        tools = get_tools_for_agent(self.tools)

        # Add Claude's native web search if agent requested web_search
        if "web_search" in self.tools:
            tools.append({
                "type": "web_search_20250305",
                "name": "web_search"
            })

        return tools

    async def execute_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        """
        Execute a tool call and return the result.

        Override this in subclasses to add custom tool handling.
        """
        return await execute_tool(tool_name, tool_input)

    async def run(self, user_message: str, context: dict = None) -> dict:
        """
        Run the agent with the given user message.

        Handles the tool use loop automatically.
        Returns the final response and any structured data extracted.
        """
        messages = [{"role": "user", "content": user_message}]
        tool_definitions = self.get_tool_definitions()

        tool_call_count = 0

        while tool_call_count < self.max_tool_calls:
            # Call Claude - only include tools parameter if we have tools
            api_kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": self.system_prompt,
                "messages": messages,
            }
            if tool_definitions:
                api_kwargs["tools"] = tool_definitions

            # Retry with exponential backoff on rate limit errors
            response = None
            for retry in range(MAX_RETRIES):
                try:
                    response = self.client.messages.create(**api_kwargs)
                    break  # Success, exit retry loop
                except anthropic.RateLimitError as e:
                    if retry == MAX_RETRIES - 1:
                        raise  # Final retry failed, propagate error
                    backoff = INITIAL_BACKOFF * (2 ** retry)
                    print(f"  [{self.name}] Rate limited, waiting {backoff}s (retry {retry + 1}/{MAX_RETRIES})...")
                    await asyncio.sleep(backoff)

            if response is None:
                raise RuntimeError("Failed to get response from API")

            # Check if we're done (no tool use)
            if response.stop_reason == "end_turn":
                return self._extract_response(response, messages)

            # Process tool calls
            if response.stop_reason == "tool_use":
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute each tool call (skip server-side tools like web_search)
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Skip server-side tools - Claude handles these automatically
                        if block.name == "web_search":
                            tool_call_count += 1
                            print(f"  [{self.name}] Web search (handled by Claude)...")
                            continue

                        tool_call_count += 1
                        print(f"  [{self.name}] Calling {block.name}...")

                        result = await self.execute_tool_call(
                            block.name,
                            block.input
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result) if isinstance(result, dict) else str(result)
                        })

                # Add tool results to messages (only if we have results to add)
                if tool_results:
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
            else:
                # Unexpected stop reason
                break

        # Max tool calls reached
        return self._extract_response(response, messages)

    def _extract_response(self, response: anthropic.types.Message, messages: list) -> dict:
        """Extract the final text response and any JSON data."""
        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        # Try to extract JSON from the response
        json_data = None
        try:
            # Look for JSON in code blocks
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', text_content, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(1))
            else:
                # Try to parse the whole response as JSON
                json_data = json.loads(text_content)
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "text": text_content,
            "json": json_data,
            "messages": messages,
            "model": self.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        }


class SimpleAgent(BaseAgent):
    """
    A simple agent that can be configured at runtime.

    Useful for one-off tasks or testing.
    """

    def __init__(
        self,
        agent_name: str,
        system: str,
        agent_tools: list[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._name = agent_name
        self._system_prompt = system
        self._tools = agent_tools or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def tools(self) -> list[str]:
        return self._tools
