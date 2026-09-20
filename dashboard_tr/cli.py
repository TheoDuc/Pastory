"""Point d'entrée unique de l'application : `uv run dashboard <commande>`.

Les commandes sont ajoutées étape par étape. Celles qui ne sont pas encore écrites le disent
clairement, avec l'étape où elles arrivent, plutôt que d'échouer sans explication.

L'enchaînement normal, au premier usage :

```
dashboard rafraichir          récupérer l'export auprès de Trade Republic
dashboard comptes             dire à quoi sert chaque compte espèces (une seule fois)
dashboard lire                vérifier qu'aucun type d'événement n'est inconnu
dashboard exporter-pivot      écrire les opérations en CSV, à vérifier dans un tableur
dashboard positions           ce que le moteur en déduit : quantités, capital investi, PRU
dashboard exporter-positions  écrire les positions et leur journal en CSV
dashboard positions-reelles   demander à la banque ce qu'elle dit détenir, pour recouper
```
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import sys
from datetime import date as Date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dashboard_tr.adaptateurs.trade_republic import evenements as lecture_evenements
from dashboard_tr.adaptateurs.trade_republic import portefeuille as portefeuille_banque
from dashboard_tr.adaptateurs.trade_republic import recoupement_csv, source
from dashboard_tr.adaptateurs.trade_republic.classement import classer
from dashboard_tr.adaptateurs.trade_republic.lecture import Lecteur
from dashboard_tr.adaptateurs.trade_republic.rapport import Rapport
from dashboard_tr.config import comptes as config_comptes
from dashboard_tr.config import emplacements
from dashboard_tr.moteur import export_csv as export_moteur
from dashboard_tr.moteur import rapport as rapport_moteur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rapprochement import rapprocher
from dashboard_tr.pivot import export_csv
from dashboard_tr.pivot.position_reelle import PositionReelle

NOM = "dashboard"

NOM_EXPORT_PIVOT = "operations.csv"

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


def _construire_moteur(
    dossier: Path, au: Date | None
) -> tuple[Portefeuille, Rapport, list[str]] | None:
    """Lecture puis rejeu. Renvoie `None` si la lecture ne permet pas d'aller plus loin."""
    rapport, _ = _lire(dossier, avec_recoupement=False)
    if rapport.declarations_attendues:
        print(rapport.resume())
        print(
            "\nAucun chiffre n'a été calculé : il manque des informations que vous seul "
            "pouvez donner (voir ci-dessus).",
            file=sys.stderr,
        )
        return None

    portefeuille = Portefeuille.construire(rapport.operations)
    if au is not None:
        portefeuille = portefeuille.au(au)
    return portefeuille, rapport, _etat_de_la_lecture(rapport)


def commande_positions(dossier_export: Path | None, au: Date | None) -> int:
    """Affiche les positions calculées par le moteur, sans rien écrire."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        construit = _construire_moteur(dossier, au)
        if construit is None:
            return CODE_DECLARATION_ATTENDUE
        portefeuille, _, entete = construit
        positions_reelles, anomalies_du_fichier = _charger_positions_reelles(dossier)
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except portefeuille_banque.PortefeuilleIllisible as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in entete:
        print(ligne)
    if au is not None:
        print(f"Chiffres arrêtés au {au.isoformat()}.")

    rapprochement = (
        rapprocher(portefeuille, positions_reelles) if positions_reelles is not None else None
    )
    print(rapport_moteur.resume(portefeuille, rapprochement))

    for anomalie in anomalies_du_fichier:
        print(f"  portefeuille réel, {anomalie}", file=sys.stderr)

    return CODE_SUCCES


def commande_exporter_positions(dossier_export: Path | None, au: Date | None) -> int:
    """Écrit `positions.csv` et `journal.csv` dans le dossier personnel."""
    dossier = dossier_export or source.dossier_par_defaut()
    try:
        construit = _construire_moteur(dossier, au)
        if construit is None:
            return CODE_DECLARATION_ATTENDUE
        portefeuille, _, entete = construit
    except source.ExportIntrouvable as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC
    except config_comptes.ConfigurationInvalide as erreur:
        print(erreur, file=sys.stderr)
        return CODE_ECHEC

    for ligne in entete:
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
    for nom, aide in (
        ("comptes", "dire à quoi sert chaque compte espèces"),
        ("lire", "rapport de lecture, sans rien écrire"),
        ("exporter-pivot", "écrire les opérations en CSV"),
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
        case "positions":
            return commande_positions(options.export, options.au)
        case "exporter-positions":
            return commande_exporter_positions(options.export, options.au)
        case "positions-reelles":
            return commande_positions_reelles()
        case "ouvrir":
            return _a_venir("ouvrir", "étape 9 (réalisation de l'interface)")
        case _:
            analyseur.print_help()
            return CODE_SUCCES


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
