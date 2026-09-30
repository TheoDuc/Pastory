"""Accès bas niveau à un événement de `all_events.json`.

Ce module ne décide de rien : il sait seulement **où** est rangée chaque information dans la
structure de l'export, et laisse `lecture.py` décider de ce qu'elle veut dire.

Deux particularités de l'export justifient qu'il existe :

1. **Le même libellé ne désigne pas la même chose selon sa section.** Sur une action gagnée,
   `Aktien` est un nombre de parts sous « Übersicht » et un montant en euros sous
   « Transaktion ». Toute lecture passe donc par un couple (section, libellé), jamais par un
   libellé seul.
2. **Le titre d'une section peut contenir un montant réel** (le bandeau « Du hast … gespart »).
   Aucun titre de section n'est donc recopié tel quel dans un message ; `rapport.sur()` s'en
   charge.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

SECTION_APERCU = "Übersicht"
"""Section principale : nature de l'opération, actif, frais, total."""

SECTION_AFFAIRE = "Geschäft"
"""Section des dividendes et des distributions : parts, montant par action, taxe, total."""

SECTION_TRANSACTION = "Transaktion"
"""Section « Transaktion » d'une action gagnée : le détail en euros de ce qui a été reçu."""


def section_detaillee(titre_ligne: str) -> str:
    """Nom donné à la page de détail attachée à une ligne.

    La ligne « Transaktion » d'un achat cache une page qui porte la quantité, le prix et le
    **montant brut**. Cette page a ses propres sections, dont le titre est vide : on lui en
    fabrique un, pour que le lexique puisse la désigner sans ambiguïté.
    """
    return f"{titre_ligne} ⤷ détail"


@dataclass(frozen=True)
class Ligne:
    """Une ligne de détail, avec la section où elle a été trouvée."""

    section: str | None
    titre: str
    texte: str | None


def _sections(evenement: dict[str, Any]) -> list[dict[str, Any]]:
    brutes = (evenement.get("details") or {}).get("sections") or []
    return [s for s in brutes if isinstance(s, dict)]


def _texte(detail: Any) -> str | None:
    if isinstance(detail, dict):
        texte = detail.get("text")
        return texte if isinstance(texte, str) else None
    return detail if isinstance(detail, str) else None


def _page_imbriquee(detail: Any) -> list[dict[str, Any]]:
    """Sections de la page de détail ouverte par une ligne, s'il y en a une."""
    if not isinstance(detail, dict):
        return []
    charge = (detail.get("action") or {}).get("payload")
    if not isinstance(charge, dict):
        return []
    return [s for s in charge.get("sections") or [] if isinstance(s, dict)]


def lignes(evenement: dict[str, Any]) -> Iterator[Ligne]:
    """Toutes les lignes de détail, **pages imbriquées comprises**.

    Les lignes sans titre (boutons, documents, bandeaux) sont ignorées : elles ne portent
    aucune information chiffrée.
    """
    for section in _sections(evenement):
        titre_section = section.get("title")
        titre_section = titre_section if isinstance(titre_section, str) else None

        for donnee in section.get("data") or []:
            if not isinstance(donnee, dict):
                continue
            titre = donnee.get("title")
            if not isinstance(titre, str) or not titre:
                continue

            detail = donnee.get("detail")
            yield Ligne(titre_section, titre, _texte(detail))

            for sous_section in _page_imbriquee(detail):
                for sous_donnee in sous_section.get("data") or []:
                    if not isinstance(sous_donnee, dict):
                        continue
                    sous_titre = sous_donnee.get("title")
                    if not isinstance(sous_titre, str) or not sous_titre:
                        continue
                    yield Ligne(
                        section_detaillee(titre),
                        sous_titre,
                        _texte(sous_donnee.get("detail")),
                    )


def texte_de(evenement: dict[str, Any], section: str | None, titre: str) -> str | None:
    """Texte d'une ligne précise, ou `None` si elle est absente."""
    for ligne in lignes(evenement):
        if ligne.section == section and ligne.titre == titre:
            return ligne.texte
    return None


def titres_de_section(evenement: dict[str, Any], section: str | None) -> list[str]:
    """Titres des lignes d'une section, dans l'ordre.

    Utile parce que Trade Republic range parfois l'information **dans le titre** : la
    première ligne de « Übersicht » d'un ordre s'appelle `Kauf`, `Verkaufen` ou
    `Stop Order`, et sa valeur est le statut. Le libellé est alors la donnée.
    """
    return [ligne.titre for ligne in lignes(evenement) if ligne.section == section]


# --- Champs structurés : les seuls solides (D-09) ---------------------------------

_ISIN_DANS_ICONE = re.compile(r"logos/([A-Z0-9]{12})(?:/|$)")


def identifiant(evenement: dict[str, Any]) -> str | None:
    valeur = evenement.get("id")
    return valeur if isinstance(valeur, str) else None


def type_evenement(evenement: dict[str, Any]) -> str | None:
    valeur = evenement.get("eventType")
    return valeur if isinstance(valeur, str) else None


def statut(evenement: dict[str, Any]) -> str | None:
    valeur = evenement.get("status")
    return valeur if isinstance(valeur, str) else None


def compte(evenement: dict[str, Any]) -> str | None:
    """Numéro de compte espèces. Il ne sort jamais de l'adaptateur (format-pivot §2)."""
    valeur = evenement.get("cashAccountNumber")
    return valeur if isinstance(valeur, str) else None


def horodatage(evenement: dict[str, Any]) -> datetime | None:
    """Instant de l'opération, **avec son fuseau**.

    Un horodatage sans fuseau est refusé plus haut par `jour_a_paris` (D-36) : deux machines
    ne doivent pas ranger la même opération dans deux journées différentes.
    """
    valeur = evenement.get("timestamp")
    if not isinstance(valeur, str):
        return None
    try:
        return datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        return None


def montant_signe(evenement: dict[str, Any]) -> Decimal | None:
    """Montant tel que la banque le donne : négatif si l'argent sort, positif s'il entre.

    C'est **le seul indicateur structuré du sens d'un ordre** : négatif = achat,
    positif = vente. Le libellé « Kauf » / « Verkaufen » ne sert qu'à le recouper.
    """
    montant = evenement.get("amount")
    if not isinstance(montant, dict):
        return None
    valeur = montant.get("value")
    if valeur is None:
        return None
    try:
        # Passage par le texte : `Decimal(float)` reprendrait l'écart du flottant produit
        # par la lecture du JSON, exactement ce que `Decimal` est là pour éviter (D-33).
        return Decimal(str(valeur))
    except (InvalidOperation, ValueError):
        return None


def devise(evenement: dict[str, Any]) -> str | None:
    montant = evenement.get("amount")
    if not isinstance(montant, dict):
        return None
    valeur = montant.get("currency")
    return valeur if isinstance(valeur, str) else None


def isin_entete(evenement: dict[str, Any]) -> str | None:
    """ISIN de l'en-tête (`instrumentDetail`) : présent sur les ordres et les plans."""
    for section in _sections(evenement):
        action = section.get("action")
        if isinstance(action, dict) and action.get("type") == "instrumentDetail":
            charge = action.get("payload")
            if isinstance(charge, str):
                return charge
    return None


def isin_icone(evenement: dict[str, Any]) -> str | None:
    """ISIN lu dans le chemin de l'icône (`logos/<ISIN>/v2`).

    C'est un **détournement d'un chemin d'image**, mais c'est la seule source pour les
    dividendes et les titres reçus. La valeur qui en vient est marquée en conséquence.
    """
    icone = evenement.get("icon")
    if not isinstance(icone, str):
        return None
    trouve = _ISIN_DANS_ICONE.search(icone)
    return trouve.group(1) if trouve else None
