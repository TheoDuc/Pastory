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

from pastory.config.actifs import SECOURS_AUCUN, Configuration, Declaration, TypeActif
from pastory.donnees_externes.cours import ErreurDeSource, Refus

TOTAL_MAXIMAL = Decimal("105")
"""Le total accepté pour une répartition, en pour cent.

Pourquoi pas 100 : le **prêt de titres** peut faire dépasser 100 % — le collatéral en espèces
réinvesti apparaît comme une ligne de plus (`docs/composition-des-etf.md` §8.3). Au-delà de 105,
en revanche, on lit autre chose que ce qu'on croit.
"""

SOURCE_DECLAREE = "déclaré par vous dans actifs.toml"
"""L'origine d'une répartition corrigée à la main (D-70). Elle l'emporte sur toute source."""

CLASSE_ACTIONS = "stock"
"""La classe d'actifs d'une composition déclarée à la main.

Le code est celui qu'emploient les sources, pour que le référentiel le reconnaisse
(`parametres/classes_actifs.toml`).
"""

CENT = Decimal("100")


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

    date_est_un_arrete: bool = True
    """Faux quand `arrete_le` n'est **pas** un arrêté de portefeuille (D-71).

    Une composition déclarée à la main n'a pas d'arrêté : sa date est celle où le fichier a été
    lu. La faire entrer dans la fourchette affichée en tête du rapport la tirerait jusqu'à
    aujourd'hui, et laisserait croire que la source a publié des chiffres du jour.
    """

    regle_de_pays: str = ""
    """**Quelle règle de pays** ces pays suivent, dite en clair (D-66, D-72).

    Le champ qui manquait jusqu'à l'étape 8 bis. La règle était connue du code — `actions.py`
    donne le siège social, `extraetf.py` le pays d'activité, `amundi.py` le pays de
    classification de l'indice — mais **aucune donnée ne la portait**, et le rapport n'en disait
    qu'une phrase générique, sans jamais dire quel actif relevait de quelle règle.

    Pourquoi ça compte : une répartition géographique **n'est pas une grandeur définie de façon
    unique**. L'écart mesuré entre deux règles, sur un même fonds à une même date, est de 2 points
    sur les États-Unis et d'un facteur huit sur l'Irlande (D-66). Trois règles cohabitent
    désormais dans la même répartition, et D-72 demande que la source **et** la règle soient
    visibles **ligne par ligne**.

    Vide veut dire « non précisé » : c'est le cas d'une répartition déclarée à la main, dont la
    règle est celle que l'utilisateur a voulue, et que lui seul connaît.
    """

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
        secours: Mapping[str, SourceDeCompositionDEtf] | None = None,
    ) -> None:
        self.cache = cache
        self.source_etf = source_etf
        self.source_action = source_action
        self.secours = dict(secours or {})
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
        # Les sources de **secours** ne sont pas listées ici : une source branchée mais qu'aucun
        # actif ne demande n'est pas une source de cette répartition. Ce qui est employé pour de
        # vrai se lit dans `Diversification.sources`, construit sur les compositions obtenues.
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
        if source is not None:
            try:
                composition = controler(source())
            except ErreurDeSource as erreur:
                # La principale a échoué. Avant de renoncer, le secours (D-72, D-80).
                nombre_de_refus = len(self._refus)
                de_secours = self._de_secours(actif, apres=erreur)
                if de_secours is not None:
                    self.cache.ecrire(de_secours)
                    return de_secours
                # Un secours imposé qui échoue a déjà dit pourquoi : ne pas répéter.
                if len(self._refus) == nombre_de_refus:
                    self._refuser(actif, erreur.categorie, str(erreur))
                return None
            self.cache.ecrire(composition)
            return composition

        # Pas de source principale du tout (type non déclaré, aucune source branchée) : le motif
        # est déjà retenu par `_source`, et le secours ne remplace pas une déclaration de type.
        return None

    def _de_secours(self, actif: str, apres: ErreurDeSource) -> Composition | None:
        """La composition d'une source de secours, pour un ETF que la principale n'ouvre pas.

        **Essayée d'elle-même** depuis l'étape 8 quater (D-80) : le secours ne connaît que ses
        propres fonds — Amundi répond « aucun produit » pour les autres — et la source comme la
        règle de pays de chaque chiffre restent affichées ligne par ligne, ce qui était la
        condition posée par D-72 pour mélanger deux sources. Une correction `secours = "aucun"`
        le refuse pour un actif ; `secours = "amundi"` l'impose.

        Essayé de lui-même, un secours qui ne connaît pas le fonds se tait : c'est le motif de la
        source principale qui est retenu, puisque c'est elle qu'on attendait. Imposé par une
        correction, c'est **son** motif qui est retenu, la principale étant rappelée.
        """
        declaration = self.actifs.declaration(actif)
        nom = declaration.secours if declaration is not None else None
        if nom == SECOURS_AUCUN:
            return None
        if nom is None:
            if declaration is None or declaration.type is not TypeActif.ETF:
                return None
            for source in self.secours.values():
                try:
                    return controler(source.composition(actif))
                except ErreurDeSource:
                    continue
            return None
        source = self.secours.get(nom)
        if source is None:
            self._refuser(
                actif,
                "source de secours absente",
                f"cet actif demande la source de secours « {nom} », qui n'est pas disponible "
                "dans cette exécution.",
            )
            return None
        try:
            return controler(source.composition(actif))
        except ErreurDeSource as erreur:
            self._refuser(
                actif,
                erreur.categorie,
                f"{erreur} (la source principale avait déjà refusé : {apres})",
            )
            return None

    def _source(self, actif: str):
        """Quelle source interroger, selon ce que l'utilisateur a déclaré du type de l'actif."""
        declaration = self.actifs.declaration(actif)
        if declaration is None or declaration.type is None:
            self._refuser(
                actif,
                "type inconnu",
                "le type de cet actif (ETF, action) n'est pas connu, et un ETF et une action "
                "ne se regardent pas au même endroit : sa composition n'est pas cherchée.",
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
            # Sans cotation retenue, le pays se trouve encore par l'ISIN ; seul le secteur,
            # qui se cherche par le ticker, manquera.
            ticker = declaration.ticker or ""
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
        """Ce que l'utilisateur a déclaré lui-même, s'il a déclaré quelque chose (D-70, D-71).

        Deux déclarations différentes vivent ici, et la seconde est souvent la seule nécessaire :

        - **le contenu** (`contenu = "obligations"`) : il suffit à ranger l'actif dans la bonne
          classe et à le sortir de la géographie et des secteurs, sans rien saisir de plus. C'est
          la réponse à « la source ne connaît pas mon ETF obligataire » ;
        - **les pays et les secteurs**, saisis à la main quand on veut vraiment la finesse.
        """
        declaration = self.actifs.declaration(actif)
        if declaration is None:
            return None
        if (
            declaration.pays is None
            and declaration.secteurs is None
            and declaration.contenu is None
        ):
            return None

        jour = self.aujourd_hui if self.aujourd_hui is not None else Date.today()
        trouvee = (
            declaration.source_du_contenu is not None
            and declaration.pays is None
            and declaration.secteurs is None
        )
        if trouvee:
            # Un contenu trouvé par une source (D-89) : il a une source et une date de relevé, et
            # il se met à jour seul. Ce n'est pas une composition « déclarée par vous ».
            return Composition(
                actif=actif,
                pays=(),
                secteurs=(),
                classes=(Part(code=_classe_declaree(declaration), pour_cent=CENT),),
                arrete_le=declaration.date_du_contenu or jour,
                intitule_de_la_date="date de relevé de la classe d'actifs chez la source",
                source=declaration.source_du_contenu or SOURCE_DECLAREE,
                recupere_le=jour,
                date_est_un_arrete=declaration.date_du_contenu is not None,
            )
        return Composition(
            actif=actif,
            pays=_parts(declaration.pays),
            secteurs=_parts(declaration.secteurs),
            classes=(Part(code=_classe_declaree(declaration), pour_cent=CENT),),
            arrete_le=jour,
            intitule_de_la_date="date de lecture du fichier (une déclaration n'a pas d'arrêté)",
            source=SOURCE_DECLAREE,
            recupere_le=jour,
            date_est_un_arrete=False,
        )

    def oublier(self, actif: str | None = None) -> list[str]:
        """Oublie une composition, ou toutes : la prochaine exécution les redemandera (D-70)."""
        self._vus.clear()
        return self.cache.oublier(actif)

    def _refuser(self, actif: str, categorie: str, motif: str) -> None:
        self._refus.append(Refus(actif=actif, categorie=categorie, motif=motif))


def _classe_declaree(declaration: Declaration) -> str:
    """La classe d'actifs d'une composition déclarée à la main.

    Le contenu déclaré s'il y en a un ; sinon **actions**, parce que déclarer des pays ou des
    secteurs, c'est décrire des actions : ces deux répartitions n'ont pas d'autre sens (D-68).
    """
    if declaration.contenu is not None:
        return declaration.contenu.value
    return CLASSE_ACTIONS


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
