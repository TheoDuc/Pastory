"""Classement de chaque événement, par liste explicite (D-08, D-11).

Quatre catégories, aucune par défaut :

| Catégorie | Ce que c'est | Ce qu'on en fait |
|---|---|---|
| `TRAITE` | une opération sur un actif | elle devient une ligne pivot |
| `HORS_PERIMETRE` | un mouvement d'espèces | écarté, mais **compté** (D-11) |
| `ECARTE` | une information, un ordre annulé | écarté, mais **compté** |
| `INCONNU` | tout le reste | **affiché à l'utilisateur** (règle 5 de CLAUDE.md) |

Deux pièges, tous deux constatés dans les exports :

- **la présence d'un montant ne dit rien.** Un plan d'épargne échoué porte un montant alors
  que rien n'a bougé ; une action gagnée n'en porte aucun alors que des titres entrent ;
- **l'absence de statut ne dit rien non plus.** Les deux seuls événements de titres reçus
  observés n'ont **pas de champ `status`**. Exiger `status == EXECUTED` les ferait
  disparaître en silence — précisément ce que le projet cherche à éviter. La règle retenue
  est donc : *un statut présent doit valoir `EXECUTED`* ; un statut absent n'est pas un refus.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

from pastory.adaptateurs.trade_republic import evenements

STATUT_EXECUTE = "EXECUTED"


class Categorie(StrEnum):
    TRAITE = auto()
    HORS_PERIMETRE = auto()
    ECARTE = auto()
    INCONNU = auto()


class Famille(StrEnum):
    """Pour un événement traité : quelle lecture lui appliquer."""

    PLAN_EPARGNE = auto()
    ORDRE_PONCTUEL = auto()
    DIVIDENDE = auto()
    VERSEMENT_NON_DIVIDENDE = auto()
    ACTION_GAGNEE = auto()
    ACTIONS_GRATUITES = auto()


TYPES_TRAITES: dict[str, Famille] = {
    "TRADING_SAVINGSPLAN_EXECUTED": Famille.PLAN_EPARGNE,
    "TRADING_TRADE_EXECUTED": Famille.ORDRE_PONCTUEL,
    "SSP_CORPORATE_ACTION_CASH": Famille.DIVIDENDE,
    "SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND": Famille.VERSEMENT_NON_DIVIDENDE,
    "GIFTING_LOTTERY_PRIZE_ACTIVITY": Famille.ACTION_GAGNEE,
    "SSP_CORPORATE_ACTION_NO_CASH": Famille.ACTIONS_GRATUITES,
}

TYPES_HORS_PERIMETRE: frozenset[str] = frozenset(
    {
        # Argent qui franchit la frontière Trade Republic
        "BANK_TRANSACTION_INCOMING",
        "CARD_TRANSACTION",
        # Mouvements entre comptes espèces
        "PEA_SAVINGS_PLAN_PAY_IN",
        "PEA_DEPOSIT_DEBIT",
        "PEA_WITHDRAWAL_CASH",
        # Revenus qui ne viennent pas d'un actif
        "INTEREST_PAYOUT",
        "CASH_PERK",
    }
)
"""Les espèces ne sont jamais suivies (D-11). Ces types sont connus et comptés, pour qu'on
puisse vérifier qu'ils ont bien été vus et volontairement laissés de côté."""

TYPES_ECARTES: frozenset[str] = frozenset(
    {
        # Documents, compte, sécurité, support
        "DOCUMENTS_ACCEPTED",
        "DOCUMENTS_CREATED",
        "CUSTOMER_CREATED",
        "SECURITIES_ACCOUNT_CREATED",
        "EMAIL_VALIDATED",
        "PIN_CHANGED",
        "PIN_RESET",
        "CSX_CHAT_ACTIVITY",
        "QUARTERLY_NET_WORTH_STATEMENT_CREATED",
        "TAX_YEAR_END_REPORT_CREATED",
        "EX_POST_COST_REPORT_CREATED",
        "CRYPTO_TNC_UPDATE_2025",
        # Annonces d'opérations sur titres : rien n'a encore eu lieu
        "SSP_CORPORATE_ACTION_INFORMATIVE",
        "SSP_CORPORATE_ACTION_UPCOMING",
        "SSP_CORPORATE_ACTION_INSTRUCTION",
        # Opérations qui n'ont pas abouti
        "TRADING_ORDER_CANCELLED",
        "TRADING_SAVINGSPLAN_EXECUTION_FAILED",
        "CARD_VERIFICATION",
    }
)

NULL_HORS_PERIMETRE: frozenset[str] = frozenset(
    {"PEA-Aktivierung", "PEA-Übertragung", "Activation PEA", "Transfert PEA"}
)
"""**Fragilité assumée** (règle 4 de CLAUDE.md). Certains événements n'ont aucun type, et la
seule chose qui les identifie est un texte allemand, la ligne « Ereignistyp ». Ce sont des
mouvements d'espèces du PEA (euro d'activation, transfert vers le compte courant), donc hors
périmètre. Un texte non listé ici reste **inconnu** : rien n'est supposé."""

NULL_ECARTE: frozenset[str] = frozenset(
    {"Rechtliche Dokumente", "Documents légaux", "Documents juridiques"}
)
"""Même fragilité, pour les événements sans type **et sans montant** : des documents."""


@dataclass(frozen=True)
class Classement:
    """Le rangement d'un événement, avec la raison quand il n'est pas traité."""

    categorie: Categorie
    type_affiche: str
    """`eventType`, ou « (sans type) ». Toujours un identifiant technique, jamais un texte
    de l'utilisateur : on peut l'écrire dans un rapport sans risque."""

    famille: Famille | None = None
    motif: str | None = None
    """Pourquoi l'événement n'est pas traité, en français, pour le rapport de lecture."""


SANS_TYPE = "(sans type)"


def _ereignistyp(evenement: dict[str, Any]) -> str | None:
    """Ligne « Ereignistyp » : la seule identification d'un événement sans type."""
    for ligne in evenements.lignes(evenement):
        if ligne.titre in ("Ereignistyp", "Type d'événement"):
            return ligne.texte
    return None


def _classer_sans_type(evenement: dict[str, Any]) -> Classement:
    """Un événement sans `eventType` ne peut être identifié que par un texte affiché.

    On ne range que ce qui est explicitement listé ; tout le reste est inconnu et affiché.
    Le transfert d'un PEA venu d'un autre établissement tombe volontairement ici : il peut
    faire entrer des titres sans qu'aucun achat n'apparaisse (limite connue de D-15).
    """
    if evenements.montant_signe(evenement) is not None:
        nature = _ereignistyp(evenement)
        if nature in NULL_HORS_PERIMETRE:
            return Classement(
                Categorie.HORS_PERIMETRE,
                SANS_TYPE,
                motif="mouvement d'espèces du PEA, identifié par son libellé seul",
            )
        return Classement(
            Categorie.INCONNU,
            SANS_TYPE,
            motif="événement sans type, portant un montant, et dont le libellé n'est pas connu",
        )

    titre = evenement.get("title")
    if isinstance(titre, str) and titre.strip() in NULL_ECARTE:
        return Classement(Categorie.ECARTE, SANS_TYPE, motif="document, identifié par son titre")

    return Classement(
        Categorie.INCONNU,
        SANS_TYPE,
        motif="événement sans type ni montant, et dont le titre n'est pas connu",
    )


def classer(evenement: dict[str, Any]) -> Classement:
    """Range un événement dans l'une des quatre catégories. Jamais de valeur par défaut."""
    type_evenement = evenements.type_evenement(evenement)

    if type_evenement is None:
        return _classer_sans_type(evenement)

    if type_evenement in TYPES_HORS_PERIMETRE:
        return Classement(
            Categorie.HORS_PERIMETRE, type_evenement, motif="ne concerne que les espèces (D-11)"
        )

    if type_evenement in TYPES_ECARTES:
        return Classement(
            Categorie.ECARTE, type_evenement, motif="ni argent ni titre ne change de main"
        )

    famille = TYPES_TRAITES.get(type_evenement)
    if famille is None:
        return Classement(
            Categorie.INCONNU,
            type_evenement,
            motif="type absent de toutes les listes : il doit être examiné avant d'être classé",
        )

    # Filet de sécurité : un type normalement exécuté qui porte un autre statut n'est pas
    # traité, mais il est signalé — il ne disparaît pas des comptages.
    statut = evenements.statut(evenement)
    if statut is not None and statut != STATUT_EXECUTE:
        return Classement(
            Categorie.ECARTE,
            type_evenement,
            motif=f"statut « {statut} » au lieu de « {STATUT_EXECUTE} » : "
            "l'opération n'a pas eu lieu",
        )

    return Classement(Categorie.TRAITE, type_evenement, famille=famille)
