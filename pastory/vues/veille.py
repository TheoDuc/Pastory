"""La veille : savoir si une page de Pastory est encore ouverte, pour s'arrêter avec elle (D-106).

Lancé par son raccourci, Pastory n'a ni terminal ni Ctrl+C : **fermer la fenêtre doit l'arrêter**,
sans quoi il resterait en mémoire à chaque utilisation. Le serveur ne voit pas la fenêtre ; c'est
donc la page qui lui donne signe de vie (`application.py`, `SIGNE_DE_VIE`) :

- toutes les quelques secondes, **un signe** ;
- à sa fermeture, **un adieu**.

Le serveur s'arrête quand plus aucune page ne vit. Trois précautions, chacune née d'un cas réel :

- **le silence se compte en battements, pas à l'horloge.** Un ordinateur mis en veille ne bat
  plus : à son réveil, une heure a passé à l'horloge et un seul battement ici. Pastory ne
  s'arrête donc pas pendant que la machine dort ;
- **un long silence est toléré avant de conclure** (`SILENCE_MAXIMAL`). Un navigateur ralentit
  une page masquée jusqu'à un signe par minute, et sur la machine du propriétaire un antivirus
  coupe une connexion locale sur dix (`FILET_DE_CHARGEMENT`) : un ou deux signes perdus ne
  doivent pas arrêter une fenêtre simplement réduite ;
- **un adieu n'arrête rien tout de suite** (`DELAI_DE_FERMETURE`). Recharger la page, c'est la
  fermer puis la rouvrir : la nouvelle page doit avoir le temps de se présenter.

Ce module ne connaît ni Dash ni le réseau : le lanceur le charge avant tout le reste.
"""

from __future__ import annotations

import threading

CHEMIN = "/pastory/vie"
"""L'adresse où la page donne signe de vie, et où le lanceur demande « qui est là ? »."""

BATTEMENT = 1.0
"""Secondes entre deux battements."""

SILENCE_MAXIMAL = 300
"""Battements sans signe après lesquels une page est tenue pour fermée (cinq minutes)."""

DELAI_DE_FERMETURE = 8
"""Battements sans aucune page après lesquels Pastory s'arrête."""

ATTENTE_DE_LA_PREMIERE_PAGE = 300
"""Battements laissés au navigateur pour ouvrir la première page. Passé ce délai, personne ne
viendra : Pastory s'arrête plutôt que de rester en mémoire sans fenêtre."""

LONGUEUR_D_UN_NOM = 40
PAGES_SUIVIES = 50


class Veille:
    """Qui est encore là. `signe` et `adieu` viennent des pages, `battre` d'une horloge."""

    def __init__(
        self,
        silence_maximal: int = SILENCE_MAXIMAL,
        delai_de_fermeture: int = DELAI_DE_FERMETURE,
        attente_de_la_premiere_page: int = ATTENTE_DE_LA_PREMIERE_PAGE,
    ) -> None:
        self._silence_maximal = silence_maximal
        self._delai_de_fermeture = delai_de_fermeture
        self._attente = attente_de_la_premiere_page
        self._verrou = threading.Lock()
        self._silences: dict[str, int] = {}
        """Par page ouverte, le nombre de battements depuis son dernier signe."""
        self._une_page_est_venue = False
        self._sans_page = 0
        self._travaux = 0

    def signe(self, page: str) -> None:
        """La page `page` est ouverte."""
        page = page[:LONGUEUR_D_UN_NOM]
        with self._verrou:
            if page not in self._silences and len(self._silences) >= PAGES_SUIVIES:
                return
            self._silences[page] = 0
            self._une_page_est_venue = True
            self._sans_page = 0

    def adieu(self, page: str) -> None:
        """La page `page` se ferme. Les autres, s'il y en a, gardent Pastory ouvert."""
        with self._verrou:
            self._silences.pop(page[:LONGUEUR_D_UN_NOM], None)

    def commencer_un_travail(self) -> None:
        """Une demande est en cours de traitement : lecture, recherche, écriture d'un cache."""
        with self._verrou:
            self._travaux += 1

    def finir_un_travail(self) -> None:
        with self._verrou:
            self._travaux = max(0, self._travaux - 1)

    def battre(self) -> bool:
        """Un battement de plus. Rend `True` quand il faut s'arrêter.

        Pastory ne s'arrête jamais au milieu d'un travail : une fenêtre fermée pendant qu'un
        cache s'écrit le laisserait à moitié écrit.
        """
        with self._verrou:
            for page in list(self._silences):
                self._silences[page] += 1
                if self._silences[page] >= self._silence_maximal:
                    del self._silences[page]
            if self._silences:
                self._sans_page = 0
                return False
            self._sans_page += 1
            if self._travaux:
                return False
            limite = self._delai_de_fermeture if self._une_page_est_venue else self._attente
            return self._sans_page >= limite
