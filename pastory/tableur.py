"""Écrire un nombre pour un lecteur francophone : dans un tableur, ou dans une phrase.

La première moitié du module fixe les conventions des fichiers CSV.

Ce sont **les fichiers que le propriétaire ouvre pour vérifier** : opérations du pivot,
positions et journal du moteur. Ils doivent donc tous se comporter pareil, et bien, dans
Excel et LibreOffice en français.

Trois conventions, rassemblées ici pour qu'aucun export n'en oublie une :

- séparateur **point-virgule** et **virgule décimale**, sinon un tableur français lit
  « 25.00 » comme du texte, ou pire, comme une date ;
- pas de séparateur de milliers, qui ferait la même chose en pire ;
- encodage UTF-8 **avec BOM**, sans lequel Excel sous Windows affiche les accents de travers
  — et un fichier de vérification illisible ne sert à rien.

Tous ces fichiers contiennent de vraies valeurs : ils sont écrits dans le dossier personnel,
hors du dossier synchronisé, et n'entrent jamais dans git (D-01, D-37).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

SEPARATEUR = ";"
ENCODAGE = "utf-8-sig"
"""UTF-8 précédé de la marque que Excel attend sous Windows."""

VALEUR_A_COMPLETER = "à compléter"
"""Ce qu'on écrit à la place d'un montant qui attend une donnée externe (D-15).

Une case **vide** passerait pour un zéro une fois dans un tableur ; le lecteur doit voir que
la valeur manque, et pourquoi."""

VALEUR_SANS_OBJET = "—"
"""Ce qu'on écrit quand la valeur n'existe pas et n'a pas à exister.

Différent de `VALEUR_A_COMPLETER` : là, rien n'est attendu. Un prix de revient n'a pas de
sens quand on ne détient plus rien, et une plus-value réalisée n'en a pas sur un achat."""


def nombre(valeur: Decimal | None, *, absent: str = "") -> str:
    """Un nombre pour un tableur français : virgule décimale, pas de séparateur de milliers.

    La précision est conservée telle quelle, sans arrondi : dans une cellule de tableur,
    c'est la valeur exacte qu'on veut pouvoir recalculer.
    """
    if valeur is None:
        return absent
    return format(valeur, "f").replace(".", ",")


CENTIME = Decimal("0.01")


def nombre_lisible(valeur: Decimal | None, *, absent: str = "") -> str:
    """Un nombre destiné à être lu dans une phrase ou dans une colonne de rapport.

    Deux décimales, et davantage **seulement si elles portent du sens** : un prix de revient
    de crypto vaut 30 012,004802 €, et l'arrondir dans un rapport de vérification cacherait
    justement ce qu'on veut contrôler. À l'inverse, « 3,000000 part(s) » dans une phrase
    française ne dit rien de plus que « 3 » et se lit moins bien.
    """
    if valeur is None:
        return absent
    arrondi = valeur.quantize(CENTIME)
    retenu = arrondi if arrondi == valeur else valeur.normalize()
    return format(retenu, "f").replace(".", ",")


def ecrire(
    colonnes: Sequence[str], lignes: Iterable[Mapping[str, str]], fichier: Path
) -> Path:
    """Écrit un fichier aux conventions ci-dessus et renvoie son chemin."""
    fichier.parent.mkdir(parents=True, exist_ok=True)

    with fichier.open("w", encoding=ENCODAGE, newline="") as flux:
        redacteur = csv.DictWriter(flux, fieldnames=list(colonnes), delimiter=SEPARATEUR)
        redacteur.writeheader()
        redacteur.writerows(lignes)

    return fichier
