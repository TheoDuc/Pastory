"""Le fournisseur de cours : ce qu'il rend, et surtout ce qu'il refuse de rendre.

Un cours faux ne se voit pas. C'est pourquoi presque tous ces tests portent sur les refus :
actif non déclaré, devise inattendue (D-48), cours trop vieux, réseau coupé. Dans chacun de ces
cas, la réponse doit être `None` **avec un motif lisible** — jamais une valeur par défaut, une
moyenne ou un cours périmé (D-45).
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import Configuration, Declaration
from pastory.donnees_externes.cours import (
    DeviseInattendue,
    FournisseurDeCours,
    ReponseIncoherente,
    SourceInjoignable,
)
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

    def test_au_dela_du_cache_le_cours_plus_recent_est_demande(self):
        # Le défaut vu à l'étape 9 : un cache arrêté au vendredi servait encore le lundi, le
        # mardi… sans jamais redemander, tant que le vendredi restait dans le recul maximal. Les
        # cours s'arrêtaient au dernier passage de `pastory cours`.
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "100.00"), cours(LUNDI, "110.00")]})

        trouve = fournisseur(source, cache=cache).cours(ACTIF, LUNDI)

        assert trouve.date == LUNDI
        assert cache.lire(ACTIF)[LUNDI].valeur == Decimal("110.00")

    def test_la_fin_du_cache_n_est_redemandee_qu_une_fois(self):
        # La valorisation jour par jour demande chaque jour après la fin du cache : un seul
        # appel doit suffire, même si la source n'a rien de plus récent (clôture pas encore
        # publiée) — et ce n'est pas un refus, le dernier jour connu reste valable.
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "100.00")]})
        mardi = Date(2026, 3, 10)
        leur_fournisseur = FournisseurDeCours(configuration(), cache, source, aujourd_hui=mardi)

        for jour in (SAMEDI, Date(2026, 3, 8), LUNDI, mardi):
            assert leur_fournisseur.cours(ACTIF, jour).date == VENDREDI

        assert len(source.appels) == 1
        assert leur_fournisseur.refus == []

    def test_un_week_end_au_milieu_du_cache_ne_provoque_aucun_appel(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00"), cours(LUNDI, "110.00")])
        source = SourceFictive({ACTIF: []})

        assert fournisseur(source, cache=cache).cours(ACTIF, SAMEDI).date == VENDREDI
        assert source.appels == []

    def test_hors_ligne_la_fin_du_cache_sert_sans_appel(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00")])

        trouve = fournisseur(None, hors_ligne=True, cache=cache).cours(ACTIF, LUNDI)

        assert trouve.date == VENDREDI

    def test_un_cours_recupere_est_ecrit_dans_le_cache(self):
        cache = CacheEnMemoire()
        source = SourceFictive({ACTIF: [cours(VENDREDI, "128.885")]})

        fournisseur(source, cache=cache).cours(ACTIF, VENDREDI)

        assert cache.lire(ACTIF)[VENDREDI].valeur == Decimal("128.885")


class TestRefus:
    def test_un_actif_sans_cotation_est_refuse_sans_toucher_au_reseau(self):
        source = SourceFictive({AUTRE_ACTIF: [cours(VENDREDI, "100.00")]})
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(AUTRE_ACTIF, VENDREDI) is None
        assert source.appels == []

        refus = leur_fournisseur.refus
        assert [un_refus.categorie for un_refus in refus] == ["aucune cotation trouvée"]
        assert "signalé plutôt qu'estimé" in refus[0].motif

    def test_le_motif_d_une_cotation_introuvable_suit_jusqu_au_refus(self):
        # Le trou dit pourquoi aucune cotation n'a été retenue (D-80, règle 3) : c'est ce motif,
        # et non un message générique, qui doit arriver à l'utilisateur.
        configuration = Configuration(
            {AUTRE_ACTIF: Declaration()}, sans_cotation={AUTRE_ACTIF: "motif de test"}
        )
        leur_fournisseur = FournisseurDeCours(
            configuration, CacheEnMemoire(), SourceFictive({}), aujourd_hui=AUJOURD_HUI
        )

        assert leur_fournisseur.cours(AUTRE_ACTIF, VENDREDI) is None
        assert leur_fournisseur.refus[0].motif == "motif de test"

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

    def test_deux_dates_voisines_ne_font_qu_une_demande(self):
        # La fenêtre demandée entoure largement la date : une seconde opération quelques jours
        # plus tard est déjà couverte, et redemander ne donnerait pas autre chose.
        source = SourceFictive()
        leur_fournisseur = fournisseur(source)

        leur_fournisseur.cours(ACTIF, VENDREDI)
        leur_fournisseur.cours(ACTIF, LUNDI)

        assert len(source.appels) == 1

    def test_deux_dates_eloignees_donnent_bien_deux_demandes(self):
        # Le piège inverse : deux titres reçus à deux ans d'écart. Ignorer la seconde date
        # produirait un refus affirmant que la source ne sait rien, alors qu'elle n'a jamais
        # été interrogée pour cette période.
        source = SourceFictive({ACTIF: [cours(Date(2024, 3, 6), "50.00")]})
        leur_fournisseur = fournisseur(source)

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None
        trouve = leur_fournisseur.cours(ACTIF, Date(2024, 3, 6))

        assert len(source.appels) == 2
        assert trouve is not None
        assert trouve.valeur == Decimal("50.00")

    def test_une_source_en_panne_n_est_pas_harcelee(self):
        # Ticker faux ou réseau coupé : dix opérations ne doivent pas donner dix appels.
        source = SourceFictive(erreur=SourceInjoignable("service indisponible"))
        leur_fournisseur = fournisseur(source)

        leur_fournisseur.cours(ACTIF, VENDREDI)
        leur_fournisseur.cours(ACTIF, Date(2024, 3, 6))

        assert len(source.appels) == 1
        assert len(leur_fournisseur.refus) == 1


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
        assert "pastory cours" in leur_fournisseur.refus[0].motif

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

    def test_ce_que_le_cache_couvre_deja_n_est_pas_redemande(self):
        # Le cache empêche de **réécrire** un cours ; ce test porte sur l'autre moitié de la
        # promesse de D-50 : ne pas le **redemander**. Sans quoi tout l'historique repartirait
        # à chaque lancement, et la source limite son débit sans prévenir.
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00"), cours(LUNDI, "101.00")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "100.00")]})

        assert fournisseur(source, cache=cache).remplir(ACTIF, VENDREDI, LUNDI) == 0
        assert source.appels == []

    def test_un_cache_a_jour_jusqu_a_hier_ne_coute_aucun_appel_pour_aujourd_hui(self):
        """Trouvé en mesurant l'attente (D-110) : la séance du jour n'étant pas close, la
        période « de demain du dernier cours à aujourd'hui » est vide. Elle ressortait pourtant
        à l'envers de la réduction au cache, donc valide, et chaque ouverture coûtait un appel
        par actif pour un cours déjà connu."""
        hier = Date(2026, 9, 25)
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(Date(2026, 9, 24), "100.00"), cours(hier, "101.00")])
        source = SourceFictive({ACTIF: [cours(hier, "101.00")]})

        trouve = fournisseur(source, cache=cache).cours(ACTIF, AUJOURD_HUI)

        assert trouve.date == hier
        assert source.appels == []

    def test_seule_la_suite_manquante_est_demandee(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00")])
        source = SourceFictive({ACTIF: [cours(LUNDI, "101.00")]})
        leur_fournisseur = fournisseur(source, cache=cache)

        # La période demandée commence quelques jours avant le premier jour coté connu : c'est
        # le cas normal d'un relancement, le cache commençant au premier jour **coté**.
        assert leur_fournisseur.remplir(ACTIF, Date(2026, 3, 1), LUNDI) == 1

        # La demande part du lendemain du dernier jour connu, pas du 1er mars.
        _, debut, fin = source.appels[0]
        assert debut == Date(2026, 3, 7)
        assert fin == LUNDI

    def test_un_jour_plus_ancien_que_le_cache_est_bien_demande(self):
        # Le cas inverse : un titre reçu avant tout ce qu'on connaît. Réduire la période
        # priverait cet actif de son cours pour toujours.
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(LUNDI, "101.00")])
        source = SourceFictive({ACTIF: [cours(Date(2026, 1, 5), "90.00")]})
        leur_fournisseur = fournisseur(source, cache=cache)

        # Deux mois avant le premier jour connu : la réduction ne s'applique pas.
        assert leur_fournisseur.remplir(ACTIF, Date(2026, 1, 1), LUNDI) == 1
        assert cache.lire(ACTIF)[Date(2026, 1, 5)].valeur == Decimal("90.00")

    def test_remplir_un_actif_non_declare_ne_fait_rien(self):
        source = SourceFictive({AUTRE_ACTIF: [cours(VENDREDI, "100.00")]})

        assert fournisseur(source).remplir(AUTRE_ACTIF, VENDREDI, LUNDI) == 0
        assert source.appels == []

    def test_une_periode_a_l_envers_ne_provoque_aucun_appel(self):
        source = SourceFictive()

        assert fournisseur(source).remplir(ACTIF, LUNDI, VENDREDI) == 0
        assert source.appels == []

    def test_une_date_lointaine_ne_cree_pas_de_trou(self):
        """Défaut trouvé à l'étape 9, sur les données du propriétaire. Le cache s'arrêtait au
        23 janvier ; un cours demandé au 6 mars faisait télécharger du 4 février (30 jours avant)
        au 9 mars seulement. Restait un trou du 24 janvier au 3 février, que rien ne comblait."""
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, jours_ouvres(Date(2026, 1, 5), Date(2026, 1, 23)))
        source = SourceFictive({ACTIF: jours_ouvres(Date(2026, 1, 1), Date(2026, 3, 31))})

        assert fournisseur(source, cache=cache).cours(ACTIF, VENDREDI) is not None

        _, debut, _ = source.appels[0]
        assert debut == Date(2026, 1, 24)

    def test_un_trou_deja_dans_le_cache_est_comble(self):
        """L'autre moitié du même défaut : un cache troué jugeait toute date du trou « déjà
        couverte », puisqu'il connaissait des cours avant et après. Rien n'était redemandé, et
        le cours d'un jour d'achat manquait — le TWRR sur un mois devenait non calculable."""
        cache = CacheEnMemoire()
        cache.ecrire(
            ACTIF,
            jours_ouvres(Date(2026, 1, 5), Date(2026, 1, 23))
            + jours_ouvres(Date(2026, 2, 16), Date(2026, 3, 6)),
        )
        source = SourceFictive({ACTIF: jours_ouvres(Date(2026, 1, 1), Date(2026, 3, 31))})
        leur_fournisseur = fournisseur(source, cache=cache)

        trouve = leur_fournisseur.cours(ACTIF, Date(2026, 2, 4))

        assert trouve is not None and trouve.date == Date(2026, 2, 4)
        assert leur_fournisseur.refus == []
        _, debut, _ = source.appels[0]
        assert debut == Date(2026, 1, 24)

    def test_un_week_end_n_est_pas_un_trou(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, jours_ouvres(Date(2026, 1, 5), Date(2026, 3, 6)))
        source = SourceFictive()

        assert fournisseur(source, cache=cache).remplir(ACTIF, Date(2026, 1, 5), VENDREDI) == 0
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
                AUTRE_ACTIF: [cours(VENDREDI, "200.00", actif=AUTRE_ACTIF, ticker="BBBB.PA")],
            }
        )
        leur_fournisseur = fournisseur(source, declarations=declarations)

        assert leur_fournisseur.cours(ACTIF, VENDREDI).valeur == Decimal("100.00")
        assert leur_fournisseur.cours(AUTRE_ACTIF, VENDREDI).valeur == Decimal("200.00")
        assert leur_fournisseur.refus == []


class TestUneCotationQuiChange:
    """Le cache est tenu par actif : changer de cotation ne doit jamais mêler deux places dans une
    même série (relecture de l'étape 8 quater, D-50, D-85)."""

    def test_hors_ligne_les_cours_d_une_autre_cotation_ne_servent_pas(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00", ticker="ANCIEN.F")])
        leur_fournisseur = FournisseurDeCours(
            configuration(), cache, None, hors_ligne=True, aujourd_hui=AUJOURD_HUI
        )

        assert leur_fournisseur.cours(ACTIF, VENDREDI) is None

    def test_en_ligne_ils_sont_oublies_et_la_serie_reprise_a_la_source(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00", ticker="ANCIEN.F")])
        source = SourceFictive({ACTIF: [cours(VENDREDI, "101.00")]})
        leur_fournisseur = FournisseurDeCours(
            configuration(), cache, source, aujourd_hui=AUJOURD_HUI
        )

        assert leur_fournisseur.cours(ACTIF, VENDREDI).valeur == Decimal("101.00")
        assert {un.ticker for un in cache.lire(ACTIF).values()} == {TICKER}

    def test_un_cours_garde_sans_ticker_reste_presume_juste(self):
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, [cours(VENDREDI, "100.00", ticker=None)])
        leur_fournisseur = FournisseurDeCours(
            configuration(), cache, None, hors_ligne=True, aujourd_hui=AUJOURD_HUI
        )

        assert leur_fournisseur.cours(ACTIF, VENDREDI).valeur == Decimal("100.00")


def jours_ouvres(du: Date, au: Date) -> list:
    """Un cours par jour du lundi au vendredi, comme une vraie place de cotation."""
    from datetime import timedelta

    jours = []
    jour = du
    while jour <= au:
        if jour.weekday() < 5:
            jours.append(cours(jour, "100.00"))
        jour += timedelta(days=1)
    return jours
