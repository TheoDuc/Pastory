"""La lecture du contenu d'un fonds dans ses deux sources : `contenus.toml` (D-58, D-89).

Deux traductions, et rien d'autre : le couple « code, libellé » d'extraETF, et la lettre du code
CFI qui dit le contenu. Ce qui n'est pas dans la table ne se traduit pas : l'appelant le dit.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path

from pastory.config.actifs import ContenuActif
from pastory.parametres import DOSSIER, ParametresInvalides

FICHIER = DOSSIER / "contenus.toml"


@dataclass(frozen=True)
class LectureDesContenus:
    extraetf: Mapping[int, tuple[str, ContenuActif]]
    """Code → (libellé exigé, contenu)."""

    cfi: Mapping[str, tuple[int, Mapping[str, ContenuActif]]]
    """Famille (« CE ») → (position de la lettre, lettre → contenu)."""

    source: str
    verifie_le: Date

    def par_extraetf(self, code: int, libelle: str) -> ContenuActif | None:
        """Le contenu, si le code est connu **et** que son libellé est celui attendu."""
        attendu = self.extraetf.get(code)
        if attendu is None or attendu[0].casefold() != libelle.strip().casefold():
            return None
        return attendu[1]

    def par_cfi(self, codes: Iterable[str]) -> frozenset[ContenuActif]:
        """Les contenus que disent ces codes, lettres muettes exclues. Vide : le registre se
        tait ; plus d'un : il se contredit d'une plateforme à l'autre."""
        dits: set[ContenuActif] = set()
        for code in codes:
            famille = self.cfi.get(code[:2].upper())
            if famille is None:
                continue
            position, lettres = famille
            if len(code) >= position and (contenu := lettres.get(code[position - 1].upper())):
                dits.add(contenu)
        return frozenset(dits)


def charger(fichier: Path | None = None) -> LectureDesContenus:
    chemin = FICHIER if fichier is None else fichier
    try:
        contenu = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ParametresInvalides(f"{chemin} illisible : {erreur}") from erreur

    meta = contenu.get("meta")
    if not isinstance(meta, dict):
        raise ParametresInvalides(f"{chemin} : la table [meta] manque")
    source, verifie_le = meta.get("source"), meta.get("verifie_le")
    if not isinstance(source, str) or not source.strip() or not isinstance(verifie_le, Date):
        raise ParametresInvalides(
            f"{chemin} : [meta] doit porter une « source » et une date « verifie_le » (D-58)"
        )

    extraetf: dict[int, tuple[str, ContenuActif]] = {}
    for code, table in (contenu.get("extraetf") or {}).items():
        if not isinstance(table, dict) or not str(code).isdigit():
            raise ParametresInvalides(f"{chemin} : [extraetf.{code}] n'a pas la forme attendue")
        extraetf[int(code)] = (
            _texte(table, "libelle", f"extraetf.{code}", chemin),
            _contenu(table.get("contenu"), f"extraetf.{code}", chemin),
        )

    cfi: dict[str, tuple[int, dict[str, ContenuActif]]] = {}
    for famille, table in (contenu.get("cfi") or {}).items():
        if not isinstance(table, dict) or not isinstance(table.get("position"), int):
            raise ParametresInvalides(f"{chemin} : [cfi.{famille}] doit porter une « position »")
        lettres = {
            lettre.upper(): _contenu(valeur, f"cfi.{famille}.{lettre}", chemin)
            for lettre, valeur in table.items()
            if lettre != "position"
        }
        cfi[famille.upper()] = (table["position"], lettres)

    return LectureDesContenus(extraetf, cfi, source.strip(), verifie_le)


def _texte(table: dict, champ: str, ou: str, chemin: Path) -> str:
    valeur = table.get(champ)
    if not isinstance(valeur, str) or not valeur.strip():
        raise ParametresInvalides(f"{chemin} : [{ou}] doit porter « {champ} »")
    return valeur.strip()


def _contenu(valeur: object, ou: str, chemin: Path) -> ContenuActif:
    try:
        return ContenuActif(str(valeur))
    except ValueError:
        raise ParametresInvalides(
            f"{chemin} : [{ou}] donne un contenu inconnu ({valeur!r})"
        ) from None
