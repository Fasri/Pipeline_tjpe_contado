import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}
resp = requests.get(f"{url}/rest/v1/", headers=headers)
data = resp.json()

tables = []
for path, info in data.get("paths", {}).items():
    if path.startswith("/"):
        tables.append(path[1:])

print(tables)
