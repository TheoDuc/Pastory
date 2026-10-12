"""Le lanceur : ce que fait le raccourci de Pastory (étape 10, D-106).

    .venv\\Scripts\\pythonw.exe -m pastory.lanceur

Il ouvre Pastory **comme un logiciel** : aucune fenêtre noire, une fenêtre à part sans barre
d'adresse, et tout s'arrête quand on la ferme. Dans l'ordre :

1. **le journal.** Lancé par `pythonw`, le programme n'a pas d'écran où écrire : ce qu'il aurait
   affiché va dans `journal.txt`, dans le dossier personnel ;
2. **le port.** Si Pastory tourne déjà, sa fenêtre revient au premier plan et rien d'autre ne
   démarre. Sinon le port est **pris tout de suite**, avant le chargement de l'interface — un
   second double-clic impatient trouve ainsi la place occupée, au lieu de lancer un double ;
3. **la fenêtre**, ouverte elle aussi tout de suite : la page attend à la porte que l'interface
   ait fini de se charger, et l'utilisateur voit qu'il se passe quelque chose ;
4. **l'interface**, puis **la veille** (`vues/veille.py`), qui arrête le serveur quand plus
   aucune page n'est ouverte.

Une erreur au démarrage ne peut pas rester muette — un double-clic qui ne fait rien est la pire
des pannes : elle s'affiche dans une boîte de message, et son détail va au journal.

`pastory ouvrir`, dans un terminal, reste ce qu'il était : sans veille, arrêté par Ctrl+C.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from pastory import demonstration as portefeuille_fictif
from pastory.config import emplacements
from pastory.demonstration import TITRE_DE_LA_FENETRE as TITRE_DE_LA_DEMONSTRATION
from pastory.vues import veille as veille_des_pages

NOM = "Pastory"
HOTE = "127.0.0.1"
PREMIER_PORT = 8050
PORTS_ESSAYES = 10

NOM_DU_JOURNAL = "journal.txt"
TAILLE_MAXIMALE_DU_JOURNAL = 1_000_000
"""Au-delà, le journal repart de zéro à l'ouverture suivante : il sert à comprendre la dernière
panne, pas à garder l'histoire."""

PATIENCE = 30.0
"""Secondes laissées à un Pastory en train de démarrer pour répondre « c'est moi »."""

CLASSE_DES_FENETRES = "Chrome_WidgetWin_1"
"""La classe des fenêtres d'Edge et de Chrome. Sans ce contrôle, le dossier « Pastory » ouvert
dans l'explorateur de fichiers, qui porte le même titre, serait pris pour l'application."""


class AucunPortLibre(Exception):
    pass


# --- Le journal ---------------------------------------------------------------------------


def ouvrir_le_journal() -> Path | None:
    """Envoie au journal ce que le programme aurait écrit à l'écran, **s'il n'a pas d'écran**.

    Lancé depuis un terminal, il garde son écran : c'est là qu'on regarde quand on cherche une
    panne.
    """
    if sys.stderr is not None and sys.stdout is not None:
        return None
    dossier = emplacements.dossier_personnel()
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / NOM_DU_JOURNAL
    if chemin.exists() and chemin.stat().st_size > TAILLE_MAXIMALE_DU_JOURNAL:
        chemin.unlink()
    flux = chemin.open("a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = flux
    print(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} · ouverture de {NOM}")
    return chemin


def avertir(message: str) -> None:
    """Dit une panne de démarrage à l'utilisateur, qui n'a pas de terminal sous les yeux."""
    print(message, file=sys.stderr)
    if sys.platform == "win32":
        import ctypes

        icone_d_erreur = 0x10
        ctypes.windll.user32.MessageBoxW(None, message, NOM, icone_d_erreur)


# --- Le port ------------------------------------------------------------------------------


def prendre(port: int) -> socket.socket | None:
    """Prend le port, ou rend `None` s'il est occupé."""
    prise = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            # Sous Windows, deux programmes peuvent écouter le même port si rien ne l'interdit.
            prise.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            prise.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        prise.bind((HOTE, port))
        prise.listen()
    except OSError:
        prise.close()
        return None
    return prise


def qui_repond(port: int, patience: float = PATIENCE) -> dict | None:
    """Ce que répond l'adresse de vie de ce port, ou `None` si ce n'est pas un Pastory.

    Un Pastory qui démarre tient déjà son port sans répondre encore : la question attend dans
    sa file, d'où la patience. Et une connexion locale coupée en route (l'antivirus du
    propriétaire) ne doit pas faire conclure « ce n'est pas lui » : on redemande.
    """
    sans_intermediaire = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    adresse = f"http://{HOTE}:{port}{veille_des_pages.CHEMIN}"
    limite = time.monotonic() + patience
    for _ in range(3):
        reste = limite - time.monotonic()
        if reste <= 0:
            break
        try:
            with sans_intermediaire.open(adresse, timeout=reste) as reponse:
                contenu = json.loads(reponse.read().decode("utf-8"))
        except urllib.error.HTTPError:
            return None  # un autre programme, qui répond autre chose
        except (OSError, ValueError):
            continue
        return contenu if isinstance(contenu, dict) else None
    return None


def premier_port(demonstration: bool) -> int:
    return PREMIER_PORT + (PORTS_ESSAYES if demonstration else 0)


def reserver(
    demonstration: bool,
    prendre: Callable[[int], socket.socket | None] = prendre,
    qui_repond: Callable[[int], dict | None] = qui_repond,
) -> tuple[int, socket.socket | None]:
    """Le port de Pastory, et la prise sur ce port — `None` s'il y tourne déjà.

    La démonstration a ses propres ports : elle peut s'ouvrir à côté du vrai portefeuille, et
    un Pastory ne répond jamais à la place de l'autre.
    """
    premier = premier_port(demonstration)
    for port in range(premier, premier + PORTS_ESSAYES):
        prise = prendre(port)
        if prise is not None:
            return port, prise
        present = qui_repond(port)
        if (
            present is not None
            and present.get("application") == NOM
            and bool(present.get("demonstration")) == demonstration
        ):
            return port, None
    raise AucunPortLibre(
        f"Les ports {premier} à {premier + PORTS_ESSAYES - 1} de cet ordinateur sont tous "
        "occupés par d'autres programmes."
    )


# --- La fenêtre ---------------------------------------------------------------------------


def navigateur_application(
    environnement: Mapping[str, str] | None = None, plateforme: str | None = None
) -> Path | None:
    """Edge ou Chrome, qui savent ouvrir une page dans une fenêtre sans barre d'adresse."""
    environnement = os.environ if environnement is None else environnement
    plateforme = sys.platform if plateforme is None else plateforme
    if plateforme == "win32":
        racines = [
            environnement.get(variable)
            for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")
        ]
        candidats = [
            Path(racine) / editeur / "Application" / programme
            for editeur, programme in (
                (Path("Microsoft") / "Edge", "msedge.exe"),
                (Path("Google") / "Chrome", "chrome.exe"),
            )
            for racine in racines
            if racine
        ]
    elif plateforme == "darwin":
        candidats = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ]
    else:
        candidats = [
            Path(trouve)
            for nom in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge")
            if (trouve := shutil.which(nom))
        ]
    return next((candidat for candidat in candidats if candidat.is_file()), None)


def ouvrir_la_fenetre(adresse: str) -> None:
    """Une fenêtre à part sur `adresse` ; à défaut d'Edge et de Chrome, un onglet du
    navigateur habituel — Pastory s'y utilise et s'y arrête de la même façon."""
    navigateur = navigateur_application()
    if navigateur is None:
        webbrowser.open(adresse)
        return
    subprocess.Popen(  # noqa: S603 - un navigateur trouvé à son emplacement d'installation
        [str(navigateur), f"--app={adresse}"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def titre_de_la_fenetre(demonstration: bool) -> str:
    return TITRE_DE_LA_DEMONSTRATION if demonstration else NOM


def ramener_la_fenetre(titre: str) -> bool:
    """Remet au premier plan la fenêtre de Pastory déjà ouverte. `False` si elle n'est pas
    trouvée — ou ailleurs que sous Windows, où l'on ouvre simplement une fenêtre de plus."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    fenetres = ctypes.windll.user32
    trouvees: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def regarder(fenetre, _):
        if fenetres.IsWindowVisible(fenetre):
            texte = ctypes.create_unicode_buffer(256)
            classe = ctypes.create_unicode_buffer(256)
            fenetres.GetWindowTextW(fenetre, texte, 256)
            fenetres.GetClassNameW(fenetre, classe, 256)
            if texte.value == titre and classe.value == CLASSE_DES_FENETRES:
                trouvees.append(fenetre)
        return True

    fenetres.EnumWindows(regarder, 0)
    if not trouvees:
        return False
    restaurer = 9
    if fenetres.IsIconic(trouvees[0]):
        fenetres.ShowWindow(trouvees[0], restaurer)
    return bool(fenetres.SetForegroundWindow(trouvees[0]))


# --- Le lancement -------------------------------------------------------------------------


def veiller(
    veille: veille_des_pages.Veille,
    arreter: Callable[[], None],
    dormir: Callable[[float], None] = time.sleep,
) -> None:
    """Bat jusqu'à ce que plus aucune page ne soit ouverte, puis arrête le serveur."""
    while not veille.battre():
        dormir(veille_des_pages.BATTEMENT)
    arreter()


def lancer(demonstration: bool = False) -> int:
    port, prise = reserver(demonstration)
    adresse = f"http://{HOTE}:{port}/"
    if prise is None:
        print(f"{NOM} tourne déjà sur {adresse}")
        if not ramener_la_fenetre(titre_de_la_fenetre(demonstration)):
            ouvrir_la_fenetre(adresse)
        return 0

    ouvrir_la_fenetre(adresse)

    # Chargés seulement maintenant : Dash et pandas prennent plusieurs secondes, et un Pastory
    # déjà ouvert n'en a pas besoin pour revenir au premier plan.
    import logging

    from werkzeug.serving import make_server

    from pastory.vues import application
    from pastory.vues.chiffres import Chiffres

    # Une ligne par demande, soit un signe de vie toutes les cinq secondes : le journal n'en
    # garde que les avertissements.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    veille = veille_des_pages.Veille()
    interface = application.creer(Chiffres(demonstration=demonstration), veille)
    serveur = make_server(HOTE, port, interface.server, threaded=True, fd=prise.fileno())
    threading.Thread(target=veiller, args=(veille, serveur.shutdown), daemon=True).start()
    print(f"{NOM} est ouvert sur {adresse}")
    serveur.serve_forever()
    print(f"{NOM} est fermé.")
    return 0


def main(arguments: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        prog="pastory.lanceur", description="Ouvre Pastory dans sa fenêtre."
    )
    analyseur.add_argument(
        "--demonstration",
        action="store_true",
        help="ouvrir le portefeuille fictif, dans son dossier à part",
    )
    try:
        # `parse_known_args` : un argument inattendu ferait quitter le programme sans un mot,
        # et un raccourci qui ne fait rien est la panne à éviter.
        options, _ = analyseur.parse_known_args(arguments)
        if options.demonstration:
            # Avant le journal, qui s'écrit dans le dossier personnel : celui de la
            # démonstration, dès maintenant.
            portefeuille_fictif.preparer()
        ouvrir_le_journal()
        return lancer(options.demonstration)
    except AucunPortLibre as erreur:
        avertir(f"{NOM} n'a pas pu s'ouvrir. {erreur}")
        return 1
    except Exception:  # noqa: BLE001 - une panne de démarrage ne doit jamais rester muette
        traceback.print_exc()
        avertir(
            f"{NOM} n'a pas pu s'ouvrir : c'est un défaut du programme, pas de vos données. "
            f"Le détail est écrit dans le fichier « {NOM_DU_JOURNAL} » du dossier "
            f"{emplacements.dossier_personnel()}."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
