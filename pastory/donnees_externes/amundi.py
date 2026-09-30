"""La source de **secours** : la répartition par pays de l'indice suivi, chez Amundi (D-77).

Pourquoi ce module existe. La source principale — extraETF — n'a pas la transparence de certains
fonds **à swap**, fonds par fonds (D-72). Or un ETF « PEA » sur un indice non européen est
synthétique **par construction**, puisqu'il doit détenir au moins 75 % de titres éligibles au PEA
(D-64) : le trou tombe donc pile sur les fonds les plus courants d'un PEA. Le service produit
d'Amundi les ouvre, et il publie la répartition de l'**indice**, qui est exactement ce que D-64
demande — mesuré le 2026-09-30 sur `FR001400U5Q4`, un PEA Monde à swap : **États-Unis 72,93 %**,
là où l'étape 7 avait relevé 15,6 % pour le panier détenu et 72,9 % pour l'indice.

**Elle ne sert QUE la géographie**, et c'est une limite de fond, pas une paresse : ses secteurs
sont du **GICS** (« Information Technology », « Health Care ») là où D-65 impose les 11 secteurs
Morningstar et **une seule** nomenclature. Les mélanger donnerait « un total juste et une
répartition fausse » — 5 points d'écart mesurés sur la technologie, piège n° 16 du comparatif. Ce
module ne lit donc **jamais** `INDEX_SECTORS`, et les secteurs d'un actif servi par lui restent
**non couverts**.

Trois pièges de cette interface, tous rencontrés en l'explorant :

1. **elle répond 200 avec une liste vide quand on la nomme mal.** Le champ de requête est
   `breakDown` **au singulier**, et ses valeurs sont `INDEX_COUNTRIES` / `INDEX_ASSETCLASSES` ;
   écrit `breakDowns`, ou avec les noms lus dans les libellés d'écran
   (`INDEX_COUNTRIES_BREAKDOWN`), elle **ne se plaint pas, elle rend le vide**. D'où le refus
   explicite d'une répartition vide, plus bas, et le test qui le couvre ;
2. **elle expose aussi les lignes détenues**, sous `composition.compositionFields`. D-63 et D-64
   l'interdisent : sur un fonds à swap, c'est le panier de collatéral, pas l'exposition. Le nom du
   champ est cité dans `CHAMP_INTERDIT` pour qu'un test vérifie que ce module ne s'en sert pas ;
3. **ses poids sont des fractions, pas des pourcentages** : `0.7293…` vaut 72,93 %. Les convertir
   au mauvais endroit donnerait un portefeuille à 1 % ou à 7 000 %.

**Et elle rend des libellés, pas des codes** — le seul des quatre critères de la recherche qu'elle
rate. La traduction en code ISO 3166-1 passe par `parametres/pays_amundi.toml`, table déclarée,
datée et sourcée, et par elle seule. C'est l'échappatoire que la règle 4 de `CLAUDE.md` autorise :
« si c'est inévitable, isoler et marquer comme fragilité. »

*Le parti pris sur un libellé inconnu, et il est discutable :* la composition entière est
**refusée**, et l'actif reste non couvert — on ne garde pas les lignes traduisibles en laissant le
reste tomber dans « non attribué ». La raison est que « non attribué » veut dire *la source n'a pas
attribué ce montant* (D-69) ; s'en servir pour dire *nous n'avons pas su traduire ce nom* mentirait
sur la cause. Le refus, lui, nomme le libellé fautif et dit quoi faire. Contrepartie assumée : un
seul pays exotique non déclaré fait perdre la répartition du fonds.
"""

from __future__ import annotations

import json
import urllib.error
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
from pastory.parametres.referentiels import LibellesDePays

NOM = "Amundi (répartition de l'indice suivi, par ISIN)"

REGLE_DE_PAYS = "pays de classification de l'indice suivi (méthodologie du fournisseur d'indice)"
"""La règle de pays de cette source, affichée avec ses chiffres (D-66, D-72).

Ce n'est **pas** celle d'extraETF, qui donne le pays d'activité, ni celle de GLEIF, qui donne le
siège social. Les trois cohabitent dans une même répartition, et l'écran doit dire laquelle
s'applique à quelle ligne — d'où ce champ porté par la composition.
"""

ADRESSE = "https://www.amundietf.fr/mapi/ProductAPI/getProductsData"

NAVIGATEUR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DELAI = 45

CONTEXTE = {"countryCode": "FRA", "languageCode": "fra", "userProfileName": "RETAIL"}
"""Le contexte que le site s'envoie à lui-même. Il choisit la langue et la gamme ; les libellés
de pays reviennent en anglais quoi qu'on demande."""

CHAMP_PAYS = "INDEX_COUNTRIES"
CHAMP_CLASSES = "INDEX_ASSETCLASSES"

CHAMP_SECTEURS_NON_LU = "INDEX_SECTORS"
"""Les secteurs de cette source. **Jamais lus** : ce sont des secteurs GICS (D-65, D-77). Nommé
ici pour qu'un test puisse vérifier qu'aucun appel ne les demande."""

CHAMP_INTERDIT = "compositionFields"
"""Les lignes détenues. **Jamais lues** (D-63, D-64). Nommé pour la même raison."""

CHAMP_DATE = "INDEX_BREAKDOWNS_AS_OF_DATE"
CHAMP_SANS_INDICE = "IS_NO_INDEX_BREAKDOWN"
CHAMP_ISIN = "ISIN"

CARACTERISTIQUES = (CHAMP_ISIN, CHAMP_DATE, CHAMP_SANS_INDICE)

INTITULE_DE_LA_DATE = (
    "champ « INDEX_BREAKDOWNS_AS_OF_DATE » de la source, qui est la date d'arrêté de l'indice"
)
"""Dit tel quel. Ici, contrairement à extraETF, le champ annonce sans ambiguïté un arrêté
d'indice — et c'est bien l'indice qu'on affiche pour un fonds synthétique (D-64)."""

CLASSES_ACTIONS = ("equity_ordinary", "equity", "equity_preferred")
"""Les classes d'actifs de cette source qui sont des **actions**, en forme normalisée.

Sert de **garde-fou négatif** et de rien d'autre : si la classe rendue n'est pas là-dedans, le
secours refuse de servir la géographie. La raison est D-68 — sur un fonds obligataire, « pays »
peut vouloir dire devise d'émission — et la prudence de D-71 : ce champ n'est pas documenté, il a
rendu `GOVERNMENT` sur un fonds qu'on croyait obligataire d'entreprises, et on ne s'appuie donc
jamais dessus pour **décider** d'un contenu. On s'en sert seulement pour **s'abstenir**.
"""

CENT = Decimal("100")
PAS = Decimal("0.0001")
"""Quatre décimales, comme extraETF : de quoi absorber le bruit de flottant sans perdre un
centième de point."""

Poster = Callable[[str, bytes], bytes]
"""Comment une requête est envoyée. Remplaçable dans les tests : aucun test du projet ne sort de
la machine."""


def corps_de_requete(actif: str) -> bytes:
    """Le corps JSON de la requête, pour cet ISIN.

    Écrit dans une fonction à part pour qu'un test puisse vérifier ce qui est **demandé** — en
    particulier qu'on ne demande ni les secteurs ni les lignes détenues.
    """
    return json.dumps(
        {
            "productIds": [actif.strip().upper()],
            "context": dict(CONTEXTE),
            "metrics": [],
            "historics": [],
            "breakDown": {"aggregationFields": [CHAMP_PAYS, CHAMP_CLASSES]},
            "characteristics": list(CARACTERISTIQUES),
        }
    ).encode("utf-8")


class SourceAmundi:
    """La source de secours, telle que `FournisseurDeCompositions` l'attend."""

    nom = NOM

    def __init__(
        self,
        libelles: LibellesDePays,
        poster: Poster | None = None,
        aujourd_hui: Date | None = None,
    ) -> None:
        self.libelles = libelles
        self.poster = poster or _envoyer
        self.aujourd_hui = aujourd_hui

    def composition(self, actif: str) -> Composition:
        """La composition de cet ISIN, ou une `ErreurDeSource` que l'appelant change en refus."""
        reponse = self.poster(ADRESSE, corps_de_requete(actif))
        return lire(reponse, actif, self.libelles, aujourd_hui=self.aujourd_hui)


def lire(
    contenu: bytes,
    actif: str,
    libelles: LibellesDePays,
    aujourd_hui: Date | None = None,
) -> Composition:
    """Lit la réponse du service. Ne touche ni aux secteurs ni aux lignes détenues."""
    charge = _json(contenu, actif)

    produits = charge.get("products")
    if not isinstance(produits, Sequence) or not produits:
        raise CompositionIndisponible(
            f"Amundi ne connaît pas {actif}. Cette source de secours ne couvre que les fonds "
            "Amundi (dont l'ancienne gamme Lyxor) : l'ETF d'un autre émetteur n'y est pas."
        )
    produit = produits[0]
    if not isinstance(produit, Mapping):
        raise CompositionIncoherente(
            f"la réponse d'Amundi pour {actif} n'a pas la forme attendue"
        )

    caracteristiques = produit.get("characteristics")
    caracteristiques = caracteristiques if isinstance(caracteristiques, Mapping) else {}

    if caracteristiques.get(CHAMP_SANS_INDICE) is True:
        raise CompositionIndisponible(
            f"Amundi annonce qu'il n'y a pas de répartition d'indice pour {actif} : ce fonds "
            "n'en suit peut-être aucun (gestion active). Rien n'est deviné à sa place."
        )

    par_champ = _repartitions(produit, actif)
    _exiger_des_actions(par_champ.get(CHAMP_CLASSES, ()), actif)

    brutes = par_champ.get(CHAMP_PAYS, ())
    if not brutes:
        # LE PIÈGE N° 1 DU MODULE. Une liste vide n'est pas « ce fonds n'a pas de pays » : c'est
        # presque toujours une requête mal nommée, et le service ne le dit pas.
        raise CompositionIncoherente(
            f"Amundi n'a rendu aucune répartition par pays pour {actif}, tout en répondant "
            "normalement. C'est le symptôme d'une interface qui a changé de vocabulaire : ce "
            "service répond « tout va bien » avec une liste vide quand on nomme mal un champ."
        )

    pays = _pays(brutes, actif, libelles)
    classes = _parts_de_classes(par_champ.get(CHAMP_CLASSES, ()), actif)

    return Composition(
        actif=actif.strip().upper(),
        pays=pays,
        secteurs=(),  # GICS : jamais employés (D-65, D-77).
        classes=classes,
        arrete_le=_jour(caracteristiques.get(CHAMP_DATE), actif),
        intitule_de_la_date=INTITULE_DE_LA_DATE,
        source=NOM,
        recupere_le=aujourd_hui or Date.today(),
        regle_de_pays=REGLE_DE_PAYS,
        replication=None,
        document=None,
    )


# --- La lecture, morceau par morceau ---------------------------------------------------


def _json(contenu: bytes, actif: str) -> Mapping[str, object]:
    try:
        charge = json.loads(contenu.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erreur:
        raise CompositionIncoherente(
            f"la réponse d'Amundi pour {actif} n'est pas du JSON lisible ({erreur}) : "
            "l'interface a peut-être changé"
        ) from erreur
    if not isinstance(charge, Mapping):
        raise CompositionIncoherente(f"la réponse d'Amundi pour {actif} n'a pas la forme attendue")
    return charge


def _repartitions(
    produit: Mapping[str, object], actif: str
) -> dict[str, Sequence[Mapping[str, object]]]:
    """Les blocs de répartition, rangés par nom de champ."""
    blocs = produit.get("breakDowns")
    if not isinstance(blocs, Sequence):
        raise CompositionIncoherente(
            f"la réponse d'Amundi pour {actif} ne porte pas de liste de répartitions"
        )
    par_champ: dict[str, Sequence[Mapping[str, object]]] = {}
    for bloc in blocs:
        if not isinstance(bloc, Mapping):
            continue
        nom = bloc.get("aggregationField")
        donnees = bloc.get("breakDownData")
        if isinstance(nom, str) and isinstance(donnees, Sequence):
            par_champ[nom] = [d for d in donnees if isinstance(d, Mapping)]
    return par_champ


def _exiger_des_actions(classes: Sequence[Mapping[str, object]], actif: str) -> None:
    """Refuse de servir la géographie d'un fonds qui n'est pas un fonds d'actions.

    D-68 : sur un fonds obligataire, « pays » peut vouloir dire la **devise d'émission** et non le
    pays de l'émetteur — « Bonds are included in US bond indices when the securities are
    denominated in U.S. dollars regardless of the domicile of the issuer ». Afficher ces pays dans
    la même répartition que ceux d'un fonds d'actions fabriquerait un chiffre faux et crédible.

    Une liste **vide** n'est pas un refus : certains fonds n'annoncent pas de classe, et
    `FournisseurDeCompositions` n'appelle de toute façon le secours que pour un actif dont le
    contenu est des actions.
    """
    if not classes:
        return
    noms = [str(c.get("aggregationName") or "") for c in classes]
    normalises = {n.strip().lower().replace("-", "_").replace(" ", "_") for n in noms if n}
    if not normalises:
        return
    if not normalises <= set(CLASSES_ACTIONS):
        lisible = ", ".join(sorted(n for n in noms if n))
        raise CompositionIndisponible(
            f"Amundi décrit {actif} comme contenant : {lisible}. La source de secours ne sert "
            "que la géographie des fonds d'**actions** : sur un fonds obligataire, « pays » peut "
            "vouloir dire la devise d'émission et non le pays de l'émetteur. Déclarez le contenu "
            "de cet actif dans actifs.toml plutôt que de lui chercher une géographie."
        )


def _pays(
    brutes: Sequence[Mapping[str, object]], actif: str, libelles: LibellesDePays
) -> tuple[Part, ...]:
    """Traduit les libellés en codes ISO, ou refuse en nommant celui qui manque."""
    parts: list[Part] = []
    inconnus: list[str] = []
    for brute in brutes:
        libelle = brute.get("aggregationName")
        if not isinstance(libelle, str) or not libelle.strip():
            raise CompositionIncoherente(
                f"une ligne de la répartition par pays d'Amundi pour {actif} n'a pas de nom"
            )
        code = libelles.code(libelle)
        if code is None:
            inconnus.append(libelle.strip())
            continue
        parts.append(Part(code=code, pour_cent=_pour_cent(brute.get("weight"), libelle, actif)))

    if inconnus:
        # On refuse tout plutôt que de laisser ces montants tomber dans « non attribué » :
        # ce libellé-là dit « la source n'a pas attribué », et ce n'est pas ce qui s'est passé.
        manquants = ", ".join(f"« {nom} »" for nom in sorted(set(inconnus)))
        raise CompositionIncoherente(
            f"Amundi emploie pour {actif} des noms de pays que la table ne connaît pas : "
            f"{manquants}. La répartition n'est pas utilisée telle quelle, parce qu'il manquerait "
            "ces montants sans qu'on puisse dire pourquoi. Ajoutez ces libellés à "
            "parametres/pays_amundi.toml, avec leur code ISO 3166-1, ou déclarez la répartition "
            "de cet actif à la main dans actifs.toml."
        )
    if not parts:
        raise CompositionIncoherente(
            f"la répartition par pays d'Amundi pour {actif} ne contient aucune ligne utilisable"
        )
    return tuple(parts)


def _parts_de_classes(
    classes: Sequence[Mapping[str, object]], actif: str
) -> tuple[Part, ...]:
    """Les classes d'actifs, telles que la source les nomme.

    Le code n'est pas traduit : `parametres/classes_actifs.toml` connaît déjà les alias des
    sources, et un code inconnu y est **affiché**, jamais rangé par défaut (règle 5).
    """
    parts = []
    for brute in classes:
        nom = brute.get("aggregationName")
        if not isinstance(nom, str) or not nom.strip():
            continue
        parts.append(
            Part(
                code=nom.strip().lower(),
                pour_cent=_pour_cent(brute.get("weight"), nom, actif),
            )
        )
    return tuple(parts)


def _pour_cent(brut: object, quoi: str, actif: str) -> Decimal:
    """Un poids de cette source est une **fraction** : 0,7293… vaut 72,93 %.

    La conversion est faite ici et une seule fois. Ailleurs, elle donnerait un portefeuille à 1 %
    ou à 7 000 % — le genre de faux qui se voit, mais seulement si on regarde.
    """
    if isinstance(brut, bool) or not isinstance(brut, int | float | str):
        raise CompositionIncoherente(
            f"le poids de « {quoi} » dans la réponse d'Amundi pour {actif} n'est pas un nombre "
            f"({brut!r})"
        )
    try:
        fraction = Decimal(str(brut))
    except InvalidOperation as erreur:
        raise CompositionIncoherente(
            f"le poids de « {quoi} » dans la réponse d'Amundi pour {actif} n'est pas lisible "
            f"({brut!r})"
        ) from erreur
    return (fraction * CENT).quantize(PAS, rounding=ROUND_HALF_UP)


def _jour(brut: object, actif: str) -> Date:
    """La date d'arrêté de l'indice. Une composition sans date est refusée (D-58, D-70)."""
    if not isinstance(brut, str) or not brut.strip():
        raise CompositionIncoherente(
            f"Amundi n'a pas donné de date d'arrêté pour {actif}. Une composition sans date "
            "n'est pas vérifiable : elle est refusée plutôt qu'affichée."
        )
    texte = brut.strip()[:10]
    try:
        return Date.fromisoformat(texte)
    except ValueError as erreur:
        raise CompositionIncoherente(
            f"la date d'arrêté rendue par Amundi pour {actif} n'est pas lisible ({brut!r})"
        ) from erreur


# --- Le réseau -------------------------------------------------------------------------


def _envoyer(adresse: str, corps: bytes) -> bytes:
    requete = urllib.request.Request(
        adresse,
        data=corps,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": NAVIGATEUR,
        },
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI) as reponse:  # noqa: S310
            return reponse.read()
    except urllib.error.HTTPError as erreur:
        raise SourceInjoignable(
            f"Amundi a refusé la demande ({erreur.code}) : la composition de secours n'a pas pu "
            "être récupérée."
        ) from erreur
    except (urllib.error.URLError, TimeoutError, OSError) as erreur:
        raise SourceInjoignable(
            f"Amundi est injoignable ({erreur}) : la composition de secours n'a pas pu être "
            "récupérée."
        ) from erreur
