from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd

BASE_DIR = Path(__file__).parent.parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SPREADSHEET_ID = '1-hXLDTxGmDlPgbr_jIq73o49divD75c1jJ6Tbsw61iU'


def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


def get_sheet_data():
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    all_data = {}
    for sheet in sheets:
        sheet_title = sheet['properties']['title']
        range_name = f'{sheet_title}!A1:Z10000'
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if values:
            df = pd.DataFrame(values[1:], columns=values[0])
            all_data[sheet_title] = df.to_string(index=False, max_rows=100)
    
    return all_data


def get_context_for_llm():
    data = get_sheet_data()
    context = "Dados das planilhas do Google Sheets:\n\n"
    
    for sheet_name, content in data.items():
        context += f"=== {sheet_name} ===\n"
        context += content + "\n\n"
    
    return context
