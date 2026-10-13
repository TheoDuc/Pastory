"""Les raccourcis de Pastory : `pastory installer` (étape 10, D-106).

Le bureau et le menu Démarrer sont détournés vers un dossier temporaire par un garde-fou
automatique (`tests/garde_fous.py`) : aucun test n'écrit sur le vrai bureau.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

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

    # Les trois façons d'écrire un raccourci, pour que ces tests ne dépendent pas du système
    # sur lequel ils tournent.
    for ecrivain in ("_ecrire", "_ecrire_une_entree_de_menu", "_ecrire_une_commande"):
        monkeypatch.setattr(installation, ecrivain, ecrire)
    return demandes


@pytest.fixture
def python_present(tmp_path, monkeypatch):
    python = tmp_path / "environnement" / "pythonw.exe"
    python.parent.mkdir()
    python.write_bytes(b"")
    monkeypatch.setattr(installation, "python_sans_fenetre", lambda plateforme=None: python)
    return python


def test_pastory_sur_le_bureau_et_au_menu_la_demonstration_au_menu_seulement(tmp_path):
    prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu", "win32")
    assert [r.chemin.relative_to(tmp_path).as_posix() for r in prevus] == [
        "bureau/Pastory.lnk",
        "menu/Pastory/Pastory.lnk",
        "menu/Pastory/Pastory (démonstration).lnk",
    ]


def test_chaque_raccourci_appelle_le_lanceur_et_jamais_uv(tmp_path):
    prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu", "win32")
    assert [r.arguments for r in prevus] == [
        "-m pastory.lanceur",
        "-m pastory.lanceur",
        "-m pastory.lanceur --demonstration",
    ]


def test_installer_cree_les_trois_raccourcis(tmp_path, ecrits, python_present):
    crees = installation.installer("win32")
    assert len(crees) == 3
    assert all(raccourci.chemin.is_file() for raccourci in crees)
    assert {cible for _, cible in ecrits} == {python_present}


def test_installer_deux_fois_remplace_sans_doubler(tmp_path, ecrits, python_present):
    installation.installer("win32")
    installation.installer("win32")
    assert len(list(tmp_path.rglob("*.lnk"))) == 3


def test_sans_environnement_installe_le_message_le_dit(tmp_path, ecrits, monkeypatch):
    monkeypatch.setattr(
        installation,
        "python_sans_fenetre",
        lambda plateforme=None: tmp_path / "absent" / "pythonw.exe",
    )
    with pytest.raises(installation.InstallationImpossible, match="n'est pas installé"):
        installation.installer("win32")
    assert ecrits == []


def test_retirer_defait_tout_et_seulement_cela(tmp_path, ecrits, python_present):
    installation.installer("win32")
    autre = tmp_path / "bureau" / "Autre chose.lnk"
    autre.write_bytes(b"")

    assert len(installation.retirer("win32")) == 3
    assert list(tmp_path.rglob("*.lnk")) == [autre]
    assert not (tmp_path / "menu" / "Pastory").exists()
    assert installation.retirer("win32") == []


def test_le_logo_des_raccourcis_existe():
    assert installation.icone().is_file()


def test_le_projet_est_bien_le_dossier_qui_contient_pastory():
    assert (installation.dossier_du_projet() / "pastory" / "lanceur.py").is_file()


class TestLaCommande:
    def test_installer_dit_ou_sont_les_raccourcis(self, tmp_path, ecrits, python_present, capsys):
        assert cli.main(["installer"]) == 0
        affichage = capsys.readouterr().out
        prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu")
        assert all(str(prevu.chemin) in affichage for prevu in prevus)
        assert installation.ou_les_trouver() in affichage
        assert "déplacé ou renommé" in affichage
        affichage.encode("cp1252")

    def test_retirer(self, ecrits, python_present, capsys):
        cli.main(["installer"])
        capsys.readouterr()
        assert cli.main(["installer", "--retirer"]) == 0
        prevus = installation.raccourcis(Path("bureau"), Path("menu"))
        assert f"{len(prevus)} raccourci(s) retiré(s)" in capsys.readouterr().out

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


class TestLaVersionDePython:
    """D-114 : chez le premier testeur, l'installation a échoué sur « failed to build
    pandas ». Sans version fixée, `uv` prend le Python le plus récent — 3.15, sorti ce
    mois-là — pour lequel pandas n'existait pas encore tout prêt ; il a tenté de le
    fabriquer, ce qui demande un compilateur. Le fichier `.python-version` fixe la version."""

    RACINE = installation.dossier_du_projet()

    def version(self) -> str:
        return (self.RACINE / ".python-version").read_text(encoding="utf-8").strip()

    def test_la_version_est_fixee_et_le_projet_l_accepte(self):
        import re
        import tomllib

        version = self.version()
        assert re.fullmatch(r"3\.\d+", version), version
        projet = tomllib.loads((self.RACINE / "pyproject.toml").read_text(encoding="utf-8"))
        minimum = projet["project"]["requires-python"].removeprefix(">=")
        assert tuple(map(int, version.split("."))) >= tuple(map(int, minimum.split(".")))

    def test_chaque_bibliotheque_existe_toute_prete_pour_cette_version(self):
        """Le garde-fou : pour le Python fixé, sous Windows 64 bits, aucune bibliothèque du
        fichier de verrouillage ne doit avoir à être fabriquée. Mettre à jour une
        bibliothèque sans regarder cela, c'est refaire la panne du premier testeur."""
        import tomllib

        marque = "cp" + self.version().replace(".", "")
        verrou = tomllib.loads((self.RACINE / "uv.lock").read_text(encoding="utf-8"))
        a_fabriquer = []
        for paquet in verrou["package"]:
            roues = [roue["url"].rsplit("/", 1)[-1] for roue in paquet.get("wheels", [])]
            if not roues:
                # Pastory lui-même, installé depuis ce dossier : il n'a rien à compiler.
                assert "editable" in paquet["source"] or "virtual" in paquet["source"], paquet
                continue
            # Toute prête : sans rien de compilé, ou compilée pour ce Python (ou pour tous :
            # « abi3 », « none ») sous Windows 64 bits.
            toute_prete = any(
                roue.endswith("-none-any.whl")
                or (
                    roue.endswith("win_amd64.whl")
                    and any(f"-{pour}-" in roue for pour in (marque, "abi3", "none"))
                )
                for roue in roues
            )
            if not toute_prete:
                a_fabriquer.append(paquet["name"])
        assert a_fabriquer == []

    def test_le_fichier_d_installation_ne_choisit_pas_une_autre_version(self):
        texte = (self.RACINE / "Installer Pastory.cmd").read_bytes().decode("ascii")
        assert "--python" not in texte and "UV_PYTHON=" not in texte
        assert ".python-version" in texte


class TestLesRaccourcisDeLinuxEtDeMacOS:
    """D-117 : le second testeur était sous Linux. Hors de Windows, un raccourci est un simple
    fichier texte : il s'écrit et se vérifie ici, quel que soit le système qui lance les tests.
    Ce que ces tests ne disent pas : qu'un bureau Linux ou un Mac l'accepte tel quel."""

    @pytest.fixture
    def projet(self, tmp_path, monkeypatch):
        """Un dossier de projet dont le chemin porte une espace, un accent et un `$`."""
        dossier = tmp_path / "dossier général" / "Mon $Pastory"
        dossier.mkdir(parents=True)
        monkeypatch.setattr(installation, "dossier_du_projet", lambda: dossier)
        return dossier

    @pytest.fixture
    def python(self, projet, monkeypatch):
        chemin = projet / ".venv" / "bin" / "python"
        chemin.parent.mkdir(parents=True)
        chemin.write_bytes(b"")
        monkeypatch.setattr(installation, "python_sans_fenetre", lambda plateforme=None: chemin)
        return chemin

    def test_sous_linux_tout_va_au_menu_des_applications(self, tmp_path):
        prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu", "linux")
        assert [r.chemin.relative_to(tmp_path).as_posix() for r in prevus] == [
            "menu/pastory.desktop",
            "menu/pastory-demonstration.desktop",
        ]

    def test_sous_macos_pastory_est_sur_le_bureau(self, tmp_path):
        prevus = installation.raccourcis(tmp_path / "bureau", tmp_path / "menu", "darwin")
        assert [r.chemin.relative_to(tmp_path).as_posix() for r in prevus] == [
            "bureau/Pastory.command",
            "menu/Pastory (démonstration).command",
        ]

    def test_une_entree_de_menu_dit_quoi_lancer_et_d_ou(self, tmp_path, projet, python):
        installation.installer("linux")

        entree = (tmp_path / "menu" / "pastory.desktop").read_bytes()
        assert b"\r" not in entree
        champs = dict(
            ligne.split("=", 1) for ligne in entree.decode("utf-8").splitlines()[1:]
        )
        assert entree.startswith(b"[Desktop Entry]\n")
        assert champs["Type"] == "Application"
        assert champs["Name"] == "Pastory"
        assert champs["Terminal"] == "false"
        assert champs["Path"] == str(projet)
        assert champs["Exec"].endswith('" -m pastory.lanceur')
        assert Path(champs["Icon"]).is_file() and champs["Icon"].endswith(".svg")

    def test_la_demonstration_a_son_entree_et_son_nom(self, tmp_path, projet, python):
        installation.installer("linux")

        entree = (tmp_path / "menu" / "pastory-demonstration.desktop").read_text("utf-8")
        assert "Name=Pastory (démonstration)\n" in entree
        assert entree.count("-m pastory.lanceur --demonstration\n") == 1

    def test_un_chemin_avec_espace_accent_et_dollar_reste_un_seul_argument(
        self, tmp_path, projet, python
    ):
        r"""La ligne `Exec` a ses propres règles : le chemin entre guillemets, `$` et `\`
        protégés. Sans cela, « dossier général » ferait deux arguments."""
        installation.installer("linux")

        ligne = next(
            ligne
            for ligne in (tmp_path / "menu" / "pastory.desktop").read_text("utf-8").splitlines()
            if ligne.startswith("Exec=")
        )
        attendu = str(python).replace("\\", "\\\\").replace("$", "\\$")
        assert ligne == f'Exec="{attendu}" -m pastory.lanceur'

    def test_un_pour_cent_est_double(self):
        chemin = PurePosixPath("/opt/100%/python")
        assert installation._pour_exec(chemin) == '"/opt/100%%/python"'

    def test_une_commande_de_macos_entre_dans_le_dossier_puis_lance(
        self, tmp_path, projet, python
    ):
        installation.installer("darwin")

        commande = (tmp_path / "bureau" / "Pastory.command").read_bytes()
        assert commande.startswith(b"#!/bin/sh\n") and b"\r" not in commande
        derniere = commande.decode("utf-8").splitlines()[-1]
        assert derniere == f"cd '{projet}' && exec '{python}' -m pastory.lanceur"

    def test_une_apostrophe_dans_le_chemin_ne_casse_pas_la_commande(
        self, tmp_path, monkeypatch
    ):
        dossier = tmp_path / "l'ordinateur de Zoé"
        dossier.mkdir()
        python = dossier / "python"
        python.write_bytes(b"")
        monkeypatch.setattr(installation, "dossier_du_projet", lambda: dossier)
        monkeypatch.setattr(installation, "python_sans_fenetre", lambda plateforme=None: python)

        installation.installer("darwin")

        commande = (tmp_path / "bureau" / "Pastory.command").read_text("utf-8")
        assert "l'\\''ordinateur de Zoé" in commande

    @pytest.mark.parametrize("plateforme", ["linux", "darwin"])
    def test_retirer_defait_tout(self, tmp_path, projet, python, plateforme):
        crees = installation.installer(plateforme)
        assert all(raccourci.chemin.is_file() for raccourci in crees)

        assert len(installation.retirer(plateforme)) == len(crees) == 2
        assert installation.retirer(plateforme) == []
        assert not list(tmp_path.rglob("*.desktop")) and not list(tmp_path.rglob("*.command"))

    def test_le_message_dit_ou_trouver_pastory_avec_les_mots_du_systeme(self):
        assert "menu Démarrer" in installation.ou_les_trouver("win32")
        assert "menu des applications" in installation.ou_les_trouver("linux")
        assert "bureau" in installation.ou_les_trouver("darwin")

    def test_hors_de_windows_le_python_est_celui_de_l_environnement(self):
        assert installation.python_sans_fenetre("linux") == Path(sys.executable)
        assert installation.python_sans_fenetre("win32").name == "pythonw.exe"


SH = shutil.which("sh")
AVEC_SH = pytest.mark.skipif(SH is None, reason="pas d'interpréteur sh sur cette machine")

FAUX_UV = """#!/bin/sh
echo "uv $*" >> appels.txt
mkdir -p .venv/bin
printf '#!/bin/sh\\necho "python $*" >> appels.txt\\n' > .venv/bin/python
chmod +x .venv/bin/python
"""


def _outil(dossier: Path, nom: str, contenu: str) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / nom
    fichier.write_bytes(contenu.encode("utf-8"))
    fichier.chmod(0o755)


def _lancer_sh(dossier: Path, commande: str, entree: str = "") -> subprocess.CompletedProcess:
    """Lance `commande` par sh dans `dossier`, avec pour seuls outils ceux du système et ceux
    de `dossier/outils` : ni le vrai uv, ni le vrai dossier personnel."""
    return subprocess.run(
        [SH, "-c", f'PATH="$PWD/outils:/usr/bin:/bin" HOME="$PWD/maison" {commande}'],
        cwd=dossier,
        input=entree.encode("utf-8"),
        capture_output=True,
        timeout=120,
        check=False,
    )


class TestLInstallateurDeLinuxEtDeMacOS:
    """`installer-pastory.sh` : le pendant du fichier de Windows. Joué ici avec de faux outils
    (un faux `uv`, un faux Python) : c'est son enchaînement qui est vérifié, pas une vraie
    installation."""

    FICHIER = installation.dossier_du_projet() / "installer-pastory.sh"

    @pytest.fixture
    def dossier(self, tmp_path):
        shutil.copyfile(self.FICHIER, tmp_path / self.FICHIER.name)
        (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
        _outil(tmp_path / "outils", "uname", "#!/bin/sh\necho Linux\n")
        (tmp_path / "maison").mkdir()
        return tmp_path

    def test_il_garde_ses_fins_de_ligne_et_reste_sans_accents(self):
        """Avec des fins de ligne Windows, sh échoue dès la première ligne."""
        contenu = self.FICHIER.read_bytes()
        assert contenu.startswith(b"#!/bin/sh\n")
        assert b"\r" not in contenu
        assert contenu.decode("ascii")
        attributs = (self.FICHIER.parent / ".gitattributes").read_text(encoding="utf-8")
        assert "*.sh text eol=lf" in attributs

    def test_il_installe_uv_par_la_methode_de_son_editeur_apres_avoir_prevenu(self):
        texte = self.FICHIER.read_text(encoding="ascii")
        assert "https://astral.sh/uv/install.sh" in texte
        assert texte.index("read -r") < texte.index("install.sh | sh")
        assert '"$UV" sync' in texte

    @AVEC_SH
    def test_avec_uv_il_synchronise_puis_cree_les_raccourcis(self, dossier):
        _outil(dossier / "outils", "uv", FAUX_UV)

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh")

        sortie = resultat.stdout.decode("ascii")
        assert resultat.returncode == 0, sortie + resultat.stderr.decode("utf-8", "replace")
        assert "deja installe" in sortie and "Pastory est installe" in sortie
        assert (dossier / "appels.txt").read_text().splitlines() == [
            "uv sync",
            "python -m pastory.cli installer",
        ]

    @AVEC_SH
    def test_sans_uv_il_previent_l_installe_puis_le_retrouve_hors_du_chemin(self, dossier):
        """Le cas du premier testeur, côté Linux : `uv` vient d'être installé dans le dossier
        personnel, que le terminal ouvert ne connaît pas encore."""
        if any(Path(d, "uv").exists() for d in ("/usr/bin", "/bin")):
            pytest.skip("un uv du système serait trouvé avant l'essai")
        (dossier / "faux-uv").write_bytes(FAUX_UV.encode("utf-8"))
        _outil(
            dossier / "outils",
            "curl",
            "#!/bin/sh\n"
            "echo 'mkdir -p \"$HOME/.local/bin\" && cp faux-uv \"$HOME/.local/bin/uv\" "
            "&& chmod +x \"$HOME/.local/bin/uv\"'\n",
        )

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh", entree="\n")

        sortie = resultat.stdout.decode("ascii")
        assert resultat.returncode == 0, sortie + resultat.stderr.decode("utf-8", "replace")
        assert "Appuyez sur Entree" in sortie
        assert (dossier / "maison" / ".local" / "bin" / "uv").is_file()
        assert (dossier / "appels.txt").read_text().splitlines()[0] == "uv sync"

    @AVEC_SH
    def test_sans_reponse_il_n_installe_rien(self, dossier):
        _outil(dossier / "outils", "curl", "#!/bin/sh\necho 'touch installe-quand-meme'\n")

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh")

        if any(Path(d, "uv").exists() for d in ("/usr/bin", "/bin")):
            pytest.skip("un uv du système serait trouvé avant l'essai")
        assert resultat.returncode == 1
        assert not (dossier / "installe-quand-meme").exists()

    @AVEC_SH
    def test_si_la_synchronisation_echoue_il_le_dit_et_s_arrete(self, dossier):
        _outil(dossier / "outils", "uv", "#!/bin/sh\necho 'uv a echoue'\nexit 2\n")

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh")

        sortie = resultat.stdout.decode("ascii")
        assert resultat.returncode == 1
        assert "L'installation des bibliotheques a echoue" in sortie
        assert "3/3" not in sortie

    @AVEC_SH
    def test_hors_du_dossier_de_pastory_il_le_dit(self, dossier):
        (dossier / "pyproject.toml").unlink()
        _outil(dossier / "outils", "uv", FAUX_UV)

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh")

        assert resultat.returncode == 1
        assert "n'est pas dans le dossier de Pastory" in resultat.stdout.decode("ascii")
        assert not (dossier / "appels.txt").exists()

    @AVEC_SH
    def test_si_les_raccourcis_echouent_il_dit_comment_ouvrir_pastory_quand_meme(self, dossier):
        _outil(
            dossier / "outils",
            "uv",
            "#!/bin/sh\nmkdir -p .venv/bin\n"
            "printf '#!/bin/sh\\nexit 1\\n' > .venv/bin/python\nchmod +x .venv/bin/python\n",
        )

        resultat = _lancer_sh(dossier, "sh installer-pastory.sh")

        sortie = resultat.stdout.decode("ascii")
        assert resultat.returncode == 1
        assert ".venv/bin/python -m pastory.lanceur" in sortie


class TestLeFichierDeWindowsLanceHorsDeWindows:
    """Ce qu'a fait le second testeur : lancer `Installer Pastory.cmd` sous Linux. Chaque
    ligne y était une commande inconnue. La première ligne du fichier est désormais lue des
    deux côtés : une étiquette sans effet pour Windows, l'ordre de lancer le bon fichier
    pour `sh`."""

    FICHIER = installation.dossier_du_projet() / "Installer Pastory.cmd"

    def test_sa_premiere_ligne_renvoie_a_l_installateur_de_linux(self):
        premiere = self.FICHIER.read_bytes().split(b"\r\n", 1)[0].decode("ascii")
        assert premiere.startswith(":;")
        assert "installer-pastory.sh" in premiere
        # Le « # » final met la fin de ligne de Windows en commentaire, pour sh.
        assert premiere.endswith("#")

    @AVEC_SH
    def test_lance_par_sh_il_passe_la_main_au_bon_fichier(self, tmp_path):
        shutil.copyfile(self.FICHIER, tmp_path / self.FICHIER.name)
        _outil(tmp_path, "installer-pastory.sh", "#!/bin/sh\necho 'le bon installateur'\n")

        resultat = subprocess.run(
            [SH, self.FICHIER.name], cwd=tmp_path, capture_output=True, timeout=60, check=False
        )

        assert resultat.returncode == 0
        assert resultat.stdout.decode("ascii").strip() == "le bon installateur"
        assert b"not found" not in resultat.stderr
