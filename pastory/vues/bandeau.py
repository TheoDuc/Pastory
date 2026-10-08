"""Le bandeau permanent : trois rangées, de la plus sombre à la plus claire (conception §4.1).

1. **la manchette** : le logo et le nom, les cinq onglets, le compteur « à surveiller » ;
2. **les filtres**, et seulement ceux qui agissent sur l'onglet affiché. La diversification et
   les frais n'en ont aucun : un filtre qui n'agit sur rien fait douter du chiffre affiché ;
3. **l'état des données** : la période de l'export, la date des cours, leur source. C'est la
   ligne qui permet de dire « ces chiffres sont d'hier », et elle ne disparaît jamais.
"""

from __future__ import annotations

from dataclasses import dataclass

from dash import html

from pastory.pivot.operation import Poche
from pastory.vues import format as f
from pastory.vues.briques import choix, dessin, groupe, mot
from pastory.vues.chiffres import PERIODES


@dataclass(frozen=True)
class Onglet:
    cle: str
    nom: str
    periode: bool
    type: bool
    poches: bool


ONGLETS = (
    Onglet("synthese", "Synthèse", periode=True, type=False, poches=True),
    Onglet("actifs", "Les actifs", periode=False, type=True, poches=True),
    # Aucun filtre ici : une répartition est la photo d'un tout, il n'y a rien à filtrer.
    Onglet("diversification", "Diversification", periode=False, type=False, poches=False),
    Onglet("frais", "Frais et taxes", periode=False, type=False, poches=False),
    Onglet("detail", "Détail des calculs", periode=True, type=False, poches=True),
)

ACCUEIL = "accueil"
"""L'écran de dépôt des exports. Ce n'est pas un sixième onglet : il s'ouvre depuis l'état des
données, et c'est le premier écran tant qu'aucun export n'est lu."""

TYPES = (("tous", "Tous"), ("etf", "ETF"), ("action", "Actions"), ("crypto", "Crypto"))

NOM_DE_POCHE = {Poche.PEA: "PEA", Poche.CTO: "CTO", Poche.CRYPTO: "Crypto"}


def onglet(cle: str) -> Onglet | None:
    return next((o for o in ONGLETS if o.cle == cle), None)


def marque() -> html.Span:
    return html.Span([dessin("logo", None), html.Span("Pastory")], className="marque")


def onglets(actuel: str) -> list:
    return [
        html.Button(
            o.nom,
            id=choix("onglet", o.cle),
            type="button",
            role="tab",
            n_clicks=0,
            **{"aria-selected": "true" if o.cle == actuel else "false"},
        )
        for o in ONGLETS
    ]


def compteur(nombre: int | None) -> list:
    """Le bouton qui mène au bloc « à surveiller ». Rien tant que rien n'est lu."""
    if nombre is None:
        return []
    return [
        html.Button(
            f"À surveiller · {nombre}",
            id=choix("surveiller", "detail"),
            className="bouton bouton--surveiller",
            type="button",
            n_clicks=0,
        )
    ]


def filtres(
    actuel: str,
    periode: str,
    type_actif: str,
    poches_presentes: tuple[Poche, ...],
    poches: tuple[Poche, ...],
) -> list:
    """Les filtres qui agissent sur l'onglet `actuel`. Une liste vide retire la rangée."""
    o = onglet(actuel)
    if o is None:
        return []
    enfants: list = []
    if o.periode:
        enfants += [
            html.Span("Période", className="etiquette"),
            groupe("periode", [(p.cle, p.nom) for p in PERIODES], periode),
        ]
    if o.type:
        enfants += [
            html.Span("Type d'actif", className="etiquette"),
            groupe("type", TYPES, type_actif),
        ]
    if o.poches:
        enfants += [
            html.Span("Poches", className="etiquette"),
            html.Div(
                [
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
                ],
                className="groupe",
            ),
        ]
    return enfants


def etat_des_donnees(
    *,
    export_du: object = None,
    export_au: object = None,
    cours_au: object = None,
    avec_cours: bool = False,
    sources: list[str] | None = None,
    debut: object = None,
    fin: object = None,
    jours: int | None = None,
    positions: int | None = None,
    non_valorisees: list[str] | None = None,
    poches_retenues: tuple[Poche, ...] | None = None,
    arretes: tuple[object, object] | None = None,
) -> list:
    """La rangée claire du bandeau. Chaque morceau absent est simplement omis."""
    morceaux: list = []
    if export_du is not None:
        morceaux.append(
            html.Span(
                [
                    "Export du ",
                    html.B(f.date_courte(export_du)),
                    " au ",
                    html.B(f.date_courte(export_au)),
                    " · ",
                    html.Button(
                        "vos exports",
                        id=choix("onglet", ACCUEIL),
                        type="button",
                        className="lien",
                        n_clicks=0,
                    ),
                ]
            )
        )
    if cours_au is not None:
        morceaux.append(html.Span(["Cours arrêtés au ", html.B(f.date_courte(cours_au))]))
    elif avec_cours:
        # Des positions, mais aucun cours : la ligne le dit, plutôt que de taire la date.
        morceaux.append(html.Span([mot("Sans cours", "absent"), " aucun cours connu"]))
    if sources:
        morceaux.append(html.Span(f"Source : {', '.join(sources)}"))
    if arretes is not None and arretes[0] is not None:
        du, au = arretes
        texte = (
            f"Compositions arrêtées au {f.date_courte(au)}"
            if du == au
            else f"Compositions arrêtées du {f.date_courte(du)} au {f.date_courte(au)}"
        )
        morceaux.append(html.Span(texte))
    if debut is not None:
        morceaux.append(
            html.Span(
                f"Du {f.date_courte(debut)} au {f.date_courte(fin)} · {f.duree_en_clair(jours)}"
            )
        )
    if positions is not None:
        morceaux.append(html.Span(f"{positions} position{'s' if positions > 1 else ''}"))
    if non_valorisees:
        morceaux.append(
            html.Span([mot("Partiel", "absent"), " " + ", ".join(non_valorisees)])
        )
    if poches_retenues is not None:
        morceaux.append(
            html.Span(
                "Poches retenues : " + ", ".join(NOM_DE_POCHE[p] for p in poches_retenues)
            )
        )
    return morceaux
