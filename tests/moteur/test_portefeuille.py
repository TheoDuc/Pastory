"""L'agrégation : par poche, au total, et à une date donnée.

Ce qui est vérifié ici, plus que les nombres eux-mêmes : **chaque total se retrouve en
additionnant la colonne correspondante du tableau des positions**. Sans cela, le propriétaire
ne pourrait pas refaire les chiffres dans un tableur.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pastory.moteur.portefeuille import Portefeuille
from pastory.pivot.operation import Poche, TypeOperation
from tests.moteur.operations_fictives import operation

AUTRE_ACTIF = "XX0000000002"


def portefeuille_fictif() -> Portefeuille:
    """Trois actifs dans trois poches, avec des frais, un dividende et une vente."""
    return Portefeuille.construire(
        [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="20.00",
                frais="1.00",
            ),
            operation(
                TypeOperation.DIVIDENDE,
                horodatage="2026-04-20 09:00",
                poche=Poche.PEA,
                quantite="10",
                prix_unitaire="0.50",
                taxes="1.50",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-02-05 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.CTO,
                quantite="4",
                prix_unitaire="25.00",
            ),
            operation(
                TypeOperation.VENTE,
                horodatage="2026-06-05 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.CTO,
                quantite="2",
                prix_unitaire="30.00",
                frais="1.00",
            ),
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-03-05 09:00",
                actif="XF000ABCDEF1",
                poche=Poche.CRYPTO,
                quantite="0.001000",
                prix_unitaire="30000.00",
                montant_brut="30.00",
            ),
        ]
    )


class TestTotaux:
    def test_le_total_est_la_somme_des_positions(self):
        portefeuille = portefeuille_fictif()

        somme = sum(
            (position.etat.capital_net_investi for position in portefeuille.positions),
            Decimal("0.00"),
        )
        assert portefeuille.total.capital_net_investi == somme
        assert portefeuille.total.capital_net_investi == Decimal("280.00")

    def test_chaque_poche_a_ses_propres_totaux(self):
        par_poche = portefeuille_fictif().par_poche()

        assert par_poche[Poche.PEA].capital_net_investi == Decimal("200.00")
        assert par_poche[Poche.CTO].capital_net_investi == Decimal("50.00")
        assert par_poche[Poche.CRYPTO].capital_net_investi == Decimal("30.00")

    def test_les_poches_sortent_dans_l_ordre_pea_cto_crypto(self):
        # L'ordre d'affichage ne doit pas dépendre de l'ordre des opérations dans l'export.
        assert list(portefeuille_fictif().par_poche()) == [Poche.PEA, Poche.CTO, Poche.CRYPTO]

    def test_les_couts_restent_separes_de_la_performance(self):
        """D-21 : rien de ce qui est prélevé n'entre dans un montant brut."""
        total = portefeuille_fictif().total

        assert total.frais == Decimal("2.00")
        assert total.taxes == Decimal("1.50")
        # 200 € en PEA, 100 € en CTO, 30 € en crypto.
        assert total.achats_bruts == Decimal("330.00")
        assert total.dividendes_bruts == Decimal("5.00")
        # Deux parts sur quatre vendues 60 € brut, pour 50 € de capital retiré.
        assert total.plus_values_realisees_brutes == Decimal("10.00")
        assert total.plus_values_realisees_nettes == Decimal("9.00")

    def test_un_portefeuille_vide_donne_des_totaux_a_zero_sans_planter(self):
        total = Portefeuille.construire([]).total

        assert total.nombre_de_positions == 0
        assert total.capital_net_investi == Decimal("0.00")
        assert total.historique_incomplet is False


class TestPositionsDetenues:
    def test_un_actif_entierement_vendu_sort_des_positions_detenues(self):
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
        portefeuille = Portefeuille.construire(operations)

        assert portefeuille.positions_detenues == []
        # ... mais il reste dans les positions : sa plus-value compte dans les totaux.
        assert len(portefeuille.positions) == 1
        assert portefeuille.total.plus_values_realisees_brutes == Decimal("20.00")


class TestAUneDate:
    def test_le_portefeuille_se_coupe_a_la_fin_du_jour_demande(self):
        portefeuille = portefeuille_fictif()

        au_15_fevrier = portefeuille.au(date(2026, 2, 15))

        assert au_15_fevrier.total.capital_net_investi == Decimal("300.00")
        assert au_15_fevrier.total.dividendes_bruts == Decimal("0.00")

    def test_une_position_nee_apres_la_date_disparait(self):
        au_debut = portefeuille_fictif().au(date(2026, 1, 31))

        assert [position.poche for position in au_debut.positions] == [Poche.PEA]

    def test_avant_la_premiere_operation_le_portefeuille_est_vide(self):
        avant = portefeuille_fictif().au(date(2025, 12, 31))

        assert avant.positions == ()
        assert avant.total.capital_net_investi == Decimal("0.00")


class TestFiabilite:
    def test_une_position_incomplete_contamine_le_total_de_sa_poche(self):
        """Le total est alors sous-estimé, et le rapport doit pouvoir le dire (D-45)."""
        operations = [
            operation(
                TypeOperation.ACHAT,
                horodatage="2026-01-05 09:00",
                poche=Poche.CTO,
                quantite="10",
                prix_unitaire="20.00",
            ),
            operation(
                TypeOperation.TITRES_RECUS,
                horodatage="2026-03-01 09:00",
                actif=AUTRE_ACTIF,
                poche=Poche.CTO,
                quantite="3",
                prix_a_completer=True,
            ),
        ]
        portefeuille = Portefeuille.construire(operations)

        assert portefeuille.total.historique_incomplet is True
        assert [position.actif for position in portefeuille.positions_incompletes] == [
            AUTRE_ACTIF
        ]
