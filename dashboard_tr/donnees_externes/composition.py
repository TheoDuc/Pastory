"""Le contrat de la couche « composition » : ce qu'il y a dans un actif, et comment on l'obtient
(D-63, D-69, D-70).

Le même dessin que pour les cours, avec **une** différence qui change tout : un cours passé ne
change jamais, une composition change chaque mois. Le cache est donc **daté et remplaçable**, là
où celui des cours est définitif ([D-50](../../docs/decisions.md), [D-70](../../docs/decisions.md)).

Quatre principes, et ils expliquent tout le fichier :

1. **on lit les répartitions agrégées, jamais les lignes détenues** (D-63, D-64). Un ETF
   synthétique ne détient pas son indice : ses lignes sont un panier sans rapport, et l'une
   d'elles — le contrat d'échange lui-même — porte parfois un pays, ce qui afficherait
   « 100 % États-Unis » pour un fonds mondial. Cette règle est la raison d'être de la couche ;
2. **les codes, pas les libellés.** Un pays est un code ISO 3166-1, un secteur un code de
   nomenclature. Les libellés des sources sont en allemand, traduits, ou périmés : aucun calcul
   ne s'appuie sur eux (règle 4 de `CLAUDE.md`) ;
3. **rien ne somme à 100 %, et on ne corrige pas.** Mesuré de 98,56 % à 99,96 % selon le fonds,
   et le prêt de titres peut faire dépasser 100 %. Ce qui manque devient du « non attribué »,
   visible (D-69). Renormaliser cacherait précisément ce qu'on ignore ;
4. **une composition sans date est refusée** (D-58, D-70). Une composition d'il y a trois ans
   n'est pas celle du mois dernier, et le propriétaire doit pouvoir la confronter à la fiche de
   l'émetteur au même arrêté.

Ce module ne sait pas ce qu'est un secteur « Technologie » ni une zone : il ne transporte que des
codes. Les libellés viennent de `parametres/referentiels.py`, et c'est `cli.py` qui les rapproche.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from dashboard_tr.config.actifs import Configuration, TypeActif
from dashboard_tr.donnees_externes.cours import ErreurDeSource, Refus

TOTAL_MAXIMAL = Decimal("105")
"""Le total accepté pour une répartition, en pour cent.

Pourquoi pas 100 : le **prêt de titres** peut faire dépasser 100 % — le collatéral en espèces
réinvesti apparaît comme une ligne de plus (`docs/composition-des-etf.md` §8.3). Au-delà de 105,
en revanche, on lit autre chose que ce qu'on croit.
"""

SOURCE_DECLAREE = "déclaré par vous dans actifs.toml"
"""L'origine d'une répartition corrigée à la main (D-70). Elle l'emporte sur toute source."""


class Rubrique(StrEnum):
    """Les trois répartitions. Elles ne se mélangent jamais (D-68)."""

    PAYS = "pays"
    SECTEUR = "secteur"
    CLASSE = "classe"


@dataclass(frozen=True)
class Part:
    """Un poste d'une répartition : un code, et le pourcentage qui lui revient."""

    code: str
    """Code ISO 3166-1 alpha-2 pour un pays, code de nomenclature pour un secteur, code de la
    source pour une classe d'actifs. **Jamais un libellé.**"""

    pour_cent: Decimal


@dataclass(frozen=True)
class Composition:
    """Ce qu'il y a dans un actif, avec tout ce qu'il faut pour le vérifier à la main."""

    actif: str
    pays: tuple[Part, ...]
    secteurs: tuple[Part, ...]
    classes: tuple[Part, ...]

    arrete_le: Date
    """La date d'arrêté annoncée par la source. Obligatoire (D-70)."""

    intitule_de_la_date: str
    """Comment la source **appelle** cette date, dit tel quel.

    La source retenue publie un champ dont le nom parle de l'**indice**, pas explicitement de
    l'arrêté du portefeuille (`docs/composition-des-etf.md` §3.1). On affiche donc la date et ce
    qu'elle dit d'elle-même, sans affirmer plus.
    """

    source: str
    recupere_le: Date

    replication: str | None = None
    """« physique » ou « synthétique », quand la source le dit. Pour un fonds synthétique,
    l'écran doit le signaler : la composition affichée est celle de l'indice, pas des titres que
    le fonds détient (D-64)."""

    document: str | None = None
    """Lien vers le document de l'émetteur (DIC, fiche), pour que la vérification à la main soit
    à un clic."""

    @staticmethod
    def total(parts: Sequence[Part]) -> Decimal:
        return sum((part.pour_cent for part in parts), Decimal("0"))

    @property
    def total_pays(self) -> Decimal:
        return self.total(self.pays)

    @property
    def total_secteurs(self) -> Decimal:
        return self.total(self.secteurs)

    @property
    def total_classes(self) -> Decimal:
        return self.total(self.classes)

    @property
    def synthetique(self) -> bool:
        return self.replication == "synthétique"

    def parts(self, rubrique: Rubrique) -> tuple[Part, ...]:
        if rubrique is Rubrique.PAYS:
            return self.pays
        if rubrique is Rubrique.SECTEUR:
            return self.secteurs
        return self.classes


# --- Les refus propres à cette couche --------------------------------------------------


class CompositionIndisponible(ErreurDeSource):
    """La source ne connaît pas cet actif.

    Cas réel et attendu : la source retenue ignore les actions détenues en direct, et rien ne
    garantit qu'elle couvre tous les émetteurs — BNP Paribas Easy et Xtrackers ne publient rien
    d'exploitable (`docs/composition-des-etf.md` §3.3).
    """

    categorie = "composition indisponible"


class CompositionIncoherente(ErreurDeSource):
    """La source a répondu quelque chose qu'on refuse d'utiliser.

    Toujours pour la même raison : mieux vaut un trou signalé qu'un camembert crédible et faux.
    """

    categorie = "composition incohérente"


# --- Ce qu'on attend d'une source ------------------------------------------------------


class SourceDeCompositionDEtf(Protocol):
    """Qui sait dire ce qu'il y a dans un fonds, à partir de son ISIN seul."""

    nom: str

    def composition(self, actif: str) -> Composition: ...


class SourceDeCompositionDAction(Protocol):
    """Qui sait dire le pays et le secteur d'une société cotée.

    Une action détenue en direct a une composition triviale — un pays, un secteur, 100 % — mais
    elle ne vient pas de la même source ni de la même **règle de pays** : celle-ci donne le
    siège social, là où la source des ETF donne le pays d'activité (D-66). L'écran le dit.
    """

    nom: str

    def composition(self, actif: str, ticker: str) -> Composition: ...


class CacheDeCompositions(Protocol):
    """Ce que le fournisseur attend d'un cache : lire, écrire, oublier."""

    def lire(self, actif: str) -> Composition | None: ...

    def ecrire(self, composition: Composition) -> None: ...

    def oublier(self, actif: str | None = None) -> list[str]: ...


# --- Les contrôles de vraisemblance ----------------------------------------------------


def controler(composition: Composition) -> Composition:
    """Refuse une composition invraisemblable, et rend la même sinon.

    Ces contrôles remplacent la relecture humaine : le propriétaire a choisi la mise à jour
    **automatique** (Q-39), donc plus personne ne regarde entre la source et l'écran. Chacun
    attrape un piège mesuré du comparatif, et **aucun** ne corrige : ils refusent.
    """
    if not (composition.pays or composition.secteurs or composition.classes):
        raise CompositionIncoherente(
            "la source n'a renvoyé aucune répartition pour cet actif : ni pays, ni secteur, ni "
            "classe d'actifs"
        )

    for rubrique in Rubrique:
        parts = composition.parts(rubrique)
        for part in parts:
            if part.pour_cent < 0:
                raise CompositionIncoherente(
                    f"la répartition par {rubrique.value} contient un poids négatif "
                    f"({part.code} : {part.pour_cent})"
                )
        total = Composition.total(parts)
        if total > TOTAL_MAXIMAL:
            raise CompositionIncoherente(
                f"la répartition par {rubrique.value} totalise {total} %, au-delà de "
                f"{TOTAL_MAXIMAL} % : ce n'est pas une répartition en pourcentages, ou une ligne "
                f"est comptée deux fois"
            )

    for part in composition.pays:
        code = part.code.strip()
        if len(code) != 2 or not code.isalpha():
            raise CompositionIncoherente(
                f"« {part.code} » n'est pas un code pays ISO 3166-1 alpha-2. La répartition "
                f"géographique n'est peut-être pas celle qu'on croit lire"
            )

    return composition


# --- Le fournisseur --------------------------------------------------------------------


class FournisseurDeCompositions:
    """La composition d'un actif, d'où qu'elle vienne, et le motif quand il n'y en a pas.

    L'ordre est fixe, et chaque étage a sa raison :

    1. **ce que l'utilisateur a déclaré** dans `actifs.toml` l'emporte toujours (D-70) : c'est la
       porte de sortie quand la source se trompe ;
    2. **le cache**, pour ne rien redemander à chaque lancement ;
    3. **la source**, sauf hors ligne.

    Rien ne remonte en exception : ce qui manque devient un `Refus` lisible, et le calcul
    continue sans cet actif — marqué non couvert, jamais estimé (D-45, D-69).
    """

    def __init__(
        self,
        cache: CacheDeCompositions,
        source_etf: SourceDeCompositionDEtf | None = None,
        source_action: SourceDeCompositionDAction | None = None,
        actifs: Configuration | None = None,
        aujourd_hui: Date | None = None,
        hors_ligne: bool = False,
    ) -> None:
        self.cache = cache
        self.source_etf = source_etf
        self.source_action = source_action
        self.actifs = actifs if actifs is not None else Configuration()
        self.aujourd_hui = aujourd_hui
        self.hors_ligne = hors_ligne
        self._refus: list[Refus] = []
        self._vus: dict[str, Composition | None] = {}

    @property
    def refus(self) -> list[Refus]:
        """Tout ce qui n'a pas pu être obtenu, dans l'ordre où c'est arrivé."""
        return list(self._refus)

    @property
    def sources(self) -> list[str]:
        """Les sources utilisables, pour que le rapport les nomme."""
        noms = []
        if self.source_etf is not None:
            noms.append(self.source_etf.nom)
        if self.source_action is not None:
            noms.append(self.source_action.nom)
        return noms

    def composition(self, actif: str) -> Composition | None:
        """La composition de cet actif, ou `None` avec un motif retenu dans `refus`.

        Un même actif n'est demandé qu'une fois par exécution, succès comme échec : sans cela,
        un actif inconnu de la source ferait un appel réseau par jour de l'évolution.
        """
        if actif in self._vus:
            return self._vus[actif]
        trouvee = self._chercher(actif)
        self._vus[actif] = trouvee
        return trouvee

    def _chercher(self, actif: str) -> Composition | None:
        declaree = self._declaree(actif)
        if declaree is not None:
            return declaree

        en_cache = self.cache.lire(actif)
        if en_cache is not None:
            return en_cache

        if self.hors_ligne:
            self._refuser(
                actif,
                "hors ligne",
                "aucune composition en mémoire, et l'option --hors-ligne interdit de la "
                "demander. Relancez sans cette option pour l'obtenir.",
            )
            return None

        source = self._source(actif)
        if source is None:
            return None
        try:
            composition = controler(source())
        except ErreurDeSource as erreur:
            self._refuser(actif, erreur.categorie, str(erreur))
            return None
        self.cache.ecrire(composition)
        return composition

    def _source(self, actif: str):
        """Quelle source interroger, selon ce que l'utilisateur a déclaré du type de l'actif."""
        declaration = self.actifs.declaration(actif)
        if declaration is None:
            self._refuser(
                actif,
                "actif non déclaré",
                "cet actif n'est pas déclaré dans actifs.toml : sans son type, je ne sais pas "
                "où chercher sa composition. Lancez « dashboard actifs » pour le déclarer.",
            )
            return None
        if declaration.type is None:
            self._refuser(
                actif,
                "type non déclaré",
                "le type de cet actif n'est pas déclaré dans actifs.toml. Un ETF et une action "
                "ne se regardent pas au même endroit. Ajoutez  type = \"etf\"  ou "
                'type = "action"  sur sa ligne.',
            )
            return None

        if declaration.type is TypeActif.ETF:
            if self.source_etf is None:
                self._refuser(actif, "aucune source", "aucune source de composition d'ETF.")
                return None
            return lambda: self.source_etf.composition(actif)

        if declaration.type is TypeActif.ACTION:
            if self.source_action is None:
                self._refuser(actif, "aucune source", "aucune source de composition d'action.")
                return None
            ticker = declaration.ticker
            return lambda: self.source_action.composition(actif, ticker)

        # La crypto n'a ni pays ni secteur : ce n'est pas un manque, c'est sa nature (D-68).
        # Le moteur la met à part sans jamais interroger de source ; si on arrive ici, c'est
        # qu'on l'a demandée par erreur, et le motif doit le dire sans inquiéter.
        self._refuser(
            actif,
            "actif numérique",
            "un actif numérique n'a ni pays ni secteur : il est présenté à part, et cela n'est "
            "pas une donnée manquante.",
        )
        return None

    def _declaree(self, actif: str) -> Composition | None:
        """La répartition corrigée à la main, s'il y en a une (D-70)."""
        declaration = self.actifs.declaration(actif)
        if declaration is None:
            return None
        if declaration.pays is None and declaration.secteurs is None:
            return None
        jour = self.aujourd_hui if self.aujourd_hui is not None else Date.today()
        return Composition(
            actif=actif,
            pays=_parts(declaration.pays),
            secteurs=_parts(declaration.secteurs),
            classes=(),
            arrete_le=jour,
            intitule_de_la_date="date de lecture du fichier (une déclaration n'a pas d'arrêté)",
            source=SOURCE_DECLAREE,
            recupere_le=jour,
        )

    def oublier(self, actif: str | None = None) -> list[str]:
        """Oublie une composition, ou toutes : la prochaine exécution les redemandera (D-70)."""
        self._vus.clear()
        return self.cache.oublier(actif)

    def _refuser(self, actif: str, categorie: str, motif: str) -> None:
        self._refus.append(Refus(actif=actif, categorie=categorie, motif=motif))


def _parts(repartition: Mapping[str, Decimal] | None) -> tuple[Part, ...]:
    if not repartition:
        return ()
    return tuple(
        Part(code=code, pour_cent=poids) for code, poids in sorted(repartition.items())
    )


def grouper_refus(refus: Iterable[Refus]) -> list[tuple[str, list[Refus]]]:
    """Les refus par catégorie, dans l'ordre d'apparition : un bloc de rapport par motif."""
    groupes: dict[str, list[Refus]] = {}
    for un in refus:
        groupes.setdefault(un.categorie, []).append(un)
    return list(groupes.items())
