"""La veille : Pastory s'arrête quand sa dernière page se ferme, et pas avant (D-106)."""

from __future__ import annotations

from pastory.vues.veille import Veille


def battements_avant_l_arret(veille: Veille, maximum: int = 1000) -> int | None:
    for numero in range(1, maximum + 1):
        if veille.battre():
            return numero
    return None


def une_veille() -> Veille:
    return Veille(silence_maximal=60, delai_de_fermeture=5, attente_de_la_premiere_page=30)


def test_tant_qu_une_page_donne_signe_de_vie_rien_ne_s_arrete():
    veille = une_veille()
    for _ in range(500):
        veille.signe("page")
        assert veille.battre() is False


def test_la_fenetre_fermee_pastory_s_arrete_apres_un_court_delai():
    veille = une_veille()
    veille.signe("page")
    veille.adieu("page")
    assert battements_avant_l_arret(veille) == 5


def test_recharger_la_page_n_arrete_rien():
    """Recharger, c'est fermer puis rouvrir : l'adieu de l'ancienne page précède de peu le
    premier signe de la nouvelle."""
    veille = une_veille()
    veille.signe("ancienne")
    veille.adieu("ancienne")
    for _ in range(4):
        assert veille.battre() is False
    veille.signe("nouvelle")
    assert veille.battre() is False
    assert battements_avant_l_arret(veille, maximum=50) is None


def test_une_seconde_fenetre_garde_pastory_ouvert_meme_silencieuse():
    """Une fenêtre réduite ne donne plus qu'un signe par minute : la fermeture de l'autre ne
    doit pas arrêter Pastory sous elle."""
    veille = une_veille()
    veille.signe("reduite")
    veille.signe("fermee")
    veille.adieu("fermee")
    for _ in range(59):
        assert veille.battre() is False


def test_une_page_qui_se_tait_trop_longtemps_est_tenue_pour_fermee():
    """Une fenêtre fermée dont l'adieu s'est perdu en route : Pastory ne reste pas en mémoire."""
    veille = une_veille()
    veille.signe("page")
    assert battements_avant_l_arret(veille) == 60 + 5 - 1


def test_un_signe_perdu_ne_suffit_pas():
    veille = une_veille()
    for _ in range(10):
        veille.signe("page")
        for _ in range(59):
            assert veille.battre() is False


def test_si_aucune_page_ne_vient_jamais_pastory_ne_reste_pas_en_memoire():
    assert battements_avant_l_arret(une_veille()) == 30


def test_pastory_ne_s_arrete_pas_au_milieu_d_un_travail():
    """Fermer la fenêtre pendant qu'un cache s'écrit le laisserait à moitié écrit."""
    veille = une_veille()
    veille.signe("page")
    veille.commencer_un_travail()
    veille.adieu("page")
    for _ in range(100):
        assert veille.battre() is False
    veille.finir_un_travail()
    assert veille.battre() is True


def test_l_adieu_d_une_page_inconnue_est_sans_effet():
    veille = une_veille()
    veille.signe("page")
    veille.adieu("une autre")
    assert veille.battre() is False


def test_le_nombre_de_pages_suivies_est_borne():
    veille = une_veille()
    for numero in range(1000):
        veille.signe(f"page-{numero}")
    assert len(veille._silences) == 50
