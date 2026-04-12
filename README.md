# ETL TJPE Contadoria

Projeto de ETL para extração e tratamento de dados de processos destinados à contadoria remota do Tribunal de Justiça de Pernambuco (TJPE), com dashboard analítico e chatbot inteligente integrados.

## 🚀 Funcionalidades

### 📊 Dashboard Analítico (Streamlit)
- **Visualização**: Conexão direta com o Supabase Storage.
- **KPIs Estratégicos**: 
    - Total de processos pendentes.
    - Monitoramento de processos com mais de 30 dias de atraso.
    - Identificação de **Superprioridades** e **Prioridades Legais**.
- **Análise de Gargalos**: Gráficos de barras evidenciando as varas com maior acúmulo.
- **Produtividade por Núcleo**: Distribuição de volume e atrasos por equipe.
- **Design Premium**: Interface moderna em Modo Escuro (Dark Professional).

### 🤖 Chatbot Inteligente (Streamlit + Groq)
- **Interface Conversacional**: Nova interface Streamlit para interação fluida.
- **IA de Alta Performance**: Integrado ao **Groq (Llama 3)** para respostas ultra-rápidas.
- **Consciência de Contexto**: Analisa simultaneamente dados do Google Sheets e arquivos consolidados do Supabase.
- **Consultas complexas**: Responde sobre pendências, núcleos sobrecarregados e varas críticas.

### ⚙️ ETL (Extract, Transform, Load)
- **Extração**: Download automático de dados de processos via site do TJPE.
- **Transformação**: Processamento, limpeza de encoding e tratamento de acentuação.
- **Carregamento**: Envio sincronizado para Google Sheets e Supabase Storage (relatórios consolidados).
- **Automação**: Orquestração via Apache Airflow.

## 🛠️ Stacks Utilizadas

- **Linguagem**: Python 3.13
- **Frontend/Dashboards**: Streamlit
- **IA/LLM**: Groq (Llama 3) / Google Gemini
- **Orquestração**: Apache Airflow
- **Dados**: Pandas, Google Sheets API
- **Infraestrutura**: Supabase (Storage & DB), Docker

## 📖 Como Usar

### Instalação

1. Clone o repositório e instale as dependências:
```bash
uv sync
# ou
pip install -r requirements.txt
```

2. Configure o arquivo `.env`:
```env
# Credenciais Supabase
SUPABASE_URL=sua_url
SUPABASE_KEY=sua_key

# IA
GROQ_API_KEY=sua_chave_groq
GEMINI_API_KEY=sua_chave_gemini
```

### Executando as Aplicações

#### 📈 Abrir o Dashboard de Gestão
```bash
streamlit run src/app_dashboard.py
```

#### 🤖 Iniciar o Chatbot Assistente
```bash
cd chatbot
streamlit run app.py
```

## 📂 Estrutura do Projeto

```
projeto_etl_contadoria/
├── src/                    # Scripts de ETL e Dashboard
│   ├── app_dashboard.py    # Painel Streamlit principal
│   ├── load_supabase_tempo_real.py
│   └── ...
├── chatbot/                # Assistente Virtual
│   ├── app.py             # Interface Streamlit do Chat
│   ├── main.py            # API FastAPI (Legado)
│   └── services/          # Conectores IA e Dados
├── airflow/               # DAGs de Automação
├── data_transform/        # Cache de transformações
├── supabase/              # Arquivos locais de referência
└── .env                   # Configurações sensíveis
```

## 📝 Variáveis de Ambiente Principais

| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto no Supabase |
| `SUPABASE_KEY` | Chave de acesso API/Service |
| `GROQ_API_KEY` | Chave para IA Groq (Recomendado) |
| `GEMINI_API_KEY`| Chave reserva Google Gemini |

## ⚖️ Licença
MIT
