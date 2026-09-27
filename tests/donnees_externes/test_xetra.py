"""La liste des ETF de Xetra : les quatre pièges du fichier, et ce qu'on en tire.

Aucun test ne sort de la machine : le fichier est **fabriqué ici**, avec la même forme que
celui de Deutsche Börse (un `.xlsx` sous une extension `.xls`). Valeurs fictives (D-03).
"""

from __future__ import annotations

import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest

from dashboard_tr.donnees_externes import xetra
from dashboard_tr.donnees_externes.cours import ErreurDeSource

ETF = "IE00EXEMPLE001"
ETF_DIST = "IE00EXEMPLE002"
ETN = "DE00EXEMPLE003"

ENTETE = [
    "PRODUCT TYPE",
    "PRODUCT NAME",
    "ISIN",
    "ONGOING CHARGES",
    "USE OF PROFITS",
    "TRADING CURRENCY",
]


def fabriquer(rangees: list[list[str]], avec_date: str | None = "As of 28/09/2026") -> bytes:
    """Un `.xlsx` minimal : une feuille, des chaînes en ligne, comme le vrai fichier."""
    toutes = []
    if avec_date is not None:
        toutes.append([avec_date])
    toutes.append([])
    toutes.append(ENTETE)
    toutes.extend(rangees)

    corps = []
    for numero, rangee in enumerate(toutes, start=1):
        corps.append(f'<row r="{numero}">')
        for cellule in rangee:
            echappe = cellule.replace("&", "&amp;").replace("<", "&lt;")
            corps.append(f'<c t="inlineStr"><is><t>{echappe}</t></is></c>')
        corps.append("</row>")

    feuille = (
        '<?xml version="1.0"?><worksheet '
        'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + "".join(corps)
        + "</sheetData></worksheet>"
    )
    tampon = BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", feuille)
    return tampon.getvalue()


def ligne(isin, charges, type_produit="ETF", nom="ETF Exemple", politique="Accumulating"):
    return [type_produit, nom, isin, charges, politique, "EUR"]


class TestLectureDuFichier:
    def test_un_etf_donne_son_ter_en_pour_cent(self):
        """La source écrit une **fraction** : 0.002 veut dire 0,20 %."""
        liste = xetra.lire(fabriquer([ligne(ETF, "0.002")]))

        frais = liste.frais_courants(ETF)
        assert frais is not None
        assert frais.ter_pour_cent == Decimal("0.2")
        assert frais.politique == "Accumulating"
        assert frais.nom == "ETF Exemple"
        assert "Xetra" in frais.source

    def test_le_bruit_de_flottant_de_la_source_est_arrondi(self):
        """Vérifié en direct : la source écrit « 0.0007000000000000001 » pour 0,07 %."""
        liste = xetra.lire(fabriquer([ligne(ETF, "0.0007000000000000001")]))

        assert liste.frais_courants(ETF).ter_pour_cent == Decimal("0.07")

    def test_la_date_d_effet_est_lue(self):
        liste = xetra.lire(fabriquer([ligne(ETF, "0.002")]))

        assert liste.date == date(2026, 9, 28)
        assert liste.frais_courants(ETF).date == date(2026, 9, 28)

    def test_un_fichier_sans_date_se_lit_quand_meme(self):
        """La date aide à vérifier, elle ne conditionne pas la lecture."""
        liste = xetra.lire(fabriquer([ligne(ETF, "0.002")], avec_date=None))

        assert liste.date is None
        assert liste.frais_courants(ETF) is not None

    def test_deux_parts_du_meme_fonds_restent_distinctes(self):
        """La clé est l'ISIN : une part capitalisante et une distribuante ont deux valeurs."""
        liste = xetra.lire(
            fabriquer(
                [
                    ligne(ETF, "0.002"),
                    ligne(ETF_DIST, "0.005", politique="Distributing"),
                ]
            )
        )

        assert liste.frais_courants(ETF).ter_pour_cent == Decimal("0.2")
        assert liste.frais_courants(ETF_DIST).ter_pour_cent == Decimal("0.5")

    def test_un_isin_repete_par_devise_ne_compte_qu_une_fois(self):
        liste = xetra.lire(fabriquer([ligne(ETF, "0.002"), ligne(ETF, "0.002")]))

        assert len(liste) == 1

    def test_ce_qui_n_est_pas_un_fonds_est_ecarte(self):
        """Un ETN ou un ETC n'est pas un fonds : ses frais ne se lisent pas ainsi."""
        liste = xetra.lire(
            fabriquer([ligne(ETF, "0.002"), ligne(ETN, "0.008", type_produit="ETN")])
        )

        assert liste.frais_courants(ETN) is None
        assert len(liste) == 1

    def test_un_etf_actif_est_retenu(self):
        liste = xetra.lire(fabriquer([ligne(ETF, "0.004", type_produit="Active ETF")]))

        assert liste.frais_courants(ETF) is not None

    def test_un_actif_absent_ne_donne_rien(self):
        liste = xetra.lire(fabriquer([ligne(ETF, "0.002")]))

        assert liste.frais_courants("IE00INCONNU0001") is None

    def test_une_ligne_sans_valeur_est_ignoree_sans_faire_echouer_le_reste(self):
        liste = xetra.lire(fabriquer([ligne(ETF_DIST, ""), ligne(ETF, "0.002")]))

        assert liste.frais_courants(ETF_DIST) is None
        assert liste.frais_courants(ETF) is not None


class TestVraisemblance:
    def test_une_valeur_hors_fourchette_n_est_pas_proposee(self):
        """Un TER de 20 % vient d'une erreur d'unité : mieux vaut ne rien proposer."""
        liste = xetra.lire(fabriquer([ligne(ETF, "0.20")]))

        assert liste.frais_courants(ETF) is None

    def test_un_ter_nul_n_est_pas_propose(self):
        liste = xetra.lire(fabriquer([ligne(ETF, "0")]))

        assert liste.frais_courants(ETF) is None


class TestCeQuiEstRefuse:
    def test_un_fichier_qui_n_est_pas_un_xlsx_est_refuse_avec_son_piege(self):
        with pytest.raises(ErreurDeSource, match=r"\.xls"):
            xetra.lire(b"ce n'est pas une archive")

    def test_un_fichier_sans_les_colonnes_attendues_le_dit(self):
        tampon = BytesIO()
        with zipfile.ZipFile(tampon, "w") as archive:
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                '<?xml version="1.0"?><worksheet '
                'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<sheetData></sheetData></worksheet>",
            )
        with pytest.raises(ErreurDeSource, match="colonnes attendues"):
            xetra.lire(tampon.getvalue())

    def test_un_fichier_sans_aucune_ligne_exploitable_le_dit(self):
        with pytest.raises(ErreurDeSource, match="aucune ligne"):
            xetra.lire(fabriquer([ligne(ETN, "0.008", type_produit="ETN")]))


class TestTelechargement:
    """Le lien change à chaque publication : il est lu sur la page, jamais mémorisé."""

    def test_le_lien_est_trouve_sur_la_page_puis_le_fichier_est_lu(self):
        fichier = fabriquer([ligne(ETF, "0.002")])
        page = (
            '<html><a href="/resource/blob/1553442/abcdef/data/'
            'Master_DataSheet_Download.xls">Download</a></html>'
        )
        demandees = []

        def ouvrir(adresse):
            demandees.append(adresse)
            return fichier if adresse.endswith(".xls") else page.encode("utf-8")

        liste = xetra.telecharger(ouvrir)

        assert liste.frais_courants(ETF).ter_pour_cent == Decimal("0.2")
        assert demandees[0] == xetra.ADRESSE_PAGE
        assert demandees[1].startswith("https://www.cashmarket.deutsche-boerse.com/resource/")

    def test_une_page_qui_a_change_de_forme_le_dit(self):
        with pytest.raises(ErreurDeSource, match="changé de forme"):
            xetra.telecharger(lambda adresse: b"<html>plus de lien</html>")


# --- Défaut trouvé à la relecture indépendante ----------------------------------------


def fabriquer_avec_trous(cellules_par_rangee: list[list[tuple[str, str]]]) -> bytes:
    """Un `.xlsx` qui **omet les cellules vides**, comme le fait un vrai fichier.

    Chaque cellule est donnée par sa référence (« C3 ») et son contenu : c'est ainsi qu'un
    tableur écrit une ligne dont des cases sont vides, et c'est le cas que la lecture par rang
    ne voyait pas.
    """
    corps = []
    for numero, cellules in enumerate(cellules_par_rangee, start=1):
        corps.append(f'<row r="{numero}">')
        for reference, contenu in cellules:
            echappe = contenu.replace("&", "&amp;").replace("<", "&lt;")
            corps.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{echappe}</t></is></c>'
            )
        corps.append("</row>")
    feuille = (
        '<?xml version="1.0"?><worksheet '
        'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + "".join(corps)
        + "</sheetData></worksheet>"
    )
    tampon = BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", feuille)
    return tampon.getvalue()


class TestCellulesOmises:
    """Trouvé à la relecture : un `.xlsx` n'écrit pas les cellules vides. Lire les cellules
    dans l'ordre où elles arrivent décale donc tout le tableau, et on lit un ISIN dans la
    colonne du nom, ou un TER dans celle de la devise — un chiffre plausible et faux."""

    def test_une_ligne_dont_une_case_est_vide_reste_bien_lue(self):
        # Colonne B (le nom) absente : les cellules écrites sont A, C, D, E.
        contenu = fabriquer_avec_trous(
            [
                [("A1", "As of 28/09/2026")],
                [],
                [
                    ("A3", "PRODUCT TYPE"),
                    ("B3", "PRODUCT NAME"),
                    ("C3", "ISIN"),
                    ("D3", "ONGOING CHARGES"),
                    ("E3", "USE OF PROFITS"),
                ],
                [("A4", "ETF"), ("C4", ETF), ("D4", "0.002"), ("E4", "Accumulating")],
            ]
        )

        liste = xetra.lire(contenu)

        frais = liste.frais_courants(ETF)
        assert frais is not None
        assert frais.ter_pour_cent == Decimal("0.2")
        assert frais.politique == "Accumulating"
        assert frais.nom is None

    def test_un_entete_dont_une_colonne_est_vide_se_repere_quand_meme(self):
        contenu = fabriquer_avec_trous(
            [
                [("A1", "PRODUCT TYPE"), ("C1", "ISIN"), ("E1", "ONGOING CHARGES")],
                [("A2", "ETF"), ("C2", ETF), ("E2", "0.0007")],
            ]
        )

        liste = xetra.lire(contenu)

        assert liste.frais_courants(ETF).ter_pour_cent == Decimal("0.07")

    def test_une_colonne_au_dela_de_la_vingt_sixieme_est_bien_placee(self):
        """« AA » vaut 26, pas 0 : une liste large ne doit pas replier ses colonnes."""
        contenu = fabriquer_avec_trous(
            [
                [("A1", "PRODUCT TYPE"), ("B1", "ISIN"), ("AA1", "ONGOING CHARGES")],
                [("A2", "ETF"), ("B2", ETF), ("AA2", "0.0015")],
            ]
        )

        liste = xetra.lire(contenu)

        assert liste.frais_courants(ETF).ter_pour_cent == Decimal("0.15")
