"""Le dossier de dépôt : l'utilisateur y dépose ses exports, Pastory lit tout ce qui s'y trouve.

C'est la seule chose que l'utilisateur ait à faire (D-80). D'où trois règles :

- **plusieurs fichiers se cumulent.** Un export récent ne remplace pas un ancien : ils peuvent
  couvrir des périodes différentes. Une opération présente dans deux fichiers qui se
  recouvrent n'est comptée qu'une fois, grâce à son `transaction_id` ;
- **un fichier qui n'est pas un export n'arrête rien** : il est cité, avec la raison, et le
  reste est lu ;
- **la période couverte est toujours dite.** L'utilisateur choisit les dates de son export :
  une période qui ne commence pas à l'ouverture du compte donne une histoire incomplète, et
  rien dans le fichier ne le dit (D-45). Un trou entre deux fichiers est signalé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from pastory.adaptateurs.trade_republic_officiel import fichier
from pastory.adaptateurs.trade_republic_officiel.fichier import FichierNonReconnu, Ligne

NOM_PAR_DEFAUT = "Exportation de transactions.csv"
"""Le nom que donne l'application en français. Tout fichier `.csv` du dossier est lu."""

CHEMIN_DANS_L_APPLICATION = "Profil > Relevés > Export des transactions"
"""Où trouver l'export dans l'application Trade Republic (export-officiel.md §1)."""


class ExportIntrouvable(Exception):
    """Aucun export lisible dans le dossier. Le message dit comment en obtenir un."""


@dataclass(frozen=True)
class FichierLu:
    """Un export lu, et la période qu'il couvre."""

    nom: str
    lignes: int
    premier_jour: date | None
    dernier_jour: date | None


@dataclass(frozen=True)
class Trou:
    """Des jours qu'aucun fichier ne couvre, entre deux fichiers."""

    du: date
    au: date


@dataclass
class Depot:
    """Ce que contient le dossier : les lignes dédoublonnées, et tout ce qu'il faut en dire."""

    lignes: list[Ligne] = field(default_factory=list)
    fichiers: list[FichierLu] = field(default_factory=list)
    fichiers_ignores: list[tuple[str, str]] = field(default_factory=list)
    """(nom du fichier, raison) pour chaque fichier `.csv` qui n'est pas un export."""
    doublons: int = 0
    """Lignes présentes dans plusieurs fichiers, à l'identique : comptées une fois."""
    conflits: list[tuple[Ligne, Ligne]] = field(default_factory=list)
    """(ligne gardée, ligne écartée) : même `transaction_id`, contenu différent."""
    sans_identifiant: list[Ligne] = field(default_factory=list)
    """Lignes sans `transaction_id` : impossibles à dédoublonner, donc non lues."""

    @property
    def premier_jour(self) -> date | None:
        jours = [lu.premier_jour for lu in self.fichiers if lu.premier_jour is not None]
        return min(jours) if jours else None

    @property
    def dernier_jour(self) -> date | None:
        jours = [lu.dernier_jour for lu in self.fichiers if lu.dernier_jour is not None]
        return max(jours) if jours else None

    def trous(self) -> list[Trou]:
        """Les jours entre deux fichiers qui ne se touchent pas.

        Un trou n'est pas forcément une opération perdue — il peut ne rien s'être passé ces
        jours-là — mais rien ne permet de le savoir : il est donc dit, jamais comblé.
        """
        periodes = sorted(
            (lu.premier_jour, lu.dernier_jour)
            for lu in self.fichiers
            if lu.premier_jour is not None and lu.dernier_jour is not None
        )
        trous: list[Trou] = []
        if not periodes:
            return trous
        couvert_jusqu_au = periodes[0][1]
        for debut, fin in periodes[1:]:
            if debut > couvert_jusqu_au + timedelta(days=1):
                trous.append(Trou(couvert_jusqu_au + timedelta(days=1), debut - timedelta(days=1)))
            couvert_jusqu_au = max(couvert_jusqu_au, fin)
        return trous


def _jour(texte: str) -> date | None:
    try:
        return date.fromisoformat(texte)
    except ValueError:
        return None


def _decrire(nom: str, lignes: list[Ligne]) -> FichierLu:
    jours = [jour for jour in (_jour(ligne.date) for ligne in lignes) if jour is not None]
    return FichierLu(
        nom=nom,
        lignes=len(lignes),
        premier_jour=min(jours) if jours else None,
        dernier_jour=max(jours) if jours else None,
    )


def comment_obtenir_l_export(dossier: Path) -> str:
    """Le message d'un dossier sans export : quoi faire, et où le déposer."""
    return (
        f"Aucun export des transactions dans {dossier}.\n"
        f"Dans l'application Trade Republic : {CHEMIN_DANS_L_APPLICATION},\n"
        "choisissez « toutes les transactions », puis déposez le fichier obtenu\n"
        f"(« {NOM_PAR_DEFAUT} ») dans ce dossier."
    )


def lire_dossier(dossier: Path) -> Depot:
    """Lit tous les exports d'un dossier, dans l'ordre alphabétique de leurs noms."""
    if not dossier.is_dir():
        raise ExportIntrouvable(comment_obtenir_l_export(dossier))
    candidats = sorted(
        (chemin for chemin in dossier.iterdir() if chemin.suffix.lower() == ".csv"),
        key=lambda chemin: chemin.name,
    )

    depot = Depot()
    par_identifiant: dict[str, Ligne] = {}
    for chemin in candidats:
        try:
            lignes = fichier.lire(chemin)
        except FichierNonReconnu as raison:
            depot.fichiers_ignores.append((chemin.name, str(raison)))
            continue
        depot.fichiers.append(_decrire(chemin.name, lignes))
        for ligne in lignes:
            if not ligne.transaction_id:
                depot.sans_identifiant.append(ligne)
                continue
            deja = par_identifiant.get(ligne.transaction_id)
            if deja is None:
                par_identifiant[ligne.transaction_id] = ligne
                depot.lignes.append(ligne)
            elif deja.contenu() == ligne.contenu():
                depot.doublons += 1
            else:
                # Deux versions d'une même opération : la première lue est gardée, et le
                # désaccord est affiché. Rien ne permet de dire laquelle est la bonne.
                depot.conflits.append((deja, ligne))

    if not depot.fichiers:
        message = comment_obtenir_l_export(dossier)
        if depot.fichiers_ignores:
            ignores = "\n".join(f"  {nom} : {raison}" for nom, raison in depot.fichiers_ignores)
            message += f"\n\nFichiers trouvés, mais qui ne sont pas un export :\n{ignores}"
        raise ExportIntrouvable(message)
    return depot
