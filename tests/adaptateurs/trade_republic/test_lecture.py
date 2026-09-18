"""La lecture d'un export : des événements Trade Republic aux opérations pivot.

Chaque test vérifie une chose que l'adaptateur **ne doit pas** faire silencieusement :
deviner une poche, ignorer un libellé, confondre deux quantités, laisser passer un chiffre
faux. Données entièrement fictives (D-03, D-38).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from dashboard_tr.adaptateurs.trade_republic.lecture import Lecteur
from dashboard_tr.config.comptes import Configuration, RoleCompte
from dashboard_tr.pivot.operation import Poche, Provenance, TypeOperation
from dashboard_tr.pivot.validation import controler
from tests.adaptateurs.trade_republic import evenements_fictifs as fictifs

COMPTES = {
    fictifs.COMPTE_COURANT: RoleCompte.COURANT,
    fictifs.COMPTE_PEA: RoleCompte.PEA,
}


def lire(evenements, poches=None):
    configuration = Configuration(roles=COMPTES, poches_corrigees=poches or {})
    return Lecteur(configuration).lire(evenements)


def une_operation(evenement, poches=None):
    rapport = lire([evenement], poches)
    assert len(rapport.operations) == 1, rapport.resume()
    return rapport.operations[0], rapport


def categories(rapport):
    return {signalement.categorie for signalement in rapport.signalements}


class TestAchatEtVente:
    def test_un_plan_d_epargne_devient_un_achat(self):
        operation, _ = une_operation(fictifs.plan_epargne())

        assert operation.type is TypeOperation.ACHAT
        assert operation.nature_source == "plan_epargne"
        assert operation.quantite == Decimal("2")
        assert operation.prix_unitaire == Decimal("25.00")
        assert operation.montant_brut == Decimal("50.00")
        assert operation.frais == Decimal("0")
        assert operation.montant_regle == Decimal("50.00")
        assert operation.poche is Poche.CTO

    def test_le_sens_vient_du_signe_du_montant_pas_du_libelle(self):
        vente, _ = une_operation(fictifs.vente_pea())
        assert vente.type is TypeOperation.VENTE
        assert vente.montant_regle == Decimal("199.00")
        assert vente.montant_brut == Decimal("200.00")

    def test_un_desaccord_entre_le_libelle_et_le_montant_est_signale(self):
        # Le montant dit « vente », le mot affiché dit « Kauf » : le montant l'emporte,
        # mais le désaccord doit être visible.
        evenement = fictifs.vente_pea()
        for section in evenement["details"]["sections"]:
            if section.get("title") == "Übersicht":
                section["data"][0]["title"] = "Kauf"

        operation, rapport = une_operation(evenement)
        assert operation.type is TypeOperation.VENTE
        assert "sens en désaccord" in categories(rapport)

    def test_les_frais_gratuits_sont_lus_comme_zero(self):
        operation, _ = une_operation(fictifs.plan_epargne())
        assert operation.frais == Decimal("0")
        assert operation.provenance["frais"] is Provenance.TEXTE

    def test_un_mot_inconnu_a_la_place_des_frais_n_est_pas_pris_pour_zero(self):
        # Prendre un mot inconnu pour « gratuit » effacerait un frais réel.
        evenement = fictifs.plan_epargne()
        for section in evenement["details"]["sections"]:
            if section.get("title") == "Übersicht":
                for ligne in section["data"]:
                    if ligne["title"] == "Gebühr":
                        ligne["detail"]["text"] = "Rabattiert"

        rapport = lire([evenement])
        assert rapport.operations == []
        assert "nombre illisible" in categories(rapport)

    def test_les_frais_et_taxes_ne_sont_pas_dans_le_montant_brut(self):
        operation, _ = une_operation(fictifs.achat_pea())

        assert operation.montant_brut == Decimal("200.00")
        assert operation.frais == Decimal("1.00")
        assert operation.taxes == Decimal("0.60")
        assert operation.montant_regle == Decimal("201.60")
        assert operation.poche is Poche.PEA


class TestQuantitesEtSeparateurDecimal:
    """Le piège principal : la quantité ne s'écrit pas pareil partout."""

    def test_la_quantite_d_un_achat_est_lue_avec_la_virgule_decimale(self):
        operation, _ = une_operation(fictifs.achat_crypto())
        assert operation.quantite == Decimal("0.000833")

    def test_la_quantite_d_un_dividende_est_lue_avec_le_point_decimal(self):
        # « 2.000000 » vaut deux parts, pas deux millions.
        operation, _ = une_operation(
            fictifs.action_gagnee(), poches={fictifs.ACTIF_ACTION_B: Poche.CTO}
        )
        assert operation.quantite == Decimal("2.000000")

    def test_les_deux_endroits_ou_la_quantite_est_ecrite_doivent_concorder(self):
        evenement = fictifs.plan_epargne()
        for section in evenement["details"]["sections"]:
            if section.get("title") == "Übersicht":
                for ligne in section["data"]:
                    if ligne["title"] == "Transaktion":
                        ligne["detail"]["text"] = "3 × 25,00 €"

        _, rapport = une_operation(evenement)
        assert "quantité en désaccord" in categories(rapport)


class TestVersements:
    def test_le_dividende_brut_vaut_le_net_plus_la_taxe(self):
        operation, _ = une_operation(fictifs.dividende())

        assert operation.type is TypeOperation.DIVIDENDE
        assert operation.montant_regle == Decimal("3.50")
        assert operation.taxes == Decimal("1.50")
        assert operation.montant_brut == Decimal("5.00")
        assert operation.quantite == Decimal("10")
        assert operation.prix_unitaire == Decimal("0.50")

    def test_la_taxe_affichee_negative_devient_positive(self):
        operation, _ = une_operation(fictifs.dividende())
        assert operation.taxes > 0

    def test_un_dividende_par_action_en_devise_etrangere_est_laisse_vide(self):
        operation, rapport = une_operation(fictifs.dividende_en_devise_etrangere())

        assert operation.prix_unitaire is None
        assert operation.montant_brut == Decimal("5.00")
        assert "dividende par action non retenu" in categories(rapport)
        # Rien n'attend de donnée externe : l'opération est complète.
        assert operation.complete

    def test_une_distribution_de_capital_lit_son_produit_brut(self):
        operation, _ = une_operation(fictifs.distribution_capital())

        assert operation.type is TypeOperation.DISTRIBUTION_CAPITAL
        assert operation.montant_brut == Decimal("12.00")
        assert operation.montant_regle == Decimal("12.00")

    def test_sans_le_libelle_qui_la_nomme_la_distribution_n_est_pas_produite(self):
        # Ce type d'événement sert aussi à d'autres versements (Q-07).
        evenement = fictifs.distribution_capital()
        for section in evenement["details"]["sections"]:
            if section.get("title") == "Übersicht":
                for ligne in section["data"]:
                    if ligne["title"] == "Event":
                        ligne["detail"]["text"] = "Irgendetwas anderes"

        rapport = lire([evenement])
        assert rapport.operations == []
        assert "nature non reconnue" in categories(rapport)


class TestTitresRecus:
    def test_une_action_gagnee_prend_le_prix_affiche(self):
        operation, rapport = une_operation(
            fictifs.action_gagnee(), poches={fictifs.ACTIF_ACTION_B: Poche.CTO}
        )

        assert operation.type is TypeOperation.TITRES_RECUS
        assert operation.nature_source == "action_gagnee"
        assert operation.prix_unitaire == Decimal("10.00")
        assert operation.montant_brut == Decimal("20.00")
        assert operation.montant_regle == Decimal("0")
        assert operation.complete
        assert "part en espèces ignorée" in categories(rapport)

    def test_le_libelle_aktien_est_lu_selon_sa_section(self):
        # Sous « Übersicht » c'est un nombre de parts, sous « Transaktion » des euros.
        operation, _ = une_operation(
            fictifs.action_gagnee(), poches={fictifs.ACTIF_ACTION_B: Poche.CTO}
        )
        assert operation.quantite == Decimal("2")
        assert operation.montant_brut == Decimal("20.00")

    def test_des_actions_gratuites_attendent_le_cours(self):
        operation, _ = une_operation(
            fictifs.actions_gratuites(), poches={fictifs.ACTIF_ACTION_B: Poche.CTO}
        )

        assert operation.quantite == Decimal("3.000000")
        assert operation.prix_unitaire is None
        assert operation.montant_brut is None
        assert operation.est_a_completer("montant_brut")
        assert not operation.complete

    def test_des_titres_recus_ne_coutent_rien(self):
        operation, _ = une_operation(
            fictifs.actions_gratuites(), poches={fictifs.ACTIF_ACTION_B: Poche.CTO}
        )
        assert (operation.montant_regle, operation.frais, operation.taxes) == (
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
        )


class TestPoche:
    def test_la_poche_vient_du_compte(self):
        assert une_operation(fictifs.achat_pea())[0].poche is Poche.PEA
        assert une_operation(fictifs.plan_epargne())[0].poche is Poche.CTO

    def test_un_code_xf_est_range_en_crypto_et_signale_comme_deduction(self):
        operation, _ = une_operation(fictifs.achat_crypto())
        assert operation.poche is Poche.CRYPTO
        assert operation.provenance["poche"] is Provenance.DEDUCTION

    def test_sans_compte_nomme_rien_n_est_devine(self):
        rapport = Lecteur(Configuration()).lire([fictifs.achat_pea()])

        assert rapport.operations == []
        assert rapport.comptes_a_nommer
        assert rapport.declarations_attendues

    def test_un_actif_sans_compte_ni_poche_declaree_est_signale(self):
        rapport = lire([fictifs.actions_gratuites()])

        assert rapport.operations == []
        assert fictifs.ACTIF_ACTION_B in rapport.actifs_sans_poche

    def test_un_desaccord_avec_le_libelle_affiche_est_signale(self):
        # Le compte dit CTO, l'écran affiche « PEA » : le compte l'emporte, mais on le dit.
        evenement = fictifs.achat_pea()
        evenement["cashAccountNumber"] = fictifs.COMPTE_COURANT

        operation, rapport = une_operation(evenement)
        assert operation.poche is Poche.CTO
        assert "poche en désaccord" in categories(rapport)


class TestCeQuiNEstPasTraite:
    def test_un_type_inconnu_est_affiche_jamais_ignore(self):
        rapport = lire([fictifs.type_inconnu()])

        assert not rapport.tout_est_reconnu
        assert "UN_TYPE_QUE_PERSONNE_N_A_JAMAIS_VU" in rapport.types_inconnus
        assert "type inconnu" in categories(rapport)

    def test_un_libelle_non_reconnu_est_signale_sans_bloquer_l_operation(self):
        rapport = lire([fictifs.libelle_non_reconnu()])

        assert len(rapport.operations) == 1
        assert "libellé non reconnu" in categories(rapport)

    def test_un_plan_echoue_ne_produit_rien_malgre_son_montant(self):
        rapport = lire([fictifs.plan_epargne_echoue()])
        assert rapport.operations == []

    def test_un_statut_inattendu_ecarte_l_operation_sans_la_faire_disparaitre(self):
        rapport = lire([fictifs.ordre_annule_avec_statut_inattendu()])

        assert rapport.operations == []
        assert rapport.par_categorie["ecarte"] == 1


class TestExportComplet:
    @pytest.fixture
    def rapport(self):
        return lire(
            fictifs.export_complet(),
            poches={fictifs.ACTIF_ACTION_B: Poche.CTO},
        )

    def test_chaque_evenement_est_range_quelque_part(self, rapport):
        assert rapport.evenements_lus == sum(rapport.par_categorie.values())

    def test_les_operations_attendues_sont_produites(self, rapport):
        assert dict(rapport.par_type_d_operation()) == {
            "achat": 3,
            "vente": 1,
            "dividende": 1,
            "distribution_capital": 1,
            "titres_recus": 2,
        }

    def test_aucune_operation_ne_viole_les_controles_de_coherence(self, rapport):
        assert rapport.anomalies == []
        for operation in rapport.operations:
            assert controler(operation) == []

    def test_les_valeurs_lues_dans_un_texte_sont_marquees_comme_telles(self, rapport):
        provenances = rapport.valeurs_par_provenance()
        assert provenances[Provenance.TEXTE.value] > 0
        assert provenances[Provenance.DONNEE.value] > 0
        assert provenances[Provenance.A_COMPLETER.value] == 2

    def test_le_resume_ne_laisse_echapper_aucun_montant(self, rapport):
        # Le rapport peut être collé dans une issue : aucun titre de section contenant
        # un montant ne doit s'y retrouver.
        resume = rapport.resume()
        assert "gespart" not in resume
        assert "investiert" not in resume

    def test_le_resume_s_affiche_sur_une_console_windows(self, rapport):
        # La console Windows par défaut écrit en cp1252. Un rapport qui contiendrait un
        # trait de tableau ou une coche ferait échouer la commande **au moment de
        # l'afficher**, alors que la lecture, elle, s'est bien passée.
        rapport.resume().encode("cp1252")
