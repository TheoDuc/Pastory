"""La répartition du portefeuille : par classe d'actifs, par pays, par secteur (D-66 à D-69).

C'est la **quatrième** donnée extérieure qui entre dans le moteur, et elle entre comme les trois
premières : **par la porte**. Ce module déclare ce dont il a besoin — une source de compositions,
et des référentiels pour nommer les codes — et c'est `cli.py` qui lui passe des objets qui savent
répondre. Le moteur ne sait pas ce qu'est extraETF, ni un fichier TOML, ni ce qu'est un ETF : il
demande la composition d'un actif et le nom d'un code.

**Comment un euro est rangé**, et c'est tout le fichier. Pour chaque position valorisée :

```
valeur de la position  =  part actions  +  part non-actions
part actions           =  ce que la composition attribue  +  non attribué
```

- la **part non-actions** (obligations, liquidités d'un fonds) est mise **hors périmètre** de la
  géographie et des secteurs : là, « pays » peut vouloir dire devise d'émission et « secteur »
  veut dire Trésor ou entreprises (D-68). On ne force pas une grandeur dans une catégorie où elle
  n'a pas de sens, exactement comme les espèces ne sont pas suivies (D-11) ;
- le **non attribué** est ce que la composition laisse de côté : liquidités, dérivés, lignes non
  classées. Aucune composition ne somme à 100 %, et **rien n'est renormalisé** (D-69) ;
- un actif **sans composition** est **non couvert**, avec son montant, et les totaux sont marqués
  partiels (D-53) ;
- une **crypto** est **hors classification** : elle n'a ni pays ni secteur, et ce n'est pas une
  donnée manquante (D-68).

Aucun pourcentage n'est rapporté à la somme des poids : tous le sont à la **valeur totale des
actifs valorisés**. C'est ce qui rend la lecture honnête — si un tiers du portefeuille n'est pas
couvert, le camembert ne fait pas 100 %, et cela se voit.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Protocol

from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.moteur.valorisation import PositionValorisee, Valorisation
from dashboard_tr.pivot.operation import Poche

CENTIME = Decimal("0.01")
CENT = Decimal("100")
ZERO = Decimal("0.00")

CATEGORIE_ECART = "répartition au-delà de la part en actions"
"""La catégorie du seul signalement que ce module produit, pour que le rapport le regroupe."""

ECART_TOLERE = Decimal("1.00")
"""Écart en euros au-delà duquel une incohérence de composition est signalée.

En dessous, c'est de l'arrondi : une composition donne ses poids à deux décimales, et 0,01 % d'un
portefeuille se perd en centimes.
"""


class Rubrique(StrEnum):
    """Les trois répartitions, qui ne se mélangent jamais (D-68)."""

    CLASSE = "classe"
    PAYS = "pays"
    SECTEUR = "secteur"


# --- Ce que le moteur attend du dehors -------------------------------------------------


class PartDeComposition(Protocol):
    """Un poste d'une composition : un code, et son pourcentage."""

    code: str
    pour_cent: Decimal


class CompositionDUnActif(Protocol):
    """Ce qu'il y a dans un actif. `donnees_externes.composition.Composition` a cette forme."""

    pays: Sequence[PartDeComposition]
    secteurs: Sequence[PartDeComposition]
    classes: Sequence[PartDeComposition]
    arrete_le: Date
    intitule_de_la_date: str
    source: str
    replication: str | None


class SourceDeComposition(Protocol):
    """Qui sait donner la composition d'un actif. Une seule méthode.

    `None` veut dire « pas de composition utilisable », et celui qui répond a gardé le motif
    quelque part. Le moteur constate et le dit.
    """

    def composition(self, actif: str) -> CompositionDUnActif | None: ...


class Nomme(Protocol):
    """Un code, et le nom qu'on affiche à sa place."""

    libelle: str


class ZoneNommee(Protocol):
    cle: str
    libelle: str
    rang: int


class ClasseNommee(Protocol):
    cle: str
    libelle: str
    rang: int
    actions: bool
    """Vrai pour la poche d'actions : la seule que la géographie et les secteurs décrivent."""


class Referentiels(Protocol):
    """Qui sait nommer un code. `parametres.referentiels.Referentiels` a cette forme."""

    def secteur(self, code: str) -> Nomme | None: ...

    def pays(self, code: str) -> Nomme | None: ...

    def zone_de(self, code_pays: str) -> ZoneNommee: ...

    def classe(self, code: str) -> ClasseNommee | None: ...


# --- Ce que le moteur produit ----------------------------------------------------------


@dataclass(frozen=True)
class Poste:
    """Une ligne d'une répartition : un pays, un secteur ou une classe d'actifs."""

    code: str
    """Le code tel qu'il sert au calcul. Affiché quand le libellé manque."""

    libelle: str
    montant: Decimal
    """En euros. C'est le chiffre refaisable à la main ; le pourcentage s'en déduit."""

    reconnu: bool = True
    """Faux si le référentiel ne connaît pas ce code. Le poste est **affiché quand même**, avec
    son code : jamais rangé dans « autres » (règle 5 de `CLAUDE.md`)."""

    zone: str | None = None
    """La zone du pays, pour le regroupement. `None` hors de la rubrique « pays »."""

    zone_libelle: str | None = None
    zone_rang: int | None = None
    rang: int | None = None
    """L'ordre voulu par le référentiel, pour les classes d'actifs."""


@dataclass(frozen=True)
class Repartition:
    """Une répartition complète, et tout ce qui n'y entre pas.

    Les quatre montants hors postes ne sont pas des détails : ce sont eux qui empêchent de croire
    qu'un camembert décrit tout le portefeuille.
    """

    rubrique: Rubrique
    postes: tuple[Poste, ...]
    base: Decimal
    """La valeur totale des actifs valorisés. Le dénominateur de tous les pourcentages."""

    non_attribue: Decimal = ZERO
    """Part actions que la composition n'attribue à rien (D-69)."""

    hors_perimetre: Decimal = ZERO
    """Part non-actions des fonds : obligations, liquidités (D-68)."""

    hors_classification: Decimal = ZERO
    """Crypto : ni pays ni secteur, et ce n'est pas un manque (D-68)."""

    non_couvert: Decimal = ZERO
    """Actifs sans composition du tout (D-69). C'est lui qui rend les totaux partiels."""

    actifs_non_couverts: tuple[str, ...] = ()
    actifs_synthetiques: tuple[str, ...] = ()
    """Les fonds dont la répartition est celle de l'**indice** et non des titres détenus (D-64)."""

    @property
    def attribue(self) -> Decimal:
        return sum((poste.montant for poste in self.postes), ZERO)

    @property
    def complete(self) -> bool:
        """Vrai si tout le portefeuille est décrit : rien de non couvert, rien de non attribué."""
        return self.non_couvert == ZERO and self.non_attribue == ZERO

    @property
    def postes_non_reconnus(self) -> tuple[Poste, ...]:
        return tuple(poste for poste in self.postes if not poste.reconnu)

    def pour_cent(self, montant: Decimal) -> Decimal | None:
        """Un montant en pour cent de la **valeur totale**, jamais de la somme des postes."""
        if self.base <= ZERO:
            return None
        return (montant * CENT / self.base).quantize(CENTIME, rounding=ROUND_HALF_UP)

    def par_zone(self) -> tuple[tuple[ZoneNommee | None, Decimal, tuple[Poste, ...]], ...]:
        """Les postes regroupés par zone, dans l'ordre des rangs (rubrique « pays »).

        Le regroupement n'est pas une donnée mais une convention, et le référentiel l'a déjà
        tranché : ici, on ne fait que rassembler.
        """
        groupes: dict[str, list[Poste]] = {}
        for poste in self.postes:
            groupes.setdefault(poste.zone or "", []).append(poste)

        def rang(cle: str) -> tuple[int, str]:
            postes = groupes[cle]
            return (postes[0].zone_rang if postes[0].zone_rang is not None else 99, cle)

        resultat = []
        for cle in sorted(groupes, key=rang):
            postes = tuple(
                sorted(groupes[cle], key=lambda poste: (-poste.montant, poste.libelle))
            )
            total = sum((poste.montant for poste in postes), ZERO)
            zone = _ZoneSimple(
                cle=cle,
                libelle=postes[0].zone_libelle or cle,
                rang=postes[0].zone_rang if postes[0].zone_rang is not None else 99,
            )
            resultat.append((zone, total, postes))
        return tuple(resultat)


@dataclass(frozen=True)
class _ZoneSimple:
    """Une zone telle que la répartition la rend, sans dépendre du référentiel."""

    cle: str
    libelle: str
    rang: int


@dataclass(frozen=True)
class Diversification:
    """Les trois répartitions à une date, et ce qu'il faut dire pour les lire."""

    date: Date
    classes: Repartition
    pays: Repartition
    secteurs: Repartition

    arrete_du: Date | None = None
    arrete_au: Date | None = None
    """La fourchette des dates d'arrêté des compositions employées.

    Une répartition est une photo, mais elle est prise à plusieurs instants : les compositions
    d'un même portefeuille ne sont pas arrêtées le même jour (31/08 à 25/09 mesuré). L'écran
    donne la fourchette plutôt qu'une date unique, qui serait fausse.
    """

    sources: tuple[str, ...] = ()
    intitules_de_date: tuple[str, ...] = ()
    signalements: tuple[Signalement, ...] = ()

    @property
    def repartitions(self) -> tuple[Repartition, ...]:
        return (self.classes, self.pays, self.secteurs)


# --- Le calcul -------------------------------------------------------------------------


@dataclass
class _Cumul:
    """Un accumulateur de travail : les montants par code, et les restes."""

    montants: dict[str, Decimal]
    non_attribue: Decimal = ZERO
    hors_perimetre: Decimal = ZERO
    hors_classification: Decimal = ZERO
    non_couvert: Decimal = ZERO

    @classmethod
    def vide(cls) -> _Cumul:
        return cls(montants={})

    def ajouter(self, code: str, montant: Decimal) -> None:
        self.montants[code] = self.montants.get(code, ZERO) + montant


def _arrondi(montant: Decimal) -> Decimal:
    return montant.quantize(CENTIME, rounding=ROUND_HALF_UP)


def _part_actions(
    composition: CompositionDUnActif, referentiels: Referentiels
) -> Decimal | None:
    """Le pourcentage du fonds investi en actions, ou `None` si la source ne le dit pas.

    C'est lui qui décide de ce qui est **hors périmètre** de la géographie et des secteurs. Sans
    lui, on ne suppose rien : tout le fonds est traité comme des actions, et le non attribué
    absorbera l'écart. Ne rien supposer donne un chiffre prudent ; supposer donnerait un chiffre
    faux.
    """
    if not composition.classes:
        return None
    total = ZERO
    connu = False
    for part in composition.classes:
        classe = referentiels.classe(part.code)
        if classe is None:
            continue
        connu = True
        if classe.actions:
            total += part.pour_cent
    return total if connu else None


def _repartir(
    positions: Iterable[PositionValorisee],
    rubrique: Rubrique,
    source: SourceDeComposition,
    referentiels: Referentiels,
) -> tuple[_Cumul, list[str], list[str], list[Signalement]]:
    """Le cœur : un passage sur les positions, et chaque euro rangé quelque part."""
    cumul = _Cumul.vide()
    non_couverts: list[str] = []
    synthetiques: list[str] = []
    signalements: list[Signalement] = []

    for position in positions:
        valeur = position.valeur
        if valeur is None:
            continue

        if position.poche is Poche.CRYPTO:
            # Hors des **trois** répartitions (D-68), y compris celle des classes d'actifs : un
            # actif numérique n'est ni une action, ni une obligation, ni une liquidité de fonds.
            # Le mettre en « non couvert » le ferait passer pour une donnée manquante, et le
            # ranger dans une classe inventerait une catégorie que personne ne publie.
            cumul.hors_classification += valeur
            continue

        composition = source.composition(position.actif)
        if composition is None:
            cumul.non_couvert += valeur
            non_couverts.append(position.actif)
            continue

        if composition.replication == "synthétique" and position.actif not in synthetiques:
            synthetiques.append(position.actif)

        parts = _parts(composition, rubrique)

        if rubrique is Rubrique.CLASSE:
            attribue = _accumuler(cumul, parts, valeur, rubrique)
            cumul.non_attribue += max(ZERO, _arrondi(valeur - attribue))
            continue

        part_actions = _part_actions(composition, referentiels)
        valeur_actions = (
            valeur if part_actions is None else _arrondi(valeur * part_actions / CENT)
        )
        cumul.hors_perimetre += _arrondi(valeur - valeur_actions)

        attribue = _accumuler(cumul, parts, valeur, rubrique)
        reste = _arrondi(valeur_actions - attribue)
        if reste >= ZERO:
            cumul.non_attribue += reste
        elif -reste > ECART_TOLERE:
            # La composition attribue plus que la part actions annoncée. Deux causes connues :
            # le prêt de titres, qui fait légitimement dépasser 100 % ; ou une source qui
            # exprime ses poids sur la seule poche actions et non sur le fonds entier. On ne
            # tranche pas, et on ne rabote rien : on le dit.
            signalements.append(
                Signalement(
                    categorie=CATEGORIE_ECART,
                    actif=position.actif,
                    poche=position.poche,
                    message=(
                        f"la répartition par {rubrique.value} attribue "
                        f"{_lisible(attribue)} € alors que la part en actions du fonds vaut "
                        f"{_lisible(valeur_actions)} €. Le total de cette répartition dépasse "
                        f"donc la valeur de l'actif. Rien n'a été corrigé : voyez la fiche de "
                        f"l'émetteur."
                    ),
                )
            )
    return cumul, non_couverts, synthetiques, signalements


def _parts(
    composition: CompositionDUnActif, rubrique: Rubrique
) -> Sequence[PartDeComposition]:
    if rubrique is Rubrique.PAYS:
        return composition.pays
    if rubrique is Rubrique.SECTEUR:
        return composition.secteurs
    return composition.classes


def _accumuler(
    cumul: _Cumul,
    parts: Sequence[PartDeComposition],
    valeur: Decimal,
    rubrique: Rubrique,
) -> Decimal:
    """Range les montants d'une position, et rend ce qui a été attribué."""
    attribue = ZERO
    for part in parts:
        montant = _arrondi(valeur * part.pour_cent / CENT)
        if montant == ZERO:
            # Un poste à 0,00 € n'apporte rien et allongerait la liste : on le laisse tomber
            # dans le non attribué, où il pèse zéro. Aucun euro n'est perdu.
            continue
        cumul.ajouter(_cle(part.code, rubrique), montant)
        attribue += montant
    return attribue


def _cle(code: str, rubrique: Rubrique) -> str:
    return code.strip().upper() if rubrique is Rubrique.PAYS else code.strip().lower()


def _postes(
    cumul: _Cumul, rubrique: Rubrique, referentiels: Referentiels
) -> tuple[Poste, ...]:
    """Les montants cumulés, nommés, et triés du plus lourd au plus léger."""
    postes: list[Poste] = []
    for code, montant in cumul.montants.items():
        if rubrique is Rubrique.PAYS:
            connu = referentiels.pays(code)
            zone = referentiels.zone_de(code)
            postes.append(
                Poste(
                    code=code,
                    libelle=connu.libelle if connu is not None else code,
                    montant=montant,
                    reconnu=connu is not None,
                    zone=zone.cle,
                    zone_libelle=zone.libelle,
                    zone_rang=zone.rang,
                )
            )
        elif rubrique is Rubrique.SECTEUR:
            connu = referentiels.secteur(code)
            postes.append(
                Poste(
                    code=code,
                    libelle=connu.libelle if connu is not None else code,
                    montant=montant,
                    reconnu=connu is not None,
                )
            )
        else:
            classe = referentiels.classe(code)
            postes.append(
                Poste(
                    code=code,
                    libelle=classe.libelle if classe is not None else code,
                    montant=montant,
                    reconnu=classe is not None,
                    rang=classe.rang if classe is not None else None,
                )
            )

    if rubrique is Rubrique.CLASSE:
        return tuple(
            sorted(postes, key=lambda poste: (poste.rang if poste.rang is not None else 99,
                                              poste.libelle))
        )
    return tuple(sorted(postes, key=lambda poste: (-poste.montant, poste.libelle)))


def repartir(
    valorisation: Valorisation,
    rubrique: Rubrique,
    source: SourceDeComposition,
    referentiels: Referentiels,
) -> tuple[Repartition, list[Signalement]]:
    """Une répartition, et ce qu'il a fallu signaler pour la produire."""
    positions = valorisation.valorisees
    cumul, non_couverts, synthetiques, signalements = _repartir(
        positions, rubrique, source, referentiels
    )
    repartition = Repartition(
        rubrique=rubrique,
        postes=_postes(cumul, rubrique, referentiels),
        base=valorisation.total.valeur,
        non_attribue=_arrondi(cumul.non_attribue),
        hors_perimetre=_arrondi(cumul.hors_perimetre),
        hors_classification=_arrondi(cumul.hors_classification),
        non_couvert=_arrondi(cumul.non_couvert),
        actifs_non_couverts=tuple(sorted(set(non_couverts))),
        actifs_synthetiques=tuple(sorted(set(synthetiques))),
    )
    return repartition, signalements


def diversifier(
    valorisation: Valorisation,
    source: SourceDeComposition,
    referentiels: Referentiels,
) -> Diversification:
    """Les trois répartitions du portefeuille à la date de la valorisation.

    Une seule passe par rubrique, et une seule demande de composition par actif : le fournisseur
    garde ses réponses, succès comme échecs.
    """
    signalements: list[Signalement] = []
    repartitions: dict[Rubrique, Repartition] = {}
    for rubrique in Rubrique:
        repartition, propres = repartir(valorisation, rubrique, source, referentiels)
        repartitions[rubrique] = repartition
        signalements.extend(propres)

    # La crypto est écartée ici aussi, et pas seulement dans le calcul : demander sa composition
    # ferait apparaître un refus « actif numérique » à l'écran, pour un actif qui n'a rien à
    # chercher. Un message rassurant est encore un message de trop quand il n'y a pas de problème.
    compositions = [
        composition
        for position in valorisation.valorisees
        if position.poche is not Poche.CRYPTO
        and (composition := source.composition(position.actif)) is not None
    ]
    arretes = sorted({composition.arrete_le for composition in compositions})
    sources = []
    intitules = []
    for composition in compositions:
        if composition.source not in sources:
            sources.append(composition.source)
        if composition.intitule_de_la_date not in intitules:
            intitules.append(composition.intitule_de_la_date)

    return Diversification(
        date=valorisation.date,
        classes=repartitions[Rubrique.CLASSE],
        pays=repartitions[Rubrique.PAYS],
        secteurs=repartitions[Rubrique.SECTEUR],
        arrete_du=arretes[0] if arretes else None,
        arrete_au=arretes[-1] if arretes else None,
        sources=tuple(sources),
        intitules_de_date=tuple(intitules),
        signalements=tuple(signalements),
    )


def _lisible(montant: Decimal) -> str:
    """Un montant dans un message du moteur, à deux décimales, en français."""
    return format(_arrondi(montant), "f").replace(".", ",")
