FROM apache/airflow:2.10.5

USER root

# Instalar dependências de sistema para o Selenium/Firefox e o uv
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Adicionar uv ao PATH
ENV PATH="/root/.local/bin/:$PATH"

# Copiar os arquivos de configuração do projeto
COPY pyproject.toml uv.lock /opt/airflow/

# Instalar as dependências usando o uv como root para ter permissão no sistema
RUN uv pip install --system -r pyproject.toml

USER airflow