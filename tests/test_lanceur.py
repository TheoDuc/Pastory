"""Le lanceur : ce que fait le raccourci de Pastory (étape 10, D-106).

Aucun test n'ouvre de fenêtre ni ne sort de la machine : le navigateur est remplacé, et le seul
serveur démarré écoute `127.0.0.1` sur un port que le système choisit.
"""

from __future__ import annotations

import socket
import sys
import threading

import pytest
from werkzeug.serving import make_server

from pastory import lanceur
from pastory.vues import application
from pastory.vues.chiffres import Chiffres
from pastory.vues.veille import CHEMIN, Veille


def un_port_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prise:
        prise.bind((lanceur.HOTE, 0))
        return prise.getsockname()[1]


class FausseVeille:
    def __init__(self) -> None:
        self.appels: list[tuple[str, str]] = []

    def signe(self, page: str) -> None:
        self.appels.append(("signe", page))

    def adieu(self, page: str) -> None:
        self.appels.append(("adieu", page))

    def commencer_un_travail(self) -> None:
        self.appels.append(("travail", "début"))

    def finir_un_travail(self) -> None:
        self.appels.append(("travail", "fin"))


class TestLePort:
    def test_un_port_pris_ne_peut_pas_l_etre_deux_fois(self):
        port = un_port_libre()
        prise = lanceur.prendre(port)
        try:
            assert prise is not None
            assert lanceur.prendre(port) is None
        finally:
            prise.close()

    def test_le_premier_port_libre_est_pris(self):
        port, prise = lanceur.reserver(False, prendre=lambda port: "prise", qui_repond=None)
        assert (port, prise) == (8050, "prise")

    def test_un_pastory_deja_ouvert_n_en_demarre_pas_un_second(self):
        port, prise = lanceur.reserver(
            False, prendre=lambda port: None, qui_repond=lambda port: {"application": "Pastory"}
        )
        assert (port, prise) == (8050, None)

    def test_un_port_occupe_par_un_autre_programme_est_saute(self):
        port, prise = lanceur.reserver(
            False,
            prendre=lambda port: "prise" if port == 8052 else None,
            qui_repond=lambda port: None if port == 8050 else {"application": "Autre"},
        )
        assert (port, prise) == (8052, "prise")

    def test_la_demonstration_et_le_vrai_portefeuille_ne_se_repondent_pas(self):
        """Ouvrir la démonstration ne doit jamais ramener la fenêtre des vraies données, ni
        l'inverse."""
        vrai = {"application": "Pastory", "demonstration": False}
        demonstration = {"application": "Pastory", "demonstration": True}

        port, prise = lanceur.reserver(
            True,
            prendre=lambda port: "prise" if port == 8061 else None,
            qui_repond=lambda port: vrai,
        )
        assert (port, prise) == (8061, "prise")

        port, prise = lanceur.reserver(
            False,
            prendre=lambda port: "prise" if port == 8051 else None,
            qui_repond=lambda port: demonstration,
        )
        assert (port, prise) == (8051, "prise")

    def test_la_demonstration_a_ses_propres_ports(self):
        port, _ = lanceur.reserver(True, prendre=lambda port: "prise", qui_repond=None)
        assert port == 8060

    def test_sans_port_libre_le_message_dit_lesquels_ont_ete_essayes(self):
        with pytest.raises(lanceur.AucunPortLibre, match="8050 à 8059"):
            lanceur.reserver(False, prendre=lambda port: None, qui_repond=lambda port: None)


class TestQuiRepond:
    def test_personne(self):
        assert lanceur.qui_repond(un_port_libre(), patience=2) is None

    def test_un_pastory_servi_sur_la_prise_du_lanceur(self):
        """Le chemin entier du lancement, sans fenêtre : le port est pris d'abord, le serveur
        s'installe ensuite sur cette prise, et il répond « c'est moi »."""
        port = un_port_libre()
        prise = lanceur.prendre(port)
        interface = application.creer(Chiffres(hors_ligne=True), Veille())
        serveur = make_server(
            lanceur.HOTE, port, interface.server, threaded=True, fd=prise.fileno()
        )
        fil = threading.Thread(target=serveur.serve_forever, daemon=True)
        fil.start()
        try:
            assert lanceur.qui_repond(port, patience=10) == {"application": "Pastory"}
            assert lanceur.prendre(port) is None
        finally:
            serveur.shutdown()
            serveur.server_close()
            prise.close()
            fil.join(timeout=5)


class TestLAdresseDeVie:
    @pytest.fixture
    def veille(self):
        return FausseVeille()

    @pytest.fixture
    def client(self, veille):
        return application.creer(Chiffres(hors_ligne=True), veille).server.test_client()

    def test_elle_dit_qui_elle_est(self, client):
        reponse = client.get(CHEMIN)
        assert reponse.get_json() == {"application": "Pastory"}
        assert reponse.headers["Cache-Control"] == "no-store"

    def test_un_signe_puis_un_adieu(self, client, veille):
        client.post(f"{CHEMIN}?page=abc")
        client.post(f"{CHEMIN}?page=abc&fin=1")
        assert veille.appels == [("signe", "abc"), ("adieu", "abc")]

    def test_une_question_n_est_pas_un_signe(self, client, veille):
        client.get(f"{CHEMIN}?page=abc")
        assert veille.appels == []

    def test_un_autre_site_ne_tient_pas_pastory_en_vie(self, client, veille):
        client.post(f"{CHEMIN}?page=abc", headers={"Sec-Fetch-Site": "cross-site"})
        assert veille.appels == []

    def test_une_demande_en_cours_est_un_travail_un_signe_de_vie_non(self, client, veille):
        client.get("/")
        assert veille.appels == [("travail", "début"), ("travail", "fin")]

    def test_sans_veille_l_adresse_repond_quand_meme(self):
        client = application.creer(Chiffres(hors_ligne=True)).server.test_client()
        assert client.post(f"{CHEMIN}?page=abc").get_json() == {"application": "Pastory"}

    def test_la_page_donne_signe_de_vie(self, client):
        page = client.get("/").get_data(as_text=True)
        assert f'"{CHEMIN}?page="' in page
        assert "sendBeacon" in page


class TestLaVeille:
    def test_le_serveur_est_arrete_quand_plus_personne_n_est_la(self):
        veille = Veille(attente_de_la_premiere_page=3)
        journal: list[str] = []
        lanceur.veiller(
            veille, lambda: journal.append("arrêt"), dormir=lambda duree: journal.append("…")
        )
        assert journal == ["…", "…", "arrêt"]


class TestLaFenetre:
    def test_edge_puis_chrome_sous_windows(self, tmp_path):
        environnement = {"ProgramFiles(x86)": str(tmp_path / "x86"), "ProgramFiles": str(tmp_path)}
        assert lanceur.navigateur_application(environnement, "win32") is None

        chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
        chrome.parent.mkdir(parents=True)
        chrome.write_bytes(b"")
        assert lanceur.navigateur_application(environnement, "win32") == chrome

        edge = tmp_path / "x86" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        edge.parent.mkdir(parents=True)
        edge.write_bytes(b"")
        assert lanceur.navigateur_application(environnement, "win32") == edge

    def test_sans_edge_ni_chrome_le_navigateur_habituel(self, monkeypatch):
        ouvertes: list[str] = []
        monkeypatch.setattr(lanceur, "navigateur_application", lambda: None)
        monkeypatch.setattr(lanceur.webbrowser, "open", ouvertes.append)
        lanceur.ouvrir_la_fenetre("http://127.0.0.1:8050/")
        assert ouvertes == ["http://127.0.0.1:8050/"]

    def test_la_fenetre_est_ouverte_en_mode_application(self, monkeypatch, tmp_path):
        commandes: list[list[str]] = []
        monkeypatch.setattr(lanceur, "navigateur_application", lambda: tmp_path / "msedge.exe")
        monkeypatch.setattr(
            lanceur.subprocess, "Popen", lambda commande, **options: commandes.append(commande)
        )
        lanceur.ouvrir_la_fenetre("http://127.0.0.1:8050/")
        assert commandes == [[str(tmp_path / "msedge.exe"), "--app=http://127.0.0.1:8050/"]]


class TestLeJournal:
    def test_avec_un_terminal_rien_n_est_detourne(self, dossier_personnel):
        assert lanceur.ouvrir_le_journal() is None
        assert not (dossier_personnel / lanceur.NOM_DU_JOURNAL).exists()

    def test_sans_terminal_tout_va_au_journal(self, dossier_personnel, monkeypatch):
        monkeypatch.setattr(sys, "stdout", None)
        monkeypatch.setattr(sys, "stderr", None)
        chemin = lanceur.ouvrir_le_journal()
        flux = sys.stdout
        try:
            print("une panne")
            print("son détail", file=sys.stderr)
        finally:
            flux.close()
        assert chemin == dossier_personnel / lanceur.NOM_DU_JOURNAL
        lu = chemin.read_text(encoding="utf-8")
        assert "ouverture de Pastory" in lu
        assert "une panne" in lu and "son détail" in lu

    def test_un_journal_trop_gros_repart_de_zero(self, dossier_personnel, monkeypatch):
        chemin = dossier_personnel / lanceur.NOM_DU_JOURNAL
        dossier_personnel.mkdir(parents=True, exist_ok=True)
        chemin.write_text("x" * (lanceur.TAILLE_MAXIMALE_DU_JOURNAL + 1), encoding="utf-8")
        monkeypatch.setattr(sys, "stdout", None)
        monkeypatch.setattr(sys, "stderr", None)
        lanceur.ouvrir_le_journal()
        sys.stdout.close()
        assert chemin.stat().st_size < 200


class TestLeLancement:
    @pytest.fixture
    def fenetres(self, monkeypatch):
        ouvertes: list[str] = []
        monkeypatch.setattr(lanceur, "ouvrir_la_fenetre", ouvertes.append)
        return ouvertes

    def test_deja_ouvert_la_fenetre_revient_et_rien_ne_demarre(self, monkeypatch, fenetres):
        ramenees: list[str] = []
        monkeypatch.setattr(lanceur, "reserver", lambda demonstration: (8050, None))
        monkeypatch.setattr(
            lanceur, "ramener_la_fenetre", lambda titre: ramenees.append(titre) or True
        )
        assert lanceur.lancer() == 0
        assert ramenees == ["Pastory"]
        assert fenetres == []

    def test_deja_ouvert_sans_fenetre_retrouvee_on_en_ouvre_une(self, monkeypatch, fenetres):
        monkeypatch.setattr(lanceur, "reserver", lambda demonstration: (8053, None))
        monkeypatch.setattr(lanceur, "ramener_la_fenetre", lambda titre: False)
        assert lanceur.lancer() == 0
        assert fenetres == ["http://127.0.0.1:8053/"]

    def test_une_panne_de_demarrage_ne_reste_jamais_muette(self, monkeypatch, capsys):
        messages: list[str] = []

        def panne():
            raise RuntimeError("le détail de la panne")

        monkeypatch.setattr(lanceur, "lancer", panne)
        monkeypatch.setattr(lanceur, "avertir", messages.append)
        assert lanceur.main([]) == 1
        assert "n'a pas pu s'ouvrir" in messages[0] and "journal.txt" in messages[0]
        assert "le détail de la panne" in capsys.readouterr().err

    def test_sans_port_libre_le_message_le_dit(self, monkeypatch):
        messages: list[str] = []

        def panne():
            raise lanceur.AucunPortLibre("Les ports 8050 à 8059 sont tous occupés.")

        monkeypatch.setattr(lanceur, "lancer", panne)
        monkeypatch.setattr(lanceur, "avertir", messages.append)
        assert lanceur.main([]) == 1
        assert "8050 à 8059" in messages[0]
