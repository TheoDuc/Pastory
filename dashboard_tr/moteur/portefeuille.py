"""Toutes les positions ensemble : par poche, et au total.

Le moteur calcule **par actif d'abord**, puis agrège (architecture-notes §5). Rien n'est
additionné qui ne vienne d'une position, et chaque total se retrouve en additionnant la
colonne correspondante du tableau des positions — c'est la condition pour que le propriétaire
puisse le refaire dans un tableur.

Ce qui n'est **pas** ici, volontairement : la valeur de marché, le gain, le TRI et le TWRR.
Tous ont besoin des cours, qui arrivent à l'étape 4. Le moteur de l'étape 3 ne calcule que ce
qui se déduit des opérations seules.
"""

from __future__ import annotations

from collections.abc import Container, Iterable
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal

from dashboard_tr.moteur.position import Position, construire_positions
from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.pivot.operation import Operation, Poche

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Totaux:
    """La somme d'un groupe de positions : une poche, ou le portefeuille entier.

    La performance et les coûts restent **deux colonnes séparées** (D-21) : rien de ce qui
    est prélevé n'entre dans le capital investi.
    """

    nombre_de_positions: int
    nombre_de_positions_detenues: int

    capital_net_investi: Decimal
    """Somme des capitaux nets investis des actifs encore détenus et de ceux déjà vendus
    (un actif entièrement vendu y compte pour zéro)."""

    achats_bruts: Decimal
    ventes_brutes: Decimal
    dividendes_bruts: Decimal
    distributions_capital: Decimal
    plus_values_realisees_brutes: Decimal
    plus_values_realisees_nettes: Decimal

    frais: Decimal
    """Frais réellement facturés. N'entrent dans aucune performance (D-21)."""
    taxes: Decimal
    """Taxes réellement prélevées, dividendes compris. N'entrent dans aucune performance."""

    historique_incomplet: bool
    """Vrai si au moins une position du groupe repose sur une histoire trouée (D-45).

    Quand il est vrai, le capital net investi du groupe est **sous-estimé** : il manque le
    montant de parts bien détenues. Le rapport et l'interface doivent le dire."""

    @classmethod
    def de(cls, positions: Iterable[Position]) -> Totaux:
        positions = list(positions)

        def somme(nom: str) -> Decimal:
            return sum((getattr(position, nom) for position in positions), ZERO)

        return cls(
            nombre_de_positions=len(positions),
            nombre_de_positions_detenues=sum(
                1 for position in positions if position.etat.detenue
            ),
            capital_net_investi=sum(
                (position.etat.capital_net_investi for position in positions), ZERO
            ),
            achats_bruts=somme("achats_bruts"),
            ventes_brutes=somme("ventes_brutes"),
            dividendes_bruts=somme("dividendes_bruts"),
            distributions_capital=somme("distributions_capital"),
            plus_values_realisees_brutes=somme("plus_values_realisees_brutes"),
            plus_values_realisees_nettes=somme("plus_values_realisees_nettes"),
            frais=somme("frais"),
            taxes=somme("taxes"),
            historique_incomplet=any(position.historique_incomplet for position in positions),
        )


@dataclass(frozen=True)
class Portefeuille:
    """Le résultat du moteur : toutes les positions, et ce qu'il n'a pas su calculer."""

    positions: tuple[Position, ...]
    signalements: tuple[Signalement, ...]

    @classmethod
    def construire(cls, operations: Iterable[Operation]) -> Portefeuille:
        """Rejoue les opérations du format pivot. C'est **la seule entrée du moteur** (D-26)."""
        positions, signalements = construire_positions(operations)
        return cls(positions=tuple(positions), signalements=tuple(signalements))

    def au(self, date: Date) -> Portefeuille:
        """Le portefeuille tel qu'il était à la fin de ce jour-là.

        Les positions nées après cette date disparaissent ; les autres sont coupées au bon
        endroit. Les signalements sont conservés tels quels : ils décrivent la lecture, pas
        une date.
        """
        positions = [position.jusqu_au(date) for position in self.positions]
        return Portefeuille(
            positions=tuple(position for position in positions if position.journal),
            signalements=self.signalements,
        )

    # --- Lecture --------------------------------------------------------------

    @property
    def positions_detenues(self) -> list[Position]:
        """Les actifs dont il reste des parts, dans l'ordre d'affichage (poche puis actif)."""
        return [position for position in self.positions if position.etat.detenue]

    def par_poche(self) -> dict[Poche, Totaux]:
        """Les totaux de chaque poche, dans l'ordre PEA, CTO, crypto."""
        groupes: dict[Poche, list[Position]] = {}
        for position in self.positions:
            groupes.setdefault(position.poche, []).append(position)
        return {
            poche: Totaux.de(groupes[poche]) for poche in Poche if poche in groupes
        }

    @property
    def total(self) -> Totaux:
        return Totaux.de(self.positions)

    def quantites_par_actif(self, poches: Container[Poche] | None = None) -> dict[str, Decimal]:
        """Quantité détenue par actif, **toutes poches confondues**.

        C'est la forme attendue par le rapprochement : le portefeuille réel donné par la
        banque liste des ISIN, sans dire dans quelle enveloppe ils sont détenus. Un actif
        présent à la fois en PEA et en CTO doit donc y être additionné.

        `poches` restreint l'addition à certaines enveloppes. Le rapprochement s'en sert
        quand la photo de la banque n'en couvre qu'une partie : additionner des parts que
        la banque ne montre pas créerait un écart de toutes pièces.
        """
        quantites: dict[str, Decimal] = {}
        for position in self.positions:
            if not position.etat.detenue:
                continue
            if poches is not None and position.poche not in poches:
                continue
            quantites[position.actif] = (
                quantites.get(position.actif, Decimal("0")) + position.etat.quantite
            )
        return quantites

    def actifs_par_poche(self) -> dict[Poche, set[str]]:
        """Les actifs encore détenus, rangés par enveloppe."""
        groupes: dict[Poche, set[str]] = {}
        for position in self.positions:
            if position.etat.detenue:
                groupes.setdefault(position.poche, set()).add(position.actif)
        return groupes

    @property
    def positions_incompletes(self) -> list[Position]:
        """Celles dont les chiffres reposent sur une histoire trouée (D-45)."""
        return [position for position in self.positions if position.historique_incomplet]
