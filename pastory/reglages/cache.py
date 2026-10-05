"""Le cache des valeurs trouvées en ligne : `cache/reglages.csv` (D-80).

Une recherche coûte des appels réseau, et surtout **une valeur ne doit pas changer en silence**
d'un lancement à l'autre. Chaque valeur trouvée — cotation, frais courants, contenu — est donc
gardée ici avec son origine complète, et relue telle quelle. Les trous sont gardés aussi, pour
ne pas refaire à chaque lancement une recherche qui vient d'échouer.

Trois durées de vie, et chacune a sa raison :

- **une cotation trouvée ne se recherche jamais d'elle-même.** Les cours d'un actif sont gardés
  pour toujours (D-50) avec le ticker qui les a donnés : changer de ticker en route mêlerait
  deux places de cotation dans une même série ;
- **des frais courants ou un contenu** se revérifient au bout de `DUREE_D_UNE_VALEUR` : un TER
  baisse, et la source se met à jour ;
- **un trou** se retente au bout de `DUREE_D_UN_TROU` : la source a pu ajouter le fonds, ou le
  réseau était coupé.

Le fichier reste un CSV aux conventions du projet, ouvrable dans un tableur : c'est ce qui permet
de vérifier une valeur sans lire de code. Il vit dans le dossier de cache personnel, hors du
dossier synchronisé et hors de git (D-01, D-37). L'effacer n'est jamais grave : tout se retrouve.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path

from pastory import tableur
from pastory.config import emplacements
from pastory.config.actifs import ContenuActif
from pastory.donnees_externes.cache import CacheIllisible
from pastory.reglages import Cotation, Origine, Trou, Trouvee

NOM_FICHIER = "reglages.csv"

DUREE_D_UNE_VALEUR = timedelta(days=30)
DUREE_D_UN_TROU = timedelta(days=7)

COLONNES = (
    "actif",
    "reglage",
    "valeur",
    "devise",
    "place",
    "nom",
    "source",
    "date",
    "controle",
    "reserve",
    "intitule_de_la_date",
    "introuvable",
    "recupere_le",
)


class Champ(StrEnum):
    COTATION = "cotation"
    TER = "ter"
    CONTENU = "contenu"


@dataclass(frozen=True)
class EnMemoire:
    """Une ligne du cache : une valeur trouvée ou un trou, et le jour où on l'a établi."""

    resultat: Trouvee | Trou
    recupere_le: Date

    def perimee(self, champ: Champ, aujourd_hui: Date) -> bool:
        """Vrai s'il faut chercher de nouveau. Une cotation trouvée ne l'est jamais."""
        if isinstance(self.resultat, Trou):
            return aujourd_hui - self.recupere_le >= DUREE_D_UN_TROU
        if champ is Champ.COTATION:
            return False
        return aujourd_hui - self.recupere_le >= DUREE_D_UNE_VALEUR


class CacheDesReglages:
    """Les valeurs déjà trouvées, par actif et par réglage."""

    def __init__(
        self, fichier: Path | None = None, environnement: Mapping[str, str] | None = None
    ) -> None:
        self.fichier = (
            fichier
            if fichier is not None
            else emplacements.dossier_cache(environnement) / NOM_FICHIER
        )
        self._lignes: dict[tuple[str, Champ], EnMemoire] | None = None

    def lire(self, actif: str, champ: Champ) -> EnMemoire | None:
        return self._tout().get((actif, champ))

    def ecrire(self, actif: str, champ: Champ, resultat: Trouvee | Trou, le: Date) -> None:
        """Remplace ce qui était connu pour ce réglage, et réécrit le fichier."""
        self._tout()[(actif, champ)] = EnMemoire(resultat, le)
        lignes = [
            _ligne(un_actif, un_champ, en_memoire)
            for (un_actif, un_champ), en_memoire in sorted(self._tout().items())
        ]
        tableur.ecrire(COLONNES, tuple(lignes), self.fichier)

    def oublier(self, actif: str | None = None) -> list[str]:
        """Oublie les réglages d'un actif, ou de tous : la prochaine exécution les recherchera.
        Renvoie les actifs oubliés."""
        tout = self._tout()
        oublies = sorted({un for un, _ in tout if actif is None or un == actif})
        for cle in [cle for cle in tout if cle[0] in oublies]:
            del tout[cle]
        if self.fichier.exists():
            if tout:
                tableur.ecrire(
                    COLONNES,
                    tuple(_ligne(a, c, m) for (a, c), m in sorted(tout.items())),
                    self.fichier,
                )
            else:
                self.fichier.unlink()
        return oublies

    # --- Lecture du fichier ---------------------------------------------------------------

    def _tout(self) -> dict[tuple[str, Champ], EnMemoire]:
        if self._lignes is None:
            self._lignes = self._charger()
        return self._lignes

    def _charger(self) -> dict[tuple[str, Champ], EnMemoire]:
        if not self.fichier.exists():
            return {}
        lignes: dict[tuple[str, Champ], EnMemoire] = {}
        with self.fichier.open("r", encoding=tableur.ENCODAGE, newline="") as flux:
            for numero, brute in enumerate(
                csv.DictReader(flux, delimiter=tableur.SEPARATEUR), start=2
            ):
                actif = (brute.get("actif") or "").strip()
                if not actif:
                    raise self._illisible(numero, "la colonne « actif » est vide")
                try:
                    champ = Champ((brute.get("reglage") or "").strip())
                except ValueError:
                    raise self._illisible(numero, "réglage inconnu") from None
                lignes[(actif, champ)] = EnMemoire(
                    self._resultat(champ, brute, numero),
                    self._jour(brute.get("recupere_le"), numero),
                )
        return lignes

    def _resultat(self, champ: Champ, brute: dict, numero: int) -> Trouvee | Trou:
        introuvable = (brute.get("introuvable") or "").strip()
        if introuvable:
            return Trou(introuvable)
        valeur = (brute.get("valeur") or "").strip()
        if not valeur:
            raise self._illisible(numero, "ni valeur ni motif")
        origine = Origine(
            source=(brute.get("source") or "").strip(),
            date=self._jour(brute.get("date"), numero) if brute.get("date") else None,
            controle=(brute.get("controle") or "").strip() or None,
            reserve=(brute.get("reserve") or "").strip() or None,
            intitule_de_la_date=(brute.get("intitule_de_la_date") or "").strip() or "au",
        )
        if champ is Champ.COTATION:
            devise = (brute.get("devise") or "").strip()
            if not devise:
                raise self._illisible(numero, "une cotation sans devise")
            return Trouvee(
                Cotation(
                    ticker=valeur,
                    devise=devise,
                    place=(brute.get("place") or "").strip() or None,
                    nom=(brute.get("nom") or "").strip() or None,
                ),
                origine,
            )
        if champ is Champ.TER:
            try:
                return Trouvee(Decimal(valeur.replace(",", ".")), origine)
            except InvalidOperation:
                raise self._illisible(numero, f"« {valeur} » n'est pas un taux") from None
        try:
            return Trouvee(ContenuActif(valeur), origine)
        except ValueError:
            raise self._illisible(numero, f"« {valeur} » n'est pas un contenu connu") from None

    def _jour(self, texte: str | None, numero: int) -> Date:
        try:
            return Date.fromisoformat((texte or "").strip())
        except ValueError:
            raise self._illisible(numero, f"« {texte} » n'est pas une date") from None

    def _illisible(self, numero: int, probleme: str) -> CacheIllisible:
        return CacheIllisible(
            f"{self.fichier}, ligne {numero} : {probleme}. Ce fichier n'est qu'une copie "
            "locale de ce qui a été trouvé : supprimez-le, et tout sera recherché de nouveau."
        )


def _ligne(actif: str, champ: Champ, en_memoire: EnMemoire) -> dict[str, str]:
    ligne = dict.fromkeys(COLONNES, "")
    ligne["actif"] = actif
    ligne["reglage"] = champ.value
    ligne["recupere_le"] = en_memoire.recupere_le.isoformat()
    resultat = en_memoire.resultat
    if isinstance(resultat, Trou):
        ligne["introuvable"] = resultat.motif
        return ligne
    valeur = resultat.valeur
    if isinstance(valeur, Cotation):
        ligne.update(
            valeur=valeur.ticker,
            devise=valeur.devise,
            place=valeur.place or "",
            nom=valeur.nom or "",
        )
    elif champ is Champ.TER:
        ligne["valeur"] = tableur.nombre(valeur)
    else:
        ligne["valeur"] = str(getattr(valeur, "value", valeur))
    origine = resultat.origine
    ligne.update(
        source=origine.source,
        date=origine.date.isoformat() if origine.date else "",
        controle=origine.controle or "",
        reserve=origine.reserve or "",
        intitule_de_la_date=origine.intitule_de_la_date,
    )
    return ligne
