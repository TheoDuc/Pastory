"""L'attente : ce que l'écran montre pendant une longue lecture (D-110).

Le compteur (`pastory/avancement.py`), les mots (`vues/attente.py`), l'adresse que la page
interroge, et le passage par l'assembleur. Une barre qui avancerait sans rapport avec ce qui se
passe serait pire que pas de barre : elle compte des actifs traités, et ces tests le tiennent.
"""

from __future__ import annotations

import re
import threading

import pytest

from pastory.avancement import Etape, Point, Suivi
from pastory.pivot.operation import Poche
from pastory.vues import application, attente
from pastory.vues.application import DOSSIER_DES_ASSETS
from pastory.vues.chiffres import Chiffres, Echec
from pastory.vues.veille import Veille
from tests.vues.outils import classes, noeuds, texte
from tests.vues.portefeuille import composer, coter


class TestLeCompteur:
    def test_au_repos_rien_n_est_en_cours(self):
        assert Suivi().lire() == (False, None)

    def test_une_lecture_commence_sans_savoir_combien_d_actifs(self):
        suivi = Suivi()
        suivi.commencer()
        assert suivi.lire() == (True, None)

    def test_une_etape_avance_actif_par_actif(self):
        suivi = Suivi()
        suivi.commencer()
        suivi.etape(Etape.COURS, 3)
        suivi.avancer()
        suivi.avancer()
        assert suivi.lire() == (True, Point(Etape.COURS, 2, 3))

    def test_on_ne_compte_jamais_plus_d_actifs_qu_il_n_y_en_a(self):
        suivi = Suivi()
        suivi.commencer()
        suivi.etape(Etape.REGLAGES, 1)
        suivi.avancer()
        suivi.avancer()
        assert suivi.lire()[1] == Point(Etape.REGLAGES, 1, 1)

    def test_terminer_remet_au_repos(self):
        suivi = Suivi()
        suivi.commencer()
        suivi.etape(Etape.COURS, 3)
        suivi.terminer()
        assert suivi.lire() == (False, None)

    def test_avancer_sans_etape_ne_casse_rien(self):
        suivi = Suivi()
        suivi.avancer()
        assert suivi.lire() == (False, None)


class TestLaPartFaite:
    """Trois étapes de même poids, chacune au rythme de ses actifs : refaisable de tête."""

    @pytest.mark.parametrize(
        ("point", "attendue"),
        [
            (Point(Etape.REGLAGES, 0, 8), 0.0),
            (Point(Etape.REGLAGES, 4, 8), 1 / 6),
            (Point(Etape.COURS, 0, 8), 1 / 3),
            (Point(Etape.COURS, 4, 8), 0.5),
            (Point(Etape.COMPOSITIONS, 7, 7), 1.0),
        ],
    )
    def test_elle_se_calcule_sur_les_actifs_traites(self, point, attendue):
        assert point.part == pytest.approx(attendue)

    def test_une_etape_sans_actif_est_tenue_pour_faite(self):
        assert Point(Etape.REGLAGES, 0, 0).part == pytest.approx(1 / 3)

    def test_elle_ne_recule_jamais_d_une_etape_a_la_suivante(self):
        parts = [
            Point(etape, fait, 4).part for etape in Etape for fait in range(5)
        ]
        assert parts == sorted(parts)


class TestLesMots:
    def test_au_repos_la_reponse_ne_dit_rien_de_plus(self):
        assert attente.etat(Suivi()) == {"en_cours": False}

    def test_en_commencant_la_barre_est_vide(self):
        suivi = Suivi()
        suivi.commencer()
        assert attente.etat(suivi) == {
            "en_cours": True, "etape": "Lecture de votre export…", "detail": "", "part": 0,
        }

    def test_une_etape_dit_son_rang_et_ses_actifs(self):
        suivi = Suivi()
        suivi.commencer()
        suivi.etape(Etape.COURS, 8)
        for _ in range(4):
            suivi.avancer()
        etat = attente.etat(suivi)
        assert etat["etape"] == "Récupération des cours de chaque actif…"
        assert etat["detail"] == "Étape 2 sur 3 · 4 actifs sur 8"
        assert etat["part"] == 50.0

    def test_le_singulier(self):
        suivi = Suivi()
        suivi.commencer()
        suivi.etape(Etape.REGLAGES, 5)
        suivi.avancer()
        assert attente.etat(suivi)["detail"] == "Étape 1 sur 3 · 1 actif sur 5"

    def test_chaque_etape_a_son_libelle(self):
        assert set(attente.LIBELLES) == set(Etape)


class TestLeBlocDAttente:
    def test_la_barre_et_la_note_sont_cachees_au_depart(self):
        """Un changement de période ne doit pas annoncer une minute d'attente : le script ne
        les montre que si une lecture est réellement en cours."""
        bloc = attente.brique()
        caches = {n.className for n in noeuds(bloc) if getattr(n, "hidden", False)}
        assert caches == {"attente__piste", "attente__note"}
        assert texte(bloc).startswith(attente.AU_REPOS)

    def test_il_dit_au_script_ou_demander(self):
        bloc = attente.brique()
        assert getattr(bloc, "data-adresse") == attente.CHEMIN
        assert getattr(bloc, "data-repos") == attente.AU_REPOS

    def test_chacune_de_ses_classes_a_sa_regle(self):
        feuille = (DOSSIER_DES_ASSETS / "pastory.css").read_text(encoding="utf-8")
        definies = set(re.findall(r"\.([a-zA-Z][\w-]*)", feuille))
        assert classes(attente.brique()) <= definies

    def test_le_script_ne_pose_que_des_textes_deja_ecrits(self):
        """Aucun chiffre n'est mis en forme dans le navigateur (D-93) : les deux textes
        affichés sont posés tels que Python les a écrits, et rien d'autre n'est écrit."""
        script = (DOSSIER_DES_ASSETS / "dessin.js").read_text(encoding="utf-8")
        attente_js = script.split("L'ATTENTE")[1].split("LES BULLES")[0]
        poses = re.findall(r"(\w+)\.textContent = ([^;]+);", attente_js)
        assert sorted(poses) == [
            ("detail", '""'),
            ("detail", "etat.detail"),
            ("etape", 'attente.getAttribute("data-repos")'),
            ("etape", "etat.etape"),
        ]
        for interdit in ("toFixed", "toLocaleString", "Intl.", "innerHTML"):
            assert interdit not in attente_js

    def test_c_est_lui_que_la_page_montre_en_attendant(self):
        page = application._mise_en_page()
        assert "attente" in classes(page)


class TestLAdresse:
    def test_elle_repond_ou_en_est_la_lecture(self, dossier_personnel):
        chiffres = Chiffres(hors_ligne=True)
        client = application.creer(chiffres).server.test_client()

        assert client.get(attente.CHEMIN).get_json() == {"en_cours": False}

        chiffres.suivi.commencer()
        chiffres.suivi.etape(Etape.REGLAGES, 4)
        chiffres.suivi.avancer()
        reponse = client.get(attente.CHEMIN)
        assert reponse.get_json()["detail"] == "Étape 1 sur 3 · 1 actif sur 4"
        assert reponse.headers["Cache-Control"] == "no-store"

    def test_elle_repond_pendant_que_le_calcul_tient_le_verrou(self, dossier_personnel):
        """La page la demande pendant que les chiffres se calculent : si elle attendait le
        verrou des chiffres, la barre ne bougerait qu'une fois tout fini."""
        chiffres = Chiffres(hors_ligne=True)
        client = application.creer(chiffres).server.test_client()
        reponses: list = []

        def demander():
            reponses.append(client.get(attente.CHEMIN).get_json())

        with chiffres._verrou:
            fil = threading.Thread(target=demander)
            fil.start()
            fil.join(timeout=5)
            assert reponses == [{"en_cours": False}]

    def test_une_question_sur_l_avancement_n_est_pas_un_travail(self, dossier_personnel):
        """Elle ne doit pas tenir Pastory ouvert après la fermeture de sa fenêtre (D-106)."""

        class VeilleQuiCompte(Veille):
            commences = 0
            finis = 0

            def commencer_un_travail(self) -> None:
                self.commences += 1
                super().commencer_un_travail()

            def finir_un_travail(self) -> None:
                self.finis += 1
                super().finir_un_travail()

        veille = VeilleQuiCompte()
        client = application.creer(Chiffres(hors_ligne=True), veille).server.test_client()
        client.get(attente.CHEMIN)
        assert (veille.commences, veille.finis) == (0, 0)
        # Une vraie demande, elle, compte — et se termine.
        client.get("/_dash-layout")
        assert (veille.commences, veille.finis) == (1, 1)


class TestLaLectureDitOuElleEnEst:
    """De bout en bout : l'assembleur fait avancer le compteur des chiffres."""

    def test_les_trois_etapes_dans_l_ordre_chacune_jusqu_au_bout(self, dossier_personnel):
        chiffres = coter(dossier_personnel)
        composer()
        vus: list[Point] = []
        suivi = chiffres.suivi
        etape, avancer = suivi.etape, suivi.avancer

        def noter_l_etape(quelle, total):
            etape(quelle, total)
            vus.append(suivi.lire()[1])

        def noter_l_avancee():
            avancer()
            vus.append(suivi.lire()[1])

        suivi.etape, suivi.avancer = noter_l_etape, noter_l_avancee

        base = chiffres.base()

        assert not isinstance(base, Echec)
        assert [p.etape for p in vus if p.fait == 0] == list(Etape)
        for quelle in Etape:
            dernier = [p for p in vus if p.etape is quelle][-1]
            assert dernier.fait == dernier.total, quelle
        actifs = {position.actif for position in base.portefeuille.positions}
        assert next(p for p in vus if p.etape is Etape.REGLAGES).total == len(actifs)
        assert next(p for p in vus if p.etape is Etape.COURS).total == len(actifs)
        # Seuls les actifs valorisés ont une composition à chercher, et jamais une crypto (D-68).
        a_composer = [
            p for p in base.synthese.valorisation.valorisees if p.poche is not Poche.CRYPTO
        ]
        assert 0 < len(a_composer) < len(actifs)
        assert next(p for p in vus if p.etape is Etape.COMPOSITIONS).total == len(a_composer)
        assert [p.part for p in vus] == sorted(p.part for p in vus)

    def test_une_fois_lue_la_base_remet_le_compteur_au_repos(self, dossier_personnel):
        chiffres = coter(dossier_personnel)
        chiffres.base()
        assert chiffres.suivi.lire() == (False, None)

    def test_un_echec_aussi(self, dossier_personnel):
        chiffres = Chiffres(hors_ligne=True)
        assert isinstance(chiffres.base(), Echec)
        assert chiffres.suivi.lire() == (False, None)
