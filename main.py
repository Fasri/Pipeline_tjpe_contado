from src.extract_tempo_real import extract_report_tempo_real
from src.transform_tempo_real import transform_tempo_real
from src.load_google_tempo_real import load_tempo_real
from src.load_supabase_tempo_real import load_supabase


def etl_tempo_real():
    print("=== ETL Tempo Real ===\n")
    
    print("1/4 - Extraindo relatório...")
    extract_report_tempo_real()
    
    print("\n2/4 - Transformando dados...")
    transform_tempo_real()
    
    print("\n3/4 - Carregando para Google Sheets...")
    load_tempo_real()
    
    print("\n4/4 - Carregando para Supabase...")
    load_supabase()
    
    print("\n=== ETL Concluído ===")


if __name__ == "__main__":
    etl_tempo_real()