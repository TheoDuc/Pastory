"""
Compare les deux portes d'entrée sur un même dossier : l'export pytr (`all_events.json`) et
l'export officiel (`*.csv`). C'est la preuve demandée par l'étape 8 ter avant de retirer pytr
(D-81) : sur la période commune, les deux doivent donner les mêmes opérations.

Usage :
    python scripts/comparer_adaptateurs.py data
    python scripts/comparer_adaptateurs.py data_tiers

Ce script ne fait que LIRE. Il n'affiche AUCUNE valeur : ni montant, ni quantité, ni ISIN, ni
date. Seulement des comptages et des « identique / différent », par type d'opération.

**Comment on rapproche.** Les opérations sont regroupées par (jour, actif, type), et l'on
compare les **sommes** de chaque groupe : un ordre exécuté en deux fois donne deux lignes dans
l'export officiel et une seule chez pytr (export-officiel.md §5.1).

**Les poches.** pytr a besoin du rôle de chaque compte espèces (D-10). S'il est déclaré dans
la configuration de l'utilisateur, la poche est comparée. Sinon — l'export d'un tiers — les
rôles sont déduits de l'export officiel, pour la seule comparaison, et la poche n'est **pas**
comparée : elle serait identique par construction.

Script de transition : il disparaît avec l'adaptateur pytr (étape 8 ter).
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pastory.adaptateurs.trade_republic import evenements, source
from pastory.adaptateurs.trade_republic.lecture import Lecteur as LecteurPytr
from pastory.adaptateurs.trade_republic_officiel.depot import lire_dossier
from pastory.adaptateurs.trade_republic_officiel.lecture import Lecteur as LecteurOfficiel
from pastory.config import comptes as config_comptes
from pastory.pivot.operation import Operation, Poche, jour_a_paris

TOLERANCE = Decimal("0.01")
ZERO = Decimal("0")


@dataclass
class Groupe:
    lignes: int = 0
    quantite: Decimal = ZERO
    brut: Decimal = ZERO
    frais: Decimal = ZERO
    taxes: Decimal = ZERO
    poches: frozenset[str] = frozenset()

    def ajouter(self, operation: Operation) -> None:
        self.lignes += 1
        self.quantite += operation.quantite or ZERO
        self.brut += operation.montant_brut or ZERO
        self.frais += operation.frais
        self.taxes += operation.taxes
        self.poches = self.poches | {operation.poche.value}


def grouper(operations: list[Operation], debut, fin) -> dict[tuple, Groupe]:
    groupes: dict[tuple, Groupe] = defaultdict(Groupe)
    for operation in operations:
        if debut <= operation.date <= fin:
            # La crypto n'a pas le même code des deux côtés (`XF…` chez pytr, `ETH` dans
            # l'export officiel) : elle est rapprochée par sa poche.
            actif = "(crypto)" if operation.poche is Poche.CRYPTO else operation.actif
            groupes[(operation.date, actif, operation.type.value)].ajouter(operation)
    return groupes


def roles_deduits(dossier: Path, bruts: list[dict]) -> dict[str, config_comptes.RoleCompte]:
    """Rôle de chaque compte pytr, lu sur la poche de la ligne officielle du même jour et du
    même actif. Pour la comparaison seulement."""
    depot = lire_dossier(dossier)
    poche_officielle = {(ligne.date, ligne.symbol): ligne.account_type for ligne in depot.lignes}
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for evenement in bruts:
        instant = evenements.horodatage(evenement)
        actif = evenements.isin_icone(evenement)
        compte = evenements.compte(evenement)
        if instant and actif and compte:
            poche = poche_officielle.get((jour_a_paris(instant).isoformat(), actif))
            if poche:
                votes[compte][poche] += 1
    return {
        compte: config_comptes.RoleCompte.PEA
        if vote.most_common(1)[0][0] == "PEA"
        else config_comptes.RoleCompte.COURANT
        for compte, vote in votes.items()
    }


def egal(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCE


def main(dossier: Path) -> None:
    bruts = source.charger_evenements(dossier)
    configuration = config_comptes.charger()
    comparer_les_poches = bool(configuration.roles)
    if not comparer_les_poches:
        configuration = config_comptes.Configuration(roles=roles_deduits(dossier, bruts))

    pytr = LecteurPytr(configuration).lire(bruts)
    officiel = LecteurOfficiel().lire(lire_dossier(dossier))

    print(
        f"pytr      : {len(pytr.operations)} opérations, "
        f"{pytr.operations_non_produites} non produites"
    )
    print(
        f"officiel  : {len(officiel.operations)} opérations, "
        f"{officiel.operations_non_produites} non produites, "
        f"{sum(officiel.types_inconnus.values())} lignes non traitées "
        f"({', '.join(sorted(officiel.types_inconnus)) or 'aucune'})"
    )
    if not pytr.operations or not officiel.operations:
        print("Rien à comparer.")
        return

    debut = max(min(o.date for o in pytr.operations), min(o.date for o in officiel.operations))
    fin = min(max(o.date for o in pytr.operations), max(o.date for o in officiel.operations))
    print(f"période commune : {(fin - debut).days + 1} jours")
    if not comparer_les_poches:
        print("poche : non comparée (rôles des comptes déduits de l'export officiel)")

    groupes_pytr = grouper(pytr.operations, debut, fin)
    groupes_officiels = grouper(officiel.operations, debut, fin)

    resultats: Counter[tuple[str, str, bool]] = Counter()
    fractionnes: Counter[str] = Counter()
    for cle in sorted(set(groupes_pytr) | set(groupes_officiels), key=str):
        type_ = cle[2]
        p, o = groupes_pytr.get(cle), groupes_officiels.get(cle)
        if p is None or o is None:
            resultats[
                (type_, "présent d'un seul côté : " + ("pytr" if o is None else "officiel"), True)
            ] += 1
            continue
        if o.lignes != p.lignes:
            fractionnes[type_] += 1
        if cle[1] == "(crypto)":
            type_ += " (crypto)"
        resultats[(type_, "quantité", p.quantite == o.quantite)] += 1
        resultats[(type_, "brut", egal(p.brut, o.brut))] += 1
        resultats[(type_, "frais", egal(p.frais, o.frais))] += 1
        resultats[(type_, "taxes", egal(p.taxes, o.taxes))] += 1
        resultats[
            (
                type_,
                "net (brut - frais - taxes)",
                egal(p.brut - p.frais - p.taxes, o.brut - o.frais - o.taxes),
            )
        ] += 1
        if comparer_les_poches:
            resultats[(type_, "poche", p.poches == o.poches)] += 1

    print()
    print("Groupes (jour, actif, type) comparés :")
    for (type_, mesure, identique), nombre in sorted(resultats.items()):
        etat = "identique" if identique else "DIFFÉRENT"
        if mesure.startswith("présent"):
            etat = ""
        print(f"  {type_:<22} {mesure:<30} {etat:<10} {nombre:>5}")
    if fractionnes:
        print()
        print("Groupes où le nombre de lignes diffère (ordre exécuté en plusieurs fois) :")
        for type_, nombre in sorted(fractionnes.items()):
            print(f"  {type_:<22} {nombre:>5}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]))
