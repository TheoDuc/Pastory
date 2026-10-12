"""Le portefeuille de démonstration (étape 10, D-107).

Deux choses sont gardées ici. D'abord, que l'export fictif est un export que Pastory **lit sans
réserve** — sinon la démonstration montrerait des trous qui n'existent pas chez un vrai
utilisateur. Ensuite, qu'il ne peut **jamais se mêler** aux vraies données, ni passer pour elles.
"""

from __future__ import annotations

from collections import Counter
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory import assembleur, cli, demonstration, lanceur
from pastory.adaptateurs.trade_republic import classement
from pastory.config import emplacements
from pastory.demonstration.clotures import CLOTURES, RELEVE_LE
from pastory.pivot.operation import Poche
from pastory.vues import application, bandeau, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues.chiffres import Chiffres
from pastory.vues.veille import CHEMIN
from tests.vues.outils import identifiants, texte


@pytest.fixture
def lignes() -> list[dict[str, str]]:
    return demonstration.lignes()


class TestLExportFictif:
    def test_pastory_le_lit_sans_aucune_reserve(self, tmp_path):
        demonstration.ecrire(tmp_path)
        rapport = assembleur.lire(tmp_path)

        assert len(rapport.operations) == 177
        # Le Saveback est là exprès : il montre un type que Pastory affiche sans le traiter.
        assert dict(rapport.types_inconnus) == {"CASH/BENEFITS_SAVEBACK": 1}
        assert [s.categorie for s in rapport.signalements] == ["non traité"]
        assert rapport.depot.fichiers_ignores == []

    def test_les_trois_poches_y_sont(self, tmp_path):
        demonstration.ecrire(tmp_path)
        poches = Counter(operation.poche for operation in assembleur.lire(tmp_path).operations)
        assert set(poches) == {Poche.PEA, Poche.CTO, Poche.CRYPTO}

    def test_seules_des_formes_deja_vues_sont_ecrites(self, lignes):
        """Aucune liste des types n'est publiée (D-79) : la démonstration n'invente pas une
        forme que personne n'a vue sur un vrai fichier — pas de dividende de fonds, par
        exemple."""
        vues = (
            set(classement.TYPES_TRAITES)
            | set(classement.TYPES_HORS_PERIMETRE)
            | {("CASH", "BENEFITS_SAVEBACK")}
        )
        assert {(ligne["category"], ligne["type"]) for ligne in lignes} <= vues
        assert {ligne["asset_class"] for ligne in lignes if ligne["type"] == "DIVIDEND"} == {
            "STOCK"
        }
        assert {ligne["asset_class"] for ligne in lignes} <= {"", "FUND", "STOCK", "CRYPTO"}

    def test_chaque_prix_d_achat_est_une_vraie_cloture(self, lignes):
        """C'est ce qui fait passer le contrôle par le prix payé (D-85) : un prix inventé ferait
        refuser la bonne cotation."""
        ordres = [ligne for ligne in lignes if ligne["category"] == "TRADING"]
        assert len(ordres) == 158
        for ligne in ordres:
            relevees = {
                jour: Decimal(cours) for jour, cours in CLOTURES[ligne["symbol"]].values()
            }
            assert abs(Decimal(ligne["price"]) - relevees[ligne["date"]]) < Decimal("0.0001")

    def test_le_montant_d_un_ordre_est_sa_quantite_fois_son_prix(self, lignes):
        for ligne in lignes:
            if ligne["category"] != "TRADING":
                continue
            attendu = Decimal(ligne["shares"]) * Decimal(ligne["price"])
            assert abs(abs(Decimal(ligne["amount"])) - abs(attendu)) <= Decimal("0.005")
            assert (Decimal(ligne["amount"]) < 0) == (ligne["type"] == "BUY")

    def test_un_dividende_en_dollars_se_recoupe(self, lignes):
        en_dollars = [ligne for ligne in lignes if ligne["original_currency"] == "USD"]
        assert len(en_dollars) == 12
        for ligne in en_dollars:
            converti = Decimal(ligne["original_amount"]) * Decimal(ligne["fx_rate"])
            assert abs(converti - Decimal(ligne["amount"])) < Decimal("0.000001")

    def test_le_premier_mouvement_du_pea_est_un_versement(self, lignes):
        """C'est lui qui date l'ouverture du plan (D-86) : aucun titre ne doit le précéder."""
        du_pea = sorted(
            (ligne for ligne in lignes if ligne["account_type"] == "PEA"),
            key=lambda ligne: ligne["datetime"],
        )
        assert (du_pea[0]["category"], du_pea[0]["type"]) == ("CASH", "TRANSFER_IN")
        assert du_pea[0]["date"] == "2023-01-02"

    def test_on_ne_vend_jamais_plus_qu_on_ne_detient(self, lignes):
        detenu: Counter[str] = Counter()
        for ligne in sorted(lignes, key=lambda ligne: ligne["datetime"]):
            if ligne["category"] == "TRADING":
                detenu[ligne["symbol"]] += Decimal(ligne["shares"])
                assert detenu[ligne["symbol"]] >= 0
            elif ligne["type"] == "DIVIDEND":
                assert Decimal(ligne["shares"]) == detenu[ligne["symbol"]]

    def test_rien_n_y_ressemble_a_une_vraie_personne(self, lignes):
        for ligne in lignes:
            assert ligne["transaction_id"].startswith("00000000-0000-4000-8000-")
            if ligne["counterparty_name"]:
                assert "Fictif" in ligne["counterparty_name"]
                assert set(ligne["counterparty_iban"][4:]) == {"0"}
        assert len({ligne["transaction_id"] for ligne in lignes}) == len(lignes)

    def test_il_est_toujours_le_meme(self):
        assert demonstration.texte_csv() == demonstration.texte_csv()

    def test_aucune_operation_n_est_posterieure_au_releve(self, lignes):
        assert max(ligne["date"] for ligne in lignes) <= RELEVE_LE

    def test_un_releve_incomplet_se_dit(self):
        with pytest.raises(demonstration.CloturesIncompletes, match="2023-01-02"):
            demonstration.lignes({})

    def test_le_releve_couvre_tout_le_scenario(self):
        for titre, jours in demonstration.jours_a_relever().items():
            assert {jour.isoformat() for jour in jours} <= set(CLOTURES[titre.code])


class TestUnDossierAPart:
    def test_la_demonstration_a_son_propre_dossier_voisin_du_vrai(self, dossier_personnel):
        assert emplacements.dossier_de_demonstration() == dossier_personnel.with_name(
            "personnel-demonstration"
        )

    def test_sous_windows_c_est_pastory_demonstration(self, tmp_path, monkeypatch):
        monkeypatch.setattr(emplacements.sys, "platform", "win32")
        environnement = {"LOCALAPPDATA": str(tmp_path)}
        assert (
            emplacements.dossier_de_demonstration(environnement)
            == tmp_path / "Pastory-demonstration"
        )

    def test_preparer_detourne_tout_et_ne_touche_pas_au_vrai_dossier(self, dossier_personnel):
        environnement = {emplacements.VARIABLE_EMPLACEMENT: str(dossier_personnel)}

        racine = demonstration.preparer(environnement)

        assert racine == dossier_personnel.with_name("personnel-demonstration")
        assert environnement[emplacements.VARIABLE_EMPLACEMENT] == str(racine)
        assert (racine / "exports" / demonstration.NOM_DU_FICHIER).is_file()
        assert emplacements.dossier_cache(environnement) == racine / "cache"
        assert not dossier_personnel.exists()

    def test_preparer_deux_fois_ne_s_eloigne_pas(self, dossier_personnel):
        environnement = {emplacements.VARIABLE_EMPLACEMENT: str(dossier_personnel)}
        assert demonstration.preparer(environnement) == demonstration.preparer(environnement)

    def test_l_export_n_est_reecrit_que_s_il_a_change(self, tmp_path):
        chemin = demonstration.ecrire(tmp_path)
        chemin.write_bytes(chemin.read_bytes() + b"")
        avant = chemin.stat().st_mtime_ns
        assert demonstration.ecrire(tmp_path).stat().st_mtime_ns == avant

        chemin.write_text("un scénario plus ancien", encoding="utf-8")
        demonstration.ecrire(tmp_path)
        assert chemin.read_text(encoding="utf-8") == demonstration.texte_csv()


@pytest.fixture
def chiffres_de_demonstration(dossier_personnel):
    demonstration.ecrire(dossier_personnel / "exports")
    return Chiffres(hors_ligne=True, demonstration=True)


def rendu(chiffres: Chiffres, **etat) -> ecrans.Rendu:
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), **etat})


class TestALEcran:
    """Personne ne doit pouvoir prendre ce portefeuille pour un vrai, ni y déposer le sien."""

    def test_la_couverture_dit_que_le_portefeuille_est_fictif(self, chiffres_de_demonstration):
        corps = rendu(chiffres_de_demonstration, onglet=bandeau.ACCUEIL)[4]
        lu = texte(corps)
        assert demonstration.MENTION in lu
        assert "Ce portefeuille est fictif" in lu
        assert "Un portefeuille fictif" in lu and "Votre livre" not in lu

    def test_on_n_y_depose_rien(self, chiffres_de_demonstration):
        corps = rendu(chiffres_de_demonstration, onglet=bandeau.ACCUEIL)[4]
        assert "depot" not in identifiants(corps)
        assert "ouvrir-dossier" not in identifiants(corps)
        assert "Ouvrir le livre" in texte(corps)

    def test_les_huit_positions_sont_la(self, chiffres_de_demonstration):
        base = chiffres_de_demonstration.base()
        assert len(base.portefeuille.positions) == 8

    def test_la_mention_reste_sur_chaque_chapitre(self, chiffres_de_demonstration):
        page = application.creer(chiffres_de_demonstration).layout
        assert demonstration.MENTION in texte(page)

    def test_la_fenetre_et_l_adresse_de_vie_disent_demonstration(self, chiffres_de_demonstration):
        interface = application.creer(chiffres_de_demonstration)
        assert interface.title == demonstration.TITRE_DE_LA_FENETRE
        assert interface.server.test_client().get(CHEMIN).get_json() == {
            "application": "Pastory",
            "demonstration": True,
        }

    def test_hors_demonstration_rien_n_en_parle(self, dossier_personnel):
        demonstration.ecrire(dossier_personnel / "exports")
        chiffres = Chiffres(hors_ligne=True)
        interface = application.creer(chiffres)
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]

        assert interface.title == "Pastory"
        assert demonstration.MENTION not in texte(interface.layout)
        assert demonstration.MENTION not in texte(corps)
        assert "depot" in identifiants(corps)

    def test_une_demonstration_empechee_ne_propose_pas_de_depot(self, dossier_personnel):
        corps = rendu(Chiffres(hors_ligne=True, demonstration=True))[4]
        assert demonstration.MENTION in texte(corps)
        assert "depot" not in identifiants(corps)


class TestLesDeuxPortesDEntree:
    def test_le_raccourci_prepare_le_dossier_avant_tout(self, dossier_personnel, monkeypatch):
        lances: list[bool] = []
        monkeypatch.setattr(lanceur, "lancer", lambda demonstration: lances.append(demonstration))

        lanceur.main(["--demonstration"])

        assert lances == [True]
        attendu = dossier_personnel.with_name("personnel-demonstration")
        assert emplacements.dossier_personnel() == attendu
        assert (attendu / "exports" / demonstration.NOM_DU_FICHIER).is_file()

    def test_sans_l_option_le_dossier_reste_le_vrai(self, dossier_personnel, monkeypatch):
        lances: list[bool] = []
        monkeypatch.setattr(lanceur, "lancer", lambda demonstration: lances.append(demonstration))

        lanceur.main([])

        assert lances == [False]
        assert emplacements.dossier_personnel() == dossier_personnel

    def test_la_commande_ouvre_la_demonstration_sur_son_port(self, dossier_personnel, monkeypatch):
        appels: list[dict] = []
        monkeypatch.setattr(application, "lancer", lambda **options: appels.append(options))

        assert cli.main(["ouvrir", "--demonstration"]) == 0

        assert appels == [
            {"hors_ligne": False, "dossier_export": None, "port": 8060, "demonstration": True}
        ]
        assert emplacements.dossier_personnel().name == "personnel-demonstration"

    def test_la_commande_garde_son_port_habituel(self, monkeypatch):
        appels: list[dict] = []
        monkeypatch.setattr(application, "lancer", lambda **options: appels.append(options))

        assert cli.main(["ouvrir"]) == 0
        assert appels[0]["port"] == 8050 and appels[0]["demonstration"] is False

    def test_la_demonstration_ne_lit_pas_l_export_d_un_tiers(self, tmp_path, capsys):
        assert cli.main(["ouvrir", "--demonstration", "--export", str(tmp_path)]) == 1
        assert "ne vont pas ensemble" in capsys.readouterr().err


def test_le_releve_date_d_un_jour_reel():
    assert Date.fromisoformat(RELEVE_LE) <= Date.today()
