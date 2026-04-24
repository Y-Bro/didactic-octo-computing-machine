import time
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _retry(fn, attempts=2, sleep=1):
    for attempt in range(attempts):
        try:
            return fn()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(sleep)


def _get_credentials(client_secret_path: str, token_cache_path: str):
    creds = None
    if Path(token_cache_path).exists():
        creds = Credentials.from_authorized_user_file(token_cache_path, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
    Path(token_cache_path).write_text(creds.to_json())
    return creds


def build_service(client_secret_path: str, token_cache_path: str):
    creds = _get_credentials(client_secret_path, token_cache_path)
    return build("sheets", "v4", credentials=creds)


class SheetsWriter:
    def __init__(self, client_secret_path: str, token_cache_path: str = ".oauth_token.json"):
        self._client_secret_path = client_secret_path
        self._token_cache_path = token_cache_path

    def create_sheet(self, title: str, rows: list[dict], gaps: list[dict]) -> str:
        service = build_service(self._client_secret_path, self._token_cache_path)

        spreadsheet_body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": "Project Plan"}}],
        }

        result = _retry(lambda: service.spreadsheets().create(body=spreadsheet_body).execute())

        sheet_id = result["spreadsheetId"]
        sheet_url = result.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{sheet_id}")

        if rows:
            columns = list(rows[0].keys())
            values = [columns] + [[row.get(col, "") for col in columns] for row in rows]
            _retry(lambda: service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Project Plan!A1",
                valueInputOption="RAW",
                body={"values": values},
            ).execute())

        if gaps:
            _retry(lambda: service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": "Gaps"}}}]},
            ).execute())
            gap_values = [["Reason", "Location"]] + [[g["reason"], g["location"]] for g in gaps]
            _retry(lambda: service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Gaps!A1",
                valueInputOption="RAW",
                body={"values": gap_values},
            ).execute())

        return sheet_url
