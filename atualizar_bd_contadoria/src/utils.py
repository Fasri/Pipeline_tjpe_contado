import unicodedata
import pandas as pd

def normalize_text(text):
    """Remove acentos e padroniza para comparação (igual ao sistema)"""
    if not text or pd.isna(text): return ""
    text = str(text).strip()
    return "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn').upper()

def get_val(row, possible_names, default=""):
    """Tenta encontrar a coluna mesmo com nomes levemente diferentes."""
    for name in possible_names:
        if name in row:
            return row[name]
    return default
