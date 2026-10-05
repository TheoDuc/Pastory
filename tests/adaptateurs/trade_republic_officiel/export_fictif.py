"""Un export officiel fictif, ligne par ligne (D-03 : aucune valeur réelle).

Chaque fabrique rend une ligne **dans la forme vue sur de vrais fichiers**
(docs/export-officiel.md §4 et §5). Un test qui veut une forme jamais vue part d'une de ces
lignes et en change une colonne.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

COLONNES = (
    "datetime",
    "date",
    "account_type",
    "category",
    "type",
    "asset_class",
    "name",
    "symbol",
    "shares",
    "price",
    "amount",
    "fee",
    "tax",
    "currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "description",
    "transaction_id",
    "counterparty_name",
    "counterparty_iban",
    "payment_reference",
    "mcc_code",
)
"""La variante vue sur nos deux fichiers : virgule, guillemets, `mcc_code`."""

COLONNES_POINT_VIRGULE = tuple(
    "value_date" if colonne == "mcc_code" else colonne for colonne in COLONNES
)
"""La variante relevée chez d'autres utilisateurs : `value_date` à la place de `mcc_code`."""

ETF = "XX0000000001"
ACTION = "XX0000000002"
ACTION_DOLLARS = "XX0000000003"
CRYPTO = "XYZ"

# Ce qui ne doit jamais sortir de la lecture d'une ligne d'espèces.
COMMERCANT = "Boulangerie Fictive"
CONTREPARTIE = "Camille Fictif"
IBAN = "FR7600000000000000000000000"
MONTANT_PERSONNEL = "-4321.98"

_compteur = 0


def _identifiant() -> str:
    global _compteur
    _compteur += 1
    return f"00000000-0000-0000-0000-{_compteur:012d}"


def ligne(**champs: str) -> dict[str, str]:
    valeurs = dict.fromkeys(COLONNES, "")
    valeurs["transaction_id"] = _identifiant()
    valeurs["currency"] = "EUR"
    valeurs.update(champs)
    return valeurs


def achat_plan_epargne(**champs: str) -> dict[str, str]:
    """2 parts à 25 € en PEA, sans frais : 50 € bruts."""
    return (
        ligne(
            datetime="2026-03-02T09:15:00.123Z",
            date="2026-03-02",
            account_type="PEA",
            category="TRADING",
            type="BUY",
            asset_class="FUND",
            name="ETF Monde Fictif",
            symbol=ETF,
            shares="2.0000000000",
            price="25.0000000000",
            amount="-50.00",
            description=f"Savings plan execution {ETF}",
        )
        | champs
    )


def achat_ordre_cto(**champs: str) -> dict[str, str]:
    """4 actions à 50 € au CTO, 1 € de frais et 0,20 € de taxe : 200 € bruts."""
    return (
        ligne(
            datetime="2026-03-05T14:30:00.456789Z",
            date="2026-03-05",
            account_type="DEFAULT",
            category="TRADING",
            type="BUY",
            asset_class="STOCK",
            name="Action Fictive",
            symbol=ACTION,
            shares="4.0000000000",
            price="50.0000000000",
            amount="-200.00",
            fee="-1.00",
            tax="-0.20",
            description=f"Buy trade {ACTION} Action Fictive, quantity: 4",
        )
        | champs
    )


def vente(**champs: str) -> dict[str, str]:
    """1 action vendue 80 €, 1 € de frais."""
    return (
        ligne(
            datetime="2026-04-10T10:00:00.000Z",
            date="2026-04-10",
            account_type="DEFAULT",
            category="TRADING",
            type="SELL",
            asset_class="STOCK",
            name="Action Fictive",
            symbol=ACTION,
            shares="-1.0000000000",
            price="80.0000000000",
            amount="80.00",
            fee="-1.00",
            description=f"Sell trade {ACTION} Action Fictive, quantity: 1",
        )
        | champs
    )


def dividende(**champs: str) -> dict[str, str]:
    """10 € bruts sur 4 actions, 3 € de retenue."""
    return (
        ligne(
            datetime="2026-05-15T06:00:00.000Z",
            date="2026-05-15",
            account_type="DEFAULT",
            category="CASH",
            type="DIVIDEND",
            asset_class="STOCK",
            name="Action Fictive",
            symbol=ACTION,
            shares="4.0000000000",
            amount="10.000000",
            tax="-3.000000",
            description=f"Cash Dividend for ISIN {ACTION}",
        )
        | champs
    )


def dividende_en_dollars(**champs: str) -> dict[str, str]:
    """12 $ à 0,90 € le dollar : 10,80 € bruts, 4,86 € de retenue."""
    return (
        ligne(
            datetime="2026-05-20T06:00:00.000Z",
            date="2026-05-20",
            account_type="DEFAULT",
            category="CASH",
            type="DIVIDEND",
            asset_class="STOCK",
            name="Action Américaine Fictive",
            symbol=ACTION_DOLLARS,
            shares="10.0000000000",
            amount="10.800000",
            tax="-4.860000",
            original_amount="12.000000",
            original_currency="USD",
            fx_rate="0.900000",
            description=f"Cash Dividend for ISIN {ACTION_DOLLARS}",
        )
        | champs
    )


def distribution_capital(**champs: str) -> dict[str, str]:
    return (
        ligne(
            datetime="2026-05-15T06:00:01.000Z",
            date="2026-05-15",
            account_type="DEFAULT",
            category="CASH",
            type="DIVIDEND_EQUIVALENT_PAYMENT",
            asset_class="STOCK",
            name="Action Fictive",
            symbol=ACTION,
            shares="4.0000000000",
            amount="2.000000",
            description=f"Capital Distribution for ISIN {ACTION}",
        )
        | champs
    )


def achat_crypto(**champs: str) -> dict[str, str]:
    """0,000833 à 30 000 € : 24,99 € bruts."""
    return (
        ligne(
            datetime="2026-03-10T12:00:00.000Z",
            date="2026-03-10",
            account_type="DEFAULT",
            category="TRADING",
            type="BUY",
            asset_class="CRYPTO",
            name="Crypto Fictive",
            symbol=CRYPTO,
            shares="0.0008330000",
            price="30000.0000000000",
            amount="-24.99",
            description=f"Savings plan execution {CRYPTO}",
        )
        | champs
    )


def paiement_carte(**champs: str) -> dict[str, str]:
    """Une ligne d'espèces, avec tout ce qu'elle a de personnel."""
    return (
        ligne(
            datetime="2026-03-03T18:45:00.000Z",
            date="2026-03-03",
            account_type="DEFAULT",
            category="CASH",
            type="CARD_TRANSACTION",
            name=COMMERCANT,
            amount=MONTANT_PERSONNEL,
            description=f"Card payment at {COMMERCANT}",
            mcc_code="5462",
        )
        | champs
    )


def virement_recu(**champs: str) -> dict[str, str]:
    return (
        ligne(
            datetime="2026-03-01T08:00:00.000Z",
            date="2026-03-01",
            account_type="DEFAULT",
            category="CASH",
            type="TRANSFER_INSTANT_INBOUND",
            name=CONTREPARTIE,
            amount="1500.00",
            description=f"Incoming transfer from {CONTREPARTIE}",
            counterparty_name=CONTREPARTIE,
            counterparty_iban=IBAN,
        )
        | champs
    )


def saveback(**champs: str) -> dict[str, str]:
    return (
        ligne(
            datetime="2026-03-31T20:00:00.000Z",
            date="2026-03-31",
            account_type="DEFAULT",
            category="CASH",
            type="BENEFITS_SAVEBACK",
            asset_class="FUND",
            name="ETF Monde Fictif",
            symbol=ETF,
            amount="3.00",
            description="Saveback",
        )
        | champs
    )


def actions_gratuites(**champs: str) -> dict[str, str]:
    return (
        ligne(
            datetime="2026-06-01T05:00:00.000Z",
            date="2026-06-01",
            account_type="PEA",
            category="CORPORATE_ACTION",
            type="BONUS_ISSUE",
            asset_class="STOCK",
            name="Action Fictive",
            symbol=ACTION,
            shares="0.4000000000",
            currency="",
            description=f"BONUS_ISSUE {ACTION}",
        )
        | champs
    )


def export_type() -> list[dict[str, str]]:
    """Un export complet, **dans le désordre** comme les vrais."""
    return [
        dividende(),
        achat_plan_epargne(),
        paiement_carte(),
        vente(),
        achat_ordre_cto(),
        virement_recu(),
        achat_crypto(),
        distribution_capital(),
        saveback(),
    ]


def texte_csv(
    lignes: list[dict[str, str]], separateur: str = ",", colonnes: tuple[str, ...] = COLONNES
) -> str:
    tampon = io.StringIO()
    citation = csv.QUOTE_ALL if separateur == "," else csv.QUOTE_MINIMAL
    ecrivain = csv.writer(tampon, delimiter=separateur, quoting=citation, lineterminator="\n")
    ecrivain.writerow(colonnes)
    for valeurs in lignes:
        ecrivain.writerow([valeurs.get(colonne, "") for colonne in colonnes])
    return tampon.getvalue()


def deposer(
    dossier: Path,
    lignes: list[dict[str, str]] | None = None,
    nom: str = "Exportation de transactions.csv",
    **options,
) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / nom
    chemin.write_text(texte_csv(export_type() if lignes is None else lignes, **options), "utf-8")
    return chemin
