"""Ce que devient un export déposé : un fichier, un portefeuille (D-109).

Le cas d'origine : un proche dépose son export à côté de celui de l'utilisateur. Avant, les deux
se cumulaient, et Pastory affichait la somme de deux comptes sans rien dire.
"""

from __future__ import annotations

import base64

import pytest

from pastory.adaptateurs.trade_republic import depot
from pastory.vues.chiffres import Chiffres
from pastory.vues.reception import EXTENSION_PROVISOIRE, recevoir
from tests.adaptateurs.trade_republic import export_fictif as fictif

NOM_DE_LA_BANQUE = "Exportation de transactions.csv"


def deposer(dossier, lignes, nom=NOM_DE_LA_BANQUE):
    """Dépose un export comme le fait la zone de dépôt du navigateur."""
    octets = fictif.texte_csv(lignes).encode("utf-8")
    return recevoir(nom, "data:text/csv;base64," + base64.b64encode(octets).decode(), dossier)


def portefeuilles(dossier) -> list[str]:
    return [p.nom for p in depot.inventaire(dossier).portefeuilles]


def ouvert(dossier) -> str:
    return depot.inventaire(dossier).ouvert.nom


@pytest.fixture
def dossier(dossier_personnel):
    return dossier_personnel / "exports"


@pytest.fixture
def compte():
    """Trois opérations d'un même compte, dans l'ordre où elles ont eu lieu."""
    return [fictif.achat_plan_epargne(), fictif.achat_ordre_cto(), fictif.vente()]


class TestLePremierDepot:
    def test_il_garde_le_nom_de_son_fichier_et_s_ouvre(self, dossier, compte):
        reception = deposer(dossier, compte)

        assert reception.accepte
        assert reception.fichier == dossier / NOM_DE_LA_BANQUE
        assert "est déposé : 3 lignes, du 02/03/2026 au 10/04/2026" in reception.message
        assert ouvert(dossier) == "Exportation de transactions"


class TestUnAutreCompte:
    """Aucune opération commune : c'est le compte de quelqu'un d'autre."""

    def test_il_devient_un_nouveau_portefeuille_et_ne_se_cumule_pas(self, dossier, compte):
        deposer(dossier, compte)

        reception = deposer(dossier, [fictif.achat_crypto()])

        assert portefeuilles(dossier) == ["Exportation de transactions", "Portefeuille"]
        assert reception.fichier == dossier / "Portefeuille.csv"
        assert "nouveau portefeuille, « Portefeuille »" in reception.message
        assert "renommer" in reception.message
        assert ouvert(dossier) == "Portefeuille"
        assert len(depot.lire(dossier).lignes) == 1

    def test_les_chiffres_de_l_un_ne_contiennent_pas_ceux_de_l_autre(self, dossier, compte):
        deposer(dossier, compte)
        seul = {p.actif for p in Chiffres(hors_ligne=True).base().portefeuille.positions}

        deposer(dossier, [fictif.achat_crypto()])
        depot.ouvrir(dossier, "Exportation de transactions")
        a_deux = {p.actif for p in Chiffres(hors_ligne=True).base().portefeuille.positions}

        assert a_deux == seul
        assert fictif.CRYPTO not in a_deux

    def test_un_troisieme_compte_recoit_un_nom_libre(self, dossier, compte):
        deposer(dossier, compte)
        deposer(dossier, [fictif.achat_crypto()])
        deposer(dossier, [fictif.dividende()])
        assert portefeuilles(dossier) == [
            "Exportation de transactions",
            "Portefeuille",
            "Portefeuille 2",
        ]

    def test_un_fichier_que_l_on_a_nomme_soi_meme_garde_son_nom(self, dossier, compte):
        deposer(dossier, compte)
        reception = deposer(dossier, [fictif.achat_crypto()], nom="Camille.csv")
        assert reception.fichier == dossier / "Camille.csv"
        assert ouvert(dossier) == "Camille"


class TestLeMemeComptePlusRecent:
    """L'export du mois suivant contient tout le précédent : il le remplace, sans rien perdre."""

    def test_le_portefeuille_est_mis_a_jour_et_garde_son_nom(self, dossier, compte):
        deposer(dossier, compte[:2], nom="Mon compte.csv")

        reception = deposer(dossier, compte)

        assert portefeuilles(dossier) == ["Mon compte"]
        assert reception.fichier == dossier / "Mon compte.csv"
        assert "« Mon compte » est mis à jour : 1 ligne de plus" in reception.message
        assert "au 10/04/2026" in reception.message
        assert len(depot.lire(dossier).lignes) == 3

    def test_c_est_le_bon_portefeuille_qui_est_mis_a_jour(self, dossier, compte):
        deposer(dossier, compte[:2], nom="Alix.csv")
        deposer(dossier, [fictif.achat_crypto()], nom="Camille.csv")
        de_camille = (dossier / "Camille.csv").read_bytes()

        deposer(dossier, compte)

        assert portefeuilles(dossier) == ["Alix", "Camille"]
        assert (dossier / "Camille.csv").read_bytes() == de_camille
        assert ouvert(dossier) == "Alix"

    def test_le_meme_fichier_redepose_ne_change_rien(self, dossier, compte):
        deposer(dossier, compte)
        avant = (dossier / NOM_DE_LA_BANQUE).stat().st_mtime_ns

        reception = deposer(dossier, compte)

        assert reception.accepte and reception.fichier is None
        assert "déjà là, à l'identique" in reception.message
        assert (dossier / NOM_DE_LA_BANQUE).stat().st_mtime_ns == avant

    def test_les_memes_operations_ecrites_autrement_mettent_a_jour_sans_rien_ajouter(
        self, dossier, compte
    ):
        deposer(dossier, compte)
        reception = deposer(dossier, list(reversed(compte)))
        assert "aucune ligne de plus" in reception.message
        assert portefeuilles(dossier) == ["Exportation de transactions"]

    def test_un_export_complet_remplace_les_exports_partiels_qu_il_contient(self, dossier, compte):
        deposer(dossier, compte[:1], nom="Début.csv")
        deposer(dossier, compte[2:], nom="Fin.csv")

        reception = deposer(dossier, compte)

        assert portefeuilles(dossier) == ["Fin"]
        assert "« Fin » est mis à jour" in reception.message
        assert "Il contient aussi « Début », qu'il remplace" in reception.message
        assert len(depot.lire(dossier).lignes) == 3


class TestUneVersionPlusAncienne:
    def test_elle_n_est_pas_rangee_et_rien_ne_change(self, dossier, compte):
        deposer(dossier, compte, nom="Mon compte.csv")
        avant = (dossier / "Mon compte.csv").read_bytes()

        reception = deposer(dossier, compte[:1])

        assert reception.accepte and reception.fichier is None
        assert "version plus ancienne du portefeuille « Mon compte »" in reception.message
        assert "2 de plus" in reception.message
        assert portefeuilles(dossier) == ["Mon compte"]
        assert (dossier / "Mon compte.csv").read_bytes() == avant


class TestDeuxExportsPartiels:
    def test_ils_ne_sont_pas_assembles_et_pastory_le_dit(self, dossier, compte):
        deposer(dossier, compte[:2], nom="Mon compte.csv")

        reception = deposer(dossier, compte[1:])

        assert portefeuilles(dossier) == ["Mon compte", "Portefeuille"]
        assert "opérations en commun avec « Mon compte » sans le contenir" in reception.message
        assert "toutes les transactions" in reception.message
        assert len(depot.lire(dossier).lignes) == 2


class TestCeQuiNeChangePas:
    def test_un_fichier_qui_n_est_pas_un_export_ne_touche_a_rien(self, dossier, compte):
        deposer(dossier, compte)
        octets = base64.b64encode(b"date;magasin\n2026-01-01;x\n").decode()

        reception = recevoir("courses.csv", "data:text/csv;base64," + octets, dossier)

        assert not reception.accepte
        assert portefeuilles(dossier) == ["Exportation de transactions"]

    def test_aucun_fichier_provisoire_ne_reste_quel_que_soit_le_cas(self, dossier, compte):
        deposer(dossier, compte[:2])
        deposer(dossier, compte)
        deposer(dossier, compte[:1])
        deposer(dossier, [fictif.achat_crypto()])
        assert not [p for p in dossier.iterdir() if p.suffix == EXTENSION_PROVISOIRE]


class TestCeQueLaRelectureATrouve:
    def test_un_fichier_deja_contenu_ne_remplace_pas_un_export_partiel(self, dossier, compte):
        """Un fichier qui contient un export partiel, mais que contient déjà un portefeuille plus
        complet, n'apporte rien : le ranger à la place du partiel ferait lire un historique
        incomplet à côté du complet."""
        deposer(dossier, compte[:1], nom="Partiel.csv")
        export_fictif_complet = fictif.texte_csv(compte).encode("utf-8")
        (dossier / "Complet.csv").write_bytes(export_fictif_complet)
        depot.ouvrir(dossier, "Complet")

        reception = deposer(dossier, compte[:2])

        assert "version plus ancienne du portefeuille « Complet »" in reception.message
        assert reception.fichier is None
        assert ouvert(dossier) == "Complet"
        assert len(depot.lire(dossier / "Partiel.csv").lignes) == 1

    def test_un_portefeuille_ouvert_ailleurs_ne_fait_pas_echouer_le_depot_en_silence(
        self, dossier, compte, monkeypatch
    ):
        """Sous Windows, on ne remplace pas un fichier qu'un autre programme tient ouvert. Avant,
        l'erreur remontait sans un mot, et l'utilisateur croyait son export déposé."""
        deposer(dossier, compte[:2])

        def refuser(self, cible):
            raise PermissionError("le fichier est utilisé par un autre processus")

        monkeypatch.setattr(type(dossier), "replace", refuser)
        reception = deposer(dossier, compte)

        assert reception.accepte is False
        assert "ouvert dans un autre programme" in reception.message
        assert len(depot.lire(dossier).lignes) == 2
        assert not [p for p in dossier.iterdir() if p.suffix == EXTENSION_PROVISOIRE]

    def test_sans_pouvoir_lire_un_portefeuille_on_ne_range_rien(
        self, dossier, compte, monkeypatch
    ):
        """Faute de pouvoir le comparer, le fichier déposé serait pris pour un nouveau compte :
        un doublon du même."""
        deposer(dossier, compte[:2], nom="Mon compte.csv")
        vraie_lecture = depot.fichier.lire

        def lecture(chemin):
            if chemin.name == "Mon compte.csv":
                raise PermissionError("accès refusé")
            return vraie_lecture(chemin)

        monkeypatch.setattr(depot.fichier, "lire", lecture)
        reception = deposer(dossier, compte)

        assert reception.accepte is False
        assert "« Mon compte » ne peut pas être lu" in reception.message
        assert [p.name for p in dossier.glob("*.csv")] == ["Mon compte.csv"]

    def test_un_nouveau_portefeuille_rappelle_qu_une_autre_periode_n_est_pas_assemblee(
        self, dossier, compte
    ):
        deposer(dossier, compte)
        reception = deposer(dossier, [fictif.achat_crypto()])
        assert "même compte sur une autre période" in reception.message

    @pytest.mark.parametrize(
        ("depose", "attendu"),
        [
            ("Exportation de transactions.csv", "Portefeuille"),
            ("Exportation de transactions (2).csv", "Portefeuille"),
            ("Exportation de transactions Camille.csv", "Exportation de transactions Camille"),
            ("Camille.csv", "Camille"),
        ],
    )
    def test_seul_le_nom_de_la_banque_tel_quel_est_remplace(
        self, dossier, compte, depose, attendu
    ):
        """Un fichier que l'on a nommé soi-même, ne serait-ce qu'en ajoutant un mot au nom de
        la banque, garde son nom : c'est souvent le seul indice de son propriétaire."""
        deposer(dossier, compte, nom="Mon compte.csv")
        reception = deposer(dossier, [fictif.achat_crypto()], nom=depose)
        assert reception.fichier.stem == attendu
