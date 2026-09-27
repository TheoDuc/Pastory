"""Une source de cours réduite à un dictionnaire, pour éprouver le moteur sans rien d'autre.

Le moteur ne demande qu'une chose à une source : `cours(actif, date)`. Cette source-ci répond
avec des cours écrits à la main, et imite le seul comportement du vrai fournisseur qui compte
pour les calculs : un jour sans cotation prend le **dernier jour coté** qui précède (jusqu'à
dix jours), jamais une valeur inventée.

Valeurs **fictives** (D-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

RECUL_MAXIMAL = timedelta(days=10)


@dataclass(frozen=True)
class CoursFictif:
    """La forme que le moteur attend d'un cours (`CoursDeMarche`), et rien de plus."""

    valeur: Decimal
    date: Date
    devise: str = "EUR"
    place: str = "PLACE DE TEST"
    source: str = "Source de test"


class SourceFixe:
    """Répond ce qu'on lui a donné : `{actif: {jour: "cours"}}`. Compte les demandes."""

    def __init__(
        self,
        series: Mapping[str, Mapping[Date, str]] | None = None,
        *,
        devise: str = "EUR",
    ) -> None:
        self.series = {
            actif: {jour: Decimal(valeur) for jour, valeur in serie.items()}
            for actif, serie in (series or {}).items()
        }
        self.devise = devise
        self.demandes: list[tuple[str, Date]] = []

    def cours(self, actif: str, date: Date) -> CoursFictif | None:
        self.demandes.append((actif, date))
        serie = self.series.get(actif, {})
        candidats = [jour for jour in serie if date - RECUL_MAXIMAL <= jour <= date]
        if not candidats:
            return None
        jour = max(candidats)
        return CoursFictif(valeur=serie[jour], date=jour, devise=self.devise)


def cours_constant(actif: str, valeur: str, du: Date, au: Date) -> dict[str, dict[Date, str]]:
    """Le même cours tous les jours entre deux dates : de quoi tester sans bruit."""
    serie: dict[Date, str] = {}
    jour = du
    while jour <= au:
        serie[jour] = valeur
        jour += timedelta(days=1)
    return {actif: serie}
