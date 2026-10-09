"""La prédiction de l'évolution : une hypothèse sur l'avenir, jamais une prévision (D-97, D-105).

Un module **indépendant** ([D-27](../docs/decisions.md)) : il n'importe rien du moteur, et rien
n'en dépend. Il reçoit une valeur de départ — la valeur des actifs, passée par l'écran — et des
hypothèses saisies ; il rend des montants. Les formules sont celles du glossaire §9, refaisables
à la main :

- **sans aléa**, chaque mois : `V ← V × g + versement`, avec `g = (1 + taux)^(1/12)` ;
- **avec aléa**, chaque mois : `V ← V × exp(μ + σₘ × Z) + versement`, avec `μ = ln(1 + taux)/12`
  (la médiane de croissance vaut le taux), `σₘ = σ/√12`, et **σ = 2 × taux** — aucune valeur
  historique, la dispersion ne dépend que du taux visé ;
- 10 000 chemins, une **graine fixe** : les mêmes entrées redonnent les mêmes courbes.

Tout est **nominal** : avant impôt, frais et inflation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

import numpy as np

TAUX_MAXIMAL = Decimal("30")
"""En pour cent : au-delà, l'hypothèse n'a plus de sens pour un placement."""
MONTANT_MAXIMAL = Decimal("1000000000")
"""Un milliard d'euros de départ, et dix millions par mois : au-delà, les montants sortent de
la précision du calcul, et l'hypothèse n'a plus de sens pour un particulier."""
VERSEMENT_MAXIMAL = Decimal("10000000")
DUREE_MINIMALE = 1
DUREE_MAXIMALE = 50
VOLATILITE_PAR_POINT_DE_TAUX = 2
"""La volatilité annuelle vaut deux fois le taux (D-105) : 4 % donne 8 %, 15 % donne 30 %."""
TIRAGES = 10_000
GRAINE = 20261009
"""Fixe : les mêmes entrées redonnent toujours les mêmes courbes, au centime près."""
QUANTILES = (10, 25, 50, 75, 90)
"""10 % et 90 % plutôt que 5 % et 95 % : des extrêmes moins rares, plus parlants (retour du
propriétaire). « Dans 8 cas sur 10 » se lit entre le premier et le dernier."""

CENT = Decimal(100)


@dataclass(frozen=True)
class Hypotheses:
    depart: Decimal
    """La valeur de départ, en euros."""
    taux: Decimal
    """Le taux annuel, en fraction : 0,05 pour 5 %."""
    annees: int
    versement: Decimal
    """Le versement mensuel, en euros, versé en fin de mois."""

    @property
    def mois(self) -> int:
        return self.annees * 12

    @property
    def volatilite(self) -> Decimal:
        """La volatilité annuelle, en fraction."""
        return self.taux * VOLATILITE_PAR_POINT_DE_TAUX

    @property
    def verse(self) -> Decimal:
        """Ce qui a été placé : le départ et tous les versements."""
        return self.depart + self.versement * self.mois


def lire(
    depart: object, taux_pour_cent: object, annees: object, versement: object
) -> Hypotheses | str:
    """Les hypothèses saisies à l'écran, ou le **motif** pour lequel elles ne conviennent pas.
    Une entrée vide ou hors bornes n'est jamais remplacée par une valeur choisie en silence."""
    valeurs = {}
    for nom, brut in (
        ("la valeur de départ", depart),
        ("le taux", taux_pour_cent),
        ("la durée", annees),
        ("le versement mensuel", versement),
    ):
        if brut is None or brut == "":
            return f"Indiquez {nom}."
        try:
            valeurs[nom] = Decimal(str(brut))
        except ArithmeticError:
            return f"{nom.capitalize()} n'est pas un nombre."
    if valeurs["la valeur de départ"] < 0 or valeurs["le versement mensuel"] < 0:
        return "La valeur de départ et le versement ne peuvent pas être négatifs."
    if valeurs["la valeur de départ"] > MONTANT_MAXIMAL:
        return "La valeur de départ ne peut pas dépasser un milliard d'euros."
    if valeurs["le versement mensuel"] > VERSEMENT_MAXIMAL:
        return "Le versement mensuel ne peut pas dépasser dix millions d'euros."
    taux = valeurs["le taux"]
    if not 0 <= taux <= TAUX_MAXIMAL:
        return f"Le taux doit être compris entre 0 % et {TAUX_MAXIMAL} %."
    duree = valeurs["la durée"]
    if duree != duree.to_integral_value() or not DUREE_MINIMALE <= duree <= DUREE_MAXIMALE:
        return (
            f"La durée doit être un nombre entier d'années, de {DUREE_MINIMALE} à "
            f"{DUREE_MAXIMALE}."
        )
    return Hypotheses(
        depart=valeurs["la valeur de départ"],
        taux=taux / CENT,
        annees=int(duree),
        versement=valeurs["le versement mensuel"],
    )


def sans_alea(h: Hypotheses) -> list[Decimal]:
    """La valeur à la fin de chaque mois, du mois 0 (le départ) au dernier. En `Decimal` : le
    calcul se refait à la calculatrice, mois par mois ou par la forme fermée du glossaire."""
    g = (1 + h.taux) ** (Decimal(1) / 12)
    valeurs = [h.depart]
    for _ in range(h.mois):
        valeurs.append(valeurs[-1] * g + h.versement)
    return valeurs


def forme_fermee(h: Hypotheses) -> Decimal:
    """`Vₙ = V₀ × gⁿ + v × (gⁿ − 1)/(g − 1)` (si le taux est nul : `V₀ + n × v`). Elle sert de
    contrôle au calcul mois par mois, et c'est celle du cahier de vérification."""
    if h.taux == 0:
        return h.depart + h.versement * h.mois
    g = (1 + h.taux) ** (Decimal(1) / 12)
    gn = g**h.mois
    return h.depart * gn + h.versement * (gn - 1) / (g - 1)


@dataclass(frozen=True)
class Eventail:
    """Les quantiles des 10 000 chemins, mois par mois."""

    quantiles: dict[int, list[float]]
    """Pour chaque quantile (10, 25, 50, 75, 90), sa valeur à la fin de chaque mois."""

    def a_la_fin(self, quantile: int) -> Decimal:
        return Decimal(str(round(self.quantiles[quantile][-1], 2)))


@lru_cache(maxsize=16)
def avec_alea(h: Hypotheses, tirages: int = TIRAGES, graine: int = GRAINE) -> Eventail:
    """Les 10 000 chemins, tirés selon la loi log-normale mois par mois (D-105), et leurs
    quantiles. Le hasard a une graine fixe : le résultat ne dépend que des hypothèses, et il est
    gardé en mémoire — revenir à « 10 000 simulations » ne refait pas les tirages."""
    taux = float(h.taux)
    mu = math.log1p(taux) / 12
    sigma_m = float(h.volatilite) / math.sqrt(12)
    versement = float(h.versement)
    generateur = np.random.default_rng(graine)
    valeurs = np.full(tirages, float(h.depart))
    lignes = np.empty((h.mois + 1, len(QUANTILES)))
    lignes[0] = float(h.depart)
    for mois in range(1, h.mois + 1):
        tirage = generateur.standard_normal(tirages)
        valeurs = valeurs * np.exp(mu + sigma_m * tirage) + versement
        lignes[mois] = np.percentile(valeurs, QUANTILES)
    return Eventail(
        quantiles={q: lignes[:, i].tolist() for i, q in enumerate(QUANTILES)},
    )
