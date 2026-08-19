import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

DW_PASS = os.getenv("DW_PASS")
pass_encoded = urllib.parse.quote_plus(DW_PASS)

user = "postgres.zmzujbdndgwjqmsohjzd"
poolers = [
    "aws-1-sa-east-1.pooler.supabase.com",
    "aws-0-sa-east-1.pooler.supabase.com",
    "aws-0-us-east-1.pooler.supabase.com"
]
ports = [6543, 5432]

print("=== TESTANDO PROJETO zmzujbdndgwjqmsohjzd NOS POOLERS ===")

for p in poolers:
    for port in ports:
        url = f"postgresql://{user}:{pass_encoded}@{p}:{port}/postgres"
        print(f"---> Host: {p} | Port: {port} | User: {user}")
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
