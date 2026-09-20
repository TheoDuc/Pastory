"""Les deux CSV du moteur, et surtout : **peut-on refaire un chiffre avec ?**

Le journal est le fichier qui doit permettre de répondre à « d'où sort ce prix de revient ? »
sans lire une ligne de code. Les tests vérifient donc qu'on y retrouve l'état d'avant, ce que
l'opération ajoute ou retire, et l'état d'après — et que les deux se recollent.
"""

from __future__ import annotations

import csv
from decimal import Decimal

from dashboard_tr import tableur
from dashboard_tr.moteur import export_csv
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.pivot.operation import TypeOperation
from tests.moteur.operations_fictives import enchainement_du_glossaire, operation


def relire(fichier):
    with fichier.open(encoding=tableur.ENCODAGE, newline="") as flux:
        return list(csv.DictReader(flux, delimiter=tableur.SEPARATEUR))


def nombre(texte: str) -> Decimal:
    """Relit un nombre écrit pour un tableur français."""
    return Decimal(texte.replace(",", "."))


class TestPositions:
    def test_une_ligne_par_position(self, tmp_path):
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_positions(portefeuille, tmp_path / "positions.csv")

        lignes = relire(fichier)
        assert len(lignes) == 1
        assert lignes[0]["quantite_detenue"] == "15"
        assert lignes[0]["capital_net_investi"] == "375,00"
        assert lignes[0]["prix_de_revient"] == "25,000000"

    def test_une_position_soldee_reste_dans_le_fichier(self, tmp_path):
        # Elle vaut zéro aujourd'hui, mais ses plus-values et ses frais comptent dans les
        # totaux : la faire disparaître les rendrait impossibles à refaire.
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                quantite="4",
                prix_unitaire="25.00",
            ),
            operation(
                TypeOperation.VENTE,
                horodatage="2026-06-05 09:00",
                quantite="4",
                prix_unitaire="30.00",
            ),
        ]
        fichier = export_csv.ecrire_positions(
            Portefeuille.construire(operations), tmp_path / "positions.csv"
        )

        ligne = relire(fichier)[0]
        assert ligne["quantite_detenue"] == "0"
        assert ligne["prix_de_revient"] == tableur.VALEUR_SANS_OBJET
        assert nombre(ligne["plus_values_realisees_brutes"]) == Decimal("20.00")

    def test_une_position_incomplete_porte_une_remarque_en_clair(self, tmp_path):
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.TITRES_RECUS,
                horodatage="2026-03-01 09:00",
                quantite="3",
                prix_a_completer=True,
            ),
        ]
        fichier = export_csv.ecrire_positions(
            Portefeuille.construire(operations), tmp_path / "positions.csv"
        )

        ligne = relire(fichier)[0]
        assert ligne["prix_de_revient"] == tableur.VALEUR_A_COMPLETER
        assert "sous-estimé" in ligne["remarque"]


class TestJournal:
    def test_une_ligne_par_operation_dans_l_ordre_du_temps(self, tmp_path):
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv")

        lignes = relire(fichier)
        assert [ligne["type"] for ligne in lignes] == ["achat", "achat", "vente"]
        assert [ligne["date"] for ligne in lignes] == [
            "2026-01-05",
            "2026-02-05",
            "2026-03-05",
        ]

    def test_chaque_ligne_se_recolle_a_la_precedente(self, tmp_path):
        """C'est ce qui permet de suivre un actif comme un relevé bancaire."""
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv")

        lignes = relire(fichier)
        for precedente, suivante in zip(lignes, lignes[1:], strict=False):
            assert suivante["capital_avant"] == precedente["capital_apres"]
            assert suivante["quantite_avant"] == precedente["quantite_apres"]

    def test_le_capital_d_apres_se_calcule_de_tete(self, tmp_path):
        """capital avant + ajouté − retiré = capital après, sur chaque ligne."""
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv")

        for ligne in relire(fichier):
            attendu = (
                nombre(ligne["capital_avant"])
                + nombre(ligne["capital_ajoute"])
                - nombre(ligne["capital_retire"])
            )
            assert attendu == nombre(ligne["capital_apres"])

    def test_la_plus_value_n_est_ecrite_que_sur_les_ventes(self, tmp_path):
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv")

        lignes = relire(fichier)
        assert lignes[0]["plus_value_brute"] == tableur.VALEUR_SANS_OBJET
        assert nombre(lignes[2]["plus_value_brute"]) == Decimal("75.00")
        assert nombre(lignes[2]["plus_value_nette"]) == Decimal("74.00")

    def test_un_montant_a_completer_le_dit_au_lieu_de_laisser_une_case_vide(self, tmp_path):
        # Une case vide passerait pour un zéro dans un tableur, et les parts sembleraient
        # ne rien valoir au lieu de signaler qu'elles attendent un cours (D-15).
        titres = operation(
            TypeOperation.TITRES_RECUS,
            horodatage="2026-03-01 09:00",
            quantite="3",
            prix_a_completer=True,
        )
        fichier = export_csv.ecrire_journal(
            Portefeuille.construire([titres]), tmp_path / "journal.csv"
        )

        ligne = relire(fichier)[0]
        assert ligne["montant_brut"] == tableur.VALEUR_A_COMPLETER
        assert ligne["prix_unitaire"] == tableur.VALEUR_A_COMPLETER
        assert ligne["capital_ajoute"] == "0,00"

    def test_les_lignes_restent_groupees_par_actif(self, tmp_path):
        operations = [
            *enchainement_du_glossaire(),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-20 09:00",
                actif="XX0000000002",
                quantite="1",
                prix_unitaire="10.00",
            ),
        ]
        fichier = export_csv.ecrire_journal(
            Portefeuille.construire(operations), tmp_path / "journal.csv"
        )

        actifs = [ligne["actif"] for ligne in relire(fichier)]
        assert actifs == ["XX0000000001"] * 3 + ["XX0000000002"]


class TestLisibiliteDansUnTableur:
    def test_les_nombres_ont_une_virgule_decimale(self, tmp_path):
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv")

        assert relire(fichier)[0]["montant_brut"] == "200,00"

    def test_le_fichier_porte_la_marque_utf8_attendue_par_excel(self, tmp_path):
        portefeuille = Portefeuille.construire(enchainement_du_glossaire())
        fichier = export_csv.ecrire_positions(portefeuille, tmp_path / "positions.csv")

        assert fichier.read_bytes().startswith(b"\xef\xbb\xbf")
