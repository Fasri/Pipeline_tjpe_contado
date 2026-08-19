import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB")
pass_encoded = urllib.parse.quote_plus(DW_PASS)

poolers = [
    "aws-1-sa-east-1.pooler.supabase.com",
    "aws-0-sa-east-1.pooler.supabase.com",
    "aws-0-us-east-1.pooler.supabase.com",
    "sa-east-1.pooler.supabase.com"
]

ports = [6543, 5432]

print("=== TESTANDO TODOS OS POOLERS E PORTAS ===")

for p in poolers:
    for port in ports:
        url = f"postgresql://{DW_USER}:{pass_encoded}@{p}:{port}/{DW_DB}"
        print(f"\n---> Host: {p} | Port: {port}")
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
                res = conn.execute(text("SELECT 1;")).scalar()
                print(f"     [SUCESSO] Conectado! Resposta: {res}")
        except Exception as e:
            print(f"     [FALHA] {e}")
