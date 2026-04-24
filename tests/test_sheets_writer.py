import pytest
from unittest.mock import MagicMock, patch
from sheets.writer import SheetsWriter


SAMPLE_ROWS = [
    {"Phase": "Build", "Milestone": "API", "Deliverable": "REST API", "Start Date": "2026-05-01", "End Date": "2026-05-10", "Estimated Days": "7", "Notes": ""},
]

SAMPLE_GAPS = [
    {"reason": "Scope unclear", "location": "Section 3"},
]


def make_mock_service():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.return_value = {
        "spreadsheetId": "sheet123",
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
    }
    mock_service.spreadsheets().batchUpdate().execute.return_value = {}
    mock_service.spreadsheets().values().update().execute.return_value = {}
    return mock_service


def test_create_sheet_returns_url():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter()
        url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    assert "docs.google.com" in url


def test_create_sheet_calls_spreadsheets_create():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter()
        writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    mock_service.spreadsheets().create.assert_called()


def test_create_sheet_writes_gaps_tab_when_gaps_present():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter()
        writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    mock_service.spreadsheets().batchUpdate.assert_called()


def test_create_sheet_retries_on_failure():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.side_effect = [
        Exception("transient error"),
        {
            "spreadsheetId": "sheet123",
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
        },
    ]
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter()
        url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    assert "docs.google.com" in url


def test_create_sheet_retries_on_values_update_failure():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.return_value = {
        "spreadsheetId": "sheet123",
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
    }
    mock_service.spreadsheets().values().update().execute.side_effect = [
        Exception("transient network error"),
        {},
    ]
    with patch("sheets.writer.build_service", return_value=mock_service):
        with patch("time.sleep"):
            writer = SheetsWriter()
            url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    assert "docs.google.com" in url
    assert mock_service.spreadsheets().values().update().execute.call_count == 2


def test_create_sheet_retries_on_batch_update_failure():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.return_value = {
        "spreadsheetId": "sheet123",
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
    }
    mock_service.spreadsheets().values().update().execute.return_value = {}
    mock_service.spreadsheets().batchUpdate().execute.side_effect = [
        Exception("transient network error"),
        {},
    ]
    with patch("sheets.writer.build_service", return_value=mock_service):
        with patch("time.sleep"):
            writer = SheetsWriter()
            url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    assert "docs.google.com" in url
    assert mock_service.spreadsheets().batchUpdate().execute.call_count == 2


def test_build_service_uses_adc_with_correct_scopes():
    """build_service uses google.auth.default with the Sheets + Drive scopes."""
    from sheets.writer import build_service, SCOPES

    mock_creds = MagicMock()
    with patch("sheets.writer.google.auth.default", return_value=(mock_creds, "fake-project")) as mock_default, \
         patch("sheets.writer.build") as mock_build:
        build_service()

    mock_default.assert_called_once_with(scopes=SCOPES)
    mock_build.assert_called_once_with("sheets", "v4", credentials=mock_creds)
    assert "https://www.googleapis.com/auth/spreadsheets" in SCOPES
    assert "https://www.googleapis.com/auth/drive.file" in SCOPES
