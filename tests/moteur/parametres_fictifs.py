"""Des paramètres de coûts et des règles fiscales écrits à la main, pour éprouver le moteur.

Le moteur ne demande que deux choses : un objet qui sait donner un taux pour un actif
(`ParametresDeCouts`) et un objet qui porte les taux fiscaux (`ReglesFiscales`). Ceux-ci les
satisfont sans lire aucun fichier — comme `cours_fictifs.py` remplace la source de cours.

**Valeurs fictives** (D-03), mais choisies égales à celles des fichiers livrés pour que les cas
du cahier de vérification soient les mêmes que ceux du rapport.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal

from dashboard_tr.pivot.operation import Poche


@dataclass(frozen=True)
class ParametreFictif:
    """La forme que le moteur attend d'un paramètre (`ParametreDate`), et rien de plus."""

    nom: str
    valeur: Decimal
    unite: str
    source: str = "source de test"
    en_vigueur_depuis: Date | None = Date(2026, 1, 1)
    verifie_le: Date | None = Date(2026, 9, 27)
    basse: Decimal | None = None
    haute: Decimal | None = None
    note: str = ""

    @property
    def en_clair(self) -> str:
        texte = format(self.valeur, "f").replace(".", ",")
        if self.unite == "pour cent":
            return f"{texte} %"
        if self.unite == "euros":
            return f"{texte} €"
        return f"{texte} {self.unite}"

    @property
    def origine(self) -> str:
        return f"vérifié le {self.verifie_le.isoformat()}" if self.verifie_le else ""


def taux(nom: str, valeur: str) -> ParametreFictif:
    return ParametreFictif(nom=nom, valeur=Decimal(valeur), unite="pour cent")


def euros(nom: str, valeur: str) -> ParametreFictif:
    return ParametreFictif(nom=nom, valeur=Decimal(valeur), unite="euros")


def annees(nom: str, valeur: str) -> ParametreFictif:
    return ParametreFictif(nom=nom, valeur=Decimal(valeur), unite="ans")


SPREAD_ETF = taux("spread_par_cote.etf", "0.05")
SPREAD_ACTION = taux("spread_par_cote.action", "0.10")
SPREAD_CRYPTO = taux("spread_par_cote.crypto", "0.50")
FRAIS_TITRES = euros("frais_par_ordre.titres", "1.00")
FRAIS_CRYPTO = euros("frais_par_ordre.crypto", "1.00")


class ParametresFictifs:
    """Répond ce qu'on lui a donné : `{actif: (type, TER)}`.

    Un actif absent n'a **pas de type** : c'est le cas que le moteur doit savoir dire, et non
    remplacer par une valeur par défaut (D-55).
    """

    def __init__(
        self,
        types: dict[str, str] | None = None,
        ter: dict[str, str] | None = None,
        spreads: dict[str, str] | None = None,
    ) -> None:
        self.types = dict(types or {})
        self.ter_declares = {actif: Decimal(valeur) for actif, valeur in (ter or {}).items()}
        self.spreads = {
            actif: Decimal(valeur) for actif, valeur in (spreads or {}).items()
        }

    def _type(self, actif: str, poche: Poche) -> str | None:
        if poche is Poche.CRYPTO:
            return "crypto"
        return self.types.get(actif)

    def spread_par_cote(self, actif: str, poche: Poche) -> ParametreFictif | None:
        if actif in self.spreads:
            return ParametreFictif(
                nom=f"spread déclaré pour {actif}",
                valeur=self.spreads[actif],
                unite="pour cent",
                source="déclaré dans le test",
            )
        return {
            "etf": SPREAD_ETF,
            "action": SPREAD_ACTION,
            "crypto": SPREAD_CRYPTO,
        }.get(self._type(actif, poche) or "")

    def attend_un_ter(self, actif: str, poche: Poche) -> bool:
        return self._type(actif, poche) == "etf"

    def ter(self, actif: str) -> ParametreFictif | None:
        if actif not in self.ter_declares:
            return None
        return ParametreFictif(
            nom=f"TER déclaré pour {actif}",
            valeur=self.ter_declares[actif],
            unite="pour cent",
            source="déclaré dans le test",
        )

    def frais_par_ordre(self, poche: Poche) -> ParametreFictif:
        return FRAIS_CRYPTO if poche is Poche.CRYPTO else FRAIS_TITRES


@dataclass(frozen=True)
class ReglesFictives:
    """Les taux fiscaux de 2026, tels que les fichiers livrés les portent."""

    impot_sur_le_revenu: ParametreFictif = taux("impot_sur_le_revenu.taux_forfaitaire", "12.8")
    prelevements_sociaux: ParametreFictif = taux("prelevements_sociaux.taux", "18.6")
    pea_duree_exoneration_ir: ParametreFictif = annees("pea.duree_exoneration_ir", "5")
    crypto_seuil_exoneration: ParametreFictif = euros("crypto.seuil_exoneration", "305")
    pea_premier_versement: Date | None = None


def regles(premier_versement_pea: Date | None = None) -> ReglesFictives:
    return ReglesFictives(pea_premier_versement=premier_versement_pea)
