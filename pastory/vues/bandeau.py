"""Le bandeau permanent : deux bandes, de la plus sombre à la plus claire (conception §4.1).

1. **la navigation**, en brun reliure : le logo et le nom, les chapitres numérotés en chiffres
   romains — l'actif marqué d'un signet d'or —, et à droite l'annexe, « Détail des calculs »
   (charte graphique §4.3) ;
2. **les filtres**, et seulement ceux qui agissent sur l'onglet affiché. La diversification et
   les frais n'en ont aucun : un filtre qui n'agit sur rien fait douter du chiffre affiché.
   À droite, ce que les filtres ont retenu : la période en clair.

Le colophon — d'où viennent les chiffres, et de quand ils datent — n'est plus une troisième bande :
il accompagne le titre de chaque chapitre (`colophon.py`).
"""

from __future__ import annotations

from dataclasses import dataclass

from dash import html

from pastory.pivot.operation import Poche
from pastory.vues.briques import choix, dessin, groupe
from pastory.vues.chiffres import PERIODES


@dataclass(frozen=True)
class Onglet:
    """Un chapitre du livre (charte graphique §4.2)."""

    cle: str
    nom: str
    numero: str
    """Le numéro du chapitre, en chiffres romains ; « Annexe » pour le détail des calculs."""
    introduction: str
    """La phrase en italique qui ouvre le chapitre et dit ce que montre la page."""
    periode: bool
    type: bool
    poches: bool
    principal: bool = True
    """Faux pour une page qui ne figure pas dans la rangée des onglets."""


ONGLETS = (
    Onglet(
        "synthese", "Synthèse", "I",
        "Ce que valent vos actifs, et le chemin parcouru depuis le premier achat.",
        periode=True, type=False, poches=True,
    ),
    Onglet(
        "actifs", "Les actifs", "II",
        "Chaque ligne du portefeuille : ce qu'elle a coûté, ce qu'elle vaut, ce qu'elle a "
        "rapporté.",
        periode=False, type=True, poches=True,
    ),
    # Aucun filtre ici : une répartition est la photo d'un tout, il n'y a rien à filtrer.
    Onglet(
        "diversification", "Diversification", "III",
        "Où se trouve votre argent, en regardant à l'intérieur des fonds.",
        periode=False, type=False, poches=False,
    ),
    Onglet(
        "frais", "Frais et taxes", "IV",
        "Ce qui a été prélevé, ce que coûte la détention, et ce que coûterait la sortie.",
        periode=False, type=False, poches=False,
    ),
    # Le chapitre de la prédiction de l'évolution (D-97, hypothèses D-105) : une hypothèse sur
    # l'avenir, calculée par `pastory/projection.py`, indépendant du moteur.
    Onglet(
        "projections", "Projections", "V",
        "Ce que pourrait devenir le portefeuille.",
        periode=False, type=False, poches=False,
    ),
    # Pas un chapitre comme les autres : l'annexe, ouverte depuis le bouton discret à droite de
    # la navigation (arbitrage du propriétaire, étape 9). Elle n'est pas aussi importante que le
    # reste, et ne doit pas en avoir l'air.
    Onglet(
        "detail", "Détail des calculs", "Annexe",
        "De quoi refaire chaque chiffre à la main.",
        periode=True, type=False, poches=True, principal=False,
    ),
)

ACCUEIL = "accueil"
"""L'écran de dépôt des exports. Ce n'est pas un sixième onglet : il s'ouvre depuis l'état des
données, et c'est le premier écran tant qu'aucun export n'est lu."""

TYPES = (("tous", "Tous"), ("etf", "ETF"), ("action", "Actions"), ("crypto", "Crypto"))

NOM_DE_POCHE = {Poche.PEA: "PEA", Poche.CTO: "CTO", Poche.CRYPTO: "Crypto"}


def jeton(poche: Poche) -> html.Span:
    """Le nom court d'une poche, précédé de sa pastille de couleur (D-96). Le texte reste à
    l'encre : la couleur dit l'identité, elle ne porte jamais le mot."""
    return html.Span(NOM_DE_POCHE[poche], className=f"jeton jeton--{poche.value.lower()}")


def onglet(cle: str) -> Onglet | None:
    return next((o for o in ONGLETS if o.cle == cle), None)


def marque() -> html.Button:
    """Le logo et le nom, en tête de la navigation : un clic referme le livre sur sa couverture
    (retour du propriétaire, étape 9 bis — le lien « vos exports » du colophon était trop
    discret). L'identifiant n'est pas celui de ce lien : deux éléments du même nom, et Dash perd
    le clic sur l'un d'eux."""
    return html.Button(
        [dessin("logo", None), html.Span("Pastory")],
        id=choix("aller", ACCUEIL),
        type="button",
        className="marque",
        n_clicks=0,
        title="Revenir à la couverture",
        **{"aria-label": "Pastory : revenir à la couverture"},
    )


def bascule_du_theme() -> html.Button:
    """Le bouton jour / nuit (D-100). Il ne passe pas par Dash : `dessin.js` change le thème
    dans le navigateur et retient le choix ; sans choix, Pastory suit le réglage du système."""
    return html.Button(
        dessin("bascule", None),
        type="button",
        className="bascule-theme",
        title="Lecture de jour ou de nuit",
        **{"aria-label": "Lecture de nuit"},
    )


def onglets(actuel: str) -> list:
    """Les chapitres : le numéro romain, puis le nom. L'actif porte le signet (CSS)."""
    return [
        html.Button(
            [html.Span(o.numero, className="onglet__numero"), html.Span(o.nom)],
            id=choix("onglet", o.cle),
            type="button",
            role="tab",
            n_clicks=0,
            **{"aria-selected": "true" if o.cle == actuel else "false"},
        )
        for o in ONGLETS
        if o.principal
    ]


def lien_vers_le_detail(actuel: str) -> list:
    """À droite de la navigation, discret : l'annexe, qui permet de refaire chaque chiffre à la
    main. Elle porte aussi le bloc « À surveiller », qui y remplace l'ancien compteur."""
    return [
        html.Button(
            [html.Span("Annexe", className="onglet__numero"), "Détail des calculs"],
            id=choix("onglet", "detail"),
            className="bouton bouton--discret",
            type="button",
            n_clicks=0,
            **{"aria-pressed": "true" if actuel == "detail" else "false"},
        ),
        bascule_du_theme(),
    ]


def filtres(
    actuel: str,
    periode: str,
    type_actif: str,
    poches_presentes: tuple[Poche, ...],
    poches: tuple[Poche, ...],
    note: object = None,
) -> list:
    """Les filtres qui agissent sur l'onglet `actuel`, chaque groupe dans sa case, et à droite
    la `note` : ce que les filtres ont retenu (la période en clair). Une liste vide retire la
    rangée."""
    o = onglet(actuel)
    if o is None:
        return []
    enfants: list = []
    if o.periode:
        enfants.append(
            _filtre("Période", groupe("periode", [(p.cle, p.nom) for p in PERIODES], periode))
        )
    if o.type:
        enfants.append(_filtre("Type d'actif", groupe("type", TYPES, type_actif)))
    if o.poches:
        boutons = [
            html.Button(
                NOM_DE_POCHE[poche],
                id=choix("poche", poche.value),
                type="button",
                className="poche-eteinte",
                n_clicks=0,
                disabled=poche not in poches_presentes,
                title=""
                if poche in poches_presentes
                else f"Ce portefeuille n'a pas de {NOM_DE_POCHE[poche]}",
                **{"aria-pressed": "true" if poche in poches else "false"},
            )
            for poche in Poche
        ]
        enfants.append(_filtre("Poches", html.Div(boutons, className="groupe")))
    if enfants and note is not None:
        enfants.append(note)
    return enfants


def _filtre(etiquette: str, boutons) -> html.Div:
    """Un groupe de filtres : son étiquette et ses boutons, serrés ; les groupes, eux, respirent."""
    return html.Div([html.Span(etiquette, className="etiquette"), boutons], className="filtre")


SECTIONS_DES_FRAIS = (
    ("frais-preleve", "Ce qui a été prélevé"),
    ("frais-detention", "Pendant la détention"),
    ("frais-sortie", "À la sortie"),
)
"""Les trois niveaux des frais (D-73) : la bande y mène d'un clic."""


def sommaire(actuel: str, rubrique: str) -> list:
    """La bande d'un chapitre qui n'a pas de filtre : son SOMMAIRE (D-104). Elle garde la
    hauteur de celle des filtres, pour que le livre ait le même rythme d'un chapitre à l'autre,
    et elle ne porte JAMAIS un faux filtre — un filtre qui n'agit sur rien fait douter du
    chiffre affiché. On y choisit ce qu'on regarde, rien n'est retiré :

    - en Diversification, la **rubrique** (actifs, zones, pays, secteurs) ;
    - en Frais et taxes, un lien vers chacun des **trois niveaux** ;
    - en Projections, une phrase : c'est une hypothèse, pas une prévision.
    """
    if actuel == "diversification":
        from pastory.vues.diversification import RUBRIQUES

        return [_filtre("Rubrique", groupe("rubrique", RUBRIQUES, rubrique))]
    if actuel == "frais":
        # De simples ancres : le navigateur défile jusqu'à la section, sans rien recalculer.
        liens = html.Div(
            [html.A(nom, href=f"#{cible}") for cible, nom in SECTIONS_DES_FRAIS],
            className="groupe",
        )
        return [_filtre("Aller à", liens)]
    if actuel == "projections":
        return [
            html.Div(
                [
                    html.Span("Hypothèse", className="etiquette"),
                    html.Span(
                        "Une hypothèse sur l'avenir, jamais une prévision ni un conseil.",
                        className="bande__phrase",
                    ),
                ],
                className="filtre",
            )
        ]
    return []
