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
        writer = SheetsWriter(client_secret_path="fake.json")
        url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    assert "docs.google.com" in url


def test_create_sheet_calls_spreadsheets_create():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(client_secret_path="fake.json")
        writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    mock_service.spreadsheets().create.assert_called()


def test_create_sheet_writes_gaps_tab_when_gaps_present():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(client_secret_path="fake.json")
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
        writer = SheetsWriter(client_secret_path="fake.json")
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
            writer = SheetsWriter(client_secret_path="fake.json")
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
            writer = SheetsWriter(client_secret_path="fake.json")
            url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    assert "docs.google.com" in url
    assert mock_service.spreadsheets().batchUpdate().execute.call_count == 2


def test_get_credentials_runs_flow_when_no_cache(tmp_path):
    """When token cache doesn't exist, the OAuth installed-app flow runs."""
    from sheets.writer import _get_credentials

    client_secret = tmp_path / "client_secret.json"
    client_secret.write_text("{}")  # contents don't matter; we mock the flow
    token_cache = tmp_path / "token.json"  # does not exist yet

    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "fake"}'

    with patch("sheets.writer.InstalledAppFlow") as mock_flow_cls:
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = _get_credentials(str(client_secret), str(token_cache))

    mock_flow_cls.from_client_secrets_file.assert_called_once()
    mock_flow.run_local_server.assert_called_once()
    assert token_cache.read_text() == '{"token": "fake"}'
    assert result is mock_creds


def test_get_credentials_uses_cached_token_when_valid(tmp_path):
    """When cache exists and creds are valid, no flow runs."""
    from sheets.writer import _get_credentials

    client_secret = tmp_path / "client_secret.json"
    client_secret.write_text("{}")
    token_cache = tmp_path / "token.json"
    token_cache.write_text('{"token": "cached"}')

    mock_creds = MagicMock()
    mock_creds.valid = True

    with patch("sheets.writer.Credentials.from_authorized_user_file", return_value=mock_creds) as mock_load, \
         patch("sheets.writer.InstalledAppFlow") as mock_flow_cls:
        result = _get_credentials(str(client_secret), str(token_cache))

    mock_load.assert_called_once()
    mock_flow_cls.from_client_secrets_file.assert_not_called()
    assert result is mock_creds
