"""Les contrôles de cohérence (docs/format-pivot.md §5).

Chaque contrôle a deux tests : un cas juste, qui doit passer, et un cas faux, qui doit être
signalé. Aucun cas faux n'est corrigé : il est signalé.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from dashboard_tr.pivot.operation import Provenance
from dashboard_tr.pivot.validation import controler, controler_toutes
from tests.pivot import exemples


def regles(anomalies) -> set[str]:
    return {anomalie.regle for anomalie in anomalies}


class TestExemplesDuDocument:
    """Les six exemples de `docs/format-pivot.md` §6 passent tous les contrôles."""

    @pytest.mark.parametrize("construire", exemples.TOUS_LES_EXEMPLES)
    def test_un_exemple_du_document_est_coherent(self, construire):
        assert controler(construire()) == []

    def test_controler_toutes_ne_perd_aucune_operation(self):
        operations = [construire() for construire in exemples.TOUS_LES_EXEMPLES]
        faussee = dataclasses.replace(operations[0], montant_regle=Decimal("49.00"))
        anomalies = controler_toutes(operations + [faussee])

        assert len(anomalies) == 1
        assert anomalies[0].identifiant_operation == faussee.identifiant
        assert anomalies[0].reference_source == faussee.reference_source


class TestMontantBrut:
    """`montant_brut = quantite × prix_unitaire`."""

    def test_un_ecart_d_arrondi_est_tolere(self):
        # Quantité × prix tombe sur une fraction de centime que la banque arrondit.
        operation = dataclasses.replace(
            exemples.achat_plan_epargne(),
            montant_brut=Decimal("50.01"),
            montant_regle=Decimal("50.01"),
        )
        assert controler(operation) == []

    def test_un_ecart_plus_grand_que_l_arrondi_est_signale(self):
        # 2 parts : la tolérance vaut 1 centime + 2 × un demi-centime, soit 2 centimes.
        operation = dataclasses.replace(
            exemples.achat_plan_epargne(),
            montant_brut=Decimal("50.05"),
            montant_regle=Decimal("50.05"),
        )
        assert "montant_brut" in regles(controler(operation))

    def test_la_tolerance_grandit_avec_le_nombre_de_parts(self):
        # Un dividende de 0,335 € par action sur 200 parts est affiché « 0,33 € » :
        # 200 × 0,33 donne 66,00 alors que la banque a versé 67,00. Ce n'est pas une erreur
        # de lecture, c'est l'arrondi du prix affiché — il ne doit pas être signalé.
        operation = dataclasses.replace(
            exemples.dividende(),
            quantite=Decimal("200"),
            prix_unitaire=Decimal("0.33"),
            montant_brut=Decimal("67.00"),
            taxes=Decimal("0.00"),
            montant_regle=Decimal("67.00"),
        )
        assert controler(operation) == []

    def test_une_quantite_mal_lue_est_signalee(self):
        # Cas réel redouté : « 2 » lu au lieu de « 0,2 » dans un libellé allemand.
        operation = dataclasses.replace(exemples.achat_plan_epargne(), quantite=Decimal("0.2"))
        assert "montant_brut" in regles(controler(operation))

    def test_un_montant_brut_absent_et_non_signale_est_une_anomalie(self):
        # Sans ce contrôle, un prix illisible ferait disparaître l'opération de tous les
        # totaux sans que rien ne le dise.
        operation = dataclasses.replace(
            exemples.achat_plan_epargne(), montant_brut=None, prix_unitaire=None
        )
        assert "montant_brut" in regles(controler(operation))


class TestMontantRegle:
    """Achat : brut + frais + taxes. Encaissement : brut − frais − taxes."""

    def test_un_achat_dont_les_frais_ne_tombent_pas_juste_est_signale(self):
        operation = dataclasses.replace(
            exemples.achat_ordre_ponctuel_pea(), frais=Decimal("2.00")
        )
        anomalie = controler(operation)[0]
        assert anomalie.regle == "montant_regle"
        assert "201.60" in anomalie.message

    def test_une_vente_dont_le_montant_recu_ne_tombe_pas_juste_est_signalee(self):
        operation = dataclasses.replace(exemples.vente_partielle(), montant_regle=Decimal("200.00"))
        assert "montant_regle" in regles(controler(operation))

    def test_un_dividende_dont_la_retenue_ne_tombe_pas_juste_est_signale(self):
        operation = dataclasses.replace(exemples.dividende(), taxes=Decimal("0.50"))
        assert "montant_regle" in regles(controler(operation))


class TestTitresRecus:
    """Des titres reçus sans achat ne coûtent rien (D-15)."""

    def test_des_frais_sur_des_titres_recus_sont_signales(self):
        operation = dataclasses.replace(
            exemples.titres_recus_prix_a_completer(), frais=Decimal("1.00")
        )
        assert "titres_recus" in regles(controler(operation))

    def test_un_montant_paye_sur_des_titres_recus_est_signale(self):
        operation = dataclasses.replace(
            exemples.titres_recus_prix_a_completer(), montant_regle=Decimal("30.00")
        )
        assert "titres_recus" in regles(controler(operation))

    def test_le_prix_a_completer_met_le_controle_en_attente(self):
        # Ni le montant brut ni le montant réglé ne sont vérifiables tant que le cours manque.
        assert controler(exemples.titres_recus_prix_a_completer()) == []


class TestSignesEtQuantites:
    def test_un_montant_negatif_est_signale(self):
        operation = dataclasses.replace(
            exemples.vente_partielle(),
            montant_brut=Decimal("-200.00"),
            montant_regle=Decimal("-199.00"),
        )
        assert "signe" in regles(controler(operation))

    def test_une_quantite_nulle_sur_un_achat_est_signalee(self):
        operation = dataclasses.replace(exemples.achat_plan_epargne(), quantite=Decimal("0"))
        assert "quantite" in regles(controler(operation))

    def test_une_quantite_absente_sur_une_vente_est_signalee(self):
        operation = dataclasses.replace(exemples.vente_partielle(), quantite=None)
        assert "quantite" in regles(controler(operation))

    def test_une_quantite_absente_sur_un_dividende_est_acceptee(self):
        # Elle n'est qu'informative : la quantité détenue ne change pas (D-14).
        operation = dataclasses.replace(
            exemples.dividende(),
            quantite=None,
            prix_unitaire=None,
            provenance={
                champ: provenance
                for champ, provenance in exemples.dividende().provenance.items()
                if champ not in ("quantite", "prix_unitaire")
            },
        )
        assert controler(operation) == []


class TestDate:
    """Le jour d'une opération découle de son horodatage (D-36)."""

    def test_un_jour_qui_ne_correspond_pas_a_l_horodatage_est_signale(self):
        operation = dataclasses.replace(exemples.achat_plan_epargne(), date=date(2025, 12, 31))
        anomalie = controler(operation)[0]
        assert anomalie.regle == "date"
        assert "2026-01-02" in anomalie.message


class TestProvenanceEtDevise:
    def test_une_valeur_sans_provenance_est_signalee(self):
        operation = exemples.achat_plan_epargne()
        sans_provenance = dataclasses.replace(
            operation,
            provenance={
                champ: provenance
                for champ, provenance in operation.provenance.items()
                if champ != "frais"
            },
        )
        assert "provenance" in regles(controler(sans_provenance))

    def test_un_champ_a_completer_qui_porte_une_valeur_est_signale(self):
        operation = exemples.achat_plan_epargne()
        contradictoire = dataclasses.replace(
            operation,
            provenance={**operation.provenance, "prix_unitaire": Provenance.A_COMPLETER},
        )
        assert "provenance" in regles(controler(contradictoire))

    def test_une_autre_devise_est_signalee(self):
        operation = dataclasses.replace(exemples.achat_plan_epargne(), devise="USD")
        assert "devise" in regles(controler(operation))
