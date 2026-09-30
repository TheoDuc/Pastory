"""Les fichiers de paramètres : un taux sans date ni source n'est pas un taux (D-58)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pastory.parametres import ParametresInvalides, couts, fiscalite
from pastory.parametres.lecture import Parametre, charger

COMPLET = """\
[impots.taux]
valeur = 18.6
unite = "pour cent"
en_vigueur_depuis = 2026-01-01
source = "CSS L. 136-8"
verifie_le = 2026-09-27
note = "une note"
"""


def ecrire(tmp_path, contenu):
    fichier = tmp_path / "parametres.toml"
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


class TestLecture:
    def test_un_parametre_complet_est_lu_avec_son_nom_en_pointille(self, tmp_path):
        parametres = charger(ecrire(tmp_path, COMPLET))

        parametre = parametres["impots.taux"]
        assert parametre.valeur == Decimal("18.6")
        assert parametre.unite == "pour cent"
        assert parametre.en_vigueur_depuis == date(2026, 1, 1)
        assert parametre.source == "CSS L. 136-8"
        assert parametre.note == "une note"

    def test_la_valeur_passe_par_le_texte_jamais_par_le_flottant(self, tmp_path):
        """D-33 : `Decimal(18.6)` ferait 18,600000000000001421…"""
        parametre = charger(ecrire(tmp_path, COMPLET))["impots.taux"]
        assert str(parametre.valeur) == "18.6"

    def test_une_fourchette_est_lue(self, tmp_path):
        contenu = COMPLET.replace("valeur = 18.6", "valeur = 0.05\nbasse = 0.01\nhaute = 0.15")
        parametre = charger(ecrire(tmp_path, contenu))["impots.taux"]
        assert (parametre.basse, parametre.haute) == (Decimal("0.01"), Decimal("0.15"))

    @pytest.mark.parametrize(
        "ligne_retiree, mot",
        [
            ("source", "source"),
            ("en_vigueur_depuis", "en_vigueur_depuis"),
            ("verifie_le", "verifie_le"),
            ("unite", "unité"),
        ],
    )
    def test_un_parametre_sans_date_ou_sans_source_est_refuse(self, tmp_path, ligne_retiree, mot):
        contenu = "\n".join(
            ligne for ligne in COMPLET.splitlines() if not ligne.startswith(ligne_retiree)
        )
        with pytest.raises(ParametresInvalides, match=mot):
            charger(ecrire(tmp_path, contenu))

    def test_une_date_entre_guillemets_est_refusee(self, tmp_path):
        contenu = COMPLET.replace("2026-01-01", '"2026-01-01"')
        with pytest.raises(ParametresInvalides, match="AAAA-MM-JJ"):
            charger(ecrire(tmp_path, contenu))

    def test_un_taux_au_dela_de_cent_pour_cent_est_refuse(self, tmp_path):
        with pytest.raises(ParametresInvalides, match="entre 0 et 100"):
            charger(ecrire(tmp_path, COMPLET.replace("18.6", "186")))

    def test_une_valeur_hors_de_sa_fourchette_est_refusee(self, tmp_path):
        contenu = COMPLET.replace("valeur = 18.6", "valeur = 0.50\nbasse = 0.01\nhaute = 0.15")
        with pytest.raises(ParametresInvalides, match="fourchette"):
            charger(ecrire(tmp_path, contenu))

    def test_une_fourchette_a_deux_bornes(self, tmp_path):
        contenu = COMPLET.replace("valeur = 18.6", "valeur = 0.05\nbasse = 0.01")
        with pytest.raises(ParametresInvalides, match="deux"):
            charger(ecrire(tmp_path, contenu))

    def test_un_fichier_absent_est_une_erreur(self, tmp_path):
        with pytest.raises(ParametresInvalides, match="introuvable"):
            charger(tmp_path / "rien.toml")

    def test_un_fichier_sans_parametre_est_une_erreur(self, tmp_path):
        with pytest.raises(ParametresInvalides, match="aucun paramètre"):
            charger(ecrire(tmp_path, "[impots]\nnom = 'x'\n"))

    def test_le_parametre_s_ecrit_en_clair(self):
        assert _parametre("18.6", "pour cent").en_clair == "18,6 %"
        assert _parametre("1.00", "euros").en_clair == "1,00 €"
        assert _parametre("5", "ans").en_clair == "5 ans"


def _parametre(valeur, unite):
    return Parametre(
        nom="x", valeur=Decimal(valeur), unite=unite, source="s", en_vigueur_depuis=date(2026, 1, 1)
    )


class TestLesFichiersLivres:
    """Les deux fichiers du dépôt doivent se lire tels quels : c'est eux qui servent."""

    def test_les_regles_fiscales_se_chargent(self):
        regles = fiscalite.charger()

        assert regles.impot_sur_le_revenu.valeur == Decimal("12.8")
        assert regles.prelevements_sociaux.valeur == Decimal("18.6")
        assert regles.pea_duree_exoneration_ir.valeur == Decimal("5")
        assert regles.crypto_seuil_exoneration.valeur == Decimal("305")
        assert regles.pea_premier_versement is None
        for parametre in (regles.impot_sur_le_revenu, regles.prelevements_sociaux):
            assert "legifrance" in parametre.source

    def test_la_date_du_pea_est_portee_par_les_regles(self):
        regles = fiscalite.charger(premier_versement_pea=date(2024, 3, 15))
        assert regles.pea_premier_versement == date(2024, 3, 15)

    def test_le_bareme_des_couts_se_charge(self):
        bareme = couts.charger()

        assert bareme.frais_par_ordre["titres"].valeur == Decimal("1.00")
        assert bareme.frais_par_ordre["plan"].valeur == Decimal("0.00")
        assert bareme.spread_par_cote["etf"].valeur == Decimal("0.05")
        assert bareme.spread_par_cote["crypto"].haute == Decimal("1.50")

    def test_un_bareme_incomplet_est_refuse(self, tmp_path):
        fichier = ecrire(
            tmp_path,
            COMPLET.replace("[impots.taux]", "[frais_par_ordre.titres]").replace(
                "pour cent", "euros"
            ),
        )
        with pytest.raises(ParametresInvalides, match="manquant"):
            couts.charger(fichier)

    def test_des_regles_fiscales_incompletes_sont_refusees(self, tmp_path):
        with pytest.raises(ParametresInvalides, match="manquant"):
            fiscalite.charger(ecrire(tmp_path, COMPLET))


def test_un_montant_en_euros_s_ecrit_au_centime():
    """TOML lit « 1.00 » comme un flottant, qui perd son second zéro : « 1,0 € » se lit mal."""
    assert _parametre("1.0", "euros").en_clair == "1,00 €"


def test_un_taux_garde_l_ecriture_de_la_loi():
    """18,6 % est le chiffre du texte : on ne lui ajoute pas une décimale."""
    assert _parametre("18.6", "pour cent").en_clair == "18,6 %"
