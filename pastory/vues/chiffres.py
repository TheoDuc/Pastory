"""Les chiffres que l'interface montre : calculés par l'assembleur, gardés tant que rien ne change.

L'interface ne calcule rien elle-même. Elle demande à l'assembleur (`pastory/assembleur.py`) —
le même que celui de `pastory positions` — de lire les exports, de trouver les réglages et de
faire tourner le moteur ; elle garde le résultat en mémoire, et ne le refait que si l'utilisateur
dépose un export ou corrige un réglage (`relire()`).

Deux choses seulement sont recalculées à la demande, et toujours **par le moteur** :

- **la période** (1 mois, 1 an, tout…) : le gain, le TRI et le TWRR dépendent du début ;
- **les poches** cochées : le TRI de « PEA + CTO » n'est pas une moyenne des deux, il se calcule
  sur les opérations de ces deux poches seulement. Le moteur rejoue donc ce sous-portefeuille.

Les sources réseau (cours, compositions, réglages) ne sont interrogées qu'à la première lecture :
ensuite, tout vient du cache, et un changement de période ne coûte que du calcul.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

from pastory import assembleur
from pastory.adaptateurs.trade_republic.depot import ExportIntrouvable
from pastory.config import ConfigurationInvalide
from pastory.donnees_externes.cache import CacheIllisible
from pastory.moteur import rendements as rendements_moteur
from pastory.moteur import valorisation as valorisation_moteur
from pastory.moteur.portefeuille import Portefeuille
from pastory.parametres import ParametresInvalides
from pastory.pivot.operation import Poche


@dataclass(frozen=True)
class ChoixDePeriode:
    cle: str
    nom: str
    jours: int | None
    """`None` : depuis la première opération."""


PERIODES = (
    ChoixDePeriode("1m", "1 mois", 31),
    ChoixDePeriode("6m", "6 mois", 183),
    ChoixDePeriode("1a", "1 an", 365),
    ChoixDePeriode("5a", "5 ans", 1826),
    ChoixDePeriode("tout", "Tout", None),
)
PERIODE_PAR_DEFAUT = "tout"


def periode_de(cle: str, fin: Date) -> rendements_moteur.Periode:
    """La période du moteur pour un bouton de période. Une clé inconnue vaut « Tout »."""
    choisie = next((p for p in PERIODES if p.cle == cle), PERIODES[-1])
    if choisie.jours is None:
        return rendements_moteur.Periode(fin=fin)
    return rendements_moteur.Periode(fin=fin, debut=fin - timedelta(days=choisie.jours))


@dataclass(frozen=True)
class Echec:
    """Rien à montrer, et pourquoi. Ce n'est pas forcément une erreur (conception §5)."""

    nature: str
    """`aucun-export` (l'état vide de l'accueil), `fichier-a-corriger` ou `memoire-illisible`."""

    message: str


@dataclass(frozen=True)
class Vue:
    """Ce qu'un écran filtré affiche : la base, et la synthèse de la période et des poches."""

    construit: assembleur.Construit
    """Le portefeuille entier, depuis la première opération : la diversification, les frais
    et la valeur réelle n'ont pas de filtre (conception §4), ils lisent ceci."""

    synthese: rendements_moteur.Synthese
    """Pour la période et les poches choisies."""

    portefeuille: Portefeuille
    """Les seules poches choisies."""

    poches_presentes: tuple[Poche, ...]
    poches: tuple[Poche, ...]

    @property
    def toutes_les_poches(self) -> bool:
        return self.poches == self.poches_presentes


Construire = Callable[..., assembleur.Construit]


class Chiffres:
    """Le point d'entrée des chiffres pour l'interface. Une instance par application."""

    def __init__(
        self,
        dossier: Path | None = None,
        hors_ligne: bool = False,
        aujourd_hui: Callable[[], Date] = Date.today,
        construire: Construire | None = None,
    ) -> None:
        """`dossier` : un autre dossier d'exports que le dossier de dépôt — celui d'un tiers,
        lu alors sans aucun appel réseau (règle 2 de CLAUDE.md)."""
        self.dossier_export = dossier
        self.hors_ligne = hors_ligne
        self._aujourd_hui = aujourd_hui
        self._construire = construire
        self._verrou = threading.RLock()
        self._base: assembleur.Construit | Echec | None = None
        self._vues: dict[tuple[str, tuple[Poche, ...]], Vue] = {}
        self._evolutions: dict[tuple[Poche, ...], list[valorisation_moteur.PointEvolution]] = {}
        self.version = 0
        """Change à chaque relecture : l'écran s'en sert pour savoir qu'il doit se redessiner."""

    @property
    def tiers(self) -> bool:
        return self.dossier_export is not None

    def dossier(self) -> Path:
        return assembleur.dossier_de_lecture(self.dossier_export)

    def relire(self) -> None:
        """Oublie tout : au prochain écran, les exports sont relus et le moteur rejoue."""
        with self._verrou:
            self._base = None
            self._vues.clear()
            self._evolutions.clear()
            self.version += 1

    def base(self) -> assembleur.Construit | Echec:
        """Le portefeuille entier, depuis la première opération, arrêté à aujourd'hui."""
        with self._verrou:
            if self._base is None:
                self._base = self._calculer_la_base()
            return self._base

    def _calculer_la_base(self) -> assembleur.Construit | Echec:
        construire = self._construire or assembleur.construire
        try:
            return construire(
                self.dossier(),
                rendements_moteur.Periode(fin=self._aujourd_hui()),
                self.hors_ligne,
                tiers=self.tiers,
            )
        except ExportIntrouvable as erreur:
            return Echec("aucun-export", str(erreur))
        except (ConfigurationInvalide, ParametresInvalides) as erreur:
            return Echec("fichier-a-corriger", str(erreur))
        except CacheIllisible as erreur:
            return Echec("memoire-illisible", str(erreur))

    def vue(self, periode: str, poches: Sequence[str] | None = None) -> Vue | Echec:
        """La synthèse pour une période et des poches. `poches=None` : toutes."""
        base = self.base()
        if isinstance(base, Echec):
            return base
        presentes = poches_du(base.portefeuille)
        retenues = tuple(p for p in presentes if poches is None or p.value in poches)
        if not retenues:
            # On ne montre jamais un écran sans aucune poche : il laisserait croire à un
            # portefeuille vide. Le filtre reprend tout (c'est aussi la règle de la maquette).
            retenues = presentes
        cle = (periode, retenues)
        with self._verrou:
            if cle not in self._vues:
                self._vues[cle] = self._calculer_la_vue(base, periode, presentes, retenues)
            return self._vues[cle]

    def _calculer_la_vue(
        self,
        base: assembleur.Construit,
        periode: str,
        presentes: tuple[Poche, ...],
        retenues: tuple[Poche, ...],
    ) -> Vue:
        portefeuille = self._portefeuille(base, presentes, retenues)
        la_periode = periode_de(periode, base.periode.fin)
        if la_periode == base.periode and retenues == presentes:
            synthese = base.synthese
        else:
            synthese = rendements_moteur.synthese(portefeuille, la_periode, base.fournisseur)
        return Vue(
            construit=base,
            synthese=synthese,
            portefeuille=portefeuille,
            poches_presentes=presentes,
            poches=retenues,
        )

    @staticmethod
    def _portefeuille(
        base: assembleur.Construit, presentes: tuple[Poche, ...], retenues: tuple[Poche, ...]
    ) -> Portefeuille:
        if retenues == presentes:
            return base.portefeuille
        operations = [op for op in base.completion.operations if op.poche in retenues]
        return Portefeuille.construire(operations).au(base.periode.fin)

    def evolution(self, vue: Vue) -> list[valorisation_moteur.PointEvolution]:
        """La valeur jour par jour, de la veille de la première opération à la fin, pour les
        poches de la vue. Calculée une fois par choix de poches : la période ne fait que la
        couper. La veille vaut zéro : la courbe part de rien, et le premier versement se voit."""
        with self._verrou:
            if vue.poches not in self._evolutions:
                premier = premier_jour(vue.portefeuille)
                self._evolutions[vue.poches] = (
                    valorisation_moteur.evolution(
                        vue.portefeuille,
                        premier - timedelta(days=1),
                        vue.construit.periode.fin,
                        vue.construit.fournisseur,
                    )
                    if premier is not None
                    else []
                )
            return self._evolutions[vue.poches]


def poches_du(portefeuille: Portefeuille) -> tuple[Poche, ...]:
    """Les poches où le portefeuille a au moins une position, dans l'ordre PEA, CTO, crypto.

    Une poche vide n'apparaît pas (conception §5.1) : sans PEA, aucun bouton « PEA »."""
    presentes = {position.poche for position in portefeuille.positions}
    return tuple(poche for poche in Poche if poche in presentes)


def premier_jour(portefeuille: Portefeuille) -> Date | None:
    """Le jour de la première opération, d'où part la courbe."""
    jours = [position.journal[0].date for position in portefeuille.positions if position.journal]
    return min(jours) if jours else None
