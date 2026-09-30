"""L'export CSV du pivot : le fichier que le propriétaire ouvre dans un tableur.

Ce qui compte ici n'est pas le format en soi, mais qu'on **puisse s'y fier** : une valeur
manquante doit se voir, et un nombre doit s'ouvrir correctement dans un tableur français.
"""

from __future__ import annotations

import csv

from pastory.pivot import export_csv
from tests.pivot import exemples


def relire(fichier):
    with fichier.open(encoding="utf-8-sig", newline="") as flux:
        return list(csv.DictReader(flux, delimiter=export_csv.SEPARATEUR))


class TestContenu:
    def test_chaque_operation_donne_une_ligne(self, tmp_path):
        operations = [construire() for construire in exemples.TOUS_LES_EXEMPLES]
        fichier = export_csv.ecrire(operations, tmp_path / "operations.csv")

        lignes = relire(fichier)
        assert len(lignes) == len(operations)
        assert lignes[0]["identifiant"] == operations[0].identifiant

    def test_les_colonnes_suivent_l_ordre_du_format(self, tmp_path):
        fichier = export_csv.ecrire([exemples.achat_plan_epargne()], tmp_path / "o.csv")

        colonnes = list(relire(fichier)[0])
        assert colonnes.index("quantite") < colonnes.index("prix_unitaire")
        assert colonnes.index("prix_unitaire") < colonnes.index("montant_brut")

    def test_l_origine_de_chaque_valeur_suit_la_valeur(self, tmp_path):
        fichier = export_csv.ecrire([exemples.achat_plan_epargne()], tmp_path / "o.csv")

        ligne = relire(fichier)[0]
        assert ligne["origine quantite"] == "texte"
        assert ligne["origine montant_regle"] == "donnee"
        assert ligne["origine poche"] == "deduction"


class TestLisibiliteDansUnTableur:
    def test_les_nombres_ont_une_virgule_decimale(self, tmp_path):
        # Avec un point, un tableur français lirait « 25.00 » comme du texte, ou pire,
        # comme une date.
        fichier = export_csv.ecrire([exemples.achat_plan_epargne()], tmp_path / "o.csv")

        ligne = relire(fichier)[0]
        assert ligne["prix_unitaire"] == "25,00"
        assert ligne["montant_brut"] == "50,00"

    def test_le_fichier_porte_la_marque_utf8_attendue_par_excel(self, tmp_path):
        fichier = export_csv.ecrire([exemples.achat_plan_epargne()], tmp_path / "o.csv")
        assert fichier.read_bytes().startswith(b"\xef\xbb\xbf")


class TestValeursManquantes:
    def test_un_montant_a_completer_le_dit_au_lieu_de_laisser_une_case_vide(self, tmp_path):
        # Une case vide passerait pour un zéro une fois dans un tableur, et l'opération
        # semblerait ne rien valoir au lieu de signaler qu'elle attend un cours (D-15).
        fichier = export_csv.ecrire(
            [exemples.titres_recus_prix_a_completer()], tmp_path / "o.csv"
        )

        ligne = relire(fichier)[0]
        assert ligne["montant_brut"] == export_csv.VALEUR_A_COMPLETER
        assert ligne["origine montant_brut"] == "a_completer"
