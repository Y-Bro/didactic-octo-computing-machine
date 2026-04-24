import pytest
from unittest.mock import MagicMock
from agent.loop import run_agent
from agent.providers.base import LLMResponse, ToolCall


def make_provider(responses):
    """Returns a mock provider that yields responses in order."""
    provider = MagicMock()
    provider.complete.side_effect = responses
    provider.add_assistant_turn.side_effect = lambda msgs, resp: msgs + [{"role": "assistant", "tool_calls": resp.tool_calls}]
    provider.add_tool_results.side_effect = lambda msgs, results: msgs + [{"role": "tool", "results": results}]
    return provider


def test_run_agent_returns_sheet_url_when_write_to_sheet_called():
    tool_call = ToolCall(id="1", name="write_to_sheet", arguments={
        "title": "My Plan",
        "rows": [{"Phase": "Build", "Milestone": "API", "Deliverable": "REST API",
                  "Start Date": "2026-05-01", "End Date": "2026-05-10",
                  "Estimated Days": "7", "Notes": ""}],
    })
    responses = [
        LLMResponse(tool_calls=[tool_call], text=None),
        LLMResponse(tool_calls=[], text="Project plan written successfully."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Build a REST API.", "images": []},
        template={"columns": ["Phase", "Milestone", "Deliverable", "Start Date", "End Date", "Estimated Days", "Notes"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )

    assert "docs.google.com" in result.sheet_url


def test_run_agent_calls_flag_gap_tool():
    flag_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear", "location": "page 1"})
    write_call = ToolCall(id="2", name="write_to_sheet", arguments={"title": "Plan", "rows": []})
    responses = [
        LLMResponse(tool_calls=[flag_call], text=None),
        LLMResponse(tool_calls=[write_call], text=None),
        LLMResponse(tool_calls=[], text="Done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Some SoW text.", "images": []},
        template={"columns": ["Phase"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )
    assert "docs.google.com" in result.sheet_url


def test_run_agent_stops_after_max_iterations():
    """Prevents infinite loops if the agent never calls write_to_sheet."""
    tool_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear", "location": "page 1"})
    provider = make_provider([LLMResponse(tool_calls=[tool_call], text=None)] * 30)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    with pytest.raises(RuntimeError, match="exceeded maximum iterations"):
        run_agent(
            sow_data={"text": "text", "images": []},
            template={"columns": ["Phase"], "sample_rows": []},
            provider=provider,
            sheets_writer=mock_writer,
        )


def test_run_agent_returns_structured_result():
    """run_agent returns a RunResult dataclass with sheet_url, iterations, rows, gaps."""
    tool_call = ToolCall(id="1", name="write_to_sheet", arguments={
        "title": "My Plan",
        "rows": [{"Phase": "Build", "Milestone": "API", "Deliverable": "REST API",
                  "Start Date": "2026-05-01", "End Date": "2026-05-10",
                  "Estimated Days": "7", "Notes": ""}],
    })
    responses = [
        LLMResponse(tool_calls=[tool_call], text=None),
        LLMResponse(tool_calls=[], text="Project plan written successfully."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Build a REST API.", "images": []},
        template={"columns": ["Phase", "Milestone", "Deliverable", "Start Date", "End Date", "Estimated Days", "Notes"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )

    assert hasattr(result, "sheet_url"), "result must have sheet_url attribute"
    assert hasattr(result, "iterations"), "result must have iterations attribute"
    assert hasattr(result, "rows"), "result must have rows attribute"
    assert hasattr(result, "gaps"), "result must have gaps attribute"
    assert "docs.google.com" in result.sheet_url
    assert result.iterations == 2   # tool-call iteration + text iteration
    assert result.rows == 1
    assert result.gaps == 0


def test_run_agent_counts_gaps():
    """run_agent counts gaps flagged via flag_gap tool calls."""
    flag_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear", "location": "page 1"})
    write_call = ToolCall(id="2", name="write_to_sheet", arguments={"title": "Plan", "rows": []})
    responses = [
        LLMResponse(tool_calls=[flag_call], text=None),
        LLMResponse(tool_calls=[write_call], text=None),
        LLMResponse(tool_calls=[], text="Done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Some SoW text.", "images": []},
        template={"columns": ["Phase"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )
    assert result.gaps == 1
    assert result.iterations == 3


def test_run_agent_counts_rows():
    """run_agent counts rows passed to write_to_sheet."""
    rows = [
        {"Phase": "Phase 1"},
        {"Phase": "Phase 2"},
        {"Phase": "Phase 3"},
    ]
    write_call = ToolCall(id="1", name="write_to_sheet", arguments={"title": "Plan", "rows": rows})
    responses = [
        LLMResponse(tool_calls=[write_call], text=None),
        LLMResponse(tool_calls=[], text="Done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Some SoW text.", "images": []},
        template={"columns": ["Phase"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )
    assert result.rows == 3
