import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import time

# Configura caminhos para o diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY não configurados no arquivo .env.")
    return create_client(url, key)

def main():
    print("=== Atualização de Prioridade: AutoInspeção ===")
    
    # 1. Carregar arquivo Excel
    excel_path = BASE_DIR / "Relatorio Autoinspeção 2026.1 - versão 2.xlsx"
    if not excel_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {excel_path}")
        return
        
    print("1/5 - Carregando arquivo Excel...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo Excel: {e}")
        return
    
    # Verificar se a coluna NPU existe
    if 'NPU' not in df.columns:
        print(f"[ERRO] A coluna 'NPU' não foi encontrada. Colunas disponíveis: {df.columns.tolist()}")
        return
        
    # Extrair e padronizar os NPUs do Excel (remover pontuações para garantir o match)
    npus_excel = df['NPU'].dropna().astype(str).str.strip().tolist()
    npus_excel_clean = {npu.replace(".", "").replace("-", "") for npu in npus_excel}
    print(f"      -> Encontrados {len(npus_excel)} processos no arquivo Excel.")
    
    # 2. Conectar ao banco de dados Supabase
    print("\n2/5 - Conectando ao Supabase...")
    try:
        supabase = get_supabase_client()
    except Exception as e:
        print(f"[ERRO] Falha ao conectar ao Supabase: {e}")
        return
    
    # 3. Buscar processos pendentes no banco de dados
    print("\n3/5 - Buscando processos pendentes no banco...")
    all_pending = []
    page_size = 1000
    start = 0
    
    while True:
        try:
            response = supabase.table("processes").select("id, number").eq("status", "Pendente").range(start, start + page_size - 1).execute()
            data = response.data
            
            if not data:
                break
                
            all_pending.extend(data)
            
            if len(data) < page_size:
                break
                
            start += page_size
        except Exception as e:
            print(f"[ERRO] Falha na busca ao banco na página inicial {start}: {e}")
            break
            
    print(f"      -> Encontrados {len(all_pending)} processos com status 'Pendente' no banco.")
    
    # 4. Comparar processos
    print("\n4/5 - Cruzando dados (Excel x Banco)...")
    to_update = []
    
    for proc in all_pending:
        db_number = str(proc.get('number', '')).strip()
        db_number_clean = db_number.replace(".", "").replace("-", "")
        
        # Se o NPU limpo do banco existe na lista limpa do Excel
        if db_number_clean in npus_excel_clean:
            to_update.append(proc['id'])
            
    print(f"      -> {len(to_update)} processos correspondentes encontrados que necessitam de atualização.")
    
    if not to_update:
        print("\n=== Processo Concluído: Nenhum processo pendente para atualizar. ===")
        return
        
    # 5. Atualizar os processos no Supabase
    print("\n5/5 - Atualizando prioridades no banco para 'AutoInspeção'...")
    updated_count = 0
    errors_count = 0
    
    for proc_id in to_update:
        try:
            # Atualiza a prioridade para AutoInspeção
            supabase.table("processes").update({"priority": "AutoInspeção"}).eq("id", proc_id).execute()
            updated_count += 1
            
            # Feedback visual a cada 50 registros
            if updated_count % 50 == 0:
                print(f"      -> Progresso: {updated_count}/{len(to_update)} atualizados...")
                time.sleep(0.5)  # Breve pausa para evitar Rate Limit na API do Supabase
                
        except Exception as e:
            print(f"      -> [ERRO] Falha ao atualizar ID {proc_id}: {e}")
            errors_count += 1
            
    print(f"\n=== Resumo da Operação ===")
    print(f"Total de processos identificados: {len(to_update)}")
    print(f"Prioridades atualizadas com sucesso: {updated_count}")
    if errors_count > 0:
        print(f"Erros durante atualização: {errors_count}")

if __name__ == "__main__":
    main()
