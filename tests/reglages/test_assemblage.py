"""L'assemblage des réglages : la correction, sinon la valeur trouvée, sinon le trou (D-80).

Valeurs fictives (D-03).
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import Configuration, ContenuActif, Declaration, TypeActif
from pastory.config.fiscalite import ConfigurationFiscale
from pastory.pivot.operation import Poche
from pastory.reglages import (
    SOURCE_CORRECTION_ACTIFS,
    SOURCE_CORRECTION_FISCALITE,
    CeQueDitLaBanque,
    Cotation,
    MouvementPea,
    Origine,
    Sens,
    Trou,
    Trouvee,
)
from pastory.reglages.assemblage import EnLigne, assembler, lire_l_histoire_du_pea

ETF = "XX0000000001"
ACTION = "XX0000000002"
CRYPTO = "XYZ"

FIN_DE_L_EXPORT = Date(2026, 8, 1)
TROUVE_LE = Date(2026, 9, 1)


def banque(**champs) -> CeQueDitLaBanque:
    valeurs = {
        "source": "export de test",
        "date": FIN_DE_L_EXPORT,
        "types": {
            ETF: frozenset({TypeActif.ETF}),
            ACTION: frozenset({TypeActif.ACTION}),
            CRYPTO: frozenset({TypeActif.CRYPTO}),
        },
        "poches": {
            ETF: frozenset({Poche.PEA}),
            ACTION: frozenset({Poche.CTO}),
            CRYPTO: frozenset({Poche.CRYPTO}),
        },
        "noms": {ETF: "ETF Monde Fictif"},
        "mouvements_pea": (MouvementPea(Date(2026, 1, 2), Sens.ENTREE),),
        "jours_operations_pea": (Date(2026, 1, 3),),
    }
    valeurs.update(champs)
    return CeQueDitLaBanque(**valeurs)


def trouvee(valeur, source="source de test"):
    return Trouvee(valeur, Origine(source=source, date=TROUVE_LE, controle="contrôlé"))


COTATION_ETF = trouvee(Cotation("AAAA.DE", "EUR", "XETRA", "ETF Monde Fictif"))


class TestCeQueDitLaBanque:
    def test_le_type_vient_de_la_banque_avec_sa_source_et_sa_date(self):
        reglages = assembler(banque(), {}, Configuration())

        type_etf = reglages.actifs[ETF].type
        assert type_etf.valeur is TypeActif.ETF
        assert "asset_class" in type_etf.retenu.origine.source
        assert type_etf.retenu.origine.date == FIN_DE_L_EXPORT

    def test_deux_types_pour_un_meme_actif_ne_donnent_aucun_type(self):
        contradictoire = banque(
            types={ETF: frozenset({TypeActif.ETF, TypeActif.ACTION})}
        )
        reglage = assembler(contradictoire, {}, Configuration()).actifs[ETF].type

        assert reglage.valeur is None
        assert "plusieurs types" in reglage.trou.motif
        assert "action, etf" in reglage.trou.motif

    def test_tous_les_actifs_de_l_export_ont_leurs_reglages(self):
        assert set(assembler(banque(), {}, Configuration()).actifs) == {ETF, ACTION, CRYPTO}


class TestValeursTrouvees:
    def test_une_cotation_trouvee_s_applique(self):
        reglages = assembler(banque(), {ETF: EnLigne(cotation=COTATION_ETF)}, Configuration())

        declaration = reglages.configuration().declaration(ETF)
        assert declaration.ticker == "AAAA.DE"
        assert declaration.devise == "EUR"
        assert declaration.type is TypeActif.ETF

    def test_sans_cotation_le_motif_suit_jusqu_au_refus_du_cours(self):
        trou = Trou("aucune cotation en euros")
        configuration = assembler(
            banque(), {ETF: EnLigne(cotation=trou)}, Configuration()
        ).configuration()

        assert configuration.declaration(ETF).ticker is None
        assert configuration.sans_cotation[ETF] == "aucune cotation en euros"

    def test_hors_ligne_et_sans_rien_en_memoire_la_cotation_est_un_trou(self):
        reglages = assembler(banque(), {}, Configuration())
        assert "sans accès au réseau" in reglages.actifs[ETF].cotation.trou.motif

    def test_le_ter_ne_concerne_qu_un_etf(self):
        reglages = assembler(
            banque(), {ACTION: EnLigne(ter=trouvee(Decimal("0.20")))}, Configuration()
        )
        assert reglages.actifs[ACTION].ter is None

    def test_un_etf_sans_ter_trouve_est_un_trou_explique(self):
        reglage = assembler(banque(), {}, Configuration()).actifs[ETF].ter
        assert reglage.valeur is None
        assert "frais courants" in reglage.trou.motif

    def test_un_ter_trouve_s_applique(self):
        reglages = assembler(
            banque(), {ETF: EnLigne(ter=trouvee(Decimal("0.20")))}, Configuration()
        )
        assert reglages.configuration().declaration(ETF).ter_pour_cent == Decimal("0.20")

    def test_un_contenu_que_rien_n_annonce_n_est_pas_un_trou(self):
        # Sans contenu annoncé, la source de composition décide, comme avant (D-71).
        reglages = assembler(banque(), {}, Configuration())
        assert reglages.actifs[ETF].contenu is None
        assert all(nom != "contenu" for _, nom, _ in reglages.trous())

    def test_un_contenu_trouve_s_applique(self):
        reglages = assembler(
            banque(),
            {ETF: EnLigne(contenu=trouvee(ContenuActif.OBLIGATIONS))},
            Configuration(),
        )
        assert reglages.configuration().declaration(ETF).contenu is ContenuActif.OBLIGATIONS


class TestCorrections:
    def test_une_correction_l_emporte_et_le_dit(self):
        corrections = Configuration({ETF: Declaration(ticker="BBBB.PA", devise="EUR")})
        reglage = assembler(
            banque(), {ETF: EnLigne(cotation=COTATION_ETF)}, corrections
        ).actifs[ETF].cotation

        assert reglage.valeur.ticker == "BBBB.PA"
        assert reglage.retenu.origine.corrigee
        assert reglage.retenu.origine.source == SOURCE_CORRECTION_ACTIFS

    def test_la_valeur_trouvee_qu_une_correction_contredit_est_gardee_pour_etre_montree(self):
        corrections = Configuration({ETF: Declaration(ticker="BBBB.PA", devise="EUR")})
        reglage = assembler(
            banque(), {ETF: EnLigne(cotation=COTATION_ETF)}, corrections
        ).actifs[ETF].cotation

        assert reglage.ecarte == COTATION_ETF

    def test_une_correction_identique_a_la_source_n_ecarte_rien(self):
        # La place et le nom ne font pas partie de la correction : seuls le ticker et la devise
        # comptent pour dire si elle contredit la source.
        corrections = Configuration({ETF: Declaration(ticker="AAAA.DE", devise="EUR")})
        reglage = assembler(
            banque(), {ETF: EnLigne(cotation=COTATION_ETF)}, corrections
        ).actifs[ETF].cotation

        assert reglage.ecarte is None

    def test_une_correction_partielle_garde_le_reste_trouve(self):
        # Corriger le seul TER ne fait pas perdre la cotation trouvée.
        corrections = Configuration({ETF: Declaration(ter_pour_cent=Decimal("0.07"))})
        declaration = assembler(
            banque(),
            {ETF: EnLigne(cotation=COTATION_ETF, ter=trouvee(Decimal("0.20")))},
            corrections,
        ).configuration().declaration(ETF)

        assert declaration.ticker == "AAAA.DE"
        assert declaration.ter_pour_cent == Decimal("0.07")

    def test_un_type_corrige_l_emporte_sur_la_banque(self):
        corrections = Configuration({ETF: Declaration(type=TypeActif.ACTION)})
        reglage = assembler(banque(), {}, corrections).actifs[ETF].type

        assert reglage.valeur is TypeActif.ACTION
        assert reglage.ecarte.valeur is TypeActif.ETF

    def test_ce_qui_ne_se_trouve_jamais_seul_passe_tel_quel(self):
        corrections = Configuration(
            {ETF: Declaration(spread_pour_cent=Decimal("0.5"), secours="aucun")}
        )
        declaration = assembler(banque(), {}, corrections).configuration().declaration(ETF)

        assert declaration.spread_pour_cent == Decimal("0.5")
        assert declaration.secours == "aucun"


class TestOrphelines:
    def test_une_correction_qu_aucun_export_ne_contient_est_signalee(self):
        corrections = Configuration({"XF000ANCIEN": Declaration(ticker="ZZZ-EUR")})
        reglages = assembler(banque(), {}, corrections)

        assert reglages.orphelines == ("XF000ANCIEN",)
        assert "XF000ANCIEN" not in reglages.configuration().declarations


def entree(jour):
    return MouvementPea(jour, Sens.ENTREE)


def sortie(jour):
    return MouvementPea(jour, Sens.SORTIE)


class TestDateDuPea:
    def test_le_premier_credit_est_retenu_avec_sa_reserve(self):
        reglage = assembler(banque(), {}, Configuration()).premier_versement_pea

        assert reglage.valeur == Date(2026, 1, 2)
        assert "transféré" in reglage.retenu.origine.reserve
        assert "premier versement" in reglage.retenu.origine.source

    def test_un_retrait_avant_cinq_ans_clot_le_plan_et_le_credit_suivant_le_rouvre(self):
        # Le cas du propriétaire : prime d'ouverture, sortie six jours plus tard, seconde prime
        # le même jour, puis les versements. Il a confirmé la date de la réouverture.
        rouvert = banque(
            mouvements_pea=(
                entree(Date(2026, 6, 1)),
                sortie(Date(2026, 6, 7)),
                entree(Date(2026, 6, 7)),
                entree(Date(2026, 6, 16)),
            ),
            jours_operations_pea=(Date(2026, 6, 16),),
        )
        reglages = assembler(rouvert, {}, Configuration())

        assert reglages.premier_versement_pea.valeur == Date(2026, 6, 7)
        assert "clos par un retrait le 2026-06-07" in (
            reglages.premier_versement_pea.retenu.origine.controle
        )
        # La sortie qui a clos l'ancien plan n'est pas un retrait du plan en cours.
        assert reglages.retraits_pea == ()

    def test_un_retrait_apres_cinq_ans_ne_clot_pas_le_plan_mais_se_signale(self):
        ancien = banque(
            mouvements_pea=(entree(Date(2019, 1, 2)), sortie(Date(2025, 6, 1))),
            jours_operations_pea=(Date(2019, 1, 3),),
        )
        reglages = assembler(ancien, {}, Configuration())

        assert reglages.premier_versement_pea.valeur == Date(2019, 1, 2)
        assert reglages.retraits_pea == (Date(2025, 6, 1),)

    def test_la_duree_vient_de_l_appelant(self):
        # Avec une durée d'un an, la même sortie ne clôt plus rien.
        mouvements = (entree(Date(2024, 1, 2)), sortie(Date(2025, 6, 1)))
        histoire = lire_l_histoire_du_pea(mouvements, duree_avant_retrait_libre=1)
        assert histoire.ouverture == Date(2024, 1, 2)
        assert histoire.retraits == (Date(2025, 6, 1),)

    def test_un_titre_entre_avant_le_premier_versement_rend_la_date_inconnue(self):
        # Le plan est plus ancien que les exports : retenir la date serait inventer.
        anterieur = banque(jours_operations_pea=(Date(2025, 12, 1), Date(2026, 1, 3)))
        reglage = assembler(anterieur, {}, Configuration()).premier_versement_pea

        assert reglage.valeur is None
        assert "2025-12-01" in reglage.trou.motif

    def test_un_titre_d_un_plan_clos_ne_rend_pas_la_date_inconnue(self):
        rouvert = banque(
            mouvements_pea=(
                entree(Date(2026, 1, 2)), sortie(Date(2026, 3, 1)), entree(Date(2026, 4, 1))
            ),
            jours_operations_pea=(Date(2026, 1, 5), Date(2026, 4, 2)),
        )
        assert assembler(rouvert, {}, Configuration()).premier_versement_pea.valeur == Date(
            2026, 4, 1
        )

    def test_sans_versement_la_date_est_un_trou(self):
        reglage = assembler(
            banque(mouvements_pea=()), {}, Configuration()
        ).premier_versement_pea
        assert reglage.valeur is None

    def test_sans_pea_la_date_est_sans_objet(self):
        sans_pea = banque(
            poches={ACTION: frozenset({Poche.CTO})}, types={ACTION: frozenset({TypeActif.ACTION})}
        )
        assert assembler(sans_pea, {}, Configuration()).premier_versement_pea is None

    def test_la_date_corrigee_l_emporte(self):
        fiscalite = ConfigurationFiscale(premier_versement_pea=Date(2019, 5, 6))
        reglage = assembler(banque(), {}, Configuration(), fiscalite).premier_versement_pea

        assert reglage.valeur == Date(2019, 5, 6)
        assert reglage.retenu.origine.source == SOURCE_CORRECTION_FISCALITE
        assert reglage.ecarte.valeur == Date(2026, 1, 2)


class TestLeCritere:
    def test_les_trous_se_comptent_par_actif_et_par_reglage(self):
        reglages = assembler(banque(mouvements_pea=()), {}, Configuration())
        trous = {(actif, nom) for actif, nom, _ in reglages.trous()}

        assert (ETF, "cotation") in trous
        assert (ETF, "frais courants") in trous
        assert ("PEA", "date d'ouverture") in trous
        assert (ETF, "type") not in trous
