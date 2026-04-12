import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    BUCKET_NAME = os.getenv("BUCKET_NAME", "")
    FILE_PATH = os.getenv("FILE_PATH", "tempo_real_Consolidado_supabase.csv")
    SYSTEM_USER_ID = os.getenv("SYSTEM_USER_ID", "")
