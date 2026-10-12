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


SUFFIXE_DE_DEMONSTRATION = "-demonstration"


def dossier_de_demonstration(environnement: Mapping[str, str] | None = None) -> Path:
    """Le dossier personnel de la démonstration (D-107) : un dossier **à part**, voisin du
    dossier personnel, avec son propre export, son cache et sa configuration. Un export fictif
    ne peut donc jamais se mêler aux vrais, ni l'inverse.

    Appelée depuis une démonstration déjà en cours, elle rend ce même dossier.
    """
    personnel = dossier_personnel(environnement)
    if personnel.name.endswith(SUFFIXE_DE_DEMONSTRATION):
        return personnel
    return personnel.with_name(personnel.name + SUFFIXE_DE_DEMONSTRATION)


def est_une_demonstration(environnement: Mapping[str, str] | None = None) -> bool:
    """Vrai si le dossier personnel en cours est celui de la démonstration.

    **C'est le dossier qui le dit, et lui seul** : l'écran qui annonce « Données de
    démonstration » et les fichiers qu'on lit ne peuvent donc pas se contredire — ni un vrai
    portefeuille s'afficher sous cette mention, ni l'inverse.
    """
    return dossier_personnel(environnement).name.endswith(SUFFIXE_DE_DEMONSTRATION)


def dossier_exports(environnement: Mapping[str, str] | None = None) -> Path:
    """Le dossier de dépôt : l'utilisateur y dépose ses exports des transactions (D-80)."""
    return dossier_personnel(environnement) / "exports"


def dossier_cache(environnement: Mapping[str, str] | None = None) -> Path:
    """Cours, TER et compositions déjà téléchargés, avec leur date (étape 4)."""
    return dossier_personnel(environnement) / "cache"


def dossier_configuration(environnement: Mapping[str, str] | None = None) -> Path:
    """Fichiers TOML de l'utilisateur : actifs, fiscalité (D-38)."""
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
