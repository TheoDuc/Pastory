"""Lecture d'un fichier d'export : ses deux variantes, et ce qu'on ne garde jamais."""

from __future__ import annotations

import dataclasses

import pytest

from pastory.adaptateurs.trade_republic import fichier
from pastory.adaptateurs.trade_republic.fichier import FichierNonReconnu
from tests.adaptateurs.trade_republic import export_fictif as fictif


def test_les_deux_variantes_donnent_les_memes_lignes(tmp_path):
    lignes = [fictif.achat_plan_epargne(), fictif.dividende_en_dollars()]
    virgule = fictif.deposer(tmp_path / "a", lignes)
    point_virgule = fictif.deposer(
        tmp_path / "b", lignes, separateur=";", colonnes=fictif.COLONNES_POINT_VIRGULE
    )

    assert [ligne.contenu() for ligne in fichier.lire(virgule)] == [
        ligne.contenu() for ligne in fichier.lire(point_virgule)
    ]


def test_les_colonnes_sont_lues_par_leur_nom_et_non_par_leur_position(tmp_path):
    colonnes = tuple(reversed(fictif.COLONNES))
    chemin = fictif.deposer(tmp_path, [fictif.achat_plan_epargne()], colonnes=colonnes)

    (ligne,) = fichier.lire(chemin)
    assert (ligne.symbol, ligne.amount) == (fictif.ETF, "-50.00")


def test_une_marque_d_encodage_ajoutee_par_un_tableur_est_toleree(tmp_path):
    chemin = tmp_path / "export.csv"
    chemin.write_text(fictif.texte_csv([fictif.achat_plan_epargne()]), encoding="utf-8-sig")

    (ligne,) = fichier.lire(chemin)
    assert ligne.datetime.startswith("2026-")


def test_un_caractere_de_saut_dans_un_champ_ne_coupe_pas_la_ligne(tmp_path):
    # Un séparateur de ligne Unicode, un saut de page, un retour à la ligne entre guillemets :
    # aucun ne doit couper l'enregistrement en deux moitiés décalées.
    ligne_piege = fictif.achat_plan_epargne(
        name="ETF Monde\x0cFictif", description="Savings plan\nexecution"
    )
    chemin = fictif.deposer(tmp_path, [ligne_piege, fictif.vente()])

    premiere, seconde = fichier.lire(chemin)
    assert (premiere.amount, premiere.name) == ("-50.00", "ETF Monde\x0cFictif")
    assert seconde.type == "SELL"


def test_le_numero_de_ligne_est_celui_d_un_tableur(tmp_path):
    chemin = fictif.deposer(tmp_path, [fictif.achat_plan_epargne(), fictif.vente()])
    assert [ligne.numero for ligne in fichier.lire(chemin)] == [2, 3]


@pytest.mark.parametrize(
    ("contenu", "attendu"),
    [
        ("", "vide"),
        ("Date;Type;Montant\n2026-01-01;Achat;10\n", "colonne"),
    ],
)
def test_un_fichier_qui_n_est_pas_un_export_est_refuse(tmp_path, contenu, attendu):
    chemin = tmp_path / "autre.csv"
    chemin.write_text(contenu, encoding="utf-8")
    with pytest.raises(FichierNonReconnu, match=attendu):
        fichier.lire(chemin)


def test_un_fichier_qui_n_est_pas_en_utf8_est_refuse(tmp_path):
    chemin = tmp_path / "export.csv"
    chemin.write_bytes(fictif.texte_csv([fictif.paiement_carte()]).encode("utf-16"))
    with pytest.raises(FichierNonReconnu, match="UTF-8"):
        fichier.lire(chemin)


class TestDonneesPersonnelles:
    """Une ligne d'espèces ne garde que son type, ses dates et son identifiant (§8)."""

    def lire(self, tmp_path):
        chemin = fictif.deposer(tmp_path, [fictif.paiement_carte(), fictif.virement_recu()])
        return fichier.lire(chemin)

    def test_aucune_valeur_personnelle_ne_survit_a_la_lecture(self, tmp_path):
        for ligne in self.lire(tmp_path):
            texte = repr(dataclasses.astuple(ligne))
            for personnel in (
                fictif.COMMERCANT,
                fictif.CONTREPARTIE,
                fictif.IBAN,
                fictif.MONTANT_PERSONNEL,
                "1500.00",
                "5462",
            ):
                assert personnel not in texte

    def test_les_colonnes_de_contrepartie_ne_sont_meme_pas_des_attributs(self):
        attributs = {champ.name for champ in dataclasses.fields(fichier.Ligne)}
        assert not attributs & {
            "counterparty_name",
            "counterparty_iban",
            "payment_reference",
            "mcc_code",
            "value_date",
        }

    def test_le_type_et_l_identifiant_restent(self, tmp_path):
        carte, virement = self.lire(tmp_path)
        assert (carte.category, carte.type) == ("CASH", "CARD_TRANSACTION")
        assert virement.transaction_id

    def test_une_ligne_d_actif_garde_son_nom_et_son_montant(self, tmp_path):
        (ligne,) = fichier.lire(fictif.deposer(tmp_path, [fictif.dividende()]))
        assert (ligne.name, ligne.amount) == ("Action Fictive", "10.000000")
