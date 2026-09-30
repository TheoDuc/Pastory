"""Recoupement des opérations avec `account_transactions.csv` (D-06, D-42).

Le CSV **n'est pas une source** : il omet des opérations et en déforme d'autres
(inventaire §8). Mais il donne la quantité, les frais et les taxes sous forme de **nombres
déjà convertis**, là où l'adaptateur doit les lire dans des textes en allemand. C'est donc
un second avis indépendant sur la partie la plus fragile de la lecture.

Ce recoupement aurait attrapé tout seul le piège du séparateur décimal : une quantité lue
un million de fois trop grande n'aurait pas correspondu à la colonne `Parts`.

**Ce que le CSV ne peut pas faire.** Sa colonne `Date` ne porte **aucun fuseau horaire**.
Elle n'est donc jamais utilisée pour décider à quel jour appartient une opération — c'est
l'horodatage du JSON qui le dit (D-36). Elle ne sert qu'à **rapprocher** une ligne d'une
opération, et ce rapprochement est exact : lue en temps universel, elle retombe à la seconde
près sur l'horodatage de l'événement correspondant.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pastory.adaptateurs.trade_republic.nombres import (
    Convention,
    LectureImpossible,
    lire_nombre,
)
from pastory.adaptateurs.trade_republic.rapport import Rapport
from pastory.pivot.operation import Operation, TypeOperation

SEPARATEUR = ";"

COLONNE_DATE = "Date"
COLONNE_TYPE = "Type"
COLONNE_ISIN = "ISIN"
COLONNE_PARTS = "Parts"
COLONNE_FRAIS = "Frais"
COLONNE_TAXES = "Impôts / Taxes"

TYPES_CSV: dict[str, TypeOperation] = {
    "Achat": TypeOperation.ACHAT,
    "Vente": TypeOperation.VENTE,
    "Dividendes": TypeOperation.DIVIDENDE,
    "SPLIT": TypeOperation.TITRES_RECUS,
}
"""Types du CSV qui correspondent à une opération du pivot.

`SPLIT` est le libellé trompeur que le CSV donne aux **actions gratuites** : ce n'est pas
une division d'action (inventaire §8). Les autres types (`Dépôt`, `Retrait`, `Intérêts`) ne
concernent que les espèces, donc rien de ce que l'application suit (D-11)."""

ABSENCES_ATTENDUES: dict[TypeOperation, str] = {
    TypeOperation.DISTRIBUTION_CAPITAL: (
        "le CSV range une distribution de capital parmi les « Dépôt », "
        "sans ISIN : elle n'y est pas rapprochable"
    ),
}
"""Absences déjà constatées et expliquées : elles ne sont pas des alertes.

Une action gagnée est absente elle aussi, mais rien ne la distingue d'une action gratuite
une fois dans le pivot : le cas est traité à part, sur la nature d'origine."""

NATURE_ABSENTE_DU_CSV = "action_gagnee"
"""Une action gagnée n'apparaît nulle part dans le CSV (inventaire §8)."""


@dataclass(frozen=True)
class LigneCsv:
    """Une ligne du CSV, réduite à ce qui sert au recoupement."""

    instant_utc: datetime
    type_operation: TypeOperation
    actif: str
    quantite: Decimal | None
    frais: Decimal | None
    taxes: Decimal | None


def _nombre(texte: str | None, colonne: str, illisibles: list[str]) -> Decimal | None:
    """Lit une colonne numérique du CSV.

    Une case **vide** vaut « non renseigné », pas zéro : la comparaison est alors sautée.
    Une case **remplie mais illisible** est tout autre chose — elle voudrait dire que le CSV
    n'a plus la forme attendue. La sauter en silence désarmerait le recoupement ([D-42]) au
    moment précis où il servirait le plus, alors le nom de la colonne part au rapport.
    """
    if texte is None or texte.strip() == "":
        return None
    try:
        return lire_nombre(texte, Convention.VIRGULE_DECIMALE).absolu().valeur
    except LectureImpossible:
        illisibles.append(colonne)
        return None


def lire_csv(fichier: Path, rapport: Rapport | None = None) -> list[LigneCsv]:
    """Lit le CSV et ne garde que les lignes qui correspondent à une opération sur actif."""
    lignes: list[LigneCsv] = []
    colonnes_illisibles: set[str] = set()

    with fichier.open(encoding="utf-8", newline="") as flux:
        for brute in csv.DictReader(flux, delimiter=SEPARATEUR):
            type_operation = TYPES_CSV.get((brute.get(COLONNE_TYPE) or "").strip())
            actif = (brute.get(COLONNE_ISIN) or "").strip()
            if type_operation is None or not actif:
                continue

            date = (brute.get(COLONNE_DATE) or "").strip()
            try:
                # Lue en temps universel : c'est ce que le rapprochement confirme.
                instant = datetime.fromisoformat(date).replace(tzinfo=UTC)
            except ValueError:
                if rapport is not None:
                    rapport.signaler(
                        "recoupement CSV",
                        f"une ligne du CSV porte une date illisible : elle n'a pas pu être "
                        f"rapprochée d'une opération sur l'actif {actif}",
                    )
                continue

            illisibles: list[str] = []
            lignes.append(
                LigneCsv(
                    instant_utc=instant,
                    type_operation=type_operation,
                    actif=actif,
                    quantite=_nombre(brute.get(COLONNE_PARTS), COLONNE_PARTS, illisibles),
                    frais=_nombre(brute.get(COLONNE_FRAIS), COLONNE_FRAIS, illisibles),
                    taxes=_nombre(brute.get(COLONNE_TAXES), COLONNE_TAXES, illisibles),
                )
            )
            colonnes_illisibles.update(illisibles)

    if rapport is not None and colonnes_illisibles:
        rapport.signaler(
            "recoupement CSV",
            f"colonne(s) {', '.join(sorted(colonnes_illisibles))} du CSV illisibles : "
            "le recoupement de ces valeurs n'a pas pu être fait. Le CSV n'a peut-être plus "
            "la forme attendue.",
        )

    return lignes


def _cle(actif: str, instant: datetime) -> tuple[str, datetime]:
    """Clé de rapprochement : l'actif et l'instant, **à la seconde**.

    Le JSON horodate à la milliseconde, le CSV tronque à la seconde. Comparer les deux tels
    quels ne rapprocherait jamais rien — et, pire, le recoupement annoncerait que toutes les
    opérations sont absentes du CSV, ce qui ressemblerait à une vraie alerte.
    """
    return actif, instant.astimezone(UTC).replace(microsecond=0)


def recouper(operations: list[Operation], lignes: list[LigneCsv], rapport: Rapport) -> None:
    """Compare chaque opération à sa ligne du CSV et signale les désaccords.

    Rien n'est corrigé : le CSV ne fait jamais autorité (D-06). Un désaccord veut dire qu'il
    faut aller regarder l'opération dans l'application Trade Republic.
    """
    par_cle = {_cle(ligne.actif, ligne.instant_utc): ligne for ligne in lignes}
    rapprochees: set[tuple[str, datetime]] = set()

    for operation in operations:
        cle = _cle(operation.actif, operation.instant_utc)
        ligne = par_cle.get(cle)

        if ligne is None:
            _signaler_absence(operation, rapport)
            continue

        rapprochees.add(cle)

        if ligne.type_operation is not operation.type:
            rapport.signaler(
                "recoupement CSV",
                f"le CSV classe cette opération en « {ligne.type_operation.value} » "
                f"alors que la lecture donne « {operation.type.value} »",
                operation.reference_source,
            )

        _comparer(operation, "quantité", operation.quantite, ligne.quantite, rapport)
        _comparer(operation, "frais", operation.frais, ligne.frais, rapport)
        _comparer(operation, "taxes", operation.taxes, ligne.taxes, rapport)

    for cle, ligne in par_cle.items():
        if cle not in rapprochees:
            rapport.signaler(
                "recoupement CSV",
                f"le CSV contient une opération « {ligne.type_operation.value} » sur "
                f"l'actif {ligne.actif} que la lecture n'a pas produite",
            )


def _signaler_absence(operation: Operation, rapport: Rapport) -> None:
    """Une opération sans ligne CSV : parfois normal, parfois non."""
    if operation.nature_source == NATURE_ABSENTE_DU_CSV:
        return
    explication = ABSENCES_ATTENDUES.get(operation.type)
    if explication is not None:
        return
    rapport.signaler(
        "recoupement CSV",
        f"aucune ligne du CSV ne correspond à cette opération « {operation.type.value} » "
        f"sur l'actif {operation.actif}",
        operation.reference_source,
    )


def _comparer(
    operation: Operation,
    nom: str,
    lue: Decimal | None,
    csv_valeur: Decimal | None,
    rapport: Rapport,
) -> None:
    """Compare une valeur lue dans un texte à la même valeur donnée en nombre par le CSV.

    Les deux viennent de la même source chez Trade Republic : elles doivent coïncider
    exactement. Un écart, même minime, veut dire que l'une des deux lectures est fausse —
    c'est exactement le genre d'erreur que ce recoupement existe pour attraper.
    """
    if lue is None or csv_valeur is None:
        return
    if lue != csv_valeur:
        rapport.signaler(
            "recoupement CSV",
            f"{nom} : la lecture des textes et le CSV ne donnent pas la même valeur "
            f"pour cette opération sur l'actif {operation.actif}",
            operation.reference_source,
        )
