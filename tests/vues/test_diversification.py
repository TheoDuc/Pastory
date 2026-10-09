"""L'onglet « Diversification » (conception §4.4) : rien n'est ramené à 100 %, ce qui manque reste
visible, et chaque chiffre dit d'où il vient."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from pastory.vues import diversification, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues import format as f
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import dessins, noeuds, texte
from tests.vues.portefeuille import composer, coter

RACINE = Path(__file__).parents[2]


def corps(chiffres, rubrique="classes"):
    etat = {**etat_ecran.initial(), "onglet": "diversification", "rubrique": rubrique}
    return ecrans.rendre(chiffres, etat)[5]


def rangs(page) -> list[str]:
    return [
        texte(n)
        for n in noeuds(page)
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
            n
            for n in noeuds(corps(chiffres))
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
        repartition = (
            d.classes
            if rubrique == "classes"
            else (d.secteurs if rubrique == "secteurs" else d.pays)
        )
        page = texte(corps(chiffres, rubrique))
        assert f"base {f.montant(repartition.base)}" in page or f.montant_entier(repartition.base)

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
        images = {n.src for n in noeuds(corps(chiffres, "pays")) if type(n).__name__ == "Img"}
        assert {f"/assets/drapeaux/{c}.svg" for c in ("us", "fr", "jp")} <= images

    def test_un_code_sans_drapeau_garde_le_globe(self, chiffres):
        """« ZZ » n'est pas un pays : il n'a pas de drapeau, et garde le globe dessiné."""
        assert [donnees(d) for d in dessins(corps(chiffres, "pays"), "drapeau")] == ["ZZ"]

    def test_chaque_pays_du_referentiel_a_son_drapeau(self):
        """Demandé par le propriétaire : l'Espagne, l'Afrique du Sud… n'avaient qu'un globe."""
        import re

        zones = (RACINE / "pastory/parametres/zones.toml").read_text(encoding="utf-8")
        codes = re.findall(r"^\[pays\.([A-Z]{2})\]", zones, flags=re.M)
        assert len(codes) > 80
        manquants = [
            c
            for c in codes
            if not (diversification.DOSSIER_DES_DRAPEAUX / f"{c.lower()}.svg").exists()
        ]
        assert manquants == []

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


class TestLaMemeMiseEnPagePartout:
    """Anneaux puis carrés essayés et écartés par le propriétaire : les quatre rubriques
    s'affichent comme les pays, en pleine largeur, sans dessin."""

    @pytest.mark.parametrize("rubrique", ["classes", "zones", "pays", "secteurs"])
    def test_aucun_dessin_de_repartition(self, chiffres, rubrique):
        page = corps(chiffres, rubrique)
        assert dessins(page, "anneau") == []
        assert "Vu en" not in texte(page)

    @pytest.mark.parametrize("rubrique", ["classes", "zones", "pays", "secteurs"])
    def test_des_chiffres_cles_en_tete(self, chiffres, rubrique):
        tuiles = [
            n
            for n in noeuds(corps(chiffres, rubrique))
            if "tuile" in (getattr(n, "className", "") or "").split()
        ]
        assert len(tuiles) >= 2

    def test_la_zone_principale_est_la_plus_grosse(self, chiffres):
        zones = chiffres.base().diversification.pays.par_zone()
        principale = max(zones, key=lambda z: z[1])
        page = texte(corps(chiffres, "zones"))
        assert "Zone principale" in page and principale[0].libelle in page

    def test_la_part_en_actions_est_celle_du_moteur(self, chiffres):
        r = chiffres.base().diversification.classes
        actions = next(p for p in r.postes if p.code == "actions")
        assert f.pour_cent(r.pour_cent(actions.montant)) in texte(corps(chiffres, "classes"))


class TestLesZonesSeDeplient:
    def test_une_zone_se_deplie_vers_ses_pays(self, chiffres):
        page = corps(chiffres, "zones")
        deroulants = [n for n in noeuds(page) if getattr(n, "className", "") == "deroulant"]
        europe = next(d for d in deroulants if "Europe" in texte(d.children[0]))
        assert "France" in texte(europe)

    def test_les_pays_y_portent_leur_drapeau(self, chiffres):
        page = corps(chiffres, "zones")
        images = {n.src for n in noeuds(page) if type(n).__name__ == "Img"}
        assert "/assets/drapeaux/fr.svg" in images


class TestLesRestesReplies:
    """Arbitrage du propriétaire : ce qui n'a pas de pays ou de secteur tient sur une ligne,
    dépliable, et reste visible à sa vraie taille (D-69)."""

    def test_une_seule_ligne_qui_dit_le_total(self, chiffres):
        r = chiffres.base().diversification.secteurs
        total = r.non_attribue + r.hors_perimetre + r.hors_classification + r.non_couvert
        page = corps(chiffres, "secteurs")
        replis = [n for n in noeuds(page) if getattr(n, "className", "") == "deroulant"]
        assert len(replis) == 1  # les secteurs n'ont pas de groupes : seul « Sans secteur »
        assert "Sans secteur" in texte(replis[0].children[0])
        assert f.montant(total) in texte(replis[0].children[0])

    def test_le_detail_est_dans_le_repli(self, chiffres):
        page = corps(chiffres, "pays")
        repli = next(n for n in noeuds(page) if getattr(n, "className", "") == "deroulant")
        assert "Actifs numériques" in texte(repli)

    def test_les_classes_d_actifs_gardent_leur_detail(self, chiffres):
        page = corps(chiffres, "classes")
        assert not [n for n in noeuds(page) if getattr(n, "className", "") == "deroulant"]


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


class TestLesLongsClassements:
    def test_au_dela_de_quinze_postes_un_bouton_dit_ce_qui_est_cache(self):
        lignes = [
            diversification.Ligne(f"Pays {i}", Decimal(100 - i), Decimal(20 - i) / 2, ("picto", ""))
            for i in range(20)
        ]
        replie = texte(diversification._classement(lignes, [], deplie=False))
        assert "Afficher les 5 autres" in replie
        assert "Pays 14" in replie and "Pays 15" not in replie

    def test_deplie_tout_est_montre_et_le_bouton_replie(self):
        lignes = [
            diversification.Ligne(f"Pays {i}", Decimal(100 - i), Decimal(1), ("picto", ""))
            for i in range(20)
        ]
        deplie = texte(diversification._classement(lignes, [], deplie=True))
        assert "Pays 19" in deplie
        assert "N'afficher que les 15 premiers" in deplie

    def test_les_restes_ne_sont_jamais_caches(self):
        lignes = [
            diversification.Ligne(f"Pays {i}", Decimal(100 - i), Decimal(1), ("picto", ""))
            for i in range(20)
        ]
        reste = diversification.Ligne(
            "Non couvert", Decimal(1), Decimal(1), ("picto", ""), absent=True
        )
        assert "Non couvert" in texte(diversification._classement(lignes, [reste], deplie=False))


def test_ce_qu_il_faut_savoir_est_replie_par_defaut(chiffres):
    repli = next(n for n in noeuds(corps(chiffres)) if type(n).__name__ == "Details")
    assert not getattr(repli, "open", False)
    assert "Ce qu'il faut savoir de ces chiffres" in texte(repli)
