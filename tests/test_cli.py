"""La ligne de commande, de bout en bout, sur un export fictif.

Tous les tests détournent `DASHBOARD_TR_DOSSIER` vers un dossier temporaire : **aucun ne
doit écrire dans le vrai dossier personnel** de la personne qui lance la suite.
"""

from __future__ import annotations

import json

import pytest

from dashboard_tr import cli
from dashboard_tr.adaptateurs.trade_republic import portefeuille as portefeuille_banque
from dashboard_tr.config import comptes as config_comptes
from tests.adaptateurs.trade_republic import evenements_fictifs as fictifs


@pytest.fixture(autouse=True)
def dossier_personnel(tmp_path, monkeypatch):
    """Isole l'application du vrai dossier personnel, pour toute la durée du test."""
    personnel = tmp_path / "personnel"
    monkeypatch.setenv("DASHBOARD_TR_DOSSIER", str(personnel))
    return personnel


def _deposer_export(dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "all_events.json").write_text(
        json.dumps(fictifs.export_complet()), encoding="utf-8"
    )
    return dossier


@pytest.fixture
def export(dossier_personnel):
    """L'export de l'utilisateur, là où l'application le range (D-37)."""
    return _deposer_export(dossier_personnel / "exports")


@pytest.fixture
def export_ailleurs(tmp_path):
    """Un export rangé ailleurs : celui de quelqu'un d'autre, lu avec --export."""
    return _deposer_export(tmp_path / "ailleurs")


def nommer_les_comptes(poches=""):
    fichier = config_comptes.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        "[comptes]\n"
        f'"{fictifs.COMPTE_COURANT}" = "courant"\n'
        f'"{fictifs.COMPTE_PEA}" = "pea"\n'
        f"{poches}",
        encoding="utf-8",
    )


class TestBases:
    def test_la_version_repond(self, capsys):
        with pytest.raises(SystemExit) as sortie:
            cli.main(["--version"])

        assert sortie.value.code == 0
        assert "dashboard" in capsys.readouterr().out

    def test_sans_commande_l_aide_s_affiche(self, capsys):
        assert cli.main([]) == 0
        assert "usage" in capsys.readouterr().out.lower()

    def test_les_emplacements_s_affichent(self, capsys):
        assert cli.main(["emplacements"]) == 0
        affichage = capsys.readouterr().out
        assert "exports" in affichage
        assert "pas encore créé" in affichage

    def test_une_commande_pas_encore_ecrite_dit_a_quelle_etape_elle_arrive(self, capsys):
        assert cli.main(["ouvrir"]) == 1
        assert "étape 9" in capsys.readouterr().err


def deposer_portefeuille_reel(dossier, *lignes: str):
    """Le fichier qu'aurait écrit « dashboard positions-reelles » (valeurs fictives)."""
    fichier = portefeuille_banque.chemin(dossier)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        "\n".join(["Name;ISIN;quantity;price;avgCost;netValue", *lignes]) + "\n",
        encoding="utf-8",
    )
    return fichier


class TestExportIntrouvable:
    @pytest.mark.parametrize("commande", ["lire", "exporter-pivot", "comptes"])
    def test_un_export_absent_dit_quoi_faire(self, commande, capsys):
        assert cli.main([commande]) == cli.CODE_ECHEC

        erreur = capsys.readouterr().err
        assert "all_events.json" in erreur
        assert "rafraichir" in erreur


class TestNommerLesComptes:
    def test_l_assistant_ecrit_un_fichier_a_completer(self, export, capsys):
        assert cli.main(["comptes"]) == 0

        affichage = capsys.readouterr().out
        assert "attendent encore un rôle" in affichage
        assert config_comptes.chemin().exists()

    def test_le_fichier_rappelle_les_operations_vues_sur_chaque_compte(self, export):
        cli.main(["comptes"])

        contenu = config_comptes.chemin().read_text(encoding="utf-8")
        assert "TRADING_SAVINGSPLAN_EXECUTED" in contenu
        assert fictifs.COMPTE_PEA in contenu

    def test_relancer_l_assistant_n_efface_pas_les_poches_declarees(self, export):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        assert cli.main(["lire"]) == 0  # huit opérations, rien ne manque

        cli.main(["comptes"])

        # Sans conservation des poches, l'export repasserait à six opérations et au code 2,
        # sans que rien n'explique ce qui a changé.
        assert cli.main(["lire"]) == 0
        assert config_comptes.charger().poches_corrigees

    def test_un_export_d_un_tiers_n_ecrit_rien(self, export_ailleurs, capsys):
        # Les numéros de compte d'un autre export ne sont pas les siens : les enregistrer
        # dans sa propre configuration serait les recopier (règle 2 de CLAUDE.md).
        assert cli.main(["comptes", "--export", str(export_ailleurs)]) == 0

        assert not config_comptes.chemin().exists()
        assert "Rien n'a été écrit" in capsys.readouterr().out

    def test_une_configuration_fautive_est_expliquee_et_ne_plante_pas(self, export, capsys):
        # C'est la commande censée aider à corriger ce fichier.
        fichier = config_comptes.chemin()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text('[comptes]\n"0000000001" = "livret A"\n', encoding="utf-8")

        assert cli.main(["comptes"]) == cli.CODE_ECHEC
        assert "courant" in capsys.readouterr().err


class TestLire:
    def test_sans_comptes_nommes_la_lecture_demande_de_les_nommer(self, export, capsys):
        code = cli.main(["lire"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "dashboard comptes" in capsys.readouterr().out

    def test_avec_les_comptes_nommes_le_rapport_montre_les_operations(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        code = cli.main(["lire"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Opérations produites : 8" in affichage

    def test_le_rapport_met_en_avant_les_types_inconnus(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        cli.main(["lire"])
        affichage = capsys.readouterr().out

        assert "types inconnus" in affichage
        assert "UN_TYPE_QUE_PERSONNE_N_A_JAMAIS_VU" in affichage

    def test_lire_n_ecrit_aucun_fichier(self, export, dossier_personnel):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        cli.main(["lire"])

        assert not (dossier_personnel / cli.NOM_EXPORT_PIVOT).exists()

    def test_un_export_range_ailleurs_se_lit_avec_export(self, export_ailleurs, capsys):
        # C'est ainsi qu'on regarde l'export de quelqu'un d'autre sans le copier dans le
        # projet : seuls les comptages et les types inconnus comptent alors.
        cli.main(["lire", "--export", str(export_ailleurs)])
        assert "Lecture de 12 événements" in capsys.readouterr().out

    def test_une_configuration_fautive_donne_un_message_clair(self, export, capsys):
        fichier = config_comptes.chemin()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text('[comptes]\n"0000000001" = "livret A"\n', encoding="utf-8")

        assert cli.main(["lire"]) == cli.CODE_ECHEC
        assert "courant" in capsys.readouterr().err


class TestExporterPivot:
    def test_le_csv_est_ecrit_dans_le_dossier_personnel(
        self, export, dossier_personnel, capsys
    ):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        code = cli.main(["exporter-pivot"])
        fichier = dossier_personnel / cli.NOM_EXPORT_PIVOT

        assert code == 0
        assert fichier.exists()
        assert "opération(s) écrite(s)" in capsys.readouterr().out

    def test_rien_n_est_ecrit_tant_qu_il_manque_une_declaration(
        self, export, dossier_personnel, capsys
    ):
        # Un fichier incomplet ressemblerait à un fichier complet (D-40).
        code = cli.main(["exporter-pivot"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert not (dossier_personnel / cli.NOM_EXPORT_PIVOT).exists()
        assert "Aucun fichier n'a été écrit" in capsys.readouterr().err

    def test_le_csv_contient_une_ligne_par_operation(self, export, dossier_personnel):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        cli.main(["exporter-pivot"])

        lignes = (dossier_personnel / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        ).strip().splitlines()
        assert len(lignes) == 9  # huit opérations, plus l'en-tête


class TestPositions:
    def test_le_rapport_montre_les_positions_par_poche(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        code = cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Positions détenues" in affichage
        # Cinq parts restent sur l'action du PEA : dix achetées, cinq vendues.
        assert fictifs.ACTIF_ACTION in affichage
        assert "PEA" in affichage and "crypto" in affichage

    def test_le_rapport_previent_qu_un_type_est_inconnu(self, export, capsys):
        # L'export fictif en contient un : aucun chiffre ne peut être tenu pour complet
        # tant qu'on ne l'a pas examiné (règle 5 de CLAUDE.md).
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "type inconnu" in affichage
        assert "dashboard lire" in affichage

    def test_les_actions_gratuites_sont_comptees_mais_sans_prix(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "histoire est incomplète" in affichage
        assert "prix à compléter" in affichage

    def test_sans_portefeuille_reel_le_rapport_dit_comment_l_obtenir(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        cli.main(["positions"])

        assert "positions-reelles" in capsys.readouterr().out

    def test_le_portefeuille_reel_est_rapproche_des_que_le_fichier_existe(
        self, export, capsys
    ):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        deposer_portefeuille_reel(export, f"Action Exemple SA;{fictifs.ACTIF_ACTION};5;40;20;200")

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "Rapprochement avec le portefeuille réel" in affichage
        assert "titres sans opération" in affichage or "parts non confirmées" in affichage

    def test_positions_n_ecrit_aucun_fichier(self, export, dossier_personnel):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        cli.main(["positions"])

        assert not (dossier_personnel / "positions.csv").exists()

    def test_au_arrete_les_chiffres_a_la_date_demandee(self, export, capsys):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        code = cli.main(["positions", "--au", "2026-01-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Chiffres arrêtés au 2026-01-31" in affichage
        # Seul le plan d'épargne du 2 janvier a eu lieu : l'action du PEA n'existe pas.
        assert fictifs.ACTIF_ACTION not in affichage

    def test_une_date_mal_ecrite_explique_comment_l_ecrire(self, export, capsys):
        with pytest.raises(SystemExit):
            cli.main(["positions", "--au", "31/01/2026"])

        assert "2026-03-15" in capsys.readouterr().err

    def test_sans_comptes_nommes_aucun_chiffre_n_est_calcule(self, export, capsys):
        code = cli.main(["positions"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "Aucun chiffre n'a été calculé" in capsys.readouterr().err


class TestExporterPositions:
    def test_les_deux_fichiers_sont_ecrits_dans_le_dossier_personnel(
        self, export, dossier_personnel, capsys
    ):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')

        code = cli.main(["exporter-positions"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert (dossier_personnel / "positions.csv").exists()
        assert (dossier_personnel / "journal.csv").exists()
        assert "ligne(s) de journal" in affichage

    def test_le_journal_a_une_ligne_par_operation(self, export, dossier_personnel):
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        cli.main(["exporter-positions"])

        lignes = (
            (dossier_personnel / "journal.csv")
            .read_text(encoding="utf-8-sig")
            .strip()
            .splitlines()
        )
        assert len(lignes) == 9  # huit opérations, plus l'en-tête

    def test_rien_n_est_ecrit_tant_qu_il_manque_une_declaration(
        self, export, dossier_personnel
    ):
        assert cli.main(["exporter-positions"]) == cli.CODE_DECLARATION_ATTENDUE
        assert not (dossier_personnel / "positions.csv").exists()


class TestPositionsReelles:
    def test_la_commande_previent_avant_de_demander_le_pin(self, monkeypatch, capsys):
        appels = []

        def faux_pytr(fichier, executable=None):
            appels.append(fichier)
            fichier.parent.mkdir(parents=True, exist_ok=True)
            fichier.write_text(
                "Name;ISIN;quantity;price;avgCost;netValue\n"
                f"Action Exemple SA;{fictifs.ACTIF_ACTION};5;40;20;200\n",
                encoding="utf-8",
            )
            return 0

        monkeypatch.setattr(cli.source, "recuperer_portefeuille", faux_pytr)

        code = cli.main(["positions-reelles"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert len(appels) == 1
        assert "vous ne verrez RIEN s'afficher" in affichage
        assert "1 position(s) enregistrée(s)" in affichage

    def test_un_echec_de_pytr_ne_touche_pas_le_fichier_precedent(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.source, "recuperer_portefeuille", lambda *_, **__: 1)

        assert cli.main(["positions-reelles"]) == cli.CODE_ECHEC
        assert "n'a pas été touché" in capsys.readouterr().err
