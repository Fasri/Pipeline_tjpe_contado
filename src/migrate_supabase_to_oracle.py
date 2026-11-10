"""
Script de Migração: Supabase (REST API) -> PostgreSQL (Oracle Cloud VM)
Projeto: ETL TJPE Contadoria
"""

import os
import sys
import json
import time
import getpass
import subprocess
from pathlib import Path
from datetime import datetime

# Garante que as dependências necessárias estejam instaladas
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    import psycopg2
    from psycopg2 import extras
except ImportError:
    print("[*] Instalando 'psycopg2-binary' para conexão com o PostgreSQL...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2
        from psycopg2 import extras
    except Exception:
        print("[*] Falha ao instalar psycopg2-binary, tentando 'pg8000'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pg8000"])
        import pg8000.native as pg8000

# Carrega variáveis do .env
BASE_DIR = Path(__file__).resolve().parent.parent
env_file = BASE_DIR / ".env"

if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("\n❌ ERRO: SUPABASE_URL e SUPABASE_KEY precisam estar configurados no arquivo .env!")
    sys.exit(1)

# Configurações do PostgreSQL de destino (Oracle Cloud VM)
PG_HOST = os.getenv("ORACLE_PG_HOST", "163.176.3.36")
PG_PORT = int(os.getenv("ORACLE_PG_PORT", "5432"))
PG_USER = os.getenv("ORACLE_PG_USER", "postgres")
PG_DB = os.getenv("ORACLE_PG_DB", "tjpe_contadoria")
PG_PASS = os.getenv("ORACLE_PG_PASS")

def get_pg_password():
    global PG_PASS
    if not PG_PASS:
        # Se DW_PASS no .env parecer a senha do container, pergunta se quer usar ou digitar
        env_dw_pass = os.getenv("DW_PASS")
        print("\n" + "="*60)
        print("  MIGRAÇÃO DE DADOS: SUPABASE -> ORACLE CLOUD POSTGRESQL")
        print("="*60)
        print(f"Destino: postgresql://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
        
        prompt = f"Digite a senha do PostgreSQL do Docker na VM ({PG_HOST})"
        if env_dw_pass:
            prompt += f" [Enter para usar '{env_dw_pass}']: "
            resp = input(prompt).strip()
            PG_PASS = resp if resp else env_dw_pass
        else:
            prompt += ": "
            PG_PASS = getpass.getpass(prompt)
    return PG_PASS

def connect_pg():
    pwd = get_pg_password()
    print(f"\n[*] Conectando ao PostgreSQL na VM {PG_HOST}...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=pwd,
            dbname=PG_DB,
            connect_timeout=10
        )
        conn.autocommit = True
        print("✅ Conexão com o PostgreSQL da Oracle estabelecida com sucesso!")
        return conn
    except Exception as e:
        print(f"❌ Falha ao conectar ao PostgreSQL: {e}")
        sys.exit(1)

def discover_tables():
    """Descobre as tabelas expostas na API REST do Supabase."""
    print("\n[*] Consultando tabelas disponíveis no Supabase...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            paths = data.get("paths", {})
            tables = [
                p[1:] for p in paths.keys()
                if p.startswith("/") and p[1:]
                and not p[1:].startswith("rpc/")
                and not p[1:].startswith("vw_")
                and not p[1:].startswith("temp")
                and not p[1:].startswith("stg")
            ]
            if tables:
                print(f"📋 Tabelas encontradas no Supabase: {', '.join(tables)}")
                return tables
    except Exception as e:
        print(f"  [Aviso] Erro na descoberta automática de tabelas: {e}")

    # Lista prioritária padrão
    fallback = ["nucleos", "prioridades", "status", "users", "processes", "audit_logs"]
    print(f"📋 Usando lista padrão de tabelas: {', '.join(fallback)}")
    return fallback

def fetch_table_rows(table_name):
    """Lê todas as linhas de uma tabela usando paginação na API REST do Supabase."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Range-Unit": "items",
        "Prefer": "count=exact"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=*"
    all_rows = []
    page_size = 1000
    offset = 0

    print(f"  ⬇️ Baixando '{table_name}' do Supabase...", end="", flush=True)

    while True:
        headers["Range"] = f"{offset}-{offset + page_size - 1}"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code not in (200, 206):
                # Tenta paginação por limit & offset
                resp = requests.get(f"{url}&limit={page_size}&offset={offset}", headers=headers, timeout=30)
            
            if resp.status_code not in (200, 206):
                if offset == 0:
                    print(f" [Aviso: Tabela vazia ou erro {resp.status_code}]")
                break

            data = resp.json()
            if not data or not isinstance(data, list):
                break

            all_rows.extend(data)
            print(f" {len(all_rows)}", end="", flush=True)

            if len(data) < page_size:
                break

            offset += page_size
            time.sleep(0.05)
        except Exception as e:
            print(f" [Erro ao baixar lote: {e}]")
            break

    print(f" -> Total: {len(all_rows)} registros.")
    return all_rows

def infer_pg_type(val):
    """Infere tipo PostgreSQL básico a partir de um valor."""
    if isinstance(val, bool):
        return "BOOLEAN"
    elif isinstance(val, int):
        return "BIGINT" if abs(val) > 2147483647 else "INTEGER"
    elif isinstance(val, float):
        return "NUMERIC"
    elif isinstance(val, (dict, list)):
        return "JSONB"
    elif isinstance(val, str):
        if len(val) == 10 and val[4] == '-' and val[7] == '-':
            try:
                datetime.strptime(val, "%Y-%m-%d")
                return "DATE"
            except ValueError:
                pass
        if len(val) >= 19 and val[4] == '-' and val[7] == '-' and ('T' in val or ' ' in val):
            return "TIMESTAMPTZ"
        return "TEXT"
    return "TEXT"

def create_table_if_not_exists(cursor, table_name, sample_rows):
    """Gera o CREATE TABLE caso não exista no PostgreSQL."""
    if not sample_rows:
        return

    # Mapear tipos inspecionando as primeiras linhas
    col_types = {}
    for row in sample_rows[:100]:
        for k, v in row.items():
            if k not in col_types and v is not None:
                col_types[k] = infer_pg_type(v)

    # Colunas que sobraram só como None
    for k in sample_rows[0].keys():
        if k not in col_types:
            col_types[k] = "TEXT"

    # Se existir coluna id, define como PK primária se não existir
    cols_sql = []
    has_id = False
    for col, c_type in col_types.items():
        if col == "id":
            has_id = True
            if c_type in ("INTEGER", "BIGINT"):
                cols_sql.append(f'"{col}" {c_type} PRIMARY KEY')
            else:
                cols_sql.append(f'"{col}" {c_type} PRIMARY KEY')
        else:
            cols_sql.append(f'"{col}" {c_type}')

    create_sql = f'CREATE TABLE IF NOT EXISTS public."{table_name}" (\n  ' + ",\n  ".join(cols_sql) + "\n);"
    cursor.execute(create_sql)

def insert_rows(cursor, table_name, rows):
    """Faz a inserção em lotes de alta performance."""
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_names = ", ".join([f'"{c}"' for c in columns])
    
    # Tratamento de valores para formato aceito pelo psycopg2
    data_tuples = []
    for r in rows:
        row_tuple = []
        for c in columns:
            val = r.get(c)
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            row_tuple.append(val)
        data_tuples.append(tuple(row_tuple))

    # Inserção em lotes de 1.000
    batch_size = 1000
    total_inserted = 0
    query = f'INSERT INTO public."{table_name}" ({col_names}) VALUES %s ON CONFLICT DO NOTHING'

    for i in range(0, len(data_tuples), batch_size):
        batch = data_tuples[i:i + batch_size]
        extras.execute_values(cursor, query, batch, page_size=batch_size)
        total_inserted += len(batch)
        print(f"    Inseridos: {total_inserted}/{len(data_tuples)}...", end="\r", flush=True)

    print(f"    ✅ Tabela '{table_name}': {len(data_tuples)} registros gravados.")
    return len(data_tuples)

def create_indexes_and_optimizations(cursor):
    """Cria os índices e otimizações de performance para consultas rápidas."""
    print("\n" + "-"*60)
    print("⚡ CRIANDO ÍNDICES E OTIMIZAÇÕES DE PERFORMANCE NO POSTGRESQL...")
    print("-" * 60)

    index_statements = [
        # Índices essenciais para consultas do Dashboard e do dbt na tabela processes
        'CREATE INDEX IF NOT EXISTS idx_proc_status ON public.processes(status);',
        'CREATE INDEX IF NOT EXISTS idx_proc_nucleus ON public.processes(nucleus);',
        'CREATE INDEX IF NOT EXISTS idx_proc_number ON public.processes(number);',
        'CREATE INDEX IF NOT EXISTS idx_proc_entry_date ON public.processes(entry_date);',
        'CREATE INDEX IF NOT EXISTS idx_proc_pje ON public.processes(pje);',
        'CREATE INDEX IF NOT EXISTS idx_proc_updated_at ON public.processes(updated_at);',
        # Índices para audit_logs e users
        'CREATE INDEX IF NOT EXISTS idx_audit_created_at ON public.audit_logs(created_at);',
        'CREATE INDEX IF NOT EXISTS idx_users_name ON public.users(name);'
    ]

    for stmt in index_statements:
        try:
            cursor.execute(stmt)
            idx_name = stmt.split()[5] if len(stmt.split()) > 5 else "indice"
            print(f"  ✅ Índice criado/garantido: {idx_name}")
        except Exception as e:
            # Se alguma coluna não existir nessa tabela, ignora suavemente
            pass

def main():
    conn = connect_pg()
    cursor = conn.cursor()

    # Cria schemas se não existirem (focando no public)
    print("\n[*] Garantindo schema public...")
    cursor.execute("CREATE SCHEMA IF NOT EXISTS public;")

    tables = discover_tables()
    
    # Ordenar tabelas de referência antes de tabelas grandes
    priority_order = ["nucleos", "prioridades", "status", "users", "processes", "audit_logs"]
    tables_sorted = [t for t in priority_order if t in tables]
    for t in tables:
        if t not in tables_sorted:
            tables_sorted.append(t)

    print("\n" + "-"*60)
    print(f"Iniciando migração de {len(tables_sorted)} tabelas:")
    print("-" * 60)

    stats = {}
    for table in tables_sorted:
        print(f"\n📦 Processando: {table}")
        rows = fetch_table_rows(table)
        if not rows:
            print(f"  ℹ️ Tabela '{table}' não possui registros para migrar.")
            stats[table] = 0
            continue

        create_table_if_not_exists(cursor, table, rows)
        inserted = insert_rows(cursor, table, rows)
        stats[table] = inserted

    # Criação de índices e otimizações essenciais após a carga
    create_indexes_and_optimizations(cursor)

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*60)
    for tbl, count in stats.items():
        print(f"  • {tbl}: {count} linhas")
    print("\nAgora você pode abrir o DBeaver, dar F5 na conexão da VM Oracle")
    print("e conferir todas as suas tabelas e dados populados!")

if __name__ == "__main__":
    main()

