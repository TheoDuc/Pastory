"""La couverture (l'accueil), le dépôt d'un export, et l'état de l'écran (étape 9, bloc 9.1 ;
étape 9 bis pour la couverture)."""

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
        onglets, compteur, _, filtres_caches, corps, _ = rendu(Chiffres())

        lu = texte(corps)
        assert "Profil → Relevés → Export des transactions" in lu
        assert "toutes les transactions" in lu
        assert "Déposez votre export ici" in lu
        assert str(dossier_de_depot) in lu
        assert "depot" in identifiants(corps)

    def test_ce_n_est_pas_une_erreur(self, dossier_de_depot):
        lu = texte(rendu(Chiffres())[4]).replace(str(dossier_de_depot), "")
        assert "erreur" not in lu.lower()

    def test_aucun_compteur_ni_filtre_ni_etat_tant_que_rien_n_est_lu(self):
        _, compteur, filtres, caches, _, _ = rendu(Chiffres())
        assert compteur == []
        assert filtres == [] and caches is True

    def test_aucun_onglet_tant_qu_aucun_export_n_est_lu(self):
        """Des onglets qui ramènent tous au dépôt feraient croire qu'il y a quelque chose
        derrière (arbitrage du propriétaire, bloc 9.1)."""
        onglets, _, _, _, corps, _ = rendu(Chiffres(), onglet="diversification")
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
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
        assert "Période couverte" in lu
        assert "Votre export" in lu

    def test_un_type_inconnu_est_affiche_jamais_ignore(self, chiffres):
        lu = texte(rendu(chiffres, onglet=bandeau.ACCUEIL)[4])
        assert "Type inconnu" in lu
        assert fictifs.TYPE_INCONNU in lu

    def test_le_detail_des_calculs_est_un_lien_discret_pas_un_onglet(self, chiffres):
        """Arbitrage du propriétaire : le détail n'est pas aussi important que le reste."""
        onglets, lien = rendu(chiffres)[:2]
        assert "Détail des calculs" not in texte(onglets)
        assert "Détail des calculs" in texte(lien)
        assert "À surveiller" not in texte(lien)

    def test_le_colophon_dit_la_periode_de_l_export(self, chiffres):
        """Dans la bulle « d'où viennent ces chiffres », à droite du titre du chapitre."""
        corps = rendu(chiffres, onglet="synthese")[4]
        assert "Export du 02/01/2026 au 01/08/2026" in texte(corps)
        assert "d'où viennent ces chiffres" in texte(corps)

    def test_la_periode_retenue_est_dans_la_bande_des_filtres(self, chiffres):
        """Ce que les filtres ont retenu se lit à côté d'eux, et non plus dans une 3e bande."""
        import re

        filtres = texte(rendu(chiffres, onglet="synthese")[2])
        assert re.search(r"Du \d\d/\d\d/\d{4} au \d\d/\d\d/\d{4} · ", filtres)

    def test_un_chapitre_sans_filtre_a_son_sommaire(self, chiffres):
        """D-104 : la bande garde sa place ; elle porte des choix, jamais un faux filtre."""
        filtres, caches = rendu(chiffres, onglet="projections")[2:4]
        assert not caches
        assert "jamais une prévision" in texte(filtres)

    def test_sans_aucun_cours_la_date_des_cours_n_est_pas_inventee(self, chiffres):
        """Hors ligne, aucun cours n'est connu : dire « arrêtés au » aujourd'hui serait faux."""
        etat = texte(rendu(chiffres, onglet="synthese")[4])
        assert "Cours arrêtés au" not in etat
        assert "aucun cours connu" in etat

    def test_les_filtres_de_la_synthese_sont_la_periode_et_les_poches(self, chiffres):
        filtres, caches = rendu(chiffres, onglet="synthese")[2:4]
        assert not caches
        assert "Période" in texte(filtres) and "Poches" in texte(filtres)
        assert "Type d'actif" not in texte(filtres)

    @pytest.mark.parametrize("onglet", ["diversification", "frais"])
    def test_diversification_et_frais_n_ont_aucun_filtre(self, chiffres, onglet):
        """Une répartition est la photo d'un tout : rien n'y est filtré. Leur bande ne porte que
        leur sommaire — la rubrique, les sections —, jamais la période, le type ou les poches."""
        bande = texte(rendu(chiffres, onglet=onglet)[2])
        for filtre in ("Période", "Type d'actif", "Poches"):
            assert filtre not in bande
        assert ("Rubrique" if onglet == "diversification" else "Aller à") in bande

    def test_aller_a_une_section_des_frais(self, chiffres):
        """De simples ancres : le navigateur défile, rien n'est recalculé."""
        from tests.vues.outils import noeuds

        corps, bande = rendu(chiffres, onglet="frais")[4], rendu(chiffres, onglet="frais")[2]
        cibles = {"frais-preleve", "frais-detention", "frais-sortie"}
        assert cibles <= set(identifiants(corps))
        liens = {getattr(n, "href", None) for n in noeuds(bande)}
        assert {f"#{c}" for c in cibles} <= liens

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


class TestLaCouverture:
    """Le livre s'ouvre sur sa couverture, à chaque session (D-98, charte graphique §4.1)."""

    @pytest.fixture
    def chiffres(self, dossier_de_depot):
        fictifs.deposer(dossier_de_depot)
        return Chiffres(hors_ligne=True)

    def test_la_session_commence_sur_la_couverture(self):
        assert etat_ecran.initial()["onglet"] == bandeau.ACCUEIL

    def test_la_couverture_ferme_le_livre_les_pages_l_ouvrent(self, chiffres):
        assert rendu(chiffres)[5] == ecrans.CLASSE_DE_LA_COUVERTURE
        assert rendu(chiffres, onglet="synthese")[5] == ecrans.CLASSE_DES_PAGES
        assert rendu(Chiffres())[5] == ecrans.CLASSE_DE_LA_COUVERTURE

    def test_avec_des_donnees_on_ouvre_le_livre_ou_on_depose_plus_recent(self, chiffres):
        corps = rendu(chiffres)[4]
        lu = texte(corps)
        assert "Ouvrir le livre" in lu
        assert "Déposer un export plus récent" in lu
        assert "depot" in identifiants(corps)
        assert {"choix": "aller", "valeur": "synthese"} in identifiants(corps)

    def test_la_periode_et_la_derniere_operation_sont_dites(self, chiffres):
        lu = texte(rendu(chiffres)[4])
        assert "Période couverte" in lu
        assert "du 02/01/2026 au 01/08/2026" in lu
        assert "Dernière opération lue le 01/08/2026" in lu

    def test_un_type_inconnu_est_signale_des_la_couverture(self, chiffres):
        lu = texte(rendu(chiffres)[4])
        assert lu.index("Type inconnu") < lu.index("Ouvrir le livre")

    def test_le_nom_ramene_a_la_couverture(self):
        """Retour du propriétaire (étape 9 bis) : le lien « vos exports » était trop discret."""
        marque = bandeau.marque()
        assert marque.id == {"choix": "aller", "valeur": bandeau.ACCUEIL}
        etat = etat_ecran.appliquer(
            {**etat_ecran.initial(), "onglet": "frais"}, "aller", bandeau.ACCUEIL, []
        )
        assert etat["onglet"] == bandeau.ACCUEIL

    def test_le_detail_est_replie_mais_les_alertes_jamais(self, chiffres):
        """La couverture tient sur un écran : le détail de la lecture est dans un volet. Une
        alerte — ici un type inconnu — reste hors du volet (règle 5)."""
        from tests.vues.outils import noeuds

        corps = rendu(chiffres)[4]
        (volet,) = [n for n in noeuds(corps) if getattr(n, "className", "") == "volet"]
        assert "Votre export" in texte(volet)
        assert fictifs.TYPE_INCONNU in texte(volet)
        dans_le_volet = {id(n) for n in noeuds(volet)}
        alertes = [
            n for n in noeuds(corps) if getattr(n, "className", "") == "cartouche__alerte"
        ]
        assert alertes
        assert not any(id(a) in dans_le_volet for a in alertes)
        assert "Type inconnu" in texte(alertes[0])

    def test_rien_n_est_pose_sous_la_couverture(self, chiffres):
        """L'écran est la couverture, et elle seule : plus de page de garde à faire défiler."""
        assert rendu(chiffres)[4].children.className == "couverture"

    def test_un_identifiant_n_apparait_qu_une_fois(self, chiffres):
        """Dash refuse deux éléments du même nom : « Ouvrir le livre » et l'ancien bouton
        « Voir la synthèse » portaient le même."""
        for corps in (rendu(chiffres)[4], rendu(Chiffres())[4]):
            ids = [str(i) for i in identifiants(corps)]
            assert len(ids) == len(set(ids))


class TestLesChapitres:
    """Chaque chapitre s'ouvre sur son numéro, son titre et sa phrase (charte graphique §4.2)."""

    @pytest.fixture
    def chiffres(self, dossier_de_depot):
        fictifs.deposer(dossier_de_depot)
        return Chiffres(hors_ligne=True)

    @pytest.mark.parametrize(
        ("onglet", "numero", "titre"),
        [
            ("synthese", "I", "Synthèse"),
            ("actifs", "II", "Les actifs"),
            ("diversification", "III", "Diversification"),
            ("frais", "IV", "Frais et taxes"),
            ("projections", "V", "Projections"),
            ("detail", "Annexe", "Détail des calculs"),
        ],
    )
    def test_l_ouverture_du_chapitre(self, chiffres, onglet, numero, titre):
        corps = rendu(chiffres, onglet=onglet)[4]
        assert texte(corps).startswith(f"{numero} {titre} ")
        # Le nom du chapitre : dessin.js ne joue la transition que s'il change.
        assert getattr(corps, "data-chapitre") == onglet

    def test_un_filtre_ne_change_pas_le_nom_du_chapitre(self, chiffres):
        corps = rendu(chiffres, onglet="synthese", periode="1m")[4]
        assert getattr(corps, "data-chapitre") == "synthese"


    def test_les_chapitres_portent_leur_numero_dans_la_navigation(self, chiffres):
        onglets = texte(rendu(chiffres, onglet="synthese")[0])
        assert onglets == "I Synthèse II Les actifs III Diversification IV Frais et taxes " \
            "V Projections"


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
        # La phrase de tête dit, sans jargon, ce qui ne va pas et où trouver le bon fichier.
        assert reception.message.startswith(
            "« courses.csv » ne ressemble pas à un export des transactions de Trade Republic"
        )
        assert "rien n'a été copié" in reception.message
        assert "Profil → Relevés → Export des transactions" in reception.message
        assert list(dossier_de_depot.iterdir()) == []

    def test_un_fichier_qui_n_est_pas_un_export_n_est_jamais_ecrase(
        self, dossier_de_depot, un_export
    ):
        """Seul un export que le nouveau contient en entier est remplacé (D-109). Tout
        autre fichier du dossier est laissé tel quel."""
        dossier_de_depot.mkdir(parents=True)
        (dossier_de_depot / "export.csv").write_bytes(b"un autre fichier")

        reception = recevoir("export.csv", _contenu(un_export), dossier_de_depot)

        assert reception.fichier == dossier_de_depot / "export 2.csv"
        assert (dossier_de_depot / "export.csv").read_bytes() == b"un autre fichier"

    def test_le_meme_fichier_depose_deux_fois_n_est_pas_double(self, dossier_de_depot, un_export):
        recevoir("export.csv", _contenu(un_export), dossier_de_depot)
        reception = recevoir("export.csv", _contenu(un_export), dossier_de_depot)

        assert reception.accepte and reception.fichier is None
        assert "déjà là, à l'identique" in reception.message
        assert [p.name for p in dossier_de_depot.glob("*.csv")] == ["export.csv"]

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

    def test_le_lien_mene_au_detail(self):
        etat = self.appliquer(etat_ecran.initial(), "onglet", "detail")
        assert etat["onglet"] == "detail"

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


def test_la_page_porte_son_filet_contre_les_coupures(dossier_personnel):
    """Une connexion locale sur dix environ est coupée sur la machine du propriétaire (mesuré à
    l'étape 9) : sans ce filet, la page restait sur « Loading… »."""
    page = creer(Chiffres(hors_ligne=True)).server.test_client().get("/").get_data(as_text=True)
    assert "pastory-rechargements" in page
    assert "Réessayer" in page


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
