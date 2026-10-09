"""L'onglet « Les actifs » : sur quoi, actif par actif ? (conception §4.3)

**Un seul tableau, pleine largeur**, une ligne par actif détenu, filtrable par type et par poche,
triable par colonne — les colonnes de la maquette (`tableauActifs`).

C'est le seul écran où une ligne peut être **partielle sans que l'écran entier le soit** : un
actif sans cours n'empêche pas les autres d'être justes. La dernière colonne, la remarque, dit
alors sur la ligne même ce qui manque et pourquoi. Pas de bouton « ? » dans une cellule : le
tableau défile et la bulle s'y ferait couper ; la marque porte son explication en clair, juste
dessous.

Le pied du tableau est **la somme des colonnes affichées** — et seulement elle. Il porte le
nombre de lignes, et ce qui n'a pas de cours n'y compte pas pour zéro : quand aucune ligne n'est
valorisée, la valeur totale n'est pas nulle, elle est inconnue.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from dash import html

from pastory.config.actifs import ContenuActif, TypeActif
from pastory.moteur.valorisation import PositionValorisee
from pastory.reglages import Trouvee
from pastory.vues import format as f
from pastory.vues.bandeau import NOM_DE_POCHE, jeton
from pastory.vues.briques import bloc, choix, mot
from pastory.vues.chiffres import Vue
from pastory.vues.synthese import NOM_DE_TYPE

LIBELLE_DU_CONTENU = {
    ContenuActif.OBLIGATIONS: "obligations",
    ContenuActif.MATIERES_PREMIERES: "matières premières",
}


@dataclass(frozen=True)
class Colonne:
    cle: str
    nom: str
    nombre: bool
    valeur: Callable[[PositionValorisee], object] | None
    """Ce sur quoi la colonne se trie. `None` : la colonne ne se trie pas."""


def _nom(p: PositionValorisee) -> str:
    return p.position.nom_actif or p.actif


COLONNES = (
    Colonne("nom", "Actif", False, lambda p: _nom(p).casefold()),
    Colonne("poche", "Poche", False, lambda p: NOM_DE_POCHE[p.poche]),
    Colonne("quantite", "Quantité", True, lambda p: p.quantite),
    Colonne("prix", "Prix de revient", True, lambda p: p.position.etat.prix_de_revient),
    Colonne("capital", "Capital net investi", True, lambda p: p.position.etat.capital_net_investi),
    Colonne("cours", "Cours", True, lambda p: p.cours.valeur if p.cours is not None else None),
    Colonne("valeur", "Valeur", True, lambda p: p.valeur),
    Colonne("latente", "+/− latente", True, lambda p: p.plus_value_latente),
    Colonne("remarque", "", False, None),
)


def ecran(vue: Vue, type_actif: str = "tous", tri: str = "valeur", sens: int = -1) -> html.Div:
    lignes = [
        p for p in vue.synthese.valorisation.positions
        if type_actif == "tous" or _type(vue, p.actif) == type_actif
    ]
    lignes = trier(lignes, tri, sens)
    if not lignes:
        # Le filtre est en cause, pas les données (conception §5.1).
        contenu: object = html.P(
            "Aucun actif détenu ne correspond à ce filtre : c'est le filtre qui est en cause, "
            "pas vos données. Choisissez « Tous » ou cochez d'autres poches.",
            className="vide",
        )
    else:
        contenu = html.Div(
            html.Table(
                [
                    html.Thead(html.Tr(_entetes(tri, sens))),
                    html.Tbody([_ligne(p, vue) for p in lignes]),
                    html.Tfoot(_pied(lignes)),
                ]
            ),
            className="cadre-tableau",
        )
    return html.Div(bloc(None, contenu, classes="bloc--plein"))


def trier(lignes: list[PositionValorisee], tri: str, sens: int) -> list[PositionValorisee]:
    """Trie sur la colonne demandée. Ce qui n'a pas de valeur va **toujours** en bas, dans les
    deux sens : une ligne sans cours n'est pas la plus petite, elle est inconnue."""
    colonne = next((c for c in COLONNES if c.cle == tri and c.valeur is not None), COLONNES[6])
    connues = [p for p in lignes if colonne.valeur(p) is not None]
    inconnues = [p for p in lignes if colonne.valeur(p) is None]
    connues.sort(key=colonne.valeur, reverse=sens < 0)
    return connues + inconnues


def _entetes(tri: str, sens: int) -> list:
    entetes = []
    for colonne in COLONNES:
        if colonne.valeur is None:
            entetes.append(html.Th(colonne.nom))
            continue
        actif = colonne.cle == tri
        entetes.append(
            html.Th(
                [
                    colonne.nom,
                    html.Span("▲" if sens > 0 else "▼", className="fleche-tri") if actif else None,
                ],
                id=choix("tri", colonne.cle),
                n_clicks=0,
                className="triable num" if colonne.nombre else "triable",
                role="button",
                tabIndex="0",
                **{
                    "aria-sort": ("ascending" if sens > 0 else "descending")
                    if actif
                    else "none"
                },
            )
        )
    return entetes


def _ligne(p: PositionValorisee, vue: Vue) -> html.Tr:
    sans_cours = not p.valorisee
    latente = p.plus_value_latente
    nom = _nom(p)
    type_affiche = NOM_DE_TYPE.get(_type_actif(vue, p.actif), "type inconnu")
    return html.Tr(
        [
            html.Td(
                [
                    html.Span(nom, className="actif__nom", title=nom),
                    html.Span(f"{p.actif} · {type_affiche}", className="actif__code"),
                ]
            ),
            html.Td(jeton(p.poche)),
            html.Td(f.quantite(p.quantite), className="num"),
            html.Td(_prix_de_revient(p), className="num"),
            html.Td(f.montant(p.position.etat.capital_net_investi), className="num"),
            html.Td(
                f.montant(p.cours.valeur, p.cours.devise) if p.cours is not None else f.ABSENT,
                className="num",
                title=_origine_du_cours(p),
            ),
            html.Td(f.montant(p.valeur), className="num"),
            html.Td(
                f.ABSENT if sans_cours else f.montant_signe(latente),
                className=f"num {'' if sans_cours else f.classe_du_signe(latente)}".strip(),
            ),
            html.Td(_remarques(p, vue)),
        ],
        className="sans-valeur" if sans_cours else None,
    )


def _prix_de_revient(p: PositionValorisee) -> str:
    """Le prix de revient, ou pourquoi il manque : une histoire trouée le rendrait faux sans
    le dire (D-45), et il n'est donc pas calculé."""
    prix = p.position.etat.prix_de_revient
    if prix is not None:
        return f.montant(prix)
    return "à compléter" if p.position.etat.historique_incomplet else f.ABSENT


def _origine_du_cours(p: PositionValorisee) -> str | None:
    """Au survol : la date, la place et la source du cours retenu (conception §1.3)."""
    if p.cours is None:
        return None
    return (
        f"Cours de clôture du {f.date_courte(p.cours.date)}, {p.cours.place}, "
        f"{p.cours.source}. Cours brut, jamais retraité des dividendes."
    )


def _remarques(p: PositionValorisee, vue: Vue) -> list:
    """Ce qu'il faut savoir de la ligne, une marque et sa phrase par point."""
    points: list[tuple[str, str, str | None]] = []
    if not p.valorisee:
        points.append(("Sans cours", p.motif or "aucun cours utilisable à cette date", "absent"))
    if p.position.etat.historique_incomplet:
        points.append(
            (
                "Histoire incomplète",
                "il manque des opérations avant celles lues : la quantité est juste, le prix "
                "de revient ne l'est pas forcément",
                None,
            )
        )
    diversification = vue.construit.diversification
    if diversification is not None and p.actif in diversification.pays.actifs_synthetiques:
        points.append(
            ("Synthétique", "la répartition affichée est celle de l'indice suivi", None)
        )
    contenu = _contenu(vue, p.actif)
    if contenu is not None:
        valeur, corrige = contenu
        points.append(
            (
                "Contenu déclaré" if corrige else "Hors actions",
                f"{LIBELLE_DU_CONTENU[valeur]} : ni pays ni secteur",
                None,
            )
        )
    remarque: list = []
    for marque, phrase, variante in points:
        remarque += [
            mot(marque, variante),
            html.Span(phrase, className="actif__code", style={"display": "block"}),
        ]
    return remarque


def _pied(lignes: list[PositionValorisee]) -> html.Tr:
    capital = sum((p.position.etat.capital_net_investi for p in lignes), Decimal(0))
    valorisees = [p for p in lignes if p.valorisee]
    sans_cours = len(lignes) - len(valorisees)
    rien = not valorisees
    valeur = sum((p.valeur for p in valorisees), Decimal(0))
    latente = sum((p.plus_value_latente or Decimal(0) for p in valorisees), Decimal(0))
    return html.Tr(
        [
            html.Td(
                f"Total — {len(lignes)} ligne{'s' if len(lignes) > 1 else ''}", colSpan=4
            ),
            html.Td(f.montant(capital), className="num"),
            html.Td(),
            html.Td(f.ABSENT if rien else f.montant(valeur), className="num"),
            html.Td(
                f.ABSENT if rien else f.montant_signe(latente),
                className=f"num {'' if rien else f.classe_du_signe(latente)}".strip(),
            ),
            html.Td(
                "aucune ligne valorisée" if rien else (f"{sans_cours} sans cours" if sans_cours
                                                        else ""),
                className="actif__code",
            ),
        ]
    )


def _type_actif(vue: Vue, actif: str) -> TypeActif | None:
    reglages = vue.construit.reglages
    if reglages is None or actif not in reglages.actifs:
        return None
    return reglages.actifs[actif].type.valeur


def _type(vue: Vue, actif: str) -> str | None:
    type_actif = _type_actif(vue, actif)
    return type_actif.value if type_actif is not None else None


def _contenu(vue: Vue, actif: str) -> tuple[ContenuActif, bool] | None:
    """Le contenu qui sort l'actif des pays et des secteurs, et s'il a été corrigé à la main."""
    reglages = vue.construit.reglages
    if reglages is None or actif not in reglages.actifs:
        return None
    reglage = reglages.actifs[actif].contenu
    if reglage is None or not isinstance(reglage.retenu, Trouvee):
        return None
    if reglage.retenu.valeur not in LIBELLE_DU_CONTENU:
        return None
    return reglage.retenu.valeur, reglage.retenu.origine.corrigee
