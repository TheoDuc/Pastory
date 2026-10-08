"""Écrire un chiffre à l'écran : **une fonction par unité**, et aucune autre façon de le faire.

Le moteur manipule deux unités différentes, et les confondre a déjà produit « 6264,00 % » au lieu
de 62,64 % (conception-interface §3.1) :

| Unité | 62,64 % s'écrit | Fonction |
|---|---|---|
| **taux** (une fraction) | `Decimal("0.6264")` | `taux()` — TRI, TWRR, poids d'un coût |
| **pour cent** | `Decimal("62.64")` | `pour_cent()` — une part, un TER, un taux d'impôt |

**Aucune vue ne multiplie par cent** : elle appelle l'une ou l'autre.

Les conventions, toutes tirées du contrat (§3.2) et de la maquette :

- deux décimales, arrondies « comme à la main » (`ROUND_HALF_UP`, comme `moteur/rapport.py`) ;
- l'espace fine insécable entre les milliers, l'espace insécable avant « € » et « % » : un
  montant ne se coupe jamais en fin de ligne ;
- le **signe** devant un gain, `+` ou `−` (le vrai signe moins), parce qu'il se lit avant la
  couleur ;
- une valeur absente s'écrit `–` : c'est la marque « sans objet » du contrat (§2.1). Le motif de
  l'absence, quand il existe, est écrit à côté, en mots — jamais un zéro.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal

ABSENT = "–"
"""Un chiffre qui n'existe pas (contrat §2.1, « Sans objet »). Jamais « 0,00 »."""

MILLIERS = " "
"""L'espace fine insécable, comme l'écrit un navigateur réglé en français."""

INSECABLE = " "
MOINS = "−"

CENTIEME = Decimal("0.01")
UN = Decimal("1")
CENT = Decimal("100")


def _chiffres(valeur: Decimal, decimales: Decimal = CENTIEME) -> str:
    """`1234.5` → `1 234,50` : la seule fonction qui écrit des chiffres."""
    arrondi = valeur.quantize(decimales, rounding=ROUND_HALF_UP)
    entier, _, reste = f"{abs(arrondi):f}".partition(".")
    groupes = []
    while len(entier) > 3:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    groupes.insert(0, entier)
    texte = MILLIERS.join(groupes)
    return f"{texte},{reste}" if reste else texte


def _signe(valeur: Decimal, decimales: Decimal = CENTIEME) -> str:
    arrondi = valeur.quantize(decimales, rounding=ROUND_HALF_UP)
    if arrondi > 0:
        return "+"
    if arrondi < 0:
        return MOINS
    return ""


def montant(valeur: Decimal | None, devise: str = "EUR") -> str:
    """`1 234,56 €`. Une autre devise s'écrit en clair, jamais convertie (D-51)."""
    if valeur is None:
        return ABSENT
    texte = _chiffres(valeur)
    if valeur.quantize(CENTIEME, rounding=ROUND_HALF_UP) < 0:
        texte = MOINS + texte
    return f"{texte}{INSECABLE}{_unite(devise)}"


def montant_signe(valeur: Decimal | None, devise: str = "EUR") -> str:
    """`+132,40 €`, `−18,90 €` : pour un gain, une plus-value, un flux."""
    if valeur is None:
        return ABSENT
    return f"{_signe(valeur)}{_chiffres(valeur)}{INSECABLE}{_unite(devise)}"


def montant_entier(valeur: Decimal | None) -> str:
    """`12 345 €` : au centre d'un anneau et sur l'axe d'une courbe, où les centimes encombrent
    sans rien dire. Jamais dans un tableau ni une tuile."""
    if valeur is None:
        return ABSENT
    texte = _chiffres(valeur, UN)
    if valeur.quantize(UN, rounding=ROUND_HALF_UP) < 0:
        texte = MOINS + texte
    return f"{texte}{INSECABLE}€"


def taux(valeur: Decimal | None, signe: bool = True) -> str:
    """Un **taux** (une fraction : 0,6264) écrit en pour cent : `+62,64 %`.

    Pour le TRI, le TWRR, une variation, le poids d'un coût. `signe=False` pour un poids ou un
    taux de frais, qui n'ont pas de sens négatif."""
    if valeur is None:
        return ABSENT
    en_pour_cent = valeur * CENT
    prefixe = _signe(en_pour_cent) if signe else ""
    return f"{prefixe}{_chiffres(en_pour_cent)}{INSECABLE}%"


def pour_cent(valeur: Decimal | None) -> str:
    """Un **pour cent** déjà calculé (62,64) : `62,64 %`. Pour une part, un TER, un taux d'impôt."""
    if valeur is None:
        return ABSENT
    texte = _chiffres(valeur)
    if valeur.quantize(CENTIEME, rounding=ROUND_HALF_UP) < 0:
        texte = MOINS + texte
    return f"{texte}{INSECABLE}%"


def quantite(valeur: Decimal | None) -> str:
    """Une quantité de parts : deux décimales au moins, six au plus.

    Une fraction de crypto ou d'ETF acheté en plan d'épargne porte souvent six décimales, et
    les couper cacherait justement ce que l'utilisateur compare avec son application."""
    if valeur is None:
        return ABSENT
    exposant = -valeur.normalize().as_tuple().exponent
    decimales = min(max(int(exposant), 2), 6) if isinstance(exposant, int) else 2
    return _chiffres(valeur, Decimal(1).scaleb(-decimales))


def date_courte(jour: Date | None) -> str:
    """`25/09/2026`."""
    if jour is None:
        return ABSENT
    return jour.strftime("%d/%m/%Y")


def duree_en_clair(jours: int | None) -> str:
    """`18 mois`, `2 ans et 3 mois` : la durée d'une période, pour un lecteur."""
    if jours is None:
        return ABSENT
    if jours < 31:
        return f"{jours} jour{'s' if jours > 1 else ''}"
    mois = round(jours / 30.44)
    if mois < 24:
        return f"{mois} mois"
    annees = jours // 365
    reste = round((jours - annees * 365) / 30.44)
    texte = f"{annees} an{'s' if annees > 1 else ''}"
    return f"{texte} et {reste} mois" if reste else texte


def classe_du_signe(valeur: Decimal | None) -> str:
    """`gain`, `perte` ou rien, pour un **montant** : la classe CSS qui **double** un signe,
    jamais ne le remplace. Elle suit le montant tel qu'il s'écrit : `0,00 €` n'a pas de couleur."""
    if valeur is None:
        return ""
    return _classe(_signe(valeur))


def classe_du_taux(valeur: Decimal | None) -> str:
    """La même chose pour un **taux** : le signe se lit sur le pour cent écrit, pas sur la
    fraction — sans quoi +0,4 % (0,004) n'aurait pas de couleur."""
    if valeur is None:
        return ""
    return _classe(_signe(valeur * CENT))


def _classe(signe: str) -> str:
    return {"+": "gain", MOINS: "perte"}.get(signe, "")


def _unite(devise: str) -> str:
    return "€" if devise == "EUR" else devise
