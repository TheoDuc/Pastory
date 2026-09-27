"""Des compositions écrites à la main, et une source factice qui les rend.

Même principe que `cours_fictifs.py` : le moteur se teste sans réseau et sans source réelle,
puisqu'il ne connaît qu'un protocole. Les chiffres sont choisis pour **tomber juste** — on veut
pouvoir refaire chaque total de tête en lisant le test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal

ARRETE_LE = Date(2026, 8, 31)


@dataclass(frozen=True)
class PartFictive:
    code: str
    pour_cent: Decimal


@dataclass(frozen=True)
class CompositionFictive:
    """La forme que `moteur.diversification.CompositionDUnActif` attend, et rien de plus."""

    pays: tuple[PartFictive, ...] = ()
    secteurs: tuple[PartFictive, ...] = ()
    classes: tuple[PartFictive, ...] = ()
    arrete_le: Date = ARRETE_LE
    intitule_de_la_date: str = "date annoncée par la source fictive"
    source: str = "source fictive"
    replication: str | None = None


def parts(**poids: str) -> tuple[PartFictive, ...]:
    """`parts(US="70", FR="30")` — dans l'ordre d'écriture."""
    return tuple(
        PartFictive(code=code, pour_cent=Decimal(valeur)) for code, valeur in poids.items()
    )


@dataclass
class SourceDeCompositionFictive:
    """Un dictionnaire d'actifs, et le compte des demandes.

    Le compteur sert à vérifier qu'un actif n'est demandé qu'une fois : le vrai fournisseur
    garde ses réponses, et un oubli ferait un appel réseau par rubrique.
    """

    table: dict[str, CompositionFictive] = field(default_factory=dict)
    demandes: list[str] = field(default_factory=list)

    def composition(self, actif: str) -> CompositionFictive | None:
        self.demandes.append(actif)
        return self.table.get(actif)


def etf_monde() -> CompositionFictive:
    """Un ETF d'actions **physique** : 100 % d'actions, et des pays qui somment à 100."""
    return CompositionFictive(
        pays=parts(US="60", FR="30", JP="10"),
        secteurs=parts(technology="50", healthcare="50"),
        classes=parts(stock="100"),
    )


def etf_synthetique_pea() -> CompositionFictive:
    """Un ETF PEA à swap : la composition est celle de **l'indice** (D-64).

    Les poids ne somment pas à 100 : c'est le cas réel, mesuré de 98,56 % à 99,96 % selon le
    fonds. Le reste doit finir en « non attribué », jamais réparti (D-69).
    """
    return CompositionFictive(
        pays=parts(US="70", DE="20"),
        secteurs=parts(technology="90"),
        classes=parts(stock="100"),
        replication="synthétique",
    )


def etf_obligataire() -> CompositionFictive:
    """Un ETF d'obligations : aucune action, donc hors géographie et hors secteurs (D-68)."""
    return CompositionFictive(classes=parts(bond="100"), arrete_le=Date(2026, 9, 22))


def etf_mixte() -> CompositionFictive:
    """60 % d'actions, 40 % d'obligations : le cas qui sépare « hors périmètre » du reste."""
    return CompositionFictive(
        pays=parts(US="60"),
        secteurs=parts(technology="60"),
        classes=parts(stock="60", bond="40"),
    )


def action_en_direct(pays: str = "FR", secteur: str = "consumer_cyclical") -> CompositionFictive:
    """Une action : un pays, un secteur, 100 % — et une règle de pays différente (D-66)."""
    return CompositionFictive(
        pays=parts(**{pays: "100"}),
        secteurs=parts(**{secteur: "100"}),
        classes=parts(stock="100"),
    )
