"""L'assembleur : les cours demandés une fois par actif (D-110).

Mesuré sur la démonstration, dossier vide : demandés par petites fenêtres — une par date
d'opération —, les cours coûtaient 78 secondes d'attente et laissaient une semaine sans cours
entre deux fenêtres. Demandés d'un coup, de la première opération à hier : 2 secondes, et une
série sans trou. Ces tests tiennent les deux promesses, et celle du cache (D-50).
"""

from __future__ import annotations

from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from pastory import assembleur
from pastory.avancement import Etape, Point, Suivi
from pastory.config import actifs as config_actifs
from pastory.config.actifs import Declaration
from pastory.donnees_externes.cours import (
    MARGE_APRES,
    MARGE_AVANT,
    FournisseurDeCours,
    PeriodeSansCours,
    SourceInjoignable,
    TickerInconnu,
)
from pastory.moteur import rendements
from pastory.pivot.operation import TypeOperation
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
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


def vente(jour: Date, actif: str = ACTIF):
    return operation(
        TypeOperation.VENTE,
        horodatage=f"{jour.isoformat()} 09:00",
        actif=actif,
        quantite="1",
        prix_unitaire="100.00",
    )


def jours_cotes(
    debut: Date, fin: Date, actif: str = ACTIF, ticker: str = TICKER, valeur: str = "100.00"
):
    jour, serie = debut, []
    while jour <= fin:
        if jour.weekday() < 5:
            serie.append(cours(jour, valeur, actif, ticker=ticker))
        jour += timedelta(days=1)
    return serie


def deja_repris(*actifs: str) -> CacheEnMemoire:
    """Un cache dont les séries ont déjà été reprises (D-113) : le régime de croisière."""
    cache = CacheEnMemoire()
    for actif in actifs:
        cache.noter_la_reprise(actif)
    return cache


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
        """Le trou que laissaient deux fenêtres voisines, reproduit puis évité : deux
        opérations à quarante jours d'écart, et sept jours qui ne tombent ni dans la fenêtre
        de l'une (jusqu'à J + 3) ni dans celle de l'autre (depuis J − 30). Trop court pour
        être vu comme un trou, assez long pour qu'une valeur s'y lise sur un cours périmé."""
        seconde = PREMIER_ACHAT + timedelta(days=40)
        operations = [achat(PREMIER_ACHAT), achat(seconde)]

        def plus_grand_ecart(cache) -> int:
            connus = [
                jour for jour in sorted(cache.lire(ACTIF)) if PREMIER_ACHAT <= jour <= seconde
            ]
            return max((b - a).days for a, b in zip(connus, connus[1:], strict=False))

        par_fenetres = CacheEnMemoire()
        a_l_ancienne = fournisseur(
            SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)}), par_fenetres
        )
        # La valorisation lit la date la plus tardive d'abord, puis remonte : c'est dans cet
        # ordre que deux fenêtres laissent un vide entre elles.
        for une in reversed(operations):
            a_l_ancienne.cours(ACTIF, une.date)
        assert plus_grand_ecart(par_fenetres) == 7

        d_un_coup = CacheEnMemoire()
        assembleur.remplir_les_cours(
            operations,
            fournisseur(SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)}), d_un_coup),
        )
        assert plus_grand_ecart(d_un_coup) <= 3

    def test_un_cache_deja_rempli_ne_redemande_que_la_suite(self):
        """D-50 : un cours gardé n'est ni redemandé ni réécrit."""
        dernier_connu = Date(2026, 9, 18)
        cache = deja_repris(ACTIF)
        cache.ecrire(ACTIF, jours_cotes(Date(2026, 1, 1), dernier_connu))
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == [(ACTIF, dernier_connu + timedelta(days=1), HIER)]

    def test_chaque_actif_a_sa_demande_depuis_sa_propre_premiere_operation(self):
        declarations = {
            ACTIF: Declaration(TICKER, "EUR"),
            AUTRE_ACTIF: Declaration("BBBB.DE", "EUR"),
        }
        source = SourceFictive(
            {
                ACTIF: jours_cotes(Date(2026, 1, 1), HIER),
                AUTRE_ACTIF: jours_cotes(Date(2026, 1, 1), HIER, AUTRE_ACTIF, "BBBB.DE"),
            }
        )
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


class TestUnTitreVendu:
    """Trouvé par la relecture : demandé jusqu'à hier comme les autres, un titre vendu puis
    retiré de la cote levait à chaque ouverture une alerte sur un actif qu'on ne détient plus."""

    VENTE = Date(2026, 6, 3)

    def operations(self):
        return [achat(PREMIER_ACHAT), vente(self.VENTE)]

    def test_il_n_est_demande_que_jusqu_a_sa_vente(self):
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours(self.operations(), fournisseur(source))

        assert source.appels == [(ACTIF, PREMIER_ACHAT - MARGE_AVANT, self.VENTE + MARGE_APRES)]

    def test_une_fois_sa_detention_couverte_il_n_est_plus_jamais_demande(self):
        cache = deja_repris(ACTIF)
        cache.ecrire(ACTIF, jours_cotes(Date(2026, 2, 1), self.VENTE))
        source = SourceFictive(erreur=PeriodeSansCours("ce titre ne cote plus"))
        le_fournisseur = fournisseur(source, cache)

        assembleur.remplir_les_cours(self.operations(), le_fournisseur)

        assert source.appels == []
        assert le_fournisseur.refus == []

    def test_retire_de_la_cote_sa_reprise_est_tentee_une_fois_sans_un_mot(self):
        """La reprise de sa série (D-113) échoue : la source ne le connaît plus. Aucune
        alerte — on ne le détient plus —, et on n'y revient pas."""
        cache = CacheEnMemoire()
        cache.ecrire(ACTIF, jours_cotes(Date(2026, 2, 1), self.VENTE))
        source = SourceFictive(erreur=TickerInconnu("ce titre ne cote plus"))

        for _ in range(3):
            le_fournisseur = fournisseur(source, cache)
            assembleur.remplir_les_cours(self.operations(), le_fournisseur)
            assert le_fournisseur.refus == []

        assert len(source.appels) == 1

    def test_un_titre_rachete_depuis_est_de_nouveau_suivi_jusqu_a_hier(self):
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours(
            [*self.operations(), achat(Date(2026, 8, 3))], fournisseur(source)
        )

        assert source.appels == [(ACTIF, PREMIER_ACHAT - MARGE_AVANT, HIER)]


class TestUnTitreQuiNeCotaitPasEncore:
    """Trouvé par la relecture : la source n'a rien avant l'introduction d'un titre. Redemander
    chaque fois « depuis trente jours avant l'achat » faisait revenir tout l'historique à
    chaque ouverture, pour rien."""

    def test_la_seconde_ouverture_ne_redemande_pas_ce_qui_n_existe_pas(self):
        introduction = PREMIER_ACHAT - timedelta(days=2)
        cache = CacheEnMemoire()
        source = SourceFictive({ACTIF: jours_cotes(introduction, HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))
        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == [(ACTIF, PREMIER_ACHAT - MARGE_AVANT, HIER)]

    def test_un_trou_au_milieu_du_cache_reste_comble(self):
        """Ne plus rien demander avant le premier jour gardé ne doit pas empêcher de
        combler un vrai trou plus loin (étape 9)."""
        cache = deja_repris(ACTIF)
        cache.ecrire(
            ACTIF,
            jours_cotes(Date(2026, 2, 2), Date(2026, 4, 30))
            + jours_cotes(Date(2026, 7, 1), HIER),
        )
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == [(ACTIF, Date(2026, 5, 1), HIER)]


class TestLaRepriseDesSeries:
    """D-113, la réponse à Q-62 : un cache construit par petites fenêtres garde des jours sans
    cours, et rien en lui ne le dit. Chaque série est donc reprise une fois en entier."""

    TROU = (Date(2026, 4, 6), Date(2026, 4, 10))
    """Une semaine sans cours : trop courte pour être vue comme un trou (il en faut dix)."""

    def cache_troue(self) -> CacheEnMemoire:
        cache = CacheEnMemoire()
        cache.ecrire(
            ACTIF,
            jours_cotes(Date(2026, 2, 2), self.TROU[0] - timedelta(days=1))
            + jours_cotes(self.TROU[1] + timedelta(days=1), HIER),
        )
        return cache

    def test_sans_reprise_le_trou_court_n_est_jamais_comble(self):
        """Le défaut, tel qu'il était : c'est ce que fait encore un cache déjà repris."""
        cache = self.cache_troue()
        cache.noter_la_reprise(ACTIF)
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == []
        assert self.TROU[0] not in cache.lire(ACTIF)

    def test_la_premiere_ouverture_comble_le_trou(self):
        cache = self.cache_troue()
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert source.appels == [(ACTIF, PREMIER_ACHAT - MARGE_AVANT, HIER)]
        connus = sorted(cache.lire(ACTIF))
        assert self.TROU[0] in connus and self.TROU[1] in connus
        assert max((b - a).days for a, b in zip(connus, connus[1:], strict=False)) <= 3

    def test_aucun_cours_deja_garde_n_est_reecrit(self):
        """D-50 : la source répond 250,00 partout, le cache gardait 100,00. Seuls les jours
        qui manquaient prennent la valeur de la source."""
        cache = self.cache_troue()
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER, valeur="250.00")})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        serie = cache.lire(ACTIF)
        assert serie[self.TROU[0]].valeur == Decimal("250.00")
        assert serie[Date(2026, 3, 2)].valeur == Decimal("100.00")
        assert serie[HIER].valeur == Decimal("100.00")

    def test_elle_n_a_lieu_qu_une_fois(self):
        cache = self.cache_troue()
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        for _ in range(3):
            assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert len(source.appels) == 1
        assert cache.serie_reprise(ACTIF)

    def test_une_panne_la_remet_a_la_prochaine_ouverture(self):
        cache = self.cache_troue()
        en_panne = SourceFictive(erreur=SourceInjoignable("réseau coupé"))

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(en_panne, cache))

        assert not cache.serie_reprise(ACTIF)
        assert self.TROU[0] not in cache.lire(ACTIF)

        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})
        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert cache.serie_reprise(ACTIF)
        assert self.TROU[0] in cache.lire(ACTIF)

    def test_un_dossier_neuf_est_repris_d_emblee(self):
        """Un nouvel utilisateur ne paie rien de plus : sa première demande est la reprise."""
        cache = CacheEnMemoire()
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours([achat(PREMIER_ACHAT)], fournisseur(source, cache))

        assert len(source.appels) == 1
        assert cache.serie_reprise(ACTIF)

    def test_hors_ligne_rien_n_est_repris_ni_retenu(self):
        cache = self.cache_troue()
        source = SourceFictive({ACTIF: jours_cotes(Date(2026, 1, 1), HIER)})

        assembleur.remplir_les_cours(
            [achat(PREMIER_ACHAT)], fournisseur(source, cache, hors_ligne=True)
        )

        assert source.appels == []
        assert not cache.serie_reprise(ACTIF)


class TestLaPlaceDansLaLecture:
    def test_les_cours_sont_demandes_avant_tout_calcul(self, dossier_personnel, monkeypatch):
        """Demandés après la valorisation, ils reviendraient par petites fenêtres : la
        première demande faite à la source doit être la grande, et rester la seule."""
        fictifs.deposer(dossier_personnel / "exports")
        fichier = config_actifs.chemin()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(
            f'[actifs]\n"{fictifs.ACTIF_ETF}" = {{ ticker = "T1.DE", devise = "EUR" }}\n',
            encoding="utf-8",
        )
        aujourd_hui = Date.today()
        source = SourceFictive(
            {
                fictifs.ACTIF_ETF: jours_cotes(
                    Date(2025, 1, 1), aujourd_hui, fictifs.ACTIF_ETF, "T1.DE"
                )
            }
        )
        monkeypatch.setattr(assembleur, "Yahoo", lambda *arguments, **options: source)

        construit = assembleur.construire(
            assembleur.dossier_de_lecture(None), rendements.Periode(fin=aujourd_hui)
        )

        premiere = min(
            une.date for une in construit.rapport.operations if une.actif == fictifs.ACTIF_ETF
        )
        assert source.appels == [
            (fictifs.ACTIF_ETF, premiere - MARGE_AVANT, aujourd_hui - timedelta(days=1))
        ]


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
