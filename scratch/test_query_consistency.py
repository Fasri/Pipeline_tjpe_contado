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

def get_src_client() -> Client:
    return create_client(SRC_URL, SRC_KEY)

def compare_specific_query():
    print("--- Teste de Consistência de Dados Específicos ---")
    user_id = '17f98528-f601-4702-852e-bcd976f0c5e5'
    start_date = '2026-04-01'
    end_date = '2026-04-30'
    
    # 1. Produção (via Supabase API)
    src_supabase = get_src_client()
    # Usando filtros da API do Supabase equivalente à query SQL
    res_src = src_supabase.table("processes") \
        .select("*", count="exact") \
        .eq("assigned_to_id", user_id) \
        .gte("completion_date", start_date) \
        .lte("completion_date", end_date) \
        .limit(1) \
        .execute()
    
    src_count = res_src.count
    
    # 2. DW Bronze (via SQLAlchemy)
    dw_engine = create_engine(f'postgresql://{DW_USER}:{DW_PASS}@{DW_HOST}:{DW_PORT}/{DW_DB}')
    query_dw = text("""
        SELECT count(*) 
        FROM bronze.processes 
        WHERE assigned_to_id = :user_id 
        AND completion_date BETWEEN :start_date AND :end_date
    """)
    
    try:
        with dw_engine.connect() as conn:
            res_dw = conn.execute(query_dw, {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            })
            dw_count = res_dw.scalar()
    except Exception as e:
        dw_count = f"ERRO: {e}"
        
    print(f"Filtro: assigned_to_id = '{user_id}'")
    print(f"Datas: {start_date} até {end_date}")
    print(f"\nResultado:")
    print(f"  Produção (Supabase): {src_count}")
    print(f"  DW Bronze (Postgres): {dw_count}")
    
    if src_count == dw_count:
        print("\n[OK] As quantidades são IDÊNTICAS.")
    else:
        print("\n[!!] DIVERGÊNCIA DETECTADA!")

if __name__ == "__main__":
    compare_specific_query()
