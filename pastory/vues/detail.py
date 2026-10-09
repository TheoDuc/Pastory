"""Le « Détail des calculs » : comment ces chiffres sont-ils obtenus ? (conception §4.6)

Une page à part, et non un onglet de plus : elle s'ouvre depuis le bouton discret à droite de la
manchette (arbitrage du propriétaire, étape 9). Elle existe pour une seule raison : pouvoir refaire
chaque chiffre à la main. Les autres écrans montrent les résultats ; celle-ci montre les tables
qui les produisent, pour la période et les poches choisies.

Dans l'ordre de la maquette (`ongletDetail`) :

1. comment le gain est obtenu, et pourquoi il ne tombe pas sur la somme de la colonne « +/−
   latente » — le piège le plus coûteux de l'étape 8 ;
2. les flux datés, qui donnent le TRI ; les sous-périodes, qui donnent le TWRR ;
3. une estimation de bout en bout ; ce que le calcul d'impôt suppose ;
4. d'où viennent les réglages — la version écran de `pastory actifs` ;
5. à surveiller : tout ce que l'application signale, en un seul endroit.
"""

from __future__ import annotations

from decimal import Decimal

from dash import html

from pastory.config.actifs import ContenuActif, TypeActif
from pastory.moteur.couts import LigneDeCout
from pastory.pivot.operation import TypeOperation
from pastory.reglages import Cotation, Origine, Reglage, Trouvee
from pastory.vues import format as f
from pastory.vues.bandeau import NOM_DE_POCHE
from pastory.vues.briques import bloc, bloc_replie, ligne_de_liste, mot
from pastory.vues.chiffres import Vue
from pastory.vues.surveiller import Point

ZERO = Decimal("0")

LIBELLE_D_OPERATION = {
    TypeOperation.ACHAT: "Achat",
    TypeOperation.VENTE: "Vente",
    TypeOperation.DIVIDENDE: "Dividende",
}

NOM_DU_REGLAGE = {
    "cotation": "Cotation",
    "type": "Type",
    "frais courants": "Frais courants",
    "contenu": "Contenu",
}
LIBELLE_DE_VALEUR: dict[object, str] = {
    TypeActif.ETF: "ETF (fonds)",
    TypeActif.ACTION: "action",
    TypeActif.CRYPTO: "crypto-actif",
    ContenuActif.ACTIONS: "actions",
    ContenuActif.OBLIGATIONS: "obligations (hors actions)",
    ContenuActif.MATIERES_PREMIERES: "matières premières (hors actions)",
}


def ecran(vue: Vue, points: list[Point]) -> html.Div:
    return html.Div(
        [
            html.P(
                "Cette page existe pour une seule raison : pouvoir refaire chaque chiffre à la "
                "main. Les autres écrans montrent les résultats, celle-ci montre les tables qui "
                "les produisent — pour la période et les poches choisies en haut.",
                className="chapeau",
            ),
            html.Div(
                [_comment_le_gain(vue), _pourquoi_pas_la_somme(vue)],
                className="rangee rangee--deux",
            ),
            html.Div(
                [_flux_du_tri(vue), _sous_periodes(vue)],
                className="rangee rangee--deux rangee--apres",
            ),
            html.Div(
                [_une_estimation(vue), _hypotheses(vue)],
                className="rangee rangee--deux rangee--apres",
            ),
            html.Div(_reglages(vue), className="rangee rangee--large rangee--apres"),
            html.Div(
                _a_surveiller(points),
                className="rangee rangee--large rangee--apres",
                id="a-surveiller",
            ),
        ]
    )


def _nom(vue: Vue, actif: str) -> str:
    for position in vue.portefeuille.positions:
        if position.actif == actif and position.nom_actif:
            return position.nom_actif
    return actif


# --- 1. Le gain --------------------------------------------------------------------------


def _comment_le_gain(vue: Vue) -> html.Section:
    total = vue.synthese.total
    if total.gain is None:
        return bloc(
            "Comment le gain est obtenu",
            html.P(total.motif or "Le gain n'est pas calculable.", className="vide"),
            cle_aide="gain",
        )
    somme = sum((un.montant for un in total.flux), ZERO)
    debut = total.valeur_debut or ZERO
    lignes = [
        ligne_de_liste(
            f"Valeur des actifs au {f.date_courte(total.periode.fin)}", f.montant(total.valeur_fin)
        ),
        ligne_de_liste(
            "− valeur au départ"
            + (
                f", le {f.date_courte(total.periode.veille)}"
                if total.periode.veille
                else " (rien n'était détenu)"
            ),
            f.montant_signe(-debut),
        ),
        ligne_de_liste(
            f"+ somme des flux de la période ({len(total.flux)} opération"
            f"{'s' if len(total.flux) > 1 else ''}) : achats en négatif, ventes et revenus "
            "en positif",
            f.montant_signe(somme),
            f"nb {f.classe_du_signe(somme)}".strip(),
        ),
        ligne_de_liste(
            "= gain",
            f.montant_signe(total.gain),
            f"nb {f.classe_du_signe(total.gain)}".strip(),
            className="liste-parts__total",
        ),
    ]
    return bloc(
        "Comment le gain est obtenu",
        html.Ul(lignes, className="liste-parts"),
        note="glossaire §4",
        cle_aide="gain",
    )


def _pourquoi_pas_la_somme(vue: Vue) -> html.Section:
    total = vue.synthese.total
    valorisees = vue.synthese.valorisation.valorisees
    latente = sum((p.plus_value_latente or ZERO for p in valorisees), ZERO)
    ecart = None if total.gain is None else total.gain - latente
    non_valorisees = [
        p.position.nom_actif or p.actif for p in vue.synthese.valorisation.non_valorisees
    ]
    texte = (
        "Le gain se calcule sur les montants bruts, sans les frais. La plus-value latente se "
        "mesure contre le capital net investi, qui est net de frais et réduit au prorata des "
        "ventes. Les deux sont justes, et ils ne se rejoignent pas : l'écart vient des frais, "
        "des ventes passées, des revenus reçus — et des parts détenues avant le début de la "
        "période."
    )
    if non_valorisees:
        texte += (
            " S'y ajoute le capital des lignes sans cours, exclues de la performance : "
            + ", ".join(non_valorisees)
            + "."
        )
    return bloc(
        "Pourquoi il ne tombe pas sur la somme de la colonne",
        html.Div(
            [
                html.Ul(
                    [
                        ligne_de_liste(
                            "Gain, sur les flux bruts",
                            f.montant_signe(total.gain),
                            f"nb {f.classe_du_signe(total.gain)}".strip(),
                        ),
                        ligne_de_liste(
                            "Somme de la colonne « +/− latente » des actifs",
                            f.montant_signe(latente),
                            f"nb {f.classe_du_signe(latente)}".strip(),
                        ),
                        ligne_de_liste(
                            "Écart, qui est normal",
                            f.montant_signe(ecart),
                            "nb",
                            className="liste-parts__total",
                        ),
                    ],
                    className="liste-parts",
                ),
                html.P(texte, className="chapeau detail__explication"),
            ]
        ),
    )


# --- 2. Le TRI et le TWRR ---------------------------------------------------------------


def _flux_du_tri(vue: Vue) -> html.Section:
    total = vue.synthese.total
    table = total.table_du_tri
    if not table:
        return bloc(
            "Les flux datés, qui donnent le TRI",
            html.P(total.motif or "Aucun flux sur la période.", className="vide"),
            cle_aide="tri",
        )
    lignes = []
    for ligne in table:
        if ligne.flux is None:
            libelle, actif = ligne.libelle.capitalize(), "—"
        else:
            libelle = LIBELLE_D_OPERATION.get(ligne.flux.type, ligne.libelle.capitalize())
            actif = [
                html.Span(_nom(vue, ligne.flux.actif), className="actif__nom"),
                html.Span(NOM_DE_POCHE[ligne.flux.poche], className="actif__code"),
            ]
        lignes.append(
            html.Tr(
                [
                    html.Td(f.date_courte(ligne.date)),
                    html.Td(libelle),
                    html.Td(actif),
                    html.Td(
                        f.montant_signe(ligne.montant),
                        className=f"num {f.classe_du_signe(ligne.montant)}".strip(),
                    ),
                ]
            )
        )
    tableau = html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Date"),
                            html.Th("Opération"),
                            html.Th("Actif"),
                            html.Th("Montant brut", className="num"),
                        ]
                    )
                ),
                html.Tbody(lignes),
                html.Tfoot(
                    html.Tr(
                        [
                            html.Td("Taux qui annule la valeur actuelle nette = TRI", colSpan=3),
                            html.Td(
                                f.taux(total.tri),
                                className=f"num {f.classe_du_taux(total.tri)}".strip(),
                            ),
                        ]
                    )
                ),
            ]
        ),
        className="cadre-tableau",
        style={"--hauteur-tableau": "330px"},
    )
    return bloc(
        "Les flux datés, qui donnent le TRI",
        tableau,
        note=f"à coller dans TRI.PAIEMENTS · {len(table)} lignes",
        classes="bloc--plein",
        cle_aide="tri",
    )


def _sous_periodes(vue: Vue) -> html.Section:
    twrr = vue.synthese.total.twrr
    if not twrr.sous_periodes:
        return bloc(
            "Les sous-périodes, qui donnent le TWRR",
            html.P(twrr.motif or "Aucune sous-période sur la période.", className="vide"),
            cle_aide="twrr",
        )
    lignes = [
        html.Tr(
            [
                html.Td(f.date_courte(s.du)),
                html.Td(f.date_courte(s.au)),
                html.Td(f.montant(s.valeur_debut), className="num"),
                html.Td(f.montant_signe(s.flux), className="num"),
                html.Td(f.montant(s.valeur_fin), className="num"),
                html.Td(
                    f.taux(s.rendement), className=f"num {f.classe_du_taux(s.rendement)}".strip()
                ),
            ]
        )
        for s in twrr.sous_periodes
    ]
    tableau = html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Du"),
                            html.Th("Au"),
                            html.Th("Valeur début", className="num"),
                            html.Th("Entrées", className="num"),
                            html.Th("Valeur fin", className="num"),
                            html.Th("Rendement", className="num"),
                        ]
                    )
                ),
                html.Tbody(lignes),
                html.Tfoot(
                    html.Tr(
                        [
                            html.Td("Produit des (1 + rendement), moins un = TWRR", colSpan=5),
                            html.Td(
                                f.taux(twrr.taux),
                                className=f"num {f.classe_du_taux(twrr.taux)}".strip(),
                            ),
                        ]
                    )
                ),
            ]
        ),
        className="cadre-tableau",
        style={"--hauteur-tableau": "330px"},
    )
    nombre = len(twrr.sous_periodes)
    return bloc(
        "Les sous-périodes, qui donnent le TWRR",
        tableau,
        note=f"{nombre} sous-période{'s' if nombre > 1 else ''}",
        classes="bloc--plein",
        cle_aide="twrr",
    )


# --- 3. Une estimation, et les hypothèses de l'impôt ------------------------------------


def _exemple(vue: Vue) -> LigneDeCout | None:
    """L'achat le plus récent dont le spread a été estimé : un cas réel, refaisable."""
    candidates = [
        ligne
        for ligne in vue.construit.detail_des_couts.lignes
        if ligne.type is TypeOperation.ACHAT and ligne.spread_estime is not None
    ]
    return max(candidates, key=lambda ligne: ligne.date) if candidates else None


def _une_estimation(vue: Vue) -> html.Section:
    ligne = _exemple(vue)
    if ligne is None:
        return bloc(
            "Une estimation, de bout en bout",
            html.P("Aucun achat dont le spread soit estimable.", className="vide"),
            cle_aide="estime",
        )
    estimation = ligne.spread_estime
    parametre = estimation.parametre
    fourchette = (
        f" (mesures entre {parametre.basse} et {parametre.haute} {parametre.unite})"
        if parametre.basse is not None and parametre.haute is not None
        else ""
    ).replace(".", ",")
    lignes = [
        ligne_de_liste(
            f"Achat de {_nom(vue, ligne.actif)} le {f.date_courte(ligne.date)}",
            f.montant(ligne.montant_brut),
        ),
        ligne_de_liste("Frais d'ordre réellement prélevés", f.montant(ligne.frais)),
        ligne_de_liste("Poids des frais dans l'opération", f.taux(ligne.poids, signe=False)),
        ligne_de_liste(
            [
                "Spread estimé : ",
                f"{f.montant(estimation.base)} × {parametre.en_clair} ",
                mot("Estimé"),
            ],
            f.montant(estimation.montant),
        ),
        ligne_de_liste(f"Taux employé{fourchette}", parametre.en_clair),
    ]
    source = f"Source du taux : {parametre.source}" + (
        f" — {parametre.origine}" if parametre.origine else ""
    )
    return bloc(
        "Une estimation, de bout en bout",
        html.Div(
            [
                html.Ul(lignes, className="liste-parts"),
                html.P(source, className="reference detail__explication"),
            ]
        ),
        note="un exemple réel",
        cle_aide="estime",
    )


def _hypotheses(vue: Vue) -> html.Section:
    valeur = vue.construit.valeur_reelle
    hypotheses: list[str] = []
    composantes: list = []
    for poche, groupe in valeur.par_poche.items():
        for hypothese in groupe.impot.hypotheses:
            if hypothese not in hypotheses:
                hypotheses.append(hypothese)
        for libelle, montant in groupe.impot.composantes:
            composantes.append(
                ligne_de_liste(f"{NOM_DE_POCHE[poche]} — {libelle}", f.montant(montant))
            )
    lignes = [ligne_de_liste(h) for h in hypotheses]
    if composantes:
        lignes.append(
            ligne_de_liste("De quoi la base imposable est faite", className="liste-parts__total")
        )
        lignes += composantes
    if not lignes:
        lignes = [ligne_de_liste("Aucune position détenue : aucun impôt n'est estimé.")]
    nombre = len(hypotheses)
    return bloc(
        "Ce que le calcul d'impôt suppose",
        html.Ul(lignes, className="liste-parts"),
        note=f"{nombre} hypothèse{'s' if nombre > 1 else ''}",
        cle_aide="baseImposable",
    )


# --- 4. D'où viennent les réglages ------------------------------------------------------


def _reglages(vue: Vue) -> html.Section:
    """La version écran de `pastory actifs` : chaque réglage, sa source, sa date, ce qui a été
    vérifié — ou le motif de son absence (D-80). Repliée par défaut."""
    reglages = vue.construit.reglages
    if reglages is None or not reglages.actifs:
        return bloc(
            "D'où viennent les réglages", html.P("Aucun actif dans vos exports.", className="vide")
        )
    trouves = corriges = trous = 0
    lignes: list = []
    for actif, du_actif in sorted(reglages.actifs.items()):
        lignes.append(
            ligne_de_liste(f"{du_actif.nom or actif} — {actif}", className="liste-parts__total")
        )
        for nom, reglage in du_actif.reglages():
            if reglage.trou is not None:
                trous += 1
            elif reglage.retenu.origine.corrigee:
                corriges += 1
            else:
                trouves += 1
            lignes.append(_ligne_de_reglage(NOM_DU_REGLAGE.get(nom, nom), reglage))
    if reglages.premier_versement_pea is not None:
        lignes.append(ligne_de_liste("PEA", className="liste-parts__total"))
        lignes.append(_ligne_de_reglage("Date d'ouverture", reglages.premier_versement_pea))
    for actif in reglages.orphelines:
        lignes.append(
            ligne_de_liste(
                [
                    mot("Correction sans actif", "absent"),
                    f" {actif} : une correction désigne un actif qu'aucun de vos exports "
                    "ne contient.",
                ]
            )
        )
    note = (
        f"{trouves} trouvée{'s' if trouves > 1 else ''} seule{'s' if trouves > 1 else ''}, "
        f"{corriges} corrigée{'s' if corriges > 1 else ''} par vous, "
        f"{trous} introuvable{'s' if trous > 1 else ''}"
    )
    return bloc_replie(
        "D'où viennent les réglages", html.Ul(lignes, className="liste-parts"), note=note
    )


def _ligne_de_reglage(nom: str, reglage: Reglage) -> html.Li:
    retenu = reglage.retenu
    if not isinstance(retenu, Trouvee):
        return ligne_de_liste([f"{nom} : ", mot("Introuvable", "absent"), f" {retenu.motif}"])
    detail = [_origine(retenu.origine)]
    if retenu.origine.controle:
        detail.append(f"vérifié : {retenu.origine.controle}")
    if retenu.origine.reserve:
        detail.append(f"à savoir : {retenu.origine.reserve}")
    if reglage.ecarte is not None:
        detail.append(
            f"la source donnait : {_valeur(reglage.ecarte.valeur)} "
            f"({_origine(reglage.ecarte.origine)})"
        )
    return html.Li(
        [
            html.Span([f"{nom} : ", html.B(_valeur(retenu.valeur))], className="liste-parts__nom"),
            html.Span(" · ".join(detail), className="reference detail__origine"),
        ]
    )


def _origine(origine: Origine) -> str:
    if origine.corrigee:
        return "corrigé par vous"
    date = f", {origine.intitule_de_la_date} {f.date_courte(origine.date)}" if origine.date else ""
    return f"trouvé : {origine.source}{date}"


def _valeur(valeur: object) -> str:
    if isinstance(valeur, Cotation):
        return f"{valeur.ticker}, en {valeur.devise}" + (
            f" ({valeur.place})" if valeur.place else ""
        )
    if isinstance(valeur, TypeActif | ContenuActif):
        return LIBELLE_DE_VALEUR.get(valeur, valeur.value)
    if isinstance(valeur, Decimal):
        return f"{f.pour_cent(valeur)} par an"
    if hasattr(valeur, "strftime"):
        return f.date_courte(valeur)
    return str(valeur)


# --- 5. À surveiller --------------------------------------------------------------------


def _a_surveiller(points: list[Point]) -> html.Section:
    """Tout ce que l'application signale, en un seul endroit (conception §1.7). Chaque point
    reste aussi marqué là où son chiffre s'affiche."""
    if not points:
        contenu: object = html.P(
            "Rien à signaler : chaque opération a été lue, chaque actif a un cours, chaque "
            "réglage a été trouvé.",
            className="vide",
        )
    else:
        contenu = html.Div(
            html.Ul(
                [
                    html.Li(
                        [
                            html.B(point.categorie),
                            html.Span(point.message),
                            html.Span(
                                f"référence : {point.reference}",
                                className="reference",
                                style={"display": "block", "marginTop": "2px"},
                            )
                            if point.reference
                            else None,
                        ]
                    )
                    for point in points
                ]
            ),
            className="surveiller",
        )
    nombre = len(points)
    return bloc(
        "À surveiller",
        contenu,
        note=f"{nombre} point{'s' if nombre > 1 else ''}" if nombre else None,
    )
