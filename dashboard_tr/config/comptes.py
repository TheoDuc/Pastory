"""« Nommer ses comptes » : le rôle de chaque compte espèces, donné par l'utilisateur (D-10).

Le rôle d'un compte n'est écrit **nulle part** dans l'export. Il ne se devine pas : le
propriétaire du projet a lui-même découvert un troisième compte dont il ignorait l'existence.
C'est pourtant lui qui dit la poche d'un achat — un achat passé sur le compte espèces du PEA
est un achat en PEA.

L'application demande donc ces rôles une fois, dans un fichier TOML lisible et corrigeable
sans être développeur (D-38). Tant qu'un compte utilisé par un achat n'a pas de rôle,
l'export s'arrête : rien n'est deviné (D-40).

Le fichier vit dans le dossier personnel, hors du dossier synchronisé et hors de git
(D-37, D-01). Les numéros de compte n'en sortent jamais : ils ne figurent pas dans le
format pivot.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from dashboard_tr.config import emplacements
from dashboard_tr.pivot.operation import Poche

NOM_FICHIER = "comptes.toml"


class RoleCompte(StrEnum):
    """Ce à quoi sert un compte espèces."""

    COURANT = "courant"
    """Compte courant : c'est de là que partent les achats en CTO et en crypto."""

    PEA = "pea"
    """Compte espèces d'un PEA, actuel **ou** ancien : les achats qui en partent sont en PEA."""


ROLES_ACCEPTES = tuple(role.value for role in RoleCompte)


class ConfigurationInvalide(Exception):
    """Le fichier de configuration existe mais ne peut pas être utilisé tel quel."""


@dataclass(frozen=True)
class Configuration:
    """Ce que l'utilisateur a déclaré."""

    roles: Mapping[str, RoleCompte] = field(default_factory=dict)
    """Numéro de compte → rôle."""

    poches_corrigees: Mapping[str, Poche] = field(default_factory=dict)
    """Actif → poche imposée par l'utilisateur, qui prime sur la déduction (D-16)."""

    def role(self, compte: str | None) -> RoleCompte | None:
        return self.roles.get(compte) if compte is not None else None


def chemin(environnement: Mapping[str, str] | None = None) -> Path:
    return emplacements.dossier_configuration(environnement) / NOM_FICHIER


def charger(
    fichier: Path | None = None, environnement: Mapping[str, str] | None = None
) -> Configuration:
    """Lit la configuration. Un fichier absent donne une configuration vide, pas une erreur.

    C'est le cas du premier lancement : l'assistant `dashboard comptes` n'a pas encore
    tourné. C'est l'export qui refusera d'aller plus loin, avec un message qui explique quoi
    faire — pas la lecture du fichier.
    """
    fichier = chemin(environnement) if fichier is None else fichier
    if not fichier.exists():
        return Configuration()

    try:
        contenu = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        raise ConfigurationInvalide(
            f"{fichier} n'est pas un fichier TOML valide : {erreur}"
        ) from erreur

    return Configuration(
        roles=_lire_roles(contenu.get("comptes", {}), fichier),
        poches_corrigees=_lire_poches(contenu.get("poches", {}), fichier),
    )


def _lire_roles(brut: object, fichier: Path) -> dict[str, RoleCompte]:
    if not isinstance(brut, dict):
        raise ConfigurationInvalide(f"{fichier} : la section [comptes] doit être un tableau")

    roles: dict[str, RoleCompte] = {}
    for compte, valeur in brut.items():
        if not isinstance(valeur, str) or valeur.strip() == "":
            # Un compte laissé vide est un compte que l'utilisateur n'a pas encore nommé :
            # ce n'est pas une erreur de fichier, c'est un travail en cours.
            continue
        try:
            roles[compte] = RoleCompte(valeur.strip())
        except ValueError as erreur:
            raise ConfigurationInvalide(
                f"{fichier} : rôle « {valeur} » inconnu pour un compte. "
                f"Rôles acceptés : {', '.join(ROLES_ACCEPTES)}."
            ) from erreur
    return roles


def _lire_poches(brut: object, fichier: Path) -> dict[str, Poche]:
    if not isinstance(brut, dict):
        raise ConfigurationInvalide(f"{fichier} : la section [poches] doit être un tableau")

    poches: dict[str, Poche] = {}
    for actif, valeur in brut.items():
        if not isinstance(valeur, str) or valeur.strip() == "":
            continue
        try:
            poches[actif] = Poche(valeur.strip())
        except ValueError as erreur:
            raise ConfigurationInvalide(
                f"{fichier} : poche « {valeur} » inconnue pour l'actif {actif}. "
                f"Poches acceptées : {', '.join(p.value for p in Poche)}."
            ) from erreur
    return poches


def modele(
    comptes_vus: Mapping[str, list[str]],
    configuration: Configuration,
) -> str:
    """Le texte du fichier à écrire, avec un compte par ligne, à compléter.

    `comptes_vus` associe chaque numéro de compte aux types d'opérations observés dessus :
    c'est ce qui permet à l'utilisateur de reconnaître un compte qu'il ne connaissait pas
    (D-10).

    **Tout ce que l'utilisateur avait déjà écrit est repris** : ses rôles, ses comptes qui
    n'apparaissent pas dans cet export-ci, et ses corrections de poche. L'assistant réécrit
    le fichier entier ; s'il n'en recopiait qu'une partie, relancer `dashboard comptes`
    effacerait le reste en silence, et les poches déclarées à la main disparaîtraient.
    """
    deja_nommes = configuration.roles
    lignes = [
        "# Le rôle de chaque compte espèces, à compléter une fois.",
        "#",
        "# Trade Republic n'écrit nulle part à quoi sert un compte. Or c'est lui qui dit la",
        "# poche d'un achat : un achat passé depuis le compte espèces du PEA est un achat en",
        "# PEA. Tant qu'un compte utilisé par un achat n'a pas de rôle, l'export s'arrête.",
        "#",
        "# Rôles acceptés : " + ", ".join(f"« {role} »" for role in ROLES_ACCEPTES),
        "#   courant : compte courant, d'où partent les achats en CTO et en crypto",
        "#   pea     : compte espèces d'un PEA, actuel ou ancien (un PEA fermé puis rouvert",
        "#             laisse un ancien compte, dont les achats restent des achats en PEA)",
        "#",
        "# Pour vous aider, les types d'opérations vus sur chaque compte sont rappelés en",
        "# commentaire. Ce fichier reste sur votre machine : il n'entre jamais dans git.",
        "",
        "[comptes]",
    ]

    for compte in sorted(comptes_vus):
        types = comptes_vus[compte]
        if types:
            lignes.append(f"# opérations vues : {', '.join(sorted(types))}")
        role = deja_nommes.get(compte)
        lignes.append(f'"{compte}" = "{role.value if role else ""}"')
        lignes.append("")

    # Les comptes déjà nommés qui n'apparaissent pas dans cet export : un export ne remonte
    # pas forcément toute l'histoire du compte, et perdre un rôle déjà donné obligerait à
    # tout refaire.
    autres = sorted(set(deja_nommes) - set(comptes_vus))
    if autres:
        lignes.append("# Comptes déjà nommés, absents de cet export :")
        for compte in autres:
            lignes.append(f'"{compte}" = "{deja_nommes[compte].value}"')
        lignes.append("")

    lignes += [
        "[poches]",
        "# Facultatif. Corrige la poche déduite pour un actif (D-16). La crypto est reconnue",
        "# à son code commençant par « XF » : si cette règle se trompe sur l'un de vos actifs,",
        '# corrigez-le ici, par exemple :  "XX0000000001" = "CTO"',
        f"# Poches acceptées : {', '.join(p.value for p in Poche)}",
    ]
    for actif, poche in sorted(configuration.poches_corrigees.items()):
        lignes.append(f'"{actif}" = "{poche.value}"')
    lignes.append("")

    return "\n".join(lignes)
