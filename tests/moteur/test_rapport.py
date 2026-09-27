"""Le rapport affiché par `dashboard positions`.

On n'y vérifie pas la mise en page, mais ce qui ne doit **jamais** manquer : ce qui est
incertain est dit, la performance et les coûts ne se mélangent pas, et le tout s'affiche sur
une console Windows.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_tr.moteur import rapport as rapport_moteur
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rapprochement import rapprocher
from dashboard_tr.moteur.rendements import Periode, Synthese, synthese
from dashboard_tr.pivot.operation import Poche, TypeOperation
from dashboard_tr.pivot.position_reelle import PositionReelle
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation

AUTRE_ACTIF = "XX0000000002"


def portefeuille_complet() -> Portefeuille:
    return Portefeuille.construire(enchainement_du_glossaire())


def synthese_du_glossaire(fin: date = date(2026, 3, 31), **series) -> Synthese:
    """L'enchaînement du glossaire valorisé à 40 € : 15 parts, 600 €, gain 300 €."""
    source = SourceFixe({**cours_constant(ACTIF, "40.00", date(2026, 1, 1), fin), **series})
    return synthese(portefeuille_complet(), Periode(fin), source)


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

    def test_sans_synthese_le_rapport_dit_ce_qui_manque(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "TRI" in texte
        assert "ont besoin des cours de marché" in texte

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


class TestColonnes:
    def test_le_sous_total_d_une_poche_tombe_sous_la_colonne_qu_il_additionne(self):
        """Un total décalé d'une colonne fait douter du chiffre autant que s'il était faux."""
        texte = rapport_moteur.resume(portefeuille_complet())
        lignes = texte.splitlines()

        entete = next(ligne for ligne in lignes if "capital investi" in ligne and "nom" in ligne)
        sous_total = next(ligne for ligne in lignes if "capital investi de la poche" in ligne)

        # Les deux colonnes « capital investi » doivent se terminer au même caractère.
        fin_de_l_entete = entete.index("capital investi") + len("capital investi")
        assert len(sous_total.rstrip()) == fin_de_l_entete


class TestCouts:
    def test_le_detail_affiche_tombe_sur_le_total_affiche(self):
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                quantite="30",
                prix_unitaire="10.00",
                frais="1.00",
            ),
            operation(
                TypeOperation.DISTRIBUTION_CAPITAL,
                horodatage="2026-05-05 09:00",
                quantite="30",
                prix_unitaire="0.40",
                frais="0.50",
            ),
        ]
        texte = rapport_moteur.resume(Portefeuille.construire(operations))

        assert "autres prélèvements" in texte
        bloc = texte.split("Coûts réellement payés")[1].split("Le spread")[0]
        montants = [
            Decimal(ligne.rsplit(" ", 1)[-1].replace(",", "."))
            for ligne in bloc.splitlines()
            if ligne.startswith("  ") and ligne.strip() and ligne.rstrip()[-1].isdigit()
        ]
        detail, total = montants[:-1], montants[-1]
        assert sum(detail) == total == Decimal("1.50")


class TestRapprochement:
    def test_sans_portefeuille_reel_le_rapport_dit_comment_l_obtenir(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "positions-reelles" in texte

    def test_a_une_date_passee_le_rapprochement_est_sans_objet(self):
        """La banque ne sait montrer qu'aujourd'hui : comparer serait un faux diagnostic."""
        texte = rapport_moteur.resume(portefeuille_complet(), None, arrete_au=date(2026, 1, 31))

        assert "Sans objet" in texte
        assert "2026-01-31" in texte
        assert "positions-reelles" not in texte

    def test_un_fichier_abime_empeche_de_conclure(self):
        portefeuille = portefeuille_complet()
        rapprochement = rapprocher(
            portefeuille,
            [PositionReelle(actif=ACTIF, quantite=Decimal("15"))],
            lignes_illisibles=1,
        )
        texte = rapport_moteur.resume(portefeuille, rapprochement)

        assert "n'ont pas pu être lues" in texte
        assert "rapprochement est donc incomplet" in texte
        assert "concordent" not in texte

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


class TestValeurEtChiffresCles:
    """Les deux blocs de l'étape 5 : la valeur des actifs, et gain / TRI / TWRR."""

    def test_la_valeur_des_actifs_est_datee_et_sourcee(self):
        texte = rapport_moteur.resume(portefeuille_complet(), synthese=synthese_du_glossaire())

        assert "Valeur des actifs au 2026-03-31" in texte
        assert "source : Source de test" in texte
        assert "600,00" in texte  # 15 x 40
        assert "D-48" in texte  # l'écart avec Trade Republic est annoncé

    def test_les_trois_chiffres_cles_sont_la(self):
        texte = rapport_moteur.resume(portefeuille_complet(), synthese=synthese_du_glossaire())

        assert "Les trois chiffres clés (D-22)" in texte
        assert "GAIN en euros" in texte
        assert "300,00" in texte  # 600 - 500 + 200
        assert "TRI (annuel)" in texte
        assert "TWRR (sur la période)" in texte
        assert "depuis la première opération (2026-01-05) jusqu'au 2026-03-31" in texte
        assert "peu significatifs" in texte  # 85 jours

    def test_les_blocs_sont_dans_l_ordre_de_lecture(self):
        texte = rapport_moteur.resume(portefeuille_complet(), synthese=synthese_du_glossaire())

        assert (
            texte.index("Positions détenues")
            < texte.index("Valeur des actifs")
            < texte.index("Ce qui est placé")
            < texte.index("Les trois chiffres clés")
            < texte.index("Coûts réellement payés")
        )

    def test_un_cours_d_un_autre_jour_est_signale(self):
        # Le 2026-03-28 est un samedi : le cours retenu est celui du vendredi.
        source = SourceFixe({ACTIF: {date(2026, 3, 27): "40.00"}})
        resultat = synthese(portefeuille_complet(), Periode(date(2026, 3, 28)), source)

        texte = rapport_moteur.resume(portefeuille_complet(), synthese=resultat)

        assert "cours du 2026-03-27 (dernier jour coté avant le 2026-03-28)" in texte

    def test_un_actif_sans_cours_sort_des_totaux_et_le_rapport_le_dit(self):
        portefeuille = Portefeuille.construire(
            enchainement_du_glossaire()
            + [
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-10 09:00",
                    actif=AUTRE_ACTIF,
                    poche=Poche.PEA,
                    quantite="4",
                    prix_unitaire="50.00",
                )
            ]
        )
        source = SourceFixe(cours_constant(ACTIF, "40.00", date(2026, 1, 1), date(2026, 3, 31)))
        resultat = synthese(portefeuille, Periode(date(2026, 3, 31)), source)

        texte = rapport_moteur.resume(portefeuille, synthese=resultat)

        assert "Non valorisés, exclus de tous les totaux (D-53) : 1" in texte
        assert AUTRE_ACTIF in texte
        assert "PARTIEL : 1 actif(s)" in texte
        assert "valeur totale" in texte
        # La poche PEA n'a que cet actif : ses chiffres sont sans objet, et c'est expliqué.
        assert "PEA : gain et TRI non calculables" in texte

    def test_un_twrr_non_calculable_est_explique(self):
        # Aucun cours au 2026-02-05, jour du second achat : le TWRR ne peut pas découper là.
        source = SourceFixe({ACTIF: {date(2026, 1, 5): "20.00", date(2026, 3, 31): "40.00"}})
        resultat = synthese(portefeuille_complet(), Periode(date(2026, 3, 31)), source)

        texte = rapport_moteur.resume(portefeuille_complet(), synthese=resultat)

        assert "300,00" in texte  # le gain, lui, se calcule
        assert "total : TWRR non calculable" in texte
        assert "2026-02-05" in texte

    def test_une_periode_bornee_est_ecrite_en_clair(self):
        source = SourceFixe(cours_constant(ACTIF, "40.00", date(2026, 1, 1), date(2026, 3, 31)))
        resultat = synthese(
            portefeuille_complet(),
            Periode(fin=date(2026, 3, 31), debut=date(2026, 3, 1)),
            source,
        )

        texte = rapport_moteur.resume(portefeuille_complet(), synthese=resultat)

        assert "du 2026-03-01 jusqu'au 2026-03-31" in texte
        assert "800,00" in texte  # 20 parts x 40 au soir du 28 février

    def test_un_pourcentage_s_arrondit_comme_a_la_main(self):
        # 10,125 % s'écrit 10,13 %, comme tous les arrondis du projet — pas 10,12 % comme le
        # ferait l'arrondi « au pair » par défaut de Decimal.
        assert rapport_moteur._pourcentage(Decimal("0.101250")) == "10,13 %"
        assert rapport_moteur._pourcentage(Decimal("0.100050")) == "10,01 %"
        assert rapport_moteur._pourcentage(None) == "-"

    def test_un_portefeuille_vide_a_une_synthese_vide(self):
        portefeuille = Portefeuille.construire([])
        resultat = synthese(portefeuille, Periode(date(2026, 3, 31)), SourceFixe())

        texte = rapport_moteur.resume(portefeuille, synthese=resultat)

        assert "rien à valoriser" in texte
        assert "aucune opération sur la période" in texte
        texte.encode("cp1252")


class TestAffichageSurUneConsoleWindows:
    def test_la_synthese_s_ecrit_en_cp1252(self):
        texte = rapport_moteur.resume(portefeuille_complet(), synthese=synthese_du_glossaire())

        texte.encode("cp1252")

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
