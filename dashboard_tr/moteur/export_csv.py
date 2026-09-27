"""Les fichiers que le propriétaire ouvre pour vérifier les calculs du moteur.

| Fichier | Une ligne par | À quoi il sert |
|---|---|---|
| `positions.csv` | actif dans une poche | comparer quantité et capital avec l'app de la banque |
| `journal.csv` | opération | **refaire un chiffre à la main**, de l'achat au total |
| `valorisation.csv` | actif dans une poche | valeur, plus-value latente, gain, TRI et TWRR |
| `flux.csv` | flux d'un groupe | **la table de `TRI.PAIEMENTS`** : dates et montants signés |
| `sous_periodes_twrr.csv` | sous-période d'un groupe | refaire le TWRR : produit des (1 + r) |
| `evolution.csv` | jour | la valeur du portefeuille dans le temps |
| `couts.csv` | opération | refaire les coûts payés, et voir leur poids |
| `valeur_reelle.csv` | position, poche, total | refaire la valeur réelle et l'impôt |

Le journal est le plus important. Il se lit comme un relevé bancaire : on part de l'état
d'avant, on applique l'opération, on tombe sur l'état d'après. C'est ce qui permet de
répondre à « d'où sort ce prix de revient ? » sans lire une ligne de code (D-44). `flux.csv`
joue le même rôle pour le TRI : collé dans un tableur, il doit redonner le même taux.

Les positions sont rangées par poche puis par actif, et les lignes du journal **restent
groupées par actif**, dans l'ordre du temps : un actif se suit d'un bout à l'autre sans avoir
à trier le fichier soi-même.

Ces fichiers contiennent de vraies valeurs : ils sont écrits dans le dossier personnel, hors
du dossier synchronisé, et n'entrent jamais dans git (D-01, D-37).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from dashboard_tr import tableur
from dashboard_tr.moteur.couts import DetailDesCouts, LigneDeCout
from dashboard_tr.moteur.diversification import Diversification, Repartition, Rubrique
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.position import EtatPosition, LigneJournal, Position
from dashboard_tr.moteur.rendements import PAS_DU_TAUX, Rendements, Synthese
from dashboard_tr.moteur.valeur_reelle import (
    LigneValeurReelle,
    ValeurReelle,
    ValeurReellePoche,
)
from dashboard_tr.moteur.valorisation import PointEvolution, PositionValorisee
from dashboard_tr.pivot.operation import Poche

NOM_POSITIONS = "positions.csv"
NOM_JOURNAL = "journal.csv"
NOM_VALORISATION = "valorisation.csv"
NOM_FLUX = "flux.csv"
NOM_SOUS_PERIODES = "sous_periodes_twrr.csv"
NOM_EVOLUTION = "evolution.csv"

COLONNES_POSITIONS = (
    "poche",
    "actif",
    "nom_actif",
    "quantite_detenue",
    "capital_net_investi",
    "prix_de_revient",
    "capital_fiscal",
    "prix_de_revient_fiscal",
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
    "capital_fiscal_apres",
    "prix_de_revient_fiscal_apres",
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


def _prix_de_revient_fiscal(etat: EtatPosition) -> str:
    """Le prix de revient au sens de l'impôt : frais et taxes d'achat compris (D-57).

    Il se tait exactement quand l'autre se tait : plus aucune part, ou histoire trouée (D-45).
    """
    prix = etat.prix_de_revient_fiscal
    if prix is not None:
        return tableur.nombre(prix)
    if etat.historique_incomplet:
        return tableur.VALEUR_A_COMPLETER
    return tableur.VALEUR_SANS_OBJET


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
        "capital_fiscal": tableur.nombre(etat.capital_fiscal),
        "prix_de_revient_fiscal": _prix_de_revient_fiscal(etat),
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
        "capital_fiscal_apres": tableur.nombre(ligne.apres.capital_fiscal),
        "prix_de_revient_fiscal_apres": _prix_de_revient_fiscal(ligne.apres),
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


# --- La valorisation et les rendements (étape 5) --------------------------------------------

COLONNES_VALORISATION = (
    "poche",
    "actif",
    "nom_actif",
    "date_valorisation",
    "quantite",
    "cours",
    "date_cours",
    "place",
    "source",
    "valeur",
    "capital_net_investi",
    "plus_value_latente",
    "gain",
    "tri",
    "twrr",
    "twrr_annualise",
    "remarque",
)

COLONNES_FLUX = ("groupe", "date", "montant", "libelle", "actif", "poche", "identifiant")

COLONNES_SOUS_PERIODES = (
    "groupe",
    "du",
    "au",
    "valeur_debut",
    "flux",
    "valeur_fin",
    "rendement",
)

COLONNES_EVOLUTION = (
    "date",
    "valeur_totale",
    *(f"valeur_{poche.value}" for poche in Poche),
    "capital_net_investi",
    "positions_non_valorisees",
)
"""Une colonne par poche, tirée de l'énumération : une poche de plus ne peut pas manquer ici
sans manquer partout, et la somme des colonnes de poche retombe toujours sur le total."""


def _taux(taux: Decimal | None) -> str:
    """Un taux en fraction (0,1 pour 10 %), à six décimales : le tableur le mettra en %."""
    if taux is None:
        return tableur.VALEUR_SANS_OBJET
    return tableur.nombre(taux.quantize(PAS_DU_TAUX, rounding=ROUND_HALF_UP))


def _remarque_rendements(rendements: Rendements | None) -> list[str]:
    raisons: list[str] = []
    if rendements is None:
        return raisons
    if not rendements.calculable:
        raisons.append(f"gain et TRI non calculables : {rendements.motif}")
    else:
        if rendements.tri is None:
            raisons.append(f"TRI non calculable : {rendements.motif_tri}")
        if rendements.twrr.taux is None:
            raisons.append(f"TWRR non calculable : {rendements.twrr.motif}")
    if rendements.calculable and not rendements.fiable:
        raisons.append("chiffres calculés sur une histoire incomplète (D-45)")
    return raisons


def _ligne_valorisation(
    synthese: Synthese,
    position: Position,
    valorisees: Mapping[tuple[str, Poche], PositionValorisee],
) -> dict[str, str]:
    """Une position à la fin de la période : détenue et valorisée, détenue sans cours, ou
    déjà soldée (valeur nulle, mais un gain sur la période)."""
    valorisee = valorisees.get((position.actif, position.poche))
    rendements = synthese.de(position)
    cours = valorisee.cours if valorisee is not None else None
    # La position reçue peut ne pas être coupée à la fin de la période : on s'en assure.
    detenue = position.jusqu_au(synthese.periode.fin).etat

    reserve = remarque(detenue)
    remarques = [reserve] if reserve else []
    if valorisee is not None and not valorisee.valorisee:
        remarques.append(valorisee.motif or "non valorisée")
    remarques += _remarque_rendements(rendements)

    if valorisee is None:
        # Plus aucune part à la fin de la période : la position vaut zéro, sans ambiguïté.
        valeur = tableur.nombre(Decimal("0.00"))
    elif valorisee.valeur is None:
        valeur = tableur.VALEUR_SANS_OBJET
    else:
        valeur = tableur.nombre(valorisee.valeur)

    return {
        "poche": position.poche.value,
        "actif": position.actif,
        "nom_actif": position.nom_actif or "",
        "date_valorisation": synthese.periode.fin.isoformat(),
        "quantite": tableur.nombre(detenue.quantite),
        "cours": tableur.nombre(cours.valeur) if cours else tableur.VALEUR_SANS_OBJET,
        "date_cours": cours.date.isoformat() if cours else "",
        "place": cours.place if cours else "",
        "source": cours.source if cours else "",
        "valeur": valeur,
        "capital_net_investi": tableur.nombre(detenue.capital_net_investi),
        "plus_value_latente": tableur.nombre(
            valorisee.plus_value_latente if valorisee is not None else None,
            absent=tableur.VALEUR_SANS_OBJET,
        ),
        "gain": tableur.nombre(
            rendements.gain if rendements else None, absent=tableur.VALEUR_SANS_OBJET
        ),
        "tri": _taux(rendements.tri if rendements else None),
        "twrr": _taux(rendements.twrr.taux if rendements else None),
        "twrr_annualise": _taux(rendements.twrr.annualise if rendements else None),
        "remarque": " ; ".join(remarques),
    }


def ecrire_valorisation(portefeuille: Portefeuille, synthese: Synthese, fichier: Path) -> Path:
    """Écrit `valorisation.csv` : **toutes** les positions, soldées comprises, pour que la
    colonne « gain » s'additionne en le gain total."""
    valorisees = {
        (valorisee.actif, valorisee.poche): valorisee
        for valorisee in synthese.valorisation.positions
    }
    return tableur.ecrire(
        COLONNES_VALORISATION,
        (
            _ligne_valorisation(synthese, position, valorisees)
            for position in portefeuille.positions
        ),
        fichier,
    )


def _groupes(synthese: Synthese) -> list[tuple[str, Rendements]]:
    """Le total, puis chaque poche, puis chaque position : un nom par groupe."""
    groupes: list[tuple[str, Rendements]] = [("total", synthese.total)]
    groupes += [(poche.value, rendements) for poche, rendements in synthese.par_poche.items()]
    groupes += [
        (f"{actif} ({poche.value})", rendements)
        for (actif, poche), rendements in synthese.par_position.items()
    ]
    return groupes


def _ligne_flux(
    groupe: str,
    jour: Date,
    montant: Decimal,
    libelle: str,
    actif: str = "",
    poche: str = "",
    identifiant: str = "",
) -> dict[str, str]:
    return {
        "groupe": groupe,
        "date": jour.isoformat(),
        "montant": tableur.nombre(montant),
        "libelle": libelle,
        "actif": actif,
        "poche": poche,
        "identifiant": identifiant,
    }


def _lignes_de_flux(synthese: Synthese) -> Iterator[Mapping[str, str]]:
    """La table de `TRI.PAIEMENTS`, groupe par groupe : **celle-là même** sur laquelle le
    TRI a été calculé (`Rendements.table_du_tri`), ligne pour ligne."""
    for nom, rendements in _groupes(synthese):
        if not rendements.calculable:
            continue
        for ligne in rendements.table_du_tri:
            flux = ligne.flux
            yield _ligne_flux(
                nom,
                ligne.date,
                ligne.montant,
                ligne.libelle,
                flux.actif if flux else "",
                flux.poche.value if flux else "",
                flux.identifiant if flux else "",
            )


def ecrire_flux(synthese: Synthese, fichier: Path) -> Path:
    """Écrit `flux.csv`. Dans un tableur : `=TRI.PAIEMENTS(montants ; dates)` d'un groupe doit
    redonner le TRI de ce groupe."""
    return tableur.ecrire(COLONNES_FLUX, _lignes_de_flux(synthese), fichier)


def _lignes_de_sous_periodes(synthese: Synthese) -> Iterator[Mapping[str, str]]:
    for nom, rendements in _groupes(synthese):
        for sous_periode in rendements.twrr.sous_periodes:
            yield {
                "groupe": nom,
                "du": sous_periode.du.isoformat(),
                "au": sous_periode.au.isoformat(),
                "valeur_debut": tableur.nombre(sous_periode.valeur_debut),
                "flux": tableur.nombre(sous_periode.flux),
                "valeur_fin": tableur.nombre(sous_periode.valeur_fin),
                "rendement": _taux(sous_periode.rendement),
            }


def ecrire_sous_periodes(synthese: Synthese, fichier: Path) -> Path:
    """Écrit `sous_periodes_twrr.csv` : le produit des (1 + rendement) d'un groupe, moins un,
    doit redonner son TWRR."""
    return tableur.ecrire(COLONNES_SOUS_PERIODES, _lignes_de_sous_periodes(synthese), fichier)


def _ligne_evolution(point: PointEvolution) -> dict[str, str]:
    zero = Decimal("0.00")
    return {
        "date": point.date.isoformat(),
        "valeur_totale": tableur.nombre(point.valeur),
        **{
            f"valeur_{poche.value}": tableur.nombre(point.par_poche.get(poche, zero))
            for poche in Poche
        },
        "capital_net_investi": tableur.nombre(point.capital_net_investi),
        "positions_non_valorisees": str(point.non_valorisees),
    }


def ecrire_evolution(points: Iterable[PointEvolution], fichier: Path) -> Path:
    """Écrit `evolution.csv` : un jour par ligne, la valeur et le capital investi."""
    return tableur.ecrire(
        COLONNES_EVOLUTION, (_ligne_evolution(point) for point in points), fichier
    )


# --- Les coûts et la valeur réelle (étape 6) ------------------------------------------------

NOM_COUTS = "couts.csv"
NOM_VALEUR_REELLE = "valeur_reelle.csv"

COLONNES_COUTS = (
    "poche",
    "actif",
    "nom_actif",
    "date",
    "type",
    "nature",
    "montant_brut",
    "frais",
    "taxes",
    "cout_paye",
    "poids",
    "spread_estime",
    "taux_de_spread",
    "moment",
    "remarque",
    "identifiant",
)

COLONNES_VALEUR_REELLE = (
    "niveau",
    "poche",
    "actif",
    "nom_actif",
    "valeur_brute",
    "frais_de_vente_estimes",
    "spread_estime",
    "taux_de_spread",
    "avant_impot",
    "prix_d_acquisition_fiscal",
    "plus_value_imposable",
    "base_imposable",
    "taux_d_impot",
    "impot_estime",
    "valeur_reelle",
    "regle",
    "remarque",
)


def _ligne_cout(
    ligne: LigneDeCout, noms: Mapping[tuple[str, Poche], str | None]
) -> dict[str, str]:
    spread = ligne.spread_estime
    remarques = []
    if ligne.spread_manquant:
        remarques.append("type d'actif non déclaré : spread non estimé")
    if ligne.montant_brut is None:
        remarques.append("montant brut à compléter : pas de poids ni de spread")
    return {
        "poche": ligne.poche.value,
        "actif": ligne.actif,
        "nom_actif": noms.get((ligne.actif, ligne.poche)) or "",
        "date": ligne.date.isoformat(),
        "type": ligne.type.value,
        "nature": ligne.operation.nature_source,
        "montant_brut": tableur.nombre(ligne.montant_brut, absent=tableur.VALEUR_A_COMPLETER),
        "frais": tableur.nombre(ligne.frais),
        "taxes": tableur.nombre(ligne.taxes),
        "cout_paye": tableur.nombre(ligne.cout_paye),
        "poids": _taux(ligne.poids),
        "spread_estime": (
            tableur.nombre(spread.montant) if spread else tableur.VALEUR_SANS_OBJET
        ),
        "taux_de_spread": (
            _taux(spread.parametre.valeur / Decimal("100"))
            if spread
            else tableur.VALEUR_SANS_OBJET
        ),
        "moment": ligne.moment,
        "remarque": " ; ".join(remarques),
        "identifiant": ligne.operation.identifiant,
    }


def ecrire_couts(detail: DetailDesCouts, fichier: Path) -> Path:
    """Écrit `couts.csv` : une ligne par opération de la période.

    C'est le fichier qui permet de refaire le bloc des coûts payés dans un tableur : la somme
    de la colonne `cout_paye` doit valoir le total affiché, et la colonne `poids` se recalcule
    en divisant `cout_paye` par `montant_brut`.
    """
    return tableur.ecrire(
        COLONNES_COUTS,
        (_ligne_cout(ligne, detail.noms) for ligne in detail.lignes),
        fichier,
    )


def _ligne_valeur_reelle_position(
    ligne: LigneValeurReelle, noms: Mapping[tuple[str, Poche], str | None]
) -> dict[str, str]:
    cession = ligne.cession
    acquisition = (
        cession.capital_net_investi if ligne.poche is Poche.CRYPTO else cession.capital_fiscal
    )
    return {
        "niveau": "position",
        "poche": ligne.poche.value,
        "actif": ligne.actif,
        "nom_actif": noms.get((ligne.actif, ligne.poche)) or "",
        "valeur_brute": tableur.nombre(ligne.valeur_brute),
        "frais_de_vente_estimes": tableur.nombre(ligne.frais_de_vente.montant),
        "spread_estime": tableur.nombre(ligne.spread.montant),
        "taux_de_spread": _taux(ligne.spread.parametre.valeur / Decimal("100")),
        "avant_impot": tableur.nombre(ligne.avant_impot),
        "prix_d_acquisition_fiscal": tableur.nombre(acquisition),
        "plus_value_imposable": tableur.nombre(ligne.plus_value_fiscale),
        "base_imposable": tableur.VALEUR_SANS_OBJET,
        "taux_d_impot": tableur.VALEUR_SANS_OBJET,
        "impot_estime": tableur.VALEUR_SANS_OBJET,
        "valeur_reelle": tableur.VALEUR_SANS_OBJET,
        "regle": "",
        "remarque": "l'impôt se calcule au niveau de la poche",
    }


def _ligne_valeur_reelle_poche(groupe: ValeurReellePoche) -> dict[str, str]:
    impot = groupe.impot
    remarques = []
    if impot.motif:
        remarques.append(impot.motif)
    if groupe.exclues:
        remarques.append(
            f"{len(groupe.exclues)} position(s) hors du calcul : {groupe.exclues[0].motif}"
        )
    if not impot.fiable:
        remarques.append("une position repose sur une histoire incomplète (D-45)")
    return {
        "niveau": "poche",
        "poche": groupe.poche.value,
        "actif": "",
        "nom_actif": "",
        "valeur_brute": tableur.nombre(groupe.valeur_brute),
        "frais_de_vente_estimes": tableur.nombre(groupe.frais_de_vente),
        "spread_estime": tableur.nombre(groupe.spread),
        "taux_de_spread": tableur.VALEUR_SANS_OBJET,
        "avant_impot": tableur.nombre(groupe.avant_impot),
        "prix_d_acquisition_fiscal": tableur.VALEUR_SANS_OBJET,
        "plus_value_imposable": tableur.nombre(
            impot.base_avant_plancher, absent=tableur.VALEUR_SANS_OBJET
        ),
        "base_imposable": tableur.nombre(impot.base, absent=tableur.VALEUR_SANS_OBJET),
        "taux_d_impot": _taux(impot.taux / Decimal("100") if impot.taux is not None else None),
        "impot_estime": tableur.nombre(impot.impot, absent=tableur.VALEUR_SANS_OBJET),
        "valeur_reelle": tableur.nombre(groupe.valeur_reelle, absent=tableur.VALEUR_SANS_OBJET),
        "regle": impot.regle,
        "remarque": " ; ".join(remarques),
    }


def _ligne_valeur_reelle_total(valeur: ValeurReelle) -> dict[str, str]:
    return {
        "niveau": "total",
        "poche": "",
        "actif": "",
        "nom_actif": "",
        "valeur_brute": tableur.nombre(valeur.valeur_brute),
        "frais_de_vente_estimes": tableur.nombre(valeur.frais_de_vente),
        "spread_estime": tableur.nombre(valeur.spread),
        "taux_de_spread": tableur.VALEUR_SANS_OBJET,
        "avant_impot": tableur.nombre(
            valeur.valeur_brute - valeur.frais_de_vente - valeur.spread
        ),
        "prix_d_acquisition_fiscal": tableur.VALEUR_SANS_OBJET,
        "plus_value_imposable": tableur.VALEUR_SANS_OBJET,
        "base_imposable": tableur.VALEUR_SANS_OBJET,
        "taux_d_impot": tableur.VALEUR_SANS_OBJET,
        "impot_estime": tableur.nombre(valeur.impot),
        "valeur_reelle": tableur.nombre(valeur.valeur_reelle, absent=tableur.VALEUR_SANS_OBJET),
        "regle": "somme des poches dont l'impôt a pu être estimé",
        "remarque": (
            "PARTIEL : tout n'y est pas, voir les lignes de poche" if valeur.partielle else ""
        ),
    }


def _lignes_valeur_reelle(
    valeur: ValeurReelle, noms: Mapping[tuple[str, Poche], str | None]
) -> Iterator[Mapping[str, str]]:
    for groupe in valeur.par_poche.values():
        for ligne in groupe.lignes:
            yield _ligne_valeur_reelle_position(ligne, noms)
        yield _ligne_valeur_reelle_poche(groupe)
    yield _ligne_valeur_reelle_total(valeur)


def ecrire_valeur_reelle(
    valeur: ValeurReelle, noms: Mapping[tuple[str, Poche], str | None], fichier: Path
) -> Path:
    """Écrit `valeur_reelle.csv` : une ligne par position, puis une par poche, puis le total.

    L'impôt figure sur les lignes de **poche**, pas de position : il se calcule sur la poche
    entière, gains et pertes compensés (et, pour le PEA, sur le plan). Une colonne d'impôt par
    position laisserait croire qu'on peut les additionner.
    """
    return tableur.ecrire(COLONNES_VALEUR_REELLE, _lignes_valeur_reelle(valeur, noms), fichier)


# --- La répartition du portefeuille (étape 7) -----------------------------------------------

NOM_REPARTITION_CLASSES = "repartition_classes.csv"
NOM_REPARTITION_PAYS = "repartition_pays.csv"
NOM_REPARTITION_SECTEURS = "repartition_secteurs.csv"

COLONNES_REPARTITION = (
    "rubrique",
    "nature",
    "zone",
    "code",
    "libelle",
    "montant",
    "part_pour_cent",
    "code_reconnu",
    "base",
    "arrete_du",
    "arrete_au",
    "source",
)
"""Les trois fichiers partagent ces colonnes, et chacun s'ouvre seul.

La colonne `nature` distingue un **poste** (un pays, un secteur) d'un **reste** (non attribué,
non couvert, hors périmètre, actifs numériques). C'est elle qui rend le fichier vérifiable : la
somme de la colonne `montant` vaut exactement la colonne `base`. Sans les restes, le fichier
donnerait l'illusion d'une répartition complète, ce que [D-69] interdit.
"""

NATURE_POSTE = "poste"
NATURE_RESTE = "reste"


def _ligne_repartition(
    repartition: Repartition,
    diversification: Diversification,
    nature: str,
    code: str,
    libelle: str,
    montant: Decimal,
    zone: str | None = None,
    reconnu: bool = True,
) -> dict[str, str]:
    return {
        "rubrique": repartition.rubrique.value,
        "nature": nature,
        "zone": zone if zone else tableur.VALEUR_SANS_OBJET,
        "code": code if code else tableur.VALEUR_SANS_OBJET,
        "libelle": libelle,
        "montant": tableur.nombre(montant),
        "part_pour_cent": tableur.nombre(repartition.pour_cent(montant)),
        "code_reconnu": "oui" if reconnu else "non",
        "base": tableur.nombre(repartition.base),
        "arrete_du": (
            diversification.arrete_du.isoformat()
            if diversification.arrete_du is not None
            else tableur.VALEUR_SANS_OBJET
        ),
        "arrete_au": (
            diversification.arrete_au.isoformat()
            if diversification.arrete_au is not None
            else tableur.VALEUR_SANS_OBJET
        ),
        "source": ", ".join(diversification.sources) or tableur.VALEUR_SANS_OBJET,
    }


def _lignes_de_repartition(
    repartition: Repartition, diversification: Diversification
) -> Iterator[Mapping[str, str]]:
    """Les postes, puis les restes. La somme des montants vaut la base."""
    for poste in repartition.postes:
        yield _ligne_repartition(
            repartition,
            diversification,
            NATURE_POSTE,
            poste.code,
            poste.libelle,
            poste.montant,
            zone=poste.zone_libelle,
            reconnu=poste.reconnu,
        )

    restes = (
        ("hors_perimetre", "Obligations, liquidités et autres", repartition.hors_perimetre),
        ("hors_classification", "Actifs numériques, ni pays ni secteur",
         repartition.hors_classification),
        ("non_attribue", "Non attribué par la source", repartition.non_attribue),
        ("non_couvert", "Non couvert : composition inconnue", repartition.non_couvert),
    )
    for code, libelle, montant in restes:
        if montant > 0:
            yield _ligne_repartition(
                repartition, diversification, NATURE_RESTE, code, libelle, montant
            )


def ecrire_repartition(
    diversification: Diversification, rubrique: Rubrique, fichier: Path
) -> Path:
    """Écrit la répartition d'une rubrique : ses postes, puis ce qui n'y entre pas.

    Trois fichiers plutôt qu'un, parce qu'on ne compare jamais deux rubriques ligne à ligne :
    un secteur et une classe d'actifs ne sont pas de même nature (D-68).
    """
    repartitions = {
        Rubrique.CLASSE: diversification.classes,
        Rubrique.PAYS: diversification.pays,
        Rubrique.SECTEUR: diversification.secteurs,
    }
    repartition = repartitions[rubrique]
    return tableur.ecrire(
        COLONNES_REPARTITION, _lignes_de_repartition(repartition, diversification), fichier
    )
