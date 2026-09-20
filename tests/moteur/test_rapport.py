"""Le rapport affiché par `dashboard positions`.

On n'y vérifie pas la mise en page, mais ce qui ne doit **jamais** manquer : ce qui est
incertain est dit, la performance et les coûts ne se mélangent pas, et le tout s'affiche sur
une console Windows.
"""

from __future__ import annotations

from decimal import Decimal

from dashboard_tr.moteur import rapport as rapport_moteur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rapprochement import rapprocher
from dashboard_tr.pivot.operation import Poche, TypeOperation
from dashboard_tr.pivot.position_reelle import PositionReelle
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation


def portefeuille_complet() -> Portefeuille:
    return Portefeuille.construire(enchainement_du_glossaire())


def portefeuille_incomplet() -> Portefeuille:
    return Portefeuille.construire(
        [
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
    )


class TestCeQuiDoitYEtre:
    def test_les_positions_detenues_apparaissent_avec_leurs_chiffres(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert ACTIF in texte
        assert "375,00" in texte  # capital net investi
        assert "25,00" in texte  # prix de revient

    def test_la_performance_et_les_couts_sont_deux_blocs_distincts(self):
        """D-21 : les frais et les taxes ne se mélangent jamais aux montants bruts."""
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "Coûts réellement payés" in texte
        assert texte.index("Ce qui est placé") < texte.index("Coûts réellement payés")

    def test_le_rapport_dit_ce_qui_n_est_pas_encore_calculable(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "TRI" in texte
        assert "étapes 4 et 5" in texte

    def test_le_rapport_previent_qu_il_contient_des_chiffres_personnels(self):
        assert "pas fait pour être partagé" in rapport_moteur.resume(portefeuille_complet())


class TestCeQuiEstIncertain:
    def test_une_position_incomplete_est_mise_en_avant(self):
        texte = rapport_moteur.resume(portefeuille_incomplet())

        assert "histoire est incomplète" in texte
        assert "sous-estimé" in texte

    def test_le_prix_de_revient_dilue_n_est_jamais_affiche(self):
        """D-45 : 200 € / 13 parts donnerait 15,38 €, un chiffre faussement rassurant."""
        texte = rapport_moteur.resume(portefeuille_incomplet())

        assert "15,38" not in texte
        assert rapport_moteur.A_COMPLETER in texte

    def test_sans_signalement_le_rapport_le_dit_aussi(self):
        # Une absence d'alerte doit se lire, sinon on ne sait pas si le contrôle a eu lieu.
        assert "Aucun signalement" in rapport_moteur.resume(portefeuille_complet())


class TestRapprochement:
    def test_sans_portefeuille_reel_le_rapport_dit_comment_l_obtenir(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "positions-reelles" in texte

    def test_un_accord_complet_se_lit_en_une_phrase(self):
        portefeuille = portefeuille_complet()
        rapprochement = rapprocher(
            portefeuille, [PositionReelle(actif=ACTIF, quantite=Decimal("15"))]
        )

        assert "concordent" in rapport_moteur.resume(portefeuille, rapprochement)

    def test_les_deux_prix_de_revient_sont_montres_sans_alerte(self):
        """D-46 : l'écart est affiché, il n'est jamais présenté comme une anomalie."""
        portefeuille = portefeuille_complet()
        rapprochement = rapprocher(
            portefeuille,
            [
                PositionReelle(
                    actif=ACTIF,
                    quantite=Decimal("15"),
                    prix_de_revient_banque=Decimal("25.07"),
                )
            ],
        )
        texte = rapport_moteur.resume(portefeuille, rapprochement)

        assert "25,07" in texte
        assert "aucun écart n'est une anomalie" in texte


class TestAffichageSurUneConsoleWindows:
    def test_le_rapport_s_ecrit_en_cp1252(self):
        # La console Windows par défaut écrit en cp1252. Un rapport qui contiendrait un
        # trait de tableau ferait planter la commande au moment de l'afficher, alors que
        # le calcul, lui, s'est bien passé.
        portefeuille = portefeuille_incomplet()
        rapprochement = rapprocher(
            portefeuille, [PositionReelle(actif=ACTIF, quantite=Decimal("20"))]
        )

        rapport_moteur.resume(portefeuille, rapprochement).encode("cp1252")

    def test_un_portefeuille_vide_ne_plante_pas(self):
        texte = rapport_moteur.resume(Portefeuille.construire([]))

        assert "Aucune part détenue" in texte
        texte.encode("cp1252")

    def test_un_nom_d_actif_tres_long_est_coupe(self):
        long = operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            poche=Poche.CTO,
            quantite="1",
            prix_unitaire="10.00",
            nom_actif="Un nom d'actif vraiment beaucoup trop long pour la colonne prévue",
        )
        texte = rapport_moteur.resume(Portefeuille.construire([long]))

        assert "trop long pour la colonne" not in texte
        for ligne in texte.splitlines():
            assert len(ligne) <= 100

    def test_aucune_ligne_ne_deborde_d_un_terminal(self):
        """Les signalements sont des phrases en français : ils doivent être enveloppés."""
        portefeuille = portefeuille_incomplet()
        rapprochement = rapprocher(
            portefeuille,
            [
                PositionReelle(actif=ACTIF, quantite=Decimal("20")),
                PositionReelle(actif="XX0000000009", quantite=Decimal("7")),
            ],
        )
        texte = rapport_moteur.resume(portefeuille, rapprochement)

        assert "titres sans opération" in texte
        for ligne in texte.splitlines():
            assert len(ligne) <= 100, ligne
