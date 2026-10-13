#!/bin/sh
# Installation de Pastory sous Linux et macOS. Dans un terminal, depuis ce dossier :
#
#     sh installer-pastory.sh
#
#   1. trouve l'outil "uv", ou l'installe s'il manque ;
#   2. installe Python et les bibliotheques de Pastory, dans ce dossier (.venv) ;
#   3. ajoute Pastory au menu des applications (Linux) ou au bureau (macOS).
# A relancer si ce dossier est deplace ou renomme.
#
# Sous Windows, ce n'est pas ce fichier : double-cliquez sur "Installer Pastory.cmd".
#
# Ecrit sans accents, comme le fichier de Windows, pour s'afficher partout de la meme facon.

set -u

dire() { printf '%s\n' "$*"; }

echouer() {
    dire ""
    for ligne in "$@"; do dire "  $ligne"; done
    dire ""
    exit 1
}

cd "$(dirname "$0")" || echouer "Impossible d'entrer dans le dossier de Pastory."

dire ""
dire "  Installation de Pastory"
dire "  -----------------------"
dire ""

case "$(uname -s 2>/dev/null)" in
    MINGW* | MSYS* | CYGWIN*)
        echouer "Ce fichier est fait pour Linux et macOS." \
            "Sous Windows, double-cliquez sur \"Installer Pastory.cmd\", dans ce dossier."
        ;;
esac

[ -f pyproject.toml ] || echouer \
    "Ce fichier n'est pas dans le dossier de Pastory." \
    "Decompressez d'abord l'archive, puis relancez-le depuis le dossier obtenu."

# --- 1. uv -------------------------------------------------------------------------------
# Dans le chemin de recherche d'abord, puis la ou son installateur le range : un uv tout
# juste installe n'est pas encore dans le chemin de recherche du terminal deja ouvert.
trouver_uv() {
    UV=$(command -v uv 2>/dev/null || true)
    [ -n "$UV" ] && return 0
    for dossier in "${UV_INSTALL_DIR:-}" "${XDG_BIN_HOME:-}" "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -n "$dossier" ] && [ -x "$dossier/uv" ]; then
            UV="$dossier/uv"
            return 0
        fi
    done
    return 1
}

if trouver_uv; then
    dire "  1/3  L'outil \"uv\" : deja installe."
    dire ""
else
    dire "  1/3  L'outil \"uv\""
    dire ""
    dire "  Pastory a besoin de \"uv\", un outil libre qui installe Python et les bibliotheques."
    dire "  Il n'est pas encore sur cet ordinateur. Ce fichier va le telecharger sur le site"
    dire "  de son editeur (astral.sh) et l'installer dans votre dossier personnel."
    dire ""
    printf '  Appuyez sur Entree pour continuer, ou sur Ctrl+C pour ne rien installer. '
    read -r _ || exit 1
    dire ""
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echouer "Ni \"curl\" ni \"wget\" ne sont installes : impossible de telecharger uv." \
            "Installez l'un des deux (ou uv lui-meme :" \
            "https://docs.astral.sh/uv/getting-started/installation/), puis relancez ce fichier."
    fi
    dire ""
    trouver_uv || echouer \
        "L'outil \"uv\" n'a pas pu etre installe : le message ci-dessus dit pourquoi." \
        "Verifiez la connexion a Internet, puis relancez ce fichier."
fi

# --- 2. Python et les bibliotheques ------------------------------------------------------
# La version de Python est fixee par le fichier ".python-version" de ce dossier : sans lui,
# uv prend le Python le plus recent, pour lequel les bibliotheques n'existent pas toujours
# toutes pretes - il essaie alors de les fabriquer, et echoue.
dire "  2/3  Python et les bibliotheques (quelques minutes la premiere fois)..."
dire ""
"$UV" sync || echouer \
    "L'installation des bibliotheques a echoue : le message ci-dessus dit pourquoi." \
    "Les causes les plus courantes :" \
    "  - pas de connexion a Internet ;" \
    "  - \"failed to build\" : le fichier \".python-version\" manque dans ce dossier." \
    "    Telechargez Pastory de nouveau."

# --- 3. Les raccourcis -------------------------------------------------------------------
dire ""
dire "  3/3  Les raccourcis..."
dire ""
PYTHON=".venv/bin/python"
[ -x "$PYTHON" ] || echouer "L'environnement de Pastory est introuvable ($PYTHON)."
if ! "$PYTHON" -m pastory.cli installer; then
    dire ""
    dire "  Les raccourcis n'ont pas pu etre crees : le message ci-dessus dit pourquoi."
    dire "  Pastory est installe quand meme. Pour l'ouvrir, dans un terminal, depuis ce dossier :"
    dire ""
    dire "      $PYTHON -m pastory.lanceur"
    dire ""
    exit 1
fi

dire ""
dire "  Pastory est installe. S'il n'apparait pas tout de suite dans le menu, il s'ouvre"
dire "  aussi depuis ce dossier, dans un terminal :"
dire ""
dire "      $PYTHON -m pastory.lanceur"
dire ""
