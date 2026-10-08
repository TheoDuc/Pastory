"""L'onglet « Les actifs » (conception §4.3) : un tableau, filtrable et triable, dont chaque ligne
dit elle-même ce qui lui manque."""

from __future__ import annotations

from datetime import date as Date
from types import SimpleNamespace

import pytest

from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.valorisation import PositionValorisee
from pastory.pivot.operation import TypeOperation
from pastory.vues import actifs, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.moteur.operations_fictives import operation
from tests.vues.outils import noeuds, texte
from tests.vues.portefeuille import coter


def corps(chiffres, **etat):
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": "actifs", **etat})[5]


def lignes(page) -> list[str]:
    corps_du_tableau = next(n for n in noeuds(page) if type(n).__name__ == "Tbody")
    return [texte(tr) for tr in corps_du_tableau.children]


def pied(page) -> str:
    return texte(next(n for n in noeuds(page) if type(n).__name__ == "Tfoot"))


@pytest.fixture
def chiffres(dossier_personnel):
    return coter(dossier_personnel)


class TestLeTableau:
    def test_une_ligne_par_actif_detenu(self, chiffres):
        vue = chiffres.vue("tout")
        assert len(lignes(corps(chiffres))) == len(vue.synthese.valorisation.positions)

    def test_les_colonnes_de_la_maquette(self, chiffres):
        entetes = [c.nom for c in actifs.COLONNES]
        assert entetes == [
            "Actif", "Poche", "Quantité", "Prix de revient", "Capital net investi", "Cours",
            "Valeur", "+/− latente", "",
        ]

    def test_les_chiffres_sont_ceux_du_moteur(self, chiffres):
        vue = chiffres.vue("tout")
        page = texte(corps(chiffres))
        for p in vue.synthese.valorisation.positions:
            assert f.montant(p.valeur) in page
            assert f.quantite(p.quantite) in page

    def test_par_defaut_de_la_plus_grande_valeur_a_la_plus_petite(self, chiffres):
        vue = chiffres.vue("tout")
        attendu = sorted(vue.synthese.valorisation.positions, key=lambda p: p.valeur, reverse=True)
        assert [f.montant(p.valeur) in ligne for p, ligne in zip(attendu, lignes(corps(chiffres)),
                                                                   strict=True)] == [True] * 3

    def test_le_tri_par_nom_va_de_a_a_z(self, chiffres):
        noms = [ligne.split(" XX")[0] for ligne in lignes(corps(chiffres, tri="nom", sens=1))]
        assert noms == sorted(noms, key=str.casefold)

    def test_le_cours_dit_sa_date_et_sa_place_au_survol(self, chiffres):
        titres = [
            n.title for n in noeuds(corps(chiffres)) if getattr(n, "title", None)
            and "Cours de clôture" in n.title
        ]
        assert titres and all("XETRA" in t and "brut" in t for t in titres)

    def test_le_pied_est_la_somme_des_lignes_affichees(self, chiffres):
        vue = chiffres.vue("tout")
        total = sum(p.valeur for p in vue.synthese.valorisation.positions)
        assert "Total — 3 lignes" in pied(corps(chiffres))
        assert f.montant(total) in pied(corps(chiffres))


class TestLesFiltres:
    def test_le_type_ne_garde_que_ses_actifs(self, chiffres):
        page = corps(chiffres, type="etf")
        assert len(lignes(page)) == 1
        assert "· ETF" in lignes(page)[0]

    def test_un_filtre_sans_resultat_le_dit_et_ne_montre_pas_un_tableau_vide(
        self, dossier_personnel
    ):
        chiffres = coter(dossier_personnel)
        page = corps(chiffres, type="action", poches=["CTO"])
        assert "c'est le filtre qui est en cause, pas vos données" in texte(page)

    def test_la_poche_filtre_le_tableau(self, chiffres):
        page = corps(chiffres, poches=["crypto"])
        assert len(lignes(page)) == 1


class TestPartiel:
    @pytest.fixture
    def chiffres(self, dossier_personnel):
        return coter(dossier_personnel, sauf=(fictifs.ACTIF_CRYPTO,))

    @pytest.mark.parametrize("sens", [1, -1])
    def test_la_ligne_sans_cours_reste_en_bas_dans_les_deux_sens(self, chiffres, sens):
        derniere = lignes(corps(chiffres, tri="valeur", sens=sens))[-1]
        assert "Sans cours" in derniere

    def test_elle_dit_pourquoi_sur_la_ligne(self, chiffres):
        derniere = lignes(corps(chiffres))[-1]
        assert "Sans cours" in derniere and len(derniere) > 60

    def test_le_pied_la_compte_a_part(self, chiffres):
        assert "1 sans cours" in pied(corps(chiffres))


class TestSansAucunCours:
    def test_la_valeur_totale_est_inconnue_pas_nulle(self, dossier_personnel):
        fictifs.deposer(dossier_personnel / "exports")
        page = corps(Chiffres(hors_ligne=True))
        assert "aucune ligne valorisée" in pied(page)
        assert "0,00 €" not in pied(page).split("aucune")[0].split("lignes")[1].split()[-1]


def test_une_histoire_trouee_ne_donne_pas_de_prix_de_revient():
    """Un prix de revient tiré d'une histoire incomplète serait artificiellement bas, sans que
    rien ne le dise (D-45) : il est « à compléter », et la ligne dit pourquoi. Le cas : trois
    parts reçues sans prix, toujours détenues."""
    position = Portefeuille.construire(
        [
            operation(TypeOperation.ACHAT, horodatage="2026-01-05 09:00", quantite="10",
                      prix_unitaire="20.00"),
            operation(TypeOperation.TITRES_RECUS, horodatage="2026-03-01 09:00", quantite="3",
                      prix_a_completer=True),
        ]
    ).positions[0]
    ligne = PositionValorisee(position=position, date=Date(2026, 3, 2), cours=None, motif="x")
    vue = SimpleNamespace(construit=SimpleNamespace(reglages=None, diversification=None))

    assert actifs._prix_de_revient(ligne) == "à compléter"
    assert "Histoire incomplète" in texte(actifs._remarques(ligne, vue))
