"""Le rapport affiché par `pastory positions`.

On n'y vérifie pas la mise en page, mais ce qui ne doit **jamais** manquer : ce qui est
incertain est dit, la performance et les coûts ne se mélangent pas, et le tout s'affiche sur
une console Windows.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from pastory.moteur import couts as couts_moteur
from pastory.moteur import diversification as diversification_moteur
from pastory.moteur import rapport as rapport_moteur
from pastory.moteur import valeur_reelle as valeur_reelle_moteur
from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.rendements import Periode, Synthese, synthese
from pastory.parametres import referentiels as parametres_referentiels
from pastory.parametres.referentiels import charger_tout as referentiels_du_projet
from pastory.pivot.operation import Poche, TypeOperation
from tests.moteur.compositions_fictives import (
    CompositionFictive,
    SourceDeCompositionFictive,
    etf_monde,
    etf_obligataire,
    etf_synthetique_pea,
    parts,
)
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation
from tests.moteur.parametres_fictifs import ParametresFictifs, regles

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


class TestControleDesQuantites:
    """Sans photo du portefeuille, le rapport renvoie à l'écran de la banque (D-81)."""

    def test_le_rapport_invite_a_comparer_avec_l_application(self):
        texte = rapport_moteur.resume(portefeuille_complet())

        assert "Contrôle des quantités" in texte
        assert "application Trade" in texte
        assert "positions-reelles" not in texte

    def test_a_une_date_passee_la_comparaison_est_sans_objet(self):
        """L'application ne montre qu'aujourd'hui : comparer serait un faux diagnostic."""
        texte = rapport_moteur.resume(portefeuille_complet(), arrete_au=date(2026, 1, 31))

        assert "Sans objet" in texte
        assert "2026-01-31" in texte


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
        # Et sa colonne ne montre aucun chiffre — pas même « 0,00 » d'achats, qui se lirait
        # comme « rien n'a été investi » alors que 200 € l'ont été.
        entete = next(ligne for ligne in texte.splitlines() if ligne.strip().startswith("total"))
        ligne_achats = next(ligne for ligne in texte.splitlines() if "achats (titres" in ligne)
        colonnes = entete.split()
        cellules = ligne_achats.split()[-len(colonnes) :]
        assert dict(zip(colonnes, cellules, strict=True))["PEA"] == "-"
        assert "200,00" not in ligne_achats

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
        rapport_moteur.resume(portefeuille_incomplet()).encode("cp1252")

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
        texte = rapport_moteur.resume(portefeuille_incomplet())

        assert "prix à compléter" in texte
        for ligne in texte.splitlines():
            assert len(ligne) <= 100, ligne


# --- Étape 6 : les trois blocs des coûts et de la valeur réelle ------------------------


def detail_et_valeur(premier_versement_pea=date(2021, 3, 1), types=None, ter=None):
    """Le portefeuille du glossaire, avec ses coûts et sa valeur réelle."""
    portefeuille = portefeuille_complet()
    periode = Periode(fin=date(2026, 3, 31))
    source = SourceFixe(cours_constant(ACTIF, "40.00", date(2026, 1, 1), periode.fin))
    la_synthese = synthese(portefeuille, periode, source)
    parametres = ParametresFictifs(
        types=types if types is not None else {ACTIF: "etf"},
        ter=ter if ter is not None else {ACTIF: "0.20"},
    )
    detail = couts_moteur.detailler(portefeuille, periode, la_synthese.valorisation, parametres)
    valeur = valeur_reelle_moteur.valeur_reelle(
        portefeuille,
        la_synthese.valorisation,
        parametres,
        regles(premier_versement_pea=premier_versement_pea),
    )
    return portefeuille, la_synthese, detail, valeur


def rapport_complet(**kwargs):
    portefeuille, la_synthese, detail, valeur = detail_et_valeur(**kwargs)
    return rapport_moteur.resume(
        portefeuille,
        synthese=la_synthese,
        detail_des_couts=detail,
        valeur_reelle_estimee=valeur,
    )


def rapport_avec_repartition(composition=None, **kwargs):
    """Le rapport complet, plus le bloc de l'étape 7."""
    portefeuille, la_synthese, detail, valeur = detail_et_valeur(**kwargs)
    table = {ACTIF: composition if composition is not None else etf_monde()}
    la_diversification = diversification_moteur.diversifier(
        la_synthese.valorisation,
        SourceDeCompositionFictive(table),
        parametres_referentiels.charger_tout(),
    )
    return rapport_moteur.resume(
        portefeuille,
        synthese=la_synthese,
        detail_des_couts=detail,
        valeur_reelle_estimee=valeur,
        diversification_estimee=la_diversification,
    )


class TestLeBlocDeRepartitionDeLEtape7:
    def test_les_trois_repartitions_sont_titrees(self):
        texte = rapport_avec_repartition()

        assert "REPARTITION DU PORTEFEUILLE" in texte
        assert "Par classe d'actifs" in texte
        assert "Par zone et par pays" in texte
        assert "Par secteur" in texte

    def test_la_date_d_arrete_des_compositions_est_donnee(self):
        texte = rapport_avec_repartition()

        assert "Compositions arrêtées au 2026-08-31" in texte

    def test_la_regle_de_pays_et_la_convention_des_zones_sont_ecrites(self):
        # D-66 et D-67 : sans elles, aucun pourcentage n'est comparable à une fiche d'émetteur.
        texte = rapport_avec_repartition()

        assert "plusieurs réponses justes" in texte
        assert "pour un fonds, c'est" in texte.lower()
        assert "convention" in texte

    def test_il_est_dit_que_rien_n_est_ramene_a_cent(self):
        texte = rapport_avec_repartition()

        assert "ne font donc pas 100 %" in texte

    def test_un_fonds_synthetique_est_signale_avec_la_raison(self):
        texte = rapport_avec_repartition(composition=etf_synthetique_pea())

        assert "réplication synthétique" in texte
        assert "pas celle des titres qu'ils" in texte

    def test_le_non_attribue_est_visible(self):
        texte = rapport_avec_repartition(composition=etf_synthetique_pea())

        assert "Non attribué par la source" in texte

    def test_un_etf_obligataire_apparait_hors_perimetre_et_non_pas_manquant(self):
        texte = rapport_avec_repartition(composition=etf_obligataire())

        assert "Obligations (hors actions)" in texte
        assert "Non couvert" not in texte

    def test_un_actif_sans_composition_dit_ce_qui_en_est_fait(self):
        # D-62 : le message est lu par quelqu'un qui n'a pas suivi la construction du projet.
        portefeuille, la_synthese, detail, valeur = detail_et_valeur()
        la_diversification = diversification_moteur.diversifier(
            la_synthese.valorisation,
            SourceDeCompositionFictive({}),
            parametres_referentiels.charger_tout(),
        )

        texte = rapport_moteur.resume(
            portefeuille,
            synthese=la_synthese,
            diversification_estimee=la_diversification,
        )

        assert "Non couvert : composition inconnue" in texte
        assert "rien\n      n'est estimé" in texte or "rien n'est estimé" in texte
        assert "actifs.toml" not in texte


class TestLeBlocDeRepartitionSAfficheSurUneConsoleWindows:
    def test_il_s_ecrit_en_cp1252(self):
        rapport_avec_repartition().encode("cp1252")

    def test_aucune_ligne_ne_depasse_la_largeur_du_rapport(self):
        # Une répartition en colonnes est précisément le genre de bloc qui déborde.
        texte = rapport_avec_repartition()

        for ligne in texte.splitlines():
            assert len(ligne) <= 100, ligne

    def test_un_pays_au_nom_long_ne_fait_pas_deborder_la_ligne(self):
        composition = CompositionFictive(
            pays=parts(VG="100"), secteurs=parts(technology="100"), classes=parts(stock="100")
        )
        texte = rapport_avec_repartition(composition=composition)

        assert "Îles Vierges" in texte
        for ligne in texte.splitlines():
            assert len(ligne) <= 100, ligne


class TestLesTroisBlocsDeLEtape6:
    def test_les_couts_payes_sont_detailles_avec_leur_poids(self):
        texte = rapport_complet()

        assert "Coûts payés du" in texte
        assert "poids" in texte
        # Le poids est expliqué avec un exemple : sans cela, personne ne sait ce qu'il mesure.
        assert "pèse 4,00 %" in texte

    def test_les_couts_estimes_sont_annonces_comme_tels(self):
        """D-17 : une estimation qu'on prendrait pour une facture serait pire que rien."""
        texte = rapport_complet()

        assert "Coûts estimés, jamais facturés" in texte
        assert "n'est pas une facture" in texte
        assert "ECART DE PRIX (SPREAD)" in texte
        assert "FRAIS COURANTS DES ETF" in texte

    def test_le_spread_dit_pourquoi_il_faut_l_estimer(self):
        texte = rapport_complet()

        assert "aucun relevé ne le montre" in texte

    def test_la_valeur_reelle_montre_sa_decomposition(self):
        """D-23 : cinq lignes, dont chacune se retranche de la précédente."""
        texte = rapport_complet()

        assert "Valeur réelle au 2026-03-31" in texte
        for ligne in (
            "valeur brute",
            "frais de vente estimés",
            "écart de prix estimé",
            "impôt estimé",
            "VALEUR REELLE",
        ):
            assert ligne in texte, ligne
        assert "ce que la sortie coûterait" in texte

    def test_chaque_impot_dit_sa_regle_sa_base_et_son_taux(self):
        texte = rapport_complet()

        assert "Comment chaque impôt est calculé" in texte
        assert "base imposable" in texte
        assert "taux appliqué" in texte
        assert "18,6 %" in texte or "31,4 %" in texte

    def test_les_taux_citent_leur_source_et_les_hypotheses_sont_ecrites(self):
        """Règle 6 de CLAUDE.md : une estimation se signale, et dit ce qu'elle suppose."""
        texte = rapport_complet()

        assert "D'où viennent les taux" in texte
        assert "source de test" in texte
        assert "Ce que ce calcul suppose" in texte
        assert "prélèvement forfaitaire unique de plein droit" in texte

    def test_le_rapport_dit_ce_qui_n_est_pas_compte(self):
        """Les impôts déjà dus ne sont pas des coûts de sortie : il faut le dire."""
        texte = rapport_complet()

        assert "dividendes déjà reçus" in texte
        assert "elle ne déclare pas" in texte

    def test_sans_type_declare_le_bloc_des_couts_estimes_le_dit(self):
        texte = rapport_complet(types={}, ter={})

        assert "PARTIEL" in texte
        assert "type" in texte
        assert "pastory actifs" in texte

    def test_sans_ter_declare_le_bloc_le_dit_sans_afficher_zero(self):
        texte = rapport_complet(ter={})

        assert "frais courants introuvables" in texte

    def test_sans_date_de_pea_la_poche_le_dit(self):
        """D-59 : l'ancienneté décide du taux ; sans date, l'impôt du PEA n'est pas calculé."""
        # L'enchaînement du glossaire est en CTO : on rejoue la même chose en PEA.
        portefeuille = Portefeuille.construire(
            [
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-05 09:00",
                    poche=Poche.PEA,
                    quantite="10",
                    prix_unitaire="20.00",
                    frais="1.00",
                )
            ]
        )
        periode = Periode(fin=date(2026, 3, 31))
        source = SourceFixe(cours_constant(ACTIF, "40.00", date(2026, 1, 1), periode.fin))
        la_synthese = synthese(portefeuille, periode, source)
        parametres = ParametresFictifs(types={ACTIF: "etf"}, ter={ACTIF: "0.20"})
        valeur = valeur_reelle_moteur.valeur_reelle(
            portefeuille, la_synthese.valorisation, parametres, regles()
        )

        texte = rapport_moteur.resume(
            portefeuille, synthese=la_synthese, valeur_reelle_estimee=valeur
        )

        assert "date d'ouverture du PEA inconnue" in texte
        assert "PARTIEL" in texte


class TestLesNouveauxBlocsSAffichentSurUneConsoleWindows:
    """La console écrit en cp1252 : un bloc juste ferait planter la commande à l'impression."""

    def test_les_trois_blocs_s_ecrivent_en_cp1252(self):
        rapport_complet().encode("cp1252")

    def test_les_refus_aussi_s_ecrivent_en_cp1252(self):
        rapport_complet(premier_versement_pea=None, types={}, ter={}).encode("cp1252")

    def test_aucune_ligne_des_nouveaux_blocs_ne_deborde(self):
        texte = rapport_complet()
        debut = texte.index("Coûts payés du")

        for ligne in texte[debut:].splitlines():
            assert len(ligne) <= 100, ligne


class TestLesPartsDeLaRepartitionSontEcritesJuste:
    """Un pourcentage multiplié par cent est un chiffre faux, et il se voit tout de suite."""

    def test_une_part_est_ecrite_en_pour_cent_et_non_en_taux(self):
        # L'ETF fictif attribue 60 % aux États-Unis : la ligne doit dire 60,00 %, pas 6000,00 %.
        texte = rapport_avec_repartition()

        assert "60,00 %" in texte
        assert "6000,00 %" not in texte

    def test_aucune_part_du_bloc_ne_depasse_cent_pour_cent(self):
        texte = rapport_avec_repartition()

        debut = texte.index("REPARTITION DU PORTEFEUILLE")
        for ligne in texte[debut:].splitlines():
            if not ligne.strip().endswith("%"):
                continue
            part = ligne.strip().rsplit(" ", 1)[0].rsplit(" ", 1)[-1]
            assert Decimal(part.replace(",", ".")) <= Decimal("100"), ligne


class TestAucunLibelleDuBlocNEstTronque:
    """Un libellé coupé au milieu n'explique plus rien, et c'est arrivé une fois."""

    def test_les_libelles_des_restes_tiennent_dans_la_colonne(self):
        classes = referentiels_du_projet().classes_dactifs.ordonnees()
        libelles = [
            rapport_moteur.LIBELLE_NUMERIQUES,
            rapport_moteur.LIBELLE_NON_ATTRIBUE,
            rapport_moteur.LIBELLE_NON_COUVERT,
            # Chaque classe d'actifs peut apparaitre suivie du suffixe « hors actions » : c'est
            # le libellé complet qui doit tenir, pas seulement le nom de la classe.
            *[
                f"{classe.libelle} {rapport_moteur.SUFFIXE_HORS_ACTIONS}"
                for classe in classes
            ],
        ]
        for libelle in libelles:
            assert len(libelle) <= rapport_moteur.LARGEUR_LIBELLE_REPARTITION, libelle

    def test_aucun_libelle_affiche_ne_finit_par_un_point_de_troncature(self):
        texte = rapport_avec_repartition(composition=etf_obligataire())

        debut = texte.index("REPARTITION DU PORTEFEUILLE")
        for ligne in texte[debut:].splitlines():
            assert "liqu. " not in ligne, ligne


class TestLesSignalementsDeLaRepartitionSontAffiches:
    """Un signalement calculé mais jamais montré ne sert à rien (règle 6 de CLAUDE.md)."""

    def test_un_depassement_est_explique_a_l_ecran(self):
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(technology="100"),
            classes=parts(stock="50", bond="50"),
        )
        texte = rapport_avec_repartition(composition=composition)

        assert "Ce qui cloche dans ces chiffres" in texte
        assert "dépasse donc la valeur du portefeuille" in texte

    def test_sans_signalement_le_bloc_n_apparait_pas(self):
        texte = rapport_avec_repartition()

        assert "Ce qui cloche dans ces chiffres" not in texte

    def test_le_bloc_des_signalements_reste_affichable_sur_une_console_windows(self):
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(technology="100"),
            classes=parts(stock="50", bond="50"),
        )
        texte = rapport_avec_repartition(composition=composition)

        texte.encode("cp1252")
        for ligne in texte.splitlines():
            assert len(ligne) <= 100, ligne


def _origine(actif: str, source: str, regle: str):
    return diversification_moteur.OrigineDUnActif(
        actif=actif, source=source, regle_de_pays=regle
    )


def _rapport_avec_origines(*origines):
    """Le rapport complet, dont on remplace les origines par celles qu'on veut éprouver.

    On part de la vraie répartition calculée par le moteur, pour que le reste du bloc soit
    exactement celui qu'un utilisateur verrait.
    """
    portefeuille, la_synthese, detail, valeur = detail_et_valeur()
    la_diversification = diversification_moteur.diversifier(
        la_synthese.valorisation,
        SourceDeCompositionFictive({ACTIF: etf_monde()}),
        parametres_referentiels.charger_tout(),
    )
    return rapport_moteur.resume(
        portefeuille,
        synthese=la_synthese,
        detail_des_couts=detail,
        valeur_reelle_estimee=valeur,
        diversification_estimee=replace(la_diversification, origines=tuple(origines)),
    )


class TestLOrigineDeChaqueActifEstEcrite:
    """La condition posée par D-72 pour qu'une source de secours soit permise.

    « À condition que la source de chaque chiffre soit visible à l'écran », et **ligne par
    ligne**. Sans ce bloc, le secours serait interdit par sa propre décision.
    """

    def test_avec_deux_origines_chacune_est_nommee_avec_sa_regle(self):
        texte = _rapport_avec_origines(
            _origine(
                "XX0000000001",
                "extraETF (composition agrégée par ISIN)",
                "pays d'activité de la société",
            ),
            _origine(
                "XX0000000002",
                "Amundi (répartition de l'indice suivi, par ISIN)",
                "pays de classification de l'indice suivi",
            ),
        )

        aplati = " ".join(texte.split())
        assert "D'où vient la composition de chaque actif" in aplati
        assert "XX0000000001 : extraETF" in aplati
        assert "XX0000000002 : Amundi" in aplati
        assert "pays d'activité de la société" in aplati
        assert "pays de classification de l'indice suivi" in aplati

    def test_avec_une_seule_origine_le_bloc_n_apparait_pas(self):
        """Vingt lignes identiques feraient douter des chiffres au lieu de les éclairer."""
        texte = _rapport_avec_origines(
            _origine("XX0000000001", "une seule source", "une seule règle"),
            _origine("XX0000000002", "une seule source", "une seule règle"),
        )

        assert "D'où vient la composition de chaque actif" not in texte

    def test_une_regle_absente_est_dite_et_non_laissee_vide(self):
        """Une composition déclarée à la main n'a pas de règle : le dire, pas le taire."""
        texte = _rapport_avec_origines(
            _origine("XX0000000001", "extraETF", "pays d'activité"),
            _origine("XX0000000002", "déclaré par vous dans actifs.toml", ""),
        )

        assert "règle non précisée par la source" in " ".join(texte.split())

    def test_le_bloc_reste_affichable_sur_une_console_windows(self):
        """La console Windows écrit en cp1252 : un caractère hors de ce jeu ferait échouer
        l'affichage alors que le calcul, lui, s'est bien passé."""
        texte = _rapport_avec_origines(
            _origine(
                "XX0000000001",
                "extraETF (composition agrégée par ISIN)",
                "pays d'activité de la société, au sens de cette source",
            ),
            _origine(
                "XX0000000002",
                "Amundi (répartition de l'indice suivi, par ISIN)",
                "pays de classification de l'indice suivi (méthodologie du fournisseur d'indice)",
            ),
        )

        texte.encode("cp1252")

    def test_aucune_ligne_du_bloc_ne_depasse_la_largeur_du_rapport(self):
        """Un libellé tronqué n'explique plus rien : c'est arrivé à l'étape 7."""
        texte = _rapport_avec_origines(
            _origine(
                "XX0000000001",
                "Amundi (répartition de l'indice suivi, par ISIN)",
                "pays de classification de l'indice suivi (méthodologie du fournisseur d'indice)",
            ),
            _origine("XX0000000002", "extraETF", "pays d'activité"),
        )

        depassent = [ligne for ligne in texte.splitlines() if len(ligne) > 100]
        assert depassent == []
