"""Ce que le dépôt public promet à qui le découvre (étape 11, D-115 et D-116).

La page d'accueil est le premier écran de Pastory pour un inconnu : un lien mort, une licence
absente ou une bibliothèque oubliée y coûtent plus cher qu'ailleurs, et personne ne les voit
depuis l'intérieur du projet.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
ACCUEIL = (RACINE / "README.md").read_text(encoding="utf-8")


class TestLaPageDAccueil:
    def test_chaque_lien_vers_le_depot_mene_quelque_part(self):
        liens = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", ACCUEIL)
        internes = [lien for lien in liens if not lien.startswith(("http://", "https://"))]
        assert len(internes) > 20
        morts = [lien for lien in internes if not (RACINE / lien).exists()]
        assert morts == []

    def test_elle_dit_que_le_projet_est_independant_de_la_banque(self):
        assert "sans aucun lien avec Trade Republic" in ACCUEIL
        assert "ni un conseil en investissement" in ACCUEIL

    def test_elle_ne_montre_que_la_demonstration(self):
        """Les seules images du dépôt sont celles du portefeuille fictif (D-107)."""
        images = sorted(image.name for image in (RACINE / "docs" / "images").glob("*.png"))
        assert images == ["couverture.png", "diversification.png", "frais.png", "synthese.png"]
        assert "portefeuille de démonstration" in ACCUEIL


class TestLesLicences:
    def test_pastory_est_sous_licence_mit(self):
        licence = (RACINE / "LICENSE").read_text(encoding="utf-8")
        assert licence.startswith("MIT License")
        assert "Permission is hereby granted, free of charge" in licence
        assert "[MIT](LICENSE)" in ACCUEIL

    def test_chaque_oeuvre_de_tiers_garde_sa_licence_a_cote_d_elle(self):
        """Les polices (OFL) et les drapeaux (MIT) se redistribuent avec leur licence."""
        assets = RACINE / "pastory" / "vues" / "assets"
        for licence in (
            assets / "polices" / "LICENCE-EB-Garamond.txt",
            assets / "polices" / "LICENCE-IBM-Plex.txt",
            assets / "drapeaux" / "LICENCE-flag-icons.txt",
        ):
            assert licence.is_file(), licence
        for oeuvre in ("EB Garamond", "IBM Plex", "flag-icons"):
            assert oeuvre in ACCUEIL, oeuvre


class TestLesDependances:
    """D-116 : pandas était déclaré sans plus servir à rien — et c'est lui qui apportait, sans
    que personne le sache, les fuseaux horaires dont Pastory a besoin sous Windows."""

    @staticmethod
    def declarees() -> set[str]:
        projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
        return {
            re.split(r"[<>=!~ ;\[]", dependance, maxsplit=1)[0].lower()
            for dependance in projet["project"]["dependencies"]
        }

    @staticmethod
    def importees() -> set[str]:
        noms: set[str] = set()
        for fichier in (RACINE / "pastory").rglob("*.py"):
            for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
                if isinstance(noeud, ast.Import):
                    noms.update(alias.name.split(".")[0] for alias in noeud.names)
                elif isinstance(noeud, ast.ImportFrom) and noeud.module and not noeud.level:
                    noms.add(noeud.module.split(".")[0])
        return noms

    def test_les_fuseaux_horaires_sont_declares_puisqu_on_s_en_sert(self):
        assert "zoneinfo" in self.importees()
        assert "tzdata" in self.declarees()

    def test_l_heure_de_paris_se_lit(self):
        assert ZoneInfo("Europe/Paris").key == "Europe/Paris"

    def test_aucune_bibliotheque_n_est_declaree_sans_servir(self):
        """« Jamais au cas où » (pyproject.toml) : tzdata mis à part, qui n'est pas du code
        mais les données que lit `zoneinfo`."""
        assert self.declarees() - {"tzdata"} <= self.importees()

    def test_pandas_n_est_ni_declare_ni_importe(self):
        assert "pandas" not in self.declarees() | self.importees()
