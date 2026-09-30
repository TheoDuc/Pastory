"""La composition d'un ETF chez extraETF, par ISIN (D-63).

Un seul appel, `api-v2/detail/?isin=<ISIN>`, sans clé, sans jeton, sans cookie. La réponse est du
JSON, et elle porte les trois répartitions **déjà agrégées**, avec des **codes** : pays en ISO
3166-1 alpha-2, secteurs en code machine. C'est ce qui permet de calculer sans lire un seul libellé
affiché (règle 4 de `CLAUDE.md`) — les libellés de cette source sont en allemand, même sur ses
pages anglaises.

**La règle absolue de ce module, et la raison pour laquelle il existe : on ne lit jamais les lignes
détenues** (`items`). Vérifié le 2026-09-27 sur un ETF *MSCI World* français éligible au PEA : son
unique ligne est un contrat d'échange, `TRS MSCI World NR USD`, auquel la source attribue
`country: "USA"` et un poids de 100 %. Un calcul fondé sur les lignes afficherait donc **100 %
d'États-Unis pour un ETF mondial**. Les listes agrégées, elles, décrivent l'indice : 32 pays et
11 secteurs pour ce même fonds (D-64).

Trois limites à connaître, écrites une fois ici :

1. **l'API n'est pas documentée**, et son usage n'est pas explicitement autorisé : usage personnel
   toléré, pas un droit (D-63). Elle peut disparaître sans préavis, et l'application doit alors le
   dire et continuer sans répartition ;
2. **elle ne connaît que les fonds.** Interrogée avec l'ISIN d'une action, elle répond `count: 0` ;
3. **la date porte un nom ambigu** : le champ employé parle de l'**indice**
   (`index_date_last_update`), pas explicitement de l'arrêté du portefeuille. On transporte donc la
   date **et** ce qu'elle dit d'elle-même, sans affirmer plus (D-70).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from pastory.donnees_externes.composition import (
    Composition,
    CompositionIncoherente,
    CompositionIndisponible,
    Part,
)
from pastory.donnees_externes.cours import SourceInjoignable

NOM = "extraETF (composition agrégée par ISIN)"

ADRESSE = "https://extraetf.com/api-v2/detail/"

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DELAI = 30

CHAMP_PAYS = "country_stocks_exposure_list"
CHAMP_SECTEURS = "global_stock_exposure_list"
CHAMP_CLASSES = "asset_allocation_exposure_list"
CHAMP_DATE = "index_date_last_update"

INTITULE_DE_LA_DATE = (
    "champ « index_date_last_update » de la source, qui nomme l'indice et non le portefeuille"
)
"""Dit tel quel à l'utilisateur : c'est la réserve du comparatif §3.1, et elle est honnête."""

CHAMP_INTERDIT = "items"
"""Les lignes détenues. Elles ne sont **jamais** lues (D-63, D-64). Nommé ici pour qu'un test
puisse vérifier que ce module ne s'en sert pas."""

CLASSES_RENSEIGNEES = ("stock", "bond", "preferred", "convertible")
"""Les classes d'actifs qui **disent quelque chose**, dans le vocabulaire de cette source.

`cash` et `other` n'en disent rien : ce sont les cases où la source range ce qu'elle ne sait pas
décrire. Ce module est le bon endroit pour le savoir, parce qu'il est déjà le seul à connaître les
noms de champs de cette source.
"""

PART_RENSEIGNEE_MINIMALE = Decimal("50")
"""En pour cent. En dessous, la source n'a pas la transparence du fonds.

**Constaté sur de vrais ETF le 2026-09-27**, et c'est la raison d'être de ce garde-fou : pour
certains fonds, la source répond normalement — avec une date et un drapeau de réplication — mais
annonce **« other » : 100 %** et zéro pays, zéro secteur. Ce n'est pas un fonds composé d'« autres
choses » : c'est un fonds dont elle ignore le contenu.

Sans ce contrôle, un tel actif atterrirait dans « hors répartition actions », c'est-à-dire présenté
à l'utilisateur comme de l'obligataire ou des liquidités — **un chiffre faux et crédible**. Il est
donc traité comme **non couvert** : composition inconnue, montant affiché, rien d'inventé (D-69).
"""

PAS = Decimal("0.0001")
"""Quatre décimales : de quoi absorber le bruit de flottant de la source (0,009 %, 0,005 %) sans
perdre un centième de point."""

Ouvrir = Callable[[str], bytes]
"""Comment le contenu d'une adresse est obtenu. Remplaçable dans les tests : aucun test du projet
ne sort de la machine."""


class SourceExtraEtf:
    """La source, telle que `FournisseurDeCompositions` l'attend."""

    nom = NOM

    def __init__(self, ouvrir: Ouvrir | None = None, aujourd_hui: Date | None = None) -> None:
        self.ouvrir = ouvrir or _telecharger
        self.aujourd_hui = aujourd_hui

    def composition(self, actif: str) -> Composition:
        """La composition de cet ISIN, ou une `ErreurDeSource` que l'appelant change en refus."""
        adresse = f"{ADRESSE}?{urllib.parse.urlencode({'isin': actif.strip().upper()})}"
        return lire(self.ouvrir(adresse), actif, aujourd_hui=self.aujourd_hui)


def lire(contenu: bytes, actif: str, aujourd_hui: Date | None = None) -> Composition:
    """Lit la réponse de l'API. Ne touche jamais aux lignes détenues (D-63)."""
    try:
        charge = json.loads(contenu.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise CompositionIncoherente(
            f"la réponse d'extraETF pour {actif} n'est pas du JSON lisible ({erreur}) : "
            "l'interface a peut-être changé"
        ) from erreur

    if not isinstance(charge, Mapping):
        raise CompositionIncoherente(
            f"la réponse d'extraETF pour {actif} n'a pas la forme attendue"
        )

    resultats = charge.get("results")
    if not isinstance(resultats, Sequence) or not resultats:
        raise CompositionIndisponible(
            f"extraETF ne connaît pas {actif}. Cette source ne couvre que les fonds : une action "
            "détenue en direct, une crypto ou un ETF d'un émetteur absent de sa base n'y sont pas."
        )

    fonds = resultats[0]
    if not isinstance(fonds, Mapping):
        raise CompositionIncoherente(
            f"la réponse d'extraETF pour {actif} n'a pas la forme attendue"
        )

    repartitions = fonds.get("portfolio_breakdown")
    if not isinstance(repartitions, Mapping):
        raise CompositionIncoherente(
            f"extraETF a répondu pour {actif}, mais sans aucune répartition de portefeuille : "
            "le fonds est peut-être trop récent, ou l'interface a changé"
        )

    arrete_le = _jour(fonds.get(CHAMP_DATE) or repartitions.get(CHAMP_DATE), actif)
    classes = _parts(repartitions.get(CHAMP_CLASSES), CHAMP_CLASSES, actif)
    _exiger_de_la_transparence(classes, actif)
    return Composition(
        actif=actif,
        pays=_parts(repartitions.get(CHAMP_PAYS), CHAMP_PAYS, actif, majuscules=True),
        secteurs=_parts(repartitions.get(CHAMP_SECTEURS), CHAMP_SECTEURS, actif),
        classes=classes,
        arrete_le=arrete_le,
        intitule_de_la_date=INTITULE_DE_LA_DATE,
        source=NOM,
        recupere_le=aujourd_hui if aujourd_hui is not None else Date.today(),
        replication=_replication(fonds),
        document=_document(fonds),
    )


def _exiger_de_la_transparence(classes: tuple[Part, ...], actif: str) -> None:
    """Refuse un fonds dont la source ne sait rien, même si elle répond poliment.

    Une liste de classes d'actifs **absente** n'est pas un problème : certains fonds n'en ont pas,
    et leurs pays et secteurs suffisent. Une liste **présente** qui met tout dans « autres », si.
    """
    if not classes:
        return
    renseignee = sum(
        (part.pour_cent for part in classes if part.code in CLASSES_RENSEIGNEES),
        Decimal("0"),
    )
    if renseignee < PART_RENSEIGNEE_MINIMALE:
        raise CompositionIndisponible(
            f"extraETF répond pour {actif}, mais ne décrit que {renseignee} % de ce fonds en "
            f"actions ou en obligations : le reste est rangé dans « autres », ce qui veut dire "
            f"qu'elle n'a pas sa transparence. L'actif est donc traité comme non couvert, plutôt "
            f"que présenté comme de l'obligataire ou des liquidités, ce qui serait faux. Vous "
            f"pouvez déclarer sa composition à la main dans actifs.toml."
        )


def _parts(
    brut: object, champ: str, actif: str, majuscules: bool = False
) -> tuple[Part, ...]:
    """Une liste `{code, value}` de la source, devenue des parts.

    Une liste absente n'est pas une erreur : un ETF obligataire n'a pas de répartition
    sectorielle d'actions, et c'est le sens même de [D-68]. Une liste **mal formée**, si.
    """
    if brut is None:
        return ()
    if not isinstance(brut, Sequence) or isinstance(brut, str | bytes):
        raise CompositionIncoherente(
            f"le champ « {champ} » d'extraETF pour {actif} n'est pas une liste"
        )

    parts: list[Part] = []
    for poste in brut:
        if not isinstance(poste, Mapping):
            raise CompositionIncoherente(
                f"un poste de « {champ} » d'extraETF pour {actif} n'a pas la forme attendue"
            )
        code = poste.get("code")
        if not isinstance(code, str) or not code.strip():
            # Un poste sans code est inexploitable : on ne peut ni le nommer ni le ranger, et
            # deviner d'après son libellé allemand est exactement ce que la règle 4 interdit.
            raise CompositionIncoherente(
                f"un poste de « {champ} » d'extraETF pour {actif} n'a pas de code : seul le "
                "libellé est fourni, et un libellé ne se calcule pas (règle 4)"
            )
        propre = code.strip().upper() if majuscules else code.strip().lower()
        parts.append(Part(code=propre, pour_cent=_poids(poste.get("value"), champ, actif)))
    return tuple(parts)


def _poids(valeur: object, champ: str, actif: str) -> Decimal:
    if isinstance(valeur, bool) or not isinstance(valeur, int | float | str):
        raise CompositionIncoherente(
            f"un poids de « {champ} » d'extraETF pour {actif} n'est pas un nombre : {valeur!r}"
        )
    try:
        return Decimal(str(valeur)).quantize(PAS, rounding=ROUND_HALF_UP)
    except InvalidOperation as erreur:
        raise CompositionIncoherente(
            f"un poids de « {champ} » d'extraETF pour {actif} n'est pas un nombre : {valeur!r}"
        ) from erreur


def _jour(valeur: object, actif: str) -> Date:
    """La date d'arrêté. Absente, la composition est refusée (D-58, D-70)."""
    if not isinstance(valeur, str) or not valeur.strip():
        raise CompositionIncoherente(
            f"extraETF n'annonce aucune date pour la composition de {actif}. Une répartition sans "
            "date n'est pas vérifiable : elle est refusée plutôt qu'affichée."
        )
    texte = valeur.strip()
    try:
        return Date.fromisoformat(texte[:10])
    except ValueError as erreur:
        raise CompositionIncoherente(
            f"la date annoncée par extraETF pour {actif} ne se lit pas : {valeur!r}"
        ) from erreur


def _replication(fonds: Mapping[str, object]) -> str | None:
    """« synthétique » ou « physique », d'après les **drapeaux** et non le libellé allemand.

    `None` quand la source ne dit rien : on ne devine pas. Le rapport affiche alors la
    composition sans préciser la réplication, ce qui est exact.
    """
    drapeaux = [fonds.get("is_swap_based_etf"), fonds.get("is_synthetic_replication")]
    connus = [un for un in drapeaux if isinstance(un, bool)]
    if not connus:
        return None
    return "synthétique" if any(connus) else "physique"


def _document(fonds: Mapping[str, object]) -> str | None:
    """Le lien vers le document de l'émetteur, pour vérifier à la main. Le DIC d'abord."""
    for champ in ("kiid_url", "factsheet_url_en", "factsheet_url"):
        lien = fonds.get(champ)
        if isinstance(lien, str) and lien.strip().startswith("http"):
            return lien.strip()
    return None


def _telecharger(adresse: str) -> bytes:
    requete = urllib.request.Request(adresse, headers={"User-Agent": NAVIGATEUR})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:  # noqa: S310
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        raise SourceInjoignable(
            f"extraETF a refusé la demande ({erreur.code}) : la composition n'a pas pu être "
            "récupérée. C'est une interface non documentée, qui peut fermer sans préavis ; la "
            "répartition sera simplement absente."
        ) from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise SourceInjoignable(
            f"extraETF est injoignable ({erreur}) : vérifiez la connexion, le pare-feu ou "
            "l'antivirus."
        ) from erreur
