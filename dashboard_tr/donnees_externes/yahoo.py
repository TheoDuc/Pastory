"""Yahoo Finance : la source de cours retenue (D-51).

Appel direct au point d'accès public, avec la **bibliothèque standard** plutôt qu'une
bibliothèque dédiée. Trois raisons :

1. `yfinance` renvoie par défaut des cours **retraités des dividendes**, que le moteur compte
   déjà (D-29, D-51) : le piège est dans son réglage par défaut, et il est invisible sur un ETF
   capitalisant ;
2. elle renvoie des **flottants**, que le projet s'interdit pour un montant (D-33). Ici, la
   réponse est lue avec `parse_float=Decimal` : aucun cours n'existe jamais sous forme de
   flottant ;
3. `urllib` utilise le magasin de certificats **de Windows**, celui où l'antivirus installe le
   sien. C'est exactement ce qui oblige `uv` à `--native-tls` sur cette machine.

Ce que la recherche de l'étape 4 a établi en interrogeant réellement le service, et qui explique
les garde-fous ci-dessous :

- demander « tout l'historique » renvoie des points **mensuels** en annonçant du quotidien. On
  borne donc toujours par dates explicites, et on vérifie l'espacement obtenu ;
- la devise dépend de la place : un même ETF répond en euros à Xetra et **en dollars** à
  Londres. La devise annoncée est confrontée à celle que l'utilisateur a déclarée (D-48) ;
- des cours manquent parfois au milieu d'une série. Un trou n'est pas une erreur : on ne
  l'invente pas, on le laisse (le fournisseur remontera au dernier jour coté) ;
- les séries sont sérialisées avec une précision de flottant court : 126.53500366210938 veut
  dire 126,535. Voir `_valeur_publiee`.

Cette source est **interchangeable** : elle n'est connue de personne d'autre que du CLI, qui la
branche. Le moteur, lui, ne sait même pas qu'elle existe (D-26).
"""

from __future__ import annotations

import json
import struct
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta, timezone
from datetime import date as Date
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dashboard_tr.config.actifs import Declaration, Proposition
from dashboard_tr.donnees_externes.cours import (
    Cours,
    DeviseInattendue,
    ErreurDeSource,
    ReponseIncoherente,
    SourceInjoignable,
    TickerInconnu,
)

NOM = "Yahoo Finance"

ADRESSE_SERIE = "https://query1.finance.yahoo.com/v8/finance/chart/"
ADRESSE_RECHERCHE = "https://query1.finance.yahoo.com/v1/finance/search"

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
"""Le service refuse les requêtes qui ne se présentent pas comme un navigateur."""

DELAI = 20
"""Secondes avant d'abandonner un appel. Un tableau de bord ne doit pas rester figé."""

ESPACEMENT_MAXIMAL = 6
"""Jours entre deux cours consécutifs au-delà desquels une série n'est plus quotidienne.

Un week-end en laisse trois, un pont un peu plus. Trente veut dire qu'on a reçu du mensuel en
croyant demander du quotidien : c'est le piège vérifié de l'étape 4, et il ne dit pas son nom
(le champ de granularité annonce « 1d » dans les deux cas)."""

Ouvrir = Callable[[str], str]
"""Comment le texte d'une réponse est obtenu. Remplaçable dans les tests : aucun test du
projet ne sort de la machine."""


class Yahoo:
    """La source Yahoo Finance, conforme au protocole `SourceDeCours`."""

    nom = NOM

    def __init__(self, ouvrir: Ouvrir | None = None) -> None:
        self.ouvrir = ouvrir or _telecharger

    # --- Ce que le protocole demande ----------------------------------------------------

    def serie(
        self, actif: str, declaration: Declaration, debut: Date, fin: Date
    ) -> list[Cours]:
        """Les cours de clôture **bruts** entre ces deux jours, bornes comprises."""
        adresse = _adresse_serie(declaration.ticker, debut, fin)
        contenu = _resultat(self.ouvrir(adresse), declaration.ticker)

        meta = contenu.get("meta") or {}
        devise = str(meta.get("currency") or "").upper()
        _verifier_la_devise(devise, declaration)

        place = str(meta.get("fullExchangeName") or meta.get("exchangeName") or "")
        fuseau = _fuseau(meta)
        aujourd_hui = Date.today()

        jours = _jours(contenu, fuseau)
        _verifier_l_espacement(jours, declaration.ticker)

        return [
            Cours(
                actif=actif,
                date=jour,
                valeur=valeur,
                devise=devise,
                place=place,
                source=self.nom,
                recupere_le=aujourd_hui,
                ticker=declaration.ticker,
            )
            for jour, valeur in jours
            if debut <= jour <= fin
        ]

    # --- Pour l'assistant `dashboard actifs` seulement -----------------------------------

    def chercher(self, actif: str) -> Proposition | None:
        """Cherche un ticker pour un ISIN, **sans rien décider**.

        Deux appels : la recherche donne un symbole, puis un appel de série d'un jour donne
        la **devise** et la place — que la recherche ne dit pas. C'est ce second appel qui
        rend visible le piège du dollar (D-48), et c'est pour cela qu'il est fait ici plutôt
        que laissé à la charge de l'utilisateur.

        Renvoie `None` dès que quelque chose manque : une proposition douteuse vaut mieux que
        rien, mais une proposition inventée ne vaut rien.
        """
        parametres = urllib.parse.urlencode({"q": actif, "quotesCount": 5, "newsCount": 0})
        adresse = f"{ADRESSE_RECHERCHE}?{parametres}"
        try:
            reponse = json.loads(self.ouvrir(adresse), parse_float=Decimal)
        except (ErreurDeSource, json.JSONDecodeError):
            return None

        quotes = reponse.get("quotes") or []
        if not quotes:
            return None

        premier = quotes[0]
        ticker = str(premier.get("symbol") or "").strip()
        if not ticker:
            return None

        nom = premier.get("longname") or premier.get("shortname")
        place = premier.get("exchDisp") or premier.get("exchange")

        devise, place_complete = self._identite(ticker)
        return Proposition(
            ticker=ticker,
            place=place_complete or (str(place) if place else None),
            devise=devise,
            nom=str(nom) if nom else None,
        )

    def _identite(self, ticker: str) -> tuple[str | None, str | None]:
        """La devise et la place d'un ticker, prises sur une série d'un seul jour."""
        fin = Date.today()
        adresse = _adresse_serie(ticker, fin - timedelta(days=7), fin)
        try:
            contenu = _resultat(self.ouvrir(adresse), ticker)
        except ErreurDeSource:
            return None, None

        meta = contenu.get("meta") or {}
        devise = str(meta.get("currency") or "").upper() or None
        place = str(meta.get("fullExchangeName") or meta.get("exchangeName") or "") or None
        return devise, place


# --- Lecture de la réponse ---------------------------------------------------------------


class ErreurDeReseau(SourceInjoignable):
    """Interne : l'appel n'a pas abouti. Vue de l'extérieur, c'est une source injoignable."""


def _adresse_serie(ticker: str, debut: Date, fin: Date) -> str:
    """L'adresse d'une série quotidienne bornée par **dates explicites**.

    Jamais de plage nommée (`range=max`) : elle renvoie du mensuel. Les bornes sont élargies
    d'un jour de chaque côté, parce qu'un horodatage se lit dans le fuseau de la place et
    pourrait, sinon, faire tomber le premier ou le dernier jour hors de la fenêtre.
    """
    parametres = {
        "period1": _horodatage(debut - timedelta(days=1)),
        "period2": _horodatage(fin + timedelta(days=1)),
        "interval": "1d",
    }
    return (
        f"{ADRESSE_SERIE}{urllib.parse.quote(ticker, safe='')}"
        f"?{urllib.parse.urlencode(parametres)}"
    )


def _horodatage(jour: Date) -> int:
    return int(datetime.combine(jour, time.min, tzinfo=UTC).timestamp())


def _telecharger(adresse: str) -> str:
    requete = urllib.request.Request(adresse, headers={"User-Agent": NAVIGATEUR})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
            return reponse.read().decode("utf-8")
    except urllib.error.HTTPError as erreur:
        if erreur.code == 429:
            raise ErreurDeReseau(
                "la source refuse temporairement de répondre (trop de demandes) : "
                "réessayez dans quelques minutes. Les cours déjà enregistrés restent "
                "utilisables."
            ) from erreur
        if erreur.code == 404:
            raise TickerInconnu(
                "la source ne connaît pas ce ticker : corrigez-le dans actifs.toml"
            ) from erreur
        raise ErreurDeReseau(
            f"la source a répondu une erreur {erreur.code} ({erreur.reason})"
        ) from erreur
    except urllib.error.URLError as erreur:
        raise ErreurDeReseau(
            f"impossible de joindre la source : {erreur.reason}. Si le réseau fonctionne, "
            "un antivirus ou un pare-feu peut inspecter la connexion."
        ) from erreur
    except TimeoutError as erreur:
        raise ErreurDeReseau(
            f"la source n'a pas répondu en moins de {DELAI} secondes"
        ) from erreur


def _resultat(texte: str, ticker: str) -> dict:
    """Le corps utile de la réponse, ou une erreur de source explicite."""
    try:
        reponse = json.loads(texte, parse_float=Decimal)
    except json.JSONDecodeError as erreur:
        raise SourceInjoignable(
            "la réponse de la source n'est pas exploitable (ce n'est pas du JSON) : "
            "un portail d'accès au réseau ou un antivirus l'a peut-être remplacée"
        ) from erreur

    graphique = reponse.get("chart") or {}
    erreur_annoncee = graphique.get("error")
    if erreur_annoncee:
        description = str(
            erreur_annoncee.get("description") or erreur_annoncee.get("code") or erreur_annoncee
        )
        if "not found" in description.lower() or "No data found" in description:
            raise TickerInconnu(
                f"la source ne connaît pas le ticker {ticker} : corrigez-le dans actifs.toml"
            )
        raise SourceInjoignable(f"la source a refusé la demande : {description}")

    resultats = graphique.get("result") or []
    if not resultats:
        raise SourceInjoignable("la source a répondu sans aucun résultat")
    return resultats[0]


def _verifier_la_devise(devise: str, declaration: Declaration) -> None:
    """Le garde-fou de D-48, au plus près de la donnée.

    Rien n'est converti et rien n'est gardé : un cours dans une autre monnaie que celle
    déclarée est presque toujours le signe qu'on interroge la mauvaise place de cotation.
    """
    if not devise:
        raise ReponseIncoherente(
            f"la source ne dit pas dans quelle monnaie « {declaration.ticker} » est coté : "
            "sans cette information, le cours ne peut pas être utilisé"
        )
    if devise != declaration.devise.upper():
        raise DeviseInattendue(
            f"« {declaration.ticker} » est coté en {devise}, or {declaration.devise} est "
            f"attendu. L'application ne convertit rien : retenez la cotation en "
            f"{declaration.devise} de cet actif, sur une autre place, dans « actifs.toml »."
        )


def _fuseau(meta: dict) -> timezone | ZoneInfo:
    """Le fuseau de la place, qui définit à quel **jour de bourse** un cours appartient.

    Lire les horodatages en temps universel décalerait d'un jour les places très à l'est ou
    très à l'ouest.
    """
    nom = meta.get("exchangeTimezoneName")
    if isinstance(nom, str) and nom:
        try:
            return ZoneInfo(nom)
        except (ZoneInfoNotFoundError, ValueError):
            pass

    # Repli quand la place n'est donnée que par son décalage en secondes.
    decalage = meta.get("gmtoffset")
    if isinstance(decalage, int):
        return timezone(timedelta(seconds=decalage))
    return UTC


def _jours(contenu: dict, fuseau: timezone | ZoneInfo) -> list[tuple[Date, Decimal]]:
    """Les couples (jour de bourse, cours de clôture brut), trous exclus."""
    horodatages = contenu.get("timestamp") or []
    cotations = (contenu.get("indicators") or {}).get("quote") or [{}]
    # `adjclose` existe à côté : il réinjecte les dividendes, et le moteur les compte déjà
    # (D-29, D-51). On ne le lit jamais.
    clotures = cotations[0].get("close") or []

    jours: list[tuple[Date, Decimal]] = []
    for horodatage, cloture in zip(horodatages, clotures, strict=False):
        if cloture is None or not isinstance(horodatage, int):
            # Un trou : jour férié, suspension, donnée manquante. On ne l'invente pas.
            continue
        jour = datetime.fromtimestamp(horodatage, tz=fuseau).date()
        jours.append((jour, _valeur_publiee(cloture)))

    # Une même journée ne doit apparaître qu'une fois ; en cas de doublon, le dernier gagne.
    return sorted(dict(jours).items())


def _valeur_publiee(cloture: object) -> Decimal:
    """Retrouve le nombre décimal que la place a publié.

    Les séries arrivent avec la précision d'un flottant court : la réponse contient
    `126.53500366210938` là où la bourse a coté **126,535**. Écrire ce bruit dans le cache
    rendrait tout invérifiable — le propriétaire compare ces chiffres avec son application.

    La règle est donc explicite et sans perte : on garde **le plus court nombre décimal qui
    désigne exactement la même valeur** pour la source, c'est-à-dire qui retombe sur le même
    flottant court. Si aucun ne le fait, la valeur reçue est conservée telle quelle.
    """
    valeur = Decimal(str(cloture))
    try:
        court = struct.pack("<f", float(valeur))
    except (OverflowError, ValueError):  # pragma: no cover - valeurs hors normes
        return valeur

    for chiffres in range(1, 10):
        candidat = Decimal(format(valeur, f".{chiffres}g"))
        if struct.pack("<f", float(candidat)) == court:
            return candidat
    return valeur


def _verifier_l_espacement(jours: list[tuple[Date, Decimal]], ticker: str) -> None:
    """Refuse une série qui n'est pas quotidienne, même si elle prétend l'être.

    Le piège vérifié de l'étape 4 : une plage trop large renvoie un point par mois, et le
    champ de granularité continue d'annoncer « 1d ». Valoriser là-dessus donnerait des
    chiffres plausibles et faux, sans le moindre signal.
    """
    if len(jours) < 3:
        # Trop peu de points pour conclure : une fenêtre de trois jours en contient deux.
        return

    ecarts = [
        (suivant[0] - precedent[0]).days
        for precedent, suivant in zip(jours, jours[1:], strict=False)
    ]
    if min(ecarts) > ESPACEMENT_MAXIMAL:
        raise ReponseIncoherente(
            f"la source a renvoyé une série trop espacée pour « {ticker} » "
            f"({min(ecarts)} jours entre deux cours) : ce n'est pas du quotidien, et elle "
            "l'annonce pourtant comme tel"
        )
