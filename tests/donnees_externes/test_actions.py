"""Le pays et le secteur d'une action détenue en direct (D-62, D-66).

Le test qui compte le plus est celui de la **fragilité assumée** : le secteur arrive sous forme de
libellé, pas de code, et il ne doit jamais produire un chiffre faux — seulement un poste
visiblement non reconnu (règles 4 et 5 de `CLAUDE.md`).

Aucun test ne sort de la machine : la fonction d'ouverture est remplacée partout.
"""

from __future__ import annotations

import json
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory.donnees_externes import actions
from pastory.donnees_externes.composition import CompositionIndisponible
from pastory.parametres import referentiels as ref

AUJOURD_HUI = Date(2026, 9, 27)
ISIN = "XX0000000001"
TICKER = "AAAA.PA"


def registre(pays: str | None = "FR", sans_resultat: bool = False) -> bytes:
    if sans_resultat:
        return json.dumps({"data": []}).encode("utf-8")
    entite = {"legalName": {"name": "SOCIETE EXEMPLE"}, "jurisdiction": "FR"}
    if pays is not None:
        entite["headquartersAddress"] = {"country": pays}
    return json.dumps({"data": [{"attributes": {"entity": entite}}]}).encode("utf-8")


def recherche(secteur: str | None = "Consumer Cyclical", symbole: str = TICKER) -> bytes:
    quote = {"symbol": symbole, "quoteType": "EQUITY", "shortname": "Societe Exemple"}
    if secteur is not None:
        quote["sector"] = secteur
    return json.dumps({"quotes": [quote]}).encode("utf-8")


def source(reponses: dict[str, bytes]):
    """Une source dont l'ouverture répond selon l'adresse appelée."""

    def ouvrir(adresse: str) -> bytes:
        for morceau, contenu in reponses.items():
            if morceau in adresse:
                return contenu
        raise AssertionError(f"adresse inattendue : {adresse}")

    return actions.SourceDActions(ouvrir=ouvrir, aujourd_hui=AUJOURD_HUI)


class TestLeCasNormal:
    def test_le_pays_vient_du_registre_en_code_iso_et_le_secteur_de_la_recherche(self):
        une = source({"gleif": registre(), "search": recherche()})

        composition = une.composition(ISIN, TICKER)

        assert [(part.code, part.pour_cent) for part in composition.pays] == [
            ("FR", Decimal("100"))
        ]
        assert [part.code for part in composition.secteurs] == ["consumer_cyclical"]
        assert [part.code for part in composition.classes] == ["stock"]

    def test_le_code_du_secteur_est_reconnu_par_le_referentiel_du_projet(self):
        # C'est tout l'intérêt de la normalisation : le libellé de la source devient un code
        # que `secteurs.toml` sait nommer, et les actions s'additionnent avec les ETF (D-65).
        une = source({"gleif": registre(), "search": recherche()})
        composition = une.composition(ISIN, TICKER)

        secteur = ref.charger_secteurs().secteur(composition.secteurs[0].code)

        assert secteur is not None
        assert secteur.libelle == "Consommation cyclique"

    def test_la_date_dit_qu_une_societe_n_a_pas_d_arrete(self):
        une = source({"gleif": registre(), "search": recherche()})

        composition = une.composition(ISIN, TICKER)

        assert composition.arrete_le == AUJOURD_HUI
        assert "n'ont pas de date d'arrêté" in composition.intitule_de_la_date


class TestLaFragiliteDuSecteur:
    """Le secteur arrive en libellé : isolé, normalisé, et jamais interprété."""

    @pytest.mark.parametrize(
        ("libelle", "attendu"),
        [
            ("Consumer Cyclical", "consumer_cyclical"),
            ("Financial Services", "financial_services"),
            ("Consumer Defensive", "consumer_defensive"),
            ("Real Estate", "real_estate"),
            ("Communication Services", "communication_services"),
            ("Technology", "technology"),
        ],
    )
    def test_les_libelles_de_la_source_deviennent_des_codes(self, libelle, attendu):
        assert actions._code_du_secteur(libelle) == attendu

    def test_les_onze_libelles_de_la_source_sont_tous_reconnus(self):
        # Si la source changeait de nomenclature, ce test tomberait — et c'est exactement ce
        # qu'on veut savoir avant que des pourcentages ne deviennent illisibles.
        nomenclature = ref.charger_secteurs()
        libelles = (
            "Basic Materials",
            "Communication Services",
            "Consumer Cyclical",
            "Consumer Defensive",
            "Energy",
            "Financial Services",
            "Healthcare",
            "Industrials",
            "Real Estate",
            "Technology",
            "Utilities",
        )

        for libelle in libelles:
            code = actions._code_du_secteur(libelle)
            assert nomenclature.secteur(code) is not None, libelle

    def test_un_libelle_inattendu_ne_fabrique_aucun_chiffre_faux(self):
        # Il remonte tel quel : le moteur l'affichera comme non reconnu, sans le ranger.
        code = actions._code_du_secteur("Artificial Intelligence")

        assert code == "artificial_intelligence"
        assert ref.charger_secteurs().secteur(code) is None

    def test_un_secteur_absent_donne_rien(self):
        assert actions._code_du_secteur(None) is None
        assert actions._code_du_secteur("  ") is None


class TestLesCasIncomplets:
    def test_sans_pays_le_secteur_suffit(self):
        une = source({"gleif": registre(sans_resultat=True), "search": recherche()})

        composition = une.composition(ISIN, TICKER)

        assert composition.pays == ()
        assert composition.secteurs

    def test_sans_secteur_le_pays_suffit(self):
        une = source({"gleif": registre(), "search": recherche(secteur=None)})

        composition = une.composition(ISIN, TICKER)

        assert composition.pays
        assert composition.secteurs == ()

    def test_sans_rien_le_refus_dit_comment_declarer_a_la_main(self):
        une = source(
            {"gleif": registre(sans_resultat=True), "search": recherche(secteur=None)}
        )

        with pytest.raises(CompositionIndisponible, match="actifs.toml"):
            une.composition(ISIN, TICKER)

    def test_un_symbole_qui_ne_correspond_pas_est_ecarte(self):
        # Prendre « la première réponse » a déjà fait retenir la mauvaise cotation à l'étape 4 :
        # ici, on exige que le symbole soit celui que l'utilisateur a validé.
        une = source({"gleif": registre(), "search": recherche(symbole="AUTRE.MI")})

        composition = une.composition(ISIN, TICKER)

        assert composition.secteurs == ()
        assert composition.pays

    def test_l_adresse_legale_sert_de_repli_quand_le_siege_manque(self):
        charge = json.loads(registre().decode("utf-8"))
        del charge["data"][0]["attributes"]["entity"]["headquartersAddress"]
        charge["data"][0]["attributes"]["entity"]["legalAddress"] = {"country": "NL"}
        une = source({"gleif": json.dumps(charge).encode("utf-8"), "search": recherche()})

        composition = une.composition(ISIN, TICKER)

        assert composition.pays[0].code == "NL"
