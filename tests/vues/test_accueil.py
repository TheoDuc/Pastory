"""L'accueil, le dépôt d'un export, et l'état de l'écran (étape 9, bloc 9.1)."""

from __future__ import annotations

import base64

import pytest

from pastory.vues import bandeau, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues.application import creer
from pastory.vues.chiffres import Chiffres, Echec
from pastory.vues.reception import EXTENSION_PROVISOIRE, recevoir
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import identifiants, texte


def _contenu(octets: bytes) -> str:
    """Ce que la zone de dépôt du navigateur transmet."""
    return "data:text/csv;base64," + base64.b64encode(octets).decode()


@pytest.fixture
def dossier_de_depot(dossier_personnel):
    return dossier_personnel / "exports"


@pytest.fixture
def un_export(tmp_path) -> bytes:
    """Un export des transactions fictif, tel que l'application de la banque le donne."""
    dossier = fictifs.deposer(tmp_path / "telechargements")
    return (dossier / "Exportation de transactions.csv").read_bytes()


def rendu(chiffres: Chiffres, **etat) -> ecrans.Rendu:
    return ecrans.rendre(chiffres, {**etat_ecran.initial(), **etat})


class TestPremierLancement:
    """Aucun export : l'accueil est le seul écran, et il dit quoi faire (conception §5.1)."""

    def test_l_accueil_dit_ou_trouver_l_export_et_ou_le_deposer(self, dossier_de_depot):
        onglets, compteur, _, filtres_caches, etat, corps = rendu(Chiffres())

        lu = texte(corps)
        assert "Profil → Relevés → Export des transactions" in lu
        assert "toutes les transactions" in lu
        assert "Déposez votre export ici" in lu
        assert str(dossier_de_depot) in lu
        assert "depot" in identifiants(corps)

    def test_ce_n_est_pas_une_erreur(self, dossier_de_depot):
        lu = texte(rendu(Chiffres())[5]).replace(str(dossier_de_depot), "")
        assert "erreur" not in lu.lower()

    def test_aucun_compteur_ni_filtre_ni_etat_tant_que_rien_n_est_lu(self):
        _, compteur, filtres, caches, etat, _ = rendu(Chiffres())
        assert compteur == []
        assert filtres == [] and caches is True
        assert etat == []

    def test_aucun_onglet_tant_qu_aucun_export_n_est_lu(self):
        """Des onglets qui ramènent tous au dépôt feraient croire qu'il y a quelque chose
        derrière (arbitrage du propriétaire, bloc 9.1)."""
        onglets, _, _, _, _, corps = rendu(Chiffres(), onglet="diversification")
        assert onglets == []
        assert "Déposez votre export ici" in texte(corps)

    def test_les_onglets_apparaissent_des_le_premier_export(self, dossier_de_depot):
        fictifs.deposer(dossier_de_depot)
        onglets = rendu(Chiffres(hors_ligne=True), onglet=bandeau.ACCUEIL)[0]
        assert "Synthèse" in texte(onglets)

    def test_l_absence_d_export_est_un_etat_et_non_une_panne(self):
        base = Chiffres().base()
        assert isinstance(base, Echec)
        assert base.nature == "aucun-export"


class TestApresLeDepot:
    @pytest.fixture
    def chiffres(self, dossier_de_depot):
        fictifs.deposer(dossier_de_depot)
        return Chiffres(hors_ligne=True)

    def test_la_periode_couverte_est_dite(self, chiffres):
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[5])
        assert "Période couverte" in lu
        assert "Vos exports" in lu

    def test_un_type_inconnu_est_affiche_jamais_ignore(self, chiffres):
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[5])
        assert "Type inconnu" in lu
        assert fictifs.TYPE_INCONNU in lu

    def test_le_compteur_a_surveiller_apparait(self, chiffres):
        compteur = rendu(chiffres)[1]
        assert compteur and "À surveiller" in texte(compteur)

    def test_l_etat_des_donnees_dit_la_periode_de_l_export(self, chiffres):
        assert "Export du 02/01/2026 au 01/08/2026" in texte(rendu(chiffres)[4])

    def test_sans_aucun_cours_la_date_des_cours_n_est_pas_inventee(self, chiffres):
        """Hors ligne, aucun cours n'est connu : dire « arrêtés au » aujourd'hui serait faux."""
        etat = texte(rendu(chiffres)[4])
        assert "Cours arrêtés au" not in etat
        assert "aucun cours connu" in etat

    def test_les_filtres_de_la_synthese_sont_la_periode_et_les_poches(self, chiffres):
        filtres, caches = rendu(chiffres, onglet="synthese")[2:4]
        assert not caches
        assert "Période" in texte(filtres) and "Poches" in texte(filtres)
        assert "Type d'actif" not in texte(filtres)

    @pytest.mark.parametrize("onglet", ["diversification", "frais"])
    def test_diversification_et_frais_n_ont_aucun_filtre(self, chiffres, onglet):
        filtres, caches = rendu(chiffres, onglet=onglet)[2:4]
        assert filtres == [] and caches is True

    def test_une_poche_absente_ne_se_coche_pas(self, chiffres):
        filtres = rendu(chiffres, onglet="synthese")[2]
        boutons = {
            b.id["valeur"]: b
            for b in _boutons(filtres)
            if isinstance(getattr(b, "id", None), dict) and b.id["choix"] == "poche"
        }
        presentes = {p.value for p in Chiffres(hors_ligne=True).vue("tout").poches_presentes}
        for valeur, bouton in boutons.items():
            assert bool(getattr(bouton, "disabled", False)) is (valeur not in presentes)


def _boutons(composant):
    from tests.vues.outils import noeuds

    return [n for n in noeuds(composant) if type(n).__name__ == "Button"]


class TestReception:
    def test_un_export_est_range_dans_le_dossier_de_depot(self, dossier_de_depot, un_export):
        nom = "Exportation de transactions.csv"
        reception = recevoir(nom, _contenu(un_export), dossier_de_depot)

        assert reception.accepte
        assert reception.fichier == dossier_de_depot / "Exportation de transactions.csv"
        assert reception.fichier.read_bytes() == un_export
        assert f"{fictifs.NOMBRE_DE_LIGNES} lignes" in reception.message

    def test_un_fichier_qui_n_est_pas_un_export_est_refuse_et_pas_copie(self, dossier_de_depot):
        pas_un_export = _contenu(b"date;magasin\n2026-01-01;x\n")
        reception = recevoir("courses.csv", pas_un_export, dossier_de_depot)

        assert not reception.accepte
        assert "n'est pas un export" in reception.message
        assert "Rien n'a été copié" in reception.message
        assert list(dossier_de_depot.iterdir()) == []

    def test_rien_n_est_jamais_ecrase(self, dossier_de_depot, un_export):
        dossier_de_depot.mkdir(parents=True)
        (dossier_de_depot / "export.csv").write_bytes(b"un autre fichier")

        reception = recevoir("export.csv", _contenu(un_export), dossier_de_depot)

        assert reception.fichier == dossier_de_depot / "export (2).csv"
        assert (dossier_de_depot / "export.csv").read_bytes() == b"un autre fichier"
        assert "un fichier de ce nom existait" in reception.message

    def test_le_meme_fichier_depose_deux_fois_n_est_pas_double(self, dossier_de_depot, un_export):
        recevoir("export.csv", _contenu(un_export), dossier_de_depot)
        reception = recevoir("export.csv", _contenu(un_export), dossier_de_depot)

        assert reception.accepte and reception.fichier is None
        assert "déjà déposé" in reception.message
        assert [p.name for p in dossier_de_depot.iterdir()] == ["export.csv"]

    def test_aucun_fichier_provisoire_ne_reste(self, dossier_de_depot, un_export):
        recevoir("a.csv", _contenu(un_export), dossier_de_depot)
        recevoir("b.csv", _contenu(b"pas un export"), dossier_de_depot)
        assert not [p for p in dossier_de_depot.iterdir() if p.suffix == EXTENSION_PROVISOIRE]

    def test_le_depot_est_lu_par_l_application(self, dossier_de_depot, un_export):
        chiffres = Chiffres(hors_ligne=True)
        assert isinstance(chiffres.base(), Echec)

        recevoir("export.csv", _contenu(un_export), dossier_de_depot)
        chiffres.relire()

        assert not isinstance(chiffres.base(), Echec)


class TestEtat:
    PRESENTES = ["PEA", "CTO", "crypto"]

    def appliquer(self, etat, champ, valeur):
        return etat_ecran.appliquer(etat, champ, valeur, self.PRESENTES)

    def test_la_derniere_poche_ne_se_decoche_jamais(self):
        etat = etat_ecran.initial()
        etat = self.appliquer(etat, "poche", "PEA")
        etat = self.appliquer(etat, "poche", "CTO")
        assert etat["poches"] == ["crypto"]
        etat = self.appliquer(etat, "poche", "crypto")
        assert etat["poches"] == ["crypto"]

    def test_toutes_les_poches_cochees_reviennent_a_toutes(self):
        etat = self.appliquer(etat_ecran.initial(), "poche", "CTO")
        assert etat["poches"] == ["PEA", "crypto"]
        etat = self.appliquer(etat, "poche", "CTO")
        assert etat["poches"] is None

    def test_une_poche_absente_ne_change_rien(self):
        etat = etat_ecran.appliquer(etat_ecran.initial(), "poche", "PEA", ["CTO"])
        assert etat["poches"] is None

    def test_le_tri_bascule_sur_la_meme_colonne(self):
        etat = self.appliquer(etat_ecran.initial(), "tri", "nom")
        assert (etat["tri"], etat["sens"]) == ("nom", 1)
        etat = self.appliquer(etat, "tri", "nom")
        assert etat["sens"] == -1
        etat = self.appliquer(etat, "tri", "valeur")
        assert (etat["tri"], etat["sens"]) == ("valeur", -1)

    def test_le_compteur_mene_au_bloc_a_surveiller(self):
        etat = self.appliquer(etat_ecran.initial(), "surveiller", "detail")
        assert etat["onglet"] == "detail"
        assert etat["ancre"] == "a-surveiller"

    def test_une_valeur_inconnue_est_ignoree(self):
        etat = self.appliquer(etat_ecran.initial(), "periode", "10 ans")
        assert etat["periode"] == "tout"


def test_l_application_se_construit_et_sert_sa_page(dossier_personnel):
    application = creer(Chiffres(hors_ligne=True))
    client = application.server.test_client()

    page = client.get("/")
    assert page.status_code == 200
    assert 'lang="fr"' in page.get_data(as_text=True)
    assert client.get("/assets/pastory.css").status_code == 200
    assert client.get("/assets/dessin.js").status_code == 200
    assert client.get("/assets/polices/ibm-plex-sans-latin-400-normal.woff2").status_code == 200


class TestIdentifiantsUniques:
    """Dash ne sait pas gérer deux éléments du même nom : le clic sur l'un se perd. C'est ainsi
    que l'onglet « Synthèse » ne répondait plus depuis l'accueil, dont le bouton « Voir la
    synthèse » portait le même identifiant (relecture du propriétaire, bloc 9.1)."""

    @pytest.mark.parametrize(
        "onglet", [bandeau.ACCUEIL, *(o.cle for o in bandeau.ONGLETS)]
    )
    def test_chaque_identifiant_est_unique_dans_la_page(self, dossier_de_depot, onglet):
        fictifs.deposer(dossier_de_depot)
        page = list(rendu(Chiffres(hors_ligne=True), onglet=onglet))
        tous = [repr(i) for i in identifiants(page)]
        doubles = sorted({i for i in tous if tous.count(i) > 1})
        assert not doubles, f"identifiants en double : {doubles}"

    def test_voir_la_synthese_mene_a_la_synthese(self):
        etat = etat_ecran.appliquer(
            {**etat_ecran.initial(), "onglet": bandeau.ACCUEIL}, "aller", "synthese", []
        )
        assert etat["onglet"] == "synthese"
