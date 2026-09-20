"""Le portefeuille actuel tel que Trade Republic le présente, traduit en format pivot.

`pytr portfolio` écrit un CSV d'une ligne par position détenue :

```
Name;ISIN;quantity;price;avgCost;netValue
```

Ce module le traduit en `PositionReelle` (format-pivot §9). C'est le seul endroit qui connaît
ce fichier : le moteur, lui, ne lit que le pivot (D-26).

**Deux colonnes seulement sont retenues** : l'ISIN et la quantité, qui servent de contrôle, et
le prix de revient de la banque, qui n'est qu'une information (D-46). Le cours et la valeur ne
sont pas lus : les cours du projet viendront d'une source choisie sur comparatif à l'étape 4
(D-18), et mélanger deux origines de cours rendrait les chiffres impossibles à recouper.

Le fichier est écrit **sans** `--decimal-localization` : les nombres y sont donc à point
décimal, sans séparateur de milliers. C'est un choix délibéré — le piège principal de
l'étape 2 était un export qui mélangeait deux écritures des nombres
([inventaire §11.1](../../../docs/inventaire-donnees.md)). Ici, la convention est imposée à la
source plutôt que devinée à la lecture, et une écriture qui ne la respecte pas est refusée.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dashboard_tr.pivot.position_reelle import PositionReelle

NOM_PORTEFEUILLE = "portefeuille_reel.csv"
"""Nom du fichier écrit dans le dossier personnel (D-37). Il contient de vraies données."""

SEPARATEUR = ";"

COLONNE_ACTIF = "ISIN"
COLONNE_QUANTITE = "quantity"
COLONNE_NOM = "Name"
COLONNE_PRIX_DE_REVIENT = "avgCost"

COLONNES_ATTENDUES = (COLONNE_NOM, COLONNE_ACTIF, COLONNE_QUANTITE)


class PortefeuilleIllisible(Exception):
    """Le fichier existe mais n'a pas la forme attendue."""


def chemin(dossier: Path) -> Path:
    return dossier / NOM_PORTEFEUILLE


def _nombre(texte: str) -> Decimal | None:
    """Lit un nombre à point décimal. Toute autre écriture est refusée, pas devinée."""
    texte = texte.strip()
    if not texte:
        return None
    try:
        return Decimal(texte)
    except InvalidOperation:
        return None


def lire(fichier: Path) -> tuple[list[PositionReelle], list[str]]:
    """Lit le fichier et renvoie les positions, plus les lignes qui n'ont pas pu être lues.

    Une ligne bancale n'interrompt pas la lecture et n'est pas devinée : elle est écartée et
    **dite**, pour que le rapprochement ne fasse pas croire à un actif manquant alors que
    c'est le fichier qui est abîmé.
    """
    if not fichier.exists():
        raise PortefeuilleIllisible(
            f"aucun fichier « {fichier.name} » dans {fichier.parent}.\n"
            "Lancez « dashboard positions-reelles » pour le récupérer auprès de "
            "Trade Republic."
        )

    with fichier.open(encoding="utf-8", newline="") as flux:
        lignes = list(csv.reader(flux, delimiter=SEPARATEUR))

    if not lignes:
        raise PortefeuilleIllisible(
            f"{fichier} est vide : relancez « dashboard positions-reelles »."
        )

    entete = [colonne.strip() for colonne in lignes[0]]
    manquantes = [colonne for colonne in COLONNES_ATTENDUES if colonne not in entete]
    if manquantes:
        raise PortefeuilleIllisible(
            f"{fichier} n'a pas les colonnes attendues (il manque : {', '.join(manquantes)}). "
            "Le format de pytr a peut-être changé ; relancez « dashboard positions-reelles »."
        )

    positions: list[PositionReelle] = []
    anomalies: list[str] = []

    for numero, ligne in enumerate(lignes[1:], start=2):
        valeurs = _associer(entete, ligne)
        if valeurs is None:
            anomalies.append(f"ligne {numero} : {len(ligne)} colonne(s) au lieu de {len(entete)}")
            continue

        actif = valeurs[COLONNE_ACTIF].strip()
        quantite = _nombre(valeurs[COLONNE_QUANTITE])
        if not actif:
            anomalies.append(f"ligne {numero} : aucun identifiant d'actif")
            continue
        if quantite is None:
            anomalies.append(
                f"ligne {numero} ({actif}) : quantité illisible. Attendu un nombre à point "
                "décimal, par exemple 12.5"
            )
            continue

        positions.append(
            PositionReelle(
                actif=actif,
                quantite=quantite,
                nom_actif=valeurs.get(COLONNE_NOM, "").strip() or None,
                prix_de_revient_banque=_nombre(valeurs.get(COLONNE_PRIX_DE_REVIENT, "")),
            )
        )

    return positions, anomalies


def _associer(entete: list[str], ligne: list[str]) -> dict[str, str] | None:
    """Associe chaque colonne à sa valeur, en tolérant un nom d'actif contenant un `;`.

    pytr écrit ce fichier sans jamais entourer les valeurs de guillemets : un nom de société
    qui contiendrait un point-virgule produirait une colonne de trop. Comme le nom est en
    première position et ne sert qu'à l'affichage, on recolle les morceaux plutôt que de
    perdre une position entière — mais on ne recolle **que** le nom, jamais un nombre.
    """
    if not ligne:
        return None
    if len(ligne) == len(entete):
        return dict(zip(entete, ligne, strict=True))
    if len(ligne) > len(entete) and entete[0] == COLONNE_NOM:
        surplus = len(ligne) - len(entete)
        recollee = [SEPARATEUR.join(ligne[: surplus + 1]), *ligne[surplus + 1 :]]
        return dict(zip(entete, recollee, strict=True))
    return None
