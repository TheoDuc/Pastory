"""Le « Détail des calculs » (conception §4.6) : chaque chiffre doit se refaire à la main."""

from __future__ import annotations

import pytest

from pastory.vues import ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import noeuds, texte
from tests.vues.portefeuille import coter


def corps(chiffres, **etat):
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": "detail", **etat})[5]


def section(page, titre):
    return next(n for n in noeuds(page) if type(n).__name__ == "Section" and titre in texte(n))


@pytest.fixture
def chiffres(dossier_personnel):
    return coter(dossier_personnel)


class TestLeGain:
    def test_il_se_recompose_a_la_main(self, chiffres):
        total = chiffres.vue("tout").synthese.total
        somme = sum(un.montant for un in total.flux)
        assert total.valeur_fin - (total.valeur_debut or 0) + somme == total.gain
        bloc = texte(section(corps(chiffres), "Comment le gain est obtenu"))
        assert f.montant(total.valeur_fin) in bloc
        assert f.montant_signe(somme) in bloc
        assert f.montant_signe(total.gain) in bloc

    def test_la_periode_choisie_s_applique(self, chiffres):
        un_mois = chiffres.vue("1m").synthese.total.gain
        assert f.montant_signe(un_mois) in texte(
            section(corps(chiffres, periode="1m"), "Comment le gain est obtenu")
        )

    def test_l_ecart_avec_la_colonne_est_explique(self, chiffres):
        bloc = texte(section(corps(chiffres), "Pourquoi il ne tombe pas"))
        assert "Écart, qui est normal" in bloc
        assert "capital net investi" in bloc


class TestLesTables:
    def test_la_table_du_tri_est_celle_du_moteur(self, chiffres):
        total = chiffres.vue("tout").synthese.total
        bloc = section(corps(chiffres), "Les flux datés")
        corps_du_tableau = next(n for n in noeuds(bloc) if type(n).__name__ == "Tbody")
        assert len(corps_du_tableau.children) == len(total.table_du_tri)
        assert f.taux(total.tri) in texte(bloc)

    def test_les_sous_periodes_du_twrr(self, chiffres):
        twrr = chiffres.vue("tout").synthese.total.twrr
        bloc = section(corps(chiffres), "Les sous-périodes")
        corps_du_tableau = next(n for n in noeuds(bloc) if type(n).__name__ == "Tbody")
        assert len(corps_du_tableau.children) == len(twrr.sous_periodes)


def test_une_estimation_montre_son_calcul(chiffres):
    bloc = texte(section(corps(chiffres), "Une estimation, de bout en bout"))
    assert "×" in bloc and "Estimé" in bloc


def test_les_reglages_sont_replies_avec_leur_compte(chiffres):
    repli = next(
        n
        for n in noeuds(corps(chiffres))
        if type(n).__name__ == "Details" and "D'où viennent les réglages" in texte(n)
    )
    assert not getattr(repli, "open", False)
    assert "corrigée" in texte(repli) and "introuvable" in texte(repli)


def test_a_surveiller_vit_desormais_ici(chiffres):
    bloc = texte(section(corps(chiffres), "À surveiller"))
    assert "Type inconnu" in bloc
    assert fictifs.TYPE_INCONNU in bloc
