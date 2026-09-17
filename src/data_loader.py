"""
Script d'exportation automatique des transactions Trade Republic
"""

from pathlib import Path
import subprocess
import sys

# Dossier d'exportation
OUTPUT_DIR = Path("./data")
OUTPUT_DIR.mkdir(exist_ok=True)


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
