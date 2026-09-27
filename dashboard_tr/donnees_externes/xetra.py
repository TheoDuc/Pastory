"""La liste des ETF négociables de Xetra : les frais courants (TER) par ISIN (D-61).

Deutsche Börse publie chaque semaine la liste de tous les ETF et produits assimilés négociables
à Xetra, avec une colonne « ONGOING CHARGES » — les **frais courants** au sens du document
d'information clé. C'est la seule source gratuite trouvée qui soit indexée par **ISIN**, sans
clé d'accès, et lisible par un programme (`docs/couts-et-fiscalite.md` §2).

Quatre pièges, tous vérifiés le 2026-09-27, et tous traités ici :

1. **le fichier s'appelle `.xls` mais c'est un `.xlsx`** : un ZIP de documents XML, que la
   bibliothèque standard sait ouvrir. Le lire comme un vrai `.xls` échouerait ;
2. **l'adresse du fichier change à chaque publication** : elle contient un numéro et une
   empreinte. Il faut donc lire la page pour y trouver le lien courant, jamais le mémoriser ;
3. **la valeur est une fraction** (0.002 pour 0,20 %), parfois avec un bruit de flottant
   (« 0.0007000000000000001 » pour 0,07 %) : on arrondit à quatre décimales avant de convertir
   en pour cent ;
4. **une même part apparaît une fois par devise de négociation** : la clé est l'ISIN, et deux
   lignes du même ISIN portent la même valeur.

Cette source ne sert qu'à **proposer** : l'utilisateur valide dans `actifs.toml`. La liste est
en retard sur environ 5 % des baisses de frais, et les ETF français de type « PEA » n'y figurent
pas du tout — deux raisons de ne jamais s'en servir sans relecture.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.etree import ElementTree

from dashboard_tr.config.actifs import (
    TER_MAXIMUM,
    TER_MINIMUM,
    FraisCourantsProposes,
)
from dashboard_tr.donnees_externes.cours import ErreurDeSource, SourceInjoignable

NOM = "Xetra (Deutsche Börse), liste des ETF négociables"

ADRESSE_PAGE = (
    "https://www.cashmarket.deutsche-boerse.com/cash-en/Data-Tech/statistics/"
    "etf-etp-statistics/etp-list"
)

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DELAI = 30

MOTIF_DU_LIEN = re.compile(
    r'href="(/resource/blob/[^"]*Master_DataSheet_Download\.xls[^"]*)"', re.IGNORECASE
)
RACINE = "https://www.cashmarket.deutsche-boerse.com"

TYPES_RETENUS = frozenset({"ETF", "ACTIVE ETF"})
"""Seuls les fonds indiciels cotés. Un ETN ou un ETC n'est pas un fonds : ses frais ne se
lisent pas de la même façon, et le projet n'en suit pas."""

PAS_DU_TER = Decimal("0.0001")
"""Quatre décimales sur la fraction, soit deux sur le pourcentage : de quoi absorber le bruit
de flottant de la source sans perdre un centième de point."""

CENT = Decimal("100")

ESPACE_XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

COLONNES_ATTENDUES = ("ISIN", "ONGOING CHARGES", "PRODUCT TYPE")

Ouvrir = Callable[[str], bytes]
"""Comment le contenu d'une adresse est obtenu. Remplaçable dans les tests : aucun test du
projet ne sort de la machine."""


@dataclass(frozen=True)
class LigneXetra:
    """Une part d'ETF telle que la liste la décrit."""

    isin: str
    ter_pour_cent: Decimal
    nom: str | None = None
    politique: str | None = None
    """« Accumulating » ou « Distributing » : de quoi vérifier qu'il s'agit bien de sa part."""


class ListeXetra:
    """La liste, une fois lue : de l'ISIN aux frais courants proposés."""

    nom = NOM

    def __init__(self, lignes: dict[str, LigneXetra], date: Date | None = None) -> None:
        self.lignes = lignes
        self.date = date
        """La date d'effet annoncée par le fichier (« As of … »), quand il la donne."""

    def __len__(self) -> int:
        return len(self.lignes)

    def frais_courants(self, actif: str) -> FraisCourantsProposes | None:
        """Ce que la liste propose pour cet ISIN, ou rien.

        Une valeur hors de la fourchette de vraisemblance est **écartée** : mieux vaut ne rien
        proposer qu'un TER de 20 % né d'une erreur d'unité (`config/actifs.py`).
        """
        ligne = self.lignes.get(actif.strip().upper())
        if ligne is None:
            return None
        if not (TER_MINIMUM <= ligne.ter_pour_cent <= TER_MAXIMUM):
            return None
        return FraisCourantsProposes(
            ter_pour_cent=ligne.ter_pour_cent,
            source=NOM,
            nom=ligne.nom,
            politique=ligne.politique,
            date=self.date,
        )


def telecharger(ouvrir: Ouvrir | None = None) -> ListeXetra:
    """Trouve le lien du fichier sur la page, le télécharge et le lit.

    Lève `ErreurDeSource` si quelque chose manque : l'appelant en fait un refus lisible, et la
    commande continue sans proposition de TER — jamais avec une valeur inventée.
    """
    ouvrir = ouvrir or _telecharger
    page = ouvrir(ADRESSE_PAGE).decode("utf-8", errors="replace")
    trouve = MOTIF_DU_LIEN.search(page)
    if trouve is None:
        raise ErreurDeSource(
            "le lien du fichier des ETF n'a pas été trouvé sur la page de Deutsche Börse : "
            "elle a probablement changé de forme"
        )
    adresse = trouve.group(1)
    if adresse.startswith("/"):
        adresse = RACINE + adresse
    return lire(ouvrir(adresse))


def lire(contenu: bytes) -> ListeXetra:
    """Lit le fichier téléchargé. C'est un `.xlsx`, malgré son extension."""
    try:
        with zipfile.ZipFile(BytesIO(contenu)) as archive:
            partages = _chaines_partagees(archive)
            rangees = list(_rangees(archive, partages))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as erreur:
        raise ErreurDeSource(
            f"le fichier des ETF de Xetra n'a pas pu être lu : {erreur}. Son format a "
            "peut-être changé (il porte l'extension .xls mais c'est un .xlsx)"
        ) from erreur

    date = _date_deffet(rangees)
    entete, rang = _entete(rangees)
    lignes: dict[str, LigneXetra] = {}
    for rangee in rangees[rang + 1 :]:
        ligne = _ligne(rangee, entete)
        if ligne is not None:
            lignes.setdefault(ligne.isin, ligne)
    if not lignes:
        raise ErreurDeSource(
            "le fichier des ETF de Xetra a été lu mais ne contient aucune ligne exploitable"
        )
    return ListeXetra(lignes, date)


# --- Lecture du .xlsx, en bibliothèque standard ----------------------------------------


def _chaines_partagees(archive: zipfile.ZipFile) -> list[str]:
    """Un `.xlsx` range les textes dans une table commune, et les cellules y renvoient."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    racine = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(morceau.text or "" for morceau in element.iter(f"{ESPACE_XLSX}t"))
        for element in racine.findall(f"{ESPACE_XLSX}si")
    ]


def _premiere_feuille(archive: zipfile.ZipFile) -> str:
    feuilles = sorted(
        nom for nom in archive.namelist() if nom.startswith("xl/worksheets/sheet")
    )
    if not feuilles:
        raise ErreurDeSource("le fichier des ETF de Xetra ne contient aucune feuille")
    return feuilles[0]


def _colonne(reference: str | None, rang_par_defaut: int) -> int:
    """La colonne d'une cellule, d'après sa référence (« B7 » → 1), en partant de zéro.

    Un `.xlsx` **omet les cellules vides** : la troisième cellule écrite d'une ligne n'est pas
    forcément la troisième colonne. Se fier au rang décalerait tout le tableau dès qu'une case
    est vide, et on lirait un ISIN dans la colonne du nom, ou un TER dans celle de la devise —
    un chiffre plausible et faux. La référence, elle, ne ment pas.
    """
    if not reference:
        return rang_par_defaut
    lettres = "".join(caractere for caractere in reference if caractere.isalpha()).upper()
    if not lettres:
        return rang_par_defaut
    index = 0
    for lettre in lettres:
        index = index * 26 + (ord(lettre) - ord("A") + 1)
    return index - 1


def _rangees(archive: zipfile.ZipFile, partages: list[str]) -> Iterator[list[str]]:
    racine = ElementTree.fromstring(archive.read(_premiere_feuille(archive)))
    for rangee in racine.iter(f"{ESPACE_XLSX}row"):
        cellules: dict[int, str] = {}
        for rang, cellule in enumerate(rangee.findall(f"{ESPACE_XLSX}c")):
            cellules[_colonne(cellule.get("r"), rang)] = _cellule(cellule, partages)
        if not cellules:
            yield []
            continue
        yield [cellules.get(colonne, "") for colonne in range(max(cellules) + 1)]


def _cellule(cellule: ElementTree.Element, partages: list[str]) -> str:
    valeur = cellule.find(f"{ESPACE_XLSX}v")
    texte = "" if valeur is None or valeur.text is None else valeur.text
    if cellule.get("t") == "s":
        try:
            return partages[int(texte)]
        except (ValueError, IndexError):
            return ""
    if cellule.get("t") == "inlineStr":
        element = cellule.find(f"{ESPACE_XLSX}is")
        if element is not None:
            return "".join(morceau.text or "" for morceau in element.iter(f"{ESPACE_XLSX}t"))
    return texte


# --- Interprétation des rangées --------------------------------------------------------

MOTIF_DE_LA_DATE = re.compile(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})")


def _date_deffet(rangees: list[list[str]]) -> Date | None:
    """La date que le fichier annonce en tête (« As of 28/09/2026 »), s'il en annonce une."""
    for rangee in rangees[:10]:
        for cellule in rangee:
            trouve = MOTIF_DE_LA_DATE.search(cellule)
            if trouve is not None and "as of" in cellule.lower():
                jour, mois, annee = (int(morceau) for morceau in trouve.groups())
                try:
                    return Date(annee, mois, jour)
                except ValueError:
                    return None
    return None


def _entete(rangees: list[list[str]]) -> tuple[dict[str, int], int]:
    """La rangée des intitulés, et où sont les colonnes qui nous intéressent."""
    for rang, rangee in enumerate(rangees[:20]):
        intitules = {cellule.strip().upper(): index for index, cellule in enumerate(rangee)}
        if all(colonne in intitules for colonne in COLONNES_ATTENDUES):
            return intitules, rang
    raise ErreurDeSource(
        "le fichier des ETF de Xetra n'a pas les colonnes attendues "
        f"({', '.join(COLONNES_ATTENDUES)}) : son format a changé"
    )


def _ligne(rangee: list[str], entete: dict[str, int]) -> LigneXetra | None:
    def colonne(nom: str) -> str:
        index = entete.get(nom)
        if index is None or index >= len(rangee):
            return ""
        return rangee[index].strip()

    if colonne("PRODUCT TYPE").upper() not in TYPES_RETENUS:
        return None
    isin = colonne("ISIN").upper()
    if not isin:
        return None
    fraction = _fraction(colonne("ONGOING CHARGES"))
    if fraction is None:
        return None
    return LigneXetra(
        isin=isin,
        ter_pour_cent=(fraction * CENT).normalize(),
        nom=colonne("PRODUCT NAME") or None,
        politique=colonne("USE OF PROFITS") or None,
    )


def _fraction(texte: str) -> Decimal | None:
    """La valeur telle que la source l'écrit : une fraction, à arrondir.

    0.0007000000000000001 veut dire 0,07 % : sans cet arrondi, le fichier proposé à
    l'utilisateur porterait dix-neuf décimales.
    """
    if not texte:
        return None
    try:
        brut = Decimal(texte)
    except ArithmeticError:
        return None
    if brut < 0:
        return None
    return brut.quantize(PAS_DU_TER, rounding=ROUND_HALF_UP)


def _telecharger(adresse: str) -> bytes:
    requete = urllib.request.Request(adresse, headers={"User-Agent": NAVIGATEUR})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:  # noqa: S310
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        raise SourceInjoignable(
            f"Deutsche Börse a refusé la demande ({erreur.code}) : la liste des ETF n'a pas "
            "pu être récupérée. Les frais courants devront être saisis à la main."
        ) from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise SourceInjoignable(
            f"Deutsche Börse est injoignable ({erreur}) : vérifiez la connexion, le pare-feu "
            "ou l'antivirus. Les frais courants devront être saisis à la main."
        ) from erreur
