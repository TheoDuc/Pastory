"""Les coûts, tenus à part de la performance (D-21) : ceux qu'on a payés, et ceux qu'on estime.

Deux familles, qui ne se mélangent jamais dans un même total :

- **les coûts payés** : frais et taxes lus dans les données, opération par opération, avec
  leur **poids** dans l'opération — 1 € de frais sur un achat de 25 € pèse 4 % (glossaire §6).
  C'est ce qui montre qu'un petit ordre ponctuel coûte cher et qu'un plan d'épargne gratuit
  ne l'est pas tout à fait ;
- **les coûts estimés** (D-17) : le spread, payé à chaque achat et à chaque vente sans jamais
  apparaître nulle part (D-30, D-56), et les frais courants d'un ETF (TER), prélevés dans sa
  valeur pendant la détention. Toujours affichés comme estimations, avec le paramètre qui les
  a produits : sa valeur, sa date, sa source.

Le moteur ne sait pas ce qu'est un ETF ni d'où vient un taux. Il déclare ce qu'il attend d'un
**paramètre** et de qui les fournit (`ParametresDeCouts`), et c'est `cli.py` qui lui passe le
barème et les déclarations de l'utilisateur — exactement comme la source de cours à l'étape 5.

```
spread estimé d'un achat ou d'une vente = montant brut × taux par côté
frais courants estimés d'un ETF, par an  = valeur brute × TER
poids d'un coût dans son opération       = (frais + taxes) / montant brut
```
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from pastory import tableur
from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.rendements import Periode
from pastory.moteur.valorisation import PositionValorisee, Valorisation
from pastory.pivot.operation import Operation, Poche, TypeOperation

ZERO = Decimal("0.00")
CENT = Decimal("100")
CENTIME = Decimal("0.01")
PAS_DU_POIDS = Decimal("0.000001")
"""Un poids est une fraction issue d'une division : six décimales, comme les taux."""

TYPES_AVEC_SPREAD = frozenset({TypeOperation.ACHAT, TypeOperation.VENTE})
"""Seules une exécution d'achat ou de vente paient un écart de prix. Des titres reçus, un
dividende, une distribution ne passent par aucun carnet d'ordres."""

MOMENTS: dict[TypeOperation, str] = {
    TypeOperation.ACHAT: "à l'entrée",
    TypeOperation.TITRES_RECUS: "à l'entrée",
    TypeOperation.VENTE: "à la sortie",
    TypeOperation.DIVIDENDE: "sur les revenus",
    TypeOperation.DISTRIBUTION_CAPITAL: "autres",
}
"""Les trois niveaux de Q-21, plus un tiroir pour ce qui n'y entre pas."""


# --- Ce que le moteur demande, sans savoir qui répond ----------------------------------


class ParametreDate(Protocol):
    """Un paramètre qu'on peut citer : sa valeur, son unité, sa date, sa source.

    `parametres.lecture.Parametre` a exactement cette forme, sans que ce module le sache.
    """

    nom: str
    valeur: Decimal
    unite: str
    source: str
    en_vigueur_depuis: Date | None
    verifie_le: Date | None
    basse: Decimal | None
    haute: Decimal | None
    note: str

    @property
    def en_clair(self) -> str: ...

    @property
    def origine(self) -> str: ...


class ParametresDeCouts(Protocol):
    """Qui sait dire, pour un actif, ce que coûte un ordre, un aller simple, une année."""

    def spread_par_cote(self, actif: str, poche: Poche) -> ParametreDate | None:
        """Le taux de spread par côté, en pour cent. `None` si le type de l'actif n'est pas
        déclaré : on n'estime rien sur une base inconnue (D-55)."""
        ...

    def attend_un_ter(self, actif: str, poche: Poche) -> bool:
        """Vrai si l'actif est un ETF : lui seul prélève des frais courants."""
        ...

    def ter(self, actif: str) -> ParametreDate | None:
        """Les frais courants annuels validés par l'utilisateur, en pour cent, ou rien."""
        ...

    def frais_par_ordre(self, poche: Poche) -> ParametreDate:
        """Ce qu'un ordre de vente coûterait dans cette poche, en euros."""
        ...


# --- Une estimation : un montant, et d'où il sort ---------------------------------------


@dataclass(frozen=True)
class Estimation:
    """Un montant estimé, avec le paramètre qui l'a produit et la base à laquelle il s'est
    appliqué. C'est ce qui permet au rapport d'écrire « 600,00 × 0,05 % = 0,30 »."""

    montant: Decimal
    parametre: ParametreDate
    base: Decimal | None = None
    """Le montant auquel le taux s'est appliqué. `None` pour un montant fixe (frais par ordre)."""

    @property
    def formule(self) -> str:
        if self.base is None:
            return f"{tableur.nombre_lisible(self.montant)} (montant fixe)"
        return (
            f"{tableur.nombre_lisible(self.base)} x {self.parametre.en_clair} = "
            f"{tableur.nombre_lisible(self.montant)}"
        )


def appliquer_un_taux(base: Decimal, parametre: ParametreDate) -> Estimation:
    """`base × taux / 100`, au centime. Le taux est en pour cent, comme dans les fichiers."""
    montant = (base * parametre.valeur / CENT).quantize(CENTIME, rounding=ROUND_HALF_UP)
    return Estimation(montant=montant, parametre=parametre, base=base)


def montant_fixe(parametre: ParametreDate) -> Estimation:
    return Estimation(montant=parametre.valeur.quantize(CENTIME), parametre=parametre)


# --- Les coûts payés, opération par opération --------------------------------------------


@dataclass(frozen=True)
class LigneDeCout:
    """Une opération vue par ses coûts : ce qu'elle a coûté, et ce qu'elle a probablement
    coûté en plus."""

    operation: Operation
    spread_estime: Estimation | None
    """`None` si l'opération n'en paie pas (dividende, titres reçus) **ou** si le type de
    l'actif n'est pas déclaré : `spread_attendu` fait la différence."""

    @property
    def actif(self) -> str:
        return self.operation.actif

    @property
    def poche(self) -> Poche:
        return self.operation.poche

    @property
    def date(self) -> Date:
        return self.operation.date

    @property
    def type(self) -> TypeOperation:
        return self.operation.type

    @property
    def moment(self) -> str:
        return MOMENTS[self.operation.type]

    @property
    def montant_brut(self) -> Decimal | None:
        """`None` tant qu'un prix est à compléter (D-15) : pas de base, donc pas de poids."""
        if self.operation.est_a_completer("montant_brut"):
            return None
        return self.operation.montant_brut

    @property
    def frais(self) -> Decimal:
        return self.operation.frais

    @property
    def taxes(self) -> Decimal:
        return self.operation.taxes

    @property
    def cout_paye(self) -> Decimal:
        return self.frais + self.taxes

    @property
    def poids(self) -> Decimal | None:
        """(frais + taxes) / montant brut, en fraction (0,04 pour 4 %). `None` sans base."""
        brut = self.montant_brut
        if brut is None or brut <= ZERO:
            return None
        return (self.cout_paye / brut).quantize(PAS_DU_POIDS, rounding=ROUND_HALF_UP)

    @property
    def spread_attendu(self) -> bool:
        """Vrai pour un achat ou une vente : il y a eu une exécution, donc un écart de prix."""
        return self.operation.type in TYPES_AVEC_SPREAD

    @property
    def spread_manquant(self) -> bool:
        """Un spread aurait dû être estimé et ne l'a pas été : le type de l'actif manque."""
        return self.spread_attendu and self.spread_estime is None and self.montant_brut is not None


def lignes_de_couts(
    portefeuille: Portefeuille, periode: Periode, parametres: ParametresDeCouts
) -> list[LigneDeCout]:
    """Toutes les opérations de la période, dans l'ordre du journal (poche, actif, temps)."""
    lignes: list[LigneDeCout] = []
    for position in portefeuille.positions:
        for ligne in position.journal:
            operation = ligne.operation
            if not periode.contient(operation.date):
                continue
            lignes.append(LigneDeCout(operation, _spread(operation, parametres)))
    return lignes


def _spread(operation: Operation, parametres: ParametresDeCouts) -> Estimation | None:
    if operation.type not in TYPES_AVEC_SPREAD:
        return None
    if operation.est_a_completer("montant_brut") or operation.montant_brut is None:
        return None
    taux = parametres.spread_par_cote(operation.actif, operation.poche)
    if taux is None:
        return None
    return appliquer_un_taux(operation.montant_brut, taux)


@dataclass(frozen=True)
class TotauxCouts:
    """La somme d'un groupe de lignes : un actif, une poche, ou tout."""

    lignes: tuple[LigneDeCout, ...]

    @property
    def frais(self) -> Decimal:
        return sum((ligne.frais for ligne in self.lignes), ZERO)

    @property
    def taxes(self) -> Decimal:
        return sum((ligne.taxes for ligne in self.lignes), ZERO)

    @property
    def cout_paye(self) -> Decimal:
        return self.frais + self.taxes

    @property
    def montant_brut_connu(self) -> Decimal:
        """La base du poids moyen : les seuls montants bruts connus."""
        return sum((ligne.montant_brut or ZERO for ligne in self.lignes), ZERO)

    @property
    def poids_moyen(self) -> Decimal | None:
        """Coûts payés sur les opérations à base connue / cette base. `None` sans base."""
        base = self.montant_brut_connu
        if base <= ZERO:
            return None
        payes = sum(
            (ligne.cout_paye for ligne in self.lignes if ligne.montant_brut is not None), ZERO
        )
        return (payes / base).quantize(PAS_DU_POIDS, rounding=ROUND_HALF_UP)

    def par_moment(self) -> dict[str, Decimal]:
        """Les coûts payés par niveau (entrée, sortie, revenus, autres), dans cet ordre.

        La somme des quatre vaut toujours `cout_paye`.
        """
        moments: dict[str, Decimal] = {}
        for nom in ("à l'entrée", "à la sortie", "sur les revenus", "autres"):
            moments[nom] = sum(
                (ligne.cout_paye for ligne in self.lignes if ligne.moment == nom), ZERO
            )
        return moments

    @property
    def spread_estime(self) -> Decimal:
        """La somme des spreads estimés — sur les seules opérations où il l'a été."""
        return sum(
            (ligne.spread_estime.montant for ligne in self.lignes if ligne.spread_estime), ZERO
        )

    @property
    def spreads_manquants(self) -> list[LigneDeCout]:
        """Les achats et ventes sans estimation : la somme ci-dessus est partielle."""
        return [ligne for ligne in self.lignes if ligne.spread_manquant]

    @property
    def actifs_sans_type(self) -> list[str]:
        return sorted({ligne.actif for ligne in self.spreads_manquants})


def totaux_par_poche(lignes: Iterable[LigneDeCout]) -> dict[Poche, TotauxCouts]:
    groupes: dict[Poche, list[LigneDeCout]] = {}
    for ligne in lignes:
        groupes.setdefault(ligne.poche, []).append(ligne)
    return {poche: TotauxCouts(tuple(groupes[poche])) for poche in Poche if poche in groupes}


def totaux_par_actif(lignes: Iterable[LigneDeCout]) -> dict[tuple[str, Poche], TotauxCouts]:
    groupes: dict[tuple[str, Poche], list[LigneDeCout]] = {}
    for ligne in lignes:
        groupes.setdefault((ligne.actif, ligne.poche), []).append(ligne)
    return {cle: TotauxCouts(tuple(du_groupe)) for cle, du_groupe in groupes.items()}


# --- Les frais courants des ETF, pendant la détention ---------------------------------------


@dataclass(frozen=True)
class FraisCourantsEstimes:
    """Ce qu'un ETF détenu coûte par an, à la valeur du jour — ou pourquoi on ne sait pas."""

    position: PositionValorisee
    estimation: Estimation | None
    motif: str | None = None

    @property
    def actif(self) -> str:
        return self.position.actif

    @property
    def poche(self) -> Poche:
        return self.position.poche


def frais_courants(
    valorisation: Valorisation, parametres: ParametresDeCouts
) -> list[FraisCourantsEstimes]:
    """Pour chaque ETF valorisé : valeur brute × TER, par an (glossaire §6).

    Un ETF sans TER validé apparaît avec un motif, jamais pour zéro (D-61). Les actifs qui ne
    sont pas des ETF n'apparaissent pas : ils n'ont pas de frais courants.
    """
    resultat: list[FraisCourantsEstimes] = []
    for position in valorisation.positions:
        if not parametres.attend_un_ter(position.actif, position.poche):
            continue
        if position.valeur is None:
            resultat.append(
                FraisCourantsEstimes(position, None, motif="actif non valorisé (D-53)")
            )
            continue
        ter = parametres.ter(position.actif)
        if ter is None:
            resultat.append(
                FraisCourantsEstimes(
                    position,
                    None,
                    motif="TER non déclaré : « pastory actifs » en propose un, à vérifier "
                    "sur la fiche de l'émetteur",
                )
            )
            continue
        resultat.append(FraisCourantsEstimes(position, appliquer_un_taux(position.valeur, ter)))
    return resultat


# --- Tout ce que le rapport et les CSV montrent, calculé une fois -----------------------


@dataclass(frozen=True)
class DetailDesCouts:
    """Les coûts d'un portefeuille sur une période : payés, estimés, et par quel chemin.

    C'est l'équivalent de `Synthese` pour les coûts : le rapport et les CSV y puisent, et rien
    n'est recalculé deux fois.
    """

    periode: Periode
    lignes: tuple[LigneDeCout, ...]
    frais_courants: tuple[FraisCourantsEstimes, ...]
    noms: dict[tuple[str, Poche], str | None]
    """Le nom affiché de chaque position, pour les tableaux. Aucun calcul n'en dépend
    (règle 4 de CLAUDE.md)."""

    @property
    def total(self) -> TotauxCouts:
        return TotauxCouts(self.lignes)

    def par_poche(self) -> dict[Poche, TotauxCouts]:
        return totaux_par_poche(self.lignes)

    def par_actif(self) -> dict[tuple[str, Poche], TotauxCouts]:
        return totaux_par_actif(self.lignes)

    def nom_de(self, actif: str, poche: Poche) -> str | None:
        return self.noms.get((actif, poche))


def detailler(
    portefeuille: Portefeuille,
    periode: Periode,
    valorisation: Valorisation,
    parametres: ParametresDeCouts,
) -> DetailDesCouts:
    """Les coûts payés de la période, et les coûts estimés à la date de la valorisation."""
    return DetailDesCouts(
        periode=periode,
        lignes=tuple(lignes_de_couts(portefeuille, periode, parametres)),
        frais_courants=tuple(frais_courants(valorisation, parametres)),
        noms={
            (position.actif, position.poche): position.nom_actif
            for position in portefeuille.positions
        },
    )
