import pytest
from unittest.mock import MagicMock
from agent.tools import get_tool_schemas, ToolExecutor


def test_get_tool_schemas_returns_list():
    schemas = get_tool_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) == 3


def test_tool_schemas_have_required_keys():
    schemas = get_tool_schemas()
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


def test_tool_schemas_names():
    names = {s["name"] for s in get_tool_schemas()}
    assert names == {"analyze_diagram", "write_to_sheet", "flag_gap"}


def test_flag_gap_accumulates():
    mock_writer = MagicMock()
    executor = ToolExecutor(sheets_writer=mock_writer, provider=MagicMock())
    result = executor.flag_gap(reason="Scope unclear", location="Section 3")
    assert result == "Gap recorded."
    assert len(executor.gaps) == 1
    assert executor.gaps[0]["reason"] == "Scope unclear"


def test_write_to_sheet_calls_writer():
    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"
    executor = ToolExecutor(sheets_writer=mock_writer, provider=MagicMock())
    executor.flag_gap(reason="Unclear item", location="page 1")

    result = executor.write_to_sheet(
        title="Project Plan",
        rows=[{"Phase": "Build", "Milestone": "API", "Deliverable": "REST API", "Start Date": "2026-05-01", "End Date": "2026-05-10", "Estimated Days": "7", "Notes": ""}],
    )
    assert "https://docs.google.com" in result
    mock_writer.create_sheet.assert_called_once()


def test_analyze_diagram_calls_provider(monkeypatch):
    mock_provider = MagicMock()
    mock_provider.complete.return_value = MagicMock(
        text='{"components": ["API Gateway"], "integrations": ["DB"], "boundaries": []}',
        tool_calls=[]
    )
    executor = ToolExecutor(sheets_writer=MagicMock(), provider=mock_provider)
    result = executor.analyze_diagram(image_base64="abc123", page_number=1)
    assert "components" in result
