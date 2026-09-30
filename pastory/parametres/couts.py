"""Les paramètres des coûts estimés, tels que le moteur les attend (D-17, D-56, D-58).

Deux choses sont réunies ici :

- le **barème** livré avec l'application (`couts.toml`) : frais par ordre, et spread par côté
  par type d'actif ;
- ce que l'utilisateur a **déclaré** dans `actifs.toml` : le type de chaque actif, son TER, et
  éventuellement son propre taux de spread.

`ParametresDuPortefeuille` les combine et répond, actif par actif, aux questions que
`moteur/couts.py` pose par son protocole `ParametresDeCouts`. Le moteur ne sait pas ce qu'est
un ETF ni un fichier TOML : il demande un taux pour un actif, et c'est ici qu'on décide.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pastory.config.actifs import Configuration, Declaration, TypeActif
from pastory.parametres import DOSSIER, ParametresInvalides
from pastory.parametres.lecture import Parametre
from pastory.parametres.lecture import charger as charger_parametres
from pastory.pivot.operation import Poche

FICHIER = DOSSIER / "couts.toml"

NATURES_DE_FRAIS = ("titres", "crypto", "plan")
TYPES_DE_SPREAD = tuple(type_actif.value for type_actif in TypeActif)

SOURCE_DECLAREE = "déclaré par vous dans actifs.toml"


@dataclass(frozen=True)
class Bareme:
    """Ce que `couts.toml` contient, vérifié."""

    frais_par_ordre: Mapping[str, Parametre]
    """Par nature : « titres », « crypto », « plan »."""

    spread_par_cote: Mapping[str, Parametre]
    """Par type d'actif : « etf », « action », « crypto »."""


def charger(fichier: Path | None = None) -> Bareme:
    chemin = FICHIER if fichier is None else fichier
    parametres = charger_parametres(chemin)

    def exiger(prefixe: str, cles: tuple[str, ...], unite: str) -> dict[str, Parametre]:
        trouves: dict[str, Parametre] = {}
        for cle in cles:
            nom = f"{prefixe}.{cle}"
            if nom not in parametres:
                raise ParametresInvalides(f"{chemin} : paramètre manquant [{nom}]")
            if parametres[nom].unite != unite:
                raise ParametresInvalides(
                    f"{chemin} : [{nom}] doit être en « {unite} », pas en "
                    f"« {parametres[nom].unite} »"
                )
            trouves[cle] = parametres[nom]
        return trouves

    return Bareme(
        frais_par_ordre=exiger("frais_par_ordre", NATURES_DE_FRAIS, "euros"),
        spread_par_cote=exiger("spread_par_cote", TYPES_DE_SPREAD, "pour cent"),
    )


class ParametresDuPortefeuille:
    """Le barème et les déclarations de l'utilisateur, vus actif par actif.

    Satisfait `moteur.couts.ParametresDeCouts` sans que le moteur le sache.
    """

    def __init__(self, bareme: Bareme, actifs: Configuration) -> None:
        self.bareme = bareme
        self.actifs = actifs

    def _declaration(self, actif: str) -> Declaration | None:
        return self.actifs.declaration(actif)

    def type_actif(self, actif: str, poche: Poche) -> TypeActif | None:
        """Le type déclaré ; une crypto l'est d'office par sa poche (D-55)."""
        if poche is Poche.CRYPTO:
            return TypeActif.CRYPTO
        declaration = self._declaration(actif)
        return declaration.type if declaration is not None else None

    def spread_par_cote(self, actif: str, poche: Poche) -> Parametre | None:
        """Le taux propre à l'actif s'il en a un, sinon celui de son type, sinon rien."""
        declaration = self._declaration(actif)
        if declaration is not None and declaration.spread_pour_cent is not None:
            return Parametre(
                nom=f"spread déclaré pour {actif}",
                valeur=declaration.spread_pour_cent,
                unite="pour cent",
                source=SOURCE_DECLAREE,
            )
        type_actif = self.type_actif(actif, poche)
        if type_actif is None:
            return None
        return self.bareme.spread_par_cote[type_actif.value]

    def attend_un_ter(self, actif: str, poche: Poche) -> bool:
        """Vrai pour un ETF : lui seul a des frais courants (D-17)."""
        return self.type_actif(actif, poche) is TypeActif.ETF

    def ter(self, actif: str) -> Parametre | None:
        """Le TER **validé** par l'utilisateur, ou rien : jamais une valeur devinée (D-61)."""
        declaration = self._declaration(actif)
        if declaration is None or declaration.ter_pour_cent is None:
            return None
        return Parametre(
            nom=f"TER déclaré pour {actif}",
            valeur=declaration.ter_pour_cent,
            unite="pour cent",
            source=SOURCE_DECLAREE,
        )

    def frais_par_ordre(self, poche: Poche) -> Parametre:
        """Ce qu'une vente coûterait : un ordre par ligne, crypto ou titres."""
        nature = "crypto" if poche is Poche.CRYPTO else "titres"
        return self.bareme.frais_par_ordre[nature]
