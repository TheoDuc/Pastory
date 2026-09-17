"""Point d'entrée unique de l'application : `uv run dashboard <commande>`.

Les commandes sont ajoutées étape par étape. Celles qui ne sont pas encore écrites le disent
clairement, avec l'étape où elles arrivent, plutôt que d'échouer sans explication.
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from dashboard_tr.config import emplacements

NOM = "dashboard"


def _version() -> str:
    try:
        return version("dashboard-tr")
    except PackageNotFoundError:  # pragma: no cover - dépend de l'installation
        return "inconnue (application non installée)"


def commande_emplacements() -> int:
    """Affiche où l'application range les fichiers personnels (D-37)."""
    print("Fichiers personnels (hors du dossier du projet, jamais dans git) :")
    for nom, chemin in emplacements.tous_les_dossiers().items():
        etat = "existe" if chemin.exists() else "pas encore créé"
        print(f"  {nom:<14} {chemin}  [{etat}]")
    return 0


def _a_venir(commande: str, etape: str) -> int:
    print(f"La commande « {commande} » sera disponible à l'{etape}.", file=sys.stderr)
    return 1


def construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog=NOM,
        description="Tableau de bord local des actifs d'un portefeuille Trade Republic.",
    )
    analyseur.add_argument("--version", action="version", version=f"{NOM} {_version()}")

    commandes = analyseur.add_subparsers(dest="commande")
    commandes.add_parser("emplacements", help="où sont rangés les fichiers personnels")
    commandes.add_parser("rafraichir", help="récupérer les données Trade Republic (étape 2)")
    commandes.add_parser("exporter-pivot", help="écrire les opérations en CSV (étape 2)")
    commandes.add_parser("ouvrir", help="ouvrir le tableau de bord (étape 9)")
    return analyseur


def main(arguments: list[str] | None = None) -> int:
    analyseur = construire_analyseur()
    options = analyseur.parse_args(arguments)

    match options.commande:
        case "emplacements":
            return commande_emplacements()
        case "rafraichir":
            return _a_venir("rafraichir", "étape 2 (lecture des données)")
        case "exporter-pivot":
            return _a_venir("exporter-pivot", "étape 2 (lecture des données)")
        case "ouvrir":
            return _a_venir("ouvrir", "étape 9 (réalisation de l'interface)")
        case _:
            analyseur.print_help()
            return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
