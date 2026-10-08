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
    texte = AIDES[cle]
    ident = _identifiant("bulle")
    return [
        html.Button(
            "?",
            className="aide",
            type="button",
            **{
                "aria-expanded": "false",
                "aria-controls": ident,
                "aria-label": f"Qu'est-ce que « {texte.titre} » ?",
            },
        ),
        html.Div(
            [html.B(texte.titre, className="bulle__titre"), html.Span(riche(texte.texte))],
            id=ident,
            className="bulle",
            role="note",
            hidden=True,
        ),
    ]


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


def mot(texte: str, variante: str | None = None, **attributs: Any) -> html.Span:
    """La marque courte posée à côté d'un chiffre : « Estimé », « Partiel », « Minorée »…"""
    classes = "mot" + (f" mot--{variante}" if variante else "")
    return html.Span(texte, className=classes, **attributs)


def pied_avec_mot(marque: str, texte: str | None = None, variante: str | None = None) -> list:
    return [mot(marque, variante), f" {texte}" if texte else None]


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
    """Une tuile de chiffre clé. Le `ton` colore le bord ; la `classe` colore le chiffre."""
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
