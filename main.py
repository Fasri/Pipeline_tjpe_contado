from src.extract_tempo_real import extract_report_tempo_real
from src.transform_tempo_real import transform_tempo_real
from src.load_google_tempo_real import load_tempo_real
from src.load_supabase_tempo_real import load_supabase
from src.db_sync import sync_database_from_storage


def etl_tempo_real():
    print("=== ETL Tempo Real ===\n")
    
    print("1/5 - Extraindo relatório...")
    extract_report_tempo_real()
    
    print("\n2/5 - Transformando dados...")
    transform_tempo_real()
    
    print("\n3/5 - Carregando para Google Sheets...")
    load_tempo_real()
    
    print("\n4/5 - Carregando para Supabase (Storage)...")
    load_supabase()
    
    print("\n5/5 - Sincronizando Banco de Dados (Postgres)...")
    sync_database_from_storage()
    
    print("\n=== ETL Concluído ===")



if __name__ == "__main__":
    etl_tempo_real()