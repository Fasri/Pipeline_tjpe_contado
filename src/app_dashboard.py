import streamlit as st
import pandas as pd
import os
import requests
from io import StringIO
from dotenv import load_dotenv
from datetime import datetime, timedelta
import plotly.express as px
from pathlib import Path

# Configuração da página - Premium Design
st.set_page_config(
    page_title="Dashboard Contadoria - TJPE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo CSS customizado para visual premium (Dark Professional Theme)
st.markdown("""
    <style>
    /* Estilização Geral */
    .stApp {
        background-color: #0c121c;
        color: #e0e6ed;
    }
    
    /* Cartões de KPI */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #a0aec0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    [data-testid="stMetric"] {
        background: #1a2234;
        padding: 1.8rem !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
        border: 1px solid #2d3748 !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #4a5568 !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6) !important;
    }

    /* Títulos e Textos */
    h1 {
        font-weight: 900 !important;
        color: #ffffff !important;
        text-shadow: 0px 4px 10px rgba(0,0,0,0.5);
        margin-bottom: 2rem !important;
    }
    
    h3, h4 {
        color: #f7fafc !important;
        font-weight: 700 !important;
        margin-top: 1.5rem !important;
    }

    /* Gráficos Plotly */
    .js-plotly-plot {
        border-radius: 16px !important;
        background: #1a2234 !important;
        padding: 10px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0a0e17 !important;
        border-right: 1px solid #2d3748 !important;
    }

    /* Dataframe */
    .stDataFrame {
        background: #1a2234 !important;
        border-radius: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Carregar variáveis de ambiente
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

@st.cache_data(ttl=600)
def load_data_from_supabase():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("Erro: SUPABASE_URL ou SUPABASE_KEY não configurados no arquivo .env")
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
            # Força a interpretação como UTF-8
            csv_text = response.content.decode('utf-8', errors='replace')
            df = pd.read_csv(StringIO(csv_text))
            
            # Tratamento de limpeza para garantir grafia correta (caso haja dupla codificação)
            def clean_encoding_artifacts(text):
                if pd.isna(text) or not isinstance(text, str):
                    return text
                # Correções comuns de mojibake (Latin-1 read as UTF-8 or vice versa)
                replacements = {
                    'Âª': 'ª',
                    'Ãª': 'ê',
                    'Ã¡': 'á',
                    'Ã©': 'é',
                    'Ã': 'í', # Pode ser perigoso se for isolado, mas comum em í
                    'Ã³': 'ó',
                    'Ãº': 'ú',
                    'Ã£': 'ã',
                    'Ãµ': 'õ',
                    'Ã§': 'ç',
                    'Ã ': 'à',
                    'Â°': '°',
                    'Ã´': 'ô'
                }
                for bad, good in replacements.items():
                    text = text.replace(bad, good)
                return text

            # Aplicar limpeza em todas as colunas de texto
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(clean_encoding_artifacts)
                
            return df
        else:
            st.error(f"Erro ao buscar dados do Supabase: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão/codificação: {str(e)}")
        return None

def main():
    st.markdown("<h1>📊 Dashboard Estratégico da Contadoria</h1>", unsafe_allow_html=True)

    with st.spinner("Sincronizando dados com Supabase..."):
        df = load_data_from_supabase()

    if df is not None:
        # Processamento de datas
        df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        hoje = datetime(2026, 4, 12)
        df['dias_aberto'] = (hoje - df['data_dt']).dt.days
        
        # 1. KPIs de Alto Nível
        st.markdown("### 📈 Indicadores Chave")
        col1, col2, col3, col4 = st.columns(4)
        
        total_processos = len(df)
        total_super = len(df[df['prioridades'] == 'Super prioridade'])
        total_legal = len(df[df['prioridades'] == 'Prioridade Legal'])
        total_30_dias = len(df[df['dias_aberto'] > 30])
        
        with col1:
            st.metric("TOTAL GERAL", f"{total_processos}")
        with col2:
            st.metric("SUPER PRIORIDADES", f"{total_super}")
        with col3:
            st.metric("PRIORIDADE LEGAL", f"{total_legal}")
        with col4:
            st.metric("PROCESSOS > 30 DIAS", f"{total_30_dias}", delta=f"{total_30_dias} em atraso", delta_color="inverse")

        st.markdown("---")
        
        # 2. Gráficos de Prioridades
        col_map, col_bar = st.columns(2)
        
        with col_map:
            st.markdown("#### 🌳 Mapa de Árvore: Superprioridades por Vara")
            df_super = df[df['prioridades'] == 'Super prioridade']
            if not df_super.empty:
                fig_tree = px.treemap(df_super, path=['nucleo', 'vara'], 
                                      color_discrete_sequence=px.colors.qualitative.Dark2)
                fig_tree.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Nenhum processo de Superprioridade encontrado.")

        with col_bar:
            st.markdown("#### ⚖️ Prioridade Legal por Núcleo")
            df_legal = df[df['prioridades'] == 'Prioridade Legal']
            if not df_legal.empty:
                legal_counts = df_legal['nucleo'].value_counts().reset_index()
                legal_counts.columns = ['Núcleo', 'Processos']
                fig_legal = px.bar(legal_counts, x='Processos', y='Núcleo', orientation='h',
                                   color='Processos', color_continuous_scale='Viridis')
                fig_legal.update_layout(height=400, margin=dict(t=30, l=10, r=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_legal, use_container_width=True)

        # 3. Distribuição por Núcleo e Atrasos
        st.markdown("---")
        st.markdown("### 🏢 Produtividade e Atrasos por Núcleo")
        col_n1, col_n2 = st.columns(2)
        
        with col_n1:
            st.markdown("#### Volume Total por Núcleo")
            nucleo_total = df['nucleo'].value_counts().reset_index()
            nucleo_total.columns = ['Núcleo', 'Total']
            fig_n_total = px.bar(nucleo_total, x='Núcleo', y='Total', 
                                color='Total', color_continuous_scale='Blues', text_auto=True)
            fig_n_total.update_layout(height=400, margin=dict(t=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_n_total, use_container_width=True)
            
        with col_n2:
            st.markdown("#### Concentração de Processos > 30 Dias")
            df_atraso = df[df['dias_aberto'] > 30]
            if not df_atraso.empty:
                atraso_counts = df_atraso['nucleo'].value_counts().reset_index()
                atraso_counts.columns = ['Núcleo', 'Atrasados']
                fig_n_atraso = px.bar(atraso_counts, x='Núcleo', y='Atrasados', 
                                    color='Atrasados', color_continuous_scale='OrRd', text_auto=True)
                fig_n_atraso.update_layout(height=400, margin=dict(t=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_n_atraso, use_container_width=True)
            else:
                st.info("Nenhum processo com mais de 30 dias.")

        # 4. Análise de Gargalos (Varas)
        st.markdown("---")
        st.markdown("### ⚠️ Gargalos Críticos (Top 10 Varas)")
        
        gargalo_counts = df['vara'].value_counts().head(10).reset_index()
        gargalo_counts.columns = ['Vara', 'Total']
        fig_gargalo = px.bar(gargalo_counts, x='Vara', y='Total', 
                             color='Total', color_continuous_scale='Reds',
                             text_auto=True)
        fig_gargalo.update_layout(xaxis_tickangle=-45, height=450, margin=dict(t=30), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gargalo, use_container_width=True)

        # 5. Detalhamento
        st.markdown("---")
        st.markdown("### 📋 Listagem de Processos críticos")
        
        st.dataframe(df[['processo', 'data', 'vara', 'nucleo', 'prioridades', 'dias_aberto']].sort_values('dias_aberto', ascending=False).head(200), 
                     use_container_width=True, hide_index=True)

    else:
        st.error("Falha ao carregar dados. Verifique a conexão com o Supabase.")

if __name__ == "__main__":
    main()
