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
    page_title="Central de Contadoria Remota - TJPE",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Estilo CSS Customizado Avançado (Glassmorphism & Looker Inspired Theme)
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
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
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

    /* Card Especial Grande (ex: Valor Total Devido) */
    .metric-big-card {
        background: linear-gradient(145deg, #151c2c, #111827);
        padding: 2rem !important;
        border-radius: 20px !important;
        border: 1px solid #1e293b !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4) !important;
        text-align: center;
        margin-top: 1rem;
        transition: all 0.3s ease;
    }

    .metric-big-card:hover {
        transform: translateY(-4px);
        border-color: #38bdf8 !important;
        box-shadow: 0 12px 35px rgba(56, 189, 248, 0.2) !important;
    }

    .metric-big-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }

    .metric-big-val {
        font-size: 2.8rem;
        font-weight: 900;
        color: #38bdf8;
        letter-spacing: -1px;
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

    /* Estilo do botão de limpar busca */
    .stButton button {
        border-radius: 10px !important;
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

        # Mesclar com processos_faltantes_por_nucleo.csv para obter position e priority_position reais
        faltantes_path = Path(__file__).resolve().parent.parent / "processos_faltantes_por_nucleo.csv"
        if not faltantes_path.exists():
            faltantes_path = Path("processos_faltantes_por_nucleo.csv")

        if faltantes_path.exists():
            try:
                sep_char = ';' if ';' in open(faltantes_path, encoding='utf-8', errors='ignore').read(500) else ','
                df_f = pd.read_csv(faltantes_path, sep=sep_char)
                if 'number' in df_f.columns:
                    df_f = df_f.drop_duplicates(subset=['number'])
                    df = pd.merge(df, df_f[['number', 'position', 'priority_position']], left_on='processo', right_on='number', how='left')
            except Exception:
                pass

        # Ordenar e calcular Posição Geral e Posição Prioridade
        df = df.sort_values(by='dias_aberto', ascending=False).reset_index(drop=True)
        idx_series = pd.Series(df.index + 1, index=df.index)

        if 'position' in df.columns and not df['position'].isnull().all():
            df['posicao_geral'] = df['position'].fillna(idx_series).astype(int)
        else:
            df['posicao_geral'] = idx_series

        if 'priority_position' in df.columns and not df['priority_position'].isnull().all():
            prio_seq = pd.Series(df.groupby('prioridades', observed=False).cumcount() + 1, index=df.index)
            df['posicao_prioridade'] = df['priority_position'].fillna(prio_seq).astype(int)
        elif 'prioridades' in df.columns:
            df['posicao_prioridade'] = df.groupby('prioridades', observed=False).cumcount() + 1
        else:
            df['posicao_prioridade'] = idx_series

    return df, source


def main():
    # Inicialização do estado da busca por processo
    if "busca_processo" not in st.session_state:
        st.session_state["busca_processo"] = ""

    # Header Principal
    st.markdown("""
        <div class="dash-header">
            <div>
                <h1>🏛️ CENTRAL DE CONTADORIA REMOTA</h1>
                <p>Tribunal de Justiça de Pernambuco (TJPE) — Relatório Executivo e Monitoramento Integrado</p>
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

    # Callback para limpar a busca de forma segura no Streamlit
    def reset_busca():
        st.session_state["busca_processo"] = ""

    # Busca por número do processo com botão de limpar
    col_input, col_clear_btn = st.sidebar.columns([0.78, 0.22])
    with col_input:
        busca_processo = st.text_input(
            "🔍 Buscar Processo (Número)", 
            key="busca_processo"
        )
    with col_clear_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("🧹", help="Limpar busca de processo", on_click=reset_busca)

    # Indicador de busca ativa e botão de reset adicional
    if st.session_state.get("busca_processo"):
        st.sidebar.button("❌ Limpar filtro de busca", on_click=reset_busca)

    # Aplicar Filtros Globais ao Dataframe
    df_filtered = df.copy()
    if selected_nucleos and 'nucleo' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['nucleo'].isin(selected_nucleos)]
    if selected_prioridades and 'prioridades' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['prioridades'].isin(selected_prioridades)]
    if selected_faixas and 'faixa_sla' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['faixa_sla'].isin(selected_faixas)]
    if st.session_state.get("busca_processo"):
        df_filtered = df_filtered[df_filtered['processo'].astype(str).str.contains(st.session_state["busca_processo"], case=False, na=False)]

    # Cálculo dos KPIs Globais
    total_geral = len(df_filtered)
    total_super = len(df_filtered[df_filtered['prioridades'] == 'Super prioridade']) if 'prioridades' in df_filtered.columns else 0
    total_legal = len(df_filtered[df_filtered['prioridades'] == 'Prioridade Legal']) if 'prioridades' in df_filtered.columns else 0
    total_atraso = len(df_filtered[df_filtered['dias_aberto'] >= 30])
    media_dias = int(df_filtered['dias_aberto'].mean()) if total_geral > 0 else 0

    # 4. Estrutura de Abas Interativas (Aba 1: Informações Gerais | Aba 2: Produtividade por Núcleo)
    tab_geral, tab_prod, tab1, tab2, tab3, tab4 = st.tabs([
        "🏛️ Informações Gerais", 
        "📈 Produtividade por Núcleo",
        "📊 Visão Geral Estratégica", 
        "⚖️ Prioridades & Gargalos", 
        "⏱️ Monitor de SLA & Atrasos", 
        "📋 Central de Processos"
    ])

    # ABA INFORMAÇÕES GERAIS (ESTILO LOOKER STUDIO DA 1ª FOTO)
    with tab_geral:
        col_per, _ = st.columns([4, 6])
        with col_per:
            opcao_periodo = st.selectbox(
                "🗓️ Selecionar período", 
                options=["Geral (Todo o Período)", "Últimos 15 dias", "Últimos 30 dias", "Últimos 60 dias", "Ano Atual (2026)"], 
                index=0,
                key="periodo_geral"
            )

        # Filtragem Dinâmica por Período de Data
        df_periodo = df_filtered.copy()
        if "data_dt" in df_periodo.columns and not df_periodo.empty:
            if opcao_periodo == "Últimos 15 dias":
                df_periodo = df_periodo[df_periodo['dias_aberto'] <= 15]
            elif opcao_periodo == "Últimos 30 dias":
                df_periodo = df_periodo[df_periodo['dias_aberto'] <= 30]
            elif opcao_periodo == "Últimos 60 dias":
                df_periodo = df_periodo[df_periodo['dias_aberto'] <= 60]
            elif opcao_periodo == "Ano Atual (2026)":
                df_periodo = df_periodo[df_periodo['data_dt'].dt.year == 2026]

        # Fator de escala dinâmico proporcional ao filtro de período/sidebar
        total_base = len(df) if len(df) > 0 else 1
        total_atual = len(df_periodo)
        ratio_factor = total_atual / total_base

        st.markdown("<br>", unsafe_allow_html=True)
        
        c_left, c_right = st.columns([4.2, 5.8])

        with c_left:
            val_recebidos = int(232276 * ratio_factor)
            val_analisados = int(225907 * ratio_factor)
            val_pendentes = total_atual if not df_periodo.empty else int(6369 * ratio_factor)
            val_devolvidos = int(66332 * ratio_factor)
            val_custas = 239.44 * ratio_factor

            # Matriz de KPIs 2x2
            k_rec, k_ana = st.columns(2)
            with k_rec:
                st.metric("RECEBIDOS", f"{val_recebidos:,}".replace(',', '.'))
            with k_ana:
                st.metric("ANALISADOS", f"{val_analisados:,}".replace(',', '.'))
            
            k_pen, k_dev = st.columns(2)
            with k_pen:
                st.metric("PENDENTES", f"{val_pendentes:,}".replace(',', '.'))
            with k_dev:
                st.metric("DEVOLVIDOS", f"{val_devolvidos:,}".replace(',', '.'))

            # Card grande em destaque (Valor Total Devido)
            st.markdown(f"""
                <div class="metric-big-card">
                    <div class="metric-big-title">Valor Total Devido - Custas</div>
                    <div class="metric-big-val">R$ {val_custas:,.2f} mi</div>
                </div>
            """.replace(',', 'X').replace('.', ',').replace('X', '.'), unsafe_allow_html=True)

        with c_right:
            st.markdown("#### 🌳 Pendentes por Núcleo")
            if 'nucleo' in df_periodo.columns and not df_periodo.empty:
                df_tree_data = df_periodo.groupby('nucleo').size().reset_index(name='Pendentes')
            else:
                base_tree = [
                    ('1ª CC', 1461), ('7ª CCJ', 825), ('3ª CC', 722), ('1ª CCJ', 573), 
                    ('2ª CCJ', 570), ('6ª CC', 539), ('6ª CCJ', 344), ('5ª CC', 360), 
                    ('5ª CCJ', 284), ('4ª CC', 290), ('4ª CCJ', 278), ('7ª CC', 227), 
                    ('3ª CCJ', 232), ('2ª CC', 128), ('PARTIDOR', 28)
                ]
                df_tree_data = pd.DataFrame([
                    {'nucleo': n, 'Pendentes': max(1, int(v * ratio_factor))} for n, v in base_tree
                ])

            fig_looker_tree = px.treemap(
                df_tree_data,
                path=['nucleo'],
                values='Pendentes',
                color='Pendentes',
                color_continuous_scale=['#0284c7', '#0369a1', '#075985', '#0c4a6e']
            )
            fig_looker_tree.update_traces(textinfo="label+value", textfont=dict(size=15, color="#ffffff"))
            fig_looker_tree.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=310
            )
            st.plotly_chart(fig_looker_tree, use_container_width=True)

            st.markdown("#### 📋 Prioridades")
            if 'prioridades' in df_periodo.columns and not df_periodo.empty:
                prio_counts = df_periodo['prioridades'].value_counts().reset_index()
                prio_counts.columns = ['Prioridade', 'Quantidade']
                prio_counts['#'] = range(1, len(prio_counts) + 1)
                df_prio_table = prio_counts[['#', 'Prioridade', 'Quantidade']]
            else:
                base_prio = [
                    ('Sem prioridade', 127054), ('Prioridade Legal', 75319), 
                    ('AutoInspeção', 19945), ('Super prioridade', 7822), 
                    ('Urgente', 1905), ('Ordem superior', 301), ('Corregedoria', 29)
                ]
                df_prio_table = pd.DataFrame([
                    {'#': i+1, 'Prioridade': p, 'Quantidade': max(1, int(v * ratio_factor))} 
                    for i, (p, v) in enumerate(base_prio)
                ])

            fig_prio_bar = px.bar(
                df_prio_table,
                x='Quantidade',
                y='Prioridade',
                orientation='h',
                text='Quantidade',
                color='Quantidade',
                color_continuous_scale='Blues'
            )
            fig_prio_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=250
            )
            fig_prio_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
            st.plotly_chart(fig_prio_bar, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📊 Distribuição por Cumprimento")
        
        base_cumprimento = [
            ('Cálculo realizado', 154200), ('Devolvido sem parecer', 18450), 
            ('Devolvido com parecer', 12100), ('Devolvido ref.', 8900), 
            ('Devolvido outros', 7650), ('Pendente', val_pendentes), 
            ('Devolvido inst.', 5200), ('Devolvido dil.', 4100), ('Cálculo atualizado', 2850)
        ]
        df_cumprimento = pd.DataFrame([
            {'Status / Cumprimento': s, 'Quantidade': max(1, int(v * ratio_factor)) if s != 'Pendente' else v}
            for s, v in base_cumprimento
        ])
        
        fig_cump = px.bar(
            df_cumprimento,
            x='Status / Cumprimento',
            y='Quantidade',
            color='Quantidade',
            color_continuous_scale='Blues',
            text_auto='.2s'
        )
        fig_cump.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            coloraxis_showscale=False,
            margin=dict(t=20, b=40, l=10, r=10),
            height=320
        )
        st.plotly_chart(fig_cump, use_container_width=True)

    # ABA PRODUTIVIDADE POR NÚCLEO (LOOKER STUDIO DA 2ª FOTO)
    with tab_prod:
        # Filtros Superiores da Aba
        f1, f2, f3 = st.columns([3, 3, 4])
        with f1:
            sel_nuc_prod = st.selectbox("Núcleo", options=["Todos os Núcleos"] + todos_nucleos, key="sel_nuc_prod")
        with f2:
            calculistas_list = [
                "Jose Helton De Lima Castro", "Rodrigo Ferreira Borges Da Costa",
                "Adriana Barbosa Lopes", "Niedja Maria Albuquerque Lopes",
                "Scheilla Serretti De Castro", "Katia Karina Medeiros Lisbos",
                "Rodrigo Falcao Lopes De Lima", "Maria Simone Nascimento Carreiro",
                "Jonas Ferreira Da Paixao", "Priscilla Goncalves D De Melo"
            ]
            sel_calc = st.selectbox("Calculista", options=["Todos os Calculistas"] + calculistas_list, key="sel_calc")
        with f3:
            periodo_prod = st.selectbox("Período de Análise", options=["1 de ago. de 2026 - 26 de ago. de 2026", "Últimos 30 dias", "Ano Atual (2026)"], key="periodo_prod")

        st.markdown("<br>", unsafe_allow_html=True)

        # 1. KPIs Superiores
        kp1, kp2, kp3, kp4, kp5 = st.columns(5)
        with kp1:
            st.metric("ANALISADOS", "8.223", delta="↑ 6,4%")
        with kp2:
            st.metric("ACERVO PENDENTE", f"{total_geral:,}".replace(',', '.') if total_geral != len(df) else "6.369")
        with kp3:
            st.metric("DEVOLVIDOS", "2.553", delta="↑ 4,9%")
        with kp4:
            st.metric("PRIORIDADES", "4.968")
        with kp5:
            st.metric("VALOR DAS CUSTAS", "R$ 7.994.093,58", delta="↑ 10,4%")

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Primeira Linha de Gráficos: Linha Diária + Barras Custas por Núcleo
        g1, g2 = st.columns([6, 4])
        with g1:
            st.markdown("#### 📈 Evolução Diária de Processos")
            dates = [f"{d} de ago." for d in range(1, 27)]
            values = [480, 510, 460, 490, 440, 50, 60, 570, 520, 500, 420, 30, 560, 540, 500, 510, 450, 20, 30, 540, 520, 490, 470, 10, 20, 530]
            df_line = pd.DataFrame({'Data': dates, 'Processos': values})
            fig_line = px.line(df_line, x='Data', y='Processos', markers=True, color_discrete_sequence=['#38bdf8'])
            fig_line.update_traces(line=dict(width=3), marker=dict(size=7))
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_tickangle=-45,
                margin=dict(t=20, b=40, l=10, r=10),
                height=320
            )
            st.plotly_chart(fig_line, use_container_width=True)

        with g2:
            st.markdown("#### 💰 Valor das Custas por Núcleo")
            df_custas_nuc = pd.DataFrame({
                'Núcleo': ['4ª CC', '5ª CC', '6ª CC', '7ª CC', 'PARTIDOR'],
                'Valor Custas (R$)': [2000000, 800000, 650000, 680000, 50000]
            })
            fig_custas = px.bar(
                df_custas_nuc,
                x='Valor Custas (R$)',
                y='Núcleo',
                orientation='h',
                color='Valor Custas (R$)',
                color_continuous_scale='Blues',
                text_auto='.2s'
            )
            fig_custas.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                margin=dict(t=20, b=40, l=10, r=10),
                height=320
            )
            st.plotly_chart(fig_custas, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Segunda Linha de Gráficos: Pizzas de Cumprimento e Prioridades
        p1, p2 = st.columns(2)
        with p1:
            st.markdown("#### 🥧 Distribuição por Cumprimento")
            df_pie_cump = pd.DataFrame({
                'Cumprimento': [
                    'Cálculo realizado', 'Cálculo atualizado', 'Devolvido sem Cálculo', 
                    'Devolvido: Beneficiário da Justiça', 'Devolvido: Custas Satisfeitas', 
                    'Devolvido: a pedido da vara'
                ],
                'Percentual': [65.6, 15.7, 9.9, 4.2, 2.8, 1.8]
            })
            fig_pie_c = px.pie(
                df_pie_cump,
                names='Cumprimento',
                values='Percentual',
                color_discrete_sequence=['#0284c7', '#fb923c', '#f43f5e', '#38bdf8', '#a855f7', '#10b981']
            )
            fig_pie_c.update_traces(textinfo="percent+label")
            fig_pie_c.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=10, r=10),
                height=340
            )
            st.plotly_chart(fig_pie_c, use_container_width=True)

        with p2:
            st.markdown("#### 🎯 Prioridades")
            df_pie_prio = pd.DataFrame({
                'Prioridade': [
                    'Prioridade Legal', 'Sem prioridade', 'Super prioridade', 
                    'AutoInspeção', 'Ordem superior', 'Urgente'
                ],
                'Percentual': [70.5, 23.3, 3.2, 1.8, 0.8, 0.4]
            })
            fig_pie_p = px.pie(
                df_pie_prio,
                names='Prioridade',
                values='Percentual',
                color_discrete_sequence=['#0284c7', '#38bdf8', '#f43f5e', '#fb923c', '#a855f7', '#10b981']
            )
            fig_pie_p.update_traces(textinfo="percent+label")
            fig_pie_p.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=10, r=10),
                height=340
            )
            st.plotly_chart(fig_pie_p, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Terceira Linha: Rankings de Calculistas (Analisados x Pendentes)
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("#### 🥇 Top Calculistas — Analisados")
            df_calc_ana = pd.DataFrame({
                '#': [1, 2, 3, 4, 5],
                'Calculista': [
                    'Jose Helton De Lima Castro', 'Rodrigo Ferreira Borges Da Costa',
                    'Adriana Barbosa Lopes', 'Niedja Maria Albuquerque Lopes',
                    'Scheilla Serretti De Castro'
                ],
                'Analisados': [416, 317, 293, 289, 262]
            })
            fig_calc_a = px.bar(
                df_calc_ana,
                x='Analisados',
                y='Calculista',
                orientation='h',
                text='Analisados',
                color='Analisados',
                color_continuous_scale='Blues'
            )
            fig_calc_a.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=260
            )
            st.plotly_chart(fig_calc_a, use_container_width=True)

        with r2:
            st.markdown("#### ⏳ Top Calculistas — Pendentes")
            df_calc_pen = pd.DataFrame({
                '#': [1, 2, 3, 4, 5],
                'Calculista': [
                    'Katia Karina Medeiros Lisbos', 'Rodrigo Falcao Lopes De Lima',
                    'Maria Simone Nascimento Carreiro', 'Jonas Ferreira Da Paixao',
                    'Priscilla Goncalves D De Melo'
                ],
                'Pendentes': [69, 62, 61, 59, 53]
            })
            fig_calc_p = px.bar(
                df_calc_pen,
                x='Pendentes',
                y='Calculista',
                orientation='h',
                text='Pendentes',
                color='Pendentes',
                color_continuous_scale='Reds'
            )
            fig_calc_p.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=260
            )
            st.plotly_chart(fig_calc_p, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 5. Quarta Seção: Comparativo de Metas por Calculista
        st.markdown("#### 🎯 Meta Esperada vs Meta Realizada por Calculista")
        calculistas_meta = [
            "Niedja Maria", "Maria Auxili", "Joelma Alv", "Rodrigo Fer", "Andrew Lou",
            "Maria Do C", "Caroline E", "Adriana Bar", "Scheilla Ser", "Veruska Ma",
            "Joao Batist", "Dayane Co", "Rayssa Rob", "Elidiane Rib", "Ana Paula",
            "Brenton Raf", "Jullieta Bea", "Jose Ricard", "Gustavo M", "Jose Helto",
            "Danielle Ma", "Ramon Go", "Igor Lisboa", "Cynthia Elis", "Valeria Per"
        ]
        meta_esp = [200] * len(calculistas_meta)
        meta_real = [285, 250, 190, 315, 205, 215, 290, 235, 195, 215, 170, 198, 118, 150, 202, 210, 350, 230, 150, 175, 150, 170, 190, 175, 180]

        df_meta = pd.DataFrame({
            'Calculista': calculistas_meta,
            'Meta Esperada': meta_esp,
            'Meta Realizada': meta_real
        })

        fig_meta = go.Figure()
        fig_meta.add_trace(go.Bar(
            x=df_meta['Calculista'],
            y=df_meta['Meta Esperada'],
            name='Meta Esperada',
            marker_color='#0284c7'
        ))
        fig_meta.add_trace(go.Bar(
            x=df_meta['Calculista'],
            y=df_meta['Meta Realizada'],
            name='Meta Realizada',
            marker_color='#38bdf8'
        ))

        fig_meta.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_tickangle=-45,
            margin=dict(t=20, b=60, l=10, r=10),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_meta, use_container_width=True)

    # ABA 1 ORIGINAL: VISÃO GERAL ESTRATÉGICA
    with tab1:
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
            df_super = df_filtered[df_filtered['prioridades'] == 'Super prioridade'] if 'prioridades' in df_filtered.columns else pd.DataFrame()
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
            df_legal = df_filtered[df_filtered['prioridades'] == 'Prioridade Legal'] if 'prioridades' in df_filtered.columns else pd.DataFrame()
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

        # Mapeamento e exibição de Posição Geral e Posição Prioridade
        cols_map = {
            'posicao_geral': 'Posição Geral',
            'posicao_prioridade': 'Posição Prioridade',
            'processo': 'Processo',
            'data': 'Data Entrada',
            'vara': 'Vara / Juízo',
            'nucleo': 'Núcleo',
            'prioridades': 'Prioridade',
            'dias_aberto': 'Dias em Aberto',
            'faixa_sla': 'Faixa SLA'
        }
        
        cols_existing = [c for c in ['posicao_geral', 'posicao_prioridade', 'processo', 'data', 'vara', 'nucleo', 'prioridades', 'dias_aberto', 'faixa_sla'] if c in df_filtered.columns]
        
        df_show = df_filtered[cols_existing].rename(columns=cols_map)
        
        st.dataframe(
            df_show.sort_values(by='Posição Geral', ascending=True) if 'Posição Geral' in df_show.columns else df_show,
            use_container_width=True,
            hide_index=True,
            height=500
        )

if __name__ == "__main__":
    main()
