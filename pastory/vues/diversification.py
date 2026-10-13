"""L'onglet « Diversification » : où est mon argent ? (conception §4.4)

**Quatre sous-onglets**, dans l'ordre où l'on se pose les questions : les classes d'actifs, les
zones, les pays, les secteurs. Chacun montre la même chose deux fois, comme la maquette
(`ongletDiversification`) :

- **le classement**, à gauche : une ligne par poste, avec son repère, sa barre, son montant et sa
  part. Toutes les barres sont rapportées à la **même base**, jamais renormalisées (D-69). Sous
  une coupure, **ce qui n'entre pas dans cette répartition** — non attribué, non couvert, hors
  actions classe par classe, actifs numériques — à sa vraie taille ;
- **l'anneau**, à droite : la même chose d'un coup d'œil. Il ne fait pas foi et ne porte aucun
  chiffre ; ce qui manque y est hachuré, et le cercle ne se ferme pas sur les seuls postes.

**Chaque ligne se déplie vers les actifs qui la composent** (D-111) : sous « États-Unis », les
fonds et les actions du portefeuille qui y sont investis, et pour combien. C'est une question
du premier testeur, et c'est ce qui rend une ligne vérifiable : la somme de ses actifs est son
montant, au centime. Ce sont les actifs **du portefeuille** qui sont listés, jamais les sociétés
qu'un fonds détient (D-63).

Puis, pleine largeur, **ce qu'il faut savoir de ces chiffres** : la source et la règle de pays
de chaque actif quand elles diffèrent (D-72), les fonds synthétiques, les actifs non couverts et
pourquoi, la nomenclature, la date des compositions.

**Aucun filtre ici** : une répartition est la photo d'un tout (conception §4). Tous les montants
et toutes les parts viennent du moteur (`Repartition.pour_cent`, sur la base) ; cet écran ne fait
que les ranger et les écrire.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dash import html

from pastory.moteur.diversification import Contribution, Diversification, Poste, Repartition
from pastory.vues import actifs as actifs_vue
from pastory.vues import format as f
from pastory.vues.briques import (
    aide,
    bloc,
    bloc_replie,
    choix,
    dessin,
    ligne_de_liste,
    tuile,
)
from pastory.vues.chiffres import Vue

RUBRIQUES = (
    ("classes", "Actifs"),
    ("zones", "Zone géographique"),
    ("pays", "Pays"),
    ("secteurs", "Secteur"),
)

PICTO_DE_CLASSE = {
    "actions": "actions",
    "obligations": "obligations",
    "matieres_premieres": "matieres",
}
PICTO_DE_SECTEUR = {
    "101": "materiaux",
    "102": "cyclique",
    "103": "finance",
    "104": "immobilier",
    "205": "defensive",
    "206": "sante",
    "207": "collectivites",
    "308": "communication",
    "309": "energie",
    "310": "industrie",
    "311": "technologie",
}
TERRES_DE_ZONE = {
    "amerique_du_nord": ["amNord"],
    "europe": ["europe"],
    "japon": ["japon"],
    "asie_pacifique_developpee": ["oceanie"],
    "marches_emergents": ["amSud", "afrique", "asie", "indonesie"],
}
"""Ce que le planisphère allume pour chaque zone. Un repère qui **situe**, il ne délimite pas :
la bulle « ? » des zones le dit, et ce sont les montants qui font foi (conception §3.2)."""

RESUME_DES_RESTES = {"zones": "Sans pays", "pays": "Sans pays", "secteurs": "Sans secteur"}
"""Le nom de la ligne qui résume ce qui n'entre pas dans la répartition, quand elle est repliée."""

PREMIERS_POSTES = 15
"""Combien de postes le classement montre avant « afficher les autres »."""

DOSSIER_DES_DRAPEAUX = Path(__file__).parent / "assets" / "drapeaux"

LIBELLE_NUMERIQUES = "Actifs numériques"
LIBELLE_NON_ATTRIBUE = "Non attribué par les fonds"
LIBELLE_NON_COUVERT = "Non couvert"
ZERO = Decimal("0")


@dataclass(frozen=True)
class Ligne:
    """Une ligne du classement, poste ou reste, prête à écrire."""

    libelle: str
    montant: Decimal
    part: Decimal | None
    repere: tuple[str, object]
    """`(nature du dessin, données)` : un drapeau, un pictogramme ou un planisphère."""
    cle_aide: str | None = None
    absent: bool = False
    rang: int = 0
    """La place canonique du poste, pour un ordre stable entre deux affichages."""
    sous_lignes: tuple[Ligne, ...] = ()
    """Ce que la ligne regroupe, montré quand on la déplie : les pays d'une zone, ou les actifs
    qui font un poste (D-111)."""
    actif: bool = False
    """Vrai pour la ligne d'un actif du portefeuille, sous le poste auquel il contribue."""


def ecran(vue: Vue, rubrique: str = "classes", deplie: bool = False) -> html.Div:
    """Les rubriques se choisissent dans la bande, sous la navigation (D-104)."""
    rubrique = rubrique if any(cle == rubrique for cle, _ in RUBRIQUES) else "classes"
    page: list = []
    diversification = vue.construit.diversification
    valorisation = vue.construit.synthese.valorisation
    if diversification is None or not valorisation.valorisees:
        page.append(
            html.Div(
                bloc(
                    "Répartition",
                    html.P(
                        "Sans cours, aucune position n'a de valeur : il n'y a rien à répartir. "
                        "Une répartition est la photo d'une valeur à une date, pas une liste "
                        "d'actifs.",
                        className="vide",
                    ),
                ),
                className="rangee rangee--large rangee--apres",
            )
        )
        return html.Div(page)

    titre, note, cle_aide, lignes, restes, base = _rubrique(
        diversification, rubrique, _noms(vue)
    )
    # Les restes des pays et des secteurs tiennent sur une ligne, dépliable : c'est l'arbitrage
    # du propriétaire (étape 9). Le montant reste visible, et rien n'est ramené à 100 % (D-69).
    # Les classes d'actifs, elles, gardent leur détail : c'est leur sujet.
    resume_des_restes = None if rubrique == "classes" else RESUME_DES_RESTES[rubrique]
    classement = bloc(
        titre,
        _classement(lignes, restes, deplie, resume_des_restes),
        note=note,
        cle_aide=cle_aide,
    )
    # Les quatre rubriques s'affichent de la même façon : les chiffres clés, puis le classement
    # en pleine largeur. Ni anneau ni carrés — essayés, et écartés par le propriétaire : avec
    # des dizaines de pays ils sont illisibles, et le classement dit déjà tout.
    page.append(
        html.Div(_chiffres_cles(diversification, rubrique, lignes, restes), className="tuiles")
    )
    page.append(html.Div(classement, className="rangee rangee--large rangee--apres"))
    page.append(
        html.Div(
            bloc_replie(
                "Ce qu'il faut savoir de ces chiffres",
                _a_savoir(vue, diversification),
                note="sources, règles de pays, fonds non couverts",
            ),
            className="rangee rangee--large rangee--apres",
        )
    )
    return html.Div(page)


# --- Les lignes de chaque rubrique ------------------------------------------------------


def _noms(vue: Vue) -> dict[str, str]:
    """Le nom de chaque actif, tel que la banque le donne ; à défaut, son code."""
    positions = vue.construit.synthese.valorisation.positions
    return {p.actif: (p.position.nom_actif or p.actif) for p in positions}


def _apports(
    contributions: Iterable[Contribution], r: Repartition, noms: Mapping[str, str]
) -> tuple[Ligne, ...]:
    """Les actifs qui font une ligne, chacun avec son montant et sa part de **la même base**
    que toutes les autres lignes (D-69, D-111). Aucun chiffre n'est calculé ici : les montants
    sont ceux du moteur, et leur somme est le montant de la ligne."""
    return tuple(
        Ligne(
            noms.get(c.actif, c.actif),
            c.montant,
            r.pour_cent(c.montant),
            ("picto", ""),
            actif=True,
        )
        for c in contributions
    )


def _rubrique(d: Diversification, rubrique: str, noms: Mapping[str, str]):
    """`(titre, note, aide, postes, restes, base)` pour la rubrique choisie."""
    if rubrique == "classes":
        r = d.classes
        lignes = [
            Ligne(
                _libelle(p),
                p.montant,
                r.pour_cent(p.montant),
                ("picto", PICTO_DE_CLASSE.get(p.code, "")),
                rang=p.rang or 50,
                sous_lignes=_apports(p.contributions, r, noms),
            )
            for p in r.postes
        ]
        if r.hors_classification > ZERO:
            # Une crypto **est** une classe d'actifs : elle compte ici, et nulle part ailleurs.
            lignes.append(
                Ligne(
                    LIBELLE_NUMERIQUES,
                    r.hors_classification,
                    r.pour_cent(r.hors_classification),
                    ("picto", "numeriques"),
                    cle_aide="numeriques",
                    rang=99,
                    sous_lignes=_apports(r.hors_classification_par_actif, r, noms),
                )
            )
        return (
            "Par classe d'actifs",
            f"base {f.montant(r.base)}",
            "pasCent",
            lignes,
            _restes(r, noms, classes=True),
            r.base,
        )
    if rubrique == "zones":
        r = d.pays
        lignes = [
            Ligne(
                zone.libelle,
                montant,
                r.pour_cent(montant),
                ("planisphere", TERRES_DE_ZONE.get(zone.cle, [])),
                rang=zone.rang,
                sous_lignes=tuple(
                    Ligne(
                        _libelle(p),
                        p.montant,
                        r.pour_cent(p.montant),
                        ("drapeau", p.code),
                        cle_aide=None if p.reconnu else "codeNonReconnu",
                        sous_lignes=_apports(p.contributions, r, noms),
                    )
                    for p in postes
                ),
            )
            for zone, montant, postes in r.par_zone()
        ]
        return (
            "Par zone d'investisseur",
            "convention datée et sourcée",
            "zones",
            lignes,
            _restes(r, noms),
            r.base,
        )
    if rubrique == "pays":
        r = d.pays
        codes = sorted(p.code for p in r.postes)
        lignes = [
            Ligne(
                _libelle(p),
                p.montant,
                r.pour_cent(p.montant),
                ("drapeau", p.code),
                cle_aide=None if p.reconnu else "codeNonReconnu",
                rang=codes.index(p.code),
                sous_lignes=_apports(p.contributions, r, noms),
            )
            for p in r.postes
        ]
        return "Par pays", _note_des_regles(d), "regleDePays", lignes, _restes(r, noms), r.base
    r = d.secteurs
    lignes = [
        Ligne(
            _libelle(p),
            p.montant,
            r.pour_cent(p.montant),
            ("picto", PICTO_DE_SECTEUR.get(p.code, "")),
            cle_aide=None if p.reconnu else "codeNonReconnu",
            rang=int(p.code) if p.code.isdigit() else 999,
            sous_lignes=_apports(p.contributions, r, noms),
        )
        for p in r.postes
    ]
    return "Par secteur", "secteurs Morningstar", "secteurs", lignes, _restes(r, noms), r.base


def _libelle(poste: Poste) -> str:
    """Le nom d'un poste, et son code quand le référentiel ne le connaît pas : il est affiché
    tel quel, jamais fondu dans « autres » (règle 5)."""
    return poste.libelle if poste.reconnu else f"{poste.code} (code non reconnu)"


def _restes(r: Repartition, noms: Mapping[str, str], classes: bool = False) -> list[Ligne]:
    """Ce qui n'entre pas dans la répartition, à sa vraie taille (D-69). Un reste nul n'est pas
    affiché : une ligne « non couvert : 0,00 € » ferait douter pour rien. Chaque reste se
    déplie lui aussi vers ses actifs (D-111)."""
    restes: list[Ligne] = []
    if not classes:
        for p in r.hors_perimetre_postes:
            if p.montant > ZERO:
                restes.append(
                    Ligne(
                        _libelle(p),
                        p.montant,
                        r.pour_cent(p.montant),
                        ("picto", PICTO_DE_CLASSE.get(p.code, "")),
                        "horsActions",
                        absent=True,
                        sous_lignes=_apports(p.contributions, r, noms),
                    )
                )
        if r.hors_classification > ZERO:
            restes.append(
                Ligne(
                    LIBELLE_NUMERIQUES,
                    r.hors_classification,
                    r.pour_cent(r.hors_classification),
                    ("picto", "numeriques"),
                    "numeriques",
                    absent=True,
                    sous_lignes=_apports(r.hors_classification_par_actif, r, noms),
                )
            )
    if r.non_attribue > ZERO:
        restes.append(
            Ligne(
                LIBELLE_NON_ATTRIBUE,
                r.non_attribue,
                r.pour_cent(r.non_attribue),
                ("picto", ""),
                "nonAttribue",
                absent=True,
                sous_lignes=_apports(r.non_attribue_par_actif, r, noms),
            )
        )
    if r.non_couvert > ZERO:
        restes.append(
            Ligne(
                LIBELLE_NON_COUVERT,
                r.non_couvert,
                r.pour_cent(r.non_couvert),
                ("picto", ""),
                "nonCouvert",
                absent=True,
                sous_lignes=_apports(r.non_couvert_par_actif, r, noms),
            )
        )
    return restes


def _note_des_regles(d: Diversification) -> str:
    regles = sorted({o.regle_de_pays for o in d.origines if o.regle_de_pays})
    if not regles:
        return "règle de pays : voir « ce qu'il faut savoir »"
    if len(regles) == 1:
        return f"règle : {regles[0]}"
    return f"{len(regles)} règles de pays : voir « ce qu'il faut savoir »"


# --- Le classement ---------------------------------------------------------------------


def _classement(
    lignes: list[Ligne],
    restes: list[Ligne],
    deplie: bool = True,
    resume_des_restes: str | None = None,
) -> html.Div:
    """Le classement. Replié, il ne montre que les `PREMIERS_POSTES` premiers postes, et un
    bouton dit combien il en reste et ce qu'ils pèsent : une liste de soixante pays noie ceux
    qui comptent. Les restes — ce qui n'entre pas dans la répartition — sont **toujours**
    montrés : c'est une information, pas un détail (D-69)."""
    parts = [ligne.part for ligne in lignes + restes if ligne.part is not None]
    maxi = max(parts) if parts else Decimal(1)
    triees = sorted(lignes, key=lambda ligne: ligne.montant, reverse=True)
    caches = [] if deplie else triees[PREMIERS_POSTES:]
    if len(caches) < 2:
        # Cacher une seule ligne derrière un bouton coûterait plus qu'elle.
        caches = []
    visibles = triees[: len(triees) - len(caches)]
    enfants: list = []
    if any(ligne.sous_lignes for ligne in lignes + restes):
        enfants.append(
            html.P(
                "Chaque ligne se déplie : elle montre les actifs de votre portefeuille qui la "
                "composent, et pour combien.",
                className="classement__mode-d-emploi",
            )
        )
    enfants += [_ligne_ou_groupe(ligne, maxi) for ligne in visibles]
    if caches:
        part_cachee = sum((ligne.part or ZERO for ligne in caches), ZERO)
        enfants.append(
            html.Button(
                f"Afficher les {len(caches)} autres ({f.pour_cent(part_cachee)} à eux tous)",
                id=choix("deplier", "classement"),
                type="button",
                className="lien classement__plus",
                n_clicks=0,
            )
        )
    elif deplie and len(triees) > PREMIERS_POSTES + 1:
        enfants.append(
            html.Button(
                f"N'afficher que les {PREMIERS_POSTES} premiers",
                id=choix("deplier", "classement"),
                type="button",
                className="lien classement__plus",
                n_clicks=0,
            )
        )
    if not lignes:
        enfants.append(
            html.P(
                "Aucun poste dans cette répartition : rien de ce que vous détenez n'y est "
                "attribué. Ce qui n'y entre pas est détaillé ci-dessous.",
                className="vide",
            )
        )
    if restes:
        enfants.append(
            html.Div(
                [html.Span("Ce qui n'entre pas dans cette répartition"), *aide("pasCent")],
                className="classement__coupure",
            )
        )
        detail = [
            _ligne_ou_groupe(ligne, maxi)
            for ligne in sorted(restes, key=lambda ligne: ligne.montant, reverse=True)
        ]
        if resume_des_restes is None or len(restes) < 2:
            enfants += detail
        else:
            total = sum((ligne.montant for ligne in restes), ZERO)
            part = sum((ligne.part or ZERO for ligne in restes), ZERO)
            resume = Ligne(resume_des_restes, total, part, ("picto", ""), absent=True)
            enfants.append(_deroulant(resume, detail, maxi))
    return html.Div(enfants, className="classement")


def _ligne_ou_groupe(ligne: Ligne, maxi: Decimal):
    """Une ligne simple, ou, si elle regroupe d'autres lignes, une ligne qui se déplie — et
    ses sous-lignes de même : une zone s'ouvre sur ses pays, un pays sur ses actifs."""
    if not ligne.sous_lignes:
        return _ligne_mesuree(ligne, maxi)
    detail = [
        _ligne_ou_groupe(sous, maxi)
        for sous in sorted(ligne.sous_lignes, key=lambda s: s.montant, reverse=True)
    ]
    return _deroulant(ligne, detail, maxi, vers_des_actifs=all(s.actif for s in ligne.sous_lignes))


def _deroulant(
    ligne: Ligne, detail: list, maxi: Decimal, vers_des_actifs: bool = False
) -> html.Details:
    """Une ligne de classement qui se déplie d'un clic : une zone vers ses pays, « Sans pays »
    vers ce qu'elle réunit, un poste vers ses actifs (`vers_des_actifs`, D-111). Toutes les
    barres restent rapportées à la même base (D-69)."""
    return html.Details(
        [html.Summary(_ligne_mesuree(ligne, maxi), className="deroulant__titre"), *detail],
        className="deroulant deroulant--actifs" if vers_des_actifs else "deroulant",
    )


def _repere(nature: str, donnees: object):
    """Le repère d'une ligne. Un pays porte son drapeau, tiré de `assets/drapeaux` ; un code
    sans drapeau garde le globe dessiné par le script — repéré, jamais confondu avec un autre."""
    if nature == "drapeau" and isinstance(donnees, str):
        nom = f"{donnees.lower()}.svg"
        if (DOSSIER_DES_DRAPEAUX / nom).exists():
            return html.Img(src=f"/assets/drapeaux/{nom}", className="fanion", alt="")
    return dessin(nature, donnees)


def _ligne_mesuree(ligne: Ligne, maxi: Decimal) -> html.Div:
    """Une ligne : le repère dans un créneau de largeur fixe (sans quoi les libellés d'une même
    liste ne commencent pas à la même abscisse), le libellé avec son texte entier au survol, la
    barre rapportée à la même base que toutes les autres, le montant, la part."""
    nature, donnees = ligne.repere
    largeur = max(0.8, float((ligne.part or ZERO) / maxi * 100)) if maxi else 0.8
    return html.Div(
        [
            html.Span(
                [
                    html.Span(_repere(nature, donnees), className="rang__repere"),
                    html.Span(ligne.libelle, className="rang__texte", title=ligne.libelle),
                    *aide(ligne.cle_aide),
                ],
                className="rang__libelle",
            ),
            html.Span(
                html.Span(
                    className="rang__barre" + (" rang__barre--absent" if ligne.absent else ""),
                    style={"width": f"{largeur:.2f}%"},
                ),
                className="rang__piste",
            ),
            html.Span(f.montant(ligne.montant), className="rang__montant nb"),
            html.Span(f.pour_cent(ligne.part), className="rang__part nb"),
        ],
        className="rang"
        + (" rang--absent" if ligne.absent else "")
        + (" rang--actif" if ligne.actif else ""),
    )


# --- Les chiffres clés -------------------------------------------------------------------


def _chiffres_cles(d: Diversification, rubrique: str, lignes: list[Ligne], restes: list[Ligne]):
    """Trois ou quatre chiffres en tête de la rubrique : ce qu'on regarde d'abord. Tous sont
    rapportés à la valeur totale, comme le classement dessous (`Repartition.pour_cent`)."""
    r = d.classes if rubrique == "classes" else (d.secteurs if rubrique == "secteurs" else d.pays)

    def part(montant: Decimal) -> str:
        return f.pour_cent(r.pour_cent(montant))

    triees = sorted(lignes, key=lambda ligne: ligne.montant, reverse=True)
    total_restes = sum((ligne.montant for ligne in restes), ZERO)
    tuiles: list = []
    if rubrique == "classes":
        actions = sum((p.montant for p in r.postes if p.code == "actions"), ZERO)
        hors = sum((p.montant for p in r.postes if p.code != "actions"), ZERO)
        tuiles.append(tuile("Part en actions", part(actions), petit=True, pied=f.montant(actions)))
        tuiles.append(
            tuile(
                "Hors actions",
                part(hors),
                petit=True,
                pied="obligations, matières premières, divers",
                cle_aide="horsActions",
            )
        )
        if r.hors_classification > ZERO:
            tuiles.append(
                tuile(
                    "Actifs numériques",
                    part(r.hors_classification),
                    petit=True,
                    pied=f.montant(r.hors_classification),
                    cle_aide="numeriques",
                )
            )
    else:
        nom = {"zones": "Zone principale", "pays": "Premier pays", "secteurs": "Premier secteur"}
        if triees:
            tuiles.append(
                tuile(
                    nom[rubrique],
                    f.pour_cent(triees[0].part),
                    petit=True,
                    pied=f"{triees[0].libelle} · {f.montant(triees[0].montant)}",
                )
            )
        reconnus = [p for p in r.postes if p.reconnu]
        if rubrique == "secteurs":
            tuiles.append(
                tuile(
                    "Secteurs représentés",
                    f"{len(reconnus)} sur 11",
                    petit=True,
                    pied="nomenclature Morningstar",
                    cle_aide="secteurs",
                )
            )
        else:
            zones = len(d.pays.par_zone())
            tuiles.append(
                tuile(
                    "Pays représentés",
                    str(len(reconnus)),
                    petit=True,
                    pied=f"dans {zones} zone{'s' if zones > 1 else ''}",
                )
            )
        if rubrique == "pays" and len(triees) > 10:
            dix = sum((ligne.montant for ligne in triees[:10]), ZERO)
            tuiles.append(tuile("Les dix premiers", part(dix), petit=True, pied=f.montant(dix)))
    if total_restes > ZERO and rubrique != "classes":
        tuiles.append(
            tuile(
                RESUME_DES_RESTES[rubrique],
                part(total_restes),
                petit=True,
                pied=f.montant(total_restes),
                cle_aide="pasCent",
            )
        )
    elif r.non_couvert > ZERO:
        tuiles.append(
            tuile(
                "Non couvert",
                part(r.non_couvert),
                petit=True,
                pied=f.montant(r.non_couvert),
                cle_aide="nonCouvert",
            )
        )
    return tuiles


# --- Ce qu'il faut savoir --------------------------------------------------------------


def _a_savoir(vue: Vue, d: Diversification) -> html.Ul:
    noms = _noms(vue)

    def nom(actif: str) -> str:
        return noms.get(actif, actif)

    lignes: list = []
    origines = d.origines
    if len({(o.source, o.regle_de_pays) for o in origines}) > 1:
        # Plusieurs sources ou plusieurs règles cohabitent : chaque actif dit la sienne (D-72).
        # Une seule : la phrase générique suffit, vingt lignes identiques feraient du bruit.
        lignes.append(
            ligne_de_liste(["D'où vient la composition de chaque actif ", *aide("regleDePays")])
        )
        for origine in origines:
            lignes.append(
                ligne_de_liste(
                    nom(origine.actif),
                    f"{origine.source} — {_regle_en_clair(vue, origine)}",
                    "reference",
                )
            )
    synthetiques = d.pays.actifs_synthetiques
    if synthetiques:
        lignes.append(
            ligne_de_liste(
                [
                    "Fonds synthétiques : on affiche l'indice suivi, pas le panier détenu ",
                    *aide("synthetique"),
                ],
                ", ".join(nom(a) for a in synthetiques),
                "part",
            )
        )
    if d.declarees_a_la_main:
        lignes.append(
            ligne_de_liste(
                [
                    "Composition déclarée par vous, donc sans date d'arrêté ",
                    *aide("declareeALaMain"),
                ],
                ", ".join(nom(a) for a in d.declarees_a_la_main),
                "part",
            )
        )
    for actif in d.pays.actifs_non_couverts:
        lignes.append(
            ligne_de_liste(
                [
                    f"Non couvert — {nom(actif)} : {_motif_non_couvert(vue, actif)} ",
                    *aide("nonCouvert"),
                ],
            )
        )
    sources = {o.actif: o.source for o in d.origines}
    for actif in d.secteurs.actifs_non_couverts:
        if actif in d.pays.actifs_non_couverts:
            continue
        # Des pays, mais aucun secteur : le cas de la source de secours (D-77). Les deux
        # répartitions ne sont pas d'accord, et c'est juste (conception §5.2).
        lignes.append(
            ligne_de_liste(
                [
                    f"Non couvert en secteur seulement — {nom(actif)} : sa source "
                    f"({sources.get(actif, 'non nommée')}) ne publie pas ses secteurs dans la "
                    "nomenclature Morningstar, et deux nomenclatures ne se mélangent jamais. "
                    "Ses pays, eux, sont comptés. ",
                    *aide("nonCouvert"),
                ],
            )
        )
    lignes.append(ligne_de_liste("Nomenclature sectorielle", "Morningstar, 11 secteurs", "part"))
    if d.arrete_du is not None:
        arrete = (
            f"au {f.date_courte(d.arrete_au)}"
            if d.arrete_du == d.arrete_au
            else f"du {f.date_courte(d.arrete_du)} au {f.date_courte(d.arrete_au)}"
        )
        lignes.append(ligne_de_liste(["Compositions arrêtées ", *aide("arrete")], arrete, "part"))
    for source in d.sources:
        lignes.append(ligne_de_liste("Source", source, "part"))
    return html.Ul(lignes, className="liste-parts")


def _regle_en_clair(vue: Vue, origine) -> str:
    """La règle de pays d'un actif, ou pourquoi il n'en a pas : un fonds d'obligations ou de
    matières premières n'a pas de pays au sens des actions, ce n'est pas une règle manquante."""
    if origine.regle_de_pays:
        return origine.regle_de_pays
    if actifs_vue._contenu(vue, origine.actif) is not None:
        return "hors actions : ni pays ni secteur, pas de règle de pays"
    return "règle non précisée par la source"


def _motif_non_couvert(vue: Vue, actif: str) -> str:
    compositions = vue.construit.compositions
    if compositions is not None:
        for refus in compositions.refus:
            if refus.actif == actif:
                return refus.motif
    return "aucune composition utilisable"
