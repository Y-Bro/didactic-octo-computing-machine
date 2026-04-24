import uuid
import google.generativeai as genai
from agent.providers.base import LLMProvider, LLMResponse, ToolCall, ToolResult


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self._model_name = model

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        gemini_tools = self._convert_tools(tools)
        model = genai.GenerativeModel(
            model_name=self._model_name,
            tools=gemini_tools if gemini_tools else None,
            system_instruction=system,
        )
        chat = model.start_chat(history=self._convert_history(messages[:-1]))
        last = messages[-1]
        content = self._convert_user_content(last["content"])
        response = chat.send_message(content)
        return self._parse_response(response)

    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        return messages + [{"role": "assistant", "tool_calls": response.tool_calls}]

    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        return messages + [{"role": "tool", "results": results}]

    def _parse_response(self, response) -> LLMResponse:
        tool_calls = []
        for part in response.parts:
            if part.function_call:
                fn = part.function_call
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),
                    name=fn.name,
                    arguments=dict(fn.args),
                ))
        if tool_calls:
            return LLMResponse(tool_calls=tool_calls, text=None)
        return LLMResponse(tool_calls=[], text=response.text)

    def _convert_tools(self, tools: list[dict]):
        if not tools:
            return []
        declarations = []
        for t in tools:
            declarations.append(genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=self._schema_to_gemini(t.get("parameters", {})),
            ))
        return [genai.protos.Tool(function_declarations=declarations)]

    def _schema_to_gemini(self, schema: dict):
        type_map = {"string": genai.protos.Type.STRING, "integer": genai.protos.Type.INTEGER,
                    "number": genai.protos.Type.NUMBER, "boolean": genai.protos.Type.BOOLEAN,
                    "array": genai.protos.Type.ARRAY, "object": genai.protos.Type.OBJECT}
        props = {}
        for name, prop in schema.get("properties", {}).items():
            props[name] = genai.protos.Schema(
                type=type_map.get(prop.get("type", "string"), genai.protos.Type.STRING),
                description=prop.get("description", ""),
            )
        return genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties=props,
            required=schema.get("required", []),
        )

    def _convert_history(self, messages: list[dict]) -> list:
        history = []
        for msg in messages:
            if msg["role"] == "user":
                history.append({"role": "user", "parts": self._convert_user_content(msg["content"])})
            elif msg["role"] == "assistant":
                parts = []
                for tc in msg.get("tool_calls", []):
                    parts.append(genai.protos.Part(
                        function_call=genai.protos.FunctionCall(
                            name=tc.name, args=tc.arguments
                        )
                    ))
                history.append({"role": "model", "parts": parts})
            elif msg["role"] == "tool":
                parts = [
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=r.name,
                            response={"result": r.content},
                        )
                    )
                    for r in msg["results"]
                ]
                history.append({"role": "user", "parts": parts})
        return history

    def _convert_user_content(self, content) -> list:
        if isinstance(content, str):
            return [content]
        parts = []
        for item in content:
            if item["type"] == "text":
                parts.append(item["text"])
            elif item["type"] == "image":
                import base64
                parts.append(genai.protos.Part(
                    inline_data=genai.protos.Blob(
                        mime_type=item["source"]["media_type"],
                        data=base64.b64decode(item["source"]["data"]),
                    )
                ))
        return parts
