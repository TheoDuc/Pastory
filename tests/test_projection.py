"""La prédiction de l'évolution (D-105) : le calcul, refaisable à la main (glossaire §9)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pastory import projection as p

CENTIME = Decimal("0.01")
NEGATIF = "La valeur de départ et le versement ne peuvent pas être négatifs."


def hypotheses(depart=1000, taux=5, annees=10, versement=100) -> p.Hypotheses:
    h = p.lire(depart, taux, annees, versement)
    assert isinstance(h, p.Hypotheses), h
    return h


class TestSansAlea:
    def test_le_cas_du_cahier(self):
        """1 000 €, 5 % par an, 10 ans, 100 € à la fin de chaque mois : 17 065,21 €
        (docs/verification/etape-9-bis.md, refait à la calculatrice)."""
        h = hypotheses()
        assert p.sans_alea(h)[-1].quantize(CENTIME) == Decimal("17065.21")

    def test_mois_par_mois_egale_la_forme_fermee(self):
        for h in (hypotheses(), hypotheses(5000, 7.5, 30, 250), hypotheses(0, 2, 1, 50)):
            assert p.sans_alea(h)[-1].quantize(CENTIME) == p.forme_fermee(h).quantize(CENTIME)

    def test_douze_mois_font_une_annee_au_taux(self):
        """Sans versement, un an à 5 % donne exactement 5 % de plus."""
        h = hypotheses(1000, 5, 1, 0)
        assert p.sans_alea(h)[-1].quantize(CENTIME) == Decimal("1050.00")

    def test_un_taux_nul_ne_fait_qu_additionner(self):
        h = hypotheses(1000, 0, 2, 100)
        assert p.sans_alea(h)[-1] == Decimal("3400")
        assert p.forme_fermee(h) == Decimal("3400")

    def test_ce_qui_a_ete_verse(self):
        assert hypotheses().verse == Decimal("13000")

    def test_une_trajectoire_par_mois(self):
        assert len(p.sans_alea(hypotheses())) == 121


class TestAvecAlea:
    def test_la_meme_graine_donne_les_memes_courbes(self):
        h = hypotheses()
        assert p.avec_alea(h).quantiles == p.avec_alea(h).quantiles

    def test_le_tableau_du_cahier(self):
        """Le cas du cahier, avec 10 000 simulations : le tableau de
        docs/verification/etape-9-bis.md, au centime près (graine fixe)."""
        e = p.avec_alea(hypotheses())
        assert [e.a_la_fin(q) for q in p.QUANTILES] == [
            Decimal("13313.00"), Decimal("14983.43"), Decimal("17136.67"),
            Decimal("19673.44"), Decimal("22195.94"),
        ]

    def test_les_quantiles_sont_ordonnes(self):
        e = p.avec_alea(hypotheses())
        for mois in range(1, 121):
            valeurs = [e.quantiles[q][mois] for q in p.QUANTILES]
            assert valeurs == sorted(valeurs)

    def test_un_taux_nul_n_a_aucune_dispersion(self):
        """La volatilité vaut deux fois le taux : à 0 %, tous les chemins sont la courbe sans
        aléa."""
        h = hypotheses(1000, 0, 5, 100)
        e = p.avec_alea(h)
        for q in p.QUANTILES:
            assert e.a_la_fin(q) == p.sans_alea(h)[-1].quantize(CENTIME)

    def test_sans_versement_la_mediane_est_la_courbe_simple(self):
        """Le taux est celui de la médiane (D-105). Seul reste l'écart du tirage."""
        h = hypotheses(10_000, 7, 20, 0)
        mediane = p.avec_alea(h).a_la_fin(50)
        simple = p.sans_alea(h)[-1]
        assert abs(mediane - simple) / simple < Decimal("0.02")

    def test_plus_le_taux_est_eleve_plus_l_eventail_est_large(self):
        def largeur(taux):
            e = p.avec_alea(hypotheses(1000, taux, 20, 0))
            return e.a_la_fin(90) / e.a_la_fin(10)

        assert largeur(15) > largeur(4) > 1

    def test_la_volatilite_vaut_deux_fois_le_taux(self):
        assert hypotheses(taux=4).volatilite == Decimal("0.08")
        assert hypotheses(taux=15).volatilite == Decimal("0.30")


class TestLesBornes:
    @pytest.mark.parametrize(
        ("entrees", "motif"),
        [
            ((None, 5, 10, 0), "Indiquez la valeur de départ."),
            ((1000, "", 10, 0), "Indiquez le taux."),
            ((1000, 31, 10, 0), "Le taux doit être compris entre 0 % et 30 %."),
            ((1000, -1, 10, 0), "Le taux doit être compris entre 0 % et 30 %."),
            ((1000, 5, 0, 0), "La durée doit être un nombre entier d'années, de 1 à 50."),
            ((1000, 5, 2.5, 0), "La durée doit être un nombre entier d'années, de 1 à 50."),
            ((1000, 5, 51, 0), "La durée doit être un nombre entier d'années, de 1 à 50."),
            ((-5, 5, 10, 0), NEGATIF),
            ((1000, 5, 10, -1), NEGATIF),
            ((1e27, 5, 10, 0), "La valeur de départ ne peut pas dépasser un milliard d'euros."),
            ((0, 5, 10, 1e12), "Le versement mensuel ne peut pas dépasser dix millions d'euros."),
        ],
    )
    def test_une_entree_hors_bornes_donne_son_motif(self, entrees, motif):
        """Jamais une valeur choisie en silence à la place de celle saisie."""
        assert p.lire(*entrees) == motif


def test_le_module_est_independant_du_moteur():
    """D-27 : rien du moteur, de la lecture ni des vues."""
    source = p.__file__
    with open(source, encoding="utf-8") as fichier:
        texte = fichier.read()
    for interdit in ("pastory.moteur", "pastory.adaptateurs", "pastory.vues", "pastory.reglages"):
        assert interdit not in texte
