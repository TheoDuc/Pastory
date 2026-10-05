"""Classement de chaque ligne de l'export, par liste explicite (D-08, règle 5 de CLAUDE.md).

Trois catégories, aucune par défaut :

| Catégorie | Ce que c'est | Ce qu'on en fait |
|---|---|---|
| `TRAITE` | une opération sur un actif | elle devient une ligne pivot |
| `HORS_PERIMETRE` | un mouvement d'espèces | écarté, mais **compté par type** (D-11) |
| `INCONNU` | tout le reste | **affiché à l'utilisateur**, avec la raison |

**Aucune liste des types n'est publiée par Trade Republic** (D-79). Un couple
`(category, type)` n'est donc traité que s'il a été vu sur un vrai fichier, et comparé
(docs/export-officiel.md §4.1). Ceux que d'autres logiciels citent sans qu'on les ait vus
(§4.2) restent inconnus : c'est ainsi qu'on évite de ranger un brut à la place d'un net.

Le classement ne regarde que des **codes** (`category`, `type`), jamais un libellé.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto

from pastory.adaptateurs.trade_republic.fichier import Ligne
from pastory.pivot.operation import TypeOperation


class Categorie(StrEnum):
    TRAITE = auto()
    HORS_PERIMETRE = auto()
    INCONNU = auto()


TYPES_TRAITES: dict[tuple[str, str], TypeOperation] = {
    ("TRADING", "BUY"): TypeOperation.ACHAT,
    ("TRADING", "SELL"): TypeOperation.VENTE,
    # Le dividende est rangé par la banque dans les espèces, mais il désigne un actif.
    ("CASH", "DIVIDEND"): TypeOperation.DIVIDENDE,
    # « Capital Distribution » : versée le même jour qu'un dividende du même titre, et
    # identique, sur le seul cas vu, à la distribution de capital que lisait pytr (D-14).
    # Le code, lui, dit « équivalent de dividende » : la lecture exige donc en plus que la
    # description l'annonce comme une distribution de capital (Q-07, et lecture.py).
    ("CASH", "DIVIDEND_EQUIVALENT_PAYMENT"): TypeOperation.DISTRIBUTION_CAPITAL,
}

TYPES_HORS_PERIMETRE: frozenset[tuple[str, str]] = frozenset(
    ("CASH", type_especes)
    for type_especes in (
        # Paiements par carte
        "CARD_TRANSACTION",
        "CARD_TRANSACTION_INTERNATIONAL",
        # Virements reçus
        "TRANSFER_INBOUND",
        "TRANSFER_INSTANT_INBOUND",
        # Mouvements d'argent, dont les versements et retraits du PEA
        "TRANSFER_IN",
        "TRANSFER_OUT",
        # Revenus et crédits qui ne viennent pas d'un actif
        "PEA_MARKETING",
        "INTEREST_PAYMENT",
        "GIFT",
        "MANUAL",
        "MANUAL_CASH_TRANSFER",
    )
)
"""Les espèces ne sont jamais suivies (D-11). Ces types ont tous été vus sur un vrai fichier,
**sans** actif. Ils sont comptés, pour qu'on puisse vérifier qu'ils ont bien été vus et
volontairement laissés de côté."""

TYPES_EN_ATTENTE: dict[tuple[str, str], str] = {
    ("CASH", "BENEFITS_SAVEBACK"): (
        "Saveback : un montant crédité, sans quantité ni prix. Les parts arrivent "
        "normalement par un achat séparé, quelques jours plus tard : à confirmer sur un "
        "export plus récent"
    ),
    ("CORPORATE_ACTION", "BONUS_ISSUE"): (
        "actions gratuites : sur le seul cas vu, une « migration » retire ensuite les mêmes "
        "parts. Les traiter seules fausserait la quantité (Q-54)"
    ),
    ("DELIVERY", "MIGRATION"): (
        "« migration » : des parts sortent, sans montant. Sur le seul cas vu, elle retire "
        "des actions gratuites reçues un mois plus tôt (Q-54)"
    ),
}
"""Vus sur un vrai fichier, mais pas encore compris : affichés avec ce qu'on en sait."""

MOTIF_INCONNU = "jamais vu sur un vrai fichier : il peut concerner vos actifs"

MOTIF_ESPECES_AVEC_ACTIF = (
    "une ligne d'espèces qui désigne un actif (code ou quantité) : elle peut faire entrer ou "
    "sortir des parts"
)


@dataclass(frozen=True)
class Classement:
    """Le rangement d'une ligne, avec la raison quand elle n'est pas traitée."""

    categorie: Categorie
    type_affiche: str
    """`CATEGORY/TYPE` : toujours des codes de la banque, jamais un texte de l'utilisateur.
    On peut l'écrire dans un rapport sans risque."""

    type_operation: TypeOperation | None = None
    motif: str | None = None
    """Pourquoi la ligne n'est pas traitée, en français, pour le rapport de lecture."""


LONGUEUR_MAXIMALE_D_UN_CODE = 40


def code_affichable(texte: str) -> str:
    """Un code de la banque commence par une majuscule, et n'est fait que de majuscules, de
    chiffres et de soulignés. Tout autre texte est masqué : la colonne pourrait contenir
    autre chose qu'un code — un nom, un montant."""
    if (
        texte
        and len(texte) <= LONGUEUR_MAXIMALE_D_UN_CODE
        and texte[0].isascii()
        and texte[0].isupper()
        and all(c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in texte)
    ):
        return texte
    return "(illisible)" if texte else "(vide)"


def classer(ligne: Ligne) -> Classement:
    cle = (ligne.category, ligne.type)
    affiche = f"{code_affichable(ligne.category)}/{code_affichable(ligne.type)}"

    if cle in TYPES_TRAITES:
        return Classement(Categorie.TRAITE, affiche, type_operation=TYPES_TRAITES[cle])
    if cle in TYPES_HORS_PERIMETRE:
        if ligne.designe_un_actif:
            return Classement(Categorie.INCONNU, affiche, motif=MOTIF_ESPECES_AVEC_ACTIF)
        return Classement(Categorie.HORS_PERIMETRE, affiche)
    if cle in TYPES_EN_ATTENTE:
        return Classement(Categorie.INCONNU, affiche, motif=TYPES_EN_ATTENTE[cle])
    return Classement(Categorie.INCONNU, affiche, motif=MOTIF_INCONNU)
