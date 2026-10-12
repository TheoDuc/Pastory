"""Les garde-fous communs aux tests qui traversent l'assembleur : la ligne de commande et
l'interface.

Tous détournent `PASTORY_DOSSIER` vers un dossier temporaire — **aucun test ne doit écrire dans
le vrai dossier personnel** de la personne qui lance la suite — et coupent chaque source
extérieure : **aucun test ne sort de la machine**. Un module de tests les active en les
important ; ils sont automatiques (`autouse`), pour qu'un test écrit plus tard ne puisse pas
appeler un service par simple oubli.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from pastory import assembleur
from pastory.donnees_externes.cours import ErreurDeSource


@pytest.fixture(autouse=True)
def dossier_personnel(tmp_path, monkeypatch):
    """Isole l'application du vrai dossier personnel, pour toute la durée du test."""
    personnel = tmp_path / "personnel"
    monkeypatch.setenv("PASTORY_DOSSIER", str(personnel))
    return personnel


@pytest.fixture(autouse=True)
def aucun_appel_a_xetra(monkeypatch):
    """Coupe la liste des ETF de Xetra par défaut : **aucun test ne sort de la machine**.

    Même raison que la fixture précédente, et même forme : le garde-fou est automatique,
    pour qu'un test écrit plus tard ne puisse pas appeler le service par simple oubli. Les
    tests qui ont besoin d'une liste la fournissent avec `brancher_la_liste_des_etf`.
    """

    def refuser():
        raise ErreurDeSource("aucun appel réseau dans les tests")

    monkeypatch.setattr(assembleur, "liste_des_etf", refuser)


@pytest.fixture(autouse=True)
def aucune_source_de_composition(monkeypatch):
    """Coupe les sources de composition : **aucun test ne sort de la machine** (étape 7).

    Troisième garde-fou de la même famille, et posé pour la même raison que celui de Xetra : il a
    été ajouté après avoir constaté que deux tests appelaient réellement Deutsche Börse. Ici, deux
    services sont en jeu — celui des fonds et celui des sociétés — et un seul oubli suffirait à
    faire sortir un test du poste. Les tests qui veulent une composition la fournissent
    eux-mêmes.

    Le fournisseur est construit **hors ligne** : le cache local reste utilisable, mais aucune
    source n'est interrogée.
    """
    vrai_fournisseur = assembleur.fournisseur_de_compositions

    def sans_reseau(configuration, hors_ligne: bool = False):
        return vrai_fournisseur(configuration, hors_ligne=True)

    monkeypatch.setattr(assembleur, "fournisseur_de_compositions", sans_reseau)


class CotationsMuettes:
    """La recherche des cotations, coupée : elle ne connaît rien, et ne sort pas de la machine."""

    nom = "recherche de test"

    def candidats(self, requete):
        return []

    def serie(self, actif, declaration, debut, fin):
        raise ErreurDeSource("aucun appel réseau dans les tests")

    def serie_brute(self, ticker, debut, fin):
        raise ErreurDeSource("aucun appel réseau dans les tests")


@pytest.fixture(autouse=True)
def aucune_recherche_de_reglages(monkeypatch):
    """Coupe la recherche des réglages (étape 8 quater) : **aucun test ne sort de la machine**.

    Quatrième garde-fou de la famille. Sans lui, chaque test qui lit un export chercherait en
    ligne la cotation et les frais courants de chaque actif. Les tests qui veulent une recherche
    branchent leur propre source avec `brancher_les_cotations`.
    """
    monkeypatch.setattr(assembleur, "source_des_cotations", CotationsMuettes)
    # L'émetteur ne connaît pas les fonds fictifs : c'est le cas normal d'un ETF qu'il n'émet
    # pas. Le simuler « en panne » empêcherait tout TER d'être gardé en mémoire.
    monkeypatch.setattr(assembleur, "frais_courants_de_l_emetteur", lambda: EmetteurMuet())
    monkeypatch.setattr(assembleur, "classes_d_actifs", lambda: ClassesMuettes())
    monkeypatch.setattr(assembleur, "registre_cfi", lambda: ClassesMuettes())


@pytest.fixture(autouse=True)
def rien_ne_touche_au_bureau(tmp_path, monkeypatch):
    """Détourne le bureau et le menu Démarrer, et interdit d'ouvrir une fenêtre (étape 10).

    Cinquième garde-fou : sans lui, un test de `pastory installer` écrirait de vrais raccourcis
    sur le bureau de la personne qui lance la suite, et un test du lanceur lui ouvrirait un
    navigateur. Les tests qui veulent voir une fenêtre s'ouvrir remplacent eux-mêmes le
    navigateur.
    """
    from pastory import installation, lanceur

    monkeypatch.setattr(
        installation, "_emplacements", lambda: (tmp_path / "bureau", tmp_path / "menu")
    )

    def refuser(*arguments, **options):
        raise AssertionError("aucune fenêtre ne s'ouvre pendant les tests")

    # Les modules du lanceur seulement, remplacés par des doublures : `subprocess` lui-même
    # reste entier, d'autres s'en servent.
    monkeypatch.setattr(
        lanceur, "subprocess", SimpleNamespace(Popen=refuser, DEVNULL=subprocess.DEVNULL)
    )
    monkeypatch.setattr(lanceur, "webbrowser", SimpleNamespace(open=refuser))


class EmetteurMuet:
    nom = "émetteur de test"

    def frais_courants(self, actif):
        return None


class ClassesMuettes:
    """extraETF et le registre de l'ESMA, coupés : ils ne savent rien du contenu d'un fonds."""

    def classe_d_actifs(self, actif):
        return None

    def codes_cfi(self, actif):
        return frozenset()
