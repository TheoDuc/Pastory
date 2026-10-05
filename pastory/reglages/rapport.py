"""Le rapport des réglages : ce que `pastory actifs` affiche (D-80).

Pour chaque actif et chaque réglage : la valeur retenue, **d'où elle vient**, **ce qui a été
vérifié**, et ce qu'il faut savoir pour s'y fier. Ou, quand rien de fiable n'a été trouvé, le
motif — écrit pour quelqu'un qui n'a pas suivi la construction du projet (règle 10).

En tête, le critère de l'étape 8 quater : combien de valeurs l'application a trouvées seule, et
combien elle n'a pas su trouver. La réponse visée est zéro, et chaque trou doit s'expliquer.

Le texte s'écrit en cp1252 (la console Windows) et aucune ligne ne dépasse 100 caractères.
"""

from __future__ import annotations

import textwrap
from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import ContenuActif, TypeActif
from pastory.reglages import Cotation, Origine, Reglage, Trouvee
from pastory.reglages.assemblage import Reglages, ReglagesDUnActif

LARGEUR = 100
RETRAIT_LIBELLE = "    "
LARGEUR_LIBELLE = 16
RETRAIT_DETAIL = RETRAIT_LIBELLE + " " * (LARGEUR_LIBELLE + 1)

CORRIGER = (
    "Rien n'est à faire : une valeur fausse peut être corrigée dans actifs.toml (dossier de "
    "configuration, voir « pastory emplacements »), et la correction l'emporte. Ce n'est "
    "jamais nécessaire pour voir le reste du portefeuille."
)


def resume(reglages: Reglages) -> str:
    lignes: list[str] = []
    trouvees, corrigees, trous = _compter(reglages)
    lignes.append("Réglages de vos actifs")
    lignes.append("-" * 22)
    lignes += _envelopper(
        f"{trouvees} valeur(s) trouvée(s) seule(s), {corrigees} corrigée(s) par vous, "
        f"{trous} introuvable(s).",
        "  ",
    )
    lignes += _envelopper(
        "Chaque valeur trouvée porte sa source et ce qui a été vérifié avant de l'appliquer. "
        "Ce qui n'a pas été trouvé de façon fiable n'est ni inventé ni demandé : c'est dit "
        "ci-dessous, et le reste du portefeuille s'affiche quand même.",
        "  ",
    )

    for actif, reglages_de_l_actif in sorted(reglages.actifs.items()):
        lignes.append("")
        lignes += _un_actif(actif, reglages_de_l_actif)

    if reglages.premier_versement_pea is not None:
        lignes.append("")
        lignes.append("  PEA")
        lignes += _un_reglage("date d'ouverture", reglages.premier_versement_pea)
        if reglages.retraits_pea:
            lignes += _envelopper(
                "ATTENTION - de l'argent est sorti du PEA depuis son ouverture, le "
                + ", le ".join(jour.isoformat() for jour in reglages.retraits_pea)
                + ". L'impôt estimé du PEA suppose qu'il n'y a jamais eu de retrait : il est "
                "alors mal approché.",
                RETRAIT_DETAIL,
            )

    if reglages.orphelines:
        lignes.append("")
        lignes += _envelopper(
            "Corrections qui ne désignent aucun actif de vos exports : "
            + ", ".join(reglages.orphelines)
            + ". Elles ne servent à rien. C'est souvent un ancien identifiant (une crypto "
            "était désignée autrement avant l'export officiel) : la valeur est désormais "
            "trouvée seule, et la ligne peut être retirée d'actifs.toml.",
            "  ",
        )

    lignes.append("")
    lignes += _envelopper(CORRIGER, "  ")
    return "\n".join(lignes)


def _compter(reglages: Reglages) -> tuple[int, int, int]:
    trouvees = corrigees = trous = 0
    tous: list[Reglage] = [
        reglage
        for un_actif in reglages.actifs.values()
        for _, reglage in un_actif.reglages()
    ]
    if reglages.premier_versement_pea is not None:
        tous.append(reglages.premier_versement_pea)
    for reglage in tous:
        if reglage.trou is not None:
            trous += 1
        elif reglage.retenu.origine.corrigee:
            corrigees += 1
        else:
            trouvees += 1
    return trouvees, corrigees, trous


def _un_actif(actif: str, reglages: ReglagesDUnActif) -> list[str]:
    poches = ", ".join(sorted(poche.value for poche in reglages.poches))
    entete = " - ".join(partie for partie in (actif, reglages.nom, poches) if partie)
    lignes = _envelopper(entete, "  ")
    for nom, reglage in reglages.reglages():
        lignes += _un_reglage(nom, reglage)
    return lignes


def _un_reglage(nom: str, reglage: Reglage) -> list[str]:
    retenu = reglage.retenu
    if not isinstance(retenu, Trouvee):
        return _envelopper(
            f"INTROUVABLE - {retenu.motif}",
            f"{RETRAIT_LIBELLE}{nom:<{LARGEUR_LIBELLE}} ",
            RETRAIT_DETAIL,
        )

    lignes = _envelopper(
        _valeur(retenu.valeur), f"{RETRAIT_LIBELLE}{nom:<{LARGEUR_LIBELLE}} ", RETRAIT_DETAIL
    )
    lignes += _origine(retenu.origine)
    if reglage.ecarte is not None:
        lignes += _envelopper(
            f"la source donnait : {_valeur(reglage.ecarte.valeur)} "
            f"({_source(reglage.ecarte.origine)})",
            RETRAIT_DETAIL,
        )
    return lignes


def _origine(origine: Origine) -> list[str]:
    lignes = _envelopper(
        ("" if origine.corrigee else "trouvé : ") + _source(origine), RETRAIT_DETAIL
    )
    if origine.controle:
        lignes += _envelopper(f"vérifié : {origine.controle}", RETRAIT_DETAIL)
    if origine.reserve:
        lignes += _envelopper(f"à savoir : {origine.reserve}", RETRAIT_DETAIL)
    return lignes


def _source(origine: Origine) -> str:
    if origine.date is None:
        return origine.source
    return f"{origine.source}, {origine.intitule_de_la_date} {origine.date.isoformat()}"


def _valeur(valeur: object) -> str:
    if isinstance(valeur, Cotation):
        texte = f"{valeur.ticker}, en {valeur.devise}"
        details = ", ".join(partie for partie in (valeur.place, valeur.nom) if partie)
        return f"{texte} ({details})" if details else texte
    if isinstance(valeur, TypeActif | ContenuActif):
        return LIBELLES.get(valeur, valeur.value)
    if isinstance(valeur, Decimal):
        return f"{format(valeur.normalize(), 'f').replace('.', ',')} % par an"
    if isinstance(valeur, Date):
        return valeur.isoformat()
    return str(valeur)


LIBELLES: dict[object, str] = {
    TypeActif.ETF: "ETF (fonds)",
    TypeActif.ACTION: "action",
    TypeActif.CRYPTO: "crypto-actif",
    ContenuActif.ACTIONS: "actions",
    ContenuActif.OBLIGATIONS: "obligations (hors actions)",
    ContenuActif.MATIERES_PREMIERES: "matières premières (hors actions)",
}


def _envelopper(texte: str, retrait: str, suite: str | None = None) -> list[str]:
    return textwrap.wrap(
        texte,
        width=LARGEUR,
        initial_indent=retrait,
        subsequent_indent=suite if suite is not None else retrait,
        break_on_hyphens=False,
        break_long_words=False,
    )
