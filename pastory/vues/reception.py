"""Recevoir un export déposé dans l'application, et en faire un portefeuille (D-95, D-109).

Quatre règles :

- **un fichier qui n'est pas un export est refusé, et n'est pas copié** : il est lu avec la
  même lecture que les autres (`adaptateurs/trade_republic/fichier.py`), et le message dit
  pourquoi il ne convient pas ;
- **un fichier, un portefeuille** : un export déposé ne s'ajoute jamais à un autre. Ce qu'il
  devient se décide sur ses **identifiants d'opération**, comparés à ceux des portefeuilles
  déjà là (`depot.comparer`) — jamais sur son nom, que la banque donne identique à tous :

  | L'export déposé…                                  | devient                               |
  |---------------------------------------------------|---------------------------------------|
  | contient toutes les opérations d'un portefeuille  | ce portefeuille, **mis à jour**       |
  | est tout entier dans un portefeuille              | rien : c'en est une version ancienne  |
  | le recoupe sans le contenir                       | un autre portefeuille, et on le dit   |
  | n'a aucune opération en commun                    | un **nouveau** portefeuille           |

- **rien n'est perdu par un remplacement** : il n'a lieu que si le nouveau fichier contient
  tout l'ancien ;
- **l'export ne passe par aucun autre dossier** : il contient des données personnelles, et il
  est vérifié sur place, dans le dossier de dépôt, sous un nom provisoire que la lecture ignore
  (son extension n'est pas `.csv`), puis renommé ou effacé.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from pathlib import Path

from pastory.adaptateurs.trade_republic import depot, fichier
from pastory.adaptateurs.trade_republic.depot import CHEMIN_DANS_L_APPLICATION, Lien, Portefeuille
from pastory.adaptateurs.trade_republic.fichier import FichierNonReconnu
from pastory.vues import format as f

EXTENSION_PROVISOIRE = ".depot"

NOM_DE_LA_BANQUE = Path(depot.NOM_PAR_DEFAUT).stem
"""Le nom que la banque donne à tous ses exports : il ne dit pas à qui est le fichier."""


@dataclass(frozen=True)
class Reception:
    accepte: bool
    message: str
    fichier: Path | None = None
    """Le fichier écrit dans le dossier de dépôt — `None` si rien n'a changé."""
    etiquette: str | None = None
    """Le mot qui résume ce qui s'est passé ; à défaut, « Déposé » ou « Refusé »."""


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

    try:
        return _ranger(nom, octets, lignes, provisoire, dossier)
    finally:
        provisoire.unlink(missing_ok=True)


def _ranger(
    nom: str, octets: bytes, lignes: list[fichier.Ligne], provisoire: Path, dossier: Path
) -> Reception:
    """Décide de ce que devient l'export déposé, et le range."""
    deposes = depot.identifiants(lignes)
    contenu = depot.inventaire(dossier)
    existants, ouvert = contenu.portefeuilles, contenu.ouvert
    liens: dict[Lien, list[tuple[Portefeuille, frozenset[str]]]] = {lien: [] for lien in Lien}
    for portefeuille in existants:
        if portefeuille.chemin.read_bytes() == octets:
            return Reception(
                True,
                f"« {nom} » est déjà là, à l'identique : c'est le portefeuille "
                f"« {portefeuille.nom} ». Rien n'a changé.",
                etiquette="Déjà là",
            )
        siens = depot.identifiants(fichier.lire(portefeuille.chemin))
        liens[depot.comparer(deposes, siens)].append((portefeuille, siens))

    periode = _periode(nom, lignes)

    if liens[Lien.CONTIENT]:
        # Le même compte, plus récent. Le portefeuille ouvert garde la préférence, s'il en est.
        contenus = sorted(liens[Lien.CONTIENT], key=lambda paire: paire[0] != ouvert)
        (garde, siens), autres = contenus[0], contenus[1:]
        provisoire.replace(garde.chemin)
        for absorbe, _ in autres:
            absorbe.chemin.unlink()
        depot.ouvrir(dossier, garde.nom)
        de_plus = len(deposes - siens)
        suite = (
            f" Il contient aussi {_noms(p for p, _ in autres)}, qu'il remplace."
            if autres
            else ""
        )
        return Reception(
            True,
            f"« {garde.nom} » est mis à jour : {_lignes_de_plus(de_plus)}{periode}.{suite}",
            garde.chemin,
            "Mis à jour",
        )

    if liens[Lien.CONTENU]:
        recent, siens = liens[Lien.CONTENU][0]
        return Reception(
            True,
            f"« {nom} » est une version plus ancienne du portefeuille « {recent.nom} », qui "
            f"contient déjà toutes ses lignes et {len(siens - deposes)} de plus : rien n'a changé.",
            etiquette="Plus ancien",
        )

    cible = dossier / f"{depot.nom_libre(dossier, _nom_souhaite(nom, bool(existants)))}.csv"
    provisoire.replace(cible)
    depot.ouvrir(dossier, cible.stem)
    if not existants:
        return Reception(True, f"« {nom} » est déposé : {len(lignes)} lignes{periode}.", cible)

    message = (
        f"« {nom} » devient un nouveau portefeuille, « {cible.stem} » : {len(lignes)} lignes"
        f"{periode}. Il est ouvert ; vous pouvez le renommer."
    )
    if liens[Lien.RECOUPE]:
        message += (
            f" Il a des opérations en commun avec {_noms(p for p, _ in liens[Lien.RECOUPE])} "
            "sans le contenir : ce sont sans doute deux exports partiels du même compte. "
            "Pastory ne les assemble pas : exportez « toutes les transactions », le fichier "
            "obtenu les remplacera tous les deux."
        )
    return Reception(True, message, cible, "Nouveau portefeuille")


def _nom_souhaite(nom: str, deja_des_portefeuilles: bool) -> str:
    """Le nom que prendra un nouveau portefeuille, avant d'en chercher un de libre.

    Le premier garde le nom de son fichier, comme avant D-109. Ensuite, le nom de la banque —
    le même pour tous ses exports — ne distinguerait rien : « Portefeuille », que l'on renomme.
    Un fichier que l'utilisateur a nommé lui-même garde son nom.
    """
    souhaite = Path(nom).stem if nom.lower().endswith(".csv") else nom
    try:
        souhaite = depot.nom_valide(souhaite)
    except depot.NomRefuse:
        return depot.NOM_D_UN_NOUVEAU_PORTEFEUILLE
    if deja_des_portefeuilles and souhaite.casefold().startswith(NOM_DE_LA_BANQUE.casefold()):
        return depot.NOM_D_UN_NOUVEAU_PORTEFEUILLE
    return souhaite


def _periode(nom: str, lignes: list[fichier.Ligne]) -> str:
    lu = depot.decrire(nom, lignes)
    if lu.premier_jour is None:
        return ""
    return f", du {f.date_courte(lu.premier_jour)} au {f.date_courte(lu.dernier_jour)}"


def _lignes_de_plus(nombre: int) -> str:
    if nombre == 0:
        return "aucune ligne de plus"
    return f"{nombre} ligne{'s' if nombre > 1 else ''} de plus"


def _noms(portefeuilles) -> str:
    return ", ".join(f"« {portefeuille.nom} »" for portefeuille in portefeuilles)
