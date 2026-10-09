"""L'onglet « Frais et taxes » (conception §4.5) : trois niveaux, le payé séparé de l'estimé."""

from __future__ import annotations

import pytest

from pastory.vues import ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import noeuds, texte
from tests.vues.portefeuille import coter


def corps(chiffres):
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": "frais"})[5]


@pytest.fixture
def chiffres(dossier_personnel):
    return coter(dossier_personnel)


class TestLesTroisNiveaux:
    def test_dans_l_ordre_du_paye_a_l_estime(self, chiffres):
        page = texte(corps(chiffres))
        positions = [
            page.index("1. Ce qui a déjà été prélevé"),
            page.index("2. Pendant la détention"),
            page.index("3. À la sortie"),
        ]
        assert positions == sorted(positions)

    def test_le_paye_est_celui_du_moteur(self, chiffres):
        total = chiffres.base().detail_des_couts.total
        assert f.montant(total.cout_paye) in texte(corps(chiffres))

    def test_un_spread_est_toujours_marque_estime(self, chiffres):
        """D-17 : un montant estimé ne se mélange jamais à un montant prélevé, et le dit."""
        preleve = next(
            n
            for n in noeuds(corps(chiffres))
            if type(n).__name__ == "Section" and "1. Ce qui a déjà" in texte(n)
        )
        assert "Spread payé à l'achat" in texte(preleve)
        assert "Estimé" in texte(preleve)


class TestLaDetention:
    def test_le_ter_dit_sa_source_au_survol(self, chiffres):
        titres = [
            n.title
            for n in noeuds(corps(chiffres))
            if type(n).__name__ == "Td" and (getattr(n, "title", None) or "").startswith("0,2 % ")
        ]
        assert titres == ["0,2 % — corrigé par vous dans actifs.toml"]

    def test_une_action_n_a_pas_de_ter_et_le_dit(self, chiffres):
        assert "sans objet : une action n'a pas de TER" in texte(corps(chiffres))

    def test_les_frais_courants_sont_ceux_du_moteur(self, chiffres):
        detail = chiffres.base().detail_des_couts
        (etf,) = [fc for fc in detail.frais_courants if fc.estimation is not None]
        assert f.montant(etf.estimation.montant) in texte(corps(chiffres))


class TestLaSortie:
    def test_la_valeur_reelle_est_celle_du_moteur(self, chiffres):
        valeur = chiffres.base().valeur_reelle
        page = texte(corps(chiffres))
        assert "Si vous vendiez tout aujourd'hui" in page
        assert f.montant(valeur.valeur_brute) in page

    def test_une_poche_sans_impot_calculable_dit_pourquoi(self, chiffres):
        valeur = chiffres.base().valeur_reelle
        motifs = [g.motif_incalculable for g in valeur.par_poche.values() if g.motif_incalculable]
        for motif in motifs:
            assert motif in texte(corps(chiffres))


def test_les_taux_sont_replies_avec_leur_source(chiffres):
    repli = next(
        n
        for n in noeuds(corps(chiffres))
        if type(n).__name__ == "Details" and "D'où viennent les taux" in texte(n)
    )
    assert not getattr(repli, "open", False)


def test_sans_aucun_cours_rien_n_est_estime(dossier_personnel):
    fictifs.deposer(dossier_personnel / "exports")
    page = texte(corps(Chiffres(hors_ligne=True)))
    assert "Aucune position valorisée : il n'y a rien à estimer." in page
