"""Ce que valent les actifs détenus, à une date, aux cours de clôture.

C'est la première fois qu'un cours de marché entre dans le moteur — et il y entre **par la
porte**, pas par un import : ce module déclare ce dont il a besoin (`SourceDeValorisation`,
une méthode), et c'est `cli.py` qui lui passe un objet qui sait répondre. Le moteur ignore
toujours d'où viennent les cours (D-26, D-49), exactement comme il ignore de quelle banque
viennent les opérations.

Deux règles, héritées de tout le reste du projet :

- **une position sans cours n'est pas valorisée, et cela se voit** (D-45). Elle sort des
  totaux, qui sont alors marqués **partiels** (D-53). Aucun zéro silencieux : un zéro ferait
  un gain faux ;
- **le cours retenu porte sa date**, qui peut être antérieure au jour demandé (dernier jour
  coté). La valeur d'« aujourd'hui » est celle de la dernière clôture connue, et le rapport
  écrit laquelle (D-52).

```
valeur d'une position = quantité détenue × cours de clôture retenu   (glossaire §3)
```
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.position import Position
from pastory.pivot.operation import Poche

CENTIME = Decimal("0.01")
"""Une valeur est un montant : elle s'arrête au centime, comme tout montant du projet. Le cours,
lui, est gardé tel quel — c'est lui qui permet de refaire la multiplication à la main."""

ZERO = Decimal("0.00")
UN_JOUR = timedelta(days=1)


# --- Ce que le moteur demande, sans savoir qui répond ----------------------------------


class CoursDeMarche(Protocol):
    """Un cours de clôture, avec ce qu'il faut pour le vérifier : sa date, sa place, sa source.

    `donnees_externes.cours.Cours` a exactement cette forme, sans que ce module le sache.
    """

    valeur: Decimal
    date: Date
    devise: str
    place: str
    source: str


class SourceDeValorisation(Protocol):
    """Qui sait donner un cours. Une seule méthode.

    `None` veut dire « pas de cours utilisable à cette date », et celui qui répond est censé
    avoir gardé le motif quelque part (le fournisseur de l'étape 4 accumule des refus). Le
    moteur, lui, se contente de constater et de le dire.
    """

    def cours(self, actif: str, date: Date) -> CoursDeMarche | None: ...


# --- Une position valorisée ------------------------------------------------------------


@dataclass(frozen=True)
class PositionValorisee:
    """Une position détenue, et ce qu'elle vaut au jour demandé — ou pourquoi on ne sait pas."""

    position: Position
    date: Date
    """Le jour demandé. Le cours retenu peut décrire un jour antérieur (`jour_decale`)."""

    cours: CoursDeMarche | None
    motif: str | None = None
    """Pourquoi la position n'est pas valorisée, quand `cours` est `None`."""

    @property
    def actif(self) -> str:
        return self.position.actif

    @property
    def poche(self) -> Poche:
        return self.position.poche

    @property
    def quantite(self) -> Decimal:
        return self.position.etat.quantite

    @property
    def valorisee(self) -> bool:
        return self.cours is not None

    @property
    def valeur(self) -> Decimal | None:
        """Quantité × cours, au centime. `None` si aucun cours n'est utilisable (D-45)."""
        if self.cours is None:
            return None
        return (self.quantite * self.cours.valeur).quantize(CENTIME, rounding=ROUND_HALF_UP)

    @property
    def plus_value_latente(self) -> Decimal | None:
        """Valeur − capital net investi (glossaire §4).

        `None` si la position n'est pas valorisée, ou si son histoire est incomplète : un
        capital investi sous-estimé donnerait une plus-value gonflée, et rien ne le dirait.
        """
        valeur = self.valeur
        if valeur is None or self.position.historique_incomplet:
            return None
        return valeur - self.position.etat.capital_net_investi

    @property
    def jour_decale(self) -> bool:
        """Vrai si le cours retenu n'est pas celui du jour demandé (week-end, jour férié)."""
        return self.cours is not None and self.cours.date != self.date

    @property
    def fiable(self) -> bool:
        """Faux si la quantité elle-même repose sur une histoire incomplète (D-45)."""
        return not self.position.historique_incomplet


@dataclass(frozen=True)
class TotauxValeur:
    """La valeur d'un groupe de positions — une poche, ou le portefeuille — et sa complétude."""

    valeur: Decimal
    """Somme des valeurs des positions **valorisées** du groupe."""

    nombre_de_positions: int
    nombre_valorisees: int

    @property
    def complet(self) -> bool:
        return self.nombre_valorisees == self.nombre_de_positions

    @classmethod
    def de(cls, positions: Iterable[PositionValorisee]) -> TotauxValeur:
        positions = list(positions)
        valorisees = [position for position in positions if position.valorisee]
        return cls(
            valeur=sum((position.valeur or ZERO for position in valorisees), ZERO),
            nombre_de_positions=len(positions),
            nombre_valorisees=len(valorisees),
        )


@dataclass(frozen=True)
class Valorisation:
    """Le portefeuille valorisé à une date : chaque position, et les totaux qui en découlent."""

    date: Date
    positions: tuple[PositionValorisee, ...]

    @property
    def valorisees(self) -> list[PositionValorisee]:
        return [position for position in self.positions if position.valorisee]

    @property
    def non_valorisees(self) -> list[PositionValorisee]:
        return [position for position in self.positions if not position.valorisee]

    @property
    def complete(self) -> bool:
        """Vrai si toutes les positions détenues ont une valeur. Sinon, les totaux sont
        partiels, et le rapport doit le dire (D-53)."""
        return not self.non_valorisees

    @property
    def total(self) -> TotauxValeur:
        return TotauxValeur.de(self.positions)

    def par_poche(self) -> dict[Poche, TotauxValeur]:
        """Les totaux de chaque poche, dans l'ordre PEA, CTO, crypto."""
        groupes: dict[Poche, list[PositionValorisee]] = {}
        for position in self.positions:
            groupes.setdefault(position.poche, []).append(position)
        return {poche: TotauxValeur.de(groupes[poche]) for poche in Poche if poche in groupes}

    @property
    def sources(self) -> list[str]:
        """Les sources des cours utilisés, sans doublon, pour que le rapport les nomme."""
        vues: dict[str, None] = {}
        for position in self.valorisees:
            assert position.cours is not None
            vues.setdefault(position.cours.source)
        return list(vues)


# --- Valoriser -------------------------------------------------------------------------


def _devise(position: Position) -> str:
    """La devise des opérations de la position. Le pivot n'en connaît qu'une (D-26)."""
    return position.journal[-1].operation.devise if position.journal else "EUR"


def valoriser_position(
    position: Position, date: Date, source: SourceDeValorisation
) -> PositionValorisee:
    """Une position, au jour demandé. Ne lève jamais : ce qui manque est dit."""
    cours = source.cours(position.actif, date)
    if cours is None:
        return PositionValorisee(
            position=position,
            date=date,
            cours=None,
            motif=f"aucun cours utilisable au {date.isoformat()} ni dans les jours qui "
            "précèdent : voir le bloc « Cours de marché »",
        )
    if cours.devise.upper() != _devise(position).upper():
        # La source vérifie déjà la devise (D-48). Le redire ici ne coûte rien, et empêche
        # qu'une autre source, un jour, fasse passer des dollars pour des euros.
        return PositionValorisee(
            position=position,
            date=date,
            cours=None,
            motif=f"cours en {cours.devise} alors que la position est en {_devise(position)} : "
            "rien n'est converti (D-48)",
        )
    return PositionValorisee(position=position, date=date, cours=cours)


def valoriser_positions(
    positions: Iterable[Position], date: Date, source: SourceDeValorisation
) -> list[PositionValorisee]:
    """Les positions **détenues** à cette date, valorisées. Les autres n'ont rien à valoir."""
    return [
        valoriser_position(coupee, date, source)
        for position in positions
        if (coupee := position.jusqu_au(date)).etat.detenue
    ]


def valoriser(
    portefeuille: Portefeuille, date: Date, source: SourceDeValorisation
) -> Valorisation:
    """Le portefeuille tel qu'il était ce jour-là, aux cours de clôture de ce jour-là.

    « Ce jour-là » vaut pour les deux : les parts détenues **et** le cours. Un samedi, le
    cours retenu est celui du vendredi, et chaque position le dit (`jour_decale`).
    """
    return Valorisation(
        date=date, positions=tuple(valoriser_positions(portefeuille.positions, date, source))
    )


# --- L'évolution dans le temps ----------------------------------------------------------


@dataclass(frozen=True)
class PointEvolution:
    """La valeur du portefeuille un jour donné : le « capital brut dans le temps »."""

    date: Date
    valeur: Decimal
    par_poche: Mapping[Poche, Decimal]
    capital_net_investi: Decimal
    non_valorisees: int
    """Combien de positions détenues ce jour-là n'ont pas de valeur : au-delà de zéro, la
    valeur du jour est partielle."""


def evolution(
    portefeuille: Portefeuille, debut: Date, fin: Date, source: SourceDeValorisation
) -> list[PointEvolution]:
    """Un point par jour calendaire, bornes comprises. Rien n'est interpolé : un jour sans
    cotation prend le dernier cours connu, comme le ferait un relevé."""
    points: list[PointEvolution] = []
    jour = debut
    while jour <= fin:
        # Une seule coupe du journal par jour : elle sert à la valeur et au capital investi.
        ce_jour = portefeuille.au(jour)
        du_jour = valoriser(ce_jour, jour, source)
        points.append(
            PointEvolution(
                date=jour,
                valeur=du_jour.total.valeur,
                par_poche={poche: totaux.valeur for poche, totaux in du_jour.par_poche().items()},
                capital_net_investi=ce_jour.total.capital_net_investi,
                non_valorisees=len(du_jour.non_valorisees),
            )
        )
        jour += UN_JOUR
    return points
