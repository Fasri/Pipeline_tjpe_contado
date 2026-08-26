import streamlit as st
import pandas as pd
import os
import requests
from io import StringIO
from dotenv import load_dotenv
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# 1. Configuração da página - Executive Dark & Glassmorphism Design
st.set_page_config(
    page_title="Dashboard Contadoria Estratégica - TJPE",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Estilo CSS Customizado Avançado (Glassmorphism & Neon Modern Dark)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Background Principal */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Header do Dashboard */
    .dash-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        margin-bottom: 2rem;
    }
    
    .dash-header h1 {
        font-weight: 800 !important;
        font-size: 2rem !important;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .dash-header p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.3rem !important;
        margin-bottom: 0 !important;
    }
    
    /* Cards de KPI */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #151c2c, #111827);
        padding: 1.4rem 1.6rem !important;
        border-radius: 16px !important;
        border: 1px solid #1e293b !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: #38bdf8 !important;
        box-shadow: 0 12px 28px rgba(56, 189, 248, 0.15) !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #f8fafc !important;
        letter-spacing: -0.5px;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Abas Customizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #111827;
        padding: 8px;
        border-radius: 14px;
        border: 1px solid #1e293b;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        padding: 0 20px;
        background-color: transparent;
        border: none !important;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }

    /* Gráficos Container */
    .js-plotly-plot {
        border-radius: 16px !important;
        background: #151c2c !important;
        padding: 12px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0d1322 !important;
        border-right: 1px solid #1e293b !important;
    }

    /* Dataframe */
    .stDataFrame {
        background: #151c2c !important;
        border-radius: 14px !important;
        border: 1px solid #1e293b;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Carregamento Robusto de Variáveis e Dados
def load_env_robust():
    current_path = Path(__file__).resolve().parent
    for _ in range(3):
        env_path = current_path / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return True
        current_path = current_path.parent
    return False

load_env_robust()

@st.cache_data(ttl=600)
def load_data():
    """Carrega dados via Supabase Storage com fallback resiliente para arquivo CSV local."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    df = None
    source = "desconhecida"

    # Tentativa 1: Supabase API Storage
    if supabase_url and supabase_key:
        try:
            file_name = "tempo_real_Consolidado_supabase.csv"
            url = f"{supabase_url}/storage/v1/object/authenticated/relatorios/{file_name}"
            headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
            
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                csv_text = response.content.decode('utf-8', errors='replace')
                df = pd.read_csv(StringIO(csv_text))
                source = "Supabase Cloud"
        except Exception:
            df = None

    # Tentativa 2: Fallback Arquivo Local CSV
    if df is None:
        local_paths = [
            Path(__file__).resolve().parent.parent / "data_transform" / "Consolidado_supabase.csv",
            Path(__file__).resolve().parent.parent / "data_transform" / "Consolidado.csv",
            Path("Consolidado_supabase.csv")
        ]
        for p in local_paths:
            if p.exists():
                try:
                    df = pd.read_csv(p)
                    source = f"Base Local ({p.name})"
                    break
                except Exception:
                    continue

    if df is not None:
        # Tratamento de Encoding
        def clean_text(val):
            if pd.isna(val) or not isinstance(val, str):
                return val
            replacements = {
                'Âª': 'ª', 'Ãª': 'ê', 'Ã¡': 'á', 'Ã©': 'é', 'Ã': 'í', 
                'Ã³': 'ó', 'Ãº': 'ú', 'Ã£': 'ã', 'Ãµ': 'õ', 'Ã§': 'ç', 
                'Ã ': 'à', 'Â°': '°', 'Ã´': 'ô'
            }
            for bad, good in replacements.items():
                val = val.replace(bad, good)
            return val

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(clean_text)

        # Processamento de Datas e Idade em Dias
        if 'data' in df.columns:
            df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', dayfirst=True, errors='coerce')
            df['data_dt'] = df['data_dt'].fillna(pd.to_datetime(df['data'], dayfirst=True, errors='coerce'))
            hoje = datetime.now()
            df['dias_aberto'] = (hoje - df['data_dt']).dt.days.fillna(0).astype(int)
        else:
            df['dias_aberto'] = 0

        # Faixas de SLA
        def categorizar_faixa(dias):
            if dias < 15:
                return "< 15 dias"
            elif dias <= 30:
                return "15 a 30 dias"
            elif dias <= 60:
                return "31 a 60 dias"
            else:
                return "> 60 dias (Crítico)"

        df['faixa_sla'] = df['dias_aberto'].apply(categorizar_faixa)

    return df, source


def main():
    # Header Principal
    st.markdown("""
        <div class="dash-header">
            <div>
                <h1>⚖️ Dashboard Estratégico da Contadoria</h1>
                <p>Tribunal de Justiça de Pernambuco (TJPE) — Monitoramento em Tempo Real & Indicadores de Desempenho</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Sincronizando base de dados..."):
        df, data_source = load_data()

    if df is None or df.empty:
        st.error("⚠️ Não foi possível carregar os dados. Verifique a conexão com o Supabase ou os arquivos em `data_transform/`.")
        return

    # Sidebar com Filtros
    st.sidebar.markdown("### 🎛️ Filtros Globais")
    st.sidebar.caption(f"Fonte de Dados: **{data_source}**")

    # Filtro por Núcleo
    todos_nucleos = sorted(df['nucleo'].dropna().unique().tolist()) if 'nucleo' in df.columns else []
    selected_nucleos = st.sidebar.multiselect("Núcleo da Contadoria", options=todos_nucleos, default=todos_nucleos)

    # Filtro por Prioridade
    todas_prioridades = sorted(df['prioridades'].dropna().unique().tolist()) if 'prioridades' in df.columns else []
    selected_prioridades = st.sidebar.multiselect("Nível de Prioridade", options=todas_prioridades, default=todas_prioridades)

    # Filtro por Faixa de SLA
    faixas_ordenadas = ["< 15 dias", "15 a 30 dias", "31 a 60 dias", "> 60 dias (Crítico)"]
    selected_faixas = st.sidebar.multiselect("Faixa de SLA (Dias em Aberto)", options=faixas_ordenadas, default=faixas_ordenadas)

    # Busca por número do processo
    busca_processo = st.sidebar.text_input("🔍 Buscar Processo (Número)", "")

    # Aplicar Filtros ao Dataframe
    df_filtered = df.copy()
    if selected_nucleos and 'nucleo' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['nucleo'].isin(selected_nucleos)]
    if selected_prioridades and 'prioridades' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['prioridades'].isin(selected_prioridades)]
    if selected_faixas and 'faixa_sla' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['faixa_sla'].isin(selected_faixas)]
    if busca_processo:
        df_filtered = df_filtered[df_filtered['processo'].astype(str).str.contains(busca_processo, case=False, na=False)]

    # Cálculo dos KPIs de topo
    total_geral = len(df_filtered)
    total_super = len(df_filtered[df_filtered['prioridades'] == 'Super prioridade']) if 'prioridades' in df_filtered.columns else 0
    total_legal = len(df_filtered[df_filtered['prioridades'] == 'Prioridade Legal']) if 'prioridades' in df_filtered.columns else 0
    total_atraso = len(df_filtered[df_filtered['dias_aberto'] >= 30])
    media_dias = int(df_filtered['dias_aberto'].mean()) if total_geral > 0 else 0

    # Exibição de KPIs Executivos
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("TOTAL DE PROCESSOS", f"{total_geral:,}".replace(',', '.'))
    with k2:
        st.metric("SUPER PRIORIDADES", f"{total_super:,}".replace(',', '.'))
    with k3:
        st.metric("PRIORIDADE LEGAL", f"{total_legal:,}".replace(',', '.'))
    with k4:
        st.metric("PROCESSOS ≥ 30 DIAS", f"{total_atraso:,}".replace(',', '.'), delta=f"{(total_atraso/total_geral*100):.1f}% do total" if total_geral > 0 else "0%", delta_color="inverse")
    with k5:
        st.metric("MÉDIA DE DIAS EM ABERTO", f"{media_dias} dias")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Estrutura de Abas Interativas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral Estratégica", 
        "⚖️ Prioridades & Gargalos", 
        "⏱️ Monitor de SLA & Atrasos", 
        "📋 Central de Processos"
    ])

    # ABA 1: VISÃO GERAL ESTRATÉGICA
    with tab1:
        c1, c2 = st.columns([6, 4])
        with c1:
            st.markdown("#### 🌳 Distribuição Geral de Processos por Núcleo")
            if 'nucleo' in df_filtered.columns and not df_filtered.empty:
                df_nucleo = df_filtered.groupby('nucleo').size().reset_index(name='Total')
                fig_tree = px.treemap(
                    df_nucleo, 
                    path=['nucleo'], 
                    values='Total',
                    color='Total', 
                    color_continuous_scale='Blues'
                )
                fig_tree.update_traces(textinfo="label+value", textfont=dict(size=16, color="#ffffff"))
                fig_tree.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=380
                )
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Sem dados para a combinação de filtros selecionada.")

        with c2:
            st.markdown("#### 🎯 Proporção de Prioridades")
            if 'prioridades' in df_filtered.columns and not df_filtered.empty:
                df_prio = df_filtered['prioridades'].value_counts().reset_index()
                df_prio.columns = ['Prioridade', 'Total']
                fig_donut = px.pie(
                    df_prio, 
                    names='Prioridade', 
                    values='Total', 
                    hole=0.55,
                    color_discrete_sequence=['#f43f5e', '#fb923c', '#38bdf8', '#94a3b8']
                )
                fig_donut.update_traces(textinfo="percent+label", marker=dict(line=dict(color='#0b0f19', width=2)))
                fig_donut.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=380
                )
                st.plotly_chart(fig_donut, use_container_width=True)

    # ABA 2: PRIORIDADES & GARGALOS
    with tab2:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### 🚨 Superprioridades por Núcleo")
            df_super = df_filtered[df_filtered['prioridades'] == 'Super prioridade']
            if not df_super.empty:
                super_counts = df_super['nucleo'].value_counts().reset_index()
                super_counts.columns = ['Núcleo', 'Total']
                fig_super = px.bar(
                    super_counts, 
                    x='Total', 
                    y='Núcleo', 
                    orientation='h',
                    color='Total', 
                    color_continuous_scale='Reds',
                    text_auto=True
                )
                fig_super.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=360
                )
                st.plotly_chart(fig_super, use_container_width=True)
            else:
                st.info("Nenhum processo com Superprioridade encontrado.")

        with col_p2:
            st.markdown("#### ⚖️ Prioridade Legal por Núcleo")
            df_legal = df_filtered[df_filtered['prioridades'] == 'Prioridade Legal']
            if not df_legal.empty:
                legal_counts = df_legal['nucleo'].value_counts().reset_index()
                legal_counts.columns = ['Núcleo', 'Total']
                fig_legal = px.bar(
                    legal_counts, 
                    x='Total', 
                    y='Núcleo', 
                    orientation='h',
                    color='Total', 
                    color_continuous_scale='Oranges',
                    text_auto=True
                )
                fig_legal.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=360
                )
                st.plotly_chart(fig_legal, use_container_width=True)
            else:
                st.info("Nenhum processo com Prioridade Legal encontrado.")

        st.markdown("---")
        st.markdown("#### 🏛️ Top 15 Varas mais Sobrecarregadas (Gargalos Críticos)")
        if 'vara' in df_filtered.columns and not df_filtered.empty:
            varas_top = df_filtered['vara'].value_counts().head(15).reset_index()
            varas_top.columns = ['Vara', 'Total Processos']
            fig_varas = px.bar(
                varas_top, 
                x='Vara', 
                y='Total Processos', 
                color='Total Processos',
                color_continuous_scale='Plasma',
                text_auto=True
            )
            fig_varas.update_layout(
                xaxis_tickangle=-40,
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=50, l=10, r=10),
                height=420
            )
            st.plotly_chart(fig_varas, use_container_width=True)

    # ABA 3: MONITOR DE SLA & ATRASOS
    with tab3:
        s1, s2 = st.columns([5, 5])
        with s1:
            st.markdown("#### ⏳ Distribuição por Faixa de Idade (SLA)")
            if 'faixa_sla' in df_filtered.columns and not df_filtered.empty:
                sla_counts = df_filtered['faixa_sla'].value_counts().reindex(faixas_ordenadas, fill_value=0).reset_index()
                sla_counts.columns = ['Faixa SLA', 'Quantidade']
                fig_sla = px.bar(
                    sla_counts, 
                    x='Faixa SLA', 
                    y='Quantidade',
                    color='Faixa SLA',
                    color_discrete_map={
                        "< 15 dias": "#10b981",
                        "15 a 30 dias": "#38bdf8",
                        "31 a 60 dias": "#fb923c",
                        "> 60 dias (Crítico)": "#f43f5e"
                    },
                    text_auto=True
                )
                fig_sla.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=380
                )
                st.plotly_chart(fig_sla, use_container_width=True)

        with s2:
            st.markdown("#### 📊 Concentração de Atrasos (≥ 30 Dias) por Núcleo")
            df_atrasados = df_filtered[df_filtered['dias_aberto'] >= 30]
            if not df_atrasados.empty:
                atraso_nucleo = df_atrasados['nucleo'].value_counts().reset_index()
                atraso_nucleo.columns = ['Núcleo', 'Atrasados']
                fig_atr_nuc = px.bar(
                    atraso_nucleo, 
                    x='Núcleo', 
                    y='Atrasados', 
                    color='Atrasados',
                    color_continuous_scale='YlOrRd',
                    text_auto=True
                )
                fig_atr_nuc.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=380
                )
                st.plotly_chart(fig_atr_nuc, use_container_width=True)
            else:
                st.success("🎉 Nenhum processo com atraso igual ou superior a 30 dias nos filtros selecionados!")

    # ABA 4: CENTRAL DE PROCESSOS & EXPORTAÇÃO
    with tab4:
        st.markdown("#### 📋 Listagem Detalhada de Processos")
        
        col_actions1, col_actions2 = st.columns([8, 2])
        with col_actions1:
            st.caption(f"Mostrando **{len(df_filtered):,}** registros ordenados pelos processos com maior tempo em aberto.")
        with col_actions2:
            # Botão de Exportação CSV
            csv_data = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar CSV",
                data=csv_data,
                file_name=f"contadoria_tjpe_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

        cols_display = [col for col in ['processo', 'data', 'vara', 'nucleo', 'prioridades', 'dias_aberto', 'faixa_sla'] if col in df_filtered.columns]
        
        st.dataframe(
            df_filtered[cols_display].sort_values(by='dias_aberto', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=480
        )

if __name__ == "__main__":
    main()
