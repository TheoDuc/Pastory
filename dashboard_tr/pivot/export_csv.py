"""Export des opérations pivot en CSV lisible dans un tableur (format-pivot §7).

C'est **le fichier que le propriétaire ouvre pour vérifier**, ligne à ligne, en face de son
application Trade Republic. Deux choix lui sont propres :

- une colonne de provenance à côté de chaque valeur qui en porte une, pour qu'on voie d'un
  coup d'œil ce qui vient d'un champ solide et ce qui a été lu dans un texte ;
- les colonnes dans l'ordre du §2 du format.

Les conventions de tableur (point-virgule, virgule décimale, encodage attendu par Excel) sont
communes à tous les exports du projet : elles sont dans `dashboard_tr/tableur.py`.

Ce fichier contient de **vraies valeurs** : il est écrit dans le dossier personnel, hors du
dossier synchronisé, et n'entre jamais dans git (D-01, D-37).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from dashboard_tr import tableur
from dashboard_tr.pivot.operation import Operation

SEPARATEUR = tableur.SEPARATEUR

CHAMPS_AVEC_PROVENANCE = (
    "actif",
    "poche",
    "quantite",
    "prix_unitaire",
    "montant_brut",
    "frais",
    "taxes",
    "montant_regle",
)
"""Champs dont on affiche l'origine, dans une colonne « origine … » qui suit la valeur."""

VALEUR_A_COMPLETER = tableur.VALEUR_A_COMPLETER
"""Ce qu'on écrit à la place d'un montant qui attend les cours de l'étape 4 (D-15)."""

_nombre = tableur.nombre


def _colonnes() -> list[str]:
    colonnes = [
        "identifiant",
        "instant_utc",
        "date",
        "type",
        "nature_source",
        "actif",
        "nom_actif",
        "poche",
        "quantite",
        "prix_unitaire",
        "montant_brut",
        "frais",
        "taxes",
        "montant_regle",
        "devise",
        "reference_source",
    ]
    for champ in CHAMPS_AVEC_PROVENANCE:
        colonnes.insert(colonnes.index(champ) + 1, f"origine {champ}")
    return colonnes


COLONNES = _colonnes()


def _ligne(operation: Operation) -> dict[str, str]:
    valeurs: dict[str, str] = {
        "identifiant": operation.identifiant,
        "instant_utc": operation.instant_utc.isoformat(),
        "date": operation.date.isoformat(),
        "type": operation.type.value,
        "nature_source": operation.nature_source,
        "actif": operation.actif,
        "nom_actif": operation.nom_actif or "",
        "poche": operation.poche.value,
        "quantite": _nombre(operation.quantite),
        "prix_unitaire": _nombre(operation.prix_unitaire),
        "montant_brut": _nombre(operation.montant_brut),
        "frais": _nombre(operation.frais),
        "taxes": _nombre(operation.taxes),
        "montant_regle": _nombre(operation.montant_regle),
        "devise": operation.devise,
        "reference_source": operation.reference_source,
    }

    for champ in CHAMPS_AVEC_PROVENANCE:
        provenance = operation.provenance.get(champ)
        valeurs[f"origine {champ}"] = provenance.value if provenance else ""
        if operation.est_a_completer(champ):
            valeurs[champ] = VALEUR_A_COMPLETER

    return valeurs


def ecrire(operations: Iterable[Operation], fichier: Path) -> Path:
    """Écrit les opérations et renvoie le chemin du fichier produit."""
    return tableur.ecrire(COLONNES, (_ligne(operation) for operation in operations), fichier)
