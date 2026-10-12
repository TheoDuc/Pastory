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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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

# Avec plusieurs portefeuilles dans Pastory, dites pour lequel, par son nom :
# [portefeuille."Camille".pea]
# premier_versement = AAAA-MM-JJ
"""


@dataclass(frozen=True)
class CorrectionDuPea:
    """Ce que `fiscalite.toml` dit du PEA **d'un portefeuille** (D-109)."""

    date: Date | None = None
    """La date corrigée qui vaut pour ce portefeuille. `None` : rien n'est corrigé, la date
    trouvée dans l'export s'applique."""
    ecartees: tuple[str, ...] = ()
    """Les corrections écrites qui ne sont **pas** appliquées, chacune avec sa raison : à
    dire à l'utilisateur, qui les croit en vigueur."""


@dataclass(frozen=True)
class ConfigurationFiscale:
    premier_versement_pea: Date | None = None
    """La date écrite sous `[pea]`, sans dire pour quel portefeuille. `None` tant que
    l'utilisateur ne l'a pas déclarée."""
    par_portefeuille: Mapping[str, Date] = field(default_factory=dict)
    """Les dates écrites sous `[portefeuille."Nom".pea]`, par nom de portefeuille."""

    def pour(
        self, portefeuille: str | None, tous: Sequence[str] = (), tiers: bool = False
    ) -> CorrectionDuPea:
        """La correction qui vaut pour `portefeuille`, parmi `tous` ceux du dossier.

        L'ancienneté d'un PEA est celle d'**une personne** : une date corrigée à la main ne
        s'applique jamais au portefeuille d'une autre. Trois règles :

        - une date écrite **pour ce portefeuille** s'applique ;
        - la date **sans nom** (`[pea]`) ne s'applique que s'il n'y a qu'un portefeuille :
          avec plusieurs, on ne sait pas à qui elle est, et elle est écartée en le disant ;
        - elle ne s'applique jamais à l'export d'un tiers, lu avec `--export`.

        Une date écrite pour un portefeuille qui n'existe pas — renommé, supprimé — est
        signalée, et n'est reportée sur aucun autre.
        """
        noms = {nom.casefold(): nom for nom in tous}
        if portefeuille is not None:
            noms.setdefault(portefeuille.casefold(), portefeuille)
        ecartees = [
            f"{NOM_FICHIER} corrige la date du PEA du portefeuille « {nom} », qui n'existe "
            "pas (renommé ou supprimé ?) : cette correction ne s'applique à aucun autre."
            for nom in sorted(self.par_portefeuille)
            if not tiers and nom.casefold() not in noms
        ]
        if portefeuille is not None and not tiers:
            for nom, date in self.par_portefeuille.items():
                if nom.casefold() == portefeuille.casefold():
                    return CorrectionDuPea(date, tuple(ecartees))
        if self.premier_versement_pea is None:
            return CorrectionDuPea(None, tuple(ecartees))
        if tiers:
            ecartees.append(
                f"La date du PEA écrite dans {NOM_FICHIER} est la vôtre : elle ne s'applique "
                "pas à l'export d'un tiers."
            )
        elif len(noms) > 1:
            ecartees.append(
                f"{NOM_FICHIER} donne une date d'ouverture de PEA sans dire pour quel "
                f"portefeuille, et il y en a {len(noms)} : elle n'est appliquée à aucun. "
                f"Écrivez-la sous [portefeuille.\"{portefeuille}\".pea] si elle est celle "
                "de ce portefeuille."
            )
        else:
            return CorrectionDuPea(self.premier_versement_pea, tuple(ecartees))
        return CorrectionDuPea(None, tuple(ecartees))


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

    portefeuilles = contenu.get("portefeuille", {})
    if not isinstance(portefeuilles, dict):
        raise ConfigurationInvalide(
            f"{fichier} : une date par portefeuille s'écrit sous [portefeuille.\"Nom\".pea]"
        )
    par_portefeuille: dict[str, Date] = {}
    for nom, sections in portefeuilles.items():
        date = _premier_versement(
            sections.get("pea", {}) if isinstance(sections, dict) else sections,
            fichier,
            f'[portefeuille."{nom}".pea]',
        )
        if date is not None:
            par_portefeuille[nom] = date
    return ConfigurationFiscale(
        premier_versement_pea=_premier_versement(contenu.get("pea", {}), fichier, "[pea]"),
        par_portefeuille=par_portefeuille,
    )


def _premier_versement(pea: object, fichier: Path, section: str) -> Date | None:
    """La date écrite dans une section, contrôlée ; `None` si elle n'y est pas."""
    if not isinstance(pea, dict):
        raise ConfigurationInvalide(f"{fichier} : la section {section} doit être un tableau")

    brut = pea.get("premier_versement")
    if brut is None or (isinstance(brut, str) and brut.strip() == ""):
        return None
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
    return brut
