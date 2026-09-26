"""Point d'entrée unique de l'application : `uv run dashboard <commande>`.

Les commandes sont ajoutées étape par étape. Celles qui ne sont pas encore écrites le disent
clairement, avec l'étape où elles arrivent, plutôt que d'échouer sans explication.

L'enchaînement normal, au premier usage :

```
dashboard rafraichir          récupérer l'export auprès de Trade Republic
dashboard comptes             dire à quoi sert chaque compte espèces (une seule fois)
dashboard lire                vérifier qu'aucun type d'événement n'est inconnu
dashboard exporter-pivot      écrire les opérations en CSV, à vérifier dans un tableur
dashboard actifs              dire où chercher le cours de chaque actif (une seule fois)
dashboard cours               récupérer les cours de marché et les garder en cache
dashboard positions           ce que le moteur en déduit : quantités, capital investi, PRU
dashboard exporter-positions  écrire les positions et leur journal en CSV
dashboard positions-reelles   demander à la banque ce qu'elle dit détenir, pour recouper
dashboard oublier-cours       effacer des cours en cache, pour les reprendre à la source
```
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import sys
import textwrap
from datetime import date as Date
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dashboard_tr import tableur
from dashboard_tr.adaptateurs.trade_republic import evenements as lecture_evenements
from dashboard_tr.adaptateurs.trade_republic import portefeuille as portefeuille_banque
from dashboard_tr.adaptateurs.trade_republic import recoupement_csv, source
from dashboard_tr.adaptateurs.trade_republic.classement import classer
from dashboard_tr.adaptateurs.trade_republic.lecture import Lecteur
from dashboard_tr.adaptateurs.trade_republic.rapport import Rapport
from dashboard_tr.config import actifs as config_actifs
from dashboard_tr.config import comptes as config_comptes
from dashboard_tr.config import emplacements
from dashboard_tr.donnees_externes import completion as completion_cours
from dashboard_tr.donnees_externes import cours as cours_module
from dashboard_tr.donnees_externes.cache import Cache, CacheIllisible
from dashboard_tr.donnees_externes.completion import Completion
from dashboard_tr.donnees_externes.cours import FournisseurDeCours
from dashboard_tr.donnees_externes.yahoo import Yahoo
from dashboard_tr.moteur import export_csv as export_moteur
from dashboard_tr.moteur import rapport as rapport_moteur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rapprochement import rapprocher
from dashboard_tr.pivot import export_csv
from dashboard_tr.pivot.position_reelle import PositionReelle

NOM = "dashboard"

NOM_EXPORT_PIVOT = "operations.csv"

DUREE_PAR_DEFAUT = timedelta(days=400)
"""Sur quelle profondeur chercher les cours d'un actif déclaré mais absent de l'export.

Un peu plus d'un an : de quoi couvrir une année complète de valorisation sans télécharger
l'histoire d'un titre qu'on ne détient pas."""

CODE_SUCCES = 0
CODE_ECHEC = 1
CODE_DECLARATION_ATTENDUE = 2
"""L'export s'est arrêté parce qu'il manque une information que seul l'utilisateur peut
donner (D-40). Un code distinct de l'échec : rien n'est cassé, il faut compléter."""


def _version() -> str:
    try:
        return version("dashboard-tr")
    except PackageNotFoundError:  # pragma: no cover - dépend de l'installation
        return "inconnue (application non installée)"


def commande_emplacements() -> int:
    """Affiche où l'application range les fichiers personnels (D-37)."""
    print("Fichiers personnels (hors du dossier du projet, jamais dans git) :")
    for nom, chemin in emplacements.tous_les_dossiers().items():
        etat = "existe" if chemin.exists() else "pas encore créé"
        print(f"  {nom:<14} {chemin}  [{etat}]")
    return CODE_SUCCES


def commande_rafraichir() -> int:
    """Récupère l'export auprès de Trade Republic, via pytr.

    L'avertissement sur le PIN invisible n'est pas une politesse : sous Windows, la saisie
    masquée n'affiche **rien**, pas même des astérisques, et la première réaction naturelle
    est de croire que le clavier ne répond plus.
    """
    dossier = source.dossier_par_defaut()
    print(f"Récupération de l'export Trade Republic dans :\n  {dossier}\n")
    print("Trade Republic va vous demander votre numéro de téléphone, puis votre code PIN.")
    print()
    print("  ATTENTION : en tapant le PIN, vous ne verrez RIEN s'afficher.")
    print("  Ni les chiffres, ni des étoiles, ni même le curseur qui avance.")
    print("  C'est normal : la saisie est masquée. Tapez le PIN, puis appuyez sur Entrée.")
    print()
    print("Rien n'est enregistré sur cette machine : le PIN vous sera redemandé la")
    print("prochaine fois. C'est le mode le plus sûr.")
    print()

    code = source.rafraichir(dossier)
    if code != CODE_SUCCES:
        print(
            "\nLa récupération a échoué. Les données déjà présentes n'ont pas été touchées.",
            file=sys.stderr,
        )
        return CODE_ECHEC

    print(f"\nExport à jour dans {dossier}.")
    print("Vérifiez la lecture avec « dashboard lire ».")
    return CODE_SUCCES


def commande_comptes(dossier_export: Path | None) -> int:
    """Assistant « nommer ses comptes » (D-10).

    Montre les types d'opérations vus sur chaque compte : c'est ce qui permet de reconnaître
    un compte dont on ignorait l'existence.

    **Avec `--export`, rien n'est écrit.** Les numéros de compte d'un export qui n'est pas le
    sien appartiennent à quelqu'un d'autre : les enregistrer dans sa propre configuration
    serait les recopier (règle 2 de CLAUDE.md). L'assistant se contente alors d'afficher ce
    qu'il a trouvé.
    """
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        bruts = source.charger_evenements(dossier)
        configuration = config_comptes.charger()
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        # C'est la commande censée aider à corriger ce fichier : elle doit l'expliquer,
        # pas s'interrompre sur une erreur technique.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    vus: dict[str, set[str]] = collections.defaultdict(set)
    for evenement in bruts:
        compte = lecture_evenements.compte(evenement)
        if compte is None:
            continue
        vus[compte].add(classer(evenement).type_affiche)

    if not vus:
        print("Aucun compte espèces n'apparaît dans cet export.")
        return CODE_SUCCES

    print(f"{len(vus)} compte(s) espèces trouvé(s) dans l'export.")
    for compte, types in sorted(vus.items()):
        role = configuration.roles.get(compte)
        print(f"\n  compte {compte} — rôle : {role.value if role else 'à donner'}")
        print(f"    opérations vues : {', '.join(sorted(types))}")

    if dossier_export is not None:
        print(
            "\nRien n'a été écrit : cet export a été lu depuis un dossier que vous avez "
            "indiqué,\net ses comptes ne sont pas forcément les vôtres. Pour nommer vos "
            f"propres comptes,\nlancez « {NOM} comptes » sans --export."
        )
        return CODE_SUCCES

    fichier = config_comptes.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        config_comptes.modele(
            {compte: sorted(types) for compte, types in vus.items()}, configuration
        ),
        encoding="utf-8",
    )

    manquants = [compte for compte in vus if compte not in configuration.roles]
    print(f"\nOuvrez ce fichier et donnez un rôle à chaque compte :\n  {fichier}\n")
    print("Les types d'opérations vus sur chaque compte y sont rappelés pour vous aider.")
    if manquants:
        print(f"\n{len(manquants)} compte(s) attendent encore un rôle.")
    else:
        print("\nTous les comptes ont déjà un rôle.")
    return CODE_SUCCES


def _lire(dossier: Path, avec_recoupement: bool) -> tuple[Rapport, int]:
    """Lecture commune à « lire » et « exporter-pivot »."""
    bruts = source.charger_evenements(dossier)
    configuration = config_comptes.charger()
    rapport = Lecteur(configuration).lire(bruts)

    if avec_recoupement:
        chemin_csv = source.chemin_transactions(dossier)
        if chemin_csv is None:
            rapport.signaler(
                "recoupement CSV",
                f"pas de fichier « {source.NOM_TRANSACTIONS} » dans cet export : "
                "les quantités, frais et taxes lus dans les textes n'ont pas pu être recoupés",
            )
        else:
            recoupement_csv.recouper(
                rapport.operations, recoupement_csv.lire_csv(chemin_csv, rapport), rapport
            )

    code = CODE_DECLARATION_ATTENDUE if rapport.declarations_attendues else CODE_SUCCES
    return rapport, code


def commande_lire(dossier_export: Path | None) -> int:
    """Affiche le rapport de lecture, sans rien écrire."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        rapport, code = _lire(dossier, avec_recoupement=True)
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(rapport.resume())
    return code


def commande_exporter_pivot(dossier_export: Path | None) -> int:
    """Écrit les opérations en CSV, après avoir affiché le rapport de lecture."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        rapport, code = _lire(dossier, avec_recoupement=True)
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(rapport.resume())

    if rapport.declarations_attendues:
        # Rien n'est écrit tant qu'il manque une déclaration : un fichier incomplet
        # ressemblerait à un fichier complet (D-40).
        print(
            "\nAucun fichier n'a été écrit : il manque des informations "
            "que vous seul pouvez donner (voir ci-dessus).",
            file=sys.stderr,
        )
        return code

    fichier = export_csv.ecrire(
        rapport.operations, emplacements.dossier_personnel() / NOM_EXPORT_PIVOT
    )
    print(f"\n{len(rapport.operations)} opération(s) écrite(s) dans :\n  {fichier}")
    print("Ouvrez ce fichier dans un tableur pour comparer avec l'application Trade Republic.")
    return code


# --- Le moteur (étape 3) -------------------------------------------------------------


def _etat_de_la_lecture(rapport: Rapport) -> list[str]:
    """Un résumé en deux lignes de la lecture dont les chiffres sortent.

    Le moteur ne recalcule pas ce que `dashboard lire` a déjà dit, mais il ne peut pas non
    plus laisser croire que tout va bien : un type inconnu peut cacher des opérations sur
    les actifs (règle 5 de CLAUDE.md), et alors aucun chiffre ci-dessous n'est complet.
    """
    lignes = [f"{len(rapport.operations)} opération(s) lues."]
    ennuis = []
    if rapport.types_inconnus:
        ennuis.append(f"{sum(rapport.types_inconnus.values())} événement(s) de type inconnu")
    if rapport.operations_non_produites:
        # Un événement traité dont aucune opération n'est sortie est un trou franc dans les
        # totaux : des parts ou des montants manquent, et rien d'autre ne le dirait.
        ennuis.append(
            f"{rapport.operations_non_produites} événement(s) traités sans opération produite"
        )
    if rapport.anomalies:
        ennuis.append(f"{len(rapport.anomalies)} contrôle(s) de cohérence en échec")
    if ennuis:
        lignes.append(
            "ATTENTION - " + ", ".join(ennuis) + f" : lancez « {NOM} lire » avant de vous "
            "fier aux chiffres ci-dessous."
        )
    return lignes


def _charger_positions_reelles(
    dossier: Path,
) -> tuple[list[PositionReelle] | None, list[str]]:
    """Lit le portefeuille réel s'il a déjà été récupéré. Son absence n'est pas une erreur.

    Renvoie `None` quand le fichier n'est pas là — et non une liste vide, qui voudrait dire
    « la banque ne détient plus rien », ce qui est une information très différente. Le
    rapport invite alors à lancer `positions-reelles`, plutôt que de faire échouer une
    commande qui n'a besoin de rien d'autre que de l'export.
    """
    fichier = portefeuille_banque.chemin(dossier)
    if not fichier.exists():
        return None, []
    return portefeuille_banque.lire(fichier)


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


def _rapport_des_cours(completion: Completion) -> list[str]:
    """Ce que les cours ont changé aux opérations, et ce qu'ils n'ont pas pu changer.

    Bloc à part, avant les chiffres du moteur : un montant déduit d'un cours de marché n'est
    pas un montant donné par la banque, et l'utilisateur doit pouvoir refaire la
    multiplication (D-15, règle 6 de CLAUDE.md).
    """
    if completion.rien_a_completer and not completion.refus:
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
            "  Ces montants sont déduits, pas donnés par la banque : les CSV les marquent"
        )
        lignes.append("  « deduction ».")

    if completion.incompletes:
        lignes.append("")
        lignes.append(
            f"  {completion.incompletes} opération(s) attendent toujours un prix. Leurs parts"
        )
        lignes.append("  sont comptées, leur montant non : le capital investi est sous-estimé.")

    for refus in completion.refus:
        lignes += _enveloppe_cours(f"{refus.categorie} : {refus.motif}", refus.actif)

    return lignes


def _enveloppe_cours(texte: str, actif: str) -> list[str]:
    """Une phrase de refus, coupée à une largeur lisible, suivie de l'actif concerné."""
    return textwrap.wrap(
        f"{texte} [{actif}]", width=96, initial_indent="    - ", subsequent_indent="      "
    )


def _construire_moteur(
    dossier: Path, au: Date | None, hors_ligne: bool = False
) -> tuple[Portefeuille, Rapport, list[str], Completion] | None:
    """Lecture, complétion des prix, puis rejeu.

    La complétion s'insère **entre** la lecture et le moteur, et ne produit que du format
    pivot : le moteur ne gagne pas une ligne et ne sait rien des cours (D-26).

    Renvoie `None` si la lecture ne permet pas d'aller plus loin.
    """
    rapport, _ = _lire(dossier, avec_recoupement=False)
    if rapport.declarations_attendues:
        print(rapport.resume())
        print(
            "\nAucun chiffre n'a été calculé : il manque des informations que vous seul "
            "pouvez donner (voir ci-dessus).",
            file=sys.stderr,
        )
        return None

    completion = completion_cours.completer_les_prix(
        rapport.operations, _fournisseur_de_cours(hors_ligne)
    )

    portefeuille = Portefeuille.construire(completion.operations)
    if au is not None:
        portefeuille = portefeuille.au(au)
    return portefeuille, rapport, _etat_de_la_lecture(rapport), completion


def commande_positions(
    dossier_export: Path | None, au: Date | None, hors_ligne: bool = False
) -> int:
    """Affiche les positions calculées par le moteur, sans rien écrire."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        construit = _construire_moteur(dossier, au, hors_ligne)
        if construit is None:
            return CODE_DECLARATION_ATTENDUE
        portefeuille, _, entete, completion = construit
        # Le portefeuille de la banque est une photo d'**aujourd'hui** : le comparer à un
        # portefeuille arrêté à une date passée signalerait à tort tout ce qui a bougé
        # depuis. Le rapprochement n'a de sens que sur les chiffres à jour.
        if au is None:
            positions_reelles, anomalies_du_fichier = _charger_positions_reelles(dossier)
        else:
            positions_reelles, anomalies_du_fichier = None, []
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except portefeuille_banque.PortefeuilleIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in entete:
        print(ligne)
    if au is not None:
        print(f"Chiffres arrêtés au {au.isoformat()}.")

    rapprochement = (
        rapprocher(portefeuille, positions_reelles, lignes_illisibles=len(anomalies_du_fichier))
        if positions_reelles is not None
        else None
    )
    print(rapport_moteur.resume(portefeuille, rapprochement, arrete_au=au))

    # Après les chiffres, et non avant : le rapport du moteur porte en tête l'avertissement
    # qu'il contient de vraies valeurs, et rien ne doit s'intercaler devant.
    for ligne in _rapport_des_cours(completion):
        print(ligne)

    for anomalie in anomalies_du_fichier:
        print(f"  portefeuille réel, {anomalie}", file=sys.stderr)

    return CODE_SUCCES


def commande_exporter_positions(
    dossier_export: Path | None, au: Date | None, hors_ligne: bool = False
) -> int:
    """Écrit `positions.csv` et `journal.csv` dans le dossier personnel."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        construit = _construire_moteur(dossier, au, hors_ligne)
        if construit is None:
            return CODE_DECLARATION_ATTENDUE
        portefeuille, _, entete, completion = construit
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except CacheIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in entete:
        print(ligne)
    for ligne in _rapport_des_cours(completion):
        print(ligne)

    personnel = emplacements.dossier_personnel()
    fichier_positions = export_moteur.ecrire_positions(
        portefeuille, personnel / export_moteur.NOM_POSITIONS
    )
    fichier_journal = export_moteur.ecrire_journal(
        portefeuille, personnel / export_moteur.NOM_JOURNAL
    )

    print(f"\n{len(portefeuille.positions)} position(s) écrite(s) dans :\n  {fichier_positions}")
    lignes = sum(len(position.journal) for position in portefeuille.positions)
    print(f"{lignes} ligne(s) de journal dans :\n  {fichier_journal}")
    print(
        "\nLe journal est celui à ouvrir pour refaire un chiffre à la main : une ligne par\n"
        "opération, avec l'état d'avant et l'état d'après."
    )
    return CODE_SUCCES


def commande_positions_reelles() -> int:
    """Demande à Trade Republic ce qu'il dit détenir, et l'enregistre pour le rapprochement.

    Commande à part, et non un morceau de `rafraichir` : comme rien n'est enregistré sur
    cette machine (D-41), chaque appel à pytr redemande le numéro, le PIN et la confirmation
    dans l'application. Les réunir obligerait à le faire deux fois à chaque rafraîchissement.
    """
    fichier = portefeuille_banque.chemin(source.dossier_par_defaut())
    print("Récupération du portefeuille actuel auprès de Trade Republic.\n")
    print("Trade Republic va vous demander votre numéro de téléphone, puis votre code PIN.")
    print()
    print("  ATTENTION : en tapant le PIN, vous ne verrez RIEN s'afficher.")
    print("  C'est normal : la saisie est masquée. Tapez le PIN, puis appuyez sur Entrée.")
    print()

    code = source.recuperer_portefeuille(fichier)
    if code != CODE_SUCCES:
        print(
            "\nLa récupération a échoué. Le fichier précédent, s'il existait, n'a pas été "
            "touché.",
            file=sys.stderr,
        )
        return CODE_ECHEC

    try:
        positions, anomalies = portefeuille_banque.lire(fichier)
    except portefeuille_banque.PortefeuilleIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    print(f"\n{len(positions)} position(s) enregistrée(s) dans :\n  {fichier}")
    for anomalie in anomalies:
        print(f"  non lue : {anomalie}", file=sys.stderr)
    print(f"\nLancez « {NOM} positions » pour comparer avec les chiffres du moteur.")
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
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        rapport, _ = _lire(dossier, avec_recoupement=False)
        configuration = config_actifs.charger()
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        # C'est la commande censée aider à corriger ce fichier : elle l'explique.
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    if rapport.declarations_attendues:
        print(rapport.resume())
        print(
            f"\nCommencez par « {NOM} comptes » : sans le rôle de chaque compte, la poche "
            "des opérations\nreste inconnue et la liste des actifs serait incomplète.",
            file=sys.stderr,
        )
        return CODE_DECLARATION_ATTENDUE

    apercu = _apercu_des_actifs(rapport)
    if not apercu:
        print("Aucun actif n'apparaît dans cet export.")
        return CODE_SUCCES

    manquants = configuration.manquants(apercu)
    propositions = {}
    if manquants and not hors_ligne:
        print(f"Recherche d'un ticker pour {len(manquants)} actif(s) sans correspondance...")
        yahoo = Yahoo()
        for actif in manquants:
            proposition = yahoo.chercher(actif)
            if proposition is not None:
                propositions[actif] = proposition

    print(f"\n{len(apercu)} actif(s) dans l'export, {len(manquants)} sans correspondance.")
    for actif in sorted(apercu):
        declaration = configuration.declaration(actif)
        if declaration is not None:
            etat = f"déclaré : {declaration.ticker} ({declaration.devise})"
        elif actif in propositions:
            proposition = propositions[actif]
            etat = f"proposé : {proposition.ticker}"
            if proposition.devise:
                etat += f" ({proposition.devise})"
            if proposition.douteuse:
                etat += " - ATTENTION, pas en euros, à ne pas retenir tel quel"
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
    if manquants:
        print(f"\n{len(manquants)} actif(s) attendent votre validation.")
        print(f"Ensuite, lancez « {NOM} cours » pour récupérer les cours.")
    else:
        print("\nTous les actifs de cet export sont déjà déclarés.")
    return CODE_SUCCES


def commande_cours(dossier_export: Path | None, actif_demande: str | None = None) -> int:
    """Récupère les cours des actifs déclarés et les garde en cache (D-50).

    La période demandée va de la **première opération** sur l'actif à aujourd'hui : c'est ce
    qui permettra de valoriser le portefeuille dans le temps (étape 5) sans y revenir. Un
    cours déjà en cache n'est jamais redemandé.
    """
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        rapport, _ = _lire(dossier, avec_recoupement=False)
        configuration = config_actifs.charger()
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
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

    oublies = cache.oublier(actif)
    if not oublies:
        cible = f"l'actif {actif}" if actif else "le cache"
        print(f"Rien à oublier : aucun cours en cache pour {cible}.")
        return CODE_SUCCES

    print(f"{len(oublies)} actif(s) oublié(s) : {', '.join(oublies)}")
    print(f"Lancez « {NOM} cours » pour les reprendre à la source.")
    return CODE_SUCCES


def _a_venir(commande: str, etape: str) -> int:
    print(f"La commande « {commande} » sera disponible à l'{etape}.", file=sys.stderr)
    return CODE_ECHEC


def construire_analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog=NOM,
        description="Tableau de bord local des actifs d'un portefeuille Trade Republic.",
    )
    analyseur.add_argument("--version", action="version", version=f"{NOM} {_version()}")

    commandes = analyseur.add_subparsers(dest="commande")
    commandes.add_parser("emplacements", help="où sont rangés les fichiers personnels")
    commandes.add_parser("rafraichir", help="récupérer les données Trade Republic")
    commandes.add_parser(
        "positions-reelles", help="demander à la banque ce qu'elle dit détenir"
    )

    avec_date = {"positions", "exporter-positions"}
    sans_reseau = {"positions", "exporter-positions", "actifs"}
    for nom, aide in (
        ("comptes", "dire à quoi sert chaque compte espèces"),
        ("lire", "rapport de lecture, sans rien écrire"),
        ("exporter-pivot", "écrire les opérations en CSV"),
        ("actifs", "dire où chercher le cours de chaque actif"),
        ("cours", "récupérer les cours de marché et les mettre en cache"),
        ("positions", "quantités, capital investi et prix de revient"),
        ("exporter-positions", "écrire les positions et leur journal en CSV"),
    ):
        sous_analyseur = commandes.add_parser(nom, help=aide)
        sous_analyseur.add_argument(
            "--export",
            type=Path,
            default=None,
            metavar="DOSSIER",
            help="dossier contenant l'export, au lieu du dossier personnel "
            "(pour examiner l'export de quelqu'un d'autre sans le copier dans le projet)",
        )
        if nom in avec_date:
            sous_analyseur.add_argument(
                "--au",
                type=_jour,
                default=None,
                metavar="AAAA-MM-JJ",
                help="arrêter les chiffres à la fin de ce jour-là, au lieu d'aller "
                "jusqu'à la dernière opération connue",
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
        case "rafraichir":
            return commande_rafraichir()
        case "comptes":
            return commande_comptes(options.export)
        case "lire":
            return commande_lire(options.export)
        case "exporter-pivot":
            return commande_exporter_pivot(options.export)
        case "actifs":
            return commande_actifs(options.export, options.hors_ligne)
        case "cours":
            return commande_cours(options.export, options.actif)
        case "positions":
            return commande_positions(options.export, options.au, options.hors_ligne)
        case "exporter-positions":
            return commande_exporter_positions(options.export, options.au, options.hors_ligne)
        case "positions-reelles":
            return commande_positions_reelles()
        case "oublier-cours":
            return commande_oublier_cours(options.actif, options.tout)
        case "ouvrir":
            return _a_venir("ouvrir", "étape 9 (réalisation de l'interface)")
        case _:
            analyseur.print_help()
            return CODE_SUCCES


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
