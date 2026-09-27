"""La ligne de commande, de bout en bout, sur un export fictif.

Tous les tests détournent `DASHBOARD_TR_DOSSIER` vers un dossier temporaire : **aucun ne
doit écrire dans le vrai dossier personnel** de la personne qui lance la suite.
"""

from __future__ import annotations

import json
from datetime import date as Date
from decimal import Decimal

import pytest

from dashboard_tr import cli, tableur
from dashboard_tr.adaptateurs.trade_republic import portefeuille as portefeuille_banque
from dashboard_tr.config import actifs as config_actifs
from dashboard_tr.config import comptes as config_comptes
from dashboard_tr.config import emplacements
from dashboard_tr.config.actifs import Proposition
from dashboard_tr.donnees_externes.cache import Cache
from dashboard_tr.donnees_externes.cours import Cours
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
        # La photo montre l'actif du PEA et un des actifs du CTO : la crypto, elle,
        # n'apparaît nulle part, donc sa poche n'est pas couverte.
        deposer_portefeuille_reel(
            export,
            f"Action Exemple SA;{fictifs.ACTIF_ACTION};5;40;20;200",
            f"ETF Exemple Monde;{fictifs.ACTIF_ETF};2;25;25;50",
        )

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "Rapprochement avec le portefeuille réel" in affichage
        assert "parts non confirmées" in affichage  # les actions gratuites du CTO

    def test_une_poche_entierement_absente_de_la_photo_ne_leve_qu_une_ligne(
        self, export, capsys
    ):
        # Le cas rencontré sur de vraies données : pytr ne demande les positions que d'un
        # seul compte-titres, et le PEA est dans un autre (D-47).
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        deposer_portefeuille_reel(
            export,
            f"ETF Exemple Monde;{fictifs.ACTIF_ETF};2;25;25;50",
            f"Action Exemple B;{fictifs.ACTIF_ACTION_B};5;10;10;50",
            f"Crypto Exemple;{fictifs.ACTIF_CRYPTO};0.000833;30000;30000;25",
        )

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "ne couvre pas : PEA" in affichage
        assert "hors périmètre" in affichage
        # L'actif du PEA ne doit plus produire d'alerte individuelle.
        assert "parts non confirmées" not in affichage

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

    def test_a_une_date_passee_le_portefeuille_actuel_n_est_pas_rapproche(
        self, export, capsys
    ):
        # La banque ne sait montrer qu'aujourd'hui : comparer une photo d'aujourd'hui à des
        # chiffres arrêtés en janvier signalerait à tort tout ce qui a bougé depuis.
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        deposer_portefeuille_reel(export, f"Action Exemple SA;{fictifs.ACTIF_ACTION};5;40;20;200")

        cli.main(["positions", "--au", "2026-01-31"])
        affichage = capsys.readouterr().out

        assert "Sans objet" in affichage
        assert "absent du moteur" not in affichage

    def test_un_evenement_traite_sans_operation_declenche_l_avertissement(
        self, export, capsys, monkeypatch
    ):
        # Un événement traité dont aucune opération n'est sortie est un trou franc dans les
        # totaux : rien d'autre que cette bannière ne le dirait.
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        lecture_reelle = cli.Lecteur.lire

        def lecture_avec_un_refus(self, bruts):
            rapport = lecture_reelle(self, bruts)
            rapport.operations_non_produites += 1
            return rapport

        monkeypatch.setattr(cli.Lecteur, "lire", lecture_avec_un_refus)

        cli.main(["positions"])

        assert "sans opération produite" in capsys.readouterr().out

    def test_un_fichier_de_banque_abime_empeche_de_conclure(self, export, capsys):
        # Sinon l'actif de la ligne illisible ressortirait « absent de la banque », ce qui
        # est un faux diagnostic : c'est le fichier qui est abîmé.
        nommer_les_comptes(f'\n[poches]\n"{fictifs.ACTIF_ACTION_B}" = "CTO"\n')
        deposer_portefeuille_reel(
            export,
            f"Action Exemple SA;{fictifs.ACTIF_ACTION};5;40;20;200",
            "Ligne Cassee;;;;;",
        )

        cli.main(["positions"])
        sortie = capsys.readouterr()

        assert "n'ont pas pu être lues" in sortie.out
        assert "portefeuille réel" in sortie.err

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


# --- Étape 4 : les cours de marché -----------------------------------------------------

POCHE_CORRIGEE = '\n[poches]\n"XX0000000004" = "CTO"\n'
"""La correction de poche que l'export fictif réclame, écrite une fois pour toutes."""


def declarer_les_actifs(*actifs: str) -> None:
    """Le fichier qu'aurait laissé « dashboard actifs » après relecture (valeurs fictives)."""
    fichier = config_actifs.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    lignes = ["[actifs]"] + [
        f'"{actif}" = {{ ticker = "T{numero}.DE", devise = "EUR" }}'
        for numero, actif in enumerate(actifs, start=1)
    ]
    fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def deposer_un_cours(actif: str, jour: Date, valeur: str) -> None:
    """Écrit un cours dans le cache, comme si la source l'avait déjà donné."""
    Cache().ecrire(
        actif,
        [
            Cours(
                actif=actif,
                date=jour,
                valeur=Decimal(valeur),
                devise="EUR",
                place="XETRA",
                source="Source de test",
                recupere_le=Date(2026, 9, 26),
                ticker="T1.DE",
            )
        ],
    )


class FauxYahoo:
    """Une source qui ne sort pas de la machine. Aucun test n'appelle le vrai service."""

    nom = "Source de test"

    def __init__(self, propositions=None, series=None):
        self._propositions = propositions or {}
        self._series = series or {}

    def chercher(self, actif):
        return self._propositions.get(actif)

    def serie(self, actif, declaration, debut, fin):
        return [
            Cours(
                actif=actif,
                date=jour,
                valeur=Decimal(valeur),
                devise="EUR",
                place="XETRA",
                source=self.nom,
                recupere_le=Date(2026, 9, 26),
                ticker=declaration.ticker,
            )
            for jour, valeur in self._series.get(actif, [])
            if debut <= jour <= fin
        ]


def brancher(monkeypatch, faux):
    """Remplace la source Yahoo par une fausse, partout où le CLI la construit."""
    monkeypatch.setattr(cli, "Yahoo", lambda *args, **kwargs: faux)


class TestDeclarerLesActifs:
    def test_l_assistant_ecrit_un_fichier_a_completer(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)

        code = cli.main(["actifs", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "sans correspondance" in affichage
        assert "attendent votre validation" in affichage
        contenu = config_actifs.chemin().read_text(encoding="utf-8")
        assert fictifs.ACTIF_ETF in contenu
        assert fictifs.ACTIF_CRYPTO in contenu

    def test_le_fichier_rappelle_les_poches_de_chaque_actif(self, export):
        nommer_les_comptes(POCHE_CORRIGEE)

        cli.main(["actifs", "--hors-ligne"])

        contenu = config_actifs.chemin().read_text(encoding="utf-8")
        assert "PEA" in contenu
        assert "crypto" in contenu

    def test_une_proposition_en_euros_est_ecrite_telle_quelle(
        self, export, monkeypatch, capsys
    ):
        nommer_les_comptes(POCHE_CORRIGEE)
        brancher(
            monkeypatch,
            FauxYahoo(
                propositions={
                    fictifs.ACTIF_ETF: Proposition("AAAA.DE", "XETRA", "EUR", "ETF Exemple")
                }
            ),
        )

        cli.main(["actifs"])

        contenu = config_actifs.chemin().read_text(encoding="utf-8")
        assert '{ ticker = "AAAA.DE", devise = "EUR" }' in contenu
        assert "proposé : AAAA.DE" in capsys.readouterr().out

    def test_une_proposition_en_dollars_est_signalee_et_reste_inactive(
        self, export, monkeypatch, capsys
    ):
        # Le piège de D-48 : la cotation londonienne en dollars d'un ETF qui cote aussi en
        # euros. Elle doit être visible et **pas** utilisable par inadvertance.
        nommer_les_comptes(POCHE_CORRIGEE)
        brancher(
            monkeypatch,
            FauxYahoo(
                propositions={fictifs.ACTIF_ETF: Proposition("BBBB.L", "London", "USD")}
            ),
        )

        cli.main(["actifs"])

        affichage = capsys.readouterr().out
        contenu = config_actifs.chemin().read_text(encoding="utf-8")
        assert "pas en euros" in affichage
        assert "ATTENTION" in contenu
        assert f'"{fictifs.ACTIF_ETF}" = ""' in contenu

    def test_avec_un_export_d_ailleurs_rien_n_est_ecrit(self, export_ailleurs, capsys):
        # Les actifs de quelqu'un d'autre ne s'écrivent pas dans notre configuration
        # (règle 2 de CLAUDE.md), pas plus que ses numéros de compte.
        nommer_les_comptes(POCHE_CORRIGEE)

        code = cli.main(["actifs", "--hors-ligne", "--export", str(export_ailleurs)])

        assert code == 0
        assert "Rien n'a été écrit" in capsys.readouterr().out
        assert not config_actifs.chemin().exists()

    def test_sans_les_comptes_nommes_l_assistant_renvoie_a_comptes(self, export, capsys):
        code = cli.main(["actifs", "--hors-ligne"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "dashboard comptes" in capsys.readouterr().err

    def test_avec_un_export_d_ailleurs_aucune_recherche_n_est_lancee(
        self, export_ailleurs, monkeypatch, capsys
    ):
        # Envoyer les ISIN de quelqu'un d'autre à un service extérieur, ce serait divulguer ce
        # qu'il détient (règle 2 de CLAUDE.md). Le garde-fou ne doit donc pas se contenter
        # d'empêcher l'écriture du fichier : aucune requête ne doit partir.
        interroges = []

        class YahooEspion:
            nom = "espion"

            def chercher(self, actif):
                interroges.append(actif)
                return None

        nommer_les_comptes(POCHE_CORRIGEE)
        brancher(monkeypatch, YahooEspion())

        assert cli.main(["actifs", "--export", str(export_ailleurs)]) == 0

        assert interroges == []
        assert "Rien n'a été écrit" in capsys.readouterr().out


class TestCours:
    def test_sans_actif_declare_la_commande_dit_quoi_faire(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)

        code = cli.main(["cours"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "dashboard actifs" in capsys.readouterr().err

    def test_les_cours_sont_recuperes_et_mis_en_cache(self, export, monkeypatch, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(
            monkeypatch,
            FauxYahoo(
                series={
                    fictifs.ACTIF_ACTION_B: [
                        (Date(2026, 2, 26), "20.00"),
                        (Date(2026, 2, 27), "21.00"),
                    ]
                }
            ),
        )

        code = cli.main(["cours"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "2 cours ajouté(s) au cache" in affichage
        serie = Cache().lire(fictifs.ACTIF_ACTION_B)
        assert serie[Date(2026, 2, 27)].valeur == Decimal("21.00")

    def test_relancer_la_commande_ne_redemande_rien(self, export, monkeypatch, capsys):
        # D-50 : un cours en cache est définitif. La seconde exécution n'ajoute rien.
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(
            monkeypatch,
            FauxYahoo(series={fictifs.ACTIF_ACTION_B: [(Date(2026, 2, 27), "21.00")]}),
        )

        cli.main(["cours"])
        capsys.readouterr()
        cli.main(["cours"])

        assert "0 cours ajouté(s) au cache" in capsys.readouterr().out

    def test_un_actif_non_declare_demande_explicitement_est_refuse(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)

        code = cli.main(["cours", "--actif", fictifs.ACTIF_ETF])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "n'est pas déclaré" in capsys.readouterr().err

    def test_un_actif_sans_aucun_cours_est_signale(self, export, monkeypatch, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(monkeypatch, FauxYahoo())

        code = cli.main(["cours"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "sans cours" in capsys.readouterr().err


class TestOublierCours:
    def test_sans_precision_la_commande_refuse_d_agir(self, capsys):
        assert cli.main(["oublier-cours"]) == cli.CODE_ECHEC
        assert "--tout" in capsys.readouterr().err

    def test_un_actif_s_oublie_seul(self, capsys):
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 2, 27), "10.00")
        deposer_un_cours(fictifs.ACTIF_ACTION, Date(2026, 2, 27), "20.00")

        code = cli.main(["oublier-cours", "--actif", fictifs.ACTIF_ETF])

        assert code == 0
        assert "1 actif(s) oublié(s)" in capsys.readouterr().out
        assert Cache().lire(fictifs.ACTIF_ETF) == {}
        assert Cache().lire(fictifs.ACTIF_ACTION) != {}

    def test_tout_le_cache_s_oublie_sur_demande_explicite(self, capsys):
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 2, 27), "10.00")
        deposer_un_cours(fictifs.ACTIF_ACTION, Date(2026, 2, 27), "20.00")

        assert cli.main(["oublier-cours", "--tout"]) == 0
        assert Cache().actifs() == []
        assert "oublié(s)" in capsys.readouterr().out

    def test_un_cache_vide_ne_fait_pas_echouer_la_commande(self, capsys):
        assert cli.main(["oublier-cours", "--tout"]) == 0
        assert "Rien à oublier" in capsys.readouterr().out

    @pytest.mark.parametrize("saisie", ["", "   ", "..."])
    def test_un_identifiant_inutilisable_donne_un_message_et_non_une_trace(
        self, saisie, capsys
    ):
        # L'ISIN est tapé à la main : une faute de frappe ne doit pas produire une trace
        # Python à l'écran.
        assert cli.main(["oublier-cours", "--actif", saisie]) == cli.CODE_ECHEC
        assert "identifiant d'actif utilisable" in capsys.readouterr().err


class TestPositionsAvecCours:
    """Le contrôle qui prouve l'étape : D-15 branché de bout en bout."""

    def test_un_titre_recu_sans_prix_est_valorise_au_dernier_jour_cote(self, export, capsys):
        # Les actions gratuites de l'export fictif tombent un dimanche (2026-03-01) : le cours
        # retenu est celui du vendredi, et le rapport doit le dire.
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "1 prix complété(s)" in affichage
        # 3 parts x 12,50 = 37,50
        assert "37,50" in affichage
        assert "dernier jour coté avant le 2026-03-01" in affichage
        # Le moteur ne réclame plus de prix pour cet actif : c'est le signe que D-15 est
        # branché. (L'export fictif garde une position incomplète pour une autre raison —
        # une distribution de capital sur un actif jamais acheté — que les cours ne peuvent
        # pas réparer.)
        assert "prix à compléter" not in affichage

    def test_sans_cours_le_rapport_explique_ce_qui_manque(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)

        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "attendent toujours un prix" in affichage
        assert "dashboard actifs" in affichage
        # Le moteur continue de dire que le capital est sous-estimé (D-45).
        assert "histoire est incomplète" in affichage

    def test_hors_ligne_aucun_appel_n_est_fait(self, export, monkeypatch, capsys):
        appels = []

        class YahooInterdit:
            nom = "interdit"

            def __init__(self, *args, **kwargs):
                appels.append("construit")

            def serie(self, *args, **kwargs):  # pragma: no cover - ne doit pas être appelé
                appels.append("serie")
                raise AssertionError("aucun appel réseau ne doit partir en hors-ligne")

        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        monkeypatch.setattr(cli, "Yahoo", YahooInterdit)

        assert cli.main(["positions", "--hors-ligne"]) == 0
        assert "serie" not in appels
        assert "dashboard cours" in capsys.readouterr().out

    def test_le_rapport_des_cours_s_affiche_en_cp1252(self, export, capsys):
        # La console Windows écrit en cp1252 : un rapport juste mais inaffichable ferait
        # échouer la commande au moment de l'imprimer. Un test par rapport, comme pour la
        # lecture et le moteur.
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        cli.main(["positions", "--hors-ligne"])

        capsys.readouterr().out.encode("cp1252")

    def test_le_journal_porte_le_montant_deduit(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        assert cli.main(["exporter-positions", "--hors-ligne"]) == 0
        capsys.readouterr()

        journal = (emplacements.dossier_personnel() / "journal.csv").read_text(
            encoding="utf-8-sig"
        )
        assert "37,50" in journal

    def test_le_csv_des_operations_dit_que_le_montant_est_deduit(self, export, capsys):
        # Le rapport affirme que les CSV marquent ces montants : c'est `operations.csv`, avec
        # sa colonne de provenance, qui le fait. Sans complétion ici, ce fichier afficherait
        # « à compléter » là où les positions montrent un montant.
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        assert cli.main(["exporter-pivot", "--hors-ligne"]) == 0
        affichage = capsys.readouterr().out

        operations = (emplacements.dossier_personnel() / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        )
        # L'export fictif contient deux entrées de titres reçus : une action gagnée, dont le
        # prix est lu dans le texte, et les actions gratuites, qui n'en ont aucun. C'est de
        # cette seconde qu'il s'agit.
        ligne_des_titres = next(
            ligne for ligne in operations.splitlines() if "evt-gratuites-1" in ligne
        )
        assert "37,50" in ligne_des_titres
        assert "deduction" in ligne_des_titres
        assert tableur.VALEUR_A_COMPLETER not in ligne_des_titres
        assert "1 prix complété(s)" in affichage

    def test_sans_cours_le_csv_des_operations_dit_a_completer(self, export, capsys):
        nommer_les_comptes(POCHE_CORRIGEE)

        assert cli.main(["exporter-pivot", "--hors-ligne"]) == 0
        capsys.readouterr()

        operations = (emplacements.dossier_personnel() / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        )
        # L'export fictif contient deux entrées de titres reçus : une action gagnée, dont le
        # prix est lu dans le texte, et les actions gratuites, qui n'en ont aucun. C'est de
        # cette seconde qu'il s'agit.
        ligne_des_titres = next(
            ligne for ligne in operations.splitlines() if "evt-gratuites-1" in ligne
        )
        assert tableur.VALEUR_A_COMPLETER in ligne_des_titres


# --- Étape 5 : la valorisation et les rendements ------------------------------------------


class TestValorisationEtRendements:
    """Les deux blocs de l'étape 5 dans « positions », et les quatre CSV de plus."""

    def preparer(self) -> None:
        nommer_les_comptes(POCHE_CORRIGEE)
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        # Le cours qui complète les actions gratuites du 1er mars (D-15)...
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")
        # ...et celui qui valorise la position à la fin de la période.
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 3, 27), "13.00")

    def test_la_valeur_et_les_chiffres_cles_s_affichent(self, export, capsys):
        self.preparer()

        code = cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Valeur des actifs au 2026-03-31" in affichage
        # 3 actions gratuites x 13,00, au cours du vendredi 27 mars.
        assert "39,00" in affichage
        assert "cours du 2026-03-27 (dernier jour coté avant le 2026-03-31)" in affichage
        assert "Les trois chiffres clés (D-22)" in affichage
        assert "GAIN en euros" in affichage

    def test_les_actifs_non_declares_sortent_des_totaux_et_les_refus_sont_listes(
        self, export, capsys
    ):
        self.preparer()

        cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert "Non valorisés, exclus de tous les totaux (D-53)" in affichage
        assert "PARTIEL" in affichage
        # Le bloc « Cours de marché » explique pourquoi : ces actifs n'ont pas de ticker.
        assert "actif non déclaré" in affichage
        assert "dashboard actifs" in affichage

    def test_depuis_borne_la_periode(self, export, capsys):
        self.preparer()

        code = cli.main(
            ["positions", "--hors-ligne", "--depuis", "2026-03-01", "--au", "2026-03-31"]
        )
        affichage = capsys.readouterr().out

        assert code == 0
        assert "du 2026-03-01 jusqu'au 2026-03-31" in affichage

    def test_une_periode_a_l_envers_est_refusee_avant_toute_lecture(self, export, capsys):
        self.preparer()

        code = cli.main(
            ["positions", "--hors-ligne", "--depuis", "2026-06-01", "--au", "2026-03-31"]
        )
        sortie = capsys.readouterr()

        assert code == 1
        assert "après la fin" in sortie.err
        # Rien n'a été lu ni calculé : une période impossible se refuse tout de suite.
        assert sortie.out == ""

    def test_exporter_positions_ecrit_les_six_fichiers(self, export, capsys):
        self.preparer()

        code = cli.main(["exporter-positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        personnel = emplacements.dossier_personnel()
        for nom in (
            "positions.csv",
            "journal.csv",
            "valorisation.csv",
            "flux.csv",
            "sous_periodes_twrr.csv",
            "evolution.csv",
        ):
            assert (personnel / nom).exists(), nom
        assert "TRI.PAIEMENTS" in affichage

        valorisation = (personnel / "valorisation.csv").read_text(encoding="utf-8-sig")
        assert "39,00" in valorisation
        # Le bloc « Cours de marché » est écrit après la construction de l'évolution : les
        # refus qu'elle rencontre y figurent. Ici, entre le 27 février et le 27 mars, il n'y a
        # aucun cours : dès le 10 mars, le dernier connu a plus de dix jours, et l'évolution le
        # dit — ce que ni la complétion ni la valorisation au 31 mars n'auraient signalé.
        assert "cours indisponible" in affichage
        assert "2026-03-10" in affichage
        evolution = (personnel / "evolution.csv").read_text(encoding="utf-8-sig").splitlines()
        # Un jour par ligne, de la première opération (2 janvier) au 31 mars : 89 jours.
        assert len(evolution) == 1 + 89
        assert evolution[-1].startswith("2026-03-31;")

    def test_les_deux_blocs_s_affichent_en_cp1252(self, export, capsys):
        self.preparer()

        cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])

        capsys.readouterr().out.encode("cp1252")

    def test_sans_au_la_valeur_est_celle_de_la_derniere_cloture_connue(self, export, capsys):
        # Le cache ne contient jamais le jour même (D-52) : sans cours récent, la position
        # n'est simplement pas valorisée, et le rapport le dit — jamais un zéro.
        self.preparer()

        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert f"Valeur des actifs au {Date.today().isoformat()}" in affichage
        assert "Non valorisés" in affichage
