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
