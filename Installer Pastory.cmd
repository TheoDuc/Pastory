@echo off
rem Installation de Pastory : un double-clic sur ce fichier.
rem   1. installe Python et les bibliotheques de Pastory, dans ce dossier (.venv) ;
rem   2. cree les raccourcis du bureau et du menu Demarrer.
rem Rien n'est installe ailleurs. A relancer si ce dossier est deplace ou renomme.
rem
rem Ce fichier est ecrit sans accents : la fenetre de commandes de Windows ne les affiche
rem pas de la meme facon d'un ordinateur a l'autre.
setlocal
cd /d "%~dp0"
title Installation de Pastory

echo.
echo   Installation de Pastory
echo   -----------------------
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo   L'outil "uv" est introuvable. C'est lui qui installe Python et les
    echo   bibliotheques dont Pastory a besoin.
    echo.
    echo   Installez-le d'abord, en suivant le fichier README.md de ce dossier
    echo   ^(https://docs.astral.sh/uv/getting-started/installation/^),
    echo   puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)

rem Les certificats de Windows plutot que ceux d'uv : un antivirus qui inspecte les
rem connexions securisees (Norton, Avast...) fait sinon echouer les telechargements.
set UV_NATIVE_TLS=1

echo   1/2  Python et les bibliotheques ^(quelques minutes la premiere fois^)...
echo.
uv sync
if errorlevel 1 (
    echo.
    echo   L'installation des bibliotheques a echoue : le message ci-dessus dit pourquoi.
    echo   Les causes les plus courantes : pas de connexion a Internet, un antivirus qui
    echo   bloque le telechargement, ou ce dossier range dans OneDrive.
    echo.
    pause
    exit /b 1
)

echo.
echo   2/2  Les raccourcis...
echo.
".venv\Scripts\python.exe" -m pastory.cli installer
if errorlevel 1 (
    echo.
    echo   Les raccourcis n'ont pas pu etre crees : le message ci-dessus dit pourquoi.
    echo.
    pause
    exit /b 1
)

echo.
echo   Pastory est installe. Vous pouvez fermer cette fenetre.
echo.
pause
