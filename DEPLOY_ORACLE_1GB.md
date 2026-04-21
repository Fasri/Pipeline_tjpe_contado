# Deploy no Oracle VPS (1 CPU, 1GB RAM) com Airflow

## ⚠️ Pré-requisito: Criar swap

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

## 1. Atualizar sistema e instalar dependências

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3.11 python3-pip python3.11-venv git libpq-dev gcc
```

## 2. Criar ambiente virtual

```bash
cd ~
mkdir airflow_venv
python3.11 -m venv airflow_venv
source airflow_venv/bin/activate

pip install --upgrade pip
```

## 3.Instalar Airflow e dependências do projeto

```bash
# Variáveis de ambiente do Airflow
export AIRFLOW_HOME=~/airflow
export AIRFLOW__CORE__FERNET_KEY=''
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION='True'
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__API__AUTH_BACKENDS='airflow.api.auth.backend.basic_auth'
export PATH=$AIRFLOW_HOME/bin:$PATH

pip install apache-airflow==2.10.5

# Instalar dependências do projeto
pip install streamlit plotly pandas requests python-dotenv supabase gspread openpyxl psycopg2-binary fastapi uvicorn groq
```

## 4. Inicializar Airflow

```bash
# Criar diretório de dags
mkdir -p $AIRFLOW_HOME/dags

# Inicializar banco de dados
airflow db init
```

## 5. Criar usuário admin

```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin123
```

## 6. Criar serviço systemd (auto-iniciar)

```bash
sudo tee /etc/systemd/system/airflow-webserver.service > /dev/null <<EOF
[Unit]
Description=Airflow Webserver
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$AIRFLOW_HOME
Environment="PATH=$HOME/airflow_venv/bin:$PATH"
Environment="AIRFLOW_HOME=$HOME/airflow"
ExecStart=$HOME/airflow_venv/bin/python -m airflow webserver --port 8080
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/airflow-scheduler.service > /dev/null <<EOF
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$AIRFLOW_HOME
Environment="PATH=$HOME/airflow_venv/bin:$PATH"
Environment="AIRFLOW_HOME=$HOME/airflow"
ExecStart=$HOME/airflow_venv/bin/python -m airflow scheduler
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver
sudo systemctl enable airflow-scheduler
sudo systemctl start airflow-scheduler
sudo systemctl start airflow-webserver
```

## 7. Copiar DAGs para o servidor

```bash
# Copiar seu arquivo de DAG para o servidor
scp -r sua_pasta_dags user@seu_servidor:$AIRFLOW_HOME/dags/
```

## 8. Acessar

```
http://seu_ip:8080
```

## Troubleshooting

```bash
# Verificar logs
sudo journalctl -u airflow-webserver -f
sudo journalctl -u airflow-scheduler -f

# Verificar uso de memória
free -h
htop

# Se der Out of Memory, aumentar swap
sudo fallocate -l 4G /swapfile
sudo swapon /swapfile
```

## Configurações recomendadas para 1GB RAM

Editar `$AIRFLOW_HOME/airflow.cfg`:

```ini
[core]
 parallelism = 2
 dag_concurrency = 2

[webserver]
 worker_refresh_batch_size = 1
 worker_refresh_interval = 600

[scheduler]
 max_tis_per_query = 25
```

---

**Nota:** Com 1GB RAM + 2GB swap, o Airflow vai funcionar mas com lentidão. Para melhor performance, considere upgrade para 2GB RAM.