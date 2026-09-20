"""La comparaison avec ce que la banque dit détenir.

Le cas qui justifie tout ce module : **un actif que la banque détient et dont aucune
opération ne parle**. C'est la signature de titres entrés sans événement — limite connue de
D-15 — et rien d'autre dans le projet ne peut le découvrir.
"""

from __future__ import annotations

from decimal import Decimal

from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.rapprochement import Accord, rapprocher
from dashboard_tr.pivot.operation import Poche, TypeOperation
from dashboard_tr.pivot.position_reelle import PositionReelle
from tests.moteur.operations_fictives import ACTIF, operation

AUTRE_ACTIF = "XX0000000002"


def portefeuille_de(quantite: str, poche: Poche = Poche.CTO, actif: str = ACTIF) -> Portefeuille:
    return Portefeuille.construire(
        [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                actif=actif,
                poche=poche,
                quantite=quantite,
                prix_unitaire="20.00",
            )
        ]
    )


class TestAccord:
    def test_deux_quantites_identiques_concordent(self):
        rapprochement = rapprocher(
            portefeuille_de("10"), [PositionReelle(actif=ACTIF, quantite=Decimal("10"))]
        )

        assert rapprochement.tout_concorde
        assert rapprochement.signalements == ()
        assert rapprochement.lignes[0].accord is Accord.ACCORD

    def test_un_ecart_sous_la_tolerance_ne_dit_rien(self):
        # La banque publie ses quantités arrondies à six décimales : deux nombres qui ne
        # diffèrent qu'au-delà décrivent la même position.
        rapprochement = rapprocher(
            portefeuille_de("0.0012335"),
            [PositionReelle(actif=ACTIF, quantite=Decimal("0.001233"))],
        )

        assert rapprochement.tout_concorde

    def test_un_actif_detenu_dans_deux_poches_est_additionne_avant_comparaison(self):
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-06 09:00",
                poche=Poche.CTO,
                quantite="5",
                prix_unitaire="20.00",
            ),
        ]
        rapprochement = rapprocher(
            Portefeuille.construire(operations),
            [PositionReelle(actif=ACTIF, quantite=Decimal("15"))],
        )

        assert rapprochement.tout_concorde


class TestDesaccords:
    def test_un_ecart_de_quantite_est_signale_avec_les_deux_chiffres(self):
        rapprochement = rapprocher(
            portefeuille_de("10"), [PositionReelle(actif=ACTIF, quantite=Decimal("12"))]
        )

        ligne = rapprochement.lignes[0]
        assert ligne.accord is Accord.ECART
        assert ligne.ecart == Decimal("-2")
        assert [signalement.categorie for signalement in rapprochement.signalements] == [
            "écart de quantité"
        ]

    def test_des_titres_detenus_sans_aucune_operation_sont_le_cas_a_examiner(self):
        """C'est ce que D-15 ne pouvait pas voir : des parts entrées hors de la timeline."""
        rapprochement = rapprocher(
            portefeuille_de("10"),
            [
                PositionReelle(actif=ACTIF, quantite=Decimal("10")),
                PositionReelle(
                    actif=AUTRE_ACTIF, quantite=Decimal("40"), nom_actif="Action Exemple B"
                ),
            ],
        )

        inconnue = next(
            ligne for ligne in rapprochement.lignes if ligne.actif == AUTRE_ACTIF
        )
        assert inconnue.accord is Accord.ABSENT_DU_MOTEUR
        assert inconnue.quantite_moteur is None
        assert inconnue.nom_actif == "Action Exemple B"
        assert any(
            signalement.categorie == "titres sans opération"
            for signalement in rapprochement.signalements
        )

    def test_des_parts_que_la_banque_ne_montre_pas_sont_signalees_aussi(self):
        rapprochement = rapprocher(portefeuille_de("10"), [])

        assert rapprochement.lignes[0].accord is Accord.ABSENT_DE_LA_BANQUE
        assert [signalement.categorie for signalement in rapprochement.signalements] == [
            "parts non confirmées"
        ]


class TestFichierAbime:
    def test_des_lignes_illisibles_empechent_de_conclure(self):
        """Un actif absent d'une ligne illisible ressortirait « absent de la banque »."""
        rapprochement = rapprocher(portefeuille_de("10"), [], lignes_illisibles=1)

        assert rapprochement.lignes_illisibles == 1
        assert rapprochement.complet is False

    def test_un_accord_parfait_est_un_rapprochement_complet(self):
        rapprochement = rapprocher(
            portefeuille_de("10"),
            [PositionReelle(actif=ACTIF, quantite=Decimal("10"))],
            lignes_illisibles=0,
        )

        assert rapprochement.tout_concorde is True
        assert rapprochement.complet is True

    def test_un_accord_apparent_sur_un_fichier_abime_n_est_pas_complet(self):
        """« Tout concorde » et « tout a été comparé » sont deux choses différentes."""
        rapprochement = rapprocher(
            portefeuille_de("10"),
            [PositionReelle(actif=ACTIF, quantite=Decimal("10"))],
            lignes_illisibles=2,
        )

        assert rapprochement.tout_concorde is True
        assert rapprochement.complet is False

    def test_un_actif_liste_deux_fois_par_la_banque_est_additionne(self):
        # Écraser la première ligne par la seconde ferait disparaître des parts et créerait
        # un écart de toutes pièces.
        rapprochement = rapprocher(
            portefeuille_de("15"),
            [
                PositionReelle(actif=ACTIF, quantite=Decimal("10"), nom_actif="ETF Exemple"),
                PositionReelle(actif=ACTIF, quantite=Decimal("5")),
            ],
        )

        assert len(rapprochement.lignes) == 1
        ligne = rapprochement.lignes[0]
        assert ligne.quantite_banque == Decimal("15")
        assert ligne.nom_actif == "ETF Exemple"
        assert rapprochement.tout_concorde

    def test_deux_lignes_abandonnent_le_prix_de_revient_de_la_banque(self):
        # Additionner ou moyenner deux prix de revient n'aurait aucun sens.
        rapprochement = rapprocher(
            portefeuille_de("15"),
            [
                PositionReelle(
                    actif=ACTIF, quantite=Decimal("10"), prix_de_revient_banque=Decimal("20")
                ),
                PositionReelle(
                    actif=ACTIF, quantite=Decimal("5"), prix_de_revient_banque=Decimal("30")
                ),
            ],
        )

        assert rapprochement.lignes[0].prix_de_revient_banque is None


class TestPocheNonCouverte:
    """Le cas rencontré sur de vraies données (D-47).

    `pytr portfolio` ne demande les positions que d'un seul compte-titres. Le PEA étant
    dans un second, aucune de ses lignes ne remonte : sans cette règle, chaque actif du PEA
    crierait au loup à chaque lancement, et on cesserait de lire ce bloc.
    """

    def portefeuille_deux_poches(self) -> Portefeuille:
        return Portefeuille.construire(
            [
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-05 09:00",
                    actif=ACTIF,
                    poche=Poche.PEA,
                    quantite="10",
                    prix_unitaire="20.00",
                ),
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-06 09:00",
                    actif=AUTRE_ACTIF,
                    poche=Poche.PEA,
                    quantite="4",
                    prix_unitaire="25.00",
                ),
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-07 09:00",
                    actif="XX0000000003",
                    poche=Poche.CTO,
                    quantite="3",
                    prix_unitaire="30.00",
                ),
            ]
        )

    def test_une_poche_entierement_absente_ne_leve_qu_un_seul_signalement(self):
        rapprochement = rapprocher(
            self.portefeuille_deux_poches(),
            [PositionReelle(actif="XX0000000003", quantite=Decimal("3"))],
        )

        assert rapprochement.poches_non_couvertes == (Poche.PEA,)
        assert [signalement.categorie for signalement in rapprochement.signalements] == [
            "poche non couverte"
        ]

    def test_les_actifs_de_cette_poche_sortent_sans_alerte(self):
        rapprochement = rapprocher(
            self.portefeuille_deux_poches(),
            [PositionReelle(actif="XX0000000003", quantite=Decimal("3"))],
        )

        hors = [
            ligne for ligne in rapprochement.lignes if ligne.accord is Accord.HORS_PERIMETRE
        ]
        assert {ligne.actif for ligne in hors} == {ACTIF, AUTRE_ACTIF}
        assert rapprochement.desaccords == []
        assert rapprochement.tout_concorde is True
        # ... mais le rapprochement n'est pas complet pour autant.
        assert rapprochement.complet is False

    def test_la_quantite_detenue_reste_affichee(self):
        """La laisser vide donnerait à croire qu'on ne détient plus rien."""
        rapprochement = rapprocher(
            self.portefeuille_deux_poches(),
            [PositionReelle(actif="XX0000000003", quantite=Decimal("3"))],
        )

        ligne = next(ligne for ligne in rapprochement.lignes if ligne.actif == ACTIF)
        assert ligne.quantite_moteur == Decimal("10")
        assert ligne.quantite_banque is None

    def test_une_poche_sans_actif_exclusif_n_est_jamais_declaree_non_couverte(self):
        """La photo ne dit pas la poche : un ISIN détenu des deux côtés ne prouve rien.

        On ne peut alors rien conclure, et se taire vaudrait mieux que deviner — mais se
        taire ici reviendrait à mettre de côté une poche sans preuve. L'écart est donc
        affiché tel quel : c'est un cas où le moteur ne sait pas, et il ne le cache pas.
        """
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-06 09:00",
                poche=Poche.CTO,
                quantite="4",
                prix_unitaire="25.00",
            ),
        ]
        rapprochement = rapprocher(
            Portefeuille.construire(operations),
            [PositionReelle(actif=ACTIF, quantite=Decimal("4"))],
        )

        assert rapprochement.poches_non_couvertes == ()
        assert rapprochement.lignes[0].accord is Accord.ECART

    def test_un_actif_des_deux_cotes_n_empeche_pas_de_voir_une_poche_non_couverte(self):
        """Les actifs exclusifs suffisent à trancher, même si d'autres sont partagés."""
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                actif=ACTIF,
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-06 09:00",
                actif=ACTIF,
                poche=Poche.CTO,
                quantite="4",
                prix_unitaire="25.00",
            ),
            # Celui-ci n'est qu'en PEA : c'est lui qui tranche.
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-07 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.PEA,
                quantite="2",
                prix_unitaire="30.00",
            ),
        ]
        rapprochement = rapprocher(
            Portefeuille.construire(operations),
            [PositionReelle(actif=ACTIF, quantite=Decimal("4"))],
        )

        assert rapprochement.poches_non_couvertes == (Poche.PEA,)
        # La part PEA est exclue de la comparaison : sinon 14 parts contre 4.
        partage = next(ligne for ligne in rapprochement.lignes if ligne.actif == ACTIF)
        assert partage.accord is Accord.ACCORD
        assert partage.quantite_moteur == Decimal("4")

    def test_une_photo_qui_ne_confirme_rien_ne_met_aucune_poche_de_cote(self):
        """Une photo qui ne confirme rien n'est pas partielle, elle est inutilisable."""
        rapprochement = rapprocher(
            self.portefeuille_deux_poches(),
            [PositionReelle(actif="XX0000000009", quantite=Decimal("1"))],
        )

        assert rapprochement.poches_non_couvertes == ()
        # Chaque actif repart en désaccord, comme avant la règle.
        assert len(rapprochement.desaccords) == 4

    def test_une_poche_couverte_meme_partiellement_reste_controlee(self):
        """Un seul actif absent parmi d'autres présents reste une vraie alerte."""
        rapprochement = rapprocher(
            self.portefeuille_deux_poches(),
            [
                PositionReelle(actif=ACTIF, quantite=Decimal("10")),
                PositionReelle(actif="XX0000000003", quantite=Decimal("3")),
            ],
        )

        assert rapprochement.poches_non_couvertes == ()
        assert [ligne.accord for ligne in rapprochement.desaccords] == [
            Accord.ABSENT_DE_LA_BANQUE
        ]


class TestPrixDeRevient:
    def test_le_prix_de_revient_de_la_banque_ne_declenche_jamais_rien(self):
        """D-46 : on ignore ce que la banque met dans le sien, on ne le compare donc pas."""
        rapprochement = rapprocher(
            portefeuille_de("10"),
            [
                PositionReelle(
                    actif=ACTIF,
                    quantite=Decimal("10"),
                    prix_de_revient_banque=Decimal("20.10"),
                )
            ],
        )

        ligne = rapprochement.lignes[0]
        assert ligne.prix_de_revient_moteur == Decimal("20.000000")
        assert ligne.prix_de_revient_banque == Decimal("20.10")
        assert rapprochement.tout_concorde
        assert rapprochement.signalements == ()

    def test_un_actif_detenu_dans_deux_poches_n_affiche_aucun_prix_de_revient(self):
        # Deux poches, c'est deux prix de revient : en montrer un seul serait trompeur.
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-06 09:00",
                poche=Poche.CTO,
                quantite="5",
                prix_unitaire="30.00",
            ),
        ]
        rapprochement = rapprocher(
            Portefeuille.construire(operations),
            [PositionReelle(actif=ACTIF, quantite=Decimal("15"))],
        )

        assert rapprochement.lignes[0].prix_de_revient_moteur is None
