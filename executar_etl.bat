@echo off
TITLE Executando ETL TJPE Contadoria
echo [%date% %time%] Iniciando execucao automatica do ETL...
cd /d "%~dp0"
uv run python main.py >> etl_execucao.log 2>&1
echo [%date% %time%] ETL finalizado com codigo de erro %errorlevel%. >> etl_execucao.log
