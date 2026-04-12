# Atualizar BD Contadoria

Projeto Python desenvolvido para automatizar a importação de processos para um banco de dados. A aplicação baixa uma planilha Excel de um Bucket do Supabase, processa os dados, previne duplicidades analisando os processos já existentes e os insere na tabela `processes`. Além disso, registra as operações na tabela de auditoria (`audit_logs`).

## Estrutura do Projeto

```
atualizar_bd_contadoria/
├── .env                  # Configuracoes sensiveis (nao versionado)
├── .env.example          # Exemplo de arquivo de configuracao
├── requirements.txt      # Dependências do projeto
├── main.py               # Ponto de entrada do script
└── src/
    ├── __init__.py
    ├── config.py         # Classe para gerenciamento de variaveis de ambiente
    ├── database.py       # Gerenciamento da conexao com o Supabase
    ├── importer.py       # Logica de importacao e processamento do Excel
    └── utils.py          # Funcoes auxiliares gerais
```

## Como Executar

1. Crie um ambiente virtual usando `uv` (recomendado) ou `venv`:
   ```bash
   uv venv
   # No Windows:
   .venv\Scripts\activate
   ```

2. Instale as dependências:
   ```bash
   uv pip install -r requirements.txt
   ```
   *(Ou use `pip install -r requirements.txt` se não estiver usando o `uv`)*

3. Configure as variáveis de ambiente:
   Copie o arquivo `.env.example` para `.env` e preencha as suas informações de acesso ao Supabase:
   ```bash
   cp .env.example .env
   ```

4. Execute a importação:
   ```bash
   python main.py
   ```
