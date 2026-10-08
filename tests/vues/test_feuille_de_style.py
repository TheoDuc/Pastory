"""La feuille de style et le script de dessin, contrôlés contre ce que posent les écrans.

Trois contrôles, nés de trois défauts de l'étape 8 :

- **une classe posée sans règle** ne fait rien, en silence : chaque classe des écrans et du
  script doit exister dans `pastory.css` ;
- **un sélecteur défini deux fois** : `.carte` désignait à la fois les cartes d'actifs et le
  planisphère, et la seconde règle écrasait la première. C'est un contrôle automatique qui l'a
  trouvé ; il n'était pas dans le dépôt, il y est désormais ;
- **une couleur écrite en clair dans un attribut SVG** (où `var()` n'est pas interprété) doit
  rester celle de la variable CSS du même rôle, sans quoi deux teintes « identiques » divergent.
"""

from __future__ import annotations

import re

import pytest

from pastory.vues import bandeau, ecrans
from pastory.vues import etat as etat_ecran
from pastory.vues.application import DOSSIER_DES_ASSETS
from pastory.vues.chiffres import Chiffres
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs
from tests.vues.outils import classes

CSS = (DOSSIER_DES_ASSETS / "pastory.css").read_text(encoding="utf-8")
SCRIPT = (DOSSIER_DES_ASSETS / "dessin.js").read_text(encoding="utf-8")


def _sans_commentaires(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def classes_definies() -> set[str]:
    return set(re.findall(r"\.([a-zA-Z][\w-]*)", _sans_commentaires(CSS)))


def regles_de_premier_niveau() -> list[tuple[str, set[str]]]:
    """`(sélecteur, propriétés posées)` pour chaque règle hors de toute règle `@media`."""
    # Les polices se déclarent par `@font-face`, une fois par fichier : ce ne sont pas des règles.
    css = re.sub(r"@font-face\s*\{[^}]*\}", "", _sans_commentaires(CSS))
    regles: list[tuple[str, set[str]]] = []
    for selecteurs, corps in re.findall(r"([^{}@]+)\{([^{}]*)\}", _hors_media(css)):
        proprietes = {
            declaration.split(":", 1)[0].strip()
            for declaration in corps.split(";")
            if ":" in declaration
        }
        for selecteur in selecteurs.split(","):
            regles.append((" ".join(selecteur.split()), proprietes))
    return regles


def _hors_media(css: str) -> str:
    """Le texte sans les blocs `@media { … }`, qui redéfinissent exprès pour un écran étroit."""
    sortie, profondeur, i = [], 0, 0
    while i < len(css):
        if css.startswith("@media", i) and profondeur == 0:
            j = css.index("{", i)
            niveau = 1
            j += 1
            while niveau:
                niveau += {"{": 1, "}": -1}.get(css[j], 0)
                j += 1
            i = j
            continue
        sortie.append(css[i])
        i += 1
    return "".join(sortie)


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


@pytest.mark.parametrize(
    ("cle_du_script", "variable_css"),
    [
        ("papier", "--papier"),
        ("surface", "--surface"),
        ("encreTresDouce", "--encre-tres-douce"),
        ("courbeBrut", "--courbe-brut"),
        ("courbeInvesti", "--courbe-investi"),
        ("absent", "--absent"),
    ],
)
def test_les_couleurs_du_script_sont_celles_de_la_feuille(cle_du_script, variable_css):
    dans_le_script = re.search(rf'{cle_du_script}:\s*"(#[0-9a-f]{{6}})"', SCRIPT).group(1)
    dans_la_feuille = re.search(rf"{variable_css}:\s*(#[0-9a-f]{{6}})", CSS).group(1)
    assert dans_le_script == dans_la_feuille


def test_la_feuille_interdit_le_mode_sombre_automatique():
    """Sans cette ligne, le navigateur inverse les clartés, et un gain en sauge vire au rouge."""
    assert "color-scheme: only light" in CSS


def test_rien_n_est_charge_sur_le_reseau():
    for texte in (CSS, SCRIPT):
        assert "http://" not in texte.replace("http://www.w3.org/2000/svg", "")
        assert "https://" not in texte
