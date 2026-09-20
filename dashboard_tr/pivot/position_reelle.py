"""Le second contrat du format pivot : ce que la banque dit détenir aujourd'hui.

Les opérations racontent **l'histoire** d'un portefeuille ; une position réelle en donne la
**photo**, telle que la banque l'affiche à l'instant où on la lui demande. Les deux doivent
concorder, et c'est le seul moyen de découvrir des titres entrés sans qu'aucun événement ne
le dise — la limite connue de [D-15](../../docs/decisions.md).

Comme pour les opérations, c'est un adaptateur qui produit ces lignes : le moteur n'ouvre
aucun fichier de banque (D-26). Le format est décrit dans `docs/format-pivot.md` §9.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PositionReelle:
    """Une ligne du portefeuille tel que la banque le présente."""

    actif: str
    """ISIN, ou code interne pour la crypto. Même identifiant que dans les opérations."""

    quantite: Decimal
    """Nombre de parts détenues. **C'est la seule valeur qui sert de contrôle** (D-46)."""

    nom_actif: str | None = None
    """Affichage seulement, jamais un calcul (règle 4 de CLAUDE.md)."""

    prix_de_revient_banque: Decimal | None = None
    """Prix de revient calculé par la banque, **à titre d'information seulement** (D-46).

    On ignore ce que la banque y met — frais d'achat compris ou non, quelle méthode de
    moyenne — alors que le prix de revient du projet les exclut explicitement (D-13). Le
    comparer automatiquement déclencherait une alerte sur presque chaque actif, à tort. Il
    est donc affiché à côté du nôtre, étiqueté, et ne déclenche jamais rien.
    """
