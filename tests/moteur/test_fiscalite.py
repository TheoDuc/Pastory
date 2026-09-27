"""L'impôt estimé, poche par poche.

Chaque test porte le numéro du cas correspondant dans `docs/verification/etape-6.md`. Les taux
sont ceux de 2026 : impôt sur le revenu 12,8 %, prélèvements sociaux 18,6 %, donc 31,4 %.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from dashboard_tr.moteur import fiscalite
from dashboard_tr.moteur.fiscalite import Cession, anniversaire
from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.pivot.operation import Poche, TypeOperation
from tests.moteur.operations_fictives import ACTIF, operation
from tests.moteur.parametres_fictifs import regles

AUTRE = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"

SANS_FRAIS = Decimal("0.00")


def position_de(operations):
    positions, _ = Portefeuille.construire(operations).positions, None
    assert len(positions) == 1
    return positions[0]


def cession(
    poche=Poche.CTO,
    actif=ACTIF,
    quantite="10",
    prix="99.90",
    frais_achat="1.00",
    valeur="1500.00",
    spread="0.00",
    frais_de_vente="1.00",
):
    """Une position achetée puis valorisée, prête à être « vendue aujourd'hui »."""
    achat = operation(
        TypeOperation.ACHAT,
        actif=actif,
        poche=poche,
        quantite=quantite,
        prix_unitaire=prix,
        frais=frais_achat,
    )
    return Cession(
        position=position_de([achat]),
        valeur_brute=Decimal(valeur),
        spread=Decimal(spread),
        frais_de_vente=Decimal(frais_de_vente),
    )


# --- A.4 : le prix de revient fiscal, frais d'achat compris --------------------------


def test_le_capital_fiscal_compte_les_frais_et_les_taxes_d_achat():
    """D-57 : 201 € payés pour 10 parts font 20,10 € de prix de revient fiscal, contre
    20,00 € de prix de revient (D-13). Les deux existent, côte à côte."""
    achat = operation(
        TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00", frais="1.00"
    )
    etat = position_de([achat]).etat

    assert etat.capital_net_investi == Decimal("200.00")
    assert etat.capital_fiscal == Decimal("201.00")
    assert etat.prix_de_revient == Decimal("20.000000")
    assert etat.prix_de_revient_fiscal == Decimal("20.100000")


def test_une_vente_retire_le_capital_fiscal_au_prorata_des_parts():
    """Le prix de revient fiscal est un prix moyen pondéré : une vente ne le change pas."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-03-05 09:00",
            quantite="5",
            prix_unitaire="40.00",
            frais="1.00",
        ),
    ]
    etat = position_de(operations).etat

    # La moitié des parts part, donc la moitié du capital fiscal : 201,00 / 2 = 100,50.
    assert etat.capital_fiscal == Decimal("100.50")
    assert etat.prix_de_revient_fiscal == Decimal("20.100000")
    # Les frais de la vente ne sont pas venus gonfler le prix d'acquisition.
    assert etat.capital_net_investi == Decimal("100.00")


def test_une_vente_totale_ramene_le_capital_fiscal_a_zero():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-03-05 09:00",
            quantite="10",
            prix_unitaire="40.00",
        ),
    ]
    assert position_de(operations).etat.capital_fiscal == Decimal("0.00")


def test_une_histoire_incomplete_n_affiche_aucun_prix_de_revient_fiscal():
    """D-45 : le prix de revient fiscal se tait exactement quand l'autre se tait."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.TITRES_RECUS,
            horodatage="2026-03-01 09:00",
            quantite="3",
            prix_a_completer=True,
        ),
    ]
    etat = position_de(operations).etat

    assert etat.prix_de_revient is None
    assert etat.prix_de_revient_fiscal is None


def test_une_distribution_de_capital_baisse_aussi_le_prix_d_acquisition_fiscal():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.DISTRIBUTION_CAPITAL,
            horodatage="2026-03-05 09:00",
            quantite="10",
            prix_unitaire="5.00",
        ),
    ]
    etat = position_de(operations).etat

    assert etat.capital_net_investi == Decimal("150.00")
    assert etat.capital_fiscal == Decimal("151.00")


# --- A.5 : l'impôt du compte-titres ordinaire ---------------------------------------


def test_l_impot_du_cto_compense_les_gains_et_les_pertes():
    """Une ligne gagne 499 €, l'autre perd 201 € : la base est 298 €, l'impôt 93,57 €."""
    # 10 parts à 99,90 € plus 1 € de frais : capital fiscal 1 000,00 €.
    gagnante = cession(valeur="1500.00")  # 1 499 − 1 000 = +499
    perdante = cession(
        actif=AUTRE, quantite="20", prix="49.95", frais_achat="1.00", valeur="800.00"
    )  # capital fiscal 1 000,00 ; 799 − 1 000 = −201

    impot = fiscalite.impot_cto([gagnante, perdante], regles())

    assert perdante.capital_fiscal == Decimal("1000.00")
    assert impot.base_avant_plancher == Decimal("298.00")
    assert impot.base == Decimal("298.00")
    assert impot.taux == Decimal("31.4")
    assert impot.impot == Decimal("93.57")


def test_une_perte_globale_ne_donne_aucun_impot():
    """Le plancher à zéro : on ne rend pas d'argent à la sortie."""
    impot = fiscalite.impot_cto([cession(valeur="500.00")], regles())

    assert impot.base_avant_plancher == Decimal("-501.00")
    assert impot.base == Decimal("0.00")
    assert impot.impot == Decimal("0.00")


def test_les_frais_de_vente_et_le_spread_reduisent_la_base():
    """Les frais de cession sont déductibles, et le spread est ce que le marché prend."""
    sans = cession(valeur="1500.00", spread="0.00", frais_de_vente="0.00")
    avec = cession(valeur="1500.00", spread="0.75", frais_de_vente="1.00")

    base_sans = fiscalite.impot_cto([sans], regles()).base
    base_avec = fiscalite.impot_cto([avec], regles()).base

    assert base_sans - base_avec == Decimal("1.75")


def test_l_impot_du_cto_cite_ses_deux_taux_et_leurs_sources():
    impot = fiscalite.impot_cto([cession()], regles())

    assert [parametre.valeur for parametre in impot.parametres] == [
        Decimal("12.8"),
        Decimal("18.6"),
    ]
    assert "12,8 %" in impot.regle and "18,6 %" in impot.regle


def test_une_position_a_l_histoire_trouee_rend_l_impot_non_fiable():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-03-05 09:00",
            quantite="15",
            prix_unitaire="25.00",
        ),
    ]
    trouee = Cession(
        position=position_de(operations),
        valeur_brute=Decimal("100.00"),
        spread=SANS_FRAIS,
        frais_de_vente=SANS_FRAIS,
    )

    assert not fiscalite.impot_cto([trouee], regles()).fiable


# --- A.6 : l'impôt du PEA -----------------------------------------------------------


def portefeuille_pea(frais="10.00", dividende="200.00"):
    """Un PEA : 9 000 € d'achats, 10 € de frais, 200 € de dividendes, valeur 12 000 €."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            poche=Poche.PEA,
            quantite="90",
            prix_unitaire="100.00",
            frais=frais,
        ),
        operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-04-20 09:00",
            poche=Poche.PEA,
            quantite="90",
            prix_unitaire=str(Decimal(dividende) / 90),
            montant_brut=dividende,
        ),
    ]
    return Portefeuille.construire(operations)


def cession_pea(valeur="12000.00"):
    return Cession(
        position=portefeuille_pea().positions[0],
        valeur_brute=Decimal(valeur),
        spread=SANS_FRAIS,
        frais_de_vente=SANS_FRAIS,
    )


def test_un_pea_de_plus_de_cinq_ans_ne_paie_que_les_prelevements_sociaux():
    """Gain du plan 3 190 € : 3 000 de latente + 200 de dividendes − 10 de frais.
    À 18,6 %, l'impôt est de 593,34 €."""
    impot = fiscalite.impot_pea(
        [cession_pea()],
        portefeuille_pea().positions,
        date(2026, 9, 27),
        regles(premier_versement_pea=date(2021, 3, 1)),
    )

    assert impot.base == Decimal("3190.00")
    assert impot.taux == Decimal("18.6")
    assert impot.impot == Decimal("593.34")
    assert "exonéré d'impôt sur le revenu" in impot.regle


def test_un_pea_de_moins_de_cinq_ans_paie_tout_et_se_ferme():
    """Le même gain, 31,4 % : 1 001,66 €. Et le rapport dit que retirer clôt le plan."""
    impot = fiscalite.impot_pea(
        [cession_pea()],
        portefeuille_pea().positions,
        date(2026, 9, 27),
        regles(premier_versement_pea=date(2023, 6, 1)),
    )

    assert impot.base == Decimal("3190.00")
    assert impot.taux == Decimal("31.4")
    assert impot.impot == Decimal("1001.66")
    assert "clôt le plan" in impot.regle


def test_le_gain_du_plan_se_decompose_ligne_par_ligne():
    """C'est la décomposition que le propriétaire refait à la main (cahier §5.3)."""
    impot = fiscalite.impot_pea(
        [cession_pea()],
        portefeuille_pea().positions,
        date(2026, 9, 27),
        regles(premier_versement_pea=date(2021, 3, 1)),
    )

    composantes = dict(impot.composantes)
    assert composantes["plus-values latentes, après frais de vente et spread"] == Decimal(
        "3000.00"
    )
    assert composantes["dividendes reçus (brut)"] == Decimal("200.00")
    assert composantes["frais et taxes payés dans le PEA, en moins"] == Decimal("-10.00")
    assert sum(composantes.values()) == impot.base


def test_les_plus_values_realisees_d_une_ligne_soldee_comptent_dans_le_gain_du_plan():
    """Le gain est celui du **plan** : une position entièrement vendue en fait partie."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            poche=Poche.PEA,
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-03-05 09:00",
            poche=Poche.PEA,
            quantite="10",
            prix_unitaire="30.00",
        ),
    ]
    soldee = Portefeuille.construire(operations)

    impot = fiscalite.impot_pea(
        [], soldee.positions, date(2026, 9, 27), regles(premier_versement_pea=date(2021, 3, 1))
    )

    assert impot.base == Decimal("100.00")
    assert impot.impot == Decimal("18.60")


def test_sans_date_de_premier_versement_l_impot_du_pea_n_est_pas_calcule():
    """D-59 : l'ancienneté décide du taux, et elle ne se devine pas (D-40)."""
    impot = fiscalite.impot_pea(
        [cession_pea()], portefeuille_pea().positions, date(2026, 9, 27), regles()
    )

    assert impot.impot is None
    assert not impot.calculable
    assert "fiscalite.toml" in impot.motif


def test_un_gain_de_plan_negatif_ne_donne_aucun_impot():
    impot = fiscalite.impot_pea(
        [cession_pea(valeur="5000.00")],
        portefeuille_pea().positions,
        date(2026, 9, 27),
        regles(premier_versement_pea=date(2021, 3, 1)),
    )

    assert impot.base_avant_plancher < 0
    assert impot.base == Decimal("0.00")
    assert impot.impot == Decimal("0.00")


def test_le_pea_annonce_ses_trois_hypotheses():
    impot = fiscalite.impot_pea(
        [cession_pea()],
        portefeuille_pea().positions,
        date(2026, 9, 27),
        regles(premier_versement_pea=date(2021, 3, 1)),
    )

    ensemble = " ".join(impot.hypotheses)
    assert "aucun retrait" in ensemble
    assert "intérêt ni frais" in ensemble
    assert "transfert de PEA" in ensemble


@pytest.mark.parametrize(
    "premier_versement, jour, exonere",
    [
        (date(2021, 9, 27), date(2026, 9, 27), True),  # cinq ans jour pour jour
        (date(2021, 9, 28), date(2026, 9, 27), False),  # un jour trop tard
        (date(2020, 2, 29), date(2025, 3, 1), True),  # un 29 février, cinq ans plus tard
    ],
)
def test_les_cinq_ans_se_comptent_au_jour_pres(premier_versement, jour, exonere):
    impot = fiscalite.impot_pea(
        [cession_pea()],
        portefeuille_pea().positions,
        jour,
        regles(premier_versement_pea=premier_versement),
    )

    assert (impot.taux == Decimal("18.6")) is exonere


def test_l_anniversaire_d_un_29_fevrier_tombe_le_premier_mars():
    assert anniversaire(date(2020, 2, 29), 5) == date(2025, 3, 1)
    assert anniversaire(date(2021, 3, 15), 5) == date(2026, 3, 15)


# --- A.7 : l'impôt de la crypto -----------------------------------------------------


def cession_crypto(valeur="1500.00", achat="1000.00", frais_de_vente="1.00"):
    achat_crypto = operation(
        TypeOperation.ACHAT,
        actif=CRYPTO,
        poche=Poche.CRYPTO,
        quantite="1",
        prix_unitaire=achat,
        frais="1.00",
    )
    return Cession(
        position=position_de([achat_crypto]),
        valeur_brute=Decimal(valeur),
        spread=SANS_FRAIS,
        frais_de_vente=Decimal(frais_de_vente),
    )


def test_l_impot_crypto_part_du_capital_investi_sans_les_frais_d_achat():
    """Lecture prudente de la loi : 1 499 − 1 000 = 499 €, impôt 156,69 €."""
    impot = fiscalite.impot_crypto([cession_crypto()], regles())

    assert impot.base == Decimal("499.00")
    assert impot.impot == Decimal("156.69")


def test_sous_le_seuil_de_305_euros_la_crypto_est_exoneree():
    """CGI 150 VH bis : pas de cession imposable sous 305 € de prix de cession dans l'année."""
    impot = fiscalite.impot_crypto(
        [cession_crypto(valeur="300.00", achat="100.00")], regles()
    )

    assert impot.base == Decimal("0.00")
    assert impot.impot == Decimal("0.00")
    assert "exonéré" in impot.regle


def test_juste_au_dessus_du_seuil_tout_devient_imposable():
    impot = fiscalite.impot_crypto(
        [cession_crypto(valeur="306.00", achat="100.00", frais_de_vente="0.00")], regles()
    )

    assert impot.base == Decimal("206.00")
    assert impot.impot == Decimal("64.68")


def test_la_crypto_annonce_ses_trois_approximations():
    impot = fiscalite.impot_crypto([cession_crypto()], regles())

    ensemble = " ".join(impot.hypotheses)
    assert "chez Trade Republic" in ensemble
    assert "prorata des parts" in ensemble
    assert "frais d'achat n'entrent pas" in ensemble


# --- L'assemblage des trois poches ---------------------------------------------------


def test_chaque_poche_presente_recoit_son_impot_dans_l_ordre_d_affichage():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            poche=Poche.PEA,
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-06 09:00",
            actif=AUTRE,
            poche=Poche.CTO,
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-07 09:00",
            actif=CRYPTO,
            poche=Poche.CRYPTO,
            quantite="1",
            prix_unitaire="1000.00",
        ),
    ]
    le_portefeuille = Portefeuille.construire(operations)

    impots = fiscalite.impots_estimes(
        [], le_portefeuille, date(2026, 9, 27), regles(premier_versement_pea=date(2021, 3, 1))
    )

    assert list(impots) == [Poche.PEA, Poche.CTO, Poche.CRYPTO]


def test_une_poche_absente_n_a_pas_d_impot():
    achat = operation(TypeOperation.ACHAT, poche=Poche.CTO, quantite="10", prix_unitaire="20.00")

    impots = fiscalite.impots_estimes(
        [], Portefeuille.construire([achat]), date(2026, 9, 27), regles()
    )

    assert list(impots) == [Poche.CTO]
