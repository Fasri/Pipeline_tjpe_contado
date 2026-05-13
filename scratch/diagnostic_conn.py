import os
import pandas as pd
from supabase import create_client
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env")

def diagnostic():
    print("=== DIAGNÓSTICO DE INGESTÃO (FIXED) ===\n")
    
    dw_host = "owpqwkntxojqnpyfebal.supabase.co"
    dw_user = os.getenv("DW_USER")
    dw_pass = os.getenv("DW_PASS")
    dw_db = os.getenv("DW_DB")
    dw_port = os.getenv("DW_PORT")
    
    print(f"Testando conexão com: {dw_host}:{dw_port} como {dw_user}")

    modes = [
        {"name": "SSL Require", "args": {"sslmode": "require", "connect_timeout": 10}},
        {"name": "SSL Prefer", "args": {"sslmode": "prefer", "connect_timeout": 10}},
        {"name": "SSL Disable", "args": {"sslmode": "disable", "connect_timeout": 10}},
    ]
    
    for mode in modes:
        print(f"   Testando Modo: {mode['name']}...")
        try:
            # Em SQLAlchemy, argumentos de conexão do driver vão no connect_args
            engine = create_engine(
                f'postgresql://{dw_user}:{dw_pass}@{dw_host}:{dw_port}/{dw_db}',
                connect_args=mode['args']
            )
            with engine.connect() as conn:
                res = conn.execute(text("SELECT version();")).scalar()
                print(f"      [SUCESSO] Conectado! Versão: {res[:50]}...")
                return True
        except Exception as e:
            print(f"      [FALHA] Erro: {str(e)}")
    return False

if __name__ == "__main__":
    diagnostic()
