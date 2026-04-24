import anthropic
from agent.providers.base import LLMProvider, LLMResponse, ToolCall, ToolResult


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        claude_messages = self._convert_messages(messages)
        claude_tools = self._convert_tools(tools)

        kwargs = {
            "model": self._model,
            "max_tokens": 8192,
            "system": system,
            "messages": claude_messages,
        }
        if claude_tools:
            kwargs["tools"] = claude_tools

        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        content = [
            {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
            for tc in response.tool_calls
        ]
        return messages + [{"role": "assistant", "content": content}]

    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        content = [
            {"type": "tool_result", "tool_use_id": r.call_id, "content": r.content}
            for r in results
        ]
        return messages + [{"role": "user", "content": content}]

    def _parse_response(self, response) -> LLMResponse:
        tool_calls = []
        text = None
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
            elif block.type == "text":
                text = block.text
        if tool_calls:
            return LLMResponse(tool_calls=tool_calls, text=None)
        return LLMResponse(tool_calls=[], text=text)

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        result = []
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    result.append({"role": "user", "content": content})
                else:
                    claude_parts = []
                    for part in content:
                        if part["type"] == "text":
                            claude_parts.append({"type": "text", "text": part["text"]})
                        elif part["type"] == "image":
                            claude_parts.append({
                                "type": "image",
                                "source": part["source"],
                            })
                    result.append({"role": "user", "content": claude_parts})
            elif msg["role"] == "assistant":
                content = [
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                    for tc in msg.get("tool_calls", [])
                ]
                result.append({"role": "assistant", "content": content})
            elif msg["role"] == "tool":
                content = [
                    {"type": "tool_result", "tool_use_id": r.call_id, "content": r.content}
                    for r in msg["results"]
                ]
                result.append({"role": "user", "content": content})
        return result

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t.get("parameters", {}),
            }
            for t in tools
        ]
