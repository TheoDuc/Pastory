"""Ce que l'utilisateur a choisi à l'écran : l'onglet, la période, les poches, le tri…

L'état est un simple dictionnaire, gardé par le navigateur (`dcc.Store`) : il ne contient
**aucun chiffre**, seulement des choix. Les chiffres sont recalculés en Python à partir de lui.

`appliquer()` est la seule fonction qui le change, et c'est une fonction pure : chaque règle de
la maquette s'y lit et se teste sans navigateur.
"""

from __future__ import annotations

from typing import Any

from pastory.vues.bandeau import ACCUEIL, ONGLETS, TYPES
from pastory.vues.chiffres import PERIODE_PAR_DEFAUT, PERIODES

Etat = dict[str, Any]

COLONNES_TEXTE = {"nom", "poche"}
"""Les colonnes triées par ordre alphabétique : un premier clic les trie de A à Z. Les autres
sont des nombres, triés du plus grand au plus petit."""


def initial() -> Etat:
    # Chaque session s'ouvre sur la couverture : c'est d'elle que le livre s'ouvre (D-98).
    return {
        "onglet": ACCUEIL,
        "periode": PERIODE_PAR_DEFAUT,
        "poches": None,
        "type": "tous",
        "tri": "valeur",
        "sens": -1,
        "rubrique": "classes",
        "page": 0,
        "deplie": False,
        "ancre": None,
        "message": None,
        "version": 0,
    }


def appliquer(etat: Etat, champ: str, valeur: str, poches_presentes: list[str]) -> Etat:
    """Le nouvel état après un clic sur le bouton `{"choix": champ, "valeur": valeur}`."""
    nouveau = {**initial(), **etat, "ancre": None}
    if champ != "depot":
        nouveau["message"] = None
    match champ:
        # « aller » : un bouton du corps de page qui mène à un onglet. Il ne peut pas porter
        # l'identifiant de l'onglet lui-même, qui est déjà dans la manchette.
        case "onglet" | "aller" if valeur == ACCUEIL or any(o.cle == valeur for o in ONGLETS):
            nouveau["onglet"] = valeur
            nouveau["page"] = 0
        case "periode" if any(p.cle == valeur for p in PERIODES):
            nouveau["periode"] = valeur
        case "type" if any(cle == valeur for cle, _ in TYPES):
            nouveau["type"] = valeur
        case "poche":
            nouveau["poches"] = _basculer(etat.get("poches"), valeur, poches_presentes)
            nouveau["page"] = 0
        case "tri":
            if etat.get("tri") == valeur:
                nouveau["sens"] = -int(etat.get("sens", -1))
            else:
                nouveau["tri"] = valeur
                nouveau["sens"] = 1 if valeur in COLONNES_TEXTE else -1
        case "rubrique":
            nouveau["rubrique"] = valeur
            nouveau["deplie"] = False
        case "deplier":
            nouveau["deplie"] = not etat.get("deplie", False)
        case "page":
            nouveau["page"] = max(0, int(etat.get("page", 0)) + (1 if valeur == "suivant" else -1))
    return nouveau


def _basculer(poches: list[str] | None, poche: str, presentes: list[str]) -> list[str] | None:
    """Coche ou décoche une poche. **La dernière ne se décoche jamais** : un écran sans aucune
    poche ne dit rien, et laisserait croire à un portefeuille vide. `None` veut dire toutes."""
    if poche not in presentes:
        return poches
    cochees = list(presentes) if poches is None else [p for p in presentes if p in poches]
    if poche in cochees:
        if len(cochees) > 1:
            cochees.remove(poche)
    else:
        cochees.append(poche)
    cochees = [p for p in presentes if p in cochees]
    return None if cochees == list(presentes) else cochees
