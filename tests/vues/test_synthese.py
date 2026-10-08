"""L'onglet « Synthèse » (conception §4.2), dans ses états : complet, partiel, sans cours."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from pastory.pivot.operation import Poche
from pastory.vues import ecrans, synthese
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import dessins, noeuds, texte
from tests.vues.portefeuille import coter


def corps(chiffres, **etat):
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": "synthese", **etat})[5]


def tuiles(page) -> list[str]:
    return [
        texte(n) for n in noeuds(page) if "tuile" in (getattr(n, "className", "") or "").split()
    ]


def donnees(composant) -> dict:
    return json.loads(getattr(composant, "data-donnees"))


@pytest.fixture
def chiffres(dossier_personnel):
    return coter(dossier_personnel)


class TestLesTuiles:
    def test_le_gain_d_abord_puis_tri_twrr_valeur_capital(self, chiffres):
        etiquettes = [t.split(" ")[0] for t in tuiles(corps(chiffres))]
        assert etiquettes == ["Gain", "TRI", "TWRR", "Valeur", "Capital"]

    def test_les_chiffres_sont_ceux_du_moteur(self, chiffres):
        vue = chiffres.vue("tout")
        gain, tri, twrr, valeur, capital = tuiles(corps(chiffres))
        assert f.montant_signe(vue.synthese.total.gain) in gain
        assert f.taux(vue.synthese.total.tri) in tri
        assert f.taux(vue.synthese.total.twrr.taux) in twrr
        assert f.montant(vue.synthese.valorisation.total.valeur) in valeur
        assert f.montant(vue.portefeuille.total.capital_net_investi) in capital

    def test_moins_d_un_an_est_dit_peu_fiable(self, chiffres):
        assert chiffres.vue("tout").synthese.total.peu_significatif
        _, tri, _, _, _ = tuiles(corps(chiffres))
        assert "Peu fiable" in tri

    def test_la_plus_value_latente_porte_son_signe(self, chiffres):
        capital = tuiles(corps(chiffres))[4]
        assert "plus-value latente +" in capital or "plus-value latente −" in capital


class TestLesFiltres:
    def test_une_poche_seule_retombe_sur_le_chiffre_du_moteur_pour_cette_poche(self, chiffres):
        """Le TRI de « PEA » filtré est celui que le moteur calcule pour la poche PEA : le
        filtre rejoue le sous-portefeuille, il ne fait aucune moyenne."""
        complet = chiffres.vue("tout").synthese.par_poche[Poche.PEA]
        filtre = chiffres.vue("tout", ["PEA"]).synthese.total
        assert filtre.gain == complet.gain
        assert filtre.tri == complet.tri

    def test_la_periode_change_le_gain(self, chiffres):
        tout = chiffres.vue("tout").synthese.total.gain
        un_mois = chiffres.vue("1m").synthese.total.gain
        assert un_mois != tout
        assert f.montant_signe(un_mois) in tuiles(corps(chiffres, periode="1m"))[0]

    def test_les_cartes_ne_montrent_que_les_poches_choisies(self, chiffres):
        page = corps(chiffres, poches=["PEA"])
        cartes = [n for n in noeuds(page) if getattr(n, "className", "") == "jeton"]
        assert {texte(c) for c in cartes} == {"PEA"}


class TestLaCourbe:
    def test_la_courbe_porte_des_libelles_deja_ecrits(self, chiffres):
        (courbe,) = dessins(corps(chiffres), "courbe")
        d = donnees(courbe)
        premier = d["points"][0]
        assert set(premier) >= {"d", "v", "i", "tv", "ti", "te", "ce"}
        assert premier["tv"].endswith("€") and "/" in premier["d"]
        assert [g["texte"] for g in d["graduations"]][0] == f.montant_entier(Decimal(0))

    def test_elle_part_de_zero_depuis_le_debut(self, chiffres):
        (courbe,) = dessins(corps(chiffres), "courbe")
        assert donnees(courbe)["points"][0]["v"] == 0

    def test_sur_une_periode_elle_part_de_la_veille_du_debut(self, chiffres):
        vue = chiffres.vue("1m")
        (courbe,) = dessins(corps(chiffres, periode="1m"), "courbe")
        assert donnees(courbe)["points"][0]["d"] == f.date_courte(vue.synthese.periode.veille)

    def test_le_plafond_est_au_dessus_du_plus_haut_point(self, chiffres):
        d = donnees(dessins(corps(chiffres), "courbe")[0])
        assert d["plafond"] >= max(max(p["v"], p["i"]) for p in d["points"])


class TestLesPoches:
    def test_anneau_et_liste_de_la_plus_grosse_a_la_plus_petite(self, chiffres):
        page = corps(chiffres)
        (anneau,) = dessins(page, "anneau")
        montants = [p["montant"] for p in donnees(anneau)["parts"]]
        assert montants == sorted(montants, reverse=True)

    def test_une_couleur_suit_sa_poche_et_non_son_rang(self, chiffres):
        (anneau,) = dessins(corps(chiffres, poches=["PEA", "crypto"]), "anneau")
        couleurs = {p["couleur"] for p in donnees(anneau)["parts"]}
        assert couleurs == {
            synthese.COULEUR_DE_POCHE[Poche.PEA],
            synthese.COULEUR_DE_POCHE[Poche.CRYPTO],
        }

    def test_une_seule_poche_n_a_pas_d_anneau(self, chiffres):
        """Un anneau à une seule part ne dit rien (conception §5.1)."""
        page = corps(chiffres, poches=["CTO"])
        assert dessins(page, "anneau") == []
        assert "Où est l'argent" in texte(page)

    def test_les_couleurs_sont_celles_de_la_feuille(self):
        from tests.vues.test_feuille_de_style import CSS

        for numero, poche in enumerate((Poche.PEA, Poche.CTO, Poche.CRYPTO), start=1):
            assert f"--poche-{numero}: {synthese.COULEUR_DE_POCHE[poche]}" in CSS


class TestLesCartes:
    def test_triees_du_plus_au_moins_performant(self, chiffres):
        vue = chiffres.vue("tout")
        attendus = sorted(
            (vue.synthese.de(p.position).twrr.taux for p in vue.synthese.valorisation.positions),
            reverse=True,
        )
        taux = [
            texte(n)
            for n in noeuds(corps(chiffres))
            if "carte__taux" in (getattr(n, "className", "") or "")
        ]
        assert taux == [f.taux(t) for t in attendus]

    def test_un_achat_en_cours_de_periode_est_dit_depuis_l_achat(self, chiffres):
        assert "depuis l'achat du" in texte(corps(chiffres))

    def test_une_page_trop_loin_revient_a_la_derniere(self, chiffres):
        assert "1 / 1" in texte(corps(chiffres, page=7))


class TestPartiel:
    """Un actif sans cours : le reste est juste, et le total le dit (conception §5.2)."""

    @pytest.fixture
    def chiffres(self, dossier_personnel):
        return coter(dossier_personnel, sauf=(fictifs.ACTIF_CRYPTO,))

    def test_la_valeur_est_marquee_partielle(self, chiffres):
        valeur = tuiles(corps(chiffres))[3]
        assert "Partiel" in valeur and "1 sans cours" in valeur

    def test_l_actif_sans_cours_va_en_bas_sans_taux(self, chiffres):
        cartes = [n for n in noeuds(corps(chiffres)) if getattr(n, "className", "") == "carte"]
        assert cartes and "sans cours" in texte(cartes[-1])


class TestSansAucunCours:
    @pytest.fixture
    def chiffres(self, dossier_personnel):
        fictifs.deposer(dossier_personnel / "exports")
        return Chiffres(hors_ligne=True)

    def test_rien_n_est_trace_plutot_qu_une_ligne_a_zero(self, chiffres):
        page = corps(chiffres)
        assert dessins(page, "courbe") == []
        assert "Rien n'est tracé, plutôt qu'une ligne à zéro" in texte(page)

    def test_la_valeur_n_est_pas_zero_elle_est_inconnue(self, chiffres):
        valeur = tuiles(corps(chiffres))[3]
        assert "0,00" not in valeur
        assert "aucune position n'a de cours" in valeur
