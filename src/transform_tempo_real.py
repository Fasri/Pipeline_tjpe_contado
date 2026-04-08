def transform_tempo_real():
    import pandas as pd
    import glob
    import shutil
    import os
    from pathlib import Path
    from datetime import datetime
    from dotenv import load_dotenv

    BASE_DIR = Path(__file__).parent.parent
    load_dotenv(BASE_DIR / ".env")
    
    download_path_str = os.getenv("DOWNLOAD_PATH", "data_tempo_real")
    download_path = Path(download_path_str)
    if not download_path.is_absolute():
        download_path = BASE_DIR / download_path
    
    list_of_files = glob.glob(str(download_path / '*.xlsx'))
    
    if not list_of_files:
        raise FileNotFoundError(f"Nenhum arquivo xlsx encontrado em {download_path}")
    
    print(f"Arquivos encontrados: {list_of_files}")
    file_path = max(list_of_files, key=os.path.getctime)
    print(f"Arquivo mais recente: {file_path}")

    df = pd.read_excel(file_path)

    num_colunas = df.shape[1]
    print(f"Número de colunas no DataFrame: {num_colunas}")

    df_selected = df[['unidade_judiciaria', 'npu', 'data_entrada_tarefa_atual', 'dias_aguardando_tarefa', 
                    'prioridade', 'lista_prioridades', 'contadoria_partidor']]

    novas = ['vara', 'processo', 'data', 'dias', 'prioridade', 'lista_prioridades', 'nucleo']
    df_selected.columns = novas[:len(df_selected.columns)]
    df_selected = df_selected[['nucleo','processo', 'vara', 'data', 'dias', 'prioridade', 'lista_prioridades']]

    def determinar_prioridade(lista_prioridades):
        if pd.isna(lista_prioridades):
            return "Sem prioridade"
        prioridades = lista_prioridades.split(';')
        super_prioridades = ["Pessoa idosa (80+)", "Doença terminal", "Pessoa com deficiência", "Deficiente físico","Deficiente Físico"]
        for prioridade in prioridades:
            if prioridade.strip() in super_prioridades:
                return "Super prioridade"
        return "Prioridade Legal"

    df_selected['prioridades'] = df_selected['lista_prioridades'].apply(determinar_prioridade)

    df_selected = df_selected.drop(columns=['prioridade','lista_prioridades'])

    df_selected = df_selected.drop_duplicates(subset=['processo', 'data'])

    df_selected = df_selected[["nucleo","processo","vara","data","prioridades","dias"]]
    df_selected = df_selected.fillna("")

    df_selected["dias"] = df_selected["dias"].str.split(",").str[0]

    def formatar_data(data):
        if pd.isna(data):
            return None
        primeira_data = data.split(',')[0].strip().replace("'","")
        data_formatada = pd.to_datetime(primeira_data, format='%d/%m/%Y %H:%M:%S', errors='coerce')
        if data_formatada is pd.NaT:
            return None
        return data_formatada.strftime('%d/%m/%Y')

    df_selected['data'] = df_selected['data'].apply(formatar_data)

    substituicoes_ccj = {
        '1ª CONTADORIA DE CÁLCULOS JUDICIAIS': '1ª CCJ',
        '2ª CONTADORIA DE CÁLCULOS JUDICIAIS': '2ª CCJ',
        '3ª CONTADORIA DE CÁLCULOS JUDICIAIS': '3ª CCJ',
        '4ª CONTADORIA DE CÁLCULOS JUDICIAIS': '4ª CCJ',
        '5ª CONTADORIA DE CÁLCULOS JUDICIAIS': '5ª CCJ',
        '6ª CONTADORIA DE CÁLCULOS JUDICIAIS': '6ª CCJ',
        '':'PARTIDOR'
    }

    substituicoes_cc = {
        '1ª CONTADORIA DE CUSTAS': '1ª CC',
        '2ª CONTADORIA DE CUSTAS': '2ª CC',
        '3ª CONTADORIA DE CUSTAS': '3ª CC',
        '4ª CONTADORIA DE CUSTAS': '4ª CC',
        '5ª CONTADORIA DE CUSTAS': '5ª CC',
        '6ª CONTADORIA DE CUSTAS': '6ª CC',
        '7ª CONTADORIA DE CUSTAS': '7ª CC'
    }

    todas_substituicoes = {**substituicoes_ccj, **substituicoes_cc}

    df_selected['nucleo'] = df_selected['nucleo'].replace(todas_substituicoes)

    print("\nValores únicos na coluna Núcleo após as substituições:")
    print(df_selected['nucleo'].unique())

    nucleos = sorted(df_selected['nucleo'].unique())

    quantidade_processos = df_selected['nucleo'].value_counts().reset_index()
    quantidade_processos.columns = ['nucleo', 'quantidade']
    quantidade_processos['data'] = datetime.now().strftime('%d/%m/%Y')
    quantidade_processos = quantidade_processos[['data', 'nucleo','quantidade']]
    
    data_transform_dir = BASE_DIR / "data_transform"
    os.makedirs(data_transform_dir, exist_ok=True)
    
    quantidade_processos.to_excel(data_transform_dir / 'quantidade_processos.xlsx', index=False)
    
    consolidado = df_selected

    divided_file_path = data_transform_dir / 'final_tempo_real.xlsx'

    file_path_xlsx = data_transform_dir / 'Consolidado.xlsx'
    file_path_csv = data_transform_dir / 'Consolidado.csv'
    file_path_csv_supabase = data_transform_dir / 'Consolidado_supabase.csv'
    supabase_dir = BASE_DIR / 'supabase'
    supabase_file_path_csv = supabase_dir / 'Consolidado_supabase.csv'
    destination_xlsx = BASE_DIR / 'contadoria' / 'data_transform'
    destination_csv = BASE_DIR / 'contadoria' / 'data_transform'

    os.makedirs(destination_xlsx, exist_ok=True)
    os.makedirs(supabase_dir, exist_ok=True)

    with pd.ExcelWriter(file_path_xlsx) as writer:
        consolidado.to_excel(writer, sheet_name='CONSOLIDADO', index=False)

    consolidado.to_csv(file_path_csv, index=False, encoding='utf-8')

    consolidado_supabase = consolidado[['processo', 'data', 'vara', 'nucleo', 'prioridades']]
    consolidado_supabase.to_csv(file_path_csv_supabase, index=False, encoding='utf-8')
    consolidado_supabase.to_csv(supabase_file_path_csv, index=False, encoding='utf-8')

    print(f'Arquivos copiados para {destination_xlsx} e {destination_csv}') 

    with pd.ExcelWriter(divided_file_path) as writer:
        for nucleo in nucleos:
            df_nucleo = df_selected[df_selected['nucleo'] == nucleo]
            df_nucleo = df_nucleo.sort_values(by='dias')

            nome_planilha = nucleo if nucleo else "Sem_Nucleo"
            
            df_nucleo.to_excel(writer, sheet_name=nome_planilha, index=False)
    
        quantidade_processos.to_excel(writer, sheet_name='QUANTIDADE', index=False)
        consolidado.to_excel(writer, sheet_name='CONSOLIDADO', index=False)
    
    os.remove(file_path)

    shutil.move(str(divided_file_path), str(divided_file_path))

    print(f"A tabela modificada foi salva como {divided_file_path}")


if __name__ == "__main__":
    transform_tempo_real()
