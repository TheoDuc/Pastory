"""De quoi fabriquer des opérations pivot pour éprouver le moteur.

**Valeurs entièrement fictives** (D-03). Le moteur ne lit que le format pivot (D-26) : il se
teste donc sans le moindre fichier Trade Republic, avec des lignes écrites à la main.

Les cas repris dans `docs/verification/etape-3.md` portent ici le même numéro que dans le
cahier, pour qu'on puisse passer de l'un à l'autre.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from decimal import Decimal

from pastory.pivot.operation import (
    Operation,
    Poche,
    Provenance,
    TypeOperation,
    jour_a_paris,
)

ACTIF = "XX0000000001"
"""ISIN fictif : le préfixe XX n'est attribué à aucun pays."""

_numero = itertools.count(1)


def instant(texte: str) -> datetime:
    """Horodatage UTC, écrit comme dans l'export : « 2026-01-02 08:00 »."""
    return datetime.strptime(texte, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)


def _euros(valeur: str | Decimal | None) -> Decimal | None:
    if valeur is None:
        return None
    return Decimal(valeur) if isinstance(valeur, str) else valeur


def operation(
    type: TypeOperation,
    *,
    horodatage: str = "2026-01-02 08:00",
    actif: str = ACTIF,
    poche: Poche = Poche.CTO,
    quantite: str | None = None,
    prix_unitaire: str | None = None,
    montant_brut: str | None = None,
    frais: str = "0.00",
    taxes: str = "0.00",
    montant_regle: str | None = None,
    nom_actif: str | None = "Actif Exemple",
    prix_a_completer: bool = False,
    identifiant: str | None = None,
) -> Operation:
    """Une ligne pivot cohérente, écrite en une ligne d'appel.

    `montant_regle` se déduit du type quand on ne le donne pas : un achat paie frais et taxes
    en plus, un encaissement les voit retranchés (format-pivot §5). C'est ce qui permet aux
    opérations fabriquées ici de passer les contrôles de cohérence du pivot sans qu'on ait à
    recalculer le montant réglé à chaque fois.
    """
    moment = instant(horodatage)
    quantite_lue = _euros(quantite)
    prix_lu = _euros(prix_unitaire)
    brut = _euros(montant_brut)
    if brut is None and not prix_a_completer and quantite_lue is not None and prix_lu is not None:
        brut = quantite_lue * prix_lu

    frais_lus = Decimal(frais)
    taxes_lues = Decimal(taxes)

    if montant_regle is not None:
        regle = Decimal(montant_regle)
    elif type is TypeOperation.TITRES_RECUS:
        regle = Decimal("0.00")
    elif type is TypeOperation.ACHAT:
        regle = (brut or Decimal("0.00")) + frais_lus + taxes_lues
    else:
        regle = (brut or Decimal("0.00")) - frais_lus - taxes_lues

    provenance: dict[str, Provenance] = {
        "actif": Provenance.DONNEE,
        "poche": Provenance.DEDUCTION,
        "frais": Provenance.TEXTE,
        "taxes": Provenance.TEXTE,
        "montant_regle": Provenance.DONNEE,
    }
    if quantite_lue is not None:
        provenance["quantite"] = Provenance.TEXTE
    if prix_a_completer:
        provenance["prix_unitaire"] = Provenance.A_COMPLETER
        provenance["montant_brut"] = Provenance.A_COMPLETER
        brut = None
        prix_lu = None
    else:
        if prix_lu is not None:
            provenance["prix_unitaire"] = Provenance.TEXTE
        if brut is not None:
            provenance["montant_brut"] = Provenance.TEXTE

    return Operation(
        identifiant=identifiant or f"op-{next(_numero):04d}",
        instant_utc=moment,
        date=jour_a_paris(moment),
        type=type,
        nature_source="ordre_ponctuel",
        actif=actif,
        nom_actif=nom_actif,
        poche=poche,
        quantite=quantite_lue,
        prix_unitaire=prix_lu,
        montant_brut=brut,
        frais=frais_lus,
        taxes=taxes_lues,
        montant_regle=regle,
        reference_source=f"evenement-fictif-{actif}",
        provenance=provenance,
    )


# --- L'enchaînement du glossaire §3, celui que le cahier fait refaire à la main --------


def enchainement_du_glossaire() -> list[Operation]:
    """Les trois opérations de l'exemple du glossaire §3.

    1. achat de 10 parts pour 201 € dont 1 € de frais → capital investi 200 €, PRU 10 € ;
    2. achat de 10 parts à 30 € sans frais → capital 500 €, 20 parts, PRU 25 € ;
    3. vente de 5 parts (un quart des parts) → capital 375 €, PRU toujours 25 €.
    """
    return [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-02-05 09:00",
            quantite="10",
            prix_unitaire="30.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-03-05 09:00",
            quantite="5",
            prix_unitaire="40.00",
            frais="1.00",
        ),
    ]
