"""Lecture d'un fichier « Export des transactions » (docs/export-officiel.md §2 et §3).

Trois choses à savoir sur ce fichier :

- **il existe en deux variantes** : virgule et champs entre guillemets, ou point-virgule sans
  guillemets (avec une colonne `value_date` à la place de `mcc_code`). Les colonnes sont donc
  repérées **par leur nom**, jamais par leur position ;
- **il mêle les actifs et toute la vie du compte courant** : noms et IBAN des contreparties,
  commerçants. D'une ligne d'espèces, on ne garde que ce qui sert à la classer et à la
  dédoublonner (§8 du relevé). Les colonnes de contrepartie ne sont jamais lues ;
- **aucune spécification n'est publiée** : un fichier sans les colonnes attendues n'est pas
  « à peu près » un export, il n'en est pas un.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from pathlib import Path

COLONNES_REQUISES = (
    "datetime",
    "date",
    "account_type",
    "category",
    "type",
    "asset_class",
    "name",
    "symbol",
    "shares",
    "price",
    "amount",
    "fee",
    "tax",
    "currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "description",
    "transaction_id",
)
"""Les colonnes que Pastory lit. Les autres (`counterparty_name`, `counterparty_iban`,
`payment_reference`, `mcc_code`, `value_date`) ne sont ni exigées ni lues."""

SEPARATEURS = (",", ";")


class FichierNonReconnu(Exception):
    """Le fichier n'est pas un export des transactions. Le message dit pourquoi, en français."""


@dataclass(frozen=True)
class Ligne:
    """Une ligne de l'export, réduite aux colonnes que Pastory lit.

    Les valeurs restent du **texte**, tel qu'écrit dans le fichier : c'est la lecture
    (`lecture.py`) qui les interprète, et qui refuse ce qu'elle ne comprend pas.
    """

    fichier: str
    """Nom du fichier d'où vient la ligne, pour la retrouver."""
    numero: int
    """Numéro de la ligne dans son fichier, en-tête compris (la première ligne de données
    est la ligne 2, comme dans un tableur)."""

    datetime: str
    date: str
    account_type: str
    category: str
    type: str
    asset_class: str
    name: str
    symbol: str
    shares: str
    price: str
    amount: str
    fee: str
    tax: str
    currency: str
    original_amount: str
    original_currency: str
    fx_rate: str
    description: str
    transaction_id: str

    @property
    def designe_un_actif(self) -> bool:
        """Vrai si la ligne nomme un titre : un code d'actif ou une quantité."""
        return bool(self.symbol or self.shares)

    def contenu(self) -> tuple[str, ...]:
        """Ce qui doit être identique pour que deux lignes soient la même opération."""
        return tuple(getattr(self, colonne) for colonne in COLONNES_REQUISES)


def _sans_donnees_personnelles(ligne: Ligne) -> Ligne:
    """Une ligne d'espèces ne garde que son type, ses dates et son identifiant.

    Son nom est celui d'une contrepartie ou d'un commerçant, sa description peut en citer un,
    et son montant est un salaire ou une dépense : rien de cela ne sert à Pastory (D-11).
    `symbol` et `shares` sont gardés **vides** — ce qui est vérifié avant d'appeler cette
    fonction — pour que la lecture puisse encore dire « ligne d'espèces sans actif ».
    """
    return replace(
        ligne,
        name="",
        amount="",
        fee="",
        tax="",
        original_amount="",
        original_currency="",
        fx_rate="",
        description="",
    )


def separateur(entete: str) -> str:
    """Le séparateur se lit sur l'en-tête, qui ne contient que des noms de colonnes."""
    return max(SEPARATEURS, key=entete.count)


def lire(chemin: Path) -> list[Ligne]:
    """Lit un export et renvoie ses lignes, dans l'ordre du fichier (qui n'est pas trié)."""
    try:
        # `utf-8-sig` accepte aussi un fichier réenregistré par un tableur, qui ajoute une
        # marque d'encodage au début.
        texte = chemin.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as erreur:
        raise FichierNonReconnu(
            "le fichier n'est pas écrit en UTF-8, comme l'export de Trade Republic"
        ) from erreur

    if not texte.strip():
        raise FichierNonReconnu("le fichier est vide")

    # Le texte est confié tel quel au lecteur CSV, sans être découpé en lignes avant : un
    # découpage préalable couperait aussi sur des caractères qu'un nom peut contenir (saut de
    # page, séparateur de ligne Unicode), et sur un retour à la ligne entre guillemets.
    entete = texte.partition("\n")[0]
    lecteur = csv.DictReader(io.StringIO(texte, newline=""), delimiter=separateur(entete))
    colonnes = {(nom or "").strip() for nom in lecteur.fieldnames or []}
    manquantes = [colonne for colonne in COLONNES_REQUISES if colonne not in colonnes]
    if manquantes:
        raise FichierNonReconnu(
            f"il manque {len(manquantes)} colonne(s) d'un export des transactions "
            f"(par exemple « {manquantes[0]} »)"
        )

    lignes: list[Ligne] = []
    for numero, brute in enumerate(lecteur, start=2):
        valeurs = {
            (cle or "").strip(): (valeur or "").strip()
            for cle, valeur in brute.items()
            if isinstance(valeur, str) or valeur is None
        }
        ligne = Ligne(
            fichier=chemin.name,
            numero=numero,
            **{colonne: valeurs.get(colonne, "") for colonne in COLONNES_REQUISES},
        )
        if not ligne.designe_un_actif:
            ligne = _sans_donnees_personnelles(ligne)
        lignes.append(ligne)
    return lignes
