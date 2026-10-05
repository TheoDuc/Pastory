"""Les **corrections** de l'utilisateur, actif par actif : `actifs.toml` (D-78, D-80).

Depuis l'étape 8 quater, l'application **trouve seule** le ticker et la devise d'un actif, son
type, ses frais courants et son contenu, chacun avec sa source, sa date et un contrôle
(`pastory/reglages`). Ce fichier ne sert plus à configurer : il sert à **corriger**. Chaque champ
y est facultatif, et celui qui est écrit **l'emporte** sur la valeur trouvée ; les autres restent
trouvés. Une correction est possible, jamais nécessaire.

L'application ne réécrit **jamais** ce fichier (D-78, point 2) : il est écrit à la main, ou
demain par l'écran de correction de l'étape 9, qui devra garder ses commentaires.

Les contrôles de lecture restent ceux d'avant, et pour les mêmes raisons :

- la **devise** d'un ticker corrigé est exigée, et ne peut être que l'euro (D-48) : sans elle,
  un cours en dollars passerait pour des euros ;
- un **TER** ou un **spread** hors de leur fourchette est refusé comme une erreur d'unité ;
- un **type**, un **contenu** ou une **source de secours** inconnus sont refusés, pas ignorés.

Le fichier vit dans le dossier personnel, hors du dossier synchronisé et hors de git
(D-37, D-01).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pastory.config import ConfigurationInvalide, emplacements
from pastory.pivot.operation import DEVISE_UNIQUE

NOM_FICHIER = "actifs.toml"

FORME_ATTENDUE = '"<ISIN>" = { ticker = "AAAA.DE", devise = "EUR" }'
"""Comment corriger une cotation, cité tel quel dans les messages d'erreur."""

TER_MINIMUM = Decimal("0.03")
TER_MAXIMUM = Decimal("1.00")
"""En pour cent. Hors de cette fourchette, c'est presque toujours une erreur d'unité : 0.20 écrit
pour 0,20 % vaudrait 20 % par an (`docs/couts-et-fiscalite.md` §2.4)."""

SPREAD_MAXIMUM = Decimal("5")
"""En pour cent, par côté. Au-delà, l'actif n'est plus négociable, ou l'unité est fausse."""

FORME_REPARTITION = 'pays = { US = 70.0, FR = 2.1 }  (et de même pour  secteurs )'
"""Comment corriger à la main la composition d'un actif (D-70)."""

TOTAL_MAXIMAL = Decimal("105")
"""Le total accepté pour une répartition déclarée, en pour cent.

Pourquoi pas 100 : le prêt de titres peut faire dépasser légèrement 100 % dans les données des
fonds (`docs/composition-des-etf.md` §8.3), et une répartition déclarée peut légitimement recopier
une telle source. Au-delà de 105, c'est une erreur de saisie.
"""


class TypeActif(StrEnum):
    """Ce qui choisit le taux de spread par défaut, et dit si un TER est attendu (D-55)."""

    ETF = "etf"
    ACTION = "action"
    CRYPTO = "crypto"


TYPES_ACCEPTES = tuple(type_actif.value for type_actif in TypeActif)


class ContenuActif(StrEnum):
    """**De quoi l'actif est fait à l'intérieur** (D-71). À ne pas confondre avec son `type`.

    Le `type` dit ce qu'on détient — un ETF, une action, une crypto — et c'est lui qui choisit le
    taux de spread et décide si un TER est attendu ([D-55](../../docs/decisions.md),
    [D-61](../../docs/decisions.md)). Le `contenu`, lui, dit ce qu'il y a dedans, et c'est lui qui
    décide de la place de l'actif dans les répartitions : un ETF obligataire reste un **ETF** avec
    ses frais courants, mais son contenu n'a ni pays ni secteur au sens des actions
    ([D-68](../../docs/decisions.md)).

    Les valeurs sont **les clés de `parametres/classes_actifs.toml`** : c'est ce qui permet au
    contenu déclaré d'être nommé et rangé comme celui qu'une source aurait annoncé.
    """

    ACTIONS = "actions"
    OBLIGATIONS = "obligations"
    MATIERES_PREMIERES = "matieres_premieres"


CONTENUS_ACCEPTES = tuple(contenu.value for contenu in ContenuActif)

SECOURS_AMUNDI = "amundi"
SECOURS_AUCUN = "aucun"
"""Refuser toute source de secours pour cet actif : la seule correction possible d'un secours
essayé automatiquement (D-80)."""

SECOURS_ACCEPTES = (SECOURS_AMUNDI, SECOURS_AUCUN)
"""Les sources de secours qu'on sait interroger (D-77), et le refus.

Une valeur inconnue est **refusée à la lecture du fichier**, et non ignorée : un utilisateur qui
écrit « amundy » doit l'apprendre tout de suite, et non découvrir six écrans plus loin que son
fonds est resté non couvert.
"""


@dataclass(frozen=True)
class Declaration:
    """Les réglages d'un actif : où chercher son cours, en quoi, ce qu'il coûte, ce qu'il
    contient.

    Deux usages, une seule forme : la **correction** lue dans `actifs.toml`, où tout champ vide
    veut dire « gardez ce que vous avez trouvé » ; et la **déclaration effective** que
    `pastory/reglages` assemble, où tout champ vide veut dire « rien de fiable n'a été trouvé ».
    """

    ticker: str | None = None
    """Identifiant de l'actif chez la source, place comprise (« AAAA.DE », « BBB-EUR »).
    Sans lui, l'actif n'est pas valorisé : il est signalé, jamais estimé (D-45)."""

    devise: str = DEVISE_UNIQUE
    """Devise **attendue**. Un cours qui arrive dans une autre est refusé, pas converti."""

    type: TypeActif | None = None
    """ETF, action ou crypto. Sans lui, pas de spread estimé pour cet actif."""

    ter_pour_cent: Decimal | None = None
    """Frais courants annuels d'un ETF, en pour cent."""

    spread_pour_cent: Decimal | None = None
    """Un taux de spread par côté propre à cet actif, qui remplace celui de son type."""

    contenu: ContenuActif | None = None
    """De quoi l'actif est fait : actions, obligations, matières premières (D-71).

    Déclaré par l'utilisateur quand la source ne sait pas le dire. Sans lui, un ETF obligataire ou
    un ETF de matières premières serait annoncé « composition inconnue », alors que la vérité est
    qu'il n'a **ni pays ni secteur** — ce qui n'est pas un manque de données.
    """

    pays: Mapping[str, Decimal] | None = None
    """Répartition par pays **déclarée à la main**, qui l'emporte sur la source (D-70).

    La porte de sortie du choix « mise à jour automatique » : si la source se trompe sur un
    actif, on corrige ici sans attendre qu'elle se corrige. Les clés sont des codes ISO 3166-1
    alpha-2, les valeurs des pourcentages.
    """

    secteurs: Mapping[str, Decimal] | None = None
    """Répartition par secteur déclarée à la main. Mêmes règles ; les clés sont les codes de la
    nomenclature retenue (`parametres/secteurs.toml`)."""

    source_du_contenu: str | None = None
    """Pour un contenu **trouvé** (pas corrigé) : sa source, pour que la répartition la nomme.
    Jamais lu dans le fichier : c'est la déclaration effective qui le porte (D-89)."""

    date_du_contenu: Date | None = None
    """Le jour où cette source a relevé le contenu."""

    secours: str | None = None
    """La **source de secours** à interroger pour cet actif, quand la principale ne sait pas
    l'ouvrir (D-72, D-77).

    Sans correction (`None`), le secours est **essayé de lui-même** quand la source principale
    ne sait pas ouvrir un fonds (D-80) : il ne connaît que ses propres fonds, et la source comme
    la règle de pays de chaque chiffre restent affichées ligne par ligne, ce qui était la
    condition de D-72. `"amundi"` l'impose ; `"aucun"` le refuse pour cet actif.

    Amundi ne sert que la **géographie** — les secteurs de cette source sont du GICS, et restent
    non couverts (D-77).
    """


@dataclass(frozen=True)
class FraisCourantsProposes:
    """Un TER trouvé dans une source, avec de quoi le reconnaître et le vérifier."""

    ter_pour_cent: Decimal
    source: str
    nom: str | None = None
    """Nom de la part dans la source : pour vérifier que c'est bien la sienne."""

    politique: str | None = None
    """« Accumulating » / « Distributing » : idem."""

    date: Date | None = None
    """La date d'effet annoncée par la source."""


@dataclass(frozen=True)
class Proposition:
    """Une cotation trouvée par la recherche d'une source, **avant** tout contrôle.

    Elle ne sert à calculer qu'après avoir passé les contrôles de `pastory/reglages` (devise,
    prix d'exécution) ; sinon elle est seulement montrée, avec le motif du refus.
    """

    ticker: str
    place: str | None = None
    devise: str | None = None
    nom: str | None = None
    """Nom affiché par la source. Aide à reconnaître l'actif, ne sert à aucun calcul
    (règle 4 de CLAUDE.md)."""

    type: TypeActif | None = None
    """Ce que la source dit de la nature de l'actif. Informatif seulement : le type retenu
    est celui de la banque (D-82), et la source se trompe sur un ETC d'or."""


@dataclass(frozen=True)
class Configuration:
    """Les réglages de tous les actifs : les corrections lues dans le fichier, ou la
    configuration effective assemblée par `pastory/reglages`."""

    declarations: Mapping[str, Declaration] = field(default_factory=dict)
    """Actif (ISIN ou code crypto) → ses réglages."""

    sans_cotation: Mapping[str, str] = field(default_factory=dict)
    """Actif → pourquoi aucune cotation n'a été trouvée, pour que le refus d'un cours le dise."""

    def declaration(self, actif: str) -> Declaration | None:
        """Les réglages d'un actif, ou `None` s'il n'en a aucun."""
        return self.declarations.get(actif)

    @property
    def actifs_declares(self) -> frozenset[str]:
        return frozenset(self.declarations)



def chemin(environnement: Mapping[str, str] | None = None) -> Path:
    return emplacements.dossier_configuration(environnement) / NOM_FICHIER


def charger(
    fichier: Path | None = None, environnement: Mapping[str, str] | None = None
) -> Configuration:
    """Lit les corrections. Un fichier absent n'est pas une erreur : c'est le cas normal, celui
    où l'utilisateur n'a rien eu à corriger."""
    fichier = chemin(environnement) if fichier is None else fichier
    if not fichier.exists():
        return Configuration()

    try:
        contenu = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        raise ConfigurationInvalide(
            f"{fichier} n'est pas un fichier TOML valide : {erreur}"
        ) from erreur

    return Configuration(declarations=_lire_declarations(contenu.get("actifs", {}), fichier))


def _lire_declarations(brut: object, fichier: Path) -> dict[str, Declaration]:
    if not isinstance(brut, dict):
        raise ConfigurationInvalide(f"{fichier} : la section [actifs] doit être un tableau")

    declarations: dict[str, Declaration] = {}
    for actif, valeur in brut.items():
        # Une ligne laissée vide ne corrige rien : c'est la forme qu'écrivait l'ancien
        # assistant pour un actif « à compléter ». Ce qui est trouvé s'applique.
        if isinstance(valeur, str):
            if valeur.strip() == "":
                continue
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} doit déclarer un ticker et une devise. "
                f"Écrivez  {FORME_ATTENDUE}"
            )

        if not isinstance(valeur, dict):
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} est déclaré d'une façon que je ne comprends "
                f"pas. Écrivez  {FORME_ATTENDUE}"
            )

        ticker = _lire_ticker(valeur.get("ticker"), actif, fichier)
        declarations[actif] = Declaration(
            ticker=ticker,
            # La devise n'a de sens qu'avec un ticker : c'est celle de cette cotation-là.
            devise=(
                _lire_devise(valeur.get("devise"), actif, fichier)
                if ticker is not None
                else DEVISE_UNIQUE
            ),
            type=_lire_type(valeur.get("type"), actif, fichier),
            ter_pour_cent=_lire_taux(
                valeur.get("ter_pour_cent"), "ter_pour_cent", TER_MINIMUM, TER_MAXIMUM,
                actif, fichier,
            ),
            spread_pour_cent=_lire_taux(
                valeur.get("spread_pour_cent"), "spread_pour_cent", Decimal("0"),
                SPREAD_MAXIMUM, actif, fichier,
            ),
            contenu=_lire_contenu(valeur.get("contenu"), actif, fichier),
            pays=_lire_repartition(valeur.get("pays"), "pays", actif, fichier),
            secteurs=_lire_repartition(valeur.get("secteurs"), "secteurs", actif, fichier),
            secours=_lire_secours(valeur.get("secours"), actif, fichier),
        )
    return declarations


def _lire_ticker(valeur: object, actif: str, fichier: Path) -> str | None:
    """Le ticker corrigé, facultatif : absent ou vide, c'est celui trouvé qui s'applique."""
    if valeur is None:
        return None
    if not isinstance(valeur, str):
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « ticker » qui n'est pas un texte : {valeur!r}. "
            f"Écrivez  {FORME_ATTENDUE}"
        )
    return valeur.strip() or None


def _lire_contenu(valeur: object, actif: str, fichier: Path) -> ContenuActif | None:
    """Le contenu, facultatif : absent, c'est la source qui décide (D-71)."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in CONTENUS_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « contenu » que je ne connais pas : {valeur!r}. "
            f"Contenus acceptés : {', '.join(CONTENUS_ACCEPTES)}. Le contenu dit de quoi l'actif "
            f"est fait à l'intérieur ; le « type », lui, dit ce que vous détenez (etf, action, "
            f"crypto)."
        )
    return ContenuActif(valeur.strip().lower())


def _lire_secours(valeur: object, actif: str, fichier: Path) -> str | None:
    """La source de secours, facultative. Une valeur inconnue est refusée, pas ignorée."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in SECOURS_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} demande une source de secours que je ne connais pas : "
            f"{valeur!r}. Sources acceptées : {', '.join(SECOURS_ACCEPTES)}."
        )
    return valeur.strip().lower()


def _lire_repartition(
    valeur: object, champ: str, actif: str, fichier: Path
) -> dict[str, Decimal] | None:
    """Une répartition déclarée à la main, facultative, qui l'emporte sur la source (D-70).

    Trois refus, et chacun protège d'un chiffre faux et crédible :

    - un poids qui n'est pas un nombre, ou négatif ;
    - un total au-delà de `TOTAL_MAXIMAL` : c'est presque toujours une ligne oubliée en double,
      ou des fractions écrites pour des pourcentages ;
    - un total nul, qui ferait disparaître l'actif des totaux sans le dire.

    Un total **inférieur** à 100 est en revanche accepté tel quel : le reste devient du « non
    attribué », exactement comme pour une source (D-69). On ne complète jamais à 100.
    """
    if valeur is None:
        return None
    if not isinstance(valeur, dict) or not valeur:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » que je ne comprends pas. "
            f"Écrivez  {FORME_REPARTITION}"
        )

    repartition: dict[str, Decimal] = {}
    for code, poids in valeur.items():
        if isinstance(poids, bool) or not isinstance(poids, int | float):
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} déclare {champ}.{code} = {poids!r}, qui n'est pas "
                f"un nombre. Écrivez un pourcentage, par exemple  {code} = 12.5"
            )
        part = Decimal(str(poids))
        if part < 0:
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} déclare {champ}.{code} = {poids}, un poids négatif."
            )
        repartition[str(code).strip()] = part

    total = sum(repartition.values(), Decimal("0"))
    if total <= 0:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » dont le total est nul. L'actif "
            f"disparaîtrait de la répartition sans que rien ne le dise. Retirez la ligne plutôt."
        )
    if total > TOTAL_MAXIMAL:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » dont le total fait {total} %, "
            f"au-delà de {TOTAL_MAXIMAL} %. C'est presque toujours une ligne comptée deux fois, "
            f"ou des fractions écrites pour des pourcentages (0.72 au lieu de 72)."
        )
    return repartition


def _lire_devise(valeur: object, actif: str, fichier: Path) -> str:
    """La devise attendue, exigée explicitement (D-48).

    Elle n'est pas devinée : sans elle, un cours en dollars passerait pour des euros. Et elle
    ne peut être que l'euro tant que l'application ne traite qu'une devise (D-26) — déclarer
    autre chose, c'est presque toujours avoir retenu la mauvaise place de cotation.
    """
    if not isinstance(valeur, str) or valeur.strip() == "":
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} n'a pas de « devise ». Elle n'est pas devinée : "
            f"sans elle, un cours dans une autre monnaie passerait pour des euros. "
            f"Écrivez  {FORME_ATTENDUE}"
        )

    devise = valeur.strip().upper()
    if devise != DEVISE_UNIQUE:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} est déclaré en {devise}, or l'application ne traite "
            f"que l'euro (D-26) et ne convertit rien. Retenez la cotation en {DEVISE_UNIQUE} "
            f"de cet actif — un même titre cote souvent sur plusieurs places, dans plusieurs "
            f"monnaies."
        )
    return devise


def _lire_type(valeur: object, actif: str, fichier: Path) -> TypeActif | None:
    """Le type, facultatif : absent ou vide, l'actif n'aura pas de spread estimé."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in TYPES_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « type » que je ne connais pas : {valeur!r}. "
            f"Types acceptés : {', '.join(TYPES_ACCEPTES)}."
        )
    return TypeActif(valeur.strip().lower())


def _lire_taux(
    valeur: object,
    champ: str,
    minimum: Decimal,
    maximum: Decimal,
    actif: str,
    fichier: Path,
) -> Decimal | None:
    """Un taux en pour cent, facultatif, et refusé hors de sa fourchette de vraisemblance.

    Écrit par un humain, un taux se trompe d'unité plus souvent que de valeur : 0.002 pour
    0,20 %, ou 20 pour 0,20 %. Les deux donneraient des frais absurdes sans rien dire.
    """
    if valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, int | float):
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « {champ} » qui n'est pas un nombre : "
            f"{valeur!r}. Écrivez par exemple  {champ} = 0.20  pour 0,20 %."
        )
    taux = Decimal(str(valeur))
    if not (minimum <= taux <= maximum) or (champ == "spread_pour_cent" and taux <= 0):
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare {champ} = {valeur}, hors de la fourchette "
            f"attendue ({minimum} à {maximum} pour cent). C'est presque toujours une erreur "
            f"d'unité : 0,20 % s'écrit  {champ} = 0.20"
        )
    return taux
