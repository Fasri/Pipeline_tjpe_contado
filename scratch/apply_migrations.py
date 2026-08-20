import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DW_HOST = os.getenv("DW_HOST", "aws-1-sa-east-1.pooler.supabase.com")
DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB", "postgres")
DW_PORT = int(os.getenv("DW_PORT", 6543))

if not DW_USER or not DW_PASS:
    print("[ERRO] DW_USER ou DW_PASS não definidos no .env")
    exit(1)

pass_encoded = urllib.parse.quote_plus(DW_PASS)
db_url = f"postgresql://{DW_USER}:{pass_encoded}@{DW_HOST}:{DW_PORT}/{DW_DB}"

engine = create_engine(
    db_url,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 30,
        "gssencmode": "disable"
    }
)

def apply_migrations():
    print("=== APLICANDO MIGRAÇÕES DE BANCO DE DADOS (UPDATED_AT & ÍNDICES) ===")
    
    sql_statements = [
        "CREATE SCHEMA IF NOT EXISTS bronze;",
        "CREATE SCHEMA IF NOT EXISTS silver;",
        "CREATE SCHEMA IF NOT EXISTS gold;",

        # 2. Adicionar coluna updated_at na tabela public.processes (se existir)
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processes') THEN
                IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_schema='public' AND table_name='processes' AND column_name='updated_at') THEN
                    ALTER TABLE public.processes ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
            END IF;
        END $$;
        """,

        # 3. Adicionar coluna updated_at na tabela bronze.processes (se existir)
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'bronze' AND tablename = 'processes') THEN
                IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_schema='bronze' AND table_name='processes' AND column_name='updated_at') THEN
                    ALTER TABLE bronze.processes ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
            END IF;
        END $$;
        """,

        # 4. Criar função da trigger
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,

        # 5. Criar trigger na public.processes se existir
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processes') THEN
                DROP TRIGGER IF EXISTS trg_update_processes_updated_at ON public.processes;
                CREATE TRIGGER trg_update_processes_updated_at
                BEFORE UPDATE ON public.processes
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,

        # 6. Criar índices para performance em public e bronze
        "CREATE INDEX IF NOT EXISTS idx_public_proc_updated_at ON public.processes(updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_public_proc_status ON public.processes(status);",
        "CREATE INDEX IF NOT EXISTS idx_public_proc_nucleus ON public.processes(nucleus);",

        "CREATE INDEX IF NOT EXISTS idx_bronze_proc_updated_at ON bronze.processes(updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_bronze_proc_status ON bronze.processes(status);",
        "CREATE INDEX IF NOT EXISTS idx_bronze_proc_nucleus ON bronze.processes(nucleus);"
    ]

    with engine.connect() as conn:
        for stmt in sql_statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                print("  [OK] Instrução executada com sucesso.")
            except Exception as e:
                print(f"  [AVISO] Erro na execução de instrução: {e}")
                conn.rollback()

    print("=== MIGRAÇÕES CONCLUÍDAS COM SUCESSO! ===")

if __name__ == "__main__":
    apply_migrations()
