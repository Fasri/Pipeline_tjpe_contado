import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

DW_HOST = os.getenv("DW_HOST")
DW_USER = os.getenv("DW_USER")
DW_PASS = os.getenv("DW_PASS")
DW_DB = os.getenv("DW_DB")
DW_PORT = int(os.getenv("DW_PORT", 6543))

def unlock_database():
    encoded_pass = urllib.parse.quote_plus(DW_PASS) if DW_PASS else ""
    
    ports_to_try = [5432, DW_PORT] if DW_PORT != 5432 else [5432, 6543]
    
    engine = None
    for port in ports_to_try:
        try:
            print(f"Tentando conectar ao DW na porta {port}...", flush=True)
            eng = create_engine(
                f'postgresql://{DW_USER}:{encoded_pass}@{DW_HOST}:{port}/{DW_DB}',
                connect_args={"sslmode": "require", "connect_timeout": 10, "gssencmode": "disable"}
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1;"))
            engine = eng
            print(f"[OK] Conectado na porta {port}.", flush=True)
            break
        except Exception as e:
            print(f"Falha na porta {port}: {e}", flush=True)

    if not engine:
        print("[ERRO] Não foi possível conectar ao DW em nenhuma porta.", flush=True)
        return

    try:
        with engine.connect() as conn:
            print("[INFO] Buscando queries longas/travadas em execução...", flush=True)
            query = text("""
                SELECT pid, usename, client_addr, state, now() - query_start AS duration, query
                FROM pg_stat_activity
                WHERE pid <> pg_backend_pid()
                  AND state <> 'idle'
                  AND (now() - query_start) > interval '3 seconds';
            """)
            result = conn.execute(query).fetchall()
            
            if not result:
                print("[INFO] Nenhuma query travada/longa encontrada em execução no momento.", flush=True)
            else:
                print(f"[INFO] Encontradas {len(result)} queries ativas rodando há mais de 3s:", flush=True)
                for row in result:
                    pid, usename, client_addr, state, duration, query_text = row
                    print(f"  - PID {pid} ({usename}) | Duração: {duration} | State: {state}", flush=True)
                    print(f"    Query: {str(query_text)[:100]}...", flush=True)
                    try:
                        conn.execute(text(f"SELECT pg_terminate_backend({pid});"))
                        print(f"    -> PID {pid} encerrado.", flush=True)
                    except Exception as e_term:
                        print(f"    -> Erro ao encerrar PID {pid}: {e_term}", flush=True)

            print("[INFO] Verificando conexões 'idle in transaction'...", flush=True)
            idle_tx_query = text("""
                SELECT pid, usename, now() - state_change AS idle_duration
                FROM pg_stat_activity
                WHERE state = 'idle in transaction'
                  AND pid <> pg_backend_pid();
            """)
            idle_results = conn.execute(idle_tx_query).fetchall()
            if not idle_results:
                print("[INFO] Nenhuma conexão 'idle in transaction' encontrada.", flush=True)
            else:
                for row in idle_results:
                    pid, usename, idle_duration = row
                    print(f"  - PID {pid} IDLE IN TRANSACTION ({idle_duration}). Encerrando...", flush=True)
                    try:
                        conn.execute(text(f"SELECT pg_terminate_backend({pid});"))
                        print(f"    -> PID {pid} encerrado.", flush=True)
                    except Exception as e_term:
                        print(f"    -> Erro: {e_term}", flush=True)

            conn.commit()
            print("[SUCESSO] O banco de dados está liberado!", flush=True)
    except Exception as ex:
        print(f"[ERRO GERAL]: {ex}", flush=True)

if __name__ == "__main__":
    unlock_database()
