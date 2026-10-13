"""La recherche en ligne, sur des sources fictives : **aucun test ne sort de la machine**.

Valeurs fictives (D-03). Les cas reproduisent les pièges mesurés le 2026-10-05
(docs/reglages-automatiques.md) : la cotation londonienne en dollars, le pseudo-ticker sans
historique, les deux parts d'un même fonds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import FraisCourantsProposes, Proposition, TypeActif
from pastory.donnees_externes.cours import Cours, DeviseInattendue, ErreurDeSource
from pastory.pivot.operation import Operation, Poche, Provenance, TypeOperation
from pastory.reglages import CeQueDitLaBanque, Origine, Trou, Trouvee
from pastory.reglages.cache import CacheDesReglages, Champ
from pastory.reglages.recherche import Recherche, _nom_simplifie, seuil

ETF = "XX0000000001"
CRYPTO = "XYZ"
AUJOURD_HUI = Date(2026, 10, 5)
JOURS = [Date(2026, 9, 1) + timedelta(days=7 * semaine) for semaine in range(4)]
"""Quatre mardis : jours cotés partout."""


def achat(actif=ETF, jour=JOURS[0], prix="100.00", poche=Poche.CTO) -> Operation:
    return Operation(
        identifiant=f"{actif}-{jour}",
        instant_utc=datetime(jour.year, jour.month, jour.day, 10, tzinfo=UTC),
        date=jour,
        type=TypeOperation.ACHAT,
        nature_source="ordre_ponctuel",
        actif=actif,
        poche=poche,
        frais=Decimal("1.00"),
        taxes=Decimal("0"),
        montant_regle=None,
        reference_source="test",
        provenance={"prix_unitaire": Provenance.DONNEE},
        quantite=Decimal("1"),
        prix_unitaire=Decimal(prix),
        montant_brut=Decimal(prix),
    )


def banque(type_actif=TypeActif.ETF, actif=ETF) -> CeQueDitLaBanque:
    poche = Poche.CRYPTO if type_actif is TypeActif.CRYPTO else Poche.CTO
    return CeQueDitLaBanque(
        source="export de test",
        date=AUJOURD_HUI,
        types={actif: frozenset({type_actif})},
        poches={actif: frozenset({poche})},
        noms={actif: "ETF Monde Fictif"},
    )


class Cotations:
    """Une source de cotations fictive.

    `recherches` : requête → candidats. `series` : ticker → (devise, cours constant), la devise
    « EUR » seule passant le contrôle de `serie`. `vides` : tickers qui répondent sans historique.
    """

    nom = "source de test"

    def __init__(self, recherches, series, vides=()):
        self.recherches = recherches
        self.series = series
        self.vides = set(vides)
        self.appels: list[str] = []

    def candidats(self, requete):
        self.appels.append(f"recherche:{requete}")
        return [Proposition(ticker=t, nom=n) for t, n in self.recherches.get(requete, [])]

    def _jours(self, debut, fin):
        jour = debut
        while jour <= fin:
            if jour.weekday() < 5:
                yield jour
            jour += timedelta(days=1)

    def serie(self, actif, declaration, debut, fin):
        self.appels.append(f"serie:{declaration.ticker}")
        if declaration.ticker in self.vides:
            return []
        if declaration.ticker not in self.series:
            raise ErreurDeSource("ticker inconnu")
        devise, valeur = self.series[declaration.ticker]
        if devise != declaration.devise:
            raise DeviseInattendue(f"{declaration.ticker} est coté en {devise}")
        return [
            Cours(actif, jour, Decimal(valeur), devise, "place", self.nom, AUJOURD_HUI)
            for jour in self._jours(debut, fin)
        ]

    def serie_brute(self, ticker, debut, fin):
        self.appels.append(f"brute:{ticker}")
        devise, valeur = self.series[ticker]
        return devise, [(jour, Decimal(valeur)) for jour in self._jours(debut, fin)]


def recherche(tmp_path, cotations, frais=(), tiers=False) -> Recherche:
    return Recherche(
        CacheDesReglages(tmp_path / "reglages.csv"),
        cotations,
        frais,
        tiers=tiers,
        aujourd_hui=AUJOURD_HUI,
    )


def achats(prix="100.00", actif=ETF, poche=Poche.CTO):
    return [achat(actif, jour, prix, poche) for jour in JOURS]


class TestParLIsin:
    def test_une_cotation_en_euros_qui_retombe_sur_le_prix_paye_est_retenue(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", "ETF Monde")]}, {"AAAA.DE": ("EUR", "100.50")})

        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert isinstance(cotation, Trouvee)
        assert cotation.valeur.ticker == "AAAA.DE"
        assert "4 ordre(s)" in cotation.origine.controle
        assert "0,5 %" in cotation.origine.controle

    def test_le_pseudo_ticker_sans_historique_est_ecarte(self, tmp_path):
        # Stuttgart annonce l'euro mais n'a aucun cours : il ne doit jamais être retenu.
        source = Cotations(
            {ETF: [("XX0000000001.SG", None), ("AAAA.DE", None)]},
            {"AAAA.DE": ("EUR", "100")},
            vides={"XX0000000001.SG"},
        )
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation
        assert cotation.valeur.ticker == "AAAA.DE"

    def test_sans_prix_paye_une_cotation_par_isin_est_retenue_avec_sa_reserve(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        cotation = recherche(tmp_path, source).trouver(banque(), [])[ETF].cotation

        assert cotation.valeur.ticker == "AAAA.DE"
        assert "aucun achat ni aucune vente" in cotation.origine.reserve

    def test_une_cotation_qui_ne_retombe_pas_sur_le_prix_paye_n_est_pas_retenue(self, tmp_path):
        # Un autre fonds sur le même indice : même devise, prix sans rapport.
        source = Cotations({ETF: [("AUTRE.PA", None)]}, {"AUTRE.PA": ("EUR", "40")})
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert isinstance(cotation, Trou)
        assert "AUTRE.PA" in cotation.motif
        assert "60 %" in cotation.motif


class TestParLeNom:
    """Le cas courant de l'ETF irlandais : par ISIN, la recherche ne trouve que Londres en $."""

    def source(self, prix_dist="100"):
        return Cotations(
            {
                ETF: [("AAAA.L", "ETF Monde Fictif")],
                "ETF Monde Fictif": [("AAAD.DE", None), ("AAAA.DE", None)],
            },
            {
                "AAAA.L": ("USD", "116"),  # 116 $ / 1,16 = 100 €
                "EURUSD=X": ("USD", "1.16"),
                "AAAA.DE": ("EUR", "100"),
                "AAAD.DE": ("EUR", str(Decimal(prix_dist))),
            },
        )

    def test_la_cotation_en_euros_est_trouvee_par_le_nom_et_controlee_par_le_change(
        self, tmp_path
    ):
        cotation = recherche(tmp_path, self.source("102")).trouver(banque(), achats())[
            ETF
        ].cotation

        assert cotation.valeur.ticker == "AAAA.DE"
        assert "par son nom" in cotation.origine.controle
        assert "AAAA.L (USD)" in cotation.origine.controle

    def test_l_autre_part_du_meme_fonds_est_ecartee_par_le_change(self, tmp_path):
        # Distribuante à 102 € : 2 % du prix payé, dans la tolérance d'un ETF à quatre ordres
        # (4 %), mais 2 % du cours de référence converti, au-delà de 1 %.
        source = self.source("102")
        source.series["AAAA.DE"] = ("EUR", "130")  # la bonne part n'est plus là
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert isinstance(cotation, Trou)
        assert "autres parts du même fonds" in cotation.motif

    def test_la_livre_en_pence_est_convertie_avant_la_comparaison(self, tmp_path):
        source = Cotations(
            {ETF: [("AAAA.L", "ETF Monde Fictif")], "ETF Monde Fictif": [("AAAA.DE", None)]},
            {
                "AAAA.L": ("GBp", "8500"),  # 85 £ / 0,85 = 100 €
                "EURGBP=X": ("GBP", "0.85"),
                "AAAA.DE": ("EUR", "100"),
            },
        )
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation
        assert cotation.valeur.ticker == "AAAA.DE"

    def test_sans_prix_paye_rien_n_est_retenu_par_le_nom(self, tmp_path):
        cotation = recherche(tmp_path, self.source()).trouver(banque(), [])[ETF].cotation
        assert isinstance(cotation, Trou)
        assert "aucun achat ni aucune vente" in cotation.motif


class TestCrypto:
    def test_le_code_de_la_banque_donne_la_cotation_en_euros(self, tmp_path):
        source = Cotations({}, {"XYZ-EUR": ("EUR", "30000")})
        cotation = recherche(tmp_path, source).trouver(
            banque(TypeActif.CRYPTO, CRYPTO),
            achats("30500", CRYPTO, Poche.CRYPTO),
        )[CRYPTO].cotation

        assert cotation.valeur.ticker == "XYZ-EUR"
        assert "code donné par la banque" in cotation.origine.controle

    def test_un_code_que_la_source_ne_connait_pas_donne_un_trou(self, tmp_path):
        cotation = recherche(tmp_path, Cotations({}, {})).trouver(
            banque(TypeActif.CRYPTO, CRYPTO), achats("30500", CRYPTO, Poche.CRYPTO)
        )[CRYPTO].cotation
        assert isinstance(cotation, Trou)


class TestLeCache:
    def test_une_cotation_trouvee_n_est_plus_recherchee(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        recherche(tmp_path, source).trouver(banque(), achats())
        source.appels.clear()

        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert cotation.valeur.ticker == "AAAA.DE"
        assert source.appels == []

    def test_hors_ligne_le_cache_sert_et_rien_d_autre(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        recherche(tmp_path, source).trouver(banque(), achats())

        hors_ligne = Recherche(CacheDesReglages(tmp_path / "reglages.csv"), None)
        assert hors_ligne.trouver(banque(), achats())[ETF].cotation.valeur.ticker == "AAAA.DE"

    def test_rien_n_est_cherche_pour_l_export_d_un_tiers(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        cotation = recherche(tmp_path, source, tiers=True).trouver(banque(), achats())[
            ETF
        ].cotation

        assert isinstance(cotation, Trou)
        assert source.appels == []

    def test_une_panne_reseau_n_est_pas_gardee(self, tmp_path):
        class EnPanne(Cotations):
            def candidats(self, requete):
                raise ErreurDeSource("réseau coupé")

        recherche(tmp_path, EnPanne({}, {})).trouver(banque(), achats())
        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.COTATION) is None


class FraisFictifs:
    def __init__(self, nom, ter):
        self.nom = nom
        self.ter = ter

    def frais_courants(self, actif):
        if self.ter is None:
            return None
        return FraisCourantsProposes(Decimal(self.ter), self.nom, date=Date(2026, 6, 1))


class TestFraisCourants:
    def source(self):
        return Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})

    def test_la_premiere_source_fait_foi_et_l_ecart_est_dit(self, tmp_path):
        frais = [lambda: FraisFictifs("émetteur", "0.12"), lambda: FraisFictifs("liste", "0.15")]
        ter = recherche(tmp_path, self.source(), frais).trouver(banque(), achats())[ETF].ter

        assert ter.valeur == Decimal("0.12")
        assert ter.origine.source == "émetteur"
        assert "liste donne 0,15 %" in ter.origine.controle

    def test_une_valeur_hors_fourchette_n_est_pas_appliquee(self, tmp_path):
        # 20 pour 0,20 % : l'erreur d'unité que D-61 refuse.
        frais = [lambda: FraisFictifs("émetteur", "20"), lambda: FraisFictifs("liste", "0.20")]
        ter = recherche(tmp_path, self.source(), frais).trouver(banque(), achats())[ETF].ter
        assert ter.origine.source == "liste"

    def test_sans_aucune_source_le_ter_est_un_trou(self, tmp_path):
        frais = [lambda: FraisFictifs("émetteur", None)]
        ter = recherche(tmp_path, self.source(), frais).trouver(banque(), achats())[ETF].ter
        assert isinstance(ter, Trou)

    def test_une_source_qui_ne_se_construit_pas_est_dite(self, tmp_path):
        def en_panne():
            raise ErreurDeSource("liste injoignable")

        ter = recherche(tmp_path, self.source(), [en_panne]).trouver(banque(), achats())[ETF].ter
        assert "liste injoignable" in ter.motif

    def test_une_action_n_a_pas_de_ter(self, tmp_path):
        frais = [lambda: FraisFictifs("émetteur", "0.12")]
        trouve = recherche(tmp_path, self.source(), frais).trouver(
            banque(TypeActif.ACTION), achats()
        )
        assert trouve[ETF].ter is None


class TestTolerances:
    def test_plus_il_y_a_d_ordres_plus_la_tolerance_est_serree(self):
        assert seuil(TypeActif.ETF, 1) > seuil(TypeActif.ETF, 4) > seuil(TypeActif.ETF, 6)
        assert seuil(TypeActif.CRYPTO, 6) > seuil(TypeActif.ETF, 6)


class TestCeQuiNeSeGardePas:
    """Trouvé sur les données du propriétaire : une panne passagère de la liste de Xetra avait
    été gardée une semaine comme « frais courants introuvables »."""

    def test_un_ter_introuvable_a_cause_d_une_panne_n_est_pas_garde(self, tmp_path):
        def en_panne():
            raise ErreurDeSource("liste injoignable")

        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        recherche(tmp_path, source, [en_panne]).trouver(banque(), achats())

        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.TER) is None

    def test_un_ter_introuvable_sans_panne_est_garde(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        recherche(tmp_path, source, [lambda: FraisFictifs("liste", None)]).trouver(
            banque(), achats()
        )

        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.TER) is not None

    def test_hors_ligne_un_ter_jamais_cherche_le_dit(self, tmp_path):
        hors_ligne = Recherche(CacheDesReglages(tmp_path / "reglages.csv"), None)
        ter = hors_ligne.trouver(banque(), achats())[ETF].ter
        assert "sans accès au réseau" in ter.motif

    def test_la_date_d_effet_d_un_ter_se_dit_comme_telle(self, tmp_path):
        from pastory.donnees_externes import amundi

        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        frais = [lambda: FraisFictifs(amundi.NOM_FRAIS_COURANTS, "0.2")]
        recherche(tmp_path, source, frais).trouver(banque(), achats())

        relu = CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.TER).resultat
        assert relu.origine.intitule_de_la_date == "taux en vigueur depuis le"


class TestLaPlace:
    ACTION_US = "US0000000001"

    def test_pour_une_action_americaine_francfort_l_emporte_a_ecart_comparable(self, tmp_path):
        # D-88 : Xetra est un peu plus proche du prix payé ce jour-là, mais l'écart est du
        # bruit d'heure de clôture ; Francfort, qui cote jusque vers 22 h, est préférée.
        source = Cotations(
            {self.ACTION_US: [("AAA.DE", None), ("AAA.F", None)]},
            {"AAA.DE": ("EUR", "100.2"), "AAA.F": ("EUR", "100.6")},
        )
        cotation = recherche(tmp_path, source).trouver(
            banque(TypeActif.ACTION, self.ACTION_US), achats("100.00", self.ACTION_US)
        )[self.ACTION_US].cotation

        assert cotation.valeur.ticker == "AAA.F"

    def test_hors_des_etats_unis_xetra_reste_premiere(self, tmp_path):
        source = Cotations(
            {ETF: [("AAA.F", None), ("AAA.DE", None)]},
            {"AAA.DE": ("EUR", "100.6"), "AAA.F": ("EUR", "100.2")},
        )
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation
        assert cotation.valeur.ticker == "AAA.DE"

    def test_un_ecart_net_l_emporte_sur_la_place(self, tmp_path):
        # Deux parts d'un même fonds : 3 points d'écart, ce n'est plus du bruit.
        source = Cotations(
            {ETF: [("DIST.DE", None), ("ACC.PA", None)]},
            {"DIST.DE": ("EUR", "103"), "ACC.PA": ("EUR", "100")},
        )
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation
        assert cotation.valeur.ticker == "ACC.PA"


class TestCeQueLaRelectureATrouve:
    """Les défauts trouvés par la relecture indépendante de l'étape 8 quater, un test chacun."""

    def test_une_panne_pendant_les_series_n_est_pas_gardee(self, tmp_path):
        # Remarque 5 : le réseau tombe après la recherche, pendant les séries des candidats.
        from pastory.donnees_externes.cours import SourceInjoignable

        class SeriesEnPanne(Cotations):
            def serie(self, actif, declaration, debut, fin):
                raise SourceInjoignable("délai dépassé")

        source = SeriesEnPanne({ETF: [("AAAA.DE", None)]}, {})
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert isinstance(cotation, Trou)
        assert "sera refaite" in cotation.motif
        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.COTATION) is None

    def test_le_pseudo_ticker_muet_n_est_pas_la_reference_du_change(self, tmp_path):
        # Remarque 4 : la référence est une cotation refusée pour sa devise, pas un candidat muet.
        source = Cotations(
            {
                ETF: [("XX.SG", "ETF Monde Fictif"), ("AAAA.L", "ETF Monde Fictif")],
                "ETF Monde Fictif": [("AAAA.DE", None)],
            },
            {
                "AAAA.L": ("USD", "116"),
                "EURUSD=X": ("USD", "1.16"),
                "AAAA.DE": ("EUR", "100"),
            },
            vides={"XX.SG"},
        )
        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert cotation.valeur.ticker == "AAAA.DE"
        assert "AAAA.L (USD)" in cotation.origine.controle

    def test_la_reference_et_le_change_ne_sont_lus_qu_une_fois(self, tmp_path):
        # Remarque 10 : plusieurs candidats par le nom, une seule lecture de chaque série.
        source = Cotations(
            {
                ETF: [("AAAA.L", "ETF Monde Fictif")],
                "ETF Monde Fictif": [("AAAA.DE", None), ("AAAA.AS", None), ("AAAA.MI", None)],
            },
            {
                "AAAA.L": ("USD", "116"),
                "EURUSD=X": ("USD", "1.16"),
                "AAAA.DE": ("EUR", "100"),
                "AAAA.AS": ("EUR", "100.1"),
                "AAAA.MI": ("EUR", "100.2"),
            },
        )
        recherche(tmp_path, source).trouver(banque(), achats())

        assert source.appels.count("brute:AAAA.L") == 1
        assert source.appels.count("brute:EURUSD=X") == 1

    def test_un_type_corrige_guide_la_recherche(self, tmp_path):
        # Remarque 3 : la banque se contredit, l'utilisateur corrige ; la recherche le suit.
        from pastory.config.actifs import Configuration, Declaration

        contradictoire = CeQueDitLaBanque(
            source="export de test",
            date=AUJOURD_HUI,
            types={ETF: frozenset({TypeActif.ETF, TypeActif.ACTION})},
            poches={ETF: frozenset({Poche.CTO})},
        )
        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        corrections = Configuration({ETF: Declaration(type=TypeActif.ETF)})
        trouve = recherche(
            tmp_path, source, [lambda: FraisFictifs("liste", "0.2")]
        ).trouver(contradictoire, achats(), corrections)[ETF]

        assert trouve.cotation.valeur.ticker == "AAAA.DE"
        assert trouve.ter.valeur == Decimal("0.2")

    def test_un_ter_sans_date_n_est_pas_retenu(self, tmp_path):
        # Remarque 7 : D-58 vaut pour toutes les sources, pas seulement pour Amundi.
        class SansDate(FraisFictifs):
            def frais_courants(self, actif):
                return FraisCourantsProposes(Decimal(self.ter), self.nom)

        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        ter = recherche(tmp_path, source, [lambda: SansDate("liste", "0.2")]).trouver(
            banque(), achats()
        )[ETF].ter
        assert isinstance(ter, Trou)

    def test_l_emetteur_en_panne_n_installe_pas_pour_un_mois_la_valeur_de_xetra(self, tmp_path):
        # Remarque 9 : la source de confiance n'a pas répondu ; la valeur de repli sert, le dit,
        # et n'est pas gardée.
        def en_panne():
            raise ErreurDeSource("émetteur injoignable")

        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        ter = recherche(
            tmp_path, source, [en_panne, lambda: FraisFictifs("liste", "0.25")]
        ).trouver(banque(), achats())[ETF].ter

        assert ter.valeur == Decimal("0.25")
        assert "émetteur injoignable" in ter.origine.controle
        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.TER) is None

    def test_une_valeur_connue_survit_a_une_panne(self, tmp_path):
        # Remarque 6 : un TER trouvé il y a 31 jours, et la source tombe aujourd'hui.
        from datetime import timedelta as Duree

        cache = CacheDesReglages(tmp_path / "reglages.csv")
        ancien = Trouvee(Decimal("0.2"), Origine(source="liste", date=Date(2026, 8, 1)))
        cache.ecrire(ETF, Champ.TER, ancien, AUJOURD_HUI - Duree(days=31))

        def en_panne():
            raise ErreurDeSource("liste injoignable")

        source = Cotations({ETF: [("AAAA.DE", None)]}, {"AAAA.DE": ("EUR", "100")})
        ter = Recherche(cache, source, [en_panne], aujourd_hui=AUJOURD_HUI).trouver(
            banque(), achats()
        )[ETF].ter

        assert ter == ancien


class TestParLeNomSimplifie:
    """Trouvé sur le premier export d'un autre utilisateur : une action américaine très courante
    restait sans cours. Par l'ISIN, la source ne donne que New York, en dollars ; par les noms
    exacts — « FICTIVE, Inc. » pour elle, « Fictive (B) » pour la banque — aucune cotation en
    euros. Seul le nom qu'on dirait, « Fictive », les lui fait trouver."""

    ACTION_US = "US0000000002"

    def banque(self):
        return CeQueDitLaBanque(
            source="export de test",
            date=AUJOURD_HUI,
            types={self.ACTION_US: frozenset({TypeActif.ACTION})},
            poches={self.ACTION_US: frozenset({Poche.CTO})},
            noms={self.ACTION_US: "Fictive (B)"},
        )

    def source(self, **series):
        return Cotations(
            {
                self.ACTION_US: [("FCT", "FICTIVE, Inc.")],
                "FICTIVE, Inc.": [("FCT", "FICTIVE, Inc."), ("AUTRE", "Autre Société, Inc.")],
                "Fictive (B)": [],
                "FICTIVE": [("FCT", None), ("FCT.DE", None), ("FCT.F", None), ("FCT.SA", None)],
            },
            {
                "FCT": ("USD", "116"),  # 116 $ / 1,16 = 100 €
                "AUTRE": ("USD", "40"),
                "EURUSD=X": ("USD", "1.16"),
                "FCT.DE": ("EUR", "100.2"),
                "FCT.F": ("EUR", "100.1"),
                "FCT.SA": ("BRL", "600"),
                **series,
            },
        )

    def cotation(self, tmp_path, source):
        return recherche(tmp_path, source).trouver(
            self.banque(), achats("100.00", self.ACTION_US)
        )[self.ACTION_US].cotation

    def test_la_cotation_en_euros_est_trouvee_par_le_nom_simplifie(self, tmp_path):
        source = self.source()
        cotation = self.cotation(tmp_path, source)

        assert cotation.valeur.ticker == "FCT.F"  # D-88 : Francfort pour une action américaine
        assert "par son nom" in cotation.origine.controle
        assert "FCT (USD)" in cotation.origine.controle
        assert "recherche:FICTIVE" in source.appels

    def test_les_deux_ecritures_d_un_meme_nom_ne_font_qu_une_demande(self, tmp_path):
        source = self.source()
        self.cotation(tmp_path, source)
        assert [a for a in source.appels if a.casefold() == "recherche:fictive"] == [
            "recherche:FICTIVE"
        ]

    def test_le_nom_simplifie_n_est_demande_qu_en_second_recours(self, tmp_path):
        """Tant que les noms exacts suffisent, rien de plus n'est demandé à la source : rien ne
        change pour les actifs que Pastory trouvait déjà."""
        source = self.source()
        source.recherches["FICTIVE, Inc."] = [("FCT", None), ("FCT.F", None)]

        cotation = self.cotation(tmp_path, source)

        assert cotation.valeur.ticker == "FCT.F"
        assert "recherche:FICTIVE, Inc." in source.appels
        assert "recherche:FICTIVE" not in source.appels

    def test_une_autre_societe_au_nom_voisin_n_est_pas_retenue(self, tmp_path):
        """Le nom ne sert qu'à demander des candidats. Une société homonyme qui cote par hasard
        au prix payé ne suit pas, une fois convertie, la cotation trouvée par l'ISIN."""
        source = self.source(**{"FCT.DE": ("EUR", "130"), "FCT.F": ("EUR", "130")})
        source.recherches["FICTIVE"] = [("HOMONYME.DE", None)]
        source.series["HOMONYME.DE"] = ("EUR", "100.3")
        source.series["FCT"] = ("USD", "150")  # la vraie vaut 129 € : l'homonyme n'en est pas

        cotation = self.cotation(tmp_path, source)
        assert isinstance(cotation, Trou)

    def test_sans_cotation_en_euros_nulle_part_le_trou_reste_un_trou(self, tmp_path):
        source = self.source()
        source.recherches["FICTIVE"] = [("FCT", None), ("FCT.SA", None)]
        cotation = self.cotation(tmp_path, source)

        assert isinstance(cotation, Trou)
        assert "aucune en euros" in cotation.motif


class TestNomSimplifie:
    def test_ce_qui_est_retire(self):
        assert _nom_simplifie("FICTIVE, Inc.") == "FICTIVE"
        assert _nom_simplifie("Fictive (B)") == "Fictive"
        assert _nom_simplifie("Fictive Corporation") == "Fictive"
        assert _nom_simplifie("Fictive Holding N.V.") == "Fictive Holding"

    def test_ce_qui_ne_se_simplifie_pas(self):
        assert _nom_simplifie("Fictive") is None
        assert _nom_simplifie("SA") is None
        assert _nom_simplifie("(B)") is None


class TestLaRechercheDitOuElleEnEst:
    """D-110 : la barre d'attente avance d'un cran par actif recherché."""

    def test_un_appel_par_actif_une_fois_l_actif_traite(self, tmp_path):
        autre = "XX0000000002"
        la_banque = CeQueDitLaBanque(
            source="export de test",
            date=AUJOURD_HUI,
            types={ETF: frozenset({TypeActif.ETF}), autre: frozenset({TypeActif.ETF})},
            poches={ETF: frozenset({Poche.CTO}), autre: frozenset({Poche.CTO})},
            noms={ETF: "ETF Monde Fictif", autre: "Autre ETF Fictif"},
        )
        source = Cotations({ETF: [("AAAA.DE", "ETF Monde")]}, {"AAAA.DE": ("EUR", "100.50")})
        traites: list[int] = []

        trouves = recherche(tmp_path, source).trouver(
            la_banque, achats(), apres_chaque_actif=lambda: traites.append(len(traites))
        )

        assert len(traites) == len(trouves) == 2

    def test_sans_personne_a_prevenir_la_recherche_est_la_meme(self, tmp_path):
        source = Cotations({ETF: [("AAAA.DE", "ETF Monde")]}, {"AAAA.DE": ("EUR", "100.50")})

        cotation = recherche(tmp_path, source).trouver(banque(), achats())[ETF].cotation

        assert isinstance(cotation, Trouvee)
