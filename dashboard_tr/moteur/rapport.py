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
from decimal import ROUND_HALF_UP, Decimal

from dashboard_tr import tableur
from dashboard_tr.moteur.couts import DetailDesCouts
from dashboard_tr.moteur.portefeuille import Portefeuille, Totaux
from dashboard_tr.moteur.position import Position
from dashboard_tr.moteur.rapprochement import Accord, Rapprochement
from dashboard_tr.moteur.rendements import Rendements, Synthese
from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.moteur.valeur_reelle import ValeurReelle
from dashboard_tr.moteur.valorisation import PositionValorisee
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


def _pourcentage(taux: Decimal | None, absent: str = SANS_OBJET) -> str:
    """Un taux écrit en pour cent, à deux décimales : « 10,00 % ».

    Arrondi « comme à la main » (`ROUND_HALF_UP`), comme partout dans le projet : 10,125 %
    s'écrit 10,13 %, pas 10,12 %.
    """
    if taux is None:
        return absent
    return f"{_lisible((taux * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))} %"


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
    synthese: Synthese | None = None,
    detail_des_couts: DetailDesCouts | None = None,
    valeur_reelle_estimee: ValeurReelle | None = None,
) -> str:
    """Le rapport complet, prêt à être affiché.

    `arrete_au` dit que les chiffres s'arrêtent à une date passée. Le rapprochement est alors
    hors sujet — la banque ne sait montrer qu'aujourd'hui — et le rapport l'explique au lieu
    de réclamer un fichier qui ne servirait à rien.

    `synthese` apporte ce que les cours permettent : la valeur des actifs, et les trois
    chiffres clés (D-22). Sans elle, le rapport dit qu'ils manquent.

    `detail_des_couts` et `valeur_reelle_estimee` apportent l'étape 6 : les coûts payés en
    détail, les coûts estimés (D-17) et la valeur réelle (D-23). Sans eux, le rapport s'arrête
    aux coûts payés, comme avant.
    """
    lignes: list[str] = []

    def titre(texte: str) -> None:
        lignes.append("")
        lignes.append(texte)
        lignes.append("-" * len(texte))

    lignes.append("Ces chiffres sont les vôtres : ce rapport n'est pas fait pour être partagé.")

    _positions(lignes, titre, portefeuille)
    if synthese is not None:
        _valeur(lignes, titre, synthese)
    _performance(lignes, titre, portefeuille.total, synthese)
    if synthese is not None:
        _chiffres_cles(lignes, titre, synthese)
    _couts(lignes, titre, portefeuille)
    if detail_des_couts is not None:
        _detail_des_couts(lignes, titre, detail_des_couts, portefeuille)
        _couts_estimes(lignes, titre, detail_des_couts)
    if valeur_reelle_estimee is not None:
        _valeur_reelle(lignes, titre, valeur_reelle_estimee)
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


# --- La valeur des actifs, aux cours de clôture (glossaire §3) ---------------------------

LARGEUR_NOM_VALEUR = 24
"""Un peu plus étroit que dans le tableau des positions : il faut loger le cours et le gain."""

LARGEUR_LIBELLE_VALEUR = 14 + 1 + LARGEUR_NOM_VALEUR + 1 + 10 + 1 + 12
"""Actif, nom, quantité et cours, séparateurs compris : un sous-total écrit sur cette largeur
tombe exactement sous la colonne « valeur »."""

ENTETE_VALEUR = (
    f"  {'actif':<14} {'nom':<{LARGEUR_NOM_VALEUR}} {'quantité':>10} {'cours':>12} "
    f"{'valeur':>14} {'gain':>12}"
)


def _nom_court(nom: str | None, largeur: int) -> str:
    nom = nom or ""
    if len(nom) > largeur:
        return nom[: largeur - 1] + "."
    return nom


def _valeur(lignes: list[str], titre: Titre, synthese: Synthese) -> None:
    valorisation = synthese.valorisation
    titre(f"Valeur des actifs au {valorisation.date.isoformat()}")

    if not valorisation.positions:
        lignes.append("  Aucune part détenue à cette date : rien à valoriser.")
        return

    sources = ", ".join(valorisation.sources) or "aucune"
    lignes.append(f"  Cours de clôture du marché principal en euros, source : {sources}.")
    lignes.append("  Ce ne sont pas les cours de Trade Republic : un écart de quelques dixièmes")
    lignes.append("  de pour cent est normal (D-48). Un cours d'un autre jour est signalé.")
    lignes.append("  La colonne « gain » est celle de la période des trois chiffres clés.")

    par_poche = valorisation.par_poche()
    for poche in Poche:
        du_groupe = [position for position in valorisation.positions if position.poche is poche]
        if not du_groupe:
            continue

        lignes.append("")
        lignes.append(f"  {poche.value}")
        lignes.append(ENTETE_VALEUR)
        for position in du_groupe:
            _ligne_valeur(lignes, position, synthese.de(position.position))
        totaux = par_poche[poche]
        lignes.append(
            f"  {'valeur de la poche':<{LARGEUR_LIBELLE_VALEUR}} {_lisible(totaux.valeur):>14}"
        )
        if not totaux.complet:
            lignes.append(
                f"    (partielle : {totaux.nombre_de_positions - totaux.nombre_valorisees} "
                "actif(s) de cette poche sans cours, voir ci-dessous)"
            )

    total = valorisation.total
    lignes.append("")
    lignes.append(f"  {'valeur totale':<{LARGEUR_LIBELLE_VALEUR}} {_lisible(total.valeur):>14}")

    if valorisation.non_valorisees:
        lignes.append("")
        combien = len(valorisation.non_valorisees)
        lignes.append(f"  Non valorisés, exclus de tous les totaux (D-53) : {combien}")
        for position in valorisation.non_valorisees:
            lignes += _enveloppe(
                f"{position.actif}  {position.poche.value}  {position.motif}", "    ", "      "
            )


def _ligne_valeur(
    lignes: list[str], position: PositionValorisee, rendements: Rendements | None
) -> None:
    gain = rendements.gain if rendements is not None else None
    if position.cours is None:
        cours = valeur = SANS_OBJET
    else:
        cours = _lisible(position.cours.valeur)
        valeur = _lisible(position.valeur)
    nom = _nom_court(position.position.nom_actif, LARGEUR_NOM_VALEUR)
    lignes.append(
        f"  {position.actif:<14} {nom:<{LARGEUR_NOM_VALEUR}} "
        f"{_lisible(position.quantite):>10} {cours:>12} {valeur:>14} {_lisible(gain):>12}"
    )
    if position.jour_decale:
        assert position.cours is not None
        lignes.append(
            f"  {'':<14} cours du {position.cours.date.isoformat()} "
            f"(dernier jour coté avant le {position.date.isoformat()}), {position.cours.place}"
        )
    if rendements is not None and not rendements.calculable and position.valorisee:
        lignes += _enveloppe(f"gain non calculable : {rendements.motif}", "    ", "      ")


# --- La performance, en montants bruts (D-21) -----------------------------------------


def _performance(
    lignes: list[str], titre: Titre, total: Totaux, synthese: Synthese | None = None
) -> None:
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

    if synthese is None:
        lignes.append("")
        lignes.append("  La valeur des actifs, le gain, le TRI et le TWRR ne sont pas dans ce")
        lignes.append("  rapport : ils ont besoin des cours de marché.")


# --- Les trois chiffres clés (D-22) ----------------------------------------------------

LARGEUR_LIBELLE_CLES = 34
LARGEUR_COLONNE_CLES = 13


def _periode_en_clair(synthese: Synthese) -> str:
    periode = synthese.periode
    total = synthese.total
    if periode.debut is None:
        origine = total.origine
        depuis = (
            f"depuis la première opération ({origine.isoformat()})"
            if origine is not None
            else "depuis le début"
        )
    else:
        depuis = f"du {periode.debut.isoformat()}"
    duree = f", soit {total.duree_jours} jours" if total.duree_jours is not None else ""
    return f"{depuis} jusqu'au {periode.fin.isoformat()}{duree}"


def _chiffres_cles(lignes: list[str], titre: Titre, synthese: Synthese) -> None:
    titre("Les trois chiffres clés (D-22)")
    lignes.append(f"  Période : {_periode_en_clair(synthese)}.")
    lignes.append("  Montants bruts : ni les frais ni les taxes n'y entrent (D-21).")
    lignes.append("")

    colonnes: list[tuple[str, Rendements]] = [("total", synthese.total)] + [
        (poche.value, rendements) for poche, rendements in synthese.par_poche.items()
    ]

    def cellule(rendements: Rendements, valeur: Callable[[Rendements], str]) -> str:
        # Un groupe dont rien n'est calculable — une poche entière sans cours, par exemple —
        # n'affiche **aucun** chiffre, pas même un « 0,00 » d'achats : ce zéro serait lu comme
        # « rien n'a été investi », alors qu'on ne sait simplement pas ce que ça vaut (D-53).
        return valeur(rendements) if rendements.calculable else SANS_OBJET

    def ligne(libelle: str, valeur: Callable[[Rendements], str]) -> None:
        cellules = "".join(f" {cellule(r, valeur):>{LARGEUR_COLONNE_CLES}}" for _, r in colonnes)
        lignes.append(f"  {libelle:<{LARGEUR_LIBELLE_CLES}}{cellules}")

    # L'en-tête : le nom de chaque colonne, aligné comme ses chiffres.
    entete = "".join(f" {nom:>{LARGEUR_COLONNE_CLES}}" for nom, _ in colonnes)
    lignes.append(f"  {'':<{LARGEUR_LIBELLE_CLES}}{entete}")
    ligne("valeur au début", lambda r: _lisible(r.valeur_debut))
    ligne("achats (titres reçus compris)", lambda r: _lisible(r.achats))
    ligne("ventes", lambda r: _lisible(r.ventes))
    ligne("dividendes (brut)", lambda r: _lisible(r.dividendes))
    ligne("distributions de capital", lambda r: _lisible(r.distributions))
    ligne("valeur à la fin", lambda r: _lisible(r.valeur_fin))
    ligne("GAIN en euros", lambda r: _lisible(r.gain))
    ligne("TRI (annuel)", lambda r: _pourcentage(r.tri))
    ligne("TWRR (sur la période)", lambda r: _pourcentage(r.twrr.taux))
    ligne("TWRR annualisé", lambda r: _pourcentage(r.twrr.annualise))

    lignes.append("")
    lignes.append("  gain = valeur à la fin - valeur au début - achats + ventes + dividendes")
    lignes.append("  + distributions. Le TRI est celui de TRI.PAIEMENTS dans un tableur ;")
    lignes.append("  flux.csv (« exporter-positions ») en donne la table. Le TWRR annualisé")
    lignes.append("  n'est écrit que si la période dépasse un an.")

    if synthese.total.peu_significatif:
        lignes.append("")
        lignes.append("  TRI et TWRR portent sur moins d'un an : peu significatifs (glossaire §5).")

    if synthese.total.partiel:
        lignes.append("")
        lignes.append(
            f"  PARTIEL : {len(synthese.total.exclues)} actif(s) détenu(s) sans cours sont exclus "
            "de ces chiffres (D-53),"
        )
        lignes.append("  achats compris. Voir « Non valorisés » ci-dessus.")

    if not synthese.total.fiable:
        lignes.append("")
        lignes.append("  NON FIABLE : au moins une position repose sur une histoire incomplète")
        lignes.append("  (vente au-delà du stock ou distribution excédentaire, D-45).")

    for nom, rendements in colonnes:
        if not rendements.calculable:
            lignes += _enveloppe(
                f"{nom} : gain et TRI non calculables. {rendements.motif}", "  ", "    "
            )
            continue
        if rendements.tri is None:
            lignes += _enveloppe(
                f"{nom} : TRI non calculable. {rendements.motif_tri}", "  ", "    "
            )
        if rendements.twrr.taux is None:
            lignes += _enveloppe(
                f"{nom} : TWRR non calculable. {rendements.twrr.motif}", "  ", "    "
            )


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


# --- Les coûts payés en détail, et les coûts estimés (étape 6) -------------------------

LARGEUR_LIBELLE_COUTS = 46
ENTETE_COUTS_PAR_ACTIF = (
    f"  {'actif':<14} {'nom':<{LARGEUR_NOM}} {'frais':>10} {'taxes':>10} "
    f"{'poids':>8} {'spread est.':>12}"
)


def _detail_des_couts(
    lignes: list[str], titre: Titre, detail: DetailDesCouts, portefeuille: Portefeuille
) -> None:
    """Les coûts payés, opération par opération puis actif par actif, avec leur poids.

    Le bloc précédent donne les mêmes totaux rangés par moment ; celui-ci dit **où** ils ont
    été pris, et ce qu'ils pèsent. Le poids répond à la question du propriétaire : « est-ce
    qu'un petit ordre ponctuel me coûte cher ? » (Q-21).
    """
    titre(f"Coûts payés du {_debut_en_clair(detail.periode)} au {detail.periode.fin.isoformat()}")
    if not detail.lignes:
        lignes.append("  Aucune opération sur cette période.")
        return

    lignes.append("  Le poids est la part des frais et taxes dans le montant brut de")
    lignes.append("  l'opération : 1,00 de frais sur un achat de 25,00 pèse 4,00 %.")

    par_poche = detail.par_poche()
    par_actif = detail.par_actif()
    for poche in Poche:
        if poche not in par_poche:
            continue
        lignes.append("")
        lignes.append(f"  {poche.value}")
        lignes.append(ENTETE_COUTS_PAR_ACTIF)
        for (actif, sa_poche), totaux in par_actif.items():
            if sa_poche is not poche:
                continue
            nom = _nom_court(detail.nom_de(actif, poche), LARGEUR_NOM)
            lignes.append(
                f"  {actif:<14} {nom:<{LARGEUR_NOM}} "
                f"{_lisible(totaux.frais):>10} {_lisible(totaux.taxes):>10} "
                f"{_pourcentage(totaux.poids_moyen):>8} "
                f"{_lisible(totaux.spread_estime, absent=SANS_OBJET):>12}"
            )
        groupe = par_poche[poche]
        lignes.append(
            f"  {'payé dans la poche':<{14 + 1 + LARGEUR_NOM}} "
            f"{_lisible(groupe.frais):>10} {_lisible(groupe.taxes):>10} "
            f"{_pourcentage(groupe.poids_moyen):>8} "
            f"{_lisible(groupe.spread_estime, absent=SANS_OBJET):>12}"
        )

    total = detail.total
    lignes.append("")
    for libelle, valeur in total.par_moment().items():
        # « autres » ne ramasse que ce que les trois moments nommés ne couvrent pas (des frais
        # sur une distribution de capital, par exemple). À zéro, il n'apprend rien : même
        # règle que dans le bloc des coûts payés au-dessus.
        if libelle == "autres" and valeur == Decimal("0.00"):
            continue
        lignes.append(f"  {libelle:<{LARGEUR_LIBELLE_COUTS}} {_lisible(valeur):>16}")
    lignes.append(f"  {'total payé':<{LARGEUR_LIBELLE_COUTS}} {_lisible(total.cout_paye):>16}")
    if detail.periode.depuis_le_debut:
        # Sur toute l'histoire, ce total doit valoir celui du bloc précédent : c'est le
        # contrôle que le propriétaire refait en additionnant couts.csv.
        attendu = portefeuille.total.frais + portefeuille.total.taxes
        if total.cout_paye != attendu:  # pragma: no cover - garde-fou
            lignes.append(
                f"  (écart avec le total du bloc précédent : {_lisible(attendu)} - à signaler)"
            )


def _debut_en_clair(periode) -> str:
    return "début" if periode.debut is None else periode.debut.isoformat()


def _couts_estimes(lignes: list[str], titre: Titre, detail: DetailDesCouts) -> None:
    """Le spread et les frais courants : estimés, donc annoncés comme tels (D-17)."""
    titre("Coûts estimés, jamais facturés (D-17)")
    lignes.append("  Ce bloc n'est pas une facture : ce sont des ordres de grandeur, calculés")
    lignes.append("  avec des taux par défaut. Ils ne figurent dans aucun chiffre ci-dessus.")

    total = detail.total
    lignes.append("")
    lignes.append("  L'ECART DE PRIX (SPREAD), payé à chaque achat et à chaque vente (D-30)")
    lignes.append("  Il est déjà compris dans le prix d'exécution : aucun relevé ne le montre,")
    lignes.append("  et c'est pour cela qu'il faut l'estimer.")
    par_poche = detail.par_poche()
    for poche in Poche:
        if poche not in par_poche:
            continue
        lignes.append(
            f"  {'spread estimé, poche ' + poche.value:<{LARGEUR_LIBELLE_COUTS}} "
            f"{_lisible(par_poche[poche].spread_estime):>16}"
        )
    lignes.append(
        f"  {'spread estimé, total':<{LARGEUR_LIBELLE_COUTS}} {_lisible(total.spread_estime):>16}"
    )
    if total.actifs_sans_type:
        lignes += _enveloppe(
            "PARTIEL : aucun spread n'est estimé pour "
            f"{', '.join(total.actifs_sans_type)} - leur « type » n'est pas déclaré dans "
            "actifs.toml. Lancez « dashboard actifs », qui le propose.",
            "  ",
            "    ",
        )

    lignes.append("")
    lignes.append("  LES FRAIS COURANTS DES ETF (TER), prélevés dans la valeur du fonds")
    if not detail.frais_courants:
        lignes.append("  Aucun ETF déclaré : rien à estimer. Le « type » de chaque actif se")
        lignes.append("  déclare dans actifs.toml (« dashboard actifs » le propose).")
    else:
        lignes.append(f"  {'actif':<14} {'valeur':>14} {'TER':>8} {'par an':>12}")
        for frais in detail.frais_courants:
            if frais.estimation is None:
                lignes.append(
                    f"  {frais.actif:<14} {_lisible(frais.position.valeur):>14} "
                    f"{SANS_OBJET:>8} {SANS_OBJET:>12}"
                )
                lignes += _enveloppe(str(frais.motif), "    ", "      ")
                continue
            lignes.append(
                f"  {frais.actif:<14} {_lisible(frais.estimation.base):>14} "
                f"{_pourcentage(frais.estimation.parametre.valeur / Decimal('100')):>8} "
                f"{_lisible(frais.estimation.montant):>12}"
            )
        estimes = [frais for frais in detail.frais_courants if frais.estimation]
        somme = sum((frais.estimation.montant for frais in estimes), Decimal("0.00"))
        lignes.append(
            f"  {'frais courants estimés, par an':<{LARGEUR_LIBELLE_COUTS}} {_lisible(somme):>16}"
        )
        lignes.append("")
        lignes.append("  C'est un coût de détention : il court chaque année, sans être prélevé")
        lignes.append("  sur votre compte. Le TER vient de votre déclaration dans actifs.toml.")


# --- La valeur réelle : si on vendait tout aujourd'hui (D-23) ---------------------------

LARGEUR_LIBELLE_REELLE = 40


def _valeur_reelle(lignes: list[str], titre: Titre, valeur: ValeurReelle) -> None:
    """Valeur brute moins ce que la sortie coûterait, poche par poche.

    C'est la seconde lecture voulue par le propriétaire (D-23) : la synthèse est brute et
    volontairement flatteuse, celle-ci répond à « combien j'ai vraiment ? ». Chaque retenue
    est une **estimation**, et chaque taux dit d'où il vient.
    """
    titre(f"Valeur réelle au {valeur.date.isoformat()} : si vous vendiez tout (D-23)")
    if not valeur.par_poche:
        lignes.append("  Aucune position détenue : rien à vendre.")
        return

    lignes.append("  Tout ce qui est retranché ici est estimé : les frais de vente d'après la")
    lignes.append("  grille de la banque, l'écart de prix d'après des mesures de marché, et")
    lignes.append("  l'impôt d'après les règles françaises. Ce n'est pas une déclaration.")

    colonnes = [(poche.value, du_groupe) for poche, du_groupe in valeur.par_poche.items()]
    largeur = 14

    def ligne(libelle: str, valeur_de) -> None:
        cellules = "".join(f" {valeur_de(groupe):>{largeur}}" for _, groupe in colonnes)
        lignes.append(f"  {libelle:<{LARGEUR_LIBELLE_REELLE}}{cellules}")

    lignes.append("")
    entete = "".join(f" {nom:>{largeur}}" for nom, _ in colonnes)
    lignes.append(f"  {'':<{LARGEUR_LIBELLE_REELLE}}{entete}")
    ligne("valeur brute", lambda groupe: _lisible(groupe.valeur_brute))
    ligne("frais de vente estimés", lambda groupe: _lisible(-groupe.frais_de_vente))
    ligne("écart de prix estimé", lambda groupe: _lisible(-groupe.spread))
    ligne(
        "impôt estimé",
        lambda groupe: _lisible(
            -groupe.impot.impot if groupe.impot.impot is not None else None,
            absent=SANS_OBJET,
        ),
    )
    ligne(
        "VALEUR REELLE",
        lambda groupe: _lisible(groupe.valeur_reelle, absent=SANS_OBJET),
    )

    lignes.append("")
    lignes.append(
        f"  {'valeur réelle totale':<{LARGEUR_LIBELLE_REELLE}} "
        f"{_lisible(valeur.valeur_reelle, absent=SANS_OBJET):>{largeur}}"
    )
    if valeur.valeur_reelle is not None:
        ecart = valeur.valeur_brute - valeur.valeur_reelle
        lignes.append(
            f"  {'ce que la sortie coûterait':<{LARGEUR_LIBELLE_REELLE}} "
            f"{_lisible(ecart):>{largeur}}"
        )

    if valeur.minoree:
        # Le cas du PEA : son impôt porte sur le gain du plan, dont une part est déjà en
        # espèces. L'argent n'est pas compté à l'actif, son impôt l'est au passif : le taire
        # ferait passer une valeur minorée pour une valeur exacte.
        lignes.append("")
        lignes += _enveloppe(
            f"MINORÉE : au moins {_lisible(valeur.hors_des_titres)} de gains déjà encaissés "
            "dans un plan (ventes passées, dividendes) sont restés dans ses espèces, que "
            "l'application ne suit pas (D-11). Leur impôt est compté ci-dessus, leur argent "
            "non : vous toucheriez davantage.",
            "  ",
            "  ",
        )

    if valeur.partielle:
        lignes.append("")
        lignes.append("  PARTIEL : tout n'entre pas dans ces chiffres.")
        for exclue in valeur.exclues:
            lignes += _enveloppe(
                f"{exclue.position.actif} ({exclue.position.poche.value}) : {exclue.motif}",
                "    - ",
                "      ",
            )
        for groupe in valeur.poches_non_calculables:
            motif = groupe.motif_incalculable
            if motif:
                lignes += _enveloppe(
                    f"poche {groupe.poche.value} : {motif}", "    - ", "      "
                )

    _detail_des_impots(lignes, valeur)


def _detail_des_impots(lignes: list[str], valeur: ValeurReelle) -> None:
    """Pour chaque poche : la base, la règle, et les sources des taux. C'est ce qui rend
    l'impôt refaisable à la main."""
    lignes.append("")
    lignes.append("  Comment chaque impôt est calculé")
    for poche, groupe in valeur.par_poche.items():
        impot = groupe.impot
        lignes.append("")
        lignes.append(f"  {poche.value}")
        lignes += _enveloppe(impot.regle, "    ", "      ")
        if impot.composantes:
            for libelle, montant in impot.composantes:
                lignes.append(
                    f"    {libelle:<{LARGEUR_LIBELLE_REELLE + 18}} {_lisible(montant):>14}"
                )
            # La première ligne se compare à l'application de la banque, la deuxième explique
            # l'écart : c'est la lecture que le propriétaire a demandée après avoir buté sur une
            # plus-value négative qu'aucun chiffre du rapport ne justifiait.
            lignes.append("      (ces deux lignes s'additionnent dans le total ci-dessous)")
        if impot.base is None:
            lignes += _enveloppe(f"non calculable : {impot.motif}", "    ", "      ")
            continue
        if impot.hors_des_titres > Decimal("0.00"):
            lignes += _enveloppe(
                f"dont {_lisible(impot.hors_des_titres)} de gains déjà encaissés, restés dans "
                "les espèces du plan : leur impôt est compté, leur argent n'est pas dans la "
                "valeur ci-dessus",
                "    ",
                "      ",
            )
        if impot.base_avant_plancher is not None and impot.base_avant_plancher != impot.base:
            lignes.append(
                f"    {'somme des plus-values et moins-values':<{LARGEUR_LIBELLE_REELLE + 18}} "
                f"{_lisible(impot.base_avant_plancher):>14}"
            )
            lignes.append("      (négative ou exonérée : la base imposable retombe à zéro)")
        lignes.append(
            f"    {'base imposable':<{LARGEUR_LIBELLE_REELLE + 18}} {_lisible(impot.base):>14}"
        )
        lignes.append(
            f"    {'taux appliqué':<{LARGEUR_LIBELLE_REELLE + 18}} "
            f"{_pourcentage((impot.taux or Decimal('0')) / Decimal('100')):>14}"
        )
        lignes.append(
            f"    {'impôt estimé':<{LARGEUR_LIBELLE_REELLE + 18}} {_lisible(impot.impot):>14}"
        )
        if not impot.fiable:
            lignes.append("      NON FIABLE : une position repose sur une histoire incomplète")

    _sources_et_hypotheses(lignes, valeur)


def _sources_et_hypotheses(lignes: list[str], valeur: ValeurReelle) -> None:
    lignes.append("")
    lignes.append("  D'où viennent les taux")
    for parametre in valeur.parametres_cites:
        lignes += _enveloppe(
            f"{parametre.en_clair} - {parametre.nom} ({parametre.origine}) : {parametre.source}",
            "    - ",
            "      ",
        )

    hypotheses: list[str] = []
    for groupe in valeur.par_poche.values():
        for hypothese in groupe.impot.hypotheses:
            if hypothese not in hypotheses:
                hypotheses.append(hypothese)
    if hypotheses:
        lignes.append("")
        lignes.append("  Ce que ce calcul suppose")
        for hypothese in hypotheses:
            lignes += _enveloppe(hypothese, "    - ", "      ")
    lignes.append("")
    lignes.append("  Ne sont pas comptés : l'impôt sur les dividendes déjà reçus et sur les")
    lignes.append("  ventes déjà faites. Ils sont dus quoi qu'il arrive, ce ne sont pas des")
    lignes.append("  coûts de sortie. L'application estime, elle ne déclare pas (D-26).")


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
