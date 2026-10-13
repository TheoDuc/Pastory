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

PASTORY = {"application": "Pastory", "demonstration": False}
"""Ce que répond l'adresse de vie du vrai portefeuille."""


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

    def annoncer_une_fenetre(self) -> None:
        self.appels.append(("annonce", "fenêtre"))


class FaussePrise:
    """Une prise sur un port, qui retient si on l'a relâchée."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.fermee = False

    def close(self) -> None:
        self.fermee = True


def ports_libres(*libres: int):
    """Une façon de prendre un port où seuls `libres` le sont (tous, si aucun n'est dit),
    et la liste des prises rendues."""
    prises: list[FaussePrise] = []

    def prendre(port: int) -> FaussePrise | None:
        if libres and port not in libres:
            return None
        prises.append(FaussePrise(port))
        return prises[-1]

    return prendre, prises


class TestLePort:
    def test_un_port_pris_ne_peut_pas_l_etre_deux_fois(self):
        port = un_port_libre()
        prise = lanceur.prendre(port)
        try:
            assert prise is not None
            assert lanceur.prendre(port) is None
        finally:
            prise.close()

    def test_le_premier_port_libre_est_pris_et_les_autres_relaches(self):
        prendre, prises = ports_libres()
        port, prise = lanceur.reserver(False, prendre=prendre, qui_repond=None)
        assert (port, prise.port, prise.fermee) == (8050, 8050, False)
        assert [autre.fermee for autre in prises[1:]] == [True] * 9

    def test_un_pastory_deja_ouvert_n_en_demarre_pas_un_second(self):
        port, prise = lanceur.reserver(
            False, prendre=lambda port: None, qui_repond=lambda port, patience: PASTORY
        )
        assert (port, prise) == (8050, None)

    def test_un_pastory_sur_un_port_de_repli_est_retrouve(self):
        """Trouvé à la relecture : lancé un jour où le premier port était pris, Pastory
        tourne sur le suivant. Le premier, libéré depuis, ne doit pas en accueillir un
        second — deux Pastory écriraient dans le même dossier."""
        prendre, prises = ports_libres(8050, 8052)
        port, prise = lanceur.reserver(
            False,
            prendre=prendre,
            qui_repond=lambda port, patience: PASTORY if port == 8051 else None,
        )
        assert (port, prise) == (8051, None)
        assert all(relachee.fermee for relachee in prises)

    def test_un_port_occupe_par_un_autre_programme_est_saute(self):
        prendre, _ = ports_libres(8052)
        port, prise = lanceur.reserver(
            False,
            prendre=prendre,
            qui_repond=lambda port, patience: (
                None if port == 8050 else {"application": "Autre", "demonstration": False}
            ),
        )
        assert (port, prise.port) == (8052, 8052)

    def test_la_patience_est_partagee_entre_les_ports_occupes(self):
        patiences: list[float] = []
        with pytest.raises(lanceur.AucunPortLibre):
            lanceur.reserver(
                False,
                prendre=lambda port: None,
                qui_repond=lambda port, patience: patiences.append(patience),
            )
        assert len(patiences) == 10
        assert max(patiences) <= lanceur.PATIENCE and min(patiences) >= 1

    def test_la_demonstration_et_le_vrai_portefeuille_ne_se_repondent_pas(self):
        """Ouvrir la démonstration ne doit jamais ramener la fenêtre des vraies données, ni
        l'inverse."""
        vrai = {"application": "Pastory", "demonstration": False}
        demonstration = {"application": "Pastory", "demonstration": True}

        port, prise = lanceur.reserver(
            True,
            prendre=ports_libres(8061)[0],
            qui_repond=lambda port, patience: vrai,
        )
        assert (port, prise.port) == (8061, 8061)

        port, prise = lanceur.reserver(
            False,
            prendre=ports_libres(8051)[0],
            qui_repond=lambda port, patience: demonstration,
        )
        assert (port, prise.port) == (8051, 8051)

    def test_la_demonstration_a_ses_propres_ports(self):
        port, _ = lanceur.reserver(True, prendre=ports_libres()[0], qui_repond=None)
        assert port == 8060

    def test_sans_port_libre_le_message_dit_lesquels_ont_ete_essayes(self):
        with pytest.raises(lanceur.AucunPortLibre, match="8050 à 8059"):
            lanceur.reserver(
                False, prendre=lambda port: None, qui_repond=lambda port, patience: None
            )


class TestQuiRepond:
    def test_personne(self):
        assert lanceur.qui_repond(un_port_libre(), patience=2) is None
        assert lanceur.annoncer(un_port_libre()) is False

    def test_un_programme_qui_ne_parle_pas_http_n_est_pas_une_panne(self):
        """Trouvé à la relecture : des octets qui ne sont pas du HTTP faisaient remonter une
        erreur jusqu'à « Pastory n'a pas pu s'ouvrir », au lieu de passer au port suivant."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ecoute:
            ecoute.bind((lanceur.HOTE, 0))
            ecoute.listen()

            def repondre_n_importe_quoi():
                client, _ = ecoute.accept()
                with client:
                    client.recv(1024)
                    client.sendall(b"\x15\x03\x01\x00\x02\x02\x46 ceci n'est pas du HTTP\r\n\r\n")

            fil = threading.Thread(target=repondre_n_importe_quoi, daemon=True)
            fil.start()
            assert lanceur.qui_repond(ecoute.getsockname()[1], patience=5) is None
            fil.join(timeout=5)

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
            assert lanceur.qui_repond(port, patience=10) == PASTORY
            assert lanceur.prendre(port) is None
            assert lanceur.annoncer(port) is True
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
        assert reponse.get_json() == PASTORY
        assert reponse.headers["Cache-Control"] == "no-store"

    def test_un_signe_puis_un_adieu(self, client, veille):
        client.post(f"{CHEMIN}?page=abc")
        client.post(f"{CHEMIN}?page=abc&fin=1")
        assert veille.appels == [("signe", "abc"), ("adieu", "abc")]

    def test_le_lanceur_annonce_la_fenetre_qu_il_amene(self, client, veille):
        client.post(f"{CHEMIN}?annonce=1")
        assert veille.appels == [("annonce", "fenêtre")]

    def test_une_question_n_est_pas_un_signe(self, client, veille):
        client.get(f"{CHEMIN}?page=abc")
        assert veille.appels == []

    def test_un_autre_site_ne_tient_pas_pastory_en_vie(self, client, veille):
        client.post(f"{CHEMIN}?page=abc", headers={"Sec-Fetch-Site": "cross-site"})
        client.post(f"{CHEMIN}?annonce=1", headers={"Sec-Fetch-Site": "cross-site"})
        assert veille.appels == []

    def test_une_demande_en_cours_est_un_travail_un_signe_de_vie_non(self, client, veille):
        client.get("/")
        assert veille.appels == [("travail", "début"), ("travail", "fin")]

    def test_sans_veille_l_adresse_repond_quand_meme(self):
        client = application.creer(Chiffres(hors_ligne=True)).server.test_client()
        assert client.post(f"{CHEMIN}?page=abc").get_json() == PASTORY

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

    def test_un_journal_tenu_par_un_pastory_ouvert_n_empeche_pas_d_ouvrir(
        self, dossier_personnel, monkeypatch
    ):
        """Trouvé à la relecture : sous Windows, on n'efface pas un fichier qu'un autre
        programme tient ouvert. Le second lancement tombait en panne au lieu de ramener la
        fenêtre."""
        chemin = dossier_personnel / lanceur.NOM_DU_JOURNAL
        dossier_personnel.mkdir(parents=True, exist_ok=True)
        chemin.write_text("x" * (lanceur.TAILLE_MAXIMALE_DU_JOURNAL + 1), encoding="utf-8")

        def refuser(self, *arguments, **options):
            raise PermissionError("le fichier est utilisé par un autre processus")

        monkeypatch.setattr(type(chemin), "unlink", refuser)
        monkeypatch.setattr(sys, "stdout", None)
        monkeypatch.setattr(sys, "stderr", None)
        assert lanceur.ouvrir_le_journal() == chemin
        sys.stdout.close()


class TestLeLancement:
    @pytest.fixture
    def fenetres(self, monkeypatch):
        ouvertes: list[str] = []
        monkeypatch.setattr(lanceur, "ouvrir_la_fenetre", ouvertes.append)
        monkeypatch.setattr(lanceur, "annoncer", lambda port: True)
        return ouvertes

    def test_un_pastory_qui_s_eteint_n_est_pas_pris_pour_ouvert(self, monkeypatch, fenetres):
        """Trouvé à la relecture : rouvrir Pastory dans les secondes qui suivent sa fermeture
        lui amenait une fenêtre juste avant qu'il ne s'arrête. S'il ne répond plus à
        l'annonce, on regarde de nouveau qui tient le port."""
        regards: list[bool] = []

        def reserver(demonstration):
            regards.append(demonstration)
            return 8050, None

        monkeypatch.setattr(lanceur, "reserver", reserver)
        monkeypatch.setattr(lanceur, "annoncer", lambda port: False)
        monkeypatch.setattr(lanceur, "ramener_la_fenetre", lambda titre: False)
        assert lanceur.lancer() == 0
        assert regards == [False, False]

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

        def panne(demonstration):
            raise RuntimeError("le détail de la panne")

        monkeypatch.setattr(lanceur, "lancer", panne)
        monkeypatch.setattr(lanceur, "avertir", messages.append)
        assert lanceur.main([]) == 1
        assert "n'a pas pu s'ouvrir" in messages[0] and "journal.txt" in messages[0]
        assert "le détail de la panne" in capsys.readouterr().err

    def test_sans_journal_la_panne_se_dit_dans_le_message_lui_meme(self, monkeypatch):
        """Trouvé à la relecture : si le journal n'a pas pu s'ouvrir, renvoyer à ce fichier
        ne laisse aucune trace de la panne."""
        messages: list[str] = []

        def panne():
            raise OSError("le dossier est protégé en écriture")

        monkeypatch.setattr(sys, "stdout", None)
        monkeypatch.setattr(sys, "stderr", None)
        monkeypatch.setattr(lanceur, "ouvrir_le_journal", panne)
        monkeypatch.setattr(lanceur, "avertir", messages.append)
        assert lanceur.main([]) == 1
        assert "le dossier est protégé en écriture" in messages[0]
        assert "journal.txt" not in messages[0]

    def test_sans_port_libre_le_message_le_dit(self, monkeypatch):
        messages: list[str] = []

        def panne(demonstration):
            raise lanceur.AucunPortLibre("Les ports 8050 à 8059 sont tous occupés.")

        monkeypatch.setattr(lanceur, "lancer", panne)
        monkeypatch.setattr(lanceur, "avertir", messages.append)
        assert lanceur.main([]) == 1
        assert "8050 à 8059" in messages[0]


class TestHorsDeWindows:
    """D-117 : sous Linux et macOS, lancé par le menu, le programme a bien une sortie — mais
    elle ne mène à aucun terminal. Ce qu'il écrit doit aller au journal, et une panne de
    démarrage s'afficher par l'outil du système, s'il en a un."""

    def test_sous_windows_seule_l_absence_de_sortie_compte(self, monkeypatch):
        import io

        monkeypatch.setattr(sys, "stderr", io.StringIO())
        assert lanceur.sans_ecran("win32") is False

    def test_ailleurs_une_sortie_qui_ne_mene_a_aucun_terminal_est_sans_ecran(self, monkeypatch):
        import io

        monkeypatch.setattr(sys, "stderr", io.StringIO())
        assert lanceur.sans_ecran("linux") is True

    def test_ailleurs_un_terminal_garde_son_ecran(self, monkeypatch):
        import io

        class Terminal(io.StringIO):
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(sys, "stderr", Terminal())
        assert lanceur.sans_ecran("linux") is False

    def test_sans_sortie_du_tout_il_n_y_a_d_ecran_nulle_part(self, monkeypatch):
        monkeypatch.setattr(sys, "stdout", None)
        assert lanceur.sans_ecran("win32") is True
        assert lanceur.sans_ecran("darwin") is True

    @staticmethod
    def outils(monkeypatch, *presents: str) -> None:
        monkeypatch.setattr(
            lanceur.shutil, "which", lambda nom: f"/usr/bin/{nom}" if nom in presents else None
        )

    def test_sous_linux_la_panne_s_affiche_par_zenity_s_il_est_la(self, monkeypatch):
        self.outils(monkeypatch, "zenity", "notify-send")
        commande = lanceur.boite_de_message("Pastory n'a pas pu s'ouvrir.", "linux")
        assert commande[:2] == ["/usr/bin/zenity", "--error"]
        assert "--text=Pastory n'a pas pu s'ouvrir." in commande
        # Le message n'est pas du balisage : un « & » ou un « < » doit s'afficher tel quel.
        assert "--no-markup" in commande

    def test_a_defaut_par_une_notification(self, monkeypatch):
        self.outils(monkeypatch, "notify-send")
        assert lanceur.boite_de_message("Panne.", "linux") == [
            "/usr/bin/notify-send", lanceur.NOM, "Panne.",
        ]

    def test_sans_aucun_outil_le_journal_reste_la_seule_trace(self, monkeypatch):
        self.outils(monkeypatch)
        assert lanceur.boite_de_message("Panne.", "linux") is None
        assert lanceur.boite_de_message("Panne.", "darwin") is None

    def test_sous_macos_le_message_ne_peut_pas_sortir_de_ses_guillemets(self, monkeypatch):
        self.outils(monkeypatch, "osascript")
        commande = lanceur.boite_de_message('Le dossier "Pastory" manque.', "darwin")
        assert commande[:2] == ["/usr/bin/osascript", "-e"]
        assert 'message "Le dossier \\"Pastory\\" manque."' in commande[2]
