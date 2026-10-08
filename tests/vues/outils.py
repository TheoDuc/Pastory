"""Lire un écran Dash sans navigateur : son texte, ses classes, ses identifiants."""

from __future__ import annotations

import re
from collections.abc import Iterator

from dash.development.base_component import Component


def noeuds(composant) -> Iterator[Component]:
    """Tous les composants de l'arbre, dans l'ordre du document."""
    if isinstance(composant, (list, tuple)):
        for enfant in composant:
            yield from noeuds(enfant)
    elif isinstance(composant, Component):
        yield composant
        yield from noeuds(getattr(composant, "children", None))
        # Une zone de dépôt ou un indicateur de chargement porte son contenu ailleurs.
        for attribut in ("custom_spinner",):
            yield from noeuds(getattr(composant, attribut, None))


def texte(composant) -> str:
    """Le texte lisible de l'arbre, mis bout à bout, espaces normalisées."""
    morceaux: list[str] = []

    def lire(element) -> None:
        if element is None or isinstance(element, bool):
            return
        if isinstance(element, (str, int, float)):
            morceaux.append(str(element))
        elif isinstance(element, (list, tuple)):
            for enfant in element:
                lire(enfant)
        elif isinstance(element, Component):
            lire(getattr(element, "children", None))

    lire(composant)
    # Seules les espaces ordinaires sont normalisées : l'espace insécable d'un montant fait partie
    # de ce qu'on vérifie (conception §3.2).
    return re.sub(r"[ \t\r\n]+", " ", " ".join(morceaux)).strip()


def classes(composant) -> set[str]:
    trouvees: set[str] = set()
    for noeud in noeuds(composant):
        trouvees.update((getattr(noeud, "className", None) or "").split())
    return trouvees


def identifiants(composant) -> list:
    return [noeud.id for noeud in noeuds(composant) if getattr(noeud, "id", None) is not None]


def dessins(composant, nature: str) -> list[Component]:
    return [
        noeud
        for noeud in noeuds(composant)
        if getattr(noeud, "data-dessin", None) == nature
    ]
