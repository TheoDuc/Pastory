"""Ce que seul l'utilisateur sait de sa fiscalité : la date du premier versement sur son PEA.

L'ancienneté d'un PEA décide de son impôt (D-59) : avant cinq ans, tout retrait est imposé au
taux forfaitaire et clôt le plan ; après, seuls les prélèvements sociaux restent. Elle se compte
depuis le **premier versement**, une date que l'export ne donne pas de façon sûre : un PEA fermé
puis rouvert repart de zéro, et un PEA transféré d'un autre établissement garde sa date
d'origine, invisible ici.

L'application ne devine donc pas (D-40) : sans cette date, l'impôt du PEA est « non calculable »
et le rapport dit quoi écrire. Le fichier vit dans le dossier personnel (D-37), hors de git
(D-01), et **aucun assistant ne le réécrit** : il est court, et la main de l'utilisateur suffit.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from pathlib import Path

from pastory.config import ConfigurationInvalide, emplacements

NOM_FICHIER = "fiscalite.toml"

MODELE = """\
# Ce que seul vous savez de votre fiscalité. Ce fichier reste sur votre machine.
#
# La date du premier versement sur votre PEA : elle décide de son ancienneté, donc de
# l'impôt estimé si vous retiriez tout (moins de 5 ans : 31,4 % et clôture du plan ;
# 5 ans ou plus : prélèvements sociaux seuls). Écrite AAAA-MM-JJ, sans guillemets.
# Un PEA fermé puis rouvert repart de la date de réouverture.

[pea]
premier_versement = AAAA-MM-JJ
"""


@dataclass(frozen=True)
class ConfigurationFiscale:
    premier_versement_pea: Date | None = None
    """`None` tant que l'utilisateur ne l'a pas déclarée."""


def chemin(environnement: Mapping[str, str] | None = None) -> Path:
    return emplacements.dossier_configuration(environnement) / NOM_FICHIER


def charger(
    fichier: Path | None = None, environnement: Mapping[str, str] | None = None
) -> ConfigurationFiscale:
    """Lit la configuration. Un fichier absent donne une configuration vide, pas une erreur :
    c'est le rapport qui dira que la date manque, et où l'écrire."""
    fichier = chemin(environnement) if fichier is None else fichier
    if not fichier.exists():
        return ConfigurationFiscale()

    try:
        contenu = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        raise ConfigurationInvalide(
            f"{fichier} n'est pas un fichier TOML valide : {erreur}. La date s'écrit "
            f"AAAA-MM-JJ, sans guillemets."
        ) from erreur

    pea = contenu.get("pea", {})
    if not isinstance(pea, dict):
        raise ConfigurationInvalide(f"{fichier} : la section [pea] doit être un tableau")

    brut = pea.get("premier_versement")
    if brut is None or (isinstance(brut, str) and brut.strip() == ""):
        return ConfigurationFiscale()
    if isinstance(brut, datetime):
        # TOML accepte « 2024-03-15T00:00:00 », et `datetime` est un `date` pour Python : sans
        # ce cas, la comparaison plus bas lèverait une exception technique au lieu d'expliquer.
        raise ConfigurationInvalide(
            f"{fichier} : « premier_versement » doit être une date seule, sans heure : "
            f"écrivez {brut.date().isoformat()}"
        )
    if not isinstance(brut, Date):
        raise ConfigurationInvalide(
            f"{fichier} : « premier_versement » doit être une date écrite AAAA-MM-JJ, sans "
            f"guillemets, pas {brut!r}"
        )
    if brut > Date.today():
        raise ConfigurationInvalide(
            f"{fichier} : le premier versement ({brut.isoformat()}) est dans le futur"
        )
    return ConfigurationFiscale(premier_versement_pea=brut)
