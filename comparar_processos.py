import pandas as pd
import os

# Caminhos dos arquivos (ajustados para serem relativos à raiz onde o script ficará)
excel_path = r'data_transform/final_tempo_real.xlsx'
csv_path = r'data_transform/backups/20260507_051612/processes.csv'
output_path = 'processos_faltantes_por_nucleo.csv'

def comparar_processos():
    print("Iniciando comparação de processos...")
    
    # 1. Carregar Excel (final_tempo_real.xlsx)
    try:
        print(f"Lendo Excel: {excel_path}")
        df_excel = pd.read_excel(excel_path)
        # Normalizar coluna 'number' do Excel
        if 'number' in df_excel.columns:
            excel_numbers = set(df_excel['number'].astype(str).str.strip())
        else:
            # Caso o header seja diferente no Excel, tenta encontrar algo parecido
            possible_cols = [c for c in df_excel.columns if 'number' in c.lower() or 'processo' in c.lower()]
            if possible_cols:
                print(f"Usando coluna '{possible_cols[0]}' do Excel para comparação.")
                excel_numbers = set(df_excel[possible_cols[0]].astype(str).str.strip())
            else:
                print("ERRO: Coluna de identificação não encontrada no Excel.")
                return
    except Exception as e:
        print(f"Erro ao ler Excel: {e}")
        return

    # 2. Carregar CSV (processes.csv)
    try:
        print(f"Lendo CSV: {csv_path}")
        # Usamos low_memory=False para evitar warnings em arquivos grandes
        df_csv = pd.read_csv(csv_path, low_memory=False)
        
        # 3. Filtrar apenas processos com status 'pendente'
        # Usamos .str.lower() para garantir que pegamos todas as variações (Pendente, pendente, etc)
        if 'status' in df_csv.columns:
            df_csv['status_normalized'] = df_csv['status'].astype(str).str.lower().str.strip()
            df_pendentes = df_csv[df_csv['status_normalized'] == 'pendente'].copy()
            print(f"Total de processos pendentes encontrados no CSV: {len(df_pendentes)}")
        else:
            print("ERRO: Coluna 'status' não encontrada no CSV.")
            return

        if len(df_pendentes) == 0:
            print("AVISO: Nenhum processo com status 'pendente' foi encontrado no CSV.")
            # Vamos mostrar os status existentes para ajudar o usuário
            print(f"Status encontrados no CSV: {df_csv['status'].unique().tolist()}")
            return

        # 4. Comparar e encontrar os que NÃO estão no Excel
        # Normalizar coluna 'number' do CSV
        df_pendentes['number_clean'] = df_pendentes['number'].astype(str).str.strip()
        
        df_faltantes = df_pendentes[~df_pendentes['number_clean'].isin(excel_numbers)].copy()
        
        print(f"Processos pendentes que não estão no Excel: {len(df_faltantes)}")

        # 5. Organizar e Salvar
        if len(df_faltantes) > 0:
            # Selecionar apenas colunas relevantes para o relatório final
            # Ordenar por núcleo para facilitar a visualização
            if 'nucleus' in df_faltantes.columns:
                df_faltantes = df_faltantes.sort_values(by='nucleus')
            
            # Remover colunas auxiliares de normalização antes de salvar
            cols_to_drop = ['status_normalized', 'number_clean']
            df_faltantes = df_faltantes.drop(columns=[c for c in cols_to_drop if c in df_faltantes.columns])
            
            df_faltantes.to_csv(output_path, index=False, encoding='utf-8-sig', sep=';')
            print(f"\nSUCESSO! O arquivo '{output_path}' foi gerado na raiz.")
            print(f"Total de registros: {len(df_faltantes)}")
        else:
            print("\nNenhum processo pendente do CSV está faltando no Excel.")

    except Exception as e:
        print(f"Erro ao processar CSV: {e}")

if __name__ == "__main__":
    comparar_processos()
