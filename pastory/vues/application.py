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
from datetime import date as Date
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
from flask import jsonify, request

from pastory.vues import bandeau, ecrans, portefeuilles, projections
from pastory.vues import etat as etat_ecran
from pastory.vues.chiffres import Chiffres, Echec, poches_du
from pastory.vues.reception import recevoir
from pastory.vues.veille import CHEMIN as CHEMIN_DE_VIE
from pastory.vues.veille import (
    HOTE,
    PORT_PAR_DEFAUT,
    Veille,
    identite,
    titre_de_la_fenetre,
)

DOSSIER_DES_ASSETS = Path(__file__).parent / "assets"

SIGNE_DE_VIE = """
<script>
/* Le signe de vie (D-106). Ouvert par son raccourci, Pastory n'a pas de terminal : il s'arrête
   quand plus aucune page n'est ouverte, et c'est la page qui le lui dit (`veille.py`) — un
   signe toutes les cinq secondes, un adieu à la fermeture.

   Dans l'autre sens : si le serveur ne répond plus à plusieurs signes de suite, c'est qu'il est
   arrêté. La page le dit, plutôt que de rester là avec des boutons qui ne font plus rien. Un
   seul signe perdu ne suffit pas (l'antivirus du filet ci-dessous en coupe un sur dix), et
   l'avis s'efface de lui-même si le serveur répond de nouveau. */
(function () {
  var adresse = "{chemin}?page=" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  var echecs = 0;
  function avis() { return document.getElementById("pastory-arrete"); }
  function prevenir() {
    if (avis() || !document.body) { return; }
    var element = document.createElement("div");
    element.id = "pastory-arrete";
    // Aucune couleur ici (charte graphique) : la classe la prend dans le thème.
    element.className = "avis-d-arret";
    element.setAttribute("role", "alert");
    element.textContent = "Pastory est arrêté : cette page ne répond plus. Fermez-la, puis " +
      "rouvrez Pastory.";
    document.body.appendChild(element);
  }
  function signe() {
    if (!window.fetch) { return; }
    fetch(adresse, {method: "POST", keepalive: true}).then(function (reponse) {
      if (!reponse.ok) { throw new Error("refus"); }
      echecs = 0;
      if (avis()) { avis().remove(); }
    }).catch(function () {
      echecs += 1;
      if (echecs >= 4) { prevenir(); }
    });
  }
  signe();
  window.setInterval(signe, 5000);
  window.addEventListener("pageshow", function (evenement) {
    if (evenement.persisted) { signe(); }
  });
  window.addEventListener("pagehide", function () {
    if (navigator.sendBeacon) { navigator.sendBeacon(adresse + "&fin=1"); }
  });
  // Un navigateur peut endormir tout à fait une page masquée depuis longtemps : plus aucun
  // signe, et Pastory s'arrêterait sous une fenêtre simplement réduite. Chrome et Edge
  // disent ne pas endormir une page qui tient un verrou : elle en tient un, jamais rendu.
  // NON MESURÉ sur la durée (il faudrait des heures) : le cahier de l'étape 10 le demande.
  if (navigator.locks && navigator.locks.request) {
    navigator.locks.request(adresse, function () { return new Promise(function () {}); });
  }
})();
</script>
""".replace("{chemin}", CHEMIN_DE_VIE)

FILET_DE_CHARGEMENT = """
<script>
/* Le filet du chargement. Sur la machine du propriétaire, une connexion locale sur dix environ
   est coupée pendant le téléchargement des fichiers de la page — mesuré à l'étape 9, avec le
   serveur de Dash comme avec celui de Python : c'est l'environnement (un antivirus qui inspecte
   le trafic local), pas l'application. Un seul fichier perdu, et la page restait vide.

   Un fichier de script qui échoue fait recharger la page, deux fois au plus par minute ; au-delà,
   ou si la page n'est toujours pas là au bout de vingt secondes, un message en français le dit,
   avec un bouton pour réessayer. La page est « là » quand son bandeau existe. */
(function () {
  var CLE = "pastory-rechargements";
  var MAXIMUM = 2;
  function recents() {
    try {
      var liste = JSON.parse(sessionStorage.getItem(CLE) || "[]");
      return liste.filter(function (quand) { return Date.now() - quand < 60000; });
    } catch (e) { return [0, 0, 0]; }
  }
  function recharger() {
    try { sessionStorage.setItem(CLE, JSON.stringify(recents().concat([Date.now()]))); }
    catch (e) {}
    window.location.reload();
  }
  function prevenir() {
    if (document.querySelector(".entete") || document.getElementById("pastory-filet")) { return; }
    var avis = document.createElement("div");
    avis.id = "pastory-filet";
    // Aucune couleur ici (charte graphique) : la classe la prend dans le thème, s'il a pu se
    // charger ; sinon, le navigateur l'écrit en noir, ce qui reste lisible.
    avis.className = "filet-de-chargement";
    avis.innerHTML = "<p>La page n'a pas fini de se charger : une connexion a été coupée en " +
      "route, souvent par un antivirus qui inspecte le trafic de l'ordinateur. Vos données ne " +
      "sont pas en cause.</p><button type='button' class='bouton'>Réessayer</button>";
    avis.querySelector("button").onclick = function () {
      try { sessionStorage.removeItem(CLE); } catch (e) {}
      window.location.reload();
    };
    document.body.insertBefore(avis, document.body.firstChild);
  }
  window.addEventListener("error", function (evenement) {
    var cible = evenement.target;
    if (!cible || cible.tagName !== "SCRIPT") { return; }
    if (recents().length < MAXIMUM) { recharger(); } else { prevenir(); }
  }, true);
  window.setTimeout(prevenir, 20000);
})();
</script>
"""

THEME_AU_CHARGEMENT = """
<script>
/* Le thème, posé AVANT le premier affichage : sans cela, une page de nuit s'afficherait un
   instant en clair. Le choix fait avec le bouton jour / nuit est retenu par le navigateur ;
   sans choix, Pastory suit le réglage clair / sombre du système (D-100). */
(function () {
  var choix = null;
  try { choix = localStorage.getItem("pastory-theme"); } catch (e) {}
  var sombre = choix ? choix === "sombre"
    : !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", sombre ? "sombre" : "clair");
})();
</script>
"""

# Les icônes de l'onglet : le logo de Pastory (D-98), en .ico — que Dash annonce avec la date du
# fichier, ce qui force le navigateur à oublier l'icône de Dash qu'il a pu garder en cache — et en
# SVG, net à toutes les tailles. Le .ico sert aussi au raccourci du bureau.
INDEX = """<!DOCTYPE html>
<html lang="fr">
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
    {%css%}
""" + THEME_AU_CHARGEMENT + FILET_DE_CHARGEMENT + SIGNE_DE_VIE + """
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


def creer(chiffres: Chiffres, veille: Veille | None = None) -> Dash:
    """L'application, branchée sur `chiffres`. Séparée du lancement pour être testée.

    `veille` : donnée par le lanceur, qui arrête Pastory quand sa fenêtre se ferme (D-106).
    Sans elle — `pastory ouvrir` dans un terminal — rien ne s'arrête seul."""
    application = Dash(
        __name__,
        assets_folder=str(DOSSIER_DES_ASSETS),
        title=titre_de_la_fenetre(chiffres.demonstration),
        update_title=None,
        suppress_callback_exceptions=True,
        serve_locally=True,
    )
    application.index_string = INDEX
    application.layout = _mise_en_page(chiffres.demonstration)
    _brancher_la_vie(application, veille, chiffres.demonstration)

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
        Output("corps", "children"),
        Output("livre", "className"),
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
        # Toujours relire : un dépôt refusé en chemin a pu toucher au dossier, et l'écran
        # doit montrer ce qui s'y trouve, pas ce qui s'y trouvait.
        chiffres.relire()
        return {
            **etat,
            "onglet": bandeau.ACCUEIL,
            "message": [
                {"accepte": r.accepte, "texte": r.message, "mot": r.etiquette}
                for r in receptions
            ],
            # Un dépôt peut ouvrir un autre portefeuille : les poches cochées étaient
            # celles du précédent.
            "poches": None,
            "page": 0,
            "a_supprimer": None,
            "version": chiffres.version,
        }

    @application.callback(
        Output("etat", "data", allow_duplicate=True),
        Input({portefeuilles.CHAMP: ALL, "nom": ALL}, "n_clicks"),
        State({portefeuilles.RENOMMER: ALL}, "value"),
        State({portefeuilles.RENOMMER: ALL}, "id"),
        State("etat", "data"),
        prevent_initial_call=True,
    )
    def gerer_les_portefeuilles(_clics, saisies, champs, etat):
        # Ouvrir, renommer ou supprimer un portefeuille (D-109). Comme pour `choisir`, un
        # bouton qui vient d'apparaître déclenche ce rappel avec zéro clic.
        if not ctx.triggered_id or not any(t["value"] for t in ctx.triggered):
            raise PreventUpdate
        action, cle = ctx.triggered_id[portefeuilles.CHAMP], ctx.triggered_id["nom"]
        # Le bouton porte la clé du portefeuille, pas son nom : un accent dans un
        # identifiant fait perdre le clic à Dash (`portefeuilles.cle`).
        nom = portefeuilles.nom_de(cle)
        if nom is None:
            raise PreventUpdate
        saisie = next(
            (
                valeur
                for valeur, champ in zip(saisies, champs, strict=True)
                if champ[portefeuilles.RENOMMER] == cle
            ),
            None,
        )
        message = portefeuilles.agir(chiffres, action, nom, saisie)
        return {
            **etat,
            "onglet": bandeau.ACCUEIL,
            "message": [message] if message else None,
            "poches": None,
            "page": 0,
            "a_supprimer": None,
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

    @application.callback(
        Output("projection-montant", "children"),
        Output("projection-courbe", "children"),
        Input("projection-depart", "value"),
        Input("projection-taux", "value"),
        Input("projection-duree", "value"),
        Input("projection-versement", "value"),
        Input("projection-alea", "value"),
        State("projection-debut", "data"),
    )
    def projeter(depart, taux, duree, versement, alea, debut):
        # La prédiction (chapitre V, D-105) : recalculée dès qu'une hypothèse change. Elle ne
        # touche à rien d'autre, et rien ne dépend d'elle (D-27). La courbe part de la date de la
        # valeur de départ — celle des derniers cours.
        return projections.resultat(
            depart, taux, duree, versement, alea == projections.ALEA,
            Date.fromisoformat(debut) if debut else None,
        )

    application.clientside_callback(
        DEFILER_VERS_L_ANCRE,
        Output("corps", "className"),
        Input("corps", "children"),
        State("etat", "data"),
    )
    return application


def _brancher_la_vie(application: Dash, veille: Veille | None, demonstration: bool) -> None:
    """L'adresse de vie. Elle sert deux fois : la page y donne signe de vie, et le lanceur y
    demande « qui est là ? » avant de démarrer un second Pastory — la réponse dit aussi si
    c'est la démonstration, pour qu'un Pastory ne réponde jamais à la place de l'autre."""
    serveur = application.server

    @serveur.route(CHEMIN_DE_VIE, methods=["GET", "POST"])
    def vie():
        page = request.args.get("page", "")
        # Seule une page de Pastory compte : un autre site ouvert dans le navigateur pourrait
        # écrire à cette adresse, et tiendrait Pastory en vie sans fenêtre.
        de_la_page = request.headers.get("Sec-Fetch-Site", "same-origin") == "same-origin"
        if veille is not None and request.method == "POST" and de_la_page:
            if request.args.get("annonce"):
                # Le lanceur, qui a trouvé ce Pastory ouvert et lui amène une fenêtre.
                veille.annoncer_une_fenetre()
            elif page and request.args.get("fin"):
                veille.adieu(page)
            elif page:
                veille.signe(page)
        reponse = jsonify(**identite(demonstration))
        reponse.headers["Cache-Control"] = "no-store"
        return reponse

    if veille is None:
        return

    @serveur.before_request
    def commencer():
        if request.path != CHEMIN_DE_VIE:
            veille.commencer_un_travail()

    @serveur.teardown_request
    def finir(_erreur):
        if request.path != CHEMIN_DE_VIE:
            veille.finir_un_travail()


def _mise_en_page(demonstration: bool = False) -> html.Div:
    # La classe de la racine dit quelle partie du livre est ouverte : la couverture, ou les
    # pages (`ecrans.rendre`). Elle commence sur la couverture, comme l'état initial.
    return html.Div(
        id="livre",
        className="livre livre--couverture",
        children=[
            dcc.Store(id="etat", data=etat_ecran.initial()),
            html.Header(
                [
                    html.Div(
                        [
                            bandeau.marque(),
                            *([bandeau.mention_de_demonstration()] if demonstration else []),
                            html.Nav(
                                id="onglets",
                                className="onglets",
                                role="tablist",
                                **{"aria-label": "Chapitres"},
                            ),
                            html.Div(id="signalements", className="pousse"),
                        ],
                        className="bande bande--titre",
                    ),
                    html.Div(id="filtres", className="bande bande--filtres", hidden=True),
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
            avis,
            ecrans.CLASSE_DES_PAGES,
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
    adresse = f"http://{HOTE}:{port}/"
    print(f"Pastory est ouvert dans votre navigateur : {adresse}")
    print("Laissez cette fenêtre ouverte pendant que vous l'utilisez ; Ctrl+C pour l'arrêter.")
    if navigateur:
        threading.Timer(1.0, webbrowser.open, args=(adresse,)).start()
    application.run(host=HOTE, port=port, debug=False)
