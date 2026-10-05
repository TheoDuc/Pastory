"""
Relevé STRUCTUREL d'un export officiel Trade Republic (« Export des transactions », D-79).

Usage :
    python scripts/inventaire_structure.py "data/Exportation de transactions.csv"
    python scripts/inventaire_structure.py "data_tiers/Exportation de transactions.csv"

C'est l'outil qui a servi à relever docs/export-officiel.md, et celui à relancer sur l'export
d'un autre utilisateur pour y chercher des types jamais vus (règle 2 de CLAUDE.md : on n'en
lit que la structure). Il ne fait que LIRE et n'écrit aucun fichier.

Il n'affiche AUCUNE valeur personnelle : ni montant, ni quantité, ni nom, ni ISIN, ni date.
Seulement :
  - des comptages par (category, type, asset_class, account_type) — des **codes**, et tout
    texte qui n'a pas la forme d'un code de la banque est masqué ;
  - les colonnes remplies, et le signe de chaque colonne numérique ;
  - la forme d'un `symbol` (ISIN, code), jamais sa valeur ;
  - des relations entre colonnes, en vrai / faux (`shares × price = amount`…) ;
  - les deux premiers mots de la description des lignes d'actif, à une condition : un mot n'est
    écrit que s'il est fait de lettres **et** revient sur au moins deux lignes du groupe. Un
    nom propre isolé, un nom de titre, un chiffre sont masqués (« # ») ;
  - l'étendue de l'export en jours.
Les lignes d'espèces ne sont décrites que par leurs comptages et le signe de leur montant.

L'ancien relevé, celui des exports pytr de l'étape 0, est dans l'historique git.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pastory.adaptateurs.trade_republic.classement import code_affichable
from pastory.adaptateurs.trade_republic.fichier import separateur

ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
REPETITIONS_MINIMALES = 2
TOLERANCE = Decimal("0.01")
COLONNES_SANS_INTERET = ("datetime", "date", "transaction_id")


def nombre(texte: str) -> Decimal | None:
    try:
        return Decimal(texte) if texte else None
    except InvalidOperation:
        return None


def signe(texte: str) -> str:
    if not texte:
        return "vide"
    valeur = nombre(texte)
    if valeur is None:
        return "illisible"
    return "+" if valeur > 0 else ("-" if valeur < 0 else "0")


def forme_du_symbole(symbole: str) -> str:
    if not symbole:
        return "vide"
    if ISIN.match(symbole):
        return "ISIN"
    if symbole.isalpha() and symbole.isupper() and len(symbole) <= 6:
        return f"code de {len(symbole)} lettres"
    return "autre"


def relation(ligne: dict[str, str]) -> str:
    """`shares × price` contre `amount`, au centime près."""
    actions, prix, montant = (nombre(ligne[c]) for c in ("shares", "price", "amount"))
    if actions is None or prix is None or montant is None:
        return "incomplète"
    ecart = abs(abs(actions * prix) - abs(montant))
    return "|shares x price| = |amount|" if ecart <= TOLERANCE else "écart > 1 centime"


def debuts_de_description(groupe: list[dict[str, str]]) -> Counter[str]:
    """Les deux premiers mots de chaque description, sans rien laisser passer de personnel.

    Un mot n'est écrit que s'il est fait de lettres ASCII et revient sur plusieurs lignes : les
    formules de la banque (« Savings plan », « Cash Dividend ») passent, un nom isolé non.
    """
    debuts = [ligne["description"].split()[:2] for ligne in groupe]
    frequence = Counter(mot for mots in debuts for mot in set(mots))

    def montrable(mot: str) -> bool:
        return mot.isascii() and mot.isalpha() and frequence[mot] >= REPETITIONS_MINIMALES

    return Counter(" ".join(mot if montrable(mot) else "#" for mot in mots) for mots in debuts)


def main(chemin: Path) -> None:
    # La même lecture que l'application : même séparateur, aucun découpage préalable.
    texte = chemin.read_text(encoding="utf-8-sig")
    entete = texte.partition("\n")[0]
    lecteur = csv.DictReader(io.StringIO(texte, newline=""), delimiter=separateur(entete))
    colonnes = lecteur.fieldnames or []
    lignes = list(lecteur)

    print(f"séparateur « {separateur(entete)} », {len(colonnes)} colonnes :")
    print("  " + ", ".join(colonnes))
    print(f"lignes : {len(lignes)}")

    groupes: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for ligne in lignes:
        cle = tuple(
            code_affichable(ligne[colonne])
            for colonne in ("category", "type", "asset_class", "account_type")
        )
        groupes[cle].append(ligne)

    for cle in sorted(groupes):
        groupe = groupes[cle]
        print(f"\n{' / '.join(cle)} : {len(groupe)} ligne(s)")
        remplies = Counter(c for ligne in groupe for c in colonnes if ligne[c])
        remplies_utiles = {c: n for c, n in remplies.items() if c not in COLONNES_SANS_INTERET}
        print(f"  colonnes remplies : {remplies_utiles}")
        if not any(ligne["symbol"] or ligne["shares"] for ligne in groupe):
            # Une ligne d'espèces : rien d'autre que son comptage et son sens.
            print(
                f"  signe de amount : {dict(Counter(signe(ligne['amount']) for ligne in groupe))}"
            )
            continue
        for colonne in ("shares", "price", "amount", "fee", "tax", "original_amount", "fx_rate"):
            signes = Counter(signe(ligne[colonne]) for ligne in groupe)
            print(f"  signe de {colonne} : {dict(signes)}")
        formes = Counter(forme_du_symbole(ligne["symbol"]) for ligne in groupe)
        print(f"  forme de symbol : {dict(formes)}")
        monnaies = Counter(code_affichable(ligne["currency"]) for ligne in groupe)
        print(f"  currency : {dict(monnaies)}")
        devises = Counter(code_affichable(ligne["original_currency"]) for ligne in groupe)
        print(f"  original_currency : {dict(devises)}")
        print(f"  shares x price : {dict(Counter(relation(ligne) for ligne in groupe))}")
        print(f"  description (deux premiers mots) : {dict(debuts_de_description(groupe))}")

    identifiants = Counter(ligne["transaction_id"] for ligne in lignes)
    print(f"\ntransaction_id en double : {sum(1 for n in identifiants.values() if n > 1)}")
    print(f"lignes sans transaction_id : {identifiants.get('', 0)}")
    jours = sorted(date.fromisoformat(ligne["date"]) for ligne in lignes if ligne["date"])
    if jours:
        print(f"étendue : {(jours[-1] - jours[0]).days} jours")
    instants = [ligne["datetime"] for ligne in lignes]
    print(f"trié par instant : {instants == sorted(instants)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(Path(sys.argv[1]))
