"""Le classement par liste explicite : rien par défaut (règle 5 de CLAUDE.md)."""

from __future__ import annotations

import pytest

from pastory.adaptateurs.trade_republic_officiel import classement as module
from pastory.adaptateurs.trade_republic_officiel.classement import Categorie, classer
from pastory.adaptateurs.trade_republic_officiel.fichier import Ligne
from pastory.pivot.operation import TypeOperation
from tests.adaptateurs.trade_republic_officiel import export_fictif as fictif


def en_ligne(valeurs: dict[str, str]) -> Ligne:
    colonnes = {champ: valeurs.get(champ, "") for champ in Ligne.__dataclass_fields__}
    colonnes.update(fichier="export.csv", numero=2)
    return Ligne(**colonnes)


@pytest.mark.parametrize(
    ("fabrique", "attendu"),
    [
        (fictif.achat_plan_epargne, TypeOperation.ACHAT),
        (fictif.vente, TypeOperation.VENTE),
        (fictif.dividende, TypeOperation.DIVIDENDE),
        (fictif.distribution_capital, TypeOperation.DISTRIBUTION_CAPITAL),
    ],
)
def test_les_types_vus_et_compares_sont_traites(fabrique, attendu):
    resultat = classer(en_ligne(fabrique()))
    assert (resultat.categorie, resultat.type_operation) == (Categorie.TRAITE, attendu)


@pytest.mark.parametrize("cle", sorted(module.TYPES_HORS_PERIMETRE))
def test_chaque_type_d_especes_sans_actif_est_hors_perimetre(cle):
    category, type_ = cle
    resultat = classer(en_ligne(fictif.ligne(category=category, type=type_)))
    assert resultat.categorie is Categorie.HORS_PERIMETRE


def test_une_ligne_d_especes_qui_designe_un_actif_est_affichee():
    # Le cas d'une action offerte, rangée par la banque dans les espèces (§4.2).
    resultat = classer(en_ligne(fictif.paiement_carte(symbol=fictif.ACTION)))
    assert resultat.categorie is Categorie.INCONNU
    assert resultat.motif == module.MOTIF_ESPECES_AVEC_ACTIF


@pytest.mark.parametrize(
    "fabrique",
    [
        fictif.saveback,
        fictif.actions_gratuites,
        lambda: fictif.ligne(category="DELIVERY", type="MIGRATION", symbol=fictif.ACTION),
    ],
)
def test_les_types_vus_mais_pas_compris_sont_affiches_avec_ce_qu_on_en_sait(fabrique):
    resultat = classer(en_ligne(fabrique()))
    assert resultat.categorie is Categorie.INCONNU
    assert resultat.motif in module.TYPES_EN_ATTENTE.values()


@pytest.mark.parametrize(
    ("category", "type_"),
    [
        # Connus d'autres logiciels, jamais vus chez nous (export-officiel.md §4.2).
        ("TRADING", "BUY_CANCELLED"),
        ("CORPORATE_ACTION", "SPLIT"),
        ("DELIVERY", "FREE_RECEIPT"),
        ("CASH", "STOCKPERK"),
        # Un code connu dans une autre catégorie n'est pas le même type.
        ("CASH", "BUY"),
        ("TRADING", "DIVIDEND"),
    ],
)
def test_un_type_jamais_vu_n_est_jamais_range_par_defaut(category, type_):
    resultat = classer(en_ligne(fictif.ligne(category=category, type=type_)))
    assert resultat.categorie is Categorie.INCONNU
    assert resultat.type_affiche == f"{category}/{type_}"
    assert resultat.motif == module.MOTIF_INCONNU


@pytest.mark.parametrize(
    ("texte", "affiche"),
    [
        ("DIVIDEND", "DIVIDEND"),
        ("TYPE_2", "TYPE_2"),
        ("Jean Dupont", "(illisible)"),
        ("12.50", "(illisible)"),
        ("", "(vide)"),
        ("A" * 41, "(illisible)"),
    ],
)
def test_seul_un_code_est_affiche_tel_quel(texte, affiche):
    resultat = classer(en_ligne(fictif.ligne(category="CASH", type=texte)))
    assert resultat.type_affiche == f"CASH/{affiche}"
