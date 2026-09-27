"""La lecture de la source de compositions, sur des réponses écrites à la main.

Les cinq premiers tests sont **la liste de contrôle du §12 du comparatif**, transposée en tests du
projet : chacun attrape un piège de gravité 1 mesuré pendant la recherche, et chacun produirait
sinon un pourcentage faux et parfaitement crédible.

Aucun test ne sort de la machine : la fonction d'ouverture est remplacée partout.
"""

from __future__ import annotations

import json
from datetime import date as Date
from decimal import Decimal

import pytest

from dashboard_tr.donnees_externes import extraetf
from dashboard_tr.donnees_externes.composition import (
    CompositionIncoherente,
    CompositionIndisponible,
    controler,
)

AUJOURD_HUI = Date(2026, 9, 27)
ISIN = "XX0000000001"


def reponse(**remplacements) -> bytes:
    """Une réponse de la source, de la forme observée le 2026-09-27."""
    fonds = {
        "ter": 0.20,
        "is_swap_based_etf": False,
        "is_synthetic_replication": False,
        "kiid_url": "https://exemple.test/dic.pdf",
        "index_date_last_update": "2026-08-31",
        "portfolio_breakdown": {
            "country_stocks_exposure_list": [
                {"name": "Vereinigte Staaten (USA)", "value": 72.04, "code": "US"},
                {"name": "Japan", "value": 5.78, "code": "JP"},
            ],
            "global_stock_exposure_list": [
                {"name": "Technologie", "value": 30.61, "code": "technology"},
                {"name": "Zykl. Konsumgüter", "value": 8.73, "code": "consumer_cyclical"},
            ],
            "asset_allocation_exposure_list": [
                {"name": "Aktien", "value": 99.96, "code": "stock"},
            ],
            # Les lignes détenues : présentes dans la réponse, et **jamais lues** (D-63).
            "items": [
                {
                    "name": "TRS MSCI World NR USD",
                    "weight": 100.0,
                    "isin": "",
                    "country": "USA",
                }
            ],
        },
    }
    fonds.update(remplacements)
    return json.dumps({"count": 1, "results": [fonds]}).encode("utf-8")


def lire(contenu: bytes):
    return extraetf.lire(contenu, ISIN, aujourd_hui=AUJOURD_HUI)


class TestLaListeDeControleDuComparatif:
    """Les cinq tests du §12 de `docs/composition-des-etf.md`."""

    def test_t2_la_nomenclature_est_bien_celle_attendue(self):
        # « consumer_cyclical » est un code Morningstar. Si la source renvoyait un jour des
        # libellés GICS, le code changerait et le référentiel ne le reconnaîtrait plus : le
        # poste serait affiché comme non reconnu au lieu d'être rangé de travers.
        composition = lire(reponse())

        assert [part.code for part in composition.secteurs] == ["technology", "consumer_cyclical"]

    def test_t3_les_codes_pays_sont_des_codes_iso_et_non_des_libelles(self):
        composition = lire(reponse())

        assert [part.code for part in composition.pays] == ["US", "JP"]

    def test_t4_les_lignes_detenues_ne_sont_jamais_lues(self):
        # Le piège le plus grave : l'unique ligne de cet ETF est un swap auquel la source
        # attribue le pays « USA » et un poids de 100 %. Le lire donnerait 100 % d'États-Unis
        # pour un fonds mondial (D-63, D-64).
        composition = lire(reponse())

        assert dict((part.code, part.pour_cent) for part in composition.pays) == {
            "US": Decimal("72.0400"),
            "JP": Decimal("5.7800"),
        }

    def test_t4_bis_le_module_ne_mentionne_jamais_le_champ_des_lignes_detenues(self):
        # Garde-fou de lecture : si quelqu'un ajoutait un jour un accès à « items », ce test
        # tomberait. Le nom du champ n'apparaît que dans la constante qui le nomme pour
        # l'interdire.
        with open(extraetf.__file__, encoding="utf-8") as fichier:
            texte = fichier.read()

        assert extraetf.CHAMP_INTERDIT == "items"
        # La seule occurrence autorisée est la constante qui **nomme** le champ pour
        # l'interdire. Toute lecture réelle passerait par l'une de ces formes.
        assert texte.count('"items"') == 1
        assert '["items"]' not in texte
        assert 'get("items")' not in texte
        assert "[CHAMP_INTERDIT]" not in texte
        assert "get(CHAMP_INTERDIT)" not in texte

    def test_t5_la_somme_des_poids_n_est_jamais_ramenee_a_cent(self):
        composition = lire(reponse())

        assert composition.total_pays == Decimal("77.8200")
        assert composition.total_secteurs == Decimal("39.3400")


class TestLaDateDArrete:
    def test_elle_est_lue_et_son_intitule_dit_ce_qu_elle_est(self):
        composition = lire(reponse())

        assert composition.arrete_le == Date(2026, 8, 31)
        assert "index_date_last_update" in composition.intitule_de_la_date

    def test_une_composition_sans_date_est_refusee(self):
        # D-58 et D-70 : une répartition sans date n'est pas vérifiable. Mieux vaut un trou
        # signalé qu'un camembert dont on ne sait pas de quel mois il parle.
        sans_date = reponse(index_date_last_update=None)

        with pytest.raises(CompositionIncoherente, match="aucune date"):
            lire(sans_date)

    def test_une_date_horodatee_est_acceptee(self):
        composition = lire(reponse(index_date_last_update="2026-09-22T00:00:00Z"))

        assert composition.arrete_le == Date(2026, 9, 22)


class TestLaReplication:
    def test_un_fonds_a_swap_est_reconnu_par_ses_drapeaux_et_non_par_son_libelle(self):
        # Le libellé de la source est en allemand (« Synthetisch ») : on ne le lit pas
        # (règle 4). Ce sont les deux drapeaux booléens qui font foi.
        composition = lire(
            reponse(is_swap_based_etf=True, replication_methodology_first_level="Synthetisch")
        )

        assert composition.replication == "synthétique"
        assert composition.synthetique

    def test_un_fonds_physique_est_reconnu_comme_tel(self):
        composition = lire(reponse())

        assert composition.replication == "physique"
        assert not composition.synthetique

    def test_sans_drapeau_on_ne_devine_pas(self):
        muette = json.loads(reponse().decode("utf-8"))
        del muette["results"][0]["is_swap_based_etf"]
        del muette["results"][0]["is_synthetic_replication"]

        composition = lire(json.dumps(muette).encode("utf-8"))

        assert composition.replication is None


class TestCeQuiEstRefuse:
    def test_un_actif_inconnu_de_la_source(self):
        with pytest.raises(CompositionIndisponible, match="ne connaît pas"):
            lire(json.dumps({"count": 0, "results": []}).encode("utf-8"))

    def test_une_reponse_qui_n_est_pas_du_json(self):
        with pytest.raises(CompositionIncoherente, match="JSON"):
            lire(b"<html>une page d'erreur</html>")

    def test_une_reponse_sans_repartition(self):
        sans = json.loads(reponse().decode("utf-8"))
        del sans["results"][0]["portfolio_breakdown"]

        with pytest.raises(CompositionIncoherente, match="sans aucune répartition"):
            lire(json.dumps(sans).encode("utf-8"))

    def test_un_poste_sans_code_est_refuse_plutot_que_devine_d_apres_son_libelle(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["country_stocks_exposure_list"] = [
            {"name": "Vereinigte Staaten (USA)", "value": 72.04}
        ]

        with pytest.raises(CompositionIncoherente, match="règle 4"):
            lire(json.dumps(charge).encode("utf-8"))

    def test_un_poids_qui_n_est_pas_un_nombre(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["country_stocks_exposure_list"] = [
            {"name": "x", "value": "beaucoup", "code": "US"}
        ]

        with pytest.raises(CompositionIncoherente, match="n'est pas un nombre"):
            lire(json.dumps(charge).encode("utf-8"))


class TestLesControlesDeVraisemblance:
    """Ils remplacent la relecture humaine : le propriétaire a choisi l'automatique (Q-39)."""

    def test_un_total_au_dela_de_la_limite_est_refuse(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["country_stocks_exposure_list"] = [
            {"name": "x", "value": 70.0, "code": "US"},
            {"name": "y", "value": 60.0, "code": "JP"},
        ]

        with pytest.raises(CompositionIncoherente, match="au-delà de"):
            controler(lire(json.dumps(charge).encode("utf-8")))

    def test_un_leger_depassement_de_cent_est_accepte(self):
        # Le prêt de titres fait légitimement dépasser 100 % : un contrôle « ça fait 100 »
        # échouerait à tort (D-69).
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["country_stocks_exposure_list"] = [
            {"name": "x", "value": 101.5, "code": "US"}
        ]

        composition = controler(lire(json.dumps(charge).encode("utf-8")))

        assert composition.total_pays == Decimal("101.5000")

    def test_un_code_pays_qui_n_est_pas_un_code_iso_est_refuse(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["country_stocks_exposure_list"] = [
            {"name": "Welt", "value": 4.73, "code": "Welt"}
        ]

        with pytest.raises(CompositionIncoherente, match="ISO 3166-1"):
            controler(lire(json.dumps(charge).encode("utf-8")))

    def test_un_poids_negatif_est_refuse(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"]["global_stock_exposure_list"] = [
            {"name": "x", "value": -5.0, "code": "technology"}
        ]

        with pytest.raises(CompositionIncoherente, match="négatif"):
            controler(lire(json.dumps(charge).encode("utf-8")))

    def test_une_composition_entierement_vide_est_refusee(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"] = {"index_date_last_update": "2026-08-31"}

        with pytest.raises(CompositionIncoherente, match="aucune répartition"):
            controler(lire(json.dumps(charge).encode("utf-8")))


class TestLAppel:
    def test_l_isin_est_passe_en_parametre_et_la_source_est_nommee(self):
        vues: list[str] = []

        def ouvrir(adresse: str) -> bytes:
            vues.append(adresse)
            return reponse()

        source = extraetf.SourceExtraEtf(ouvrir=ouvrir, aujourd_hui=AUJOURD_HUI)
        composition = source.composition("xx0000000001")

        assert vues == ["https://extraetf.com/api-v2/detail/?isin=XX0000000001"]
        assert composition.source == extraetf.NOM
        assert composition.recupere_le == AUJOURD_HUI
        assert composition.document == "https://exemple.test/dic.pdf"


class TestUneSourceQuiRepondSansRienSavoir:
    """Le cas trouvé sur de vrais ETF : une réponse valide, et des poids tous à zéro.

    Sans ce contrôle, l'actif serait compté en « non attribué » — comme si le calcul était en
    faute — au lieu de « non couvert », qui est la vérité : personne ne sait ce qu'il y a dedans.
    """

    def test_des_repartitions_toutes_a_zero_sont_traitees_comme_une_absence(self):
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"] = {
            "index_date_last_update": "2026-08-31",
            "country_stocks_exposure_list": [],
            "global_stock_exposure_list": [],
            "asset_allocation_exposure_list": [
                {"name": "Aktien", "value": 0.0, "code": "stock"},
                {"name": "Anleihen", "value": 0.0, "code": "bond"},
            ],
        }

        with pytest.raises(CompositionIndisponible, match="n'a pas sa transparence"):
            controler(lire(json.dumps(charge).encode("utf-8")))

    def test_une_repartition_qui_n_explique_presque_rien_est_ecartee(self):
        # Cas réel : un fonds dont la source ne connaît que 2,92 % d'obligations.
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"] = {
            "index_date_last_update": "2026-08-31",
            "asset_allocation_exposure_list": [
                {"name": "Anleihen", "value": 2.92131, "code": "bond"}
            ],
        }

        with pytest.raises(CompositionIndisponible, match="2.9213 %"):
            controler(lire(json.dumps(charge).encode("utf-8")))

    def test_un_etf_obligataire_normal_reste_accepte(self):
        # Sa seule répartition renseignée est celle des classes d'actifs, et elle fait 100 %.
        charge = json.loads(reponse().decode("utf-8"))
        charge["results"][0]["portfolio_breakdown"] = {
            "index_date_last_update": "2026-09-22",
            "country_stocks_exposure_list": [],
            "global_stock_exposure_list": [],
            "asset_allocation_exposure_list": [
                {"name": "Anleihen", "value": 99.8, "code": "bond"}
            ],
        }

        composition = controler(lire(json.dumps(charge).encode("utf-8")))

        assert composition.pays == ()
        assert composition.total_classes == Decimal("99.8000")
