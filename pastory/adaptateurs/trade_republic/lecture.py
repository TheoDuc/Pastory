"""Lecture de l'export officiel au format pivot (D-79).

Presque tout est une **colonne** : la poche (`account_type`), la quantité, le prix, le montant
brut, les frais, les taxes. Rien n'est lu dans un texte, sauf la nature de l'opération (plan
d'épargne, ordre ponctuel), qui est informative et marquée `texte`.

**Une forme jamais vue n'est pas traitée**, même pour un type connu. Chaque type traité a
été vu sur de vrais fichiers avec une forme précise (docs/export-officiel.md §5) : un achat a
une quantité positive et un montant négatif, un dividende un montant positif et pas de prix.
Une ligne qui s'en écarte — un dividende négatif, qui est une extourne chez d'autres
utilisateurs ; une obligation, dont le montant inclut les intérêts courus — n'est pas
« corrigée » : elle n'est pas produite, et le rapport dit pourquoi. C'est un trou affiché
plutôt qu'un chiffre faux.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from pastory.adaptateurs.trade_republic.classement import Categorie, classer
from pastory.adaptateurs.trade_republic.depot import Depot
from pastory.adaptateurs.trade_republic.fichier import Ligne
from pastory.adaptateurs.trade_republic.rapport import Rapport
from pastory.pivot.operation import DEVISE_UNIQUE, Operation, Poche, Provenance, TypeOperation
from pastory.pivot.validation import Anomalie, controler

ZERO = Decimal("0")

CLASSES_ACCEPTEES = frozenset({"FUND", "STOCK", "CRYPTO"})
"""Les valeurs d'`asset_class` vues sur nos fichiers. `BOND` existe chez d'autres
utilisateurs, mais son montant inclut les intérêts courus : `amount ≠ shares × price`."""

CLASSE_CRYPTO = "CRYPTO"

POCHE_PAR_COMPTE: dict[str, Poche] = {"DEFAULT": Poche.CTO, "PEA": Poche.PEA}
"""`account_type` → poche. `JUNIOR` (compte enfant) existe chez d'autres : il n'est pas
traité, faute de savoir à quelle enveloppe fiscale il correspond."""

TOLERANCE_DU_CHANGE = Decimal("0.01")
"""Écart admis entre `original_amount × fx_rate` et `amount` : l'arrondi au centime."""


class NatureSource(StrEnum):
    """Nature d'origine d'une opération (`nature_source` du pivot). Informative."""

    PLAN_EPARGNE = "plan_epargne"
    ORDRE_PONCTUEL = "ordre_ponctuel"
    DIVIDENDE_ESPECES = "dividende_especes"
    DISTRIBUTION_CAPITAL = "distribution_capital"
    NON_RECONNUE = "non_reconnue"


NATURES_EN_DESCRIPTION: tuple[tuple[str, NatureSource], ...] = (
    ("Savings plan", NatureSource.PLAN_EPARGNE),
    ("Buy trade", NatureSource.ORDRE_PONCTUEL),
    ("Sell trade", NatureSource.ORDRE_PONCTUEL),
    ("Cash Dividend", NatureSource.DIVIDENDE_ESPECES),
    ("Capital Distribution", NatureSource.DISTRIBUTION_CAPITAL),
)
"""**Fragilité assumée** (règle 4 de CLAUDE.md), sans conséquence sur les chiffres : le début
de la `description`, toujours en anglais. La nature n'est qu'affichée ; le moteur ne calcule
jamais dessus (format-pivot §2)."""


class OperationNonProduite(Exception):
    """La ligne ne peut pas devenir une opération sans inventer quelque chose.

    Le message explique quoi, en français : il part tel quel au rapport de lecture. Il ne
    cite que des noms de colonnes et des codes, jamais une valeur.
    """

    def __init__(self, categorie: str, message: str) -> None:
        self.categorie = categorie
        super().__init__(message)


def _ou(ligne: Ligne) -> str:
    return f"{ligne.fichier}, ligne {ligne.numero}"


def _nombre(ligne: Ligne, colonne: str) -> Decimal | None:
    """La valeur d'une colonne numérique : `None` si elle est vide, refus si illisible."""
    texte = getattr(ligne, colonne)
    if not texte:
        return None
    try:
        valeur = Decimal(texte)
    except InvalidOperation as erreur:
        raise OperationNonProduite(
            "valeur illisible", f"la colonne « {colonne} » ne contient pas un nombre"
        ) from erreur
    if not valeur.is_finite():
        raise OperationNonProduite(
            "valeur illisible", f"la colonne « {colonne} » ne contient pas un nombre"
        )
    return valeur


def _instant(ligne: Ligne) -> datetime:
    try:
        instant = datetime.fromisoformat(ligne.datetime)
    except ValueError as erreur:
        raise OperationNonProduite(
            "horodatage illisible", "la colonne « datetime » n'est pas une date et une heure"
        ) from erreur
    if instant.tzinfo is None:
        # Sans fuseau, le jour de l'opération dépendrait de l'ordinateur (D-36).
        raise OperationNonProduite(
            "horodatage illisible", "la colonne « datetime » n'indique pas le fuseau horaire"
        )
    return instant


_APRES_TOUT = datetime.max.replace(tzinfo=UTC)


def _ordre(ligne: Ligne) -> tuple[datetime, str, int]:
    try:
        instant = _instant(ligne)
    except OperationNonProduite:
        instant = _APRES_TOUT
    return instant, ligne.fichier, ligne.numero


def _jour(ligne: Ligne) -> date:
    try:
        return date.fromisoformat(ligne.date)
    except ValueError as erreur:
        raise OperationNonProduite(
            "date illisible", "la colonne « date » n'est pas une date"
        ) from erreur


def _forme(condition: bool, nom_du_type: str, attendu: str) -> None:
    if not condition:
        raise OperationNonProduite(
            "forme jamais vue",
            f"{nom_du_type} : {attendu}. Cette forme n'a jamais été vue sur un vrai fichier, "
            "elle n'est pas interprétée",
        )


def _negatif_ou_vide(valeur: Decimal | None) -> bool:
    return valeur is None or valeur <= 0


def _positif(valeur: Decimal | None) -> bool:
    return valeur is not None and valeur > 0


def _nature(ligne: Ligne) -> NatureSource:
    for debut, nature in NATURES_EN_DESCRIPTION:
        if ligne.description.startswith(debut):
            return nature
    return NatureSource.NON_RECONNUE


class Lecteur:
    """Lit le contenu d'un dossier de dépôt et produit le rapport de lecture."""

    def lire(self, depot: Depot) -> Rapport:
        rapport = Rapport(depot=depot)
        self._signaler_le_depot(depot, rapport)

        # Le fichier n'est pas trié (export-officiel.md §2) : l'ordre des opérations est
        # rétabli ici, sur l'instant lu et non sur le texte (le nombre de décimales de
        # seconde varie d'une ligne à l'autre). Une ligne sans horodatage lisible va à la
        # fin, où elle sera refusée.
        for ligne in sorted(depot.lignes, key=_ordre):
            classement = classer(ligne)
            rapport.compter(classement)

            if classement.categorie is Categorie.INCONNU:
                rapport.signaler(
                    "non traité",
                    f"{classement.type_affiche} (voir « types non traités » plus haut)",
                    _ou(ligne),
                )
                continue
            if classement.categorie is Categorie.HORS_PERIMETRE:
                continue

            assert classement.type_operation is not None
            try:
                operation = self._construire(ligne, classement.type_operation, rapport)
            except OperationNonProduite as refus:
                rapport.operations_non_produites += 1
                rapport.signaler(
                    refus.categorie, f"{classement.type_affiche} : {refus}", _ou(ligne)
                )
                continue

            rapport.operations.append(operation)
            rapport.anomalies.extend(controler(operation))
            rapport.anomalies.extend(self._controler_le_change(ligne, operation))
            rapport.classes_par_actif.setdefault(operation.actif, set()).add(ligne.asset_class)

        return rapport

    # --- Le dossier ------------------------------------------------------------

    @staticmethod
    def _signaler_le_depot(depot: Depot, rapport: Rapport) -> None:
        for gardee, ecartee in depot.conflits:
            rapport.signaler(
                "deux versions d'une opération",
                "la même opération figure dans deux fichiers avec un contenu différent : la "
                f"première lue est gardée ({_ou(gardee)}), l'autre est écartée. Vérifiez "
                "laquelle correspond à l'application",
                _ou(ecartee),
            )
        for ligne in depot.sans_identifiant:
            rapport.signaler(
                "ligne sans identifiant",
                "ligne sans « transaction_id » : impossible de savoir si un autre fichier la "
                "contient déjà, elle n'est pas lue",
                _ou(ligne),
            )

    # --- Une ligne -------------------------------------------------------------

    def _construire(
        self, ligne: Ligne, type_operation: TypeOperation, rapport: Rapport
    ) -> Operation:
        instant = _instant(ligne)
        jour = _jour(ligne)

        if not ligne.symbol:
            raise OperationNonProduite("actif absent", "la colonne « symbol » est vide")

        classe = ligne.asset_class
        if classe not in CLASSES_ACCEPTEES:
            raise OperationNonProduite(
                "classe d'actif non prise en charge",
                f"classe d'actif « {classe or 'vide'} » : seules FUND, STOCK et CRYPTO ont "
                "été vues et vérifiées",
            )
        poche = self._poche(ligne)

        if ligne.currency != DEVISE_UNIQUE:
            raise OperationNonProduite(
                "devise étrangère",
                f"montant en « {ligne.currency or 'vide'} » ; seul l'euro est pris en charge",
            )

        actions = _nombre(ligne, "shares")
        prix = _nombre(ligne, "price")
        montant = _nombre(ligne, "amount")
        frais = _nombre(ligne, "fee")
        taxes = _nombre(ligne, "tax")
        montant_en_devise = _nombre(ligne, "original_amount")
        taux = _nombre(ligne, "fx_rate")

        nom = type_operation.value
        _forme(_negatif_ou_vide(frais), nom, "des frais positifs, alors qu'ils sont négatifs")
        _forme(_negatif_ou_vide(taxes), nom, "des taxes positives, alors qu'elles sont négatives")

        if type_operation in (TypeOperation.ACHAT, TypeOperation.VENTE):
            sens = 1 if type_operation is TypeOperation.ACHAT else -1
            _forme(
                actions is not None and actions * sens > 0,
                nom,
                "une quantité de signe inattendu",
            )
            _forme(_positif(prix), nom, "un prix absent ou négatif")
            _forme(
                montant is not None and montant * sens < 0,
                nom,
                "un montant absent ou de signe inattendu",
            )
            _forme(
                montant_en_devise is None and taux is None,
                nom,
                "un montant en devise étrangère sur un ordre",
            )
        else:
            # Dividende ou distribution de capital : des parts détenues, un montant reçu.
            _forme(_positif(montant), nom, "un montant absent ou négatif (une extourne ?)")
            _forme(_positif(actions), nom, "un nombre de parts absent ou négatif")
            _forme(prix is None, nom, "un prix, qui n'a jamais été vu sur un versement")
            if montant_en_devise is not None or taux is not None:
                _forme(
                    _positif(montant_en_devise)
                    and _positif(taux)
                    and bool(ligne.original_currency),
                    nom,
                    "des colonnes de change incomplètes",
                )

        assert actions is not None and montant is not None
        nature = _nature(ligne)
        if nature is NatureSource.NON_RECONNUE:
            rapport.signaler(
                "nature non reconnue",
                "la description ne commence par aucune nature connue (plan d'épargne, ordre "
                "ponctuel, dividende) : sans effet sur les chiffres, la nature est seulement "
                "affichée « non_reconnue »",
                _ou(ligne),
            )

        provenance: dict[str, Provenance] = {
            "actif": Provenance.DONNEE,
            "poche": Provenance.DONNEE,
            "quantite": Provenance.DONNEE,
            "montant_brut": Provenance.DONNEE,
            "frais": Provenance.DONNEE,
            "taxes": Provenance.DONNEE,
            "nature_source": Provenance.TEXTE,
        }
        if prix is not None:
            provenance["prix_unitaire"] = Provenance.DONNEE
        if ligne.name:
            provenance["nom_actif"] = Provenance.DONNEE

        return Operation(
            identifiant=f"tr-{ligne.transaction_id}",
            instant_utc=instant,
            date=jour,
            type=type_operation,
            nature_source=nature.value,
            actif=ligne.symbol,
            nom_actif=ligne.name or None,
            poche=poche,
            quantite=abs(actions),
            prix_unitaire=prix,
            montant_brut=abs(montant),
            frais=abs(frais) if frais is not None else ZERO,
            taxes=abs(taxes) if taxes is not None else ZERO,
            # La banque ne donne pas ce qui a été réellement réglé (D-83).
            montant_regle=None,
            reference_source=ligne.transaction_id,
            provenance=provenance,
        )

    @staticmethod
    def _poche(ligne: Ligne) -> Poche:
        if ligne.asset_class == CLASSE_CRYPTO:
            if ligne.account_type != "DEFAULT":
                raise OperationNonProduite(
                    "poche indéterminable",
                    f"une crypto sur un compte « {ligne.account_type or 'vide'} », qui n'a "
                    "jamais été vu",
                )
            return Poche.CRYPTO
        poche = POCHE_PAR_COMPTE.get(ligne.account_type)
        if poche is None:
            raise OperationNonProduite(
                "poche indéterminable",
                f"compte « {ligne.account_type or 'vide'} » : seuls DEFAULT (compte-titres) et "
                "PEA ont été vus",
            )
        return poche

    @staticmethod
    def _controler_le_change(ligne: Ligne, operation: Operation) -> list[Anomalie]:
        """Sur un versement en devise étrangère, `original_amount × fx_rate = amount`.

        Vérifié sur de vrais fichiers (export-officiel.md §5.3) : `fx_rate` est le nombre
        d'euros pour une unité de devise. Un écart veut dire que le montant en euros ne
        découle pas du montant versé, et il est montré, jamais corrigé.
        """
        if not ligne.original_amount or operation.montant_brut is None:
            return []
        attendu = Decimal(ligne.original_amount) * Decimal(ligne.fx_rate)
        if abs(attendu - operation.montant_brut) <= TOLERANCE_DU_CHANGE:
            return []
        return [
            Anomalie(
                identifiant_operation=operation.identifiant,
                reference_source=operation.reference_source,
                regle="change",
                message=(
                    f"montant brut {operation.montant_brut} alors que le montant en "
                    f"{ligne.original_currency} multiplié par le taux de change donne "
                    f"{attendu.quantize(Decimal('0.01'))}"
                ),
            )
        ]
