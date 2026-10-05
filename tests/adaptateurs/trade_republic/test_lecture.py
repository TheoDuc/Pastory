"""Lecture au format pivot : chaque type traité, et chaque forme refusée.

Les montants attendus se refont à la main : ils sont écrits à côté de chaque fabrique de
`export_fictif.py`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from pastory.adaptateurs.trade_republic.depot import lire_dossier
from pastory.adaptateurs.trade_republic.lecture import Lecteur
from pastory.pivot.operation import Poche, Provenance, TypeOperation
from pastory.pivot.validation import controler
from pastory.reglages import MouvementPea, Sens
from tests.adaptateurs.trade_republic import export_fictif as fictif


def lire(tmp_path, *lignes):
    fictif.deposer(tmp_path, list(lignes))
    return Lecteur().lire(lire_dossier(tmp_path))


def une_operation(tmp_path, ligne):
    rapport = lire(tmp_path, ligne)
    assert rapport.signalements == [], rapport.resume()
    assert rapport.anomalies == [], rapport.resume()
    (operation,) = rapport.operations
    return operation


class TestAchat:
    def test_un_plan_d_epargne_en_pea(self, tmp_path):
        operation = une_operation(tmp_path, fictif.achat_plan_epargne())

        assert operation.type is TypeOperation.ACHAT
        assert operation.nature_source == "plan_epargne"
        assert operation.actif == fictif.ETF
        assert operation.poche is Poche.PEA
        assert (operation.quantite, operation.prix_unitaire) == (Decimal(2), Decimal(25))
        assert operation.montant_brut == Decimal("50.00")
        assert (operation.frais, operation.taxes) == (Decimal(0), Decimal(0))
        assert operation.nom_actif == "ETF Monde Fictif"

    def test_l_instant_est_en_temps_universel_et_le_jour_celui_de_la_colonne(self, tmp_path):
        operation = une_operation(tmp_path, fictif.achat_plan_epargne())
        assert operation.instant_utc == datetime(2026, 3, 2, 9, 15, 0, 123000, tzinfo=UTC)
        assert operation.date == date(2026, 3, 2)

    def test_un_ordre_au_cto_avec_frais_et_taxe(self, tmp_path):
        operation = une_operation(tmp_path, fictif.achat_ordre_cto())

        assert operation.nature_source == "ordre_ponctuel"
        assert operation.poche is Poche.CTO
        # Le brut se lit directement : les frais et la taxe sont à côté (§5.1).
        assert operation.montant_brut == Decimal("200.00")
        assert (operation.frais, operation.taxes) == (Decimal("1.00"), Decimal("0.20"))

    def test_le_montant_regle_reste_vide(self, tmp_path):
        # La banque ne le donne pas, et il n'est jamais recalculé (D-83).
        operation = une_operation(tmp_path, fictif.achat_ordre_cto())
        assert operation.montant_regle is None
        assert "montant_regle" not in operation.provenance

    def test_toutes_les_valeurs_sont_des_donnees_sauf_la_nature(self, tmp_path):
        operation = une_operation(tmp_path, fictif.achat_ordre_cto())
        textes = {champ for champ, p in operation.provenance.items() if p is Provenance.TEXTE}
        assert textes == {"nature_source"}
        assert operation.provenance["montant_brut"] is Provenance.DONNEE

    def test_une_crypto_va_dans_la_poche_crypto(self, tmp_path):
        operation = une_operation(tmp_path, fictif.achat_crypto())
        assert operation.poche is Poche.CRYPTO
        assert operation.actif == fictif.CRYPTO

    def test_un_ordre_execute_en_deux_fois_donne_deux_operations(self, tmp_path):
        # Deux lignes au même prix, à des instants différents : pytr n'en donnait qu'une.
        moitie = {"shares": "2.0000000000", "amount": "-100.00", "fee": "-1.00", "tax": ""}
        rapport = lire(
            tmp_path,
            fictif.achat_ordre_cto(**moitie),
            fictif.achat_ordre_cto(**(moitie | {"fee": ""}), datetime="2026-03-05T14:30:01.000Z"),
        )
        assert rapport.anomalies == []
        assert sum(o.quantite for o in rapport.operations) == Decimal(4)
        assert sum(o.montant_brut for o in rapport.operations) == Decimal("200.00")
        assert sum(o.frais for o in rapport.operations) == Decimal("1.00")


class TestVente:
    def test_une_vente_partielle(self, tmp_path):
        operation = une_operation(tmp_path, fictif.vente())

        assert operation.type is TypeOperation.VENTE
        # La quantité est négative dans l'export ; le pivot n'a que des nombres positifs.
        assert operation.quantite == Decimal(1)
        assert operation.montant_brut == Decimal("80.00")
        assert operation.frais == Decimal("1.00")


class TestVersements:
    def test_un_dividende(self, tmp_path):
        operation = une_operation(tmp_path, fictif.dividende())

        assert operation.type is TypeOperation.DIVIDENDE
        assert operation.nature_source == "dividende_especes"
        assert operation.quantite == Decimal(4)
        assert operation.prix_unitaire is None
        assert operation.montant_brut == Decimal("10.00")
        assert operation.taxes == Decimal("3.00")

    def test_un_dividende_en_dollars_est_controle_par_le_change(self, tmp_path):
        # 12 $ × 0,90 = 10,80 € : le montant en euros découle bien du montant versé.
        operation = une_operation(tmp_path, fictif.dividende_en_dollars())
        assert operation.montant_brut == Decimal("10.80")
        assert operation.devise == "EUR"

    def test_un_change_qui_ne_tombe_pas_juste_est_une_anomalie(self, tmp_path):
        rapport = lire(tmp_path, fictif.dividende_en_dollars(fx_rate="0.950000"))
        (anomalie,) = rapport.anomalies
        assert anomalie.regle == "change"
        assert "11.40" in anomalie.message
        assert len(rapport.operations) == 1

    def test_une_distribution_de_capital(self, tmp_path):
        operation = une_operation(tmp_path, fictif.distribution_capital())
        assert operation.type is TypeOperation.DISTRIBUTION_CAPITAL
        assert operation.nature_source == "distribution_capital"
        assert operation.montant_brut == Decimal("2.00")


class TestMouvementsPea:
    """Les mouvements d'espèces du PEA, d'où se lit sa date d'ouverture (D-59, D-86)."""

    def test_versements_primes_et_retraits_sont_releves_dans_l_ordre(self, tmp_path):
        rapport = lire(
            tmp_path,
            fictif.versement_pea(datetime="2026-04-01T07:00:00.000Z", date="2026-04-01"),
            fictif.versement_pea(
                datetime="2026-02-01T07:00:00.000Z", date="2026-02-01", type="PEA_MARKETING"
            ),
            fictif.versement_pea(
                datetime="2026-03-01T07:00:00.000Z", date="2026-03-01", type="TRANSFER_OUT",
                amount="-10.00",
            ),
        )
        assert rapport.mouvements_pea == [
            MouvementPea(date(2026, 2, 1), Sens.ENTREE),
            MouvementPea(date(2026, 3, 1), Sens.SORTIE),
            MouvementPea(date(2026, 4, 1), Sens.ENTREE),
        ]

    def test_un_mouvement_sur_le_compte_titres_ne_compte_pas(self, tmp_path):
        rapport = lire(tmp_path, fictif.versement_pea(account_type="DEFAULT"))
        assert rapport.mouvements_pea == []

    def test_un_autre_type_d_especes_sur_le_pea_ne_compte_pas(self, tmp_path):
        rapport = lire(tmp_path, fictif.versement_pea(type="INTEREST_PAYMENT"))
        assert rapport.mouvements_pea == []

    def test_le_montant_n_est_jamais_lu(self, tmp_path):
        rapport = lire(tmp_path, fictif.versement_pea(amount="pas un nombre"))
        assert rapport.mouvements_pea == [MouvementPea(date(2026, 1, 2), Sens.ENTREE)]
        assert rapport.signalements == []


class TestFormesJamaisVues:
    """Une forme jamais vue n'est pas interprétée : elle est un trou affiché."""

    @pytest.mark.parametrize(
        ("ligne", "categorie"),
        [
            # Une extourne de dividende, vue chez d'autres utilisateurs (§5.3).
            (
                fictif.dividende(amount="-10.000000", tax="3.000000"),
                "annulation non interprétée",
            ),
            (fictif.achat_ordre_cto(fee="1.00"), "forme jamais vue"),
            (fictif.achat_ordre_cto(tax="0.20"), "forme jamais vue"),
            (fictif.achat_ordre_cto(shares="-4.0000000000"), "forme jamais vue"),
            (fictif.achat_ordre_cto(amount="200.00"), "forme jamais vue"),
            (fictif.achat_ordre_cto(price=""), "forme jamais vue"),
            (fictif.vente(shares="1.0000000000"), "forme jamais vue"),
            (fictif.dividende(price="2.5000000000"), "forme jamais vue"),
            (fictif.dividende(shares=""), "forme jamais vue"),
            (
                fictif.achat_ordre_cto(original_amount="220.00", fx_rate="0.909"),
                "forme jamais vue",
            ),
            (fictif.dividende_en_dollars(original_currency=""), "forme jamais vue"),
            # Une obligation : son montant inclut les intérêts courus.
            (fictif.achat_ordre_cto(asset_class="BOND"), "classe d'actif non prise en charge"),
            (fictif.achat_ordre_cto(asset_class=""), "classe d'actif non prise en charge"),
            (fictif.achat_plan_epargne(account_type="JUNIOR"), "poche indéterminable"),
            (fictif.achat_crypto(account_type="PEA"), "poche indéterminable"),
            (fictif.dividende(currency="USD"), "devise étrangère"),
            (fictif.achat_plan_epargne(amount="cinquante"), "valeur illisible"),
            (fictif.achat_plan_epargne(datetime="2026-03-02T09:15:00"), "horodatage illisible"),
            (fictif.achat_plan_epargne(date="02/03/2026"), "date illisible"),
            (fictif.achat_plan_epargne(symbol=""), "actif absent"),
        ],
    )
    def test_elle_n_est_pas_produite_et_le_rapport_dit_pourquoi(self, tmp_path, ligne, categorie):
        rapport = lire(tmp_path, ligne)

        assert rapport.operations == []
        assert rapport.operations_non_produites == 1
        (signalement,) = rapport.signalements
        assert signalement.categorie == categorie
        assert signalement.ou == "Exportation de transactions.csv, ligne 2"


class TestCeQueLaRelectureATrouve:
    """Les défauts trouvés par la relecture indépendante de l'étape, un test chacun."""

    def test_une_annulation_de_dividende_dit_que_les_versements_sont_surestimes(self, tmp_path):
        # Une correction s'écrit « original, annulation, nouvelle ligne » : refuser la seule
        # annulation laisse l'original compté. Ce n'est pas un trou, c'est un excès.
        rapport = lire(
            tmp_path,
            fictif.dividende(),
            fictif.dividende(amount="-10.000000", tax="3.000000"),
        )

        assert len(rapport.operations) == 1
        (signalement,) = rapport.signalements
        assert signalement.categorie == "annulation non interprétée"
        assert "SURESTIMÉS" in signalement.message

    def test_un_equivalent_de_dividende_doit_s_annoncer_comme_distribution(self, tmp_path):
        # Le code dit « équivalent de dividende » : sans la mention de la banque, ce peut
        # être un revenu, qui ne se calcule pas comme un remboursement de capital (Q-07).
        rapport = lire(
            tmp_path, fictif.distribution_capital(description="Dividend equivalent payment")
        )

        assert rapport.operations == []
        (signalement,) = rapport.signalements
        assert signalement.categorie == "nature non confirmée"

    def test_un_decalage_horaire_est_converti_en_temps_universel(self, tmp_path):
        operation = une_operation(
            tmp_path, fictif.achat_plan_epargne(datetime="2026-03-02T10:15:00.123+01:00")
        )

        assert operation.instant_utc == datetime(2026, 3, 2, 9, 15, 0, 123000, tzinfo=UTC)
        assert operation.instant_utc.utcoffset() == timedelta(0)

    def test_un_texte_qui_n_est_pas_un_code_n_est_jamais_recopie(self, tmp_path):
        # Une colonne décalée peut contenir un nom à la place d'un code.
        rapport = lire(tmp_path, fictif.achat_plan_epargne(account_type="Camille Fictif"))

        (signalement,) = rapport.signalements
        assert "Camille" not in signalement.message
        assert "(illisible)" in signalement.message

    def test_le_change_tolere_l_arrondi_du_taux_sur_un_gros_montant(self, tmp_path):
        # 2 000 $ à un taux affiché 0,9234 : le taux exact (0,92344) a donné 1 846,88 €. Huit
        # centimes d'écart, que l'arrondi du taux explique : 2 000 × 0,00005 = 0,10 €.
        une_operation(
            tmp_path,
            fictif.dividende_en_dollars(
                original_amount="2000.00",
                fx_rate="0.9234",
                amount="1846.880000",
                tax="-554.060000",
            ),
        )

    def test_un_change_faux_reste_signale_sur_un_gros_montant(self, tmp_path):
        rapport = lire(
            tmp_path,
            fictif.dividende_en_dollars(
                original_amount="2000.00",
                fx_rate="0.9234",
                amount="1856.88",
                tax="-554.060000",
            ),
        )
        assert [anomalie.regle for anomalie in rapport.anomalies] == ["change"]


class TestEnsemble:
    def test_l_export_type(self, tmp_path):
        rapport = lire(tmp_path, *fictif.export_type())

        assert rapport.lignes_lues == 9
        assert rapport.par_type_d_operation() == {
            "achat": 3,
            "vente": 1,
            "dividende": 1,
            "distribution_capital": 1,
        }
        assert rapport.especes_par_type == {
            "CASH/CARD_TRANSACTION": 1,
            "CASH/TRANSFER_INSTANT_INBOUND": 1,
        }
        assert rapport.types_inconnus == {"CASH/BENEFITS_SAVEBACK": 1}
        assert rapport.anomalies == []
        assert rapport.operations_non_produites == 0

    def test_les_operations_sont_remises_dans_l_ordre_du_temps(self, tmp_path):
        rapport = lire(tmp_path, *fictif.export_type())
        instants = [operation.instant_utc for operation in rapport.operations]
        assert instants == sorted(instants)

    def test_l_ordre_se_lit_sur_l_instant_et_non_sur_le_texte(self, tmp_path):
        # « .1234Z » vient après « .123Z » dans le temps, mais avant dans l'ordre du texte.
        rapport = lire(
            tmp_path,
            fictif.achat_plan_epargne(datetime="2026-03-02T09:15:00.1234Z"),
            fictif.achat_plan_epargne(datetime="2026-03-02T09:15:00.123Z", amount="-50.00"),
        )
        premier, second = rapport.operations
        assert premier.instant_utc < second.instant_utc

    def test_chaque_operation_passe_les_controles_du_pivot(self, tmp_path):
        rapport = lire(tmp_path, *fictif.export_type())
        for operation in rapport.operations:
            assert controler(operation) == []

    def test_un_jour_qui_ne_correspond_pas_a_l_instant_est_une_anomalie(self, tmp_path):
        # 23 h 30 en temps universel, le 2 mars, c'est déjà le 3 mars à Paris (D-36).
        rapport = lire(
            tmp_path,
            fictif.achat_plan_epargne(datetime="2026-03-02T23:30:00.000Z", date="2026-03-02"),
        )
        assert [anomalie.regle for anomalie in rapport.anomalies] == ["date"]

    def test_la_classe_de_chaque_actif_est_gardee_pour_l_etape_suivante(self, tmp_path):
        rapport = lire(tmp_path, *fictif.export_type())
        assert rapport.classes_par_actif == {
            fictif.ETF: {"FUND"},
            fictif.ACTION: {"STOCK"},
            fictif.CRYPTO: {"CRYPTO"},
        }

    def test_une_description_inconnue_ne_change_aucun_chiffre(self, tmp_path):
        rapport = lire(tmp_path, fictif.achat_plan_epargne(description="Something new"))
        (operation,) = rapport.operations
        assert operation.nature_source == "non_reconnue"
        assert operation.montant_brut == Decimal("50.00")
        assert [s.categorie for s in rapport.signalements] == ["nature non reconnue"]

    def test_deux_versions_d_une_operation_sont_signalees(self, tmp_path):
        originale = fictif.achat_plan_epargne()
        fictif.deposer(tmp_path, [originale], nom="a.csv")
        fictif.deposer(tmp_path, [originale | {"amount": "-51.00"}], nom="b.csv")

        rapport = Lecteur().lire(lire_dossier(tmp_path))
        assert len(rapport.operations) == 1
        (signalement,) = rapport.signalements
        assert signalement.categorie == "deux versions d'une opération"
        assert signalement.ou == "b.csv, ligne 2"
