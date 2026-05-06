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

def test_full_fetch():
    print("--- Teste de Busca Completa (Paginada) ---")
    src_supabase = get_src_client()
    table = "processes"
    
    all_data = []
    page_size = 1000
    start = 0
    
    # Pegar contagem exata primeiro
    res_count = src_supabase.table(table).select("*", count="exact").limit(1).execute()
    total_expected = res_count.count
    print(f"Total esperado (contagem exata): {total_expected}")
    
    while True:
        print(f"Buscando range {start} a {start + page_size - 1}...")
        response = src_supabase.table(table).select("*").range(start, start + page_size - 1).execute()
        data = response.data
        if not data:
            print("Nenhum dado retornado neste range.")
            break
        all_data.extend(data)
        print(f"  Encontrados: {len(data)} | Acumulado: {len(all_data)}")
        if len(data) < page_size:
            print("Última página alcançada.")
            break
        start += page_size
        
        # Para o teste não demorar muito, vamos parar em 5000 se o total for muito grande, 
        # mas aqui queremos verificar se falta algo no final.
        # No entanto, 196k vai demorar. Vamos tentar pelo menos as primeiras páginas e as últimas.
    
    print(f"Total recuperado: {len(all_data)}")
    if len(all_data) == total_expected:
        print("[OK] Recuperação total bate com a contagem.")
    else:
        print(f"[!!] FALHA NA RECUPERAÇÃO! Diferença: {total_expected - len(all_data)}")

if __name__ == "__main__":
    test_full_fetch()
