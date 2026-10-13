"""« À surveiller » : tout ce que l'application signale, réuni en un seul endroit (conception §1.7).

Un signalement qu'on n'affiche pas n'existe pas (premier principe du contrat). Cette liste est la
liste de contrôle qui l'empêche : chaque couche qui signale quelque chose y a sa ligne — la
lecture de l'export, le moteur, les sources de cours et de composition, les réglages. Le
compteur de la manchette en donne le nombre, et le bloc du même nom, dans « Détail des
calculs », la détaille.

Le panneau se parcourt ; **la marque, elle, reste aussi à l'endroit où le chiffre s'affiche**.
Les deux, pas l'un ou l'autre.
"""

from __future__ import annotations

from dataclasses import dataclass

from pastory import assembleur
from pastory.adaptateurs.trade_republic.depot import PORTEFEUILLE_PERIME
from pastory.adaptateurs.trade_republic.rapport import LIMITE_DES_DIVIDENDES
from pastory.donnees_externes import composition as composition_externe
from pastory.vues import format as f


@dataclass(frozen=True)
class Point:
    """Une chose à savoir avant de se fier à un chiffre."""

    categorie: str
    message: str
    reference: str | None = None
    """De quoi remonter à la donnée brute : l'identifiant d'une opération, un actif."""

    actif: str | None = None
    """L'actif concerné, quand il y en a un : sa fiche de réglages s'ouvre depuis la ligne."""


def points(construit: assembleur.Construit) -> list[Point]:
    """Tous les points, de la lecture vers le calcul : c'est l'ordre où ils se produisent."""
    return (
        _lecture(construit)
        + _moteur(construit)
        + _cours(construit)
        + _compositions(construit)
        + _reglages(construit)
    )


def _lecture(construit: assembleur.Construit) -> list[Point]:
    rapport = construit.rapport
    depot = rapport.depot
    liste: list[Point] = []
    for type_affiche, nombre in rapport.types_inconnus.most_common():
        motif = rapport.motifs.get(type_affiche)
        liste.append(
            Point(
                "Type inconnu",
                f"{nombre} ligne(s) de type « {type_affiche} » : ni ignorées ni rangées au "
                "hasard, elles ne sont pas comptées, et elles peuvent faire entrer ou sortir des "
                "parts de vos actifs." + (f" {motif}" if motif else ""),
            )
        )
    if rapport.operations_non_produites:
        liste.append(
            Point(
                "Opération non lue",
                f"{rapport.operations_non_produites} ligne(s) d'un type connu n'ont produit "
                "aucune opération : des parts ou des montants manquent aux chiffres.",
            )
        )
    for anomalie in rapport.anomalies:
        liste.append(
            Point("Contrôle de cohérence", anomalie.message, anomalie.reference_source)
        )
    for signalement in rapport.signalements:
        liste.append(Point(signalement.categorie, signalement.message, signalement.ou))
    if depot.plus_a_jour:
        liste.append(
            Point(
                "Portefeuille périmé",
                PORTEFEUILLE_PERIME.format(noms=", ".join(depot.plus_a_jour))
                + " Ouvrez-le sur la couverture, puis supprimez celui-ci.",
            )
        )
    for nom, raison in depot.fichiers_ignores:
        liste.append(Point("Fichier ignoré", f"{nom} : {raison}."))
    if depot.sans_identifiant:
        liste.append(
            Point(
                "Ligne sans identifiant",
                f"{len(depot.sans_identifiant)} ligne(s) sans identifiant d'opération : "
                "impossibles à reconnaître d'un export à l'autre, elles ne sont pas lues.",
            )
        )
    for gardee, _ in depot.conflits:
        liste.append(
            Point(
                "Opération en deux versions",
                "Deux exports donnent deux versions différentes de la même opération : la "
                "première lue est gardée, rien ne permet de dire laquelle est la bonne.",
                gardee.transaction_id,
            )
        )
    if rapport.a_des_dividendes:
        liste.append(Point("Limite connue", LIMITE_DES_DIVIDENDES))
    return liste


def _moteur(construit: assembleur.Construit) -> list[Point]:
    liste = [
        Point(s.categorie, s.message, s.reference_source, s.actif)
        for s in construit.portefeuille.signalements
    ]
    for prix in construit.completion.prix_completes:
        liste.append(
            Point(
                "Prix déduit d'un cours",
                f"Cette opération est arrivée sans son montant : il est déduit du cours de "
                f"marché, {f.quantite(prix.quantite)} × {f.montant(prix.cours.valeur)} = "
                f"{f.montant(prix.montant_brut)} (cours du {f.date_courte(prix.cours.date)}, "
                f"{prix.cours.place}, {prix.cours.source}). Ce n'est pas un montant donné par "
                "la banque.",
                prix.reference_source,
                prix.actif,
            )
        )
    if construit.completion.incompletes:
        liste.append(
            Point(
                "À compléter",
                f"{construit.completion.incompletes} opération(s) attendent toujours un prix : "
                "leurs parts sont comptées, leur montant non. Le capital investi est sous-estimé.",
            )
        )
    if construit.diversification is not None:
        liste += [
            Point(s.categorie, s.message, s.reference_source, s.actif)
            for s in construit.diversification.signalements
        ]
    return liste


def _cours(construit: assembleur.Construit) -> list[Point]:
    return [
        Point(refus.categorie, refus.motif, refus.actif, refus.actif)
        for refus in construit.fournisseur.refus
    ]


def _compositions(construit: assembleur.Construit) -> list[Point]:
    if construit.compositions is None:
        return []
    return [
        Point(categorie, un.motif, un.actif, un.actif)
        for categorie, refus in composition_externe.grouper_refus(construit.compositions.refus)
        for un in refus
    ]


def _reglages(construit: assembleur.Construit) -> list[Point]:
    reglages = construit.reglages
    if reglages is None:
        return []
    liste = [
        Point(
            "Réglage introuvable",
            f"{nom.capitalize()} : {trou.motif}",
            actif,
            actif if actif != "PEA" else None,
        )
        for actif, nom, trou in reglages.trous()
    ]
    for ecartee in reglages.corrections_ecartees:
        liste.append(Point("Correction non appliquée", ecartee))
    for actif in reglages.orphelines:
        liste.append(
            Point(
                "Correction sans actif",
                "Une correction désigne un actif qu'aucun de vos exports ne contient : elle ne "
                "sert à rien. C'est souvent un ancien identifiant, et elle peut être retirée.",
                actif,
            )
        )
    if reglages.retraits_pea:
        jours = ", ".join(f.date_courte(jour) for jour in reglages.retraits_pea)
        liste.append(
            Point(
                "Retrait du PEA",
                f"De l'argent est sorti du PEA depuis son ouverture ({jours}). L'impôt estimé du "
                "PEA suppose qu'il n'y a jamais eu de retrait : il est alors mal approché.",
            )
        )
    return liste
