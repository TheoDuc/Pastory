"""La date du premier versement du PEA : déclarée, jamais devinée (D-59)."""

from __future__ import annotations

from datetime import date

import pytest

from pastory.config import ConfigurationInvalide
from pastory.config.fiscalite import MODELE, CorrectionDuPea, charger


def ecrire(tmp_path, contenu):
    fichier = tmp_path / "fiscalite.toml"
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


def test_un_fichier_absent_donne_une_configuration_vide(tmp_path):
    assert charger(tmp_path / "rien.toml").premier_versement_pea is None


def test_la_date_est_lue(tmp_path):
    fichier = ecrire(tmp_path, "[pea]\npremier_versement = 2024-03-15\n")
    assert charger(fichier).premier_versement_pea == date(2024, 3, 15)


def test_une_date_entre_guillemets_est_expliquee(tmp_path):
    fichier = ecrire(tmp_path, '[pea]\npremier_versement = "2024-03-15"\n')
    with pytest.raises(ConfigurationInvalide, match="sans guillemets"):
        charger(fichier)


def test_une_date_laissee_vide_est_un_travail_en_cours(tmp_path):
    fichier = ecrire(tmp_path, '[pea]\npremier_versement = ""\n')
    assert charger(fichier).premier_versement_pea is None


def test_une_date_dans_le_futur_est_refusee(tmp_path):
    fichier = ecrire(tmp_path, "[pea]\npremier_versement = 2999-01-01\n")
    with pytest.raises(ConfigurationInvalide, match="futur"):
        charger(fichier)


def test_le_modele_explique_ce_qu_il_faut_ecrire():
    # Le modèle tel quel n'est pas un TOML valide (AAAA-MM-JJ est à remplacer), et c'est
    # voulu : une valeur d'exemple passerait pour une vraie date.
    assert "premier_versement = AAAA-MM-JJ" in MODELE
    assert "5 ans" in MODELE


def test_une_date_avec_une_heure_est_expliquee_sans_trace(tmp_path):
    """Trouvé à la relecture : TOML accepte « 2024-03-15T00:00:00 », et pour Python un
    `datetime` est un `date`. La comparaison avec aujourd'hui levait alors une exception
    technique, et la commande affichait une trace au lieu du message."""
    fichier = ecrire(tmp_path, "[pea]\npremier_versement = 2024-03-15T00:00:00\n")

    with pytest.raises(ConfigurationInvalide, match="sans heure"):
        charger(fichier)


def test_le_message_donne_la_date_a_ecrire(tmp_path):
    fichier = ecrire(tmp_path, "[pea]\npremier_versement = 2024-03-15T10:30:00\n")

    with pytest.raises(ConfigurationInvalide, match="2024-03-15"):
        charger(fichier)


class TestParPortefeuille:
    """L'ancienneté d'un PEA est celle d'une personne (D-109) : une date corrigée à la main ne
    s'applique jamais au portefeuille d'une autre."""

    LA_MIENNE = date(2021, 3, 1)
    CELLE_DE_CAMILLE = date(2019, 6, 15)

    def configuration(self, tmp_path, contenu):
        return charger(ecrire(tmp_path, contenu))

    def test_une_date_peut_viser_un_portefeuille(self, tmp_path):
        fiscale = self.configuration(
            tmp_path,
            "[pea]\npremier_versement = 2021-03-01\n\n"
            '[portefeuille."Camille".pea]\npremier_versement = 2019-06-15\n',
        )
        assert fiscale.premier_versement_pea == self.LA_MIENNE
        assert dict(fiscale.par_portefeuille) == {"Camille": self.CELLE_DE_CAMILLE}

    def test_seul_la_date_sans_nom_s_applique_comme_avant(self, tmp_path):
        fiscale = self.configuration(tmp_path, "[pea]\npremier_versement = 2021-03-01\n")
        correction = fiscale.pour("Exportation de transactions")
        assert (correction.date, correction.ecartees) == (self.LA_MIENNE, ())

    def test_a_plusieurs_la_date_sans_nom_n_est_appliquee_a_aucun(self, tmp_path):
        """Le cas qui donnerait un impôt faux sans rien dire : ma date, sur le PEA d'un proche."""
        fiscale = self.configuration(tmp_path, "[pea]\npremier_versement = 2021-03-01\n")
        for ouvert, autre in (("Alix", "Camille"), ("Camille", "Alix")):
            correction = fiscale.pour(ouvert, [autre])
            assert correction.date is None
            (raison,) = correction.ecartees
            assert "sans dire pour quel portefeuille" in raison
            assert f'[portefeuille."{ouvert}".pea]' in raison

    def test_la_date_d_un_portefeuille_ne_sert_qu_a_lui(self, tmp_path):
        fiscale = self.configuration(
            tmp_path, '[portefeuille."Camille".pea]\npremier_versement = 2019-06-15\n'
        )
        assert fiscale.pour("Camille", ["Alix"]) == CorrectionDuPea(self.CELLE_DE_CAMILLE)
        assert fiscale.pour("camille", ["Alix"]).date == self.CELLE_DE_CAMILLE
        assert fiscale.pour("Alix", ["Camille"]) == CorrectionDuPea(None)

    def test_la_date_nommee_l_emporte_sur_la_date_sans_nom(self, tmp_path):
        fiscale = self.configuration(
            tmp_path,
            "[pea]\npremier_versement = 2021-03-01\n\n"
            '[portefeuille."Camille".pea]\npremier_versement = 2019-06-15\n',
        )
        assert fiscale.pour("Camille", ["Alix"]).date == self.CELLE_DE_CAMILLE

    def test_une_date_pour_un_portefeuille_disparu_est_signalee_jamais_reportee(self, tmp_path):
        fiscale = self.configuration(
            tmp_path, '[portefeuille."Ancien nom".pea]\npremier_versement = 2019-06-15\n'
        )
        correction = fiscale.pour("Camille", ["Alix"])
        assert correction.date is None
        (raison,) = correction.ecartees
        assert "« Ancien nom », qui n'existe pas" in raison

    def test_rien_de_tout_cela_ne_vaut_pour_l_export_d_un_tiers(self, tmp_path):
        fiscale = self.configuration(
            tmp_path,
            "[pea]\npremier_versement = 2021-03-01\n\n"
            '[portefeuille."Camille".pea]\npremier_versement = 2019-06-15\n',
        )
        correction = fiscale.pour("Camille", tiers=True)
        assert correction.date is None
        (raison,) = correction.ecartees
        assert "ne s'applique pas à l'export d'un tiers" in raison

    def test_une_date_mal_ecrite_pour_un_portefeuille_dit_ou(self, tmp_path):
        fichier = ecrire(tmp_path, '[portefeuille."Camille".pea]\npremier_versement = "hier"\n')
        with pytest.raises(ConfigurationInvalide, match="AAAA-MM-JJ"):
            charger(fichier)

    def test_le_modele_montre_la_forme_par_portefeuille(self):
        assert '[portefeuille."Camille".pea]' in MODELE
