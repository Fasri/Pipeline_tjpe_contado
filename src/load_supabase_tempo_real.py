def load_supabase():
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    from datetime import datetime
    import pandas as pd
    
    BASE_DIR = Path(__file__).parent.parent
    load_dotenv(BASE_DIR / ".env")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Aviso: SUPABASE_URL ou SUPABASE_KEY não definidos no .env")
        return
    
    import requests
    
    file_path = BASE_DIR / "data_transform" / "final_tempo_real.xlsx"
    sheets = pd.read_excel(file_path, sheet_name=None)
    
    data_upload = datetime.now().strftime('%Y-%m-%d')
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "text/csv",
        "x-upsert": "true"
    }
    
    for sheet_name, df in sheets.items():
        df = df.fillna("")
        csv_content = df.to_csv(index=False)
        
        sheet_name_clean = sheet_name.replace(" ", "_").replace("ª", "a").replace("º", "o")
        file_name = f"tempo_real_{data_upload}_{sheet_name_clean}.csv"
        
        url = f"{supabase_url}/storage/v1/object/relatorios/{file_name}"
        
        response = requests.put(url, headers=headers, data=csv_content)
        
        if response.status_code in [200, 201]:
            print(f"Arquivo {file_name} enviado para o Supabase Storage")
        else:
            print(f"Erro ao enviar {file_name}: {response.status_code} - {response.text}")


if __name__ == "__main__":
    load_supabase()