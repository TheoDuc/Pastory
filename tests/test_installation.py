"""Les raccourcis de Pastory : `pastory installer` (étape 10, D-106).

Le bureau et le menu Démarrer sont détournés vers un dossier temporaire par un garde-fou
automatique (`tests/garde_fous.py`) : aucun test n'écrit sur le vrai bureau.
"""

from __future__ import annotations

import sys

import pytest

from pastory import cli, installation

SOUS_WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="raccourcis Windows")


@pytest.fixture
def ecrits(monkeypatch):
    """Remplace l'outil du système : note ce qui lui est demandé, et pose un fichier."""
    demandes: list[tuple[installation.Raccourci, object]] = []

    def ecrire(raccourci, cible):
        demandes.append((raccourci, cible))
        raccourci.chemin.write_bytes(b"raccourci")

    monkeypatch.setattr(installation, "_ecrire", ecrire)
    return demandes


@pytest.fixture
def python_present(tmp_path, monkeypatch):
    python = tmp_path / "environnement" / "pythonw.exe"
    python.parent.mkdir()
    python.write_bytes(b"")
    monkeypatch.setattr(installation, "python_sans_fenetre", lambda: python)
    return python


def test_pastory_sur_le_bureau_et_au_menu_la_demonstration_au_menu_seulement(tmp_path):
    prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu")
    assert [r.chemin.relative_to(tmp_path).as_posix() for r in prevus] == [
        "bureau/Pastory.lnk",
        "menu/Pastory/Pastory.lnk",
        "menu/Pastory/Pastory (démonstration).lnk",
    ]


def test_chaque_raccourci_appelle_le_lanceur_et_jamais_uv(tmp_path):
    prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu")
    assert [r.arguments for r in prevus] == [
        "-m pastory.lanceur",
        "-m pastory.lanceur",
        "-m pastory.lanceur --demonstration",
    ]


def test_installer_cree_les_trois_raccourcis(tmp_path, ecrits, python_present):
    crees = installation.installer()
    assert len(crees) == 3
    assert all(raccourci.chemin.is_file() for raccourci in crees)
    assert {cible for _, cible in ecrits} == {python_present}


def test_installer_deux_fois_remplace_sans_doubler(tmp_path, ecrits, python_present):
    installation.installer()
    installation.installer()
    assert len(list(tmp_path.rglob("*.lnk"))) == 3


def test_sans_environnement_installe_le_message_le_dit(tmp_path, ecrits, monkeypatch):
    monkeypatch.setattr(
        installation, "python_sans_fenetre", lambda: tmp_path / "absent" / "pythonw.exe"
    )
    with pytest.raises(installation.InstallationImpossible, match="n'est pas installé"):
        installation.installer()
    assert ecrits == []


def test_retirer_defait_tout_et_seulement_cela(tmp_path, ecrits, python_present):
    installation.installer()
    autre = tmp_path / "bureau" / "Autre chose.lnk"
    autre.write_bytes(b"")

    assert len(installation.retirer()) == 3
    assert list(tmp_path.rglob("*.lnk")) == [autre]
    assert not (tmp_path / "menu" / "Pastory").exists()
    assert installation.retirer() == []


def test_le_logo_des_raccourcis_existe():
    assert installation.icone().is_file()


def test_le_projet_est_bien_le_dossier_qui_contient_pastory():
    assert (installation.dossier_du_projet() / "pastory" / "lanceur.py").is_file()


class TestLaCommande:
    def test_installer_dit_ou_sont_les_raccourcis(self, tmp_path, ecrits, python_present, capsys):
        assert cli.main(["installer"]) == 0
        affichage = capsys.readouterr().out
        assert str(tmp_path / "bureau" / "Pastory.lnk") in affichage
        assert "déplacé ou renommé" in affichage
        affichage.encode("cp1252")

    def test_retirer(self, ecrits, python_present, capsys):
        cli.main(["installer"])
        capsys.readouterr()
        assert cli.main(["installer", "--retirer"]) == 0
        assert "3 raccourci(s) retiré(s)" in capsys.readouterr().out

    def test_une_installation_impossible_s_explique(self, ecrits, monkeypatch, capsys):
        def refuser():
            raise installation.InstallationImpossible("Sous Windows seulement.")

        monkeypatch.setattr(installation, "_emplacements", refuser)
        assert cli.main(["installer"]) == 1
        assert "Sous Windows seulement." in capsys.readouterr().err


@SOUS_WINDOWS
class TestAvecLeVraiWindows:
    """Les deux seuls tests qui parlent au système : ils lisent où est le bureau, et écrivent
    un vrai raccourci — dans le dossier temporaire du test."""

    def test_windows_dit_ou_sont_le_bureau_et_le_menu(self):
        assert installation._dossier_connu(installation.BUREAU).is_dir()
        assert installation._dossier_connu(installation.PROGRAMMES).is_dir()

    def test_un_vrai_raccourci_s_ecrit_meme_dans_un_chemin_accentue(self, tmp_path):
        dossier = tmp_path / "dossier_général"
        dossier.mkdir()
        cible = dossier / "pythonw.exe"
        cible.write_bytes(b"")
        raccourci = installation.Raccourci(
            dossier / "Pastory (démonstration).lnk", "-m pastory.lanceur", "Ouvrir Pastory"
        )

        installation._ecrire(raccourci, cible)

        contenu = raccourci.chemin.read_bytes()
        assert "pythonw.exe".encode("utf-16-le") in contenu
        assert "-m pastory.lanceur".encode("utf-16-le") in contenu
        assert "dossier_général".encode("utf-16-le") in contenu
