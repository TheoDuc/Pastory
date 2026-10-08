"""L'onglet « Diversification » (conception §4.4) : rien n'est ramené à 100 %, ce qui manque reste
visible, et chaque chiffre dit d'où il vient."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from pastory.vues import diversification, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import dessins, noeuds, texte
from tests.vues.portefeuille import composer, coter


def corps(chiffres, rubrique="classes"):
    etat = {**etat_ecran.initial(), "onglet": "diversification", "rubrique": rubrique}
    return ecrans.rendre(chiffres, etat)[5]


def rangs(page) -> list[str]:
    return [
        texte(n) for n in noeuds(page)
        if (getattr(n, "className", "") or "").split()[:1] == ["rang"]
    ]


def donnees(composant) -> dict:
    return json.loads(getattr(composant, "data-donnees"))


@pytest.fixture
def chiffres(dossier_personnel):
    resultat = coter(dossier_personnel)
    composer()
    return resultat


class TestLesSousOnglets:
    def test_quatre_rubriques_dans_l_ordre_des_questions(self, chiffres):
        boutons = [
            n for n in noeuds(corps(chiffres))
            if isinstance(getattr(n, "id", None), dict) and n.id["choix"] == "rubrique"
        ]
        assert [texte(b) for b in boutons] == ["Actifs", "Zone géographique", "Pays", "Secteur"]

    def test_une_rubrique_inconnue_revient_aux_classes(self, chiffres):
        assert "Par classe d'actifs" in texte(corps(chiffres, "n'importe quoi"))


class TestRienNEstRamenéACent:
    """D-69 : la part manquante est une information, pas un défaut de présentation."""

    @pytest.mark.parametrize("rubrique", ["classes", "zones", "pays", "secteurs"])
    def test_les_parts_sont_celles_du_moteur_sur_la_base(self, chiffres, rubrique):
        d = chiffres.base().diversification
        repartition = d.classes if rubrique == "classes" else (
            d.secteurs if rubrique == "secteurs" else d.pays
        )
        page = texte(corps(chiffres, rubrique))
        assert f"base {f.montant(repartition.base)}" in page or f.montant_entier(
            repartition.base
        )

    def test_les_postes_seuls_ne_font_pas_cent(self, chiffres):
        r = chiffres.base().diversification.pays
        total = sum(r.pour_cent(p.montant) for p in r.postes)
        assert total < Decimal("100")

    def test_ce_qui_manque_reste_visible_a_sa_vraie_taille(self, chiffres):
        r = chiffres.base().diversification.pays
        page = texte(corps(chiffres, "pays"))
        assert "Ce qui n'entre pas dans cette répartition" in page
        assert "Non attribué par les fonds" in page
        assert f.montant(r.non_attribue) in page

    def test_l_anneau_hache_ce_qui_manque_au_lieu_de_le_cacher(self, chiffres):
        (anneau,) = dessins(corps(chiffres, "pays"), "anneau")
        parts = donnees(anneau)["parts"]
        assert any(p.get("absent") for p in parts)
        base = float(chiffres.base().diversification.pays.base)
        assert sum(p["montant"] for p in parts) == pytest.approx(base, abs=0.05)

    def test_hors_actions_est_detaille_classe_par_classe(self, chiffres):
        """De l'or n'est pas de la dette : chaque classe sortie des pays a sa ligne (D-71)."""
        assert "Obligations" in " ".join(rangs(corps(chiffres, "pays")))


class TestLesClasses:
    def test_la_crypto_compte_dans_les_classes_d_actifs(self, chiffres):
        lignes = rangs(corps(chiffres, "classes"))
        coupure = texte(corps(chiffres, "classes")).index("Ce qui n'entre pas")
        page = texte(corps(chiffres, "classes"))
        assert any("Actifs numériques" in ligne for ligne in lignes)
        assert page.index("Actifs numériques") < coupure

    def test_mais_hors_des_pays_et_des_secteurs(self, chiffres):
        page = texte(corps(chiffres, "pays"))
        assert page.index("Actifs numériques") > page.index("Ce qui n'entre pas")


class TestLesRepères:
    def test_un_pays_porte_son_drapeau(self, chiffres):
        codes = {donnees(d) for d in dessins(corps(chiffres, "pays"), "drapeau")}
        assert {"US", "FR", "JP"} <= codes

    def test_une_zone_allume_ses_terres(self, chiffres):
        terres = [donnees(d) for d in dessins(corps(chiffres, "zones"), "planisphere")]
        assert ["amNord"] in terres

    def test_un_secteur_porte_son_pictogramme(self, chiffres):
        pictos = {donnees(d) for d in dessins(corps(chiffres, "secteurs"), "picto")}
        assert {"technologie", "finance", "industrie"} <= pictos

    def test_un_code_inconnu_est_affiche_sous_son_code_jamais_dans_autres(self, chiffres):
        page = texte(corps(chiffres, "pays"))
        assert "ZZ (code non reconnu)" in page
        assert "Autres" not in page


class TestCeQuIlFautSavoir:
    def test_deux_origines_se_disent_actif_par_actif(self, chiffres):
        """D-72 : deux sources et deux règles de pays cohabitent, chaque actif dit la sienne."""
        page = texte(corps(chiffres, "pays"))
        assert "D'où vient la composition de chaque actif" in page
        assert "Source des fonds — pays d'activité" in page
        assert "Source des sociétés — siège social" in page

    def test_le_fonds_synthetique_est_nomme(self, chiffres):
        assert "ETF Exemple Monde (Acc)" in texte(corps(chiffres))

    def test_la_nomenclature_est_morningstar_jamais_gics(self, chiffres):
        page = texte(corps(chiffres, "secteurs"))
        assert "Morningstar" in page
        assert "GICS" not in page


class TestNonCouvert:
    def test_un_actif_sans_composition_est_non_couvert_et_dit_pourquoi(self, dossier_personnel):
        chiffres = coter(dossier_personnel)
        composer(sans=(fictifs.ACTIF_ACTION,))
        page = texte(corps(chiffres, "pays"))
        assert "Non couvert" in page
        assert "Non couvert — Action Exemple SA" in page


class TestCouleurs:
    def test_une_couleur_suit_son_poste_et_non_son_rang(self):
        assert diversification.teinte(0, 3) != diversification.teinte(2, 3)
        assert diversification.teinte(0, 4) == "#1c5369"  # hslEnHex(197, 58, 26), la maquette


def test_sans_aucun_cours_il_n_y_a_rien_a_repartir(dossier_personnel):
    fictifs.deposer(dossier_personnel / "exports")
    page = corps(Chiffres(hors_ligne=True))
    assert "il n'y a rien à répartir" in texte(page)
    assert dessins(page, "anneau") == []


def test_un_fonds_sans_secteurs_est_non_couvert_en_secteur_seulement(dossier_personnel):
    """Le cas de la source de secours : des pays, aucun secteur (conception §5.2)."""
    from datetime import date as Date

    from pastory.donnees_externes.cache_compositions import CacheDeCompositions
    from pastory.donnees_externes.composition import Composition, Part

    chiffres = coter(dossier_personnel)
    composer()
    CacheDeCompositions().ecrire(
        Composition(
            actif=fictifs.ACTIF_ETF,
            pays=(Part("US", Decimal("60")), Part("CN", Decimal("40"))),
            secteurs=(),
            classes=(Part("equity_ordinary", Decimal("100")),),
            arrete_le=Date(2026, 8, 31),
            intitule_de_la_date="arrêté de l'indice",
            source="Source de secours",
            recupere_le=Date(2026, 9, 30),
            regle_de_pays="pays de l'indice",
        )
    )
    secteurs = texte(corps(chiffres, "secteurs"))
    pays = texte(corps(chiffres, "pays"))

    assert "Non couvert en secteur seulement — ETF Exemple Monde (Acc)" in secteurs
    assert "Non attribué par les fonds" not in secteurs.split("Ce qu'il faut savoir")[0]
    assert "Chine" in pays
