"""Point d'entrée unique de l'application : `uv run pastory <commande>`.

Les commandes sont ajoutées étape par étape. Celles qui ne sont pas encore écrites le disent
clairement, avec l'étape où elles arrivent, plutôt que d'échouer sans explication.

L'enchaînement normal, au premier usage : télécharger l'export des transactions dans
l'application Trade Republic (Profil > Relevés > Export des transactions), le déposer dans le
dossier `exports` de Pastory (`pastory emplacements` dit où), puis :

```
pastory lire                vérifier qu'aucun type d'opération n'est inconnu
pastory exporter-pivot      écrire les opérations en CSV, à vérifier dans un tableur
pastory actifs              dire où chercher le cours de chaque actif (une seule fois)
pastory cours               récupérer les cours de marché et les garder en cache
pastory positions           ce que le moteur en déduit : quantités, capital investi, PRU,
                              valeur des actifs, gain, TRI et TWRR
pastory exporter-positions  écrire les positions, le journal, la valorisation, les flux,
                              les sous-périodes du TWRR, l'évolution, les coûts et la
                              valeur réelle en CSV
pastory composition         ce qu'il y a à l'intérieur de chaque actif détenu
pastory oublier-cours       effacer des cours en cache, pour les reprendre à la source
pastory oublier-composition effacer des compositions, pour les reprendre à la source
```

`positions` et `exporter-positions` acceptent `--au AAAA-MM-JJ` (la fin de la période, et la
date de valorisation ; par défaut aujourd'hui, valorisé à la dernière clôture connue, D-52) et
`--depuis AAAA-MM-JJ` (le début de la période ; par défaut, depuis la première opération).

Depuis l'étape 6, les deux affichent aussi les **coûts estimés** (spread, frais courants des
ETF) et la **valeur réelle** — ce qu'on récupérerait en vendant tout (D-17, D-23). Les taux
viennent de `pastory/parametres/`, datés et sourcés ; le type de chaque actif et son TER
se déclarent dans `actifs.toml`, que `pastory actifs` propose de remplir.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import sys
import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date as Date
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pastory import tableur
from pastory.adaptateurs.trade_republic import depot as depot_export
from pastory.adaptateurs.trade_republic.lecture import Lecteur
from pastory.adaptateurs.trade_republic.rapport import Rapport
from pastory.config import ConfigurationInvalide, emplacements
from pastory.config import actifs as config_actifs
from pastory.config import fiscalite as config_fiscalite
from pastory.donnees_externes import actions as source_actions
from pastory.donnees_externes import amundi, extraetf, xetra
from pastory.donnees_externes import completion as completion_cours
from pastory.donnees_externes import composition as composition_externe
from pastory.donnees_externes import cours as cours_module
from pastory.donnees_externes.cache import Cache, CacheIllisible
from pastory.donnees_externes.cache_compositions import CacheDeCompositions
from pastory.donnees_externes.completion import Completion
from pastory.donnees_externes.cours import ErreurDeSource, FournisseurDeCours, Refus
from pastory.donnees_externes.yahoo import Yahoo
from pastory.moteur import couts as couts_moteur
from pastory.moteur import diversification as diversification_moteur
from pastory.moteur import export_csv as export_moteur
from pastory.moteur import rapport as rapport_moteur
from pastory.moteur import rendements as rendements_moteur
from pastory.moteur import valeur_reelle as valeur_reelle_moteur
from pastory.moteur import valorisation as valorisation_moteur
from pastory.moteur.portefeuille import Portefeuille
from pastory.parametres import ParametresInvalides
from pastory.parametres import couts as parametres_couts
from pastory.parametres import fiscalite as parametres_fiscalite
from pastory.parametres import referentiels as parametres_referentiels
from pastory.pivot import export_csv
from pastory.pivot.operation import Poche

NOM = "pastory"

NOM_EXPORT_PIVOT = "operations.csv"

DUREE_PAR_DEFAUT = timedelta(days=400)
"""Sur quelle profondeur chercher les cours d'un actif déclaré mais absent de l'export.

Un peu plus d'un an : de quoi couvrir une année complète de valorisation sans télécharger
l'histoire d'un titre qu'on ne détient pas."""

CODE_SUCCES = 0
CODE_ECHEC = 1
CODE_DECLARATION_ATTENDUE = 2
"""La commande s'est arrêtée parce qu'il manque une déclaration (le ticker d'un actif). Un
code distinct de l'échec : rien n'est cassé, il faut compléter."""


def _version() -> str:
    try:
        return version("pastory")
    except PackageNotFoundError:  # pragma: no cover - dépend de l'installation
        return "inconnue (application non installée)"


def commande_emplacements() -> int:
    """Affiche où l'application range les fichiers personnels (D-37)."""
    print("Fichiers personnels (hors du dossier du projet, jamais dans git) :")
    for nom, chemin in emplacements.tous_les_dossiers().items():
        etat = "existe" if chemin.exists() else "pas encore créé"
        print(f"  {nom:<14} {chemin}  [{etat}]")

    # L'application a changé de nom, et son dossier personnel avec elle. Sur une machine
    # où elle tournait déjà, tout est resté dans l'ancien dossier : le dire ici, plutôt
    # que de laisser croire que les données ont disparu.
    for ancien in emplacements.anciens_dossiers_personnels():
        print(
            "\nL'application s'appelait auparavant « DashBoard Trade Republic », et les "
            "fichiers\n"
            f"de cette époque sont restés dans :\n  {ancien}\n"
            "Rien n'a été déplacé automatiquement. Pour les reprendre, déplacez le "
            "contenu de\n"
            "ce dossier dans celui indiqué ci-dessus, puis supprimez l'ancien."
        )
    return CODE_SUCCES


def _dossier(dossier_export: Path | None) -> Path:
    """Le dossier où lire les exports : celui indiqué par `--export`, ou le dossier de dépôt.

    Le dossier de dépôt est créé s'il n'existe pas encore : c'est là que l'utilisateur doit
    déposer son export (D-80), et le message qui l'y invite doit désigner un dossier réel.
    """
    if dossier_export is not None:
        return dossier_export
    dossier = emplacements.dossier_exports()
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def _lire(dossier: Path) -> Rapport:
    """Lecture commune à toutes les commandes : tous les exports du dossier (D-80)."""
    return Lecteur().lire(depot_export.lire_dossier(dossier))


def commande_lire(dossier_export: Path | None) -> int:
    """Affiche le rapport de lecture, sans rien écrire."""
    try:
        rapport = _lire(_dossier(dossier_export))
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(rapport.resume())
    return CODE_SUCCES


def commande_exporter_pivot(dossier_export: Path | None, hors_ligne: bool = False) -> int:
    """Écrit les opérations en CSV, après avoir affiché le rapport de lecture.

    Les prix manquants sont complétés comme pour `positions` : sans cela, ce fichier
    montrerait « à compléter » là où le rapport des positions montre un montant, et c'est
    justement le fichier que le propriétaire ouvre pour vérifier.
    """
    try:
        rapport = _lire(_dossier(dossier_export))
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(rapport.resume())

    try:
        completion = completion_cours.completer_les_prix(
            rapport.operations, _fournisseur_de_cours(hors_ligne)
        )
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except (ParametresInvalides, ConfigurationInvalide) as erreur:
        # Un taux sans source, une date de PEA mal écrite : c'est un fichier à corriger,
        # pas une panne. Le message dit lequel et où.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    fichier = export_csv.ecrire(
        completion.operations, emplacements.dossier_personnel() / NOM_EXPORT_PIVOT
    )
    print(f"\n{len(completion.operations)} opération(s) écrite(s) dans :\n  {fichier}")
    print("Ouvrez ce fichier dans un tableur pour comparer avec l'application Trade Republic.")
    for ligne in _rapport_des_cours(completion, completion.refus):
        print(ligne)
    return CODE_SUCCES


# --- Le moteur (étape 3) -------------------------------------------------------------


def _etat_de_la_lecture(rapport: Rapport) -> list[str]:
    """Un résumé en deux lignes de la lecture dont les chiffres sortent.

    Le moteur ne recalcule pas ce que `pastory lire` a déjà dit, mais il ne peut pas non
    plus laisser croire que tout va bien : un type inconnu peut cacher des opérations sur
    les actifs (règle 5 de CLAUDE.md), et alors aucun chiffre ci-dessous n'est complet.
    """
    lignes = [f"{len(rapport.operations)} opération(s) lues."]
    ennuis = []
    if rapport.types_inconnus:
        ennuis.append(f"{sum(rapport.types_inconnus.values())} ligne(s) de type non traité")
    if rapport.operations_non_produites:
        # Une ligne d'un type traité dont aucune opération n'est sortie fausse les totaux : des
        # parts ou des montants y manquent — ou, pour une annulation non interprétée, y sont
        # en trop. Rien d'autre que cette bannière ne le dirait.
        ennuis.append(
            f"{rapport.operations_non_produites} ligne(s) d'un type traité sans opération produite"
        )
    if rapport.anomalies:
        ennuis.append(f"{len(rapport.anomalies)} contrôle(s) de cohérence en échec")
    # Le dossier de dépôt lui-même : un trou entre deux exports ou un fichier ignoré ne
    # produit aucune anomalie, et peut pourtant faire manquer des opérations (D-45).
    ennuis.extend(rapport.reserves_du_depot())
    if ennuis:
        lignes.extend(
            textwrap.wrap(
                "ATTENTION - " + ", ".join(ennuis) + f" : lancez « {NOM} lire » avant de vous "
                "fier aux chiffres ci-dessous.",
                width=100,
                break_on_hyphens=False,
            )
        )
    return lignes


def _fournisseur_de_cours(hors_ligne: bool = False) -> FournisseurDeCours:
    """Réunit la correspondance ISIN vers ticker, le cache local et la source.

    **C'est le seul endroit de l'application qui nomme Yahoo** (D-51). Le moteur ne sait pas
    d'où viennent les cours, et changer de source ne toucherait que cette fonction (D-26).
    """
    return FournisseurDeCours(
        config_actifs.charger(),
        Cache(),
        None if hors_ligne else Yahoo(),
        hors_ligne=hors_ligne,
    )


def _parametres_des_couts() -> couts_moteur.ParametresDeCouts:
    """Le barème livré avec l'application, croisé avec ce que l'utilisateur a déclaré.

    C'est **le seul endroit** qui réunit les deux : le moteur, lui, ne connaît qu'un protocole
    (`ParametresDeCouts`) et ne sait ni ce qu'est un fichier TOML, ni ce qu'est un ETF (D-26).
    """
    return parametres_couts.ParametresDuPortefeuille(
        parametres_couts.charger(), config_actifs.charger()
    )


def _fournisseur_de_compositions(
    hors_ligne: bool = False,
) -> composition_externe.FournisseurDeCompositions:
    """Réunit le cache local, la source des fonds et celle des actions (D-63, D-70).

    **C'est le seul endroit de l'application qui nomme extraETF et GLEIF.** Le moteur ne sait pas
    d'où viennent les compositions : il déclare un protocole, et changer de source ne toucherait
    que cette fonction (D-26).

    Le type déclaré de chaque actif décide de la source interrogée : un ETF et une action ne se
    regardent pas au même endroit, et une crypto ne se regarde nulle part (D-68).

    **Les sources de secours sont branchées ici, et employées nulle part par défaut** (D-72,
    D-77) : elles n'interviennent que pour un actif qui les demande par son « secours » dans
    `actifs.toml`. Les construire n'appelle rien — c'est la première demande qui le fait.
    """
    return composition_externe.FournisseurDeCompositions(
        cache=CacheDeCompositions(),
        source_etf=None if hors_ligne else extraetf.SourceExtraEtf(),
        source_action=None if hors_ligne else source_actions.SourceDActions(),
        actifs=config_actifs.charger(),
        hors_ligne=hors_ligne,
        secours={} if hors_ligne else _sources_de_secours(),
    )


def _sources_de_secours() -> dict[str, composition_externe.SourceDeCompositionDEtf]:
    """Les sources de secours, par le nom sous lequel un actif les demande (D-77).

    Une seule pour l'instant. Sa table de libellés de pays est chargée ici, parce que c'est ici
    qu'on sait qu'elle existe : le moteur n'a jamais à connaître ni Amundi, ni un fichier TOML.
    """
    return {"amundi": amundi.SourceAmundi(parametres_referentiels.charger_libelles_de_pays())}


def _referentiels() -> parametres_referentiels.Referentiels:
    """Les secteurs, les pays et leurs zones, avec leur source et leur date (D-65 à D-67)."""
    return parametres_referentiels.charger_tout()


def _regles_fiscales() -> parametres_fiscalite.ReglesFiscales:
    """Les taux datés et sourcés, plus la date du premier versement du PEA (D-58, D-59)."""
    return parametres_fiscalite.charger(
        premier_versement_pea=config_fiscalite.charger().premier_versement_pea
    )


def _rapport_des_compositions(
    fournisseur: composition_externe.FournisseurDeCompositions | None,
) -> list[str]:
    """Ce qui a empêché de connaître la composition d'un actif, dit en clair.

    Bloc à part, comme celui des cours : un actif absent d'une répartition doit trouver son
    explication quelque part, sinon l'utilisateur croit à un oubli du programme (D-62, D-69).
    """
    if fournisseur is None or not fournisseur.refus:
        return []

    lignes = ["", "Compositions", "-" * 12]
    for categorie, refus in composition_externe.grouper_refus(fournisseur.refus):
        lignes.append(f"  {categorie} : {len(refus)} actif(s)")
        for un in refus:
            lignes += _enveloppe_cours(un.motif, un.actif)
    return lignes


def _rapport_des_cours(completion: Completion, refus: Sequence[Refus]) -> list[str]:
    """Ce que les cours ont changé aux opérations, et ce qu'ils n'ont pas pu changer.

    Bloc à part, avant les chiffres du moteur : un montant déduit d'un cours de marché n'est
    pas un montant donné par la banque, et l'utilisateur doit pouvoir refaire la
    multiplication (D-15, règle 6 de CLAUDE.md).

    `refus` réunit **tous** les refus du fournisseur — ceux de la complétion et ceux de la
    valorisation — puisque c'est le même fournisseur qui a servi aux deux.
    """
    if completion.rien_a_completer and not refus:
        return []

    lignes = ["", "Cours de marché", "-" * 15]

    if completion.prix_completes:
        lignes.append(
            f"  {len(completion.prix_completes)} prix complété(s) à partir d'un cours de "
            "marché (D-15) :"
        )
        for prix in completion.prix_completes:
            quantite = tableur.nombre_lisible(prix.quantite)
            cours = tableur.nombre_lisible(prix.cours.valeur)
            montant = tableur.nombre_lisible(prix.montant_brut)
            lignes.append(
                f"    {prix.actif:<14} {prix.poche.value:<7} {prix.date_operation.isoformat()}"
                f"   {quantite} x {cours} = {montant} {prix.cours.devise}"
            )
            origine = f"cours du {prix.cours.date.isoformat()}"
            if prix.jour_decale:
                origine += f" (dernier jour coté avant le {prix.date_operation.isoformat()})"
            lignes.append(f"    {'':<14} {'':<7} {origine}, {prix.cours.place}, "
                          f"{prix.cours.source}")
        lignes.append(
            "  Ces montants sont déduits, pas donnés par la banque. Dans operations.csv,"
        )
        lignes.append(
            "  écrit par « exporter-pivot », la colonne « origine montant_brut » le dit :"
        )
        lignes.append("  elle vaut « deduction » au lieu de « donnee ».")

    if completion.incompletes:
        lignes.append("")
        lignes.append(
            f"  {completion.incompletes} opération(s) attendent toujours un prix. Leurs parts"
        )
        lignes.append("  sont comptées, leur montant non : le capital investi est sous-estimé.")

    if refus:
        lignes.append("")
        lignes.append("  Ce que la source de cours a refusé, avec la date demandée quand elle")
        lignes.append("  compte. Un actif détenu sans cours à la date de valorisation sort des")
        lignes.append("  totaux : voir « Non valorisés » dans le rapport.")
    for un_refus in refus:
        lignes += _enveloppe_cours(f"{un_refus.categorie} : {un_refus.motif}", un_refus.actif)

    return lignes


def _enveloppe_cours(texte: str, actif: str) -> list[str]:
    """Une phrase de refus, coupée à une largeur lisible, suivie de l'actif concerné."""
    return textwrap.wrap(
        f"{texte} [{actif}]", width=96, initial_indent="    - ", subsequent_indent="      "
    )


@dataclass(frozen=True)
class Construit:
    """Tout ce qu'une commande du moteur a sous la main après la lecture et le rejeu."""

    portefeuille: Portefeuille
    """Arrêté à la fin de la période."""

    rapport: Rapport
    entete: list[str]
    completion: Completion
    fournisseur: FournisseurDeCours
    """Le même pour la complétion et la valorisation : ses refus couvrent les deux."""

    periode: rendements_moteur.Periode
    synthese: rendements_moteur.Synthese

    detail_des_couts: couts_moteur.DetailDesCouts
    """Les coûts payés de la période et les coûts estimés (étape 6)."""

    valeur_reelle: valeur_reelle_moteur.ValeurReelle
    """Ce qu'on récupérerait en vendant tout à la date de valorisation (D-23)."""

    diversification: diversification_moteur.Diversification | None = None
    """Les trois répartitions (étape 7). `None` si aucune composition n'est disponible."""

    compositions: composition_externe.FournisseurDeCompositions | None = None
    """Gardé pour que les refus de compositions soient affichés après les chiffres."""


def _periode(au: Date | None, depuis: Date | None) -> rendements_moteur.Periode | None:
    """La période des chiffres clés, ou `None` avec un message si elle est à l'envers.

    Sans `--au`, elle finit aujourd'hui — valorisé à la dernière clôture connue, puisque la
    séance du jour n'est pas close (D-52). Vérifiée **avant** toute lecture : une période
    impossible ne doit pas coûter un export lu et des cours demandés pour rien.
    """
    try:
        return rendements_moteur.Periode(fin=au or Date.today(), debut=depuis)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return None


def _construire_moteur(
    dossier: Path, periode: rendements_moteur.Periode, hors_ligne: bool = False
) -> Construit:
    """Lecture, complétion des prix, rejeu, puis valorisation et rendements.

    La complétion s'insère **entre** la lecture et le moteur, et ne produit que du format
    pivot : le moteur ne gagne pas une ligne et ne sait rien des cours (D-26). La
    valorisation, elle, reçoit le fournisseur de cours **en paramètre** : le moteur déclare
    ce dont il a besoin, et c'est ici, et seulement ici, qu'on le lui donne.
    """
    rapport = _lire(dossier)

    fournisseur = _fournisseur_de_cours(hors_ligne)
    completion = completion_cours.completer_les_prix(rapport.operations, fournisseur)

    portefeuille = Portefeuille.construire(completion.operations).au(periode.fin)
    synthese = rendements_moteur.synthese(portefeuille, periode, fournisseur)

    # Les coûts et la valeur réelle partent de la **même** valorisation que les rendements :
    # deux valorisations du même jour pourraient différer d'un centime, et le propriétaire
    # verrait deux valeurs brutes dans le même rapport.
    parametres = _parametres_des_couts()
    detail = couts_moteur.detailler(
        portefeuille, periode, synthese.valorisation, parametres
    )
    valeur = valeur_reelle_moteur.valeur_reelle(
        portefeuille, synthese.valorisation, parametres, _regles_fiscales()
    )

    # La répartition part de la **même** valorisation que tout le reste : c'est elle qui fournit
    # les poids, et deux valorisations du même jour pourraient différer d'un centime.
    compositions = _fournisseur_de_compositions(hors_ligne)
    diversification = diversification_moteur.diversifier(
        synthese.valorisation, compositions, _referentiels()
    )
    return Construit(
        portefeuille=portefeuille,
        rapport=rapport,
        entete=_etat_de_la_lecture(rapport),
        completion=completion,
        fournisseur=fournisseur,
        periode=periode,
        synthese=synthese,
        detail_des_couts=detail,
        valeur_reelle=valeur,
        diversification=diversification,
        compositions=compositions,
    )


def commande_positions(
    dossier_export: Path | None,
    au: Date | None,
    hors_ligne: bool = False,
    depuis: Date | None = None,
) -> int:
    """Affiche les positions calculées par le moteur, sans rien écrire."""
    periode = _periode(au, depuis)
    if periode is None:
        return CODE_ECHEC
    try:
        construit = _construire_moteur(_dossier(dossier_export), periode, hors_ligne)
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except (ParametresInvalides, ConfigurationInvalide) as erreur:
        # Un taux sans source, une date de PEA mal écrite : c'est un fichier à corriger,
        # pas une panne. Le message dit lequel et où.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in construit.entete:
        print(ligne)
    if au is not None:
        print(f"Chiffres arrêtés au {au.isoformat()}.")

    print(
        rapport_moteur.resume(
            construit.portefeuille,
            arrete_au=au,
            synthese=construit.synthese,
            detail_des_couts=construit.detail_des_couts,
            valeur_reelle_estimee=construit.valeur_reelle,
            diversification_estimee=construit.diversification,
        )
    )

    # Après les chiffres, et non avant : le rapport du moteur porte en tête l'avertissement
    # qu'il contient de vraies valeurs, et rien ne doit s'intercaler devant.
    for ligne in _rapport_des_cours(construit.completion, construit.fournisseur.refus):
        print(ligne)
    for ligne in _rapport_des_compositions(construit.compositions):
        print(ligne)

    return CODE_SUCCES


def _premier_jour(portefeuille: Portefeuille) -> Date | None:
    """Le jour de la première opération, d'où part l'évolution."""
    jours = [position.journal[0].date for position in portefeuille.positions if position.journal]
    return min(jours) if jours else None


def commande_exporter_positions(
    dossier_export: Path | None,
    au: Date | None,
    hors_ligne: bool = False,
    depuis: Date | None = None,
) -> int:
    """Écrit les six CSV du moteur dans le dossier personnel."""
    periode = _periode(au, depuis)
    if periode is None:
        return CODE_ECHEC
    try:
        construit = _construire_moteur(_dossier(dossier_export), periode, hors_ligne)
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except (ParametresInvalides, ConfigurationInvalide) as erreur:
        # Un taux sans source, une date de PEA mal écrite : c'est un fichier à corriger,
        # pas une panne. Le message dit lequel et où.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in construit.entete:
        print(ligne)

    portefeuille, synthese = construit.portefeuille, construit.synthese
    personnel = emplacements.dossier_personnel()
    fichier_positions = export_moteur.ecrire_positions(
        portefeuille, personnel / export_moteur.NOM_POSITIONS
    )
    fichier_journal = export_moteur.ecrire_journal(
        portefeuille, personnel / export_moteur.NOM_JOURNAL
    )
    fichier_valorisation = export_moteur.ecrire_valorisation(
        portefeuille, synthese, personnel / export_moteur.NOM_VALORISATION
    )
    fichier_flux = export_moteur.ecrire_flux(synthese, personnel / export_moteur.NOM_FLUX)
    fichier_sous_periodes = export_moteur.ecrire_sous_periodes(
        synthese, personnel / export_moteur.NOM_SOUS_PERIODES
    )

    premier = _premier_jour(portefeuille)
    points = (
        valorisation_moteur.evolution(
            portefeuille, premier, construit.periode.fin, construit.fournisseur
        )
        if premier is not None
        else []
    )
    fichier_evolution = export_moteur.ecrire_evolution(
        points, personnel / export_moteur.NOM_EVOLUTION
    )
    fichier_couts = export_moteur.ecrire_couts(
        construit.detail_des_couts, personnel / export_moteur.NOM_COUTS
    )
    fichier_valeur_reelle = export_moteur.ecrire_valeur_reelle(
        construit.valeur_reelle,
        construit.detail_des_couts.noms,
        personnel / export_moteur.NOM_VALEUR_REELLE,
    )

    fichiers_repartition: list[Path] = []
    fichier_origines: Path | None = None
    if construit.diversification is not None:
        for rubrique, nom in (
            (diversification_moteur.Rubrique.CLASSE, export_moteur.NOM_REPARTITION_CLASSES),
            (diversification_moteur.Rubrique.PAYS, export_moteur.NOM_REPARTITION_PAYS),
            (diversification_moteur.Rubrique.SECTEUR, export_moteur.NOM_REPARTITION_SECTEURS),
        ):
            fichiers_repartition.append(
                export_moteur.ecrire_repartition(
                    construit.diversification, rubrique, personnel / nom
                )
            )
        # L'origine de chaque composition, dans le tableur et pas seulement à l'écran : sans
        # elle, on ne peut pas contrôler quel actif a suivi quelle règle de pays (D-66, D-72).
        if construit.diversification.origines:
            fichier_origines = export_moteur.ecrire_origines(
                construit.diversification, personnel / export_moteur.NOM_ORIGINES
            )

    # Après l'évolution, et non avant : elle demande un cours par jour, et ses refus doivent
    # figurer dans ce bloc — sans quoi une colonne « positions_non_valorisees » à 1 n'aurait
    # d'explication nulle part.
    for ligne in _rapport_des_cours(construit.completion, construit.fournisseur.refus):
        print(ligne)

    print(f"\n{len(portefeuille.positions)} position(s) écrite(s) dans :\n  {fichier_positions}")
    lignes = sum(len(position.journal) for position in portefeuille.positions)
    print(f"{lignes} ligne(s) de journal dans :\n  {fichier_journal}")
    print(
        f"Valeur, plus-value latente, gain, TRI et TWRR par position, au "
        f"{construit.periode.fin.isoformat()} :\n  {fichier_valorisation}"
    )
    print(f"Les flux de la période, à coller dans TRI.PAIEMENTS :\n  {fichier_flux}")
    print(f"Les sous-périodes du TWRR :\n  {fichier_sous_periodes}")
    print(f"{len(points)} jour(s) d'évolution de la valeur dans :\n  {fichier_evolution}")
    print(
        f"{len(construit.detail_des_couts.lignes)} opération(s) et leurs coûts dans :"
        f"\n  {fichier_couts}"
    )
    print(f"La valeur réelle et l'impôt estimé, poche par poche :\n  {fichier_valeur_reelle}")
    for fichier in fichiers_repartition:
        print(f"Répartition, avec ce qui n'y entre pas :\n  {fichier}")
    if fichier_origines is not None:
        print(
            "Source et règle de pays de chaque composition, pour les vérifier une par une :"
            f"\n  {fichier_origines}"
        )

    for ligne in _rapport_des_compositions(construit.compositions):
        print(ligne)

    print(
        "\nLe journal est celui à ouvrir pour refaire un chiffre à la main : une ligne par\n"
        "opération, avec l'état d'avant et l'état d'après. Pour le TRI, c'est flux.csv ;\n"
        "pour les coûts, couts.csv ; pour l'impôt estimé, valeur_reelle.csv ; pour la\n"
        "répartition, repartition_pays.csv, dont la colonne « montant » somme à la colonne\n"
        "« base »."
    )
    return CODE_SUCCES


def _apercu_des_actifs(rapport: Rapport) -> dict[str, str]:
    """Par actif, de quoi le reconnaître dans le fichier de correspondance.

    Le nom affiché par la banque et les poches où l'actif est détenu. Le nom ne sert à aucun
    calcul (règle 4 de CLAUDE.md) ; il n'est là que pour que le propriétaire sache de quel
    titre on parle, dans un fichier qui reste sur sa machine.
    """
    noms: dict[str, str] = {}
    poches: dict[str, set[str]] = collections.defaultdict(set)
    for operation in rapport.operations:
        poches[operation.actif].add(operation.poche.value)
        if operation.nom_actif and operation.actif not in noms:
            noms[operation.actif] = operation.nom_actif

    return {
        actif: " - ".join(
            partie
            for partie in (noms.get(actif), ", ".join(sorted(poches[actif])))
            if partie
        )
        for actif in poches
    }


def commande_actifs(dossier_export: Path | None, hors_ligne: bool = False) -> int:
    """Assistant « déclarer ses actifs » : de l'ISIN au ticker (D-48, D-51).

    L'application **propose**, l'utilisateur **valide**. Une proposition dans une autre
    monnaie que l'euro est écrite en commentaire, donc inactive : c'est le garde-fou de D-48
    au niveau du fichier, parce que la recherche automatique renvoie parfois la cotation
    londonienne en dollars d'un ETF qui cote aussi en euros.

    **Avec `--export`, rien n'est écrit** : les actifs d'un export qui n'est pas le sien
    appartiennent à quelqu'un d'autre (règle 2 de CLAUDE.md).
    """
    try:
        rapport = _lire(_dossier(dossier_export))
        configuration = config_actifs.charger()
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except ConfigurationInvalide as erreur:
        # C'est la commande censée aider à corriger ce fichier : elle l'explique.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    apercu = _apercu_des_actifs(rapport)
    if not apercu:
        print("Aucun actif n'apparaît dans cet export.")
        return CODE_SUCCES

    manquants = configuration.manquants(apercu)
    propositions: dict[str, config_actifs.Proposition] = {}
    # Avec --export, **aucune** recherche n'est lancée : envoyer les ISIN de quelqu'un d'autre
    # à un service extérieur, ce serait divulguer ce qu'il détient (règle 2 de CLAUDE.md).
    # L'assistant se contente alors d'afficher ce qu'il a trouvé dans le fichier.
    if manquants and not hors_ligne and dossier_export is None:
        print(f"Recherche d'un ticker pour {len(manquants)} actif(s) sans correspondance...")
        yahoo = Yahoo()
        for actif in manquants:
            proposition = yahoo.chercher(actif)
            if proposition is not None:
                propositions[actif] = proposition

    # Les frais courants, pour tous les actifs : même ceux déjà déclarés peuvent attendre leur
    # TER, puisqu'il n'existe que depuis l'étape 6. La proposition reste une proposition : elle
    # est écrite en commentaire au-dessus d'une ligne déjà validée (D-61).
    if not hors_ligne and dossier_export is None:
        propositions = _completer_par_les_frais_courants(
            propositions, apercu, configuration
        )

    # Une crypto n'a pas d'ISIN : la recherche par ISIN ne trouvera jamais rien, et il faut le
    # dire plutôt que de laisser croire à un échec passager. L'export officiel donne son code
    # de marché (`BTC`), d'où la forme du ticker. Son application automatique, contrôlée par la
    # devise, est l'affaire de l'étape 8 quater (D-80).
    cryptos = {
        operation.actif for operation in rapport.operations if operation.poche is Poche.CRYPTO
    }

    print(f"\n{len(apercu)} actif(s) dans l'export, {len(manquants)} sans correspondance.")
    for actif in sorted(apercu):
        declaration = configuration.declaration(actif)
        if declaration is not None:
            etat = f"déclaré : {declaration.ticker} ({declaration.devise})"
            if declaration.type is not None:
                etat += f", {declaration.type.value}"
            if declaration.ter_pour_cent is not None:
                etat += f", TER {tableur.nombre_lisible(declaration.ter_pour_cent)} %"
            elif declaration.type in (None, config_actifs.TypeActif.ETF):
                # Seul un ETF prélève des frais courants : réclamer un TER pour une action ou
                # une crypto enverrait chercher un chiffre qui n'existe pas.
                etat += ", TER à compléter"
        elif actif in propositions:
            proposition = propositions[actif]
            etat = f"proposé : {proposition.ticker}"
            if proposition.devise:
                etat += f" ({proposition.devise})"
            if proposition.douteuse:
                etat += " - ATTENTION, pas en euros, à ne pas retenir tel quel"
        elif actif in cryptos:
            etat = (
                "à compléter à la main : une crypto n'a pas d'ISIN. Son ticker est de la forme "
                f"{actif}-EUR (la cotation en euros)"
            )
        else:
            etat = "à compléter à la main"
        print(f"  {actif:<14} {etat}")
        if apercu[actif]:
            print(f"  {'':<14} {apercu[actif]}")

    if dossier_export is not None:
        print(
            "\nRien n'a été écrit : cet export a été lu depuis un dossier que vous avez "
            f"indiqué,\net ses actifs ne sont pas forcément les vôtres. Pour déclarer les "
            f"vôtres,\nlancez « {NOM} actifs » sans --export."
        )
        return CODE_SUCCES

    fichier = config_actifs.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        config_actifs.modele(apercu, propositions, configuration), encoding="utf-8"
    )

    print(f"\nOuvrez ce fichier et vérifiez chaque ligne :\n  {fichier}\n")
    print("Une ligne vide veut dire « pas valorisé » : l'actif sera signalé, jamais estimé.")
    print("Le « type » choisit le spread estimé ; le TER, proposé depuis la liste de Xetra,")
    print("est à vérifier sur la fiche de l'émetteur : la liste est parfois en retard sur une")
    print("baisse de frais. Sans type ni TER, rien n'est estimé pour cet actif.")
    if manquants:
        print(f"\n{len(manquants)} actif(s) attendent votre validation.")
        print(f"Ensuite, lancez « {NOM} cours » pour récupérer les cours.")
    else:
        print("\nTous les actifs de cet export sont déjà déclarés.")
    return CODE_SUCCES


def _liste_des_etf() -> xetra.ListeXetra:
    """La liste des ETF de Xetra, d'où viennent les frais courants proposés (D-61).

    Fonction à part, et non un appel direct, pour la même raison que `_fournisseur_de_cours` :
    c'est **le seul endroit** qui nomme la source, et les tests la remplacent ici — aucun test
    du projet ne sort de la machine.
    """
    return xetra.telecharger()


def _completer_par_les_frais_courants(
    propositions: dict[str, config_actifs.Proposition],
    apercu: Mapping[str, str],
    configuration: config_actifs.Configuration,
) -> dict[str, config_actifs.Proposition]:
    """Ajoute à chaque proposition le TER trouvé dans la liste des ETF de Xetra (D-61).

    Un échec n'interrompt rien : la liste est un confort, pas une dépendance. Sans elle, les
    frais courants restent à saisir à la main, et l'assistant le dit.
    """
    a_completer = [
        actif
        for actif in apercu
        if (declaration := configuration.declaration(actif)) is None
        or declaration.ter_pour_cent is None
    ]
    if not a_completer:
        return propositions

    print("Recherche des frais courants (TER) dans la liste des ETF de Xetra...")
    try:
        liste = _liste_des_etf()
    except ErreurDeSource as erreur:
        print(f"  {erreur}", file=sys.stderr)
        print(
            "  Les frais courants des ETF resteront à saisir à la main, depuis la fiche de\n"
            "  l'émetteur ou son document d'information clé.",
            file=sys.stderr,
        )
        return propositions

    print(f"  {len(liste)} ETF dans la liste" + (
        f", au {liste.date.isoformat()}." if liste.date else "."
    ))
    completees = dict(propositions)
    trouves = 0
    for actif in a_completer:
        frais = liste.frais_courants(actif)
        if frais is None:
            continue
        trouves += 1
        existante = completees.get(actif)
        if existante is None:
            declaration = configuration.declaration(actif)
            ticker = declaration.ticker if declaration is not None else ""
            completees[actif] = config_actifs.Proposition(
                ticker=ticker,
                type=config_actifs.TypeActif.ETF,
                frais_courants=frais,
            )
        else:
            completees[actif] = replace(
                existante,
                frais_courants=frais,
                type=existante.type or config_actifs.TypeActif.ETF,
            )
    print(f"  {trouves} actif(s) avec des frais courants proposés.")
    return completees


def commande_cours(dossier_export: Path | None, actif_demande: str | None = None) -> int:
    """Récupère les cours des actifs déclarés et les garde en cache (D-50).

    La période demandée va de la **première opération** sur l'actif à aujourd'hui : c'est ce
    qui permettra de valoriser le portefeuille dans le temps (étape 5) sans y revenir. Un
    cours déjà en cache n'est jamais redemandé.
    """
    try:
        rapport = _lire(_dossier(dossier_export))
        configuration = config_actifs.charger()
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    premiere_operation: dict[str, Date] = {}
    for operation in rapport.operations:
        actuelle = premiere_operation.get(operation.actif)
        if actuelle is None or operation.date < actuelle:
            premiere_operation[operation.actif] = operation.date

    if not configuration.declarations:
        print(
            f"Aucun actif n'est déclaré : lancez d'abord « {NOM} actifs », qui dit où "
            "chercher le cours de chaque actif.",
            file=sys.stderr,
        )
        return CODE_DECLARATION_ATTENDUE

    if actif_demande is not None and actif_demande not in configuration.declarations:
        print(
            f"L'actif {actif_demande} n'est pas déclaré : ajoutez-le dans "
            f"{config_actifs.chemin()}, ou lancez « {NOM} actifs ».",
            file=sys.stderr,
        )
        return CODE_DECLARATION_ATTENDUE

    a_remplir = sorted(
        actif
        for actif in configuration.actifs_declares
        if actif_demande is None or actif == actif_demande
    )

    fournisseur = _fournisseur_de_cours()
    cache = Cache()
    aujourd_hui = Date.today()
    total_nouveaux = 0

    print(
        f"Récupération des cours pour {len(a_remplir)} actif(s), "
        f"source : {fournisseur.nom_source}."
    )
    print("Les cours déjà en cache ne sont pas redemandés (D-50).\n")

    try:
        for actif in a_remplir:
            premiere = premiere_operation.get(actif)
            # On commence **avant** la première opération : des titres reçus un dimanche sont
            # valorisés au cours du vendredi, qui précède donc toute opération sur l'actif.
            debut = (
                premiere - cours_module.MARGE_AVANT
                if premiere is not None
                else aujourd_hui - DUREE_PAR_DEFAUT
            )
            nouveaux = fournisseur.remplir(actif, debut, aujourd_hui)
            total_nouveaux += nouveaux
            resume = cache.resume(actif)
            if resume.nombre == 0:
                print(f"  {actif:<14} aucun cours")
                continue
            periode = f"du {resume.premier_jour.isoformat()} au {resume.dernier_jour.isoformat()}"
            print(
                f"  {actif:<14} {resume.nombre:>5} cours en cache ({nouveaux:>4} nouveau(x))"
                f"   {periode}   {resume.place}"
            )
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except (ParametresInvalides, ConfigurationInvalide) as erreur:
        # Un taux sans source, une date de PEA mal écrite : c'est un fichier à corriger,
        # pas une panne. Le message dit lequel et où.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(f"\n{total_nouveaux} cours ajouté(s) au cache :\n  {cache.dossier}")

    refus = fournisseur.refus
    if refus:
        # La sortie normale est vidée d'abord : sans cela, les deux flux s'entremêlent dès que
        # l'affichage est redirigé, et le rapport devient incompréhensible.
        sys.stdout.flush()
        print(f"\n{len(refus)} actif(s) sans cours :", file=sys.stderr)
        for un_refus in refus:
            motif = f"{un_refus.categorie} : {un_refus.motif}"
            for ligne in _enveloppe_cours(motif, un_refus.actif):
                print(ligne, file=sys.stderr)
        return CODE_DECLARATION_ATTENDUE

    print(f"\nLancez « {NOM} positions » pour voir les chiffres.")
    return CODE_SUCCES


def commande_oublier_cours(actif: str | None, tout: bool) -> int:
    """Efface des cours en cache pour les reprendre à la source (D-50).

    Deux cas, rares et visibles à l'œil : une correction de la source après coup, et un
    regroupement d'actions, qui réécrit d'un coup toute la série passée d'un actif. Le reste
    du temps, un cours est définitif — c'est ce qui rend les chiffres stables d'un lancement
    à l'autre.

    Sans `--actif`, il faut `--tout` : effacer tout le cache par inadvertance obligerait à
    tout retélécharger.
    """
    cache = Cache()
    if actif is None and not tout:
        print(
            "Précisez ce qu'il faut oublier : « --actif <ISIN> » pour un seul actif, ou "
            "« --tout » pour l'ensemble du cache.",
            file=sys.stderr,
        )
        return CODE_ECHEC

    try:
        oublies = cache.oublier(actif)
    except ValueError:
        # L'identifiant est tapé à la main : il peut être vide ou n'être que des espaces.
        print(
            f"« {actif} » n'est pas un identifiant d'actif utilisable. Donnez l'ISIN tel "
            "qu'il apparaît dans « pastory positions ».",
            file=sys.stderr,
        )
        return CODE_ECHEC

    if not oublies:
        cible = f"l'actif {actif}" if actif else "le cache"
        print(f"Rien à oublier : aucun cours en cache pour {cible}.")
        return CODE_SUCCES

    print(f"{len(oublies)} actif(s) oublié(s) : {', '.join(oublies)}")
    print(f"Lancez « {NOM} cours » pour les reprendre à la source.")
    return CODE_SUCCES


def commande_composition(dossier_export: Path | None, hors_ligne: bool = False) -> int:
    """Montre ce que l'application sait de l'intérieur de chaque actif détenu.

    Commande à part, et non un bout de `positions`, pour la même raison qui a séparé
    `cours` : elle **demande** les compositions manquantes, donc elle parle au réseau, et
    l'utilisateur doit savoir quand cela arrive (D-63).
    """
    try:
        rapport = _lire(_dossier(dossier_export))
        portefeuille = Portefeuille.construire(rapport.operations)
        fournisseur = _fournisseur_de_compositions(hors_ligne)
        referentiels = _referentiels()
    except depot_export.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except (ParametresInvalides, ConfigurationInvalide) as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    detenues = portefeuille.positions_detenues
    if not detenues:
        print("Aucune position détenue : il n'y a aucune composition à chercher.")
        return CODE_SUCCES

    print(f"{len(detenues)} position(s) détenue(s). Nomenclature : {referentiels.nomenclature}.")
    print("")
    for position in sorted(detenues, key=lambda une: une.actif):
        if position.poche is Poche.CRYPTO:
            print(
                f"  {position.actif:<16} actif numérique : ni pays ni secteur, présenté à part "
                "(ce n'est pas une donnée manquante)"
            )
            continue
        composition = fournisseur.composition(position.actif)
        if composition is None:
            print(f"  {position.actif:<16} aucune composition (voir le motif ci-dessous)")
            continue
        replication = f", {composition.replication}" if composition.replication else ""
        if not composition.pays and not composition.secteurs:
            # Un ETF d'obligations ou de matières premières : il a bien une composition, elle
            # n'a simplement ni pays ni secteur. Le dire ainsi, et non « 0 pays », évite de
            # faire passer une nature d'actif pour une donnée manquante (D-71).
            classes = ", ".join(
                referentiels.classe(part.code).libelle
                if referentiels.classe(part.code) is not None
                else part.code
                for part in composition.classes
            )
            print(
                f"  {position.actif:<16} {classes or 'classe inconnue'} : ni pays ni secteur "
                f"au sens des actions (ce n'est pas une donnée manquante)"
            )
        else:
            print(
                f"  {position.actif:<16} {len(composition.pays)} pays, "
                f"{len(composition.secteurs)} secteur(s), arrêté au "
                f"{composition.arrete_le.isoformat()}{replication}"
            )
        if composition.document is not None:
            print(f"  {'':<16} à vérifier sur : {composition.document}")

    for ligne in _rapport_des_compositions(fournisseur):
        print(ligne)

    print("")
    for origine in referentiels.origines:
        print(f"  {origine}")
    print(f"\nLancez « {NOM} positions » pour voir la répartition du portefeuille.")
    return CODE_SUCCES


def commande_oublier_composition(actif: str | None, tout: bool) -> int:
    """Efface des compositions en cache pour les reprendre à la source (D-70).

    Contrairement aux cours, une composition n'est **pas** définitive : celle d'un ETF change
    chaque mois. Cette commande sert donc régulièrement, et pas seulement en cas d'erreur —
    c'est elle qui rafraîchit une répartition devenue vieille.
    """
    cache = CacheDeCompositions()
    if actif is None and not tout:
        print(
            "Précisez ce qu'il faut oublier : « --actif <ISIN> » pour un seul actif, ou "
            "« --tout » pour l'ensemble des compositions.",
            file=sys.stderr,
        )
        return CODE_ECHEC

    oublies = cache.oublier(actif)
    if not oublies:
        cible = f"l'actif {actif}" if actif else "le cache"
        print(f"Rien à oublier : aucune composition en mémoire pour {cible}.")
        return CODE_SUCCES

    print(f"{len(oublies)} composition(s) oubliée(s) : {', '.join(oublies)}")
    print(f"Lancez « {NOM} composition » pour les reprendre à la source.")
    return CODE_SUCCES


def _a_venir(commande: str, etape: str) -> int:
    print(f"La commande « {commande} » sera disponible à l'{etape}.", file=sys.stderr)
    return CODE_ECHEC


def construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog=NOM,
        description="Pastory — tableau de bord local des actifs d'un portefeuille Trade Republic.",
    )
    analyseur.add_argument("--version", action="version", version=f"{NOM} {_version()}")

    commandes = analyseur.add_subparsers(dest="commande")
    commandes.add_parser("emplacements", help="où sont rangés les fichiers personnels")

    avec_date = {"positions", "exporter-positions"}
    sans_reseau = {
        "positions",
        "exporter-positions",
        "exporter-pivot",
        "actifs",
        "composition",
    }
    for nom, aide in (
        ("lire", "rapport de lecture, sans rien écrire"),
        ("exporter-pivot", "écrire les opérations en CSV"),
        ("actifs", "dire où chercher le cours de chaque actif"),
        ("cours", "récupérer les cours de marché et les mettre en cache"),
        ("composition", "ce qu'il y a à l'intérieur de chaque actif détenu"),
        ("positions", "quantités, capital investi et prix de revient"),
        ("exporter-positions", "écrire les positions et leur journal en CSV"),
    ):
        sous_analyseur = commandes.add_parser(nom, help=aide)
        sous_analyseur.add_argument(
            "--export",
            type=Path,
            default=None,
            metavar="DOSSIER",
            help="dossier contenant l'export, au lieu du dossier de dépôt de Pastory "
            "(pour examiner l'export de quelqu'un d'autre sans le copier dans le projet)",
        )
        if nom in avec_date:
            sous_analyseur.add_argument(
                "--au",
                type=_jour,
                default=None,
                metavar="AAAA-MM-JJ",
                help="arrêter les chiffres à la fin de ce jour-là, et valoriser à cette "
                "date, au lieu d'aujourd'hui",
            )
            sous_analyseur.add_argument(
                "--depuis",
                type=_jour,
                default=None,
                metavar="AAAA-MM-JJ",
                help="faire commencer la période du gain, du TRI et du TWRR à ce jour-là, "
                "au lieu de la première opération",
            )
        if nom in sans_reseau:
            sous_analyseur.add_argument(
                "--hors-ligne",
                action="store_true",
                help="n'utiliser que les cours déjà en cache, sans aucun appel réseau",
            )
        if nom == "cours":
            sous_analyseur.add_argument(
                "--actif",
                default=None,
                metavar="ISIN",
                help="ne récupérer que les cours de cet actif",
            )

    oublier = commandes.add_parser(
        "oublier-cours", help="effacer des cours en cache, pour les reprendre à la source"
    )
    oublier.add_argument(
        "--actif", default=None, metavar="ISIN", help="n'oublier que les cours de cet actif"
    )
    oublier.add_argument(
        "--tout", action="store_true", help="oublier le cache de tous les actifs"
    )

    oublier_composition = commandes.add_parser(
        "oublier-composition",
        help="effacer des compositions en cache, pour les reprendre à la source",
    )
    oublier_composition.add_argument(
        "--actif",
        default=None,
        metavar="ISIN",
        help="n'oublier que la composition de cet actif",
    )
    oublier_composition.add_argument(
        "--tout", action="store_true", help="oublier les compositions de tous les actifs"
    )

    commandes.add_parser("ouvrir", help="ouvrir le tableau de bord (étape 9)")
    return analyseur


def _jour(texte: str) -> Date:
    """Lit une date écrite AAAA-MM-JJ, et refuse toute autre écriture.

    Une seule écriture acceptée, et elle est sans ambiguïté : « 03/04/2026 » ne veut pas
    dire la même chose des deux côtés de la Manche, et le projet ne devine rien.
    """
    try:
        return Date.fromisoformat(texte)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"« {texte} » n'est pas une date. Écrivez-la comme 2026-03-15 (année-mois-jour)."
        ) from None


def _preparer_la_sortie() -> None:
    """Fait en sorte que l'affichage ne puisse pas faire échouer une commande.

    La console Windows par défaut écrit en cp1252, qui ne connaît ni les caractères de
    dessin ni la plupart des symboles. Un rapport parfaitement correct ferait alors planter
    l'application au moment de l'afficher — et sur un projet dont le but est de montrer des
    chiffres, perdre le résultat à l'impression serait absurde.
    """
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is None:
            continue
        # Si le terminal refuse, tant pis : on continue avec ce qu'il sait faire.
        with contextlib.suppress(ValueError, OSError):
            reconfigurer(encoding="utf-8", errors="replace")


def main(arguments: list[str] | None = None) -> int:
    _preparer_la_sortie()
    analyseur = construire_analyseur()
    options = analyseur.parse_args(arguments)

    match options.commande:
        case "emplacements":
            return commande_emplacements()
        case "lire":
            return commande_lire(options.export)
        case "exporter-pivot":
            return commande_exporter_pivot(options.export, options.hors_ligne)
        case "actifs":
            return commande_actifs(options.export, options.hors_ligne)
        case "cours":
            return commande_cours(options.export, options.actif)
        case "positions":
            return commande_positions(
                options.export, options.au, options.hors_ligne, options.depuis
            )
        case "exporter-positions":
            return commande_exporter_positions(
                options.export, options.au, options.hors_ligne, options.depuis
            )
        case "composition":
            return commande_composition(options.export, options.hors_ligne)
        case "oublier-cours":
            return commande_oublier_cours(options.actif, options.tout)
        case "oublier-composition":
            return commande_oublier_composition(options.actif, options.tout)
        case "ouvrir":
            return _a_venir("ouvrir", "étape 9 (réalisation de l'interface)")
        case _:
            analyseur.print_help()
            return CODE_SUCCES


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
