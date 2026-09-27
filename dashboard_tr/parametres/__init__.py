"""Les paramètres datés et sourcés : taux fiscaux, frais par ordre, spreads par défaut (D-58).

Ils sont livrés avec l'application, dans des fichiers TOML **versionnés** : ils ne contiennent
rien de personnel. Ce paquet les lit et les vérifie ; le moteur, lui, ne les lit jamais
directement — il déclare la forme qu'il attend d'un paramètre, et `cli.py` lui passe ceux-ci.
"""

from __future__ import annotations

from pathlib import Path

DOSSIER = Path(__file__).parent


class ParametresInvalides(Exception):
    """Un fichier de paramètres existe mais ne peut pas être utilisé tel quel.

    Un taux sans date ou sans source n'est pas un taux : c'est un chiffre qu'on ne peut plus
    vérifier, et le rapport ne pourrait pas dire d'où il vient.
    """
