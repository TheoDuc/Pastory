"""Script d'exportation des transactions Trade Republic — **à reprendre**.

Premier jet écrit avant le cadrage du projet. Il est conservé pour ce qu'il montre de
l'appel à pytr, mais il n'est pas branché sur l'application. Deux choses sont à corriger
avant de le réutiliser :

- le **PIN est passé en argument de commande** (`-p`), ce que D-25 interdit : un argument de
  commande est visible par les autres programmes de la machine et reste dans l'historique du
  terminal. Les trois modes de stockage au choix de l'utilisateur sont écrits à l'étape 10 ;
- l'export est écrit dans `./data`, à l'intérieur du dossier synchronisé par OneDrive, alors
  que D-37 le range dans le dossier personnel local.

La récupération des données devient la commande `dashboard rafraichir` à l'étape 2.
"""

import subprocess
import sys
from pathlib import Path

# Dossier d'exportation. Il est créé au moment de l'export, pas à l'import du module :
# importer un script ne doit rien écrire sur le disque.
OUTPUT_DIR = Path("./data")


def check_and_install_pytr():
    # Vérifie que le package soit installé
    try:
        import pytr  # noqa: F401
    except ImportError:
        print("[-] pytr n'est pas installé. Installation via uv...")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pytr",
                "--break-system-packages",
            ]
        )
        print("[+] pytr installé avec succès.")


def run_export():
    # Récupère les données du compte trade republic dans un csv
    check_and_install_pytr()
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("\n[+] Lancement de l'exportation des transactions Trade Republic...")

    phone_number = input(
        "Entrez votre numéro de téléphone Trade Republic (ex: +33612345678) : "
    )
    pin = input("Entrez votre code PIN TR (4 chiffres) : ")

    cmd = [
        sys.executable,
        "-m",
        "pytr.main",
        "export_transactions",
        "-n",
        phone_number,
        "-p",
        pin,
        "--v2",
        "--decimal-localization",
        "--outputdir",
        str(OUTPUT_DIR),
        "--export-format",
        "csv",
    ]

    try:
        subprocess.run(cmd, check=True)
        print(
            "\n[+] Exportation terminée avec succès ! Fichier disponible dans :"
            f" {OUTPUT_DIR.resolve()}"
        )
    except subprocess.CalledProcessError as e:
        print(f"\n[-] Erreur lors de l'exportation : {e}")


if __name__ == "__main__":
    run_export()
