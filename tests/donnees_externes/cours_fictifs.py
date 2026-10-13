"""Une source de cours en mémoire, pour tester sans réseau.

Aucun test du projet ne sort de la machine : une source factice permet de vérifier tout ce qui
compte — le repli sur le dernier jour coté, les refus, le cache — sans dépendre de Yahoo, ni de
la météo du réseau. Le lecteur de la vraie réponse Yahoo, lui, est testé sur des fichiers JSON
écrits à la main (`test_yahoo.py`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import Configuration, Declaration
from pastory.donnees_externes.cours import Cours, ErreurDeSource

AUJOURD_HUI = Date(2026, 9, 26)

ACTIF = "XX0000000001"
AUTRE_ACTIF = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"

TICKER = "AAAA.DE"
PLACE = "XETRA"


def configuration(
    declarations: Mapping[str, Declaration] | None = None,
) -> Configuration:
    """Une configuration où `ACTIF` est déclaré, sauf indication contraire."""
    if declarations is None:
        declarations = {ACTIF: Declaration(TICKER, "EUR")}
    return Configuration(declarations=dict(declarations))


def cours(
    jour: Date,
    valeur: str,
    actif: str = ACTIF,
    *,
    place: str = PLACE,
    devise: str = "EUR",
    ticker: str | None = TICKER,
) -> Cours:
    return Cours(
        actif=actif,
        date=jour,
        valeur=Decimal(valeur),
        devise=devise,
        place=place,
        source="Source de test",
        recupere_le=AUJOURD_HUI,
        ticker=ticker,
    )


class SourceFictive:
    """Répond ce qu'on lui a donné, et compte les appels.

    Le comptage sert à vérifier une promesse précise : un cours déjà en cache ne provoque
    aucun appel (D-50), et un actif introuvable n'est pas redemandé à chaque opération.
    """

    nom = "Source de test"

    def __init__(
        self,
        series: Mapping[str, Iterable[Cours]] | None = None,
        erreur: ErreurDeSource | None = None,
    ) -> None:
        self.series = {
            actif: sorted(valeurs, key=lambda un_cours: un_cours.date)
            for actif, valeurs in (series or {}).items()
        }
        self.erreur = erreur
        self.appels: list[tuple[str, Date, Date]] = []

    def serie(
        self, actif: str, declaration: Declaration, debut: Date, fin: Date
    ) -> list[Cours]:
        self.appels.append((actif, debut, fin))
        if self.erreur is not None:
            raise self.erreur
        return [
            un_cours
            for un_cours in self.series.get(actif, [])
            if debut <= un_cours.date <= fin
        ]


class CacheEnMemoire:
    """Le cache réduit à un dictionnaire, quand le test ne porte pas sur les fichiers."""

    def __init__(self) -> None:
        self.series: dict[str, dict[Date, Cours]] = {}
        self.reprises: set[str] = set()

    def serie_reprise(self, actif: str) -> bool:
        return actif in self.reprises

    def noter_la_reprise(self, actif: str) -> None:
        self.reprises.add(actif)

    def lire(self, actif: str) -> dict[Date, Cours]:
        return dict(self.series.get(actif, {}))

    def oublier(self, actif: str | None = None) -> list[str]:
        concernes = [actif] if actif is not None else list(self.series)
        return [un for un in concernes if self.series.pop(un, None) is not None]

    def ecrire(self, actif: str, cours: Iterable[Cours]) -> int:
        serie = self.series.setdefault(actif, {})
        nouveaux = [un_cours for un_cours in cours if un_cours.date not in serie]
        for un_cours in nouveaux:
            serie[un_cours.date] = un_cours
        return len(nouveaux)
