"""L'application Dash : `uv run pastory ouvrir` (D-31).

Elle tourne **sur l'ordinateur de l'utilisateur**, n'écoute que lui (`127.0.0.1`) et s'ouvre
dans son navigateur. Elle ne charge rien sur le réseau pour s'afficher : la feuille de style, les
polices et le script de dessin sont dans `assets/` (conception §3.2).

Trois rappels font tout :

- **choisir** : un clic sur un bouton de choix (onglet, période, poche, tri…) change l'état ;
- **rendre** : l'état change, l'écran est reconstruit en Python à partir des chiffres ;
- **déposer** : un export glissé dans la zone de dépôt est vérifié, rangé, et tout est relu.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

from pastory.vues import bandeau, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues.chiffres import Chiffres, Echec, poches_du
from pastory.vues.reception import recevoir

DOSSIER_DES_ASSETS = Path(__file__).parent / "assets"
PORT_PAR_DEFAUT = 8050

INDEX = """<!DOCTYPE html>
<html lang="fr">
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
  </head>
  <body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
  </body>
</html>"""

DEFILER_VERS_L_ANCRE = """
function (enfants, etat) {
    if (etat && etat.ancre) {
        window.requestAnimationFrame(function () {
            var cible = document.getElementById(etat.ancre);
            if (cible) { cible.scrollIntoView({block: "start", behavior: "smooth"}); }
        });
    }
    return window.dash_clientside.no_update;
}
"""


def creer(chiffres: Chiffres) -> Dash:
    """L'application, branchée sur `chiffres`. Séparée du lancement pour être testée."""
    application = Dash(
        __name__,
        assets_folder=str(DOSSIER_DES_ASSETS),
        title="Pastory",
        update_title=None,
        suppress_callback_exceptions=True,
        serve_locally=True,
    )
    application.index_string = INDEX
    application.layout = _mise_en_page()

    @application.callback(
        Output("etat", "data"),
        Input({"choix": ALL, "valeur": ALL}, "n_clicks"),
        State("etat", "data"),
        prevent_initial_call=True,
    )
    def choisir(_clics, etat):
        # Un bouton qui vient d'apparaître déclenche ce rappel avec zéro clic : seul un vrai
        # clic change l'état.
        if not ctx.triggered_id or not any(t["value"] for t in ctx.triggered):
            raise PreventUpdate
        declencheur = ctx.triggered_id
        return etat_ecran.appliquer(
            etat, declencheur["choix"], declencheur["valeur"], _poches_presentes(chiffres)
        )

    @application.callback(
        Output("onglets", "children"),
        Output("signalements", "children"),
        Output("filtres", "children"),
        Output("filtres", "hidden"),
        Output("etat-des-donnees", "children"),
        Output("corps", "children"),
        Input("etat", "data"),
    )
    def rendre(etat):
        return _rendre(chiffres, etat or etat_ecran.initial())

    @application.callback(
        Output("etat", "data", allow_duplicate=True),
        Input("depot", "contents"),
        State("depot", "filename"),
        State("etat", "data"),
        prevent_initial_call=True,
    )
    def deposer(contenus, noms, etat):
        if not contenus:
            raise PreventUpdate
        dossier = chiffres.dossier()
        receptions = [
            recevoir(nom, contenu, dossier)
            for nom, contenu in zip(noms, contenus, strict=True)
        ]
        if any(r.fichier is not None for r in receptions):
            chiffres.relire()
        return {
            **etat,
            "onglet": bandeau.ACCUEIL,
            "message": [{"accepte": r.accepte, "texte": r.message} for r in receptions],
            "version": chiffres.version,
        }

    @application.callback(
        Output("ouvrir-dossier", "title"),
        Input("ouvrir-dossier", "n_clicks"),
        prevent_initial_call=True,
    )
    def ouvrir_le_dossier(clics):
        if not clics:
            raise PreventUpdate
        _ouvrir(chiffres.dossier())
        return no_update

    application.clientside_callback(
        DEFILER_VERS_L_ANCRE,
        Output("corps", "className"),
        Input("corps", "children"),
        State("etat", "data"),
    )
    return application


def _mise_en_page() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="etat", data=etat_ecran.initial()),
            html.Header(
                [
                    html.Div(
                        [
                            bandeau.marque(),
                            html.Nav(
                                id="onglets",
                                className="onglets",
                                role="tablist",
                                **{"aria-label": "Sections"},
                            ),
                            html.Div(id="signalements", className="pousse"),
                        ],
                        className="bande bande--titre",
                    ),
                    html.Div(id="filtres", className="bande bande--filtres", hidden=True),
                    html.Div(id="etat-des-donnees", className="bande bande--etat"),
                ],
                className="entete",
            ),
            html.Main(
                dcc.Loading(
                    html.Div(id="corps"),
                    custom_spinner=html.P(
                        "Lecture de vos exports et calcul des chiffres… La première ouverture "
                        "interroge les sources de cours et de composition : elle peut prendre "
                        "une minute.",
                        className="chargement",
                    ),
                    delay_show=400,
                ),
                className="page",
            ),
        ]
    )


def _poches_presentes(chiffres: Chiffres) -> list[str]:
    base = chiffres.base()
    if isinstance(base, Echec):
        return []
    return [poche.value for poche in poches_du(base.portefeuille)]


def _rendre(chiffres: Chiffres, etat: dict) -> tuple:
    """Les six morceaux de l'écran. Une erreur du programme se **dit** à l'écran, avec de quoi
    la signaler : une page blanche laisserait croire que le portefeuille est vide — exactement
    l'erreur que l'application s'interdit sur les chiffres."""
    try:
        return ecrans.rendre(chiffres, etat)
    except Exception:  # noqa: BLE001 - le filet de sécurité de tout l'écran
        detail = traceback.format_exc()
        avis = html.Div(
            [
                html.Section(
                    [
                        html.Div(
                            html.H2("Cet écran n'a pas pu se dessiner", className="bloc__titre"),
                            className="bloc__entete",
                        ),
                        html.P(
                            "C'est un défaut du programme, pas de vos données : vos fichiers ne "
                            "sont pas touchés. Les autres onglets restent utilisables. Pour le "
                            "signaler, copiez le détail ci-dessous.",
                            className="chapeau",
                        ),
                        html.Details(
                            [html.Summary("Détail technique"), html.Pre(detail, className="trace")]
                        ),
                    ],
                    className="bloc",
                )
            ],
            className="rangee rangee--large",
        )
        return (
            bandeau.onglets(etat.get("onglet", "synthese")),
            [],
            [],
            True,
            [],
            avis,
        )


def _ouvrir(dossier: Path) -> None:
    """Ouvre le dossier dans l'explorateur de fichiers du système."""
    dossier.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(dossier)  # noqa: S606 - un dossier de l'utilisateur, ouvert à sa demande
    elif sys.platform == "darwin":
        subprocess.run(["open", str(dossier)], check=False)
    else:
        subprocess.run(["xdg-open", str(dossier)], check=False)


def lancer(
    hors_ligne: bool = False,
    dossier_export: Path | None = None,
    port: int = PORT_PAR_DEFAUT,
    navigateur: bool = True,
) -> None:
    """Démarre l'application et ouvre le navigateur. S'arrête avec Ctrl+C."""
    chiffres = Chiffres(dossier=dossier_export, hors_ligne=hors_ligne)
    application = creer(chiffres)
    adresse = f"http://127.0.0.1:{port}/"
    print(f"Pastory est ouvert dans votre navigateur : {adresse}")
    print("Laissez cette fenêtre ouverte pendant que vous l'utilisez ; Ctrl+C pour l'arrêter.")
    if navigateur:
        threading.Timer(1.0, webbrowser.open, args=(adresse,)).start()
    application.run(host="127.0.0.1", port=port, debug=False)

