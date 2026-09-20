"""Comparer ce que le moteur a compté avec ce que la banque dit détenir.

C'est le contrôle le plus fort de tout le projet : il ne dépend d'aucune lecture de texte,
d'aucune déduction et d'aucune règle. Soit les quantités tombent juste, soit il manque
quelque chose.

**Un actif que la banque détient et que le moteur ignore est le cas intéressant** : c'est la
signature de titres entrés sans aucun événement dans l'export, limite connue de D-15 (un PEA
transféré depuis un autre établissement, par exemple).

Deux règles, arbitrées le 2026-09-20 (D-46) :

- **la quantité est un contrôle** : tout écart est signalé ;
- **le prix de revient de la banque est une information** : il est affiché à côté du nôtre,
  jamais comparé automatiquement. On ignore s'il inclut les frais d'achat, que D-13 exclut.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from dashboard_tr import tableur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.pivot.position_reelle import PositionReelle

TOLERANCE_QUANTITE = Decimal("0.000001")
"""Écart de quantité en deçà duquel on ne dit rien.

La banque publie ses quantités arrondies à six décimales : deux nombres qui ne diffèrent
qu'au-delà décrivent la même position. Au-delà, l'écart est réel et il est dit.
"""


class Accord(StrEnum):
    """Ce que le rapprochement a trouvé pour un actif."""

    ACCORD = "accord"
    """Les deux quantités concordent."""

    ECART = "écart"
    """Les deux comptent des parts, mais pas le même nombre."""

    ABSENT_DE_LA_BANQUE = "absent de la banque"
    """Le moteur détient des parts que la banque ne montre pas."""

    ABSENT_DU_MOTEUR = "absent du moteur"
    """La banque détient des parts dont aucune opération ne parle : **le cas à examiner**."""


@dataclass(frozen=True)
class LigneRapprochement:
    """Un actif, vu des deux côtés."""

    actif: str
    accord: Accord
    quantite_moteur: Decimal | None
    quantite_banque: Decimal | None
    nom_actif: str | None = None
    prix_de_revient_moteur: Decimal | None = None
    prix_de_revient_banque: Decimal | None = None
    """Information seulement, jamais un contrôle (D-46)."""

    @property
    def ecart(self) -> Decimal | None:
        """Quantité du moteur moins quantité de la banque, quand les deux existent."""
        if self.quantite_moteur is None or self.quantite_banque is None:
            return None
        return self.quantite_moteur - self.quantite_banque

    @property
    def concorde(self) -> bool:
        return self.accord is Accord.ACCORD


@dataclass(frozen=True)
class Rapprochement:
    """Le résultat de la comparaison, actif par actif."""

    lignes: tuple[LigneRapprochement, ...]
    signalements: tuple[Signalement, ...]

    lignes_illisibles: int = 0
    """Lignes du fichier de la banque qui n'ont pas pu être lues.

    Tant qu'il y en a, **le rapprochement est incomplet** : un actif signalé « absent de la
    banque » peut très bien se trouver dans l'une de ces lignes. Le rapport le dit, pour que
    le désaccord ne soit pas pris pour un diagnostic."""

    @property
    def desaccords(self) -> list[LigneRapprochement]:
        return [ligne for ligne in self.lignes if not ligne.concorde]

    @property
    def tout_concorde(self) -> bool:
        return not self.desaccords and not self.lignes_illisibles


def rapprocher(
    portefeuille: Portefeuille,
    positions_reelles: Iterable[PositionReelle],
    lignes_illisibles: int = 0,
) -> Rapprochement:
    """Compare les quantités du moteur à celles de la banque, actif par actif.

    Les quantités du moteur sont additionnées **toutes poches confondues** : la banque liste
    des ISIN sans dire dans quelle enveloppe ils sont détenus, et un même ETF peut être à la
    fois en PEA et en CTO.

    `lignes_illisibles` est le nombre de lignes que l'adaptateur n'a pas su lire. Le
    rapprochement les compte pour pouvoir dire qu'il est incomplet, plutôt que de faire
    passer un fichier abîmé pour un désaccord.
    """
    du_moteur = portefeuille.quantites_par_actif()
    de_la_banque = _par_actif(positions_reelles)

    lignes: list[LigneRapprochement] = []
    signalements: list[Signalement] = []

    for actif in sorted(set(du_moteur) | set(de_la_banque)):
        quantite_moteur = du_moteur.get(actif)
        reelle = de_la_banque.get(actif)
        quantite_banque = reelle.quantite if reelle else None

        if quantite_moteur is not None and quantite_banque is not None:
            ecart = abs(quantite_moteur - quantite_banque)
            accord = Accord.ACCORD if ecart <= TOLERANCE_QUANTITE else Accord.ECART
        elif quantite_banque is not None:
            accord = Accord.ABSENT_DU_MOTEUR
        else:
            accord = Accord.ABSENT_DE_LA_BANQUE

        lignes.append(
            LigneRapprochement(
                actif=actif,
                accord=accord,
                quantite_moteur=quantite_moteur,
                quantite_banque=quantite_banque,
                nom_actif=(reelle.nom_actif if reelle else None)
                or _nom_du_moteur(portefeuille, actif),
                prix_de_revient_moteur=_prix_de_revient_du_moteur(portefeuille, actif),
                prix_de_revient_banque=reelle.prix_de_revient_banque if reelle else None,
            )
        )

        match accord:
            case Accord.ECART:
                signalements.append(
                    Signalement(
                        categorie="écart de quantité",
                        message=(
                            "le moteur compte "
                            f"{tableur.nombre_lisible(quantite_moteur)} part(s) et la "
                            f"banque {tableur.nombre_lisible(quantite_banque)} : une "
                            "opération manque ou a été mal lue"
                        ),
                        actif=actif,
                    )
                )
            case Accord.ABSENT_DU_MOTEUR:
                signalements.append(
                    Signalement(
                        categorie="titres sans opération",
                        message=(
                            "la banque détient "
                            f"{tableur.nombre_lisible(quantite_banque)} part(s) dont "
                            "aucune opération ne parle : ces titres sont entrés sans "
                            "événement "
                            "dans l'export (limite connue de D-15). Ils ne comptent dans "
                            "aucun chiffre du moteur"
                        ),
                        actif=actif,
                    )
                )
            case Accord.ABSENT_DE_LA_BANQUE:
                signalements.append(
                    Signalement(
                        categorie="parts non confirmées",
                        message=(
                            "le moteur compte "
                            f"{tableur.nombre_lisible(quantite_moteur)} part(s) que la "
                            "banque ne montre pas : soit l'actif a été vendu sans que "
                            "l'export le "
                            "dise, soit une opération a été comptée deux fois"
                        ),
                        actif=actif,
                    )
                )
            case Accord.ACCORD:
                pass

    return Rapprochement(
        lignes=tuple(lignes),
        signalements=tuple(signalements),
        lignes_illisibles=lignes_illisibles,
    )


def _par_actif(positions_reelles: Iterable[PositionReelle]) -> dict[str, PositionReelle]:
    """Regroupe les positions de la banque par actif, **en additionnant les doublons**.

    Une banque liste normalement chaque actif une fois. Si elle le fait deux fois — deux
    lignes pour une même valeur détenue dans deux enveloppes, par exemple — écraser la
    première par la seconde ferait disparaître des parts et créerait un écart de toutes
    pièces. On additionne donc, comme le moteur le fait déjà de son côté.

    Le prix de revient, lui, est abandonné dès qu'il y a plusieurs lignes : additionner ou
    moyenner deux prix de revient n'aurait aucun sens, et ce n'est qu'une information
    (D-46).
    """
    regroupees: dict[str, PositionReelle] = {}
    for position in positions_reelles:
        deja_vue = regroupees.get(position.actif)
        if deja_vue is None:
            regroupees[position.actif] = position
            continue
        regroupees[position.actif] = PositionReelle(
            actif=position.actif,
            quantite=deja_vue.quantite + position.quantite,
            nom_actif=deja_vue.nom_actif or position.nom_actif,
            prix_de_revient_banque=None,
        )
    return regroupees


def _positions_de(portefeuille: Portefeuille, actif: str):
    return [position for position in portefeuille.positions if position.actif == actif]


def _nom_du_moteur(portefeuille: Portefeuille, actif: str) -> str | None:
    for position in _positions_de(portefeuille, actif):
        if position.nom_actif:
            return position.nom_actif
    return None


def _prix_de_revient_du_moteur(portefeuille: Portefeuille, actif: str) -> Decimal | None:
    """Le prix de revient du moteur, **seulement** si l'actif n'est détenu que dans une poche.

    Deux poches, c'est deux prix de revient différents (D-13) : en afficher un seul en face
    du chiffre de la banque serait trompeur. Le détail par poche reste dans le tableau des
    positions.
    """
    detenues = [
        position for position in _positions_de(portefeuille, actif) if position.etat.detenue
    ]
    if len(detenues) != 1:
        return None
    return detenues[0].etat.prix_de_revient
