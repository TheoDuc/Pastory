"""Le cache local des cours : un fichier par actif, définitif, et oubliable (D-50).

Trois raisons d'être, dans cet ordre :

1. **la stabilité.** Un cours écrit n'est jamais redemandé : le montant vu hier est celui
   qu'on revoit aujourd'hui. C'est la condition d'une vérification à la main — un chiffre qui
   bouge tout seul entre deux lancements n'est pas vérifiable ;
2. **l'indépendance du réseau.** Le tableau de bord doit s'ouvrir et afficher une valeur sans
   rien demander à personne (D-49, et la source peut limiter son débit) ;
3. **la relecture.** Chaque fichier est un CSV aux conventions du projet, que le propriétaire
   peut ouvrir dans un tableur pour confronter un cours à son application.

Un cours déjà présent n'est **jamais réécrit**, même si la source en renvoie un autre : c'est
exactement ce que D-50 promet. Quand il faut vraiment reprendre les chiffres — correction de la
source, regroupement d'actions — c'est `oublier()`, appelée explicitement par l'utilisateur.

Les fichiers vivent dans le dossier de cache personnel, hors du dossier synchronisé et hors de
git (D-01, D-37).
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dashboard_tr import tableur
from dashboard_tr.config import emplacements
from dashboard_tr.donnees_externes.cours import Cours

NOM_DOSSIER = "cours"

COLONNES = ("date", "cours", "devise", "place", "ticker", "source", "recupere_le")
"""Les colonnes du fichier, dans l'ordre où on les lit : le jour décrit, le cours, puis tout
ce qui permet de savoir d'où il vient."""

CARACTERES_INTERDITS = re.compile(r"[^A-Za-z0-9._-]")
"""Un identifiant d'actif vient d'un fichier écrit à la main : il ne doit pas pouvoir
désigner un autre dossier. Les ISIN et les codes crypto n'en sont pas affectés."""


class CacheIllisible(Exception):
    """Un fichier de cache existe mais ne se relit pas.

    Ce n'est jamais grave : le cache se reconstruit. Le message dit donc quoi faire plutôt que
    de laisser l'utilisateur devant une trace technique.
    """


@dataclass(frozen=True)
class ResumeActif:
    """De quoi rendre compte du cache d'un actif sans afficher tous ses cours."""

    actif: str
    nombre: int
    premier_jour: Date | None
    dernier_jour: Date | None
    place: str | None
    source: str | None


class Cache:
    """Les cours déjà connus, rangés par actif."""

    def __init__(
        self,
        dossier: Path | None = None,
        environnement: Mapping[str, str] | None = None,
    ) -> None:
        self.dossier = (
            dossier if dossier is not None else emplacements.dossier_cache(environnement)
        ) / NOM_DOSSIER

    # --- Lecture ------------------------------------------------------------------------

    def chemin(self, actif: str) -> Path:
        return self.dossier / f"{_nom_de_fichier(actif)}.csv"

    def lire(self, actif: str) -> dict[Date, Cours]:
        """Les cours connus de cet actif, par jour. Un fichier absent donne un cache vide."""
        fichier = self.chemin(actif)
        if not fichier.exists():
            return {}

        serie: dict[Date, Cours] = {}
        with fichier.open("r", encoding=tableur.ENCODAGE, newline="") as flux:
            for numero, brute in enumerate(
                csv.DictReader(flux, delimiter=tableur.SEPARATEUR), start=2
            ):
                cours = _lire_ligne(actif, brute, fichier, numero)
                serie[cours.date] = cours
        return serie

    def actifs(self) -> list[str]:
        """Les actifs pour lesquels un fichier existe, dans l'ordre alphabétique."""
        if not self.dossier.exists():
            return []
        return sorted(fichier.stem for fichier in self.dossier.glob("*.csv"))

    def resume(self, actif: str) -> ResumeActif:
        """Ce que le cache sait de cet actif, pour les rapports."""
        serie = self.lire(actif)
        if not serie:
            return ResumeActif(actif, 0, None, None, None, None)

        dernier = serie[max(serie)]
        return ResumeActif(
            actif=actif,
            nombre=len(serie),
            premier_jour=min(serie),
            dernier_jour=max(serie),
            place=dernier.place,
            source=dernier.source,
        )

    # --- Écriture -----------------------------------------------------------------------

    def ecrire(self, actif: str, cours: Iterable[Cours]) -> int:
        """Ajoute des cours sans jamais écraser ceux déjà connus (D-50).

        Renvoie le nombre de cours **nouvellement** enregistrés : c'est ce que les rapports
        annoncent, et c'est zéro quand tout était déjà là.
        """
        existants = self.lire(actif)
        nouveaux = {
            un_cours.date: un_cours
            for un_cours in cours
            if un_cours.date not in existants
        }
        if not nouveaux:
            return 0

        serie = existants | nouveaux
        tableur.ecrire(
            COLONNES,
            (_ligne(serie[jour]) for jour in sorted(serie)),
            self.chemin(actif),
        )
        return len(nouveaux)

    def oublier(self, actif: str | None = None) -> list[str]:
        """Supprime le cache d'un actif, ou de tous. Renvoie les actifs oubliés.

        C'est la commande explicite de D-50 : elle existe pour les deux cas où un cours passé
        change vraiment — une correction de la source, et un regroupement d'actions, qui
        réécrit d'un coup toute la série d'un actif.
        """
        concernes = [actif] if actif is not None else self.actifs()
        oublies: list[str] = []
        for un_actif in concernes:
            fichier = self.chemin(un_actif)
            if fichier.exists():
                fichier.unlink()
                oublies.append(un_actif)
        return oublies


# --- Une ligne du fichier ---------------------------------------------------------------


def _ligne(cours: Cours) -> dict[str, str]:
    return {
        "date": cours.date.isoformat(),
        "cours": tableur.nombre(cours.valeur),
        "devise": cours.devise,
        "place": cours.place,
        "ticker": cours.ticker or "",
        "source": cours.source,
        "recupere_le": cours.recupere_le.isoformat(),
    }


def _lire_ligne(actif: str, brute: Mapping[str, str], fichier: Path, numero: int) -> Cours:
    return Cours(
        actif=actif,
        date=_jour(brute.get("date"), fichier, numero),
        valeur=_montant(brute.get("cours"), fichier, numero),
        devise=(brute.get("devise") or "").strip(),
        place=(brute.get("place") or "").strip(),
        source=(brute.get("source") or "").strip(),
        recupere_le=_jour(brute.get("recupere_le"), fichier, numero),
        ticker=(brute.get("ticker") or "").strip() or None,
    )


def _jour(texte: str | None, fichier: Path, numero: int) -> Date:
    try:
        return Date.fromisoformat((texte or "").strip())
    except ValueError as erreur:
        raise _illisible(fichier, numero, f"« {texte} » n'est pas une date") from erreur


def _montant(texte: str | None, fichier: Path, numero: int) -> Decimal:
    """Relit un nombre écrit à la française, en tolérant ce qu'un tableur peut ajouter.

    Le fichier est écrit par l'application, mais rien n'empêche le propriétaire de l'ouvrir
    dans un tableur et de l'enregistrer : un espace de milliers ne doit pas tout casser.
    """
    nettoye = (texte or "").replace(" ", "").replace(" ", "").replace(" ", "")
    nettoye = nettoye.replace(",", ".")
    try:
        valeur = Decimal(nettoye)
    except InvalidOperation as erreur:
        raise _illisible(fichier, numero, f"« {texte} » n'est pas un nombre") from erreur

    # `Decimal` accepte « nan » et « inf ». Les laisser passer serait pire qu'une erreur de
    # lecture : un total deviendrait « nan » sans que rien ne le signale, ou l'affichage
    # planterait bien plus loin, sur un fichier qu'on ne soupçonnerait plus.
    if not valeur.is_finite():
        raise _illisible(fichier, numero, f"« {texte} » n'est pas un nombre utilisable")
    if valeur < 0:
        raise _illisible(fichier, numero, f"« {texte} » est un cours négatif")
    return valeur


def _illisible(fichier: Path, numero: int, probleme: str) -> CacheIllisible:
    return CacheIllisible(
        f"{fichier}, ligne {numero} : {probleme}. Ce fichier est un cache, il se "
        f"reconstruit : lancez « dashboard oublier-cours » puis « dashboard cours »."
    )


def _nom_de_fichier(actif: str) -> str:
    nom = CARACTERES_INTERDITS.sub("_", actif.strip())
    if not nom or set(nom) <= {".", "_", "-"}:
        raise ValueError(f"identifiant d'actif inutilisable comme nom de fichier : {actif!r}")
    return nom
