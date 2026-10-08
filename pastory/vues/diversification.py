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

Puis, pleine largeur, **ce qu'il faut savoir de ces chiffres** : la source et la règle de pays
de chaque actif quand elles diffèrent (D-72), les fonds synthétiques, les actifs non couverts et
pourquoi, la nomenclature, la date des compositions.

**Aucun filtre ici** : une répartition est la photo d'un tout (conception §4). Tous les montants
et toutes les parts viennent du moteur (`Repartition.pour_cent`, sur la base) ; cet écran ne fait
que les ranger et les écrire.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dash import html

from pastory.moteur.diversification import Diversification, Poste, Repartition
from pastory.vues import actifs as actifs_vue
from pastory.vues import format as f
from pastory.vues.briques import aide, bloc, bloc_replie, choix, dessin, ligne_de_liste
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
    """La place canonique du poste : c'est elle qui choisit sa couleur, jamais son rang de
    taille — une couleur suit son poste (conception §3.2)."""


def ecran(vue: Vue, rubrique: str = "classes", deplie: bool = False) -> html.Div:
    rubrique = rubrique if any(cle == rubrique for cle, _ in RUBRIQUES) else "classes"
    page: list = [_sous_onglets(rubrique)]
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

    titre, note, cle_aide, lignes, restes, base = _rubrique(diversification, rubrique)
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
    if rubrique in ("classes", "zones"):
        rangee = html.Div(
            # Moitié-moitié : quelques postes seulement, et chaque carré doit avoir la place
            # d'écrire son nom à côté de sa part.
            [classement, _bloc_carres(lignes, restes, base)],
            className="rangee rangee--deux rangee--apres",
        )
    else:
        # Des dizaines de pays ou onze secteurs : un dessin de plus serait illisible, et le
        # classement dit déjà tout (arbitrage du propriétaire, étape 9).
        rangee = html.Div(classement, className="rangee rangee--large rangee--apres")
    page.append(rangee)
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


def _sous_onglets(actuelle: str) -> html.Div:
    """On **choisit** ce qu'on regarde : ce ne sont pas des filtres, rien n'est retiré."""
    return html.Div(
        [
            html.Button(
                nom,
                id=choix("rubrique", cle),
                type="button",
                role="tab",
                n_clicks=0,
                **{"aria-selected": "true" if cle == actuelle else "false"},
            )
            for cle, nom in RUBRIQUES
        ],
        className="onglets onglets--secondaires",
        role="tablist",
    )


# --- Les lignes de chaque rubrique ------------------------------------------------------


def _rubrique(d: Diversification, rubrique: str):
    """`(titre, note, aide, postes, restes, base)` pour la rubrique choisie."""
    if rubrique == "classes":
        r = d.classes
        lignes = [
            Ligne(
                _libelle(p), p.montant, r.pour_cent(p.montant),
                ("picto", PICTO_DE_CLASSE.get(p.code, "")), rang=p.rang or 50,
            )
            for p in r.postes
        ]
        if r.hors_classification > ZERO:
            # Une crypto **est** une classe d'actifs : elle compte ici, et nulle part ailleurs.
            lignes.append(
                Ligne(
                    LIBELLE_NUMERIQUES, r.hors_classification, r.pour_cent(r.hors_classification),
                    ("picto", "numeriques"), cle_aide="numeriques", rang=99,
                )
            )
        return (
            "Par classe d'actifs", f"base {f.montant(r.base)}", "pasCent", lignes,
            _restes(r, classes=True), r.base,
        )
    if rubrique == "zones":
        r = d.pays
        lignes = [
            Ligne(
                zone.libelle, montant, r.pour_cent(montant),
                ("planisphere", TERRES_DE_ZONE.get(zone.cle, [])), rang=zone.rang,
            )
            for zone, montant, _ in r.par_zone()
        ]
        return (
            "Par zone d'investisseur", "convention datée et sourcée", "zones", lignes,
            _restes(r), r.base,
        )
    if rubrique == "pays":
        r = d.pays
        codes = sorted(p.code for p in r.postes)
        lignes = [
            Ligne(
                _libelle(p), p.montant, r.pour_cent(p.montant), ("drapeau", p.code),
                cle_aide=None if p.reconnu else "codeNonReconnu", rang=codes.index(p.code),
            )
            for p in r.postes
        ]
        return "Par pays", _note_des_regles(d), "regleDePays", lignes, _restes(r), r.base
    r = d.secteurs
    lignes = [
        Ligne(
            _libelle(p),
            p.montant,
            r.pour_cent(p.montant),
            ("picto", PICTO_DE_SECTEUR.get(p.code, "")),
            cle_aide=None if p.reconnu else "codeNonReconnu",
            rang=int(p.code) if p.code.isdigit() else 999,
        )
        for p in r.postes
    ]
    return "Par secteur", "secteurs Morningstar", "secteurs", lignes, _restes(r), r.base


def _libelle(poste: Poste) -> str:
    """Le nom d'un poste, et son code quand le référentiel ne le connaît pas : il est affiché
    tel quel, jamais fondu dans « autres » (règle 5)."""
    return poste.libelle if poste.reconnu else f"{poste.code} (code non reconnu)"


def _restes(r: Repartition, classes: bool = False) -> list[Ligne]:
    """Ce qui n'entre pas dans la répartition, à sa vraie taille (D-69). Un reste nul n'est pas
    affiché : une ligne « non couvert : 0,00 € » ferait douter pour rien."""
    restes: list[Ligne] = []
    if not classes:
        for p in r.hors_perimetre_postes:
            if p.montant > ZERO:
                restes.append(
                    Ligne(
                        _libelle(p), p.montant, r.pour_cent(p.montant),
                        ("picto", PICTO_DE_CLASSE.get(p.code, "")), "horsActions", absent=True,
                    )
                )
        if r.hors_classification > ZERO:
            restes.append(
                Ligne(
                    LIBELLE_NUMERIQUES, r.hors_classification,
                    r.pour_cent(r.hors_classification), ("picto", "numeriques"), "numeriques",
                    absent=True,
                )
            )
    if r.non_attribue > ZERO:
        restes.append(
            Ligne(
                LIBELLE_NON_ATTRIBUE, r.non_attribue, r.pour_cent(r.non_attribue),
                ("picto", ""), "nonAttribue", absent=True,
            )
        )
    if r.non_couvert > ZERO:
        restes.append(
            Ligne(
                LIBELLE_NON_COUVERT, r.non_couvert, r.pour_cent(r.non_couvert), ("picto", ""),
                "nonCouvert", absent=True,
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
    enfants = [_ligne_mesuree(ligne, maxi) for ligne in visibles]
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
            _ligne_mesuree(ligne, maxi)
            for ligne in sorted(restes, key=lambda ligne: ligne.montant, reverse=True)
        ]
        if resume_des_restes is None or len(restes) < 2:
            enfants += detail
        else:
            total = sum((ligne.montant for ligne in restes), ZERO)
            part = sum((ligne.part or ZERO for ligne in restes), ZERO)
            resume = Ligne(resume_des_restes, total, part, ("picto", ""), absent=True)
            enfants.append(
                html.Details(
                    [html.Summary(_ligne_mesuree(resume, maxi), className="restes__titre"),
                     *detail],
                    className="restes",
                )
            )
    return html.Div(enfants, className="classement")


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
        className="rang" + (" rang--absent" if ligne.absent else ""),
    )


# --- Les carrés découpés ----------------------------------------------------------------

LARGEUR_DES_CARRES = 100.0
HAUTEUR_DES_CARRES = 46.0
"""Les proportions du dessin. Le calcul se fait dans ce repère, et les rectangles sont posés en
pour cent de la boîte : le dessin suit la largeur de l'écran sans rien recalculer."""

LARGEUR_POUR_UN_NOM, HAUTEUR_POUR_UN_NOM = 14.0, 9.0
LARGEUR_POUR_UNE_PART, HAUTEUR_POUR_UNE_PART = 9.0, 5.5
"""Dans le repère du dessin (100 × 46). En deçà, un carré n'a pas la place d'écrire son nom,
puis sa part, sans les couper n'importe où : il les donne au survol, et le classement à gauche
les donne toujours. C'est la **largeur** qui compte, pas la surface : une colonne étroite et
haute coupait « Europe développée » en « Europ / e dévelo / ppée »."""


def disposer(valeurs: list[float], largeur: float, hauteur: float) -> list[tuple[float, ...]]:
    """Découpe un rectangle en carrés de surfaces proportionnelles aux `valeurs`, rangées de la
    plus grande à la plus petite : la méthode « squarified » (Bruls, Huizing et van Wijk, 2000),
    qui rend des carrés aussi proches que possible de carrés vrais, donc lisibles.

    Ce n'est que de la géométrie : les montants et les parts affichés viennent du moteur. Rend
    `(x, y, largeur, hauteur)` pour chaque valeur, dans l'ordre donné."""
    total = sum(valeurs)
    if total <= 0:
        return [(0.0, 0.0, 0.0, 0.0) for _ in valeurs]
    aires = [v * largeur * hauteur / total for v in valeurs]
    rects: list[tuple[float, ...]] = []
    x, y, w, h = 0.0, 0.0, largeur, hauteur

    def pire(rangee: list[float], cote: float) -> float:
        s = sum(rangee)
        return max(max(cote * cote * r / (s * s), (s * s) / (cote * cote * r)) for r in rangee)

    restantes = [a for a in aires]
    while restantes:
        cote = min(w, h)
        rangee = [restantes[0]]
        i = 1
        while i < len(restantes) and pire(rangee + [restantes[i]], cote) <= pire(rangee, cote):
            rangee.append(restantes[i])
            i += 1
        s = sum(rangee)
        if w >= h:
            colonne = s / h
            yy = y
            for aire in rangee:
                rects.append((x, yy, colonne, aire / colonne))
                yy += aire / colonne
            x += colonne
            w -= colonne
        else:
            ligne = s / w
            xx = x
            for aire in rangee:
                rects.append((xx, y, aire / ligne, ligne))
                xx += aire / ligne
            y += ligne
            h -= ligne
        restantes = restantes[i:]
    return rects


def _bloc_carres(lignes: list[Ligne], restes: list[Ligne], base: Decimal) -> html.Section:
    """La répartition vue en surfaces : chaque carré est proportionnel à son montant, et porte
    son nom et sa part quand il a la place. Ce qui n'entre pas dans la répartition est hachuré,
    à sa vraie taille : le dessin ne se referme jamais sur les seuls postes (D-69).

    Une seule teinte pour tous les postes : c'est le nom écrit dans le carré qui l'identifie,
    pas une couleur à retrouver dans une légende."""
    parts = sorted(
        [ligne for ligne in lignes if ligne.montant > 0],
        key=lambda ligne: ligne.montant,
        reverse=True,
    ) + sorted([r for r in restes if r.montant > 0], key=lambda r: r.montant, reverse=True)
    note = f"base {f.montant(base)}"
    if len(parts) < 2:
        # Un seul carré ne dit rien que le classement ne dise (conception §5.1).
        return bloc(
            "Vu en surfaces",
            html.P(
                "Une seule part : le classement suffit, un dessin n'ajouterait rien.",
                className="vide",
            ),
            note=note,
        )
    rects = disposer(
        [float(ligne.montant) for ligne in parts], LARGEUR_DES_CARRES, HAUTEUR_DES_CARRES
    )
    carres = []
    for ligne, (x, y, w, h) in zip(parts, rects, strict=True):
        texte: list = []
        if w >= LARGEUR_POUR_UN_NOM and h >= HAUTEUR_POUR_UN_NOM:
            texte.append(html.Span(ligne.libelle, className="carre__nom"))
        if w >= LARGEUR_POUR_UNE_PART and h >= HAUTEUR_POUR_UNE_PART:
            texte.append(html.Span(f.pour_cent(ligne.part), className="carre__part nb"))
        classes = "carre" + (" carre--absent" if ligne.absent else "")
        if not texte:
            # Sans texte, pas de marge intérieure : plus large que lui, elle forçait le carré à
            # déborder de la boîte.
            classes += " carre--muet"
        carres.append(
            html.Div(
                texte,
                className=classes,
                title=f"{ligne.libelle} : {f.montant(ligne.montant)}, {f.pour_cent(ligne.part)}",
                style={
                    "left": f"{x / LARGEUR_DES_CARRES * 100:.3f}%",
                    "top": f"{y / HAUTEUR_DES_CARRES * 100:.3f}%",
                    "width": f"{w / LARGEUR_DES_CARRES * 100:.3f}%",
                    "height": f"{h / HAUTEUR_DES_CARRES * 100:.3f}%",
                },
            )
        )
    return bloc(
        "Vu en surfaces",
        html.Div(
            [
                html.Div(carres, className="carres"),
                html.P(
                    "Chaque surface est proportionnelle au montant ; les hachures sont ce qui "
                    "n'entre pas dans la répartition. Les montants exacts sont dans le "
                    "classement, à gauche.",
                    className="reference carres__renvoi",
                ),
            ]
        ),
        note=note,
    )


# --- Ce qu'il faut savoir --------------------------------------------------------------


def _a_savoir(vue: Vue, d: Diversification) -> html.Ul:
    positions = vue.construit.synthese.valorisation.positions
    noms = {p.actif: (p.position.nom_actif or p.actif) for p in positions}

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
                ["Fonds synthétiques : on affiche l'indice suivi, pas le panier détenu ",
                 *aide("synthetique")],
                ", ".join(nom(a) for a in synthetiques),
                "part",
            )
        )
    if d.declarees_a_la_main:
        lignes.append(
            ligne_de_liste(
                ["Composition déclarée par vous, donc sans date d'arrêté ",
                 *aide("declareeALaMain")],
                ", ".join(nom(a) for a in d.declarees_a_la_main),
                "part",
            )
        )
    for actif in d.pays.actifs_non_couverts:
        lignes.append(
            ligne_de_liste(
                [f"Non couvert — {nom(actif)} : {_motif_non_couvert(vue, actif)} ",
                 *aide("nonCouvert")],
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
