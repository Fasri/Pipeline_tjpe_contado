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

def is_2cc(nucleus_str: str) -> bool:
    """Verifica se o núcleo corresponde à 2ª CC (2ª Contadoria de Custas)."""
    clean = str(nucleus_str or "").strip().upper()
    return clean in ["2ª CC", "2ªCC", "2 CC", "2CC"]

def is_partidor(nucleus_str: str) -> bool:
    """Verifica se o núcleo corresponde ao Partidor."""
    return str(nucleus_str or "").strip().upper() == "PARTIDOR"

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

        # 2.1. Buscar processos que já estão pendentes no banco para a 2ª CC
        print("Consultando processos pendentes da 2ª CC no banco de dados...")
        pending_2cc_db = set()
        page_size = 1000
        start = 0
        while True:
            try:
                res = (
                    supabase.table("processes")
                    .select("number")
                    .in_("nucleus", ["2ª CC", "2ªCC", "2 CC", "2CC"])
                    .ilike("status", "Pendente%")
                    .range(start, start + page_size - 1)
                    .execute()
                )
                data = res.data or []
                if not data:
                    break
                for item in data:
                    num = str(item.get("number") or "").strip()
                    if num:
                        pending_2cc_db.add(num)
                if len(data) < page_size:
                    break
                start += page_size
            except Exception as e:
                print(f"  [AVISO] Erro ao carregar processos pendentes da 2ª CC: {e}")
                break

        print(f"Total de processos pendentes da 2ª CC no banco: {len(pending_2cc_db)}")

        # 3. Preparar dados para inserção
        to_insert = []
        candidates_2cc = {}  # {number: item_data} para 2ª CC, mantendo a data de entrada mais antiga
        existing_set = set() # Evitar duplicados no mesmo arquivo para os demais núcleos
        file_numbers_set = set()
        file_composite_keys = set()
        intra_file_skipped = 0
        skipped_2cc_pending = 0
        skipped_partidor_criminal = 0
        
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

            court = str(get_val(row, ['vara', 'Vara', 'Juízo'], "")).strip()

            file_numbers_set.add(number)
            file_composite_keys.add(f"{number}|{entry_date}|{nucleus}")

            # Regra Partidor: não adicionar ao banco varas que contenham 'criminal' no nome
            if is_partidor(nucleus) and "criminal" in court.lower():
                skipped_partidor_criminal += 1
                continue

            item_data = {
                "number": number,
                "entry_date": entry_date,
                "court": court,
                "nucleus": nucleus,
                "priority": str(get_val(row, ['prioridades', 'prioridade', 'Prioridade'], "2-Sem prioridade")).strip(), 
                "status": "Pendente",
                "position": 0,
                "valor_custas": float(get_val(row, ['valor_custas', 'Custas'], 0)),
                "observacao": str(get_val(row, ['observacao', 'Nota'], "")).strip(),
                "pje": True,
                "inconsistencia_tempo_real": False,
                "created_at": datetime.now().isoformat()
            }

            if is_2cc(nucleus):
                # Regra 2ª CC: se o processo já estiver pendente no sistema, não deve ser incluído
                if number in pending_2cc_db:
                    skipped_2cc_pending += 1
                    continue

                # Regra 2ª CC no arquivo: manter a ocorrência com data de entrada mais antiga
                if number in candidates_2cc:
                    intra_file_skipped += 1
                    if entry_date < candidates_2cc[number]["entry_date"]:
                        candidates_2cc[number] = item_data
                else:
                    candidates_2cc[number] = item_data
            else:
                identifier = f"{number}|{entry_date}|{nucleus}"
                if identifier in existing_set:
                    intra_file_skipped += 1
                    continue
                existing_set.add(identifier)
                to_insert.append(item_data)

        # Adiciona processos selecionados da 2ª CC
        if candidates_2cc:
            to_insert.extend(candidates_2cc.values())

        if skipped_2cc_pending > 0:
            print(f"  [2ª CC] {skipped_2cc_pending} registros ignorados por já estarem com status Pendente no banco.")

        if skipped_partidor_criminal > 0:
            print(f"  [PARTIDOR] {skipped_partidor_criminal} registros ignorados por pertencerem a varas criminais.")

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
                res = supabase.table("processes").select("id, number, status, pje, inconsistencia_tempo_real").ilike("status", "Pendente%").range(start, start + page_size - 1).execute()
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

        # 4.6. Sincronizar campo 'inconsistencia_tempo_real' no banco
        # Regra: True se (processo, data, nucleo) está no arquivo Tempo Real E o status no banco NÃO é Pendente.
        # False em todos os demais casos.
        print("Sincronizando campo 'inconsistencia_tempo_real' nos processos...")
        all_non_pending_db = []
        start = 0
        while True:
            try:
                res = supabase.table("processes").select("id, number, entry_date, nucleus, status, inconsistencia_tempo_real").not_.ilike("status", "Pendente%").range(start, start + page_size - 1).execute()
                data = res.data or []
                if not data:
                    break
                all_non_pending_db.extend(data)
                if len(data) < page_size:
                    break
                start += page_size
            except Exception as fetch_err:
                print(f"  [AVISO] Erro ao carregar processos não pendentes do banco para sincronização 'inconsistencia_tempo_real': {fetch_err}")
                break

        ids_inconsistencia_true = []
        ids_inconsistencia_false = []

        # Analisa processos que NÃO estão pendentes no banco
        for p in all_non_pending_db:
            p_id = p.get("id")
            p_num = str(p.get("number") or "").strip()
            p_date = str(p.get("entry_date") or "").strip()[:10]
            p_nuc = str(p.get("nucleus") or "").strip()
            curr_inc = p.get("inconsistencia_tempo_real")

            comp_key = f"{p_num}|{p_date}|{p_nuc}"
            in_file = comp_key in file_composite_keys

            if in_file and curr_inc is not True:
                ids_inconsistencia_true.append(p_id)
            elif not in_file and curr_inc is not False:
                ids_inconsistencia_false.append(p_id)

        # Analisa processos pendentes (devem ter inconsistencia_tempo_real = False sempre)
        for p in all_pending_db:
            p_id = p.get("id")
            curr_inc = p.get("inconsistencia_tempo_real")
            if curr_inc is True:
                ids_inconsistencia_false.append(p_id)

        if ids_inconsistencia_false:
            print(f"  -> Atualizando inconsistencia_tempo_real=False para {len(ids_inconsistencia_false)} processos...")
            for b in range(0, len(ids_inconsistencia_false), 100):
                batch = ids_inconsistencia_false[b:b+100]
                try:
                    supabase.table("processes").update({"inconsistencia_tempo_real": False}).in_("id", batch).execute()
                except Exception as e:
                    print(f"  [AVISO] Erro ao atualizar inconsistencia_tempo_real=False no lote: {e}")

        if ids_inconsistencia_true:
            print(f"  -> [ALERTA] Encontradas {len(ids_inconsistencia_true)} inconsistências (concluído/não pendente no banco, mas presente no arquivo Tempo Real)! Atualizando inconsistencia_tempo_real=True...")
            for b in range(0, len(ids_inconsistencia_true), 100):
                batch = ids_inconsistencia_true[b:b+100]
                try:
                    supabase.table("processes").update({"inconsistencia_tempo_real": True}).in_("id", batch).execute()
                except Exception as e:
                    print(f"  [AVISO] Erro ao atualizar inconsistencia_tempo_real=True no lote: {e}")

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
                            "skipped_2cc_pending": skipped_2cc_pending,
                            "skipped_partidor_criminal": skipped_partidor_criminal,
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
