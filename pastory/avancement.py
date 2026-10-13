"""Où en est une longue lecture : ce que la barre d'attente de l'écran montre (D-110).

La première lecture d'un export interroge des sources en ligne, **actif par actif** : la
cotation et les frais de chacun, ses cours, puis sa composition. Elle dure de quelques secondes à
une minute, et un écran qui ne dit rien pendant ce temps laisse croire à une panne (retour du
premier testeur). L'assembleur dit donc où il en est, et l'écran le montre.

Ce module ne connaît ni l'écran ni les sources : il compte. **Il ne mesure pas du temps**, il
compte des actifs traités — c'est la seule chose qu'on sache avec certitude, et c'est ce que la
barre affiche (« 3 actifs sur 8 »). Aucun libellé n'est écrit ici : les mots sont ceux de
l'écran (`vues/attente.py`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import StrEnum


class Etape(StrEnum):
    """Les trois temps longs d'une lecture, dans l'ordre où l'assembleur les parcourt."""

    REGLAGES = "reglages"
    """La cotation, les frais courants et le contenu de chaque actif (D-80)."""

    COURS = "cours"
    """Les cours de chaque actif, depuis sa première opération."""

    COMPOSITIONS = "compositions"
    """La composition de chaque fonds et de chaque société."""


@dataclass(frozen=True)
class Point:
    """Où en est la lecture : l'étape en cours, et combien d'actifs y sont traités."""

    etape: Etape
    fait: int
    total: int

    @property
    def part(self) -> float:
        """La part de la lecture entière déjà faite, de 0 à 1.

        Chaque étape pèse **le même poids**, et avance au rythme de ses actifs : la barre ne
        prétend pas savoir combien de secondes il reste.
        """
        etapes = list(Etape)
        dans_l_etape = self.fait / self.total if self.total else 1.0
        return (etapes.index(self.etape) + dans_l_etape) / len(etapes)


class Suivi:
    """Le compteur que l'assembleur fait avancer et que l'écran lit, d'un fil à l'autre.

    Sans lecteur, il ne coûte rien : la ligne de commande s'en passe (`construire` en crée un
    que personne ne regarde).
    """

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._en_cours = False
        self._point: Point | None = None

    def commencer(self) -> None:
        """Une lecture commence : on ne sait pas encore combien d'actifs elle compte."""
        with self._verrou:
            self._en_cours = True
            self._point = None

    def etape(self, etape: Etape, total: int) -> None:
        """Une étape commence, sur `total` actifs."""
        with self._verrou:
            self._point = Point(etape, 0, max(0, total))

    def avancer(self) -> None:
        """Un actif de plus est traité."""
        with self._verrou:
            if self._point is not None and self._point.fait < self._point.total:
                self._point = Point(self._point.etape, self._point.fait + 1, self._point.total)

    def terminer(self) -> None:
        """La lecture est finie, qu'elle ait abouti ou non."""
        with self._verrou:
            self._en_cours = False
            self._point = None

    def lire(self) -> tuple[bool, Point | None]:
        """`(une lecture est en cours, où elle en est)`. Sans point : elle vient de commencer."""
        with self._verrou:
            return self._en_cours, self._point
