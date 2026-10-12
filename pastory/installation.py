"""Les raccourcis de Pastory : `pastory installer` (étape 10, D-106).

Un raccourci sur le bureau et dans le menu Démarrer, avec le logo, qui appelle le lanceur
(`pastory/lanceur.py`). C'est tout ce que « installer » veut dire ici : aucun fichier n'est
copié ailleurs, rien n'est inscrit dans le système, et `pastory installer --retirer` défait tout.

**Le raccourci pointe sur ce dossier-ci.** Il appelle le Python de l'environnement du projet,
par son chemin : jamais `uv run`, qui voudrait d'abord réinstaller le projet et peut échouer
là où l'environnement, lui, fonctionne. Si le dossier du projet est déplacé ou renommé, les
raccourcis sont à recréer.

Sous Windows seulement, pour l'instant. Un fichier `.lnk` ne s'écrit pas en Python sans
bibliothèque de plus : c'est l'outil du système qui le fait (`WScript.Shell`, par PowerShell),
et les valeurs lui sont passées par l'environnement, pour qu'un chemin accentué arrive intact.
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


def python_sans_fenetre() -> Path:
    """Le Python de cet environnement, dans sa version qui n'ouvre pas de fenêtre noire."""
    return Path(sys.executable).with_name("pythonw.exe")


def icone() -> Path:
    return Path(__file__).resolve().parent / "vues" / "assets" / "favicon.ico"


def raccourcis(bureau: Path, programmes: Path) -> list[Raccourci]:
    """Pastory sur le bureau et dans le menu Démarrer ; la démonstration dans le menu
    seulement, pour ne pas encombrer le bureau d'une icône qui sert rarement."""
    lanceur = "-m pastory.lanceur"
    menu = programmes / NOM
    ouvrir = f"Ouvrir {NOM}, le tableau de bord de vos actifs"
    return [
        Raccourci(bureau / f"{NOM}.lnk", lanceur, ouvrir),
        Raccourci(menu / f"{NOM}.lnk", lanceur, ouvrir),
        Raccourci(
            menu / f"{NOM_DE_LA_DEMONSTRATION}.lnk",
            f"{lanceur} --demonstration",
            f"Ouvrir {NOM} sur un portefeuille fictif",
        ),
    ]


def installer() -> list[Raccourci]:
    """Crée les raccourcis, en remplaçant ceux d'une installation précédente."""
    crees = raccourcis(*_emplacements())
    cible = python_sans_fenetre()
    if not cible.is_file():
        raise InstallationImpossible(
            f"Le programme {cible} est introuvable : l'environnement de {NOM} n'est pas "
            "installé dans ce dossier."
        )
    for raccourci in crees:
        raccourci.chemin.parent.mkdir(parents=True, exist_ok=True)
        _ecrire(raccourci, cible)
    return crees


def retirer() -> list[Raccourci]:
    """Supprime les raccourcis, et le dossier du menu Démarrer s'il est vide. Rend ceux qui
    existaient."""
    retires = []
    for raccourci in raccourcis(*_emplacements()):
        if raccourci.chemin.is_file():
            raccourci.chemin.unlink()
            retires.append(raccourci)
        dossier = raccourci.chemin.parent
        if dossier.name == NOM and dossier.is_dir() and not any(dossier.iterdir()):
            dossier.rmdir()
    return retires


def _emplacements() -> tuple[Path, Path]:
    if sys.platform != "win32":
        raise InstallationImpossible(
            "Les raccourcis ne sont créés que sous Windows pour l'instant. Sur cet "
            f"ordinateur, {NOM} s'ouvre par la commande :\n"
            f"  {sys.executable} -m pastory.lanceur"
        )
    return _dossier_connu(BUREAU), _dossier_connu(PROGRAMMES)


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
