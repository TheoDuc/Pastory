"""Le format pivot : une opération sur un actif.

C'est le contrat entre les adaptateurs (une banque chacun) et le moteur (D-26, D-35).
La description lisible, avec un exemple par type, est dans `docs/format-pivot.md`.

Trois règles de forme, rappelées ici parce que tout le reste en dépend :

1. tous les nombres sont **positifs** ; le sens est porté par le type de l'opération ;
2. les montants sont des `Decimal`, jamais des flottants (D-33) ;
3. aucun numéro de compte n'entre dans le pivot.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from zoneinfo import ZoneInfo

FUSEAU_AFFICHAGE = ZoneInfo("Europe/Paris")
"""Fuseau qui définit le *jour* d'une opération (D-36)."""


class TypeOperation(StrEnum):
    """Liste **fermée** (D-35). Un cas qui n'y entre pas est signalé comme inconnu,
    jamais rangé de force dans un type existant."""

    ACHAT = "achat"
    VENTE = "vente"
    DIVIDENDE = "dividende"
    DISTRIBUTION_CAPITAL = "distribution_capital"
    TITRES_RECUS = "titres_recus"


class Poche(StrEnum):
    """Enveloppe de détention. Il n'existe pas de poche « espèces » (D-11)."""

    PEA = "PEA"
    CTO = "CTO"
    CRYPTO = "crypto"


class Provenance(StrEnum):
    """D'où vient la valeur d'un champ (docs/format-pivot.md §4)."""

    DONNEE = "donnee"
    """Champ structuré de l'export : solide."""
    TEXTE = "texte"
    """Lu dans un texte affiché, dans la langue de l'application : fragile (D-09, D-19)."""
    DEDUCTION = "deduction"
    """Reconstitué par une règle écrite (D-15, D-16)."""
    ESTIMATION = "estimation"
    """Valeur approchée (spread, TER, impôt). Aucune dans le pivot : réservée au moteur."""
    A_COMPLETER = "a_completer"
    """Valeur manquante, en attente d'une donnée externe (cours de l'étape 4)."""


TYPES_AVEC_QUANTITE_OBLIGATOIRE = frozenset(
    {TypeOperation.ACHAT, TypeOperation.VENTE, TypeOperation.TITRES_RECUS}
)
"""Types où des parts changent de main : la quantité doit être présente et strictement positive."""

TYPES_ENCAISSEMENT = frozenset(
    {TypeOperation.VENTE, TypeOperation.DIVIDENDE, TypeOperation.DISTRIBUTION_CAPITAL}
)
"""Types où de l'argent est reçu : montant réglé = montant brut − frais − taxes."""

DEVISE_UNIQUE = "EUR"
"""Seule devise prise en charge pour l'instant (D-26)."""


def jour_a_paris(instant_utc: datetime) -> Date:
    """Jour calendaire d'une opération, en heure de Paris (D-36).

    Sans cette conversion, une opération passée en soirée serait comptée le lendemain et
    ne correspondrait plus à ce que l'utilisateur lit dans son application.

    L'horodatage doit porter son fuseau. Un horodatage sans fuseau — par exemple la colonne
    `Date` du CSV, qui n'en donne aucun — serait interprété dans le fuseau de la machine :
    le jour obtenu dépendrait alors de l'ordinateur qui fait tourner l'application.
    """
    if instant_utc.tzinfo is None:
        raise ValueError(
            "horodatage sans fuseau : impossible de dire à quel jour appartient l'opération"
        )
    return instant_utc.astimezone(FUSEAU_AFFICHAGE).date()


@dataclass(frozen=True)
class Operation:
    """Une ligne du format pivot. Les champs suivent `docs/format-pivot.md` §2."""

    identifiant: str
    """Identifiant de la ligne, stable d'un chargement à l'autre."""

    instant_utc: datetime
    """Date et heure exactes, en temps universel."""

    date: Date
    """Jour de l'opération en heure de Paris : sert à tout regroupement (D-36)."""

    type: TypeOperation
    nature_source: str
    """Nature d'origine (`plan_epargne`, `actions_gratuites`…). **Informative** : le moteur
    ne calcule jamais dessus."""

    actif: str
    """ISIN, ou code interne pour la crypto."""

    poche: Poche

    frais: Decimal
    """Frais réellement facturés. N'entrent jamais dans la performance (D-21)."""

    taxes: Decimal
    """Taxes réellement prélevées. N'entrent jamais dans la performance (D-21)."""

    montant_regle: Decimal
    """Montant réellement débité ou crédité, tel que la banque le donne."""

    reference_source: str
    """Identifiant de l'événement d'origine, pour remonter à la donnée brute."""

    provenance: Mapping[str, Provenance] = field(hash=False)
    """Origine de chaque champ rempli, par nom de champ.

    Exclu du calcul d'empreinte : le dictionnaire figé du `__post_init__` n'est pas
    « hachable », et sans cela une opération ne pourrait pas entrer dans un ensemble."""

    quantite: Decimal | None = None
    prix_unitaire: Decimal | None = None
    montant_brut: Decimal | None = None
    """Base de toute la performance (D-21, D-29). Vide tant qu'un prix est à compléter."""

    nom_actif: str | None = None
    """Affichage seulement, jamais un calcul (règle 4 de CLAUDE.md)."""

    devise: str = DEVISE_UNIQUE

    def __post_init__(self) -> None:
        # Le dictionnaire de provenance est figé avec l'opération : une ligne pivot ne se
        # modifie pas après coup, elle est reconstruite.
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))

    def est_a_completer(self, champ: str) -> bool:
        """Vrai si la valeur de ce champ attend encore une donnée externe (D-15)."""
        return self.provenance.get(champ) is Provenance.A_COMPLETER

    @property
    def complete(self) -> bool:
        """Vrai si aucun champ n'attend de donnée externe. Une opération incomplète est
        affichée, mais son montant brut ne compte dans aucun total."""
        return Provenance.A_COMPLETER not in self.provenance.values()
