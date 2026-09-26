"""Le fournisseur de cours : ce qu'il rend, et surtout ce qu'il refuse de rendre.

Un cours faux ne se voit pas. C'est pourquoi presque tous ces tests portent sur les refus :
actif non déclaré, devise inattendue (D-48), cours trop vieux, réseau coupé. Dans chacun de ces
cas, la réponse doit être `None` **avec un motif lisible** — jamais une valeur par défaut, une
moyenne ou un cours périmé (D-45).
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from dashboard_tr.config.actifs import Declaration
from dashboard_tr.donnees_externes.cours import (
    DeviseInattendue,
    FournisseurDeCours,
    ReponseIncoherente,
    SourceInjoignable,
)
from tests.donnees_externes.cours_fictifs import (
    ACTIF,
    AUJOURD_HUI,
    AUTRE_ACTIF,
    CacheEnMemoire,
    SourceFictive,
    configuration,
    cours,
)

VENDREDI = Date(2026, 3, 6)
SAMEDI = Date(2026, 3, 7)
LUNDI = Date(2026, 3, 9)


def fournisseur(source=None, *, hors_ligne=False, declarations=None, cache=None):
    return FournisseurDeCours(
        configuration(declarations),
        cache or CacheEnMemoire(),
        source,
        hors_ligne=hors_ligne,
        aujourd_hui=AUJOURD_HUI,
    )


class TestCoursTrouve:
    def test_un_cours_du_jour_demande_est_rendu_tel_quel(self):
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})

        trouve = fournisseur(source).cours(ACTIF, VENDREDI)

        assert trouve.valeur == Decimal("128.885")
        assert trouve.date == VENDREDI
        assert trouve.place == "XETRA"

    def test_un_jour_non_cote_prend_le_dernier_jour_cote_et_garde_sa_date(self):
        # Un samedi n'est pas une erreur. Le cours rendu est celui du vendredi, et il **dit**
        # qu'il est du vendredi : l'écart doit rester visible pour l'appelant.
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})

        trouve = fournisseur(source).cours(ACTIF, SAMEDI)

        assert trouve.date == VENDREDI
        assert trouve.valeur == Decimal("128.885")

    def test_rien_n_est_interpole_entre_deux_jours(self):
        source = SourceFictive(
            {ACTIF: [cours(VENDREDI, "100.00"), cours(LUNDI, "110.00")]}
        )

        trouve = fournisseur(source).cours(ACTIF, Date(2026, 3, 8))

        assert trouve.valeur == Decimal("100.00")  # pas 105,00

    def test_un_cours_deja_en_cache_ne_provoque_aucun_appel(self):
        # La promesse de D-50, et ce qui protège des limitations de débit de la source.
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "128.885")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "999.99")]})

        trouve = fournisseur(source, cache=cache).cours(ACTIF, VENDREDI)

        assert trouve.valeur == Decimal("128.885")
        assert source.appels == []

    def test_un_cours_recupere_est_ecrit_dans_le_cache(self):
        cache = CacheEnMemoire()
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})

        fournisseur(source, cache=cache).cours(ACTIF, VENDREDI)

        assert cache.lire(ACTIF)[VENDREDI].valeur == Decimal("128.885")


class TestRefus:
    def test_un_actif_non_declare_est_refuse_sans_toucher_au_reseau(self):
        source = SourceFictive({AUTRE_ACTIF: [cours(VENDREDI, "100.00")]})
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(AUTRE_ACTIF, VENDREDI) is None
        assert source.appels == []

        refus = leur_fournisseur.refus
        assert [un_refus.categorie for un_refus in refus] == ["actif non déclaré"]
        assert "dashboard actifs" in refus[0].motif

    def test_un_cours_trop_vieux_est_refuse_plutot_que_reutilise(self):
        # Au-delà du recul maximal, ce n'est plus un jour férié : c'est un actif qui ne cote
        # plus, ou un mauvais ticker. Valoriser là-dessus serait un chiffre crédible et faux.
        source = SourceFictive({ACTIF: [cours(Date(2026, 1, 5), "100.00")]})
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        assert leur_fournisseur.refus[0].categorie == "cours indisponible"

    def test_une_devise_inattendue_ne_donne_aucun_cours(self):
        # Le garde-fou de D-48, au niveau de la source : rien n'est converti, rien n'est gardé.
        cache = CacheEnMemoire()
        source = SourceFictive(erreur=DeviseInattendue("la source répond en USD, pas en EUR"))
        leur_fournisseur = fournisseur(source, cache=cache)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        assert leur_fournisseur.refus[0].categorie == "devise inattendue"
        assert "USD" in leur_fournisseur.refus[0].motif
        assert cache.lire(ACTIF) == {}

    def test_une_source_injoignable_n_empeche_pas_de_continuer(self):
        # Le réseau tombe, l'antivirus bloque, le service répond n'importe quoi : le calcul
        # doit continuer sans ce cours, pas s'arrêter.
        source = SourceFictive(erreur=SourceInjoignable("service indisponible"))
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        assert leur_fournisseur.refus[0].categorie == "source injoignable"

    def test_une_reponse_incoherente_est_refusee(self):
        source = SourceFictive(erreur=ReponseIncoherente("série mensuelle au lieu de quotidienne"))
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        assert leur_fournisseur.refus[0].categorie == "réponse incohérente"

    def test_le_meme_refus_n_est_pas_repete_pour_chaque_operation(self):
        # Un actif porte souvent dix opérations. Dix fois le même message ferait perdre les
        # autres : c'est le raisonnement de D-47, appliqué ici.
        source = SourceFictive()
        leur_fournisseur = fournisseur(source, declarations={})

        for _ in range(5):
            leur_fournisseur.cours(ACTIF, VENDREDI)

        assert len(leur_fournisseur.refus) == 1

    def test_un_actif_introuvable_n_est_demande_qu_une_fois(self):
        source = SourceFictive()
        leur_fournisseur = fournisseur(source)

        leur_fournisseur.cours(ACTIF, VENDREDI)
        leur_fournisseur.cours(ACTIF, LUNDI)

        assert len(source.appels) == 1


class TestHorsLigne:
    def test_hors_ligne_le_cache_suffit(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "128.885")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})

        trouve = fournisseur(source, hors_ligne=True, cache=cache).cours(ACTIF, VENDREDI)

        assert trouve.valeur == Decimal("128.885")
        assert source.appels == []

    def test_hors_ligne_un_cours_absent_dit_quelle_commande_lancer(self):
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})
        leur_fournisseur = fournisseur(source, hors_ligne=True)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        assert source.appels == []
        assert "dashboard cours" in leur_fournisseur.refus[0].motif

    def test_sans_source_le_fournisseur_est_hors_ligne(self):
        # Le cas de l'interface qui s'ouvre : aucune source branchée, donc aucun appel
        # possible, et des refus qui l'expliquent.
        leur_fournisseur = fournisseur(None)

        assert leur_fournisseur.hors_ligne is True
        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None


class TestRemplir:
    def test_remplir_ecrit_les_cours_de_la_periode(self):
        cache = CacheEnMemoire()
        source = SourceFictive(
            {ACTIF: [cours(VENDREDI, "100.00"), cours(LUNDI, "110.00")]}
        )

        ecrits = fournisseur(source, cache=cache).remplir(ACTIF, VENDREDI, LUNDI)

        assert ecrits == 2
        assert sorted(cache.lire(ACTIF)) == [VENDREDI, LUNDI]

    def test_remplir_deux_fois_n_ecrit_rien_la_seconde(self):
        cache = CacheEnMemoire()
        source = SourceFictive({ACTIF: [cours(VENDREDI, "100.00")]})
        leur_fournisseur = fournisseur(source, cache=cache)

        assert leur_fournisseur.remplir(ACTIF, VENDREDI, LUNDI) == 1
        assert leur_fournisseur.remplir(ACTIF, VENDREDI, LUNDI) == 0

    def test_remplir_un_actif_non_declare_ne_fait_rien(self):
        source = SourceFictive({AUTRE_ACTIF: [cours(VENDREDI, "100.00")]})

        assert fournisseur(source).remplir(AUTRE_ACTIF, VENDREDI, LUNDI) == 0
        assert source.appels == []

    def test_une_periode_a_l_envers_ne_provoque_aucun_appel(self):
        source = SourceFictive()

        assert fournisseur(source).remplir(ACTIF, LUNDI, VENDREDI) == 0
        assert source.appels == []

    def test_la_periode_demandee_ne_depasse_jamais_aujourd_hui(self):
        # Demander l'avenir à une source de cours n'a pas de sens, et certaines répondent
        # alors n'importe quoi.
        source = SourceFictive({ACTIF: [cours(VENDREDI, "100.00")]})

        fournisseur(source).cours(ACTIF, AUJOURD_HUI)

        _, _, fin = source.appels[0]
        assert fin <= AUJOURD_HUI


class TestPlusieursActifs:
    def test_chaque_actif_a_sa_propre_serie(self):
        declarations = {
            ACTIF: Declaration("AAAA.DE", "EUR"),
            AUTRE_ACTIF: Declaration("BBBB.PA", "EUR"),
        }
        source = SourceFictive(
            {
                ACTIF: [cours(VENDREDI, "100.00")],
                AUTRE_ACTIF: [cours(VENDREDI, "200.00", actif=AUTRE_ACTIF)],
            }
        )
        leur_fournisseur = fournisseur(source, declarations=declarations)

        assert leur_fournisseur.cours(ACTIF, VENDREDI).valeur == Decimal("100.00")
        assert leur_fournisseur.cours(AUTRE_ACTIF, VENDREDI).valeur == Decimal("200.00")
        assert leur_fournisseur.refus == []
