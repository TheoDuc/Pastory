"""La date du premier versement du PEA : déclarée, jamais devinée (D-59)."""

from __future__ import annotations

from datetime import date

import pytest

from pastory.config import ConfigurationInvalide
from pastory.config.fiscalite import MODELE, charger


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
