"""Le dossier de dépôt : plusieurs fichiers, doublons, période couverte (D-80, D-45)."""

from __future__ import annotations

from datetime import date

import pytest

from pastory.adaptateurs.trade_republic_officiel import depot as module_depot
from pastory.adaptateurs.trade_republic_officiel.depot import ExportIntrouvable, lire_dossier
from tests.adaptateurs.trade_republic_officiel import export_fictif as fictif


def test_un_dossier_absent_explique_ou_trouver_l_export(tmp_path):
    with pytest.raises(ExportIntrouvable) as erreur:
        lire_dossier(tmp_path / "absent")
    assert module_depot.CHEMIN_DANS_L_APPLICATION in str(erreur.value)
    assert "toutes les transactions" in str(erreur.value)


def test_un_dossier_sans_export_cite_les_fichiers_ecartes(tmp_path):
    (tmp_path / "notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ExportIntrouvable, match="notes.csv"):
        lire_dossier(tmp_path)


def test_seuls_les_fichiers_csv_sont_lus(tmp_path):
    fictif.deposer(tmp_path)
    (tmp_path / "all_events.json").write_text("[]", encoding="utf-8")
    depot = lire_dossier(tmp_path)
    assert [lu.nom for lu in depot.fichiers] == ["Exportation de transactions.csv"]
    assert depot.fichiers_ignores == []


def test_un_fichier_qui_n_est_pas_un_export_n_arrete_pas_la_lecture(tmp_path):
    fictif.deposer(tmp_path)
    (tmp_path / "account_transactions.csv").write_text("Date;Type\n", encoding="utf-8")
    depot = lire_dossier(tmp_path)
    assert len(depot.lignes) == len(fictif.export_type())
    assert [nom for nom, _ in depot.fichiers_ignores] == ["account_transactions.csv"]


class TestPlusieursFichiers:
    def test_une_operation_presente_dans_deux_fichiers_n_est_comptee_qu_une_fois(self, tmp_path):
        commune = fictif.achat_plan_epargne()
        fictif.deposer(tmp_path, [commune, fictif.vente()], nom="ancien.csv")
        fictif.deposer(tmp_path, [commune, fictif.dividende()], nom="recent.csv")

        depot = lire_dossier(tmp_path)
        assert len(depot.lignes) == 3
        assert depot.doublons == 1
        assert depot.conflits == []

    def test_deux_versions_d_une_operation_sont_signalees_et_la_premiere_gardee(self, tmp_path):
        originale = fictif.achat_plan_epargne()
        modifiee = originale | {"amount": "-51.00"}
        fictif.deposer(tmp_path, [originale], nom="a.csv")
        fictif.deposer(tmp_path, [modifiee], nom="b.csv")

        depot = lire_dossier(tmp_path)
        assert [ligne.amount for ligne in depot.lignes] == ["-50.00"]
        ((gardee, ecartee),) = depot.conflits
        assert (gardee.fichier, ecartee.fichier) == ("a.csv", "b.csv")

    def test_une_ligne_sans_identifiant_n_est_pas_lue(self, tmp_path):
        fictif.deposer(tmp_path, [fictif.achat_plan_epargne(transaction_id="")])
        depot = lire_dossier(tmp_path)
        assert depot.lignes == []
        assert len(depot.sans_identifiant) == 1


class TestPeriode:
    def fichier(self, dossier, nom, *jours):
        lignes = [
            fictif.paiement_carte(datetime=f"{jour}T12:00:00.000Z", date=jour) for jour in jours
        ]
        fictif.deposer(dossier, lignes, nom=nom)

    def test_la_periode_d_un_fichier_et_du_tout(self, tmp_path):
        self.fichier(tmp_path, "a.csv", "2026-01-10", "2026-03-31")
        self.fichier(tmp_path, "b.csv", "2026-03-15", "2026-06-30")

        depot = lire_dossier(tmp_path)
        assert [(lu.premier_jour, lu.dernier_jour) for lu in depot.fichiers] == [
            (date(2026, 1, 10), date(2026, 3, 31)),
            (date(2026, 3, 15), date(2026, 6, 30)),
        ]
        assert (depot.premier_jour, depot.dernier_jour) == (date(2026, 1, 10), date(2026, 6, 30))
        assert depot.trous() == []

    def test_deux_fichiers_qui_se_suivent_ne_font_pas_de_trou(self, tmp_path):
        self.fichier(tmp_path, "a.csv", "2026-01-10", "2026-03-31")
        self.fichier(tmp_path, "b.csv", "2026-04-01", "2026-06-30")
        assert lire_dossier(tmp_path).trous() == []

    def test_un_trou_entre_deux_fichiers_est_dit(self, tmp_path):
        self.fichier(tmp_path, "a.csv", "2026-01-10", "2026-03-31")
        self.fichier(tmp_path, "b.csv", "2026-05-01", "2026-06-30")

        (trou,) = lire_dossier(tmp_path).trous()
        assert (trou.du, trou.au) == (date(2026, 4, 1), date(2026, 4, 30))

    def test_un_fichier_englobe_ne_cree_pas_de_trou(self, tmp_path):
        self.fichier(tmp_path, "a.csv", "2026-01-01", "2026-12-31")
        self.fichier(tmp_path, "b.csv", "2026-03-01", "2026-03-31")
        self.fichier(tmp_path, "c.csv", "2026-11-01", "2027-01-31")
        assert lire_dossier(tmp_path).trous() == []
