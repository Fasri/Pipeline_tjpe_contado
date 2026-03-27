def load_tempo_real():
    import os.path

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pandas as pd

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    SPREADSHEET_ID = '1-hXLDTxGmDlPgbr_jIq73o49divD75c1jJ6Tbsw61iU'

    file_path = 'data_transform/final_tempo_real.xlsx'
    sheets = pd.read_excel(file_path, sheet_name=None)

    for sheet_name, df in sheets.items():
        df = df.fillna("")
        values = [df.columns.values.tolist()] + df.values.tolist()
    
        body = {
            'values': values
        }         
        
        range_name = f'{sheet_name}!A1:J6000'
        service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption='RAW', body=body).execute()

        print(f'{result.get("updatedCells")} células atualizadas na aba {sheet_name}.')


if __name__ == "__main__":
    load_tempo_real()