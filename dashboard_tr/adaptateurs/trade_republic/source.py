"""D'où viennent les fichiers de l'export, et comment les rafraîchir.

Deux fichiers, produits par `pytr` :

- `all_events.json`, la timeline complète : **c'est la source** (D-06) ;
- `account_transactions.csv`, qui ne sert qu'à recouper (D-42).

Ils sont écrits dans le dossier personnel, hors du dossier synchronisé par OneDrive (D-37).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dashboard_tr.config import emplacements

NOM_EVENEMENTS = "all_events.json"
NOM_TRANSACTIONS = "account_transactions.csv"


class ExportIntrouvable(Exception):
    """Le fichier d'événements n'est pas là où on l'attendait."""


def dossier_par_defaut(environnement: Mapping[str, str] | None = None) -> Path:
    return emplacements.dossier_exports(environnement)


def chemin_evenements(dossier: Path) -> Path:
    return dossier / NOM_EVENEMENTS


def chemin_transactions(dossier: Path) -> Path | None:
    """Chemin du CSV de recoupement, ou `None` s'il n'a pas été exporté."""
    chemin = dossier / NOM_TRANSACTIONS
    return chemin if chemin.exists() else None


def charger_evenements(dossier: Path) -> list[dict[str, Any]]:
    """Lit `all_events.json`. Un fichier absent donne un message qui dit quoi faire."""
    fichier = chemin_evenements(dossier)
    if not fichier.exists():
        raise ExportIntrouvable(
            f"aucun fichier « {NOM_EVENEMENTS} » dans {dossier}.\n"
            "Lancez « dashboard rafraichir » pour le récupérer, ou indiquez un autre "
            "dossier avec --export."
        )

    contenu = json.loads(fichier.read_text(encoding="utf-8"))
    if not isinstance(contenu, list):
        raise ExportIntrouvable(
            f"{fichier} ne contient pas une liste d'événements : le fichier est peut-être "
            "incomplet. Relancez « dashboard rafraichir »."
        )
    return [evenement for evenement in contenu if isinstance(evenement, dict)]


# --- Récupération auprès de Trade Republic ------------------------------------------

COMMANDE_PYTR = (
    "export_transactions",
    "--v2",
    "--decimal-localization",
    "--store-event-database",
    "--export-format",
    "csv",
)
"""Arguments passés à pytr.

Ce qui **n'est pas** passé compte autant que le reste (D-25, D-41) :

- ni `-n` ni `-p` : pytr demande lui-même le numéro et le PIN, **la saisie du PIN étant
  masquée**. Le PIN ne transite donc jamais par cette application, et n'apparaît ni dans la
  ligne de commande — visible des autres programmes de la machine — ni dans l'historique du
  terminal ;
- pas de `--store_credentials` : rien n'est enregistré. C'est le plus sûr des trois modes
  de D-25 ; les deux autres seront proposés à l'installation, à l'étape 10.

`--store-event-database` est ce qui écrit `all_events.json` ; il complète l'existant au lieu
de le remplacer, ce qui permet de rafraîchir sans repartir de zéro.
"""


def rafraichir(dossier: Path, executable: str | None = None) -> int:
    """Lance pytr pour (re)télécharger l'export dans `dossier`.

    Rend la main à pytr pour le dialogue de connexion : c'est lui qui demande le numéro, le
    PIN et le code de confirmation, directement à l'utilisateur.
    """
    dossier.mkdir(parents=True, exist_ok=True)

    commande = [
        executable or sys.executable,
        "-m",
        "pytr.main",
        *COMMANDE_PYTR,
        "--outputdir",
        str(dossier),
    ]
    # Pas de capture des flux : l'utilisateur doit voir les questions de pytr et pouvoir y
    # répondre. Une capture ferait attendre indéfiniment devant un terminal muet.
    return subprocess.run(commande, check=False).returncode


COMMANDE_PYTR_PORTEFEUILLE = ("portfolio", "--v2")
"""Arguments passés à pytr pour la photo du portefeuille actuel (D-46).

Les mêmes précautions que ci-dessus s'appliquent : ni `-n`, ni `-p`, ni
`--store_credentials`. Comme rien n'est enregistré, **cet appel redemande le numéro et le
PIN** : c'est le prix du mode le plus sûr (D-41), et la raison pour laquelle le portefeuille
réel a sa propre commande au lieu d'être récupéré à chaque rafraîchissement.

`--decimal-localization` est volontairement **absent**, alors qu'il est passé à l'export des
transactions : les nombres arrivent ainsi à point décimal, sans séparateur de milliers. La
convention est imposée à la source plutôt que devinée à la lecture — c'est exactement le
piège qui a coûté le plus cher à l'étape 2 (inventaire §11.1).
"""


def recuperer_portefeuille(fichier: Path, executable: str | None = None) -> int:
    """Lance pytr pour écrire dans `fichier` le portefeuille tel que la banque le voit.

    Ce fichier contient de vraies positions : il est écrit dans le dossier personnel, hors
    du dossier synchronisé, et n'entre jamais dans git (D-01, D-37).
    """
    fichier.parent.mkdir(parents=True, exist_ok=True)

    commande = [
        executable or sys.executable,
        "-m",
        "pytr.main",
        *COMMANDE_PYTR_PORTEFEUILLE,
        "--output",
        str(fichier),
    ]
    return subprocess.run(commande, check=False).returncode
