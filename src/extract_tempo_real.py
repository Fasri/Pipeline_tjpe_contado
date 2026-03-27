def extract_report_tempo_real(totp_secret: str | None = None):
    import os
    import shutil
    import glob
    import time
    from pathlib import Path
    from dotenv import load_dotenv
    
    BASE_DIR = Path(__file__).parent.parent
    load_dotenv(BASE_DIR / ".env")
    
    from selenium import webdriver
    from webdriver_manager.firefox import GeckoDriverManager
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    cpf = os.getenv("TJPE_CPF") or ""
    senha = os.getenv("TJPE_SENHA") or ""
    totp_secret = totp_secret or os.getenv("TJPE_TOTP_SECRET") or ""
    download_path = os.getenv("DOWNLOAD_PATH")
    if download_path and not Path(download_path).is_absolute():
        download_path = str(BASE_DIR / download_path)
    
    if not download_path:
        raise ValueError("DOWNLOAD_PATH deve ser definido no arquivo .env")
    
    if not cpf or not senha:
        raise ValueError("TJPE_CPF e TJPE_SENHA devem ser definidos no arquivo .env")
    
    print(f"Iniciando extração - Download path: {download_path}")
    os.makedirs(download_path, exist_ok=True)
    
    fp = Options()
    fp.binary_location = "/usr/bin/firefox-esr"
    fp.set_capability("pageLoadStrategy", "normal")

    fp.add_argument("--headless")
    fp.add_argument("--no-sandbox")
    fp.add_argument("--disable-dev-shm-usage")
    fp.add_argument("--width=1920")
    fp.add_argument("--height=1080")
    fp.set_preference("browser.download.folderList", 2)
    fp.set_preference("browser.download.manager.showWhenStarting", False)
    fp.set_preference("browser.download.dir", download_path)
    fp.set_preference("browser.download.manager.useWindow", False)
    fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream")
    fp.set_preference("browser.helperApps.alwaysAsk.force", False)
    fp.set_preference("browser.download.manager.focusWhenStarting", False)
    fp.set_preference("pdfjs.disabled", True)

    servico = Service(GeckoDriverManager().install())

    navegador = webdriver.Firefox(options=fp, service=servico)
    navegador.set_page_load_timeout(60)
    navegador.delete_all_cookies()
    wait = WebDriverWait(navegador, 30)

    navegador.get("https://www.tjpe.jus.br/tjpereports/xhtml/login.xhtml")
    print(f"Página carregada: {navegador.current_url}")
    print(f"Download path: {download_path}")

    wait.until(EC.presence_of_element_located((By.ID, "username")))

    navegador.find_element('id', 'username').send_keys(cpf)

    wait.until(EC.presence_of_element_located((By.ID, "password")))
    navegador.find_element('id', 'password').send_keys(senha)

    navegador.find_element('id', 'kc-form-login').submit()

    time.sleep(5)
    
    url_atual = navegador.current_url
    print(f"URL após submit: {url_atual}")
    
    if "otp" in url_atual.lower() or "login" in url_atual.lower():
        if totp_secret:
            try:
                import pyotp
                totp = pyotp.TOTP(totp_secret)
                time.sleep(2)
                codigo_totp = totp.now()
                print(f"Código TOTP gerado: {codigo_totp}")
                time.sleep(3)
                try:
                    campo_totp = navegador.find_element('id', 'otp')
                    print(f"Campo OTP encontrado")
                    campo_totp.clear()
                    campo_totp.send_keys(codigo_totp)
                    print(f"Código TOTP inserido")
                    time.sleep(2)
                    navegador.find_element('id', 'kc-otp-login-form').submit()
                    print("Formulário TOTP enviado")
                    time.sleep(5)
                except Exception as e:
                    print(f"Aviso: Não foi possível inserir código TOTP: {e}")
            except ImportError:
                print("Aviso: pyotp não está instalado. Instale com: pip install pyotp")
    
    navegador.get("https://www.tjpe.jus.br/tjpereports/xhtml/manterRelatorio/executarRelatorio.xhtml")
    time.sleep(5)
    
    url_atual = navegador.current_url
    print(f"URL atual: {url_atual}")
    
    if "login" in url_atual.lower() or "otp" in url_atual.lower():
        print("Ainda na página de login/TOTP. Tentando acessar relatório diretamente...")
        navegador.get("https://www.tjpe.jus.br/tjpereports/secure/consulta/ConsultaPrincipal.jspx")
        time.sleep(5)
    
    try:
        wait.until(EC.presence_of_element_located((By.ID, "relatorioForm:pesquisarButton")))
    except:
        print("Timeout esperando botão pesquisar. Tentando continuar...")
        time.sleep(5)
    
    navegador.find_element('xpath', '//*[@id="relatorioForm:j_id61_body"]/table/tbody/tr[1]/td[2]/input').send_keys("PJe 1º Grau | Acervo em Tramitação em tempo real d")
    time.sleep(8)
    navegador.find_element('xpath', '//*[@id="relatorioForm:pesquisarButton"]').click()
    time.sleep(8)
    navegador.find_element('xpath', '/html/body/div/div/div/div/div[9]/div/form/table/tbody/tr/td[7]/table/tbody/tr/td/a/img').click()
    time.sleep(8)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:GRUPO"]').send_keys("TODAS")
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:ORGAO"]').send_keys("TODOS")
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:j_id97:0"]').click()
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:j_id104:1"]').click()
    time.sleep(4)

    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:btnExportarXlsx"]').click()
    print("Botão Exportar XLSX clicado")

    print(f"Aguardando download na pasta: {download_path}")
    
    max_wait = 180
    check_interval = 5
    arquivos_antes = set(os.listdir(download_path))
    
    for i in range(0, max_wait, check_interval):
        time.sleep(check_interval)
        arquivos_atuais = set(os.listdir(download_path))
        novos = arquivos_atuais - arquivos_antes
        xlsx_files = [f for f in novos if f.endswith('.xlsx')]
        if xlsx_files:
            print(f"Download detectado: {xlsx_files}")
            break
        
        for check_dir in ["/home/airflow/Downloads", "/tmp", "/downloads"]:
            if os.path.exists(check_dir):
                extra_files = glob.glob(f"{check_dir}/*.xlsx")
                if extra_files:
                    print(f"Arquivo encontrado em {check_dir}: {extra_files}")
                    for f in extra_files:
                        dest = os.path.join(download_path, os.path.basename(f))
                        shutil.move(f, dest)
                        print(f"Movido para {download_path}")
                    break
    else:
        print("Timeout esperando download")
        arquivos_atuais = os.listdir(download_path)
        print(f"Arquivos na pasta: {arquivos_atuais}")
        
        for check_dir in ["/home/airflow/Downloads", "/tmp", "/downloads", os.path.expanduser("~/Downloads")]:
            if os.path.exists(check_dir):
                extra_files = glob.glob(f"{check_dir}/*.xlsx")
                if extra_files:
                    print(f"Arquivos xlsx encontrados em {check_dir}: {extra_files}")
    
    arquivos_finais = set(os.listdir(download_path))
    novos_arquivos = [f for f in (arquivos_finais - arquivos_antes) if f.endswith('.xlsx')]
    print(f"Novos arquivos xlsx: {novos_arquivos}")
    
    if not novos_arquivos:
        import glob
        xlsx_files = glob.glob(os.path.join(download_path, "*.xlsx"))
        print(f"Arquivos xlsx na pasta: {xlsx_files}")

    print("Fechando navegador...")
    
    import threading
    
    def close_browser():
        try:
            navegador.quit()
        except:
            try:
                navegador.close()
            except:
                pass
    
    close_thread = threading.Thread(target=close_browser)
    close_thread.daemon = True
    close_thread.start()
    close_thread.join(timeout=15)
    
    if close_thread.is_alive():
        print("Timeout ao fechar navegador, continuando...")
    else:
        print("Navegador fechado")
    
    if novos_arquivos:
        print(f"Download concluído: {novos_arquivos}")
        return True
    
    return False


if __name__ == "__main__":
    extract_report_tempo_real()