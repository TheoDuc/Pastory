"""Le cœur du moteur, règle par règle.

Chaque test porte le numéro du cas correspondant dans `docs/verification/etape-3.md` : si le
cahier et le code divergeaient un jour, c'est ici qu'on le verrait.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from dashboard_tr.moteur.position import (
    EtatPosition,
    Position,
    appliquer,
    arrondi_au_centime,
    construire_positions,
)
from dashboard_tr.pivot.operation import Poche, TypeOperation
from dashboard_tr.pivot.validation import controler
from tests.moteur.operations_fictives import enchainement_du_glossaire, operation


def rejouer(operations):
    """Construit la position unique de ces opérations, et renvoie ses signalements."""
    positions, signalements = construire_positions(operations)
    assert len(positions) == 1
    return positions[0], signalements


# --- A.1 et A.2 : achats, capital investi et prix de revient moyen --------------------


def test_un_achat_ajoute_son_montant_brut_pas_le_montant_paye():
    """D-12 : les frais et la taxe sont suivis à part, ils n'entrent pas dans le capital."""
    achat = operation(
        TypeOperation.ACHAT, quantite="10", prix_unitaire="20.00", frais="1.00", taxes="0.60"
    )
    assert controler(achat) == []

    position, signalements = rejouer([achat])

    assert position.etat.quantite == Decimal("10")
    assert position.etat.capital_net_investi == Decimal("200.00")
    assert achat.montant_regle == Decimal("201.60")
    assert position.frais == Decimal("1.00")
    assert position.taxes == Decimal("0.60")
    assert signalements == []


def test_le_prix_de_revient_est_la_moyenne_ponderee_des_achats():
    """D-13 : PRU = capital net investi / quantité détenue."""
    position, _ = rejouer(enchainement_du_glossaire()[:2])

    assert position.etat.quantite == Decimal("20")
    assert position.etat.capital_net_investi == Decimal("500.00")
    assert position.etat.prix_de_revient == Decimal("25.000000")


def test_le_journal_suit_l_enchainement_du_glossaire():
    """L'exemple du glossaire §3 et §4, repris tel quel : 200 €, puis 500 €, puis 375 €."""
    position, signalements = rejouer(enchainement_du_glossaire())

    capitaux = [ligne.apres.capital_net_investi for ligne in position.journal]
    assert capitaux == [Decimal("200.00"), Decimal("500.00"), Decimal("375.00")]

    prix_de_revient = [ligne.apres.prix_de_revient for ligne in position.journal]
    assert prix_de_revient == [
        Decimal("20.000000"),
        Decimal("25.000000"),
        Decimal("25.000000"),
    ]
    assert signalements == []


# --- A.3 : vente partielle au prorata et plus-value réalisée --------------------------


def test_une_vente_retire_le_capital_au_prorata_des_parts_vendues():
    """D-12 : cinq parts sur vingt, c'est un quart du capital qui sort — pas les 200 € reçus."""
    position, _ = rejouer(enchainement_du_glossaire())
    vente = position.journal[-1]

    assert vente.capital_retire == Decimal("125.00")
    assert vente.apres.quantite == Decimal("15")
    assert vente.apres.capital_net_investi == Decimal("375.00")
    # Le prix de revient ne bouge pas à la vente (D-13).
    assert vente.avant.prix_de_revient == vente.apres.prix_de_revient


def test_la_plus_value_realisee_compare_l_encaissement_au_capital_retire():
    """Glossaire §4 : 200 € encaissés − 125 € de mise = 75 € brut, 74 € net après 1 € de frais."""
    position, _ = rejouer(enchainement_du_glossaire())
    vente = position.journal[-1]

    assert vente.plus_value_brute == Decimal("75.00")
    assert vente.plus_value_nette == Decimal("74.00")
    assert position.plus_values_realisees_brutes == Decimal("75.00")
    assert position.plus_values_realisees_nettes == Decimal("74.00")


def test_une_vente_totale_vide_la_position_sans_reliquat():
    """Tout vendre doit ramener le capital exactement à zéro, pas à un centime résiduel."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="3",
            prix_unitaire="33.33",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-02-05 09:00",
            quantite="3",
            prix_unitaire="40.00",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.etat.quantite == Decimal("0")
    assert position.etat.capital_net_investi == Decimal("0.00")
    assert position.etat.prix_de_revient is None
    assert signalements == []


def test_le_capital_retire_et_le_capital_restant_retombent_sur_le_capital_d_avant():
    """Aucun centime ne doit se perdre dans l'arrondi d'un prorata qui tombe mal."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="7",
            prix_unitaire="14.29",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-02-05 09:00",
            quantite="2",
            prix_unitaire="20.00",
        ),
    ]
    position, _ = rejouer(operations)
    vente = position.journal[-1]

    # 100,03 € pour 7 parts ; deux parts sortent, soit 28,5800... € arrondis à 28,58 €.
    assert vente.avant.capital_net_investi == Decimal("100.03")
    assert vente.capital_retire == Decimal("28.58")
    assert vente.apres.capital_net_investi == Decimal("71.45")
    assert vente.capital_retire + vente.apres.capital_net_investi == (
        vente.avant.capital_net_investi
    )


# --- A.4 : dividende ------------------------------------------------------------------


def test_un_dividende_ne_change_ni_les_parts_ni_le_capital():
    """D-14 : c'est un revenu de l'actif. D-29 : c'est le brut qui compte."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="20.00",
        ),
        operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-04-20 09:00",
            quantite="10",
            prix_unitaire="0.50",
            taxes="1.50",
        ),
    ]
    dividende = operations[1]
    assert controler(dividende) == []
    assert dividende.montant_brut == Decimal("5.00")
    assert dividende.montant_regle == Decimal("3.50")

    position, signalements = rejouer(operations)

    assert position.etat.quantite == Decimal("10")
    assert position.etat.capital_net_investi == Decimal("200.00")
    assert position.dividendes_bruts == Decimal("5.00")
    assert position.dividendes_taxes == Decimal("1.50")
    assert signalements == []


# --- A.5 : distribution de capital ----------------------------------------------------


def test_une_distribution_de_capital_baisse_le_capital_investi():
    """D-14 : ce n'est pas un revenu, c'est une part de la mise qui revient."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="30",
            prix_unitaire="10.00",
        ),
        operation(
            TypeOperation.DISTRIBUTION_CAPITAL,
            horodatage="2026-05-05 09:00",
            quantite="30",
            prix_unitaire="0.40",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.etat.quantite == Decimal("30")
    assert position.etat.capital_net_investi == Decimal("288.00")
    assert position.distributions_capital == Decimal("12.00")
    assert signalements == []


def test_une_distribution_superieure_au_capital_s_arrete_a_zero():
    """D-45 : une distribution ne peut pas rendre plus que ce qui a été mis."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="10",
            prix_unitaire="1.00",
        ),
        operation(
            TypeOperation.DISTRIBUTION_CAPITAL,
            horodatage="2026-05-05 09:00",
            quantite="10",
            prix_unitaire="3.00",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.etat.capital_net_investi == Decimal("0.00")
    assert position.distributions_capital == Decimal("10.00")
    assert [signalement.categorie for signalement in signalements] == ["distribution excédentaire"]
    # Le plafonnement laisse un montant distribué supérieur au capital retiré : sans
    # drapeau, le journal montrerait cet écart sans un mot d'explication.
    assert position.etat.distribution_excedentaire is True
    assert position.historique_incomplet is True
    assert position.etat.prix_de_revient is None


# --- A.6 : titres reçus sans achat ----------------------------------------------------


def test_des_titres_recus_avec_un_prix_connu_entrent_dans_le_capital():
    """D-15 : une action gagnée dont le cours est affiché vaut son cours."""
    titres = operation(
        TypeOperation.TITRES_RECUS,
        horodatage="2026-03-01 09:00",
        quantite="2",
        prix_unitaire="10.00",
    )
    assert controler(titres) == []

    position, signalements = rejouer([titres])

    assert position.etat.quantite == Decimal("2")
    assert position.etat.capital_net_investi == Decimal("20.00")
    assert position.etat.prix_de_revient == Decimal("10.000000")
    assert signalements == []


def test_des_parts_sans_prix_connu_sont_comptees_mais_pas_leur_montant():
    """D-15 et D-45 : les parts sont détenues, le prix viendra des cours de l'étape 4."""
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
    assert controler(operations[1]) == []

    position, signalements = rejouer(operations)

    assert position.etat.quantite == Decimal("13")
    assert position.etat.capital_net_investi == Decimal("200.00")
    assert position.etat.prix_inconnu is True
    assert [signalement.categorie for signalement in signalements] == ["prix à compléter"]


def test_le_prix_de_revient_se_tait_plutot_que_d_afficher_un_nombre_dilue():
    """D-45 : 200 € / 13 parts donnerait 15,38 €, un prix de revient faussement bas."""
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
    position, _ = rejouer(operations)

    assert position.etat.prix_de_revient is None
    assert position.historique_incomplet is True


# --- A.7 : crypto ---------------------------------------------------------------------


def test_une_quantite_a_six_decimales_garde_sa_precision():
    """Une crypto s'achète par fractions : le moteur ne doit rien arrondir sur la quantité."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            actif="XF000ABCDEF1",
            poche=Poche.CRYPTO,
            quantite="0.000833",
            prix_unitaire="30000.00",
            montant_brut="24.99",
        ),
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-02-05 09:00",
            actif="XF000ABCDEF1",
            poche=Poche.CRYPTO,
            quantite="0.000400",
            prix_unitaire="31250.00",
            montant_brut="12.50",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.poche is Poche.CRYPTO
    assert position.etat.quantite == Decimal("0.001233")
    assert position.etat.capital_net_investi == Decimal("37.49")
    # 37,49 / 0,001233 = 30 405,515004... € par unité.
    assert position.etat.prix_de_revient == Decimal("30405.515004")
    assert signalements == []


# --- A.8 : vente au-delà du stock compté ----------------------------------------------


def test_une_vente_au_dela_du_stock_vide_la_position_et_le_signale():
    """D-45 : plutôt qu'une quantité négative, on vide et on dit que l'histoire est trouée."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="4",
            prix_unitaire="25.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-06-05 09:00",
            quantite="10",
            prix_unitaire="30.00",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.etat.quantite == Decimal("0")
    assert position.etat.capital_net_investi == Decimal("0.00")
    assert position.etat.stock_insuffisant is True
    assert position.etat.prix_de_revient is None
    assert [signalement.categorie for signalement in signalements] == ["stock insuffisant"]
    assert position.journal[-1].fiable is False


def test_vendre_exactement_tout_n_est_pas_un_stock_insuffisant():
    """La limite doit être franchie, pas atteinte : une vente totale est parfaitement normale."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="4",
            prix_unitaire="25.00",
        ),
        operation(
            TypeOperation.VENTE,
            horodatage="2026-06-05 09:00",
            quantite="4",
            prix_unitaire="30.00",
        ),
    ]
    position, signalements = rejouer(operations)

    assert position.etat.stock_insuffisant is False
    assert signalements == []


# --- L'ordre et le découpage ----------------------------------------------------------


def test_les_operations_sont_rejouees_dans_l_ordre_des_horodatages():
    """L'ordre du fichier n'est jamais supposé : c'est l'horodatage qui commande."""
    achat, second_achat, vente = enchainement_du_glossaire()
    position, _ = rejouer([vente, achat, second_achat])

    assert [ligne.operation.type for ligne in position.journal] == [
        TypeOperation.ACHAT,
        TypeOperation.ACHAT,
        TypeOperation.VENTE,
    ]


def test_deux_operations_simultanees_gardent_toujours_le_meme_ordre():
    """Deux lectures du même export doivent donner exactement le même journal."""
    premiere = operation(
        TypeOperation.ACHAT,
        horodatage="2026-01-05 09:00",
        quantite="1",
        prix_unitaire="10.00",
        identifiant="op-a",
    )
    seconde = operation(
        TypeOperation.ACHAT,
        horodatage="2026-01-05 09:00",
        quantite="1",
        prix_unitaire="20.00",
        identifiant="op-b",
    )
    position, _ = rejouer([seconde, premiere])

    assert [ligne.operation.identifiant for ligne in position.journal] == ["op-a", "op-b"]


def test_un_meme_actif_dans_deux_poches_fait_deux_positions():
    """Un même ETF peut être détenu en PEA et en CTO : deux histoires, deux prix de revient."""
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
            poche=Poche.CTO,
            quantite="10",
            prix_unitaire="30.00",
        ),
    ]
    positions, _ = construire_positions(operations)

    assert [(position.poche, position.etat.prix_de_revient) for position in positions] == [
        (Poche.CTO, Decimal("30.000000")),
        (Poche.PEA, Decimal("20.000000")),
    ]


def test_jusqu_au_rend_la_position_telle_qu_elle_etait_ce_jour_la():
    """De quoi tracer l'évolution jour par jour à l'étape 5, sans rejouer quoi que ce soit."""
    position, _ = rejouer(enchainement_du_glossaire())

    au_debut = position.jusqu_au(date(2026, 1, 31))
    assert au_debut.etat.quantite == Decimal("10")
    assert au_debut.etat.capital_net_investi == Decimal("200.00")
    assert au_debut.plus_values_realisees_brutes == Decimal("0.00")

    avant_tout = position.jusqu_au(date(2025, 12, 31))
    assert avant_tout.journal == ()
    assert avant_tout.etat == EtatPosition()


# --- Les coûts, tenus à part de la performance (D-21) ---------------------------------


def test_les_couts_sont_ranges_par_moment():
    """Prépare les trois niveaux de la vue « frais et taxes » sans rien mélanger au brut."""
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
    position, _ = rejouer(operations)

    assert position.couts_par_moment() == {
        "frais d'achat": Decimal("1.00"),
        "taxes d'achat": Decimal("0.60"),
        "frais de vente": Decimal("1.00"),
        "taxes de vente": Decimal("0.00"),
        "taxes sur revenus": Decimal("1.50"),
        "autres prélèvements": Decimal("0.00"),
    }
    assert position.frais == Decimal("2.00")
    assert position.taxes == Decimal("2.10")
    # Rien de tout cela n'a touché au capital investi.
    assert position.etat.capital_net_investi == Decimal("100.00")


def test_le_detail_des_couts_tombe_toujours_sur_leur_total():
    """Une colonne de rapport qui ne fait pas son propre total fait douter de tout le reste."""
    operations = [
        operation(
            TypeOperation.ACHAT,
            horodatage="2026-01-05 09:00",
            quantite="30",
            prix_unitaire="10.00",
        ),
        # Une distribution de capital avec des frais : aucun des cinq moments nommés ne la
        # couvre, et sans la ligne « autres prélèvements » ces 0,80 € disparaîtraient.
        operation(
            TypeOperation.DISTRIBUTION_CAPITAL,
            horodatage="2026-05-05 09:00",
            quantite="30",
            prix_unitaire="0.40",
            frais="0.50",
            taxes="0.30",
        ),
    ]
    position, _ = rejouer(operations)

    detail = position.couts_par_moment()
    assert detail["autres prélèvements"] == Decimal("0.80")
    assert sum(detail.values()) == position.frais + position.taxes


# --- Les garde-fous -------------------------------------------------------------------


def test_une_position_vide_ne_calcule_pas_de_prix_de_revient():
    assert EtatPosition().prix_de_revient is None
    assert Position(actif="XX0000000001", poche=Poche.CTO, journal=()).etat == EtatPosition()


def test_une_operation_sans_quantite_est_signalee_et_laisse_l_etat_intact():
    """Le moteur ne devine rien et ne plante pas : il dit que la ligne est inexploitable."""
    boiteuse = operation(TypeOperation.ACHAT, montant_brut="50.00")
    etat = EtatPosition(quantite=Decimal("2"), capital_net_investi=Decimal("50.00"))
    signalements = []

    ligne = appliquer(etat, boiteuse, signalements.append)

    assert ligne.apres == etat
    assert [signalement.categorie for signalement in signalements] == ["opération inexploitable"]


def test_l_arrondi_au_centime_suit_la_regle_apprise_a_l_ecole():
    assert arrondi_au_centime(Decimal("0.125")) == Decimal("0.13")
    assert arrondi_au_centime(Decimal("0.124")) == Decimal("0.12")
