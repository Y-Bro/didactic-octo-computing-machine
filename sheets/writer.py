import time
from googleapiclient.discovery import build
from google.oauth2 import service_account


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def build_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


class SheetsWriter:
    def __init__(self, credentials_path: str):
        self._credentials_path = credentials_path

    def create_sheet(self, title: str, rows: list[dict], gaps: list[dict]) -> str:
        service = build_service(self._credentials_path)

        spreadsheet_body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": "Project Plan"}}],
        }

        for attempt in range(2):
            try:
                result = service.spreadsheets().create(body=spreadsheet_body).execute()
                break
            except Exception:
                if attempt == 1:
                    raise
                time.sleep(1)

        sheet_id = result["spreadsheetId"]
        sheet_url = result.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{sheet_id}")

        if rows:
            columns = list(rows[0].keys())
            values = [columns] + [[row.get(col, "") for col in columns] for row in rows]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Project Plan!A1",
                valueInputOption="RAW",
                body={"values": values},
            ).execute()

        if gaps:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": "Gaps"}}}]},
            ).execute()
            gap_values = [["Reason", "Location"]] + [[g["reason"], g["location"]] for g in gaps]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Gaps!A1",
                valueInputOption="RAW",
                body={"values": gap_values},
            ).execute()

        return sheet_url
