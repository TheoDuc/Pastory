"""Le classement des événements : quatre catégories, aucune par défaut (D-08).

Les deux pièges que ces tests protègent : un montant ne prouve rien, et une absence de
statut ne prouve rien non plus.
"""

from __future__ import annotations

from dashboard_tr.adaptateurs.trade_republic.classement import (
    TYPES_ECARTES,
    TYPES_HORS_PERIMETRE,
    TYPES_TRAITES,
    Categorie,
    Famille,
    classer,
)
from tests.adaptateurs.trade_republic import evenements_fictifs as fictifs


class TestQuatreCategories:
    def test_un_achat_est_traite(self):
        classement = classer(fictifs.plan_epargne())
        assert classement.categorie is Categorie.TRAITE
        assert classement.famille is Famille.PLAN_EPARGNE

    def test_un_virement_est_hors_perimetre_mais_compte(self):
        classement = classer(fictifs.hors_perimetre())
        assert classement.categorie is Categorie.HORS_PERIMETRE
        assert classement.motif

    def test_un_document_est_ecarte(self):
        assert classer(fictifs.ecarte()).categorie is Categorie.ECARTE

    def test_un_type_absent_de_toutes_les_listes_est_inconnu(self):
        classement = classer(fictifs.type_inconnu())
        assert classement.categorie is Categorie.INCONNU
        assert classement.type_affiche == "UN_TYPE_QUE_PERSONNE_N_A_JAMAIS_VU"


class TestLeMontantNeProuveRien:
    def test_un_plan_echoue_porte_un_montant_et_n_est_pas_traite(self):
        assert classer(fictifs.plan_epargne_echoue()).categorie is Categorie.ECARTE

    def test_des_titres_recus_n_ont_aucun_montant_et_sont_traites(self):
        # L'action gagnée et les actions gratuites ne portent ni montant, ni compte, ni
        # statut. Les écarter sur l'un de ces trois critères les ferait disparaître.
        for construire in (fictifs.action_gagnee, fictifs.actions_gratuites):
            assert classer(construire()).categorie is Categorie.TRAITE


class TestStatut:
    def test_un_statut_absent_n_est_pas_un_refus(self):
        evenement = fictifs.actions_gratuites()
        assert evenement["status"] is None
        assert classer(evenement).categorie is Categorie.TRAITE

    def test_un_statut_present_doit_valoir_execute(self):
        classement = classer(fictifs.ordre_annule_avec_statut_inattendu())
        assert classement.categorie is Categorie.ECARTE
        assert "CANCELED" in (classement.motif or "")


class TestEvenementsSansType:
    def _sans_type(self, **champs):
        evenement = {
            "id": "evt-null",
            "timestamp": "2026-01-01T10:00:00.000+0000",
            "eventType": None,
            "details": {"sections": []},
        }
        evenement.update(champs)
        return evenement

    def test_un_mouvement_d_especes_du_pea_est_hors_perimetre(self):
        evenement = self._sans_type(
            amount={"currency": "EUR", "value": 1.0},
            cashAccountNumber=fictifs.COMPTE_PEA,
            details={
                "sections": [
                    {
                        "type": "table",
                        "title": "Übersicht",
                        "data": [
                            {
                                "title": "Ereignistyp",
                                "detail": {"text": "PEA-Aktivierung"},
                            }
                        ],
                    }
                ]
            },
        )
        assert classer(evenement).categorie is Categorie.HORS_PERIMETRE

    def test_un_document_sans_type_est_ecarte(self):
        evenement = self._sans_type(title="Rechtliche Dokumente")
        assert classer(evenement).categorie is Categorie.ECARTE

    def test_tout_autre_evenement_sans_type_reste_inconnu(self):
        # C'est ici que tombe le transfert d'un PEA venu d'un autre établissement : il peut
        # faire entrer des titres sans qu'aucun achat n'apparaisse (limite de D-15).
        evenement = self._sans_type(title="Un titre que personne ne connaît")
        assert classer(evenement).categorie is Categorie.INCONNU


class TestListes:
    def test_aucun_type_n_est_range_dans_deux_listes(self):
        traites = set(TYPES_TRAITES)
        assert not traites & TYPES_HORS_PERIMETRE
        assert not traites & TYPES_ECARTES
        assert not TYPES_HORS_PERIMETRE & TYPES_ECARTES
