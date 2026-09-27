"""La valeur réelle : ce qu'on récupérerait en vendant tout aujourd'hui (D-23).

```
valeur réelle = valeur brute − frais de vente estimés − spread de vente estimé − impôt estimé
```

Elle part de la valorisation de l'étape 5 (`valorisation.valoriser()`), jamais recalculée, et
en hérite les règles : une position sans cours **n'a pas de valeur réelle**, elle sort des totaux
qui sont alors marqués partiels (D-53). Deux autres absences y font le même effet, chacune avec
son motif : un actif sans type déclaré (pas de spread estimé, D-55) et un impôt non calculable
(PEA sans date, D-59).

Tout ce qui est retranché ici est une **estimation** (D-17) : le rapport le dit, et cite pour
chaque montant le paramètre qui l'a produit. La performance brute, elle, ne change pas (D-21).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal

from dashboard_tr.moteur import fiscalite
from dashboard_tr.moteur.couts import (
    Estimation,
    ParametresDeCouts,
    appliquer_un_taux,
    montant_fixe,
)
from dashboard_tr.moteur.fiscalite import Cession, ImpotEstime, ReglesFiscales
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.valorisation import PositionValorisee, Valorisation
from dashboard_tr.pivot.operation import Poche

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class LigneValeurReelle:
    """Une position vendue aujourd'hui : ce qu'elle vaut, ce que la vente coûterait."""

    position: PositionValorisee
    valeur_brute: Decimal
    frais_de_vente: Estimation
    spread: Estimation

    @property
    def actif(self) -> str:
        return self.position.actif

    @property
    def poche(self) -> Poche:
        return self.position.poche

    @property
    def avant_impot(self) -> Decimal:
        """Valeur brute − frais de vente − spread : ce que la vente rapporterait avant impôt."""
        return self.valeur_brute - self.frais_de_vente.montant - self.spread.montant

    @property
    def cession(self) -> Cession:
        """La même ligne, vue par le fisc."""
        return Cession(
            position=self.position.position,
            valeur_brute=self.valeur_brute,
            spread=self.spread.montant,
            frais_de_vente=self.frais_de_vente.montant,
        )

    @property
    def plus_value_fiscale(self) -> Decimal:
        return self.cession.plus_value(self.poche)


@dataclass(frozen=True)
class Exclue:
    """Une position détenue qui n'a pas de valeur réelle, et pourquoi."""

    position: PositionValorisee
    motif: str


@dataclass(frozen=True)
class ValeurReellePoche:
    poche: Poche
    lignes: tuple[LigneValeurReelle, ...]
    exclues: tuple[Exclue, ...]
    impot: ImpotEstime

    @property
    def valeur_brute(self) -> Decimal:
        return sum((ligne.valeur_brute for ligne in self.lignes), ZERO)

    @property
    def frais_de_vente(self) -> Decimal:
        return sum((ligne.frais_de_vente.montant for ligne in self.lignes), ZERO)

    @property
    def spread(self) -> Decimal:
        return sum((ligne.spread.montant for ligne in self.lignes), ZERO)

    @property
    def avant_impot(self) -> Decimal:
        return self.valeur_brute - self.frais_de_vente - self.spread

    @property
    def valeur_reelle(self) -> Decimal | None:
        """Ce que la poche rapporterait, après frais, spread et impôt.

        `None` dans deux cas, et aucun n'est un zéro :

        - l'impôt n'a pas pu être estimé (PEA sans date déclarée, par exemple) ;
        - le résultat serait **négatif**, ce qui n'arrive que sur un PEA dont l'essentiel du
          gain est déjà en espèces : on retrancherait alors l'impôt d'un argent qu'on ne voit
          pas (`motif_incalculable`). Afficher un nombre négatif laisserait croire à une perte.
        """
        if self.impot.impot is None:
            return None
        valeur = self.avant_impot - self.impot.impot
        return None if valeur < ZERO else valeur

    @property
    def minoree(self) -> bool:
        """Vrai si une part de l'impôt porte sur de l'argent hors des titres (PEA).

        Les ventes passées et les dividendes du plan ont produit des liquidités, qui sont dans
        les espèces du plan — hors périmètre (D-11). Leur impôt est compté ici, leur argent
        non : la valeur réelle de la poche est donc **inférieure** à ce qu'on toucherait.
        """
        return self.impot.hors_des_titres > ZERO

    @property
    def motif_incalculable(self) -> str | None:
        """Pourquoi la poche n'a pas de valeur réelle, quand elle n'en a pas."""
        if self.valeur_reelle is not None:
            return None
        if self.impot.impot is None:
            return self.impot.motif
        return (
            "l'impôt estimé du plan dépasse ce que les titres rapporteraient : l'essentiel de "
            "son gain est déjà en espèces dans le plan, que l'application ne suit pas (D-11). "
            "La valeur réelle de cette poche ne peut pas être établie à partir des seuls titres"
        )

    @property
    def partielle(self) -> bool:
        return bool(self.exclues)

    @property
    def calculable(self) -> bool:
        return self.valeur_reelle is not None


@dataclass(frozen=True)
class ValeurReelle:
    date: Date
    par_poche: dict[Poche, ValeurReellePoche]

    @property
    def poches_calculables(self) -> list[ValeurReellePoche]:
        return [poche for poche in self.par_poche.values() if poche.calculable]

    @property
    def valeur_brute(self) -> Decimal:
        return sum((poche.valeur_brute for poche in self.poches_calculables), ZERO)

    @property
    def frais_de_vente(self) -> Decimal:
        return sum((poche.frais_de_vente for poche in self.poches_calculables), ZERO)

    @property
    def spread(self) -> Decimal:
        return sum((poche.spread for poche in self.poches_calculables), ZERO)

    @property
    def impot(self) -> Decimal:
        return sum((poche.impot.impot or ZERO for poche in self.poches_calculables), ZERO)

    @property
    def valeur_reelle(self) -> Decimal | None:
        """La somme des poches calculables ; `None` s'il n'y en a aucune."""
        calculables = self.poches_calculables
        if not calculables:
            return None
        return sum((poche.valeur_reelle or ZERO for poche in calculables), ZERO)

    @property
    def exclues(self) -> list[Exclue]:
        return [exclue for poche in self.par_poche.values() for exclue in poche.exclues]

    @property
    def poches_non_calculables(self) -> list[ValeurReellePoche]:
        return [poche for poche in self.par_poche.values() if not poche.calculable]

    @property
    def partielle(self) -> bool:
        """Vrai dès qu'une position ou une poche manque au total (D-53)."""
        return bool(self.exclues) or bool(self.poches_non_calculables)

    @property
    def minoree(self) -> bool:
        """Vrai si une poche retenue est minorée par des liquidités non suivies (PEA)."""
        return any(poche.minoree for poche in self.poches_calculables)

    @property
    def hors_des_titres(self) -> Decimal:
        """De combien le total est minoré, au minimum : les liquidités dont l'impôt est
        compté et l'argent non."""
        return sum(
            (poche.impot.hors_des_titres for poche in self.poches_calculables), ZERO
        )

    @property
    def parametres_cites(self) -> list:
        """Tous les paramètres qui ont servi, sans doublon, pour la note de bas de rapport."""
        vus: dict[str, object] = {}
        for poche in self.par_poche.values():
            for ligne in poche.lignes:
                vus.setdefault(ligne.frais_de_vente.parametre.nom, ligne.frais_de_vente.parametre)
                vus.setdefault(ligne.spread.parametre.nom, ligne.spread.parametre)
            for parametre in poche.impot.parametres:
                vus.setdefault(parametre.nom, parametre)
        return list(vus.values())


def _ligne(
    position: PositionValorisee, parametres: ParametresDeCouts
) -> LigneValeurReelle | Exclue:
    if position.valeur is None:
        return Exclue(position, position.motif or "sans cours (D-53)")
    taux = parametres.spread_par_cote(position.actif, position.poche)
    if taux is None:
        return Exclue(
            position,
            "type d'actif non déclaré, donc spread de vente non estimable : complétez "
            "« type » dans actifs.toml (« dashboard actifs » le propose)",
        )
    return LigneValeurReelle(
        position=position,
        valeur_brute=position.valeur,
        frais_de_vente=montant_fixe(parametres.frais_par_ordre(position.poche)),
        spread=appliquer_un_taux(position.valeur, taux),
    )


def valeur_reelle(
    portefeuille: Portefeuille,
    valorisation: Valorisation,
    parametres: ParametresDeCouts,
    regles: ReglesFiscales,
) -> ValeurReelle:
    """Le portefeuille vendu à la date de la valorisation, poche par poche.

    `portefeuille` doit être celui dont `valorisation` est issue (même date) : les positions
    soldées y comptent pour le gain du plan du PEA.
    """
    lignes: list[LigneValeurReelle] = []
    exclues: list[Exclue] = []
    for position in valorisation.positions:
        resultat = _ligne(position, parametres)
        if isinstance(resultat, Exclue):
            exclues.append(resultat)
        else:
            lignes.append(resultat)

    exclues_pea = [exclue for exclue in exclues if exclue.position.poche is Poche.PEA]
    motif_pea = None
    if exclues_pea:
        motif_pea = (
            f"{len(exclues_pea)} position(s) du PEA sans valeur réelle ({exclues_pea[0].motif}) : "
            "le gain du plan ne se calcule pas à moitié"
        )

    impots = fiscalite.impots_estimes(
        (ligne.cession for ligne in lignes), portefeuille, valorisation.date, regles, motif_pea
    )

    par_poche: dict[Poche, ValeurReellePoche] = {}
    for poche, impot in impots.items():
        par_poche[poche] = ValeurReellePoche(
            poche=poche,
            lignes=tuple(ligne for ligne in lignes if ligne.poche is poche),
            exclues=tuple(exclue for exclue in exclues if exclue.position.poche is poche),
            impot=impot,
        )
    return ValeurReelle(date=valorisation.date, par_poche=par_poche)


def cessions_de(lignes: Iterable[LigneValeurReelle]) -> list[Cession]:
    return [ligne.cession for ligne in lignes]
