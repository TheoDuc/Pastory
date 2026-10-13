"""L'attente : ce que l'écran montre pendant une longue lecture (D-110).

La première lecture d'un export dure de quelques secondes à une minute : Pastory cherche en
ligne la cotation, les cours et la composition de chaque actif. Un texte immobile pendant ce
temps laisse croire à une panne (retour du premier testeur). La page montre donc **où en est la
lecture** : l'étape en cours, combien d'actifs y sont traités, et une barre.

Trois morceaux, chacun à sa place :

- l'assembleur compte (`pastory/avancement.py`), sans rien savoir de l'écran ;
- ce module écrit les mots et répond à l'adresse `CHEMIN`, que la page interroge ;
- `assets/dessin.js` pose la réponse dans la page — **sans mettre aucun chiffre en forme** : le
  texte arrive déjà écrit, comme pour les graphiques (D-93).

**La barre compte des actifs, pas des secondes.** Personne ne sait combien de temps mettra une
source à répondre ; on sait, en revanche, combien d'actifs sont traités. Les trois étapes pèsent
le même poids, et chacune avance au rythme de ses actifs.
"""

from __future__ import annotations

from dash import html

from pastory.avancement import Etape, Suivi

CHEMIN = "/pastory/avancement"
"""L'adresse où la page demande où en est la lecture."""

AU_REPOS = "Calcul des chiffres…"
"""Ce que dit l'attente quand aucune lecture n'est en cours : un simple recalcul."""

EN_COMMENCANT = "Lecture de votre export…"

LIBELLES = {
    Etape.REGLAGES: "Recherche de la cotation et des frais de chaque actif…",
    Etape.COURS: "Récupération des cours de chaque actif…",
    Etape.COMPOSITIONS: "Lecture de la composition des fonds et des sociétés…",
}

NOTE = (
    "La première lecture d'un export interroge les sources de cours et de composition : elle "
    "peut prendre une minute. Les suivantes ne redemandent que les derniers cours."
)


def brique() -> html.Div:
    """Ce qui s'affiche à la place de la page pendant qu'elle se calcule.

    La barre et la note sont cachées au départ : `dessin.js` ne les montre que si une lecture
    est réellement en cours — un changement de période ne doit pas annoncer une minute
    d'attente."""
    return html.Div(
        [
            html.P(AU_REPOS, className="attente__etape"),
            html.Div(
                html.Span(className="attente__barre"),
                className="attente__piste",
                hidden=True,
                role="progressbar",
                **{"aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Avancement"},
            ),
            html.P("", className="attente__detail nb"),
            html.P(NOTE, className="attente__note", hidden=True),
        ],
        className="attente",
        role="status",
        **{"data-adresse": CHEMIN, "data-repos": AU_REPOS},
    )


def etat(suivi: Suivi) -> dict:
    """Ce que répond l'adresse : des textes déjà écrits, et la part faite, en pour cent."""
    en_cours, point = suivi.lire()
    if not en_cours:
        return {"en_cours": False}
    if point is None:
        return {"en_cours": True, "etape": EN_COMMENCANT, "detail": "", "part": 0}
    etapes = list(Etape)
    rang = f"Étape {etapes.index(point.etape) + 1} sur {len(etapes)}"
    return {
        "en_cours": True,
        "etape": LIBELLES[point.etape],
        "detail": f"{rang} · {_actifs(point.fait, point.total)}",
        "part": round(point.part * 100, 1),
    }


def _actifs(fait: int, total: int) -> str:
    if total == 0:
        return "aucun actif à traiter"
    return f"{fait} actif{'s' if fait > 1 else ''} sur {total}"
