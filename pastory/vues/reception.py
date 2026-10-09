"""Recevoir un export déposé dans l'application, et le ranger dans le dossier de dépôt (D-95).

Trois règles :

- **un fichier qui n'est pas un export est refusé, et n'est pas copié** : il est lu avec la
  même lecture que les autres (`adaptateurs/trade_republic/fichier.py`), et le message dit
  pourquoi il ne convient pas ;
- **rien n'est jamais écrasé** : un fichier du même nom mais d'un autre contenu reçoit un nom
  libre. Un export récent ne remplace pas un ancien — les deux se cumulent, et les opérations
  communes ne sont comptées qu'une fois (D-80) ;
- **l'export ne passe par aucun autre dossier** : il contient des données personnelles, et il
  est vérifié sur place, dans le dossier de dépôt, sous un nom provisoire que la lecture ignore
  (son extension n'est pas `.csv`), puis renommé ou effacé.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path

from pastory.adaptateurs.trade_republic import fichier
from pastory.adaptateurs.trade_republic.depot import CHEMIN_DANS_L_APPLICATION
from pastory.adaptateurs.trade_republic.fichier import FichierNonReconnu
from pastory.vues import format as f

EXTENSION_PROVISOIRE = ".depot"


@dataclass(frozen=True)
class Reception:
    accepte: bool
    message: str
    fichier: Path | None = None


def recevoir(nom: str, contenu: str, dossier: Path) -> Reception:
    """`contenu` est ce que donne la zone de dépôt du navigateur : `data:…;base64,…`."""
    nom = Path(nom or "").name
    if not nom:
        return Reception(False, "Le fichier déposé n'a pas de nom.")
    try:
        octets = base64.b64decode(contenu.partition(",")[2], validate=True)
    except (binascii.Error, ValueError):
        return Reception(False, f"« {nom} » n'a pas pu être lu par le navigateur.")

    dossier.mkdir(parents=True, exist_ok=True)
    provisoire = dossier / f".{nom}{EXTENSION_PROVISOIRE}"
    provisoire.write_bytes(octets)
    try:
        lignes = fichier.lire(provisoire)
    except FichierNonReconnu as raison:
        provisoire.unlink(missing_ok=True)
        # La phrase de tête dit, sans jargon, ce qui ne va pas et où trouver le bon fichier ;
        # la raison précise de la lecture vient ensuite, pour qui veut comprendre.
        return Reception(
            False,
            f"« {nom} » ne ressemble pas à un export des transactions de Trade Republic : rien "
            "n'a été copié. Le bon fichier s'obtient dans l'application Trade Republic "
            f"({CHEMIN_DANS_L_APPLICATION.replace(' > ', ' → ')}). Ce qui ne va pas : {raison}.",
        )

    cible = _destination(dossier, nom, octets)
    if cible is None:
        provisoire.unlink(missing_ok=True)
        return Reception(True, f"« {nom} » était déjà déposé, à l'identique : rien n'a changé.")
    provisoire.replace(cible)

    jours = sorted(j for j in (_jour(ligne.date) for ligne in lignes) if j is not None)
    periode = (
        f", du {f.date_courte(jours[0])} au {f.date_courte(jours[-1])}" if jours else ""
    )
    renomme = f" (enregistré sous « {cible.name} », un fichier de ce nom existait)" if (
        cible.name != _nom_csv(nom)
    ) else ""
    return Reception(
        True, f"« {nom} » est déposé{renomme} : {len(lignes)} lignes{periode}.", cible
    )


def _nom_csv(nom: str) -> str:
    return nom if nom.lower().endswith(".csv") else f"{nom}.csv"


def _destination(dossier: Path, nom: str, octets: bytes) -> Path | None:
    """Un chemin libre pour ce fichier, ou `None` s'il est déjà là à l'identique."""
    base = Path(_nom_csv(nom))
    candidat = dossier / base.name
    numero = 2
    while candidat.exists():
        if candidat.read_bytes() == octets:
            return None
        candidat = dossier / f"{base.stem} ({numero}){base.suffix}"
        numero += 1
    return candidat


def _jour(texte: str) -> Date | None:
    try:
        return Date.fromisoformat(texte)
    except ValueError:
        return None
