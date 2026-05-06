import os
from supabase import create_client, Client
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Carrega variáveis de ambiente
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Configurações Origem (Via API REST do Supabase)
SRC_URL = os.getenv("SUPABASE_URL")
SRC_KEY = os.getenv("SUPABASE_KEY")

def get_src_client() -> Client:
    return create_client(SRC_URL, SRC_KEY)

def check_duplicates():
    print("--- Verificando Duplicatas no Banco de Produção ---")
    src_supabase = get_src_client()
    
    # Vamos pegar uma amostra ou usar uma query RPC se disponível, 
    # mas como não sabemos os RPCs, vamos fazer via Python para uma parte dos dados.
    # Na verdade, a restrição de conflito no upsert já evita duplicatas por (number, entry_date, nucleus).
    
    # O usuário disse que está FALTANDO dados.
    # Vamos verificar se o arquivo CSV original tem mais dados do que o banco.
    
    csv_path = BASE_DIR / "data_transform" / "tempo_real_Consolidado_supabase.csv"
    if os.path.exists(csv_path):
        df_csv = pd.read_csv(csv_path)
        print(f"Linhas no CSV Consolidado: {len(df_csv)}")
        
        # Agora vamos contar no banco
        res = src_supabase.table("processes").select("*", count="exact").limit(1).execute()
        print(f"Linhas no Banco (Tabela processes): {res.count}")
        
        if len(df_csv) > res.count:
             print(f"Aviso: O CSV tem mais linhas ({len(df_csv)}) que o banco ({res.count}).")
        else:
             print("O banco tem mais ou igual número de linhas que o CSV (esperado, pois o banco acumula histórico).")
    else:
        print("Arquivo CSV consolidado não encontrado para comparação.")

if __name__ == "__main__":
    check_duplicates()
