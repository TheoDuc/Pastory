"""Le chapitre V, « Projections » : la prédiction de l'évolution (D-97, D-105).

Une **hypothèse sur l'avenir, jamais une prévision ni un conseil**, et la page le dit trois fois :
dans la bande, sous le montant, et dans « Ce que ce calcul suppose ». Elle ne lit du portefeuille
qu'une chose, **la valeur des actifs**, proposée comme valeur de départ et modifiable (D-27).

La page tient sur un écran, de haut en bas (retour du propriétaire) :

1. **le montant atteint**, en une bande : le grand chiffre, et les niveaux à côté ;
2. **la courbe** ;
3. **les hypothèses**, sur une ligne : valeur de départ, taux, durée, versement, et le choix
   « une courbe | 10 000 simulations » ; à leur pied, « Ce que ce calcul suppose », replié.

`ecran` pose les champs et les emplacements ; `resultat` les remplit chaque fois qu'une hypothèse
change (rappel dans `application.py`). Le calcul est dans `pastory/projection.py`, indépendant du
moteur.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from dash import dcc, html

from pastory import projection as p
from pastory.vues import format as f
from pastory.vues.briques import bloc, dessin, mot
from pastory.vues.chiffres import Vue
from pastory.vues.synthese import plafond_de_l_axe

TAUX_PAR_DEFAUT = 5
DUREE_PAR_DEFAUT = 20
VERSEMENT_PAR_DEFAUT = 100
"""Des valeurs de départ pour les champs, visibles et modifiables : ce ne sont pas des
hypothèses cachées, ce sont des exemples à remplacer."""

HAUTEUR_DE_LA_COURBE = 200

SIMPLE = "simple"
ALEA = "alea"

MOIS = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
)
MOIS_EN_TOUTES_LETTRES = (
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
    "septembre", "octobre", "novembre", "décembre",
)

LIBELLES = {90: "90 %", 75: "75 %", 50: "Médiane", 25: "25 %", 10: "10 %"}
CLASSES = {90: "extreme", 75: "quartile", 50: "mediane", 25: "quartile", 10: "extreme"}


def _tirages_en_clair() -> str:
    return f"{p.TIRAGES:,}".replace(",", f.MILLIERS)


# --- La page ---------------------------------------------------------------------------------


def ecran(vue: Vue) -> html.Div:
    valorisation = vue.construit.synthese.valorisation
    valeur = valorisation.total.valeur if valorisation.valorisees else None
    jours = [pv.cours.date for pv in valorisation.valorisees if pv.cours is not None]
    au = max(jours) if jours else None
    sans_cours = len(valorisation.non_valorisees)
    return html.Div(
        [
            # La date de la valeur de départ : la courbe part d'elle, et non du jour.
            dcc.Store(id="projection-debut", data=au.isoformat() if au else None),
            html.Div(
                bloc("Le montant atteint", html.Div(id="projection-montant")),
                className="rangee rangee--large",
            ),
            html.Div(
                bloc("L'évolution supposée", html.Div(id="projection-courbe")),
                className="rangee rangee--large rangee--apres",
            ),
            html.Div(
                _hypotheses(valeur, au, sans_cours),
                className="rangee rangee--large rangee--apres",
            ),
        ]
    )


def _champ(etiquette: str, ident: str, valeur, unite: str, aide_texte=None, **bornes) -> html.Div:
    return html.Div(
        [
            html.Label(etiquette, htmlFor=ident, className="champ__etiquette"),
            html.Div(
                [
                    dcc.Input(
                        id=ident,
                        type="number",
                        value=valeur,
                        debounce=True,
                        persistence=True,
                        persistence_type="session",
                        className="champ__saisie",
                        **bornes,
                    ),
                    html.Span(unite, className="champ__unite"),
                ],
                className="champ__ligne",
            ),
            html.Span(aide_texte, className="champ__aide") if aide_texte else None,
        ],
        className="champ",
    )


def _hypotheses(valeur: Decimal | None, au: Date | None, sans_cours: int = 0) -> html.Section:
    # Sans valeur connue, le champ reste VIDE : une valeur par défaut serait une hypothèse cachée
    # (D-80), et la page dit « Indiquez la valeur de départ ».
    depart = float(valeur.quantize(Decimal("0.01"))) if valeur is not None else None
    if valeur is None:
        origine: object = "aucune valeur connue : saisissez un montant"
    elif sans_cours:
        # Une valeur partielle se dit, là où elle est proposée (D-53, règle 6).
        origine = [
            f"vos actifs au {f.date_courte(au)} : {f.montant(valeur)} — ",
            mot("Partiel", "absent"),
            f" {sans_cours} sans cours",
        ]
    else:
        origine = f"vos actifs au {f.date_courte(au)} : {f.montant(valeur)}"
    # Le choix « une courbe | 10 000 simulations » : deux boutons, comme les filtres, plutôt
    # qu'une case à cocher — c'est un choix entre deux lectures, pas une option cachée.
    mode = html.Div(
        [
            html.Span("Lecture", className="champ__etiquette"),
            dcc.RadioItems(
                id="projection-alea",
                options=[
                    {"label": "Une courbe", "value": SIMPLE},
                    {"label": f"{_tirages_en_clair()} simulations", "value": ALEA},
                ],
                value=SIMPLE,
                persistence=True,
                persistence_type="session",
                className="choix-de-lecture",
            ),
            html.Span("un taux aléatoire autour du taux saisi", className="champ__aide"),
        ],
        className="champ",
    )
    # « Ce que ce calcul suppose » : un volet replié au pied des hypothèses — là où on le
    # cherche, et sans boîte de plus, pour que la page tienne sur un écran.
    suppose = html.Details(
        [
            html.Summary(
                "Ce que ce calcul suppose : la loi, la volatilité, ce qui n'est pas compté",
                className="volet__titre",
            ),
            html.Div(_ce_que_ce_calcul_suppose(), className="volet__corps"),
        ],
        className="volet",
    )
    champs = html.Div(
        [
            _champ("Valeur de départ", "projection-depart", depart, "€", origine,
                   min=0, step=0.01),
            _champ("Taux annuel", "projection-taux", TAUX_PAR_DEFAUT, "%",
                   "nominal : avant impôt, frais, inflation",
                   min=0, max=float(p.TAUX_MAXIMAL), step=0.1),
            _champ("Durée", "projection-duree", DUREE_PAR_DEFAUT, "ans",
                   f"de {p.DUREE_MINIMALE} à {p.DUREE_MAXIMALE} ans",
                   min=p.DUREE_MINIMALE, max=p.DUREE_MAXIMALE, step=1),
            _champ("Versement mensuel", "projection-versement", VERSEMENT_PAR_DEFAUT, "€",
                   "à la fin de chaque mois", min=0, step=1),
            mode,
        ],
        className="champs",
    )
    return bloc("Vos hypothèses", html.Div([champs, suppose]))


def _ce_que_ce_calcul_suppose() -> html.Ul:
    k = p.VOLATILITE_PAR_POINT_DE_TAUX
    points = [
        "Chaque mois, le placement grandit au taux annuel ramené au mois : douze mois au taux "
        "mensuel font une année au taux saisi. Le versement tombe à la fin du mois.",
        "Le taux est nominal : en euros de l'époque, avant impôt, frais et inflation.",
        f"Avec les simulations, {_tirages_en_clair()} chemins sont tirés au hasard. Chaque mois, "
        "le rendement suit une loi log-normale, indépendante des autres mois.",
        "Le taux saisi est celui de la médiane : la moitié des chemins font mieux, la moitié "
        "moins bien. La courbe du milieu retombe donc presque sur la courbe sans aléa.",
        "Les niveaux affichés sont les quantiles 10 %, 25 %, 50 % (la médiane), 75 % et 90 % : "
        "8 chemins sur 10 finissent entre le premier et le dernier.",
        f"La volatilité annuelle vaut {k} fois le taux : un taux élevé ne s'obtient qu'en "
        f"acceptant plus de variations. À 4 %, elle vaut {4 * k} % ; à 15 %, {15 * k} %. "
        "Aucune valeur historique n'est employée.",
        "Le hasard est tiré avec une graine fixe : les mêmes entrées redonnent toujours les "
        "mêmes courbes.",
        "Cette loi sous-estime les krachs : une chute brutale comme celle de 2008 y est plus "
        "rare que dans la réalité. Le taux et sa volatilité restent constants sur toute la durée.",
        "C'est une hypothèse, pas une prévision ni un conseil.",
    ]
    return html.Ul([html.Li(texte) for texte in points], className="suppose")


# --- Le résultat ---------------------------------------------------------------------------


def resultat(
    depart: object,
    taux: object,
    duree: object,
    versement: object,
    alea: bool,
    debut: Date | None = None,
) -> tuple:
    """`(montant, courbe)` : ce que le rappel pose dans les deux emplacements de la page."""
    h = p.lire(depart, taux, duree, versement)
    if isinstance(h, str):
        return html.P(h, className="vide"), html.P(
            "Pas de courbe tant qu'une hypothèse manque ou sort des bornes.", className="vide"
        )
    debut = debut or Date.today()
    simple = p.sans_alea(h)
    eventail = p.avec_alea(h) if alea else None
    fin = _mois(debut, h.mois, long=True)
    return _le_montant(h, simple, eventail, fin), _la_courbe(h, simple, eventail, debut)


def _mois(debut: Date, decalage: int, long: bool = False) -> str:
    indice = debut.month - 1 + decalage
    annee, mois = debut.year + indice // 12, indice % 12
    return f"{(MOIS_EN_TOUTES_LETTRES if long else MOIS)[mois]} {annee}"


def _arrondi(valeur) -> Decimal:
    return Decimal(str(valeur)).quantize(Decimal("0.01"))


def _niveau(etiquette: str, montant: str, classe: str = "") -> html.Div:
    """Un niveau de la bande des résultats : son nom au-dessus, son montant dessous."""
    return html.Div(
        [html.Span(etiquette, className="niveau__nom"), html.Span(montant, className="nb")],
        className=f"niveau {classe}".strip(),
    )


def _le_montant(h: p.Hypotheses, simple: list[Decimal], eventail, fin: str) -> html.Div:
    final = _arrondi(simple[-1])
    verse = _arrondi(h.verse)
    if eventail is None:
        tete = [
            html.Span(f.montant(final), className="entree__valeur nb"),
            html.Span(f"en {fin}, sans aléa", className="entree__pied"),
        ]
        niveaux = [
            _niveau("Ce que vous aurez versé", f.montant(verse)),
            _niveau("Ce que le taux aura ajouté", f.montant_signe(final - verse)),
        ]
    else:
        q = {quantile: eventail.a_la_fin(quantile) for quantile in p.QUANTILES}
        tete = [
            html.Span(f.montant(q[50]), className="entree__valeur nb"),
            html.Span(
                f"en {fin}, la médiane des {_tirages_en_clair()} chemins",
                className="entree__pied",
            ),
            html.P(
                [
                    "Dans 8 cas sur 10, entre ",
                    html.B(f.montant(q[10]), className="nb"),
                    " et ",
                    html.B(f.montant(q[90]), className="nb"),
                    " ; dans 1 cas sur 2, entre ",
                    html.B(f.montant(q[25]), className="nb"),
                    " et ",
                    html.B(f.montant(q[75]), className="nb"),
                    ".",
                ],
                className="projection__phrase",
            ),
        ]
        niveaux = [
            *[
                _niveau(LIBELLES[quantile], f.montant(q[quantile]))
                for quantile in reversed(p.QUANTILES)
            ],
            _niveau("Sans aléa", f.montant(final), "niveau--repere"),
            _niveau("Versé", f.montant(verse), "niveau--repere"),
        ]
    return html.Div(
        [html.Div(tete, className="projection__tete"), html.Div(niveaux, className="niveaux")],
        className="projection__resultat",
    )


def _la_courbe(h: p.Hypotheses, simple: list[Decimal], eventail, debut: Date) -> html.Span:
    # Un point par mois jusqu'à 20 ans, un par trimestre au-delà : la forme est la même, et le
    # dessin reste léger (relecture de l'étape 9 bis).
    pas_des_points = 1 if h.mois <= 240 else 3
    mois = list(range(0, h.mois + 1, pas_des_points))
    if mois[-1] != h.mois:
        mois.append(h.mois)
    verse = [float(h.depart + h.versement * m) for m in mois]
    series: list[dict] = [
        {"classe": "verse", "libelle": "Total versé", "valeurs": verse},
    ]
    if eventail is None:
        valeurs = [float(simple[m]) for m in mois]
        series.append({"classe": "simple", "libelle": "Sans aléa", "valeurs": valeurs})
    else:
        for quantile in reversed(p.QUANTILES):
            series.append(
                {
                    "classe": CLASSES[quantile],
                    "libelle": LIBELLES[quantile],
                    "valeurs": [eventail.quantiles[quantile][m] for m in mois],
                }
            )
    maxi = max(max(s["valeurs"]) for s in series)
    plafond = plafond_de_l_axe(maxi)
    annees = h.annees
    pas = max(1, round(annees / 6))
    lecture = [
        {
            "d": _mois(debut, m),
            "lignes": [[s["libelle"], f.montant(_arrondi(s["valeurs"][k]))] for s in series],
        }
        for k, m in enumerate(mois)
    ]
    donnees = {
        "hauteur": HAUTEUR_DE_LA_COURBE,
        "aria": (
            f"Évolution supposée, de {_mois(debut, 0, long=True)} à "
            f"{_mois(debut, h.mois, long=True)}."
        ),
        "plafond": plafond,
        "graduations": [
            {"valeur": plafond / 4 * i, "texte": f.montant_entier(Decimal(str(plafond / 4 * i)))}
            for i in range(5)
        ],
        "axe": [
            {"i": mois.index(min(mois, key=lambda m, a=a: abs(m - a * 12))),
             "texte": str(debut.year + a)}
            for a in range(0, annees + 1, pas)
        ],
        "series": series,
        "lecture": lecture,
    }
    return dessin("projection", donnees)
