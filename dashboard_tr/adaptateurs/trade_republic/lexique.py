"""Le dictionnaire des libellés affichés par Trade Republic (D-09, D-19).

**Tout ce que le projet sait lire dans un texte est écrit ici, et nulle part ailleurs.**
Ailleurs, le code parle de notions (`Notion.QUANTITE`), jamais de mots allemands.

Trois raisons à ce module :

1. Les textes sont **dans la langue de l'application**, et un même export mélange
   l'allemand et le français.
2. **Un libellé seul ne suffit pas.** `Aktien` désigne un nombre de parts sous « Übersicht »
   et un montant en euros sous « Transaktion » : la clé est donc un couple
   (section, libellé).
3. Chaque libellé numérique déclare **comment son nombre est écrit** (`Convention`). C'est
   ce qui empêche de lire `1.234567` comme 1 234 567 (voir `nombres.py`).

Un libellé absent de ce module n'est **jamais ignoré** : il part au rapport de lecture
(règle 5 de CLAUDE.md).

> **Les libellés français ne sont pas observés.** Les deux exports disponibles sont en
> allemand, à l'exception de quelques écrans. Les entrées françaises sont donc déduites de
> l'interface française et signalées comme telles. Le risque est faible : un libellé mal
> deviné n'est pas reconnu, donc il apparaît au rapport au lieu de produire un chiffre faux.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto

from dashboard_tr.adaptateurs.trade_republic.nombres import Convention

VIRGULE = Convention.VIRGULE_DECIMALE
POINT = Convention.POINT_DECIMAL


class Section(StrEnum):
    """Sections utiles d'un écran de détail, indépendamment de la langue."""

    APERCU = auto()
    """« Übersicht » : nature, actif, poche, frais, total."""

    AFFAIRE = auto()
    """« Geschäft » : le détail d'un dividende ou d'une distribution."""

    TRANSACTION = auto()
    """« Transaktion » d'une action gagnée : ce qui a été reçu, en euros."""

    DETAIL_TRANSACTION = auto()
    """Page ouverte par la ligne « Transaktion » d'un achat : quantité, prix, montant brut."""

    SANS_INFORMATION = auto()
    """Documents, performance calculée par Trade Republic, aide : rien à lire."""


class Notion(StrEnum):
    """Ce qu'une ligne apporte, une fois le libellé traduit."""

    QUANTITE = auto()
    PRIX_UNITAIRE = auto()
    MONTANT_BRUT = auto()
    """Quantité × prix, lu directement dans la page de détail d'un achat ou d'une vente."""
    MONTANT_REGLE = auto()
    """Ce qui a réellement été débité ou crédité. Recoupe le champ structuré `amount`."""
    MONTANT_NET_RECU = auto()
    """« Gesamt » d'un dividende : le **net**, après retenue."""
    PRODUIT_BRUT = auto()
    """« Bruttoertrag » d'une distribution de capital."""
    DIVIDENDE_PAR_ACTION = auto()
    FRAIS = auto()
    TAXES = auto()
    VALEUR_DES_TITRES = auto()
    """Valeur en euros des titres reçus, sur une action gagnée."""
    CREDIT_ESPECES = auto()
    """Part en espèces d'une action gagnée : **hors périmètre** (D-11), lue pour mémoire."""
    RESUME_TRANSACTION = auto()
    """Le texte « quantité × prix » ; le détail chiffré est dans la page qu'il ouvre."""
    NOM_ACTIF = auto()
    """Affichage seulement, jamais un calcul (règle 4 de CLAUDE.md)."""
    POCHE = auto()
    NATURE = auto()
    STATUT = auto()
    MOYEN_PAIEMENT = auto()
    PLACE_COTATION = auto()


@dataclass(frozen=True)
class Entree:
    """Ce que le lexique sait d'un libellé."""

    notion: Notion
    convention: Convention | None = None
    """Écriture attendue du nombre, ou `None` si la valeur n'est pas un nombre."""


# --- Sections -----------------------------------------------------------------------

SECTIONS: dict[str, Section] = {
    # Allemand, observé
    "Übersicht": Section.APERCU,
    "Geschäft": Section.AFFAIRE,
    "Transaktion": Section.TRANSACTION,
    "Transaktion ⤷ détail": Section.DETAIL_TRANSACTION,
    "Dokumente": Section.SANS_INFORMATION,
    "Performance": Section.SANS_INFORMATION,
    "Mehr": Section.SANS_INFORMATION,
    "Sparplan": Section.SANS_INFORMATION,
    "Ausführung": Section.SANS_INFORMATION,
    "Vorteile": Section.SANS_INFORMATION,
    # Français, déduit
    "Aperçu": Section.APERCU,
    "Synthèse": Section.APERCU,
    "Opération": Section.AFFAIRE,
    "Transaction": Section.TRANSACTION,
    "Transaction ⤷ détail": Section.DETAIL_TRANSACTION,
    "Documents": Section.SANS_INFORMATION,
    "Plus": Section.SANS_INFORMATION,
    "Exécution": Section.SANS_INFORMATION,
    "Avantages": Section.SANS_INFORMATION,
}


# --- Libellés -----------------------------------------------------------------------

LIBELLES: dict[tuple[Section, str], Entree] = {
    # --- Section « Übersicht » : achats, ventes, plans d'épargne ---
    (Section.APERCU, "Transaktion"): Entree(Notion.RESUME_TRANSACTION),
    (Section.APERCU, "Transaction"): Entree(Notion.RESUME_TRANSACTION),
    (Section.APERCU, "Gebühr"): Entree(Notion.FRAIS, VIRGULE),
    (Section.APERCU, "Frais"): Entree(Notion.FRAIS, VIRGULE),
    (Section.APERCU, "Steuer"): Entree(Notion.TAXES, VIRGULE),
    (Section.APERCU, "Taxe"): Entree(Notion.TAXES, VIRGULE),
    (Section.APERCU, "Impôt"): Entree(Notion.TAXES, VIRGULE),
    (Section.APERCU, "Summe"): Entree(Notion.MONTANT_REGLE, VIRGULE),
    (Section.APERCU, "Total"): Entree(Notion.MONTANT_REGLE, VIRGULE),
    (Section.APERCU, "Portfolio"): Entree(Notion.POCHE),
    (Section.APERCU, "Portefeuille"): Entree(Notion.POCHE),
    (Section.APERCU, "Konto"): Entree(Notion.POCHE),
    (Section.APERCU, "Compte"): Entree(Notion.POCHE),
    (Section.APERCU, "Asset"): Entree(Notion.NOM_ACTIF),
    (Section.APERCU, "Wertpapier"): Entree(Notion.NOM_ACTIF),
    (Section.APERCU, "Titre"): Entree(Notion.NOM_ACTIF),
    (Section.APERCU, "Actif"): Entree(Notion.NOM_ACTIF),
    (Section.APERCU, "Zahlung"): Entree(Notion.MOYEN_PAIEMENT),
    (Section.APERCU, "Paiement"): Entree(Notion.MOYEN_PAIEMENT),
    (Section.APERCU, "Börse"): Entree(Notion.PLACE_COTATION),
    (Section.APERCU, "Bourse"): Entree(Notion.PLACE_COTATION),
    (Section.APERCU, "Status"): Entree(Notion.STATUT),
    (Section.APERCU, "Statut"): Entree(Notion.STATUT),
    (Section.APERCU, "Event"): Entree(Notion.NATURE),
    (Section.APERCU, "Événement"): Entree(Notion.NATURE),
    (Section.APERCU, "Orderart"): Entree(Notion.NATURE),
    (Section.APERCU, "Type d'ordre"): Entree(Notion.NATURE),
    # --- Section « Übersicht » : titres reçus sans achat ---
    # La quantité y est écrite avec un **point décimal**, contrairement à celle d'un achat.
    (Section.APERCU, "Aktien"): Entree(Notion.QUANTITE, POINT),
    (Section.APERCU, "Aktien hinzugefügt"): Entree(Notion.QUANTITE, POINT),
    (Section.APERCU, "Actions"): Entree(Notion.QUANTITE, POINT),
    (Section.APERCU, "Actions ajoutées"): Entree(Notion.QUANTITE, POINT),
    (Section.APERCU, "Aktienkurs"): Entree(Notion.PRIX_UNITAIRE, VIRGULE),
    (Section.APERCU, "Cours de l'action"): Entree(Notion.PRIX_UNITAIRE, VIRGULE),
    # --- Page de détail d'un achat ou d'une vente ---
    # Ici la quantité est écrite avec une **virgule décimale**. Même notion, autre écriture :
    # c'est tout l'intérêt d'une clé (section, libellé).
    (Section.DETAIL_TRANSACTION, "Aktien"): Entree(Notion.QUANTITE, VIRGULE),
    (Section.DETAIL_TRANSACTION, "Actions"): Entree(Notion.QUANTITE, VIRGULE),
    (Section.DETAIL_TRANSACTION, "Aktienkurs"): Entree(Notion.PRIX_UNITAIRE, VIRGULE),
    (Section.DETAIL_TRANSACTION, "Cours de l'action"): Entree(Notion.PRIX_UNITAIRE, VIRGULE),
    (Section.DETAIL_TRANSACTION, "Summe"): Entree(Notion.MONTANT_BRUT, VIRGULE),
    (Section.DETAIL_TRANSACTION, "Total"): Entree(Notion.MONTANT_BRUT, VIRGULE),
    # --- Section « Geschäft » : dividendes et distributions ---
    (Section.AFFAIRE, "Aktien"): Entree(Notion.QUANTITE, POINT),
    (Section.AFFAIRE, "Actions"): Entree(Notion.QUANTITE, POINT),
    (Section.AFFAIRE, "Dividende pro Aktie"): Entree(Notion.DIVIDENDE_PAR_ACTION, VIRGULE),
    (Section.AFFAIRE, "Dividende par action"): Entree(Notion.DIVIDENDE_PAR_ACTION, VIRGULE),
    (Section.AFFAIRE, "Bruttoertrag"): Entree(Notion.PRODUIT_BRUT, VIRGULE),
    (Section.AFFAIRE, "Produit brut"): Entree(Notion.PRODUIT_BRUT, VIRGULE),
    (Section.AFFAIRE, "Steuer"): Entree(Notion.TAXES, VIRGULE),
    (Section.AFFAIRE, "Taxe"): Entree(Notion.TAXES, VIRGULE),
    (Section.AFFAIRE, "Impôt"): Entree(Notion.TAXES, VIRGULE),
    (Section.AFFAIRE, "Gesamt"): Entree(Notion.MONTANT_NET_RECU, VIRGULE),
    (Section.AFFAIRE, "Total"): Entree(Notion.MONTANT_NET_RECU, VIRGULE),
    # --- Section « Transaktion » d'une action gagnée : des euros, pas des parts ---
    (Section.TRANSACTION, "Aktien"): Entree(Notion.VALEUR_DES_TITRES, VIRGULE),
    (Section.TRANSACTION, "Actions"): Entree(Notion.VALEUR_DES_TITRES, VIRGULE),
    (Section.TRANSACTION, "Cash-Gutschrift"): Entree(Notion.CREDIT_ESPECES, VIRGULE),
    (Section.TRANSACTION, "Crédit en espèces"): Entree(Notion.CREDIT_ESPECES, VIRGULE),
    (Section.TRANSACTION, "Summe"): Entree(Notion.MONTANT_REGLE, VIRGULE),
    (Section.TRANSACTION, "Total"): Entree(Notion.MONTANT_REGLE, VIRGULE),
}


# --- Valeurs qui sont des mots ------------------------------------------------------

MOTS_SANS_FRAIS = frozenset({"Kostenlos", "Gratuit", "Sans frais", "Kostenfrei"})
"""« Gebühr » vaut un **mot** sur tous les plans d'épargne observés. Un mot inconnu à cette
place n'est pas traité comme zéro : c'est une anomalie (constat 8 de l'inventaire)."""

STATUTS_EXECUTE = frozenset({"Ausgeführt", "Exécuté", "Executed"})
"""Statut affiché d'une opération réalisée. Il recoupe le champ structuré `status`."""

POCHES_AFFICHEES: dict[str, str] = {
    "PEA": "PEA",
    "Brokerage": "CTO",
    "Courtage": "CTO",
}
"""Libellé « Portfolio » → poche. Sert de **contrôle** du compte, jamais de source (D-10)."""


class NatureSource(StrEnum):
    """Nature d'origine d'une opération (`nature_source` du pivot). Informative."""

    PLAN_EPARGNE = "plan_epargne"
    ORDRE_PONCTUEL = "ordre_ponctuel"
    ACTION_GAGNEE = "action_gagnee"
    ACTIONS_GRATUITES = "actions_gratuites"
    TRANSFERT_ENTRANT = "transfert_entrant"
    DIVIDENDE_ESPECES = "dividende_especes"
    DISTRIBUTION_CAPITAL = "distribution_capital"


NATURES_EN_TITRE: dict[str, NatureSource] = {
    # Trade Republic range la nature **dans le titre** de la première ligne : la ligne
    # s'appelle « Kauf » et sa valeur est le statut. Le libellé est donc la donnée.
    "Sparplan": NatureSource.PLAN_EPARGNE,
    "Plan d'épargne": NatureSource.PLAN_EPARGNE,
    "Kauf": NatureSource.ORDRE_PONCTUEL,
    "Achat": NatureSource.ORDRE_PONCTUEL,
    "Verkaufen": NatureSource.ORDRE_PONCTUEL,
    "Verkauf": NatureSource.ORDRE_PONCTUEL,
    "Vente": NatureSource.ORDRE_PONCTUEL,
    "Stop Order": NatureSource.ORDRE_PONCTUEL,
    "Limit Order": NatureSource.ORDRE_PONCTUEL,
    "Ordre stop": NatureSource.ORDRE_PONCTUEL,
    "Ordre limite": NatureSource.ORDRE_PONCTUEL,
}

SENS_EN_TITRE: dict[str, str] = {
    "Kauf": "achat",
    "Achat": "achat",
    "Verkaufen": "vente",
    "Verkauf": "vente",
    "Vente": "vente",
}
"""Sens annoncé par le titre, quand il le dit. Il **recoupe** le signe du montant, qui reste
la source (constat 7 de l'inventaire). « Stop Order » ne dit pas le sens : il est absent."""

NATURES_EN_VALEUR: dict[str, NatureSource] = {
    "Bardividende": NatureSource.DIVIDENDE_ESPECES,
    "Dividende en espèces": NatureSource.DIVIDENDE_ESPECES,
    "Kapitalverteilung": NatureSource.DISTRIBUTION_CAPITAL,
    "Distribution de capital": NatureSource.DISTRIBUTION_CAPITAL,
    "Répartition du capital": NatureSource.DISTRIBUTION_CAPITAL,
    "Bonusaktien": NatureSource.ACTIONS_GRATUITES,
    "Actions bonus": NatureSource.ACTIONS_GRATUITES,
    "Actions gratuites": NatureSource.ACTIONS_GRATUITES,
}
"""Valeur des lignes « Event » et « Orderart ». C'est elle qui distingue une distribution de
capital d'un autre versement non-dividende (Q-07) : rien n'est supposé sans ce mot."""


# --- Interrogation ------------------------------------------------------------------


def section_connue(titre_section: str | None) -> Section | None:
    """Section canonique correspondant à un titre affiché, ou `None` si inconnue.

    Le titre d'une section peut contenir un montant réel (bandeau « Du hast … gespart ») :
    il n'est jamais recopié dans un message sans passer par `rapport.sur()`.
    """
    if titre_section is None:
        return None
    return SECTIONS.get(titre_section.strip())


def entree(section: Section, libelle: str) -> Entree | None:
    """Ce que le lexique sait de ce libellé dans cette section, ou `None`."""
    return LIBELLES.get((section, libelle.strip()))


def _conventions_par_notion() -> dict[tuple[Section, Notion], Convention]:
    """Écriture attendue pour chaque notion numérique, section par section.

    Construit à partir de `LIBELLES`, et **vérifié au chargement** : deux libellés qui
    désignent la même notion au même endroit doivent annoncer la même écriture. Sans ce
    contrôle, ajouter un synonyme avec la mauvaise convention passerait inaperçu et
    donnerait des quantités fausses (voir `nombres.py`).
    """
    conventions: dict[tuple[Section, Notion], Convention] = {}
    for (section, libelle), valeur in LIBELLES.items():
        if valeur.convention is None:
            continue
        cle = (section, valeur.notion)
        deja = conventions.get(cle)
        if deja is not None and deja is not valeur.convention:
            raise ValueError(
                f"lexique incohérent : « {libelle} » annonce l'écriture {valeur.convention} "
                f"pour {valeur.notion} dans {section}, alors qu'un autre libellé de la même "
                f"section annonce {deja}"
            )
        conventions[cle] = valeur.convention
    return conventions


CONVENTIONS: dict[tuple[Section, Notion], Convention] = _conventions_par_notion()


def convention(section: Section, notion: Notion) -> Convention | None:
    """Comment est écrit le nombre de cette notion, à cet endroit de l'écran."""
    return CONVENTIONS.get((section, notion))
