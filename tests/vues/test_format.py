"""La mise en forme des chiffres à l'écran (conception-interface §3)."""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

import pytest

from pastory.vues import format as f

NBSP = " "
FINE = " "


class TestLePiegeDesPourCent:
    """Le défaut de l'étape 7 : « 6264,00 % » au lieu de 62,64 %."""

    def test_un_taux_est_une_fraction(self):
        assert f.taux(Decimal("0.6264")) == f"+62,64{NBSP}%"

    def test_un_pour_cent_est_deja_calcule(self):
        assert f.pour_cent(Decimal("62.64")) == f"62,64{NBSP}%"

    def test_les_deux_ecritures_d_une_meme_part_concordent(self):
        assert f.taux(Decimal("0.6264"), signe=False) == f.pour_cent(Decimal("62.64"))


class TestMontant:
    def test_milliers_et_unite_insecables(self):
        assert f.montant(Decimal("1234.56")) == f"1{FINE}234,56{NBSP}€"

    def test_deux_decimales_arrondies_comme_a_la_main(self):
        assert f.montant(Decimal("0.125")) == f"0,13{NBSP}€"
        assert f.montant(Decimal("0.135")) == f"0,14{NBSP}€"

    def test_grand_montant(self):
        assert f.montant(Decimal("1234567")) == f"1{FINE}234{FINE}567,00{NBSP}€"

    def test_negatif_avec_le_vrai_signe_moins(self):
        assert f.montant(Decimal("-18.9")) == f"−18,90{NBSP}€"

    def test_absent_n_est_jamais_zero(self):
        assert f.montant(None) == "–"

    def test_une_autre_devise_est_ecrite_jamais_convertie(self):
        assert f.montant(Decimal("12"), "USD") == f"12,00{NBSP}USD"


class TestSigne:
    def test_le_signe_se_lit_avant_la_couleur(self):
        assert f.montant_signe(Decimal("132.4")) == f"+132,40{NBSP}€"
        assert f.montant_signe(Decimal("-18.9")) == f"−18,90{NBSP}€"

    def test_zero_n_a_pas_de_signe_ni_de_couleur(self):
        assert f.montant_signe(Decimal("0.001")) == f"0,00{NBSP}€"
        assert f.classe_du_signe(Decimal("0.001")) == ""

    def test_couleur(self):
        assert f.classe_du_signe(Decimal("3")) == "gain"
        assert f.classe_du_signe(Decimal("-3")) == "perte"
        assert f.classe_du_signe(None) == ""

    def test_un_petit_taux_garde_sa_couleur(self):
        # 0,004 = +0,40 % : arrondie au centième comme un montant, la fraction vaudrait 0,00.
        assert f.taux(Decimal("0.004")) == f"+0,40{NBSP}%"
        assert f.classe_du_taux(Decimal("0.004")) == "gain"

    def test_un_poids_n_a_pas_de_signe(self):
        assert f.taux(Decimal("0.04"), signe=False) == f"4,00{NBSP}%"


class TestQuantite:
    @pytest.mark.parametrize(
        ("valeur", "attendu"),
        [
            (Decimal("3"), "3,00"),
            (Decimal("12.5"), "12,50"),
            (Decimal("0.004521"), "0,004521"),
            (Decimal("0.12345678"), "0,123457"),
            (Decimal("1500"), f"1{FINE}500,00"),
        ],
    )
    def test_deux_a_six_decimales(self, valeur, attendu):
        assert f.quantite(valeur) == attendu


class TestDates:
    def test_date_courte(self):
        assert f.date_courte(Date(2026, 9, 5)) == "05/09/2026"

    @pytest.mark.parametrize(
        ("jours", "attendu"),
        [(1, "1 jour"), (12, "12 jours"), (183, "6 mois"), (567, "19 mois"),
         (800, "2 ans et 2 mois"), (730, "2 ans")],
    )
    def test_duree(self, jours, attendu):
        assert f.duree_en_clair(jours) == attendu


def test_montant_entier_pour_les_axes():
    assert f.montant_entier(Decimal("12345.67")) == f"12{FINE}346{NBSP}€"
