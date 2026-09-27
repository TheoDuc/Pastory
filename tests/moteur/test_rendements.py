"""Le gain, le TRI et le TWRR, sur des cas qu'on peut refaire dans un tableur.

Les cas portent le numéro du cahier de vérification (`docs/verification/etape-5.md`) : ce
sont exactement ceux que le propriétaire est invité à refaire avec `TRI.PAIEMENTS`. Les
valeurs sont choisies pour tomber juste : 10 % exactement, ou une racine qu'on connaît.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rendements import (
    Periode,
    SousPeriode,
    enchainer,
    rendements,
    synthese,
    tri,
)
from dashboard_tr.pivot.operation import Poche, TypeOperation
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation

AUTRE_ACTIF = "XX0000000002"


def achat(jour: str, quantite: str, prix: str, **reste) -> object:
    return operation(
        TypeOperation.ACHAT, horodatage=f"{jour} 09:00", quantite=quantite, prix_unitaire=prix,
        **reste,
    )


class TestA1GainDepuisLeDebut:
    """A.1 — L'enchaînement du glossaire, plus un dividende, valorisé à 40 €."""

    def portefeuille(self) -> Portefeuille:
        return Portefeuille.construire(
            enchainement_du_glossaire()
            + [
                operation(
                    TypeOperation.DIVIDENDE,
                    horodatage="2026-03-20 09:00",
                    quantite="15",
                    montant_brut="5.00",
                    taxes="1.50",
                )
            ]
        )

    def test_le_gain_est_la_valeur_finale_plus_les_flux(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = rendements(self.portefeuille().positions, Periode(date(2026, 3, 31)), source)

        assert resultat.valeur_debut == Decimal("0.00")
        assert resultat.valeur_fin == Decimal("600.00")  # 15 x 40
        assert resultat.achats == Decimal("500.00")  # 200 + 300
        assert resultat.ventes == Decimal("200.00")  # 5 x 40
        assert resultat.dividendes == Decimal("5.00")  # brut, pas 3,50 (D-29)
        # 600 - 0 - 500 + 200 + 5
        assert resultat.gain == Decimal("305.00")

    def test_le_gain_se_decompose_en_latente_realisee_et_dividendes(self):
        """L'identité du glossaire §4, qui prouve que les deux comptabilités concordent."""
        portefeuille = self.portefeuille()
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        [position] = portefeuille.positions
        latente = resultat.valeur_fin - position.etat.capital_net_investi  # 600 - 375
        assert latente == Decimal("225.00")
        assert position.plus_values_realisees_brutes == Decimal("75.00")
        assert resultat.gain == latente + position.plus_values_realisees_brutes + Decimal("5.00")

    def test_les_flux_sont_signes_du_point_de_vue_de_l_investisseur(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = rendements(self.portefeuille().positions, Periode(date(2026, 3, 31)), source)

        assert [(flux.date, flux.montant) for flux in resultat.flux] == [
            (date(2026, 1, 5), Decimal("-200.00")),
            (date(2026, 2, 5), Decimal("-300.00")),
            (date(2026, 3, 5), Decimal("200.00")),
            (date(2026, 3, 20), Decimal("5.00")),
        ]
        # La table du tableur : les flux, puis la valeur finale comme dernière ligne.
        assert resultat.flux_dates[-1] == (date(2026, 3, 31), Decimal("600.00"))
        assert len(resultat.flux_dates) == 5


class TestA2TriAUnSeulFlux:
    """A.2 — 1 000 € le 1er janvier 2025, 1 100 € un an plus tard : 10 %, exactement."""

    def test_dix_pour_cent_exactement(self):
        portefeuille = Portefeuille.construire([achat("2025-01-01", "10", "100.00")])
        source = SourceFixe(
            {ACTIF: {date(2025, 1, 1): "100.00", date(2026, 1, 1): "110.00"}}
        )

        resultat = rendements(portefeuille.positions, Periode(date(2026, 1, 1)), source)

        assert resultat.gain == Decimal("100.00")
        assert resultat.tri == Decimal("0.100000")
        assert resultat.twrr.taux == Decimal("0.100000")
        # Exactement un an : significatif, mais rien à annualiser.
        assert resultat.duree_jours == 365
        assert not resultat.peu_significatif
        assert resultat.twrr.annualise is None

    def test_la_formule_du_tableur_donne_la_meme_chose(self):
        # TRI.PAIEMENTS({-1000 ; 1100} ; {2025-01-01 ; 2026-01-01}) = 10 %.
        assert tri([(date(2025, 1, 1), Decimal("-1000")), (date(2026, 1, 1), Decimal("1100"))]) == (
            Decimal("0.100000")
        )


class TestA3TriADeuxFlux:
    """A.3 — Deux achats de 1 000 € à un an d'écart, 2 310 € au bout de deux ans.

    Le taux qui annule −1000 − 1000/(1+r) + 2310/(1+r)² = 0 est r = 10 % : avec x = 1/(1+r),
    2310x² − 1000x − 1000 = 0 a pour racine positive x = 10/11.
    """

    def portefeuille(self) -> Portefeuille:
        return Portefeuille.construire(
            [achat("2025-01-01", "10", "100.00"), achat("2026-01-01", "10", "100.00")]
        )

    def source(self) -> SourceFixe:
        return SourceFixe(
            {
                ACTIF: {
                    date(2025, 1, 1): "100.00",
                    date(2025, 12, 31): "100.00",
                    date(2026, 1, 1): "100.00",
                    date(2027, 1, 1): "115.50",
                }
            }
        )

    def test_le_tri_vaut_dix_pour_cent(self):
        resultat = rendements(
            self.portefeuille().positions, Periode(date(2027, 1, 1)), self.source()
        )

        assert resultat.valeur_fin == Decimal("2310.00")
        assert resultat.gain == Decimal("310.00")
        assert resultat.tri == Decimal("0.100000")

    def test_le_twrr_ne_vaut_pas_le_tri(self):
        # Année 1 : 100 → 100, soit 0 %. Année 2 : 100 → 115,50, soit +15,5 %.
        # TWRR = 1,00 x 1,155 − 1 = 15,5 % sur deux ans, 7,47 % par an : la stratégie a moins
        # rapporté que le TRI ne le dit, parce que le second achat est tombé la bonne année.
        resultat = rendements(
            self.portefeuille().positions, Periode(date(2027, 1, 1)), self.source()
        )

        assert resultat.twrr.taux == Decimal("0.155000")
        assert resultat.twrr.annualise == Decimal("0.074709")  # racine carrée de 1,155 − 1
        [premiere, seconde] = resultat.twrr.sous_periodes
        assert premiere.valeur_debut == Decimal("1000.00")
        assert premiere.valeur_fin == Decimal("1000.00")
        assert seconde.valeur_debut == Decimal("2000.00")
        assert seconde.valeur_fin == Decimal("2310.00")
        assert seconde.flux == Decimal("1000.00")  # vu du portefeuille : l'achat entre


class TestA4AcheterJusteAvantLaBaisse:
    """A.4 — La stratégie fait 0 %, l'investisseur perd 26,8 % : c'est toute la différence.

    10 parts à 100 €, le cours double, on rachète 10 parts à 200 €, le cours revient à 100 €.
    TWRR : (+100 %) puis (−50 %) → 2 x 0,5 − 1 = 0 %. TRI : −1000 − 2000x + 2000x² = 0, soit
    x = (1 + √3)/2, r = 1/x − 1 = √3 − 2 ≈ −26,79 %.
    """

    def test_twrr_nul_et_tri_negatif(self):
        portefeuille = Portefeuille.construire(
            [achat("2025-01-01", "10", "100.00"), achat("2026-01-01", "10", "200.00")]
        )
        source = SourceFixe(
            {
                ACTIF: {
                    date(2025, 1, 1): "100.00",
                    date(2026, 1, 1): "200.00",
                    date(2027, 1, 1): "100.00",
                }
            }
        )

        resultat = rendements(portefeuille.positions, Periode(date(2027, 1, 1)), source)

        assert resultat.gain == Decimal("-1000.00")  # 2000 - 3000
        assert resultat.twrr.taux == Decimal("0.000000")
        assert resultat.twrr.annualise == Decimal("0.000000")
        assert resultat.tri == Decimal("-0.267949")


class TestA5PeriodeCommencantApresLePremierAchat:
    """A.5 — Le même portefeuille qu'en A.3, regardé seulement sur sa seconde année."""

    def test_la_valeur_au_debut_compte_comme_un_achat_a_la_veille(self):
        portefeuille = Portefeuille.construire(
            [achat("2025-01-01", "10", "100.00"), achat("2026-01-01", "10", "100.00")]
        )
        source = SourceFixe(
            {
                ACTIF: {
                    date(2025, 1, 1): "100.00",
                    date(2025, 12, 31): "100.00",
                    date(2026, 1, 1): "100.00",
                    date(2027, 1, 1): "115.50",
                }
            }
        )
        periode = Periode(fin=date(2027, 1, 1), debut=date(2026, 1, 1))

        resultat = rendements(portefeuille.positions, periode, source)

        assert resultat.valeur_debut == Decimal("1000.00")  # 10 parts au soir du 2025-12-31
        assert resultat.achats == Decimal("1000.00")  # seul l'achat du 2026-01-01 est dedans
        assert resultat.gain == Decimal("310.00")  # 2310 - 1000 - 1000
        assert resultat.flux_dates[0] == (date(2025, 12, 31), Decimal("-1000.00"))
        # Un jour de plus qu'une année pleine : le TRI est presque 15,5 %.
        assert resultat.tri is not None
        assert Decimal("0.154") < resultat.tri < Decimal("0.156")
        assert resultat.twrr.taux == Decimal("0.155000")
        assert resultat.duree_jours == 366
        assert resultat.twrr.annualise is not None

    def test_une_periode_a_l_envers_est_refusee(self):
        with pytest.raises(ValueError, match="après la fin"):
            Periode(fin=date(2026, 1, 1), debut=date(2026, 6, 1))


class TestA6DividendeEtDistribution:
    """A.6 — Ce qui sort de l'actif compte comme un flux positif, distribution comprise."""

    def test_le_gain_les_compte_et_l_identite_tient(self):
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "30.00"),
                operation(
                    TypeOperation.DIVIDENDE,
                    horodatage="2026-02-01 09:00",
                    quantite="10",
                    montant_brut="5.00",
                ),
                operation(
                    TypeOperation.DISTRIBUTION_CAPITAL,
                    horodatage="2026-03-01 09:00",
                    quantite="10",
                    montant_brut="12.00",
                ),
            ]
        )
        source = SourceFixe(cours_constant(ACTIF, "30.00", date(2026, 1, 1), date(2026, 3, 31)))

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        assert resultat.dividendes == Decimal("5.00")
        assert resultat.distributions == Decimal("12.00")
        # 300 - 300 + 5 + 12
        assert resultat.gain == Decimal("17.00")
        [position] = portefeuille.positions
        latente = resultat.valeur_fin - position.etat.capital_net_investi  # 300 - 288
        assert latente == Decimal("12.00")
        assert resultat.gain == latente + Decimal("5.00")


class TestA7CeQuiNEstPasCalculable:
    """A.7 — Un montant encore à compléter, une histoire trouée, un actif sans cours."""

    def test_un_prix_a_completer_dans_la_periode_rend_le_gain_non_calculable(self):
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "20.00"),
                operation(
                    TypeOperation.TITRES_RECUS,
                    horodatage="2026-03-01 09:00",
                    quantite="3",
                    prix_a_completer=True,
                ),
            ]
        )
        source = SourceFixe(cours_constant(ACTIF, "40.00", date(2026, 1, 1), date(2026, 3, 31)))

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        assert not resultat.calculable
        assert resultat.gain is None and resultat.tri is None
        assert "dashboard cours" in (resultat.motif or "")
        # La valeur, elle, existe : les 13 parts sont bien là.
        assert resultat.valeur_fin == Decimal("520.00")

    def test_un_prix_a_completer_avant_la_periode_ne_gene_pas(self):
        # Les parts reçues sans prix sont là au début comme à la fin : le gain de la période
        # se calcule, et il est fiable.
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "20.00"),
                operation(
                    TypeOperation.TITRES_RECUS,
                    horodatage="2026-01-10 09:00",
                    quantite="3",
                    prix_a_completer=True,
                ),
            ]
        )
        source = SourceFixe(
            {ACTIF: {date(2026, 1, 31): "20.00", date(2026, 2, 28): "22.00"}}
        )

        resultat = rendements(
            portefeuille.positions, Periode(fin=date(2026, 2, 28), debut=date(2026, 2, 1)), source
        )

        assert resultat.valeur_debut == Decimal("260.00")  # 13 x 20
        assert resultat.gain == Decimal("26.00")  # 13 x 22 - 260
        assert resultat.fiable

    def test_une_vente_au_dela_du_stock_rend_le_chiffre_non_fiable(self):
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "4", "25.00"),
                operation(
                    TypeOperation.VENTE,
                    horodatage="2026-02-05 09:00",
                    quantite="10",
                    prix_unitaire="30.00",
                ),
            ]
        )
        source = SourceFixe(cours_constant(ACTIF, "30.00", date(2026, 1, 1), date(2026, 3, 31)))

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        assert resultat.gain == Decimal("200.00")  # 0 - 100 + 300 : arithmétiquement juste...
        assert not resultat.fiable  # ...mais sur une histoire trouée (D-45)

    def test_un_actif_sans_cours_a_la_fin_sort_des_totaux_et_le_dit(self):
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "20.00"),
                achat("2026-01-06", "2", "100.00", actif=AUTRE_ACTIF),
            ]
        )
        source = SourceFixe(cours_constant(ACTIF, "25.00", date(2026, 1, 1), date(2026, 3, 31)))

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        assert resultat.partiel
        [exclue] = resultat.exclues
        assert exclue.actif == AUTRE_ACTIF
        # Ni sa valeur, ni son achat : les chiffres décrivent le premier actif seul.
        assert resultat.valeur_fin == Decimal("250.00")
        assert resultat.achats == Decimal("200.00")
        assert resultat.gain == Decimal("50.00")

    def test_quand_rien_n_est_valorise_il_n_y_a_pas_de_chiffres(self):
        portefeuille = Portefeuille.construire([achat("2026-01-05", "10", "20.00")])

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), SourceFixe())

        assert not resultat.calculable
        assert "aucune des positions" in (resultat.motif or "")

    def test_un_cours_manquant_au_debut_de_la_periode_est_dit(self):
        portefeuille = Portefeuille.construire([achat("2026-01-05", "10", "20.00")])
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "25.00"}})

        resultat = rendements(
            portefeuille.positions, Periode(fin=date(2026, 3, 31), debut=date(2026, 3, 1)), source
        )

        assert not resultat.calculable
        assert "2026-02-28" in (resultat.motif or "")

    def test_sans_operation_sur_la_periode_rien_n_est_calcule(self):
        portefeuille = Portefeuille.construire([achat("2026-06-05", "10", "20.00")])
        source = SourceFixe(cours_constant(ACTIF, "20.00", date(2026, 1, 1), date(2026, 12, 31)))

        resultat = rendements(
            portefeuille.positions, Periode(fin=date(2026, 3, 31), debut=date(2026, 3, 1)), source
        )

        assert not resultat.calculable
        assert resultat.motif == "aucune opération sur la période"


class TestA8Signification:
    """A.8 — Moins d'un an : peu significatif ; plus d'un an : le TWRR s'annualise."""

    def test_moins_d_un_an_est_peu_significatif(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = rendements(
            Portefeuille.construire(enchainement_du_glossaire()).positions,
            Periode(date(2026, 3, 31)),
            source,
        )

        assert resultat.duree_jours == 85
        assert resultat.peu_significatif
        assert resultat.twrr.annualise is None

    def test_plus_d_un_an_annualise_le_twrr(self):
        # 21 % sur deux ans, c'est 10 % par an : 1,21^(365/730) = 1,1.
        portefeuille = Portefeuille.construire([achat("2025-01-01", "10", "100.00")])
        source = SourceFixe(
            {ACTIF: {date(2025, 1, 1): "100.00", date(2027, 1, 1): "121.00"}}
        )

        resultat = rendements(portefeuille.positions, Periode(date(2027, 1, 1)), source)

        assert resultat.twrr.taux == Decimal("0.210000")
        assert resultat.twrr.annualise == Decimal("0.100000")
        assert resultat.tri == Decimal("0.100000")
        assert not resultat.peu_significatif


class TestA9CasLimites:
    """A.9 — Là où un tableur rendrait une erreur, le moteur rend `None` et le dit."""

    def test_sans_changement_de_signe_il_n_y_a_pas_de_tri(self):
        deux_sorties = [(date(2026, 1, 1), Decimal("-100")), (date(2026, 6, 1), Decimal("-100"))]
        assert tri(deux_sorties) is None
        assert tri([(date(2026, 1, 1), Decimal("100"))]) is None

    def test_une_sous_periode_vide_est_ignoree(self):
        vide = SousPeriode(
            du=date(2026, 2, 1),
            au=date(2026, 3, 1),
            valeur_debut=Decimal("0.00"),
            flux=Decimal("-200.00"),
            valeur_fin=Decimal("0.00"),
        )
        pleine = SousPeriode(
            du=date(2026, 3, 1),
            au=date(2026, 4, 1),
            valeur_debut=Decimal("200.00"),
            flux=Decimal("200.00"),
            valeur_fin=Decimal("220.00"),
        )

        assert enchainer([vide, pleine]) == Decimal("0.100000")

    def test_tout_vendre_puis_racheter_ne_casse_pas_le_twrr(self):
        # Vente totale le 5 février, rachat le 5 mars : entre les deux, rien n'est détenu.
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "20.00"),
                operation(
                    TypeOperation.VENTE,
                    horodatage="2026-02-05 09:00",
                    quantite="10",
                    prix_unitaire="22.50",  # exécutée au-dessus de la clôture du jour
                ),
                achat("2026-03-05", "10", "20.00"),
            ]
        )
        source = SourceFixe(
            {
                ACTIF: {
                    date(2026, 1, 5): "20.00",
                    date(2026, 2, 5): "22.00",
                    date(2026, 3, 5): "20.00",
                    date(2026, 3, 31): "24.00",
                }
            }
        )

        resultat = rendements(portefeuille.positions, Periode(date(2026, 3, 31)), source)

        # 20 → 22 (+10 %), rien, puis 20 → 24 (+20 %) : 1,1 x 1,2 − 1 = 32 %.
        assert resultat.twrr.taux == Decimal("0.320000")
        assert resultat.gain == Decimal("65.00")  # 240 - 200 + 225 - 200

    def test_le_tri_est_borne_par_ses_deux_bornes(self):
        # Un gain absurde en un jour : au-delà de 100 000 % par an, pas de TRI.
        assert tri([(date(2026, 1, 1), Decimal("-1")), (date(2026, 1, 2), Decimal("1000"))]) is None

    def test_un_tri_hors_bornes_est_explique(self):
        portefeuille = Portefeuille.construire([achat("2026-01-05", "1", "1.00")])
        source = SourceFixe({ACTIF: {date(2026, 1, 5): "1.00", date(2026, 1, 6): "1000.00"}})

        resultat = rendements(portefeuille.positions, Periode(date(2026, 1, 6)), source)

        assert resultat.calculable
        assert resultat.tri is None
        assert "même signe" in (resultat.motif_tri or "")

    def test_un_gain_rapide_donne_un_tri_annuel_enorme_mais_calcule(self):
        # +20 % en un mois : plus de 700 % par an. C'est ce qu'un tableur afficherait, et c'est
        # le drapeau « peu significatif » qui dit que le chiffre ne veut rien dire.
        portefeuille = Portefeuille.construire([achat("2026-01-05", "10", "100.00")])
        source = SourceFixe({ACTIF: {date(2026, 1, 5): "100.00", date(2026, 2, 4): "120.00"}})

        resultat = rendements(portefeuille.positions, Periode(date(2026, 2, 4)), source)

        assert resultat.tri is not None
        assert resultat.tri > Decimal("7")
        assert resultat.peu_significatif


class TestSynthese:
    def test_total_par_poche_et_par_position_se_recoupent(self):
        portefeuille = Portefeuille.construire(
            [
                achat("2026-01-05", "10", "20.00", poche=Poche.PEA),
                achat("2026-01-06", "2", "100.00", actif=AUTRE_ACTIF, poche=Poche.CTO),
            ]
        )
        source = SourceFixe(
            {
                **cours_constant(ACTIF, "25.00", date(2026, 1, 1), date(2026, 3, 31)),
                **cours_constant(AUTRE_ACTIF, "90.00", date(2026, 1, 1), date(2026, 3, 31)),
            }
        )

        resultat = synthese(portefeuille, Periode(date(2026, 3, 31)), source)

        assert resultat.total.gain == Decimal("30.00")  # +50 - 20
        assert resultat.par_poche[Poche.PEA].gain == Decimal("50.00")
        assert resultat.par_poche[Poche.CTO].gain == Decimal("-20.00")
        assert resultat.par_position[(ACTIF, Poche.PEA)].gain == Decimal("50.00")
        assert resultat.valorisation.total.valeur == Decimal("430.00")
        [en_pea] = [position for position in portefeuille.positions if position.poche is Poche.PEA]
        assert resultat.de(en_pea) is resultat.par_position[(ACTIF, Poche.PEA)]
