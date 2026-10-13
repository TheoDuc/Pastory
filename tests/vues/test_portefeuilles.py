"""Les portefeuilles à l'écran : en ouvrir un, le renommer, le supprimer (D-109).

Deux comptes fictifs : celui de la ligne de commande (des actions, un ETF, de la crypto), et
celui d'un proche, qui ne détient qu'un titre que l'autre n'a pas.
"""

from __future__ import annotations

import json

import pytest

from pastory import demonstration
from pastory.adaptateurs.trade_republic import depot
from pastory.config import actifs as config_actifs
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
            if isinstance(b.children, str)
            and getattr(b, "id", None) == portefeuilles.bouton("ouvrir", b.children)
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
        for etat in ({}, {"a_supprimer": portefeuilles.cle("Camille")}):
            tous = [repr(i) for i in identifiants(list(rendu(chiffres, **etat)))]
            assert sorted({i for i in tous if tous.count(i) > 1}) == []

    def test_chaque_classe_a_sa_regle(self, chiffres, avec_un_proche):
        posees = set()
        for etat in ({}, {"a_supprimer": portefeuilles.cle("Camille")}, {"onglet": "synthese"}):
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
        cle = portefeuilles.cle("Camille")
        etat = etat_ecran.appliquer(etat_ecran.initial(), "supprimer", cle, [])
        assert etat["a_supprimer"] == cle

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


class TestCeQueLaRelectureATrouve:
    def test_une_correction_qui_sert_a_un_autre_portefeuille_n_est_pas_dite_inutile(
        self, chiffres, avec_un_proche
    ):
        """Dite « sans actif » dans le portefeuille qui ne détient pas le titre, elle invitait à
        la retirer — et cassait le réglage du voisin. Une correction d'actif vaut pour tous."""
        fichier = config_actifs.chemin()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text(
            "[actifs]\n"
            f'"{TITRE_DU_PROCHE}" = {{ ticker = "PROCHE.DE", devise = "EUR" }}\n'
            '"XX0000000077" = { ticker = "PERSONNE.DE", devise = "EUR" }\n',
            encoding="utf-8",
        )
        chiffres.relire()

        assert chiffres.base().reglages.orphelines == ("XX0000000077",)

    def test_un_portefeuille_perime_se_dit_des_la_couverture(self, chiffres, dossier):
        """Un export plus récent copié à la main à côté de l'ancien : on lirait le périmé."""
        export_fictif.deposer(
            dossier,
            [*fictifs.lignes(), export_fictif.achat_ordre_cto(symbol=TITRE_DU_PROCHE)],
            nom="Plus récent.csv",
        )
        depot.ouvrir(dossier, LE_MIEN)
        chiffres.relire()

        corps = rendu(chiffres, onglet=bandeau.ACCUEIL)[4]
        lu = texte(corps)
        assert "Périmé" in lu
        assert "« Plus récent » contient toutes ses opérations" in lu
        # Une alerte ne se replie jamais : elle est hors du volet du détail.
        (volet,) = [n for n in noeuds(corps) if getattr(n, "className", "") == "volet"]
        assert "contient toutes ses opérations" not in texte(volet)

        portefeuilles.agir(chiffres, "ouvrir", "Plus récent")
        assert "Périmé" not in texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])

    def test_un_geste_sans_effet_ne_fait_pas_tout_recalculer(self, chiffres, avec_un_proche):
        chiffres.base()
        avant = chiffres.version

        assert portefeuilles.agir(chiffres, "ouvrir", LE_MIEN) is None
        assert portefeuilles.agir(chiffres, "renommer", "Camille", " Camille ") is None
        assert chiffres.version == avant

        portefeuilles.agir(chiffres, "ouvrir", "Camille")
        assert chiffres.version == avant + 1

    def test_un_portefeuille_illisible_ne_fait_pas_dire_votre_livre(
        self, chiffres, avec_un_proche, monkeypatch
    ):
        """Le mien verrouillé un instant : Pastory lit celui du proche, mais ne le présente pas
        comme « Votre livre » — il porte son nom, et le fichier illisible est cité."""
        vraie_lecture = depot.fichier.lire

        def lecture(chemin):
            if chemin.stem == LE_MIEN:
                raise PermissionError("accès refusé")
            return vraie_lecture(chemin)

        monkeypatch.setattr(depot.fichier, "lire", lecture)
        chiffres.relire()

        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
        assert "Votre livre" not in lu
        assert "Camille" in lu and "pas pu être ouvert" in lu


def _comme_le_navigateur(identifiant: dict) -> str:
    """L'identifiant tel que le navigateur l'écrit : clés triées, sans espace, accents tels
    quels."""
    return json.dumps(identifiant, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cliquer(interface, identifiant: dict, etat: dict, saisies: dict | None = None) -> dict | None:
    """Un clic sur un bouton de portefeuille, **passé par Dash** comme le fait le navigateur.
    Rend le nouvel état de l'écran, ou `None` si Dash n'a rien changé."""
    sortie = next(
        cle
        for cle, rappel in interface.callback_map.items()
        if portefeuilles.CHAMP in str(rappel.get("inputs"))
    )
    propriete = sortie.partition(".")[2]
    champs = list((saisies or {}).items())
    reponse = interface.server.test_client().post(
        "/_dash-update-component",
        data=json.dumps(
            {
                "output": sortie,
                "outputs": {"id": "etat", "property": propriete},
                "inputs": [[{"id": identifiant, "property": "n_clicks", "value": 1}]],
                "changedPropIds": [_comme_le_navigateur(identifiant) + ".n_clicks"],
                "state": [
                    [
                        {"id": champ, "property": "value", "value": valeur}
                        for champ, valeur in ((portefeuilles.champ_du_nom(n), v) for n, v in champs)
                    ],
                    [
                        {"id": champ, "property": "id", "value": champ}
                        for champ in (portefeuilles.champ_du_nom(n) for n, _ in champs)
                    ],
                    {"id": "etat", "property": "data", "value": etat},
                ],
            }
        ),
        content_type="application/json",
    )
    if reponse.status_code == 204:
        return None
    assert reponse.status_code == 200, reponse.get_data(as_text=True)
    # Dash rend la propriété sous son nom, sans le suffixe qui distingue les rappels.
    (etat_rendu,) = reponse.get_json()["response"]["etat"].values()
    return etat_rendu


class TestUnNomAccentue:
    """Trouvé par le propriétaire : nommé d'un prénom accentué, son portefeuille ne s'ouvrait
    plus. Dash perd la valeur du clic d'un bouton dont l'identifiant porte un accent ; le clic
    était alors pris pour celui d'un bouton qui vient d'apparaître, et ignoré. Aucun test ne
    passait par Dash : ceux-ci le font."""

    ACCENTUE = "Zoé, à Noël"

    @pytest.fixture
    def interface(self, chiffres, avec_un_proche):
        depot.renommer(avec_un_proche, LE_MIEN, self.ACCENTUE)
        depot.ouvrir(avec_un_proche, "Camille")
        chiffres.relire()
        return application.creer(chiffres)

    def test_l_identifiant_d_un_bouton_ne_porte_aucun_accent(self, chiffres, interface):
        corps = rendu(chiffres, a_supprimer=portefeuilles.cle(self.ACCENTUE))
        for identifiant in identifiants(list(corps)):
            assert repr(identifiant).isascii(), identifiant
        assert portefeuilles.nom_de(portefeuilles.cle(self.ACCENTUE)) == self.ACCENTUE
        assert portefeuilles.nom_de("ceci n'est pas une clé") is None

    def test_aucun_identifiant_d_aucun_ecran_ne_porte_d_accent(self, chiffres, interface):
        """Le garde-fou général : la même panne guette tout bouton dont l'identifiant
        reprendrait un texte de l'utilisateur ou un libellé."""
        depot.ouvrir(chiffres.dossier(), self.ACCENTUE)
        chiffres.relire()
        for onglet in [bandeau.ACCUEIL, *(o.cle for o in bandeau.ONGLETS)]:
            for identifiant in identifiants(list(rendu(chiffres, onglet=onglet))):
                assert repr(identifiant).isascii(), (onglet, identifiant)

    def test_un_clic_l_ouvre(self, chiffres, interface, avec_un_proche):
        clic = portefeuilles.bouton("ouvrir", self.ACCENTUE)
        etat = cliquer(interface, clic, etat_ecran.initial())

        assert etat is not None, "Dash n'a rien fait de ce clic"
        assert depot.inventaire(avec_un_proche).ouvert.nom == self.ACCENTUE
        assert TITRE_DU_PROCHE not in actifs(chiffres)

    def test_on_le_renomme_d_un_autre_nom_accentue(self, chiffres, interface, avec_un_proche):
        etat = cliquer(
            interface,
            portefeuilles.bouton("renommer", self.ACCENTUE),
            etat_ecran.initial(),
            saisies={self.ACCENTUE: "Élodie", "Camille": "Camille"},
        )

        assert etat["message"][0]["mot"] == "Renommé"
        assert [p.nom for p in depot.inventaire(avec_un_proche).portefeuilles] == [
            "Camille",
            "Élodie",
        ]

    def test_on_le_supprime_en_deux_clics(self, chiffres, interface, avec_un_proche):
        demande = etat_ecran.appliquer(
            etat_ecran.initial(), "supprimer", portefeuilles.cle(self.ACCENTUE), []
        )
        assert f"Supprimer « {self.ACCENTUE} » ?" in texte(rendu(chiffres, **demande)[4])
        assert (avec_un_proche / f"{self.ACCENTUE}.csv").exists()

        etat = cliquer(interface, portefeuilles.bouton("supprimer", self.ACCENTUE), demande)

        assert etat["a_supprimer"] is None and etat["message"][0]["mot"] == "Supprimé"
        assert [p.nom for p in depot.inventaire(avec_un_proche).portefeuilles] == ["Camille"]

    def test_un_bouton_qui_vient_d_apparaitre_ne_declenche_rien(self, interface, avec_un_proche):
        """La garde qui ignorait les vrais clics est toujours là, pour ce qu'elle doit ignorer."""
        sortie = next(
            cle
            for cle, rappel in interface.callback_map.items()
            if portefeuilles.CHAMP in str(rappel.get("inputs"))
        )
        identifiant = portefeuilles.bouton("supprimer", "Camille")
        reponse = interface.server.test_client().post(
            "/_dash-update-component",
            data=json.dumps(
                {
                    "output": sortie,
                    "outputs": {"id": "etat", "property": sortie.partition(".")[2]},
                    "inputs": [[{"id": identifiant, "property": "n_clicks", "value": 0}]],
                    "changedPropIds": [
                        json.dumps(identifiant, sort_keys=True, separators=(",", ":")) + ".n_clicks"
                    ],
                    "state": [[], [], {"id": "etat", "property": "data", "value": {}}],
                }
            ),
            content_type="application/json",
        )
        assert reponse.status_code == 204
        assert (avec_un_proche / "Camille.csv").exists()
