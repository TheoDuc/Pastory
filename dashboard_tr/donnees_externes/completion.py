"""Compléter les prix manquants : du pivot vers du pivot (D-15).

Des titres peuvent entrer dans un portefeuille **sans prix** : action offerte, actions
gratuites, titres transférés. Le format pivot les accepte tels quels, avec un `montant_brut`
marqué `a_completer` — et le moteur, jusqu'ici, comptait leurs parts sans compter leur montant.
Conséquence visible dans `dashboard positions` : un capital investi sous-estimé et un prix de
revient laissé vide plutôt que faussement bas (D-45).

Ce module est le chaînon qui manquait. Il ne touche **ni à l'adaptateur, ni au moteur** :

    pivot (montant_brut « à compléter »)  →  ici  →  pivot (montant_brut « déduit »)

Le format pivot avait prévu ce moment : `A_COMPLETER` s'y décrit comme « en attente d'une donnée
externe (cours de l'étape 4) », et `DEDUCTION` comme « reconstitué par une règle écrite (D-15) ».
Compléter un prix, c'est faire passer un champ de l'une à l'autre. Le moteur, qui sait déjà
traiter les deux cas, n'a pas une ligne à changer (D-26).

Deux règles de conduite, héritées de tout le reste du projet :

- **rien n'est estimé.** Sans cours utilisable, l'opération est rendue **inchangée** : elle
  reste à compléter, et le refus est rapporté avec son motif (D-45) ;
- **tout ce qui est déduit est traçable.** Le rapport donne, pour chaque prix complété, la
  quantité, le cours retenu, son jour, sa place et sa source : de quoi refaire la
  multiplication à la main.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal

from dashboard_tr.donnees_externes.cours import Cours, FournisseurDeCours, Refus
from dashboard_tr.pivot.operation import Operation, Poche, Provenance

CENTIME = Decimal("0.01")
"""Le montant brut déduit est arrêté au centime, comme tout montant du pivot.

Le cours, lui, est conservé tel quel dans le cache et dans le rapport : c'est lui qui permet de
refaire le calcul, et l'arrondi ne doit se produire qu'une fois, à la fin."""


@dataclass(frozen=True)
class PrixComplete:
    """Un prix qui manquait et qui a été déduit d'un cours. Destiné à être montré."""

    actif: str
    poche: Poche
    date_operation: Date
    quantite: Decimal
    cours: Cours
    montant_brut: Decimal
    reference_source: str | None = None
    nom_actif: str | None = None

    @property
    def jour_decale(self) -> bool:
        """Vrai si le cours retenu n'est pas du jour de l'opération.

        Cas normal — un titre reçu un samedi est valorisé au cours du vendredi — mais qui doit
        se voir : c'est une information dont l'utilisateur a besoin pour comparer avec son
        application.
        """
        return self.cours.date != self.date_operation


@dataclass(frozen=True)
class Completion:
    """Ce que la complétion a fait, et ce qu'elle n'a pas pu faire."""

    operations: tuple[Operation, ...]
    prix_completes: tuple[PrixComplete, ...] = ()
    refus: tuple[Refus, ...] = ()
    attendus: int = 0
    """Combien d'opérations attendaient un prix, complétées ou non."""

    @property
    def rien_a_completer(self) -> bool:
        """Vrai quand aucune opération n'attendait de prix : il n'y a rien à dire."""
        return self.attendus == 0

    @property
    def incompletes(self) -> int:
        """Combien attendent toujours un prix après le passage."""
        return self.attendus - len(self.prix_completes)


def completer_les_prix(
    operations: Iterable[Operation], fournisseur: FournisseurDeCours
) -> Completion:
    """Remplace `a_completer` par un montant déduit d'un cours, quand c'est possible.

    L'ordre des opérations est conservé : le moteur rejoue une histoire, et une histoire dont
    l'ordre change ne raconte plus la même chose.
    """
    resultat: list[Operation] = []
    completes: list[PrixComplete] = []
    attendus = 0

    for operation in operations:
        if not _attend_un_prix(operation):
            resultat.append(operation)
            continue

        attendus += 1
        cours = fournisseur.cours(operation.actif, operation.date)
        if cours is None:
            # Le fournisseur a déjà enregistré le motif : l'opération repart telle quelle, et
            # le moteur se comportera comme avant (parts comptées, montant non compté).
            resultat.append(operation)
            continue

        completee, trace = _completer(operation, cours)
        resultat.append(completee)
        completes.append(trace)

    return Completion(
        operations=tuple(resultat),
        prix_completes=tuple(completes),
        refus=tuple(fournisseur.refus),
        attendus=attendus,
    )


def _attend_un_prix(operation: Operation) -> bool:
    """Vrai si un cours permettrait de compléter cette opération.

    La quantité est exigée : sans elle, il n'y a rien à multiplier. Une telle opération est
    déjà signalée par le moteur comme inexploitable, et ce n'est pas ici qu'on le répète.
    """
    return operation.est_a_completer("montant_brut") and operation.quantite is not None


def _completer(operation: Operation, cours: Cours) -> tuple[Operation, PrixComplete]:
    """L'opération avec son montant brut déduit, et la trace de ce qui a été fait."""
    quantite = operation.quantite
    assert quantite is not None  # garanti par `_attend_un_prix`

    montant_brut = (quantite * cours.valeur).quantize(CENTIME, rounding=ROUND_HALF_UP)

    provenance = dict(operation.provenance)
    provenance["montant_brut"] = Provenance.DEDUCTION
    # Le prix unitaire n'est renseigné que s'il manquait : une valeur donnée par la banque
    # reste la sienne, on ne la remplace jamais par un cours de marché.
    if operation.prix_unitaire is None or operation.est_a_completer("prix_unitaire"):
        provenance["prix_unitaire"] = Provenance.DEDUCTION
        prix_unitaire = cours.valeur
    else:
        prix_unitaire = operation.prix_unitaire

    completee = replace(
        operation,
        montant_brut=montant_brut,
        prix_unitaire=prix_unitaire,
        provenance=provenance,
    )
    trace = PrixComplete(
        actif=operation.actif,
        poche=operation.poche,
        date_operation=operation.date,
        quantite=quantite,
        cours=cours,
        montant_brut=montant_brut,
        reference_source=operation.reference_source,
        nom_actif=operation.nom_actif,
    )
    return completee, trace
