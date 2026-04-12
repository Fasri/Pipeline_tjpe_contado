import os
import pandas as pd
from datetime import datetime

from src.database import get_supabase_client
from src.config import Config
from src.utils import get_val

def import_real_time():
    print(f"[{datetime.now()}] Iniciando a importação automática...")
    
    TEMP_FILE = "temp_import.csv"
    
    try:
        supabase = get_supabase_client()
        
        # 1. Baixar o arquivo do Storage
        print(f"Baixando arquivo '{Config.FILE_PATH}' do bucket '{Config.BUCKET_NAME}'...")
        response = supabase.storage.from_(Config.BUCKET_NAME).download(Config.FILE_PATH)
        
        # Salva temporariamente para o pandas ler
        with open(TEMP_FILE, "wb") as f:
            f.write(response)

        # 2. Ler o arquivo CSV
        df = pd.read_csv(TEMP_FILE)
        print(f"Arquivo lido. Encontradas {len(df)} linhas.")

        # 3. Buscar processos existentes (Removido busca parcial que causava erro de contagem)
        existing_set = set() # Usado apenas para evitar duplicados NO MESMO ARQUIVO

        # 4. Preparar dados para inserção
        to_insert = []
        intra_file_skipped = 0
        
        for _, row in df.iterrows():
            number = str(get_val(row, ['processo', 'Processo', 'numero', 'Número'], "")).strip()
            raw_date = str(get_val(row, ['data', 'Data', 'data_remessa', 'Entrada'], ""))[:10].strip()
            
            # Converte DD/MM/YYYY para YYYY-MM-DD exigido pelo Supabase
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
                
            # Adiciona ao set para evitar duplicidade NO MESMO ARQUIVO CSV
            existing_set.add(identifier)

            # Dados para o banco
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

        # 5. Inserir no banco em blocos (chunks)
        inserted_count = 0
        if to_insert:
            print(f"Processando {len(to_insert)} candidatos a novos processos...")
            # Supabase suporta upsert com ignore_duplicates
            for i in range(0, len(to_insert), 500):
                chunk = to_insert[i:i + 500]
                # Usamos select() para saber o que foi REALMENTE inserido
                res = supabase.table("processes").upsert(
                    chunk, 
                    on_conflict="number,entry_date,nucleus", 
                    ignore_duplicates=True
                ).execute()
                
                # Se ignore_duplicates=True e o registro existia, res.data costuma vir vazio para aquele registro
                if res.data:
                    inserted_count += len(res.data)
            
            # 6. Registrar na Auditoria
            supabase.table("audit_logs").insert({
                "user_id": Config.SYSTEM_USER_ID,
                "user_name": "Sistema Automático (Python)",
                "action": f"Importação automática: {inserted_count} novos processos adicionados.",
                "created_at": datetime.now().isoformat(),
                "details": {
                    "attempted": len(to_insert), 
                    "new_inserted": inserted_count, 
                    "intra_file_skipped": intra_file_skipped
                }
            }).execute()
            
            print(f"Sucesso! {inserted_count} novos processos foram realmente adicionados ao banco.")
            if (len(to_insert) - inserted_count) > 0:
                print(f"Nota: {(len(to_insert) - inserted_count)} processos ja existiam no banco e foram ignorados.")
            if intra_file_skipped > 0:
                print(f"Nota: {intra_file_skipped} duplicados encontrados dentro do propio arquivo CSV.")
        else:
            print(f"Nenhum processo novo encontrado no arquivo.")

    except Exception as e:
        print(f"ERRO durante a importação: {str(e)}")
    finally:
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)
            print("Arquivo temporário foi removido.")
