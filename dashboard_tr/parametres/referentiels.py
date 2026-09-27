"""Lire les référentiels de la diversification : les secteurs, les pays et leurs zones (D-65
à D-67).

Un **référentiel** n'est pas un taux. Un taux porte une valeur, une unité et une date d'entrée en
vigueur ([lecture.py](lecture.py)) ; un référentiel, lui, est une **table** : un code, un libellé,
un rattachement. D'où ce second lecteur, à côté du premier.

Ce qu'ils ont en commun, et qui vient de [D-58](../../docs/decisions.md) : **sans source ni date de
vérification, le fichier est refusé**. Un secteur affiché sans savoir de quelle nomenclature il
vient n'est pas vérifiable, et deux nomenclatures ne s'additionnent pas — c'est tout l'objet de
`secteurs.toml`.

Trois refus, tous pour la même raison (un référentiel faux est pire qu'un référentiel absent) :

1. **un alias employé deux fois** : deux secteurs revendiqueraient le même code de source, et le
   résultat dépendrait de l'ordre de lecture ;
2. **un pays rattaché à une zone qui n'existe pas** : la zone disparaîtrait silencieusement du
   total ;
3. **un fichier vide ou sans sa table** : ces fichiers sont livrés avec l'application, il n'y a
   aucune raison qu'ils manquent.

Ce qui n'est **pas** un refus : un code que le fichier ne connaît pas. Ce n'est pas au référentiel
de connaître la terre entière. Un code inconnu remonte tel quel, il est affiché, et il est signalé
— jamais rangé par défaut (règle 5 de `CLAUDE.md`).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from pathlib import Path

from dashboard_tr.parametres import DOSSIER, ParametresInvalides

FICHIER_SECTEURS = DOSSIER / "secteurs.toml"
FICHIER_ZONES = DOSSIER / "zones.toml"
FICHIER_CLASSES = DOSSIER / "classes_actifs.toml"

ZONE_INCONNUE = "inconnue"
"""La zone des pays que `zones.toml` ne connaît pas. Elle n'est **pas** dans le fichier : elle est
fabriquée ici, pour que le total reste juste sans qu'aucun pays soit rattaché de force."""

LIBELLE_ZONE_INCONNUE = "Zone non renseignee"
"""Sans accent : ce libellé peut sortir sur une console Windows, qui écrit en cp1252."""

RANG_ZONE_INCONNUE = 99


def normaliser(code: str) -> str:
    """La forme sous laquelle un code de source est comparé.

    Les sources écrivent le même secteur de trois façons — `financial_services` chez l'une,
    `financial-services` chez l'autre, « Financial Services » chez la troisième. On ramène les
    trois à la même clé, sans jamais toucher au **sens** : rapprocher deux écritures d'une même
    nomenclature est permis, rapprocher deux nomenclatures ne l'est pas (D-65).
    """
    return code.strip().lower().replace("-", "_").replace(" ", "_")


# --- Ce que tout référentiel porte -----------------------------------------------------


@dataclass(frozen=True)
class Origine:
    """D'où vient cette table, et quand quelqu'un l'a vérifiée (D-58)."""

    source: str
    verifie_le: Date
    nomenclature: str | None = None
    """Le nom de la classification, quand il y en a une à nommer. C'est ce que l'écran affiche :
    « classification Morningstar », jamais « GICS » (D-65)."""

    fournisseur: str | None = None
    """Qui publie le découpage, quand c'est une convention et non une norme (D-67)."""

    note: str = ""

    @property
    def en_clair(self) -> str:
        """« Morningstar…, vérifiée le 2026-09-27 » — pour les phrases du rapport."""
        morceaux = []
        if self.nomenclature is not None:
            morceaux.append(self.nomenclature)
        elif self.fournisseur is not None:
            morceaux.append(self.fournisseur)
        morceaux.append(f"vérifiée le {self.verifie_le.isoformat()}")
        return ", ".join(morceaux)


# --- Lecture, et les refus -------------------------------------------------------------


def _lire(fichier: Path) -> dict[str, object]:
    if not fichier.exists():
        raise ParametresInvalides(f"fichier de référentiel introuvable : {fichier}")
    try:
        return tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        message = f"{fichier} n'est pas un fichier TOML valide : {erreur}"
        raise ParametresInvalides(message) from erreur


def _texte_ou_none(valeur: object) -> str | None:
    return valeur.strip() if isinstance(valeur, str) and valeur.strip() else None


def _origine(contenu: Mapping[str, object], fichier: Path) -> Origine:
    meta = contenu.get("meta")
    if not isinstance(meta, dict):
        raise ParametresInvalides(f"{fichier} : la table [meta] est absente")
    source = _texte_ou_none(meta.get("source"))
    if source is None:
        raise ParametresInvalides(
            f"{fichier} : [meta] doit porter une « source » non vide. Un référentiel sans source "
            "n'est pas vérifiable (D-58)."
        )
    verifie_le = meta.get("verifie_le")
    if not isinstance(verifie_le, Date):
        raise ParametresInvalides(
            f"{fichier} : [meta] doit porter une date « verifie_le », écrite 2026-09-27, sans "
            "guillemets."
        )
    return Origine(
        source=source,
        verifie_le=verifie_le,
        nomenclature=_texte_ou_none(meta.get("nomenclature")),
        fournisseur=_texte_ou_none(meta.get("fournisseur_des_zones")),
        note=_texte_ou_none(meta.get("note")) or "",
    )


def _table(contenu: Mapping[str, object], cle: str, fichier: Path) -> Mapping[str, object]:
    valeur = contenu.get(cle)
    if not isinstance(valeur, dict) or not valeur:
        raise ParametresInvalides(f"{fichier} : la table [{cle}] est absente ou vide")
    return valeur


def _sous_table(valeur: object, ou: str, fichier: Path) -> Mapping[str, object]:
    if not isinstance(valeur, dict):
        raise ParametresInvalides(f"{fichier} : [{ou}] devrait être une table")
    return valeur


def _exiger_texte(table: Mapping[str, object], cle: str, ou: str, fichier: Path) -> str:
    valeur = _texte_ou_none(table.get(cle))
    if valeur is None:
        raise ParametresInvalides(f"{fichier} : [{ou}] doit porter un « {cle} » non vide")
    return valeur


def _alias(table: Mapping[str, object], ou: str, fichier: Path) -> tuple[str, ...]:
    valeur = table.get("alias", [])
    if not isinstance(valeur, list) or not all(isinstance(un, str) for un in valeur):
        raise ParametresInvalides(f"{fichier} : [{ou}] « alias » doit être une liste de textes")
    return tuple(str(un) for un in valeur)


# --- Les secteurs ----------------------------------------------------------------------


@dataclass(frozen=True)
class Secteur:
    """Un poste de la nomenclature retenue."""

    code: str
    """Le code officiel de la nomenclature (« 311 »), jamais celui d'une source."""

    libelle: str
    super_secteur: str


@dataclass(frozen=True)
class Nomenclature:
    """Les secteurs, et de quoi reconnaître celui qu'une source nomme à sa façon."""

    origine: Origine
    secteurs: Mapping[str, Secteur]
    """Par code officiel, dans l'ordre du fichier."""

    par_alias: Mapping[str, str] = field(default_factory=dict)
    """Code de source normalisé → code officiel."""

    def secteur(self, code_source: str) -> Secteur | None:
        """Le secteur qu'une source désigne par ce code, ou `None` si le code est inconnu.

        `None` n'est pas une erreur du référentiel : c'est un code que l'application devra
        **afficher** sans le ranger (règle 5 de `CLAUDE.md`).
        """
        code = self.par_alias.get(normaliser(code_source))
        return self.secteurs.get(code) if code is not None else None

    @property
    def libelles(self) -> tuple[str, ...]:
        return tuple(secteur.libelle for secteur in self.secteurs.values())


def charger_secteurs(fichier: Path | None = None) -> Nomenclature:
    """La nomenclature sectorielle, ou une erreur explicite."""
    chemin = FICHIER_SECTEURS if fichier is None else fichier
    contenu = _lire(chemin)
    origine = _origine(contenu, chemin)
    if origine.nomenclature is None:
        raise ParametresInvalides(
            f"{chemin} : [meta] doit porter une « nomenclature ». C'est ce que l'écran affiche à "
            "côté des chiffres, et deux nomenclatures ne s'additionnent pas (D-65)."
        )

    secteurs: dict[str, Secteur] = {}
    par_alias: dict[str, str] = {}
    for code, brut in _table(contenu, "secteur", chemin).items():
        ou = f"secteur.{code}"
        table = _sous_table(brut, ou, chemin)
        secteurs[code] = Secteur(
            code=code,
            libelle=_exiger_texte(table, "libelle", ou, chemin),
            super_secteur=_exiger_texte(table, "super_secteur", ou, chemin),
        )
        for alias in (*_alias(table, ou, chemin), code):
            normalise = normaliser(alias)
            if normalise in par_alias and par_alias[normalise] != code:
                raise ParametresInvalides(
                    f"{chemin} : l'alias « {alias} » est revendiqué par deux secteurs "
                    f"({par_alias[normalise]} et {code}). Le résultat dépendrait de l'ordre de "
                    "lecture."
                )
            par_alias[normalise] = code
    return Nomenclature(origine=origine, secteurs=secteurs, par_alias=par_alias)


# --- Les pays et leurs zones -----------------------------------------------------------


@dataclass(frozen=True)
class Zone:
    """Un regroupement de pays. **Une convention, pas une donnée** (D-67)."""

    cle: str
    libelle: str
    rang: int
    """L'ordre d'affichage voulu, pour que deux écrans ne classent pas les zones autrement."""

    note: str = ""


@dataclass(frozen=True)
class Pays:
    """Un pays : son code ISO, son nom français, et la zone où il est rattaché."""

    code: str
    libelle: str
    zone: str
    note: str = ""


@dataclass(frozen=True)
class Geographie:
    """Les pays connus, leurs noms français et leurs zones."""

    origine: Origine
    zones: Mapping[str, Zone]
    pays: Mapping[str, Pays]

    def connait(self, code: str) -> bool:
        return code.strip().upper() in self.pays

    def nom(self, code: str) -> str:
        """Le nom français du pays, ou **son code tel quel** s'il est inconnu.

        Jamais de « Autre » ni de case vide : un code inconnu reste lisible et repérable, et
        l'appelant le signale.
        """
        propre = code.strip().upper()
        connu = self.pays.get(propre)
        return connu.libelle if connu is not None else propre

    def zone_de(self, code: str) -> Zone:
        """La zone du pays, ou la zone « non renseignée », qui n'est pas dans le fichier."""
        connu = self.pays.get(code.strip().upper())
        if connu is None:
            return self.zone_inconnue
        return self.zones[connu.zone]

    @property
    def zone_inconnue(self) -> Zone:
        return Zone(
            cle=ZONE_INCONNUE,
            libelle=LIBELLE_ZONE_INCONNUE,
            rang=RANG_ZONE_INCONNUE,
            note="Pays absents de zones.toml : leur nom et leur zone n'ont pas été renseignés.",
        )

    def ordonnees(self) -> tuple[Zone, ...]:
        """Les zones du fichier, par rang, puis la zone « non renseignée »."""
        triees = sorted(self.zones.values(), key=lambda zone: (zone.rang, zone.cle))
        return (*triees, self.zone_inconnue)


def charger_zones(fichier: Path | None = None) -> Geographie:
    """Les pays et les zones, ou une erreur explicite."""
    chemin = FICHIER_ZONES if fichier is None else fichier
    contenu = _lire(chemin)
    origine = _origine(contenu, chemin)

    zones: dict[str, Zone] = {}
    for cle, brut in _table(contenu, "zone", chemin).items():
        ou = f"zone.{cle}"
        table = _sous_table(brut, ou, chemin)
        rang = table.get("rang")
        if not isinstance(rang, int):
            raise ParametresInvalides(f"{chemin} : [{ou}] doit porter un « rang » entier")
        if cle == ZONE_INCONNUE:
            raise ParametresInvalides(
                f"{chemin} : la zone « {ZONE_INCONNUE} » est réservée à ce que le fichier ne "
                "connaît pas ; elle ne peut pas y être déclarée."
            )
        zones[cle] = Zone(
            cle=cle,
            libelle=_exiger_texte(table, "libelle", ou, chemin),
            rang=rang,
            note=_texte_ou_none(table.get("note")) or "",
        )

    pays: dict[str, Pays] = {}
    for code, brut in _table(contenu, "pays", chemin).items():
        ou = f"pays.{code}"
        table = _sous_table(brut, ou, chemin)
        zone = _exiger_texte(table, "zone", ou, chemin)
        if zone not in zones:
            raise ParametresInvalides(
                f"{chemin} : [{ou}] est rattaché à la zone « {zone} », qui n'est pas déclarée. "
                "Elle disparaîtrait silencieusement du total."
            )
        propre = code.strip().upper()
        if len(propre) != 2 or not propre.isalpha():
            raise ParametresInvalides(
                f"{chemin} : [{ou}] n'est pas un code ISO 3166-1 alpha-2 (deux lettres)."
            )
        pays[propre] = Pays(
            code=propre,
            libelle=_exiger_texte(table, "libelle", ou, chemin),
            zone=zone,
            note=_texte_ou_none(table.get("note")) or "",
        )
    return Geographie(origine=origine, zones=zones, pays=pays)


# --- Les classes d'actifs --------------------------------------------------------------


@dataclass(frozen=True)
class ClasseDActifs:
    """Actions, obligations, liquidités : ce qui décide si un actif entre dans la géographie."""

    cle: str
    libelle: str
    rang: int
    actions: bool
    """Vrai pour la poche d'actions, la **seule** que la géographie et les secteurs décrivent
    (D-68)."""


@dataclass(frozen=True)
class Classes:
    """Les classes d'actifs, et de quoi reconnaître celle qu'une source nomme à sa façon."""

    origine: Origine
    classes: Mapping[str, ClasseDActifs]
    par_alias: Mapping[str, str] = field(default_factory=dict)

    def classe(self, code_source: str) -> ClasseDActifs | None:
        cle = self.par_alias.get(normaliser(code_source))
        return self.classes.get(cle) if cle is not None else None

    def ordonnees(self) -> tuple[ClasseDActifs, ...]:
        return tuple(
            sorted(self.classes.values(), key=lambda classe: (classe.rang, classe.cle))
        )


def charger_classes(fichier: Path | None = None) -> Classes:
    """Les classes d'actifs, ou une erreur explicite."""
    chemin = FICHIER_CLASSES if fichier is None else fichier
    contenu = _lire(chemin)
    origine = _origine(contenu, chemin)

    classes: dict[str, ClasseDActifs] = {}
    par_alias: dict[str, str] = {}
    for cle, brut in _table(contenu, "classe", chemin).items():
        ou = f"classe.{cle}"
        table = _sous_table(brut, ou, chemin)
        rang = table.get("rang")
        if not isinstance(rang, int):
            raise ParametresInvalides(f"{chemin} : [{ou}] doit porter un « rang » entier")
        actions = table.get("actions", False)
        if not isinstance(actions, bool):
            raise ParametresInvalides(f"{chemin} : [{ou}] « actions » doit être true ou false")
        classes[cle] = ClasseDActifs(
            cle=cle,
            libelle=_exiger_texte(table, "libelle", ou, chemin),
            rang=rang,
            actions=actions,
        )
        for alias in (*_alias(table, ou, chemin), cle):
            normalise = normaliser(alias)
            if normalise in par_alias and par_alias[normalise] != cle:
                raise ParametresInvalides(
                    f"{chemin} : l'alias « {alias} » est revendiqué par deux classes "
                    f"({par_alias[normalise]} et {cle})."
                )
            par_alias[normalise] = cle

    if not any(classe.actions for classe in classes.values()):
        raise ParametresInvalides(
            f"{chemin} : aucune classe n'est marquée « actions = true ». Sans elle, aucune "
            "répartition géographique ni sectorielle n'aurait de base (D-68)."
        )
    return Classes(origine=origine, classes=classes, par_alias=par_alias)


# --- Les trois réunis, tels que le moteur les attend -----------------------------------


@dataclass(frozen=True)
class Referentiels:
    """Les trois référentiels derrière une seule porte.

    C'est cet objet que `cli.py` passe au moteur, et il satisfait
    `moteur.diversification.Referentiels` sans que le moteur sache qu'il existe des fichiers
    TOML — le même montage que pour les cours et les taux.
    """

    secteurs: Nomenclature
    geographie: Geographie
    classes_dactifs: Classes

    def secteur(self, code: str) -> Secteur | None:
        return self.secteurs.secteur(code)

    def pays(self, code: str) -> Pays | None:
        return self.geographie.pays.get(code.strip().upper())

    def zone_de(self, code_pays: str) -> Zone:
        return self.geographie.zone_de(code_pays)

    def classe(self, code: str) -> ClasseDActifs | None:
        return self.classes_dactifs.classe(code)

    @property
    def nomenclature(self) -> str:
        """Le nom de la classification sectorielle, tel qu'il doit s'afficher (D-65)."""
        return self.secteurs.origine.nomenclature or "nomenclature non nommée"

    @property
    def origines(self) -> tuple[str, ...]:
        """Ce que le rapport écrit sous les répartitions, pour qu'elles soient vérifiables."""
        return (
            f"Secteurs : {self.secteurs.origine.en_clair}",
            f"Zones : {self.geographie.origine.en_clair}",
            f"Classes d'actifs : {self.classes_dactifs.origine.en_clair}",
        )


def charger_tout(
    secteurs: Path | None = None,
    zones: Path | None = None,
    classes: Path | None = None,
) -> Referentiels:
    """Les trois référentiels, ou la première erreur rencontrée."""
    return Referentiels(
        secteurs=charger_secteurs(secteurs),
        geographie=charger_zones(zones),
        classes_dactifs=charger_classes(classes),
    )
