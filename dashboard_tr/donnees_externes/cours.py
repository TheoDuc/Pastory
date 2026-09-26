"""Le contrat de la couche « cours » : ce qu'un cours est, et comment on l'obtient.

Deux principes, qui expliquent presque tout le fichier :

1. **un cours porte son origine.** Sa place de cotation, sa source, le jour qu'il décrit et le
   jour où il a été récupéré. Sans cela, un cache définitif (D-50) deviendrait un cache
   opaque, et le propriétaire ne pourrait pas confronter un chiffre à son application ;
2. **on refuse plutôt que d'estimer.** Actif non déclaré, devise inattendue, aucun cours à la
   date demandée : la réponse est `None` **avec un motif lisible**, jamais une valeur par
   défaut (D-45). Un chiffre crédible et faux est pire qu'un trou signalé.

La source elle-même est interchangeable (`SourceDeCours`) : le reste de l'application ne sait
pas de qui viennent les cours, exactement comme le moteur ne sait pas de quelle banque
viennent les opérations (D-26).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from typing import Protocol

from dashboard_tr.config.actifs import Configuration, Declaration

RECUL_MAXIMAL = timedelta(days=10)
"""Jusqu'où remonter quand le jour demandé n'est pas coté.

Un jour sans cours est normal — week-end, jour férié, suspension — et on prend alors le
**dernier jour coté**, sans jamais interpoler. Mais au-delà d'une dizaine de jours, ce n'est
plus un jour férié : c'est un actif qui ne cote plus, ou un mauvais ticker. Mieux vaut le dire
que valoriser sur un cours périmé.
"""

MARGE_AVANT = timedelta(days=30)
"""Combien de jours demander avant la date cherchée : de quoi couvrir un pont, une
suspension, et le recul maximal ci-dessus, en un seul appel."""

MARGE_APRES = timedelta(days=3)
"""Et après : une opération passée le soir peut tomber un jour non encore coté."""


@dataclass(frozen=True)
class Cours:
    """Un cours de clôture, avec tout ce qu'il faut pour le vérifier à la main."""

    actif: str
    """ISIN, ou code interne pour la crypto — l'identifiant du pivot."""

    date: Date
    """Jour que ce cours décrit. Peut être **antérieur** au jour demandé (dernier jour coté)."""

    valeur: Decimal
    """Cours de clôture **brut**, jamais retraité des dividendes (D-51)."""

    devise: str
    place: str
    """Place de cotation telle que la source la nomme, pour que D-48 soit vérifiable."""

    source: str
    recupere_le: Date

    ticker: str | None = None
    """Le ticker interrogé. Gardé pour que le cache dise sur quoi le cours a été pris : un
    ticker corrigé dans `actifs.toml` doit se voir."""


@dataclass(frozen=True)
class Refus:
    """Pourquoi un cours n'a pas pu être donné. Destiné à être lu tel quel."""

    actif: str
    categorie: str
    """Nom court, pour regrouper : « actif non déclaré », « cours indisponible »…"""

    motif: str
    """Phrase en français, qui dit quoi faire quand il y a quelque chose à faire."""

    date: Date | None = None


class ErreurDeSource(Exception):
    """La source n'a pas pu répondre, ou a répondu quelque chose d'inutilisable.

    Les appelants ne la laissent jamais remonter jusqu'à l'utilisateur : elle devient un
    `Refus`, et le calcul continue sans le cours manquant. Chaque erreur porte sa `categorie`,
    pour que l'ajout d'un cas plus tard n'oblige pas à retoucher tous les appelants.
    """

    categorie = "source injoignable"


class SourceInjoignable(ErreurDeSource):
    """Réseau coupé, service indisponible, réponse illisible."""


class TickerInconnu(ErreurDeSource):
    """La source ne connaît pas ce ticker : presque toujours une faute dans `actifs.toml`."""

    categorie = "ticker inconnu"


class DeviseInattendue(ErreurDeSource):
    """La source répond dans une autre monnaie que celle déclarée (D-48).

    C'est le garde-fou principal de l'étape : rien n'est converti, rien n'est utilisé.
    """

    categorie = "devise inattendue"


class ReponseIncoherente(ErreurDeSource):
    """La réponse ne décrit pas ce qu'on a demandé — par exemple une série mensuelle là où
    on a demandé du quotidien."""

    categorie = "réponse incohérente"


class SourceDeCours(Protocol):
    """Ce qu'une source doit savoir faire. Une seule méthode, et un nom.

    Elle reçoit la déclaration de l'utilisateur (ticker **et** devise attendue) parce que
    c'est elle qui voit ce que le service renvoie : la confrontation des devises se fait donc
    au plus près de la donnée.
    """

    nom: str

    def serie(
        self, actif: str, declaration: Declaration, debut: Date, fin: Date
    ) -> list[Cours]:
        """Les cours de clôture connus entre ces deux jours, bornes comprises.

        Lève `ErreurDeSource` si la réponse n'est pas exploitable. Renvoie une liste vide si
        le service répond correctement mais ne connaît aucun cours sur la période.
        """
        ...


class CacheDeCours(Protocol):
    """Ce que le fournisseur attend d'un cache. Voir `cache.py` pour la mise en œuvre."""

    def lire(self, actif: str) -> dict[Date, Cours]: ...

    def ecrire(self, actif: str, cours: Iterable[Cours]) -> int: ...


def dernier_jour_cote(
    serie: Mapping[Date, Cours], date: Date, recul: timedelta = RECUL_MAXIMAL
) -> Cours | None:
    """Le cours du jour demandé, ou à défaut celui du dernier jour coté avant lui.

    Jamais de moyenne, jamais d'interpolation : on rend un cours qui a réellement existé, et
    il porte sa vraie date pour que l'écart soit visible.
    """
    if not serie:
        return None
    candidats = [jour for jour in serie if date - recul <= jour <= date]
    if not candidats:
        return None
    return serie[max(candidats)]


class FournisseurDeCours:
    """La façade : la configuration de l'utilisateur, le cache, et une source.

    C'est le seul objet que le reste de l'application manipule. Il ne lève pas d'exception
    sur un cours manquant : il accumule des `Refus` que l'appelant affiche.
    """

    def __init__(
        self,
        configuration: Configuration,
        cache: CacheDeCours,
        source: SourceDeCours | None = None,
        *,
        hors_ligne: bool = False,
        aujourd_hui: Date | None = None,
    ) -> None:
        self.configuration = configuration
        self.cache = cache
        self.source = source
        self.hors_ligne = hors_ligne or source is None
        self.aujourd_hui = aujourd_hui or Date.today()
        self._series: dict[str, dict[Date, Cours]] = {}
        self._refus: dict[tuple[str, str], Refus] = {}
        self._deja_demande: set[str] = set()

    # --- Ce que les appelants utilisent -------------------------------------------------

    def cours(self, actif: str, date: Date) -> Cours | None:
        """Le cours d'un actif à une date, ou `None` avec un refus enregistré."""
        declaration = self.configuration.declaration(actif)
        if declaration is None:
            self._refuser(
                actif,
                "actif non déclaré",
                "aucun ticker déclaré pour cet actif : lancez « dashboard actifs » pour "
                "dire où chercher son cours",
            )
            return None

        trouve = dernier_jour_cote(self._serie(actif), date)
        if trouve is not None:
            return trouve

        if self.hors_ligne:
            self._refuser(
                actif,
                "cours indisponible",
                f"aucun cours au {date.isoformat()} dans le cache, et le réseau n'est pas "
                "utilisé : lancez « dashboard cours » pour le compléter",
                date=date,
            )
            return None

        # Un actif dont la source ne sait rien ne doit pas être redemandé à chaque opération :
        # une seule tentative par actif et par exécution.
        if actif not in self._deja_demande:
            self.remplir(actif, date - MARGE_AVANT, min(date + MARGE_APRES, self.aujourd_hui))
            trouve = dernier_jour_cote(self._serie(actif), date)
            if trouve is not None:
                return trouve

        if not self._a_deja_refuse(actif):
            self._refuser(
                actif,
                "cours indisponible",
                f"la source ne donne aucun cours au {date.isoformat()}, ni dans les "
                f"{RECUL_MAXIMAL.days} jours qui précèdent",
                date=date,
            )
        return None

    def remplir(self, actif: str, debut: Date, fin: Date) -> int:
        """Demande une période à la source et l'écrit dans le cache. Renvoie le nombre de
        cours **nouvellement** enregistrés.

        Utilisée par `dashboard cours`, et par `cours()` quand le cache ne suffit pas.
        """
        declaration = self.configuration.declaration(actif)
        if declaration is None or self.source is None:
            return 0

        self._deja_demande.add(actif)
        if fin < debut:
            return 0

        try:
            recus = self.source.serie(actif, declaration, debut, fin)
        except ErreurDeSource as erreur:
            self._refuser(actif, erreur.categorie, str(erreur))
            return 0

        if not recus:
            # La source a répondu, mais elle ne connaît aucun cours sur la période. C'est le
            # symptôme d'un ticker qui existe sans coter — ou qui n'est pas celui qu'on croit.
            self._refuser(
                actif,
                "cours indisponible",
                f"la source n'a renvoyé aucun cours entre le {debut.isoformat()} et le "
                f"{fin.isoformat()} pour « {declaration.ticker} » : vérifiez ce ticker dans "
                "« actifs.toml »",
            )
            return 0

        ecrits = self.cache.ecrire(actif, recus)
        self._series.pop(actif, None)
        return ecrits

    @property
    def nom_source(self) -> str:
        """Le nom de la source réellement utilisée, pour les rapports.

        Hors ligne, il n'y en a pas : ce qui s'affiche vient alors du cache, et le dire
        évite de laisser croire qu'un appel a été fait."""
        return self.source.nom if self.source is not None and not self.hors_ligne else "cache local"

    @property
    def refus(self) -> list[Refus]:
        """Tous les refus rencontrés, sans doublon, dans l'ordre d'apparition."""
        return list(self._refus.values())

    # --- Interne ------------------------------------------------------------------------

    def _serie(self, actif: str) -> dict[Date, Cours]:
        if actif not in self._series:
            self._series[actif] = self.cache.lire(actif)
        return self._series[actif]

    def _refuser(self, actif: str, categorie: str, motif: str, date: Date | None = None) -> None:
        # Un seul refus par actif et par catégorie : sur un portefeuille où un actif porte
        # dix opérations, répéter dix fois le même message ferait perdre les autres.
        self._refus.setdefault(
            (actif, categorie), Refus(actif=actif, categorie=categorie, motif=motif, date=date)
        )

    def _a_deja_refuse(self, actif: str) -> bool:
        return any(cle[0] == actif for cle in self._refus)
