import pytest
from agent.providers.base import ToolCall, ToolResult, LLMResponse, LLMProvider


def test_tool_call_fields():
    tc = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear"})
    assert tc.id == "1"
    assert tc.name == "flag_gap"
    assert tc.arguments == {"reason": "unclear"}


def test_tool_result_fields():
    tr = ToolResult(call_id="1", name="flag_gap", content="Gap recorded.")
    assert tr.call_id == "1"


def test_llm_response_text_only():
    r = LLMResponse(tool_calls=[], text="Done.")
    assert r.text == "Done."
    assert r.tool_calls == []


def test_llm_response_tool_calls():
    tc = ToolCall(id="1", name="flag_gap", arguments={})
    r = LLMResponse(tool_calls=[tc], text=None)
    assert r.text is None
    assert len(r.tool_calls) == 1


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


from unittest.mock import MagicMock, patch
from agent.providers.gemini import GeminiProvider
from agent.providers.base import ToolCall, ToolResult, LLMResponse


def test_gemini_complete_returns_text_response():
    mock_response = MagicMock()
    mock_response.parts = [MagicMock(text="Plan complete.", function_call=None)]
    mock_response.text = "Plan complete."

    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    with patch("agent.providers.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text == "Plan complete."
    assert result.tool_calls == []


def test_gemini_complete_returns_tool_call():
    mock_fn = MagicMock()
    mock_fn.name = "flag_gap"
    mock_fn.args = {"reason": "unclear scope", "location": "Section 2"}

    mock_part = MagicMock()
    mock_part.text = None
    mock_part.function_call = mock_fn

    mock_response = MagicMock()
    mock_response.parts = [mock_part]
    mock_response.text = None

    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    with patch("agent.providers.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "flag_gap"
    assert result.tool_calls[0].arguments == {"reason": "unclear scope", "location": "Section 2"}


def test_gemini_add_tool_results_appends_to_messages():
    with patch("agent.providers.gemini.genai"):
        provider = GeminiProvider(api_key="fake-key")

    messages = [{"role": "user", "content": "Hello"}]
    response = LLMResponse(tool_calls=[ToolCall(id="1", name="flag_gap", arguments={})], text=None)
    results = [ToolResult(call_id="1", name="flag_gap", content="Gap recorded.")]

    messages = provider.add_assistant_turn(messages, response)
    messages = provider.add_tool_results(messages, results)

    assert messages[-1]["role"] == "tool"
    assert len(messages[-1]["results"]) == 1
