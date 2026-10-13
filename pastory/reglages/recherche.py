"""Chercher en ligne ce que l'export ne donne pas, et le contrôler avant de l'appliquer (D-80).

Deux réglages se cherchent ici : la **cotation** d'un actif (où lire son cours) et les **frais
courants** d'un ETF. Chaque valeur trouvée passe un contrôle ; celle qui échoue n'est pas
appliquée et devient un `Trou` qui dit pourquoi.

**La cotation, et le contrôle qui la rend sûre.** La recherche par ISIN se trompe de façon
connue : pour un ETF irlandais, elle renvoie d'abord la cotation de Londres en dollars, et une
recherche par nom mêle les parts capitalisante et distribuante d'un même fonds
(docs/reglages-automatiques.md). Mais la banque donne, sur chaque achat et chaque vente, le
**prix payé**. Un candidat n'est donc retenu que si son cours de clôture, aux jours des dernières
opérations, retombe sur ce prix à moins de `ECART_MAXIMAL` près — écart médian, pour qu'une
seule séance agitée ne suffise pas à écarter le bon. Entre plusieurs candidats qui passent, le
plus proche l'emporte : c'est ce qui sépare deux parts d'un même fonds, dont les prix diffèrent
de quelques pour cent.

Ce contrôle attrape le dollar, la livre en pence, la mauvaise part, la mauvaise société. Il ne
distingue pas deux cotations en euros du même titre sur deux places — et c'est sans danger :
elles donnent le même cours.

**Les frais courants.** L'émetteur d'abord — Amundi publie le TER de ses fonds, dont les ETF
« PEA » de droit français, absents de la liste de Xetra — puis la liste de Xetra. Le contrôle est
la fourchette de vraisemblance de D-61 ; quand les deux sources répondent et diffèrent, l'émetteur
fait foi et l'écart est dit.

**Rien n'est cherché pour l'export d'un tiers** (règle 2 de CLAUDE.md) : envoyer ses ISIN à un
service extérieur, ce serait divulguer ce qu'il détient.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from typing import Protocol

from pastory.config.actifs import (
    TER_MAXIMUM,
    TER_MINIMUM,
    Configuration,
    ContenuActif,
    Declaration,
    FraisCourantsProposes,
    Proposition,
    TypeActif,
)
from pastory.donnees_externes import amundi, xetra
from pastory.donnees_externes.cours import (
    Cours,
    DeviseInattendue,
    ErreurDeSource,
    SourceInjoignable,
)
from pastory.donnees_externes.extraetf import ClasseAnnoncee
from pastory.parametres.contenus import LectureDesContenus
from pastory.pivot.operation import (
    DEVISE_UNIQUE,
    Operation,
    Poche,
    Provenance,
    TypeOperation,
)
from pastory.reglages import CeQueDitLaBanque, Cotation, Origine, Trou, Trouvee
from pastory.reglages.assemblage import TROU_HORS_LIGNE, EnLigne
from pastory.reglages.cache import CacheDesReglages, Champ

TOLERANCES: dict[TypeActif, tuple[Decimal, Decimal, Decimal]] = {
    TypeActif.ETF: (Decimal("6"), Decimal("4"), Decimal("2")),
    TypeActif.ACTION: (Decimal("12"), Decimal("6"), Decimal("4")),
    TypeActif.CRYPTO: (Decimal("20"), Decimal("10"), Decimal("5")),
}
"""L'écart médian toléré entre clôture et prix payé, en pour cent, pour 1 à 2 ordres, 3 à 5,
et 6 ou plus.

Mesuré le 2026-10-05 (docs/reglages-automatiques.md) : sur une seule séance, l'écart entre un
prix pris dans la journée et la clôture atteint 3 % pour un ETF, 5,7 % pour un ETC d'or, 7 %
pour une action et 13,6 % pour un crypto-actif au 99ᵉ centile ; avec le bon ticker et six
ordres, la médiane ne dépasse plus 1,2 %, 3,3 % et 4,3 %. Les fonds partagent la tolérance des
ETC d'or, plus agités, parce que l'export les range tous deux sous « fonds ». Une erreur de
cotation donne, elle, des écarts massifs : les pence (− 99 %), un autre fonds sur le même
indice (+ 73 % et plus), le dollar (− 14 % au change de 2026).
"""

ECART_DE_CHANGE_MAXIMAL = Decimal("1")
"""Pour un candidat trouvé par son nom : l'écart médian toléré, en pour cent, entre ses cours
et ceux de la cotation trouvée par ISIN dans une autre monnaie, convertis en euros.

Mesuré : de 0,02 à 0,06 % pour le bon ETF, 0,2 % pour une action ; 2 % entre les parts
capitalisante et distribuante d'un fonds S&P 500, 3,3 % pour un fonds monde. C'est le contrôle
qui sépare deux parts qu'un prix payé, trop bruité, ne sépare pas."""

JOURS_DE_CHANGE = timedelta(days=90)
"""La fenêtre du contrôle de change : une soixantaine de séances communes."""

NOMBRE_DE_PRIX = 6
"""Combien d'ordres, les plus récents, servent au contrôle."""

RECUL = timedelta(days=4)
"""Quand aucun ordre ne tombe un jour où la place du candidat cote : jusqu'où chercher la
clôture la plus proche."""

MARGE = timedelta(days=10)

NOMBRE_MAXIMAL_DE_CANDIDATS = 7
"""La recherche ne rend jamais plus de sept résultats, quel que soit le nombre demandé."""

PREFERENCE_DE_PLACE = (".DE", ".PA", ".AS", ".MI", ".F", ".BR", ".MC", ".VI")
"""Entre deux candidats aussi proches du prix payé, la place la plus liquide l'emporte."""

PREFERENCE_POUR_LES_ACTIONS_AMERICAINES = (".F", ".DE", ".PA", ".AS", ".MI")
"""Pour un ISIN américain, Francfort d'abord (D-88) : elle cote jusque vers 22 h, au plus près
de la clôture de New York et de l'heure où ferme la banque, quand Xetra ferme à 17 h 30. Mesuré
le 2026-10-05 : ± 1,5 à 2 % du cours américain converti au pire jour, contre ± 2,6 à 4,9 %."""

EQUIVALENCE = Decimal("1")
"""En points de pourcentage : deux candidats dont l'écart au prix payé diffère de moins que cela
sont tenus pour également justes, et c'est la place qui les départage."""

SOURCE_DES_COTATIONS = "Yahoo Finance (recherche)"

TROU_TIERS = Trou(
    "aucune recherche n'est faite pour l'export de quelqu'un d'autre : ce serait envoyer ses "
    "ISIN à un service extérieur."
)

SANS_PRIX = (
    "aucune cotation n'a pu être vérifiée : vos exports ne contiennent aucun achat ni aucune "
    "vente de cet actif qui donne le prix payé. Il n'est pas valorisé, et il est signalé plutôt "
    "qu'estimé."
)

INCONNU = (
    "la recherche ne connaît aucune cotation de cet actif. Il n'est pas valorisé, et il est "
    "signalé plutôt qu'estimé."
)


def seuil(type_actif: TypeActif, controles: int) -> Decimal:
    """La tolérance selon le nombre d'ordres comparés : plus il y en a, plus elle est serrée."""
    un_ou_deux, trois_a_cinq, six_et_plus = TOLERANCES[type_actif]
    if controles >= 6:
        return six_et_plus
    if controles >= 3:
        return trois_a_cinq
    return un_ou_deux


class SourceDeCotations(Protocol):
    nom: str

    def candidats(self, requete: str) -> list[Proposition]: ...

    def serie(
        self, actif: str, declaration: Declaration, debut: Date, fin: Date
    ) -> list[Cours]: ...

    def serie_brute(
        self, ticker: str, debut: Date, fin: Date
    ) -> tuple[str, list[tuple[Date, Decimal]]]: ...


class SourceDeClasses(Protocol):
    def classe_d_actifs(self, actif: str) -> ClasseAnnoncee | None: ...


class RegistreCfi(Protocol):
    def codes_cfi(self, actif: str) -> frozenset[str]: ...


SOURCE_DES_CONTENUS = "extraETF (classe d'actifs du fonds)"


class SourceDeFraisCourants(Protocol):
    nom: str

    def frais_courants(self, actif: str) -> FraisCourantsProposes | None: ...


@dataclass(frozen=True)
class PrixPaye:
    """Le prix d'une part, donné par la banque sur un achat ou une vente."""

    jour: Date
    """Le jour à Paris ; pour une crypto, le jour en temps universel, celui des bougies de la
    source."""

    prix: Decimal


@dataclass(frozen=True)
class Verdict:
    """Ce que le contrôle a mesuré pour un candidat en euros."""

    candidat: Proposition
    ecart_median: Decimal | None
    """En pour cent. `None` : aucun prix payé n'a pu servir."""
    controles: int
    """Combien d'ordres ont été comparés."""
    ecart_de_change: Decimal | None = None
    reference: str | None = None

    def dans_la_tolerance(self, type_actif: TypeActif) -> bool:
        return self.ecart_median is not None and self.ecart_median <= seuil(
            type_actif, self.controles
        )


class Recherche:
    """Trouve, contrôle et garde en mémoire la cotation et les frais courants de chaque actif."""

    def __init__(
        self,
        cache: CacheDesReglages,
        cotations: SourceDeCotations | None = None,
        frais_courants: Sequence[Callable[[], SourceDeFraisCourants]] = (),
        *,
        classes: SourceDeClasses | None = None,
        registre: RegistreCfi | None = None,
        lecture_des_contenus: LectureDesContenus | None = None,
        tiers: bool = False,
        aujourd_hui: Date | None = None,
    ) -> None:
        """`cotations` à `None` : hors ligne, seul le cache sert. `frais_courants` : les sources
        de TER, **dans l'ordre de confiance**, construites seulement si l'on en a besoin (la liste
        de Xetra pèse un demi-mégaoctet). `classes`, `registre` et `lecture_des_contenus` : le
        contenu d'un fonds et son témoin (D-89) ; sans eux, le contenu n'est pas cherché."""
        self.cache = cache
        self.cotations = cotations
        self.fabriques_de_frais = tuple(frais_courants)
        self._sources_de_frais: list[SourceDeFraisCourants | ErreurDeSource] | None = None
        self.classes = classes
        self.registre = registre
        self.lecture_des_contenus = lecture_des_contenus
        self._autres_devises: set[str] = set()
        self._series_brutes: dict[tuple[str, Date, Date], tuple[str, list]] = {}
        self.tiers = tiers
        self.aujourd_hui = aujourd_hui or Date.today()

    @property
    def en_ligne(self) -> bool:
        return self.cotations is not None and not self.tiers

    def trouver(
        self,
        banque: CeQueDitLaBanque,
        operations: Iterable[Operation],
        corrections: Configuration | None = None,
    ) -> dict[str, EnLigne]:
        """Ce que les sources trouvent pour chaque actif de l'export.

        Le type qui guide la recherche — quelle tolérance, faut-il un TER — est celui que
        l'utilisateur a corrigé s'il l'a fait, sinon celui de la banque : une correction
        l'emporte partout, pas seulement sur le spread.
        """
        prix = _prix_payes(operations)
        resultat: dict[str, EnLigne] = {}
        for actif in sorted(banque.poches):
            corrige = corrections.declaration(actif) if corrections is not None else None
            types = banque.types.get(actif, frozenset())
            type_actif = (
                corrige.type
                if corrige is not None and corrige.type is not None
                else next(iter(types)) if len(types) == 1 else None
            )
            resultat[actif] = EnLigne(
                cotation=self._cotation(actif, type_actif, banque, prix.get(actif, [])),
                ter=self._ter(actif) if type_actif is TypeActif.ETF else None,
                contenu=self._contenu(actif) if type_actif is TypeActif.ETF else None,
            )
        return resultat

    # --- La cotation ----------------------------------------------------------------------

    def _cotation(
        self,
        actif: str,
        type_actif: TypeActif | None,
        banque: CeQueDitLaBanque,
        prix: list[PrixPaye],
    ) -> Trouvee[Cotation] | Trou:
        connu = self.cache.lire(actif, Champ.COTATION)
        if connu is not None and not (
            self.en_ligne and connu.perimee(Champ.COTATION, self.aujourd_hui)
        ):
            return connu.resultat
        if not self.en_ligne:
            return TROU_TIERS if self.tiers else TROU_HORS_LIGNE
        try:
            resultat = self._chercher_une_cotation(
                actif, type_actif, banque.noms.get(actif), prix
            )
        except ErreurDeSource as erreur:
            # Réseau coupé en pleine recherche : rien n'est gardé, on réessaiera au lancement
            # suivant plutôt que de retenir un trou d'une semaine pour une panne passagère.
            return Trou(f"la recherche n'a pas pu aboutir ({erreur}) : elle sera refaite.")
        self.cache.ecrire(actif, Champ.COTATION, resultat, self.aujourd_hui)
        return resultat

    def _chercher_une_cotation(
        self,
        actif: str,
        type_actif: TypeActif | None,
        nom: str | None,
        prix: list[PrixPaye],
    ) -> Trouvee[Cotation] | Trou:
        """Trois étages, du plus sûr au moins sûr, chacun avec son contrôle :

        1. **par l'ISIN**, une cotation en euros : la recherche l'associe à l'ISIN de l'actif,
           et c'est toujours le bon instrument (33 sur 33 mesurés). Si l'export donne des prix
           payés, elle doit en plus retomber dessus ;
        2. **par le nom**, une cotation en euros : elle doit retomber sur le prix payé, et, si la
           recherche par ISIN a trouvé l'actif dans une autre monnaie, suivre cette cotation-là
           une fois convertie (`ECART_DE_CHANGE_MAXIMAL`). C'est ce second contrôle qui sépare
           deux parts d'un même fonds ;
        3. une crypto : `CODE-EUR`, qui doit retomber sur le prix payé.
        """
        assert self.cotations is not None
        if type_actif is None:
            return Trou(
                "le type de l'actif n'est pas connu, et c'est lui qui dit quel écart de prix "
                "tolérer : aucune cotation n'est retenue."
            )
        if type_actif is TypeActif.CRYPTO:
            candidat = Proposition(ticker=f"{actif}-{DEVISE_UNIQUE}", nom=nom)
            if not prix:
                return Trou(SANS_PRIX)
            verdict = self._controler(actif, candidat, prix)
            if verdict is None or not verdict.dans_la_tolerance(type_actif):
                return Trou(_motif_sans_cotation([verdict] if verdict else [], type_actif, 1))
            return self._retenir(verdict, type_actif, "son code donné par la banque")

        essayes: set[str] = set()
        par_isin = self.cotations.candidats(actif)[:NOMBRE_MAXIMAL_DE_CANDIDATS]
        verdicts_isin = self._controler_tous(actif, par_isin, prix, essayes)
        retenus = [
            verdict
            for verdict in verdicts_isin
            if verdict.ecart_median is None or verdict.dans_la_tolerance(type_actif)
        ]
        if retenus:
            return self._retenir(_meilleur(retenus, actif), type_actif, "son ISIN")

        if not par_isin:
            return Trou(INCONNU)
        if not prix:
            return Trou(SANS_PRIX)

        # La référence du contrôle de change : une cotation trouvée par l'ISIN que la source a
        # refusée **pour sa devise** — et non un candidat muet, comme le pseudo-ticker de
        # Stuttgart, qui ferait échouer à tort tous les candidats trouvés par le nom.
        reference = next(
            (candidat for candidat in par_isin if candidat.ticker in self._autres_devises),
            None,
        )
        noms = list(
            dict.fromkeys(
                un for un in [*(c.nom for c in par_isin[:1]), nom] if un
            )
        )
        # En second recours seulement, les mêmes noms **simplifiés** : la recherche de la
        # source est littérale, et « Société, Inc. » ou « Société (B) » ne lui font pas trouver les
        # cotations en euros que « Société » lui fait trouver. Tant que les noms exacts
        # suffisent, rien de plus n'est demandé, et rien ne change pour les actifs déjà
        # trouvés.
        simplifies: list[str] = []
        for un in noms:
            court = _nom_simplifie(un)
            # « SOCIÉTÉ » et « Société » sont la même demande : une seule suffit.
            if court and court.casefold() not in {n.casefold() for n in [*noms, *simplifies]}:
                simplifies.append(court)
        verdicts_nom: list[Verdict] = []
        for recours, maximum in ((noms, 2), (simplifies, 3)):
            verdicts: list[Verdict] = []
            for un_nom in recours:
                verdicts += self._controler_tous(
                    actif,
                    self.cotations.candidats(un_nom),
                    prix,
                    essayes,
                    maximum * NOMBRE_MAXIMAL_DE_CANDIDATS,
                )
            verdicts_nom += verdicts
            retenus = []
            for verdict in verdicts:
                if not verdict.dans_la_tolerance(type_actif):
                    continue
                if reference is not None:
                    verdict = self._controler_le_change(actif, verdict, reference)
                    if (
                        verdict.ecart_de_change is None
                        or verdict.ecart_de_change > ECART_DE_CHANGE_MAXIMAL
                    ):
                        continue
                retenus.append(verdict)
            if retenus:
                return self._retenir(_meilleur(retenus, actif), type_actif, "son nom")

        return Trou(_motif_sans_cotation(verdicts_isin + verdicts_nom, type_actif, len(essayes)))

    def _controler_tous(
        self,
        actif: str,
        candidats: Sequence[Proposition],
        prix: list[PrixPaye],
        essayes: set[str],
        maximum: int = 2 * NOMBRE_MAXIMAL_DE_CANDIDATS,
    ) -> list[Verdict]:
        verdicts = []
        for candidat in candidats:
            if candidat.ticker in essayes or len(essayes) >= maximum:
                continue
            essayes.add(candidat.ticker)
            verdict = self._controler(actif, candidat, prix)
            if verdict is not None:
                verdicts.append(verdict)
        return verdicts

    def _controler(
        self, actif: str, candidat: Proposition, prix: list[PrixPaye]
    ) -> Verdict | None:
        """Le candidat en euros, et l'écart de ses clôtures aux prix payés.

        `None` : pas en euros, ticker inconnu, ou aucun cours — le pseudo-ticker de Stuttgart
        annonce l'euro et un cours du jour, mais n'a aucun historique.
        """
        assert self.cotations is not None
        if prix:
            debut = min(un.jour for un in prix) - MARGE
            fin = min(max(un.jour for un in prix) + MARGE, self.aujourd_hui)
        else:
            debut, fin = self.aujourd_hui - JOURS_DE_CHANGE, self.aujourd_hui
        try:
            serie = self.cotations.serie(
                actif, Declaration(ticker=candidat.ticker, devise=DEVISE_UNIQUE), debut, fin
            )
        except SourceInjoignable:
            # Le réseau, pas le candidat : la recherche s'arrête, et rien n'est gardé.
            raise
        except DeviseInattendue:
            self._autres_devises.add(candidat.ticker)
            return None
        except ErreurDeSource:
            return None
        clotures = {cours.date: cours.valeur for cours in serie}
        if not clotures:
            return None
        if not prix:
            return Verdict(candidat, None, 0)

        # Un ordre passé un jour où la place du candidat ne cote pas n'est pas comparé : la
        # veille ajouterait une séance de bruit (docs/reglages-automatiques.md).
        ecarts = [_ecart(clotures[un.jour], un.prix) for un in prix if un.jour in clotures]
        if ecarts:
            return Verdict(candidat, _mediane(ecarts), len(ecarts))
        # Aucun ordre un jour coté : la clôture la plus proche à quatre jours près, jugée avec
        # la tolérance la plus large, celle d'un ordre unique.
        proches = [
            _ecart(cloture, un.prix)
            for un in prix
            if (cloture := _cloture_proche(clotures, un.jour)) is not None
        ]
        if not proches:
            return None
        return Verdict(candidat, _mediane(proches), 1)

    def _controler_le_change(
        self, actif: str, verdict: Verdict, reference: Proposition
    ) -> Verdict:
        """L'écart entre le candidat et la cotation trouvée par ISIN, convertie en euros.

        Rendu sans écart (donc écarté par l'appelant) si l'une des séries manque : un contrôle
        qui n'a pas pu se faire n'est pas un contrôle réussi.
        """
        assert self.cotations is not None
        debut, fin = self.aujourd_hui - JOURS_DE_CHANGE, self.aujourd_hui
        try:
            devise, en_devise = self._serie_brute(reference.ticker, debut, fin)
            facteur = Decimal(100) if devise == "GBp" else Decimal(1)
            code = "GBP" if devise == "GBp" else devise.upper()
            if code == DEVISE_UNIQUE:
                return verdict
            _, taux = self._serie_brute(f"{DEVISE_UNIQUE}{code}=X", debut, fin)
            candidat = self.cotations.serie(
                actif,
                Declaration(ticker=verdict.candidat.ticker, devise=DEVISE_UNIQUE),
                debut,
                fin,
            )
        except SourceInjoignable:
            raise
        except ErreurDeSource:
            return verdict
        reference_par_jour = dict(en_devise)
        taux_par_jour = dict(taux)
        rapports = [
            cours.valeur
            / (reference_par_jour[cours.date] / facteur / taux_par_jour[cours.date])
            for cours in candidat
            if reference_par_jour.get(cours.date) and taux_par_jour.get(cours.date)
        ]
        if not rapports:
            return verdict
        return replace(
            verdict,
            ecart_de_change=abs(_mediane(rapports) - 1) * Decimal(100),
            reference=f"{reference.ticker} ({devise})",
        )

    def _serie_brute(
        self, ticker: str, debut: Date, fin: Date
    ) -> tuple[str, list[tuple[Date, Decimal]]]:
        """Une série de référence ou de change, lue une seule fois par exécution."""
        assert self.cotations is not None
        cle = (ticker, debut, fin)
        if cle not in self._series_brutes:
            self._series_brutes[cle] = self.cotations.serie_brute(ticker, debut, fin)
        return self._series_brutes[cle]

    def _retenir(self, verdict: Verdict, type_actif: TypeActif, par: str) -> Trouvee[Cotation]:
        candidat = verdict.candidat
        morceaux = [f"trouvée par {par}, cotée en euros avec des cours"]
        reserve = None
        if verdict.ecart_median is None:
            reserve = (
                "aucun achat ni aucune vente dans vos exports ne donne un prix payé pour la "
                "vérifier : elle est retenue parce que la recherche l'associe à l'ISIN de "
                "l'actif."
            )
        else:
            morceaux.append(
                f"sur {verdict.controles} ordre(s), son cours de clôture s'écarte en médiane de "
                f"{_pour_cent(verdict.ecart_median)} du prix payé (tolérance "
                f"{_pour_cent(seuil(type_actif, verdict.controles))})"
            )
        if verdict.ecart_de_change is not None:
            morceaux.append(
                f"elle suit {verdict.reference} converti en euros à "
                f"{_pour_cent(verdict.ecart_de_change)} près (tolérance "
                f"{_pour_cent(ECART_DE_CHANGE_MAXIMAL)})"
            )
        return Trouvee(
            Cotation(candidat.ticker, DEVISE_UNIQUE, candidat.place, candidat.nom),
            Origine(
                source=SOURCE_DES_COTATIONS,
                date=self.aujourd_hui,
                controle="; ".join(morceaux),
                reserve=reserve,
            ),
        )

    # --- Les frais courants ----------------------------------------------------------------

    def _ter(self, actif: str) -> Trouvee[Decimal] | Trou | None:
        connu = self.cache.lire(actif, Champ.TER)
        if connu is not None and not (
            self.en_ligne and connu.perimee(Champ.TER, self.aujourd_hui)
        ):
            return connu.resultat
        if not self.en_ligne:
            if connu is not None:
                return connu.resultat
            return TROU_TIERS if self.tiers else TROU_HORS_LIGNE
        resultat, en_panne = self._chercher_un_ter(actif)
        # Une source en panne n'a rien dit du fonds : rien n'est gardé, la recherche sera refaite
        # au lancement suivant. Et ce qu'on savait déjà reste valable en attendant.
        if en_panne:
            if connu is not None and isinstance(connu.resultat, Trouvee):
                return connu.resultat
            return resultat
        self.cache.ecrire(actif, Champ.TER, resultat, self.aujourd_hui)
        return resultat

    def _chercher_un_ter(self, actif: str) -> tuple[Trouvee[Decimal] | Trou, bool]:
        """Le TER retenu, et `True` si le résultat dépend d'une source tombée en panne."""
        trouves: list[FraisCourantsProposes] = []
        pannes: list[str] = []
        for source in self._sources():
            if isinstance(source, ErreurDeSource):
                pannes.append(str(source))
                continue
            try:
                frais = source.frais_courants(actif)
            except ErreurDeSource as erreur:
                pannes.append(str(erreur))
                continue
            # Un taux sans date n'est pas retenu (D-58), quelle que soit sa source.
            if (
                frais is not None
                and frais.date is not None
                and TER_MINIMUM <= frais.ter_pour_cent <= TER_MAXIMUM
            ):
                trouves.append(frais)

        if not trouves:
            motif = (
                "ni l'émetteur (s'il publie ses frais) ni la liste des ETF de Xetra ne donnent "
                "les frais courants de ce fonds : ils ne sont pas comptés."
            )
            if pannes:
                motif += (
                    " Une source n'a pas répondu, la recherche sera refaite : "
                    + " ; ".join(pannes)
                )
            return Trou(motif), bool(pannes)

        retenu, autres = trouves[0], trouves[1:]
        controle = (
            f"dans la fourchette de vraisemblance ({_pour_cent(TER_MINIMUM)} à "
            f"{_pour_cent(TER_MAXIMUM)})"
        )
        differents = [
            autre for autre in autres if autre.ter_pour_cent != retenu.ter_pour_cent
        ]
        if differents:
            controle += "; " + "; ".join(
                f"{autre.source} donne {_pour_cent(autre.ter_pour_cent)} : la première source "
                "fait foi"
                for autre in differents
            )
        elif autres:
            controle += "; " + ", ".join(autre.source for autre in autres) + " concorde"
        if pannes:
            controle += (
                "; une source n'a pas répondu, la recherche sera refaite : " + " ; ".join(pannes)
            )
        origine = Origine(
            source=retenu.source,
            date=retenu.date,
            controle=controle,
            reserve=RESERVES_DES_TER.get(retenu.source),
            intitule_de_la_date=INTITULES_DES_DATES.get(retenu.source, "au"),
        )
        return Trouvee(retenu.ter_pour_cent, origine), bool(pannes)

    # --- Le contenu ------------------------------------------------------------------------

    def _contenu(self, actif: str) -> Trouvee[ContenuActif] | Trou | None:
        """De quoi le fonds est fait : extraETF décide, le code CFI confirme ou contredit (D-89).

        `None` : rien n'est cherché (hors ligne et rien en mémoire, ou sources non branchées) ;
        la source de composition décide alors, comme avant.
        """
        if self.classes is None or self.registre is None or self.lecture_des_contenus is None:
            return None
        connu = self.cache.lire(actif, Champ.CONTENU)
        if connu is not None and not (
            self.en_ligne and connu.perimee(Champ.CONTENU, self.aujourd_hui)
        ):
            return connu.resultat
        if not self.en_ligne:
            return connu.resultat if connu is not None else None
        try:
            resultat, en_panne = self._chercher_un_contenu(actif)
        except ErreurDeSource:
            # La source principale est tombée : ce qu'on savait reste valable en attendant.
            return connu.resultat if connu is not None else None
        if en_panne:
            if connu is not None and isinstance(connu.resultat, Trouvee):
                return connu.resultat
            return resultat
        if resultat is not None:
            self.cache.ecrire(actif, Champ.CONTENU, resultat, self.aujourd_hui)
        return resultat

    def _chercher_un_contenu(
        self, actif: str
    ) -> tuple[Trouvee[ContenuActif] | Trou | None, bool]:
        assert self.classes is not None and self.registre is not None
        assert self.lecture_des_contenus is not None
        annonce = self.classes.classe_d_actifs(actif)
        if annonce is None:
            return None, False
        contenu = self.lecture_des_contenus.par_extraetf(annonce.code, annonce.libelle)
        if contenu is None:
            return Trou(
                f"extraETF range ce fonds dans la classe « {annonce.libelle} » ({annonce.code}), "
                "que l'application ne traduit pas encore : son contenu n'est pas retenu, et sa "
                "répartition vient de sa composition, s'il en a une."
            ), False

        en_panne = False
        try:
            codes = self.registre.codes_cfi(actif)
        except ErreurDeSource:
            codes, en_panne = frozenset(), True
        dits = self.lecture_des_contenus.par_cfi(codes)
        cites = ", ".join(sorted(codes)) or "aucun"
        if len(dits) == 1 and contenu not in dits:
            (autre,) = dits
            return Trou(
                f"extraETF dit « {contenu.value} », le registre de l'ESMA dit « {autre.value} » "
                f"(code CFI {cites}) : les deux sources se contredisent, et rien n'est retenu."
            ), False

        reserves = []
        if dits == {contenu}:
            controle = f"le code CFI déclaré au registre de l'ESMA concorde ({cites})"
        else:
            controle = "classe et libellé de la source concordent"
            reserves.append(
                "non recoupé : le registre de l'ESMA n'a pas répondu"
                if en_panne
                else f"non recoupé : le code CFI du registre de l'ESMA ne dit rien d'exploitable "
                f"({cites})"
            )
        if contenu is ContenuActif.ACTIONS:
            reserves.append(
                "sans effet sur les répartitions : un fonds d'actions garde les pays et les "
                "secteurs de sa composition"
            )
        return Trouvee(
            contenu,
            Origine(
                source=SOURCE_DES_CONTENUS,
                date=annonce.releve_le,
                controle=controle,
                reserve="; ".join(reserves) or None,
            ),
        ), en_panne

    def _sources(self) -> list[SourceDeFraisCourants | ErreurDeSource]:
        if self._sources_de_frais is None:
            self._sources_de_frais = []
            for fabrique in self.fabriques_de_frais:
                try:
                    self._sources_de_frais.append(fabrique())
                except ErreurDeSource as erreur:
                    self._sources_de_frais.append(erreur)
        return self._sources_de_frais


RESERVES_DES_TER: dict[str, str] = {
    xetra.NOM: (
        "cette liste est parfois en retard sur une baisse de frais (5,4 % des lignes mesurées "
        "en 2026, toujours trop haut) : les frais estimés peuvent être un peu surestimés."
    ),
}
"""La limite connue de chaque source de TER, par son nom. L'émetteur n'en a pas : c'est lui
qui publie le chiffre, et son service concorde avec son document d'information clé."""

INTITULES_DES_DATES: dict[str, str] = {
    amundi.NOM_FRAIS_COURANTS: "taux en vigueur depuis le",
}
"""Ce que veut dire la date d'une source, quand ce n'est pas « l'état de la source au ». Chez
Amundi, c'est la date d'effet du taux : un taux de 2023 toujours en vigueur n'est pas périmé."""


def _prix_payes(operations: Iterable[Operation]) -> Mapping[str, list[PrixPaye]]:
    """Par actif, les `NOMBRE_DE_PRIX` derniers prix donnés par la banque, en euros."""
    par_actif: dict[str, list[PrixPaye]] = {}
    for operation in operations:
        if operation.type not in (TypeOperation.ACHAT, TypeOperation.VENTE):
            continue
        if operation.prix_unitaire is None or operation.devise != DEVISE_UNIQUE:
            continue
        if operation.provenance.get("prix_unitaire") is not Provenance.DONNEE:
            continue
        # Les bougies des cryptos sont découpées en temps universel, pas à l'heure de Paris.
        jour = (
            operation.instant_utc.date() if operation.poche is Poche.CRYPTO else operation.date
        )
        par_actif.setdefault(operation.actif, []).append(PrixPaye(jour, operation.prix_unitaire))
    return {
        actif: sorted(prix, key=lambda un: un.jour)[-NOMBRE_DE_PRIX:]
        for actif, prix in par_actif.items()
    }


def _ecart(cloture: Decimal, prix: Decimal) -> Decimal:
    return abs(cloture - prix) / prix * Decimal(100)


def _mediane(valeurs: Sequence[Decimal]) -> Decimal:
    return Decimal(statistics.median(valeurs))


def _cloture_proche(clotures: Mapping[Date, Decimal], jour: Date) -> Decimal | None:
    """La clôture la plus proche du jour, avant ou après, à `RECUL` près."""
    for distance in range(1, RECUL.days + 1):
        for candidat in (jour - timedelta(days=distance), jour + timedelta(days=distance)):
            if candidat in clotures:
                return clotures[candidat]
    return None


def _meilleur(verdicts: Sequence[Verdict], actif: str) -> Verdict:
    """Parmi les candidats aussi proches du prix payé que le meilleur, à `EQUIVALENCE` près, la
    place préférée ; puis le plus proche.

    Deux cotations du même titre sur deux places diffèrent de quelques dixièmes, au hasard des
    heures de clôture : les départager à l'écart reviendrait à tirer au sort. Deux parts d'un
    même fonds, elles, s'écartent de plusieurs points : l'écart les sépare.
    """

    def ecart(verdict: Verdict) -> Decimal:
        return verdict.ecart_median if verdict.ecart_median is not None else Decimal(0)

    plus_proche = min(ecart(verdict) for verdict in verdicts)
    equivalents = [verdict for verdict in verdicts if ecart(verdict) <= plus_proche + EQUIVALENCE]
    return min(
        equivalents,
        key=lambda verdict: (
            _rang_de_place(verdict.candidat.ticker, actif),
            ecart(verdict),
            verdict.ecart_de_change if verdict.ecart_de_change is not None else Decimal(0),
        ),
    )


def _rang_de_place(ticker: str, actif: str) -> int:
    preference = (
        PREFERENCE_POUR_LES_ACTIONS_AMERICAINES
        if actif.upper().startswith("US")
        else PREFERENCE_DE_PLACE
    )
    for rang, suffixe in enumerate(preference):
        if ticker.upper().endswith(suffixe):
            return rang
    return len(preference)


FORMES_SOCIALES = frozenset(
    {"inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc", "sa", "se", "ag", "nv"}
)
"""Ce qui suit le nom d'une société sans en faire partie, d'une bourse à l'autre."""


def _nom_simplifie(nom: str) -> str | None:
    """Le nom tel qu'on le dirait : sans ce qui est entre parenthèses (« (B) », la classe de
    l'action), sans ce qui suit une virgule, sans forme sociale. `None` s'il n'y a rien à
    simplifier.

    C'est un texte, et il ne sert qu'à **demander des candidats** à la source (règle 4) :
    aucun n'est retenu sur son nom. Chacun doit retomber sur le prix payé, et suivre la
    cotation trouvée par l'ISIN une fois convertie en euros — deux contrôles chiffrés, que
    ne passe pas une autre société au nom voisin.
    """
    court = re.sub(r"\([^)]*\)", " ", nom).split(",")[0]
    mots = court.split()
    while len(mots) > 1 and mots[-1].replace(".", "").casefold() in FORMES_SOCIALES:
        mots.pop()
    court = " ".join(mots)
    return court if len(court) >= 3 and court.casefold() != nom.casefold() else None


def _motif_sans_cotation(verdicts: list[Verdict], type_actif: TypeActif, essayes: int) -> str:
    fin = " Cet actif n'est pas valorisé, et il est signalé plutôt qu'estimé."
    mesures = [verdict for verdict in verdicts if verdict.ecart_median is not None]
    if not mesures:
        return (
            f"{essayes} cotation(s) essayée(s), aucune en euros avec des cours : l'application "
            "ne convertit aucune monnaie." + fin
        )
    dans_la_tolerance = [verdict for verdict in mesures if verdict.dans_la_tolerance(type_actif)]
    if dans_la_tolerance:
        return (
            f"{essayes} cotation(s) essayée(s). Celles qui retombent sur le prix payé ne suivent "
            "pas la cotation que la recherche associe à l'ISIN, une fois convertie en euros : ce "
            "sont sans doute d'autres parts du même fonds (capitalisante, distribuante, "
            "couverte), et aucune n'est retenue." + fin
        )
    plus_proche = min(mesures, key=lambda verdict: verdict.ecart_median)
    return (
        f"{essayes} cotation(s) essayée(s), aucune ne retombe sur le prix que vous avez payé : la "
        f"plus proche ({plus_proche.candidat.ticker}) s'en écarte de "
        f"{_pour_cent(plus_proche.ecart_median)}, au-delà de la tolérance de "
        f"{_pour_cent(seuil(type_actif, plus_proche.controles))}. Ce n'est sans doute pas le même "
        "titre." + fin
    )


def _pour_cent(valeur: Decimal) -> str:
    arrondi = valeur.quantize(Decimal("0.01")) if valeur >= Decimal("0.01") else valeur
    return f"{format(arrondi.normalize(), 'f').replace('.', ',')} %"
