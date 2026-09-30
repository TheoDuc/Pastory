"""Les trois chiffres clés (D-22) : le gain en euros, le TRI et le TWRR.

Tout est en **montants bruts** : ni les frais ni les taxes n'y entrent (D-21), et les
dividendes comptent en brut (D-29). Les définitions sont dans le glossaire (§4 et §5) ; ce
module les écrit dans l'ordre où on les refait dans un tableur.

Les **flux** sont les mouvements d'argent entre les espèces (hors périmètre) et les actifs,
vus par l'investisseur : ce qu'il met est négatif, ce qu'il reçoit est positif. Le format
pivot dit lequel est lequel (format-pivot §3) :

| Type | Flux |
|---|---|
| `achat`, `titres_recus` | **négatif** : de l'argent entre dans l'actif |
| `vente`, `dividende`, `distribution_capital` | **positif** : de l'argent en sort |

Trois chiffres, une même période `[début, fin]` :

```
gain = V_fin − V_début + Σ flux
TRI  = le taux r qui annule
       −V_début + Σ F_k / (1+r)^((t_k − t_0)/365) + V_fin / (1+r)^((T − t_0)/365)
TWRR = Π (V_fin,i / V_début,i) − 1, une sous-période par jour de flux
```

Ce que ce module refuse de faire, et dit (D-45) : calculer sur un flux dont le montant brut
attend encore un cours, ou sur une valeur qu'aucun cours ne permet d'établir. Les positions
sans cours à la date de fin sortent des totaux, qui sont alors marqués **partiels** (D-53).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date as Date
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.position import Position
from pastory.moteur.valorisation import (
    PositionValorisee,
    SourceDeValorisation,
    Valorisation,
    valoriser,
    valoriser_position,
    valoriser_positions,
)
from pastory.pivot.operation import Poche, TypeOperation

ZERO = Decimal("0.00")
UN = Decimal("1")
UN_JOUR = timedelta(days=1)

JOURS_PAR_AN = Decimal("365")
"""La convention du glossaire, et celle de `TRI.PAIEMENTS` (XIRR) dans un tableur."""

UN_AN = 365
"""En jours. En dessous, un taux annuel ne dit pas grand-chose (glossaire §5)."""

PAS_DU_TAUX = Decimal("0.000001")
"""Six décimales pour un taux : 0,0001 %. Un TRI est le résultat d'une recherche, pas un
montant reçu ; il faut bien l'arrêter quelque part, et un tableur affiche moins que ça."""

TAUX_PLANCHER = Decimal("-0.99")
TAUX_PLAFOND = Decimal("1000")
"""Entre −99 % et +100 000 % par an. Ce sont des bornes de calcul, pas un jugement : un gain
de 20 % en un mois fait plus de 700 % par an, et un tableur l'afficherait tel quel. C'est le
drapeau « peu significatif » qui dit qu'un taux annuel n'a pas de sens sur trois mois."""

PRECISION_DICHOTOMIE = Decimal("0.0000000001")

SENS_POUR_L_INVESTISSEUR: dict[TypeOperation, Decimal] = {
    TypeOperation.ACHAT: Decimal("-1"),
    TypeOperation.TITRES_RECUS: Decimal("-1"),
    TypeOperation.VENTE: Decimal("1"),
    TypeOperation.DIVIDENDE: Decimal("1"),
    TypeOperation.DISTRIBUTION_CAPITAL: Decimal("1"),
}
"""Le signe de chaque type, vu par l'investisseur (format-pivot §3)."""


# --- La période ----------------------------------------------------------------------


@dataclass(frozen=True)
class Periode:
    """`[début, fin]`, bornes comprises. Sans début : depuis la première opération.

    `V_début` est la valeur **au soir de la veille** du début : les flux du jour de début
    sont dans la période. `V_fin` est la valeur au soir de la fin.
    """

    fin: Date
    debut: Date | None = None

    def __post_init__(self) -> None:
        if self.debut is not None and self.debut > self.fin:
            raise ValueError(
                f"période impossible : le début ({self.debut.isoformat()}) est après la fin "
                f"({self.fin.isoformat()})"
            )

    @property
    def veille(self) -> Date | None:
        """Le jour dont la clôture donne `V_début`. `None` quand on part du début."""
        return None if self.debut is None else self.debut - UN_JOUR

    @property
    def depuis_le_debut(self) -> bool:
        return self.debut is None

    def contient(self, jour: Date) -> bool:
        return (self.debut is None or self.debut <= jour) and jour <= self.fin


# --- Les flux ------------------------------------------------------------------------


@dataclass(frozen=True)
class Flux:
    """Un mouvement d'argent entre les espèces et un actif, vu par l'investisseur."""

    date: Date
    montant: Decimal
    """Signé : négatif pour un achat, positif pour ce qui est reçu. C'est la colonne qu'on
    colle dans `TRI.PAIEMENTS`."""

    type: TypeOperation
    actif: str
    poche: Poche
    identifiant: str

    @property
    def montant_brut(self) -> Decimal:
        return abs(self.montant)


@dataclass(frozen=True)
class LigneDuTri:
    """Une ligne de la table du TRI : une date, un montant signé, et ce que c'est."""

    date: Date
    montant: Decimal
    libelle: str
    """`valeur au début`, le type de l'opération, ou `valeur à la fin`."""

    flux: Flux | None = None
    """Le flux d'origine, quand la ligne en est un."""


class NonCalculable(Exception):
    """Un chiffre n'a pas de sens avec ce qu'on sait. Le motif est fait pour être lu."""


def flux_de(position: Position, periode: Periode) -> list[Flux]:
    """Les flux d'une position sur la période, dans l'ordre du journal.

    Lève `NonCalculable` si un montant brut de la période attend encore un cours (D-15) : on
    ne connaît pas ce qui a été mis, donc on ne sait pas ce que ça a rapporté (D-45).
    """
    flux: list[Flux] = []
    for ligne in position.journal:
        operation = ligne.operation
        if not periode.contient(operation.date):
            continue
        if operation.est_a_completer("montant_brut") or operation.montant_brut is None:
            raise NonCalculable(
                f"le montant brut de l'opération du {operation.date.isoformat()} sur "
                f"{operation.actif} n'est pas connu : lancez « pastory cours »"
            )
        flux.append(
            Flux(
                date=operation.date,
                montant=SENS_POUR_L_INVESTISSEUR[operation.type] * operation.montant_brut,
                type=operation.type,
                actif=operation.actif,
                poche=operation.poche,
                identifiant=operation.identifiant,
            )
        )
    return flux


# --- Le TRI --------------------------------------------------------------------------


def valeur_actuelle_nette(
    taux: Decimal, flux: Sequence[tuple[Date, Decimal]], origine: Date
) -> Decimal:
    """`Σ montant / (1 + taux)^(jours depuis l'origine / 365)` : la formule d'`XIRR`."""
    facteur = UN + taux
    total = Decimal("0")
    for jour, montant in flux:
        exposant = Decimal((jour - origine).days) / JOURS_PAR_AN
        total += montant / facteur**exposant
    return total


def tri(flux: Sequence[tuple[Date, Decimal]]) -> Decimal | None:
    """Le taux annuel qui annule la valeur actuelle nette des flux, par dichotomie.

    `None` s'il n'y en a pas : il faut au moins un montant négatif et un positif, et la
    fonction doit changer de signe entre −99 % et +1 000 %. Un tableur rendrait une erreur
    au même endroit ; ici, c'est un `None` que le rapport explique.
    """
    montants = [montant for _, montant in flux]
    if not any(montant < 0 for montant in montants) or not any(montant > 0 for montant in montants):
        return None

    origine = min(jour for jour, _ in flux)
    bas, haut = TAUX_PLANCHER, TAUX_PLAFOND
    van_bas = valeur_actuelle_nette(bas, flux, origine)
    van_haut = valeur_actuelle_nette(haut, flux, origine)
    if van_bas == 0:
        return bas
    if van_haut == 0:
        return haut
    if (van_bas < 0) == (van_haut < 0):
        return None

    milieu = (bas + haut) / 2
    while haut - bas > PRECISION_DICHOTOMIE:
        milieu = (bas + haut) / 2
        van_milieu = valeur_actuelle_nette(milieu, flux, origine)
        if van_milieu == 0:
            break
        if (van_milieu < 0) == (van_bas < 0):
            bas, van_bas = milieu, van_milieu
        else:
            haut = milieu
    return milieu.quantize(PAS_DU_TAUX, rounding=ROUND_HALF_UP)


# --- Le TWRR -------------------------------------------------------------------------


@dataclass(frozen=True)
class SousPeriode:
    """Un morceau de la période entre deux jours de flux, et son rendement.

    La valeur **après** un flux est prise aux cours de clôture du jour : parts détenues après
    l'opération × cours du jour. Pas au prix d'exécution : une vente exécutée quelques
    centimes au-dessus de la clôture n'a pas à inventer un rendement, et une vente totale
    doit laisser une valeur nulle, pas négative. Le flux est là pour comprendre, pas pour
    calculer.
    """

    du: Date
    """Le jour de flux qui ouvre la sous-période (ou la veille du début de la période)."""

    au: Date
    """Le jour de flux qui la ferme (ou la fin de la période)."""

    valeur_debut: Decimal
    """Parts détenues **après** les flux du jour `du` × cours de clôture de ce jour."""

    flux: Decimal
    """Les flux du jour `du`, vus du portefeuille (achats positifs). Pour information."""

    valeur_fin: Decimal
    """Parts détenues **avant** les flux du jour `au` × cours de clôture de ce jour."""

    @property
    def rendement(self) -> Decimal | None:
        """`valeur_fin / valeur_début − 1`, ou `None` si rien n'était détenu."""
        if self.valeur_debut == 0:
            return None
        return self.valeur_fin / self.valeur_debut - UN

    @property
    def vide(self) -> bool:
        """Rien détenu d'un bout à l'autre : la sous-période ne compte pas."""
        return self.valeur_debut == 0 and self.valeur_fin == 0


@dataclass(frozen=True)
class Twrr:
    taux: Decimal | None
    """Sur la période entière, non annualisé."""

    annualise: Decimal | None
    """`(1 + taux)^(365 / jours) − 1`, seulement si la période dépasse un an."""

    sous_periodes: tuple[SousPeriode, ...]
    """La pièce à ouvrir pour refaire le calcul : le produit des `(1 + rendement)`."""

    motif: str | None = None
    """Pourquoi il n'y a pas de taux, quand il n'y en a pas."""


def enchainer(sous_periodes: Iterable[SousPeriode]) -> Decimal | None:
    """`Π (1 + r_i) − 1`. Les sous-périodes vides sont ignorées ; une sous-période qui part
    de zéro et arrive ailleurs n'a pas de sens, et rend `None`."""
    produit = UN
    for sous_periode in sous_periodes:
        if sous_periode.vide:
            continue
        rendement = sous_periode.rendement
        if rendement is None:
            return None
        produit *= UN + rendement
    return (produit - UN).quantize(PAS_DU_TAUX, rounding=ROUND_HALF_UP)


def annualiser(taux: Decimal, jours: int) -> Decimal | None:
    """Le même taux ramené à un an, seulement si la période dépasse un an (glossaire §5)."""
    if jours <= UN_AN or taux <= -UN:
        return None
    annuel = (UN + taux) ** (JOURS_PAR_AN / Decimal(jours)) - UN
    return annuel.quantize(PAS_DU_TAUX, rounding=ROUND_HALF_UP)


# --- Les rendements d'un groupe de positions ---------------------------------------------


@dataclass(frozen=True)
class Rendements:
    """Les trois chiffres clés d'un groupe de positions — un actif, une poche, le tout."""

    periode: Periode
    positions: tuple[Position, ...]
    """Les positions retenues, coupées à la fin de la période."""

    exclues: tuple[PositionValorisee, ...]
    """Détenues à la fin mais sans cours : elles ne comptent dans aucun chiffre (D-53)."""

    valeur_debut: Decimal | None
    """`None` quand un cours manquait pour l'établir : gain et TRI sont alors sans objet."""

    valeur_fin: Decimal
    flux: tuple[Flux, ...]
    gain: Decimal | None
    tri: Decimal | None
    twrr: Twrr
    motif: str | None = None
    """Pourquoi le gain et le TRI manquent, quand ils manquent."""

    motif_tri: str | None = None
    """Pourquoi le TRI seul manque, alors que le gain existe."""

    # --- Ce qui se lit directement --------------------------------------------

    @property
    def calculable(self) -> bool:
        return self.gain is not None

    @property
    def partiel(self) -> bool:
        return bool(self.exclues)

    @property
    def fiable(self) -> bool:
        """Faux si la quantité d'une position retenue repose sur une histoire trouée (D-45).

        Un prix encore à compléter ne rend pas le chiffre infidèle par lui-même : soit il
        tombe dans la période, et le calcul est refusé ; soit il la précède, et les parts sont
        bien là, valorisées au début comme à la fin.
        """
        return not any(
            position.etat.stock_insuffisant or position.etat.distribution_excedentaire
            for position in self.positions
        )

    @property
    def origine(self) -> Date | None:
        """Le premier jour daté du calcul : la veille du début si quelque chose était
        détenu, sinon le premier flux."""
        if self.valeur_debut and self.periode.veille is not None:
            return self.periode.veille
        if self.flux:
            return min(flux.date for flux in self.flux)
        return None

    @property
    def duree_jours(self) -> int | None:
        origine = self.origine
        return None if origine is None else (self.periode.fin - origine).days

    @property
    def peu_significatif(self) -> bool:
        """TRI et TWRR sur moins d'un an ne disent pas grand-chose (glossaire §5, D-22)."""
        duree = self.duree_jours
        return duree is None or duree < UN_AN

    def total_des(self, *types: TypeOperation) -> Decimal:
        return sum((flux.montant_brut for flux in self.flux if flux.type in types), ZERO)

    @property
    def achats(self) -> Decimal:
        """Achats et titres reçus : tout ce qui est entré dans les actifs sur la période."""
        return self.total_des(TypeOperation.ACHAT, TypeOperation.TITRES_RECUS)

    @property
    def ventes(self) -> Decimal:
        return self.total_des(TypeOperation.VENTE)

    @property
    def dividendes(self) -> Decimal:
        return self.total_des(TypeOperation.DIVIDENDE)

    @property
    def distributions(self) -> Decimal:
        return self.total_des(TypeOperation.DISTRIBUTION_CAPITAL)

    @property
    def table_du_tri(self) -> list[LigneDuTri]:
        """La table à coller dans un tableur : dates et montants signés, `−V_début` et
        `+V_fin` compris. `TRI.PAIEMENTS(montants ; dates)` doit redonner le TRI.

        C'est **la** table : le TRI est calculé dessus, et `flux.csv` l'écrit telle quelle.
        Les deux ne peuvent donc pas diverger.
        """
        table: list[LigneDuTri] = []
        if self.valeur_debut and self.periode.veille is not None:
            table.append(LigneDuTri(self.periode.veille, -self.valeur_debut, "valeur au début"))
        table += [
            LigneDuTri(flux.date, flux.montant, flux.type.value, flux) for flux in self.flux
        ]
        if self.valeur_fin:
            table.append(LigneDuTri(self.periode.fin, self.valeur_fin, "valeur à la fin"))
        return table

    @property
    def flux_dates(self) -> list[tuple[Date, Decimal]]:
        """La même table, réduite à ce que `tri()` consomme."""
        return [(ligne.date, ligne.montant) for ligne in self.table_du_tri]


def _valeur(
    positions: Iterable[Position],
    jour_des_parts: Date,
    jour_du_cours: Date,
    source: SourceDeValorisation,
) -> Decimal:
    """Parts détenues à la fin de `jour_des_parts` × cours de clôture de `jour_du_cours`.

    Un cours n'est demandé que s'il y a des parts : avant le premier achat, la valeur est
    zéro sans qu'aucune source n'ait à répondre. La multiplication et ses garde-fous (devise,
    arrondi) sont ceux de `valoriser_position` : une seule façon de valoriser dans le moteur.
    """
    total = ZERO
    for position in positions:
        coupee = position.jusqu_au(jour_des_parts)
        if not coupee.etat.detenue:
            continue
        valorisee = valoriser_position(coupee, jour_du_cours, source)
        if valorisee.valeur is None:
            raise NonCalculable(
                f"{position.actif} au {jour_du_cours.isoformat()} : {valorisee.motif}"
            )
        total += valorisee.valeur
    return total


def _valeur_debut(
    positions: Iterable[Position], periode: Periode, source: SourceDeValorisation
) -> Decimal:
    veille = periode.veille
    if veille is None:
        return ZERO
    return _valeur(positions, veille, veille, source)


def _twrr(
    positions: Sequence[Position],
    periode: Periode,
    flux: Sequence[Flux],
    valeur_debut: Decimal,
    valeur_fin: Decimal,
    source: SourceDeValorisation,
) -> Twrr:
    """Découpe la période à chaque jour de flux et enchaîne les sous-périodes."""
    jours = sorted({un_flux.date for un_flux in flux})
    flux_du_jour = {
        jour: -sum((un_flux.montant for un_flux in flux if un_flux.date == jour), ZERO)
        for jour in jours
    }

    def valeur_avant(jour: Date) -> Decimal:
        return _valeur(positions, jour - UN_JOUR, jour, source)

    def valeur_apres(jour: Date) -> Decimal:
        return _valeur(positions, jour, jour, source)

    sous_periodes: list[SousPeriode] = []
    try:
        if valeur_debut > 0:
            assert periode.veille is not None
            sous_periodes.append(
                SousPeriode(
                    du=periode.veille,
                    au=jours[0] if jours else periode.fin,
                    valeur_debut=valeur_debut,
                    flux=ZERO,
                    valeur_fin=valeur_avant(jours[0]) if jours else valeur_fin,
                )
            )
        for rang, jour in enumerate(jours):
            suivant = jours[rang + 1] if rang + 1 < len(jours) else None
            sous_periodes.append(
                SousPeriode(
                    du=jour,
                    au=suivant or periode.fin,
                    valeur_debut=valeur_apres(jour) if jour < periode.fin else valeur_fin,
                    flux=flux_du_jour[jour],
                    valeur_fin=valeur_avant(suivant) if suivant else valeur_fin,
                )
            )
    except NonCalculable as erreur:
        return Twrr(None, None, tuple(sous_periodes), motif=str(erreur))

    if not sous_periodes:
        return Twrr(None, None, (), motif="aucune opération sur la période")

    taux = enchainer(sous_periodes)
    if taux is None:
        return Twrr(
            None,
            None,
            tuple(sous_periodes),
            motif="une sous-période part d'une valeur nulle et n'y revient pas",
        )
    origine = sous_periodes[0].du
    return Twrr(taux, annualiser(taux, (periode.fin - origine).days), tuple(sous_periodes))


def rendements(
    positions: Iterable[Position], periode: Periode, source: SourceDeValorisation
) -> Rendements:
    """Les trois chiffres clés d'un groupe de positions sur une période.

    Dans l'ordre où on les refait : la valeur à la fin (et qui n'en a pas), les flux, la
    valeur au début, puis le gain, le TRI et le TWRR.
    """
    coupees = [position.jusqu_au(periode.fin) for position in positions]
    coupees = [position for position in coupees if position.journal]

    valorisees = valoriser_positions(coupees, periode.fin, source)
    exclues = tuple(position for position in valorisees if not position.valorisee)
    a_exclure = {(position.actif, position.poche) for position in exclues}
    retenues = tuple(
        position for position in coupees if (position.actif, position.poche) not in a_exclure
    )
    valeur_fin = sum(
        (position.valeur or ZERO for position in valorisees if position.valorisee), ZERO
    )

    def sans_chiffres(motif: str, flux: tuple[Flux, ...] = ()) -> Rendements:
        return Rendements(
            periode=periode,
            positions=retenues,
            exclues=exclues,
            valeur_debut=None,
            valeur_fin=valeur_fin,
            flux=flux,
            gain=None,
            tri=None,
            twrr=Twrr(None, None, (), motif=motif),
            motif=motif,
        )

    if exclues and not retenues:
        return sans_chiffres("aucune des positions détenues n'est valorisée")

    try:
        flux = tuple(
            un_flux for position in retenues for un_flux in flux_de(position, periode)
        )
        flux = tuple(sorted(flux, key=lambda un_flux: (un_flux.date, un_flux.identifiant)))
        valeur_debut = _valeur_debut(retenues, periode, source)
    except NonCalculable as erreur:
        return sans_chiffres(str(erreur))

    if not flux and valeur_debut == 0:
        return sans_chiffres("aucune opération sur la période")

    gain = valeur_fin - valeur_debut + sum((un_flux.montant for un_flux in flux), ZERO)
    resultat = Rendements(
        periode=periode,
        positions=retenues,
        exclues=exclues,
        valeur_debut=valeur_debut,
        valeur_fin=valeur_fin,
        flux=flux,
        gain=gain,
        tri=None,
        twrr=_twrr(retenues, periode, flux, valeur_debut, valeur_fin, source),
    )
    # Le TRI part de la même table que celle que le tableur recevra : `flux_dates`.
    taux = tri(resultat.flux_dates)
    motif_tri = None
    if taux is None:
        motif_tri = (
            "aucun taux annuel entre -99 % et +100 000 % n'annule les flux : soit ils sont "
            "tous du même signe, soit le résultat est hors de toute mesure"
        )
    return replace(resultat, tri=taux, motif_tri=motif_tri)


# --- Le portefeuille entier : total, par poche, par position ------------------------------


@dataclass(frozen=True)
class Synthese:
    """La valorisation à la fin de la période, et les rendements à tous les niveaux."""

    periode: Periode
    valorisation: Valorisation
    total: Rendements
    par_poche: dict[Poche, Rendements]
    par_position: dict[tuple[str, Poche], Rendements]

    def de(self, position: Position) -> Rendements | None:
        return self.par_position.get((position.actif, position.poche))


def synthese(
    portefeuille: Portefeuille, periode: Periode, source: SourceDeValorisation
) -> Synthese:
    """Tout ce que le rapport et les CSV montrent, calculé une fois."""
    valorisation = valoriser(portefeuille, periode.fin, source)
    groupes: dict[Poche, list[Position]] = {}
    for position in portefeuille.positions:
        groupes.setdefault(position.poche, []).append(position)

    return Synthese(
        periode=periode,
        valorisation=valorisation,
        total=rendements(portefeuille.positions, periode, source),
        par_poche={
            poche: rendements(groupes[poche], periode, source)
            for poche in Poche
            if poche in groupes
        },
        par_position={
            (position.actif, position.poche): rendements([position], periode, source)
            for position in portefeuille.positions
        },
    )
