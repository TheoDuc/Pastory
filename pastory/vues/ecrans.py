"""Quel écran montrer, et avec quels chiffres : le seul endroit qui relie l'état aux écrans.

Il rend les six morceaux de la page — les onglets, le bouton de l'annexe, les filtres (et
s'ils sont cachés), le corps, et la classe de la page, qui dit si le livre est fermé (la
couverture) ou ouvert — à partir de l'état choisi à l'écran et des chiffres.

Chaque chapitre s'ouvre sur son numéro, son titre, sa phrase d'introduction et son colophon
(d'où viennent les chiffres), puis un fleuron (charte graphique §4.2, §4.4), posés ici une
fois pour toutes plutôt que dans chaque écran.
"""

from __future__ import annotations

from dash import html

from pastory.vues import (
    accueil,
    actifs,
    bandeau,
    colophon,
    detail,
    diversification,
    frais,
    portefeuilles,
    projections,
    surveiller,
    synthese,
)
from pastory.vues.briques import bloc, mot, ouverture
from pastory.vues.chiffres import Chiffres, Echec, Vue
from pastory.vues.surveiller import Point

Rendu = tuple[list, list, list, bool, object, str]

CLASSE_DE_LA_COUVERTURE = "livre livre--couverture"
CLASSE_DES_PAGES = "livre"


def rendre(chiffres: Chiffres, etat: dict) -> Rendu:
    base = chiffres.base()
    onglet = etat.get("onglet", bandeau.ONGLETS[0].cle)

    if isinstance(base, Echec) or onglet == bandeau.ACCUEIL:
        # La couverture : la navigation et le colophon sont masqués (le livre est fermé), et
        # sans export lisible elle est le seul écran — cinq onglets qui ramènent tous au dépôt
        # feraient croire qu'il y a quelque chose derrière (conception §5.1).
        corps = accueil.ecran(
            base,
            chiffres.dossier(),
            chiffres.tiers,
            _messages_du_depot(etat.get("message")),
            chiffres.demonstration,
            chiffres.inventaire(),
            etat.get("a_supprimer"),
        )
        return (
            [] if isinstance(base, Echec) else bandeau.onglets(onglet),
            [] if isinstance(base, Echec) else bandeau.lien_vers_le_detail(onglet),
            [],
            True,
            corps,
            CLASSE_DE_LA_COUVERTURE,
        )

    vue = chiffres.vue(etat.get("periode", "tout"), etat.get("poches"))
    if isinstance(vue, Echec):  # pragma: no cover - la base vient d'être lue sans échec
        return rendre(chiffres, {**etat, "onglet": bandeau.ACCUEIL})

    points = surveiller.points(base)
    lu = _colophon(vue, onglet)
    filtres = bandeau.filtres(
        onglet, etat.get("periode", "tout"), etat.get("type", "tous"), vue.poches_presentes,
        vue.poches, colophon.note_des_filtres(lu),
    )
    if not filtres:
        # Un chapitre sans filtre a son sommaire à la place (D-104) : jamais un faux filtre.
        filtres = bandeau.sommaire(onglet, etat.get("rubrique", "classes"))
    # Avec plusieurs portefeuilles, le nom de celui qu'on lit ne quitte pas l'écran (D-109).
    inventaire = chiffres.inventaire()
    lequel = (
        [bandeau.portefeuille_ouvert(inventaire.ouvert.nom)]
        if portefeuilles.plusieurs(inventaire) and inventaire.ouvert is not None
        else []
    )
    return (
        bandeau.onglets(onglet),
        [*lequel, *bandeau.lien_vers_le_detail(onglet)],
        filtres,
        not filtres,
        _chapitre(onglet, _corps(onglet, vue, points, chiffres, etat), colophon.note(lu)),
        CLASSE_DES_PAGES,
    )


def _chapitre(onglet: str, corps, note=None) -> html.Div:
    """Le chapitre : son ouverture, puis son contenu.

    Il porte son nom (`data-chapitre`) : `dessin.js` ne joue la transition que si ce nom change
    — à chaque changement de chapitre, et à lui seul ; un filtre ne bouge rien (charte
    graphique §7). Une clé React n'y suffirait pas : Dash recrée le contenu à chaque rappel,
    quelle que soit la clé (mesuré dans le navigateur à l'étape 9 bis)."""
    o = bandeau.onglet(onglet)
    tete = [ouverture(o.numero, o.nom, o.introduction, note)] if o is not None else []
    return html.Div([*tete, corps], className="chapitre", **{"data-chapitre": onglet})


def _corps(onglet: str, vue: Vue, points: list[Point], chiffres: Chiffres, etat: dict):
    if onglet == "synthese":
        return synthese.ecran(vue, chiffres, int(etat.get("page", 0)))
    if onglet == "detail":
        return detail.ecran(vue, points)
    if onglet == "frais":
        return frais.ecran(vue)
    if onglet == "diversification":
        return diversification.ecran(
            vue, etat.get("rubrique", "classes"), bool(etat.get("deplie", False))
        )
    if onglet == "actifs":
        return actifs.ecran(
            vue, etat.get("type", "tous"), etat.get("tri", "valeur"), int(etat.get("sens", -1))
        )
    if onglet == "projections":
        return projections.ecran(vue)
    return html.Div(
        bloc(
            "Écran en cours de réalisation",
            html.P(
                "Cet onglet arrive dans un prochain bloc de l'étape 9. Les chiffres sont "
                "déjà calculés : « pastory positions » les montre en attendant.",
                className="chapeau",
            ),
        ),
        className="rangee rangee--large",
    )


def _colophon(vue: Vue, onglet: str) -> colophon.Colophon:
    """Le colophon dit **ce sur quoi portent les chiffres de cet onglet** : la période et les
    poches seulement là où elles agissent."""
    base = vue.construit
    depot = base.rapport.depot
    o = bandeau.onglet(onglet)
    synthese = vue.synthese if o is not None and o.periode else base.synthese
    valorisation = synthese.valorisation
    total = synthese.total
    diversification = base.diversification
    arretes = (
        (diversification.arrete_du, diversification.arrete_au)
        if diversification is not None and onglet == "diversification"
        else None
    )
    avec_periode = o is not None and o.periode and total.origine is not None
    return colophon.lire(
        export_du=depot.premier_jour,
        export_au=depot.dernier_jour,
        cours_au=_dernier_cours(valorisation),
        avec_cours=bool(valorisation.positions),
        sources=valorisation.sources,
        debut=total.origine if avec_periode else None,
        fin=synthese.periode.fin,
        jours=total.duree_jours,
        positions=len(valorisation.positions),
        non_valorisees=[_nom(p.position) for p in valorisation.non_valorisees],
        poches_retenues=(
            None if o is None or not o.poches or vue.toutes_les_poches else vue.poches
        ),
        arretes=arretes,
    )


def _dernier_cours(valorisation):
    """Le jour du plus récent cours **réellement employé** — pas la date demandée : hors ligne
    ou sans source, aucun cours n'est connu, et dire « arrêtés au » aujourd'hui serait faux."""
    jours = [p.cours.date for p in valorisation.valorisees]
    return max(jours) if jours else None


def _nom(position) -> str:
    return position.nom_actif or position.actif


def _messages_du_depot(messages: list[dict] | None):
    if not messages:
        return None
    return html.Ul(
        [
            html.Li(
                [
                    mot(m.get("mot") or "Déposé")
                    if m["accepte"]
                    else mot(m.get("mot") or "Refusé", "absent"),
                    " " + m["texte"],
                ],
                className="depot__retour",
            )
            for m in messages
        ],
        className="depot__retours",
        role="status",
    )
