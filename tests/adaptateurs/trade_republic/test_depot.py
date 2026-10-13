"""Le dossier de dépôt : un fichier, un portefeuille (D-109) ; la période couverte (D-45)."""

from __future__ import annotations

import os
from datetime import date

import pytest

from pastory.adaptateurs.trade_republic import depot as module_depot
from pastory.adaptateurs.trade_republic.depot import (
    ExportIntrouvable,
    Lien,
    NomRefuse,
    comparer,
    identifiants,
    inventaire,
    lire,
    nom_libre,
    nom_valide,
    ouvrir,
    renommer,
    supprimer,
)
from pastory.adaptateurs.trade_republic.fichier import lire as lire_un_fichier
from tests.adaptateurs.trade_republic import export_fictif as fictif


def test_un_dossier_absent_explique_ou_trouver_l_export(tmp_path):
    with pytest.raises(ExportIntrouvable) as erreur:
        lire(tmp_path / "absent")
    assert module_depot.CHEMIN_DANS_L_APPLICATION in str(erreur.value)
    assert "toutes les transactions" in str(erreur.value)


def test_un_dossier_sans_export_cite_les_fichiers_ecartes(tmp_path):
    (tmp_path / "notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ExportIntrouvable, match="notes.csv"):
        lire(tmp_path)


def test_seuls_les_fichiers_csv_sont_lus(tmp_path):
    fictif.deposer(tmp_path)
    (tmp_path / "all_events.json").write_text("[]", encoding="utf-8")
    depot = lire(tmp_path)
    assert [lu.nom for lu in depot.fichiers] == ["Exportation de transactions.csv"]
    assert depot.fichiers_ignores == []


def test_un_fichier_qui_n_est_pas_un_export_n_est_pas_un_portefeuille(tmp_path):
    fictif.deposer(tmp_path)
    (tmp_path / "account_transactions.csv").write_text("Date;Type\n", encoding="utf-8")

    depot = lire(tmp_path)
    assert len(depot.lignes) == len(fictif.export_type())
    assert [nom for nom, _ in depot.fichiers_ignores] == ["account_transactions.csv"]
    assert depot.autres == []
    assert [p.nom for p in inventaire(tmp_path).portefeuilles] == ["Exportation de transactions"]


def test_un_dossier_nomme_comme_un_csv_est_ignore(tmp_path):
    fictif.deposer(tmp_path)
    (tmp_path / "anciens.csv").mkdir()

    depot = lire(tmp_path)
    assert [lu.nom for lu in depot.fichiers] == ["Exportation de transactions.csv"]


def test_un_fichier_inaccessible_est_cite_et_le_reste_est_lu(tmp_path, monkeypatch):
    # Verrouillé, protégé, ou laissé « dans le nuage » par un service de synchronisation.
    fictif.deposer(tmp_path)
    fictif.deposer(tmp_path, [fictif.vente()], nom="verrouille.csv")
    vraie_lecture = module_depot.fichier.lire

    def lecture(chemin):
        if chemin.name == "verrouille.csv":
            raise PermissionError("accès refusé")
        return vraie_lecture(chemin)

    monkeypatch.setattr(module_depot.fichier, "lire", lecture)
    depot = lire(tmp_path)

    assert len(depot.lignes) == len(fictif.export_type())
    ((nom, raison),) = depot.fichiers_ignores
    assert nom == "verrouille.csv"
    assert "pas pu être ouvert" in raison


class TestUnFichierUnPortefeuille:
    """Le cumul de l'étape 8 ter a mélangé deux comptes dès qu'un proche a déposé son export à
    côté de celui du propriétaire. Désormais Pastory ne lit qu'un fichier : celui qui est ouvert."""

    @pytest.fixture
    def deux_comptes(self, tmp_path):
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne(), fictif.vente()], nom="Alix.csv")
        fictif.deposer(tmp_path, [fictif.achat_crypto()], nom="Camille.csv")
        return tmp_path

    def test_deux_exports_ne_se_cumulent_jamais(self, deux_comptes):
        ouvrir(deux_comptes, "Alix")
        d_alix = lire(deux_comptes)
        ouvrir(deux_comptes, "Camille")
        de_camille = lire(deux_comptes)

        assert (d_alix.portefeuille, len(d_alix.lignes), d_alix.autres) == ("Alix", 2, ["Camille"])
        assert (de_camille.portefeuille, len(de_camille.lignes)) == ("Camille", 1)
        assert not identifiants(d_alix.lignes) & identifiants(de_camille.lignes)

    def test_le_nom_d_un_portefeuille_est_celui_de_son_fichier(self, deux_comptes):
        contenu = inventaire(deux_comptes)
        assert [p.nom for p in contenu.portefeuilles] == ["Alix", "Camille"]
        assert contenu.nomme("Camille").chemin == deux_comptes / "Camille.csv"
        assert contenu.nomme("Personne") is None

    def test_le_portefeuille_ouvert_est_retenu(self, deux_comptes):
        ouvrir(deux_comptes, "Alix")
        assert inventaire(deux_comptes).ouvert.nom == "Alix"
        ouvrir(deux_comptes, "Camille")
        assert inventaire(deux_comptes).ouvert.nom == "Camille"

    def test_sans_choix_retenu_c_est_le_plus_recemment_depose(self, deux_comptes):
        os.utime(deux_comptes / "Alix.csv", (2_000_000_000, 2_000_000_000))
        os.utime(deux_comptes / "Camille.csv", (1_000_000_000, 1_000_000_000))
        assert inventaire(deux_comptes).ouvert.nom == "Alix"

    def test_un_choix_qui_ne_designe_plus_rien_est_oublie(self, deux_comptes):
        (deux_comptes / module_depot.MARQUE).write_text("Disparu.csv", encoding="utf-8")
        assert inventaire(deux_comptes).ouvert is not None

    def test_ouvrir_un_portefeuille_qui_n_existe_pas_se_dit(self, deux_comptes):
        with pytest.raises(ExportIntrouvable, match="Personne"):
            ouvrir(deux_comptes, "Personne")

    def test_on_peut_lire_un_fichier_designe_directement(self, deux_comptes):
        depot = lire(deux_comptes / "Camille.csv")
        assert (depot.portefeuille, len(depot.lignes), depot.autres) == ("Camille", 1, [])

    def test_un_fichier_designe_qui_n_est_pas_un_export_se_dit(self, tmp_path):
        chemin = tmp_path / "notes.csv"
        chemin.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(ExportIntrouvable, match="n'est pas un export"):
            lire(chemin)

    def test_la_marque_n_est_pas_prise_pour_un_portefeuille(self, deux_comptes):
        ouvrir(deux_comptes, "Alix")
        assert len(inventaire(deux_comptes).portefeuilles) == 2


class TestDansUnFichier:
    def test_une_ligne_ecrite_deux_fois_n_est_comptee_qu_une_fois(self, tmp_path):
        commune = fictif.achat_plan_epargne()
        fictif.deposer(tmp_path, [commune, commune, fictif.vente()])

        depot = lire(tmp_path)
        assert len(depot.lignes) == 2
        assert depot.doublons == 1
        assert depot.conflits == []

    def test_deux_versions_d_une_operation_sont_signalees_et_la_premiere_gardee(self, tmp_path):
        originale = fictif.achat_plan_epargne()
        modifiee = originale | {"amount": "-51.00"}
        fictif.deposer(tmp_path, [originale, modifiee])

        depot = lire(tmp_path)
        assert [ligne.amount for ligne in depot.lignes] == ["-50.00"]
        ((gardee, ecartee),) = depot.conflits
        assert (gardee.numero, ecartee.numero) == (2, 3)

    def test_une_ligne_sans_identifiant_n_est_pas_lue(self, tmp_path):
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne(transaction_id="")])
        depot = lire(tmp_path)
        assert depot.lignes == []
        assert len(depot.sans_identifiant) == 1

    def test_la_periode_est_celle_du_fichier_lu_et_de_lui_seul(self, tmp_path):
        for nom, jours in (("a.csv", ("2026-01-10", "2026-03-31")), ("b.csv", ("2025-01-01",))):
            fictif.deposer(
                tmp_path,
                [fictif.paiement_carte(datetime=f"{j}T12:00:00.000Z", date=j) for j in jours],
                nom=nom,
            )
        ouvrir(tmp_path, "a")

        depot = lire(tmp_path)
        assert (depot.premier_jour, depot.dernier_jour) == (date(2026, 1, 10), date(2026, 3, 31))


class TestComparerDeuxExports:
    """C'est ce qui dit, au dépôt, si un fichier est la suite d'un portefeuille ou un autre
    compte — par les identifiants d'opération, jamais par un nom."""

    def ids(self, tmp_path, nom, lignes):
        return identifiants(lire_un_fichier(fictif.deposer(tmp_path, lignes, nom=nom)))

    def test_les_quatre_liens(self, tmp_path):
        achat, vente, dividende = fictif.achat_plan_epargne(), fictif.vente(), fictif.dividende()
        ancien = self.ids(tmp_path, "ancien.csv", [achat, vente])
        recent = self.ids(tmp_path, "recent.csv", [achat, vente, dividende])
        partiel = self.ids(tmp_path, "partiel.csv", [vente, dividende])
        autre = self.ids(tmp_path, "autre.csv", [fictif.achat_crypto()])

        assert comparer(recent, ancien) is Lien.CONTIENT
        assert comparer(ancien, recent) is Lien.CONTENU
        assert comparer(partiel, ancien) is Lien.RECOUPE
        assert comparer(autre, ancien) is Lien.SANS_RAPPORT

    def test_le_meme_export_se_contient(self, tmp_path):
        ancien = self.ids(tmp_path, "ancien.csv", [fictif.achat_plan_epargne()])
        assert comparer(ancien, ancien) is Lien.CONTIENT

    def test_un_export_sans_identifiant_ne_se_compare_a_rien(self, tmp_path):
        ancien = self.ids(tmp_path, "ancien.csv", [fictif.achat_plan_epargne()])
        assert comparer(frozenset(), ancien) is Lien.SANS_RAPPORT
        assert comparer(ancien, frozenset()) is Lien.SANS_RAPPORT


class TestNommer:
    @pytest.mark.parametrize(
        ("saisi", "retenu"),
        [("Camille", "Camille"), ("  Mon   PEA ", "Mon PEA"), ("Camille.csv", "Camille")],
    )
    def test_un_nom_est_nettoye(self, saisi, retenu):
        assert nom_valide(saisi) == retenu

    @pytest.mark.parametrize(
        "refuse",
        ["", "   ", "a/b", "a\\b", "quoi?", 'dit "x"', "a:b", ".cache", "fin.", "CON", "nul"]
        + ["x" * 61],
    )
    def test_un_nom_qui_ne_peut_pas_etre_un_fichier_est_refuse(self, refuse):
        with pytest.raises(NomRefuse):
            nom_valide(refuse)

    def test_un_nom_libre(self, tmp_path):
        assert nom_libre(tmp_path) == "Portefeuille"
        fictif.deposer(tmp_path, nom="Portefeuille.csv")
        assert nom_libre(tmp_path) == "Portefeuille 2"
        fictif.deposer(tmp_path, nom="portefeuille 2.csv")
        assert nom_libre(tmp_path) == "Portefeuille 3"


class TestRenommerEtSupprimer:
    @pytest.fixture
    def dossier(self, tmp_path):
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne()], nom="Alix.csv")
        fictif.deposer(tmp_path, [fictif.achat_crypto()], nom="Camille.csv")
        ouvrir(tmp_path, "Alix")
        return tmp_path

    def test_renommer_garde_le_fichier_et_le_portefeuille_ouvert(self, dossier):
        avant = (dossier / "Alix.csv").read_bytes()

        renomme = renommer(dossier, "Alix", "  Mon compte ")

        assert renomme.nom == "Mon compte"
        assert (dossier / "Mon compte.csv").read_bytes() == avant
        assert not (dossier / "Alix.csv").exists()
        assert inventaire(dossier).ouvert.nom == "Mon compte"

    def test_renommer_un_autre_ne_change_pas_le_portefeuille_ouvert(self, dossier):
        renommer(dossier, "Camille", "Sacha")
        assert inventaire(dossier).ouvert.nom == "Alix"

    def test_un_nom_deja_pris_est_refuse_meme_a_la_casse_pres(self, dossier):
        with pytest.raises(NomRefuse, match="déjà"):
            renommer(dossier, "Alix", "camille")
        assert (dossier / "Alix.csv").exists()

    def test_on_peut_changer_la_seule_casse_d_un_nom(self, dossier):
        assert renommer(dossier, "Alix", "ALIX").nom == "ALIX"

    def test_un_nom_refuse_ne_change_rien(self, dossier):
        with pytest.raises(NomRefuse):
            renommer(dossier, "Alix", "a/b")
        assert [p.nom for p in inventaire(dossier).portefeuilles] == ["Alix", "Camille"]

    def test_supprimer_efface_le_fichier_et_lui_seul(self, dossier):
        supprimer(dossier, "Camille")
        assert [p.nom for p in inventaire(dossier).portefeuilles] == ["Alix"]
        assert inventaire(dossier).ouvert.nom == "Alix"

    def test_le_portefeuille_ouvert_supprime_cede_la_place(self, dossier):
        supprimer(dossier, "Alix")
        assert inventaire(dossier).ouvert.nom == "Camille"
        assert not (dossier / module_depot.MARQUE).exists()

    def test_le_dernier_supprime_il_ne_reste_rien(self, dossier):
        supprimer(dossier, "Alix")
        supprimer(dossier, "Camille")
        assert inventaire(dossier).ouvert is None
        with pytest.raises(ExportIntrouvable):
            lire(dossier)


class TestCeQueLaRelectureATrouve:
    def test_un_portefeuille_illisible_compte_quand_meme(self, tmp_path, monkeypatch):
        """Verrouillé un instant, il sortait de la liste : l'écran disait « Votre livre » sur les
        chiffres d'un autre, et une date de PEA sans nom s'appliquait à ce dernier."""
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne()], nom="Moi.csv")
        fictif.deposer(tmp_path, [fictif.achat_crypto()], nom="Camille.csv")
        ouvrir(tmp_path, "Moi")
        vraie_lecture = module_depot.fichier.lire

        def lecture(chemin):
            if chemin.name == "Moi.csv":
                raise PermissionError("accès refusé")
            return vraie_lecture(chemin)

        monkeypatch.setattr(module_depot.fichier, "lire", lecture)
        contenu = inventaire(tmp_path)

        assert contenu.inaccessibles == ("Moi",)
        assert contenu.nombre == 2
        assert lire(tmp_path).autres == ["Moi"]

    def test_un_fichier_copie_a_la_main_a_cote_de_sa_version_ancienne_se_voit(self, tmp_path):
        """Le dépôt par l'écran remplace l'ancien. Copié à la main dans le dossier, l'export
        récent devient un second portefeuille : on lirait le périmé sans le savoir."""
        achat, vente = fictif.achat_plan_epargne(), fictif.vente()
        fictif.deposer(tmp_path, [achat], nom="Mars.csv")
        fictif.deposer(tmp_path, [achat, vente], nom="Avril.csv")
        fictif.deposer(tmp_path, [fictif.achat_crypto()], nom="Camille.csv")

        ouvrir(tmp_path, "Mars")
        assert lire(tmp_path).plus_a_jour == ["Avril"]
        ouvrir(tmp_path, "Avril")
        assert lire(tmp_path).plus_a_jour == []
        ouvrir(tmp_path, "Camille")
        assert lire(tmp_path).plus_a_jour == []

        mars = inventaire(tmp_path).nomme("Mars")
        assert [(p.nom, lien) for p, lien in inventaire(tmp_path).meme_compte(mars)] == [
            ("Avril", Lien.CONTENU)
        ]

    def test_les_titres_des_autres_portefeuilles_sont_connus(self, tmp_path):
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne()], nom="Moi.csv")
        fictif.deposer(tmp_path, [fictif.achat_crypto()], nom="Camille.csv")
        ouvrir(tmp_path, "Moi")
        assert lire(tmp_path).actifs_des_autres == {fictif.CRYPTO}
