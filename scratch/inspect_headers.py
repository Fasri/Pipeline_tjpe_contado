import pandas as pd
import csv

def inspect_files():
    print("--- Inspecting Excel file: final_tempo_real.xlsx ---")
    try:
        df_excel = pd.read_excel('data_transform/final_tempo_real.xlsx', nrows=5)
        print("Columns:", df_excel.columns.tolist())
        print("First row preview:")
        print(df_excel.head(1))
    except Exception as e:
        print(f"Error reading Excel: {e}")

    print("\n--- Inspecting CSV file: processes.csv ---")
    try:
        with open('data_transform/backups/20260507_051612/processes.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            first_row = next(reader)
            print("Columns:", header)
            print("First row preview:", first_row)
    except Exception as e:
        print(f"Error reading CSV: {e}")

if __name__ == "__main__":
    inspect_files()
