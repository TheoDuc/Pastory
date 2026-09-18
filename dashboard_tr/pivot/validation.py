"""Contrôles de cohérence d'une ligne pivot (docs/format-pivot.md §5).

Ils servent à attraper une lecture de texte douteuse — quantité, prix, frais et taxes ne
sont lisibles que dans des libellés en allemand ou en français (D-09) — plutôt que de
laisser un chiffre faux se propager en silence.

Rien n'est corrigé automatiquement : la ligne est conservée telle quelle et l'anomalie
part dans le rapport de lecture, que l'interface affiche.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dashboard_tr.pivot.operation import (
    DEVISE_UNIQUE,
    TYPES_AVEC_QUANTITE_OBLIGATOIRE,
    TYPES_ENCAISSEMENT,
    Operation,
    Provenance,
    TypeOperation,
    jour_a_paris,
)

TOLERANCE = Decimal("0.01")
"""Un centime : l'arrondi que la banque applique à un montant. Au-delà, l'écart n'est plus
un arrondi, c'est une anomalie."""

def arrondi_affiche(valeur: Decimal) -> Decimal:
    """De combien une valeur peut s'écarter de ce qui est écrit à l'écran (D-39).

    C'est la moitié de son dernier chiffre : un prix affiché ``0,33`` vaut en réalité entre
    0,325 et 0,335, donc un demi-centime près. Un prix affiché ``0,3300`` est cent fois plus
    précis. Le nombre de décimales n'est pas supposé : il est **lu sur la valeur elle-même**,
    qui garde l'écriture exacte du libellé dont elle vient.

    Une valeur écrite **sans décimale** est tenue pour exacte : Trade Republic écrit les
    fractions de part avec des décimales, donc « 200 » veut dire deux cents parts, pas
    « entre 199,5 et 200,5 ».
    """
    exposant = valeur.as_tuple().exponent
    if not isinstance(exposant, int) or exposant >= 0:
        return Decimal(0)
    return Decimal(1).scaleb(exposant) / 2


def tolerance_du_produit(quantite: Decimal, prix_unitaire: Decimal) -> Decimal:
    """Écart acceptable entre `montant_brut` et `quantite × prix_unitaire` (D-39).

    Trois arrondis se cumulent, et la tolérance les additionne :

    ```
    1 centime                         l'arrondi que la banque applique au montant
    + quantité × arrondi du prix      le prix affiché est lui-même arrondi
    + prix × arrondi de la quantité   la quantité affichée l'est aussi
    ```

    Les deux derniers termes sont symétriques, et il faut les deux. Avec le seul arrondi du
    prix, un achat de crypto — quantité minuscule écrite avec six décimales, prix de
    plusieurs dizaines de milliers d'euros — était signalé comme anormal à chaque fois : la
    moitié du dernier chiffre de la quantité, multipliée par un tel prix, vaut bien plus
    qu'un centime.

    Exemples :

    - 2 parts à 25,00 € → 0,01 + 2 × 0,005 + 25,00 × 0 = **0,02 €** ;
    - 200 parts à 0,33 € → 0,01 + 200 × 0,005 + 0,33 × 0 = **1,01 €** ;
    - 0,000123 part à 25 000,00 € → 0,01 + 0,000123 × 0,005 + 25 000 × 0,0000005 ≈ **0,02 €**.
    """
    return (
        TOLERANCE
        + abs(quantite) * arrondi_affiche(prix_unitaire)
        + abs(prix_unitaire) * arrondi_affiche(quantite)
    )


CHAMPS_NUMERIQUES = ("quantite", "prix_unitaire", "montant_brut", "frais", "taxes", "montant_regle")


@dataclass(frozen=True)
class Anomalie:
    """Un contrôle qui a échoué sur une opération."""

    identifiant_operation: str
    reference_source: str
    regle: str
    """Nom court du contrôle, pour regrouper les anomalies de même nature."""
    message: str
    """Phrase en français, destinée à être lue par l'utilisateur."""


def controler(operation: Operation) -> list[Anomalie]:
    """Applique tous les contrôles à une opération et renvoie les anomalies trouvées.

    Une liste vide signifie que l'opération est cohérente. Un contrôle dont un ingrédient
    est `a_completer` n'est pas exécuté : il est mis en attente (D-15).
    """
    anomalies: list[Anomalie] = []

    def signaler(regle: str, message: str) -> None:
        anomalies.append(
            Anomalie(
                identifiant_operation=operation.identifiant,
                reference_source=operation.reference_source,
                regle=regle,
                message=message,
            )
        )

    # --- Devise ---------------------------------------------------------------
    if operation.devise != DEVISE_UNIQUE:
        signaler("devise", f"devise « {operation.devise} » : seul l'euro est pris en charge")

    # --- Le jour doit correspondre à l'horodatage (D-36) ----------------------
    # C'est `date` qui sert à tout regrouper : si elle ne découle pas de l'instant réel,
    # l'opération se retrouve dans le mauvais mois sans que rien ne le signale.
    jour_attendu = jour_a_paris(operation.instant_utc)
    if operation.date != jour_attendu:
        signaler(
            "date",
            f"jour {operation.date} alors que l'horodatage correspond au {jour_attendu} "
            "en heure de Paris",
        )

    # --- Signes : tous les nombres du pivot sont positifs ----------------------
    for champ in CHAMPS_NUMERIQUES:
        valeur = getattr(operation, champ)
        if valeur is not None and valeur < 0:
            signaler(
                "signe",
                f"{champ} vaut {valeur} : le format pivot n'accepte aucun nombre négatif, "
                "le sens de l'opération est porté par son type",
            )

    # --- Provenance : toute valeur renseignée dit d'où elle vient --------------
    for champ in CHAMPS_NUMERIQUES:
        if getattr(operation, champ) is not None and champ not in operation.provenance:
            signaler("provenance", f"{champ} est renseigné mais sans provenance")
    for champ, provenance in operation.provenance.items():
        if provenance is Provenance.A_COMPLETER and getattr(operation, champ, None) is not None:
            signaler("provenance", f"{champ} est marqué « à compléter » mais porte une valeur")

    # --- Quantité -------------------------------------------------------------
    if operation.type in TYPES_AVEC_QUANTITE_OBLIGATOIRE:
        if operation.quantite is None:
            signaler(
                "quantite",
                f"une opération de type « {operation.type.value} » doit avoir une quantité",
            )
        elif operation.quantite == 0:
            signaler("quantite", "la quantité est nulle alors que des parts changent de main")

    # --- Le montant brut doit exister -----------------------------------------
    # C'est la base de toute la performance (D-21) : s'il manque sans que personne ne le
    # dise, l'opération disparaît des totaux en silence. Un montant absent n'est donc
    # accepté que s'il est explicitement marqué « à compléter » (D-15).
    if operation.montant_brut is None and not operation.est_a_completer("montant_brut"):
        signaler(
            "montant_brut",
            "montant brut absent alors qu'il est la base de tous les calculs de performance ; "
            "si le prix n'a pas pu être lu, la valeur doit être marquée « à compléter »",
        )

    # --- Montant brut = quantité × prix ---------------------------------------
    attendu_calculable = (
        operation.quantite is not None
        and operation.prix_unitaire is not None
        and operation.montant_brut is not None
        and not operation.est_a_completer("prix_unitaire")
        and not operation.est_a_completer("montant_brut")
    )
    if attendu_calculable:
        attendu = operation.quantite * operation.prix_unitaire
        tolerance = tolerance_du_produit(operation.quantite, operation.prix_unitaire)
        if abs(attendu - operation.montant_brut) > tolerance:
            signaler(
                "montant_brut",
                f"montant brut {operation.montant_brut} alors que quantité × prix donne {attendu}",
            )

    # --- Montant réglé --------------------------------------------------------
    if operation.type is TypeOperation.TITRES_RECUS:
        # Rien n'a été payé : des titres sont simplement apparus (D-15).
        for champ in ("montant_regle", "frais", "taxes"):
            valeur = getattr(operation, champ)
            if valeur != 0:
                signaler(
                    "titres_recus",
                    f"{champ} vaut {valeur} alors que des titres reçus sans achat ne coûtent rien",
                )
    elif operation.montant_brut is not None and not operation.est_a_completer("montant_brut"):
        if operation.type is TypeOperation.ACHAT:
            attendu = operation.montant_brut + operation.frais + operation.taxes
            formule = "montant brut + frais + taxes"
        elif operation.type in TYPES_ENCAISSEMENT:
            attendu = operation.montant_brut - operation.frais - operation.taxes
            formule = "montant brut − frais − taxes"
        else:  # pragma: no cover - la liste des types est fermée (D-35)
            raise ValueError(f"type d'opération non prévu par les contrôles : {operation.type}")

        if abs(attendu - operation.montant_regle) > TOLERANCE:
            signaler(
                "montant_regle",
                f"montant réglé {operation.montant_regle} alors que {formule} donne {attendu}",
            )

    return anomalies


def controler_toutes(operations: list[Operation]) -> list[Anomalie]:
    """Contrôle une liste d'opérations, dans l'ordre. Aucune n'est écartée."""
    return [anomalie for operation in operations for anomalie in controler(operation)]
