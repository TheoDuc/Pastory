"""Le colophon : d'où viennent les chiffres de la page, et de quand ils datent.

Jusqu'à l'étape 9 bis, c'était une troisième bande sous la navigation, qui empilait sur une ligne
serrée la période de l'export, la date des cours, leur source, la période affichée, le nombre de
positions, les poches retenues, les arrêtés de composition et un lien. Le propriétaire l'a jugée
« fourre-tout » : trop d'informations dans trop peu de place, là où le reste de l'application
respire.

**Aucune de ces informations n'est supprimée** — c'est ce qui permet de dire « ces chiffres sont
d'hier ». Elles sont **rangées là où elles ont un sens** :

- la **période retenue** (« du … au … · 2 mois ») dit ce que les filtres ont donné : elle rejoint
  la bande des filtres ;
- la **fraîcheur des données** (cours, source, export, compositions, positions) accompagne le titre
  du chapitre ;
- une **valeur partielle** (un actif sans cours) reste toujours visible, jamais dans un repli.

- le reste — la source, l'export, les compositions, le nombre de positions — se lit **à la
  demande**, dans une bulle ouverte par un lien discret.

Trois pistes ont été essayées à l'écran (deux lignes à droite du titre ; une mention et sa bulle ;
un colophon en pied de chapitre) : le propriétaire a retenu la deuxième (D-103).
"""

from __future__ import annotations

from dataclasses import dataclass

from dash import html

from pastory.pivot.operation import Poche
from pastory.vues import format as f
from pastory.vues.bandeau import NOM_DE_POCHE
from pastory.vues.briques import bulle_a_contenu, mot


@dataclass(frozen=True)
class Colophon:
    cours: list | None
    """« Cours arrêtés au … », ou « Sans cours », ou rien s'il n'y a aucune position."""
    source: str | None
    export: list | None
    compositions: str | None
    positions: str | None
    partiel: list | None
    """La marque « Partiel » et les actifs sans cours : jamais repliée."""
    periode: str | None
    """La période retenue par les filtres, en clair : elle va dans la bande des filtres."""
    poches_retenues: str | None


def lire(
    *,
    export_du: object = None,
    export_au: object = None,
    cours_au: object = None,
    avec_cours: bool = False,
    sources: list[str] | None = None,
    debut: object = None,
    fin: object = None,
    jours: int | None = None,
    positions: int | None = None,
    non_valorisees: list[str] | None = None,
    poches_retenues: tuple[Poche, ...] | None = None,
    arretes: tuple[object, object] | None = None,
) -> Colophon:
    """Chaque morceau absent reste `None` : il n'est simplement pas écrit."""
    if cours_au is not None:
        cours: list | None = ["Cours arrêtés au ", html.B(f.date_courte(cours_au))]
    elif avec_cours:
        # Des positions, mais aucun cours : on le dit, plutôt que de taire la date.
        cours = [mot("Sans cours", "absent"), " aucun cours connu"]
    else:
        cours = None
    compositions = None
    if arretes is not None and arretes[0] is not None:
        du, au = arretes
        compositions = (
            f"Compositions arrêtées au {f.date_courte(au)}"
            if du == au
            else f"Compositions arrêtées du {f.date_courte(du)} au {f.date_courte(au)}"
        )
    return Colophon(
        cours=cours,
        source=", ".join(sources) if sources else None,
        export=(
            ["Export du ", html.B(f.date_courte(export_du)), " au ",
             html.B(f.date_courte(export_au))]
            if export_du is not None
            else None
        ),
        compositions=compositions,
        positions=(
            f"{positions} position{'s' if positions > 1 else ''}" if positions is not None else None
        ),
        partiel=(
            [mot("Partiel", "absent"), " " + ", ".join(non_valorisees)]
            if non_valorisees
            else None
        ),
        periode=(
            f"Du {f.date_courte(debut)} au {f.date_courte(fin)} · {f.duree_en_clair(jours)}"
            if debut is not None
            else None
        ),
        poches_retenues=(
            "Poches retenues : " + ", ".join(NOM_DE_POCHE[p] for p in poches_retenues)
            if poches_retenues is not None
            else None
        ),
    )


def _joindre(morceaux: list) -> list:
    """Des morceaux présents, séparés d'un point médian."""
    sortie: list = []
    for morceau in morceaux:
        if not morceau:
            continue
        if sortie:
            sortie.append(" · ")
        sortie.extend(morceau if isinstance(morceau, list) else [morceau])
    return sortie


def note_des_filtres(c: Colophon) -> html.Span | None:
    """À droite de la bande des filtres : ce que les filtres ont retenu."""
    morceaux = _joindre([c.periode, c.poches_retenues])
    return html.Span(morceaux, className="filtres__note") if morceaux else None


def note(c: Colophon) -> html.Div | None:
    """À droite du titre du chapitre : la seule information utile d'un coup d'œil — la date des
    cours —, une valeur partielle s'il y en a une, et un lien discret, « d'où viennent ces
    chiffres », qui ouvre le reste dans une bulle : la source, l'export, les compositions, les
    positions. Arbitrage du propriétaire (étape 9 bis), parmi trois pistes essayées à l'écran."""
    if c.cours is None and c.export is None:
        return None
    detail = html.Ul(
        [
            html.Li(ligne)
            for ligne in (
                c.cours,
                c.source and f"Source : {c.source}",
                c.export,
                c.compositions,
                c.positions,
            )
            if ligne
        ],
        className="colophon__detail",
    )
    return html.Div(
        _joindre([c.partiel, c.cours or c.export])
        + [" ", *bulle_a_contenu("d'où viennent ces chiffres", "D'où viennent ces chiffres",
                                 detail)],
        className="colophon",
    )
