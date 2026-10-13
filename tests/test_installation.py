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


class TestLeFichierDInstallation:
    """`Installer Pastory.cmd` : le seul geste d'un nouvel utilisateur. Le premier testeur l'a
    lancé avant d'avoir installé `uv`, puis n'a pas réussi à repartir sans aide : le fichier
    installe désormais `uv` lui-même, et le retrouve là où son installateur le range."""

    FICHIER = installation.dossier_du_projet() / "Installer Pastory.cmd"

    @pytest.fixture
    def texte(self) -> str:
        return self.FICHIER.read_bytes().decode("ascii")

    def test_il_est_ecrit_sans_accents(self):
        """La fenêtre de commandes ne les affiche pas de la même façon partout : `decode`
        échouerait au premier accent."""
        assert self.FICHIER.read_bytes().decode("ascii")

    def test_il_installe_uv_lui_meme_par_la_methode_de_son_editeur(self, texte):
        assert "https://astral.sh/uv/install.ps1" in texte
        assert "call :installer_uv" in texte

    def test_il_previent_avant_d_installer_quoi_que_ce_soit(self, texte):
        installer = texte.split(":installer_uv", 2)[2]
        assert installer.index("pause >nul") < installer.index("install.ps1")
        assert "fermez cette fenetre pour ne rien installer" in installer

    def test_il_cherche_uv_la_ou_son_installateur_le_range(self, texte):
        r"""Un `uv` tout juste installé n'est pas encore dans le chemin de recherche de
        Windows : s'en tenir à `where uv` répondait « introuvable » à qui venait de
        l'installer."""
        assert r"%USERPROFILE%\.local\bin" in texte
        assert '"%UV%" sync' in texte
        assert "\nuv sync" not in texte

    def test_il_refuse_de_partir_de_l_archive_non_decompressee(self, texte):
        assert texte.index('if not exist "pyproject.toml"') < texte.index("call :trouver_uv")

    def test_aucun_echec_ne_ferme_la_fenetre_sans_laisser_lire(self, texte):
        """Un double-clic dont la fenêtre se referme aussitôt est la pire des pannes."""
        lignes = [ligne.strip() for ligne in texte.splitlines()]
        for rang, ligne in enumerate(lignes):
            if ligne == "exit /b 1":
                assert lignes[rang - 1] == "pause", f"ligne {rang + 1}"

    def test_il_se_contente_de_copies_dans_un_dossier_synchronise(self, texte):
        assert "set UV_LINK_MODE=copy" in texte
        assert "set UV_NATIVE_TLS=1" in texte

    @SOUS_WINDOWS
    def test_lance_hors_du_dossier_de_pastory_il_le_dit_et_n_installe_rien(self, tmp_path):
        """Le vrai fichier, dans un dossier vide : c'est ce qui arrive quand on double-clique
        dessus dans l'archive ZIP sans l'avoir décompressée."""
        import shutil
        import subprocess

        copie = tmp_path / self.FICHIER.name
        shutil.copyfile(self.FICHIER, copie)

        resultat = subprocess.run(
            ["cmd", "/c", copie.name],
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
            check=False,
        )

        sortie = resultat.stdout.decode("ascii", errors="replace")
        assert resultat.returncode == 1
        assert "Decompressez d'abord l'archive" in sortie
        assert '"uv"' not in sortie and "astral" not in sortie
        assert list(tmp_path.iterdir()) == [copie]
