# Deploy no Oracle VPS (1 CPU, 1GB RAM) usando Cron (Sem Docker / Sem Airflow)

Este guia apresenta o passo a passo para configurar o seu servidor Oracle Cloud utilizando apenas o sistema operacional (`cron`), otimizando drasticamente o uso de memória (1GB RAM) ao remover o peso do Airflow e do Docker.

## 1. Pré-requisito: Criar Swap
Mesmo sem o Docker/Airflow, processos pontuais pesados (como manipulação de grandes DataFrames) podem estourar 1GB de RAM. Vamos garantir um fôlego:

```bash
# Criar 2GB de swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Adicionar ao /etc/fstab para persistir após reiniciar o servidor
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verificar swap
sudo swapon --show
free -h
```

## 2. Instalação das Dependências do Sistema

Como estamos num Ubuntu limpo, precisamos garantir as ferramentas básicas e o gerenciador de pacotes `uv` (usado no projeto).

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git python3-venv python3-pip

# Instalar o 'uv' (gerenciador de pacotes rápido que você está utilizando)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Recarregue o terminal para o uv ficar disponível ou rode:
source $HOME/.cargo/env
```

## 3. Configurar o Projeto

Clone o seu repositório para o servidor. Se for um repositório privado, use um Personal Access Token ou chave SSH.

```bash
# Navegar para o diretório do usuário
cd ~

# Clonar o projeto (ajuste a URL)
git clone https://github.com/SEU_USUARIO/projeto_etl_contadoria.git
cd projeto_etl_contadoria

# Criar o ambiente virtual e sincronizar as dependências usando uv
uv venv
uv pip sync requirements.txt
```

### Configurando Credenciais
Você precisa subir os arquivos sensíveis que não estão no GitHub (`.env`, `credentials.json`, `token.json` e o `Relatorio Autoinspeção 2026.1 - versão 2.xlsx`).

```bash
# Crie o arquivo .env
nano .env
# Cole o conteúdo do seu .env local e salve (Ctrl+O, Enter, Ctrl+X)

# Crie a pasta para logs
mkdir -p logs
```

*(Lembre-se de transferir os arquivos via SCP/SFTP, como FileZilla ou Cyberduck, para dentro da pasta `~/projeto_etl_contadoria`)*.

## 4. Agendamento das Tarefas (Crontab)

O sistema de agendamento nativo do Linux é o `cron`. Ele é extremamente leve e perfeito para essa arquitetura de 1GB de RAM.

Vamos abrir o editor do cron:
```bash
crontab -e
```
*(Se perguntar qual editor usar, escolha o número correspondente ao `nano`)*

No final do arquivo, adicione as seguintes linhas:

```cron
# Definir variáveis de ambiente para o cron encontrar o executável correto (uv e python)
PATH=/home/ubuntu/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/home/ubuntu

# 1. Executar main.py todo dia às 03:00 da manhã
0 3 * * * cd /home/ubuntu/projeto_etl_contadoria && uv run python main.py >> /home/ubuntu/projeto_etl_contadoria/logs/main_etl.log 2>&1

# 2. Executar script de AutoInspeção de segunda a sexta-feira às 05:00 da manhã
0 5 * * 1-5 cd /home/ubuntu/projeto_etl_contadoria && uv run python autoinspecao/atualizar_prioridade_autoinspecao.py >> /home/ubuntu/projeto_etl_contadoria/logs/autoinspecao.log 2>&1
```

### Explicando a configuração do Cron:
* `0 3 * * *`: Roda no minuto 0, da hora 3 (03:00 AM), todos os dias do mês, todos os meses, todos os dias da semana.
* `0 5 * * 1-5`: Roda no minuto 0, da hora 5 (05:00 AM), `1-5` significa Segunda a Sexta.
* `>> /caminho/do/log.log 2>&1`: Salva todo o histórico e os erros em arquivos `.log` dentro da pasta `logs`, para você auditar o funcionamento sem precisar de uma interface gráfica complexa.

## 5. Como Monitorar (Operação no dia a dia)

Como removemos o Airflow (que dava a interface web), você monitora pelo terminal.

Para ver os logs do ETL principal em tempo real:
```bash
tail -f ~/projeto_etl_contadoria/logs/main_etl.log
```

Para ver os logs da AutoInspeção:
```bash
tail -f ~/projeto_etl_contadoria/logs/autoinspecao.log
```

Para forçar a execução manual do script e ver se está tudo certo:
```bash
cd ~/projeto_etl_contadoria
uv run python main.py
```
