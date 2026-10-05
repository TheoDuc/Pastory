"""Le registre FIRDS de l'ESMA : le code CFI d'un instrument, par ISIN (D-89).

Pourquoi ce module existe. Le contenu d'un fonds — actions, obligations, matières premières —
est lu chez extraETF (`extraetf.SourceExtraEtf.classe_d_actifs`). Une seule source, c'est une
erreur qu'on ne verrait pas. Le **code CFI** (norme ISO 10962) que les plateformes de négociation
déclarent au registre public de l'ESMA en est un second avis indépendant : pour un fonds coté
(`CE…`), sa 5ᵉ lettre dit de quoi il est fait ; pour un ETC (`EY…`), sa 6ᵉ dit son sous-jacent.

**Un témoin, jamais un juge** : le code est déclaré par l'agence de numérotation, sans contrôle.
Mesuré le 2026-10-05 sur 3 574 ISIN : 30 % de codes muets (presque tous les ISIN luxembourgeois
portent le code par défaut `CECGMS`), et une trentaine d'erreurs franches. Il ne décide donc
jamais seul : il confirme extraETF, ou il le contredit — et alors rien n'est retenu
(`pastory/reglages/recherche`).

La lecture des lettres est dans `parametres/contenus.toml`, datée et sourcée (D-58). Ce module ne
fait que rendre les codes, en majuscules : le service les indexe en minuscules.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence

from pastory.donnees_externes.cours import ReponseIncoherente, SourceInjoignable

NOM = "registre FIRDS de l'ESMA (code CFI)"

ADRESSE = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DELAI = 60

Ouvrir = Callable[[str], bytes]
"""Comment le contenu d'une adresse est obtenu. Remplaçable dans les tests : aucun test du projet
ne sort de la machine."""


def adresse(actif: str) -> str:
    """Une requête qui ne rend que les codes distincts et leur nombre de plateformes."""
    parametres = {
        "q": f"isin:{actif.strip().upper()}",
        "fq": "type_s:parent",
        "rows": 0,
        "facet": "true",
        "facet.field": "gnr_cfi_code",
        "facet.limit": 20,
        "facet.mincount": 1,
        "wt": "json",
    }
    return f"{ADRESSE}?{urllib.parse.urlencode(parametres)}"


class RegistreFirds:
    nom = NOM

    def __init__(self, ouvrir: Ouvrir | None = None) -> None:
        self.ouvrir = ouvrir or _telecharger

    def codes_cfi(self, actif: str) -> frozenset[str]:
        """Les codes CFI déclarés pour cet ISIN, en majuscules. Vide : l'ISIN n'y est pas.

        Un ISIN peut en porter plusieurs, une plateforme ne déclarant pas le même code qu'une
        autre (3,5 % des ETF mesurés, surtout des lancements récents) : c'est à l'appelant de
        dire si leurs lettres concordent.
        """
        try:
            charge = json.loads(self.ouvrir(adresse(actif)).decode("utf-8", errors="replace"))
        except json.JSONDecodeError as erreur:
            raise ReponseIncoherente(
                f"la réponse du registre de l'ESMA pour {actif} n'est pas du JSON lisible"
            ) from erreur
        champs = (charge.get("facet_counts") or {}).get("facet_fields") or {}
        brut = champs.get("gnr_cfi_code") if isinstance(champs, Mapping) else None
        if not isinstance(brut, Sequence) or isinstance(brut, str | bytes):
            raise ReponseIncoherente(
                f"le registre de l'ESMA a répondu pour {actif} sans liste de codes CFI : "
                "l'interface a peut-être changé"
            )
        # La facette alterne valeur et nombre : ['ceoges', 83, 'ceogms', 2].
        return frozenset(
            str(code).strip().upper()
            for code in brut[::2]
            if isinstance(code, str) and len(code.strip()) == 6
        )


def _telecharger(adresse: str) -> bytes:
    requete = urllib.request.Request(adresse, headers={"User-Agent": NAVIGATEUR})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:  # noqa: S310
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        raise SourceInjoignable(
            f"le registre de l'ESMA a refusé la demande ({erreur.code})"
        ) from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise SourceInjoignable(f"le registre de l'ESMA est injoignable ({erreur})") from erreur
