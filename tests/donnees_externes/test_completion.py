"""La complétion des prix manquants : le branchement de D-15.

Ce que ces tests prouvent, et c'est tout l'objet de l'étape :

1. un titre reçu sans prix, une fois valorisé au cours de son jour d'apparition, **rend son
   capital investi et son prix de revient** au moteur (D-15, D-45) ;
2. sans cours utilisable, l'opération repart **inchangée** : on ne remplace rien par un zéro ni
   par une estimation, et le motif du refus est rapporté ;
3. ce qui sort d'ici reste du format pivot valide — les contrôles de cohérence du pivot le
   vérifient dans ces tests mêmes.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from pastory.donnees_externes.completion import completer_les_prix
from pastory.donnees_externes.cours import FournisseurDeCours
from pastory.moteur.portefeuille import Portefeuille
from pastory.pivot import validation
from pastory.pivot.operation import Provenance, TypeOperation
from tests.donnees_externes.cours_fictifs import (
    ACTIF,
    AUJOURD_HUI,
    CacheEnMemoire,
    SourceFictive,
    configuration,
    cours,
)
from tests.moteur.operations_fictives import operation

JOUR = Date(2026, 3, 6)
SAMEDI = Date(2026, 3, 7)


def fournisseur(series=None, *, declarations=None):
    return FournisseurDeCours(
        configuration(declarations),
        CacheEnMemoire(),
        SourceFictive(series or {}),
        aujourd_hui=AUJOURD_HUI,
    )


def titres_recus(horodatage="2026-03-06 08:00", quantite="13.000000"):
    """Des parts qui apparaissent sans prix : le cas de D-15."""
    return operation(
        TypeOperation.TITRES_RECUS,
        horodatage=horodatage,
        actif=ACTIF,
        quantite=quantite,
        prix_a_completer=True,
    )


class TestPrixComplete:
    def test_le_montant_brut_devient_quantite_fois_cours(self):
        une_operation = titres_recus(quantite="13.000000")
        source = {ACTIF: [cours(JOUR, "15.384615")]}

        completion = completer_les_prix([une_operation], fournisseur(source))

        completee = completion.operations[0]
        # 13 × 15,384615 = 200,000 (arrondi au centime)
        assert completee.montant_brut == Decimal("200.00")
        assert completee.prix_unitaire == Decimal("15.384615")

    def test_le_montant_deduit_est_marque_comme_deduit(self):
        # D-15 : « la valeur est marquée comme déduite ». C'est cette marque que les CSV et
        # l'interface reprennent pour dire au propriétaire que ce chiffre n'est pas de la
        # banque.
        completion = completer_les_prix(
            [titres_recus()], fournisseur({ACTIF: [cours(JOUR, "10.00")]})
        )

        completee = completion.operations[0]
        assert completee.provenance["montant_brut"] is Provenance.DEDUCTION
        assert completee.provenance["prix_unitaire"] is Provenance.DEDUCTION
        assert completee.complete is True

    def test_l_operation_completee_reste_un_pivot_valide(self):
        # Le garde-fou qui compte : ce module produit du format pivot, et le pivot a ses
        # propres contrôles de cohérence. Ils doivent passer sans exception.
        completion = completer_les_prix(
            [titres_recus()], fournisseur({ACTIF: [cours(JOUR, "15.384615")]})
        )

        assert validation.controler(completion.operations[0]) == []

    def test_rien_d_autre_n_est_touche(self):
        une_operation = titres_recus()
        completion = completer_les_prix(
            [une_operation], fournisseur({ACTIF: [cours(JOUR, "10.00")]})
        )

        completee = completion.operations[0]
        assert completee.identifiant == une_operation.identifiant
        assert completee.date == une_operation.date
        assert completee.quantite == une_operation.quantite
        assert completee.poche == une_operation.poche
        # Des titres reçus ne coûtent rien : compléter leur valeur ne change pas ce fait.
        assert completee.montant_regle == Decimal("0.00")
        assert completee.frais == Decimal("0.00")

    def test_la_trace_permet_de_refaire_le_calcul_a_la_main(self):
        completion = completer_les_prix(
            [titres_recus(quantite="13.000000")],
            fournisseur({ACTIF: [cours(JOUR, "15.384615")]}),
        )

        trace = completion.prix_completes[0]
        assert trace.actif == ACTIF
        assert trace.quantite == Decimal("13.000000")
        assert trace.cours.valeur == Decimal("15.384615")
        assert trace.cours.place == "XETRA"
        assert trace.cours.source == "Source de test"
        assert trace.montant_brut == Decimal("200.00")
        assert trace.jour_decale is False

    def test_un_cours_d_un_autre_jour_se_voit(self):
        # Des titres reçus un samedi sont valorisés au cours du vendredi : c'est normal, et
        # ça doit rester visible pour qui compare avec son application.
        completion = completer_les_prix(
            [titres_recus(horodatage="2026-03-07 08:00")],
            fournisseur({ACTIF: [cours(JOUR, "10.00")]}),
        )

        trace = completion.prix_completes[0]
        assert trace.date_operation == SAMEDI
        assert trace.cours.date == JOUR
        assert trace.jour_decale is True


class TestRefus:
    def test_sans_cours_l_operation_repart_inchangee(self):
        une_operation = titres_recus()

        completion = completer_les_prix([une_operation], fournisseur({}))

        assert completion.operations[0] == une_operation
        assert completion.operations[0].est_a_completer("montant_brut")
        assert completion.prix_completes == ()
        assert completion.incompletes == 1

    def test_le_motif_du_refus_est_rapporte(self):
        completion = completer_les_prix([titres_recus()], fournisseur({}, declarations={}))

        assert [refus.categorie for refus in completion.refus] == ["actif non déclaré"]
        assert "pastory actifs" in completion.refus[0].motif

    def test_rien_n_est_estime_a_zero(self):
        # L'erreur qu'il ne faut jamais commettre : un montant absent remplacé par zéro
        # disparaîtrait des totaux sans que rien ne le dise.
        completion = completer_les_prix([titres_recus()], fournisseur({}))

        assert completion.operations[0].montant_brut is None


class TestCeQuiNAPasBesoinDEtreComplete:
    def test_un_achat_normal_n_est_pas_touche(self):
        achat = operation(
            TypeOperation.ACHAT,
            actif=ACTIF,
            quantite="2.000000",
            prix_unitaire="100.00",
            frais="1.00",
        )

        completion = completer_les_prix([achat], fournisseur({ACTIF: [cours(JOUR, "999.99")]}))

        assert completion.operations == (achat,)
        assert completion.rien_a_completer is True

    def test_l_ordre_des_operations_est_conserve(self):
        # Le moteur rejoue une histoire : en changer l'ordre changerait les chiffres.
        premiere = operation(
            TypeOperation.ACHAT,
            horodatage="2026-03-02 08:00",
            actif=ACTIF,
            quantite="1.000000",
            prix_unitaire="100.00",
        )
        seconde = titres_recus()
        troisieme = operation(
            TypeOperation.DIVIDENDE,
            horodatage="2026-03-10 08:00",
            actif=ACTIF,
            montant_brut="5.00",
        )

        completion = completer_les_prix(
            [premiere, seconde, troisieme], fournisseur({ACTIF: [cours(JOUR, "10.00")]})
        )

        assert [une.identifiant for une in completion.operations] == [
            premiere.identifiant,
            seconde.identifiant,
            troisieme.identifiant,
        ]

    def test_une_operation_sans_quantite_n_est_pas_comptee_comme_attendue(self):
        # Sans quantité, il n'y a rien à multiplier. Le moteur la signale déjà comme
        # inexploitable : ce n'est pas ici qu'on le répète.
        sans_quantite = operation(
            TypeOperation.TITRES_RECUS, actif=ACTIF, prix_a_completer=True
        )

        completion = completer_les_prix(
            [sans_quantite], fournisseur({ACTIF: [cours(JOUR, "10.00")]})
        )

        assert completion.rien_a_completer is True
        assert completion.operations == (sans_quantite,)

    def test_une_liste_vide_ne_dit_rien(self):
        completion = completer_les_prix([], fournisseur())

        assert completion.operations == ()
        assert completion.rien_a_completer is True


class TestCeQueLeMoteurEnFait:
    """Le contrôle qui prouve l'étape, bout en bout, sans toucher au moteur."""

    def test_un_titre_recu_sans_prix_retrouve_son_capital_et_son_prix_de_revient(self):
        operations = [titres_recus(quantite="13.000000")]

        avant = Portefeuille.construire(operations)
        position_avant = avant.positions[0]

        completion = completer_les_prix(
            operations, fournisseur({ACTIF: [cours(JOUR, "15.384615")]})
        )
        apres = Portefeuille.construire(completion.operations)
        position_apres = apres.positions[0]

        # Avant : les parts étaient comptées, leur montant non, et le prix de revient se
        # taisait plutôt que d'afficher un nombre faussement bas (D-45).
        assert position_avant.etat.quantite == Decimal("13.000000")
        assert position_avant.etat.capital_net_investi == Decimal("0.00")
        assert position_avant.etat.prix_de_revient is None
        assert position_avant.historique_incomplet is True

        # Après : le capital est là, et le prix de revient redevient un nombre.
        assert position_apres.etat.quantite == Decimal("13.000000")
        assert position_apres.etat.capital_net_investi == Decimal("200.00")
        assert position_apres.etat.prix_de_revient == Decimal("15.384615")
        assert position_apres.historique_incomplet is False

    def test_le_moteur_ne_signale_plus_de_prix_a_completer(self):
        operations = [titres_recus()]

        completion = completer_les_prix(operations, fournisseur({ACTIF: [cours(JOUR, "10.00")]}))
        apres = Portefeuille.construire(completion.operations)

        assert [signalement.categorie for signalement in apres.signalements] == []
