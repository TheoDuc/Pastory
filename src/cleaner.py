"""
Module servant à calculer les indicateurs importants d'un portefeuille
"""

import pandas as pd

df = pd.read_csv("data/account_transactions.csv", sep=";", decimal=",")

# ------------------- Nettoyage de la base de données -------------------

# Conversion des dates
df["Date"] = pd.to_datetime(df["Date"])

# Suppression des colonnes inutiles
df = df.drop(columns=["ISIN2", "Parts2"])

# Remplacement des valeurs manquantes en 0 (colonnes "Frais" et "Impôts / Taxes")
df["Frais"] = df["Frais"].fillna(0)
df["Impôts / Taxes"] = df["Impôts / Taxes"].fillna(0)

print(df.head())
print(df.dtypes)
