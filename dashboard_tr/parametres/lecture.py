"""Lire un fichier de paramètres, et refuser ce qui ne se vérifie pas (D-58).

Un paramètre est une table TOML qui porte au moins `valeur`, `unite`, `en_vigueur_depuis`,
`source` et `verifie_le`. Les tables qui n'ont pas de `valeur` ne sont que des tiroirs : elles
donnent son nom au paramètre (« prelevements_sociaux.taux »).

Les valeurs sont converties en `Decimal` **en passant par le texte** (D-33) : TOML lit `18.6`
comme un flottant, et `Decimal(18.6)` donnerait 18,60000000000000142… ; `Decimal("18.6")` donne
18,6.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date as Date
from decimal import Decimal
from pathlib import Path

from dashboard_tr.parametres import ParametresInvalides

UNITES_CONNUES = ("pour cent", "euros", "ans")

CENTIME = Decimal("0.01")


@dataclass(frozen=True)
class Parametre:
    """Une valeur, et tout ce qu'il faut pour la vérifier."""

    nom: str
    """Le chemin dans le fichier : « prelevements_sociaux.taux »."""

    valeur: Decimal
    unite: str
    source: str
    """La source officielle, en clair, avec son adresse."""

    en_vigueur_depuis: Date | None = None
    """`None` seulement pour une valeur déclarée par l'utilisateur, qui n'a pas de date de loi."""

    verifie_le: Date | None = None
    basse: Decimal | None = None
    haute: Decimal | None = None
    """La fourchette mesurée, quand la valeur est un ordre de grandeur et non un tarif."""

    note: str = ""

    @property
    def en_clair(self) -> str:
        """« 18,6 % », « 1,00 € », « 5 ans » : pour les phrases du rapport.

        Un montant en euros est écrit **au centime**, parce que c'est un montant : TOML lit
        `1.00` comme un flottant, qui a perdu son second zéro en chemin, et « 1,0 € » se lit
        mal. Un taux, lui, est écrit tel qu'il a été déclaré : 18,6 % est le chiffre de la loi.
        """
        valeur = self.valeur.quantize(CENTIME) if self.unite == "euros" else self.valeur
        texte = format(valeur, "f").replace(".", ",")
        if self.unite == "pour cent":
            return f"{texte} %"
        if self.unite == "euros":
            return f"{texte} €"
        return f"{texte} {self.unite}"

    @property
    def origine(self) -> str:
        """« en vigueur depuis le 2026-01-01, vérifié le 2026-09-27 » — ou ce qu'on en sait."""
        morceaux = []
        if self.en_vigueur_depuis is not None:
            morceaux.append(f"en vigueur depuis le {self.en_vigueur_depuis.isoformat()}")
        if self.verifie_le is not None:
            morceaux.append(f"vérifié le {self.verifie_le.isoformat()}")
        return ", ".join(morceaux)


def charger(fichier: Path) -> dict[str, Parametre]:
    """Tous les paramètres d'un fichier, par nom. Un fichier absent est une erreur : ces
    fichiers sont livrés avec l'application, il n'y a aucune raison qu'ils manquent."""
    if not fichier.exists():
        raise ParametresInvalides(f"fichier de paramètres introuvable : {fichier}")
    try:
        contenu = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        raise ParametresInvalides(
            f"{fichier} n'est pas un fichier TOML valide : {erreur}"
        ) from erreur

    parametres: dict[str, Parametre] = {}
    _parcourir(contenu, "", parametres, fichier)
    if not parametres:
        raise ParametresInvalides(f"{fichier} ne contient aucun paramètre")
    return parametres


def _parcourir(
    table: dict, prefixe: str, parametres: dict[str, Parametre], fichier: Path
) -> None:
    if "valeur" in table:
        parametres[prefixe] = _lire(table, prefixe, fichier)
        return
    for cle, valeur in table.items():
        if isinstance(valeur, dict):
            _parcourir(valeur, f"{prefixe}.{cle}" if prefixe else cle, parametres, fichier)


def _lire(table: dict, nom: str, fichier: Path) -> Parametre:
    def refuser(probleme: str) -> ParametresInvalides:
        return ParametresInvalides(f"{fichier}, paramètre [{nom}] : {probleme}")

    unite = table.get("unite")
    if unite not in UNITES_CONNUES:
        raise refuser(
            f"unité « {unite} » inconnue. Unités acceptées : {', '.join(UNITES_CONNUES)}"
        )
    source = table.get("source")
    if not isinstance(source, str) or not source.strip():
        raise refuser("pas de « source » : un taux qu'on ne peut pas vérifier n'est pas un taux")
    en_vigueur = table.get("en_vigueur_depuis")
    if not isinstance(en_vigueur, Date):
        raise refuser("pas de date « en_vigueur_depuis » (écrite AAAA-MM-JJ, sans guillemets)")
    verifie = table.get("verifie_le")
    if not isinstance(verifie, Date):
        raise refuser("pas de date « verifie_le » (écrite AAAA-MM-JJ, sans guillemets)")

    valeur = _nombre(table.get("valeur"), "valeur", refuser)
    if unite == "pour cent" and not (Decimal("0") <= valeur <= Decimal("100")):
        raise refuser(f"un taux en pour cent doit être entre 0 et 100, pas {valeur}")
    if valeur < 0:
        raise refuser(f"une valeur négative n'a pas de sens ici : {valeur}")

    basse = _nombre(table.get("basse"), "basse", refuser) if "basse" in table else None
    haute = _nombre(table.get("haute"), "haute", refuser) if "haute" in table else None
    if (basse is None) != (haute is None):
        raise refuser("une fourchette a une borne « basse » et une borne « haute », pas une seule")
    if basse is not None and haute is not None and not (basse <= valeur <= haute):
        raise refuser(f"la valeur {valeur} n'est pas dans sa fourchette [{basse} ; {haute}]")

    note = table.get("note", "")
    if not isinstance(note, str):
        raise refuser("la « note » doit être un texte")

    return Parametre(
        nom=nom,
        valeur=valeur,
        unite=unite,
        source=source.strip(),
        en_vigueur_depuis=en_vigueur,
        verifie_le=verifie,
        basse=basse,
        haute=haute,
        note=note.strip(),
    )


def _nombre(brut: object, champ: str, refuser) -> Decimal:
    """Un nombre du TOML, en `Decimal` par le texte, jamais par le flottant (D-33)."""
    if isinstance(brut, bool) or not isinstance(brut, int | float):
        raise refuser(f"« {champ} » doit être un nombre, pas {brut!r}")
    return Decimal(str(brut))
