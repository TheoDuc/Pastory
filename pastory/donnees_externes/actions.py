"""Le pays et le secteur d'une action détenue en direct (D-62, D-66).

Pourquoi ce module existe alors que le propriétaire ne détient aucune action : parce que l'achat
d'actions à l'unité est **courant** chez Trade Republic, et que les fonctionnalités visent
l'utilisateur type ([D-62](../../docs/decisions.md)). Une répartition qui ne saurait pas traiter une
action serait inutilisable pour beaucoup de gens.

Une action a une composition triviale — un pays, un secteur, 100 % — mais elle ne vient pas de la
même source que celle des ETF, qui ne connaît que les fonds. **Deux sources gratuites, chacune
pour ce qu'elle fait le mieux :**

- **le pays** vient de **GLEIF**, le registre officiel des identifiants d'entités juridiques :
  le pays du **siège social**, en **code ISO 3166-1**, interrogeable **par ISIN**, sans clé ;
- **le secteur** vient de la recherche de la source de cours déjà employée par le projet : un
  **libellé** de secteur, sur la même nomenclature à 11 postes que la source des ETF.

**Deux choses à savoir, et elles sont écrites à l'écran, pas cachées ici :**

1. **la règle de pays n'est pas la même que pour un ETF.** Ici c'est le **siège social** ; là-bas
   c'est le **pays d'activité**. Accenture est irlandaise pour l'une et américaine pour l'autre.
   Les deux réponses sont justes, elles ne répondent pas à la même question, et
   [D-66](../../docs/decisions.md) impose de le dire plutôt que de choisir en silence ;
2. **le secteur arrive sous forme de libellé, pas de code.** C'est une **fragilité** au sens de la
   règle 4 de `CLAUDE.md`, et elle est isolée ici, dans `_code_du_secteur()`. Le libellé n'est pas
   interprété : il est seulement **normalisé** (minuscules, espaces en soulignés), puis confronté
   aux alias de `parametres/secteurs.toml`. Un libellé que la nomenclature ne reconnaît pas n'est
   jamais rangé au hasard : il remonte tel quel et l'écran l'affiche (règle 5).

Rien ici n'a de date d'arrêté, et c'est normal : le siège social et le secteur d'une société ne
sont pas un portefeuille, il n'y a rien à arrêter. La date transportée est donc **le jour de la
lecture**, et l'intitulé le dit en clair.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import date as Date
from decimal import Decimal

from pastory.donnees_externes.composition import (
    Composition,
    CompositionIncoherente,
    CompositionIndisponible,
    Part,
)
from pastory.donnees_externes.cours import SourceInjoignable

NOM = "GLEIF (pays du siège) et Yahoo Finance (secteur)"

ADRESSE_GLEIF = "https://api.gleif.org/api/v1/lei-records"
ADRESSE_RECHERCHE = "https://query1.finance.yahoo.com/v1/finance/search"

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DELAI = 20

CENT = Decimal("100")

REGLE_DE_PAYS = "siège social de la société (registre GLEIF)"
"""Dit tel quel à l'écran, à côté du chiffre : c'est l'exigence de D-66."""

INTITULE_DE_LA_DATE = (
    "jour de la lecture : le siège et le secteur d'une société ne sont pas un portefeuille, "
    "ils n'ont pas de date d'arrêté"
)

CLASSE_ACTIONS = "stock"
"""Une action est à 100 % dans la classe « actions ». Le code est celui qu'emploie la source des
ETF, pour que les deux se rangent au même endroit (`parametres/classes_actifs.toml`)."""

Ouvrir = Callable[[str], bytes]


class SourceDActions:
    """Le pays et le secteur d'une société cotée, tels que le fournisseur les attend."""

    nom = NOM

    def __init__(self, ouvrir: Ouvrir | None = None, aujourd_hui: Date | None = None) -> None:
        self.ouvrir = ouvrir or _telecharger
        self.aujourd_hui = aujourd_hui

    def composition(self, actif: str, ticker: str) -> Composition:
        """Le pays et le secteur de cette société.

        Il faut **au moins l'un des deux** pour que la réponse ait un intérêt. Si les deux
        manquent, c'est un refus : l'actif sera marqué non couvert, avec son montant (D-69).
        """
        pays = self._pays(actif)
        secteur = self._secteur(actif, ticker)
        if pays is None and secteur is None:
            raise CompositionIndisponible(
                f"ni le pays ni le secteur de {actif} n'ont pu être obtenus : la société est "
                "comptée comme non couverte, avec son montant."
            )
        jour = self.aujourd_hui if self.aujourd_hui is not None else Date.today()
        return Composition(
            actif=actif,
            pays=() if pays is None else (Part(code=pays, pour_cent=CENT),),
            secteurs=() if secteur is None else (Part(code=secteur, pour_cent=CENT),),
            classes=(Part(code=CLASSE_ACTIONS, pour_cent=CENT),),
            arrete_le=jour,
            intitule_de_la_date=INTITULE_DE_LA_DATE,
            source=NOM,
            recupere_le=jour,
            regle_de_pays=REGLE_DE_PAYS,
            replication=None,
        )

    # --- Le pays, par le registre officiel ----------------------------------------------

    def _pays(self, actif: str) -> str | None:
        """Le pays du siège social, en code ISO, ou `None`.

        GLEIF est interrogeable **par ISIN**, ce qui évite tout détour par un ticker, et répond
        un **code** : aucun libellé à interpréter.
        """
        parametres = urllib.parse.urlencode(
            {"filter[isin]": actif.strip().upper(), "page[size]": 1}
        )
        charge = _json(self.ouvrir(f"{ADRESSE_GLEIF}?{parametres}"), actif, "GLEIF")
        donnees = charge.get("data") if isinstance(charge, Mapping) else None
        if not isinstance(donnees, Sequence) or not donnees:
            return None
        premier = donnees[0]
        if not isinstance(premier, Mapping):
            return None
        entite = _sous(_sous(premier, "attributes"), "entity")
        # Le siège d'abord, l'adresse légale ensuite : une société peut être enregistrée dans un
        # territoire de domiciliation tout en exerçant ailleurs, et c'est le siège qui décrit le
        # mieux « de quel pays elle est » au sens de D-66.
        for champ in ("headquartersAddress", "legalAddress"):
            code = _sous(entite, champ).get("country")
            if isinstance(code, str) and len(code.strip()) == 2 and code.strip().isalpha():
                return code.strip().upper()
        juridiction = entite.get("jurisdiction")
        if isinstance(juridiction, str) and len(juridiction.strip()) == 2:
            return juridiction.strip().upper()
        return None

    # --- Le secteur, et sa fragilité assumée --------------------------------------------

    def _secteur(self, actif: str, ticker: str) -> str | None:
        """Le secteur de la société, normalisé en code, ou `None`.

        La recherche est faite sur le **ticker retenu** (trouvé et contrôlé, ou corrigé), et le
        résultat n'est gardé que si le symbole renvoyé est bien celui-là : prendre « la première
        réponse » a déjà fait retenir la mauvaise cotation à l'étape 4.
        """
        voulu = ticker.strip().upper()
        if not voulu:
            return None
        parametres = urllib.parse.urlencode(
            {"q": ticker.strip(), "quotesCount": 10, "newsCount": 0}
        )
        charge = _json(self.ouvrir(f"{ADRESSE_RECHERCHE}?{parametres}"), actif, "Yahoo Finance")
        resultats = charge.get("quotes") if isinstance(charge, Mapping) else None
        if not isinstance(resultats, Sequence):
            return None
        for quote in resultats:
            if not isinstance(quote, Mapping):
                continue
            symbole = quote.get("symbol")
            if not isinstance(symbole, str) or symbole.strip().upper() != voulu:
                continue
            return _code_du_secteur(quote.get("sector"))
        return None


def _code_du_secteur(libelle: object) -> str | None:
    """**La fragilité de ce module, isolée en une fonction** (règle 4 de `CLAUDE.md`).

    La source ne donne pas de code de secteur : elle donne « Consumer Cyclical ». On ne
    l'interprète pas et on ne le traduit pas — on le **normalise** exactement comme
    `parametres/referentiels.normaliser()`, pour que les alias de `secteurs.toml` puissent le
    reconnaître. S'ils ne le reconnaissent pas, le code remonte tel quel et l'écran l'affiche
    comme non reconnu : jamais rangé par défaut (règle 5).

    Ce qui rend la fragilité acceptable : les onze libellés de cette source sont ceux de la
    nomenclature retenue, et un libellé inattendu ne produit **aucun** chiffre faux — seulement
    un poste visiblement non reconnu.
    """
    if not isinstance(libelle, str) or not libelle.strip():
        return None
    return libelle.strip().lower().replace("-", "_").replace(" ", "_")


# --- Outils ----------------------------------------------------------------------------


def _sous(table: Mapping[str, object], cle: str) -> Mapping[str, object]:
    valeur = table.get(cle)
    return valeur if isinstance(valeur, Mapping) else {}


def _json(contenu: bytes, actif: str, service: str) -> Mapping[str, object]:
    try:
        charge = json.loads(contenu.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise CompositionIncoherente(
            f"la réponse de {service} pour {actif} n'est pas du JSON lisible ({erreur})"
        ) from erreur
    if not isinstance(charge, Mapping):
        raise CompositionIncoherente(
            f"la réponse de {service} pour {actif} n'a pas la forme attendue"
        )
    return charge


def _telecharger(adresse: str) -> bytes:
    requete = urllib.request.Request(adresse, headers={"User-Agent": NAVIGATEUR})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:  # noqa: S310
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        raise SourceInjoignable(
            f"la demande a été refusée ({erreur.code}) : le pays ou le secteur de cette action "
            "n'a pas pu être récupéré. Vous pouvez les déclarer à la main dans actifs.toml."
        ) from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise SourceInjoignable(
            f"service injoignable ({erreur}) : vérifiez la connexion, le pare-feu ou l'antivirus."
        ) from erreur
