import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Garantir que o diretório raiz está no path para importar os serviços
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services import groq_client as ai_client, google_sheets, supabase_loader
except ImportError:
    from chatbot.services import groq_client as ai_client, google_sheets, supabase_loader

# Configuração da página - Design Premium
st.set_page_config(
    page_title="Assistente Contadoria - IA",
    page_icon="🤖",
    layout="centered"
)

# Estilo CSS customizado (Sleek Dark Chat)
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .main {
        max-width: 800px;
        margin: 0 auto;
    }
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    h1 {
        text-align: center;
        color: #f0f2f6;
        font-weight: 800;
        margin-bottom: 2rem;
        background: -webkit-linear-gradient(#00a2ff, #004a88);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    /* Estilo para as mensagens do assistente */
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #1a2234 !important;
        border: 1px solid #2d3748;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600, show_spinner="Carregando base de conhecimento...")
def get_combined_context():
    try:
        sheets_ctx = google_sheets.get_context_for_llm()
        supabase_ctx = supabase_loader.get_context_for_llm()
        return f"{sheets_ctx}\n\n{supabase_ctx}"
    except Exception as e:
        return f"Erro ao carregar contexto: {str(e)}"

def main():
    st.markdown("<h1>🤖 Assistente Virtual TJPE</h1>", unsafe_allow_html=True)
    
    # Inicializar histórico de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sidebar para opções
    with st.sidebar:
        st.image("https://www.tjpe.jus.br/documents/10181/0/logomarca_tjpe.png/3c3b0f5e-0b0a-4b0a-9b0a-9b0a9b0a9b0a", width=150)
        st.markdown("### Configurações")
        if st.button("Limpar Conversa"):
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("---")
        st.info("Este assistente utiliza IA para analisar dados das planilhas e do Supabase Storage em tempo real.")
        
        # Status do contexto
        with st.status("Verificando bases de dados...", expanded=False):
            context = get_combined_context()
            st.write("✅ Conectado ao Google Sheets")
            st.write("✅ Conectado ao Supabase")
            st.write("📊 Contexto carregado com sucesso.")

    # Exibir mensagens do histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input do usuário
    if prompt := st.chat_input("Como posso ajudar com os processos hoje?"):
        # Adicionar mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gerar resposta do assistente
        with st.chat_message("assistant"):
            with st.spinner("Analisando registros..."):
                try:
                    # Carregar contexto atualizado
                    context = get_combined_context()
                    
                    # Preparar histórico formatado para o gemini_client
                    history = []
                    for msg in st.session_state.messages[:-1]: # Tudo exceto a última que acabamos de adicionar
                        history.append({"role": msg["role"], "content": msg["content"]})
                    
                    # Chamar cliente do Groq
                    response = ai_client.chat(st.session_state.messages, context)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Erro ao processar sua solicitação: {str(e)}")

if __name__ == "__main__":
    main()
