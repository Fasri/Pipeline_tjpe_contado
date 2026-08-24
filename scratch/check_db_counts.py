import os
import sys
from pathlib import Path
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DW_HOST = os.getenv("DW_HOST")
DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB")
DW_PORT = int(os.getenv("DW_PORT", 6543))

SRC_URL = os.getenv("SUPABASE_URL")
SRC_KEY = os.getenv("SUPABASE_KEY")

def check():
    print("=== VERIFICANDO CONTAGENS EM PRODUÇÃO E NO DW ===")
    
    # 1. Checar via API REST do Supabase (Origem de Produção)
    if SRC_URL and SRC_KEY:
        try:
            sp = create_client(SRC_URL, SRC_KEY)
            res_total = sp.table("processes").select("id", count="exact").limit(1).execute()
            res_pend = sp.table("processes").select("id", count="exact").ilike("status", "Pendente%").limit(1).execute()
            print(f"Supabase REST API (Produção):")
            print(f"  -> Total de linhas em 'processes': {res_total.count}")
            print(f"  -> Pendentes em 'processes': {res_pend.count}")
        except Exception as e:
            print(f"Erro ao consultar Supabase REST API: {e}")

    # 2. Checar via conexão direta no PostgreSQL do DW
    encoded_pass = urllib.parse.quote_plus(DW_PASS)
    engine = create_engine(f'postgresql://{DW_USER}:{encoded_pass}@{DW_HOST}:{DW_PORT}/{DW_DB}')
    
    with engine.connect() as conn:
        print("\nPostgreSQL DW (Conexão Direta):")
        
        # Schema public
        pub_exists = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processes');")).scalar()
        if pub_exists:
            p_total = conn.execute(text("SELECT COUNT(*) FROM public.processes;")).scalar()
            p_pend = conn.execute(text("SELECT COUNT(*) FROM public.processes WHERE LOWER(TRIM(status)) = 'pendente';")).scalar()
            print(f"  -> Schema public.processes (Total): {p_total}")
            print(f"  -> Schema public.processes (Pendentes): {p_pend}")
        else:
            print("  -> Schema public.processes NÃO EXISTE!")

        # Schema bronze
        brz_exists = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'bronze' AND tablename = 'processes');")).scalar()
        if brz_exists:
            b_total = conn.execute(text("SELECT COUNT(*) FROM bronze.processes;")).scalar()
            b_pend = conn.execute(text("SELECT COUNT(*) FROM bronze.processes WHERE LOWER(TRIM(status)) = 'pendente';")).scalar()
            print(f"  -> Schema bronze.processes (Total): {b_total}")
            print(f"  -> Schema bronze.processes (Pendentes): {b_pend}")

if __name__ == "__main__":
    check()
