"""Les référentiels livrés avec l'application, et ce qu'ils refusent (D-65 à D-67).

Deux familles de tests, et la seconde compte autant que la première : ce que les **vrais** fichiers
contiennent, et ce qu'un fichier mal écrit ne peut pas faire passer. Un référentiel faux est pire
qu'un référentiel absent — il range des euros dans la mauvaise case sans rien dire.
"""

from __future__ import annotations

from datetime import date as Date

import pytest

from dashboard_tr.parametres import ParametresInvalides
from dashboard_tr.parametres import referentiels as ref


def ecrire(chemin, texte: str):
    chemin.write_text(texte, encoding="utf-8")
    return chemin


META = """
[meta]
nomenclature = "Nomenclature de test"
source = "un document public"
verifie_le = 2026-09-27
"""


class TestLesVraisFichiers:
    def test_les_onze_secteurs_sont_la_avec_leur_nomenclature_nommee(self):
        # D-65 : la nomenclature doit être nommée, parce que l'écran l'affiche et que deux
        # nomenclatures ne s'additionnent pas.
        nomenclature = ref.charger_secteurs()

        assert len(nomenclature.secteurs) == 11
        assert "Morningstar" in nomenclature.origine.nomenclature
        assert nomenclature.origine.verifie_le == Date(2026, 9, 27)

    def test_les_codes_des_deux_sources_tombent_sur_le_meme_secteur(self):
        # La source des fonds écrit « consumer_defense », celle des sociétés
        # « Consumer Defensive » : deux écritures de la même nomenclature.
        nomenclature = ref.charger_secteurs()

        attendu = nomenclature.secteur("consumer_defense")
        assert attendu is not None
        assert nomenclature.secteur("consumer-defensive") == attendu
        assert nomenclature.secteur("Consumer Defensive") == attendu
        assert attendu.libelle == "Consommation de base"

    def test_un_code_inconnu_ne_leve_pas_mais_rend_rien(self):
        nomenclature = ref.charger_secteurs()

        assert nomenclature.secteur("intelligence_artificielle") is None

    def test_les_pays_sont_nommes_en_francais_et_ranges_dans_une_zone(self):
        geographie = ref.charger_zones()

        assert geographie.nom("US") == "États-Unis"
        assert geographie.zone_de("US").libelle == "Amérique du Nord"
        assert geographie.zone_de("JP").libelle == "Japon"

    def test_les_pays_dont_la_zone_est_disputee_sont_ranges_et_documentes(self):
        # La Corée du Sud, la Pologne et la Grèce changent de camp selon le fournisseur : le
        # fichier tranche **et** écrit pourquoi (D-67).
        geographie = ref.charger_zones()

        for code in ("KR", "PL", "GR"):
            assert geographie.zone_de(code).cle == "marches_emergents"
            assert geographie.pays[code].note

    def test_le_mexique_n_est_pas_en_amerique_du_nord(self):
        # Piège de lecture connu : la géographie dit le contraire de la classification.
        geographie = ref.charger_zones()

        assert geographie.zone_de("MX").cle == "marches_emergents"

    def test_un_pays_inconnu_garde_son_code_et_tombe_dans_une_zone_a_part(self):
        geographie = ref.charger_zones()

        assert geographie.nom("ZZ") == "ZZ"
        assert not geographie.connait("ZZ")
        assert geographie.zone_de("ZZ").cle == ref.ZONE_INCONNUE

    def test_la_zone_a_part_s_affiche_sur_une_console_windows(self):
        # Elle est écrite sans accent : elle peut sortir sur une console en cp1252.
        ref.charger_zones().zone_inconnue.libelle.encode("cp1252")

    def test_les_zones_sortent_dans_l_ordre_des_rangs_et_l_inconnue_en_dernier(self):
        geographie = ref.charger_zones()

        ordre = [zone.cle for zone in geographie.ordonnees()]

        assert ordre[0] == "amerique_du_nord"
        assert ordre[-1] == ref.ZONE_INCONNUE

    def test_les_classes_d_actifs_disent_laquelle_porte_les_actions(self):
        classes = ref.charger_classes()

        assert classes.classe("stock").actions
        assert not classes.classe("bond").actions
        assert not classes.classe("cash").actions

    def test_une_obligation_convertible_compte_avec_les_obligations(self):
        # Lecture prudente, écrite dans le fichier : elle ne gonfle pas la poche actions.
        classes = ref.charger_classes()

        assert classes.classe("convertible").cle == "obligations"

    def test_les_trois_referentiels_se_chargent_ensemble_et_disent_leur_origine(self):
        referentiels = ref.charger_tout()

        assert "Morningstar" in referentiels.nomenclature
        assert len(referentiels.origines) == 3
        for origine in referentiels.origines:
            assert "vérifiée le" in origine


class TestCeQuiEstRefuse:
    def test_un_fichier_sans_source(self, tmp_path):
        fichier = ecrire(
            tmp_path / "secteurs.toml",
            '[meta]\nnomenclature = "x"\nverifie_le = 2026-09-27\n[secteur.1]\n'
            'libelle = "a"\nsuper_secteur = "b"\n',
        )

        with pytest.raises(ParametresInvalides, match="source"):
            ref.charger_secteurs(fichier)

    def test_un_fichier_sans_date_de_verification(self, tmp_path):
        fichier = ecrire(
            tmp_path / "secteurs.toml",
            '[meta]\nnomenclature = "x"\nsource = "y"\n[secteur.1]\n'
            'libelle = "a"\nsuper_secteur = "b"\n',
        )

        with pytest.raises(ParametresInvalides, match="verifie_le"):
            ref.charger_secteurs(fichier)

    def test_une_nomenclature_non_nommee(self, tmp_path):
        fichier = ecrire(
            tmp_path / "secteurs.toml",
            '[meta]\nsource = "y"\nverifie_le = 2026-09-27\n[secteur.1]\n'
            'libelle = "a"\nsuper_secteur = "b"\n',
        )

        with pytest.raises(ParametresInvalides, match="nomenclature"):
            ref.charger_secteurs(fichier)

    def test_un_alias_revendique_par_deux_secteurs(self, tmp_path):
        # Le résultat dépendrait de l'ordre de lecture du fichier : c'est un refus.
        fichier = ecrire(
            tmp_path / "secteurs.toml",
            META
            + '\n[secteur.101]\nlibelle = "a"\nsuper_secteur = "s"\nalias = ["tech"]\n'
            '\n[secteur.311]\nlibelle = "b"\nsuper_secteur = "s"\nalias = ["tech"]\n',
        )

        with pytest.raises(ParametresInvalides, match="revendiqué par deux secteurs"):
            ref.charger_secteurs(fichier)

    def test_un_pays_rattache_a_une_zone_inexistante(self, tmp_path):
        # Sans ce refus, la zone disparaîtrait du total sans que rien ne le dise.
        fichier = ecrire(
            tmp_path / "zones.toml",
            '[meta]\nsource = "y"\nverifie_le = 2026-09-27\n'
            '[zone.europe]\nlibelle = "Europe"\nrang = 1\n'
            '[pays.US]\nlibelle = "États-Unis"\nzone = "amerique"\n',
        )

        with pytest.raises(ParametresInvalides, match="qui n'est pas déclarée"):
            ref.charger_zones(fichier)

    def test_un_code_pays_qui_n_est_pas_un_code_iso(self, tmp_path):
        fichier = ecrire(
            tmp_path / "zones.toml",
            '[meta]\nsource = "y"\nverifie_le = 2026-09-27\n'
            '[zone.europe]\nlibelle = "Europe"\nrang = 1\n'
            '[pays.FRA]\nlibelle = "France"\nzone = "europe"\n',
        )

        with pytest.raises(ParametresInvalides, match="ISO 3166-1"):
            ref.charger_zones(fichier)

    def test_la_zone_reservee_ne_peut_pas_etre_redeclaree(self, tmp_path):
        fichier = ecrire(
            tmp_path / "zones.toml",
            '[meta]\nsource = "y"\nverifie_le = 2026-09-27\n'
            f'[zone.{ref.ZONE_INCONNUE}]\nlibelle = "Ailleurs"\nrang = 1\n'
            '[pays.FR]\nlibelle = "France"\nzone = "inconnue"\n',
        )

        with pytest.raises(ParametresInvalides, match="réservée"):
            ref.charger_zones(fichier)

    def test_des_classes_sans_poche_d_actions(self, tmp_path):
        # Sans classe d'actions, la géographie et les secteurs n'auraient plus de base (D-68).
        fichier = ecrire(
            tmp_path / "classes.toml",
            '[meta]\nsource = "y"\nverifie_le = 2026-09-27\n'
            '[classe.obligations]\nlibelle = "Obligations"\nrang = 1\nactions = false\n',
        )

        with pytest.raises(ParametresInvalides, match="actions = true"):
            ref.charger_classes(fichier)

    def test_un_fichier_absent(self, tmp_path):
        with pytest.raises(ParametresInvalides, match="introuvable"):
            ref.charger_secteurs(tmp_path / "rien.toml")

    def test_un_fichier_qui_n_est_pas_du_toml(self, tmp_path):
        fichier = ecrire(tmp_path / "secteurs.toml", "ceci n'est pas du TOML {{{")

        with pytest.raises(ParametresInvalides, match="TOML"):
            ref.charger_secteurs(fichier)
