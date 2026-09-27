"""Ce que valent les actifs : quantité × cours, et rien quand il n'y a pas de cours.

Le moteur reçoit les cours par un protocole qu'il déclare lui-même. Ces tests le nourrissent
avec une source réduite à un dictionnaire ; le dernier vérifie que le vrai fournisseur de
l'étape 4 a bien la forme attendue — sans qu'aucun des deux modules n'importe l'autre.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_tr.donnees_externes.cours import FournisseurDeCours
from dashboard_tr.moteur import valorisation
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.pivot.operation import Poche, TypeOperation
from tests.donnees_externes import cours_fictifs as fournisseur_fictif
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, enchainement_du_glossaire, operation

AUTRE_ACTIF = "XX0000000002"


def portefeuille_du_glossaire() -> Portefeuille:
    """10 parts à 20 €, 10 à 30 €, 5 vendues à 40 € : 15 parts, capital 375 €."""
    return Portefeuille.construire(enchainement_du_glossaire())


class TestUnePosition:
    def test_la_valeur_est_quantite_fois_cours(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = valorisation.valoriser(portefeuille_du_glossaire(), date(2026, 3, 31), source)

        [position] = resultat.positions
        assert position.valeur == Decimal("600.00")  # 15 x 40
        assert position.plus_value_latente == Decimal("225.00")  # 600 - 375
        assert not position.jour_decale
        assert resultat.complete
        assert resultat.total.valeur == Decimal("600.00")

    def test_la_valeur_s_arrete_au_centime(self):
        # 15 parts x 40,333 = 604,995 : arrondi au centime supérieur, comme tout montant.
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.333"}})

        [position] = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 3, 31), source
        ).positions

        assert position.valeur == Decimal("605.00")

    def test_un_samedi_prend_le_cours_du_vendredi_et_le_dit(self):
        # Le 2026-03-28 est un samedi : la bourse était fermée.
        source = SourceFixe({ACTIF: {date(2026, 3, 27): "40.00"}})

        [position] = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 3, 28), source
        ).positions

        assert position.valeur == Decimal("600.00")
        assert position.jour_decale
        assert position.cours is not None
        assert position.cours.date == date(2026, 3, 27)

    def test_la_position_est_prise_telle_qu_elle_etait_ce_jour_la(self):
        # Le 2026-02-10, la vente n'a pas encore eu lieu : 20 parts, pas 15.
        source = SourceFixe(cours_constant(ACTIF, "35.00", date(2026, 1, 1), date(2026, 3, 31)))

        [position] = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 2, 10), source
        ).positions

        assert position.quantite == Decimal("20")
        assert position.valeur == Decimal("700.00")

    def test_avant_le_premier_achat_il_n_y_a_rien_a_valoriser(self):
        source = SourceFixe(cours_constant(ACTIF, "35.00", date(2025, 1, 1), date(2026, 3, 31)))

        resultat = valorisation.valoriser(portefeuille_du_glossaire(), date(2025, 12, 31), source)

        assert resultat.positions == ()
        assert resultat.total.valeur == Decimal("0.00")
        assert source.demandes == []


class TestCeQuiNEstPasValorise:
    def test_sans_cours_la_position_est_dite_non_valorisee_et_le_total_partiel(self):
        portefeuille = Portefeuille.construire(
            enchainement_du_glossaire()
            + [
                operation(
                    TypeOperation.ACHAT,
                    horodatage="2026-01-10 09:00",
                    actif=AUTRE_ACTIF,
                    quantite="4",
                    prix_unitaire="50.00",
                )
            ]
        )
        # Seul le premier actif a un cours.
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        resultat = valorisation.valoriser(portefeuille, date(2026, 3, 31), source)

        assert not resultat.complete
        [exclue] = resultat.non_valorisees
        assert exclue.actif == AUTRE_ACTIF
        assert exclue.valeur is None
        assert exclue.plus_value_latente is None
        assert "Cours de marché" in (exclue.motif or "")
        # Le total ne compte que ce qui est valorisé, et le dit : jamais un zéro silencieux.
        assert resultat.total.valeur == Decimal("600.00")
        assert resultat.total.nombre_de_positions == 2
        assert resultat.total.nombre_valorisees == 1
        assert not resultat.total.complet

    def test_un_cours_dans_une_autre_devise_est_refuse(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}}, devise="USD")

        [position] = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 3, 31), source
        ).positions

        assert not position.valorisee
        assert "USD" in (position.motif or "")
        assert "D-48" in (position.motif or "")

    def test_une_histoire_incomplete_a_une_valeur_mais_pas_de_plus_value(self):
        # 4 parts achetées, 10 vendues : la quantité tombe à zéro (D-45)... donc rien à
        # valoriser. Prenons plutôt des titres reçus sans prix : les parts sont là, le capital
        # est sous-estimé, et la plus-value latente serait gonflée.
        portefeuille = Portefeuille.construire(
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
        source = SourceFixe({ACTIF: {date(2026, 3, 31): "40.00"}})

        [position] = valorisation.valoriser(portefeuille, date(2026, 3, 31), source).positions

        assert position.valeur == Decimal("520.00")  # 13 x 40 : les parts sont bien là
        assert position.plus_value_latente is None
        assert not position.fiable


class TestParPoche:
    def test_les_totaux_par_poche_s_additionnent_en_un_total(self):
        portefeuille = Portefeuille.construire(
            [
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
                    actif=AUTRE_ACTIF,
                    poche=Poche.CTO,
                    quantite="2",
                    prix_unitaire="100.00",
                ),
            ]
        )
        source = SourceFixe(
            {ACTIF: {date(2026, 3, 31): "25.00"}, AUTRE_ACTIF: {date(2026, 3, 31): "90.00"}}
        )

        resultat = valorisation.valoriser(portefeuille, date(2026, 3, 31), source)
        par_poche = resultat.par_poche()

        assert par_poche[Poche.PEA].valeur == Decimal("250.00")
        assert par_poche[Poche.CTO].valeur == Decimal("180.00")
        assert resultat.total.valeur == Decimal("430.00")
        assert list(par_poche) == [Poche.PEA, Poche.CTO]
        assert resultat.sources == ["Source de test"]


class TestEvolution:
    def test_un_point_par_jour_avec_la_valeur_et_le_capital(self):
        # Les cours ne sont connus que les 5 et 7 janvier : le 6 reprend celui du 5.
        source = SourceFixe(
            {ACTIF: {date(2026, 1, 5): "21.00", date(2026, 1, 7): "22.00"}}
        )

        points = valorisation.evolution(
            portefeuille_du_glossaire(), date(2026, 1, 4), date(2026, 1, 7), source
        )

        assert [point.date for point in points] == [
            date(2026, 1, 4),
            date(2026, 1, 5),
            date(2026, 1, 6),
            date(2026, 1, 7),
        ]
        assert [point.valeur for point in points] == [
            Decimal("0.00"),
            Decimal("210.00"),
            Decimal("210.00"),
            Decimal("220.00"),
        ]
        assert points[0].capital_net_investi == Decimal("0.00")
        assert points[1].capital_net_investi == Decimal("200.00")
        assert points[1].par_poche == {Poche.CTO: Decimal("210.00")}
        assert all(point.non_valorisees == 0 for point in points)

    def test_un_jour_sans_cours_compte_ses_positions_non_valorisees(self):
        source = SourceFixe({ACTIF: {date(2026, 3, 1): "40.00"}})

        [point] = valorisation.evolution(
            portefeuille_du_glossaire(), date(2026, 1, 20), date(2026, 1, 20), source
        )

        assert point.valeur == Decimal("0.00")
        assert point.non_valorisees == 1


class TestLeFournisseurDeLEtape4ALaFormeAttendue:
    """Aucun import entre `moteur/` et `donnees_externes/` : c'est ici, dans les tests, que
    la compatibilité des deux se prouve."""

    def test_le_fournisseur_de_cours_valorise_un_portefeuille(self):
        fournisseur = FournisseurDeCours(
            fournisseur_fictif.configuration(),
            fournisseur_fictif.CacheEnMemoire(),
            fournisseur_fictif.SourceFictive(
                {ACTIF: [fournisseur_fictif.cours(date(2026, 3, 27), "40.00")]}
            ),
            aujourd_hui=date(2026, 3, 31),
        )

        resultat = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 3, 28), fournisseur
        )

        [position] = resultat.positions
        assert position.valeur == Decimal("600.00")
        assert position.jour_decale
        assert resultat.sources == ["Source de test"]

    def test_un_refus_du_fournisseur_devient_une_position_non_valorisee(self):
        # L'actif n'est pas déclaré : le fournisseur refuse, et garde le motif.
        fournisseur = FournisseurDeCours(
            fournisseur_fictif.configuration({}),
            fournisseur_fictif.CacheEnMemoire(),
            None,
            hors_ligne=True,
            aujourd_hui=date(2026, 3, 31),
        )

        resultat = valorisation.valoriser(
            portefeuille_du_glossaire(), date(2026, 3, 31), fournisseur
        )

        assert not resultat.complete
        [refus] = fournisseur.refus
        assert refus.categorie == "actif non déclaré"
