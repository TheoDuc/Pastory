"""Le cache des compositions : daté, **remplaçable**, et relisible dans un tableur (D-70).

La différence avec le cache des cours est la seule chose qui compte ici : un cours écrit n'est
jamais réécrit (D-50), une composition l'est à chaque rafraîchissement.
"""

from __future__ import annotations

import csv
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory import tableur
from pastory.donnees_externes.cache import CacheIllisible
from pastory.donnees_externes.cache_compositions import (
    COLONNES,
    CacheDeCompositions,
)
from pastory.donnees_externes.composition import Composition, Part

ACTIF = "XX0000000001"


def composition(arrete_le: Date = Date(2026, 8, 31), pays: str = "US") -> Composition:
    return Composition(
        actif=ACTIF,
        pays=(Part(pays, Decimal("72.04")), Part("JP", Decimal("5.78"))),
        secteurs=(Part("technology", Decimal("30.61")),),
        classes=(Part("stock", Decimal("99.96")),),
        arrete_le=arrete_le,
        intitule_de_la_date="champ de la source",
        source="source de test",
        recupere_le=Date(2026, 9, 27),
        replication="synthétique",
        document="https://exemple.test/dic.pdf",
    )


@pytest.fixture
def cache(tmp_path):
    return CacheDeCompositions(dossier=tmp_path / "compositions")


class TestEcrireEtRelire:
    def test_ce_qui_est_ecrit_se_relit_a_l_identique(self, cache):
        cache.ecrire(composition())

        relue = cache.lire(ACTIF)

        assert relue == composition()

    def test_un_actif_absent_n_est_pas_une_erreur(self, cache):
        assert cache.lire("XX0000000999") is None

    def test_le_fichier_s_ouvre_dans_un_tableur_aux_conventions_du_projet(self, cache):
        fichier = cache.chemin(ACTIF)
        cache.ecrire(composition())

        with fichier.open(encoding=tableur.ENCODAGE, newline="") as flux:
            lignes = list(csv.DictReader(flux, delimiter=tableur.SEPARATEUR))

        assert list(lignes[0]) == list(COLONNES)
        # L'origine est répétée sur chaque ligne : un tableur n'a pas d'en-tête de document.
        assert {ligne["arrete_le"] for ligne in lignes} == {"2026-08-31"}
        assert {ligne["rubrique"] for ligne in lignes} == {"pays", "secteur", "classe"}


class TestUneCompositionEstRemplacable:
    def test_une_nouvelle_composition_remplace_l_ancienne(self, cache):
        # C'est toute la différence avec les cours : la composition d'un ETF change chaque mois.
        cache.ecrire(composition(arrete_le=Date(2026, 7, 31), pays="US"))
        cache.ecrire(composition(arrete_le=Date(2026, 8, 31), pays="CA"))

        relue = cache.lire(ACTIF)

        assert relue.arrete_le == Date(2026, 8, 31)
        assert [part.code for part in relue.pays] == ["CA", "JP"]

    def test_oublier_un_actif(self, cache):
        cache.ecrire(composition())

        assert cache.oublier(ACTIF) == [ACTIF]
        assert cache.lire(ACTIF) is None

    def test_oublier_tout(self, cache):
        cache.ecrire(composition())

        assert cache.oublier() == [ACTIF]
        assert cache.actifs() == []

    def test_oublier_ce_qui_n_existe_pas_ne_fait_rien(self, cache):
        assert cache.oublier(ACTIF) == []


class TestLeResume:
    def test_il_dit_l_essentiel_sans_reafficher_les_pourcentages(self, cache):
        cache.ecrire(composition())

        resume = cache.resume(ACTIF)

        assert resume.arrete_le == Date(2026, 8, 31)
        assert resume.nombre_de_pays == 2
        assert resume.nombre_de_secteurs == 1
        assert resume.replication == "synthétique"

    def test_un_actif_sans_composition_a_un_resume_vide(self, cache):
        resume = cache.resume(ACTIF)

        assert resume.arrete_le is None
        assert resume.nombre_de_pays == 0


class TestUnFichierAbime:
    def test_une_rubrique_inconnue_dit_quoi_faire(self, cache):
        cache.ecrire(composition())
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("pays", "planete", 1),
            encoding=tableur.ENCODAGE,
        )

        with pytest.raises(CacheIllisible, match="oublier-composition"):
            cache.lire(ACTIF)

    def test_un_fichier_reduit_a_son_entete_est_traite_comme_une_absence(self, cache):
        fichier = cache.chemin(ACTIF)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        tableur.ecrire(COLONNES, [], fichier)

        assert cache.lire(ACTIF) is None
