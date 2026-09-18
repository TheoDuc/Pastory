"""La configuration « nommer ses comptes » (D-10, D-38).

Elle est écrite et relue par quelqu'un qui ne code pas : une erreur de saisie doit donner un
message clair, et un compte laissé vide doit être traité comme « pas encore fait », pas comme
une panne.
"""

from __future__ import annotations

import pytest

from dashboard_tr.config import comptes
from dashboard_tr.config.comptes import (
    Configuration,
    ConfigurationInvalide,
    RoleCompte,
    charger,
    modele,
)
from dashboard_tr.pivot.operation import Poche


def ecrire(tmp_path, contenu):
    fichier = tmp_path / "comptes.toml"
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


class TestLecture:
    def test_un_fichier_absent_donne_une_configuration_vide(self, tmp_path):
        # Le premier lancement : ce n'est pas une erreur ici. C'est l'export qui refusera
        # d'aller plus loin, avec un message qui dit quoi faire.
        configuration = charger(tmp_path / "rien.toml")
        assert configuration.roles == {}

    def test_les_roles_sont_lus(self, tmp_path):
        fichier = ecrire(
            tmp_path,
            '[comptes]\n"0000000001" = "courant"\n"0000000002" = "pea"\n',
        )
        configuration = charger(fichier)

        assert configuration.role("0000000001") is RoleCompte.COURANT
        assert configuration.role("0000000002") is RoleCompte.PEA
        assert configuration.role("0000000003") is None

    def test_un_compte_laisse_vide_est_un_travail_en_cours(self, tmp_path):
        fichier = ecrire(tmp_path, '[comptes]\n"0000000001" = ""\n')
        assert charger(fichier).roles == {}

    def test_une_correction_de_poche_est_lue(self, tmp_path):
        fichier = ecrire(tmp_path, '[poches]\n"XX0000000001" = "CTO"\n')
        assert charger(fichier).poches_corrigees == {"XX0000000001": Poche.CTO}


class TestMessagesDErreur:
    def test_un_role_inconnu_dit_les_roles_acceptes(self, tmp_path):
        fichier = ecrire(tmp_path, '[comptes]\n"0000000001" = "livret A"\n')

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)
        assert "courant" in str(erreur.value)
        assert "pea" in str(erreur.value)

    def test_une_poche_inconnue_dit_les_poches_acceptees(self, tmp_path):
        fichier = ecrire(tmp_path, '[poches]\n"XX0000000001" = "assurance-vie"\n')

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)
        assert "PEA" in str(erreur.value)

    def test_un_fichier_mal_ecrit_le_dit(self, tmp_path):
        fichier = ecrire(tmp_path, "[comptes\nceci n'est pas du TOML")

        with pytest.raises(ConfigurationInvalide, match="TOML"):
            charger(fichier)


class TestModele:
    def test_le_modele_rappelle_les_operations_vues_sur_chaque_compte(self):
        texte = modele({"0000000001": ["TRADING_SAVINGSPLAN_EXECUTED"]}, Configuration())

        assert "TRADING_SAVINGSPLAN_EXECUTED" in texte
        assert '"0000000001" = ""' in texte

    def test_le_modele_conserve_les_roles_deja_donnes(self):
        texte = modele({"0000000001": []}, Configuration(roles={"0000000001": RoleCompte.PEA}))
        assert '"0000000001" = "pea"' in texte

    def test_le_modele_conserve_les_poches_declarees_a_la_main(self, tmp_path):
        # L'assistant réécrit le fichier entier. S'il ne recopiait que les rôles, relancer
        # « dashboard comptes » effacerait les poches déclarées à la main — et des opérations
        # disparaîtraient du jour au lendemain, sans message.
        depart = Configuration(poches_corrigees={"XX0000000001": Poche.CTO})
        fichier = ecrire(tmp_path, modele({"0000000001": []}, depart))

        assert charger(fichier).poches_corrigees == {"XX0000000001": Poche.CTO}

    def test_le_modele_conserve_un_compte_absent_de_cet_export(self, tmp_path):
        # Un export ne remonte pas forcément toute l'histoire du compte.
        depart = Configuration(roles={"0000000009": RoleCompte.PEA})
        fichier = ecrire(tmp_path, modele({"0000000001": []}, depart))

        assert charger(fichier).role("0000000009") is RoleCompte.PEA

    def test_le_modele_se_relit_tout_seul(self, tmp_path):
        # Ce que l'assistant écrit doit pouvoir être relu sans retouche : sinon l'utilisateur
        # se retrouverait devant un fichier que l'application refuse.
        texte = modele(
            {"0000000001": ["TRADING_TRADE_EXECUTED"], "0000000002": []},
            Configuration(roles={"0000000001": RoleCompte.COURANT}),
        )
        fichier = ecrire(tmp_path, texte)

        configuration = charger(fichier)
        assert configuration.role("0000000001") is RoleCompte.COURANT
        assert configuration.role("0000000002") is None


class TestEmplacement:
    def test_le_fichier_vit_hors_du_dossier_du_projet(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DASHBOARD_TR_DOSSIER", str(tmp_path / "personnel"))
        assert comptes.chemin().name == comptes.NOM_FICHIER
        assert tmp_path in comptes.chemin().parents
