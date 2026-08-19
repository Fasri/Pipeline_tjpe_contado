import urllib.parse
from sqlalchemy.engine import make_url
import os
from dotenv import load_dotenv

load_dotenv(".env")

dw_host = os.getenv("DW_HOST")
dw_user = os.getenv("DW_USER")
dw_pass = os.getenv("DW_PASS")
dw_db = os.getenv("DW_DB")
dw_port = os.getenv("DW_PORT")

print("Raw password:", dw_pass)
raw_url = f"postgresql://{dw_user}:{dw_pass}@{dw_host}:{dw_port}/{dw_db}"
print("\nUnencoded URL:", raw_url)
try:
    parsed_raw = make_url(raw_url)
    print("Parsed Unencoded Password:", parsed_raw.password)
    print("Parsed Unencoded Host:", parsed_raw.host)
    print("Parsed Unencoded Port:", parsed_raw.port)
    print("Parsed Unencoded Database:", parsed_raw.database)
except Exception as e:
    print("Failed to parse raw url:", e)

encoded_pass = urllib.parse.quote_plus(dw_pass)
print("\nEncoded password:", encoded_pass)
encoded_url = f"postgresql://{dw_user}:{encoded_pass}@{dw_host}:{dw_port}/{dw_db}"
print("Encoded URL:", encoded_url)
parsed_encoded = make_url(encoded_url)
print("Parsed Encoded Password:", parsed_encoded.password)
print("Parsed Encoded Host:", parsed_encoded.host)
print("Parsed Encoded Port:", parsed_encoded.port)
print("Parsed Encoded Database:", parsed_encoded.database)
