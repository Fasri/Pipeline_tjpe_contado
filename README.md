# ETL TJPE Contadoria

Projeto de ETL para extração e tratamento de dados de processos jurídicos do Tribunal de Justiça de Pernambuco (TJPE), com chatbot integrado para consulta de informações.

## Funcionalidades

### ETL (Extract, Transform, Load)
- **Extração**: Download automático de dados de processos via site do TJPE
- **Transformação**: Processamento e limpeza dos dados
- **Carregamento**: Envio para Google Sheets e banco de dados Supabase
- **Automação**: Agendamento via Apache Airflow

### Chatbot
- Interface web para consulta de processos
- Responde perguntas sobre:
  - Quantidade de processos por contadoria
  - Contadoria com mais/menos processos
  - Localização de processos específicos
  - Processos com prioridade legal
  - Processos mais antigos
- Dados atualizados em tempo real

## Stacks Utilizadas

### Backend
- **Python 3.13**
- **FastAPI** - API web
- **Apache Airflow** - Orquestração de tarefas
- **Pandas** - Manipulação de dados
- **Google API Python Client** - Integração Google Sheets
- **Google Generative AI (Gemini)** - Inteligência artificial

### Banco de Dados
- **PostgreSQL** (via Supabase)

### Infraestrutura
- **Docker** - Containerização
- **Git** - Controle de versão

## Como Usar

### Pré-requisitos
- Python 3.13+
- Credenciais do Google (credentials.json)
- Token de API do Gemini (ou Groq)

### Instalação

1. Clone o repositório:
```bash
git clone <repositorio>
cd projeto_etl_contadoria
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
# ou
uv sync
```

3. Configure as variáveis de ambiente no arquivo `.env`:
```env
# Credenciais TJPE
TJPE_CPF=seu_cpf
TJPE_SENHA=sua_senha
TJPE_TOTP_SECRET=seu_secret

# Credenciais Supabase
SUPABASE_URL=sua_url
SUPABASE_KEY=sua_key

# API Gemini
GEMINI_API_KEY=sua_api_key
```

4. Execute a autenticação Google:
```bash
# O navegador será aberto para autorização
# O token será salvo em token.json
```

### Executando o ETL

```bash
# Executar manualmente
python src/extract_tempo_real.py
python src/transform_tempo_real.py
python src/load_google_tempo_real.py
```

### Executando o Chatbot

```bash
python chatbot/main.py
```

O chatbot estará disponível em http://localhost:8000

### Executando com Docker

```bash
docker-compose up -d
```

## Estrutura do Projeto

```
projeto_etl_contadoria/
├── src/                    # Código fonte do ETL
│   ├── extract_tempo_real.py
│   ├── transform_tempo_real.py
│   ├── load_google_tempo_real.py
│   └── load_supabase_tempo_real.py
├── chatbot/                # Chatbot
│   ├── main.py            # API FastAPI
│   ├── services/
│   │   ├── google_sheets.py
│   │   └── gemini_client.py
│   └── templates/
│       └── index.html
├── airflow/               # Configurações Airflow
├── data_transform/        # Dados processados
├── credentials.json        # Credenciais Google
├── token.json             # Token de acesso Google
└── docker-compose.yaml    # Orquestração Docker
```

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `TJPE_CPF` | CPF para login no TJPE |
| `TJPE_SENHA` | Senha para login no TJPE |
| `TJPE_TOTP_SECRET` | Secret do TOTP |
| `SUPABASE_URL` | URL do banco Supabase |
| `SUPABASE_KEY` | Chave API do Supabase |
| `GEMINI_API_KEY` | Chave API do Gemini |

## Licença

MIT
