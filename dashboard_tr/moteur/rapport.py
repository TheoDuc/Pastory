"""Le rapport de `dashboard positions` : ce que le moteur a calculé, en français.

Il est écrit pour être lu **en face de l'application Trade Republic**, actif par actif. Trois
règles de présentation, qui viennent toutes de la même idée — un chiffre qu'on ne peut pas
vérifier ne vaut rien :

1. **la performance et les coûts ne se mélangent jamais** : ce sont deux blocs distincts,
   parce que les frais et les taxes n'entrent dans aucun montant brut (D-21) ;
2. **ce qui manque est écrit**, jamais remplacé par un zéro ni par une moyenne (D-45) ;
3. **rien qui ne s'affiche pas sur une console Windows** : ni trait de tableau, ni coche, ni
   flèche. La console écrit en cp1252 par défaut, et un rapport parfaitement juste ferait
   planter la commande au moment de l'imprimer. Un test le vérifie.

Contrairement au rapport de lecture de l'adaptateur, celui-ci ne masque rien : ce sont les
chiffres du propriétaire, et les masquer le priverait de ce qu'il vient chercher. Il porte
donc en tête un avertissement, parce qu'un rapport se colle vite dans une issue publique.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable, Iterable
from datetime import date as Date
from decimal import Decimal

from dashboard_tr import tableur
from dashboard_tr.moteur.portefeuille import Portefeuille, Totaux
from dashboard_tr.moteur.position import Position
from dashboard_tr.moteur.rapprochement import Accord, Rapprochement
from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.pivot.operation import Poche

Titre = Callable[[str], None]
"""Une section du rapport : un intitulé, souligné, précédé d'une ligne vide."""

LARGEUR_NOM = 26
LARGEUR_TEXTE = 96
"""Au-delà, une phrase revient à la ligne n'importe où et le rapport devient illisible.

Les messages de signalement sont écrits en français, donc longs : ils sont enveloppés à
l'affichage, jamais raccourcis. Le message lui-même reste entier dans les données, où
l'interface (étape 9) le reprendra tel quel."""

SANS_OBJET = "-"
A_COMPLETER = "a completer"
"""Écrit sans accent : cette colonne est étroite et doit rester alignée partout."""


def _lisible(valeur: Decimal | None, absent: str = SANS_OBJET) -> str:
    """Un nombre écrit comme dans les messages du moteur (`tableur.nombre_lisible`)."""
    return tableur.nombre_lisible(valeur, absent=absent)


def _enveloppe(texte: str, marge: str, suite: str) -> list[str]:
    """Coupe une phrase à la largeur du rapport, en gardant son indentation."""
    return textwrap.wrap(
        texte, width=LARGEUR_TEXTE, initial_indent=marge, subsequent_indent=suite
    ) or [marge.rstrip()]


def _prix_de_revient(position: Position) -> str:
    prix = position.etat.prix_de_revient
    if prix is not None:
        return _lisible(prix)
    return A_COMPLETER if position.historique_incomplet else SANS_OBJET


def _nom(position: Position) -> str:
    nom = position.nom_actif or ""
    if len(nom) > LARGEUR_NOM:
        return nom[: LARGEUR_NOM - 1] + "."
    return nom


def resume(
    portefeuille: Portefeuille,
    rapprochement: Rapprochement | None = None,
    arrete_au: Date | None = None,
) -> str:
    """Le rapport complet, prêt à être affiché.

    `arrete_au` dit que les chiffres s'arrêtent à une date passée. Le rapprochement est alors
    hors sujet — la banque ne sait montrer qu'aujourd'hui — et le rapport l'explique au lieu
    de réclamer un fichier qui ne servirait à rien.
    """
    lignes: list[str] = []

    def titre(texte: str) -> None:
        lignes.append("")
        lignes.append(texte)
        lignes.append("-" * len(texte))

    lignes.append("Ces chiffres sont les vôtres : ce rapport n'est pas fait pour être partagé.")

    _positions(lignes, titre, portefeuille)
    _performance(lignes, titre, portefeuille.total)
    _couts(lignes, titre, portefeuille)
    _a_surveiller(lignes, titre, portefeuille)
    _rapprochement(lignes, titre, rapprochement, arrete_au)

    return "\n".join(lignes)


# --- Les positions, poche par poche ---------------------------------------------------


ENTETE_POSITIONS = (
    f"  {'actif':<14} {'nom':<{LARGEUR_NOM}} {'quantité':>12} "
    f"{'capital investi':>16} {'prix de revient':>16}"
)


def _positions(lignes: list[str], titre: Titre, portefeuille: Portefeuille) -> None:
    detenues = portefeuille.positions_detenues
    titre(f"Positions détenues : {len(detenues)}")

    if not detenues:
        lignes.append("  Aucune part détenue. Lancez « dashboard lire » pour vérifier la lecture.")
        return

    par_poche = portefeuille.par_poche()
    for poche in Poche:
        du_groupe = [position for position in detenues if position.poche is poche]
        if not du_groupe:
            continue

        lignes.append("")
        lignes.append(f"  {poche.value}")
        lignes.append(ENTETE_POSITIONS)
        for position in du_groupe:
            lignes.append(
                f"  {position.actif:<14} {_nom(position):<{LARGEUR_NOM}} "
                f"{_lisible(position.etat.quantite):>12} "
                f"{_lisible(position.etat.capital_net_investi):>16} "
                f"{_prix_de_revient(position):>16}"
            )
        totaux = par_poche[poche]
        # Le sous-total doit tomber **exactement** sous la colonne qu'il additionne : la
        # largeur reprend celle de l'en-tête, séparateurs compris (actif, nom, quantité).
        lignes.append(
            f"  {'capital investi de la poche':<{14 + 1 + LARGEUR_NOM + 1 + 12}} "
            f"{_lisible(totaux.capital_net_investi):>16}"
        )
        if totaux.historique_incomplet:
            lignes.append(
                "    (sous-estimé : des parts de cette poche sont entrées sans prix connu)"
            )


# --- La performance, en montants bruts (D-21) -----------------------------------------


def _performance(lignes: list[str], titre: Titre, total: Totaux) -> None:
    titre("Ce qui est placé, et ce que ça a rapporté")
    lignes.append("  Tout en montants bruts : ni les frais ni les taxes n'y entrent (D-21).")
    lignes.append("")

    for libelle, valeur in (
        ("capital net investi", total.capital_net_investi),
        ("dont acheté depuis le début", total.achats_bruts),
        ("ventes encaissées (brut)", total.ventes_brutes),
        ("dividendes reçus (brut)", total.dividendes_bruts),
        ("distributions de capital", total.distributions_capital),
        ("plus-values réalisées (brut)", total.plus_values_realisees_brutes),
        ("plus-values réalisées (net de frais et taxes)", total.plus_values_realisees_nettes),
    ):
        lignes.append(f"  {libelle:<46} {_lisible(valeur):>16}")

    lignes.append("")
    lignes.append("  La valeur actuelle des actifs, le gain, le TRI et le TWRR ont besoin des")
    lignes.append("  cours de marché : ils arrivent aux étapes 4 et 5.")


# --- Les coûts, tenus à part ----------------------------------------------------------


def _couts(lignes: list[str], titre: Titre, portefeuille: Portefeuille) -> None:
    total = portefeuille.total
    titre("Coûts réellement payés")
    lignes.append("  Suivis à part : ils n'entrent dans aucun chiffre ci-dessus (D-21).")
    lignes.append("")

    moments: dict[str, Decimal] = {}
    for position in portefeuille.positions:
        for nom, valeur in position.couts_par_moment().items():
            moments[nom] = moments.get(nom, Decimal("0.00")) + valeur

    for nom, valeur in moments.items():
        # « autres prélèvements » n'est là que pour boucler la colonne : à zéro, il n'apprend
        # rien et une ligne de plus rend le bloc moins lisible.
        if nom == "autres prélèvements" and valeur == Decimal("0.00"):
            continue
        lignes.append(f"  {nom:<46} {_lisible(valeur):>16}")
    lignes.append(f"  {'total':<46} {_lisible(total.frais + total.taxes):>16}")
    lignes.append("")
    lignes.append("  Le spread et les frais courants des ETF ne sont pas là : ce sont des")
    lignes.append("  estimations, qui arrivent à l'étape 6 (D-17).")


# --- Ce qui demande l'attention de l'utilisateur ---------------------------------------


def _a_surveiller(lignes: list[str], titre: Titre, portefeuille: Portefeuille) -> None:
    incompletes = portefeuille.positions_incompletes
    if incompletes:
        titre(f"ATTENTION - positions dont l'histoire est incomplète : {len(incompletes)}")
        lignes.append("  Leur capital investi est sous-estimé et leur prix de revient est")
        lignes.append("  laissé vide, plutôt que d'afficher un nombre faussement bas (D-45).")
        for position in incompletes:
            lignes.append(f"  {position.actif:<14} {position.poche.value:<8} {_nom(position)}")

    if portefeuille.signalements:
        titre(f"Signalements : {len(portefeuille.signalements)}")
        for categorie, groupe in _grouper(portefeuille.signalements):
            lignes.append(f"  {categorie} ({len(groupe)})")
            for signalement in groupe:
                lignes += _enveloppe(str(signalement), "    - ", "      ")
                if signalement.reference_source:
                    lignes.append(f"      événement {signalement.reference_source}")
    else:
        lignes.append("")
        lignes.append("Aucun signalement : toutes les opérations se sont appliquées normalement.")


# --- Le rapprochement avec ce que la banque dit détenir -------------------------------


def _rapprochement(
    lignes: list[str],
    titre: Titre,
    rapprochement: Rapprochement | None,
    arrete_au: Date | None = None,
) -> None:
    if rapprochement is None:
        titre("Rapprochement avec le portefeuille réel")
        if arrete_au is not None:
            # La banque ne sait montrer qu'aujourd'hui : comparer une photo d'aujourd'hui à
            # des chiffres arrêtés dans le passé signalerait à tort tout ce qui a bougé
            # depuis. Mieux vaut ne pas rapprocher du tout que rapprocher de travers.
            lignes.append(
                f"  Sans objet : les chiffres sont arrêtés au {arrete_au.isoformat()}, alors "
                "que la banque"
            )
            lignes.append("  ne sait montrer que son portefeuille d'aujourd'hui.")
            lignes.append("")
            lignes.append("  Relancez « dashboard positions » sans --au pour le rapprochement.")
            return
        lignes.append("  Pas encore fait. C'est le contrôle le plus sûr du projet : il ne")
        lignes.append("  dépend d'aucune lecture de texte, et lui seul peut révéler des titres")
        lignes.append("  entrés sans qu'aucune opération ne l'indique.")
        lignes.append("")
        lignes.append("  Lancez « dashboard positions-reelles », puis cette commande à nouveau.")
        return

    titre("Rapprochement avec le portefeuille réel")
    if rapprochement.poches_non_couvertes:
        # Le cas connu : pytr ne demande les positions que d'un seul compte-titres, et la
        # banque range le PEA dans un second (D-47). Le dire une fois vaut mieux que de
        # lever une alerte par actif à chaque lancement.
        poches = ", ".join(poche.value for poche in rapprochement.poches_non_couvertes)
        concernes = [
            ligne for ligne in rapprochement.lignes if ligne.accord is Accord.HORS_PERIMETRE
        ]
        lignes.append(
            f"  La photo de la banque ne couvre pas : {poches}. "
            f"{len(concernes)} actif(s) ne sont donc"
        )
        lignes.append("  ni comparés, ni confirmés - ils sortent en « hors périmètre »")
        lignes.append("  ci-dessous, sans alerte. Ce n'est pas un désaccord.")
        lignes.append("")
        lignes.append("  Cause connue : l'outil qui interroge Trade Republic ne demande les")
        lignes.append("  positions que d'un seul compte-titres, et le PEA est dans un autre.")
        lignes.append("")

    if rapprochement.lignes_illisibles:
        # Un actif absent d'une ligne illisible ressortirait « absent de la banque », ce qui
        # est un faux diagnostic : c'est le fichier qui est abîmé, pas le portefeuille.
        lignes.append(
            f"  ATTENTION - {rapprochement.lignes_illisibles} ligne(s) du fichier de la "
            "banque n'ont pas pu être lues."
        )
        lignes.append("  Le rapprochement est donc incomplet : un « absent de la banque »")
        lignes.append("  ci-dessous peut très bien s'y trouver. Relancez")
        lignes.append("  « dashboard positions-reelles » avant de conclure.")
        lignes.append("")
    elif rapprochement.tout_concorde:
        # « comparées » n'est pas une précaution de style : quand une poche n'est pas
        # couverte, dire « toutes » laisserait croire à un contrôle complet.
        if rapprochement.complet:
            lignes.append("  Toutes les quantités concordent avec celles de Trade Republic.")
        else:
            lignes.append("  Toutes les quantités comparées concordent avec Trade Republic.")
    else:
        lignes.append("  Des quantités ne concordent pas. Chacune est expliquée ci-dessous.")

    lignes.append("")
    lignes.append(
        f"  {'actif':<14} {'nom':<{LARGEUR_NOM}} {'moteur':>12} {'banque':>12} {'état':>20}"
    )
    for ligne in rapprochement.lignes:
        nom = (ligne.nom_actif or "")[:LARGEUR_NOM]
        lignes.append(
            f"  {ligne.actif:<14} {nom:<{LARGEUR_NOM}} "
            f"{_lisible(ligne.quantite_moteur):>12} "
            f"{_lisible(ligne.quantite_banque):>12} "
            f"{ligne.accord.value:>20}"
        )

    _prix_de_revient_compares(lignes, rapprochement)

    if rapprochement.signalements:
        lignes.append("")
        for signalement in rapprochement.signalements:
            lignes += _enveloppe(
                f"[{signalement.categorie}] {signalement}", "  ", "    "
            )


def _prix_de_revient_compares(lignes: list[str], rapprochement: Rapprochement) -> None:
    """Les deux prix de revient côte à côte, **pour information seulement** (D-46)."""
    comparables = [
        ligne
        for ligne in rapprochement.lignes
        if ligne.prix_de_revient_moteur is not None and ligne.prix_de_revient_banque is not None
    ]
    if not comparables:
        return

    lignes.append("")
    lignes.append("  Prix de revient, pour information - aucun écart n'est une anomalie :")
    lignes.append("  Trade Republic ne dit pas ce qu'il met dans le sien, alors que celui de")
    lignes.append("  cette application exclut explicitement les frais et les taxes (D-13).")
    lignes.append(f"  {'actif':<14} {'ici':>16} {'Trade Republic':>18}")
    for ligne in comparables:
        lignes.append(
            f"  {ligne.actif:<14} {_lisible(ligne.prix_de_revient_moteur):>16} "
            f"{_lisible(ligne.prix_de_revient_banque):>18}"
        )


def _grouper(signalements: Iterable[Signalement]) -> list[tuple[str, list[Signalement]]]:
    """Regroupe par catégorie, en gardant l'ordre d'apparition."""
    groupes: dict[str, list[Signalement]] = {}
    for signalement in signalements:
        groupes.setdefault(signalement.categorie, []).append(signalement)
    return list(groupes.items())
