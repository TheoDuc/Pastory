"""Le cache des cours : définitif, relisible, et oubliable sur demande (D-50).

Ce que ces tests protègent, dans l'ordre d'importance :

1. un cours déjà enregistré n'est **jamais** réécrit — c'est la promesse de stabilité de D-50 ;
2. un cours relu est **identique** à celui écrit, au centime comme à la sixième décimale d'une
   crypto : un cache qui arrondit en silence ruinerait toute vérification ;
3. un fichier abîmé donne un message qui dit quoi faire, pas une trace technique.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

import pytest

from dashboard_tr import tableur
from dashboard_tr.donnees_externes.cache import Cache, CacheIllisible
from tests.donnees_externes.cours_fictifs import ACTIF, CRYPTO, cours


@pytest.fixture
def cache(tmp_path):
    return Cache(dossier=tmp_path)


class TestAllerRetour:
    def test_un_cache_vide_ne_connait_rien(self, cache):
        assert cache.lire(ACTIF) == {}
        assert cache.actifs() == []

    def test_un_cours_relu_est_identique_a_celui_ecrit(self, cache):
        ecrit = cours(Date(2026, 3, 6), "128,885".replace(",", "."))

        assert cache.ecrire(ACTIF, [ecrit]) == 1
        relu = cache.lire(ACTIF)[Date(2026, 3, 6)]

        assert relu == ecrit
        assert relu.valeur == Decimal("128.885")

    def test_la_precision_d_une_crypto_survit(self, cache):
        # Un cours de crypto porte des décimales qui comptent : les perdre ferait mentir le
        # capital investi d'une position entière.
        ecrit = cours(Date(2026, 3, 6), "30012.004802", actif=CRYPTO)
        cache.ecrire(CRYPTO, [ecrit])

        assert cache.lire(CRYPTO)[Date(2026, 3, 6)].valeur == Decimal("30012.004802")

    def test_le_fichier_se_lit_dans_un_tableur_francais(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "128.885")])
        texte = cache.chemin(ACTIF).read_text(encoding=tableur.ENCODAGE)

        # Virgule décimale et point-virgule : les conventions communes à tous les CSV du
        # projet, sans lesquelles Excel lit un nombre comme du texte ou comme une date.
        assert "128,885" in texte
        assert tableur.SEPARATEUR in texte
        assert "2026-03-06" in texte

    def test_chaque_cours_garde_son_origine(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "10.00")])
        relu = cache.lire(ACTIF)[Date(2026, 3, 6)]

        assert relu.place == "XETRA"
        assert relu.source == "Source de test"
        assert relu.ticker == "AAAA.DE"
        assert relu.recupere_le == Date(2026, 9, 26)

    def test_les_actifs_en_cache_se_listent(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "10.00")])
        cache.ecrire(CRYPTO, [cours(Date(2026, 3, 6), "10.00", actif=CRYPTO)])

        assert cache.actifs() == [CRYPTO, ACTIF]


class TestDefinitif:
    def test_un_cours_deja_connu_n_est_pas_reecrit(self, cache):
        # Le cœur de D-50 : le chiffre vu hier est celui qu'on revoit aujourd'hui.
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])

        ajoutes = cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "999.99")])

        assert ajoutes == 0
        assert cache.lire(ACTIF)[Date(2026, 3, 6)].valeur == Decimal("100.00")

    def test_les_jours_nouveaux_s_ajoutent_sans_toucher_aux_autres(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])

        ajoutes = cache.ecrire(
            ACTIF,
            [cours(Date(2026, 3, 6), "999.99"), cours(Date(2026, 3, 9), "101.00")],
        )

        serie = cache.lire(ACTIF)
        assert ajoutes == 1
        assert serie[Date(2026, 3, 6)].valeur == Decimal("100.00")
        assert serie[Date(2026, 3, 9)].valeur == Decimal("101.00")

    def test_le_fichier_reste_trie_par_date(self, cache):
        cache.ecrire(
            ACTIF,
            [cours(Date(2026, 3, 9), "101.00"), cours(Date(2026, 3, 6), "100.00")],
        )
        texte = cache.chemin(ACTIF).read_text(encoding=tableur.ENCODAGE)

        assert texte.index("2026-03-06") < texte.index("2026-03-09")


class TestOubli:
    def test_oublier_un_actif_ne_touche_pas_les_autres(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        cache.ecrire(CRYPTO, [cours(Date(2026, 3, 6), "100.00", actif=CRYPTO)])

        assert cache.oublier(ACTIF) == [ACTIF]
        assert cache.lire(ACTIF) == {}
        assert cache.lire(CRYPTO) != {}

    def test_oublier_sans_precision_vide_tout(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        cache.ecrire(CRYPTO, [cours(Date(2026, 3, 6), "100.00", actif=CRYPTO)])

        assert sorted(cache.oublier()) == sorted([ACTIF, CRYPTO])
        assert cache.actifs() == []

    def test_oublier_ce_qui_n_existe_pas_ne_casse_rien(self, cache):
        assert cache.oublier(ACTIF) == []

    def test_apres_un_oubli_le_cache_se_reconstruit_a_l_identique(self, cache):
        serie = [cours(Date(2026, 3, 6), "100.00"), cours(Date(2026, 3, 9), "101.00")]
        cache.ecrire(ACTIF, serie)
        avant = cache.lire(ACTIF)

        cache.oublier(ACTIF)
        cache.ecrire(ACTIF, serie)

        assert cache.lire(ACTIF) == avant


class TestFichierAbime:
    def test_un_cours_illisible_dit_quoi_faire(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("100,00", "cent"),
            encoding=tableur.ENCODAGE,
        )

        with pytest.raises(CacheIllisible) as erreur:
            cache.lire(ACTIF)
        assert "oublier-cours" in str(erreur.value)

    def test_une_date_illisible_dit_quoi_faire(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("2026-03-06", "6 mars"),
            encoding=tableur.ENCODAGE,
        )

        with pytest.raises(CacheIllisible, match="oublier-cours"):
            cache.lire(ACTIF)

    @pytest.mark.parametrize("valeur", ["nan", "inf", "-inf"])
    def test_un_nombre_qui_n_en_est_pas_un_est_refuse(self, cache, valeur):
        # `Decimal` accepte « nan » et « inf ». Les laisser passer serait pire qu'une erreur de
        # lecture : un total deviendrait « nan » sans que rien ne le signale.
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("100,00", valeur),
            encoding=tableur.ENCODAGE,
        )

        with pytest.raises(CacheIllisible, match="oublier-cours"):
            cache.lire(ACTIF)

    def test_un_cours_negatif_est_refuse(self, cache):
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "100.00")])
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("100,00", "-100,00"),
            encoding=tableur.ENCODAGE,
        )

        with pytest.raises(CacheIllisible, match="négatif"):
            cache.lire(ACTIF)

    def test_un_nombre_reenregistre_par_un_tableur_reste_lisible(self, cache):
        # Le propriétaire est invité à ouvrir ces fichiers : s'il en enregistre un depuis un
        # tableur, un séparateur de milliers peut apparaître. Ce n'est pas une raison de tout
        # casser.
        cache.ecrire(ACTIF, [cours(Date(2026, 3, 6), "1234.56")])
        fichier = cache.chemin(ACTIF)
        fichier.write_text(
            fichier.read_text(encoding=tableur.ENCODAGE).replace("1234,56", "1 234,56"),
            encoding=tableur.ENCODAGE,
        )

        assert cache.lire(ACTIF)[Date(2026, 3, 6)].valeur == Decimal("1234.56")


class TestNomDeFichier:
    def test_un_identifiant_d_actif_ne_peut_pas_designer_un_autre_dossier(self, cache):
        # L'identifiant vient d'un fichier écrit à la main : il ne doit pas pouvoir sortir du
        # dossier de cache.
        chemin = cache.chemin("../../ailleurs")

        # Le point compte comme un caractère normal — les tickers en contiennent (« AAAA.DE »).
        # Ce qui est garanti, c'est que le fichier reste dans le dossier de cache.
        assert chemin.resolve().parent == cache.dossier.resolve()
        assert "/" not in chemin.name and "\\" not in chemin.name

    def test_un_identifiant_vide_est_refuse(self, cache):
        with pytest.raises(ValueError, match="inutilisable"):
            cache.chemin("   ")
