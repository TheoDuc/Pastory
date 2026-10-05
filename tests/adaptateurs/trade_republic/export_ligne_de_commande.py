"""L'export fictif sur lequel tournent les tests de la ligne de commande (D-03).

C'est un vrai fichier « Export des transactions », au format officiel. Il reprend les actifs,
les dates et les montants de l'ancien export pytr fictif, pour que les chiffres attendus par
les tests du moteur, des cours et des coûts n'aient pas bougé en changeant de porte d'entrée.

**Ce que l'export officiel ne produit pas encore : des titres reçus.** Les actions gratuites
et l'action gagnée y sont des types non traités (`BONUS_ISSUE`, Q-54 ; `STOCKPERK`, jamais vu
sur un vrai fichier). Or la complétion de leur prix par le cours du jour (D-15) reste un
trajet de l'application. `titres_recus()` donne donc, **à part**, les deux opérations que
l'ancien export en tirait : les tests de la ligne de commande les ajoutent à la lecture, en
le disant, et des tests à part vérifient la lecture pure.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pastory.pivot.operation import Operation, Poche, Provenance, TypeOperation
from tests.adaptateurs.trade_republic import export_fictif

ACTIF_ETF = "XX0000000001"
ACTIF_ACTION = "XX0000000002"
ACTIF_FONDS = "XX0000000003"
ACTIF_ACTION_B = "XX0000000004"
ACTIF_CRYPTO = "BTC"

TYPE_INCONNU = "UN_TYPE_QUE_PERSONNE_N_A_JAMAIS_VU"

NOMBRE_DE_LIGNES = 11
OPERATIONS_LUES = 6
"""Ce que l'adaptateur produit seul. Avec les deux titres reçus ajoutés : 8."""


def _ligne(identifiant: str, **colonnes: str) -> dict[str, str]:
    return export_fictif.ligne(transaction_id=f"evt-{identifiant}", **colonnes)


def lignes() -> list[dict[str, str]]:
    """Une ligne de chaque situation, dans le désordre comme les vrais fichiers."""
    return [
        _ligne(
            "vente-1",
            datetime="2026-06-15T14:05:00.000Z",
            date="2026-06-15",
            account_type="PEA",
            category="TRADING",
            type="SELL",
            asset_class="STOCK",
            name="Action Exemple SA",
            symbol=ACTIF_ACTION,
            shares="-5",
            price="40.00",
            amount="200.00",
            fee="-1.00",
            description=f"Sell trade {ACTIF_ACTION} Action Exemple SA, quantity: 5",
        ),
        _ligne(
            "plan-1",
            datetime="2026-01-02T08:00:00.000Z",
            date="2026-01-02",
            account_type="DEFAULT",
            category="TRADING",
            type="BUY",
            asset_class="FUND",
            name="ETF Exemple Monde (Acc)",
            symbol=ACTIF_ETF,
            shares="2",
            price="25.00",
            amount="-50.00",
            description=f"Savings plan execution {ACTIF_ETF} ETF Exemple Monde (Acc)",
        ),
        _ligne(
            "carte-1",
            datetime="2026-01-15T18:00:00.000Z",
            date="2026-01-15",
            account_type="DEFAULT",
            category="CASH",
            type="CARD_TRANSACTION",
            name=export_fictif.COMMERCANT,
            amount=export_fictif.MONTANT_PERSONNEL,
            description=f"Card payment at {export_fictif.COMMERCANT}",
        ),
        _ligne(
            "achat-1",
            datetime="2026-02-10T09:30:00.000Z",
            date="2026-02-10",
            account_type="PEA",
            category="TRADING",
            type="BUY",
            asset_class="STOCK",
            name="Action Exemple SA",
            symbol=ACTIF_ACTION,
            shares="10",
            price="20.00",
            amount="-200.00",
            fee="-1.00",
            tax="-0.60",
            description=f"Buy trade {ACTIF_ACTION} Action Exemple SA, quantity: 10",
        ),
        _ligne(
            "versement-pea-1",
            datetime="2026-02-09T10:00:00.000Z",
            date="2026-02-09",
            account_type="PEA",
            category="CASH",
            type="TRANSFER_IN",
            amount="201.60",
            description="PEA deposit",
        ),
        _ligne(
            "gratuites-1",
            datetime="2026-03-01T09:00:00.000Z",
            date="2026-03-01",
            account_type="DEFAULT",
            category="CORPORATE_ACTION",
            type="BONUS_ISSUE",
            asset_class="STOCK",
            name="Action Exemple B",
            symbol=ACTIF_ACTION_B,
            shares="3",
            currency="",
            description=f"BONUS_ISSUE {ACTIF_ACTION_B}",
        ),
        _ligne(
            "crypto-1",
            datetime="2026-03-05T07:15:00.000Z",
            date="2026-03-05",
            account_type="DEFAULT",
            category="TRADING",
            type="BUY",
            asset_class="CRYPTO",
            name="Crypto Exemple",
            symbol=ACTIF_CRYPTO,
            # 0,000833 × 30 000 = 24,99 € : à un centime des 25 € débités, dans la tolérance
            # du contrôle « quantité × prix » (format-pivot §5), comme sur l'ancien export.
            shares="0.000833",
            price="30000.00",
            amount="-25.00",
            description=f"Savings plan execution {ACTIF_CRYPTO}",
        ),
        _ligne(
            "dividende-1",
            datetime="2026-04-20T06:00:00.000Z",
            date="2026-04-20",
            account_type="PEA",
            category="CASH",
            type="DIVIDEND",
            asset_class="STOCK",
            name="Action Exemple SA",
            symbol=ACTIF_ACTION,
            shares="10",
            amount="5.00",
            tax="-1.50",
            description=f"Cash Dividend for ISIN {ACTIF_ACTION}",
        ),
        _ligne(
            "distribution-1",
            datetime="2026-05-05T06:00:00.000Z",
            date="2026-05-05",
            account_type="DEFAULT",
            category="CASH",
            type="DIVIDEND_EQUIVALENT_PAYMENT",
            asset_class="FUND",
            name="Fonds Exemple",
            symbol=ACTIF_FONDS,
            shares="4",
            amount="12.00",
            description=f"Capital Distribution for ISIN {ACTIF_FONDS}",
        ),
        _ligne(
            "gagnee-1",
            datetime="2026-07-01T10:00:00.000Z",
            date="2026-07-01",
            account_type="DEFAULT",
            category="CASH",
            type="STOCKPERK",
            asset_class="STOCK",
            name="Action Exemple B",
            symbol=ACTIF_ACTION_B,
            amount="20.00",
            description="Stockperk",
        ),
        _ligne(
            "inconnu-1",
            datetime="2026-08-01T10:00:00.000Z",
            date="2026-08-01",
            account_type="DEFAULT",
            category="CASH",
            type=TYPE_INCONNU,
            symbol=ACTIF_ACTION,
            description="Something new",
        ),
    ]


def deposer(dossier: Path) -> Path:
    export_fictif.deposer(dossier, lignes())
    return dossier


def _titres_recus(
    reference: str,
    instant: datetime,
    nature: str,
    quantite: str,
    prix: str | None,
) -> Operation:
    provenance = {
        "actif": Provenance.DONNEE,
        "poche": Provenance.DONNEE,
        "frais": Provenance.DONNEE,
        "taxes": Provenance.DONNEE,
        "quantite": Provenance.DONNEE,
    }
    if prix is None:
        provenance["prix_unitaire"] = Provenance.A_COMPLETER
        provenance["montant_brut"] = Provenance.A_COMPLETER
    else:
        provenance["prix_unitaire"] = Provenance.DONNEE
        provenance["montant_brut"] = Provenance.DONNEE
    return Operation(
        identifiant=f"tr-{reference}",
        instant_utc=instant,
        date=instant.date(),
        type=TypeOperation.TITRES_RECUS,
        nature_source=nature,
        actif=ACTIF_ACTION_B,
        nom_actif="Action Exemple B",
        poche=Poche.CTO,
        quantite=Decimal(quantite),
        prix_unitaire=Decimal(prix) if prix is not None else None,
        montant_brut=Decimal(quantite) * Decimal(prix) if prix is not None else None,
        frais=Decimal("0"),
        taxes=Decimal("0"),
        montant_regle=None,
        reference_source=reference,
        provenance=provenance,
    )


def titres_recus() -> list[Operation]:
    """Les deux opérations que donnera le traitement des titres reçus (Q-54).

    3 actions gratuites le dimanche 1er mars, **sans prix** : le cours du jour les complétera
    (D-15). 2 actions gagnées le 1er juillet, à 10 € : 20 €.
    """
    return [
        _titres_recus(
            "evt-gratuites-1",
            datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
            "actions_gratuites",
            "3",
            None,
        ),
        _titres_recus(
            "evt-gagnee-1",
            datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            "action_gagnee",
            "2",
            "10.00",
        ),
    ]
