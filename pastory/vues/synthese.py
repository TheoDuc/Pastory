"""L'onglet « Synthèse » : combien ai-je gagné, et comment ça a évolué ? (conception §4.2)

De haut en bas, comme la maquette (`ongletSynthese`) :

1. **cinq tuiles**, le gain d'abord (D-22) : gain, TRI, TWRR, puis la valeur des actifs et le
   capital net investi, celui-ci portant la plus-value latente ;
2. **la courbe** du capital brut et du capital net investi, et à côté **les poches** ;
3. **les cartes d'actifs**, triées par variation : ce qui a le plus bougé, pas un doublon du
   tableau de l'onglet suivant.

Tous les chiffres viennent du moteur, pour la période et les poches choisies ; cet écran ne fait
que les mettre en forme. Les deux seules divisions qu'il fait — la part d'une poche dans la
valeur totale, et la position d'un point sur l'axe — servent à **placer** un trait ou à écrire
une part dont le dénominateur est affiché à côté.
"""

from __future__ import annotations

import math
from datetime import date as Date
from decimal import Decimal

from dash import html

from pastory.config.actifs import TypeActif
from pastory.moteur.rendements import Rendements
from pastory.moteur.valorisation import PointEvolution, PositionValorisee
from pastory.pivot.operation import Poche
from pastory.vues import format as f
from pastory.vues.bandeau import NOM_DE_POCHE
from pastory.vues.briques import aide, bloc, choix, dessin, mot, pied_avec_mot, tuile
from pastory.vues.chiffres import Chiffres, Vue

COULEUR_DE_POCHE = {Poche.PEA: "#1b4a63", Poche.CTO: "#37738c", Poche.CRYPTO: "#6fa0b4"}
"""Les couleurs des poches, **en clair** : elles vont dans un attribut SVG, où `var()` n'est pas
interprété. Ce sont celles de `--poche-1` à `--poche-3`, et un test le vérifie. Une couleur suit
sa poche, jamais son rang : décocher une poche ne repeint pas les autres."""

NOM_DE_TYPE = {TypeActif.ETF: "ETF", TypeActif.ACTION: "Action", TypeActif.CRYPTO: "Crypto"}

CARTES_PAR_PAGE = 5
HAUTEUR_DE_LA_COURBE = 250
CENT = Decimal("100")


def ecran(vue: Vue, chiffres: Chiffres, page: int = 0) -> html.Div:
    return html.Div(
        [
            html.Div(_tuiles(vue), className="tuiles"),
            html.Div(
                [_bloc_courbe(vue, chiffres), _bloc_poches(vue)],
                className="rangee rangee--apres",
            ),
            html.Div([_cartes(vue, page)], className="rangee rangee--large rangee--apres"),
        ]
    )


# --- Les tuiles ------------------------------------------------------------------------


def _ton(valeur: Decimal | None, classe: str) -> str:
    if valeur is None:
        return "neutre"
    return "perte" if classe == "perte" else "gain"


def _tuiles(vue: Vue) -> list:
    total = vue.synthese.total
    valorisation = vue.synthese.valorisation
    twrr = total.twrr

    pied_gain: object
    if total.gain is None:
        pied_gain = total.motif or "non calculable"
    else:
        pied_gain = f"sur {f.duree_en_clair(total.duree_jours)}"
        if not total.fiable:
            pied_gain = [mot("Histoire incomplète"), *aide("histoireIncomplete"), f" {pied_gain}"]

    if total.tri is None:
        pied_tri: object = total.motif_tri or total.motif or "non calculable"
    elif total.peu_significatif:
        pied_tri = pied_avec_mot("Peu fiable")
    else:
        pied_tri = "annualisé"

    if twrr.taux is None:
        pied_twrr: object = twrr.motif or total.motif or "non calculable"
    elif twrr.annualise is None:
        pied_twrr = "sur la période"
    else:
        pied_twrr = f"annualisé {f.taux(twrr.annualise)}"

    rien_de_valorise = bool(valorisation.positions) and not valorisation.valorisees
    valeur = None if rien_de_valorise else valorisation.total.valeur
    sans_cours = valorisation.non_valorisees
    if rien_de_valorise:
        pied_valeur: object = "aucune position n'a de cours : la valeur ne peut pas être calculée"
    elif sans_cours:
        pied_valeur = [mot("Partiel", "absent"), f" {len(sans_cours)} sans cours", *aide("partiel")]
    else:
        pied_valeur = f"au {f.date_courte(_dernier_cours(valorisation.valorisees))}"

    latente = None if rien_de_valorise else _latente(valorisation.valorisees)
    pied_capital: object = (
        "valeur inconnue : pas de plus-value calculable"
        if latente is None
        else [
            "plus-value latente ",
            html.B(f.montant_signe(latente), className=f.classe_du_signe(latente)),
        ]
    )

    return [
        tuile(
            "Gain",
            f.montant_signe(total.gain),
            ton=_ton(total.gain, f.classe_du_signe(total.gain)),
            classe=f.classe_du_signe(total.gain),
            cle_aide="gain",
            pied=pied_gain,
        ),
        tuile(
            "TRI",
            f.taux(total.tri),
            ton=_ton(total.tri, f.classe_du_taux(total.tri)),
            classe=f.classe_du_taux(total.tri),
            cle_aide="peuSignificatif" if total.peu_significatif else "tri",
            pied=pied_tri,
        ),
        tuile(
            "TWRR",
            f.taux(twrr.taux),
            ton=_ton(twrr.taux, f.classe_du_taux(twrr.taux)),
            classe=f.classe_du_taux(twrr.taux),
            cle_aide="peuSignificatif" if total.peu_significatif else "twrr",
            pied=pied_twrr,
        ),
        tuile("Valeur des actifs", f.montant(valeur), petit=True, cle_aide="valeur",
              pied=pied_valeur),
        tuile(
            "Capital net investi",
            f.montant(vue.portefeuille.total.capital_net_investi),
            petit=True,
            cle_aide="capital",
            pied=pied_capital,
        ),
    ]


def _latente(valorisees: list[PositionValorisee]) -> Decimal:
    return sum((p.plus_value_latente or Decimal(0) for p in valorisees), Decimal(0))


def _dernier_cours(valorisees: list[PositionValorisee]) -> Date | None:
    jours = [p.cours.date for p in valorisees if p.cours is not None]
    return max(jours) if jours else None


# --- La courbe -------------------------------------------------------------------------


def _bloc_courbe(vue: Vue, chiffres: Chiffres) -> html.Section:
    points = _points_de_la_periode(chiffres.evolution(vue), vue)
    # La même période que la ligne d'état : la courbe part d'un jour plus tôt, la veille, pour
    # montrer d'où l'on part — ce point n'est pas un jour de la période.
    origine = vue.synthese.total.origine
    note = (
        f"{f.date_courte(origine)} → {f.date_courte(vue.synthese.periode.fin)}"
        if points and origine is not None
        else None
    )
    return bloc(
        "Évolution du capital",
        html.Div([_courbe(points), _legende(), _partiels(points)]),
        note=note,
    )


def _points_de_la_periode(points: list[PointEvolution], vue: Vue) -> list[PointEvolution]:
    """Les jours de la période. Depuis le début : à partir de la veille du premier jour où il y
    a quelque chose, pour que la courbe parte de zéro. Sinon : de la veille du début, dont la
    clôture est la valeur de départ (glossaire, D-54)."""
    if not points:
        return []
    veille = vue.synthese.periode.veille
    if veille is None:
        premier = next(
            (i for i, p in enumerate(points) if p.valeur > 0 or p.capital_net_investi > 0), 0
        )
        retenus = points[max(0, premier - 1) :]
    else:
        retenus = [p for p in points if p.date >= veille]
    return retenus if len(retenus) >= 2 else points[-2:]


def _courbe(points: list[PointEvolution]) -> html.Div:
    if len(points) < 2 or not any(p.valeur > 0 for p in points):
        # Rien n'est tracé plutôt qu'une ligne à zéro : un zéro affiché et une donnée absente
        # ne se ressemblent pas (conception §5.1).
        return html.Div(
            html.P(
                "Pas de courbe : aucun cours connu sur la période. Rien n'est tracé, plutôt "
                "qu'une ligne à zéro.",
                className="vide",
            ),
            className="cadre-graphique",
        )
    maxi = max(max(p.valeur, p.capital_net_investi) for p in points)
    plafond = _plafond(float(maxi))
    donnees = {
        "hauteur": HAUTEUR_DE_LA_COURBE,
        "aria": (
            "Évolution du capital brut et du capital net investi, du "
            f"{f.date_courte(points[0].date)} au {f.date_courte(points[-1].date)}."
        ),
        "plafond": plafond,
        "graduations": [
            {"valeur": plafond / 4 * i, "texte": f.montant_entier(Decimal(str(plafond / 4 * i)))}
            for i in range(5)
        ],
        "points": [_point(p) for p in points],
    }
    return html.Div(dessin("courbe", donnees), className="cadre-graphique")


def _plafond(maxi: float) -> float:
    """Le haut de l'axe : un nombre rond au-dessus du plus haut point, comme dans la maquette."""
    pas = 10 ** math.floor(math.log10(maxi or 1)) / 2
    return max(pas, math.ceil(maxi * 1.06 / pas) * pas)


def _point(p: PointEvolution) -> dict:
    ecart = p.valeur - p.capital_net_investi
    point = {
        "d": f.date_courte(p.date),
        "v": float(p.valeur),
        "i": float(p.capital_net_investi),
        "tv": f.montant(p.valeur),
        "ti": f.montant(p.capital_net_investi),
        "te": f.montant_signe(ecart),
        "ce": f.classe_du_signe(ecart),
    }
    if p.non_valorisees:
        point["tp"] = f"partiel : {p.non_valorisees} actif(s) sans cours ce jour-là"
    return point


def _legende() -> html.Ul:
    return html.Ul(
        [
            html.Li(
                [html.I(style={"borderTopColor": "var(--courbe-brut)"}),
                 "Capital brut — ce que valent les actifs"]
            ),
            html.Li(
                [
                    html.I(
                        style={
                            "borderTopColor": "var(--courbe-investi)",
                            "borderTopStyle": "dashed",
                        }
                    ),
                    "Capital net investi — ce qui a été placé, net de frais",
                ]
            ),
        ],
        className="legende",
    )


def _partiels(points: list[PointEvolution]) -> html.P | None:
    """Les jours où la valeur est partielle se disent sous la courbe (conception §1.2)."""
    jours = [p for p in points if p.non_valorisees]
    if not jours or len(points) < 2:
        return None
    return html.P(
        [
            mot("Partiel", "absent"),
            f" Sur {len(jours)} jour{'s' if len(jours) > 1 else ''} de la période, un actif au "
            "moins n'a pas de cours : la courbe y montre la valeur des seuls actifs cotés. La "
            "boîte de lecture le signale jour par jour.",
        ],
        className="reference courbe__partiels",
    )


# --- Les poches ------------------------------------------------------------------------


def _bloc_poches(vue: Vue) -> html.Section:
    par_poche = vue.synthese.valorisation.par_poche()
    parts = [
        (poche, totaux.valeur)
        for poche, totaux in par_poche.items()
        if poche in vue.poches and totaux.valeur > 0
    ]
    titre = "Où est l'argent que j'investis"
    if not parts:
        return bloc(titre, html.P("Aucune poche valorisée : il n'y a rien à répartir.",
                                  className="vide"))
    total = sum((montant for _, montant in parts), Decimal(0))
    # De la plus grosse à la plus petite : l'anneau part de midi avec la part principale, et la
    # liste se lit dans le même ordre.
    parts.sort(key=lambda part: part[1], reverse=True)
    liste = html.Ul(
        [
            html.Li(
                [
                    html.Span(className="puce", style={"background": COULEUR_DE_POCHE[poche]}),
                    html.Span(NOM_DE_POCHE[poche], className="liste-parts__nom"),
                    html.Span(f.montant(montant), className="nb"),
                    html.Span(f.pour_cent(montant / total * CENT), className="part nb"),
                ]
            )
            for poche, montant in parts
        ],
        className="liste-parts",
    )
    if len(parts) == 1:
        # Un anneau à une seule part ne dit rien (conception §5.1) : la liste suffit.
        return bloc(titre, liste)
    anneau = dessin(
        "anneau",
        {
            "taille": 156,
            "centre": f.montant_entier(total),
            "sous": "au total",
            "parts": [
                {"montant": float(montant), "couleur": COULEUR_DE_POCHE[poche]}
                for poche, montant in parts
            ],
        },
    )
    return bloc(
        titre,
        html.Div([anneau, liste], className="anneau-bloc anneau-bloc--colonne"),
        note=f"base {f.montant(total)}",
    )


# --- Les cartes d'actifs ---------------------------------------------------------------


def _cartes(vue: Vue, page: int) -> html.Section:
    lignes = [(p, vue.synthese.de(p.position)) for p in vue.synthese.valorisation.positions]
    lignes.sort(key=lambda ligne: _cle_de_tri(ligne[1]))

    pages = max(1, math.ceil(len(lignes) / CARTES_PAR_PAGE))
    page = max(0, min(page, pages - 1))
    visibles = lignes[page * CARTES_PAR_PAGE : (page + 1) * CARTES_PAR_PAGE]
    origine_totale = vue.synthese.total.origine

    cartes = [_carte(p, r, origine_totale, vue) for p, r in visibles]
    precedent = html.Button(
        "‹",
        id=choix("page", "precedent"),
        className="fleche",
        type="button",
        n_clicks=0,
        disabled=page == 0,
        **{"aria-label": "Cinq actifs précédents"},
    )
    suivant = html.Button(
        "›",
        id=choix("page", "suivant"),
        className="fleche",
        type="button",
        n_clicks=0,
        disabled=page >= pages - 1,
        **{"aria-label": "Cinq actifs suivants"},
    )
    return html.Section(
        [
            html.Div(
                [
                    html.H2("Vos actifs, du plus au moins performant", className="bloc__titre"),
                    *aide("variation"),
                    html.Span(
                        [
                            f"{len(lignes)} actif{'s' if len(lignes) > 1 else ''} · "
                            f"{page + 1} / {pages} ",
                            precedent,
                            suivant,
                        ],
                        className="bloc__note",
                    ),
                ],
                className="bloc__entete",
            ),
            html.Div(cartes, className="cartes")
            if cartes
            else html.P("Aucun actif détenu dans les poches choisies.", className="vide"),
        ],
        className="bloc",
    )


def _cle_de_tri(rendements: Rendements | None) -> tuple:
    """Du plus au moins performant ; ce qui n'a pas de variation va **toujours** en bas — une
    ligne sans cours n'est pas la moins performante, elle est inconnue."""
    taux = rendements.twrr.taux if rendements is not None else None
    return (taux is None, -(taux or Decimal(0)))


def _carte(
    p: PositionValorisee, rendements: Rendements | None, origine_totale: Date | None, vue: Vue
) -> html.Article:
    taux = rendements.twrr.taux if rendements is not None else None
    if not p.valorisee:
        precision = "sans cours"
    elif taux is None:
        precision = (rendements.twrr.motif if rendements else None) or "variation non calculable"
    elif (
        rendements is not None
        and rendements.origine is not None
        and origine_totale is not None
        and rendements.origine > origine_totale
    ):
        precision = f"depuis l'achat du {f.date_courte(rendements.origine)}"
    else:
        precision = "sur la période"
    classe = f.classe_du_taux(taux)
    ton = "neutre" if taux is None else ("perte" if classe == "perte" else "gain")
    nom = p.position.nom_actif or p.actif
    return html.Article(
        [
            html.Div(
                [
                    html.Span(NOM_DE_POCHE[p.poche], className="jeton"),
                    html.Span(_type(vue, p.actif), className="carte__type"),
                ],
                className="carte__haut",
            ),
            html.Span(nom, className="carte__nom", title=nom),
            html.Span(f.taux(taux), className=f"carte__taux nb {classe}".strip()),
            html.Span(precision, className="carte__precision"),
            html.Dl(
                [
                    html.Dt("Quantité"),
                    html.Dd(f.quantite(p.quantite), className="nb"),
                    html.Dt("Valeur"),
                    html.Dd(f.montant(p.valeur), className="nb"),
                ],
                className="carte__chiffres",
            ),
        ],
        # Pas de `carte--neutre` : la maquette la posait sans qu'aucune règle ne la définisse.
        className="carte" if ton == "neutre" else f"carte carte--{ton}",
    )


def _type(vue: Vue, actif: str) -> str:
    reglages = vue.construit.reglages
    if reglages is None or actif not in reglages.actifs:
        return ""
    type_actif = reglages.actifs[actif].type.valeur
    return NOM_DE_TYPE.get(type_actif, "") if type_actif is not None else "type inconnu"
