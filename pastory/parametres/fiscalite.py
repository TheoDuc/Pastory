"""Les règles fiscales, telles que le moteur les attend (D-58, D-59, D-60).

Les taux viennent de `fiscalite.toml`, livré avec l'application ; la date du premier versement
du PEA vient des réglages (`pastory/reglages` : trouvée dans l'export, ou corrigée). Les deux
sont réunis ici, en un objet qui a exactement la forme que `moteur/fiscalite.py` déclare
attendre — sans que le moteur importe ce paquet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path

from pastory.parametres import DOSSIER, ParametresInvalides
from pastory.parametres.lecture import Parametre
from pastory.parametres.lecture import charger as charger_parametres

FICHIER = DOSSIER / "fiscalite.toml"

NOMS_ATTENDUS = {
    "impot_sur_le_revenu": "impot_sur_le_revenu.taux_forfaitaire",
    "prelevements_sociaux": "prelevements_sociaux.taux",
    "pea_duree_exoneration_ir": "pea.duree_exoneration_ir",
    "crypto_seuil_exoneration": "crypto.seuil_exoneration",
}


@dataclass(frozen=True)
class ReglesFiscales:
    """Ce dont l'impôt estimé a besoin, et rien d'autre."""

    impot_sur_le_revenu: Parametre
    """Taux forfaitaire, en pour cent (CTO, PEA de moins de cinq ans, crypto)."""

    prelevements_sociaux: Parametre
    """En pour cent, sur les trois poches."""

    pea_duree_exoneration_ir: Parametre
    """En années depuis le premier versement."""

    crypto_seuil_exoneration: Parametre
    """En euros de cessions par an."""

    pea_premier_versement: Date | None = None
    """Trouvée dans l'export ou corrigée par l'utilisateur (D-59, D-80) ; `None` si inconnue."""

    pea_origine_de_la_date: str | None = None
    """D'où vient la date, en clair, pour qu'elle se voie là où elle sert."""

    pea_reserve: str | None = None
    """Ce qu'il faut savoir pour se fier à la date, quand elle a été trouvée et non corrigée."""

    pea_alerte: str | None = None
    """Une hypothèse du calcul que les exports contredisent : un retrait passé (D-87)."""


def charger(
    fichier: Path | None = None,
    premier_versement_pea: Date | None = None,
    origine_de_la_date: str | None = None,
    reserve: str | None = None,
    alerte: str | None = None,
) -> ReglesFiscales:
    parametres = charger_parametres(FICHIER if fichier is None else fichier)
    manquants = [nom for nom in NOMS_ATTENDUS.values() if nom not in parametres]
    if manquants:
        raise ParametresInvalides(
            f"{fichier or FICHIER} : paramètre(s) manquant(s) : {', '.join(manquants)}"
        )
    for attribut, nom in NOMS_ATTENDUS.items():
        attendue = "ans" if "duree" in attribut else "euros" if "seuil" in attribut else "pour cent"
        if parametres[nom].unite != attendue:
            raise ParametresInvalides(
                f"{fichier or FICHIER} : [{nom}] doit être en « {attendue} », pas en "
                f"« {parametres[nom].unite} »"
            )
    return ReglesFiscales(
        impot_sur_le_revenu=parametres[NOMS_ATTENDUS["impot_sur_le_revenu"]],
        prelevements_sociaux=parametres[NOMS_ATTENDUS["prelevements_sociaux"]],
        pea_duree_exoneration_ir=parametres[NOMS_ATTENDUS["pea_duree_exoneration_ir"]],
        crypto_seuil_exoneration=parametres[NOMS_ATTENDUS["crypto_seuil_exoneration"]],
        pea_premier_versement=premier_versement_pea,
        pea_origine_de_la_date=origine_de_la_date,
        pea_reserve=reserve,
        pea_alerte=alerte,
    )
