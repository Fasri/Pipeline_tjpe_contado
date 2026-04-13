import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Configuração de caminhos
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY não configurados.")
    return create_client(url, key)

def get_val(row, keys, default=""):
    """Busca um valor no dataframe tentando diferentes nomes de coluna."""
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default

def sync_database_from_storage():
    """
    Baixa o arquivo consolidado do Supabase Storage e sincroniza com a tabela 'processes'.
    Equivalente à última etapa do ETL (atualizar_bd_contadoria).
    """
    print(f"[{datetime.now()}] Iniciando a sincronização do Banco de Dados...")
    
    BUCKET_NAME = os.getenv("BUCKET_NAME", "relatorios")
    FILE_PATH = "tempo_real_Consolidado_supabase.csv"
    SYSTEM_USER_ID = os.getenv("SYSTEM_USER_ID")
    TEMP_FILE = BASE_DIR / "data_transform" / "temp_sync.csv"
    
    try:
        supabase = get_supabase_client()
        
        # 1. Baixar o arquivo do Storage
        print(f"Baixando arquivo '{FILE_PATH}' do bucket '{BUCKET_NAME}'...")
        response = supabase.storage.from_(BUCKET_NAME).download(FILE_PATH)
        
        # Salva temporariamente
        with open(TEMP_FILE, "wb") as f:
            f.write(response)

        # 2. Ler o arquivo CSV
        df = pd.read_csv(TEMP_FILE)
        print(f"Arquivo lido. Encontradas {len(df)} linhas.")

        # 3. Preparar dados para inserção
        to_insert = []
        existing_set = set() # Evitar duplicados no mesmo arquivo
        intra_file_skipped = 0
        
        for _, row in df.iterrows():
            number = str(get_val(row, ['processo', 'Processo', 'numero', 'Número'], "")).strip()
            raw_date = str(get_val(row, ['data', 'Data', 'data_remessa', 'Entrada'], ""))[:10].strip()
            
            # Converte DD/MM/YYYY para YYYY-MM-DD
            try:
                if '/' in raw_date:
                    entry_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                else:
                    entry_date = raw_date
            except Exception:
                entry_date = raw_date
                
            nucleus = str(get_val(row, ['nucleo', 'Núcleo'], "1ª CC")).strip()
            
            if not number or not entry_date:
                continue

            identifier = f"{number}|{entry_date}|{nucleus}"
            if identifier in existing_set:
                intra_file_skipped += 1
                continue
                
            existing_set.add(identifier)

            # Mapeamento para o banco
            to_insert.append({
                "number": number,
                "entry_date": entry_date,
                "court": str(get_val(row, ['vara', 'Vara', 'Juízo'], "")).strip(),
                "nucleus": nucleus,
                "priority": str(get_val(row, ['prioridades', 'prioridade', 'Prioridade'], "2-Sem prioridade")).strip(), 
                "status": "Pendente",
                "position": 0,
                "valor_custas": float(get_val(row, ['valor_custas', 'Custas'], 0)),
                "observacao": str(get_val(row, ['observacao', 'Nota'], "")).strip(),
                "created_at": datetime.now().isoformat()
            })

        # 4. Inserir no banco em blocos (upsert)
        inserted_count = 0
        if to_insert:
            print(f"Processando {len(to_insert)} candidatos a novos processos...")
            for i in range(0, len(to_insert), 500):
                chunk = to_insert[i:i + 500]
                res = supabase.table("processes").upsert(
                    chunk, 
                    on_conflict="number,entry_date,nucleus", 
                    ignore_duplicates=True
                ).execute()
                
                if res.data:
                    inserted_count += len(res.data)
            
            # 5. Registrar na Auditoria
            if SYSTEM_USER_ID:
                supabase.table("audit_logs").insert({
                    "user_id": SYSTEM_USER_ID,
                    "user_name": "Sistema Automático (ETL)",
                    "action": f"Sincronização automática: {inserted_count} novos processos adicionados.",
                    "created_at": datetime.now().isoformat(),
                    "details": {
                        "attempted": len(to_insert), 
                        "new_inserted": inserted_count, 
                        "intra_file_skipped": intra_file_skipped
                    }
                }).execute()
            
            print(f"Sucesso! {inserted_count} novos processos adicionados ao banco.")
        else:
            print(f"Nenhum processo novo encontrado no arquivo.")

    except Exception as e:
        print(f"ERRO durante a sincronização: {str(e)}")
    finally:
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)

if __name__ == "__main__":
    sync_database_from_storage()
