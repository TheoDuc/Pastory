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

NOM_APPLICATION = "Pastory"

VARIABLE_EMPLACEMENT = "PASTORY_DOSSIER"
"""Permet de choisir un autre emplacement : utile pour les tests et pour un utilisateur
qui range ses fichiers ailleurs."""

ANCIENS_NOMS_APPLICATION = ("DashBoardTradeRepublic",)
"""L'application s'est appelée « DashBoard Trade Republic » avant de s'appeler Pastory, et
le dossier personnel a changé de nom avec elle : sur une machine où elle tournait déjà,
l'export, le cache de cours et la configuration sont restés dans l'ancien dossier.

**Rien n'est déplacé automatiquement.** Un cours en cache est définitif (D-50), et le
déplacer sans le dire reviendrait à changer des chiffres dans le dos de l'utilisateur.
L'application se contente de **signaler** l'ancien dossier ; c'est lui qui décide.
"""


def _racine_du_systeme(environnement: Mapping[str, str]) -> Path:
    """Le dossier où le système range les données des applications."""
    if sys.platform == "win32":
        return Path(environnement.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(environnement.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def dossier_personnel(environnement: Mapping[str, str] | None = None) -> Path:
    """Dossier racine des fichiers personnels, jamais à l'intérieur du projet."""
    environnement = os.environ if environnement is None else environnement

    choisi = environnement.get(VARIABLE_EMPLACEMENT)
    if choisi:
        return Path(choisi)

    return _racine_du_systeme(environnement) / NOM_APPLICATION


def anciens_dossiers_personnels(
    environnement: Mapping[str, str] | None = None,
) -> list[Path]:
    """Les dossiers personnels d'un ancien nom de l'application, s'ils existent encore.

    Vide dans le cas normal. Un emplacement choisi à la main (`PASTORY_DOSSIER`) n'a pas
    changé de nom : on ne cherche alors rien.
    """
    environnement = os.environ if environnement is None else environnement
    if environnement.get(VARIABLE_EMPLACEMENT):
        return []

    racine = _racine_du_systeme(environnement)
    actuel = dossier_personnel(environnement)
    return [
        racine / nom
        for nom in ANCIENS_NOMS_APPLICATION
        if racine / nom != actuel and (racine / nom).is_dir()
    ]


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
