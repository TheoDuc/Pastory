"""Le cache local des compositions : un fichier par actif, **daté et remplaçable** (D-70).

C'est le frère du cache des cours, avec une différence qui est toute la décision
[D-70](../../docs/decisions.md) : un cours passé ne change jamais, donc il est écrit une fois pour
toutes ([D-50](../../docs/decisions.md)) ; une composition d'ETF change chaque mois. Ici, une
nouvelle composition **remplace** l'ancienne, et le fichier ne garde que la dernière connue.

Pourquoi ne pas garder l'historique : il ne servirait à rien. Une répartition est une photo du
jour ([glossaire §8](../../docs/glossaire.md)), jamais une série ; et garder trois arrêtés d'un
même fonds inviterait à les comparer alors que la source ne garantit pas leur continuité.

Le fichier reste un CSV aux conventions du projet, ouvrable dans un tableur : c'est ce qui permet
de confronter un pourcentage à la fiche de l'émetteur sans lire une ligne de code. Les colonnes
d'origine — l'arrêté, la source, le jour de récupération — sont répétées sur chaque ligne, comme
dans le cache des cours, parce qu'un tableur n'a pas d'en-tête de document.

Les fichiers vivent dans le dossier de cache personnel, hors du dossier synchronisé et hors de
git (D-01, D-37).
"""

from __future__ import annotations

import csv
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pastory import tableur
from pastory.config import emplacements
from pastory.donnees_externes.cache import CacheIllisible
from pastory.donnees_externes.composition import Composition, Part, Rubrique

NOM_DOSSIER = "compositions"

COLONNES = (
    "rubrique",
    "code",
    "poids_pour_cent",
    "arrete_le",
    "intitule_de_la_date",
    "replication",
    "document",
    "source",
    "recupere_le",
)

CARACTERES_INTERDITS = re.compile(r"[^A-Za-z0-9._-]")
"""Un identifiant d'actif vient d'un fichier écrit à la main : il ne doit pas pouvoir désigner un
autre dossier. Les ISIN et les codes crypto n'en sont pas affectés."""

VIDE = ""


@dataclass(frozen=True)
class ResumeComposition:
    """De quoi rendre compte du cache d'un actif sans réafficher tous ses pourcentages."""

    actif: str
    arrete_le: Date | None
    source: str | None
    nombre_de_pays: int
    nombre_de_secteurs: int
    replication: str | None


class CacheDeCompositions:
    """Les compositions déjà connues, une par actif."""

    def __init__(
        self,
        dossier: Path | None = None,
        environnement: Mapping[str, str] | None = None,
    ) -> None:
        self.dossier = (
            dossier
            if dossier is not None
            else emplacements.dossier_cache(environnement) / NOM_DOSSIER
        )

    def chemin(self, actif: str) -> Path:
        return self.dossier / f"{_nom_de_fichier(actif)}.csv"

    # --- Lecture ------------------------------------------------------------------------

    def lire(self, actif: str) -> Composition | None:
        """La composition connue de cet actif, ou `None`. Un fichier absent n'est pas une erreur."""
        fichier = self.chemin(actif)
        if not fichier.exists():
            return None

        parts: dict[Rubrique, list[Part]] = {rubrique: [] for rubrique in Rubrique}
        entete: dict[str, str] | None = None
        with fichier.open("r", encoding=tableur.ENCODAGE, newline="") as flux:
            for numero, brute in enumerate(
                csv.DictReader(flux, delimiter=tableur.SEPARATEUR), start=2
            ):
                rubrique = _rubrique(brute.get("rubrique"), fichier, numero)
                code = (brute.get("code") or "").strip()
                if not code:
                    raise _illisible(fichier, numero, "la colonne « code » est vide")
                parts[rubrique].append(
                    Part(code=code, pour_cent=_poids(brute.get("poids_pour_cent"), fichier, numero))
                )
                if entete is None:
                    entete = {cle: (brute.get(cle) or "") for cle in COLONNES}

        if entete is None:
            # Fichier réduit à son en-tête : rien à en tirer, et rien de grave. On le traite
            # comme une absence, ce qui le fera redemander puis réécrire.
            return None

        return Composition(
            actif=actif,
            pays=tuple(parts[Rubrique.PAYS]),
            secteurs=tuple(parts[Rubrique.SECTEUR]),
            classes=tuple(parts[Rubrique.CLASSE]),
            arrete_le=_jour(entete.get("arrete_le"), fichier, 2),
            intitule_de_la_date=entete.get("intitule_de_la_date", VIDE),
            source=entete.get("source", VIDE),
            recupere_le=_jour(entete.get("recupere_le"), fichier, 2),
            replication=entete.get("replication") or None,
            document=entete.get("document") or None,
        )

    def actifs(self) -> list[str]:
        """Les actifs pour lesquels un fichier existe, dans l'ordre alphabétique."""
        if not self.dossier.exists():
            return []
        return sorted(fichier.stem for fichier in self.dossier.glob("*.csv"))

    def resume(self, actif: str) -> ResumeComposition:
        """Ce que le cache sait de cet actif, pour les rapports."""
        composition = self.lire(actif)
        if composition is None:
            return ResumeComposition(actif, None, None, 0, 0, None)
        return ResumeComposition(
            actif=actif,
            arrete_le=composition.arrete_le,
            source=composition.source,
            nombre_de_pays=len(composition.pays),
            nombre_de_secteurs=len(composition.secteurs),
            replication=composition.replication,
        )

    # --- Écriture -----------------------------------------------------------------------

    def ecrire(self, composition: Composition) -> None:
        """Enregistre la composition, en **remplaçant** celle qui s'y trouvait (D-70)."""
        tableur.ecrire(
            COLONNES,
            tuple(_lignes(composition)),
            self.chemin(composition.actif),
        )

    def oublier(self, actif: str | None = None) -> list[str]:
        """Supprime la composition d'un actif, ou de tous. Renvoie les actifs oubliés."""
        concernes = [actif] if actif is not None else self.actifs()
        oublies: list[str] = []
        for un_actif in concernes:
            fichier = self.chemin(un_actif)
            if fichier.exists():
                fichier.unlink()
                oublies.append(un_actif)
        return oublies


# --- Les lignes du fichier --------------------------------------------------------------


def _lignes(composition: Composition):
    commun = {
        "arrete_le": composition.arrete_le.isoformat(),
        "intitule_de_la_date": composition.intitule_de_la_date,
        "replication": composition.replication or VIDE,
        "document": composition.document or VIDE,
        "source": composition.source,
        "recupere_le": composition.recupere_le.isoformat(),
    }
    for rubrique in Rubrique:
        for part in composition.parts(rubrique):
            yield {
                "rubrique": rubrique.value,
                "code": part.code,
                "poids_pour_cent": tableur.nombre(part.pour_cent),
                **commun,
            }


def _rubrique(texte: str | None, fichier: Path, numero: int) -> Rubrique:
    try:
        return Rubrique((texte or "").strip())
    except ValueError:
        raise _illisible(
            fichier,
            numero,
            f"« {texte} » n'est pas une rubrique connue "
            f"({', '.join(rubrique.value for rubrique in Rubrique)})",
        ) from None


def _jour(texte: str | None, fichier: Path, numero: int) -> Date:
    try:
        return Date.fromisoformat((texte or "").strip())
    except ValueError:
        raise _illisible(fichier, numero, f"« {texte} » n'est pas une date (2026-09-27)") from None


def _poids(texte: str | None, fichier: Path, numero: int) -> Decimal:
    brut = (texte or "").strip().replace(",", ".")
    try:
        return Decimal(brut)
    except InvalidOperation:
        raise _illisible(fichier, numero, f"« {texte} » n'est pas un pourcentage") from None


def _illisible(fichier: Path, numero: int, probleme: str) -> CacheIllisible:
    return CacheIllisible(
        f"{fichier}, ligne {numero} : {probleme}. Ce fichier n'est qu'une copie locale : "
        f"supprimez-le, ou lancez « pastory oublier-composition », et il sera redemandé."
    )


def _nom_de_fichier(actif: str) -> str:
    return CARACTERES_INTERDITS.sub("_", actif.strip()) or "_"
