import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def load_tempo_real():
    CREDENTIALS_FILE = BASE_DIR / "credentials.json"
    TOKEN_FILE = BASE_DIR / "token.json"
    DATA_FILE = BASE_DIR / "data_transform" / "final_tempo_real.xlsx"

    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SPREADSHEET_ID não configurado no .env")

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Erro ao atualizar token: {e}")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("sheets", "v4", credentials=creds)

    sheets = pd.read_excel(DATA_FILE, sheet_name=None)

    for sheet_name, df in sheets.items():
        df = df.fillna("")
        values = [df.columns.values.tolist()] + df.values.tolist()

        body = {"values": values}
        range_clear = f"{sheet_name}!A:Z"
        range_update = f"{sheet_name}!A1"
        
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_clear
        ).execute()
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_update,
            valueInputOption="RAW",
            body=body,
        ).execute()

        print(f'{result.get("updatedCells")} células atualizadas na aba {sheet_name}.')


if __name__ == "__main__":
    load_tempo_real()