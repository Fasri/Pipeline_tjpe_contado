import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

url1 = os.getenv("SUPABASE_URL")
key1 = os.getenv("SUPABASE_KEY")

dw_user = os.getenv("DW_USER")
ref2 = dw_user.split(".")[-1] if "." in dw_user else "owpqwkntxojqnpyfebal"
url2 = f"https://{ref2}.supabase.co"

print(f"=== TESTANDO REST API DOS PROJETOS SUPABASE ===")

print(f"\n1. Testando Origem: {url1}")
try:
    r = requests.get(f"{url1}/rest/v1/", headers={"apikey": key1, "Authorization": f"Bearer {key1}"}, timeout=10)
    print(f"   Status: {r.status_code} | Resposta: {r.text[:100]}")
except Exception as e:
    print(f"   Erro: {e}")

print(f"\n2. Testando DW Project Ref ({ref2}): {url2}")
try:
    r = requests.get(f"{url2}/rest/v1/", headers={"apikey": key1, "Authorization": f"Bearer {key1}"}, timeout=10)
    print(f"   Status: {r.status_code} | Resposta: {r.text[:100]}")
except Exception as e:
    print(f"   Erro: {e}")
