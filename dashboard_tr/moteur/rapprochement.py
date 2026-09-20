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

Une troisième, ajoutée le 2026-09-21 après essai sur de vraies données (D-47) : **la photo
ne couvre pas forcément tout le portefeuille.** `pytr portfolio` ne demande les positions que
d'un seul compte-titres ; si la banque range le PEA dans un second, aucune de ses lignes ne
remonte. Une poche dont **aucun** actif n'apparaît est donc déclarée non couverte, signalée
une fois, et ses actifs sortent en `hors périmètre` — sans quoi chaque ligne de PEA crierait
au loup à chaque lancement, et on cesserait de lire ce bloc.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from dashboard_tr import tableur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.signalement import Signalement
from dashboard_tr.pivot.operation import Poche
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

    HORS_PERIMETRE = "hors périmètre"
    """L'actif est dans une poche que la photo de la banque ne couvre pas (D-47).

    Ce n'est **pas** un désaccord : c'est une absence de comparaison. Aucune alerte n'est
    levée par actif ; la poche entière fait l'objet d'un seul signalement."""


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

    poches_non_couvertes: tuple[Poche, ...] = ()
    """Poches dont **aucun** actif n'apparaît dans la photo de la banque (D-47).

    Leurs actifs ne sont pas comparés : ils sortent en `hors périmètre`, sans alerte."""

    @property
    def desaccords(self) -> list[LigneRapprochement]:
        """Les vrais désaccords. Un actif hors périmètre n'en est pas un : il n'a pas été
        comparé du tout."""
        return [
            ligne
            for ligne in self.lignes
            if not ligne.concorde and ligne.accord is not Accord.HORS_PERIMETRE
        ]

    @property
    def tout_concorde(self) -> bool:
        """Vrai si **tout ce qui a pu être comparé** concorde.

        Distinct de `complet` : la photo peut ne couvrir qu'une partie du portefeuille, et
        cette partie tomber parfaitement juste."""
        return not self.desaccords

    @property
    def complet(self) -> bool:
        """Vrai si le rapprochement a pu tout comparer.

        Faux dès qu'une poche n'est pas couverte ou qu'une ligne du fichier est illisible :
        dans les deux cas, un « rien à signaler » serait une fausse impression de contrôle.
        """
        return not self.lignes_illisibles and not self.poches_non_couvertes


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
    de_la_banque = _par_actif(positions_reelles)
    non_couvertes = _poches_non_couvertes(portefeuille, de_la_banque)
    hors_perimetre = _actifs_hors_perimetre(portefeuille, non_couvertes)
    du_moteur = portefeuille.quantites_par_actif(
        poches=[poche for poche in Poche if poche not in non_couvertes]
    )
    # Ce que le moteur détient vraiment, poches non couvertes comprises. Sert uniquement à
    # **afficher** la quantité d'un actif hors périmètre : la laisser vide donnerait à
    # croire qu'on n'en détient plus, alors qu'on n'a simplement pas pu la confronter.
    tout_le_moteur = portefeuille.quantites_par_actif()

    lignes: list[LigneRapprochement] = []
    signalements: list[Signalement] = []

    for poche in non_couvertes:
        signalements.append(
            Signalement(
                categorie="poche non couverte",
                message=(
                    f"la photo du portefeuille ne montre aucun actif de la poche "
                    f"{poche.value} : ces positions ne sont pas comparées, ni confirmées. "
                    "Ce n'est pas un désaccord, c'est une absence de comparaison"
                ),
                poche=poche,
            )
        )

    for actif in sorted(set(du_moteur) | set(de_la_banque) | hors_perimetre):
        quantite_moteur = du_moteur.get(actif)
        reelle = de_la_banque.get(actif)
        quantite_banque = reelle.quantite if reelle else None

        if actif in hors_perimetre and quantite_moteur is None and reelle is None:
            accord = Accord.HORS_PERIMETRE
            quantite_moteur = tout_le_moteur.get(actif)
        elif quantite_moteur is not None and quantite_banque is not None:
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
            case Accord.ACCORD | Accord.HORS_PERIMETRE:
                pass

    return Rapprochement(
        lignes=tuple(lignes),
        signalements=tuple(signalements),
        lignes_illisibles=lignes_illisibles,
        poches_non_couvertes=non_couvertes,
    )


def _poches_non_couvertes(
    portefeuille: Portefeuille, de_la_banque: Mapping[str, PositionReelle]
) -> tuple[Poche, ...]:
    """Les poches dont **aucun** actif détenu n'apparaît dans la photo de la banque (D-47).

    Le cas connu : `pytr portfolio` ne demande les positions que d'un seul compte-titres.
    Si la banque range le PEA dans un second, aucune de ses lignes ne remonte, et chaque
    actif du PEA ressortirait « absent de la banque » à chaque lancement. Ce n'est pas N
    désaccords, c'est **un** fait — et un rapport qui crie au loup partout ne sert plus à
    rien (D-39).

    **Le verdict se fonde sur les actifs exclusifs à la poche.** La photo de la banque ne
    dit pas dans quelle enveloppe un titre est détenu : un ISIN présent à la fois en PEA et
    en CTO ne prouve donc la couverture ni de l'un ni de l'autre. Seuls les actifs détenus
    dans cette poche **et nulle part ailleurs** tranchent.

    **Trois garde-fous**, pour ne pas étouffer une vraie alerte :

    - il faut qu'au moins un actif soit confirmé **ailleurs**. Si la photo ne confirme
      rien du tout, elle n'est pas « partielle », elle est inutilisable : on ne déclare
      alors aucune poche non couverte et chaque actif repart en désaccord, comme avant ;
    - une poche sans aucun actif exclusif n'est **jamais** déclarée non couverte : on ne
      peut rien en dire, et se taire vaut mieux que deviner ;
    - la règle ne dit rien de la raison. Une poche qui ne contient **qu'un seul** actif,
      réellement vendu hors de l'export, entre dans ce cas de figure sans qu'on puisse
      l'en distinguer. Le rapport donne donc toujours le nombre d'actifs concernés.
    """
    par_poche = portefeuille.actifs_par_poche()
    confirmes = {
        actif for actifs in par_poche.values() for actif in actifs if actif in de_la_banque
    }
    if not confirmes:
        return ()

    non_couvertes = []
    for poche in Poche:
        exclusifs = _actifs_exclusifs(par_poche, poche)
        if exclusifs and not (exclusifs & set(de_la_banque)):
            non_couvertes.append(poche)
    return tuple(non_couvertes)


def _actifs_exclusifs(par_poche: Mapping[Poche, set[str]], poche: Poche) -> set[str]:
    """Les actifs détenus dans cette poche et dans aucune autre."""
    ailleurs = {
        actif for autre, actifs in par_poche.items() if autre is not poche for actif in actifs
    }
    return par_poche.get(poche, set()) - ailleurs


def _actifs_hors_perimetre(
    portefeuille: Portefeuille, non_couvertes: tuple[Poche, ...]
) -> set[str]:
    """Les actifs détenus **uniquement** dans des poches non couvertes.

    Un actif détenu à la fois en PEA et en CTO reste comparé : la photo en montre la part
    CTO, et c'est à elle seule que le moteur la compare (`quantites_par_actif` restreint
    aux poches couvertes). Additionner la part PEA créerait un écart de toutes pièces.
    """
    if not non_couvertes:
        return set()

    par_poche = portefeuille.actifs_par_poche()
    dans_les_non_couvertes = {
        actif for poche in non_couvertes for actif in par_poche.get(poche, set())
    }
    ailleurs = {
        actif
        for poche, actifs in par_poche.items()
        if poche not in non_couvertes
        for actif in actifs
    }
    return dans_les_non_couvertes - ailleurs


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
