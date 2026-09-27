"""La valeur réelle : ce qu'on récupérerait en vendant tout aujourd'hui (D-23).

Chaque test porte le numéro du cas correspondant dans `docs/verification/etape-6.md`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_tr.moteur.portefeuille import Portefeuille
from dashboard_tr.moteur.valeur_reelle import valeur_reelle
from dashboard_tr.moteur.valorisation import valoriser
from dashboard_tr.pivot.operation import Poche, TypeOperation
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import ACTIF, operation
from tests.moteur.parametres_fictifs import ParametresFictifs, regles

AUTRE = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"
FIN = date(2026, 9, 27)


def construire(operations, series, parametres=None, premier_versement_pea=None):
    """Un portefeuille valorisé, puis sa valeur réelle."""
    portefeuille = Portefeuille.construire(operations)
    source = SourceFixe(series)
    valorisation = valoriser(portefeuille, FIN, source)
    return valeur_reelle(
        portefeuille,
        valorisation,
        parametres or ParametresFictifs(types={ACTIF: "etf"}),
        regles(premier_versement_pea=premier_versement_pea),
    )


def achat_etf(poche=Poche.CTO, actif=ACTIF, quantite="10", prix="20.00", frais="1.00"):
    return operation(
        TypeOperation.ACHAT,
        horodatage="2026-01-05 09:00",
        actif=actif,
        poche=poche,
        quantite=quantite,
        prix_unitaire=prix,
        frais=frais,
    )


def serie(actif, cours):
    return cours_constant(actif, cours, date(2026, 1, 1), FIN)


# --- A.8 : la décomposition, ligne par ligne -----------------------------------------


def test_la_valeur_reelle_retranche_les_frais_le_spread_et_l_impot():
    """10 parts valant 30 € : 300 € bruts, 1 € de frais, 0,15 € de spread (0,05 %), puis
    l'impôt sur 298,85 − 201 = 97,85 €, soit 30,72 €. Reste 268,13 €."""
    resultat = construire([achat_etf()], serie(ACTIF, "30.00"))

    poche = resultat.par_poche[Poche.CTO]
    assert poche.valeur_brute == Decimal("300.00")
    assert poche.frais_de_vente == Decimal("1.00")
    assert poche.spread == Decimal("0.15")
    assert poche.avant_impot == Decimal("298.85")
    assert poche.impot.base == Decimal("97.85")
    assert poche.impot.impot == Decimal("30.72")
    assert poche.valeur_reelle == Decimal("268.13")


def test_le_total_est_la_somme_des_poches():
    operations = [
        achat_etf(poche=Poche.PEA),
        achat_etf(actif=AUTRE, poche=Poche.CTO),
    ]
    series = {**serie(ACTIF, "30.00"), **serie(AUTRE, "30.00")}
    parametres = ParametresFictifs(types={ACTIF: "etf", AUTRE: "etf"})

    resultat = construire(
        operations, series, parametres, premier_versement_pea=date(2021, 3, 1)
    )

    assert resultat.valeur_brute == Decimal("600.00")
    assert resultat.frais_de_vente == Decimal("2.00")
    assert resultat.spread == Decimal("0.30")
    attendu = sum(
        poche.valeur_reelle for poche in resultat.par_poche.values()
    )
    assert resultat.valeur_reelle == attendu
    assert not resultat.partielle


def test_chaque_retenue_dit_d_ou_vient_son_taux():
    """Règle 6 de CLAUDE.md : une estimation doit être signalée, avec sa source."""
    resultat = construire([achat_etf()], serie(ACTIF, "30.00"))

    ligne = resultat.par_poche[Poche.CTO].lignes[0]
    assert "0,05 %" in ligne.spread.formule
    assert ligne.spread.parametre.source
    assert "montant fixe" in ligne.frais_de_vente.formule
    # Le rapport doit pouvoir citer chaque paramètre une seule fois.
    noms = [parametre.nom for parametre in resultat.parametres_cites]
    assert len(noms) == len(set(noms))


def test_les_trois_poches_ont_chacune_leur_regle():
    operations = [
        achat_etf(poche=Poche.PEA),
        achat_etf(actif=AUTRE, poche=Poche.CTO),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-07 09:00",
            actif=CRYPTO,
            poche=Poche.CRYPTO,
            quantite="1",
            prix_unitaire="1000.00",
            frais="1.00",
        ),
    ]
    series = {
        **serie(ACTIF, "30.00"),
        **serie(AUTRE, "30.00"),
        **serie(CRYPTO, "1500.00"),
    }
    parametres = ParametresFictifs(types={ACTIF: "etf", AUTRE: "action"})

    resultat = construire(
        operations, series, parametres, premier_versement_pea=date(2021, 3, 1)
    )

    assert list(resultat.par_poche) == [Poche.PEA, Poche.CTO, Poche.CRYPTO]
    # Le PEA de plus de cinq ans ne paie que les prélèvements sociaux.
    assert resultat.par_poche[Poche.PEA].impot.taux == Decimal("18.6")
    assert resultat.par_poche[Poche.CTO].impot.taux == Decimal("31.4")
    # La crypto : 1 500 € − 7,50 de spread (0,50 %) − 1 € de frais − 1 000 investis.
    crypto = resultat.par_poche[Poche.CRYPTO]
    assert crypto.spread == Decimal("7.50")
    assert crypto.impot.base == Decimal("491.50")


def test_le_capital_fiscal_sert_au_cto_et_le_capital_investi_a_la_crypto():
    """Les frais d'achat entrent dans le prix de revient fiscal du CTO, pas dans celui de la
    crypto (lecture prudente de la loi)."""
    operations = [
        achat_etf(actif=AUTRE, poche=Poche.CTO, frais="1.00"),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-07 09:00",
            actif=CRYPTO,
            poche=Poche.CRYPTO,
            quantite="1",
            prix_unitaire="200.00",
            frais="1.00",
        ),
    ]
    series = {**serie(AUTRE, "30.00"), **serie(CRYPTO, "200.00")}
    parametres = ParametresFictifs(types={AUTRE: "etf"})

    resultat = construire(operations, series, parametres)

    cto = resultat.par_poche[Poche.CTO].lignes[0].cession
    crypto = resultat.par_poche[Poche.CRYPTO].lignes[0].cession
    assert cto.capital_fiscal == Decimal("201.00")
    assert crypto.capital_net_investi == Decimal("200.00")
    assert crypto.capital_fiscal == Decimal("201.00")
    # La crypto est imposée sur le capital investi, donc sans les frais d'achat.
    assert crypto.plus_value(Poche.CRYPTO) == Decimal("200.00") - Decimal("1.00") - Decimal(
        "1.00"
    ) - Decimal("200.00")


# --- A.9 : ce qui est refusé -------------------------------------------------------


def test_un_actif_sans_cours_sort_de_la_valeur_reelle_qui_est_partielle():
    """D-53 : jamais un zéro silencieux."""
    operations = [achat_etf(), achat_etf(actif=AUTRE)]
    parametres = ParametresFictifs(types={ACTIF: "etf", AUTRE: "etf"})

    resultat = construire(operations, serie(ACTIF, "30.00"), parametres)

    assert resultat.partielle
    assert [exclue.position.actif for exclue in resultat.exclues] == [AUTRE]
    assert resultat.par_poche[Poche.CTO].valeur_brute == Decimal("300.00")


def test_un_actif_sans_type_declare_sort_aussi_et_dit_quoi_faire():
    """D-55 : sans type, pas de spread estimé — donc pas de valeur réelle pour cet actif."""
    resultat = construire([achat_etf()], serie(ACTIF, "30.00"), ParametresFictifs())

    assert resultat.partielle
    assert "actifs.toml" in resultat.exclues[0].motif


def test_un_pea_dont_une_ligne_manque_n_a_pas_d_impot_du_tout():
    """Le gain est celui du plan : un impôt calculé sur la moitié des lignes serait faux."""
    operations = [
        achat_etf(poche=Poche.PEA),
        achat_etf(actif=AUTRE, poche=Poche.PEA),
    ]
    parametres = ParametresFictifs(types={ACTIF: "etf", AUTRE: "etf"})

    resultat = construire(
        operations, serie(ACTIF, "30.00"), parametres, premier_versement_pea=date(2021, 3, 1)
    )

    poche = resultat.par_poche[Poche.PEA]
    assert poche.impot.impot is None
    assert poche.valeur_reelle is None
    assert "ne se calcule pas à moitié" in poche.impot.motif
    assert resultat.partielle


def test_sans_date_de_pea_la_poche_n_a_pas_de_valeur_reelle_mais_les_autres_si():
    """Une poche non calculable ne doit pas emporter tout le rapport avec elle."""
    operations = [achat_etf(poche=Poche.PEA), achat_etf(actif=AUTRE, poche=Poche.CTO)]
    series = {**serie(ACTIF, "30.00"), **serie(AUTRE, "30.00")}
    parametres = ParametresFictifs(types={ACTIF: "etf", AUTRE: "etf"})

    resultat = construire(operations, series, parametres)

    assert resultat.par_poche[Poche.PEA].valeur_reelle is None
    assert resultat.par_poche[Poche.CTO].valeur_reelle is not None
    assert resultat.valeur_reelle == resultat.par_poche[Poche.CTO].valeur_reelle
    assert resultat.partielle
    assert [poche.poche for poche in resultat.poches_non_calculables] == [Poche.PEA]


def test_un_portefeuille_sans_rien_de_calculable_n_a_pas_de_valeur_reelle():
    resultat = construire([achat_etf(poche=Poche.PEA)], serie(ACTIF, "30.00"))

    assert resultat.valeur_reelle is None
    assert resultat.partielle
