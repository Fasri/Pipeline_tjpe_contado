import os
from supabase import create_client, Client
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text

# Carrega variáveis de ambiente
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Configurações Origem (Via API REST do Supabase)
SRC_URL = os.getenv("SUPABASE_URL")
SRC_KEY = os.getenv("SUPABASE_KEY")

# Configurações Destino (Via Pooler para o DW)
DW_HOST = "aws-1-sa-east-1.pooler.supabase.com"
DW_USER = "postgres.owpqwkntxojqnpyfebal"
DW_PASS = "Nk6/4Q-_Aq8ukW!"
DW_DB = "postgres"
DW_PORT = 6543

TABLES = ["processes", "users", "status", "nucleos", "prioridades"]

def get_src_client() -> Client:
    return create_client(SRC_URL, SRC_KEY)

def check_counts():
    print("--- Verificação de Contagem de Registros ---")
    src_supabase = get_src_client()
    dw_engine = create_engine(f'postgresql://{DW_USER}:{DW_PASS}@{DW_HOST}:{DW_PORT}/{DW_DB}')
    
    for table in TABLES:
        # Origem
        res = src_supabase.table(table).select("*", count="exact").limit(1).execute()
        src_count = res.count
        
        # Destino
        try:
            with dw_engine.connect() as conn:
                res_dw = conn.execute(text(f"SELECT count(*) FROM bronze.{table}"))
                dw_count = res_dw.scalar()
        except Exception as e:
            dw_count = f"ERRO: {e}"
            
        print(f"Tabela: {table}")
        print(f"  Origem (Supabase API): {src_count}")
        print(f"  Destino (DW Bronze):    {dw_count}")
        if src_count == dw_count:
            print("  [OK] Contagens batem.")
        else:
            print("  [!!] DIVERGÊNCIA ENCONTRADA!")

if __name__ == "__main__":
    check_counts()
