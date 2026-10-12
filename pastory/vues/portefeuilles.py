"""Les portefeuilles sur la couverture : en ouvrir un, le renommer, le supprimer (D-109).

Un fichier du dossier de dépôt est un portefeuille (`adaptateurs/trade_republic/depot.py`). Ce
module en est l'écran, et rien d'autre :

- **le choix**, au-dessus de l'étiquette, quand il y en a plusieurs : un bouton par
  portefeuille, celui qui est ouvert enfoncé ;
- **la gestion**, dans le volet replié du détail : pour chacun, sa période, un champ pour le
  renommer, et sa suppression — en deux clics, parce qu'elle efface un fichier ;
- **`agir`**, ce que fait un clic. Il ne calcule rien : il change le dossier, puis fait tout
  relire.

Avec un seul portefeuille, le choix n'apparaît pas, et la couverture reste celle d'avant.
"""

from __future__ import annotations

from dash import dcc, html

from pastory.adaptateurs.trade_republic import depot
from pastory.adaptateurs.trade_republic.depot import Inventaire, Portefeuille
from pastory.vues import format as f
from pastory.vues.briques import choix, ligne_de_liste, mot
from pastory.vues.chiffres import Chiffres

CHAMP = "portefeuille"

OUVRIR, RENOMMER, SUPPRIMER = "ouvrir", "renommer", "supprimer"

CHACUN_EST_CALCULE_SEUL = (
    "Chaque portefeuille est calculé seul, comme celui d'une seule personne : les chiffres de "
    "l'un ne tiennent jamais compte des autres, et l'impôt estimé non plus."
)


def bouton(action: str, nom: str) -> dict[str, str]:
    """L'identifiant d'un bouton qui agit sur le portefeuille `nom` (voir `application.py`)."""
    return {CHAMP: action, "nom": nom}


def champ_du_nom(nom: str) -> dict[str, str]:
    """L'identifiant du champ où l'on tape le nouveau nom du portefeuille `nom`."""
    return {RENOMMER: nom}


def plusieurs(inventaire: Inventaire | None) -> bool:
    return inventaire is not None and len(inventaire.portefeuilles) > 1


def choix_du_portefeuille(inventaire: Inventaire) -> html.Div:
    """Un bouton par portefeuille ; celui qui est ouvert est enfoncé."""
    return html.Div(
        [
            html.Span("Portefeuille", className="etiquette"),
            html.Div(
                [
                    html.Button(
                        portefeuille.nom,
                        id=bouton(OUVRIR, portefeuille.nom),
                        type="button",
                        n_clicks=0,
                        **{
                            "aria-pressed": "true"
                            if portefeuille == inventaire.ouvert
                            else "false"
                        },
                    )
                    for portefeuille in inventaire.portefeuilles
                ],
                className="portefeuilles__choix",
            ),
        ],
        className="portefeuilles",
    )


def gestion(inventaire: Inventaire, a_supprimer: str | None) -> list:
    """Pour chaque portefeuille : ce qu'il couvre, et de quoi le renommer ou le supprimer."""
    blocs: list = []
    for portefeuille in inventaire.portefeuilles:
        # Seul, un portefeuille est forcément l'ouvert : le dire n'apprendrait rien.
        ouvert = plusieurs(inventaire) and portefeuille == inventaire.ouvert
        blocs.append(
            html.Li(
                [
                    html.Div(
                        [
                            html.Span(
                                [portefeuille.nom, *([" ", mot("Ouvert")] if ouvert else [])],
                                className="liste-parts__nom",
                            ),
                            html.Span(_ce_qu_il_couvre(portefeuille), className="reference"),
                        ],
                        className="portefeuille__entete",
                    ),
                    _suppression(portefeuille.nom)
                    if a_supprimer == portefeuille.nom
                    else _actions(portefeuille.nom),
                ],
                className="portefeuille",
            )
        )
    suite = [html.Ul(blocs, className="liste-parts")]
    if plusieurs(inventaire):
        suite.append(html.P(CHACUN_EST_CALCULE_SEUL, className="reference"))
    return suite


def _ce_qu_il_couvre(portefeuille: Portefeuille) -> str:
    lu = portefeuille.lu
    periode = (
        f"du {f.date_courte(lu.premier_jour)} au {f.date_courte(lu.dernier_jour)}"
        if lu.premier_jour is not None
        else "aucune date lisible"
    )
    return f"{lu.lignes} lignes, {periode}"


def _actions(nom: str) -> html.Div:
    return html.Div(
        [
            dcc.Input(
                id=champ_du_nom(nom),
                type="text",
                value=nom,
                maxLength=depot.LONGUEUR_MAXIMALE_D_UN_NOM,
                placeholder="Nouveau nom",
                className="portefeuille__nom",
            ),
            html.Button(
                "Renommer",
                id=bouton(RENOMMER, nom),
                type="button",
                className="bouton bouton--clair",
                n_clicks=0,
            ),
            html.Button(
                "Supprimer",
                # Un premier clic ne supprime rien : il demande confirmation (`etat.py`).
                id=choix(SUPPRIMER, nom),
                type="button",
                className="bouton bouton--clair",
                n_clicks=0,
            ),
        ],
        className="portefeuille__actions",
    )


def _suppression(nom: str) -> html.Div:
    """La confirmation : supprimer efface un fichier, et ne se défait pas."""
    return html.Div(
        [
            html.Span(
                f"Supprimer « {nom} » ? Son fichier est effacé de cet ordinateur ; il se "
                "retrouve dans l'application de la banque.",
                className="portefeuille__question",
            ),
            html.Button(
                "Oui, supprimer",
                id=bouton(SUPPRIMER, nom),
                type="button",
                className="bouton bouton--clair",
                n_clicks=0,
            ),
            html.Button(
                "Annuler",
                id=choix(SUPPRIMER, ""),
                type="button",
                className="bouton bouton--clair",
                n_clicks=0,
            ),
        ],
        className="portefeuille__actions",
    )


def restes_de_la_lecture(base) -> list:
    """Ce que la lecture du portefeuille ouvert a écarté, à dire sous la liste."""
    lecture = base.rapport.depot
    lignes: list = []
    if lecture.doublons:
        lignes.append(
            ligne_de_liste(
                f"{lecture.doublons} ligne(s) écrite(s) deux fois dans le fichier, comptée(s) "
                "une seule fois"
            )
        )
    for nom, raison in lecture.fichiers_ignores:
        lignes.append(ligne_de_liste([mot("Ignoré", "absent"), f" {nom} : {raison}."]))
    return lignes


def agir(chiffres: Chiffres, action: str, nom: str, saisie: str | None = None) -> dict | None:
    """Ce que fait un clic sur un portefeuille. Rend le message à afficher, ou `None`.

    Tout passe par le dossier de dépôt, puis par une relecture complète : les chiffres à
    l'écran sont toujours ceux du portefeuille ouvert, jamais un reste du précédent.
    """
    if chiffres.inventaire() is None:
        return _refus("On ne change pas de portefeuille ici.")
    dossier = chiffres.dossier()
    try:
        match action:
            case "ouvrir":
                depot.ouvrir(dossier, nom)
                message = None
            case "renommer":
                nouveau = depot.renommer(dossier, nom, saisie or "").nom
                message = (
                    None
                    if nouveau == nom
                    else _fait("Renommé", f"« {nom} » s'appelle désormais « {nouveau} ».")
                )
            case "supprimer":
                depot.supprimer(dossier, nom)
                restant = depot.inventaire(dossier).ouvert
                message = _fait(
                    "Supprimé",
                    f"« {nom} » est supprimé."
                    + (f" « {restant.nom} » est ouvert." if restant is not None else ""),
                )
            case _:
                return _refus("Cette action n'existe pas.")
    except depot.NomRefuse as raison:
        return _refus(str(raison))
    except depot.ExportIntrouvable:
        # Le fichier a disparu entre l'affichage et le clic : la relecture montrera ce qui est.
        message = _refus(f"« {nom} » n'est plus dans le dossier de dépôt.")
    except OSError:
        return _refus(
            f"« {nom} » n'a pas pu être modifié : son fichier est ouvert ailleurs ou protégé."
        )
    chiffres.relire()
    return message


def _fait(etiquette: str, texte: str) -> dict:
    return {"accepte": True, "mot": etiquette, "texte": texte}


def _refus(texte: str) -> dict:
    return {"accepte": False, "mot": "Refusé", "texte": texte}
