from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

sys.path.insert(0, "/opt/airflow/project")

from src.extract_tempo_real import extract_report_tempo_real
from src.transform_tempo_real import transform_tempo_real
from src.load_google_tempo_real import load_tempo_real
from src.load_supabase_tempo_real import load_supabase

with DAG(
    dag_id="etl_tempo_real",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 6 * * *", 
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": 300,
    },
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_report_tempo_real,
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=transform_tempo_real,
    )

    load_google = PythonOperator(
        task_id="load_google_sheets",
        python_callable=load_tempo_real,
    )

    load_supabase = PythonOperator(
        task_id="load_supabase",
        python_callable=load_supabase,
    )

    extract >> transform >> [load_google, load_supabase]