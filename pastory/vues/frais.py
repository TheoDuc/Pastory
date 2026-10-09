"""L'onglet « Frais et taxes » : combien tout cela coûte ? (conception §4.5)

**Trois niveaux à la file, sur un seul écran** (D-73). Le découpage porte la séparation entre ce
qui a été **payé** et ce qui est **estimé** (D-17), et non une chronologie (D-75) :

1. **ce qui a déjà été prélevé** — frais d'ordre, taxes, retenue à la source sur les dividendes :
   des montants qui figurent sur les relevés. Le spread d'entrée y est rappelé, marqué estimé ;
2. **pendant la détention, les frais courants** — TER et spread de sortie, estimés, chacun avec
   son taux, sa date et sa source (D-58) ;
3. **à la sortie, par poche** — la valeur réelle (D-23), impôt estimé compris, poche par poche
   parce que la fiscalité l'est.

**Aucun filtre** (conception §4) : ce sont les coûts de tout le portefeuille, depuis la première
opération. Tous les montants viennent du moteur (`DetailDesCouts`, `ValeurReelle`) ; les seuls
calculs de cet écran sont des **sommes de lignes affichées** et trois taux moyens, dont la base
est écrite à côté.
"""

from __future__ import annotations

from decimal import Decimal

from dash import html

from pastory.config.actifs import TypeActif
from pastory.moteur.couts import DetailDesCouts, FraisCourantsEstimes
from pastory.moteur.valeur_reelle import ValeurReelle
from pastory.pivot.operation import Poche, TypeOperation
from pastory.vues import format as f
from pastory.vues.bandeau import jeton
from pastory.vues.briques import aide, bloc, bloc_replie, ligne_de_liste, mot, tuile
from pastory.vues.chiffres import Vue

ZERO = Decimal("0")


def ecran(vue: Vue) -> html.Div:
    base = vue.construit
    detail = base.detail_des_couts
    valeur = base.valeur_reelle
    return html.Div(
        [
            html.Div(_tuiles(detail, valeur), className="tuiles"),
            html.Div(_preleve(detail), className="rangee rangee--large rangee--apres"),
            html.Div(
                _detention(vue, detail, valeur), className="rangee rangee--large rangee--apres"
            ),
            html.Div(
                [_par_poche(valeur), _si_vous_vendiez(valeur)],
                className="rangee rangee--apres",
            ),
            html.Div(
                _d_ou_viennent_les_taux(detail, valeur),
                className="rangee rangee--large rangee--apres",
            ),
        ]
    )


# --- Les sommes de l'écran --------------------------------------------------------------


def _spread_par_moment(detail: DetailDesCouts, moment: str) -> tuple[Decimal, Decimal]:
    """`(spread estimé, montant brut exécuté)` des opérations d'un moment : le taux moyen se lit
    sur cette base, écrite à côté."""
    spread = brut = ZERO
    for ligne in detail.lignes:
        if ligne.moment == moment and ligne.spread_estime is not None:
            spread += ligne.spread_estime.montant
            brut += ligne.montant_brut or ZERO
    return spread, brut


def _taux_moyen(montant: Decimal, base: Decimal) -> Decimal | None:
    return montant / base if base > ZERO else None


def _frais_courants(detail: DetailDesCouts) -> tuple[Decimal, Decimal]:
    """`(frais courants estimés à un an, valeur des fonds concernés)`."""
    estimes = [fc for fc in detail.frais_courants if fc.estimation is not None]
    montant = sum((fc.estimation.montant for fc in estimes), ZERO)
    base = sum((fc.estimation.base or ZERO for fc in estimes), ZERO)
    return montant, base


# --- Les tuiles ------------------------------------------------------------------------


def _tuiles(detail: DetailDesCouts, valeur: ValeurReelle) -> list:
    total = detail.total
    ordres = sum(1 for ligne in detail.lignes if ligne.frais > ZERO)
    spread_entree, brut_entree = _spread_par_moment(detail, "à l'entrée")
    frais_courants, base_ter = _frais_courants(detail)
    taux_entree = _taux_moyen(spread_entree, brut_entree)
    taux_sortie = _taux_moyen(valeur.spread, valeur.valeur_brute)
    taux_ter = _taux_moyen(frais_courants, base_ter)
    return [
        tuile(
            "Payé depuis le début",
            f.montant(total.cout_paye),
            petit=True,
            ton="perte" if total.cout_paye > ZERO else "neutre",
            cle_aide="coutsPreleves",
            pied=f"{ordres} ordre{'s' if ordres > 1 else ''} · {f.montant(total.frais)} de "
            f"frais, {f.montant(total.taxes)} de taxes",
        ),
        tuile(
            "Poids moyen d'un coût",
            f.taux(total.poids_moyen, signe=False),
            petit=True,
            pied="du montant brut de l'opération",
        ),
        tuile(
            "Spread d'entrée estimé",
            f.montant(spread_entree),
            petit=True,
            cle_aide="spread",
            pied=[mot("Estimé"), f" {f.taux(taux_entree, signe=False)} des achats"]
            if taux_entree is not None
            else "aucun achat estimable",
        ),
        tuile(
            "Spread de sortie estimé",
            f.montant(valeur.spread),
            petit=True,
            cle_aide="spread",
            pied=[mot("Estimé"), f" {f.taux(taux_sortie, signe=False)} de la valeur"]
            if taux_sortie is not None
            else "aucune position valorisée",
        ),
        tuile(
            "Frais courants à un an",
            f.montant(frais_courants),
            petit=True,
            cle_aide="ter",
            pied=[mot("Estimé"), f" {f.taux(taux_ter, signe=False)} des fonds"]
            if taux_ter is not None
            else "aucun fonds dont le TER est connu",
        ),
    ]


# --- 1. Ce qui a déjà été prélevé ------------------------------------------------------


def _preleve(detail: DetailDesCouts) -> html.Section:
    total = detail.total
    ordres = sum(1 for ligne in detail.lignes if ligne.frais > ZERO)
    retenue = sum(
        (ligne.taxes for ligne in detail.lignes if ligne.type is TypeOperation.DIVIDENDE), ZERO
    )
    taxes_d_ordre = total.taxes - retenue
    spread_entree, brut_entree = _spread_par_moment(detail, "à l'entrée")
    spread_ventes, _ = _spread_par_moment(detail, "à la sortie")
    taux_entree = _taux_moyen(spread_entree, brut_entree)

    lignes = [
        ligne_de_liste(
            f"Frais d'ordre payés, sur {ordres} ordre{'s' if ordres > 1 else ''}",
            f.montant(total.frais),
            "nb",
        )
    ]
    if taxes_d_ordre > ZERO:
        lignes.append(
            ligne_de_liste("Taxes sur les achats et les ventes", f.montant(taxes_d_ordre), "nb")
        )
    lignes.append(
        ligne_de_liste(
            ["Retenue à la source sur les dividendes ", *aide("retenueDividendes")],
            f.montant(retenue),
            "nb",
        )
    )
    lignes.append(
        ligne_de_liste(
            "Total réellement prélevé",
            f.montant(total.cout_paye),
            "nb",
            className="liste-parts__total",
        )
    )
    lignes.append(
        ligne_de_liste(
            [
                "Spread payé à l'achat"
                + (f", {f.taux(taux_entree, signe=False)} en moyenne " if taux_entree else " "),
                mot("Estimé"),
                *aide("spread"),
            ],
            f.montant(spread_entree),
            "nb",
        )
    )
    if spread_ventes > ZERO:
        lignes.append(
            ligne_de_liste(
                ["Spread payé sur les ventes passées ", mot("Estimé")],
                f.montant(spread_ventes),
                "nb",
            )
        )
    if total.actifs_sans_type:
        lignes.append(
            ligne_de_liste(
                [
                    mot("Partiel", "absent"),
                    f" Aucun spread n'est estimé pour {len(total.actifs_sans_type)} actif(s) dont "
                    "le type (ETF, action, crypto) n'est pas connu : le montant ci-dessus est "
                    "donc plus bas que la réalité.",
                ]
            )
        )
    return bloc(
        "1. Ce qui a déjà été prélevé",
        html.Ul(lignes, className="liste-parts"),
        note=f"réel, sauf le spread · du {_debut(detail)} au {f.date_courte(detail.periode.fin)}",
        cle_aide="coutsPreleves",
    )


def _debut(detail: DetailDesCouts) -> str:
    if detail.periode.debut is not None:
        return f.date_courte(detail.periode.debut)
    jours = [ligne.date for ligne in detail.lignes]
    return f.date_courte(min(jours)) if jours else "début"


# --- 2. Pendant la détention -----------------------------------------------------------


def _detention(vue: Vue, detail: DetailDesCouts, valeur: ValeurReelle) -> html.Section:
    ter = {(fc.actif, fc.poche): fc for fc in detail.frais_courants}
    lignes_vr = [ligne for groupe in valeur.par_poche.values() for ligne in groupe.lignes]
    if not lignes_vr:
        return bloc(
            "2. Pendant la détention — les frais courants",
            html.P("Aucune position valorisée : il n'y a rien à estimer.", className="vide"),
        )
    corps = []
    for ligne in sorted(lignes_vr, key=lambda une: une.valeur_brute, reverse=True):
        position = ligne.position
        nom = position.position.nom_actif or position.actif
        frais = ter.get((position.actif, position.poche))
        corps.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Span(nom, className="actif__nom", title=nom),
                            html.Span(position.actif, className="actif__code"),
                        ]
                    ),
                    html.Td(jeton(position.poche)),
                    html.Td(f.montant(ligne.valeur_brute), className="num"),
                    _cellule_ter(frais),
                    _cellule_frais_courants(vue, position.actif, frais),
                    html.Td(
                        f"{f.montant(ligne.spread.montant)} · {ligne.spread.parametre.en_clair}",
                        className="num",
                        title=_origine(ligne.spread.parametre),
                    ),
                ]
            )
        )
    frais_courants, _ = _frais_courants(detail)
    tableau = html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Actif"),
                            html.Th("Poche"),
                            html.Th("Valeur", className="num"),
                            html.Th("TER", className="num"),
                            html.Th("Frais courants / an", className="num"),
                            html.Th("Spread de sortie", className="num"),
                        ]
                    )
                ),
                html.Tbody(corps),
                html.Tfoot(
                    html.Tr(
                        [
                            html.Td("Total estimé", colSpan=4),
                            html.Td(f.montant(frais_courants), className="num"),
                            html.Td(f.montant(valeur.spread), className="num"),
                        ]
                    )
                ),
            ]
        ),
        className="cadre-tableau",
    )
    return bloc(
        "2. Pendant la détention — les frais courants",
        tableau,
        note=[mot("Estimé"), " taux, date et source au survol"],
        classes="bloc--plein",
        cle_aide="ter",
    )


def _cellule_ter(frais: FraisCourantsEstimes | None) -> html.Td:
    if frais is None or frais.estimation is None:
        return html.Td(f.ABSENT, className="num")
    parametre = frais.estimation.parametre
    return html.Td(f.pour_cent(parametre.valeur), className="num", title=_origine(parametre))


def _cellule_frais_courants(vue: Vue, actif: str, frais: FraisCourantsEstimes | None) -> html.Td:
    """Le montant, ou **pourquoi** il manque : « sans objet » n'est pas « introuvable »."""
    if frais is not None and frais.estimation is not None:
        return html.Td(f.montant(frais.estimation.montant), className="num")
    if frais is not None and frais.motif:
        # La marque dans la cellule, la phrase au survol : écrite en entier, elle étirait la
        # colonne et décalait tout le tableau. Le motif complet est aussi dans « à surveiller ».
        return html.Td(
            mot("TER introuvable", "absent", title=frais.motif),
            className="num",
            title=frais.motif,
        )
    type_actif = _type(vue, actif)
    texte = {
        TypeActif.ACTION: "sans objet : une action n'a pas de TER",
        TypeActif.CRYPTO: "sans objet",
    }.get(type_actif, "type inconnu : pas de TER estimable")
    return html.Td(html.Span(texte, className="actif__code"), className="num")


def _type(vue: Vue, actif: str) -> TypeActif | None:
    reglages = vue.construit.reglages
    if reglages is None or actif not in reglages.actifs:
        return None
    return reglages.actifs[actif].type.valeur


def _origine(parametre) -> str:
    """« 0,20 % — liste des ETF de Xetra, en vigueur depuis le … » : la source d'un taux, au
    survol de la cellule qui l'emploie (D-58)."""
    origine = parametre.origine
    return f"{parametre.en_clair} — {parametre.source}" + (f", {origine}" if origine else "")


# --- 3. À la sortie --------------------------------------------------------------------


def _par_poche(valeur: ValeurReelle) -> html.Section:
    if not valeur.par_poche:
        return bloc(
            "3. À la sortie — par poche",
            html.P("Aucune position détenue : rien à vendre.", className="vide"),
        )
    corps = []
    for poche in Poche:
        groupe = valeur.par_poche.get(poche)
        if groupe is None:
            continue
        impot = groupe.impot
        regle: list = [impot.regle]
        if groupe.minoree:
            regle += [" ", mot("Minorée"), *aide("minoree")]
        if groupe.partielle:
            regle += [" ", mot("Partiel", "absent")]
        if groupe.motif_incalculable:
            regle.append(
                html.Span(
                    groupe.motif_incalculable, className="actif__code", style={"display": "block"}
                )
            )
        corps.append(
            html.Tr(
                [
                    html.Td(jeton(poche)),
                    html.Td(f.montant(groupe.valeur_brute), className="num"),
                    html.Td(f.montant(impot.base), className="num"),
                    html.Td(f.pour_cent(impot.taux), className="num"),
                    html.Td(f.montant(impot.impot), className="num"),
                    html.Td(f.montant(groupe.valeur_reelle), className="num"),
                    html.Td(regle),
                ]
            )
        )
    tableau = html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Poche"),
                            html.Th("Valeur brute", className="num"),
                            html.Th("Base imposable", className="num"),
                            html.Th("Taux", className="num"),
                            html.Th("Impôt estimé", className="num"),
                            html.Th("Valeur réelle", className="num"),
                            html.Th("Règle appliquée"),
                        ]
                    )
                ),
                html.Tbody(corps),
                html.Tfoot(
                    html.Tr(
                        [
                            html.Td("Total"),
                            html.Td(f.montant(valeur.valeur_brute), className="num"),
                            html.Td(),
                            html.Td(),
                            html.Td(f.montant(valeur.impot), className="num"),
                            html.Td(f.montant(valeur.valeur_reelle), className="num"),
                            html.Td(),
                        ]
                    )
                ),
            ]
        ),
        className="cadre-tableau",
    )
    return bloc(
        "3. À la sortie — par poche", tableau, classes="bloc--plein", cle_aide="baseImposable"
    )


def _si_vous_vendiez(valeur: ValeurReelle) -> html.Section:
    """La cascade de la valeur réelle : chaque retenue est une estimation, et le dit (D-23)."""
    base_imposable = sum((g.impot.base or ZERO for g in valeur.par_poche.values()), ZERO)
    lignes = [
        ligne_de_liste("Valeur brute des actifs", f.montant(valeur.valeur_brute), "nb"),
        ligne_de_liste(
            "− frais de vente estimés", f.montant_signe(-valeur.frais_de_vente), "nb perte"
        ),
        ligne_de_liste("− spread de sortie estimé", f.montant_signe(-valeur.spread), "nb perte"),
        ligne_de_liste(
            f"− impôt estimé, sur {f.montant(base_imposable)} de base imposable",
            f.montant_signe(-valeur.impot),
            "nb perte",
        ),
        ligne_de_liste(
            "Valeur réelle", f.montant(valeur.valeur_reelle), "nb", className="liste-parts__total"
        ),
    ]
    if valeur.valeur_reelle is not None:
        lignes.append(
            ligne_de_liste(
                "Ce que la sortie coûterait",
                f.montant(valeur.valeur_brute - valeur.valeur_reelle),
                "nb",
            )
        )
    if valeur.minoree:
        lignes.append(
            ligne_de_liste(
                [
                    mot("Minorée"),
                    f" Au moins {f.montant(valeur.hors_des_titres)} de gains déjà encaissés dans "
                    "un plan sont restés dans ses espèces, que l'application ne suit pas. Leur "
                    "impôt est compté, leur argent non : le montant réellement dû serait plus "
                    "élevé que l'argent compté ici, donc vous toucheriez davantage.",
                ]
            )
        )
    for exclue in valeur.exclues:
        nom = exclue.position.position.nom_actif or exclue.position.actif
        lignes.append(
            ligne_de_liste([mot("Partiel", "absent"), f" {nom} n'est pas compté : {exclue.motif}"])
        )
    note = [mot("Minorée"), *aide("minoree")] if valeur.minoree else [mot("Estimé")]
    return bloc(
        "Si vous vendiez tout aujourd'hui",
        html.Ul(lignes, className="liste-parts"),
        note=note,
        cle_aide="valeurReelle",
    )


# --- D'où viennent les taux ------------------------------------------------------------


def _d_ou_viennent_les_taux(detail: DetailDesCouts, valeur: ValeurReelle) -> html.Section:
    """Chaque taux employé, avec sa valeur, sa date et sa source (D-58) : fermé par défaut, comme
    « ce qu'il faut savoir » de la diversification."""
    lignes = [
        ligne_de_liste(
            f"{p.nom} : {p.en_clair}",
            f"{p.source}" + (f" — {p.origine}" if p.origine else ""),
            "reference",
        )
        for p in valeur.parametres_cites
    ]
    par_source: dict[str, list[str]] = {}
    for fc in detail.frais_courants:
        if fc.estimation is None:
            continue
        p = fc.estimation.parametre
        cle = p.source + (f" — {p.origine}" if p.origine else "")
        nom = fc.position.position.nom_actif or fc.actif
        if nom not in par_source.setdefault(cle, []):
            par_source[cle].append(nom)
    for source, noms in par_source.items():
        lignes.append(ligne_de_liste(f"TER de {', '.join(noms)}", source, "reference"))
    lignes.append(
        ligne_de_liste(
            "Ne sont pas comptés : l'impôt sur les dividendes déjà reçus et sur les ventes déjà "
            "faites. Il est dû quoi qu'il arrive : ce n'est pas un coût de sortie."
        )
    )
    return bloc_replie(
        "D'où viennent les taux",
        html.Ul(lignes, className="liste-parts"),
        note="valeur, date et source de chaque taux employé",
    )
