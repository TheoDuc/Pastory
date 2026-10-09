"""Quel écran montrer, et avec quels chiffres : le seul endroit qui relie l'état aux écrans.

Il rend les six morceaux de la page — les onglets, le compteur, les filtres (et s'ils sont
cachés), l'état des données, le corps — à partir de l'état choisi à l'écran et des chiffres.
"""

from __future__ import annotations

from dash import html

from pastory.vues import (
    accueil,
    actifs,
    bandeau,
    diversification,
    frais,
    surveiller,
    synthese,
)
from pastory.vues.briques import bloc, mot
from pastory.vues.chiffres import Chiffres, Echec, Vue
from pastory.vues.surveiller import Point

Rendu = tuple[list, list, list, bool, list, object]


def rendre(chiffres: Chiffres, etat: dict) -> Rendu:
    base = chiffres.base()
    onglet = etat.get("onglet", bandeau.ONGLETS[0].cle)

    if isinstance(base, Echec) or onglet == bandeau.ACCUEIL:
        # Sans export lisible, l'accueil est le seul écran, et **les onglets n'apparaissent
        # pas** : cinq onglets qui ramènent tous au dépôt feraient croire qu'il y a quelque chose
        # derrière (arbitrage du propriétaire, bloc 9.1 ; conception §5.1).
        corps = accueil.ecran(base, chiffres.dossier(), chiffres.tiers)
        messages = _messages_du_depot(etat.get("message"))
        if messages is not None:
            corps.children.insert(0, messages)
        etat_des_donnees = [] if isinstance(base, Echec) else _etat_de_l_export(base)
        compteur = None if isinstance(base, Echec) else len(surveiller.points(base))
        return (
            [] if isinstance(base, Echec) else bandeau.onglets(onglet),
            bandeau.compteur(compteur),
            [],
            True,
            etat_des_donnees,
            corps,
        )

    vue = chiffres.vue(etat.get("periode", "tout"), etat.get("poches"))
    if isinstance(vue, Echec):  # pragma: no cover - la base vient d'être lue sans échec
        return rendre(chiffres, {**etat, "onglet": bandeau.ACCUEIL})

    points = surveiller.points(base)
    filtres = bandeau.filtres(
        onglet, etat.get("periode", "tout"), etat.get("type", "tous"), vue.poches_presentes,
        vue.poches,
    )
    return (
        bandeau.onglets(onglet),
        bandeau.compteur(len(points)),
        filtres,
        not filtres,
        _etat_des_donnees(vue, onglet),
        _corps(onglet, vue, points, chiffres, etat),
    )


def _corps(onglet: str, vue: Vue, points: list[Point], chiffres: Chiffres, etat: dict):
    if onglet == "synthese":
        return synthese.ecran(vue, chiffres, int(etat.get("page", 0)))
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


def _etat_de_l_export(base) -> list:
    depot = base.rapport.depot
    return bandeau.etat_des_donnees(export_du=depot.premier_jour, export_au=depot.dernier_jour)


def _etat_des_donnees(vue: Vue, onglet: str) -> list:
    """L'état des données dit **ce sur quoi portent les chiffres de cet onglet** : la période
    et les poches seulement là où elles agissent."""
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
    return bandeau.etat_des_donnees(
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
    return html.Div(
        html.Ul(
            [
                html.Li(
                    [
                        mot("Déposé") if m["accepte"] else mot("Refusé", "absent"),
                        " " + m["texte"],
                    ],
                    className="depot__retour",
                )
                for m in messages
            ],
            className="depot__retours",
        ),
        className="rangee rangee--large",
        role="status",
    )
