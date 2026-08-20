from src.extract_tempo_real import extract_report_tempo_real
from src.transform_tempo_real import transform_tempo_real
from src.load_google_tempo_real import load_tempo_real
from src.load_supabase_tempo_real import load_supabase
from src.db_sync import sync_database_from_storage
from src.ingest_to_dw import ingest as ingest_to_dw
import subprocess


def run_dbt():
    print("\nExecutando dbt (Transformações Silver/Gold)...")
    try:
        subprocess.run(
            ["uv", "run", "dbt", "run", "--profiles-dir", "dbt_contadoria", "--project-dir", "dbt_contadoria"],
            check=True
        )
        print("dbt executado com sucesso!")
    except Exception as e:
        print(f"Aviso: Erro ao executar dbt: {e}")


def etl_tempo_real():
    # print("=== ETL Tempo Real ===\n")

    # print("1/7 - Extraindo relatório...")
    # success = extract_report_tempo_real()
    # if not success:
    #     raise RuntimeError(
    #         "Extração falhou: nenhum arquivo xlsx foi baixado. Pipeline abortado."
    #     )

    # print("\n2/7 - Transformando dados...")
    # transform_tempo_real()

    # print("\n3/7 - Carregando para Google Sheets...")
    # load_tempo_real()

    # print("\n4/7 - Carregando para Supabase (Storage)...")
    # load_supabase()

    # print("\n5/7 - Sincronizando Banco de Dados de Produção (Postgres)...")
    # backup_dir = sync_database_from_storage()

    print("\n6/7 - Sincronizando Data Warehouse (Bronze Layer Incremental)...")
    success = ingest_to_dw()
    if not success:
        print("\n[ERRO] Falha na ingestão do DW. Pipeline interrompido para evitar inconsistências.")
        return

    print("\n7/7 - Processando Camadas Medalhão com dbt...")
    run_dbt()

    print("\n=== Pipeline Completo Concluído ===")


if __name__ == "__main__":
    etl_tempo_real()


