import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

DW_PASS = os.getenv("DW_PASS")
pass_encoded = urllib.parse.quote_plus(DW_PASS)

prod_targets = [
    {
        "name": "Pooler Transaction (aws-1-sa-east-1.pooler.supabase.com:6543)",
        "host": "aws-1-sa-east-1.pooler.supabase.com",
        "port": 6543,
        "user": "postgres.zmzujbdndgwjqmsohjzd",
        "pass": pass_encoded,
    },
    {
        "name": "Direct DB Connection (db.zmzujbdndgwjqmsohjzd.supabase.co:5432)",
        "host": "db.zmzujbdndgwjqmsohjzd.supabase.co",
        "port": 5432,
        "user": "postgres",
        "pass": pass_encoded,
    },
]

print("=== TESTANDO CONEXÃO COM O BANCO DE PRODUÇÃO (zmzujbdndgwjqmsohjzd) ===")
for target in prod_targets:
    url = f"postgresql://{target['user']}:{target['pass']}@{target['host']}:{target['port']}/postgres"
    print(f"\n---> Testando: {target['name']}")
    try:
        engine = create_engine(
            url,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 5,
                "gssencmode": "disable"
            }
        )
        with engine.connect() as conn:
            val = conn.execute(text("SELECT version();")).scalar()
            print(f"     [SUCESSO] Conectado! DB Version: {val[:60]}")
            
            # Tentar aplicar a coluna updated_at e trigger no banco de produção
            conn.execute(text("ALTER TABLE processes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();"))
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))
            conn.execute(text("""
                DROP TRIGGER IF EXISTS trg_update_processes_updated_at ON processes;
                CREATE TRIGGER trg_update_processes_updated_at
                BEFORE UPDATE ON processes
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_processes_updated_at ON processes(updated_at);"))
            conn.commit()
            print("     [SUCESSO INTEGRAL] Coluna updated_at, Trigger e Índice criados com sucesso no banco de PRODUÇÃO!")
            break
    except Exception as e:
        print(f"     [FALHA] {e}")
