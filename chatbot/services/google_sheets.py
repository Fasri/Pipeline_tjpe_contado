from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent.parent
DATA_FILE = BASE_DIR / "data_transform" / "final_tempo_real.xlsx"


def get_sheet_data(max_rows=50):
    if not DATA_FILE.exists():
        return {"Erro": f"Arquivo não encontrado: {DATA_FILE}"}
    
    sheets = pd.read_excel(DATA_FILE, sheet_name=None)
    
    all_data = {}
    for sheet_name, df in sheets.items():
        df_limited = df.head(max_rows)
        all_data[sheet_name] = df_limited.to_string(index=False)
    
    return all_data


def get_context_for_llm():
    data = get_sheet_data(max_rows=50)
    context = "Dados da planilha final_tempo_real.xlsx:\n\n"
    
    for sheet_name, content in data.items():
        context += f"=== {sheet_name} ===\n"
        context += content + "\n\n"
    
    if len(context) > 8000:
        context = context[:8000] + "\n\n[continua...]"
    
    return context
