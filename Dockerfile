FROM apache/airflow:2.10.5

USER root

RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY pyproject.toml /opt/airflow/pyproject.toml

RUN pip install --no-cache-dir \
    gdown>=5.2.1 \
    google-api-python-client>=2.193.0 \
    google-auth>=2.49.1 \
    google-auth-httplib2>=0.3.0 \
    google-auth-oauthlib>=1.3.0 \
    gspread>=6.2.1 \
    openpyxl>=3.1.5 \
    pandas>=3.0.1 \
    pydrive>=1.3.1 \
    pydrive2>=1.21.3 \
    pyotp>=2.9.0 \
    python-dotenv>=1.2.2 \
    selenium>=4.41.0 \
    supabase>=2.28.3 \
    webdriver-manager>=4.0.2 \
    psycopg2-binary>=2.9.9