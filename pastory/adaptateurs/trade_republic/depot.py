"""Le dossier de dépôt : l'utilisateur y dépose ses exports, et **chaque fichier est un
portefeuille** (D-109).

C'est la seule chose que l'utilisateur ait à faire (D-80). D'où quatre règles :

- **un fichier, un portefeuille.** Les exports ne se cumulent pas : Pastory n'en lit qu'un à la
  fois, celui qui est **ouvert**. Deux comptes ne peuvent donc pas se mélanger — ce que le cumul
  de l'étape 8 ter permettait, et qui est arrivé au premier export d'un proche déposé à côté du
  sien. Le nom du portefeuille est le nom de son fichier : il n'y a pas d'index à tenir ;
- **le portefeuille ouvert est retenu** dans le dossier (`MARQUE`), pour s'ouvrir au lancement
  suivant ;
- **un fichier qui n'est pas un export n'arrête rien** : il est cité, avec la raison, et il
  n'est pas un portefeuille ;
- **la période couverte est toujours dite.** L'utilisateur choisit les dates de son export :
  une période qui ne commence pas à l'ouverture du compte donne une histoire incomplète, et
  rien dans le fichier ne le dit (D-45).

Deux exports se comparent par leurs **identifiants d'opération** (`transaction_id`), jamais par
un nom ni un texte : c'est ce qui dit, au dépôt, si un fichier est la suite d'un portefeuille ou
un autre compte (`comparer`, et `vues/reception.py`).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum, auto
from pathlib import Path

from pastory.adaptateurs.trade_republic import fichier
from pastory.adaptateurs.trade_republic.fichier import FichierNonReconnu, Ligne

NOM_PAR_DEFAUT = "Exportation de transactions.csv"
"""Le nom que donne l'application en français. Tout fichier `.csv` du dossier est lu."""

CHEMIN_DANS_L_APPLICATION = "Profil > Relevés > Export des transactions"
"""Où trouver l'export dans l'application Trade Republic (export-officiel.md §1)."""

MARQUE = ".portefeuille-ouvert"
"""Le petit fichier du dossier qui retient le portefeuille ouvert : le nom de son fichier."""

NOM_D_UN_NOUVEAU_PORTEFEUILLE = "Portefeuille"

LONGUEUR_MAXIMALE_D_UN_NOM = 60
INTERDITS_DANS_UN_NOM = '<>:"/\\|?*'
"""Ce que Windows refuse dans un nom de fichier — refusé partout, pour qu'un dossier de dépôt
se copie d'un ordinateur à l'autre."""
NOMS_RESERVES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{numero}" for numero in range(1, 10)}
    | {f"LPT{numero}" for numero in range(1, 10)}
)

INACCESSIBLE = "le fichier n'a pas pu être ouvert (verrouillé ou inaccessible)"


class ExportIntrouvable(Exception):
    """Aucun export lisible. Le message dit comment en obtenir un."""


class NomRefuse(Exception):
    """Ce nom ne peut pas être celui d'un portefeuille. Le message dit pourquoi."""


@dataclass(frozen=True)
class FichierLu:
    """Un export lu, et la période qu'il couvre."""

    nom: str
    lignes: int
    premier_jour: date | None
    dernier_jour: date | None


@dataclass(frozen=True)
class Portefeuille:
    """Un export du dossier de dépôt."""

    chemin: Path
    lu: FichierLu

    @property
    def nom(self) -> str:
        """Le nom du portefeuille : celui de son fichier, sans « .csv »."""
        return self.chemin.stem


@dataclass(frozen=True)
class Inventaire:
    """Ce que contient le dossier de dépôt."""

    portefeuilles: tuple[Portefeuille, ...] = ()
    """Par ordre alphabétique, sans tenir compte des majuscules."""
    ignores: tuple[tuple[str, str], ...] = ()
    """(nom du fichier, raison) pour chaque fichier `.csv` qui n'est pas un export."""
    ouvert: Portefeuille | None = None

    def nomme(self, nom: str) -> Portefeuille | None:
        return next((p for p in self.portefeuilles if p.nom == nom), None)


@dataclass
class Depot:
    """Le portefeuille lu : ses lignes dédoublonnées, et tout ce qu'il faut en dire."""

    lignes: list[Ligne] = field(default_factory=list)
    fichiers: list[FichierLu] = field(default_factory=list)
    """Le fichier lu — un seul, depuis D-109. Une liste, parce que tout ce qui l'affiche
    parcourait déjà celle des fichiers cumulés."""
    fichiers_ignores: list[tuple[str, str]] = field(default_factory=list)
    """(nom du fichier, raison) pour chaque fichier `.csv` du dossier qui n'est pas un export."""
    doublons: int = 0
    """Lignes écrites deux fois dans le fichier, à l'identique : comptées une fois."""
    conflits: list[tuple[Ligne, Ligne]] = field(default_factory=list)
    """(ligne gardée, ligne écartée) : même `transaction_id`, contenu différent."""
    sans_identifiant: list[Ligne] = field(default_factory=list)
    """Lignes sans `transaction_id` : impossibles à reconnaître d'un export à l'autre, donc
    non lues."""
    portefeuille: str | None = None
    """Le nom du portefeuille lu."""
    autres: list[str] = field(default_factory=list)
    """Les autres portefeuilles du dossier, qui ne sont **pas** lus."""

    @property
    def premier_jour(self) -> date | None:
        jours = [lu.premier_jour for lu in self.fichiers if lu.premier_jour is not None]
        return min(jours) if jours else None

    @property
    def dernier_jour(self) -> date | None:
        jours = [lu.dernier_jour for lu in self.fichiers if lu.dernier_jour is not None]
        return max(jours) if jours else None


def _jour(texte: str) -> date | None:
    try:
        return date.fromisoformat(texte)
    except ValueError:
        return None


def decrire(nom: str, lignes: list[Ligne]) -> FichierLu:
    jours = [jour for jour in (_jour(ligne.date) for ligne in lignes) if jour is not None]
    return FichierLu(
        nom=nom,
        lignes=len(lignes),
        premier_jour=min(jours) if jours else None,
        dernier_jour=max(jours) if jours else None,
    )


def comment_obtenir_l_export(dossier: Path) -> str:
    """Le message d'un dossier sans export : quoi faire, et où le déposer."""
    return (
        f"Aucun export des transactions dans {dossier}.\n"
        f"Dans l'application Trade Republic : {CHEMIN_DANS_L_APPLICATION},\n"
        "choisissez « toutes les transactions », puis déposez le fichier obtenu\n"
        f"(« {NOM_PAR_DEFAUT} ») dans ce dossier."
    )


# --- Le dossier : ses portefeuilles, et celui qui est ouvert ------------------------------


def _fichiers_csv(dossier: Path) -> list[Path]:
    if not dossier.is_dir():
        return []
    return sorted(
        (
            chemin
            for chemin in dossier.iterdir()
            if chemin.suffix.lower() == ".csv" and chemin.is_file()
        ),
        key=lambda chemin: (chemin.name.casefold(), chemin.name),
    )


def inventaire(dossier: Path) -> Inventaire:
    """Les portefeuilles du dossier, les fichiers écartés, et le portefeuille ouvert."""
    portefeuilles: list[Portefeuille] = []
    ignores: list[tuple[str, str]] = []
    for chemin in _fichiers_csv(dossier):
        try:
            lignes = fichier.lire(chemin)
        except FichierNonReconnu as raison:
            ignores.append((chemin.name, str(raison)))
        except OSError:
            # Verrouillé, protégé, ou laissé « dans le nuage » par un service de
            # synchronisation : le fichier est cité, et le reste du dossier est lu.
            ignores.append((chemin.name, INACCESSIBLE))
        else:
            portefeuilles.append(Portefeuille(chemin, decrire(chemin.name, lignes)))
    return Inventaire(
        tuple(portefeuilles), tuple(ignores), _ouvert(dossier, portefeuilles)
    )


def _ouvert(dossier: Path, portefeuilles: list[Portefeuille]) -> Portefeuille | None:
    """Le portefeuille retenu par la marque ; à défaut, le plus récemment déposé."""
    if not portefeuilles:
        return None
    with contextlib.suppress(OSError, UnicodeDecodeError):
        retenu = (dossier / MARQUE).read_text(encoding="utf-8").strip()
        for portefeuille in portefeuilles:
            if portefeuille.chemin.name == retenu:
                return portefeuille
    return max(portefeuilles, key=lambda p: (_depose_le(p.chemin), p.chemin.name))


def _depose_le(chemin: Path) -> float:
    try:
        return chemin.stat().st_mtime
    except OSError:
        return 0.0


def ouvrir(dossier: Path, nom: str) -> Portefeuille:
    """Fait du portefeuille `nom` celui que Pastory lit, maintenant et au lancement suivant."""
    portefeuille = _trouver(dossier, nom)
    (dossier / MARQUE).write_text(portefeuille.chemin.name, encoding="utf-8")
    return portefeuille


def _trouver(dossier: Path, nom: str) -> Portefeuille:
    portefeuille = inventaire(dossier).nomme(nom)
    if portefeuille is None:
        raise ExportIntrouvable(f"Aucun portefeuille « {nom} » dans {dossier}.")
    return portefeuille


# --- La lecture d'un portefeuille ---------------------------------------------------------


def lire(source: Path) -> Depot:
    """Lit **un** portefeuille : le fichier `source`, ou le portefeuille ouvert du dossier
    `source`."""
    if source.is_file():
        try:
            return _lire_un_fichier(source)
        except FichierNonReconnu as raison:
            raise ExportIntrouvable(
                f"{source} n'est pas un export des transactions : {raison}."
            ) from raison
        except OSError as erreur:
            raise ExportIntrouvable(f"{source} : {INACCESSIBLE}.") from erreur

    contenu = inventaire(source)
    if contenu.ouvert is None:
        message = comment_obtenir_l_export(source)
        if contenu.ignores:
            ignores = "\n".join(f"  {nom} : {raison}" for nom, raison in contenu.ignores)
            message += f"\n\nFichiers trouvés, mais qui ne sont pas un export :\n{ignores}"
        raise ExportIntrouvable(message)

    depot = _lire_un_fichier(contenu.ouvert.chemin)
    depot.fichiers_ignores = list(contenu.ignores)
    depot.autres = [p.nom for p in contenu.portefeuilles if p != contenu.ouvert]
    return depot


def _lire_un_fichier(chemin: Path) -> Depot:
    lignes = fichier.lire(chemin)
    depot = Depot(fichiers=[decrire(chemin.name, lignes)], portefeuille=chemin.stem)
    par_identifiant: dict[str, Ligne] = {}
    for ligne in lignes:
        if not ligne.transaction_id:
            depot.sans_identifiant.append(ligne)
            continue
        deja = par_identifiant.get(ligne.transaction_id)
        if deja is None:
            par_identifiant[ligne.transaction_id] = ligne
            depot.lignes.append(ligne)
        elif deja.contenu() == ligne.contenu():
            depot.doublons += 1
        else:
            # Deux versions d'une même opération : la première lue est gardée, et le
            # désaccord est affiché. Rien ne permet de dire laquelle est la bonne.
            depot.conflits.append((deja, ligne))
    return depot


# --- Comparer deux exports ----------------------------------------------------------------


class Lien(StrEnum):
    """Ce qu'un export déposé est à un portefeuille déjà là, d'après leurs opérations."""

    CONTIENT = auto()
    """Toutes les opérations du portefeuille y sont : c'est le même compte, plus récent."""
    CONTENU = auto()
    """Toutes ses opérations sont déjà dans le portefeuille : une version plus ancienne."""
    RECOUPE = auto()
    """Des opérations communes, sans que l'un contienne l'autre : deux exports partiels."""
    SANS_RAPPORT = auto()
    """Aucune opération commune : un autre compte, ou une autre période."""


def identifiants(lignes: Iterable[Ligne]) -> frozenset[str]:
    return frozenset(ligne.transaction_id for ligne in lignes if ligne.transaction_id)


def comparer(depose: frozenset[str], existant: frozenset[str]) -> Lien:
    """Compare les opérations d'un export déposé à celles d'un portefeuille.

    Un export sans aucun identifiant ne se compare à rien : il est sans rapport.
    """
    if not depose or not existant or not (depose & existant):
        return Lien.SANS_RAPPORT
    if existant <= depose:
        return Lien.CONTIENT
    if depose < existant:
        return Lien.CONTENU
    return Lien.RECOUPE


# --- Nommer, renommer, supprimer ----------------------------------------------------------


def nom_valide(nom: str) -> str:
    """Le nom, nettoyé de ses espaces de bord, ou `NomRefuse` avec la raison."""
    nom = " ".join(nom.split())
    # Qui écrit « Camille.csv » veut dire « Camille » : l'extension est celle du fichier.
    if nom.lower().endswith(".csv"):
        nom = nom[:-4].rstrip()
    if not nom:
        raise NomRefuse("Un portefeuille doit avoir un nom.")
    if len(nom) > LONGUEUR_MAXIMALE_D_UN_NOM:
        raise NomRefuse(
            f"Ce nom est trop long : {LONGUEUR_MAXIMALE_D_UN_NOM} caractères au plus."
        )
    interdits = sorted({c for c in nom if c in INTERDITS_DANS_UN_NOM or ord(c) < 32})
    if interdits:
        raise NomRefuse(
            "Un nom de portefeuille est un nom de fichier : il ne peut pas contenir "
            + " ".join(c if c.isprintable() else "(caractère invisible)" for c in interdits)
        )
    if nom.startswith(".") or nom.endswith("."):
        raise NomRefuse("Un nom de portefeuille ne commence ni ne finit par un point.")
    if nom.split(".")[0].upper() in NOMS_RESERVES:
        raise NomRefuse(f"« {nom} » est un nom que Windows se réserve : choisissez-en un autre.")
    return nom


def _pris(dossier: Path, nom: str, sauf: Path | None = None) -> bool:
    """Vrai si un fichier du dossier porte déjà ce nom, sans tenir compte des majuscules —
    Windows ne les distingue pas."""
    return any(
        chemin.stem.casefold() == nom.casefold() and chemin != sauf
        for chemin in _fichiers_csv(dossier)
    )


def nom_libre(dossier: Path, souhaite: str = NOM_D_UN_NOUVEAU_PORTEFEUILLE) -> str:
    """Un nom que personne ne porte : `souhaite`, sinon « souhaite 2 », « souhaite 3 »…"""
    if not _pris(dossier, souhaite):
        return souhaite
    numero = 2
    while _pris(dossier, f"{souhaite} {numero}"):
        numero += 1
    return f"{souhaite} {numero}"


def renommer(dossier: Path, nom: str, nouveau: str) -> Portefeuille:
    """Renomme un portefeuille — c'est-à-dire son fichier. Le portefeuille ouvert le reste."""
    portefeuille = _trouver(dossier, nom)
    nouveau = nom_valide(nouveau)
    if _pris(dossier, nouveau, sauf=portefeuille.chemin):
        raise NomRefuse(f"Un portefeuille s'appelle déjà « {nouveau} ».")
    etait_ouvert = inventaire(dossier).ouvert == portefeuille
    cible = portefeuille.chemin.with_name(f"{nouveau}.csv")
    # Les noms, pas les chemins : sous Windows, deux chemins qui ne diffèrent que par la
    # casse sont égaux, et « alix » ne deviendrait jamais « Alix ».
    if cible.name != portefeuille.chemin.name:
        portefeuille.chemin.rename(cible)
    if etait_ouvert:
        (dossier / MARQUE).write_text(cible.name, encoding="utf-8")
    return _trouver(dossier, nouveau)


def supprimer(dossier: Path, nom: str) -> None:
    """Efface le fichier du portefeuille. Les cours et les réglages en mémoire, qui décrivent
    des titres et non une personne, restent : ils servent aux autres portefeuilles."""
    portefeuille = _trouver(dossier, nom)
    portefeuille.chemin.unlink()
    with contextlib.suppress(OSError, UnicodeDecodeError):
        marque = dossier / MARQUE
        if marque.read_text(encoding="utf-8").strip() == portefeuille.chemin.name:
            marque.unlink()
