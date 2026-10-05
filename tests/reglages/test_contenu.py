"""Le contenu d'un fonds : extraETF décide, le code CFI de l'ESMA confirme ou contredit (D-89).

Aucun test ne sort de la machine. Valeurs fictives (D-03) ; les codes et libellés sont ceux
relevés le 2026-10-05 (docs/reglages-automatiques.md §3).
"""

from __future__ import annotations

import json
from datetime import date as Date

import pytest

from pastory.config.actifs import Configuration, ContenuActif, TypeActif
from pastory.donnees_externes.composition import FournisseurDeCompositions
from pastory.donnees_externes.cours import SourceInjoignable
from pastory.donnees_externes.extraetf import ClasseAnnoncee, lire_la_classe
from pastory.donnees_externes.firds import RegistreFirds
from pastory.parametres import ParametresInvalides, contenus
from pastory.pivot.operation import Poche
from pastory.reglages import CeQueDitLaBanque, Origine, Trou, Trouvee
from pastory.reglages.assemblage import EnLigne, assembler
from pastory.reglages.cache import CacheDesReglages, Champ
from pastory.reglages.recherche import Recherche

ETF = "XX0000000001"
RELEVE = Date(2026, 10, 5)


@pytest.fixture(scope="module")
def lecture():
    """La vraie table du dépôt : c'est elle qu'on veut éprouver."""
    return contenus.charger()


class TestLaTable:
    def test_un_code_n_est_traduit_qu_avec_son_libelle(self, lecture):
        assert lecture.par_extraetf(3, "Anleihen") is ContenuActif.OBLIGATIONS
        # Le piège de D-71 : un code lu sans son libellé.
        assert lecture.par_extraetf(3, "Aktien") is None

    def test_le_monetaire_n_est_pas_traduit(self, lecture):
        assert lecture.par_extraetf(5, "Geldmarkt") is None

    def test_les_lettres_du_cfi(self, lecture):
        assert lecture.par_cfi(["CEOIBS"]) == {ContenuActif.OBLIGATIONS}
        assert lecture.par_cfi(["EYAYMT"]) == {ContenuActif.MATIERES_PREMIERES}
        # Le code par défaut des ISIN luxembourgeois : muet.
        assert lecture.par_cfi(["CECGMS"]) == frozenset()

    def test_une_table_sans_date_est_refusee(self, tmp_path):
        fichier = tmp_path / "contenus.toml"
        fichier.write_text('[meta]\nsource = "x"\n', encoding="utf-8")
        with pytest.raises(ParametresInvalides, match="D-58"):
            contenus.charger(fichier)


class TestLesSources:
    def test_extraetf_donne_le_code_le_libelle_et_la_date(self):
        reponse = json.dumps(
            {
                "results": [
                    {
                        "asset_class_id": 3,
                        "asset_class_name": "Anleihen",
                        "last_imported_at": "2026-10-05T04:00:41.862595+02:00",
                    }
                ]
            }
        ).encode()
        assert lire_la_classe(reponse, ETF) == ClasseAnnoncee(3, "Anleihen", RELEVE)

    def test_extraetf_sans_le_fonds_ne_dit_rien(self):
        assert lire_la_classe(json.dumps({"results": []}).encode(), ETF) is None

    def test_le_registre_rend_les_codes_en_majuscules(self):
        reponse = json.dumps(
            {"facet_counts": {"facet_fields": {"gnr_cfi_code": ["ceoibs", 77, "ceogms", 2]}}}
        ).encode()
        assert RegistreFirds(lambda adresse: reponse).codes_cfi(ETF) == {"CEOIBS", "CEOGMS"}


class Classes:
    def __init__(self, code=None, libelle=None):
        self.annonce = None if code is None else ClasseAnnoncee(code, libelle, RELEVE)

    def classe_d_actifs(self, actif):
        return self.annonce


class Registre:
    def __init__(self, *codes, panne=False):
        self.codes = frozenset(codes)
        self.panne = panne

    def codes_cfi(self, actif):
        if self.panne:
            raise SourceInjoignable("registre coupé")
        return self.codes


class Muette:
    nom = "muette"

    def candidats(self, requete):
        return []


BANQUE = CeQueDitLaBanque(
    source="export de test",
    date=RELEVE,
    types={ETF: frozenset({TypeActif.ETF})},
    poches={ETF: frozenset({Poche.CTO})},
)


def contenu(tmp_path, lecture, classes, registre):
    recherche = Recherche(
        CacheDesReglages(tmp_path / "reglages.csv"),
        Muette(),
        classes=classes,
        registre=registre,
        lecture_des_contenus=lecture,
        aujourd_hui=RELEVE,
    )
    return recherche.trouver(BANQUE, [])[ETF].contenu


class TestLaDecision:
    def test_deux_sources_qui_concordent(self, tmp_path, lecture):
        trouve = contenu(tmp_path, lecture, Classes(3, "Anleihen"), Registre("CEOIBS"))

        assert trouve.valeur is ContenuActif.OBLIGATIONS
        assert "CEOIBS" in trouve.origine.controle
        assert trouve.origine.reserve is None

    def test_deux_sources_qui_se_contredisent_ne_donnent_rien(self, tmp_path, lecture):
        # Le cas mesuré : un fonds d'emprunts d'État annoncé « actions » par son code CFI.
        trouve = contenu(tmp_path, lecture, Classes(3, "Anleihen"), Registre("CEOGES"))

        assert isinstance(trouve, Trou)
        assert "se contredisent" in trouve.motif

    def test_un_registre_muet_laisse_extraetf_seul_et_le_dit(self, tmp_path, lecture):
        trouve = contenu(tmp_path, lecture, Classes(4, "Rohstoffe"), Registre("CECGMS"))

        assert trouve.valeur is ContenuActif.MATIERES_PREMIERES
        assert "non recoupé" in trouve.origine.reserve

    def test_une_classe_non_traduite_est_un_trou_explique(self, tmp_path, lecture):
        trouve = contenu(tmp_path, lecture, Classes(5, "Geldmarkt"), Registre())
        assert "Geldmarkt" in trouve.motif

    def test_un_fonds_inconnu_de_la_source_ne_dit_rien(self, tmp_path, lecture):
        assert contenu(tmp_path, lecture, Classes(), Registre()) is None

    def test_un_registre_en_panne_n_est_pas_garde_en_memoire(self, tmp_path, lecture):
        trouve = contenu(tmp_path, lecture, Classes(3, "Anleihen"), Registre(panne=True))

        assert "n'a pas répondu" in trouve.origine.reserve
        assert CacheDesReglages(tmp_path / "reglages.csv").lire(ETF, Champ.CONTENU) is None


class TestLEffet:
    def reglages(self, valeur):
        trouve = Trouvee(
            valeur,
            Origine(source="extraETF (classe d'actifs du fonds)", date=RELEVE, controle="ok"),
        )
        return assembler(BANQUE, {ETF: EnLigne(contenu=trouve)}, Configuration())

    def test_un_contenu_obligataire_trouve_range_le_fonds_avec_sa_source(self):
        configuration = self.reglages(ContenuActif.OBLIGATIONS).configuration()
        fournisseur = FournisseurDeCompositions(cache=_CacheVide(), actifs=configuration)

        composition = fournisseur.composition(ETF)

        assert composition.source == "extraETF (classe d'actifs du fonds)"
        assert composition.arrete_le == RELEVE
        assert composition.date_est_un_arrete
        assert [part.code for part in composition.classes] == ["obligations"]

    def test_un_contenu_actions_trouve_ne_s_applique_pas(self):
        # Il ferait passer le fonds avant sa composition, et lui ferait perdre ses pays.
        declaration = self.reglages(ContenuActif.ACTIONS).configuration().declaration(ETF)
        assert declaration.contenu is None


class _CacheVide:
    def lire(self, actif):
        return None

    def ecrire(self, composition):
        pass

    def oublier(self, actif=None):
        return []
