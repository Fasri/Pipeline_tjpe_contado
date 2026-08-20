import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import requests
import time

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

def backup_database():
    """
    Faz o backup completo de todas as tabelas e views expostas no banco (Supabase)
    antes da sincronização.
    """
    print(f"[{datetime.now()}] Iniciando o backup de segurança do banco de dados...")
    supabase = get_supabase_client()
    # Reutiliza as mesmas variáveis já carregadas pelo get_supabase_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    # Pegar todas as tabelas da API REST do Supabase
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        resp = requests.get(f"{url}/rest/v1/", headers=headers)
        data = resp.json()
        paths = data.get("paths", {})
        
        # Filtra paths vazios, procedimentos armazenados (rpc), views (vw_) e tabelas temporárias (temp_*, stg_*)
        tables = [
            p[1:] for p in paths.keys() 
            if p.startswith("/") and p[1:] 
            and not p[1:].startswith("rpc/") 
            and not p[1:].startswith("vw_")
            and not p[1:].startswith("temp")
            and not p[1:].startswith("stg")
        ]
    except Exception as e:
        print(f"Erro ao buscar lista de tabelas para backup via OpenAPI: {e}")
        # Lista de fallback das tabelas físicas reais
        tables = ['processes', 'audit_logs', 'users', 'nucleos', 'status', 'prioridades']
        
    backup_dir = BASE_DIR / "data_transform" / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for table in tables:
        print(f"  Fazendo backup da tabela/view: {table}...")
        try:
            # Tenta verificar se a tabela possui a coluna "id" para usar Keyset Pagination
            use_keyset = False
            try:
                # Busca apenas 1 linha para testar a estrutura
                test_res = supabase.table(table).select("*").limit(1).execute()
                if test_res.data and "id" in test_res.data[0]:
                    use_keyset = True
            except Exception:
                use_keyset = False

            all_data = []
            page_size = 1000

            if use_keyset:
                # Paginação por Keyset: extremamente rápida e eficiente em I/O
                last_id = None
                while True:
                    query = supabase.table(table).select("*").order("id").limit(page_size)
                    if last_id is not None:
                        query = query.gt("id", last_id)
                    
                    response = query.execute()
                    data = response.data
                    if not data:
                        break
                    all_data.extend(data)
                    last_id = data[-1]['id']
                    if len(data) < page_size:
                        break
            else:
                # Fallback para paginação por Offset tradicional
                start = 0
                while True:
                    response = supabase.table(table).select("*").range(start, start + page_size - 1).execute()
                    data = response.data
                    if not data:
                        break
                    all_data.extend(data)
                    if len(data) < page_size:
                        break
                    start += page_size
                
            if all_data:
                df = pd.DataFrame(all_data)
                filepath = backup_dir / f"{table}.csv"
                df.to_csv(filepath, index=False)
                print(f"  -> {len(all_data)} registros salvos em {filepath.name} (Keyset: {use_keyset})")
            else:
                print(f"  -> {table} vazia. Ignorada.")
                
        except Exception as e:
            print(f"  -> Erro ao fazer backup de {table}: {e}")
            
    print(f"[{datetime.now()}] Backup concluído. Salvo em {backup_dir}\n")
    return backup_dir


def sync_database_from_storage():
    """
    Baixa o arquivo consolidado do Supabase Storage e sincroniza com a tabela 'processes'.
    Equivalente à última etapa do ETL (atualizar_bd_contadoria).
    """
    print(f"[{datetime.now()}] Iniciando a sincronização do Banco de Dados...")
    
    # Executa o backup antes de começar a mexer nos dados
    backup_dir = backup_database()
    
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
                "pje": True,
                "created_at": datetime.now().isoformat()
            })

        # Conjunto de números de processos presentes no arquivo baixado
        file_numbers_set = set(item["number"] for item in to_insert if item.get("number"))

        # 4. Inserir no banco em blocos (upsert)
        inserted_count = 0
        if to_insert:
            total_items = len(to_insert)
            chunk_size = 100
            print(f"Processando {total_items} candidatos a novos processos (Lotes de {chunk_size})...")
            
            for i in range(0, total_items, chunk_size):
                chunk = to_insert[i:i + chunk_size]
                current_batch = (i // chunk_size) + 1
                total_batches = (total_items // chunk_size) + (1 if total_items % chunk_size > 0 else 0)
                
                print(f"  -> Enviando lote {current_batch}/{total_batches} ({len(chunk)} registros)...")
                
                try:
                    res = supabase.table("processes").upsert(
                        chunk, 
                        on_conflict="number,entry_date,nucleus", 
                        ignore_duplicates=True
                    ).execute()
                    
                    if res.data:
                        inserted_count += len(res.data)
                    
                    # Pequena pausa para evitar sobrecarga e timeout
                    time.sleep(0.5)
                    
                except Exception as batch_err:
                    print(f"  [AVISO] Erro no lote {current_batch}: {batch_err}")
                    print("  Tentando continuar com o próximo lote...")
                    continue

        # 4.5. Sincronizar campo 'pje' (booleano) nos processos com status Pendente no banco
        print("Sincronizando campo 'pje' nos processos com status Pendente...")
        all_pending_db = []
        page_size = 1000
        start = 0
        while True:
            try:
                res = supabase.table("processes").select("id, number, status, pje").ilike("status", "Pendente%").range(start, start + page_size - 1).execute()
                data = res.data or []
                if not data:
                    break
                all_pending_db.extend(data)
                if len(data) < page_size:
                    break
                start += page_size
            except Exception as fetch_err:
                print(f"  [AVISO] Erro ao carregar processos pendentes do banco para sincronização 'pje': {fetch_err}")
                break

        ids_pje_false = []
        ids_pje_true = []

        for p in all_pending_db:
            p_id = p.get("id")
            p_num = str(p.get("number") or "").strip()
            curr_pje = p.get("pje")
            in_file = p_num in file_numbers_set

            if in_file and curr_pje is not True:
                ids_pje_true.append(p_id)
            elif not in_file and curr_pje is not False:
                ids_pje_false.append(p_id)

        if ids_pje_false:
            print(f"  -> Atualizando pje=False para {len(ids_pje_false)} processos pendentes no banco que NÃO estão no arquivo...")
            for b in range(0, len(ids_pje_false), 100):
                batch = ids_pje_false[b:b+100]
                try:
                    supabase.table("processes").update({"pje": False}).in_("id", batch).execute()
                except Exception as e:
                    print(f"  [AVISO] Erro ao atualizar pje=False no lote: {e}")

        if ids_pje_true:
            print(f"  -> Atualizando pje=True para {len(ids_pje_true)} processos pendentes no banco que ESTÃO no arquivo...")
            for b in range(0, len(ids_pje_true), 100):
                batch = ids_pje_true[b:b+100]
                try:
                    supabase.table("processes").update({"pje": True}).in_("id", batch).execute()
                except Exception as e:
                    print(f"  [AVISO] Erro ao atualizar pje=True no lote: {e}")

        if to_insert:
            # 5. Registrar na Auditoria
            if SYSTEM_USER_ID:
                try:
                    supabase.table("audit_logs").insert({
                        "user_id": SYSTEM_USER_ID,
                        "user_name": "Sistema Automático (ETL)",
                        "action": f"Sincronização automática: {inserted_count} novos processos adicionados.",
                        "created_at": datetime.now().isoformat(),
                        "details": {
                            "attempted": len(to_insert),
                            "new_inserted": inserted_count,
                            "intra_file_skipped": intra_file_skipped,
                        },
                    }).execute()
                except Exception as audit_err:
                    print(f"Aviso: Falha ao registrar auditoria (sincronização já concluída): {audit_err}")
            
            print(f"Sucesso! {inserted_count} novos processos adicionados ao banco.")
        else:
            print(f"Nenhum processo novo encontrado no arquivo.")

    except Exception as e:
        print(f"ERRO durante a sincronização: {str(e)}")
    finally:
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)
            
    return backup_dir

if __name__ == "__main__":
    sync_database_from_storage()
