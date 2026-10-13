"""Le contrat de la couche « cours » : ce qu'un cours est, et comment on l'obtient.

Deux principes, qui expliquent presque tout le fichier :

1. **un cours porte son origine.** Sa place de cotation, sa source, le jour qu'il décrit et le
   jour où il a été récupéré. Sans cela, un cache définitif (D-50) deviendrait un cache
   opaque, et le propriétaire ne pourrait pas confronter un chiffre à son application ;
2. **on refuse plutôt que d'estimer.** Actif sans cotation, devise inattendue, aucun cours à la
   date demandée : la réponse est `None` **avec un motif lisible**, jamais une valeur par
   défaut (D-45). Un chiffre crédible et faux est pire qu'un trou signalé.

La source elle-même est interchangeable (`SourceDeCours`) : le reste de l'application ne sait
pas de qui viennent les cours, exactement comme le moteur ne sait pas de quelle banque
viennent les opérations (D-26).
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from typing import Protocol

from pastory.config.actifs import Configuration, Declaration

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

UN_JOUR = timedelta(days=1)

CATEGORIE_SANS_COTATION = "aucune cotation trouvée"
MOTIF_SANS_COTATION = (
    "aucune cotation en euros n'a été trouvée pour cet actif : il n'est pas valorisé, et il "
    "est signalé plutôt qu'estimé"
)
"""Le motif par défaut, quand la configuration ne dit pas pourquoi (D-45, D-80)."""

JOURS_SANS_COTATION_TOLERES = 5
"""Durée à partir de laquelle une période sans aucun cours devient suspecte.

Un week-end prolongé n'a rien d'anormal. Une semaine entière sans le moindre cours, si."""


@dataclass(frozen=True)
class Cours:
    """Un cours de clôture, avec tout ce qu'il faut pour le vérifier à la main."""

    actif: str
    """ISIN, ou code de la crypto donné par la banque — l'identifiant du pivot."""

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
    ticker qui change doit se voir."""


@dataclass(frozen=True)
class Refus:
    """Pourquoi un cours n'a pas pu être donné. Destiné à être lu tel quel."""

    actif: str
    categorie: str
    """Nom court, pour regrouper : « aucune cotation trouvée », « cours indisponible »…"""

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
    """La source ne connaît pas ce ticker : il ne cote plus, ou il a été mal écrit."""

    categorie = "ticker inconnu"


class PeriodeSansCours(ErreurDeSource):
    """La source connaît ce ticker, mais n'a aucun cours sur la période demandée — le plus
    souvent parce qu'il n'y était pas encore coté. Ce n'est ni une panne, ni un ticker
    inconnu ; la source ne dit pas pourquoi, et le message ne le suppose pas."""

    categorie = "période sans cours"


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

    def oublier(self, actif: str | None = None) -> list[str]: ...

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
        self._jours_tries: dict[str, list[Date]] = {}
        self._refus: dict[tuple[str, str], Refus] = {}
        self._demandes: dict[str, list[tuple[Date, Date]]] = {}
        self._en_panne: set[str] = set()

    # --- Ce que les appelants utilisent -------------------------------------------------

    def cours(self, actif: str, date: Date) -> Cours | None:
        """Le cours d'un actif à une date, ou `None` avec un refus enregistré."""
        declaration = self.configuration.declaration(actif)
        if declaration is None or declaration.ticker is None:
            self._refuser(
                actif,
                CATEGORIE_SANS_COTATION,
                self.configuration.sans_cotation.get(actif, MOTIF_SANS_COTATION),
            )
            return None

        if not self.hors_ligne:
            self._completer_la_fin(actif, date)
        trouve = self._dernier_jour_cote(actif, date)
        if trouve is not None:
            return trouve

        if self.hors_ligne:
            self._refuser(
                actif,
                "cours indisponible",
                f"aucun cours au {date.isoformat()} dans le cache, et le réseau n'est pas "
                "utilisé : lancez « pastory cours » pour le compléter",
                date=date,
            )
            return None

        # Une date déjà couverte par une demande précédente ne vaut pas un second appel : la
        # réponse serait la même. Mais une date **ailleurs** en vaut un — deux opérations sans
        # prix, à deux ans d'écart, ne se trouvent pas dans la même fenêtre, et ignorer la
        # seconde produirait un refus qui affirmerait à tort que la source ne sait rien.
        if not self._date_deja_demandee(actif, date):
            self.remplir(actif, date - MARGE_AVANT, min(date + MARGE_APRES, self.aujourd_hui))
            trouve = self._dernier_jour_cote(actif, date)
            if trouve is not None:
                return trouve

        # Quand la source est tombée en panne sur cet actif, son motif est déjà enregistré et
        # dit l'essentiel : ajouter « aucun cours au tel jour » par date ne ferait que noyer
        # le vrai message.
        if actif not in self._en_panne:
            self._refuser(
                actif,
                "cours indisponible",
                f"aucun cours au {date.isoformat()} ni dans les {RECUL_MAXIMAL.days} jours "
                "qui précèdent",
                date=date,
            )
        return None

    def remplir(self, actif: str, debut: Date, fin: Date) -> int:
        """Demande à la source **ce qui manque** sur cette période, et l'écrit dans le cache.

        Renvoie le nombre de cours **nouvellement** enregistrés. Trois raisons de ne rien
        demander du tout, et ce sont elles qui donnent son sens au cache (D-50) :

        - le cache couvre déjà la période : aucun appel ;
        - il en couvre le début : on ne demande que la suite. Relancer `pastory cours` le
          lendemain ne redemande donc qu'un jour, pas dix ans d'historique — ce qui compte,
          parce que la source limite son débit sans prévenir ;
        - la même période a déjà été demandée pendant cette exécution, ou la source est
          tombée en panne sur cet actif : on n'insiste pas.
        """
        declaration = self.configuration.declaration(actif)
        if (
            declaration is None
            or declaration.ticker is None
            or self.source is None
            or actif in self._en_panne
        ):
            return 0

        # La séance du jour n'est pas close : la source ne la rend pas, et le cache ne doit pas
        # la contenir. Demander le jour même ne rapporterait donc rien, et l'absence de réponse
        # ressemblerait à une panne.
        fin = min(fin, self.aujourd_hui - UN_JOUR)
        if fin < debut:
            # La période ne contenait que la séance du jour : il n'y a rien à demander. Sans
            # cet arrêt, la réduction ci-dessous rendait la période à l'envers — donc de
            # nouveau « valide » — et un cache à jour jusqu'à hier coûtait quand même un appel
            # par actif à chaque ouverture (trouvé en mesurant l'attente, D-110).
            return 0

        debut, fin = self._ce_qui_manque(actif, debut, fin)
        if fin < debut or self._deja_demande(actif, debut, fin):
            return 0
        self._demandes.setdefault(actif, []).append((debut, fin))

        try:
            recus = self.source.serie(actif, declaration, debut, fin)
        except ErreurDeSource as erreur:
            # Ticker faux, devise inattendue, réseau coupé : redemander le même actif dix fois
            # dans la même exécution ne donnerait rien de plus, et dix messages identiques
            # noieraient les autres.
            self._en_panne.add(actif)
            self._refuser(actif, erreur.categorie, str(erreur))
            return 0

        if not recus:
            # Sur une période courte, une réponse vide est normale : un week-end, un pont, un
            # jour férié. Ce n'est qu'au-delà qu'elle devient un symptôme — un ticker qui
            # existe sans coter, ou qui n'est pas celui qu'on croit.
            if (fin - debut).days >= JOURS_SANS_COTATION_TOLERES:
                self._refuser(
                    actif,
                    "cours indisponible",
                    f"la source n'a renvoyé aucun cours entre le {debut.isoformat()} et le "
                    f"{fin.isoformat()} pour « {declaration.ticker} » : ce ticker ne cote "
                    "plus, ou ne désigne pas cet actif",
                )
            return 0

        ecrits = self.cache.ecrire(actif, recus)
        self._series.pop(actif, None)
        self._jours_tries.pop(actif, None)
        return ecrits

    def jours_connus(self, actif: str) -> tuple[Date, Date] | None:
        """Le premier et le dernier jour gardés pour cet actif, ou `None` s'il n'y en a aucun.

        Sert à ne demander que ce qui peut encore manquer : ni ce qui précède le premier jour
        coté — la source n'a rien avant, et le redemander à chaque ouverture ne rapporterait
        rien —, ni la suite d'un titre vendu (D-110)."""
        serie = self._serie(actif)
        if not serie:
            return None
        return min(serie), max(serie)

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
        """Les cours gardés de l'actif, **pris sur sa cotation actuelle** seulement.

        Une cotation peut changer : corrigée par l'utilisateur, ou recherchée de nouveau
        (`pastory oublier-reglages`). Le cache étant tenu par actif, il garderait alors des cours
        de l'ancienne place à côté de ceux de la nouvelle — une série qui en mêle deux, et des
        écarts de quelques pour cent qui ne seraient ni des gains ni des pertes. Ces cours-là ne
        sont jamais employés ; en ligne, ils sont oubliés, et la série est reprise à la source
        (D-50, D-85). Un cours sans ticker (gardé avant qu'on l'enregistre) est présumé juste.
        """
        if actif not in self._series:
            serie = self.cache.lire(actif)
            declaration = self.configuration.declaration(actif)
            ticker = declaration.ticker if declaration is not None else None
            if ticker and any(
                cours.ticker and cours.ticker != ticker for cours in serie.values()
            ):
                if self.hors_ligne:
                    serie = {
                        jour: cours
                        for jour, cours in serie.items()
                        if not cours.ticker or cours.ticker == ticker
                    }
                else:
                    self.cache.oublier(actif)
                    serie = {}
            self._series[actif] = serie
        return self._series[actif]

    def _dernier_jour_cote(self, actif: str, date: Date) -> Cours | None:
        """Comme `dernier_jour_cote`, mais par recherche dichotomique dans les jours triés.

        La valorisation jour par jour demande un cours par actif et par jour calendaire sur
        toute la durée de détention : parcourir toute la série à chaque demande rendrait
        l'évolution lente à mesure que le cache grossit. Le résultat est le même.
        """
        serie = self._serie(actif)
        if not serie:
            return None
        if actif not in self._jours_tries:
            self._jours_tries[actif] = sorted(serie)
        jours = self._jours_tries[actif]
        rang = bisect.bisect_right(jours, date)
        if rang == 0:
            return None
        candidat = jours[rang - 1]
        if candidat < date - RECUL_MAXIMAL:
            return None
        return serie[candidat]

    def _completer_la_fin(self, actif: str, date: Date) -> None:
        """Demande la suite du cache quand on cherche un jour **après** son dernier jour connu.

        Sans cela, un cache arrêté au lundi servait encore le jeudi : le cours du lundi est dans
        le recul maximal, donc « trouvé », et rien n'était redemandé. Les cours ne bougeaient
        plus qu'en lançant `pastory cours` (défaut vu à l'étape 9 : l'écran restait au lundi).

        Une seule demande par exécution suffit — du lendemain du dernier jour connu jusqu'à
        hier —, et les jours suivants tombent dedans. Une réponse vide n'est pas un refus : la
        clôture d'hier n'est souvent pas encore publiée, et le dernier jour connu reste valable.
        Un jour **dans** la série (un week-end entre deux cours) ne provoque aucun appel (D-50).
        """
        if not self._serie(actif) or self._date_deja_demandee(actif, date):
            return
        if actif not in self._jours_tries:
            self._jours_tries[actif] = sorted(self._serie(actif))
        dernier = self._jours_tries[actif][-1]
        if date > dernier:
            self.remplir(actif, dernier + UN_JOUR, self.aujourd_hui)

    def _ce_qui_manque(self, actif: str, debut: Date, fin: Date) -> tuple[Date, Date]:
        """Réduit la période à ce que le cache ne connaît pas encore.

        Le cache empêche de **réécrire** un cours ; c'est ici qu'on évite de le **redemander**.
        La réduction n'a lieu que si le cache couvre déjà le début de la période : s'il faut
        un jour plus ancien que tout ce qu'on connaît, il faut bien aller le chercher.

        « Couvre le début » demande une tolérance : la période demandée commence à une date
        quelconque, alors que le cache commence au premier jour **coté** qui suit. Quelques
        jours d'écart sont donc normaux — au-delà, c'est que la source ne connaissait rien
        avant, et il faut redemander.

        **Le cache ne doit jamais se trouer**, et un trou existant doit se combler : c'est le
        défaut trouvé à l'étape 9. La version d'avant ne regardait que le premier et le dernier
        jour connus. Un cache arrêté au 21 août, interrogé pour un jour d'octobre, faisait donc
        télécharger les seuls trente jours précédant ce jour — laissant un trou fin août ; et
        toute date tombant ensuite dans ce trou était jugée « couverte », puisque le cache
        connaissait des cours avant et après. Le cours d'un jour d'achat manquait pour toujours.

        D'où la règle : on parcourt les jours connus à partir du début demandé, et la demande
        repart **du lendemain du dernier jour connu avant le premier trou** — un écart de plus
        de `RECUL_MAXIMAL` entre deux jours cotés, qu'aucun week-end ni jour férié n'explique.
        Les jours déjà connus que la réponse contiendra ne sont pas réécrits (D-50).
        """
        serie = self._serie(actif)
        if not serie:
            return debut, fin

        if actif not in self._jours_tries:
            self._jours_tries[actif] = sorted(serie)
        jours = self._jours_tries[actif]
        premier = jours[0]
        if debut < premier - RECUL_MAXIMAL:
            return debut, fin

        # Le dernier jour connu au début de la période (ou le premier, si la période commence
        # juste avant lui) : c'est de là que l'on vérifie que rien ne manque jusqu'à la fin.
        rang = bisect.bisect_right(jours, max(debut, premier))
        curseur = jours[rang - 1]
        for jour in jours[rang:]:
            if jour > fin:
                break
            if jour - curseur > RECUL_MAXIMAL:
                return curseur + UN_JOUR, fin  # un trou : on repart de son début
            curseur = jour
        if curseur >= fin:
            return fin, debut  # période vide : le cache couvre tout
        return curseur + UN_JOUR, fin

    def _deja_demande(self, actif: str, debut: Date, fin: Date) -> bool:
        return any(
            depuis <= debut and fin <= jusqu_a
            for depuis, jusqu_a in self._demandes.get(actif, [])
        )

    def _date_deja_demandee(self, actif: str, date: Date) -> bool:
        """Vrai si une demande précédente couvrait déjà ce jour-là."""
        return any(
            depuis <= date <= jusqu_a for depuis, jusqu_a in self._demandes.get(actif, [])
        )

    def _refuser(self, actif: str, categorie: str, motif: str, date: Date | None = None) -> None:
        # Un seul refus par actif et par catégorie : sur un portefeuille où un actif porte
        # dix opérations, répéter dix fois le même message ferait perdre les autres.
        self._refus.setdefault(
            (actif, categorie), Refus(actif=actif, categorie=categorie, motif=motif, date=date)
        )


