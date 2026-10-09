"""Le chapitre V, « Projections » (D-97, D-105) : ce que l'écran pose, et ce qu'il dit."""

from __future__ import annotations

import json
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory.vues import ecrans, projections
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from tests.vues.outils import dessins, identifiants, noeuds, texte
from tests.vues.portefeuille import coter


@pytest.fixture
def chiffres(dossier_personnel):
    return coter(dossier_personnel)


def page(chiffres):
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": "projections"})[4]


class TestLaPage:
    def test_la_valeur_de_depart_est_celle_des_actifs(self, chiffres):
        valeur = chiffres.vue("tout").synthese.valorisation.total.valeur
        (champ,) = [
            n for n in noeuds(page(chiffres)) if getattr(n, "id", None) == "projection-depart"
        ]
        assert champ.value == float(valeur.quantize(Decimal("0.01")))
        assert f.montant(valeur) in texte(page(chiffres))

    def test_les_champs_et_la_case(self, chiffres):
        ids = set(identifiants(page(chiffres)))
        assert {
            "projection-depart", "projection-taux", "projection-duree", "projection-versement",
            "projection-alea", "projection-montant", "projection-courbe",
        } <= ids

    def test_les_hypotheses_sont_affichees(self, chiffres):
        lu = texte(page(chiffres))
        assert "log-normale" in lu
        assert "2 fois le taux" in lu
        assert "nominal" in lu
        assert "sous-estime les krachs" in lu
        assert "pas une prévision ni un conseil" in lu

    def test_on_choisit_sa_lecture_par_deux_boutons(self, chiffres):
        """« Une courbe | 10 000 simulations » : un choix, pas une case à cocher."""
        (choix,) = [
            n for n in noeuds(page(chiffres)) if getattr(n, "id", None) == "projection-alea"
        ]
        assert [o["value"] for o in choix.options] == [projections.SIMPLE, projections.ALEA]
        assert choix.value == projections.SIMPLE

    def test_l_ordre_de_la_page(self, chiffres):
        """Le montant, puis la courbe, puis les hypothèses (retour du propriétaire)."""
        ordre = [
            n.id
            for n in noeuds(page(chiffres))
            if getattr(n, "id", None)
            in ("projection-montant", "projection-courbe", "projection-depart")
        ]
        assert ordre == ["projection-montant", "projection-courbe", "projection-depart"]


class TestLeResultat:
    def test_sans_alea_le_montant_du_cahier(self):
        montant, courbe = projections.resultat(1000, 5, 10, 100, False, Date(2026, 10, 9))
        lu = texte(montant)
        assert f.montant(Decimal("17065.21")) in lu
        assert f.montant(Decimal("13000")) in lu  # ce qui a été versé
        assert "octobre 2036" in lu
        (dessin,) = dessins(courbe, "projection")
        donnees = json.loads(getattr(dessin, "data-donnees"))
        assert [s["libelle"] for s in donnees["series"]] == ["Total versé", "Sans aléa"]
        assert len(donnees["lecture"]) == 121

    def test_avec_alea_les_cinq_quantiles(self):
        montant, courbe = projections.resultat(1000, 5, 10, 100, True, Date(2026, 10, 9))
        lu = texte(montant)
        assert "Dans 8 cas sur 10" in lu
        assert "Médiane" in lu and "Sans aléa" in lu
        (dessin,) = dessins(courbe, "projection")
        donnees = json.loads(getattr(dessin, "data-donnees"))
        assert [s["libelle"] for s in donnees["series"]] == [
            "Total versé", "90 %", "75 %", "Médiane", "25 %", "10 %",
        ]

    def test_une_hypothese_hors_bornes_dit_pourquoi(self):
        montant, courbe = projections.resultat(1000, 45, 10, 100, False)
        assert "Le taux doit être compris entre 0 % et 30 %." in texte(montant)
        assert dessins(courbe, "projection") == []

    def test_un_montant_enorme_ne_fait_pas_tomber_la_page(self):
        """Relecture : 1e27 faisait sortir le calcul de sa précision, et le rappel plantait."""
        montant, _courbe = projections.resultat(1e27, 5, 1, 0, False)
        assert "un milliard" in texte(montant)

    def test_la_courbe_part_de_la_date_de_la_valeur(self):
        montant, _courbe = projections.resultat(1000, 5, 10, 100, False, Date(2026, 3, 15))
        assert "mars 2036" in texte(montant)

    def test_au_dela_de_vingt_ans_un_point_par_trimestre(self):
        _montant, courbe = projections.resultat(1000, 5, 40, 100, True, Date(2026, 1, 1))
        (dessin,) = dessins(courbe, "projection")
        donnees = json.loads(getattr(dessin, "data-donnees"))
        assert len(donnees["lecture"]) == 40 * 4 + 1
        assert donnees["lecture"][-1]["d"] == "janv. 2066"


class TestSansValeur:
    def test_le_champ_reste_vide(self):
        """Sans valeur connue, aucune valeur par défaut (D-80) : le champ est vide."""
        page_vide = projections._hypotheses(None, None)
        (champ,) = [n for n in noeuds(page_vide) if getattr(n, "id", None) == "projection-depart"]
        assert champ.value is None
        montant, _ = projections.resultat(None, 5, 10, 100, False)
        assert "Indiquez la valeur de départ." in texte(montant)
