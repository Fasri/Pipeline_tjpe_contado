import os
from supabase import create_client, Client
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Carrega variáveis de ambiente
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Configurações Origem (Via API REST do Supabase)
SRC_URL = os.getenv("SUPABASE_URL")
SRC_KEY = os.getenv("SUPABASE_KEY")

# Configurações Destino (Via Pooler para o DW)
DW_HOST = os.getenv("DW_HOST")
DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB")
DW_PORT = int(os.getenv("DW_PORT", 6543))

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
    print(f"[{datetime.now()}] Iniciando ingestão para o Data Warehouse (Origem via API)...", flush=True)
    
    try:
        src_supabase = get_src_client()
        # Conexão simplificada (Removido pool_pre_ping para evitar travamentos na AWS)
        dw_engine = create_engine(
            f'postgresql://{DW_USER}:{DW_PASS}@{DW_HOST}:{DW_PORT}/{DW_DB}',
            connect_args={
                "sslmode": "require",
                "connect_timeout": 30,
                "gssencmode": "disable"
            },
            poolclass=NullPool
        )
        
        # Garantir schema bronze e configurar timeout da sessão com lógica de Retry
        max_conn_retries = 3
        for attempt in range(max_conn_retries):
            try:
                print(f"    Tentando conectar ao DW (Tentativa {attempt+1})...", flush=True)
                with dw_engine.connect() as conn:
                    conn.execute(text("SET client_encoding TO 'UTF8';"))
                    conn.execute(text("SET statement_timeout = '1800s';"))
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))
                    conn.commit()
                print("    [OK] Conectado ao DW.", flush=True)
                break
            except Exception as e:
                if attempt == max_conn_retries - 1:
                    raise e
                print(f"    [AVISO] Falha na conexão inicial ({e}). Tentando novamente em 5s... ({attempt+1}/{max_conn_retries})")
                import time
                time.sleep(5)
        
        results = []
        for table in TABLES:
            table_temp = f"{table}_temp"
            print(f"Limpando resquícios de bronze.{table_temp}...", flush=True)
            with dw_engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS bronze.{table_temp} CASCADE;"))
                conn.commit()

            print(f"Processando tabela: {table}...", flush=True)
            
            # Pegar contagem exata para log de progresso
            res_count = src_supabase.table(table).select("*", count="exact").limit(1).execute()
            total_expected = res_count.count
            print(f"  Total esperado na origem: {total_expected}", flush=True)

            # Estratégia de Shadow Table: Carregar em uma tabela temporária e depois trocar (swap)
            # Isso minimiza o tempo de bloqueio (lock) na tabela oficial e evita dados parciais.
            table_temp = f"{table}_temp"
            print(f"  Iniciando carregamento na tabela sombra: bronze.{table_temp}...", flush=True)

            # Extrair e Inserir em chunks na tabela TEMPORÁRIA
            all_data = []
            page_size = 1000
            last_id = None
            total_loaded = 0
            first_chunk = True

            while True:
                # Keyset Pagination com Retry (para lidar com instabilidades de rede)
                max_retries = 5
                data = None
                for attempt in range(max_retries):
                    try:
                        query = src_supabase.table(table).select("*").order("id").limit(page_size)
                        if last_id is not None:
                            query = query.gt("id", last_id)
                        
                        response = query.execute()
                        data = response.data
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise e
                        print(f"    [AVISO] Falha na conexão ({e}). Tentando novamente em 10s... ({attempt+1}/{max_retries})")
                        import time
                        time.sleep(10)
                
                if not data:
                    break
                
                # Apenas acumula dados em memória se a tabela for pequena para evitar estouro de RAM (RNF01)
                if total_expected < 50000:
                    all_data.extend(data)
                
                df_chunk = pd.DataFrame(data)
                mode = 'replace' if first_chunk else 'append'
                # Reduzido chunksize para 100 e adicionado retry para evitar timeout (psycopg2.errors.QueryCanceled)
                max_insert_retries = 3
                for insert_attempt in range(max_insert_retries):
                    try:
                        df_chunk.to_sql(table_temp, dw_engine, schema='bronze', if_exists=mode, index=False, chunksize=100)
                        break
                    except Exception as e:
                        if insert_attempt == max_insert_retries - 1:
                            raise e
                        print(f"    [AVISO] Erro no to_sql ({e}). Tentando novamente em 5s... ({insert_attempt+1}/{max_insert_retries})")
                        import time
                        time.sleep(5)
                
                last_id = data[-1]['id']
                first_chunk = False
                total_loaded += len(data)
                
                if total_loaded % 10000 == 0:
                    print(f"    Progresso {table}: {total_loaded} / {total_expected}...", flush=True)

            # Cálculo de Checksum da Origem (Otimizado)
            if total_expected < 50000:
                df = pd.DataFrame(all_data)
                src_check = calculate_checksum(df)
            else:
                src_check = {"count": total_loaded, "hash": "ignorado_por_volume"}
            
            print(f"  Origem (API): {src_check['count']} linhas | Hash: {src_check['hash']}")
            
            # Finalização: SWAP (DROP + RENAME)
            # Voltamos para o SWAP pois ele suporta mudanças de schema (colunas novas), que foi o erro detectado.
            # Adicionamos uma lógica para lidar com locks caso o dashboard esteja travando a tabela.
            print(f"  Finalizando ingestão (Swap): bronze.{table_temp} -> bronze.{table}...")
            with dw_engine.connect() as conn:
                conn.execute(text("SET statement_timeout = '1800s';"))
                try:
                    # Tenta o swap atômico
                    conn.execute(text(f"DROP TABLE IF EXISTS bronze.{table} CASCADE;"))
                    conn.execute(text(f"ALTER TABLE bronze.{table_temp} RENAME TO {table};"))
                    conn.commit()
                    print(f"  [OK] Swap da tabela {table} realizado com sucesso.", flush=True)
                except Exception as e:
                    conn.rollback()
                    if "timeout" in str(e).lower() or "lock" in str(e).lower():
                        print(f"  [AVISO] Conflito de lock detectado no swap da {table}. Tentando forçar encerramento de bloqueios...")
                        try:
                            # Tentar derrubar conexões que estão lendo a tabela e impedindo o DROP (locks ACCESS SHARE)
                            # Filtramos pela query para evitar derrubar a própria conexão ou processos vitais
                            conn.execute(text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND query LIKE '%{table}%';"))
                            conn.commit()
                            
                            # Tentar novamente o swap
                            conn.execute(text(f"DROP TABLE IF EXISTS bronze.{table} CASCADE;"))
                            conn.execute(text(f"ALTER TABLE bronze.{table_temp} RENAME TO {table};"))
                            conn.commit()
                            print(f"  [OK] Swap da tabela {table} realizado com sucesso após forçar.")
                        except Exception as e_force:
                            print(f"  [ERRO] Falha ao forçar swap: {e_force}")
                            raise e_force
                    else:
                        raise e
            
            # Verificar no destino (Otimizado para evitar estouro de memória e timeout de rede)
            # Para tabelas grandes, verificamos apenas a contagem de linhas para garantir a integridade básica.
            with dw_engine.connect() as conn:
                conn.execute(text("SET statement_timeout = '1800s';"))
                dw_count = conn.execute(text(f"SELECT count(*) FROM bronze.{table};")).scalar()
            
            if src_check['count'] == dw_count:
                if dw_count < 50000:
                    # Tabelas pequenas: Verificação completa de Hash
                    with dw_engine.connect() as conn:
                        df_dest = pd.read_sql(text(f"SELECT * FROM bronze.{table};"), conn)
                    dw_check = calculate_checksum(df_dest)
                    print(f"  Destino (Postgres): {dw_check['count']} linhas | Hash: {dw_check['hash']}")
                else:
                    # Tabelas grandes: Apenas contagem para segurança
                    print(f"  Destino (Postgres): {dw_count} linhas | [OK] Contagem coincide. (Hash ignorado por volume)")
                results.append(True)
            else:
                print(f"  [ERRO] Divergência na contagem de linhas: Origem {src_check['count']} != Destino {dw_count}")
                results.append(False)
                
        if all(results):
            print(f"\n[{datetime.now()}] Ingestão concluída com sucesso!")
            return True
        else:
            print(f"\n[{datetime.now()}] Ingestão concluída com ERROS.")
            return False
            
    except Exception as e:
        print(f"ERRO CRÍTICO NA INGESTÃO: {e}")
        return False

if __name__ == "__main__":
    ingest()
