"""Le serveur local ne répond qu'à l'ordinateur où il tourne (D-115).

Trouvé par la revue de sécurité de l'étape 11. Pastory n'écoute que `127.0.0.1`, mais une page
web malveillante peut faire pointer son propre nom vers cette adresse (« DNS rebinding ») : le
navigateur croit alors parler au même site, et ses protections tombent. La parade tient en une
ligne — refuser toute demande qui ne s'adresse pas à nous par notre nom — et ces tests la
tiennent sur chaque adresse du serveur.
"""

from __future__ import annotations

import base64
import json

import pytest

from pastory import demonstration
from pastory.config import emplacements
from pastory.vues import application, attente
from pastory.vues import etat as etat_ecran
from pastory.vues.chiffres import Chiffres
from pastory.vues.veille import CHEMIN as CHEMIN_DE_VIE
from pastory.vues.veille import Veille
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs

ADRESSES = ["/", "/_dash-layout", "/_dash-dependencies", CHEMIN_DE_VIE, attente.CHEMIN]


@pytest.fixture
def client(dossier_personnel):
    return application.creer(Chiffres(hors_ligne=True)).server.test_client()


class TestSeulSonPropreNomEstAccepte:
    @pytest.mark.parametrize("adresse", ADRESSES)
    @pytest.mark.parametrize("nom", ["127.0.0.1:8050", "localhost:8050", "127.0.0.1", "LocalHost"])
    def test_l_ordinateur_lui_meme_est_servi(self, client, adresse, nom):
        assert client.get(adresse, headers={"Host": nom}).status_code == 200

    @pytest.mark.parametrize("adresse", ADRESSES)
    @pytest.mark.parametrize(
        "nom",
        [
            "attaquant.example:8050",  # le nom d'un autre, pointé sur cet ordinateur
            "127.0.0.1.attaquant.example:8050",
            "attaquant.example",
            "192.168.1.20:8050",  # une autre machine du réseau
            "",
        ],
    )
    def test_tout_autre_nom_est_refuse(self, client, adresse, nom):
        reponse = client.get(adresse, headers={"Host": nom})
        assert reponse.status_code == 403
        assert "portefeuille" not in reponse.get_data(as_text=True).lower()

    def test_un_rappel_d_ecran_est_refuse_aussi(self, client):
        """C'est par là qu'une page hostile lirait les chiffres : la demande qui redessine
        l'écran, avec le bon type de contenu, mais adressée au nom d'un autre."""
        demande = {
            "output": "..onglets.children...signalements.children..",
            "outputs": [],
            "inputs": [{"id": "etat", "property": "data", "value": etat_ecran.initial()}],
            "changedPropIds": ["etat.data"],
        }
        reponse = client.post(
            "/_dash-update-component",
            data=json.dumps(demande),
            content_type="application/json",
            headers={"Host": "attaquant.example:8050"},
        )
        assert reponse.status_code == 403

    def test_un_refus_ne_compte_pas_comme_un_travail(self, dossier_personnel):
        """Refusée avant Flask, la demande ne touche ni à la veille ni à ses compteurs : une
        page hostile ne peut pas tenir Pastory ouvert, ni fausser son arrêt (D-106)."""

        class VeilleQuiCompte(Veille):
            vus = 0

            def commencer_un_travail(self) -> None:
                self.vus += 1
                super().commencer_un_travail()

            def signe(self, page: str) -> None:
                self.vus += 1
                super().signe(page)

        veille = VeilleQuiCompte()
        client = application.creer(Chiffres(hors_ligne=True), veille).server.test_client()
        hostile = {"Host": "attaquant.example:8050"}

        client.get("/", headers=hostile)
        client.post(f"{CHEMIN_DE_VIE}?page=abc", headers=hostile)

        assert veille.vus == 0

    def test_le_lanceur_s_adresse_a_pastory_par_le_nom_accepte(self):
        """Le lanceur demande « qui est là ? » à cette adresse : s'il employait un autre nom,
        il ne reconnaîtrait plus son propre Pastory et en démarrerait un second."""
        from pastory import lanceur

        assert lanceur.HOTE in application.ADRESSES_DE_PASTORY


class TestCeQueLEcranNeMontrePasLeServeurLeRefuse:
    """La démonstration n'a pas de zone de dépôt (D-107). Le serveur ne s'en remet pas à
    l'écran pour cela : une demande forgée n'y range aucun fichier."""

    def test_la_demande_forgee_est_bien_celle_d_un_depot(self, dossier_personnel, tmp_path):
        """Le témoin : hors démonstration, la même demande range le fichier. Sans lui, le
        test suivant passerait aussi avec une demande mal écrite."""
        chiffres = Chiffres(hors_ligne=True)

        reponse = _deposer(application.creer(chiffres), _un_export(tmp_path))

        assert reponse.status_code == 200
        assert [fichier.name for fichier in chiffres.dossier().glob("*.csv")] == ["Un autre.csv"]

    def test_la_demonstration_ne_recoit_aucun_fichier(
        self, dossier_personnel, tmp_path, monkeypatch
    ):
        un_export = _un_export(tmp_path)
        monkeypatch.setenv(
            emplacements.VARIABLE_EMPLACEMENT, str(emplacements.dossier_de_demonstration())
        )
        demonstration.ecrire(emplacements.dossier_exports())
        chiffres = Chiffres(hors_ligne=True)
        assert chiffres.demonstration
        avant = sorted(chiffres.dossier().iterdir())

        reponse = _deposer(application.creer(chiffres), un_export)

        assert reponse.status_code == 204
        assert sorted(chiffres.dossier().iterdir()) == avant


def _un_export(dossier) -> bytes:
    return next(fictifs.deposer(dossier / "ailleurs").glob("*.csv")).read_bytes()


def _deposer(interface, un_export: bytes):
    """Un dépôt, passé par Dash comme le fait le navigateur."""
    sortie = next(
        cle
        for cle, rappel in interface.callback_map.items()
        if any(une["id"] == "depot" for une in rappel.get("inputs", []))
    )
    contenu = base64.b64encode(un_export).decode()
    return interface.server.test_client().post(
        "/_dash-update-component",
        data=json.dumps(
            {
                "output": sortie,
                "outputs": {"id": "etat", "property": sortie.partition(".")[2]},
                "inputs": [
                    {
                        "id": "depot",
                        "property": "contents",
                        "value": [f"data:text/csv;base64,{contenu}"],
                    }
                ],
                "changedPropIds": ["depot.contents"],
                "state": [
                    {"id": "depot", "property": "filename", "value": ["Un autre.csv"]},
                    {"id": "etat", "property": "data", "value": etat_ecran.initial()},
                ],
            }
        ),
        content_type="application/json",
    )
