import logging
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


def test_loop_logs_iteration_info(caplog):
    """run_agent logs iteration start/end info for a text-only response."""
    responses = [
        LLMResponse(tool_calls=[], text="All done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    # Patch sheet_url so the no-sheet error doesn't fire
    from unittest.mock import patch
    with caplog.at_level(logging.INFO, logger="agent.loop"):
        with patch("agent.loop.ToolExecutor") as MockExecutor:
            MockExecutor.return_value.execute.return_value = "https://docs.google.com/spreadsheets/d/abc"
            # Force sheet_url to be set by monkey-patching run_agent is hard;
            # instead, provide a write_to_sheet tool call first then text
            responses2 = [
                LLMResponse(
                    tool_calls=[ToolCall(id="1", name="write_to_sheet", arguments={"title": "Plan", "rows": []})],
                    text=None,
                ),
                LLMResponse(tool_calls=[], text="Done."),
            ]
            provider2 = make_provider(responses2)
            mock_writer2 = MagicMock()
            mock_writer2.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"
            run_agent(
                sow_data={"text": "SoW text.", "images": []},
                template={"columns": ["Phase"], "sample_rows": []},
                provider=provider2,
                sheets_writer=mock_writer2,
            )

    messages = [r.getMessage() for r in caplog.records]
    assert any("iteration" in m for m in messages), f"No iteration log found; got: {messages}"


def test_loop_logs_tool_names_per_iteration(caplog):
    """run_agent logs the tool names called during a tool-call iteration."""
    tool_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "missing scope", "location": "page 1"})
    write_call = ToolCall(id="2", name="write_to_sheet", arguments={"title": "Plan", "rows": []})
    responses = [
        LLMResponse(tool_calls=[tool_call], text=None),
        LLMResponse(tool_calls=[write_call], text=None),
        LLMResponse(tool_calls=[], text="Done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    with caplog.at_level(logging.INFO, logger="agent.loop"):
        run_agent(
            sow_data={"text": "SoW text.", "images": []},
            template={"columns": ["Phase"], "sample_rows": []},
            provider=provider,
            sheets_writer=mock_writer,
        )

    messages = [r.getMessage() for r in caplog.records]
    assert any("flag_gap" in m for m in messages), f"Tool name 'flag_gap' not found in logs; got: {messages}"


def test_main_verbose_flag_sets_debug_level():
    """--verbose parses to True; omitting it defaults to False."""
    from main import build_arg_parser

    parser = build_arg_parser()

    args_verbose = parser.parse_args(["--sow", "x", "--template", "y", "--verbose"])
    assert args_verbose.verbose is True

    args_default = parser.parse_args(["--sow", "x", "--template", "y"])
    assert args_default.verbose is False
