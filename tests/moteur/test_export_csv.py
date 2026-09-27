"""Les deux CSV du moteur, et surtout : **peut-on refaire un chiffre avec ?**

Le journal est le fichier qui doit permettre de répondre à « d'où sort ce prix de revient ? »
sans lire une ligne de code. Les tests vérifient donc qu'on y retrouve l'état d'avant, ce que
l'opération ajoute ou retire, et l'état d'après — et que les deux se recollent.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from dashboard_tr import tableur
from dashboard_tr.moteur import export_csv, valorisation
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rendements import Periode, synthese
from dashboard_tr.pivot.operation import Poche, TypeOperation
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation

AUTRE_ACTIF = "XX0000000002"


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


# --- Les fichiers de l'étape 5 ------------------------------------------------------------


def portefeuille_a_deux_actifs() -> Portefeuille:
    """L'enchaînement du glossaire (CTO), plus un actif en PEA entièrement revendu."""
    return Portefeuille.construire(
        [
            *enchainement_du_glossaire(),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-10 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.PEA,
                quantite="4",
                prix_unitaire="50.00",
            ),
            operation(
                TypeOperation.VENTE,
                horodatage="2026-02-10 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.PEA,
                quantite="4",
                prix_unitaire="55.00",
            ),
        ]
    )


def source_a_deux_actifs() -> SourceFixe:
    return SourceFixe(
        {
            **cours_constant(ACTIF, "40.00", date(2026, 1, 1), date(2026, 3, 31)),
            **cours_constant(AUTRE_ACTIF, "50.00", date(2026, 1, 1), date(2026, 3, 31)),
        }
    )


def synthese_a_deux_actifs():
    return synthese(
        portefeuille_a_deux_actifs(), Periode(date(2026, 3, 31)), source_a_deux_actifs()
    )


class TestValorisation:
    def test_une_ligne_par_position_soldee_comprise(self, tmp_path):
        fichier = export_csv.ecrire_valorisation(
            portefeuille_a_deux_actifs(), synthese_a_deux_actifs(), tmp_path / "v.csv"
        )

        lignes = relire(fichier)
        assert [ligne["actif"] for ligne in lignes] == [ACTIF, AUTRE_ACTIF]
        detenue, soldee = lignes
        assert detenue["quantite"] == "15"
        assert detenue["cours"] == "40,00"
        assert detenue["valeur"] == "600,00"
        assert detenue["plus_value_latente"] == "225,00"
        assert detenue["gain"] == "300,00"
        assert detenue["twrr"] == "0,000000"  # 40 tout le temps : la stratégie n'a rien fait
        # La position soldée vaut zéro, mais elle a un gain : 220 - 200.
        assert soldee["quantite"] == "0"
        assert soldee["valeur"] == "0,00"
        assert soldee["gain"] == "20,00"

    def test_la_colonne_gain_s_additionne_en_le_gain_total(self, tmp_path):
        resultat = synthese_a_deux_actifs()
        fichier = export_csv.ecrire_valorisation(
            portefeuille_a_deux_actifs(), resultat, tmp_path / "v.csv"
        )

        somme = sum(nombre(ligne["gain"]) for ligne in relire(fichier))
        assert somme == resultat.total.gain == Decimal("320.00")

    def test_une_position_sans_cours_est_ecrite_sans_zero(self, tmp_path):
        portefeuille = portefeuille_a_deux_actifs()
        source = SourceFixe(
            cours_constant(AUTRE_ACTIF, "50.00", date(2026, 1, 1), date(2026, 3, 31))
        )
        resultat = synthese(portefeuille, Periode(date(2026, 3, 31)), source)

        fichier = export_csv.ecrire_valorisation(portefeuille, resultat, tmp_path / "v.csv")

        sans_cours = relire(fichier)[0]
        assert sans_cours["valeur"] == tableur.VALEUR_SANS_OBJET
        assert sans_cours["cours"] == tableur.VALEUR_SANS_OBJET
        assert sans_cours["gain"] == tableur.VALEUR_SANS_OBJET
        assert "Cours de marché" in sans_cours["remarque"]


class TestFlux:
    def test_la_table_du_total_commence_par_les_flux_et_finit_par_la_valeur(self, tmp_path):
        fichier = export_csv.ecrire_flux(synthese_a_deux_actifs(), tmp_path / "flux.csv")

        total = [ligne for ligne in relire(fichier) if ligne["groupe"] == "total"]
        assert [(ligne["date"], ligne["montant"]) for ligne in total] == [
            ("2026-01-05", "-200,00"),
            ("2026-01-10", "-200,00"),
            ("2026-02-05", "-300,00"),
            ("2026-02-10", "220,00"),
            ("2026-03-05", "200,00"),
            ("2026-03-31", "600,00"),
        ]
        assert total[-1]["libelle"] == "valeur à la fin"
        # -200 - 200 - 300 + 220 + 200 + 600 = 320 : c'est le gain, et c'est la table
        # qu'on colle dans TRI.PAIEMENTS.
        assert sum(nombre(ligne["montant"]) for ligne in total) == Decimal("320.00")

    def test_chaque_poche_et_chaque_position_a_sa_table(self, tmp_path):
        fichier = export_csv.ecrire_flux(synthese_a_deux_actifs(), tmp_path / "flux.csv")

        groupes = {ligne["groupe"] for ligne in relire(fichier)}
        assert groupes == {"total", "CTO", "PEA", f"{ACTIF} (CTO)", f"{AUTRE_ACTIF} (PEA)"}

    def test_la_valeur_au_debut_est_un_flux_negatif_a_la_veille(self, tmp_path):
        resultat = synthese(
            portefeuille_a_deux_actifs(),
            Periode(fin=date(2026, 3, 31), debut=date(2026, 3, 1)),
            source_a_deux_actifs(),
        )
        fichier = export_csv.ecrire_flux(resultat, tmp_path / "flux.csv")

        premiere = next(ligne for ligne in relire(fichier) if ligne["groupe"] == "total")
        assert premiere["date"] == "2026-02-28"
        assert premiere["montant"] == "-800,00"  # 20 parts x 40
        assert premiere["libelle"] == "valeur au début"


class TestSousPeriodes:
    def test_le_produit_des_rendements_redonne_le_twrr(self, tmp_path):
        source = SourceFixe(
            {
                ACTIF: {
                    date(2026, 1, 5): "20.00",
                    date(2026, 2, 5): "22.00",
                    date(2026, 3, 5): "24.20",
                    date(2026, 3, 31): "24.20",
                }
            }
        )
        resultat = synthese(
            Portefeuille.construire(enchainement_du_glossaire()), Periode(date(2026, 3, 31)), source
        )
        fichier = export_csv.ecrire_sous_periodes(resultat, tmp_path / "sp.csv")

        total = [ligne for ligne in relire(fichier) if ligne["groupe"] == "total"]
        produit = Decimal("1")
        for ligne in total:
            produit *= Decimal("1") + nombre(ligne["rendement"])
        assert [ligne["rendement"] for ligne in total] == ["0,100000", "0,100000", "0,000000"]
        assert (produit - 1).quantize(Decimal("0.000001")) == resultat.total.twrr.taux
        assert total[0]["valeur_debut"] == "200,00"
        assert total[0]["flux"] == "200,00"
        assert total[0]["valeur_fin"] == "220,00"


class TestEvolution:
    def test_une_colonne_par_poche_tiree_de_l_enumeration(self):
        # Une poche de plus ne peut pas manquer au fichier sans manquer partout ailleurs : la
        # somme des colonnes de poche doit toujours retomber sur le total.
        for poche in Poche:
            assert f"valeur_{poche.value}" in export_csv.COLONNES_EVOLUTION

    def test_un_jour_par_ligne_avec_les_poches(self, tmp_path):
        points = valorisation.evolution(
            portefeuille_a_deux_actifs(),
            date(2026, 1, 9),
            date(2026, 1, 11),
            source_a_deux_actifs(),
        )
        fichier = export_csv.ecrire_evolution(points, tmp_path / "evolution.csv")

        lignes = relire(fichier)
        assert [ligne["date"] for ligne in lignes] == ["2026-01-09", "2026-01-10", "2026-01-11"]
        assert lignes[0]["valeur_totale"] == "400,00"  # 10 parts x 40
        assert lignes[1]["valeur_totale"] == "600,00"  # + 4 parts x 50
        assert lignes[1]["valeur_PEA"] == "200,00"
        assert lignes[1]["valeur_CTO"] == "400,00"
        assert lignes[1]["valeur_crypto"] == "0,00"
        assert lignes[1]["capital_net_investi"] == "400,00"
        assert lignes[1]["positions_non_valorisees"] == "0"


# --- Étape 6 : le prix de revient fiscal, et les deux fichiers de plus ------------------


def test_le_journal_porte_le_prix_de_revient_fiscal(tmp_path):
    """D-57 : c'est la colonne qui permet de refaire l'impôt à la main, ligne par ligne."""
    portefeuille = Portefeuille.construire(enchainement_du_glossaire())

    lignes = relire(export_csv.ecrire_journal(portefeuille, tmp_path / "journal.csv"))

    premier = lignes[0]
    # 201 € payés pour 10 parts : 20,10 € fiscal contre 20,00 € de prix de revient.
    assert nombre(premier["capital_apres"]) == Decimal("200.00")
    assert nombre(premier["capital_fiscal_apres"]) == Decimal("201.00")
    assert premier["prix_de_revient_apres"] == "20,000000"
    assert premier["prix_de_revient_fiscal_apres"] == "20,100000"
