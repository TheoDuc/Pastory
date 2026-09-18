"""Événements Trade Republic **entièrement fictifs**, pour les tests (D-03, D-38).

Ils reproduisent la **structure exacte** d'un export : sections imbriquées, libellés
allemands, page de détail ouverte par la ligne « Transaktion », taxe affichée avec un signe
moins, séparateur décimal différent selon l'endroit. Cette fidélité est le but : un test qui
s'appuierait sur une structure simplifiée ne prouverait rien.

Les montants sont ceux des exemples de `docs/format-pivot.md` §6, pour que la documentation
et le code se contrôlent l'un l'autre.
"""

from __future__ import annotations

from typing import Any

ACTIF_ETF = "XX0000000001"
ACTIF_ACTION = "XX0000000002"
ACTIF_FONDS = "XX0000000003"
ACTIF_ACTION_B = "XX0000000004"
ACTIF_CRYPTO = "XF000EXEMPLE01"

COMPTE_COURANT = "0000000001"
COMPTE_PEA = "0000000002"


def _ligne(titre: str, texte: str | None, action: dict[str, Any] | None = None) -> dict[str, Any]:
    detail: dict[str, Any] = {"type": "text", "text": texte}
    if action is not None:
        detail["action"] = action
    return {"title": titre, "detail": detail}


def _page_transaction(quantite: str, prix: str, brut: str) -> dict[str, Any]:
    """La page de détail ouverte par la ligne « Transaktion ».

    Ses sections n'ont pas de titre : c'est l'adaptateur qui leur en donne un, pour pouvoir
    distinguer cette quantité — écrite avec une **virgule** décimale — de celle d'un
    dividende, écrite avec un **point**.
    """
    return {
        "type": "infoPage",
        "payload": {
            "sections": [
                {"type": "title", "title": "Transaktion"},
                {
                    "type": "table",
                    "data": [
                        _ligne("Aktienkurs", prix),
                        _ligne("Aktien", quantite),
                        _ligne("Summe", brut),
                    ],
                },
            ]
        },
    }


def _entete(actif: str, titre_bandeau: str) -> dict[str, Any]:
    """L'en-tête porte l'ISIN, et un titre qui contient un montant réel dans un vrai export."""
    return {
        "type": "header",
        "title": titre_bandeau,
        "action": {"type": "instrumentDetail", "payload": actif},
        "data": ["bandeau", "sans", "libellé"],
    }


def _documents() -> dict[str, Any]:
    return {
        "type": "documents",
        "title": "Dokumente",
        "data": [_ligne("Abrechnung", None)],
    }


def _evenement(
    identifiant: str,
    type_evenement: str | None,
    horodatage: str,
    sections: list[dict[str, Any]],
    *,
    montant: float | None = None,
    compte: str | None = None,
    statut: str | None = "EXECUTED",
    icone: str = "logos/timeline_document/v2",
    titre: str | None = None,
) -> dict[str, Any]:
    evenement: dict[str, Any] = {
        "id": identifiant,
        "timestamp": horodatage,
        "eventType": type_evenement,
        "status": statut,
        "icon": icone,
        "title": titre,
        "subtitle": None,
        "details": {"sections": sections},
    }
    if montant is not None:
        evenement["amount"] = {"currency": "EUR", "value": montant}
    if compte is not None:
        evenement["cashAccountNumber"] = compte
    return evenement


# --- Achats et ventes ----------------------------------------------------------------


def plan_epargne() -> dict[str, Any]:
    """Plan d'épargne : 2 parts à 25,00 €, sans frais (« Kostenlos »)."""
    return _evenement(
        "evt-plan-1",
        "TRADING_SAVINGSPLAN_EXECUTED",
        "2026-01-02T08:00:00.000+0000",
        [
            _entete(ACTIF_ETF, "Du hast 50,00 € gespart"),
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Sparplan", "Ausgeführt"),
                    _ligne("Zahlung", "Cash"),
                    _ligne("Asset", "ETF Exemple Monde (Acc)"),
                    _ligne(
                        "Transaktion",
                        "2 × 25,00 €",
                        _page_transaction("2", "25,00 €", "50,00 €"),
                    ),
                    _ligne("Gebühr", "Kostenlos"),
                    _ligne("Summe", "50,00 €"),
                ],
            },
            _documents(),
        ],
        montant=-50.0,
        compte=COMPTE_COURANT,
        icone=f"logos/{ACTIF_ETF}/v2",
    )


def achat_pea() -> dict[str, Any]:
    """Ordre ponctuel en PEA : 10 parts à 20,00 €, 1,00 € de frais, 0,60 € de taxe."""
    return _evenement(
        "evt-achat-1",
        "TRADING_TRADE_EXECUTED",
        "2026-02-10T09:30:00.000+0000",
        [
            _entete(ACTIF_ACTION, "Du hast 201,60 € investiert"),
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Kauf", "Ausgeführt"),
                    _ligne("Portfolio", "PEA"),
                    _ligne("Asset", "Action Exemple SA"),
                    _ligne(
                        "Transaktion",
                        "10 × 20,00 €",
                        _page_transaction("10", "20,00 €", "200,00 €"),
                    ),
                    _ligne("Gebühr", "1,00 €"),
                    _ligne("Steuer", "0,60 €"),
                    _ligne("Summe", "201,60 €"),
                ],
            },
            _documents(),
        ],
        montant=-201.60,
        compte=COMPTE_PEA,
        icone=f"logos/{ACTIF_ACTION}/v2",
    )


def vente_pea() -> dict[str, Any]:
    """Vente partielle : 5 parts à 40,00 €, 1,00 € de frais, 199,00 € encaissés."""
    return _evenement(
        "evt-vente-1",
        "TRADING_TRADE_EXECUTED",
        "2026-06-15T14:05:00.000+0000",
        [
            _entete(ACTIF_ACTION, "Du hast 199,00 € erhalten"),
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Verkaufen", "Ausgeführt"),
                    _ligne("Portfolio", "PEA"),
                    _ligne("Asset", "Action Exemple SA"),
                    _ligne(
                        "Transaktion",
                        "5 × 40,00 €",
                        _page_transaction("5", "40,00 €", "200,00 €"),
                    ),
                    _ligne("Gebühr", "1,00 €"),
                    _ligne("Summe", "199,00 €"),
                ],
            },
            _documents(),
        ],
        montant=199.00,
        compte=COMPTE_PEA,
        icone=f"logos/{ACTIF_ACTION}/v2",
    )


def achat_crypto() -> dict[str, Any]:
    """Achat de crypto : quantité minuscule à six décimales, prix élevé.

    C'est le cas qui échouait aux contrôles avant la tolérance symétrique (D-39) : un
    demi-millionième de part, multiplié par des dizaines de milliers d'euros, dépasse
    largement le centime.
    """
    return _evenement(
        "evt-crypto-1",
        "TRADING_SAVINGSPLAN_EXECUTED",
        "2026-03-05T07:15:00.000+0000",
        [
            _entete(ACTIF_CRYPTO, "Du hast 25,00 € gespart"),
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Sparplan", "Ausgeführt"),
                    _ligne("Asset", "Crypto Exemple"),
                    _ligne(
                        "Transaktion",
                        "0,000833 × 30.000,00 €",
                        _page_transaction("0,000833", "30.000,00 €", "25,00 €"),
                    ),
                    _ligne("Gebühr", "Kostenlos"),
                    _ligne("Summe", "25,00 €"),
                ],
            },
        ],
        montant=-25.00,
        compte=COMPTE_COURANT,
        icone=f"logos/{ACTIF_CRYPTO}/v2",
    )


# --- Versements sur un actif ---------------------------------------------------------


def dividende() -> dict[str, Any]:
    """Dividende : 10 parts, 0,50 € par action, 1,50 € de taxe, 3,50 € reçus.

    Deux pièges réunis : la quantité est écrite avec un **point décimal**, et la taxe est
    affichée **négative**. Le brut, qui seul compte dans la performance (D-29), vaut
    3,50 + 1,50 = 5,00 €.
    """
    return _evenement(
        "evt-dividende-1",
        "SSP_CORPORATE_ACTION_CASH",
        "2026-04-20T06:00:00.000+0000",
        [
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Status", "Ausgeführt"),
                    _ligne("Event", "Bardividende"),
                    _ligne("Wertpapier", "Action Exemple SA"),
                ],
            },
            {
                "type": "table",
                "title": "Geschäft",
                "data": [
                    _ligne("Aktien", "10"),
                    _ligne("Dividende pro Aktie", "0,50 €"),
                    _ligne("Steuer", "-1,50 €"),
                    _ligne("Gesamt", "3,50 €"),
                ],
            },
        ],
        montant=3.50,
        compte=COMPTE_PEA,
        icone=f"logos/{ACTIF_ACTION}/v2",
    )


def dividende_en_devise_etrangere() -> dict[str, Any]:
    """Même dividende, mais le montant par action est affiché en dollars.

    Il n'est alors pas comparable au brut en euros : il est laissé vide plutôt que recopié.
    """
    evenement = dividende()
    evenement["id"] = "evt-dividende-2"
    for section in evenement["details"]["sections"]:
        if section.get("title") != "Geschäft":
            continue
        for ligne in section["data"]:
            if ligne["title"] == "Dividende pro Aktie":
                ligne["detail"]["text"] = "0,55 $"
    return evenement


def distribution_capital() -> dict[str, Any]:
    """Distribution de capital : 12,00 € bruts, sans taxe.

    La nature n'est écrite **que** dans le libellé « Event » : sans lui, ce type d'événement
    pourrait être tout autre chose (Q-07).
    """
    return _evenement(
        "evt-distribution-1",
        "SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND",
        "2026-05-05T06:00:00.000+0000",
        [
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Status", "Ausgeführt"),
                    _ligne("Event", "Kapitalverteilung"),
                    _ligne("Wertpapier", "Fonds Exemple"),
                ],
            },
            {
                "type": "table",
                "title": "Geschäft",
                "data": [
                    _ligne("Bruttoertrag", "12,00 €"),
                    _ligne("Gesamt", "12,00 €"),
                ],
            },
        ],
        montant=12.00,
        compte=COMPTE_COURANT,
        icone=f"logos/{ACTIF_FONDS}/v2",
    )


# --- Titres reçus sans achat ---------------------------------------------------------


def action_gagnee() -> dict[str, Any]:
    """Action gagnée : 2 parts à 10,00 €, plus un crédit en espèces hors périmètre.

    Attention au libellé « Aktien » : sous « Übersicht » c'est un **nombre de parts**, sous
    « Transaktion » c'est un **montant en euros**. Sans clé (section, libellé), l'un serait
    lu pour l'autre.
    """
    return _evenement(
        "evt-gagnee-1",
        "GIFTING_LOTTERY_PRIZE_ACTIVITY",
        "2026-07-01T10:00:00.000+0000",
        [
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Status", "Ausgeführt"),
                    _ligne("Orderart", "Kauf"),
                    _ligne("Asset", "Action Exemple B"),
                    _ligne("Aktien", "2.000000"),
                    _ligne("Aktienkurs", "10,00 €"),
                ],
            },
            {
                "type": "table",
                "title": "Transaktion",
                "data": [
                    _ligne("Aktien", "20,00 €"),
                    _ligne("Cash-Gutschrift", "5,00 €"),
                    _ligne("Summe", "25,00 €"),
                ],
            },
        ],
        statut=None,
        icone=f"logos/{ACTIF_ACTION_B}/v2",
    )


def actions_gratuites() -> dict[str, Any]:
    """Actions gratuites : 3 parts entrent, **aucun prix n'est affiché**.

    Ni montant, ni compte, ni statut : exiger l'un des trois ferait disparaître l'opération.
    """
    return _evenement(
        "evt-gratuites-1",
        "SSP_CORPORATE_ACTION_NO_CASH",
        "2026-03-01T09:00:00.000+0000",
        [
            {
                "type": "table",
                "title": "Übersicht",
                "data": [
                    _ligne("Status", "Ausgeführt"),
                    _ligne("Orderart", "Bonusaktien"),
                    _ligne("Wertpapier", "Action Exemple B"),
                    _ligne("Aktien hinzugefügt", "3.000000"),
                ],
            },
            _documents(),
        ],
        statut=None,
        icone=f"logos/{ACTIF_ACTION_B}/v2",
    )


# --- Événements qui ne produisent pas d'opération -------------------------------------


def type_inconnu() -> dict[str, Any]:
    """Un type qu'aucune liste ne connaît : il doit être affiché, jamais ignoré."""
    return _evenement(
        "evt-inconnu-1",
        "UN_TYPE_QUE_PERSONNE_N_A_JAMAIS_VU",
        "2026-08-01T10:00:00.000+0000",
        [],
        montant=-42.0,
        compte=COMPTE_COURANT,
    )


def hors_perimetre() -> dict[str, Any]:
    """Un virement reçu : connu, compté, mais hors périmètre (D-11)."""
    return _evenement(
        "evt-virement-1",
        "BANK_TRANSACTION_INCOMING",
        "2026-01-01T10:00:00.000+0000",
        [],
        montant=500.0,
        compte=COMPTE_COURANT,
    )


def ecarte() -> dict[str, Any]:
    """Un document accepté : ni argent ni titre."""
    return _evenement(
        "evt-document-1",
        "DOCUMENTS_ACCEPTED",
        "2026-01-01T09:00:00.000+0000",
        [],
        statut=None,
    )


def plan_epargne_echoue() -> dict[str, Any]:
    """Un plan d'épargne qui a échoué : il **porte un montant**, mais rien n'a bougé."""
    return _evenement(
        "evt-plan-echec-1",
        "TRADING_SAVINGSPLAN_EXECUTION_FAILED",
        "2026-02-02T08:00:00.000+0000",
        [],
        montant=-50.0,
        compte=COMPTE_COURANT,
        statut="CANCELED",
    )


def ordre_annule_avec_statut_inattendu() -> dict[str, Any]:
    """Un type normalement exécuté, mais dont le statut dit le contraire."""
    evenement = achat_pea()
    evenement["id"] = "evt-achat-annule"
    evenement["status"] = "CANCELED"
    return evenement


def libelle_non_reconnu() -> dict[str, Any]:
    """Un achat normal, avec une ligne supplémentaire que le lexique ne connaît pas."""
    evenement = plan_epargne()
    evenement["id"] = "evt-plan-libelle"
    for section in evenement["details"]["sections"]:
        if section.get("title") == "Übersicht":
            section["data"].append(_ligne("Sonderrabatt", "Ja"))
    return evenement


def export_complet() -> list[dict[str, Any]]:
    """Un export fictif contenant un cas de chaque situation."""
    return [
        plan_epargne(),
        achat_pea(),
        vente_pea(),
        achat_crypto(),
        dividende(),
        distribution_capital(),
        action_gagnee(),
        actions_gratuites(),
        type_inconnu(),
        hors_perimetre(),
        ecarte(),
        plan_epargne_echoue(),
    ]
