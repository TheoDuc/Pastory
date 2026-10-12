"""La couverture du livre : où trouver l'export, où le déposer, et ce que la lecture en a tiré.

C'est le premier écran de chaque session, et la seule chose qu'un nouvel utilisateur ait à
faire (D-80). Fond brun reliure, le logo et le nom en or, un filet et un fleuron, puis une
**étiquette** de papier qui porte le dépôt (charte graphique §4.1) :

- **sans données** : quel fichier déposer et où l'obtenir dans l'application Trade Republic, en
  deux phrases, puis la zone de dépôt ;
- **avec données** : la période couverte, la dernière opération lue, et deux actions : **ouvrir le
  livre**, ou **déposer un export plus récent**. Un export récent s'ajoute aux précédents, et une
  opération présente dans deux fichiers n'est comptée qu'une fois (D-80, D-95) : un export
  complet plus récent vaut donc un remplacement.

**La couverture tient sur un écran, sans défiler** (retour du propriétaire, étape 9 bis) : le
détail de la lecture — fichiers lus, lignes, opérations, espèces, dossier — est dans un **volet
replié** de l'étiquette. Mais **une alerte ne se replie jamais** : un type d'opération inconnu
(règle 5), une période qu'aucun fichier ne couvre, un fichier ignoré restent visibles, au-dessus
des actions.

Un portefeuille vide n'est pas une erreur, et ce message ne doit pas en avoir l'air (§5.1).
"""

from __future__ import annotations

from pathlib import Path

from dash import dcc, html

from pastory import assembleur
from pastory.adaptateurs.trade_republic.depot import (
    CHEMIN_DANS_L_APPLICATION,
    NOM_PAR_DEFAUT,
    Inventaire,
)
from pastory.demonstration import MENTION
from pastory.vues import format as f
from pastory.vues import portefeuilles
from pastory.vues.bandeau import bascule_du_theme
from pastory.vues.briques import aide, choix, dessin, fleuron, ligne_de_liste, mot
from pastory.vues.chiffres import Echec

CHEMIN = CHEMIN_DANS_L_APPLICATION.replace(" > ", " → ")
"""Le chemin des menus de l'application Trade Republic : une seule constante, dans l'adaptateur."""

ETAPES = (
    f"Dans l'application Trade Republic : {CHEMIN}.",
    "Choisissez « toutes les transactions », depuis l'ouverture du compte : un export qui "
    "commence plus tard donne une histoire incomplète.",
    f"Déposez ici le fichier obtenu (« {NOM_PAR_DEFAUT} »). Plus tard, un export plus récent "
    "du même compte mettra ce portefeuille à jour ; l'export d'un autre compte deviendra un "
    "autre portefeuille, jamais mélangé au vôtre.",
)

CE_QUE_DEVIENT_UN_DEPOT = (
    "plus récent, il met ce portefeuille à jour · d'un autre compte, il devient un autre "
    "portefeuille"
)


def zone_de_depot(
    titre: str = "Déposez votre export ici",
    precision: str = "glissez le fichier ici, ou cliquez pour le choisir",
) -> html.Div:
    return html.Div(
        [
            dcc.Upload(
                html.Div(
                    [
                        html.B(titre),
                        html.Br(),
                        html.Span(precision, className="reference"),
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


def ecran(
    base: assembleur.Construit | Echec,
    dossier: Path,
    tiers: bool = False,
    messages: object = None,
    demonstration: bool = False,
    inventaire: Inventaire | None = None,
    a_supprimer: str | None = None,
) -> html.Div:
    """La couverture, dans l'un de ses trois états : vide, lu, ou empêché.

    En **démonstration** (D-107), l'étiquette s'ouvre sur un avis — ce portefeuille est fictif —
    et ne propose aucun dépôt : un vrai export n'a rien à faire dans ce dossier-là."""
    avis = [_avis_de_demonstration()] if demonstration else []
    return html.Div(
        html.Section(
            [
                html.Div(bascule_du_theme(), className="couverture__outils"),
                html.Div(
                    [
                        dessin("logo", None),
                        html.H1("Pastory", className="couverture__titre"),
                        fleuron(),
                        html.Div(
                            [
                                messages,
                                *avis,
                                *_etiquette(
                                    base,
                                    dossier,
                                    tiers or demonstration,
                                    demonstration,
                                    inventaire,
                                    a_supprimer,
                                ),
                            ],
                            className="cartouche",
                        ),
                    ],
                    className="couverture__interieur",
                ),
            ],
            className="couverture",
        ),
        className="accueil",
    )


def _etiquette(
    base,
    dossier: Path,
    sans_depot: bool,
    demonstration: bool = False,
    inventaire: Inventaire | None = None,
    a_supprimer: str | None = None,
) -> list:
    """`sans_depot` : l'export d'un tiers ou la démonstration — on y lit, on n'y dépose rien."""
    if isinstance(base, Echec):
        contenu: list = []
        if base.nature != "aucun-export":
            contenu.append(_empeche(base))
        # La démonstration écrit elle-même son export : sans lui, il n'y a rien à expliquer de
        # plus que l'avis et l'empêchement.
        return contenu if demonstration else [*contenu, *_premier_depot(dossier, sans_depot)]
    if demonstration:
        titre = "Un portefeuille fictif"
    elif portefeuilles.plusieurs(inventaire) and base.rapport.depot.portefeuille:
        # Avec plusieurs portefeuilles, l'étiquette porte le nom de celui qu'elle décrit.
        titre = base.rapport.depot.portefeuille
    else:
        titre = "Votre livre"
    return _livre_lu(base, dossier, sans_depot, titre, inventaire, a_supprimer)


def _avis_de_demonstration() -> html.P:
    return html.P(
        [
            mot(MENTION),
            " Ce portefeuille est fictif : des opérations inventées, sur des titres réels dont "
            "les cours, les frais et la composition sont les vrais. Pour suivre votre "
            "portefeuille, fermez cette fenêtre et ouvrez « Pastory », sans « démonstration ».",
        ],
        className="cartouche__alerte",
    )


def _volet(titre: str, contenu: list, ouvert: bool = False) -> html.Details:
    """Un volet replié dans l'étiquette : ce qui éclaire sans être nécessaire au premier coup
    d'œil. Il s'ouvre sur place, sans rien appeler."""
    return html.Details(
        [
            html.Summary(titre, className="volet__titre"),
            html.Div(contenu, className="volet__corps"),
        ],
        className="volet",
        open=ouvert,
    )


# --- Sans données -------------------------------------------------------------------------


def _premier_depot(dossier: Path, tiers: bool) -> list:
    if tiers:
        # L'export d'un tiers est lu dans son propre dossier, sans rien copier dans le dossier
        # de dépôt de l'utilisateur : aucune zone de dépôt ici (règle 2 de CLAUDE.md).
        return [
            html.H2("Les exports lus", className="cartouche__titre"),
            html.P(
                [
                    "Cet écran lit les exports d'un autre dossier que le vôtre, sans aucun appel "
                    "réseau ni aucune copie : ",
                    html.Code(str(dossier)),
                ],
                className="chapeau",
            ),
        ]
    return [
        html.H2("Déposer un export", className="cartouche__titre"),
        html.P(
            "Pastory lit l'export des transactions, un fichier CSV que Trade Republic fournit "
            f"dans son application ({CHEMIN}) : demandez « toutes les transactions », depuis "
            "l'ouverture du compte, et déposez-le ici. C'est la seule chose à faire : le reste — "
            "cours, frais des fonds, composition — est trouvé seul, et chaque valeur dit d'où "
            "elle vient.",
            className="chapeau",
        ),
        zone_de_depot(),
        _volet(
            "Pas à pas, et où vos exports sont rangés",
            [html.Ol([html.Li(etape) for etape in ETAPES], className="etapes"),
             _ou_sont_les_exports(dossier)],
        ),
    ]


def _ou_sont_les_exports(dossier: Path) -> html.P:
    return html.P(
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
    )


def _empeche(echec: Echec) -> html.Div:
    """Un fichier empêche le calcul : un réglage mal écrit, ou une mémoire illisible. Ce n'est
    pas une panne, et le message dit lequel et pourquoi (conception §5.4)."""
    titre = (
        "Un fichier de réglages empêche le calcul"
        if echec.nature == "fichier-a-corriger"
        else "La mémoire de Pastory est illisible"
    )
    return html.Div(
        [html.B(titre), html.Br(), echec.message], className="cartouche__alerte"
    )


# --- Avec données -------------------------------------------------------------------------


def _livre_lu(
    base: assembleur.Construit,
    dossier: Path,
    tiers: bool,
    titre: str = "Votre livre",
    inventaire: Inventaire | None = None,
    a_supprimer: str | None = None,
) -> list:
    depot = base.rapport.depot
    lignes: list = []
    if depot.premier_jour is not None:
        lignes += [
            ligne_de_liste(
                ["Période couverte ", *aide("periodeCouverte")],
                f"du {f.date_courte(depot.premier_jour)} au {f.date_courte(depot.dernier_jour)}",
            ),
            # L'export ne porte pas la date de sa création : on donne celle de sa dernière
            # opération, et on le dit, plutôt que d'inventer une date.
            ligne_de_liste(
                "Dernière opération lue", f"le {f.date_courte(depot.dernier_jour)}"
            ),
        ]
    # Là où l'on dépose, le détail liste les portefeuilles, et permet de les renommer ou de
    # les supprimer (D-109). Ailleurs — un tiers, la démonstration — le seul export lu.
    gerables = inventaire is not None and not tiers and bool(inventaire.portefeuilles)
    detail: list = [
        html.H3(
            "Vos portefeuilles" if portefeuilles.plusieurs(inventaire) else "Votre export",
            className="volet__sous-titre",
        ),
        *(
            [
                *portefeuilles.gestion(inventaire, a_supprimer),
                html.Ul(portefeuilles.restes_de_la_lecture(base), className="liste-parts"),
            ]
            if gerables
            else [_les_exports(base)]
        ),
        html.H3("Ce que la lecture a trouvé", className="volet__sous-titre"),
        _ce_que_la_lecture_a_trouve(base),
    ]
    if not tiers:
        detail.append(_ou_sont_les_exports(dossier))
    actions: list = [
        html.Button(
            "Ouvrir le livre",
            # Pas l'identifiant de l'onglet : deux éléments du même nom, et Dash perd le clic
            # sur l'un d'eux (l'onglet « Synthèse » ne répondait plus).
            id=choix("aller", "synthese"),
            type="button",
            className="bouton bouton--ouvrir ouvrir-le-livre",
            n_clicks=0,
        )
    ]
    if not tiers:
        actions.append(zone_de_depot("Déposer un export", CE_QUE_DEVIENT_UN_DEPOT))
    nombre = len(depot.fichiers)
    return [
        *(
            [portefeuilles.choix_du_portefeuille(inventaire)]
            if portefeuilles.plusieurs(inventaire) and not tiers
            else []
        ),
        html.H2(titre, className="cartouche__titre"),
        html.Ul(lignes, className="liste-parts"),
        *_alertes(base),
        _volet(
            f"Détail de la lecture · {nombre} fichier{'s' if nombre > 1 else ''}, "
            f"{len(base.rapport.operations)} opérations sur vos actifs",
            detail,
            # Une question posée doit se voir : le volet s'ouvre sur elle.
            ouvert=a_supprimer is not None,
        ),
        html.Div(actions, className="cartouche__actions"),
    ]


def _alertes(base: assembleur.Construit) -> list:
    """Ce qui ne se replie jamais : ce que la lecture n'a pas compris, ce qui manque, ce qui a
    été écarté. Visible dès la couverture, au-dessus des actions."""
    depot = base.rapport.depot
    alertes: list = []
    inconnus = sum(base.rapport.types_inconnus.values())
    if inconnus:
        alertes.append(
            [
                mot("Type inconnu"),
                f" {inconnus} ligne{'s' if inconnus > 1 else ''} d'un type d'opération que "
                "Pastory ne connaît pas : elles ne sont pas comptées. Le détail de la lecture "
                "les nomme.",
            ]
        )
    for nom, raison in depot.fichiers_ignores:
        alertes.append([mot("Ignoré", "absent"), f" {nom} : {raison}."])
    return [html.P(alerte, className="cartouche__alerte") for alerte in alertes]


def _les_exports(base: assembleur.Construit) -> html.Ul:
    depot = base.rapport.depot
    lignes: list = []
    for lu in depot.fichiers:
        periode = (
            f"du {f.date_courte(lu.premier_jour)} au {f.date_courte(lu.dernier_jour)}"
            if lu.premier_jour is not None
            else "aucune date lisible"
        )
        lignes.append(ligne_de_liste(lu.nom, f"{lu.lignes} lignes, {periode}", "reference"))
    if depot.doublons:
        lignes.append(
            ligne_de_liste(
                f"{depot.doublons} ligne(s) écrite(s) deux fois dans le fichier, comptée(s) "
                "une seule fois"
            )
        )
    for nom, raison in depot.fichiers_ignores:
        lignes.append(ligne_de_liste([mot("Ignoré", "absent"), f" {nom} : {raison}."]))
    return html.Ul(lignes, className="liste-parts")


def _ce_que_la_lecture_a_trouve(base: assembleur.Construit) -> html.Ul:
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
    return html.Ul(lignes, className="liste-parts")
