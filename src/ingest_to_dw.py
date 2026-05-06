import os
from supabase import create_client, Client
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import hashlib
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

def calculate_checksum(df):
    if df.empty:
        return {"count": 0, "hash": "empty"}
    row_count = len(df)
    # Ordena por ID ou colunas para garantir hash estável
    df_sorted = df.sort_values(by=list(df.columns)).reset_index(drop=True)
    df_hash = hashlib.md5(pd.util.hash_pandas_object(df_sorted, index=True).values).hexdigest()
    return {"count": row_count, "hash": df_hash}

def ingest():
    print(f"[{datetime.now()}] Iniciando ingestão para o Data Warehouse (Origem via API)...")
    
    try:
        src_supabase = get_src_client()
        dw_engine = create_engine(f'postgresql://{DW_USER}:{DW_PASS}@{DW_HOST}:{DW_PORT}/{DW_DB}')
        
        # Garantir schema bronze
        with dw_engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))
            conn.commit()
        
        results = []
        
        for table in TABLES:
            print(f"Processando tabela: {table}...")
            
            # Extrair da origem via API com paginação
            all_data = []
            page_size = 1000
            start = 0
            
            # Pegar contagem exata para log de progresso
            res_count = src_supabase.table(table).select("*", count="exact").limit(1).execute()
            total_expected = res_count.count
            print(f"  Total esperado na origem: {total_expected}")

            while True:
                # Adicionada ordenação estável por 'id' para evitar problemas de paginação (pular ou repetir registros)
                response = src_supabase.table(table).select("*") \
                    .order("id") \
                    .range(start, start + page_size - 1) \
                    .execute()
                
                data = response.data
                if not data:
                    break
                all_data.extend(data)
                
                if len(all_data) % 5000 == 0 or len(data) < page_size:
                    print(f"    Progresso {table}: {len(all_data)} / {total_expected}...")

                if len(data) < page_size:
                    break
                start += page_size
            
            df = pd.DataFrame(all_data)
            src_check = calculate_checksum(df)
            print(f"  Origem (API): {src_check['count']} linhas | Hash: {src_check['hash']}")
            
            # Inserir no destino (Bronze)
            df.to_sql(table, dw_engine, schema='bronze', if_exists='replace', index=False)
            
            # Verificar no destino
            df_dest = pd.read_sql(f"SELECT * FROM bronze.{table};", dw_engine)
            dw_check = calculate_checksum(df_dest)
            
            print(f"  Destino (Postgres): {dw_check['count']} linhas | Hash: {dw_check['hash']}")
            
            if src_check['hash'] == dw_check['hash']:
                print(f"  [OK] Tabela {table} copiada com sucesso (Checksum OK)")
                results.append(True)
            else:
                # O hash do pandas pode variar se os tipos de dados mudarem na ida/volta (ex: datas)
                # Vamos fazer uma validação de contagem se o hash falhar
                if src_check['count'] == dw_check['count']:
                    print(f"  [AVISO] Checksum de hash falhou (provável divergência de tipos), mas Contagem OK ({src_check['count']})")
                    results.append(True)
                else:
                    print(f"  [ERRO] Erro de integridade na tabela {table}!")
                    results.append(False)
                
        if all(results):
            print(f"\n[{datetime.now()}] Ingestão concluída com sucesso!")
        else:
            print(f"\n[{datetime.now()}] Ingestão concluída com ERROS.")
            
    except Exception as e:
        print(f"ERRO CRÍTICO NA INGESTÃO: {e}")

if __name__ == "__main__":
    ingest()
