"""Le thème, la feuille de style et le script de dessin, contrôlés contre ce que posent les écrans
et contre la charte graphique (docs/charte-graphique.md).

Les contrôles, nés de défauts réels :

- **une classe posée sans règle** ne fait rien, en silence : chaque classe des écrans et du
  script doit exister dans la feuille ;
- **un sélecteur défini deux fois** : `.carte` désignait à la fois les cartes d'actifs et le
  planisphère, et la seconde règle écrasait la première (étape 8) ;
- **une couleur écrite en dur hors du thème** : avant l'étape 9 bis, la même teinte vivait en
  trois endroits (la feuille, le script, une vue Python) et un test devait les garder d'accord.
  Désormais elle ne vit qu'à un endroit, `theme.css` ;
- **un contraste insuffisant**, et **de l'or en texte sur fond clair** : la charte les mesure, ce
  test les recalcule à partir du thème.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pastory.vues import bandeau, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues.application import DOSSIER_DES_ASSETS
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import classes

THEME = (DOSSIER_DES_ASSETS / "theme.css").read_text(encoding="utf-8")
FEUILLE = (DOSSIER_DES_ASSETS / "pastory.css").read_text(encoding="utf-8")
CSS = THEME + "\n" + FEUILLE
SCRIPT = (DOSSIER_DES_ASSETS / "dessin.js").read_text(encoding="utf-8")
FAVICON = (DOSSIER_DES_ASSETS / "favicon.svg").read_text(encoding="utf-8")
VUES = Path(DOSSIER_DES_ASSETS).parent

COULEUR_EN_DUR = re.compile(
    r"(?<![\w&])#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?\b"
    r"|\b(?:rgba?|hsla?)\s*\("
)


def _sans_commentaires(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _sans_commentaires_js(js: str) -> str:
    return re.sub(r"(?m)^\s*//.*$", "", _sans_commentaires(js))


def classes_definies() -> set[str]:
    return set(re.findall(r"\.([a-zA-Z][\w-]*)", _sans_commentaires(CSS)))


def regles_de_premier_niveau() -> list[tuple[str, set[str]]]:
    """`(sélecteur, propriétés posées)` pour chaque règle hors de toute règle `@media`."""
    # Les polices se déclarent par `@font-face`, une fois par fichier : ce ne sont pas des règles.
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", _sans_commentaires(CSS))
    regles: list[tuple[str, set[str]]] = []
    for selecteurs, corps in re.findall(r"([^{}@]+)\{([^{}]*)\}", _hors_blocs(css)):
        proprietes = {
            declaration.split(":", 1)[0].strip()
            for declaration in corps.split(";")
            if ":" in declaration
        }
        for selecteur in selecteurs.split(","):
            regles.append((" ".join(selecteur.split()), proprietes))
    return regles


def _hors_blocs(css: str) -> str:
    """Le texte sans les blocs `@media { … }` (qui redéfinissent exprès pour un écran étroit)
    ni `@keyframes { … }` (dont les étapes `from` et `to` ne sont pas des sélecteurs)."""
    sortie, i = [], 0
    while i < len(css):
        if css.startswith(("@media", "@keyframes"), i):
            j = css.index("{", i) + 1
            niveau = 1
            while niveau:
                niveau += {"{": 1, "}": -1}.get(css[j], 0)
                j += 1
            i = j
            continue
        sortie.append(css[i])
        i += 1
    return "".join(sortie)


# --- Le thème : ses jetons, résolus -------------------------------------------------------


BLOC_DE_NUIT = re.compile(r':root\[data-theme="sombre"\]\s*\{([^}]*)\}')


def jetons(theme: str = "clair") -> dict[str, str]:
    """Chaque variable du thème, résolue jusqu'à sa couleur quand c'en est une. La nuit
    redéfinit des rôles sur la même racine : ses valeurs l'emportent sur celles du jour."""
    texte = _sans_commentaires(THEME)
    nuit = BLOC_DE_NUIT.search(texte)
    jour = BLOC_DE_NUIT.sub("", texte)
    brut = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", jour))
    if theme == "sombre":
        brut |= dict(re.findall(r"(--[\w-]+):\s*([^;]+);", nuit.group(1)))

    def resoudre(valeur: str, profondeur: int = 0) -> str:
        reference = re.fullmatch(r"var\((--[\w-]+)\)", valeur.strip())
        if reference and profondeur < 10:
            return resoudre(brut[reference.group(1)], profondeur + 1)
        return valeur.strip().lower()

    return {nom: resoudre(valeur) for nom, valeur in brut.items()}


def contraste(a: str, b: str) -> float:
    def luminance(hexa: str) -> float:
        canaux = [int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lineaires = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
        return 0.2126 * lineaires[0] + 0.7152 * lineaires[1] + 0.0722 * lineaires[2]

    clair, sombre = sorted((luminance(a), luminance(b)), reverse=True)
    return (clair + 0.05) / (sombre + 0.05)


TEXTE_SUR_FOND = [
    # Les pages
    ("--texte", "--fond-page"),
    ("--texte", "--fond-secondaire"),
    ("--texte-secondaire", "--fond-page"),
    ("--texte-secondaire", "--fond-secondaire"),
    ("--gain", "--fond-page"),
    ("--gain", "--fond-secondaire"),
    ("--perte", "--fond-page"),
    ("--perte", "--fond-secondaire"),
    ("--reserve", "--fond-page"),
    ("--reserve", "--fond-secondaire"),
    ("--texte-mise-en-valeur", "--fond-page"),
    # Le fond du livre, derrière les boîtes : l'ouverture des chapitres, le colophon
    ("--texte", "--fond-livre"),
    ("--texte-secondaire", "--fond-livre"),
    ("--texte", "--fond-colophon"),
    ("--texte-secondaire", "--fond-colophon"),
    # La reliure
    ("--sur-reliure", "--reliure"),
    ("--sur-reliure", "--reliure-clair"),
    ("--sur-reliure-pale", "--reliure"),
    ("--sur-reliure-pale", "--reliure-clair"),
    ("--sur-reliure-or", "--reliure"),
    ("--sur-reliure-or", "--reliure-clair"),
    ("--sur-reliure-actif", "--reliure"),
    ("--sur-reliure-actif", "--reliure-clair"),
]

TRAIT_SUR_FOND = [
    "--graphique-principal",
    "--graphique-secondaire",
    "--graphique-barre",
    "--contour",
    "--poche-1",
    "--poche-2",
    "--poche-3",
]

PALETTE = {
    "#2b2118", "#3a2c20", "#b8955a", "#d4b87a",
    "#f4ecdd", "#eae0cc", "#d8cbb3", "#2a211a", "#6b5b4b",
    "#5f7a5a", "#a4553a", "#9c7a3c",
    "#4d6748", "#974b31", "#7a5c24", "#bfaf95", "#93826a", "#625241", "#9a8566",
}
"""Les couleurs de la charte (§2) : douze du propriétaire, et les variantes mesurées."""

PALETTE_DE_NUIT = {
    "#1a140f", "#17110c", "#241c15", "#2e241b", "#44372a", "#7d6b55", "#ede3d0", "#b6a68c",
    "#9db894", "#e0967b", "#c49a55", "#d7b46f", "#b09c7e", "#7a6852",
}
"""La lecture de nuit (charte §2.8, D-100)."""

OR = {"#b8955a", "#d4b87a"}

THEMES = ["clair", "sombre"]


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize(("texte", "fond"), TEXTE_SUR_FOND)
def test_chaque_texte_passe_le_niveau_aa(theme, texte, fond):
    t = jetons(theme)
    assert contraste(t[texte], t[fond]) >= 4.5, f"{texte} sur {fond}, en {theme}"


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("trait", TRAIT_SUR_FOND)
def test_chaque_trait_se_voit_sur_la_page(theme, trait):
    t = jetons(theme)
    assert contraste(t[trait], t["--fond-page"]) >= 3, f"{trait}, en {theme}"


def test_la_nuit_redefinit_les_roles_et_non_la_palette():
    """La nuit ne touche ni l'or ni la palette du jour : elle redéfinit les rôles. Le gabarit
    des graphiques, qui renvoie aux rôles, suit de lui-même."""
    jour, nuit = jetons("clair"), jetons("sombre")
    assert nuit["--or-vieilli"] == jour["--or-vieilli"]
    assert nuit["--papier"] == jour["--papier"]
    assert nuit["--graphique-principal"] == nuit["--texte"] != jour["--graphique-principal"]
    assert nuit["--fond-page"] != jour["--fond-page"]


def test_le_theme_n_emploie_que_la_palette_de_la_charte():
    couleurs = set(re.findall(r"#[0-9a-f]{6}\b", _sans_commentaires(THEME).lower()))
    admises = PALETTE | PALETTE_DE_NUIT
    assert couleurs <= admises, sorted(couleurs - admises)


def test_l_or_n_est_jamais_un_texte_sur_les_pages():
    """L'or n'a que 2,4:1 sur le papier : sur les pages, il n'est qu'un ornement (charte §2.4).
    Toute règle qui écrit en or doit viser la reliure — ou le numéro de chapitre, ornement
    caché aux lecteurs d'écran et redit par le titre."""
    t = jetons()
    regles = re.findall(r"([^{}@]+)\{([^{}]*)\}", _hors_blocs(_sans_commentaires(FEUILLE)))
    sur_la_reliure = (
        ".entete", ".onglets", ".marque", ".couverture", ".bande--titre", ".bande--filtres",
        ".groupe", ".bouton--discret", ".bouton--ouvrir", ".logo",
        # Le bouton jour / nuit n'est posé que sur la reliure : navigation, coin de la couverture.
        ".bascule-theme",
    )
    fautives = []
    for selecteurs, corps in regles:
        for declaration in corps.split(";"):
            nom, _, valeur = declaration.partition(":")
            if nom.strip() not in {"color", "fill"}:
                continue
            reference = re.fullmatch(r"\s*var\((--[\w-]+)\)\s*", valeur)
            if reference is None or t.get(reference.group(1)) not in OR:
                continue
            for selecteur in selecteurs.split(","):
                selecteur = " ".join(selecteur.split())
                if selecteur == ".ouverture__numero" or selecteur.startswith(sur_la_reliure):
                    continue
                fautives.append(selecteur)
    assert not fautives, f"de l'or en texte hors de la reliure : {fautives}"


def test_aucune_couleur_n_est_ecrite_en_dur_hors_du_theme():
    """La charte graphique : une couleur ne vit qu'à un endroit. Les drapeaux (des images) et le
    favicon (une image autonome) sont les deux exceptions assumées (charte §9)."""
    fautes: dict[str, list[str]] = {}
    sources = {
        "pastory.css": _sans_commentaires(FEUILLE),
        "dessin.js": _sans_commentaires_js(SCRIPT),
        **{
            f.name: f.read_text(encoding="utf-8")
            for f in sorted(VUES.glob("*.py"))
        },
    }
    for nom, texte in sources.items():
        trouvees = COULEUR_EN_DUR.findall(texte)
        if trouvees:
            fautes[nom] = trouvees
    assert not fautes, f"couleurs écrites en dur hors de theme.css : {fautes}"


def test_le_favicon_porte_les_couleurs_du_theme():
    t = jetons()
    couleurs = set(re.findall(r'"(#[0-9a-f]{6})"', FAVICON.lower()))
    assert couleurs == {t["--brun-reliure"], t["--or-vieilli"]}


def test_aucune_ombre_ni_texture():
    """La règle cardinale : un livre bien composé, pas un faux livre (charte §1)."""
    feuille = _sans_commentaires(FEUILLE) + _sans_commentaires(THEME)
    assert "box-shadow" not in feuille
    assert "text-shadow" not in feuille
    assert "drop-shadow" not in feuille
    assert "url(" not in _sans_commentaires(FEUILLE)
    assert "radial-gradient" not in feuille


# --- Les classes, les règles -----------------------------------------------------------------


@pytest.fixture
def tous_les_ecrans(dossier_personnel) -> list:
    rendus = [ecrans.rendre(Chiffres(), etat_ecran.initial())]
    fictifs.deposer(dossier_personnel / "exports")
    chiffres = Chiffres(hors_ligne=True)
    for onglet in [bandeau.ACCUEIL, *(o.cle for o in bandeau.ONGLETS)]:
        rendus.append(ecrans.rendre(chiffres, {**etat_ecran.initial(), "onglet": onglet}))
    return rendus


def test_chaque_classe_des_ecrans_a_sa_regle(tous_les_ecrans):
    posees = set().union(*(classes(list(rendu)) for rendu in tous_les_ecrans))
    sans_regle = posees - classes_definies()
    assert not sans_regle, f"classes posées par les écrans sans règle CSS : {sorted(sans_regle)}"


def test_chaque_classe_du_script_a_sa_regle():
    posees = set()
    for valeur in re.findall(r'class:\s*"([^"]+)"', SCRIPT):
        posees.update(valeur.split())
    sans_regle = posees - classes_definies()
    assert not sans_regle, f"classes posées par dessin.js sans règle CSS : {sorted(sans_regle)}"


def test_aucune_regle_n_en_ecrase_une_autre():
    """Deux règles d'un même sélecteur peuvent se compléter (`td.num` : l'alignement d'un côté,
    les chiffres à chasse fixe de l'autre). Elles ne doivent jamais poser **la même propriété** :
    c'est ainsi que la règle du planisphère, nommé `.carte`, écrasait la taille des cartes."""
    vues: dict[str, set[str]] = {}
    ecrasees: list[str] = []
    for selecteur, proprietes in regles_de_premier_niveau():
        communes = vues.setdefault(selecteur, set()) & proprietes
        ecrasees += [f"{selecteur} {{ {p} }}" for p in sorted(communes)]
        vues[selecteur] |= proprietes
    assert not ecrasees, f"propriétés posées deux fois pour un même sélecteur : {ecrasees}"


def test_la_feuille_interdit_le_mode_sombre_automatique():
    """Sans cette ligne, le navigateur inverse les clartés, et un gain en sauge vire au rouge.
    La nuit dit qu'elle est déjà sombre : le navigateur ne l'assombrit pas une seconde fois."""
    assert "color-scheme: only light" in THEME
    assert "color-scheme: dark" in BLOC_DE_NUIT.search(THEME).group(1)


def test_le_reduit_des_animations_est_respecte():
    """Si le système demande moins d'animations, tout devient un simple fondu (charte §7)."""
    assert "prefers-reduced-motion: reduce" in FEUILLE


def test_rien_n_est_charge_sur_le_reseau():
    for texte in (THEME, FEUILLE, SCRIPT, FAVICON):
        assert "http://" not in texte.replace("http://www.w3.org/2000/svg", "")
        assert "https://" not in texte


def test_l_onglet_porte_le_logo_de_pastory():
    """Sans icône dans les fichiers, Dash sert la sienne, et le navigateur la garde en cache.
    Le .ico (que Dash annonce avec la date du fichier) et le SVG sont ceux du logo."""
    import struct

    from pastory.vues.application import INDEX

    assert "{%favicon%}" in INDEX
    assert 'href="/assets/favicon.svg"' in INDEX
    ico = (DOSSIER_DES_ASSETS / "favicon.ico").read_bytes()
    reserve, genre, nombre = struct.unpack("<HHH", ico[:6])
    assert (reserve, genre) == (0, 1) and nombre >= 3
