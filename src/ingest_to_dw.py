import os
from supabase import create_client, Client
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

import urllib.parse

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

def find_latest_backup_dir():
    backup_base = BASE_DIR / "data_transform" / "backups"
    if not backup_base.exists():
        return None
    dirs = [d for d in backup_base.iterdir() if d.is_dir()]
    if not dirs:
        return None
    latest = sorted(dirs)[-1]
    try:
        folder_time = datetime.strptime(latest.name, "%Y%m%d_%H%M%S")
        # Considera o backup válido se foi gerado nas últimas 3 horas
        if (datetime.now() - folder_time).total_seconds() > 3 * 3600:
            print(f"  [AVISO] O backup mais recente encontrado ({latest.name}) tem mais de 3 horas. Ignorando para evitar dados desatualizados.", flush=True)
            return None
    except Exception:
        pass
    return latest


def ingest(backup_dir=None):
    if backup_dir is None:
        backup_dir = find_latest_backup_dir()
        if backup_dir:
            print(f"[{datetime.now()}] Pasta de backup recente detectada dinamicamente: {backup_dir.name}", flush=True)
            
    print(f"[{datetime.now()}] Iniciando ingestão para o Data Warehouse (Backup: {backup_dir.name if backup_dir else 'Origem via API'})...", flush=True)
    
    try:
        src_supabase = get_src_client()
        encoded_pass = urllib.parse.quote_plus(DW_PASS) if DW_PASS else ""
        # Conexão simplificada (Removido pool_pre_ping para evitar travamentos na AWS)
        dw_engine = create_engine(
            f'postgresql://{DW_USER}:{encoded_pass}@{DW_HOST}:{DW_PORT}/{DW_DB}',
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
                    conn.execute(text("SET statement_timeout = '120s';"))
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))
                    conn.commit()
                print("    [OK] Conectado ao DW.", flush=True)
                break
            except Exception as e:
                err_str = str(e)
                if "EAUTHQUERY" in err_str or "connection to database not available" in err_str:
                    proj_ref = DW_USER.split('.')[-1] if DW_USER and '.' in DW_USER else DW_USER
                    print(f"    [ERRO SUPABASE] A instância do PostgreSQL no Supabase (projeto DW: {proj_ref}) está PAUSADA ou indisponível.", flush=True)
                    print(f"    -> SOLUÇÃO: Acesse o painel do Supabase (https://supabase.com/dashboard/project/{proj_ref}) e clique em 'Restore project' para reativar o banco de dados.", flush=True)
                if attempt == max_conn_retries - 1:
                    raise e
                print(f"    [AVISO] Falha na conexão inicial ({e}). Tentando novamente em 5s... ({attempt+1}/{max_conn_retries})")
                import time
                time.sleep(5)
        
        results = []
        for table in TABLES:
            stg_table = f"stg_{table}"
            print(f"\nProcessando tabela de forma incremental: {table}...", flush=True)
            
            # 1. Garantir que a tabela final no schema bronze existe
            with dw_engine.connect() as conn:
                conn.execute(text("SET statement_timeout = '120s';"))
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
                    # Garantir que assigned_to_id seja TEXT em tabelas pré-existentes
                    try:
                        conn.execute(text("ALTER TABLE bronze.processes ALTER COLUMN assigned_to_id TYPE TEXT;"))
                        conn.commit()
                    except Exception:
                        conn.rollback()

                    # Garantir constraint de unicidade para o ON CONFLICT
                    try:
                        conn.execute(text("""
                            DO $$
                            BEGIN
                                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_bronze_processes_key') THEN
                                    ALTER TABLE bronze.processes ADD CONSTRAINT unique_bronze_processes_key UNIQUE (number, entry_date, nucleus);
                                END IF;
                            END $$;
                        """))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_status ON bronze.processes(status);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_assigned ON bronze.processes(assigned_to_id);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_nucleus ON bronze.processes(nucleus);"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bronze_proc_composite ON bronze.processes(number, entry_date, nucleus);"))
                        try:
                            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_public_proc_composite ON public.processes(number, entry_date, nucleus);"))
                        except Exception:
                            pass
                        conn.commit()
                    except Exception as e_c:
                        conn.rollback()
                else:
                    # Tabelas auxiliares
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS bronze.{table} (
                            id TEXT PRIMARY KEY,
                            name TEXT,
                            nome TEXT,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        );
                    """))
                    try:
                        conn.execute(text(f"ALTER TABLE bronze.{table} ALTER COLUMN id TYPE TEXT;"))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                conn.commit()

            # 2. Carregar dados para a tabela temporária de staging
            with dw_engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS bronze.{stg_table} CASCADE;"))
                conn.commit()

            df_table = None
            total_loaded = 0
            has_public_table = False
            
            # Verificar se a tabela existe no schema public (PostgreSQL direto)
            with dw_engine.connect() as conn:
                chk = conn.execute(text(f"SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = '{table}');")).scalar()
                has_public_table = bool(chk)

            if has_public_table and not backup_dir:
                print(f"  [OK] Cópia direta SQL rápida detectada (public.{table} -> bronze.{table})...", flush=True)
                with dw_engine.connect() as conn:
                    conn.execute(text("SET statement_timeout = '120s';"))
                    if table == "processes":
                        # Obter colunas reais da public.processes
                        pub_cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='processes'")).scalars().all()
                        brz_cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='bronze' AND table_name='processes'")).scalars().all()
                        
                        common_cols = [c for c in pub_cols if c in brz_cols and c not in ['id']]
                        if 'updated_at' not in common_cols:
                            common_cols.append('updated_at')

                        col_names = ", ".join(common_cols)
                        
                        # Construir expressão de SELECT com fallback para colunas faltantes na origem
                        select_exprs = []
                        for c in common_cols:
                            if c == 'updated_at':
                                if 'updated_at' in pub_cols:
                                    select_exprs.append("COALESCE(NULLIF(updated_at::text, '')::timestamptz, NOW()) AS updated_at")
                                else:
                                    select_exprs.append("NOW() AS updated_at")
                            elif c == 'created_at':
                                if 'created_at' in pub_cols:
                                    select_exprs.append("NULLIF(created_at::text, '')::timestamptz AS created_at")
                                else:
                                    select_exprs.append("NOW() AS created_at")
                            elif c in pub_cols:
                                select_exprs.append(c)
                            else:
                                select_exprs.append(f"NULL AS {c}")
                        select_sql = ", ".join(select_exprs)

                        upd_cols = [c for c in common_cols if c not in ['number', 'entry_date', 'nucleus', 'created_at', 'updated_at']]
                        update_assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in upd_cols])
                        if update_assignments:
                            update_assignments += ", updated_at = NOW()"
                        else:
                            update_assignments = "updated_at = NOW()"
                        distinct_checks = " OR ".join([f"bronze.processes.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in upd_cols])

                        # Sincronização Incremental Inteligente (Otimizada para Supabase Free Tier):
                        # 1. Remover do bronze registros que foram excluídos na produção (public) usando NOT EXISTS (Indexável)
                        del_sql = """
                        DELETE FROM bronze.processes b
                        WHERE NOT EXISTS (
                            SELECT 1 
                            FROM public.processes p 
                            WHERE p.number = b.number 
                              AND p.entry_date = b.entry_date 
                              AND p.nucleus = b.nucleus
                        );
                        """
                        res_del = conn.execute(text(del_sql))

                        # 2. UPSERT apenas das linhas que efetivamente mudaram ou são novas
                        upsert_direct_sql = f"""
                        INSERT INTO bronze.processes ({col_names})
                        SELECT {select_sql}
                        FROM public.processes
                        ON CONFLICT (number, entry_date, nucleus)
                        DO UPDATE SET {update_assignments}
                        WHERE {distinct_checks};
                        """
                        res_d = conn.execute(text(upsert_direct_sql))
                        conn.commit()
                        print(f"  [OK] Sync incremental limpo: {res_del.rowcount} apagados, {res_d.rowcount} novos/atualizados.", flush=True)
                    else:
                        del_sql = f"""
                        DELETE FROM bronze.{table} b
                        WHERE NOT EXISTS (
                            SELECT 1 FROM public.{table} p WHERE p.id = b.id
                        );
                        """
                        conn.execute(text(del_sql))
                        
                        pub_cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='{table}'")).scalars().all()
                        col_list = [c for c in pub_cols if c in ['id', 'name', 'nome', 'created_at']]
                        col_names = ", ".join(col_list)
                        
                        update_assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in col_list if c != 'id'])
                        if update_assignments:
                            distinct_checks = " OR ".join([f"bronze.{table}.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in col_list if c != 'id'])
                            upsert_direct_sql = f"""
                            INSERT INTO bronze.{table} ({col_names})
                            SELECT {col_names} FROM public.{table}
                            ON CONFLICT (id)
                            DO UPDATE SET {update_assignments}
                            WHERE {distinct_checks};
                            """
                        else:
                            upsert_direct_sql = f"""
                            INSERT INTO bronze.{table} ({col_names})
                            SELECT {col_names} FROM public.{table}
                            ON CONFLICT (id) DO NOTHING;
                            """
                        res_d = conn.execute(text(upsert_direct_sql))
                        conn.commit()
                        print(f"  [OK] Cópia incremental de public.{table} concluída!", flush=True)

                    dw_count = conn.execute(text(f"SELECT count(*) FROM bronze.{table};")).scalar()
                    print(f"  Destino DW (Postgres): {dw_count} total de linhas em bronze.{table}.")
                    results.append(True)
                    continue

            if backup_dir:
                csv_path = Path(backup_dir) / f"{table}.csv"
                if csv_path.exists():
                    try:
                        print(f"  [OK] Carregando {table} do backup local: {csv_path.name}", flush=True)
                        df_table = pd.read_csv(csv_path)
                        total_loaded = len(df_table)
                    except Exception as csv_err:
                        print(f"  [AVISO] Falha ao ler CSV local ({csv_err}). Fallback para API REST...", flush=True)
                        df_table = None

            if df_table is not None:
                if 'pje' in df_table.columns:
                    df_table['pje'] = df_table['pje'].astype(str).str.lower().map({'true': True, '1': True, '1.0': True, 'false': False, '0': False, '0.0': False}).fillna(True)
                print(f"  Enviando {total_loaded} linhas para staging bronze.{stg_table}...", flush=True)
                df_table.to_sql(stg_table, dw_engine, schema='bronze', if_exists='replace', index=False, chunksize=5000, method='multi')
            else:
                # Fallback: API REST com retry robusto
                print(f"  Carregando {table} via API REST...", flush=True)
                all_data = []
                page_size = 1000
                last_id = None
                first_chunk = True

                while True:
                    data = None
                    for api_retry in range(3):
                        try:
                            query = src_supabase.table(table).select("*").order("id").limit(page_size)
                            if last_id is not None:
                                query = query.gt("id", last_id)
                            response = query.execute()
                            data = response.data
                            break
                        except Exception as req_err:
                            if api_retry == 2:
                                print(f"  [AVISO] Conexão API REST indisponível: {req_err}")
                                data = []
                                break
                            import time
                            time.sleep(3)

                    if not data:
                        break
                    
                    df_chunk = pd.DataFrame(data)
                    mode = 'replace' if first_chunk else 'append'
                    df_chunk.to_sql(stg_table, dw_engine, schema='bronze', if_exists=mode, index=False, chunksize=1000, method='multi')
                    
                    last_id = data[-1]['id']
                    first_chunk = False
                    total_loaded += len(data)

            # 3. Executar o BULK UPSERT condicional (Incremental)
            print(f"  Executando UPSERT incremental de bronze.{stg_table} -> bronze.{table}...", flush=True)
            with dw_engine.connect() as conn:
                conn.execute(text("SET statement_timeout = '1800s';"))
                if table == "processes":
                    # Mapear colunas existentes no staging
                    cols_stg = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='bronze' AND table_name='{stg_table}'")).scalars().all()
                    
                    col_list = [c for c in cols_stg if c in ['number', 'entry_date', 'court', 'nucleus', 'priority', 'status', 'position', 'priority_position', 'assigned_to_id', 'completion_date', 'valor_custas', 'observacao', 'pje', 'created_at', 'updated_at']]
                    col_names = ", ".join(col_list)
                    
                    select_exprs = []
                    for c in col_list:
                        if c == 'created_at':
                            select_exprs.append("NULLIF(created_at::text, '')::timestamptz AS created_at")
                        elif c == 'updated_at':
                            select_exprs.append("COALESCE(NULLIF(updated_at::text, '')::timestamptz, NOW()) AS updated_at")
                        elif c in ['position', 'priority_position']:
                            select_exprs.append(f"NULLIF({c}::text, '')::numeric::integer AS {c}")
                        elif c == 'assigned_to_id':
                            select_exprs.append("assigned_to_id::text AS assigned_to_id")
                        elif c == 'valor_custas':
                            select_exprs.append("NULLIF(valor_custas::text, '')::numeric AS valor_custas")
                        elif c == 'pje':
                            select_exprs.append("COALESCE(pje::text::boolean, true) AS pje")
                        else:
                            select_exprs.append(c)
                    select_sql = ", ".join(select_exprs)
                    
                    upd_cols = [c for c in col_list if c not in ['number', 'entry_date', 'nucleus', 'created_at', 'updated_at']]
                    update_assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in upd_cols])
                    if update_assignments:
                        update_assignments += ", updated_at = NOW()"
                    else:
                        update_assignments = "updated_at = NOW()"
                    distinct_checks = " OR ".join([f"bronze.processes.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in upd_cols])

                    # Remover do bronze registros que não existem mais na origem/staging
                    del_sql = f"""
                    DELETE FROM bronze.processes p
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM bronze.{stg_table} s
                        WHERE s.number = p.number
                          AND s.entry_date = p.entry_date
                          AND s.nucleus = p.nucleus
                    );
                    """
                    res_del = conn.execute(text(del_sql))

                    upsert_sql = f"""
                    INSERT INTO bronze.processes ({col_names})
                    SELECT {select_sql} FROM bronze.{stg_table}
                    ON CONFLICT (number, entry_date, nucleus)
                    DO UPDATE SET {update_assignments}
                    WHERE {distinct_checks};
                    """
                    result = conn.execute(text(upsert_sql))
                    conn.commit()
                    print(f"  [OK] UPSERT incremental concluído! Removidos: {res_del.rowcount}, Linhas alteradas/inseridas: {result.rowcount}", flush=True)
                else:
                    cols_stg = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='bronze' AND table_name='{stg_table}'")).scalars().all()
                    col_list = [c for c in cols_stg if c in ['id', 'name', 'nome', 'created_at']]
                    col_names = ", ".join(col_list)
                    
                    select_exprs = []
                    for c in col_list:
                        if c == 'created_at':
                            select_exprs.append("NULLIF(created_at::text, '')::timestamptz AS created_at")
                        elif c == 'id':
                            select_exprs.append("id::text AS id")
                        else:
                            select_exprs.append(c)
                    select_sql = ", ".join(select_exprs)
                    
                    update_assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in col_list if c != 'id'])
                    
                    if update_assignments:
                        distinct_checks = " OR ".join([f"bronze.{table}.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in col_list if c != 'id'])
                        upsert_sql = f"""
                        INSERT INTO bronze.{table} ({col_names})
                        SELECT {select_sql} FROM bronze.{stg_table}
                        ON CONFLICT (id)
                        DO UPDATE SET {update_assignments}
                        WHERE {distinct_checks};
                        """
                    else:
                        upsert_sql = f"""
                        INSERT INTO bronze.{table} ({col_names})
                        SELECT {select_sql} FROM bronze.{stg_table}
                        ON CONFLICT (id) DO NOTHING;
                        """
                    result = conn.execute(text(upsert_sql))
                    conn.commit()
                    print(f"  [OK] UPSERT tabela {table} concluído! Linhas alteradas/inseridas: {result.rowcount}", flush=True)

                # Limpar staging
                conn.execute(text(f"DROP TABLE IF EXISTS bronze.{stg_table} CASCADE;"))
                conn.commit()

            # 4. Verificar total de registros no destino
            with dw_engine.connect() as conn:
                dw_count = conn.execute(text(f"SELECT count(*) FROM bronze.{table};")).scalar()
                print(f"  Destino DW (Postgres): {dw_count} total de linhas em bronze.{table}.")
                results.append(True)
                
        if all(results):
            # Executar VACUUM ANALYZE ao final da ingestão para otimizar estatísticas e limpar tuplas mortas
            with dw_engine.connect() as conn:
                print(f"[{datetime.now()}] Executando VACUUM ANALYZE em bronze.processes para otimizar o DW...", flush=True)
                try:
                    conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM ANALYZE bronze.processes;"))
                    print("  [OK] VACUUM ANALYZE concluído com sucesso.", flush=True)
                except Exception as e_vac:
                    print(f"  [AVISO] Não foi possível executar VACUUM ANALYZE: {e_vac}", flush=True)

            print(f"\n[{datetime.now()}] Ingestão INCREMENTAL concluída com SUCESSO!")
            return True
        else:
            print(f"\n[{datetime.now()}] Ingestão concluída com AVISOS.")
            return False
            
    except Exception as e:
        print(f"ERRO CRÍTICO NA INGESTÃO INCREMENTAL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ingest()

