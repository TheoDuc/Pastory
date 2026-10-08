"""Un portefeuille fictif **coté**, pour éprouver les écrans sur des chiffres (D-03).

L'export est celui de la ligne de commande (`export_ligne_de_commande.py`) ; chaque actif reçoit
une cotation corrigée dans `actifs.toml` et une série de cours quotidiens dans le cache, comme si
la source les avait déjà donnés. Tout est lu **hors ligne** : aucun test ne sort de la machine.

Les cours montent régulièrement, chacun à son rythme : l'un gagne, l'autre perd, ce qui donne à
la synthèse un gain, une courbe et des cartes à trier.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from pastory.config import actifs as config_actifs
from pastory.donnees_externes.cache import Cache
from pastory.donnees_externes.cours import Cours
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs

AUJOURD_HUI = Date(2026, 9, 30)
DEBUT_DES_COURS = Date(2025, 12, 1)

COURS = {
    # actif: (ticker, cours au premier jour, variation par jour)
    fictifs.ACTIF_ETF: ("TETF.DE", "100.00", "0.05"),
    fictifs.ACTIF_ACTION: ("TACT.DE", "45.00", "-0.02"),
    fictifs.ACTIF_CRYPTO: ("BTC-EUR", "30000.00", "20.00"),
}


def coter(dossier_personnel: Path, sauf: tuple[str, ...] = ()) -> Chiffres:
    """Dépose l'export, déclare les cotations, remplit le cache ; rend les chiffres, hors ligne.

    `sauf` : les actifs laissés **sans cours**, pour l'état partiel."""
    fictifs.deposer(dossier_personnel / "exports")
    fichier = config_actifs.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        "[actifs]\n"
        + "".join(
            f'"{actif}" = {{ ticker = "{ticker}", devise = "EUR" }}\n'
            for actif, (ticker, _, _) in COURS.items()
        ),
        encoding="utf-8",
    )
    cache = Cache()
    for actif, (ticker, depart, pas) in COURS.items():
        if actif in sauf:
            continue
        jours = (AUJOURD_HUI - DEBUT_DES_COURS).days + 1
        cache.ecrire(
            actif,
            [
                Cours(
                    actif=actif,
                    date=DEBUT_DES_COURS + timedelta(days=n),
                    valeur=Decimal(depart) + Decimal(pas) * n,
                    devise="EUR",
                    place="XETRA",
                    source="Source de test",
                    recupere_le=AUJOURD_HUI,
                    ticker=ticker,
                )
                for n in range(jours)
            ],
        )
    return Chiffres(hors_ligne=True, aujourd_hui=lambda: AUJOURD_HUI)
