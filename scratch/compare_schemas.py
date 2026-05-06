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

def compare_schemas():
    print("--- Comparação de Esquemas (Colunas) ---")
    src_supabase = get_src_client()
    dw_engine = create_engine(f'postgresql://{DW_USER}:{DW_PASS}@{DW_HOST}:{DW_PORT}/{DW_DB}')
    
    for table in TABLES:
        # Origem (Pegar 1 linha)
        res = src_supabase.table(table).select("*").limit(1).execute()
        if res.data:
            src_cols = set(res.data[0].keys())
        else:
            src_cols = set()
            
        # Destino
        try:
            df_dw = pd.read_sql(f"SELECT * FROM bronze.{table} LIMIT 1", dw_engine)
            dw_cols = set(df_dw.columns)
        except Exception as e:
            dw_cols = set([f"ERRO: {e}"])
            
        print(f"Tabela: {table}")
        print(f"  Colunas Origem: {len(src_cols)}")
        print(f"  Colunas Destino: {len(dw_cols)}")
        
        missing_in_dw = src_cols - dw_cols
        extra_in_dw = dw_cols - src_cols
        
        if missing_in_dw:
            print(f"  [!!] Faltando no DW: {missing_in_dw}")
        if extra_in_dw and not any("ERRO" in str(x) for x in extra_in_dw):
            print(f"  [..] Extra no DW: {extra_in_dw}")
        if not missing_in_dw:
            print("  [OK] Todas as colunas da origem estão no DW.")

if __name__ == "__main__":
    compare_schemas()
