"""La répartition du portefeuille : chaque euro rangé, et rien de renormalisé (D-66 à D-69).

Le test qui compte le plus est `TestChaqueEuroEstRange` : si la somme des postes et des restes
ne fait pas exactement la valeur du portefeuille, un montant s'est évaporé, et aucun pourcentage
n'est fiable. Il est écrit avant les autres pour cette raison.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory.config.actifs import Configuration, ContenuActif, Declaration, TypeActif
from pastory.donnees_externes.composition import FournisseurDeCompositions
from pastory.moteur import diversification as dv
from pastory.moteur.portefeuille import Portefeuille
from pastory.moteur.valorisation import valoriser
from pastory.parametres import referentiels as parametres_referentiels
from pastory.pivot.operation import Poche, TypeOperation
from tests.moteur.compositions_fictives import (
    ARRETE_LE,
    CompositionFictive,
    SourceDeCompositionFictive,
    action_en_direct,
    etf_mixte,
    etf_monde,
    etf_obligataire,
    etf_synthetique_pea,
    parts,
)
from tests.moteur.cours_fictifs import SourceFixe, cours_constant
from tests.moteur.operations_fictives import operation

AU = Date(2026, 9, 30)

ETF = "XX0000000ETF"
OBLIG = "XX0000000OBL"
CRYPTO = "BTC"
ACTION = "XX0000000ACT"
INCONNU = "XX0000000INC"
ETF_2 = "XX0000000ET2"


@pytest.fixture
def referentiels():
    """Les vrais référentiels livrés avec l'application : ce sont eux qu'on veut éprouver."""
    return parametres_referentiels.charger_tout()


def _achat(actif: str, quantite: str, prix: str, poche: Poche = Poche.CTO):
    return operation(
        TypeOperation.ACHAT,
        horodatage="2026-01-05 09:00",
        actif=actif,
        poche=poche,
        quantite=quantite,
        prix_unitaire=prix,
    )


def _valorisation(*achats, cours: dict[str, str]):
    """Un portefeuille valorisé à `AU`, avec un cours fixe par actif."""
    series: dict[str, dict[Date, str]] = {}
    for actif, valeur in cours.items():
        series |= cours_constant(actif, valeur, Date(2026, 1, 1), AU)
    portefeuille = Portefeuille.construire(list(achats)).au(AU)
    return valoriser(portefeuille, AU, SourceFixe(series))


class TestChaqueEuroEstRange:
    """La propriété qui garantit tout le reste : postes + restes = valeur du portefeuille."""

    def test_les_trois_rubriques_somment_a_la_valeur_totale(self, referentiels):
        # 10 parts a 100 EUR d'ETF, 5 a 100 EUR d'obligataire, 2 a 100 EUR de crypto, et un
        # actif dont personne ne connait la composition : 1 000 + 500 + 200 + 300 = 2 000 EUR.
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(OBLIG, "5", "100.00"),
            _achat(CRYPTO, "2", "100.00", poche=Poche.CRYPTO),
            _achat(INCONNU, "3", "100.00"),
            cours={ETF: "100.00", OBLIG: "100.00", CRYPTO: "100.00", INCONNU: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde(), OBLIG: etf_obligataire()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert valorisation.total.valeur == Decimal("2000.00")
        for repartition in resultat.repartitions:
            total = (
                repartition.attribue
                + repartition.non_attribue
                + repartition.hors_perimetre
                + repartition.hors_classification
                + repartition.non_couvert
            )
            assert total == Decimal("2000.00"), repartition.rubrique

    def test_un_actif_sans_composition_est_non_couvert_et_nomme(self, referentiels):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(INCONNU, "5", "100.00"),
            cours={ETF: "100.00", INCONNU: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.non_couvert == Decimal("500.00")
        assert resultat.pays.actifs_non_couverts == (INCONNU,)
        assert not resultat.pays.complete


class TestLesPourcentagesNeSontJamaisRenormalises:
    def test_un_poids_manquant_devient_du_non_attribue(self, referentiels):
        # L'ETF synthétique n'attribue que 90 % de ses pays : 70 + 20. Les 10 % restants
        # doivent rester visibles, et non gonfler les États-Unis.
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: etf_synthetique_pea()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        montants = {poste.code: poste.montant for poste in resultat.pays.postes}
        assert montants == {"US": Decimal("700.00"), "DE": Decimal("200.00")}
        assert resultat.pays.non_attribue == Decimal("100.00")
        assert resultat.pays.pour_cent(montants["US"]) == Decimal("70.00")

    def test_le_pourcentage_se_rapporte_a_la_valeur_totale_et_non_aux_postes(self, referentiels):
        # La moitié du portefeuille n'est pas couverte : les États-Unis pèsent 30 % du
        # portefeuille, et non 60 % comme le donnerait un total ramené aux seuls postes.
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(INCONNU, "10", "100.00"),
            cours={ETF: "100.00", INCONNU: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        etats_unis = next(poste for poste in resultat.pays.postes if poste.code == "US")
        assert resultat.pays.pour_cent(etats_unis.montant) == Decimal("30.00")


class TestLObligataireResteHorsDeLaGeographieEtDesSecteurs:
    """D-68 : « pays » peut vouloir dire devise d'émission, et « secteur » veut dire Trésor."""

    def test_un_etf_obligataire_est_hors_perimetre_et_non_pas_non_couvert(self, referentiels):
        valorisation = _valorisation(_achat(OBLIG, "5", "100.00"), cours={OBLIG: "100.00"})
        source = SourceDeCompositionFictive({OBLIG: etf_obligataire()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.hors_perimetre == Decimal("500.00")
        assert resultat.pays.non_couvert == Decimal("0.00")
        assert resultat.pays.postes == ()

    def test_il_compte_normalement_dans_la_repartition_par_classe_d_actifs(self, referentiels):
        valorisation = _valorisation(_achat(OBLIG, "5", "100.00"), cours={OBLIG: "100.00"})
        source = SourceDeCompositionFictive({OBLIG: etf_obligataire()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        libelles = {poste.libelle: poste.montant for poste in resultat.classes.postes}
        assert libelles == {"Obligations": Decimal("500.00")}

    def test_un_fonds_mixte_separe_sa_part_actions_du_reste(self, referentiels):
        # 60 % d'actions, 40 % d'obligations, sur 1 000 EUR : 600 EUR entrent dans la
        # géographie, 400 EUR en sortent.
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: etf_mixte()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.attribue == Decimal("600.00")
        assert resultat.pays.hors_perimetre == Decimal("400.00")
        assert resultat.pays.non_attribue == Decimal("0.00")


class TestLaCryptoEstAPart:
    def test_elle_n_est_ni_non_couverte_ni_rangee_dans_un_secteur(self, referentiels):
        valorisation = _valorisation(
            _achat(CRYPTO, "2", "100.00", poche=Poche.CRYPTO), cours={CRYPTO: "100.00"}
        )
        source = SourceDeCompositionFictive({})

        resultat = dv.diversifier(valorisation, source, referentiels)

        for repartition in resultat.repartitions:
            assert repartition.hors_classification == Decimal("200.00"), repartition.rubrique
            assert repartition.non_couvert == Decimal("0.00")
            assert repartition.postes == ()

    def test_aucune_source_n_est_interrogee_pour_une_crypto(self, referentiels):
        valorisation = _valorisation(
            _achat(CRYPTO, "2", "100.00", poche=Poche.CRYPTO), cours={CRYPTO: "100.00"}
        )
        source = SourceDeCompositionFictive({})

        dv.diversifier(valorisation, source, referentiels)

        assert CRYPTO not in source.demandes


class TestUnCodeInconnuEstAfficheJamaisRange:
    """Règle 5 de CLAUDE.md, transposée aux codes de pays et de secteur."""

    def test_un_pays_inconnu_du_referentiel_garde_son_code_et_sa_zone_est_dite(
        self, referentiels
    ):
        composition = CompositionFictive(
            pays=parts(ZZ="100"), secteurs=parts(technology="100"), classes=parts(stock="100")
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        poste = resultat.pays.postes[0]
        assert poste.code == "ZZ"
        assert poste.libelle == "ZZ"
        assert not poste.reconnu
        assert poste.zone == parametres_referentiels.ZONE_INCONNUE
        assert poste.montant == Decimal("1000.00")

    def test_un_secteur_inconnu_est_conserve_et_signale_comme_non_reconnu(self, referentiels):
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(intelligence_artificielle="100"),
            classes=parts(stock="100"),
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert [poste.code for poste in resultat.secteurs.postes_non_reconnus] == [
            "intelligence_artificielle"
        ]
        assert resultat.secteurs.non_attribue == Decimal("0.00")


class TestLesZones:
    def test_les_pays_sont_regroupes_dans_l_ordre_des_rangs(self, referentiels):
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: etf_monde()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        zones = [(zone.libelle, montant) for zone, montant, _ in resultat.pays.par_zone()]
        assert zones == [
            ("Amérique du Nord", Decimal("600.00")),
            ("Europe développée", Decimal("300.00")),
            ("Japon", Decimal("100.00")),
        ]


class TestLesFondsSynthetiquesSontSignales:
    def test_un_fonds_a_swap_est_nomme_pour_que_l_ecart_soit_comprehensible(self, referentiels):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00", poche=Poche.PEA), cours={ETF: "100.00"}
        )
        source = SourceDeCompositionFictive({ETF: etf_synthetique_pea()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.actifs_synthetiques == (ETF,)


class TestLesDatesDArrete:
    def test_la_fourchette_des_arretes_est_rendue(self, referentiels):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(OBLIG, "5", "100.00"),
            cours={ETF: "100.00", OBLIG: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde(), OBLIG: etf_obligataire()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.arrete_du == Date(2026, 8, 31)
        assert resultat.arrete_au == Date(2026, 9, 22)
        assert resultat.intitules_de_date == ("date annoncée par la source fictive",)


class TestUneRepartitionQuiDepasseLaPartActionsEstSignalee:
    """Prêt de titres, ou source qui exprime ses poids sur la seule poche actions."""

    def test_le_depassement_est_dit_et_rien_n_est_rabote(self, referentiels):
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(technology="100"),
            classes=parts(stock="50", bond="50"),
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.attribue == Decimal("1000.00")
        assert resultat.pays.non_attribue == Decimal("0.00")
        messages = [signalement.message for signalement in resultat.signalements]
        assert any("dépasse donc la valeur du portefeuille" in message for message in messages)


class TestUneActionEnDirectEntreDansLesDeuxRepartitions:
    """D-62 : l'achat d'actions à l'unité est courant, la répartition doit savoir les traiter."""

    def test_son_pays_et_son_secteur_comptent(self, referentiels):
        valorisation = _valorisation(_achat(ACTION, "4", "50.00"), cours={ACTION: "50.00"})
        source = SourceDeCompositionFictive({ACTION: action_en_direct()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert [(poste.libelle, poste.montant) for poste in resultat.pays.postes] == [
            ("France", Decimal("200.00"))
        ]
        assert [(poste.libelle, poste.montant) for poste in resultat.secteurs.postes] == [
            ("Consommation cyclique", Decimal("200.00"))
        ]


class TestUnPortefeuilleSansRien:
    def test_aucune_position_ne_fait_pas_echouer(self, referentiels):
        valorisation = _valorisation(cours={})
        source = SourceDeCompositionFictive({})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.postes == ()
        assert resultat.pays.base == Decimal("0.00")
        assert resultat.pays.pour_cent(Decimal("0")) is None
        assert resultat.arrete_du is None


class TestLesCasDuCahierDeVerification:
    """Les pourcentages écrits dans `docs/verification/etape-7.md`, épinglés ici.

    Le propriétaire refait ces calculs à la main. Si un chiffre du programme changeait sans que
    le cahier soit corrigé, ces tests tomberaient — c'est leur seule raison d'être.
    """

    def test_a3_un_etf_obligataire_reduit_la_part_des_pays_sans_changer_leur_montant(
        self, referentiels
    ):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(OBLIG, "5", "100.00"),
            cours={ETF: "100.00", OBLIG: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde(), OBLIG: etf_obligataire()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        classes = {poste.libelle: resultat.classes.pour_cent(poste.montant)
                   for poste in resultat.classes.postes}
        assert classes == {"Actions": Decimal("66.67"), "Obligations": Decimal("33.33")}

        etats_unis = next(poste for poste in resultat.pays.postes if poste.code == "US")
        assert etats_unis.montant == Decimal("600.00")
        assert resultat.pays.pour_cent(etats_unis.montant) == Decimal("40.00")
        assert resultat.pays.pour_cent(resultat.pays.hors_perimetre) == Decimal("33.33")

    def test_a4_un_fonds_mixte_isole_sa_part_actions(self, referentiels):
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: etf_mixte()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.pour_cent(resultat.pays.attribue) == Decimal("60.00")
        assert resultat.pays.pour_cent(resultat.pays.hors_perimetre) == Decimal("40.00")

    def test_a5_la_crypto_pese_seize_virgule_soixante_sept_pour_cent(self, referentiels):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(CRYPTO, "2", "100.00", poche=Poche.CRYPTO),
            cours={ETF: "100.00", CRYPTO: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.hors_classification == Decimal("200.00")
        assert resultat.pays.pour_cent(resultat.pays.hors_classification) == Decimal("16.67")

    def test_a6_un_actif_inconnu_pese_vingt_trois_virgule_zero_huit_pour_cent(self, referentiels):
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(INCONNU, "3", "100.00"),
            cours={ETF: "100.00", INCONNU: "100.00"},
        )
        source = SourceDeCompositionFictive({ETF: etf_monde()})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert resultat.pays.pour_cent(resultat.pays.non_couvert) == Decimal("23.08")
        france = next(poste for poste in resultat.pays.postes if poste.code == "FR")
        assert resultat.pays.pour_cent(france.montant) == Decimal("23.08")


class TestLesQuatreDefautsDeLaRelecture:
    """Les quatre défauts trouvés par la relecture indépendante, chacun avec son test."""

    def test_deux_ecritures_d_un_meme_poste_ne_font_qu_une_ligne(self, referentiels):
        # La source répond « stock 88 » et « preferred 2 » : ce sont deux écritures de la même
        # classe d'actifs. Sans passer par le référentiel, l'écran affichait « Actions 880,00 »
        # puis « Actions 20,00 ».
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(consumer_defense="50", consumer_defensive="50"),
            classes=parts(stock="88", preferred="2", bond="5", convertible="5"),
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        classes = [(poste.libelle, poste.montant) for poste in resultat.classes.postes]
        assert classes == [
            ("Actions", Decimal("900.00")),
            ("Obligations", Decimal("100.00")),
        ]
        secteurs = [(poste.libelle, poste.montant) for poste in resultat.secteurs.postes]
        assert secteurs == [("Consommation de base", Decimal("1000.00"))]

    def test_une_part_actions_au_dela_de_cent_ne_rend_pas_le_hors_perimetre_negatif(
        self, referentiels
    ):
        # Le prêt de titres fait légitimement dépasser 100 %. Sans plafond, « hors périmètre »
        # devenait négatif, le filtre d'affichage le cachait, et la somme des lignes dépassait
        # la valeur du portefeuille — l'invariant même que le CSV promet.
        composition = CompositionFictive(
            pays=parts(US="100"),
            secteurs=parts(technology="100"),
            classes=parts(stock="100", preferred="3"),
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        # Aucun montant negatif, et aucun montant cache : c'est ce qui etait casse.
        for repartition in resultat.repartitions:
            assert repartition.hors_perimetre >= Decimal("0.00"), repartition.rubrique
            assert repartition.non_attribue >= Decimal("0.00"), repartition.rubrique

        # La geographie et les secteurs retombent juste : la part actions est plafonnee a 100 %.
        for repartition in (resultat.pays, resultat.secteurs):
            total = (
                repartition.attribue
                + repartition.non_attribue
                + repartition.hors_perimetre
                + repartition.hors_classification
                + repartition.non_couvert
            )
            assert total == Decimal("1000.00"), repartition.rubrique

        # La repartition par classe d'actifs, elle, depasse : la source annonce 103 %, et on ne
        # rabote pas (D-69). Le depassement doit donc etre explique, au centime.
        assert resultat.classes.attribue == Decimal("1030.00")
        messages = [signalement.message for signalement in resultat.signalements]
        assert any("de 30,00" in message for message in messages), messages


class TestLeContenuDeclareRangeLActifSansLeDireManquant:
    """D-71 : un ETF obligataire ou de matières premières n'a pas de pays, et ce n'est pas un trou.

    Le défaut corrigé ici : ces actifs s'affichaient « non couvert : composition inconnue », ce qui
    est **faux**. Ils ont bien une composition — elle n'a simplement ni pays ni secteur.
    """

    def _valorisation_et_source(self, contenu: str):
        declaration = Declaration(ticker="T1.DE", devise="EUR", type=TypeActif.ETF)
        declaration = replace(declaration, contenu=ContenuActif(contenu))
        fournisseur = FournisseurDeCompositions(
            cache=_CacheVide(),
            actifs=Configuration(declarations={ETF: declaration}),
            aujourd_hui=AU,
        )
        valorisation = _valorisation(_achat(ETF, "5", "100.00"), cours={ETF: "100.00"})
        return valorisation, fournisseur

    def test_un_contenu_obligations_compte_en_obligations_et_sort_de_la_geographie(
        self, referentiels
    ):
        valorisation, fournisseur = self._valorisation_et_source("obligations")

        resultat = dv.diversifier(valorisation, fournisseur, referentiels)

        assert [(poste.libelle, poste.montant) for poste in resultat.classes.postes] == [
            ("Obligations", Decimal("500.00"))
        ]
        assert resultat.pays.non_couvert == Decimal("0.00")
        assert [
            (poste.libelle, poste.montant) for poste in resultat.pays.hors_perimetre_postes
        ] == [("Obligations", Decimal("500.00"))]

    def test_un_contenu_matieres_premieres_a_sa_propre_ligne_nommee(self, referentiels):
        valorisation, fournisseur = self._valorisation_et_source("matieres_premieres")

        resultat = dv.diversifier(valorisation, fournisseur, referentiels)

        assert [(poste.libelle, poste.montant) for poste in resultat.classes.postes] == [
            ("Matières premières", Decimal("500.00"))
        ]
        assert [
            poste.libelle for poste in resultat.secteurs.hors_perimetre_postes
        ] == ["Matières premières"]
        assert resultat.secteurs.non_couvert == Decimal("0.00")

    def test_l_invariant_tient_toujours_au_centime(self, referentiels):
        valorisation, fournisseur = self._valorisation_et_source("matieres_premieres")

        resultat = dv.diversifier(valorisation, fournisseur, referentiels)

        for repartition in resultat.repartitions:
            total = (
                repartition.attribue
                + repartition.non_attribue
                + repartition.hors_perimetre
                + repartition.hors_classification
                + repartition.non_couvert
            )
            assert total == Decimal("500.00"), repartition.rubrique


class TestDeuxClassesHorsActionsSontDeuxLignesDistinctes:
    def test_obligations_et_matieres_premieres_ne_sont_pas_fondues(self, referentiels):
        # Un seul fourre-tout ferait passer de l'or pour de la dette.
        composition = CompositionFictive(
            pays=parts(US="50"),
            secteurs=parts(technology="50"),
            classes=parts(stock="50", bond="30", commodity="20"),
        )
        valorisation = _valorisation(_achat(ETF, "10", "100.00"), cours={ETF: "100.00"})
        source = SourceDeCompositionFictive({ETF: composition})

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert [
            (poste.libelle, poste.montant) for poste in resultat.pays.hors_perimetre_postes
        ] == [
            ("Obligations", Decimal("300.00")),
            ("Matières premières", Decimal("200.00")),
        ]
        assert resultat.pays.hors_perimetre == Decimal("500.00")


class _CacheVide:
    """Un cache qui ne sait rien : la déclaration de l'utilisateur doit suffire."""

    def lire(self, actif):
        return None

    def ecrire(self, composition):
        raise AssertionError("rien ne doit être mis en cache : la déclaration passe avant")

    def oublier(self, actif=None):
        return []


class TestUneDeclarationNAPasDeDateDArrete:
    """Sinon la fourchette affichée en tête serait tirée jusqu'à aujourd'hui (D-71)."""

    def test_la_fourchette_ignore_les_compositions_declarees(self, referentiels):
        declaration = replace(
            Declaration(ticker="T2.DE", devise="EUR", type=TypeActif.ETF),
            contenu=ContenuActif.OBLIGATIONS,
        )
        fournisseur = FournisseurDeCompositions(
            cache=_CacheVide(),
            actifs=Configuration(declarations={OBLIG: declaration}),
            aujourd_hui=AU,
        )
        source = _SourceMixte(
            declaree=fournisseur, table={ETF: etf_monde()}
        )
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(OBLIG, "5", "100.00"),
            cours={ETF: "100.00", OBLIG: "100.00"},
        )

        resultat = dv.diversifier(valorisation, source, referentiels)

        # L'ETF a un arrêté au 31/08 ; la déclaration, elle, n'en a pas.
        assert resultat.arrete_du == ARRETE_LE
        assert resultat.arrete_au == ARRETE_LE
        assert resultat.declarees_a_la_main == (OBLIG,)


class _SourceMixte:
    """Une source qui rend des compositions fictives, et une déclarée pour un actif."""

    def __init__(self, declaree, table):
        self.declaree = declaree
        self.table = table

    def composition(self, actif):
        trouvee = self.declaree.composition(actif)
        return trouvee if trouvee is not None else self.table.get(actif)


class TestLOrigineDeChaqueActifEstConnue:
    """Le champ ajouté par l'étape 8 bis : source **et** règle de pays, par actif (D-66, D-72).

    C'est la condition posée par D-72 pour qu'une source de secours soit permise. Avant, la
    règle de pays était connue du code mais **portée par aucune donnée** : le rapport n'en disait
    qu'une phrase générique, sans jamais dire quel actif relevait de quelle règle. Or l'écart
    mesuré entre deux règles, sur un même fonds à une même date, est de 2 points sur les
    États-Unis et d'un facteur huit sur l'Irlande.
    """

    def test_chaque_actif_porte_sa_source_et_sa_regle(self, referentiels):
        deux = SourceDeCompositionFictive(
            table={
                ETF: replace(
                    etf_monde(), source="source principale", regle_de_pays="pays d'activité"
                ),
                ETF_2: replace(
                    etf_monde(), source="source de secours", regle_de_pays="pays de l'indice"
                ),
            }
        )
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(ETF_2, "10", "100.00"),
            cours={ETF: "100.00", ETF_2: "100.00"},
        )

        resultat = dv.diversifier(valorisation, deux, referentiels)

        par_actif = {origine.actif: origine for origine in resultat.origines}
        assert par_actif[ETF].source == "source principale"
        assert par_actif[ETF].regle_de_pays == "pays d'activité"
        assert par_actif[ETF_2].source == "source de secours"
        assert par_actif[ETF_2].regle_de_pays == "pays de l'indice"

    def test_les_origines_sont_triees_par_actif(self, referentiels):
        """Deux exécutions doivent donner le même ordre, sinon l'écran bouge sans raison."""
        deux = SourceDeCompositionFictive(table={ETF: etf_monde(), ETF_2: etf_monde()})
        valorisation = _valorisation(
            _achat(ETF_2, "10", "100.00"),
            _achat(ETF, "10", "100.00"),
            cours={ETF: "100.00", ETF_2: "100.00"},
        )

        resultat = dv.diversifier(valorisation, deux, referentiels)

        assert [o.actif for o in resultat.origines] == sorted(o.actif for o in resultat.origines)

    def test_une_crypto_n_a_pas_d_origine_a_afficher(self, referentiels):
        """Elle n'a ni pays ni secteur : ce n'est pas une donnée manquante (D-68)."""
        source = SourceDeCompositionFictive(table={ETF: etf_monde()})
        valorisation = _valorisation(
            _achat(ETF, "10", "100.00"),
            _achat(CRYPTO, "1", "100.00", poche=Poche.CRYPTO),
            cours={ETF: "100.00", CRYPTO: "100.00"},
        )

        resultat = dv.diversifier(valorisation, source, referentiels)

        assert [o.actif for o in resultat.origines] == [ETF]
