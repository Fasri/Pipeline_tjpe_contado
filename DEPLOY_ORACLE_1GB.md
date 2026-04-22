# Deploy no Oracle VPS (1 CPU, 1GB RAM) com Airflow

## ⚠️ Pré-requisito: Criar swap
Essencial para evitar erros de "Out of Memory" durante a instalação.

```bash
# Criar 2GB de swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Adicionar ao /etc/fstab para persistir após reboot
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verificar swap
sudo swapon --show
free -h
```

## 1. Firewall e Dependências do Sistema

### Configurar Firewall (UFW)
No Oracle Cloud, você precisa liberar as portas no painel (Security List) e também no SO:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 8501/tcp
sudo ufw enable
```

### Instalar dependências
```bash
sudo apt install -y python3.11 python3-pip python3.11-venv git libpq-dev gcc
```

## 2. Preparar Ambiente e Código

```bash
cd ~
git clone https://github.com/Fasri/Pipeline_tjpe_contado.git
cd Pipeline_tjpe_contado

# Criar ambiente virtual dentro da pasta do projeto
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
```

## 3. Configurar Variáveis de Ambiente

Crie o arquivo `.env` com suas credenciais:

```bash
nano .env
```
(Cole o conteúdo do seu .env local aqui)

## 4. Instalar Airflow e Dependências

```bash
# Definir home do Airflow (pode ser dentro do projeto para facilitar)
export AIRFLOW_HOME=~/airflow
mkdir -p $AIRFLOW_HOME

# Gerar Fernet Key (Segurança)
export AIRFLOW__CORE__FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Outras configs para economizar RAM
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION='True'
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__API__AUTH_BACKENDS='airflow.api.auth.backend.basic_auth'

# Instalar Airflow
pip install "apache-airflow==2.10.5" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt"

# Instalar dependências do projeto
pip install streamlit plotly pandas requests python-dotenv supabase gspread openpyxl psycopg2-binary fastapi uvicorn groq cryptography
```

## 5. Inicializar Airflow

```bash
# Criar diretório de dags e vincular ao projeto
mkdir -p $AIRFLOW_HOME/dags
cp ~/Pipeline_tjpe_contado/airflow/dags/*.py $AIRFLOW_HOME/dags/

# Inicializar banco de dados (SQLite por padrão para economizar RAM)
airflow db init
```

## 6. Criar usuário admin

```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin123
```

## 7. Criar serviços systemd (Auto-iniciar)

### Airflow Webserver
```bash
sudo tee /etc/systemd/system/airflow-webserver.service > /dev/null <<EOF
[Unit]
Description=Airflow Webserver
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/Pipeline_tjpe_contado
Environment="PATH=$HOME/Pipeline_tjpe_contado/venv/bin:$PATH"
Environment="AIRFLOW_HOME=$HOME/airflow"
ExecStart=$HOME/Pipeline_tjpe_contado/venv/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
```

### Airflow Scheduler
```bash
sudo tee /etc/systemd/system/airflow-scheduler.service > /dev/null <<EOF
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/Pipeline_tjpe_contado
Environment="PATH=$HOME/Pipeline_tjpe_contado/venv/bin:$PATH"
Environment="AIRFLOW_HOME=$HOME/airflow"
ExecStart=$HOME/Pipeline_tjpe_contado/venv/bin/airflow scheduler
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
```

### Streamlit (Dashboard)
```bash
sudo tee /etc/systemd/system/streamlit-app.service > /dev/null <<EOF
[Unit]
Description=Streamlit Dashboard
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/Pipeline_tjpe_contado
Environment="PATH=$HOME/Pipeline_tjpe_contado/venv/bin:$PATH"
ExecStart=$HOME/Pipeline_tjpe_contado/venv/bin/streamlit run main.py --server.port 8501
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

### Ativar serviços
```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver airflow-scheduler streamlit-app
sudo systemctl start airflow-webserver airflow-scheduler streamlit-app
```

## 8. Acessar

- **Airflow:** `http://seu_ip:8080` (admin / admin123)
- **Streamlit:** `http://seu_ip:8501`

## Troubleshooting

```bash
# Verificar logs
sudo journalctl -u airflow-webserver -f
sudo journalctl -u streamlit-app -f

# Se der Out of Memory (OOM), verifique o swap
free -h

# Se precisar aumentar o swap de 2GB para 4GB:
sudo swapoff /swapfile
sudo fallocate -l 4G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Configurações recomendadas para 1GB RAM

No arquivo `~/airflow/airflow.cfg`:

```ini
[core]
# SequentialExecutor é o mais leve (padrão com SQLite)
executor = SequentialExecutor
parallelism = 1
dag_concurrency = 1
max_active_runs_per_dag = 1

[scheduler]
# Diminuir frequência de scan para poupar CPU
dag_dir_list_interval = 300
min_file_process_interval = 300
```

---

**Nota:** O Airflow em 1GB RAM é extremamente limitado. Use apenas para agendamentos simples. Se o Scheduler começar a cair, a única solução real é aumentar a RAM para 2GB ou 4GB.