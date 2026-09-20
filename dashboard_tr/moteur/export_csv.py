"""Les deux fichiers que le propriétaire ouvre pour vérifier les calculs du moteur.

| Fichier | Une ligne par | À quoi il sert |
|---|---|---|
| `positions.csv` | actif dans une poche | comparer quantité et capital avec l'app de la banque |
| `journal.csv` | opération | **refaire un chiffre à la main**, de l'achat au total |

Le journal est le plus important des deux. Il se lit comme un relevé bancaire : on part de
l'état d'avant, on applique l'opération, on tombe sur l'état d'après. C'est ce qui permet de
répondre à « d'où sort ce prix de revient ? » sans lire une ligne de code (D-44).

Les positions sont rangées par poche puis par actif, et les lignes du journal **restent
groupées par actif**, dans l'ordre du temps : un actif se suit d'un bout à l'autre sans avoir
à trier le fichier soi-même.

Ces fichiers contiennent de vraies valeurs : ils sont écrits dans le dossier personnel, hors
du dossier synchronisé, et n'entrent jamais dans git (D-01, D-37).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from decimal import Decimal
from pathlib import Path

from dashboard_tr import tableur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.position import EtatPosition, LigneJournal, Position

NOM_POSITIONS = "positions.csv"
NOM_JOURNAL = "journal.csv"

COLONNES_POSITIONS = (
    "poche",
    "actif",
    "nom_actif",
    "quantite_detenue",
    "capital_net_investi",
    "prix_de_revient",
    "remarque",
    "achats_bruts",
    "ventes_brutes",
    "plus_values_realisees_brutes",
    "plus_values_realisees_nettes",
    "dividendes_bruts",
    "distributions_capital",
    "frais",
    "taxes",
    "dont taxes sur dividendes",
)

COLONNES_JOURNAL = (
    "poche",
    "actif",
    "nom_actif",
    "date",
    "type",
    "quantite",
    "prix_unitaire",
    "montant_brut",
    "frais",
    "taxes",
    "quantite_avant",
    "quantite_apres",
    "capital_avant",
    "capital_ajoute",
    "capital_retire",
    "capital_apres",
    "prix_de_revient_apres",
    "plus_value_brute",
    "plus_value_nette",
    "remarque",
    "identifiant",
    "reference_source",
)


def remarque(etat: EtatPosition) -> str:
    """Ce qui empêche de se fier aux chiffres de cette position, en clair (D-45).

    Vide quand tout va bien : une colonne vide se repère mieux qu'un « non » répété partout.
    """
    raisons = []
    if etat.prix_inconnu:
        raisons.append("des parts sont entrées sans prix connu : capital sous-estimé")
    if etat.stock_insuffisant:
        raisons.append("une vente a dépassé le stock compté : il manque une entrée de titres")
    if etat.distribution_excedentaire:
        raisons.append(
            "une distribution a dépassé le capital investi : le capital s'est arrêté à zéro, "
            "d'où un montant distribué supérieur au capital retiré"
        )
    return " ; ".join(raisons)


def _prix_de_revient(etat: EtatPosition) -> str:
    """Le prix de revient, ou la raison pour laquelle il n'y en a pas.

    Deux absences différentes, écrites différemment : « à compléter » quand le chiffre
    viendra (les cours de l'étape 4), un tiret quand il n'a tout simplement pas de sens
    parce qu'on ne détient plus rien.
    """
    prix = etat.prix_de_revient
    if prix is not None:
        return tableur.nombre(prix)
    if etat.historique_incomplet:
        return tableur.VALEUR_A_COMPLETER
    return tableur.VALEUR_SANS_OBJET


def _ligne_position(position: Position) -> dict[str, str]:
    etat = position.etat
    return {
        "poche": position.poche.value,
        "actif": position.actif,
        "nom_actif": position.nom_actif or "",
        "quantite_detenue": tableur.nombre(etat.quantite),
        "capital_net_investi": tableur.nombre(etat.capital_net_investi),
        "prix_de_revient": _prix_de_revient(etat),
        "remarque": remarque(etat),
        "achats_bruts": tableur.nombre(position.achats_bruts),
        "ventes_brutes": tableur.nombre(position.ventes_brutes),
        "plus_values_realisees_brutes": tableur.nombre(position.plus_values_realisees_brutes),
        "plus_values_realisees_nettes": tableur.nombre(position.plus_values_realisees_nettes),
        "dividendes_bruts": tableur.nombre(position.dividendes_bruts),
        "distributions_capital": tableur.nombre(position.distributions_capital),
        "frais": tableur.nombre(position.frais),
        "taxes": tableur.nombre(position.taxes),
        "dont taxes sur dividendes": tableur.nombre(position.dividendes_taxes),
    }


def _montant_du_pivot(valeur: Decimal | None, operation_a_completer: bool) -> str:
    """Un montant du pivot, en disant s'il attend encore une donnée externe (D-15)."""
    if valeur is not None:
        return tableur.nombre(valeur)
    return tableur.VALEUR_A_COMPLETER if operation_a_completer else ""


def _ligne_journal(position: Position, ligne: LigneJournal) -> dict[str, str]:
    operation = ligne.operation
    a_completer = operation.est_a_completer("montant_brut")
    return {
        "poche": position.poche.value,
        "actif": position.actif,
        "nom_actif": position.nom_actif or "",
        "date": operation.date.isoformat(),
        "type": operation.type.value,
        "quantite": tableur.nombre(operation.quantite),
        "prix_unitaire": _montant_du_pivot(
            operation.prix_unitaire, operation.est_a_completer("prix_unitaire")
        ),
        "montant_brut": _montant_du_pivot(operation.montant_brut, a_completer),
        "frais": tableur.nombre(operation.frais),
        "taxes": tableur.nombre(operation.taxes),
        "quantite_avant": tableur.nombre(ligne.avant.quantite),
        "quantite_apres": tableur.nombre(ligne.apres.quantite),
        "capital_avant": tableur.nombre(ligne.avant.capital_net_investi),
        "capital_ajoute": tableur.nombre(ligne.capital_ajoute),
        "capital_retire": tableur.nombre(ligne.capital_retire),
        "capital_apres": tableur.nombre(ligne.apres.capital_net_investi),
        "prix_de_revient_apres": _prix_de_revient(ligne.apres),
        "plus_value_brute": tableur.nombre(
            ligne.plus_value_brute, absent=tableur.VALEUR_SANS_OBJET
        ),
        "plus_value_nette": tableur.nombre(
            ligne.plus_value_nette, absent=tableur.VALEUR_SANS_OBJET
        ),
        "remarque": remarque(ligne.apres),
        "identifiant": operation.identifiant,
        "reference_source": operation.reference_source,
    }


def _lignes_du_journal(positions: Iterable[Position]) -> Iterator[Mapping[str, str]]:
    for position in positions:
        for ligne in position.journal:
            yield _ligne_journal(position, ligne)


def ecrire_positions(portefeuille: Portefeuille, fichier: Path) -> Path:
    """Écrit `positions.csv`. **Toutes** les positions y sont, y compris celles soldées.

    Une position entièrement vendue vaut zéro aujourd'hui, mais elle a produit des
    plus-values, des frais et des dividendes qui comptent dans les totaux : la faire
    disparaître du fichier rendrait ces totaux impossibles à refaire.
    """
    return tableur.ecrire(
        COLONNES_POSITIONS,
        (_ligne_position(position) for position in portefeuille.positions),
        fichier,
    )


def ecrire_journal(portefeuille: Portefeuille, fichier: Path) -> Path:
    """Écrit `journal.csv` : une ligne par opération, groupée par actif puis dans le temps."""
    return tableur.ecrire(
        COLONNES_JOURNAL, _lignes_du_journal(portefeuille.positions), fichier
    )
