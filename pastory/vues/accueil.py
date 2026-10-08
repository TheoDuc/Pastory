"""L'accueil : où trouver l'export, où le déposer, et ce que la lecture en a tiré.

C'est le premier écran d'un nouvel utilisateur (feuille de route, étape 9), et la seule chose
qu'il ait à faire (D-80). Il dit donc, pour quelqu'un qui n'a jamais ouvert Pastory :

- **où trouver l'export** dans l'application Trade Republic, et quelle période choisir ;
- **où le déposer** : ici même, dans la zone de dépôt (D-95). Le dossier est montré aussi ;
- une fois le fichier lu, **la période couverte** et **ce qui n'a pas été compris** — un type
  d'opération inconnu n'est jamais ignoré ni rangé au hasard (règle 5).

Un portefeuille vide n'est pas une erreur, et ce message ne doit pas en avoir l'air (§5.1).
"""

from __future__ import annotations

from pathlib import Path

from dash import dcc, html

from pastory import assembleur
from pastory.adaptateurs.trade_republic.depot import CHEMIN_DANS_L_APPLICATION, NOM_PAR_DEFAUT
from pastory.vues import format as f
from pastory.vues.briques import aide, bloc, choix, ligne_de_liste, mot
from pastory.vues.chiffres import Echec

ETAPES = (
    f"Dans l'application Trade Republic : {CHEMIN_DANS_L_APPLICATION.replace(' > ', ' → ')}.",
    "Choisissez « toutes les transactions », depuis l'ouverture du compte : un export qui "
    "commence plus tard donne une histoire incomplète.",
    f"Déposez ici le fichier obtenu (« {NOM_PAR_DEFAUT} »). Vous pouvez en déposer plusieurs : "
    "ils se cumulent, et une opération présente dans deux fichiers n'est comptée qu'une fois.",
)


def zone_de_depot() -> html.Div:
    return html.Div(
        [
            dcc.Upload(
                html.Div(
                    [
                        html.B("Déposez votre export ici"),
                        html.Span(" ou cliquez pour choisir le fichier", className="reference"),
                    ]
                ),
                id="depot",
                className="depot",
                multiple=True,
                accept=".csv",
            ),
            html.P(id="depot-message", className="depot__message", **{"aria-live": "polite"}),
        ]
    )


def _comment_faire(dossier: Path, tiers: bool) -> html.Section:
    if tiers:
        # L'export d'un tiers est lu dans son propre dossier, sans rien copier dans le dossier
        # de dépôt de l'utilisateur : aucune zone de dépôt ici (règle 2 de CLAUDE.md).
        return bloc(
            "Les exports lus",
            html.P(
                [
                    "Cet écran lit les exports d'un autre dossier que le vôtre, sans aucun appel "
                    "réseau ni aucune copie : ",
                    html.Code(str(dossier)),
                ],
                className="chapeau",
            ),
        )
    return bloc(
        "Déposer un export",
        html.Div(
            [
                html.P(
                    "Pastory lit l'export des transactions que Trade Republic fournit dans son "
                    "application. C'est la seule chose à faire : tout le reste — les cours, les "
                    "frais des fonds, leur composition — est trouvé seul, et chaque valeur dit "
                    "d'où elle vient.",
                    className="chapeau",
                ),
                html.Ol([html.Li(etape) for etape in ETAPES], className="etapes"),
                zone_de_depot(),
                html.P(
                    [
                        "Les exports sont rangés sur votre ordinateur, dans ",
                        html.Code(str(dossier)),
                        ". Rien ne sort de votre machine. ",
                        html.Button(
                            "Ouvrir le dossier",
                            id="ouvrir-dossier",
                            type="button",
                            className="bouton bouton--clair",
                            n_clicks=0,
                        ),
                    ],
                    className="reference depot__dossier",
                ),
            ]
        ),
    )


def ecran(base: assembleur.Construit | Echec, dossier: Path, tiers: bool = False) -> html.Div:
    """L'accueil, dans l'un de ses trois états : vide, lu, ou empêché."""
    rangees: list = [html.Div([_comment_faire(dossier, tiers)], className="rangee rangee--large")]
    if isinstance(base, Echec):
        if base.nature != "aucun-export":
            rangees.append(_empeche(base))
        return html.Div(rangees)

    rangees.append(
        html.Div(
            [_les_exports(base), _ce_que_la_lecture_a_trouve(base)],
            className="rangee rangee--deux rangee--apres",
        )
    )
    return html.Div(rangees)


def _empeche(echec: Echec) -> html.Div:
    """Un fichier empêche le calcul : un réglage mal écrit, ou une mémoire illisible. Ce n'est
    pas une panne, et le message dit lequel et pourquoi (conception §5.4)."""
    titre = (
        "Un fichier de réglages empêche le calcul"
        if echec.nature == "fichier-a-corriger"
        else "La mémoire de Pastory est illisible"
    )
    return html.Div(
        [bloc(titre, html.P(echec.message, className="chapeau"))],
        className="rangee rangee--large rangee--apres",
    )


def _les_exports(base: assembleur.Construit) -> html.Section:
    depot = base.rapport.depot
    lignes: list = []
    for lu in depot.fichiers:
        periode = (
            f"du {f.date_courte(lu.premier_jour)} au {f.date_courte(lu.dernier_jour)}"
            if lu.premier_jour is not None
            else "aucune date lisible"
        )
        lignes.append(ligne_de_liste(lu.nom, f"{lu.lignes} lignes, {periode}", "reference"))
    for trou in depot.trous():
        lignes.append(
            ligne_de_liste(
                [
                    mot("Trou"),
                    f" Aucun fichier ne couvre la période du {f.date_courte(trou.du)} au "
                    f"{f.date_courte(trou.au)} : des opérations peuvent y manquer.",
                ]
            )
        )
    if depot.doublons:
        lignes.append(
            ligne_de_liste(
                f"{depot.doublons} ligne(s) présente(s) dans plusieurs fichiers, comptée(s) "
                "une seule fois"
            )
        )
    for nom, raison in depot.fichiers_ignores:
        lignes.append(ligne_de_liste([mot("Ignoré", "absent"), f" {nom} : {raison}."]))
    if depot.premier_jour is not None:
        lignes.append(
            ligne_de_liste(
                ["Période couverte ", *aide("periodeCouverte")],
                f"du {f.date_courte(depot.premier_jour)} au {f.date_courte(depot.dernier_jour)}",
                className="liste-parts__total",
            )
        )
    nombre = len(depot.fichiers)
    return bloc(
        "Vos exports",
        html.Ul(lignes, className="liste-parts"),
        note=f"{nombre} fichier{'s' if nombre > 1 else ''}",
    )


def _ce_que_la_lecture_a_trouve(base: assembleur.Construit) -> html.Section:
    rapport = base.rapport
    lignes: list = [
        ligne_de_liste("Lignes lues", str(rapport.lignes_lues)),
        ligne_de_liste("Opérations sur vos actifs", str(len(rapport.operations))),
        ligne_de_liste(
            "Mouvements d'espèces, laissés de côté (Pastory ne suit que les actifs)",
            str(sum(rapport.especes_par_type.values())),
        ),
    ]
    if rapport.types_inconnus:
        for type_affiche, nombre in rapport.types_inconnus.most_common():
            lignes.append(
                ligne_de_liste(
                    [mot("Type inconnu"), *aide("typeInconnu"), f" {type_affiche}"],
                    f"{nombre} ligne(s)",
                )
            )
    else:
        lignes.append(
            ligne_de_liste("Aucun type d'opération inconnu", None, className="liste-parts__total")
        )
    return bloc(
        "Ce que la lecture a trouvé",
        html.Div(
            [
                html.Ul(lignes, className="liste-parts"),
                html.P(
                    html.Button(
                        "Voir la synthèse",
                        # Pas l'identifiant de l'onglet : deux éléments du même nom, et Dash perd
                        # le clic sur l'un d'eux (l'onglet « Synthèse » ne répondait plus).
                        id=choix("aller", "synthese"),
                        type="button",
                        className="bouton bouton--clair",
                        n_clicks=0,
                    ),
                    className="depot__suite",
                ),
            ]
        ),
    )
