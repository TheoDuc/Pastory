"""Export des opérations pivot en CSV lisible dans un tableur (format-pivot §7).

C'est **le fichier que le propriétaire ouvre pour vérifier**, ligne à ligne, en face de son
application Trade Republic. Tout est donc pensé pour un tableur français :

- séparateur point-virgule et **virgule décimale**, pour qu'Excel et LibreOffice n'aillent
  pas interpréter les nombres de travers ;
- une colonne de provenance à côté de chaque valeur qui en porte une, pour qu'on voie d'un
  coup d'œil ce qui vient d'un champ solide et ce qui a été lu dans un texte ;
- les colonnes dans l'ordre du §2 du format.

Ce fichier contient de **vraies valeurs** : il est écrit dans le dossier personnel, hors du
dossier synchronisé, et n'entre jamais dans git (D-01, D-37).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path

from dashboard_tr.pivot.operation import Operation

SEPARATEUR = ";"

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

VALEUR_A_COMPLETER = "à compléter"
"""Ce qu'on écrit à la place d'un montant qui attend les cours de l'étape 4 (D-15).

Une case **vide** laisserait croire à un zéro une fois dans un tableur ; le lecteur doit
voir que la valeur manque et pourquoi."""


def _nombre(valeur: Decimal | None) -> str:
    """Un nombre pour un tableur français : virgule décimale, pas de séparateur de milliers."""
    if valeur is None:
        return ""
    return format(valeur, "f").replace(".", ",")


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
    """Écrit les opérations et renvoie le chemin du fichier produit.

    L'encodage est UTF-8 **avec BOM** : sans lui, Excel sous Windows affiche les accents de
    travers, et un fichier de vérification illisible ne sert à rien.
    """
    fichier.parent.mkdir(parents=True, exist_ok=True)

    with fichier.open("w", encoding="utf-8-sig", newline="") as flux:
        redacteur = csv.DictWriter(flux, fieldnames=COLONNES, delimiter=SEPARATEUR)
        redacteur.writeheader()
        for operation in operations:
            redacteur.writerow(_ligne(operation))

    return fichier
