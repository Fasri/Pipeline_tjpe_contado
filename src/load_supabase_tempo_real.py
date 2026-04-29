import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


def load_supabase():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Aviso: SUPABASE_URL ou SUPABASE_KEY não definidos no .env")
        return

    file_path = BASE_DIR / "data_transform" / "final_tempo_real.xlsx"
    sheets = pd.read_excel(file_path, sheet_name=None)

    data_upload = datetime.now().strftime("%Y-%m-%d")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "text/csv",
        "x-upsert": "true",
    }

    for sheet_name, df in sheets.items():
        df = df.fillna("")
        csv_content = df.to_csv(index=False)

        sheet_name_clean = (
            sheet_name.replace(" ", "_").replace("ª", "a").replace("º", "o")
        )
        file_name = f"tempo_real_{data_upload}_{sheet_name_clean}.csv"
        url = f"{supabase_url}/storage/v1/object/relatorios/{file_name}"

        response = requests.put(url, headers=headers, data=csv_content)

        if response.status_code in [200, 201]:
            print(f"Arquivo {file_name} enviado para o Supabase Storage")
        else:
            print(f"Erro ao enviar {file_name}: {response.status_code} - {response.text}")

    # Enviar também o arquivo Consolidado_supabase.csv da pasta supabase
    consolidado_path = BASE_DIR / "supabase" / "Consolidado_supabase.csv"
    if consolidado_path.exists():
        with open(consolidado_path, "rb") as f:
            csv_content_consolidado = f.read()

        file_name_consolidado = "tempo_real_Consolidado_supabase.csv"
        url_consolidado = f"{supabase_url}/storage/v1/object/relatorios/{file_name_consolidado}"

        auth_headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        }
        del_resp = requests.delete(url_consolidado, headers=auth_headers)
        if del_resp.status_code not in [200, 204, 404]:
            print(
                f"Aviso: Erro ao deletar arquivo anterior: "
                f"{del_resp.status_code} - {del_resp.text}"
            )

        response_consolidado = requests.put(
            url_consolidado, headers=headers, data=csv_content_consolidado
        )
        if response_consolidado.status_code in [200, 201]:
            print(f"Arquivo {file_name_consolidado} enviado para o Supabase Storage (nova cópia)")
        else:
            print(
                f"Erro ao enviar {file_name_consolidado}: "
                f"{response_consolidado.status_code} - {response_consolidado.text}"
            )
    else:
        print(f"Aviso: Arquivo {consolidado_path} não encontrado para upload.")


if __name__ == "__main__":
    load_supabase()