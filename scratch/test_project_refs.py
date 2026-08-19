import socket
import os
from dotenv import load_dotenv

load_dotenv(".env")

DW_PASS = os.getenv("DW_PASS")

refs = ["zmzujbdndgwjqmsohjzd", "owpqwkntxojqnpyfebal"]
poolers = [
    "aws-1-sa-east-1.pooler.supabase.com",
    "aws-0-sa-east-1.pooler.supabase.com",
    "aws-0-us-east-1.pooler.supabase.com"
]

print("=== VERIFICANDO RESOLUÇÃO DE DNS ===")

for ref in refs:
    direct_host = f"db.{ref}.supabase.co"
    try:
        ip = socket.gethostbyname(direct_host)
        print(f"[OK] Direct Host: {direct_host} -> {ip}")
    except Exception as e:
        print(f"[ERR] Direct Host: {direct_host} -> {e}")

for pooler in poolers:
    try:
        ip = socket.gethostbyname(pooler)
        print(f"[OK] Pooler Host: {pooler} -> {ip}")
    except Exception as e:
        print(f"[ERR] Pooler Host: {pooler} -> {e}")
