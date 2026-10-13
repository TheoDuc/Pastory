"""Le rapport de lecture : ce qu'il dit, et ce qu'il ne dit jamais."""

from __future__ import annotations

from pastory.adaptateurs.trade_republic.depot import lire as lire_dossier
from pastory.adaptateurs.trade_republic.depot import ouvrir
from pastory.adaptateurs.trade_republic.lecture import Lecteur
from pastory.adaptateurs.trade_republic.rapport import LIMITE_DES_DIVIDENDES
from tests.adaptateurs.trade_republic import export_fictif as fictif


def resume(tmp_path, lignes=None, **options):
    fictif.deposer(tmp_path, lignes, **options)
    return Lecteur().lire(lire_dossier(tmp_path)).resume()


def test_il_dit_la_periode_couverte_et_comment_la_completer(tmp_path):
    texte = resume(tmp_path)
    assert "Période couverte : du 2026-03-01 au 2026-05-15" in texte
    assert "toutes les transactions" in texte


def test_il_nomme_le_portefeuille_lu_et_ceux_qui_ne_le_sont_pas(tmp_path):
    """Un fichier, un portefeuille (D-109) : le rapport ne laisse pas croire que ses chiffres
    comprennent les autres fichiers du dossier."""
    fictif.deposer(tmp_path, [fictif.achat_plan_epargne()], nom="Alix.csv")
    fictif.deposer(tmp_path, [fictif.vente()], nom="Camille.csv")
    ouvrir(tmp_path, "Camille")

    texte = Lecteur().lire(lire_dossier(tmp_path)).resume()

    assert "Portefeuille lu : Camille" in texte
    assert "1 autre(s) portefeuille(s)" in texte and "Alix" in texte
    # Avec --export, la couverture ne propose aucun choix : le message dit aussi l'autre voie.
    assert "--export" in texte
    assert "du 2026-04-10 au 2026-04-10" in texte


def test_avec_un_seul_portefeuille_il_ne_parle_pas_des_autres(tmp_path):
    assert "autre(s) portefeuille(s)" not in resume(tmp_path)


def test_il_liste_les_types_non_traites_avec_leur_raison(tmp_path):
    texte = resume(tmp_path)
    assert "ATTENTION - types non traités" in texte
    assert "CASH/BENEFITS_SAVEBACK" in texte
    assert "Saveback" in texte


def test_les_especes_ne_sont_que_comptees(tmp_path):
    texte = resume(tmp_path)
    assert "CASH/CARD_TRANSACTION" in texte
    for personnel in (
        fictif.COMMERCANT,
        fictif.CONTREPARTIE,
        fictif.IBAN,
        fictif.MONTANT_PERSONNEL,
        "1500.00",
    ):
        assert personnel not in texte


def test_la_limite_des_dividendes_est_dite_des_qu_il_y_a_un_dividende(tmp_path):
    assert "Pays-Bas" in LIMITE_DES_DIVIDENDES
    assert "Limite connue : le brut des dividendes" in resume(tmp_path / "a")
    sans = resume(tmp_path / "b", [fictif.achat_plan_epargne()])
    assert "Limite connue" not in sans


def test_il_s_ecrit_en_cp1252(tmp_path):
    # La console Windows par défaut écrit en cp1252 : un caractère hors de ce jeu ferait
    # échouer la commande au moment d'afficher, alors que la lecture s'est bien passée.
    fictif.deposer(tmp_path / "x", [fictif.achat_plan_epargne()], nom="a.csv")
    texte = resume(
        tmp_path / "x",
        fictif.export_type() + [fictif.dividende(amount="-1.000000"), fictif.actions_gratuites()],
    )
    texte.encode("cp1252")


def test_aucune_ligne_ne_deborde_d_un_terminal(tmp_path):
    texte = resume(
        tmp_path,
        fictif.export_type()
        + [
            fictif.dividende(amount="-1.000000"),
            fictif.achat_plan_epargne(account_type="JUNIOR"),
            fictif.ligne(category="CORPORATE_ACTION", type="SPLIT", symbol=fictif.ACTION),
        ],
        nom="Exportation de transactions avec un nom de fichier vraiment très long (2).csv",
    )
    for ligne in texte.splitlines():
        assert len(ligne) <= 100, ligne
