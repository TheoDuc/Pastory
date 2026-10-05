"""La source de secours : ce qu'elle lit, et surtout ce qu'elle refuse (D-72, D-77).

Aucun test ne sort de la machine : chacun fournit la réponse du service. Les réponses sont
calquées sur celles relevées le 2026-09-30 (`docs/composition-des-etf.md` §16), en particulier
la forme des poids — des **fractions**, pas des pourcentages.
"""

from __future__ import annotations

import json
from datetime import date as Date
from decimal import Decimal

import pytest

from pastory.donnees_externes.amundi import (
    CHAMP_CLASSES,
    CHAMP_INTERDIT,
    CHAMP_PAYS,
    CHAMP_SECTEURS_NON_LU,
    NOM,
    REGLE_DE_PAYS,
    FraisCourantsAmundi,
    SourceAmundi,
    corps_de_requete,
    lire,
)
from pastory.donnees_externes.composition import (
    CompositionIncoherente,
    CompositionIndisponible,
)
from pastory.donnees_externes.cours import SourceInjoignable
from pastory.parametres.referentiels import charger_libelles_de_pays

ACTIF = "FR001400U5Q4"
AUJOURD_HUI = Date(2026, 9, 30)


@pytest.fixture(scope="module")
def libelles():
    """La vraie table du dépôt : c'est elle qu'on veut éprouver, pas une copie."""
    return charger_libelles_de_pays()


def reponse(
    pays: list[tuple[str, str]] | None = None,
    classes: list[tuple[str, str]] | None = ((("EQUITY_ORDINARY", "1.0")),),
    arrete: str | None = "2026-09-28",
    sans_indice: bool = False,
    produits: object = None,
) -> bytes:
    """Une réponse du service, de la forme relevée le 2026-09-30."""
    if pays is None:
        pays = [("United States", "0.72933585716323"), ("Japan", "0.05860844245419")]

    blocs = [
        {
            "aggregationField": CHAMP_PAYS,
            "breakDownData": [
                {"aggregationName": nom, "weight": float(poids), "additionalProperties": None}
                for nom, poids in pays
            ],
        }
    ]
    if classes:
        blocs.append(
            {
                "aggregationField": CHAMP_CLASSES,
                "breakDownData": [
                    {"aggregationName": nom, "weight": float(poids)} for nom, poids in classes
                ],
            }
        )
    caracteristiques = {"ISIN": ACTIF, "IS_NO_INDEX_BREAKDOWN": sans_indice}
    if arrete is not None:
        caracteristiques["INDEX_BREAKDOWNS_AS_OF_DATE"] = arrete

    charge = {
        "products": produits
        if produits is not None
        else [
            {
                "productId": ACTIF,
                "breakDowns": blocs,
                "characteristics": caracteristiques,
            }
        ]
    }
    return json.dumps(charge).encode("utf-8")


class TestCeQuOnDemande:
    """La requête elle-même. Elle porte deux interdits, et un test les garde."""

    def test_les_secteurs_ne_sont_jamais_demandes(self):
        """Ils sont du GICS, et D-65 n'admet qu'une nomenclature."""
        assert CHAMP_SECTEURS_NON_LU not in corps_de_requete(ACTIF).decode("utf-8")

    def test_les_lignes_detenues_ne_sont_jamais_demandees(self):
        """D-63 et D-64 : sur un fonds à swap, c'est le panier de collatéral."""
        demande = corps_de_requete(ACTIF).decode("utf-8")
        assert CHAMP_INTERDIT not in demande
        assert "composition" not in demande

    def test_la_repartition_par_pays_et_la_date_sont_demandees(self):
        demande = json.loads(corps_de_requete(ACTIF))
        assert demande["breakDown"]["aggregationFields"] == [CHAMP_PAYS, CHAMP_CLASSES]
        assert "INDEX_BREAKDOWNS_AS_OF_DATE" in demande["characteristics"]

    def test_l_isin_est_normalise(self):
        assert json.loads(corps_de_requete(" fr001400u5q4 "))["productIds"] == [ACTIF]


class TestUneReponseNormale:
    def test_les_poids_sont_des_fractions_converties_en_pour_cent(self, libelles):
        """Le piège n° 3 du module : 0,7293… vaut 72,93 %, pas 0,73 % ni 7 293 %."""
        composition = lire(reponse(), ACTIF, libelles, aujourd_hui=AUJOURD_HUI)

        par_code = {part.code: part.pour_cent for part in composition.pays}
        assert par_code["US"] == Decimal("72.9336")
        assert par_code["JP"] == Decimal("5.8608")

    def test_les_libelles_deviennent_des_codes_iso(self, libelles):
        composition = lire(
            reponse(pays=[("United Kingdom", "0.5"), ("South Korea", "0.3"), ("UAE", "0.2")]),
            ACTIF,
            libelles,
        )

        assert [part.code for part in composition.pays] == ["GB", "KR", "AE"]

    def test_les_secteurs_restent_vides(self, libelles):
        """La limite de fond de cette source (D-77) : ses secteurs ne sont pas employés."""
        assert lire(reponse(), ACTIF, libelles).secteurs == ()

    def test_la_date_est_celle_de_l_indice(self, libelles):
        composition = lire(reponse(), ACTIF, libelles)

        assert composition.arrete_le == Date(2026, 9, 28)
        assert composition.date_est_un_arrete
        assert "INDEX_BREAKDOWNS_AS_OF_DATE" in composition.intitule_de_la_date

    def test_la_source_et_la_regle_de_pays_sont_portees(self, libelles):
        """Le champ ajouté à l'étape 8 bis : D-72 les veut visibles ligne par ligne."""
        composition = lire(reponse(), ACTIF, libelles)

        assert composition.source == NOM
        assert composition.regle_de_pays == REGLE_DE_PAYS
        assert "indice" in composition.regle_de_pays

    def test_un_total_de_cent_pour_cent_est_accepte(self, libelles):
        """Contrairement à extraETF, cette source somme **exactement** à 100 % (§16.2)."""
        deux_pays = reponse(pays=[("United States", "0.7"), ("Japan", "0.3")])
        composition = lire(deux_pays, ACTIF, libelles)

        assert composition.total_pays == Decimal("100.0000")


class TestCeQuElleRefuse:
    """Chaque refus attrape un piège mesuré. Aucun ne corrige : ils refusent."""

    def test_une_repartition_vide_est_refusee(self, libelles):
        """LE piège de cette interface : elle répond 200 avec une liste vide (§16.7).

        Sans ce refus, un champ mal nommé dans une version future rendrait l'actif silencieusement
        non couvert, et personne ne saurait que l'interface a changé.
        """
        with pytest.raises(CompositionIncoherente, match="aucune répartition par pays"):
            lire(reponse(pays=[]), ACTIF, libelles)

    def test_un_libelle_de_pays_inconnu_refuse_toute_la_composition(self, libelles):
        """On ne garde pas les lignes traduisibles : « non attribué » voudrait dire autre chose.

        Ce libellé-là dit « la source n'a pas attribué ce montant » (D-69). S'en servir pour dire
        « nous n'avons pas su traduire ce nom » mentirait sur la cause.
        """
        with pytest.raises(CompositionIncoherente) as erreur:
            lire(reponse(pays=[("United States", "0.9"), ("Atlantide", "0.1")]), ACTIF, libelles)

        assert "Atlantide" in str(erreur.value)
        assert "pays_amundi.toml" in str(erreur.value)

    def test_un_fonds_sans_indice_est_refuse_sans_rien_deviner(self, libelles):
        with pytest.raises(CompositionIndisponible, match="pas de répartition d'indice"):
            lire(reponse(sans_indice=True), ACTIF, libelles)

    def test_un_isin_absent_de_la_gamme_est_refuse_avec_la_bonne_raison(self, libelles):
        """Un ISIN iShares rend « aucun produit » : c'est la limite de couverture de D-77."""
        with pytest.raises(CompositionIndisponible) as erreur:
            lire(reponse(produits=[]), "IE00B4L5Y983", libelles)

        assert "fonds Amundi" in str(erreur.value)

    def test_un_fonds_qui_n_est_pas_en_actions_ne_donne_pas_sa_geographie(self, libelles):
        """D-68 : sur un fonds obligataire, « pays » peut vouloir dire devise d'émission."""
        with pytest.raises(CompositionIndisponible) as erreur:
            lire(reponse(classes=[("GOVERNMENT", "1.0")]), ACTIF, libelles)

        assert "GOVERNMENT" in str(erreur.value)
        assert "actifs.toml" in str(erreur.value)

    def test_une_petite_ligne_de_liquidites_ne_fait_pas_refuser_un_fonds_d_actions(
        self, libelles
    ):
        """Le garde-fou est un seuil, pas une liste blanche stricte.

        Exiger que *toutes* les classes rendues soient des actions refuserait un indice
        d'actions portant 0,2 % de liquidités — un faux refus, et le genre de refus qui fait
        perdre confiance sans rien protéger.
        """
        avec_liquidites = reponse(
            classes=[("EQUITY_ORDINARY", "0.998"), ("CASH", "0.002")]
        )

        composition = lire(avec_liquidites, ACTIF, libelles)

        assert [part.code for part in composition.pays] == ["US", "JP"]

    def test_un_fonds_majoritairement_obligataire_est_refuse_avec_sa_part(self, libelles):
        """Le seuil est à 50 %, comme celui d'extraETF, et pour la même raison."""
        mixte = reponse(classes=[("EQUITY_ORDINARY", "0.30"), ("GOVERNMENT", "0.70")])

        with pytest.raises(CompositionIndisponible) as erreur:
            lire(mixte, ACTIF, libelles)

        assert "30.0000 %" in str(erreur.value)

    def test_une_composition_sans_date_est_refusee(self, libelles):
        with pytest.raises(CompositionIncoherente, match="date d'arrêté"):
            lire(reponse(arrete=None), ACTIF, libelles)

    def test_une_date_illisible_est_refusee(self, libelles):
        with pytest.raises(CompositionIncoherente, match="pas lisible"):
            lire(reponse(arrete="le 28 septembre"), ACTIF, libelles)

    def test_une_reponse_qui_n_est_pas_du_json_est_refusee(self, libelles):
        with pytest.raises(CompositionIncoherente, match="pas du JSON lisible"):
            lire(b"<html>maintenance</html>", ACTIF, libelles)

    def test_un_poids_qui_n_est_pas_un_nombre_est_refuse(self, libelles):
        charge = json.loads(reponse())
        charge["products"][0]["breakDowns"][0]["breakDownData"][0]["weight"] = "beaucoup"

        with pytest.raises(CompositionIncoherente, match="n'est pas lisible"):
            lire(json.dumps(charge).encode("utf-8"), ACTIF, libelles)


class TestLaSourceComplete:
    """La classe telle que le fournisseur l'emploie, sans réseau."""

    def test_elle_envoie_le_corps_attendu_et_rend_la_composition(self, libelles):
        vues: list[tuple[str, bytes]] = []

        def poster(adresse: str, corps: bytes) -> bytes:
            vues.append((adresse, corps))
            return reponse()

        source = SourceAmundi(libelles, poster=poster, aujourd_hui=AUJOURD_HUI)
        composition = source.composition(ACTIF)

        assert source.nom == NOM
        assert len(vues) == 1
        assert "amundietf.fr" in vues[0][0]
        assert json.loads(vues[0][1])["productIds"] == [ACTIF]
        assert composition.recupere_le == AUJOURD_HUI

    def test_un_service_injoignable_remonte_comme_tel(self, libelles):
        def poster(adresse: str, corps: bytes) -> bytes:
            raise SourceInjoignable("coupé")

        with pytest.raises(SourceInjoignable):
            SourceAmundi(libelles, poster=poster).composition(ACTIF)


class TestLaTableDesLibelles:
    """La fragilité assumée de D-77, et ce qui la borne."""

    def test_les_quarante_sept_libelles_releves_sont_tous_connus(self, libelles):
        """Ceux du §16 du comparatif. Si l'un manquait, un fonds entier serait refusé."""
        releves = [
            "Australia", "Austria", "Belgium", "Brazil", "Canada", "Chile", "China",
            "Colombia", "Czech Republic", "Denmark", "Egypt", "Finland", "France",
            "Germany", "Greece", "Hong Kong", "Hungary", "India", "Indonesia", "Ireland",
            "Israel", "Italy", "Japan", "Kuwait", "Malaysia", "Mexico", "Netherlands",
            "New Zealand", "Norway", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
            "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain", "Sweden",
            "Switzerland", "Taiwan", "Thailand", "Turkey", "UAE", "United Kingdom",
            "United States",
        ]
        assert len(releves) == 47
        manquants = [nom for nom in releves if libelles.code(nom) is None]
        assert manquants == []

    def test_les_six_pieges_de_nommage_sont_traites(self, libelles):
        """Les six que le relevé a signalés comme demandant de l'attention."""
        assert libelles.code("United Kingdom") == "GB"  # et non « UK », qui n'est pas ISO
        assert libelles.code("South Korea") == "KR"  # KP serait la Corée du Nord
        assert libelles.code("UAE") == "AE"
        assert libelles.code("Czech Republic") == "CZ"  # ISO écrit « Czechia »
        assert libelles.code("Turkey") == "TR"  # ISO écrit « Türkiye »
        assert libelles.code("Taiwan") == "TW"  # distinct de CN

    def test_hong_kong_et_la_chine_ne_sont_pas_le_meme_pays(self, libelles):
        """Les deux apparaissent côte à côte dans les fonds émergents."""
        assert libelles.code("Hong Kong") == "HK"
        assert libelles.code("China") == "CN"

    def test_la_casse_et_les_espaces_ne_font_pas_rater_une_ligne(self, libelles):
        assert libelles.code("  UNITED   STATES ") == "US"

    def test_un_libelle_inconnu_rend_none_et_n_est_jamais_devine(self, libelles):
        """Règle 5 : il sera affiché, jamais rangé par défaut."""
        assert libelles.code("Atlantide") is None

    def test_la_table_porte_sa_source_et_sa_date(self, libelles):
        """D-58 : sans date ni source, un paramètre est refusé."""
        assert libelles.origine.verifie_le == Date(2026, 9, 30)
        assert "amundietf.fr" in libelles.origine.source

    def test_tous_les_codes_sont_des_codes_iso_a_deux_lettres(self, libelles):
        mauvais = [c for c in libelles.codes.values() if len(c) != 2 or not c.isalpha()]
        assert mauvais == []


class TestLesFraisCourants:
    """Le TER d'Amundi (étape 8 quater) : en pour cent, daté, sans répartition ni lignes."""

    @staticmethod
    def source(caracteristiques=None, produits=True):
        envoye = []

        def poster(adresse, corps):
            envoye.append(json.loads(corps))
            if not produits:
                return json.dumps({"products": []}).encode()
            return json.dumps(
                {"products": [{"characteristics": caracteristiques or {}}]}
            ).encode()

        return FraisCourantsAmundi(poster), envoye

    def test_le_ter_est_lu_en_pour_cent_avec_sa_date_d_effet(self):
        source, _ = self.source(
            {"TER": 0.2, "TER_EFFECTIVE_DATE": "2025-10-01T00:00:00.000+00:00"}
        )
        frais = source.frais_courants(ACTIF)

        assert frais.ter_pour_cent == Decimal("0.2")
        assert frais.date == Date(2025, 10, 1)

    def test_trois_decimales_sont_gardees(self):
        source, _ = self.source({"TER": 0.165, "TER_EFFECTIVE_DATE": "2024-03-31"})
        assert source.frais_courants(ACTIF).ter_pour_cent == Decimal("0.165")

    def test_un_ter_sans_date_n_est_pas_retenu(self):
        # D-58 : un taux sans date n'est pas vérifiable.
        source, _ = self.source({"TER": 0.2})
        assert source.frais_courants(ACTIF) is None

    def test_un_fonds_d_un_autre_emetteur_n_a_pas_de_ter_ici(self):
        source, _ = self.source(produits=False)
        assert source.frais_courants("IE0000000001") is None

    def test_on_ne_demande_ni_repartition_ni_lignes_detenues(self):
        source, envoye = self.source({"TER": 0.2, "TER_EFFECTIVE_DATE": "2025-10-01"})
        source.frais_courants(ACTIF)

        texte = json.dumps(envoye[0])
        assert "breakDown" not in texte
        assert CHAMP_INTERDIT not in texte
