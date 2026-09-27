"""L'impôt estimé si l'on vendait tout aujourd'hui, poche par poche (D-23, D-59, D-60).

Une **estimation**, jamais une déclaration (D-26). Les règles sont celles du droit français
pour un particulier résident, au prélèvement forfaitaire unique de plein droit
(`docs/couts-et-fiscalite.md` §5) ; les taux viennent d'un fichier daté et sourcé que le
rapport cite à côté de chaque montant (D-58).

Trois poches, trois règles :

| Poche | Base imposable | Taux |
|---|---|---|
| **CTO** | Σ (cession nette − capital fiscal), gains et pertes | impôt sur le revenu |
| | compensés, plancher à zéro | + prélèvements sociaux |
| **PEA** | le gain **du plan** : plus-values latentes + réalisées | avant 5 ans : les deux ; |
| | + dividendes − coûts payés | après : prélèvements sociaux |
| **Crypto** | Σ (cession nette − capital net investi), plancher à | impôt sur le revenu |
| | zéro ; rien sous le seuil de cessions de l'année | + prélèvements sociaux |

La « cession nette » est ce que la vente rapporterait vraiment : valeur brute − spread de vente
estimé − frais de vente. Le moteur déclare ce qu'il attend des règles (`ReglesFiscales`) et
c'est `cli.py` qui les lui passe.

Ce que ce module refuse de calculer, et dit : le PEA sans date de premier versement (l'ancienneté
décide du taux), ou avec une position sans cours (un gain de plan « partiel » n'a pas de sens).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from dashboard_tr import tableur
from dashboard_tr.moteur.couts import ParametreDate
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.position import Position
from dashboard_tr.pivot.operation import Poche, TypeOperation

ZERO = Decimal("0.00")
CENT = Decimal("100")
CENTIME = Decimal("0.01")


class ReglesFiscales(Protocol):
    """Les taux et seuils, chacun avec sa date et sa source, et la date du PEA."""

    impot_sur_le_revenu: ParametreDate
    prelevements_sociaux: ParametreDate
    pea_duree_exoneration_ir: ParametreDate
    crypto_seuil_exoneration: ParametreDate
    pea_premier_versement: Date | None


# --- Ce qu'une vente rapporterait, position par position ---------------------------------


@dataclass(frozen=True)
class Cession:
    """Une position vendue aujourd'hui, vue par le fisc."""

    position: Position
    valeur_brute: Decimal
    spread: Decimal
    frais_de_vente: Decimal

    @property
    def actif(self) -> str:
        return self.position.actif

    @property
    def poche(self) -> Poche:
        return self.position.poche

    @property
    def prix_de_cession(self) -> Decimal:
        """Ce que le marché paierait : la valeur brute moins l'écart de prix."""
        return self.valeur_brute - self.spread

    @property
    def cession_nette(self) -> Decimal:
        """Le prix de cession net des frais de cession, déductibles (CGI 150-0 D, 1)."""
        return self.prix_de_cession - self.frais_de_vente

    @property
    def capital_fiscal(self) -> Decimal:
        """Le prix d'acquisition au sens du CTO : frais d'achat inclus (D-57)."""
        return self.position.etat.capital_fiscal

    @property
    def capital_net_investi(self) -> Decimal:
        """Le prix d'acquisition au sens de la crypto : lecture prudente, sans les frais."""
        return self.position.etat.capital_net_investi

    def plus_value(self, poche: Poche) -> Decimal:
        """Cession nette − prix d'acquisition selon la règle de la poche."""
        acquisition = (
            self.capital_net_investi if poche is Poche.CRYPTO else self.capital_fiscal
        )
        return self.cession_nette - acquisition


@dataclass(frozen=True)
class ImpotEstime:
    """L'impôt d'une poche dans le scénario « tout vendre », et tout ce qu'il faut pour le
    refaire : les lignes, la base, le taux, la règle, les hypothèses."""

    poche: Poche
    regle: str
    """La règle appliquée, en une phrase."""

    cessions: tuple[Cession, ...]
    base_avant_plancher: Decimal | None
    """La somme des plus-values, pertes comprises : elle peut être négative."""

    base: Decimal | None
    """La base imposable : plancher à zéro, ou zéro sous un seuil d'exonération."""

    taux: Decimal | None
    """En pour cent, IR et prélèvements sociaux réunis."""

    impot: Decimal | None
    parametres: tuple[ParametreDate, ...]
    """Ceux qui ont servi, pour que le rapport les cite avec leur date et leur source."""

    hypotheses: tuple[str, ...]
    composantes: tuple[tuple[str, Decimal], ...] = ()
    """Pour le PEA : de quoi la base est faite, ligne par ligne."""

    hors_des_titres: Decimal = ZERO
    """La part de la base imposable qui n'est **pas** dans les titres détenus (PEA).

    Les plus-values réalisées et les dividendes du plan ont produit de l'argent, et cet argent
    est dans les **espèces du plan**, que l'application ne suit pas (D-11). Leur impôt, lui, est
    compté ici. La valeur réelle du PEA est donc **minorée** de ces liquidités, et le rapport
    doit le dire plutôt que de laisser croire à une perte."""

    motif: str | None = None
    """Pourquoi rien n'a été calculé, quand rien ne l'a été."""

    fiable: bool = True
    """Faux si une position repose sur une histoire incomplète (D-45)."""

    @property
    def calculable(self) -> bool:
        return self.impot is not None


LATENTES_BRUTES = "plus-values latentes, avant coûts de sortie"
COUTS_DE_SORTIE = "frais de vente et écart de prix estimés, en moins"
"""Les deux lignes qui rendent l'arithmétique visible.

La plus-value **après** coûts de sortie est le chiffre utile — c'est celle qui sera imposée — mais
elle ne se rapproche d'aucun chiffre de l'application de la banque. Montrer d'abord le brut, puis
ce qui en est retranché, permet de comparer la première ligne à ce que la banque affiche, et
d'attribuer l'écart à sa cause. Sans cela, une petite position dont le gain ne couvre pas l'euro
de frais de vente affiche une plus-value négative que rien n'explique."""


def _decomposition(cessions: Sequence[Cession], poche: Poche) -> tuple[Decimal, Decimal]:
    """La plus-value **avant** coûts de sortie, et ces coûts.

    Leur différence vaut exactement la somme des plus-values imposables : c'est la même
    soustraction, écrite en deux temps.
    """
    # Le PEA ne s'impose pas titre par titre : son gain est celui du plan, calculé sur ce qui
    # a été réellement placé. La crypto, elle, exclut les frais d'achat par lecture prudente
    # de la loi. Seul le CTO retient le prix de revient fiscal, frais d'achat compris (D-57).
    acquisition = (
        (lambda cession: cession.capital_fiscal)
        if poche is Poche.CTO
        else (lambda cession: cession.capital_net_investi)
    )
    brutes = sum(
        (cession.valeur_brute - acquisition(cession) for cession in cessions), ZERO
    )
    couts = sum(
        (cession.spread + cession.frais_de_vente for cession in cessions), ZERO
    )
    return brutes, couts


HYPOTHESES_COMMUNES = (
    "prélèvement forfaitaire unique de plein droit, sans option pour le barème",
    "taux en vigueur à la date de valorisation, vente supposée dans l'année en cours",
    "aucune moins-value reportée d'une année antérieure, aucune autre cession hors de cet "
    "export",
    "ce qui est déjà encaissé (dividendes, plus-values réalisées) n'est pas compté : ces impôts "
    "sont dus quoi qu'il arrive, ce ne sont pas des coûts de sortie",
)


def _taux_total(regles: ReglesFiscales) -> Decimal:
    return regles.impot_sur_le_revenu.valeur + regles.prelevements_sociaux.valeur


def _impot(base: Decimal, taux: Decimal) -> Decimal:
    return (base * taux / CENT).quantize(CENTIME, rounding=ROUND_HALF_UP)


def _fiable(positions: Iterable[Position]) -> bool:
    return not any(position.historique_incomplet for position in positions)


# --- CTO et crypto : par position, puis compensés --------------------------------------------


def impot_cto(cessions: Iterable[Cession], regles: ReglesFiscales) -> ImpotEstime:
    """Σ (cession nette − capital fiscal), gains et pertes compensés, plancher à zéro."""
    cessions = tuple(cession for cession in cessions if cession.poche is Poche.CTO)
    somme = sum((cession.plus_value(Poche.CTO) for cession in cessions), ZERO)
    base = max(somme, ZERO)
    taux = _taux_total(regles)
    brutes, couts_de_sortie = _decomposition(cessions, Poche.CTO)
    return ImpotEstime(
        poche=Poche.CTO,
        regle="plus-values de cession de valeurs mobilières : prix moyen pondéré frais d'achat "
        "inclus, frais de vente déduits, gains et pertes compensés ; impôt sur le revenu "
        f"{regles.impot_sur_le_revenu.en_clair} + prélèvements sociaux "
        f"{regles.prelevements_sociaux.en_clair}",
        cessions=cessions,
        base_avant_plancher=somme,
        base=base,
        taux=taux,
        impot=_impot(base, taux),
        parametres=(regles.impot_sur_le_revenu, regles.prelevements_sociaux),
        hypotheses=HYPOTHESES_COMMUNES
        + ("prix de revient fiscal = capital net investi + frais et taxes d'achat, au prorata "
           "des parts vendues (D-57)",),
        composantes=(
            (LATENTES_BRUTES, brutes),
            (COUTS_DE_SORTIE, -couts_de_sortie),
        ),
        fiable=_fiable(cession.position for cession in cessions),
    )


def cessions_crypto_de_l_annee(positions: Iterable[Position], date: Date) -> Decimal:
    """Ce qui a **déjà** été vendu en crypto dans l'année civile de `date`.

    Le seuil d'exonération de 305 € porte sur **toutes** les cessions de l'année, pas sur la
    seule vente qu'on simule : une vente de 200 € en mars et une de 200 € aujourd'hui font
    400 €, donc plus d'exonération. Ne regarder que la vente simulée annoncerait « exonéré »
    à tort — et c'est le genre d'erreur qui ne se voit pas, puisqu'elle donne zéro.
    """
    total = ZERO
    for position in positions:
        if position.poche is not Poche.CRYPTO:
            continue
        for ligne in position.journal:
            operation = ligne.operation
            if operation.type is not TypeOperation.VENTE:
                continue
            if operation.date.year != date.year:
                continue
            if operation.est_a_completer("montant_brut") or operation.montant_brut is None:
                continue
            total += operation.montant_brut
    return total


def impot_crypto(
    cessions: Iterable[Cession],
    regles: ReglesFiscales,
    deja_vendu_dans_l_annee: Decimal = ZERO,
) -> ImpotEstime:
    """Σ (cession nette − capital net investi), plancher à zéro ; rien sous le seuil.

    `deja_vendu_dans_l_annee` est le prix des cessions crypto **déjà réalisées** la même année :
    il entre dans le seuil d'exonération, mais **pas** dans la base imposable, les plus-values
    déjà réalisées étant hors de la valeur réelle (D-60).
    """
    cessions = tuple(cession for cession in cessions if cession.poche is Poche.CRYPTO)
    somme = sum((cession.plus_value(Poche.CRYPTO) for cession in cessions), ZERO)
    prix_de_cession = sum((cession.prix_de_cession for cession in cessions), ZERO)
    cessions_de_l_annee = prix_de_cession + deja_vendu_dans_l_annee
    brutes, couts_de_sortie = _decomposition(cessions, Poche.CRYPTO)
    seuil = regles.crypto_seuil_exoneration
    exonere = cessions_de_l_annee <= seuil.valeur
    base = ZERO if exonere else max(somme, ZERO)
    taux = _taux_total(regles)
    if exonere:
        regle = (
            f"cessions d'actifs numériques : {tableur.nombre_lisible(cessions_de_l_annee)} € "
            f"de cessions dans l'année, soit {seuil.en_clair} ou moins, donc exonéré "
            "(CGI 150 VH bis, II, B)"
        )
    else:
        regle = (
            "cessions d'actifs numériques (CGI 150 VH bis) : prix d'acquisition sans les frais, "
            f"frais de vente déduits, pertes compensées ; impôt sur le revenu "
            f"{regles.impot_sur_le_revenu.en_clair} + prélèvements sociaux "
            f"{regles.prelevements_sociaux.en_clair}"
        )
        if deja_vendu_dans_l_annee > ZERO:
            deja = tableur.nombre_lisible(deja_vendu_dans_l_annee)
            regle += (
                f". Les {deja} € déjà vendus cette année comptent dans le seuil "
                f"de {seuil.en_clair}, mais pas dans la base (D-60)"
            )
    return ImpotEstime(
        poche=Poche.CRYPTO,
        regle=regle,
        cessions=cessions,
        base_avant_plancher=somme,
        base=base,
        taux=taux,
        impot=_impot(base, taux),
        parametres=(regles.impot_sur_le_revenu, regles.prelevements_sociaux, seuil),
        hypotheses=HYPOTHESES_COMMUNES
        + (
            "tout le portefeuille de crypto-actifs est chez Trade Republic (la loi compte "
            "toutes les plateformes, et toutes les cessions de l'année)",
            "après une vente partielle passée, le prix d'acquisition est réduit au prorata des "
            "parts, et non de la valeur comme le veut la loi : identique tant qu'il n'y a pas eu "
            "de vente partielle",
            "les frais d'achat n'entrent pas dans le prix d'acquisition (lecture prudente de la "
            "loi, qui ne les nomme pas)",
        ),
        composantes=(
            (LATENTES_BRUTES, brutes),
            (COUTS_DE_SORTIE, -couts_de_sortie),
        ),
        fiable=_fiable(cession.position for cession in cessions),
    )


# --- PEA : le gain du plan -------------------------------------------------------------------


HYPOTHESES_PEA = (
    "aucun retrait n'a jamais été fait sur le plan",
    "les espèces du plan ne portent ni intérêt ni frais",
    "tout mouvement d'espèces est un versement ou la contrepartie d'une opération sur titres "
    "connue (pas de transfert de PEA : l'histoire d'avant manquerait)",
)


def anniversaire(depuis: Date, annees: int) -> Date:
    """La date à laquelle `annees` années révolues sont atteintes. Un 29 février compte pour
    le 1er mars des années sans."""
    try:
        return depuis.replace(year=depuis.year + annees)
    except ValueError:
        return Date(depuis.year + annees, 3, 1)


def impot_pea(
    cessions: Iterable[Cession],
    positions_pea: Iterable[Position],
    date: Date,
    regles: ReglesFiscales,
    motif: str | None = None,
) -> ImpotEstime:
    """Le gain du plan, approché par les seuls titres (D-59, `docs/couts-et-fiscalite.md`
    §5.3) :

    ```
    gain du plan = Σ (cession nette − capital net investi)    plus-values latentes, après
                                                              frais de vente et spread
                 + Σ plus-values réalisées brutes
                 + Σ dividendes bruts
                 − Σ frais − Σ taxes                          tous les coûts payés dans le PEA
    ```

    `positions_pea` réunit **toutes** les positions du PEA, soldées comprises : leurs
    plus-values réalisées et leurs frais font partie du gain du plan. `motif`, s'il est donné,
    dit pourquoi rien ne peut être calculé (une position sans cours, par exemple).
    """
    cessions = tuple(cession for cession in cessions if cession.poche is Poche.PEA)
    positions = [position for position in positions_pea if position.poche is Poche.PEA]

    def rien(pourquoi: str) -> ImpotEstime:
        return ImpotEstime(
            poche=Poche.PEA,
            regle="gain du plan : valeur liquidative moins versements",
            cessions=cessions,
            base_avant_plancher=None,
            base=None,
            taux=None,
            impot=None,
            parametres=(),
            hypotheses=HYPOTHESES_COMMUNES + HYPOTHESES_PEA,
            motif=pourquoi,
            fiable=_fiable(positions),
        )

    if motif is not None:
        return rien(motif)
    if regles.pea_premier_versement is None:
        return rien(
            "date du premier versement sur le PEA non déclarée : l'ancienneté du plan décide du "
            "taux. Écrivez-la dans fiscalite.toml (dossier de configuration), section [pea]"
        )

    brutes, couts_de_sortie = _decomposition(cessions, Poche.PEA)
    latentes = brutes - couts_de_sortie
    realisees = sum((position.plus_values_realisees_brutes for position in positions), ZERO)
    dividendes = sum((position.dividendes_bruts for position in positions), ZERO)
    couts = sum((position.frais + position.taxes for position in positions), ZERO)
    gain = latentes + realisees + dividendes - couts
    base = max(gain, ZERO)

    duree = int(regles.pea_duree_exoneration_ir.valeur)
    exonere_ir = date >= anniversaire(regles.pea_premier_versement, duree)
    if exonere_ir:
        taux = regles.prelevements_sociaux.valeur
        regle = (
            f"PEA de {duree} ans ou plus (premier versement le "
            f"{regles.pea_premier_versement.isoformat()}) : exonéré d'impôt sur le revenu, "
            f"prélèvements sociaux {regles.prelevements_sociaux.en_clair} sur le gain du plan"
        )
        parametres: tuple[ParametreDate, ...] = (
            regles.prelevements_sociaux,
            regles.pea_duree_exoneration_ir,
        )
    else:
        taux = _taux_total(regles)
        regle = (
            f"PEA de moins de {duree} ans (premier versement le "
            f"{regles.pea_premier_versement.isoformat()}) : retirer clôt le plan ; impôt sur "
            f"le revenu {regles.impot_sur_le_revenu.en_clair} + prélèvements sociaux "
            f"{regles.prelevements_sociaux.en_clair} sur le gain du plan"
        )
        parametres = (
            regles.impot_sur_le_revenu,
            regles.prelevements_sociaux,
            regles.pea_duree_exoneration_ir,
        )

    return ImpotEstime(
        poche=Poche.PEA,
        regle=regle,
        cessions=cessions,
        base_avant_plancher=gain,
        base=base,
        taux=taux,
        impot=_impot(base, taux),
        parametres=parametres,
        hypotheses=HYPOTHESES_COMMUNES + HYPOTHESES_PEA,
        # Ce que le plan a déjà transformé en espèces : son impôt est compté, son argent non.
        hors_des_titres=max(realisees + dividendes - couts, ZERO),
        composantes=(
            (LATENTES_BRUTES, brutes),
            (COUTS_DE_SORTIE, -couts_de_sortie),
            ("plus-values réalisées (brut), positions soldées comprises", realisees),
            ("dividendes reçus (brut)", dividendes),
            ("frais et taxes payés dans le PEA, en moins", -couts),
        ),
        fiable=_fiable(positions),
    )


def impots_estimes(
    cessions: Iterable[Cession],
    portefeuille: Portefeuille,
    date: Date,
    regles: ReglesFiscales,
    motif_pea: str | None = None,
) -> dict[Poche, ImpotEstime]:
    """L'impôt de chaque poche présente dans le portefeuille, dans l'ordre PEA, CTO, crypto."""
    cessions = tuple(cessions)
    poches = {position.poche for position in portefeuille.positions}
    resultat: dict[Poche, ImpotEstime] = {}
    for poche in Poche:
        if poche not in poches:
            continue
        if poche is Poche.PEA:
            resultat[poche] = impot_pea(
                cessions, portefeuille.positions, date, regles, motif=motif_pea
            )
        elif poche is Poche.CTO:
            resultat[poche] = impot_cto(cessions, regles)
        else:
            resultat[poche] = impot_crypto(
                cessions,
                regles,
                cessions_crypto_de_l_annee(portefeuille.positions, date),
            )
    return resultat
