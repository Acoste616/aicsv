#!/usr/bin/env python3
import pandas as pd

print("=== SPRAWDZENIE STRUKTURY CSV ===")

# Sprawdź cleaned CSV
df = pd.read_csv('bookmarks_cleaned.csv')
print(f"Liczba wierszy: {len(df)}")
print(f"Kolumny: {list(df.columns)}")
print("\nPierwszy wiersz:")
for col in df.columns:
    print(f"{col}: {df[col].iloc[0]}")

print("\n=== DRUGI WIERSZ (do porównania) ===")
for col in df.columns:
    print(f"{col}: {df[col].iloc[1]}") 