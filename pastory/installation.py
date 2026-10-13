"""Les raccourcis de Pastory : `pastory installer` (étape 10, D-106 ; Linux et macOS, D-117).

Un raccourci sur le bureau et dans le menu Démarrer, avec le logo, qui appelle le lanceur
(`pastory/lanceur.py`). C'est tout ce que « installer » veut dire ici : aucun fichier n'est
copié ailleurs, rien n'est inscrit dans le système, et `pastory installer --retirer` défait tout.

Chaque système a sa façon de ranger un raccourci, et ce module en connaît trois :

- **Windows** : un fichier `.lnk`, sur le bureau et dans le menu Démarrer ;
- **Linux** : une entrée du menu des applications (un fichier `.desktop`, la convention
  commune à tous les bureaux) ;
- **macOS** : un fichier `.command` sur le bureau, qu'un double-clic exécute.

Les deux derniers sont de simples fichiers texte : ils s'écrivent et se testent depuis
n'importe quel système. **Ils n'ont pas été essayés sur un vrai Linux ni un vrai Mac** au
moment où ils ont été écrits (2026-10-13).

**Le raccourci pointe sur ce dossier-ci.** Il appelle le Python de l'environnement du projet,
par son chemin : jamais `uv run`, qui voudrait d'abord réinstaller le projet et peut échouer
là où l'environnement, lui, fonctionne. Si le dossier du projet est déplacé ou renommé, les
raccourcis sont à recréer.

Sous Windows, un fichier `.lnk` ne s'écrit pas en Python sans bibliothèque de plus : c'est
l'outil du système qui le fait (`WScript.Shell`, par PowerShell), et les valeurs lui sont
passées par l'environnement, pour qu'un chemin accentué arrive intact.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pastory.config.emplacements import NOM_APPLICATION

NOM = NOM_APPLICATION
NOM_DE_LA_DEMONSTRATION = f"{NOM} (démonstration)"

BUREAU = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"
PROGRAMMES = "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"
"""Les identifiants que Windows donne au bureau et au menu Démarrer. On les lui demande,
on ne les devine pas : le bureau est souvent déplacé dans OneDrive."""

ECRIRE_UN_RACCOURCI = (
    "$raccourci = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PASTORY_RACCOURCI); "
    "$raccourci.TargetPath = $env:PASTORY_CIBLE; "
    "$raccourci.Arguments = $env:PASTORY_ARGUMENTS; "
    "$raccourci.WorkingDirectory = $env:PASTORY_DEPART; "
    "$raccourci.IconLocation = $env:PASTORY_ICONE; "
    "$raccourci.Description = $env:PASTORY_DESCRIPTION; "
    "$raccourci.Save()"
)


class InstallationImpossible(Exception):
    """Les raccourcis n'ont pas pu être créés. Le message dit pourquoi, et comment ouvrir
    Pastory sans eux."""


@dataclass(frozen=True)
class Raccourci:
    chemin: Path
    arguments: str
    description: str


def dossier_du_projet() -> Path:
    return Path(__file__).resolve().parent.parent


def python_sans_fenetre(plateforme: str | None = None) -> Path:
    """Le Python de cet environnement. Sous Windows, sa version qui n'ouvre pas de fenêtre
    noire ; ailleurs il n'y en a qu'un, et c'est le lanceur qui se passe de terminal."""
    if (plateforme or sys.platform) == "win32":
        return Path(sys.executable).with_name("pythonw.exe")
    return Path(sys.executable)


def icone(plateforme: str | None = None) -> Path:
    """Le logo : en `.ico` pour Windows, en SVG pour le menu d'un bureau Linux."""
    nom = "favicon.ico" if (plateforme or sys.platform) == "win32" else "favicon.svg"
    return Path(__file__).resolve().parent / "vues" / "assets" / nom


def raccourcis(bureau: Path, programmes: Path, plateforme: str | None = None) -> list[Raccourci]:
    """Pastory sur le bureau et dans le menu ; la démonstration dans le menu seulement, pour
    ne pas encombrer le bureau d'une icône qui sert rarement.

    Sous Linux, tout va au menu des applications : un fichier posé sur le bureau y demande
    une autorisation que chaque bureau accorde à sa façon."""
    plateforme = plateforme or sys.platform
    lanceur = "-m pastory.lanceur"
    ouvrir = f"Ouvrir {NOM}, le tableau de bord de vos actifs"
    essayer = f"Ouvrir {NOM} sur un portefeuille fictif"
    demonstration = f"{lanceur} --demonstration"
    if plateforme == "win32":
        menu = programmes / NOM
        return [
            Raccourci(bureau / f"{NOM}.lnk", lanceur, ouvrir),
            Raccourci(menu / f"{NOM}.lnk", lanceur, ouvrir),
            Raccourci(menu / f"{NOM_DE_LA_DEMONSTRATION}.lnk", demonstration, essayer),
        ]
    if plateforme == "darwin":
        return [
            Raccourci(bureau / f"{NOM}.command", lanceur, ouvrir),
            Raccourci(programmes / f"{NOM_DE_LA_DEMONSTRATION}.command", demonstration, essayer),
        ]
    return [
        Raccourci(programmes / "pastory.desktop", lanceur, ouvrir),
        Raccourci(programmes / "pastory-demonstration.desktop", demonstration, essayer),
    ]


def ou_les_trouver(plateforme: str | None = None) -> str:
    """Où l'utilisateur trouvera Pastory, dit avec les mots de son système."""
    plateforme = plateforme or sys.platform
    if plateforme == "win32":
        return "sur le bureau ou dans le menu Démarrer"
    if plateforme == "darwin":
        return "sur le bureau (la démonstration est dans le dossier Applications de votre session)"
    return "dans le menu des applications"


def installer(plateforme: str | None = None) -> list[Raccourci]:
    """Crée les raccourcis, en remplaçant ceux d'une installation précédente."""
    plateforme = plateforme or sys.platform
    crees = raccourcis(*_emplacements(), plateforme)
    cible = python_sans_fenetre(plateforme)
    if not cible.is_file():
        raise InstallationImpossible(
            f"Le programme {cible} est introuvable : l'environnement de {NOM} n'est pas "
            "installé dans ce dossier."
        )
    if plateforme == "win32":
        ecrire = _ecrire
    elif plateforme == "darwin":
        ecrire = _ecrire_une_commande
    else:
        ecrire = _ecrire_une_entree_de_menu
    for raccourci in crees:
        raccourci.chemin.parent.mkdir(parents=True, exist_ok=True)
        ecrire(raccourci, cible)
    return crees


def retirer(plateforme: str | None = None) -> list[Raccourci]:
    """Supprime les raccourcis, et le dossier du menu Démarrer s'il est vide. Rend ceux qui
    existaient."""
    retires = []
    for raccourci in raccourcis(*_emplacements(), plateforme):
        if raccourci.chemin.is_file():
            raccourci.chemin.unlink()
            retires.append(raccourci)
        dossier = raccourci.chemin.parent
        if dossier.name == NOM and dossier.is_dir() and not any(dossier.iterdir()):
            dossier.rmdir()
    return retires


def _emplacements() -> tuple[Path, Path]:
    """Le bureau, et l'endroit où le système range ses programmes pour cette session."""
    if sys.platform == "win32":
        return _dossier_connu(BUREAU), _dossier_connu(PROGRAMMES)
    maison = Path.home()
    if sys.platform == "darwin":
        return maison / "Desktop", maison / "Applications"
    # Linux et les autres : la convention commune des bureaux (XDG).
    donnees = os.environ.get("XDG_DATA_HOME") or str(maison / ".local" / "share")
    return maison / "Desktop", Path(donnees) / "applications"


def _ecrire_une_entree_de_menu(raccourci: Raccourci, cible: Path) -> None:
    """Une entrée du menu des applications, sous Linux : un fichier `.desktop`."""
    nom = NOM_DE_LA_DEMONSTRATION if "--demonstration" in raccourci.arguments else NOM
    lignes = [
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.0",
        f"Name={nom}",
        f"Comment={raccourci.description}",
        f"Exec={_pour_exec(cible)} {raccourci.arguments}",
        f"Path={dossier_du_projet()}",
        f"Icon={icone('linux')}",
        "Terminal=false",
        "Categories=Office;Finance;",
    ]
    try:
        raccourci.chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")
        raccourci.chemin.chmod(0o755)
    except OSError as erreur:
        raise InstallationImpossible(
            f"L'entrée de menu {raccourci.chemin} n'a pas pu être écrite : {erreur}"
        ) from erreur


def _pour_exec(chemin: Path) -> str:
    """Un chemin tel que la ligne `Exec` d'un fichier `.desktop` le veut : entre guillemets,
    ses caractères spéciaux protégés, et tout `%` doublé (il y annonce un champ)."""
    texte = str(chemin)
    for special in ("\\", '"', "`", "$"):
        texte = texte.replace(special, "\\" + special)
    return '"' + texte.replace("%", "%%") + '"'


def _ecrire_une_commande(raccourci: Raccourci, cible: Path) -> None:
    """Un fichier `.command`, sous macOS : un double-clic l'exécute dans un terminal."""

    def cite(chemin: Path) -> str:
        return "'" + str(chemin).replace("'", "'\\''") + "'"

    lignes = [
        "#!/bin/sh",
        f"# {raccourci.description} (écrit par « pastory installer »).",
        f"cd {cite(dossier_du_projet())} && exec {cite(cible)} {raccourci.arguments}",
    ]
    try:
        raccourci.chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")
        raccourci.chemin.chmod(0o755)
    except OSError as erreur:
        raise InstallationImpossible(
            f"Le fichier {raccourci.chemin} n'a pas pu être écrit : {erreur}"
        ) from erreur


def _dossier_connu(identifiant: str) -> Path:
    """Demande à Windows où se trouve un de ses dossiers (`SHGetKnownFolderPath`)."""
    import ctypes
    from ctypes import wintypes

    class Identifiant(ctypes.Structure):
        _fields_ = [
            ("a", wintypes.DWORD),
            ("b", wintypes.WORD),
            ("c", wintypes.WORD),
            ("d", wintypes.BYTE * 8),
        ]

    cle = Identifiant()
    ctypes.windll.ole32.CLSIDFromString(identifiant, ctypes.byref(cle))
    chemin = ctypes.c_void_p()
    refus = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(cle), 0, None, ctypes.byref(chemin)
    )
    try:
        if refus or not chemin.value:
            raise InstallationImpossible(
                "Windows n'a pas dit où se trouvent le bureau et le menu Démarrer."
            )
        return Path(ctypes.wstring_at(chemin.value))
    finally:
        ctypes.windll.ole32.CoTaskMemFree(chemin)


def _ecrire(raccourci: Raccourci, cible: Path) -> None:
    environnement = {
        **os.environ,
        "PASTORY_RACCOURCI": str(raccourci.chemin),
        "PASTORY_CIBLE": str(cible),
        "PASTORY_ARGUMENTS": raccourci.arguments,
        "PASTORY_DEPART": str(dossier_du_projet()),
        "PASTORY_ICONE": str(icone()),
        "PASTORY_DESCRIPTION": raccourci.description,
    }
    try:
        resultat = subprocess.run(  # noqa: S603 - l'outil du système, une commande fixe
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ECRIRE_UN_RACCOURCI],
            env=environnement,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as erreur:
        raise InstallationImpossible(
            f"PowerShell, l'outil de Windows qui écrit les raccourcis, n'a pas répondu : {erreur}"
        ) from erreur
    if resultat.returncode != 0 or not raccourci.chemin.is_file():
        detail = resultat.stderr.decode("utf-8", errors="replace").strip()
        raise InstallationImpossible(
            f"Le raccourci {raccourci.chemin} n'a pas pu être écrit."
            + (f" Ce que Windows en dit : {detail}" if detail else "")
        )
