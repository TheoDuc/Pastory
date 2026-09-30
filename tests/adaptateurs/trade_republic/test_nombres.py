"""Lecture des nombres localisés.

Le premier test est celui qui a motivé tout le module : **la même suite de caractères ne
veut pas dire la même chose selon l'endroit où Trade Republic l'écrit.** Le reste vérifie
qu'aucune écriture douteuse ne reçoit une valeur de repli.

Valeurs entièrement fictives (D-03).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pastory.adaptateurs.trade_republic.nombres import (
    Convention,
    LectureImpossible,
    lire_nombre,
)


class TestLePiegeDuSeparateurDecimal:
    """« 1.234567 » vaut 1 234 567 parts ou 1,234567 part selon la convention.

    Un même export contient les deux écritures : les quantités des ordres utilisent la
    virgule décimale, celles des dividendes le point décimal.
    """

    def test_le_point_decimal_donne_une_fraction_de_part(self):
        lu = lire_nombre("1.234567", Convention.POINT_DECIMAL)
        assert lu.valeur == Decimal("1.234567")
        assert lu.decimales == 6

    def test_la_meme_ecriture_est_refusee_en_convention_virgule(self):
        # Si elle était acceptée, elle donnerait 1 234 567 parts : un million de fois trop.
        # Le lecteur refuse plutôt que de choisir.
        with pytest.raises(LectureImpossible) as echec:
            lire_nombre("1.234567", Convention.VIRGULE_DECIMALE)
        assert "milliers" in echec.value.raison

    def test_un_vrai_separateur_de_milliers_reste_lisible(self):
        assert lire_nombre("1.234,56 €", Convention.VIRGULE_DECIMALE).valeur == Decimal("1234.56")


class TestConventionVirguleDecimale:
    """``1.234,56 €`` : virgule décimale, point ou espace pour les milliers."""

    @pytest.mark.parametrize(
        ("texte", "attendu"),
        [
            ("25,00 €", Decimal("25.00")),
            ("0,123456", Decimal("0.123456")),
            ("1.234.567,89 €", Decimal("1234567.89")),
            ("1 234,56 €", Decimal("1234.56")),  # séparateur en espace (libellés français)
            ("1 234,56 €", Decimal("1234.56")),  # espace insécable
            ("12", Decimal("12")),
        ],
    )
    def test_ecritures_acceptees(self, texte, attendu):
        assert lire_nombre(texte, Convention.VIRGULE_DECIMALE).valeur == attendu

    @pytest.mark.parametrize(
        "texte",
        [
            "1.23",  # groupe de milliers incomplet
            "1.2345",  # groupe de milliers de quatre chiffres
            "12,34,56",  # deux virgules
            "Kostenlos",  # un mot, pas un nombre
            "",
        ],
    )
    def test_ecritures_refusees(self, texte):
        with pytest.raises(LectureImpossible):
            lire_nombre(texte, Convention.VIRGULE_DECIMALE)


class TestConventionPointDecimal:
    """``1.234567`` : point décimal, aucun séparateur de milliers."""

    def test_un_entier_est_lu_sans_decimale(self):
        lu = lire_nombre("12", Convention.POINT_DECIMAL)
        assert (lu.valeur, lu.decimales) == (Decimal("12"), 0)

    @pytest.mark.parametrize("texte", ["1,5", "1 234.5", "1.2.3"])
    def test_une_ecriture_ambigue_est_refusee(self, texte):
        with pytest.raises(LectureImpossible):
            lire_nombre(texte, Convention.POINT_DECIMAL)


class TestSigneEtDevise:
    def test_la_taxe_affichee_negative_garde_son_signe(self):
        # `Steuer` est affiché avec un moins ; c'est à l'appelant de le retirer,
        # explicitement, parce que le pivot n'accepte aucun nombre négatif.
        assert lire_nombre("-1,50 €", Convention.VIRGULE_DECIMALE).valeur == Decimal("-1.50")

    def test_le_signe_moins_typographique_est_reconnu(self):
        assert lire_nombre("−1,50 €", Convention.VIRGULE_DECIMALE).valeur == Decimal("-1.50")

    def test_absolu_retire_le_signe_sans_toucher_a_la_precision(self):
        lu = lire_nombre("-1,50 €", Convention.VIRGULE_DECIMALE).absolu()
        assert (lu.valeur, lu.decimales, lu.devise) == (Decimal("1.50"), 2, "EUR")

    @pytest.mark.parametrize(
        ("texte", "devise"),
        [("25,00 €", "EUR"), ("0,43 $", "USD"), ("12,00", None)],
    )
    def test_la_devise_lue_est_conservee(self, texte, devise):
        # Elle sert à **refuser** une valeur qui n'est pas en euros, jamais à convertir.
        assert lire_nombre(texte, Convention.VIRGULE_DECIMALE).devise == devise


class TestPrecisionAffichee:
    """Le nombre de décimales affichées nourrit la tolérance des contrôles (D-39)."""

    @pytest.mark.parametrize(
        ("texte", "decimales", "demi_dernier_chiffre"),
        [
            ("25", 0, Decimal("0.5")),
            ("25,00 €", 2, Decimal("0.005")),
            ("25,0000 €", 4, Decimal("0.00005")),
        ],
    )
    def test_le_dernier_chiffre_affiche_donne_l_arrondi(
        self, texte, decimales, demi_dernier_chiffre
    ):
        lu = lire_nombre(texte, Convention.VIRGULE_DECIMALE)
        assert lu.decimales == decimales
        assert lu.demi_dernier_chiffre == demi_dernier_chiffre

    def test_deux_prix_de_meme_valeur_mais_d_ecriture_differente_n_ont_pas_le_meme_arrondi(self):
        # « 25,00 » et « 25,0000 » valent pareil, mais le second est cent fois plus précis.
        court = lire_nombre("25,00 €", Convention.VIRGULE_DECIMALE)
        long = lire_nombre("25,0000 €", Convention.VIRGULE_DECIMALE)
        assert court.valeur == long.valeur
        assert court.demi_dernier_chiffre > long.demi_dernier_chiffre


class TestValeurNonTextuelle:
    @pytest.mark.parametrize("valeur", [None, 25, {"text": "25,00 €"}])
    def test_une_valeur_qui_n_est_pas_un_texte_est_refusee(self, valeur):
        with pytest.raises(LectureImpossible):
            lire_nombre(valeur, Convention.VIRGULE_DECIMALE)
