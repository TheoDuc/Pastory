"""Où vivent les fichiers personnels de l'utilisateur (D-37).

Le projet est rangé dans OneDrive (D-24). Tout ce qui est réécrit souvent — exports, cache
de cours, configuration, résultats de vérification — est donc écrit **en dehors** du dossier
synchronisé, pour éviter les conflits de synchronisation.

Aucun de ces fichiers n'entre dans git (D-01).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

NOM_APPLICATION = "DashBoardTradeRepublic"

VARIABLE_EMPLACEMENT = "DASHBOARD_TR_DOSSIER"
"""Permet de choisir un autre emplacement : utile pour les tests et pour un utilisateur
qui range ses fichiers ailleurs."""


def dossier_personnel(environnement: Mapping[str, str] | None = None) -> Path:
    """Dossier racine des fichiers personnels, jamais à l'intérieur du projet."""
    environnement = os.environ if environnement is None else environnement

    choisi = environnement.get(VARIABLE_EMPLACEMENT)
    if choisi:
        return Path(choisi)

    if sys.platform == "win32":
        racine = Path(environnement.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        racine = Path.home() / "Library" / "Application Support"
    else:
        racine = Path(environnement.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    return racine / NOM_APPLICATION


def dossier_exports(environnement: Mapping[str, str] | None = None) -> Path:
    """Exports pytr bruts (`all_events.json`, `account_transactions.csv`)."""
    return dossier_personnel(environnement) / "exports"


def dossier_cache(environnement: Mapping[str, str] | None = None) -> Path:
    """Cours, TER et compositions déjà téléchargés, avec leur date (étape 4)."""
    return dossier_personnel(environnement) / "cache"


def dossier_configuration(environnement: Mapping[str, str] | None = None) -> Path:
    """Fichiers TOML de l'utilisateur : noms des comptes, corrections de poche, ISIN (D-38)."""
    return dossier_personnel(environnement) / "configuration"


def tous_les_dossiers(environnement: Mapping[str, str] | None = None) -> dict[str, Path]:
    """Les emplacements, dans l'ordre où l'application les présente à l'utilisateur."""
    return {
        "racine": dossier_personnel(environnement),
        "exports": dossier_exports(environnement),
        "cache": dossier_cache(environnement),
        "configuration": dossier_configuration(environnement),
    }


def creer_dossiers(environnement: Mapping[str, str] | None = None) -> dict[str, Path]:
    """Crée les dossiers manquants et renvoie leurs emplacements."""
    dossiers = tous_les_dossiers(environnement)
    for chemin in dossiers.values():
        chemin.mkdir(parents=True, exist_ok=True)
    return dossiers
