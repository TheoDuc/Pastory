@echo off
rem Installation de Pastory : un double-clic sur ce fichier, et rien d'autre.
rem   1. trouve l'outil "uv", ou l'installe s'il manque ;
rem   2. installe Python et les bibliotheques de Pastory, dans ce dossier (.venv) ;
rem   3. cree les raccourcis du bureau et du menu Demarrer.
rem A relancer si ce dossier est deplace ou renomme.
rem
rem Ce fichier est ecrit sans accents : la fenetre de commandes de Windows ne les affiche
rem pas de la meme facon d'un ordinateur a l'autre.
setlocal
rem pushd, et non cd : il sait aussi entrer dans un dossier partage sur le reseau.
pushd "%~dp0"
title Installation de Pastory

echo.
echo   Installation de Pastory
echo   -----------------------
echo.

rem Un double-clic dans l'archive ZIP, sans l'avoir decompressee, ne lance que ce fichier,
rem seul, depuis un dossier temporaire : le reste de Pastory n'y est pas.
if not exist "pyproject.toml" (
    echo   Ce fichier n'est pas dans le dossier de Pastory : il a sans doute ete lance
    echo   depuis l'archive ZIP, sans la decompresser.
    echo.
    echo   Decompressez d'abord l'archive ^(clic droit sur le fichier ZIP, puis
    echo   "Extraire tout"^), ouvrez le dossier obtenu, et relancez ce fichier de la.
    echo.
    pause
    exit /b 1
)

call :trouver_uv
if defined UV echo   1/3  L'outil "uv" : deja installe.
if defined UV echo.
if not defined UV call :installer_uv
if not defined UV (
    echo.
    echo   L'outil "uv" n'a pas pu etre installe : le message ci-dessus dit pourquoi.
    echo   Verifiez la connexion a Internet, puis relancez ce fichier.
    echo.
    echo   Si cela echoue encore, installez-le a la main en suivant
    echo   https://docs.astral.sh/uv/getting-started/installation/
    echo   puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)

rem Les certificats de Windows plutot que ceux d'uv : un antivirus qui inspecte les
rem connexions securisees (Norton, Avast...) fait sinon echouer les telechargements.
rem Ce reglage a change de nom d'une version d'uv a l'autre : on donne a chacune le sien.
call "%UV%" --help 2>nul | findstr /c:"--system-certs" >nul
if errorlevel 1 (set UV_NATIVE_TLS=1) else (set UV_SYSTEM_CERTS=1)
rem Des copies plutot que des liens : dans un dossier synchronise (OneDrive), les liens
rem echouent.
set UV_LINK_MODE=copy

rem La version de Python est fixee par le fichier ".python-version" de ce dossier : sans
rem lui, uv prend le Python le plus recent, pour lequel les bibliotheques n'existent pas
rem toujours toutes pretes - il essaie alors de les fabriquer, et echoue.
echo   2/3  Python et les bibliotheques ^(quelques minutes la premiere fois^)...
echo.
rem "call" : si uv est lui-meme un fichier de commandes, ce fichier-ci doit reprendre la main.
call "%UV%" sync
if errorlevel 1 (
    rem Dans un dossier synchronise, le premier essai peut buter sur un fichier que la
    rem synchronisation tient encore : le second passe.
    echo.
    echo   Premier essai interrompu : nouvel essai...
    echo.
    call "%UV%" sync
)
if errorlevel 1 (
    echo.
    echo   L'installation des bibliotheques a echoue : le message ci-dessus dit pourquoi.
    echo   Les causes les plus courantes :
    echo     - pas de connexion a Internet ;
    echo     - "invalid peer certificate" : un antivirus inspecte les connexions securisees.
    echo       Suspendez son analyse HTTPS le temps de l'installation, puis relancez ;
    echo     - "Acces refuse" : ce dossier est range dans OneDrive. Deplacez-le ailleurs,
    echo       par exemple dans C:\Pastory, puis relancez ce fichier de la ;
    echo     - "failed to build" : une bibliotheque n'existe pas toute prete pour le Python
    echo       employe. Verifiez que le fichier ".python-version" est bien dans ce dossier
    echo       ^(il fixe la version de Python^) : s'il manque, telechargez Pastory de nouveau.
    echo.
    pause
    exit /b 1
)

echo.
echo   3/3  Les raccourcis...
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
echo   Pastory est installe : son icone est sur le bureau et dans le menu Demarrer.
echo   Vous pouvez fermer cette fenetre.
echo.
pause
exit /b 0


rem --- Trouver uv ---------------------------------------------------------------------
rem Dans le chemin de recherche de Windows d'abord, puis la ou son installateur le range.
rem Un uv tout juste installe n'est pas encore dans le chemin de recherche des fenetres
rem deja ouvertes, ni toujours dans celui des suivantes : le chercher a son emplacement
rem evite de repondre "introuvable" a quelqu'un qui vient de l'installer.
:trouver_uv
set "UV="
for /f "delims=" %%U in ('where uv 2^>nul') do if not defined UV set "UV=%%U"
if defined UV exit /b 0
for %%D in ("%UV_INSTALL_DIR%" "%XDG_BIN_HOME%" "%USERPROFILE%\.local\bin" "%USERPROFILE%\.cargo\bin") do (
    if not defined UV if not "%%~D"=="" if exist "%%~D\uv.exe" set "UV=%%~D\uv.exe"
)
exit /b 0


rem --- Installer uv -------------------------------------------------------------------
rem Par la methode officielle de son editeur, la meme que celle du fichier README.md.
:installer_uv
echo   1/3  L'outil "uv"
echo.
echo   Pastory a besoin de "uv", un outil libre qui installe Python et les bibliotheques.
echo   Il n'est pas encore sur cet ordinateur. Ce fichier va le telecharger sur le site
echo   de son editeur ^(astral.sh^) et l'installer dans votre dossier personnel.
echo.
echo   Appuyez sur une touche pour continuer, ou fermez cette fenetre pour ne rien installer.
pause >nul
echo.
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
echo.
call :trouver_uv
exit /b 0
