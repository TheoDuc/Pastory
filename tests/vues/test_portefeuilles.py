"""Les portefeuilles à l'écran : en ouvrir un, le renommer, le supprimer (D-109).

Deux comptes fictifs : celui de la ligne de commande (des actions, un ETF, de la crypto), et
celui d'un proche, qui ne détient qu'un titre que l'autre n'a pas.
"""

from __future__ import annotations

import pytest

from pastory import demonstration
from pastory.adaptateurs.trade_republic import depot
from pastory.vues import application, bandeau, ecrans, portefeuilles
from pastory.vues import etat as etat_ecran
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_fictif
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import classes, identifiants, noeuds, texte
from tests.vues.test_feuille_de_style import classes_definies

LE_MIEN = "Exportation de transactions"
TITRE_DU_PROCHE = "XX0000000099"


def rendu(chiffres: Chiffres, **etat) -> ecrans.Rendu:
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), **etat})


def actifs(chiffres: Chiffres) -> set[str]:
    return {position.actif for position in chiffres.base().portefeuille.positions}


def boutons(composant) -> list:
    return [n for n in noeuds(composant) if type(n).__name__ == "Button"]


@pytest.fixture
def dossier(dossier_personnel):
    return fictifs.deposer(dossier_personnel / "exports")


@pytest.fixture
def chiffres(dossier):
    return Chiffres(hors_ligne=True)


@pytest.fixture
def avec_un_proche(dossier):
    """Le dossier avec un second portefeuille ; le mien reste ouvert."""
    export_fictif.deposer(
        dossier,
        [export_fictif.achat_ordre_cto(symbol=TITRE_DU_PROCHE, name="Titre d'un proche")],
        nom="Camille.csv",
    )
    depot.ouvrir(dossier, LE_MIEN)
    return dossier


class TestAvecUnSeulPortefeuille:
    """Rien ne change pour qui n'a qu'un export : ni choix, ni nom dans la navigation."""

    def test_aucun_choix_n_est_propose(self, chiffres):
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        assert "portefeuilles" not in classes(corps)
        assert "Votre livre" in texte(corps)
        assert "Ouvert" not in texte(corps)

    def test_la_navigation_ne_porte_pas_de_nom(self, chiffres):
        assert "nom-du-portefeuille" not in classes(rendu(chiffres, onglet="synthese")[1])

    def test_on_peut_quand_meme_le_renommer_et_le_supprimer(self, chiffres):
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        assert portefeuilles.bouton("renommer", LE_MIEN) in identifiants(corps)
        assert "Supprimer" in [b.children for b in boutons(corps)]

    def test_la_zone_de_depot_dit_ce_que_devient_un_fichier(self, chiffres):
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
        assert "plus récent, il met ce portefeuille à jour" in lu
        assert "d'un autre compte, il devient un autre portefeuille" in lu
        assert "se cumulent" not in lu


class TestAvecPlusieurs:
    def test_la_couverture_propose_le_choix_et_marque_celui_qui_est_ouvert(
        self, chiffres, avec_un_proche
    ):
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        choix = {
            b.children: getattr(b, "aria-pressed")
            for b in boutons(corps)
            if getattr(b, "id", None) == portefeuilles.bouton("ouvrir", b.children)
        }
        assert choix == {"Camille": "false", LE_MIEN: "true"}

    def test_l_etiquette_porte_le_nom_du_portefeuille_ouvert(self, chiffres, avec_un_proche):
        titres = [
            n.children
            for n in noeuds(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
            if getattr(n, "className", "") == "cartouche__titre"
        ]
        assert titres == [LE_MIEN]

    def test_le_nom_reste_dans_la_navigation_de_chaque_chapitre(self, chiffres, avec_un_proche):
        for onglet in (o.cle for o in bandeau.ONGLETS):
            a_droite = rendu(chiffres, onglet=onglet)[1]
            assert "nom-du-portefeuille" in classes(a_droite), onglet
            assert LE_MIEN in texte(a_droite)

    def test_chaque_portefeuille_est_dit_calcule_seul(self, chiffres, avec_un_proche):
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
        assert "Chaque portefeuille est calculé seul" in lu
        assert "l'impôt estimé non plus" in lu

    def test_les_chiffres_sont_ceux_du_portefeuille_ouvert_et_de_lui_seul(
        self, chiffres, avec_un_proche
    ):
        les_miens = actifs(chiffres)
        assert TITRE_DU_PROCHE not in les_miens

        assert portefeuilles.agir(chiffres, "ouvrir", "Camille") is None
        assert actifs(chiffres) == {TITRE_DU_PROCHE}

        portefeuilles.agir(chiffres, "ouvrir", LE_MIEN)
        assert actifs(chiffres) == les_miens

    def test_chaque_identifiant_est_unique_dans_la_page(self, chiffres, avec_un_proche):
        for etat in ({}, {"a_supprimer": "Camille"}):
            tous = [repr(i) for i in identifiants(list(rendu(chiffres, **etat)))]
            assert sorted({i for i in tous if tous.count(i) > 1}) == []

    def test_chaque_classe_a_sa_regle(self, chiffres, avec_un_proche):
        posees = set()
        for etat in ({}, {"a_supprimer": "Camille"}, {"onglet": "synthese"}):
            posees |= classes(list(rendu(chiffres, **etat)))
        assert not posees - classes_definies()


class TestRenommer:
    def test_le_nouveau_nom_est_partout(self, chiffres, avec_un_proche):
        message = portefeuilles.agir(chiffres, "renommer", "Camille", "  Sacha ")

        assert message == {
            "accepte": True,
            "mot": "Renommé",
            "texte": "« Camille » s'appelle désormais « Sacha ».",
        }
        assert [p.nom for p in chiffres.inventaire().portefeuilles] == [LE_MIEN, "Sacha"]
        assert chiffres.inventaire().ouvert.nom == LE_MIEN

    def test_un_nom_refuse_s_explique_et_ne_change_rien(self, chiffres, avec_un_proche):
        message = portefeuilles.agir(chiffres, "renommer", "Camille", "a/b")
        assert message["accepte"] is False and "nom de fichier" in message["texte"]

        message = portefeuilles.agir(chiffres, "renommer", "Camille", LE_MIEN.upper())
        assert message["accepte"] is False and "déjà" in message["texte"]
        assert [p.nom for p in chiffres.inventaire().portefeuilles] == ["Camille", LE_MIEN]

    def test_le_meme_nom_ne_dit_rien(self, chiffres, avec_un_proche):
        assert portefeuilles.agir(chiffres, "renommer", "Camille", "Camille") is None


class TestSupprimer:
    def test_un_premier_clic_ne_supprime_rien_il_pose_la_question(self, chiffres, avec_un_proche):
        etat = etat_ecran.appliquer(etat_ecran.initial(), "supprimer", "Camille", [])
        assert etat["a_supprimer"] == "Camille"

        corps = rendu(chiffres, **etat)[4]
        assert "Supprimer « Camille » ?" in texte(corps)
        assert portefeuilles.bouton("supprimer", "Camille") in identifiants(corps)
        (volet,) = [n for n in noeuds(corps) if getattr(n, "className", "") == "volet"]
        assert volet.open is True
        assert (avec_un_proche / "Camille.csv").exists()

    def test_tout_autre_clic_retire_la_question(self):
        etat = etat_ecran.appliquer(etat_ecran.initial(), "supprimer", "Camille", [])
        assert etat_ecran.appliquer(etat, "supprimer", "", [])["a_supprimer"] is None
        assert etat_ecran.appliquer(etat, "onglet", "synthese", [])["a_supprimer"] is None

    def test_la_confirmation_efface_le_fichier_et_lui_seul(self, chiffres, avec_un_proche):
        les_miens = actifs(chiffres)

        message = portefeuilles.agir(chiffres, "supprimer", "Camille")

        assert message["mot"] == "Supprimé"
        assert f"« {LE_MIEN} » est ouvert" in message["texte"]
        assert not (avec_un_proche / "Camille.csv").exists()
        assert actifs(chiffres) == les_miens

    def test_le_portefeuille_ouvert_supprime_cede_la_place(self, chiffres, avec_un_proche):
        portefeuilles.agir(chiffres, "supprimer", LE_MIEN)
        assert actifs(chiffres) == {TITRE_DU_PROCHE}

    def test_le_dernier_supprime_la_couverture_redevient_vide(self, chiffres, dossier):
        message = portefeuilles.agir(chiffres, "supprimer", LE_MIEN)

        assert message["texte"] == f"« {LE_MIEN} » est supprimé."
        onglets, _, _, _, corps, _ = rendu(chiffres)
        assert onglets == []
        assert "Déposez votre export ici" in texte(corps)

    def test_un_portefeuille_disparu_entre_temps_se_dit(self, chiffres, avec_un_proche):
        (avec_un_proche / "Camille.csv").unlink()
        message = portefeuilles.agir(chiffres, "supprimer", "Camille")
        assert message["accepte"] is False and "n'est plus dans le dossier" in message["texte"]
        assert [p.nom for p in chiffres.inventaire().portefeuilles] == [LE_MIEN]


class TestLaOuLOnNeChoisitPas:
    def test_la_demonstration_n_a_ni_choix_ni_gestion(self, dossier_personnel):
        demonstration.preparer()
        chiffres = Chiffres(hors_ligne=True)

        assert chiffres.inventaire() is None
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        assert "portefeuilles" not in classes(corps)
        assert not [i for i in identifiants(corps) if isinstance(i, dict) and "renommer" in i]
        assert portefeuilles.agir(chiffres, "supprimer", "x")["accepte"] is False

    def test_l_export_d_un_tiers_non_plus(self, avec_un_proche, tmp_path):
        chiffres = Chiffres(dossier=avec_un_proche / "Camille.csv", hors_ligne=True)

        assert chiffres.inventaire() is None
        assert actifs(chiffres) == {TITRE_DU_PROCHE}
        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        assert "portefeuilles" not in classes(corps)
        assert portefeuilles.agir(chiffres, "ouvrir", LE_MIEN)["accepte"] is False


def test_l_application_ecoute_les_boutons_des_portefeuilles(chiffres):
    """Le rappel existe : sans lui, les boutons de la couverture ne feraient rien."""
    rappels = application.creer(chiffres).callback_map.values()
    assert any(portefeuilles.CHAMP in str(rappel.get("inputs")) for rappel in rappels)
