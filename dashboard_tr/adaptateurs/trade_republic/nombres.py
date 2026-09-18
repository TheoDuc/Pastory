"""Lecture des nombres écrits dans les textes affichés par Trade Republic.

Tout est isolé ici (D-09) parce que c'est **l'endroit le plus dangereux de l'adaptateur**.

Un même export mélange deux écritures des nombres :

- les montants et les quantités des ordres et des plans d'épargne utilisent la **virgule**
  décimale, avec le point comme séparateur de milliers : ``1.234,56 €`` ;
- les quantités des dividendes et des titres reçus utilisent le **point** décimal, sans
  séparateur de milliers : ``1.234567``.

Lire la seconde forme avec les règles de la première donne 1 234 567 parts au lieu de
1,234567 — **un million de fois trop**, sans que rien ne le signale. C'est pour cela que la
convention n'est jamais devinée : elle est déclarée libellé par libellé dans `lexique.py`,
et une écriture qui ne respecte pas la convention annoncée est **refusée**, jamais
interprétée au mieux.

Chaque lecture renvoie aussi le **nombre de décimales réellement affichées**. C'est
l'ingrédient de la tolérance des contrôles de cohérence (D-39) : un prix écrit avec deux
décimales et un autre avec quatre ne portent pas le même arrondi.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

ESPACES = "    "
"""Espace insécable, espace fine insécable, espace fine, espace ordinaire : tous utilisés
comme séparateurs de milliers selon la langue de l'application."""

SIGNES_MOINS = "-−–"
"""Trait d'union, signe moins typographique, tiret demi-cadratin."""

SYMBOLES_DEVISE = {"€": "EUR", "$": "USD", "£": "GBP", "CHF": "CHF", "¥": "JPY"}
"""Symboles rencontrés dans les libellés. La devise lue sert à **refuser** une valeur qui
n'est pas en euros, jamais à la convertir (D-26)."""


class Convention(StrEnum):
    """Écriture attendue pour un texte donné. Déclarée dans le lexique, jamais devinée."""

    VIRGULE_DECIMALE = "virgule_decimale"
    """``1.234,56`` ou ``1 234,56`` : virgule décimale, point ou espace pour les milliers."""

    POINT_DECIMAL = "point_decimal"
    """``1.234567`` : point décimal, aucun séparateur de milliers."""


class LectureImpossible(Exception):
    """Un texte n'a pas pu être lu comme un nombre selon la convention annoncée.

    Elle n'est jamais rattrapée par une valeur de repli : l'information part au rapport de
    lecture et l'opération concernée est signalée.
    """

    def __init__(self, texte: object, raison: str) -> None:
        self.texte = texte
        self.raison = raison
        super().__init__(raison)


@dataclass(frozen=True)
class NombreLu:
    """Un nombre lu dans un texte, avec ce qu'il faut pour juger de sa précision."""

    valeur: Decimal
    """Valeur lue, **signe compris** : `Steuer` est affiché négatif alors que le pivot
    n'accepte que des nombres positifs. C'est à l'appelant de prendre la valeur absolue,
    explicitement, là où il sait pourquoi il le fait."""

    decimales: int
    """Nombre de décimales réellement affichées. ``25,00`` en a deux, ``25,0000`` en a
    quatre : le second est dix fois plus précis, et sa tolérance est dix fois plus serrée."""

    devise: str | None = None
    """Devise lue dans le texte, si un symbole y figurait."""

    @property
    def demi_dernier_chiffre(self) -> Decimal:
        """Moitié du dernier chiffre affiché : l'arrondi maximal que porte cette valeur.

        Un prix affiché ``0,33`` vaut en réalité entre 0,325 et 0,335, donc un demi-centime
        d'incertitude. Une quantité affichée ``0,123456`` en porte 0,0000005. C'est ce que
        la tolérance des contrôles additionne (D-39).
        """
        return Decimal(1).scaleb(-self.decimales) / 2

    def absolu(self) -> NombreLu:
        """Le même nombre, sans son signe. À utiliser là où le pivot exige un positif."""
        if self.valeur >= 0:
            return self
        return NombreLu(-self.valeur, self.decimales, self.devise)


def _nettoyer(texte: str) -> tuple[str, bool, str | None]:
    """Retire habillage, signe et devise. Renvoie (chiffres, negatif, devise)."""
    t = unicodedata.normalize("NFKC", texte).strip()

    devise: str | None = None
    for symbole, code in SYMBOLES_DEVISE.items():
        if symbole in t:
            devise = code
            t = t.replace(symbole, "")

    t = t.replace("+", "").strip()

    negatif = False
    while t and t[0] in SIGNES_MOINS:
        negatif = True
        t = t[1:].strip()

    return t.strip(), negatif, devise


_SANS_SEPARATEUR = re.compile(r"\d+")
_GROUPES_DE_MILLIERS = re.compile(rf"\d{{1,3}}(?:[.{ESPACES}]\d{{3}})+")


def _lire_virgule_decimale(chiffres: str, texte: object) -> tuple[Decimal, int]:
    """``1.234,56`` : virgule décimale, point ou espace pour les milliers."""
    if chiffres.count(",") > 1:
        raise LectureImpossible(texte, "plusieurs virgules décimales")

    entier, _, decimale = chiffres.partition(",")

    if decimale and not decimale.isdigit():
        raise LectureImpossible(texte, "la partie décimale n'est pas faite de chiffres")

    # Un point ne peut être qu'un séparateur de milliers : il découpe donc des groupes de
    # trois chiffres. « 1.234567 » n'en est pas un — et c'est précisément l'écriture des
    # quantités de dividendes, qu'il ne faut surtout pas lire comme 1 234 567.
    if not (_SANS_SEPARATEUR.fullmatch(entier) or _GROUPES_DE_MILLIERS.fullmatch(entier)):
        raise LectureImpossible(
            texte,
            "la partie entière n'est ni un nombre simple ni des groupes de trois chiffres : "
            "le point n'y est donc pas un séparateur de milliers, et le nombre ne peut pas "
            "être lu sans risque de se tromper d'un facteur mille",
        )

    entier_nu = re.sub(rf"[.{ESPACES}]", "", entier)
    return Decimal(f"{entier_nu}.{decimale}" if decimale else entier_nu), len(decimale)


def _lire_point_decimal(chiffres: str, texte: object) -> tuple[Decimal, int]:
    """``1.234567`` : point décimal, aucun séparateur de milliers."""
    if "," in chiffres:
        raise LectureImpossible(
            texte, "une virgule dans une écriture à point décimal : lecture ambiguë"
        )
    if any(espace in chiffres for espace in ESPACES):
        raise LectureImpossible(
            texte, "une espace dans une écriture à point décimal : lecture ambiguë"
        )
    if chiffres.count(".") > 1:
        raise LectureImpossible(texte, "plusieurs points décimaux")

    entier, _, decimale = chiffres.partition(".")
    if not entier.isdigit() or (decimale and not decimale.isdigit()):
        raise LectureImpossible(texte, "le texte n'est pas fait que de chiffres")

    return Decimal(f"{entier}.{decimale}" if decimale else entier), len(decimale)


def lire_nombre(texte: object, convention: Convention) -> NombreLu:
    """Lit un nombre écrit selon la convention annoncée.

    Lève `LectureImpossible` dès que le texte ne correspond pas exactement à la convention.
    C'est volontaire : mieux vaut une opération signalée qu'un chiffre faux silencieux.
    """
    if not isinstance(texte, str):
        raise LectureImpossible(texte, f"valeur de type {type(texte).__name__}, pas un texte")

    chiffres, negatif, devise = _nettoyer(texte)
    if not chiffres:
        raise LectureImpossible(texte, "aucun chiffre")

    if convention is Convention.VIRGULE_DECIMALE:
        valeur, decimales = _lire_virgule_decimale(chiffres, texte)
    elif convention is Convention.POINT_DECIMAL:
        valeur, decimales = _lire_point_decimal(chiffres, texte)
    else:  # pragma: no cover - la liste des conventions est fermée
        raise LectureImpossible(texte, f"convention de lecture inconnue : {convention!r}")

    return NombreLu(-valeur if negatif else valeur, decimales, devise)
