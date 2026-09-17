"""Les exemples de `docs/format-pivot.md` §6, rendus exécutables.

**Valeurs entièrement fictives** (D-03). Ce sont les mêmes que celles du document : si le
document change, ces exemples changent avec lui, et les tests disent lequel des deux ment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from dashboard_tr.pivot.operation import (
    Operation,
    Poche,
    Provenance,
    TypeOperation,
    jour_a_paris,
)


def _instant(texte: str) -> datetime:
    """Horodatage UTC, écrit comme dans l'export : « 2026-01-02 08:00 »."""
    return datetime.strptime(texte, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def achat_plan_epargne() -> Operation:
    """Plan d'épargne mensuel de 50 €, sans frais : 2 parts à 25,00 €."""
    instant = _instant("2026-01-02 08:00")
    return Operation(
        identifiant="op-0001",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.ACHAT,
        nature_source="plan_epargne",
        actif="XX0000000001",
        nom_actif="ETF Exemple Monde (Acc)",
        poche=Poche.CTO,
        quantite=Decimal("2"),
        prix_unitaire=Decimal("25.00"),
        montant_brut=Decimal("50.00"),
        frais=Decimal("0.00"),
        taxes=Decimal("0.00"),
        montant_regle=Decimal("50.00"),
        reference_source="evenement-fictif-1",
        provenance={
            "quantite": Provenance.TEXTE,
            "prix_unitaire": Provenance.TEXTE,
            "montant_brut": Provenance.TEXTE,
            "frais": Provenance.TEXTE,
            "taxes": Provenance.DONNEE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
        },
    )


def achat_ordre_ponctuel_pea() -> Operation:
    """Ordre ponctuel dans le PEA : 10 parts à 20,00 €, 1,00 € de frais, 0,60 € de taxe."""
    instant = _instant("2026-02-10 09:30")
    return Operation(
        identifiant="op-0002",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.ACHAT,
        nature_source="ordre_ponctuel",
        actif="XX0000000002",
        nom_actif="Action Exemple SA",
        poche=Poche.PEA,
        quantite=Decimal("10"),
        prix_unitaire=Decimal("20.00"),
        montant_brut=Decimal("200.00"),
        frais=Decimal("1.00"),
        taxes=Decimal("0.60"),
        montant_regle=Decimal("201.60"),
        reference_source="evenement-fictif-2",
        provenance={
            "quantite": Provenance.TEXTE,
            "prix_unitaire": Provenance.TEXTE,
            "montant_brut": Provenance.TEXTE,
            "frais": Provenance.TEXTE,
            "taxes": Provenance.TEXTE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
        },
    )


def vente_partielle() -> Operation:
    """Vente de 5 parts à 40,00 €, 1,00 € de frais."""
    instant = _instant("2026-06-15 14:05")
    return Operation(
        identifiant="op-0003",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.VENTE,
        nature_source="ordre_ponctuel",
        actif="XX0000000002",
        nom_actif="Action Exemple SA",
        poche=Poche.PEA,
        quantite=Decimal("5"),
        prix_unitaire=Decimal("40.00"),
        montant_brut=Decimal("200.00"),
        frais=Decimal("1.00"),
        taxes=Decimal("0.00"),
        montant_regle=Decimal("199.00"),
        reference_source="evenement-fictif-3",
        provenance={
            "quantite": Provenance.TEXTE,
            "prix_unitaire": Provenance.TEXTE,
            "montant_brut": Provenance.TEXTE,
            "frais": Provenance.TEXTE,
            "taxes": Provenance.DONNEE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
        },
    )


def dividende() -> Operation:
    """Dividende de 0,50 € par action sur 10 parts : 5,00 € bruts, 1,50 € de retenue."""
    instant = _instant("2026-04-20 06:00")
    return Operation(
        identifiant="op-0004",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.DIVIDENDE,
        nature_source="dividende_especes",
        actif="XX0000000002",
        nom_actif="Action Exemple SA",
        poche=Poche.PEA,
        quantite=Decimal("10"),
        prix_unitaire=Decimal("0.50"),
        montant_brut=Decimal("5.00"),
        frais=Decimal("0.00"),
        taxes=Decimal("1.50"),
        montant_regle=Decimal("3.50"),
        reference_source="evenement-fictif-4",
        provenance={
            "quantite": Provenance.TEXTE,
            "prix_unitaire": Provenance.TEXTE,
            "montant_brut": Provenance.TEXTE,
            "frais": Provenance.DONNEE,
            "taxes": Provenance.TEXTE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
        },
    )


def distribution_capital() -> Operation:
    """Distribution de capital de 12,00 € : une part de la mise qui revient (D-14)."""
    instant = _instant("2026-05-05 06:00")
    return Operation(
        identifiant="op-0005",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.DISTRIBUTION_CAPITAL,
        nature_source="distribution_capital",
        actif="XX0000000003",
        nom_actif="Fonds Exemple",
        poche=Poche.CTO,
        quantite=Decimal("30"),
        prix_unitaire=None,
        montant_brut=Decimal("12.00"),
        frais=Decimal("0.00"),
        taxes=Decimal("0.00"),
        montant_regle=Decimal("12.00"),
        reference_source="evenement-fictif-5",
        provenance={
            "quantite": Provenance.TEXTE,
            "montant_brut": Provenance.TEXTE,
            "frais": Provenance.DONNEE,
            "taxes": Provenance.DONNEE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
            "nature_source": Provenance.TEXTE,
        },
    )


def titres_recus_prix_a_completer() -> Operation:
    """3 actions gratuites : les parts entrent, le prix attend les cours de l'étape 4 (D-15)."""
    instant = _instant("2026-03-01 07:00")
    return Operation(
        identifiant="op-0006",
        instant_utc=instant,
        date=jour_a_paris(instant),
        type=TypeOperation.TITRES_RECUS,
        nature_source="actions_gratuites",
        actif="XX0000000004",
        nom_actif="Action Exemple B",
        poche=Poche.CTO,
        quantite=Decimal("3"),
        prix_unitaire=None,
        montant_brut=None,
        frais=Decimal("0.00"),
        taxes=Decimal("0.00"),
        montant_regle=Decimal("0.00"),
        reference_source="evenement-fictif-6",
        provenance={
            "quantite": Provenance.TEXTE,
            "prix_unitaire": Provenance.A_COMPLETER,
            "montant_brut": Provenance.A_COMPLETER,
            "frais": Provenance.DONNEE,
            "taxes": Provenance.DONNEE,
            "montant_regle": Provenance.DONNEE,
            "poche": Provenance.DEDUCTION,
            "nature_source": Provenance.TEXTE,
        },
    )


TOUS_LES_EXEMPLES = (
    achat_plan_epargne,
    achat_ordre_ponctuel_pea,
    vente_partielle,
    dividende,
    distribution_capital,
    titres_recus_prix_a_completer,
)
