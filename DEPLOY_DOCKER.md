# Guia de Deploy com Docker - VPS Oracle Cloud (1GB RAM)

Este guia descreve como realizar o deploy do projeto ETL Contadoria usando Docker e Docker Compose, otimizado para instâncias com recursos limitados.

## 🚀 1. Preparação da VPS (Obrigatório)

Em instâncias de 1GB de RAM, o Airflow pode travar o sistema. Para evitar isso, **é obrigatório configurar o Swap**.

### Configurar 4GB de Swap
Execute os comandos abaixo na sua VPS:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Instalar Docker e Docker Compose
Caso ainda não tenha instalado:
```bash
# Atualizar pacotes
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable --now docker
# Adicionar seu usuário ao grupo docker para não precisar de sudo
sudo usermod -aG docker $USER
# Reinicie a sessão SSH após o comando acima
```

---

## 📂 2. Preparação do Projeto

### Clonar o Repositório
```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd projeto_etl_contadoria
```

### Configurar Variáveis de Ambiente
Crie o arquivo `.env` baseado no seu ambiente local:
```bash
nano .env
```
*(Cole suas chaves do Supabase, Banco de Dados, etc.)*

### Arquivos de Credenciais (Google Sheets/Drive)
Certifique-se de que os arquivos `credentials.json` e `token.json` (se existirem) estejam na raiz do projeto ou no local esperado pelo seu código, para que o Docker possa montá-los.

---

## 🛠️ 3. Deploy com Docker

### Build e Inicialização
O comando abaixo irá construir a imagem (usando o `uv` para velocidade máxima) e subir os serviços (Postgres, Airflow Webserver e Scheduler):

```bash
docker-compose up --build -d
```

### Verificar se está rodando
```bash
docker-compose ps
```

### Acessar Logs (Útil para Debug)
```bash
docker-compose logs -f scheduler
```

---

## 🌐 4. Acesso ao Airflow

1.  Abra o navegador e acesse: `http://<IP_DA_SUA_VPS>:8080`
2.  **Usuário Padrão:** `admin`
3.  **Senha Padrão:** `admin` (conforme configurado no `docker-compose.yaml`)

---

## ⚙️ 5. Manutenção e Atualização

### Atualizar o Código
Sempre que fizer alterações no código ou no `pyproject.toml`, execute:
```bash
git pull
docker-compose up --build -d
```

### Limpeza de Cache (Se o disco encher)
```bash
docker system prune -a
```

---

## ⚠️ Notas Importantes para 1GB de RAM

*   **LocalExecutor:** Este projeto está configurado para usar o `LocalExecutor`, eliminando a necessidade de Redis e Workers extras, economizando cerca de 400MB de RAM.
*   **Limites de Memória:** O Docker está configurado para limitar o uso de RAM de cada container. Se uma tarefa falhar por falta de memória, verifique se o arquivo Swap foi criado corretamente.
*   **Selenium no Docker:** O container já inclui o Firefox (ESR) e o driver necessários. No seu código, certifique-se de usar o Selenium em modo **headless**:
    ```python
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    ```

---

## 🛠️ Comandos Úteis do Docker

*   **Parar tudo:** `docker-compose down`
*   **Reiniciar um serviço específico:** `docker-compose restart scheduler`
*   **Entrar no container do Airflow:** `docker-compose exec airflow-webserver bash`
