"""Les coûts payés et les coûts estimés, règle par règle.

Chaque test porte le numéro du cas correspondant dans `docs/verification/etape-6.md` : si le
cahier et le code divergeaient un jour, c'est ici qu'on le verrait.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pastory.moteur import couts
from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.rendements import Periode
from pastory.moteur.valorisation import valoriser
from pastory.pivot.operation import Poche, TypeOperation
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, operation
from tests.moteur.parametres_fictifs import ParametresFictifs

AUTRE = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"


def portefeuille(operations):
    return Portefeuille.construire(operations)


def lignes(operations, parametres=None, periode=None):
    return couts.lignes_de_couts(
        portefeuille(operations),
        periode or Periode(fin=date(2026, 12, 31)),
        parametres or ParametresFictifs(types={ACTIF: "etf"}),
    )


# --- A.1 : le poids d'un coût dans son opération -------------------------------------


def test_le_poids_d_un_cout_est_sa_part_du_montant_brut():
    """1 € de frais sur un achat brut de 25 € pèse 4 % (glossaire §6)."""
    achat = operation(
        TypeOperation.ACHAT, quantite="5", prix_unitaire="5.00", frais="1.00"
    )

    ligne = lignes([achat])[0]

    assert ligne.montant_brut == Decimal("25.00")
    assert ligne.cout_paye == Decimal("1.00")
    assert ligne.poids == Decimal("0.040000")


def test_un_plan_d_epargne_gratuit_pese_zero():
    achat = operation(TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00")

    assert lignes([achat])[0].poids == Decimal("0.000000")


def test_sans_montant_brut_connu_il_n_y_a_pas_de_poids():
    """D-15 : sans base, la division n'a pas de sens — et on ne met pas zéro."""
    recus = operation(TypeOperation.TITRES_RECUS, quantite="3", prix_a_completer=True)

    ligne = lignes([recus])[0]

    assert ligne.montant_brut is None
    assert ligne.poids is None


def test_la_somme_des_lignes_retombe_sur_les_totaux_du_moteur():
    """Le contrôle que le propriétaire refait dans le tableur : couts.csv contre le rapport."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
            taxes="0.60",
        ),
        operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-04-20 09:00",
            quantite="10",
            prix_unitaire="0.50",
            taxes="1.50",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-06-15 09:00",
            quantite="5",
            prix_unitaire="40.00",
            frais="1.00",
        ),
    ]
    le_portefeuille = portefeuille(operations)
    totaux = couts.TotauxCouts(tuple(lignes(operations)))

    assert totaux.frais == le_portefeuille.total.frais == Decimal("2.00")
    assert totaux.taxes == le_portefeuille.total.taxes == Decimal("2.10")


def test_les_couts_se_rangent_en_trois_niveaux_dont_la_somme_fait_le_total():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-04-20 09:00",
            quantite="10",
            prix_unitaire="0.50",
            taxes="1.50",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-06-15 09:00",
            quantite="5",
            prix_unitaire="40.00",
            frais="2.00",
        ),
    ]
    totaux = couts.TotauxCouts(tuple(lignes(operations)))

    par_moment = totaux.par_moment()
    assert par_moment["à l'entrée"] == Decimal("1.00")
    assert par_moment["sur les revenus"] == Decimal("1.50")
    assert par_moment["à la sortie"] == Decimal("2.00")
    assert sum(par_moment.values()) == totaux.cout_paye == Decimal("4.50")


def test_la_periode_filtre_les_operations():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-06-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
            frais="5.00",
        ),
    ]
    du_semestre = lignes(
        operations, periode=Periode(debut=date(2026, 6, 1), fin=date(2026, 12, 31))
    )

    assert couts.TotauxCouts(tuple(du_semestre)).frais == Decimal("5.00")


# --- A.2 : le spread estimé ------------------------------------------------------------


def test_le_spread_estime_est_le_montant_brut_fois_le_taux_par_cote():
    """D-30, D-56 : 200 € à 0,05 % par côté font 0,10 €, à l'achat comme à la vente."""
    achat = operation(TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00")

    ligne = lignes([achat])[0]

    assert ligne.spread_estime is not None
    assert ligne.spread_estime.montant == Decimal("0.10")
    assert ligne.spread_estime.base == Decimal("200.00")
    assert "0,05 %" in ligne.spread_estime.formule


def test_une_action_et_une_crypto_ont_leur_propre_taux():
    achat_action = operation(
        TypeOperation.ACHAT, actif=AUTRE, quantite="10", prix_unitaire="20.00"
    )
    achat_crypto = operation(
        TypeOperation.ACHAT,
        actif=CRYPTO,
        poche=Poche.CRYPTO,
        quantite="1",
        prix_unitaire="200.00",
    )
    parametres = ParametresFictifs(types={AUTRE: "action"})

    action, crypto = (
        lignes([achat_action], parametres)[0],
        lignes([achat_crypto], parametres)[0],
    )

    assert action.spread_estime.montant == Decimal("0.20")  # 0,10 %
    assert crypto.spread_estime.montant == Decimal("1.00")  # 0,50 %


def test_un_taux_declare_pour_un_actif_remplace_celui_de_son_type():
    achat = operation(TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00")
    parametres = ParametresFictifs(types={ACTIF: "etf"}, spreads={ACTIF: "0.25"})

    assert lignes([achat], parametres)[0].spread_estime.montant == Decimal("0.50")


def test_sans_type_declare_aucun_spread_n_est_estime_et_cela_se_voit():
    """D-55 : on ne devine pas un type, et on ne compte pas zéro en silence."""
    achat = operation(TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00")

    ligne = lignes([achat], ParametresFictifs())[0]

    assert ligne.spread_estime is None
    assert ligne.spread_attendu
    assert ligne.spread_manquant
    totaux = couts.TotauxCouts((ligne,))
    assert totaux.spread_estime == Decimal("0.00")
    assert totaux.actifs_sans_type == [ACTIF]


def test_un_dividende_et_des_titres_recus_ne_paient_aucun_spread():
    """Aucun carnet d'ordres n'est traversé : il n'y a pas d'écart de prix à estimer."""
    operations = [
        operation(
            TypeOperation.TITRES_RECUS,
            horodatage="2026-01-05 09:00",
            quantite="3",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-04-20 09:00",
            quantite="3",
            prix_unitaire="0.50",
        ),
    ]
    for ligne in lignes(operations):
        assert ligne.spread_estime is None
        assert not ligne.spread_attendu
        assert not ligne.spread_manquant


# --- A.3 : les frais courants d'un ETF (TER) -------------------------------------------


def valorisation_d_un_etf(cours="40.00", quantite="15"):
    achat = operation(
        TypeOperation.ACHAT, horodatage="2026-01-05 09:00", quantite=quantite,
        prix_unitaire="20.00",
    )
    source = SourceFixe(cours_constant(ACTIF, cours, date(2026, 1, 1), date(2026, 3, 31)))
    return valoriser(portefeuille([achat]), date(2026, 3, 31), source)


def test_les_frais_courants_estimes_sont_la_valeur_fois_le_ter():
    """600,00 € de valeur à 0,20 % font 1,20 € par an (glossaire §6)."""
    valorisation = valorisation_d_un_etf()
    parametres = ParametresFictifs(types={ACTIF: "etf"}, ter={ACTIF: "0.20"})

    frais = couts.frais_courants(valorisation, parametres)

    assert len(frais) == 1
    assert frais[0].estimation.montant == Decimal("1.20")
    assert frais[0].estimation.base == Decimal("600.00")


def test_sans_ter_rien_n_est_estime_et_le_motif_le_dit():
    """D-61 : un TER introuvable ne devient jamais un zéro."""
    frais = couts.frais_courants(
        valorisation_d_un_etf(), ParametresFictifs(types={ACTIF: "etf"})
    )

    assert frais[0].estimation is None
    assert "frais courants introuvables" in frais[0].motif


def test_ce_qui_n_est_pas_un_etf_n_a_pas_de_frais_courants():
    """Une action ne prélève rien pendant la détention : elle n'apparaît pas dans ce bloc."""
    assert couts.frais_courants(valorisation_d_un_etf(), ParametresFictifs()) == []


def test_un_etf_non_valorise_n_a_pas_de_frais_courants_estimes():
    """D-53 : sans valeur, pas de base — et le motif le dit plutôt que d'afficher zéro."""
    achat = operation(TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00")
    valorisation = valoriser(portefeuille([achat]), date(2026, 3, 31), SourceFixe())

    frais = couts.frais_courants(
        valorisation, ParametresFictifs(types={ACTIF: "etf"}, ter={ACTIF: "0.20"})
    )

    assert frais[0].estimation is None
    assert "non valorisé" in frais[0].motif


# --- Les regroupements, ceux que le rapport affiche ------------------------------------


def test_les_totaux_se_groupent_par_poche_et_par_actif():
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            poche=Poche.PEA,
            quantite="10",
            prix_unitaire="20.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-02-05 09:00",
            actif=AUTRE,
            poche=Poche.CTO,
            quantite="10",
            prix_unitaire="20.00",
            frais="2.00",
        ),
    ]
    toutes = lignes(operations, ParametresFictifs(types={ACTIF: "etf", AUTRE: "action"}))

    par_poche = couts.totaux_par_poche(toutes)
    assert par_poche[Poche.PEA].frais == Decimal("1.00")
    assert par_poche[Poche.CTO].frais == Decimal("2.00")
    par_actif = couts.totaux_par_actif(toutes)
    assert par_actif[(ACTIF, Poche.PEA)].cout_paye == Decimal("1.00")
    # Les poches gardent l'ordre d'affichage du projet.
    assert list(par_poche) == [Poche.PEA, Poche.CTO]


def test_le_poids_moyen_ignore_les_operations_sans_base():
    """Sinon un titre reçu sans prix ferait baisser le poids moyen sans raison."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="5",
            prix_unitaire="5.00",
            frais="1.00",
        ),
        operation(
            TypeOperation.TITRES_RECUS,
            horodatage="2026-02-05 09:00",
            quantite="3",
            prix_a_completer=True,
        ),
    ]
    totaux = couts.TotauxCouts(tuple(lignes(operations)))

    assert totaux.poids_moyen == Decimal("0.040000")
