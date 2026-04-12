import os
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

load_dotenv()

def get_supabase_data():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        return None

    file_name = "tempo_real_Consolidado_supabase.csv"
    url = f"{supabase_url}/storage/v1/object/authenticated/relatorios/{file_name}"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            csv_text = response.content.decode('utf-8', errors='replace')
            df = pd.read_csv(StringIO(csv_text))
            
            # Limpeza rápida de encoding
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.replace('Âª', 'ª').replace('Ã©', 'é').replace('Ã£', 'ã').replace('Ã³', 'ó')
            
            return df
    except Exception as e:
        print(f"Erro ao carregar dados do Supabase para o Chatbot: {e}")
        return None

def get_context_for_llm():
    df = get_supabase_data()
    if df is None:
        return "Dados do Supabase não disponíveis."

    hoje = datetime(2026, 4, 12)
    df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    df['dias_aberto'] = (hoje - df['data_dt']).dt.days

    # Gerar resumo para o contexto
    total_geral = len(df)
    total_30_dias = len(df[df['dias_aberto'] > 30])
    
    resumo_nucleos = df['nucleo'].value_counts().to_string()
    resumo_atrasos_nucleos = df[df['dias_aberto'] > 30]['nucleo'].value_counts().to_string()
    resumo_varas = df['vara'].value_counts().head(10).to_string()
    
    # Processos mais antigos (Top 20 para contexto)
    mais_antigos = df.sort_values('dias_aberto', ascending=False).head(20)[['processo', 'vara', 'nucleo', 'dias_aberto']].to_string(index=False)

    context = f"""
=== DADOS CONSOLIDADOS TJPE (DATA DE REFERÊNCIA: 12/04/2026) ===
TOTAL GERAL DE PROCESSOS: {total_geral}
PROCESSOS EM ATRASO (> 30 DIAS): {total_30_dias}

DISTRIBUIÇÃO POR NÚCLEO (TOTAL):
{resumo_nucleos}

CONCENTRAÇÃO DE ATRASOS (> 30 DIAS) POR NÚCLEO:
{resumo_atrasos_nucleos}

TOP 10 VARAS COM MAIS PROCESSOS (GARGALOS):
{resumo_varas}

AMOSTRA DOS 20 PROCESSOS MAIS ANTIGOS:
{mais_antigos}
============================================================
"""
    return context
