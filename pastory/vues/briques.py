"""Les briques des écrans, reprises une à une des fonctions de la maquette (`maquette.js`).

Chaque brique produit **le même balisage, avec les mêmes classes**, que la maquette : c'est ce qui
permet de reprendre sa feuille de style telle quelle (D-31). Un test compare les classes posées
ici à celles que définit `assets/pastory.css`.

Deux sortes d'éléments interactifs, et deux mécanismes :

- **un choix** (un onglet, une période, une poche, un tri) est un bouton dont l'identifiant dit
  quoi changer : `{"choix": "periode", "valeur": "1a"}`. Un seul rappel Dash les écoute tous, et
  recalcule l'écran en Python ;
- **un dessin** (la courbe, un anneau, un drapeau…) est un élément vide qui porte ses données
  dans un attribut `data-…` ; `assets/dessin.js` le trace. Les libellés y arrivent **déjà
  écrits** : le script ne met aucun chiffre en forme (D-93).
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from typing import Any

from dash import html

from pastory.vues.vocabulaire import AIDES, riche

_numeros = itertools.count(1)


def _identifiant(prefixe: str) -> str:
    """Un identifiant unique dans la page : Dash refuse deux éléments du même nom."""
    return f"{prefixe}-{next(_numeros)}"


def choix(champ: str, valeur: str) -> dict[str, str]:
    """L'identifiant d'un bouton qui change l'état de l'écran (voir `application.py`)."""
    return {"choix": champ, "valeur": valeur}


def aide(cle: str | None) -> list:
    """Le bouton « ? » et sa bulle, côte à côte. Vide si la clé n'existe pas.

    La bulle est cachée ; `dessin.js` l'ouvre au clic, la pose en position fixe et la ramène dans
    l'écran — la correction d'un défaut vu à l'étape 8, où la moitié du texte sortait de la page.
    """
    if cle is None or cle not in AIDES:
        return []
    ident, contenu = _bulle(cle)
    return [
        html.Button(
            "?",
            className="aide",
            type="button",
            **{
                "aria-expanded": "false",
                "aria-controls": ident,
                "aria-label": f"Qu'est-ce que « {AIDES[cle].titre} » ?",
            },
        ),
        contenu,
    ]


def bulle_a_contenu(libelle: str, titre: str, contenu: Any) -> list:
    """Un bouton en toutes lettres qui ouvre une bulle au contenu calculé (et non tiré du
    vocabulaire) : le même mécanisme que le « ? », pour un détail qu'on ne montre qu'à la
    demande."""
    ident = _identifiant("bulle")
    return [
        html.Button(
            libelle,
            className="aide aide--texte",
            type="button",
            **{"aria-expanded": "false", "aria-controls": ident},
        ),
        html.Div(
            [html.B(titre, className="bulle__titre"), contenu],
            id=ident,
            className="bulle",
            role="note",
            hidden=True,
        ),
    ]


def _bulle(cle: str) -> tuple[str, html.Div]:
    """La bulle d'une aide, cachée, et son identifiant."""
    texte = AIDES[cle]
    ident = _identifiant("bulle")
    return ident, html.Div(
        [html.B(texte.titre, className="bulle__titre"), html.Span(riche(texte.texte))],
        id=ident,
        className="bulle",
        role="note",
        hidden=True,
    )


def entete(titre: str, cle_aide: str | None = None, note: Any = None) -> html.Div:
    """Un titre de bloc, suivi **immédiatement** de son « ? » : le bouton reste collé au mot
    qu'il explique."""
    return html.Div(
        [
            html.H2(titre, className="bloc__titre"),
            *aide(cle_aide),
            html.Span(note, className="bloc__note") if note else None,
        ],
        className="bloc__entete",
    )


def bloc(
    titre: str | None,
    contenu: Any,
    note: Any = None,
    classes: str = "",
    cle_aide: str | None = None,
    **attributs: Any,
) -> html.Section:
    return html.Section(
        [entete(titre, cle_aide, note) if titre else None, contenu],
        className=f"bloc {classes}".strip(),
        **attributs,
    )


def bloc_replie(titre: str, contenu: Any, note: Any = None) -> html.Section:
    """Un bloc fermé par défaut, qui s'ouvre d'un clic sur son titre : pour ce qui éclaire les
    chiffres sans être un chiffre — les sources, les règles, les réserves. Il reste dans la
    page, à sa place : rien n'est relégué ailleurs (conception §2)."""
    return html.Section(
        html.Details(
            [
                html.Summary(
                    [
                        html.H2(titre, className="bloc__titre"),
                        html.Span(note, className="bloc__note") if note else None,
                    ],
                    className="bloc__entete repli__titre",
                ),
                contenu,
            ],
            className="repli",
        ),
        className="bloc",
    )


def mot(texte: str, variante: str | None = None, **attributs: Any) -> html.Span:
    """La marque courte posée à côté d'un chiffre : « Estimé », « Partiel », « Minorée »…"""
    classes = "mot" + (f" mot--{variante}" if variante else "")
    return html.Span(texte, className=classes, **attributs)


def mot_explique(texte: str, cle_aide: str, variante: str | None = None) -> list:
    """Une marque qui dit elle-même pourquoi elle est là : au survol (ou au clic, ou au clavier),
    elle ouvre la bulle de son explication. Une marque comme « Peu fiable », sans explication à
    portée de souris, inquiète sans rien apprendre (retour du propriétaire, étape 9 bis)."""
    if cle_aide not in AIDES:
        return [mot(texte, variante)]
    ident, contenu = _bulle(cle_aide)
    classes = "mot mot--explique" + (f" mot--{variante}" if variante else "")
    return [
        html.Span(
            texte,
            className=classes,
            tabIndex=0,
            role="button",
            **{
                "aria-expanded": "false",
                "aria-controls": ident,
                "aria-label": f"{texte} : {AIDES[cle_aide].titre.lower()}",
            },
        ),
        contenu,
    ]


def pied_avec_mot(
    marque: str,
    texte: str | None = None,
    variante: str | None = None,
    cle_aide: str | None = None,
) -> list:
    marque_posee = mot_explique(marque, cle_aide, variante) if cle_aide else [mot(marque, variante)]
    return [*marque_posee, f" {texte}" if texte else None]


def tuile(
    etiquette: str,
    valeur: str,
    *,
    ton: str = "neutre",
    classe: str = "",
    petit: bool = False,
    cle_aide: str | None = None,
    pied: Any = None,
) -> html.Div:
    """Une tuile de chiffre clé, sans cadre (charte graphique §5). La `classe` colore le
    chiffre, dont le signe double toujours la couleur ; le `ton` le dit, sans rien peindre."""
    classes_valeur = "tuile__valeur" + (" tuile__valeur--petit" if petit else "")
    if classe:
        classes_valeur += f" {classe}"
    return html.Div(
        [
            html.Div(
                [html.Span(etiquette, className="etiquette"), *aide(cle_aide)],
                className="tuile__haut",
            ),
            html.Span(valeur, className=classes_valeur),
            html.Span(pied, className="tuile__pied"),
        ],
        className=f"tuile tuile--{ton}",
    )


def entree(
    etiquette: str, valeur: str, *, cle_aide: str | None = None, pied: Any = None
) -> html.Div:
    """LE point d'entrée d'une page : un chiffre nettement plus grand que tout le reste, en
    serif (charte graphique §3.2). Une page n'en a qu'un."""
    return html.Div(
        [
            html.Div(
                [html.Span(etiquette, className="etiquette"), *aide(cle_aide)],
                className="entree__haut",
            ),
            html.Span(valeur, className="entree__valeur nb"),
            html.Span(pied, className="entree__pied"),
        ],
        className="entree",
    )


def fleuron() -> html.Span:
    """Un filet et un losange, dessinés en CSS : l'ornement de la couverture."""
    return html.Span(className="fleuron", **{"aria-hidden": "true"})


def ouverture(numero: str, titre: str, introduction: str, note: Any = None) -> html.Header:
    """L'ouverture d'un chapitre : son numéro en grand (un ornement d'or, caché aux lecteurs
    d'écran puisque le titre le redit), son titre, et la phrase qui dit ce que montre la page
    (charte graphique §4.2)."""
    return html.Header(
        [
            html.Span(numero, className="ouverture__numero", **{"aria-hidden": "true"}),
            html.H1(titre, className="ouverture__titre"),
            html.P(introduction, className="ouverture__introduction"),
            # À droite : d'où viennent les chiffres, et de quand ils datent (le colophon).
            note,
            # Puis le fleuron qui sépare le titre du chapitre de sa page, sur toute la largeur
            # (retour du propriétaire, étape 9 bis).
            html.Span(className="fleuron fleuron--chapitre", **{"aria-hidden": "true"}),
        ],
        className="ouverture",
    )


def ligne_de_liste(nom: Any, valeur: Any = None, classe_valeur: str = "nb", **attributs) -> html.Li:
    """Une ligne de `liste-parts` : un libellé à gauche, un chiffre aligné à droite."""
    return html.Li(
        [
            html.Span(nom, className="liste-parts__nom"),
            html.Span(valeur, className=classe_valeur) if valeur is not None else None,
        ],
        **attributs,
    )


def groupe(champ: str, valeurs: Sequence[tuple[str, str]], actuelle: str) -> html.Div:
    """Des boutons dont un seul est enfoncé : la période, le type d'actif, une rubrique."""
    return html.Div(
        [
            html.Button(
                nom,
                id=choix(champ, cle),
                type="button",
                n_clicks=0,
                **{"aria-pressed": "true" if cle == actuelle else "false"},
            )
            for cle, nom in valeurs
        ],
        className="groupe",
    )


def dessin(nature: str, donnees: Any, classe: str = "", **attributs: Any) -> html.Span:
    """Un emplacement que `dessin.js` remplit : `nature` dit quoi tracer, `donnees` avec quoi.

    Les données sont écrites en JSON dans l'attribut `data-donnees`. Quand un filtre les change,
    Dash met l'attribut à jour, et le script redessine.
    """
    return html.Span(
        className=f"dessin {classe}".strip(),
        **{"data-dessin": nature, "data-donnees": json.dumps(donnees, ensure_ascii=False)},
        **attributs,
    )
