"""Ce que le moteur n'a pas pu calculer normalement.

Le moteur ne s'arrête jamais sur un cas bancal et ne le corrige jamais en silence : il
calcule ce qu'il peut, et il **dit** ce qui cloche (règles 5 et 6 de CLAUDE.md). Un
signalement voyage avec le résultat, s'affiche dans le rapport de `dashboard positions`, et
sera montré en permanence par l'interface (étape 9).

C'est le pendant, côté moteur, du rapport de lecture de l'adaptateur. Il est écrit à part
parce que le moteur ne connaît pas l'adaptateur : il ne lit que le format pivot (D-26).
"""

from __future__ import annotations

from dataclasses import dataclass

from dashboard_tr.pivot.operation import Poche


@dataclass(frozen=True)
class Signalement:
    """Quelque chose que l'utilisateur doit savoir avant de se fier à un chiffre."""

    categorie: str
    """Nom court, pour regrouper : « prix à compléter », « stock insuffisant »…"""

    message: str
    """Phrase en français, destinée à être lue telle quelle.

    **Aucune valeur venue d'un texte affiché n'y entre.** Les montants et les quantités qui
    s'y trouvent sont ceux du pivot, déjà vérifiés ; le nom d'un actif, lui, n'y figure
    jamais — seul son identifiant, qui est un ISIN, donc pas une donnée personnelle."""

    actif: str | None = None
    poche: Poche | None = None
    reference_source: str | None = None
    """Identifiant de l'événement d'origine, pour remonter à la donnée brute."""

    def __str__(self) -> str:
        ou = f" [{self.actif}" + (f" · {self.poche.value}]" if self.poche else "]")
        return f"{self.message}{ou if self.actif else ''}"
