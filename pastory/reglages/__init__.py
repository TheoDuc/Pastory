"""Les réglages trouvés seuls : chaque valeur avec sa source, sa date et son contrôle (D-80).

L'utilisateur dépose l'export, et c'est tout. Le ticker et la devise d'un actif, son type, ses
frais courants, son contenu, la date d'ouverture du PEA : tout est **cherché et appliqué par
l'application**. Trois règles font de cet automatisme une décision sûre, et non un pari :

1. **une valeur trouvée porte sa source et sa date** (`Origine`), visibles là où elle sert ;
2. **elle passe un contrôle avant d'être appliquée** — la devise d'une cotation, le prix
   d'exécution donné par la banque, la fourchette d'un TER. Une valeur qui échoue n'est pas
   appliquée : elle devient un `Trou` ;
3. **sans source fiable, rien n'est inventé ni demandé** : le `Trou` dit pourquoi, et le reste
   du portefeuille s'affiche quand même.

Une **correction** écrite par l'utilisateur dans `actifs.toml` ou `fiscalite.toml` l'emporte
toujours, et l'application ne réécrit jamais ces fichiers (D-78). Quand une correction contredit
la source, les deux sont gardées pour être montrées côte à côte (`Reglage.ecarte`).

Le paquet est rangé à part, entre l'adaptateur et le moteur : il lit ce que dit la banque
(`CeQueDitLaBanque`, produit par l'adaptateur), interroge les sources extérieures, et rend une
`Configuration` que les cours, les coûts et les compositions lisent comme avant. Le moteur, lui,
ne sait rien de tout cela (D-26).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from enum import StrEnum

from pastory.config.actifs import TypeActif
from pastory.pivot.operation import Poche

SOURCE_CORRECTION_ACTIFS = "corrigé par vous dans actifs.toml"
SOURCE_CORRECTION_FISCALITE = "corrigé par vous dans fiscalite.toml"


@dataclass(frozen=True)
class Origine:
    """D'où vient une valeur, et ce qui a été vérifié avant de l'appliquer."""

    source: str
    """En clair : « export Trade Republic (colonne asset_class) », « liste des ETF de Xetra »…"""

    date: Date | None = None
    """Le jour que décrit la source : dernier jour de l'export, date d'effet de la liste…"""

    controle: str | None = None
    """Ce qui a été vérifié, en une phrase. `None` pour une correction de l'utilisateur."""

    reserve: str | None = None
    """Ce qu'il faut savoir pour s'y fier : la limite connue de la source, dite une fois pour
    toutes (conception-interface §2.2). Par exemple : « la liste est parfois en retard sur une
    baisse de frais »."""

    corrigee: bool = False
    """Vrai quand la valeur a été écrite par l'utilisateur."""

    intitule_de_la_date: str = "au"
    """Comment lire la date : « au » (l'état de la source ce jour-là), ou « taux en vigueur
    depuis le » (la date d'effet d'un TER, qui peut être ancienne sans être périmée)."""


@dataclass(frozen=True)
class Trouvee[T]:
    """Une valeur appliquée, avec son origine."""

    valeur: T
    origine: Origine


@dataclass(frozen=True)
class Trou:
    """Rien de fiable n'a été trouvé. Le motif est écrit pour quelqu'un qui n'a pas suivi la
    construction du projet (règle 10 de CLAUDE.md) : il dit ce qui manque et ce que ça change."""

    motif: str


@dataclass(frozen=True)
class Reglage[T]:
    """La valeur retenue pour un réglage, et ce que la source disait quand on l'a corrigée."""

    retenu: Trouvee[T] | Trou
    ecarte: Trouvee[T] | None = None
    """La valeur trouvée qu'une correction a remplacée, si elle est **différente** : elle est
    montrée à côté, pour qu'une correction devenue inutile ou fausse se voie."""

    @property
    def valeur(self) -> T | None:
        return self.retenu.valeur if isinstance(self.retenu, Trouvee) else None

    @property
    def trou(self) -> Trou | None:
        return self.retenu if isinstance(self.retenu, Trou) else None


@dataclass(frozen=True)
class Cotation:
    """Où chercher le cours d'un actif : un ticker, et la devise **attendue** (D-48)."""

    ticker: str
    devise: str
    place: str | None = None
    nom: str | None = None
    """Le nom de l'instrument chez la source : il aide à reconnaître l'actif, il ne sert à aucun
    calcul (règle 4 de CLAUDE.md)."""


class Sens(StrEnum):
    ENTREE = "entrée"
    SORTIE = "sortie"


@dataclass(frozen=True)
class MouvementPea:
    """Un mouvement d'espèces sur le PEA : un versement, une prime d'ouverture, un retrait."""

    jour: Date
    sens: Sens


@dataclass(frozen=True)
class CeQueDitLaBanque:
    """Ce que l'export de la banque dit des réglages, sous une forme qui ne dépend pas d'elle.

    L'adaptateur le produit (`Rapport.ce_que_dit_la_banque`) ; ce paquet ne sait pas lire un
    export, exactement comme le moteur ne sait pas lire un CSV de Trade Republic (D-26).
    """

    source: str
    """« export Trade Republic » : le nom affiché comme origine des valeurs qui en viennent."""

    date: Date | None
    """Le dernier jour couvert par les exports déposés."""

    types: Mapping[str, frozenset[TypeActif]] = field(default_factory=dict)
    """Actif → les types que la banque lui donne. Plus d'un : la banque se contredit.

    Une classe que l'on ne sait pas traduire (`BOND`…) n'arrive jamais ici : l'adaptateur ne
    produit pas d'opération pour elle, et son rapport de lecture le dit (D-82)."""

    poches: Mapping[str, frozenset[Poche]] = field(default_factory=dict)
    """Actif → les poches où il apparaît. Tous les actifs de l'export y figurent."""

    noms: Mapping[str, str] = field(default_factory=dict)
    """Actif → nom affiché par la banque. Pour reconnaître l'actif, jamais pour calculer."""

    mouvements_pea: tuple[MouvementPea, ...] = ()
    """Les entrées et sorties d'espèces du PEA, dans l'ordre : leur jour et leur sens, jamais
    leur montant (D-11). C'est d'elles que se lit la date d'ouverture du plan."""

    jours_operations_pea: tuple[Date, ...] = ()
    """Les jours des opérations sur les actifs du PEA, dans l'ordre : un achat **avant**
    l'ouverture retenue prouve que le plan est plus ancien que ce que montre l'export."""
