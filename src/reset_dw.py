import os
import sys
from pathlib import Path
from datetime import datetime
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from supabase import create_client
import subprocess

# Carrega variáveis de ambiente
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Supabase Produção (Origem)
SRC_URL = os.getenv("SUPABASE_URL")
SRC_KEY = os.getenv("SUPABASE_KEY")

# Data Warehouse Postgres (Destino)
DW_HOST = os.getenv("DW_HOST")
DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB")
DW_PORT = int(os.getenv("DW_PORT", 6543))

TABLES = ["processes", "users", "status", "nucleos", "prioridades"]

def fetch_table_from_supabase(sp_client, table):
    """Carrega todos os dados de uma tabela da API REST do Supabase via Keyset Pagination."""
    print(f"  [PRODUÇÃO] Baixando dados completos da tabela '{table}' via API Supabase...")
    all_data = []
    page_size = 1000
    last_id = None
    
    # Verifica se a tabela possui id
    try:
        while True:
            query = sp_client.table(table).select("*").order("id").limit(page_size)
            if last_id is not None:
                query = query.gt("id", last_id)
            resp = query.execute()
            data = resp.data
            if not data:
                break
            all_data.extend(data)
            last_id = data[-1]['id']
            if len(data) < page_size:
                break
            if len(all_data) % 10000 == 0 or len(data) < page_size:
                print(f"    -> Baixadas {len(all_data)} linhas até agora...", flush=True)
    except Exception as e:
        print(f"  [AVISO] Paging por ID falhou para {table} ({e}). Tentando offset...")
        start = 0
        while True:
            resp = sp_client.table(table).select("*").range(start, start + page_size - 1).execute()
            data = resp.data
            if not data:
                break
            all_data.extend(data)
            if len(data) < page_size:
                break
            start += page_size
            
    print(f"  [OK] Baixados {len(all_data)} registros no total de 'public.{table}'.")
    return pd.DataFrame(all_data) if all_data else pd.DataFrame()

def reset_dw_from_production():
    print(f"[{datetime.now()}] === INICIANDO RESET COMPLETO DO DW DIRETAMENTE DA PRODUÇÃO (SUPABASE REST) ===")
    
    if not all([SRC_URL, SRC_KEY]):
        print("[ERRO CRÍTICO] SUPABASE_URL e SUPABASE_KEY não configurados!")
        sys.exit(1)
        
    if not all([DW_HOST, DW_USER, DW_PASS, DW_DB]):
        print("[ERRO CRÍTICO] Variáveis do DW não configuradas no .env!")
        sys.exit(1)

    sp_client = create_client(SRC_URL, SRC_KEY)
    
    encoded_pass = urllib.parse.quote_plus(DW_PASS)
    dw_engine = create_engine(
        f'postgresql://{DW_USER}:{encoded_pass}@{DW_HOST}:{DW_PORT}/{DW_DB}',
        connect_args={
            "sslmode": "require",
            "connect_timeout": 30,
            "gssencmode": "disable"
        },
        poolclass=NullPool
    )

    with dw_engine.connect() as conn:
        print("\n1/4 - Garantindo existência do schema 'bronze'...")
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))
        conn.commit()

    for table in TABLES:
        print(f"\n==========================================")
        print(f"Processando tabela de produção: {table}")
        print(f"==========================================")
        
        # 1. Buscar os dados da produção (Tenta backup recente em CSV se existir, senão via API REST)
        df_data = None
        backup_base = BASE_DIR / "data_transform" / "backups"
        if backup_base.exists():
            dirs = sorted([d for d in backup_base.iterdir() if d.is_dir()])
            if dirs:
                latest_backup = dirs[-1]
                csv_file = latest_backup / f"{table}.csv"
                if csv_file.exists():
                    print(f"  [BACKUP LOCAL] Encontrado backup recente em {csv_file.name}. Carregando...")
                    try:
                        df_data = pd.read_csv(csv_file, low_memory=False)
                        print(f"  [OK] Carregadas {len(df_data)} linhas do backup local.")
                    except Exception as err:
                        print(f"  [AVISO] Falha ao ler CSV local ({err}). Baixando via API...")
                        df_data = None

        if df_data is None or df_data.empty:
            print(f"  [LIVE API] Baixando a versão mais recente em tempo real da tabela '{table}' via API Supabase...")
            df_data = fetch_table_from_supabase(sp_client, table)
            
        if df_data.empty:
            print(f"  [AVISO] Tabela {table} vazia ou sem dados na produção.")
            continue

        # Tratar booleanos e tipos
        if 'pje' in df_data.columns:
            df_data['pje'] = df_data['pje'].astype(str).str.lower().map({'true': True, '1': True, '1.0': True, 'false': False, '0': False, '0.0': False}).fillna(True)
        if 'assigned_to_id' in df_data.columns:
            df_data['assigned_to_id'] = df_data['assigned_to_id'].astype(str)

        # 2. Reconstruir a estrutura e Limpar bronze.{table}
        with dw_engine.connect() as conn:
            if table == "processes":
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS bronze.processes (
                        id SERIAL PRIMARY KEY,
                        number TEXT,
                        entry_date TEXT,
                        court TEXT,
                        nucleus TEXT,
                        priority TEXT,
                        status TEXT,
                        position INT,
                        priority_position INT,
                        assigned_to_id TEXT,
                        completion_date TEXT,
                        valor_custas NUMERIC,
                        observacao TEXT,
                        pje BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))
                try:
                    conn.execute(text("ALTER TABLE bronze.processes ALTER COLUMN assigned_to_id TYPE TEXT;"))
                except Exception:
                    pass
            else:
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS bronze.{table} (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        nome TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))
            conn.commit()

            print(f"  [LIMPEZA] Truncando bronze.{table}...")
            conn.execute(text(f"TRUNCATE TABLE bronze.{table} RESTART IDENTITY CASCADE;"))
            conn.commit()

        # 3. Enviar dados para o DW em lotes (to_sql)
        print(f"  [CARGA] Inserindo {len(df_data)} linhas na tabela bronze.{table}...")
        # Selecionar apenas colunas que pertencem à tabela de destino
        with dw_engine.connect() as conn:
            brz_cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='bronze' AND table_name='{table}'")).scalars().all()
            
        valid_cols = [c for c in df_data.columns if c in brz_cols]
        df_to_insert = df_data[valid_cols].copy()
        
        df_to_insert.to_sql(
            table, 
            dw_engine, 
            schema='bronze', 
            if_exists='append', 
            index=False, 
            chunksize=5000, 
            method='multi'
        )
        print(f"  [OK] Carga de {len(df_to_insert)} linhas concluída em bronze.{table}!")

        # 4. Criar Índices e Constraints
        if table == "processes":
            with dw_engine.connect() as conn:
                print("  [INDEX] Recriando índices e constraints em bronze.processes...")
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_bronze_processes_key') THEN
                            ALTER TABLE bronze.processes ADD CONSTRAINT unique_bronze_processes_key UNIQUE (number, entry_date, nucleus);
                        END IF;
                    EXCEPTION WHEN OTHERS THEN NULL;
                    END $$;
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_status ON bronze.processes(status);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_assigned ON bronze.processes(assigned_to_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_nucleus ON bronze.processes(nucleus);"))
                conn.commit()

    print("\n3/4 - Executando dbt para reconstruir camadas Silver e Gold...")
    try:
        cmd = ["uv", "run", "dbt", "run", "--profiles-dir", "dbt_contadoria", "--project-dir", "dbt_contadoria"]
        print(f"Executando: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("dbt Output:\n", result.stdout)
    except Exception as e:
        print(f"[AVISO] Falha na execução do dbt: {e}")

    # Verificar contagem final com retry contra instabilidades do Supabase Pooler
    for attempt in range(3):
        try:
            with dw_engine.connect() as conn:
                print("\n4/4 - === CONTAGEM E VERIFICAÇÃO FINAL DOS PROCESSOS PENDENTES ===")
                b_total = conn.execute(text("SELECT COUNT(*) FROM bronze.processes;")).scalar()
                b_pend = conn.execute(text("SELECT COUNT(*) FROM bronze.processes WHERE LOWER(TRIM(status)) = 'pendente';")).scalar()
                
                s_exists = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'silver' AND tablename = 'slv_processos');")).scalar()
                s_pend = conn.execute(text("SELECT COUNT(*) FROM silver.slv_processos WHERE LOWER(TRIM(status_atual)) = 'pendente';")).scalar() if s_exists else "N/A"
                
                g_exists = conn.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'gold' AND tablename = 'gld_processos_pendentes');")).scalar()
                g_pend = conn.execute(text("SELECT COUNT(*) FROM gold.gld_processos_pendentes;")).scalar() if g_exists else "N/A"

                print(f"  -> Bronze Total: {b_total} | Pendentes: {b_pend}")
                print(f"  -> Silver Pendentes: {s_pend}")
                print(f"  -> Gold Pendentes: {g_pend}")
                break
        except Exception as err:
            if attempt == 2:
                print(f"[AVISO] Não foi possível conectar ao DW para checar a contagem final ({err}), mas a carga e o dbt foram concluídos.")
            else:
                import time
                time.sleep(3)

    print(f"\n[{datetime.now()}] === RESET DO DW CONCLUÍDO COM SUCESSO A PARTIR DA PRODUÇÃO REAL! ===")

if __name__ == "__main__":
    reset_dw_from_production()
