# Documento de Requisitos do Produto (PRD) - ETL TJPE Contadoria

## 1. Visão Geral do Produto
O **ETL TJPE Contadoria** é uma solução completa de engenharia de dados e business intelligence projetada para automatizar o fluxo de trabalho da contadoria remota do Tribunal de Justiça de Pernambuco (TJPE). O sistema extrai dados brutos do sistema de relatórios do tribunal, processa-os através de uma arquitetura de dados moderna e os disponibiliza para análise via dashboards e assistência por IA.

## 2. Objetivos Principais
- Eliminar a extração manual de relatórios xlsx do sistema TJPE.
- Centralizar os dados processuais em um Data Warehouse robusto.
- Fornecer visibilidade em tempo real sobre gargalos, produtividade e prioridades legais.
- Facilitar a consulta de dados complexos através de uma interface de linguagem natural (Chatbot).

## 3. Público-Alvo
- **Gestores de Núcleo**: Para monitoramento de KPIs e alocação de recursos.
- **Calculistas/Servidores**: Para acompanhamento de suas próprias metas e pendências.
- **Administradores do Sistema**: Para garantir a integridade e automação do pipeline.

## 4. Arquitetura e Stack Tecnológica

### 4.1. Camada de Dados (Medallion Architecture)
- **Bronze (Raw)**: Ingestão direta dos dados extraídos, mantendo a fidelidade à origem.
- **Silver (Cleaned)**: Dados tratados, com limpeza de encoding, padronização de datas e junção com tabelas de usuários e núcleos.
- **Gold (Business)**: Tabelas e views otimizadas para consumo pelo dashboard (ex: processos pendentes, metas batidas).

### 4.2. Tecnologias Utilizadas
- **Linguagem**: Python 3.13
- **Extração**: Selenium Webdriver (Firefox Geckodriver) com suporte a autenticação TOTP.
- **Tratamento/ETL**: Pandas e dbt (data build tool).
- **Banco de Dados/DW**: Supabase (PostgreSQL) para tabelas e Storage para arquivos consolidados.
- **Orquestração**: Apache Airflow.
- **Dashboard/UI**: Streamlit.
- **IA**: Groq (Llama 3) e Google Gemini.

## 5. Requisitos Funcionais (RF)

### RF01: Extração Automatizada
O sistema deve realizar o login automático no portal de relatórios do TJPE, utilizando CPF, Senha e gerando o código TOTP dinamicamente para vencer o MFA.

### RF02: Pipeline de ETL (Bronze)
Os dados extraídos em XLSX devem ser convertidos para CSV, limpos (encoding/acentuação) e carregados no DW Bronze utilizando estratégia de **Full Load** (Replace).

### RF03: Transformação de Dados (Silver)
O dbt deve processar os dados da Bronze para a Silver, realizando:
- Conversão de strings de data para objetos `date`.
- De-depara de IDs de usuários para nomes reais.
- Cálculo de métricas como "Dias Parado" e flag de "Meta".

### RF04: Dashboard Analítico
Interface Streamlit que apresente:
- Total de processos pendentes e distribuídos por núcleo.
- Filtros de prioridade legal e superprioridade.
- Gráficos de barras por vara e calculista.

### RF05: Chatbot com Consciência de Dados
Assistente virtual que utiliza RAG (Retrieval-Augmented Generation) para responder perguntas sobre o estado atual do acervo baseado nos dados do DW e do Google Sheets.

## 6. Requisitos Não Funcionais (RNF)

### RNF01: Performance em Hardware Limitado
O pipeline e o navegador (Firefox Headless) devem ser otimizados para execução em instâncias com 1GB de RAM (ex: Oracle Cloud Free Tier).

### RNF02: Segurança
Todas as credenciais e chaves de API devem ser armazenadas exclusivamente em variáveis de ambiente (`.env`).

### RNF03: Integridade de Dados
O processo de ingestão deve realizar verificação de Checksum (contagem de linhas e hash) para garantir que os dados no DW coincidem com a extração original.

### RNF04: Localização
Todos os timestamps e visualizações devem respeitar o fuso horário de Brasília/Recife e o formato de data brasileiro (DD/MM/YYYY).

## 7. Fluxo de Dados (Data Flow)
1. **TJPE Reports** -> Selenium (Extração) -> `xlsx` local.
2. `xlsx` -> Pandas (Transformação Inicial) -> `csv` local.
3. `csv` -> Supabase Storage (Backup) + Google Sheets (Espelhamento).
4. `csv` -> Supabase Postgres (**Bronze Layer** - Replace).
5. **Bronze** -> dbt run (**Silver/Gold Layers** - Table/View).
6. **Silver/Gold** -> Dashboard / Chatbot.
