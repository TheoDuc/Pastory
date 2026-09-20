"""La lecture du portefeuille écrit par `pytr portfolio`.

**Valeurs entièrement fictives** (D-03). Ce qui compte ici : le fichier est produit par un
outil extérieur, dont le format peut changer sans prévenir. La lecture doit donc refuser ce
qu'elle ne comprend pas plutôt que de le deviner — c'est la même règle que pour les nombres
de l'étape 2 (inventaire §11.1).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from dashboard_tr.adaptateurs.trade_republic import portefeuille

ENTETE = "Name;ISIN;quantity;price;avgCost;netValue"


def deposer(dossier, *lignes: str):
    fichier = portefeuille.chemin(dossier)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8")
    return fichier


class TestLecture:
    def test_une_position_se_lit_entierement(self, tmp_path):
        fichier = deposer(tmp_path, "ETF Exemple Monde;XX0000000001;12.5;30.1;25.4;376.25")

        positions, anomalies = portefeuille.lire(fichier)

        assert anomalies == []
        assert len(positions) == 1
        position = positions[0]
        assert position.actif == "XX0000000001"
        assert position.quantite == Decimal("12.5")
        assert position.nom_actif == "ETF Exemple Monde"
        assert position.prix_de_revient_banque == Decimal("25.4")

    def test_une_quantite_de_crypto_garde_ses_six_decimales(self, tmp_path):
        fichier = deposer(tmp_path, "Crypto Exemple;XF000ABCDEF1;0.001233;30000;29000;36.99")

        positions, _ = portefeuille.lire(fichier)

        assert positions[0].quantite == Decimal("0.001233")

    def test_un_fichier_sans_position_se_lit_sans_erreur(self, tmp_path):
        # Un portefeuille vide est une information, pas une panne.
        positions, anomalies = portefeuille.lire(deposer(tmp_path))

        assert positions == []
        assert anomalies == []

    def test_un_nom_contenant_un_point_virgule_ne_fait_pas_perdre_la_position(self, tmp_path):
        # pytr n'entoure jamais les valeurs de guillemets : un nom de société avec un
        # point-virgule produit une colonne de trop. On recolle le nom, jamais un nombre.
        fichier = deposer(tmp_path, "Exemple SA; filiale;XX0000000001;3;10;10;30")

        positions, anomalies = portefeuille.lire(fichier)

        assert anomalies == []
        assert positions[0].actif == "XX0000000001"
        assert positions[0].quantite == Decimal("3")
        assert positions[0].nom_actif == "Exemple SA; filiale"


class TestCeQuiEstRefuse:
    def test_une_quantite_a_virgule_decimale_est_refusee_pas_devinee(self, tmp_path):
        # Le fichier est demandé à pytr sans localisation des nombres : une virgule
        # signifierait que le format a changé, et la deviner donnerait des quantités
        # fausses sans que rien ne le signale.
        fichier = deposer(tmp_path, "Exemple;XX0000000001;12,5;30;25;375")

        positions, anomalies = portefeuille.lire(fichier)

        assert positions == []
        assert len(anomalies) == 1
        assert "quantité illisible" in anomalies[0]

    def test_une_ligne_sans_actif_est_ecartee_et_dite(self, tmp_path):
        fichier = deposer(tmp_path, "Exemple;;3;10;10;30")

        positions, anomalies = portefeuille.lire(fichier)

        assert positions == []
        assert "aucun identifiant d'actif" in anomalies[0]

    def test_une_ligne_ecartee_n_empeche_pas_les_autres(self, tmp_path):
        fichier = deposer(
            tmp_path,
            "Exemple;;3;10;10;30",
            "Autre Exemple;XX0000000002;5;20;18;100",
        )

        positions, anomalies = portefeuille.lire(fichier)

        assert [position.actif for position in positions] == ["XX0000000002"]
        assert len(anomalies) == 1

    def test_des_colonnes_inattendues_arretent_la_lecture(self, tmp_path):
        fichier = portefeuille.chemin(tmp_path)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text("colonne;autre\n1;2\n", encoding="utf-8")

        with pytest.raises(portefeuille.PortefeuilleIllisible) as erreur:
            portefeuille.lire(fichier)

        assert "ISIN" in str(erreur.value)

    def test_un_fichier_absent_dit_quoi_faire(self, tmp_path):
        with pytest.raises(portefeuille.PortefeuilleIllisible) as erreur:
            portefeuille.lire(portefeuille.chemin(tmp_path))

        assert "positions-reelles" in str(erreur.value)

    def test_un_prix_de_revient_illisible_laisse_la_position_utilisable(self, tmp_path):
        # Ce n'est qu'une information (D-46) : la quantité, elle, reste un contrôle valable.
        fichier = deposer(tmp_path, "Exemple;XX0000000001;3;10;n/a;30")

        positions, anomalies = portefeuille.lire(fichier)

        assert anomalies == []
        assert positions[0].quantite == Decimal("3")
        assert positions[0].prix_de_revient_banque is None
