import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

DW_HOST = os.getenv("DW_HOST", "aws-1-sa-east-1.pooler.supabase.com")
DW_USER = os.getenv("DW_USER", "postgres.owpqwkntxojqnpyfebal")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB", "postgres")
DW_PORT = os.getenv("DW_PORT", "6543")

project_ref = DW_USER.split(".")[-1] if "." in DW_USER else "owpqwkntxojqnpyfebal"

pass_encoded = urllib.parse.quote_plus(DW_PASS)

targets = [
    {
        "name": "Pooler Transaction (aws-1-sa-east-1.pooler.supabase.com:6543)",
        "host": DW_HOST,
        "port": DW_PORT,
        "user": DW_USER,
        "pass": pass_encoded,
    },
    {
        "name": "Pooler Session (aws-1-sa-east-1.pooler.supabase.com:5432)",
        "host": DW_HOST,
        "port": 5432,
        "user": DW_USER,
        "pass": pass_encoded,
    },
    {
        "name": "Direct DB Connection (db.owpqwkntxojqnpyfebal.supabase.co:5432)",
        "host": f"db.{project_ref}.supabase.co",
        "port": 5432,
        "user": "postgres",
        "pass": pass_encoded,
    },
    {
        "name": "Direct DB Connection (db.owpqwkntxojqnpyfebal.supabase.co:6543)",
        "host": f"db.{project_ref}.supabase.co",
        "port": 6543,
        "user": DW_USER,
        "pass": pass_encoded,
    },
]

print("=== TESTANDO CONEXÕES COM O DW ===")
for target in targets:
    url = f"postgresql://{target['user']}:{target['pass']}@{target['host']}:{target['port']}/{DW_DB}"
    print(f"\n---> Testando: {target['name']}")
    try:
        engine = create_engine(
            url,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 10,
                "gssencmode": "disable"
            }
        )
        with engine.connect() as conn:
            val = conn.execute(text("SELECT version();")).scalar()
            print(f"     [SUCESSO] Conectado com sucesso! DB Version: {val[:60]}")
    except Exception as e:
        print(f"     [FALHA] Erro: {e}")
