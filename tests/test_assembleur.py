"""L'assembleur : les cours demandés une fois par actif (D-110).

Mesuré sur la démonstration, dossier vide : demandés par petites fenêtres — une par date
d'opération —, les cours coûtaient 78 secondes d'attente et laissaient une semaine sans cours
entre deux fenêtres. Demandés d'un coup, de la première opération à hier : 2 secondes, et une
série sans trou. Ces tests tiennent les deux promesses, et celle du cache (D-50).
"""

from __future__ import annotations

from datetime import date as Date
from datetime import timedelta

from pastory import assembleur
from pastory.avancement import Etape, Point, Suivi
from pastory.config.actifs import Declaration
from pastory.donnees_externes.cours import MARGE_AVANT, FournisseurDeCours
from pastory.pivot.operation import TypeOperation
from tests.donnees_externes.cours_fictifs import (
    ACTIF,
    AUJOURD_HUI,
    AUTRE_ACTIF,
    TICKER,
    CacheEnMemoire,
    SourceFictive,
    configuration,
    cours,
)
from tests.moteur.operations_fictives import operation

HIER = AUJOURD_HUI - timedelta(days=1)
PREMIER_ACHAT = Date(2026, 3, 2)


def achat(jour: Date, actif: str = ACTIF):
    return operation(
        TypeOperation.ACHAT,
        horodatage=f"{jour.isoformat()} 09:00",
        actif=actif,
        quantite="1",
        prix_unitaire="100.00",
    )


def jours_cotes(debut: Date, fin: Date, actif: str = ACTIF):
    jour, serie = debut, []
    while jour <= fin:
        if jour.weekday() < 5:
            serie.append(cours(jour, "100.00", actif))
        jour += timedelta(days=1)
    return serie


def fournisseur(source, cache=None, declarations=None, hors_ligne=False):
    return FournisseurDeCours(
        configuration(declarations),
        cache or CacheEnMemoire(),
        source,
        hors_ligne=hors_ligne,
        aujourd_hui=AUJOURD_HUI,
    )


class TestUneDemandeParActif:
    def test_de_la_premiere_operation_a_hier_en_un_seul_appel(self):
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})
        operations = [achat(PREMIER_ACHAT), achat(Date(2026, 6, 1)), achat(Date(2026, 9, 1))]

        assembleur.remplir_les_cours(operations, fournisseur(source))

        assert source.appels == [(ACTIF, PREMIER_ACHAT - MARGE_AVANT, HIER)]

    def test_la_suite_ne_redemande_rien(self):
        """Une fois la série reçue, valoriser à chaque date d'opération ne coûte plus un
        appel : c'était une fenêtre par date, et c'est ce qui faisait attendre."""
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})
        operations = [achat(PREMIER_ACHAT), achat(Date(2026, 6, 1)), achat(Date(2026, 9, 1))]
        le_fournisseur = fournisseur(source)
        assembleur.remplir_les_cours(operations, le_fournisseur)

        for une in operations:
            assert le_fournisseur.cours(ACTIF, une.date) is not None
        assert le_fournisseur.cours(ACTIF, AUJOURD_HUI) is not None

        assert len(source.appels) == 1

    def test_aucune_semaine_ne_reste_sans_cours(self):
        """Le trou que laissaient deux fenêtres voisines : sept jours entre la fin de l'une et
        le début de l'autre, trop court pour être vu comme un trou, assez long pour que la
        courbe s'y fige sur un cours périmé."""
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})
        cache = CacheEnMemoire()

        assembleur.remplir_les_cours(
            [achat(PREMIER_ACHAT), achat(Date(2026, 9, 1))], fournisseur(source, cache)
        )

        connus = sorted(cache.lire(ACTIF))
        assert max(b - a for a, b in zip(connus, connus[1:], strict=False)).days <= 3

    def test_un_cache_deja_rempli_ne_redemande_que_la_suite(self):
        """D-50 : un cours gardé n'est ni redemandé ni réécrit."""
        dernier_connu = Date(2026, 9, 18)
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, jours_cotes(Date(2026, 1, 1), dernier_connu))
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == [(ACTIF, dernier_connu + timedelta(days=1), HIER)]

    def test_chaque_actif_a_sa_demande_depuis_sa_propre_premiere_operation(self):
        declarations = {
            ACTIF: Declaration(TICKER, "EUR"),
            AUTRE_ACTIF: Declaration("BBBB.DE", "EUR"),
        }
        source = SourceFictive({})
        plus_tard = Date(2026, 7, 1)

        assembleur.remplir_les_cours(
            [achat(plus_tard, AUTRE_ACTIF), achat(PREMIER_ACHAT), achat(Date(2026, 8, 3))],
            fournisseur(source, declarations=declarations),
        )

        assert sorted(source.appels) == [
            (ACTIF, PREMIER_ACHAT - MARGE_AVANT, HIER),
            (AUTRE_ACTIF, plus_tard - MARGE_AVANT, HIER),
        ]

    def test_un_actif_sans_cotation_n_est_pas_demande(self):
        source = SourceFictive({})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT, AUTRE_ACTIF)], fournisseur(source))

        assert source.appels == []

    def test_hors_ligne_rien_n_est_demande(self):
        """Ni pour l'export d'un tiers (règle 2 de CLAUDE.md), ni avec `--hors-ligne`."""
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours(
            [achat(PREMIER_ACHAT)], fournisseur(source, hors_ligne=True)
        )
        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(None))

        assert source.appels == []


class TestLeSuiviDesCours:
    def test_il_avance_d_un_actif_a_chaque_demande(self):
        declarations = {
            ACTIF: Declaration(TICKER, "EUR"),
            AUTRE_ACTIF: Declaration("BBBB.DE", "EUR"),
        }
        suivi = Suivi()
        suivi.commencer()

        assembleur.remplir_les_cours(
            [achat(PREMIER_ACHAT), achat(PREMIER_ACHAT, AUTRE_ACTIF)],
            fournisseur(SourceFictive({}), declarations=declarations),
            suivi,
        )

        assert suivi.lire() == (True, Point(Etape.COURS, 2, 2))

    def test_sans_suivi_rien_ne_change(self):
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source))

        assert len(source.appels) == 1
