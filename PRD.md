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

### RF06: Sincronização do Banco de Produção e Auditoria (`db_sync`)
O pipeline deve sincronizar a base transacional (`processes`) a partir dos dados do Storage, realizando:
- Backup de segurança automático pré-sincronização.
- Upsert em lotes (batching) com controle de duplicidades.
- Atualização dinâmica da flag `pje` (sinalizando se o processo ainda consta na fila do PJe).
- Monitoramento e marcação de inconsistências temporais (`inconsistencia_tempo_real`).
- Registro detalhado de cada execução na tabela `audit_logs`.

## 6. Requisitos Não Funcionais (RNF)

### RNF01: Performance em Hardware Limitado
O pipeline e o navegador (Firefox Headless) devem ser otimizados para execução em instâncias com 1GB de RAM (ex: Oracle Cloud Free Tier).

### RNF02: Segurança
Todas as credenciais e chaves de API devem ser armazenadas exclusivamente em variáveis de ambiente (`.env`).

### RNF03: Integridade de Dados
O processo de ingestão deve realizar verificação de Checksum (contagem de linhas e hash) para garantir que os dados no DW coincidem com a extração original.

### RNF04: Localização
Todos os timestamps e visualizações devem respeitar o fuso horário de Brasília/Recife e o formato de data brasileiro (DD/MM/YYYY).

## 7. Regras de Negócio (RN)

### RN01: Unicidade e Controle de Pendências Exclusivo da 2ª CC (2ª Contadoria de Custas)
- **Escopo:** Aplica-se exclusivamente aos processos da **2ª CC**. Os demais núcleos mantêm a estratégia padrão de unicidade baseada na chave composta `(number, entry_date, nucleus)`.
- **Bloqueio por Pendência Ativa:** Quando um processo da 2ª CC já possuir registro com status `Pendente` no sistema (`status` iniciado por `"Pendente%"`), qualquer nova ocorrência com o mesmo número de processo — mesmo que venha com data de entrada/remessa diferente — **não deve ser incluída** no banco de dados.
- **Ciclo de Vida / Conclusão:** O bloqueio restringe-se ao período em que o processo permanece pendente. Caso o processo já esteja com status Concluído (ou outro status finalizado) no sistema e surja no arquivo com uma nova remessa/data, a inclusão é realizada normalmente.
- **Desduplicação Intra-Arquivo (Data Mais Antiga):** Caso o relatório diário do PJe traga múltiplas linhas do mesmo processo para a 2ª CC com datas de entrada distintas, o pipeline preserva obrigatoriamente a ocorrência com a **data de entrada mais antiga** (menor valor cronológico).
- **Rastreabilidade e Sincronização de Status:**
  - Os processos da 2ª CC ignorados por pendência ativa são contabilizados nos logs e gravados na tabela `audit_logs` no atributo `skipped_2cc_pending`.
  - O mapeamento geral de processos do arquivo (`file_numbers_set`) preserva esses registros para que a sincronização da flag `pje` continue indicando corretamente que o processo permanece ativo no tribunal.

### RN02: Bloqueio de Varas Criminais no Núcleo Partidor
- **Escopo:** Aplica-se exclusivamente aos processos do núcleo **Partidor** (`PARTIDOR`).
- **Critério de Bloqueio:** Processos em que a vara/unidade judiciária (`court`) contenha o termo `"criminal"` (busca *case-insensitive*) **não devem ser adicionados ao banco de dados** (`processes`).
- **Aplicação:** O filtro atua especificamente nas novas inserções executadas pela rotina de sincronização (`db_sync.py`), sem afetar registros pretéritos já existentes.
- **Rastreabilidade:** O total de processos criminais descartados no Partidor é exibido nos logs de execução e registrado na tabela de auditoria (`audit_logs`) pelo campo `skipped_partidor_criminal`.

## 8. Fluxo de Dados (Data Flow)
1. **TJPE Reports** -> Selenium (Extração) -> `xlsx` local.
2. `xlsx` -> Pandas (Transformação Inicial) -> `csv` local.
3. `csv` -> Supabase Storage (Backup) + Google Sheets (Espelhamento).
4. `csv` -> Supabase Postgres (**db_sync** com aplicação de regras de negócio como RN01).
5. `csv` -> Supabase Postgres (**Bronze Layer** - Data Warehouse).
6. **Bronze** -> dbt run (**Silver/Gold Layers** - Table/View).
7. **Silver/Gold** -> Dashboard / Chatbot.
