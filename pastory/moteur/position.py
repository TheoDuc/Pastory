"""Le cœur du moteur : rejouer les opérations d'un actif, une par une.

C'est le module que le propriétaire du projet doit pouvoir relire ligne à ligne et refaire
sur papier (D-33). Chaque règle renvoie à sa définition du [glossaire](../../docs/glossaire.md)
et à la décision qui l'a arrêtée.

Ce que le moteur tient à jour pour un actif, à chaque opération :

| Type | Quantité détenue | Capital net investi | Capital fiscal (D-57) |
|---|---|---|---|
| `achat` | **+** `quantite` | **+** `montant_brut` (D-12) | **+** `montant_brut` + frais + taxes |
| `vente` | **−** `quantite` | **−** la part vendue, au prorata (D-12) | idem, au prorata |
| `dividende` | inchangée | inchangé — c'est un revenu (D-14) | inchangé |
| `distribution_capital` | inchangée | **−** `montant_brut` (D-14) | **−** `montant_brut` |
| `titres_recus` | **+** `quantite` | **+** `montant_brut`, s'il est connu (D-15) | idem |

Le **capital fiscal** est la seule colonne où frais et taxes entrent : c'est le prix de revient
au sens de l'impôt français, qui inclut les frais d'acquisition (D-13, D-57). Il ne sert qu'à
estimer l'impôt d'une vente ; aucun chiffre de performance ne le lit (D-21).

Le moteur ne lit **que** le format pivot : aucun champ Trade Republic n'apparaît ici (D-26).
Il ne calcule jamais sur `nature_source`, qui n'est qu'informative (format-pivot §2).

**Trois situations où l'arithmétique n'a plus de sens** sont traitées explicitement, jamais
en silence (D-45) : des parts entrées sans prix connu, une vente qui dépasse le stock compté,
une distribution de capital qui dépasse le capital investi.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal

from pastory import tableur
from pastory.moteur.signalement import Signalement
from pastory.pivot.operation import Operation, Poche, TypeOperation

ZERO = Decimal("0")
CENTIME = Decimal("0.01")

PAS_DU_PRIX_DE_REVIENT = Decimal("0.000001")
"""Six décimales pour le prix de revient.

C'est un **résultat d'une division**, pas un montant reçu de la banque : il faut bien
l'arrêter quelque part. Six décimales suffisent à n'importe quel prix, y compris une crypto
à plusieurs dizaines de milliers d'euros, et gardent un nombre imprimable dans un tableur.

Conséquence assumée : `prix de revient × quantité` peut s'écarter du capital investi de
quelques centièmes de centime. **C'est le capital investi qui fait foi** ; le prix de revient
est un indicateur qu'on en déduit, jamais l'inverse.
"""


def arrondi_au_centime(montant: Decimal) -> Decimal:
    """Arrondit au centime, comme le ferait une banque — et comme le ferait une main.

    Le capital net investi est arrondi après **chaque** opération plutôt qu'à la fin. Sans
    cela, une vente au prorata laisserait une traînée de décimales que personne ne peut
    refaire de tête, et le journal cesserait d'être vérifiable (D-44).
    """
    return montant.quantize(CENTIME, rounding=ROUND_HALF_UP)


# --- L'état d'une position à un instant donné ---------------------------------------


@dataclass(frozen=True)
class EtatPosition:
    """Ce qu'on détient d'un actif, et ce qu'il a coûté, après une opération."""

    quantite: Decimal = ZERO
    capital_net_investi: Decimal = Decimal("0.00")
    """Ce qui est réellement placé dans l'actif, hors frais et hors taxes (D-12)."""

    capital_fiscal: Decimal = Decimal("0.00")
    """Le même, **frais et taxes d'achat compris** : le prix de revient au sens de l'impôt
    (D-57). Rangé côté coûts, il n'entre dans aucune performance (D-21)."""

    prix_inconnu: bool = False
    """Des parts sont entrées sans prix connu : le capital investi les **sous-estime** (D-15).

    Le drapeau ne s'efface plus une fois levé : même après avoir tout vendu, les chiffres
    de cet actif ont été calculés sur une histoire incomplète."""

    stock_insuffisant: bool = False
    """Une vente a porté sur plus de parts que le moteur n'en avait comptées (D-45).

    Signe qu'il manque une entrée de titres : c'est la limite connue de D-15, des titres
    peuvent être arrivés sans aucun événement dans l'export."""

    distribution_excedentaire: bool = False
    """Une distribution de capital a dépassé le capital investi, et a été plafonnée (D-45).

    C'est aussi le signe d'une histoire trouée : ou bien une acquisition manque, ou bien la
    distribution a été mal lue. Sans ce drapeau, le journal montrerait un montant distribué
    différent du capital retiré, sans un mot d'explication."""

    @property
    def historique_incomplet(self) -> bool:
        """Vrai si les chiffres de cet actif reposent sur une histoire trouée.

        Dans les trois cas, le capital investi ne décrit plus ce qui a réellement été mis
        dans l'actif, et le prix de revient qu'on en tirerait serait faux sans le dire
        (D-45)."""
        return self.prix_inconnu or self.stock_insuffisant or self.distribution_excedentaire

    @property
    def prix_de_revient(self) -> Decimal | None:
        """PRU = capital net investi / quantité détenue (D-13). `None` s'il n'a pas de sens.

        Il vaut `None` dans deux cas :

        - **plus aucune part** : diviser par zéro ne veut rien dire ;
        - **histoire incomplète** : le capital connu ne couvre pas toutes les parts
          détenues, donc la division donnerait un prix de revient **artificiellement bas**.
          Afficher ce nombre-là serait pire que ne rien afficher : rien ne dirait qu'il est
          faux. Il redeviendra un nombre quand les cours de l'étape 4 auront complété les
          prix manquants (D-15, D-45).
        """
        if self.quantite <= ZERO or self.historique_incomplet:
            return None
        return (self.capital_net_investi / self.quantite).quantize(
            PAS_DU_PRIX_DE_REVIENT, rounding=ROUND_HALF_UP
        )

    @property
    def prix_de_revient_fiscal(self) -> Decimal | None:
        """Capital fiscal / quantité détenue (D-57). `None` dans les mêmes cas que le prix de
        revient : il n'a pas plus de sens qu'un autre sur une histoire trouée (D-45)."""
        if self.quantite <= ZERO or self.historique_incomplet:
            return None
        return (self.capital_fiscal / self.quantite).quantize(
            PAS_DU_PRIX_DE_REVIENT, rounding=ROUND_HALF_UP
        )

    @property
    def detenue(self) -> bool:
        return self.quantite > ZERO


# --- Une ligne du journal : une opération, avant et après -----------------------------


@dataclass(frozen=True)
class LigneJournal:
    """Une opération et son effet, pour que chaque chiffre se retrouve à la main (D-44).

    C'est ce qui permet de lire un actif comme un relevé bancaire : on part de l'état
    d'avant, on applique l'opération, on tombe sur l'état d'après.
    """

    operation: Operation
    avant: EtatPosition
    apres: EtatPosition

    capital_ajoute: Decimal = Decimal("0.00")
    """Ce que l'opération a ajouté au capital net investi (achat, titres reçus)."""

    capital_retire: Decimal = Decimal("0.00")
    """Ce qu'elle en a retiré (vente au prorata, distribution de capital)."""

    plus_value_brute: Decimal | None = None
    """Vente seulement : montant brut encaissé − capital retiré (glossaire §4)."""

    plus_value_nette: Decimal | None = None
    """Vente seulement : plus-value brute − frais − taxes de cette vente."""

    fiable: bool = True
    """Faux si cette ligne a été calculée sur une histoire incomplète."""

    @property
    def date(self) -> Date:
        return self.operation.date


# --- Le rejeu d'une opération ---------------------------------------------------------


def _montant_brut(operation: Operation) -> Decimal | None:
    """Le montant brut, ou `None` s'il attend encore une donnée externe (D-15)."""
    if operation.est_a_completer("montant_brut"):
        return None
    return operation.montant_brut


def appliquer(
    etat: EtatPosition,
    operation: Operation,
    signaler: Callable[[Signalement], None],
) -> LigneJournal:
    """Applique une opération à un état et renvoie la ligne de journal correspondante.

    `signaler` reçoit tout ce qui n'a pas pu être calculé normalement. La fonction ne lève
    jamais d'exception sur une donnée bancale : elle calcule ce qu'elle peut et le dit.
    """

    def signalement(categorie: str, message: str) -> None:
        signaler(
            Signalement(
                categorie=categorie,
                message=message,
                actif=operation.actif,
                poche=operation.poche,
                reference_source=operation.reference_source,
            )
        )

    match operation.type:
        case TypeOperation.ACHAT | TypeOperation.TITRES_RECUS:
            return _entree(etat, operation, signalement)
        case TypeOperation.VENTE:
            return _vente(etat, operation, signalement)
        case TypeOperation.DIVIDENDE:
            return _sans_effet(etat, operation, signalement)
        case TypeOperation.DISTRIBUTION_CAPITAL:
            return _distribution_capital(etat, operation, signalement)
        case _:  # pragma: no cover - la liste des types est fermée (D-35)
            raise ValueError(f"type d'opération non prévu par le moteur : {operation.type}")


def _entree(
    etat: EtatPosition, operation: Operation, signalement: Callable[[str, str], None]
) -> LigneJournal:
    """Achat ou titres reçus : des parts entrent, et avec elles leur montant brut.

    Un achat ajoute son **montant brut**, pas le montant payé : les frais et les taxes sont
    suivis à part (D-12, D-21). Des titres reçus sans achat ajoutent le cours du jour de
    leur apparition (D-15) — tant qu'il n'est pas connu, **les parts sont comptées mais
    leur montant ne l'est pas**, et l'actif est marqué.
    """
    if operation.quantite is None:
        signalement(
            "opération inexploitable",
            f"opération du {operation.date} sans quantité : elle ne peut pas être appliquée",
        )
        return LigneJournal(operation=operation, avant=etat, apres=etat, fiable=False)

    montant = _montant_brut(operation)
    quantite = etat.quantite + operation.quantite

    if montant is None:
        signalement(
            "prix à compléter",
            f"{tableur.nombre_lisible(operation.quantite)} part(s) entrées le "
            f"{operation.date} sans prix connu : "
            "elles sont comptées, mais leur montant n'entre dans aucun total tant que les "
            "cours ne sont pas disponibles",
        )
        apres = replace(etat, quantite=quantite, prix_inconnu=True)
        return LigneJournal(operation=operation, avant=etat, apres=apres, fiable=False)

    apres = replace(
        etat,
        quantite=quantite,
        capital_net_investi=arrondi_au_centime(etat.capital_net_investi + montant),
        # Le capital fiscal, lui, compte ce que l'achat a coûté en tout (D-57).
        capital_fiscal=arrondi_au_centime(
            etat.capital_fiscal + montant + operation.frais + operation.taxes
        ),
    )
    return LigneJournal(
        operation=operation,
        avant=etat,
        apres=apres,
        capital_ajoute=montant,
        fiable=not etat.historique_incomplet,
    )


def _vente(
    etat: EtatPosition, operation: Operation, signalement: Callable[[str, str], None]
) -> LigneJournal:
    """Vente : le capital investi est réduit **au prorata des parts vendues** (D-12).

    ```
    capital retiré = capital investi × (parts vendues / parts détenues avant)
    capital après  = capital investi − capital retiré
    ```

    Écrit dans cet ordre, et non `capital × (1 − vendues/détenues)`, pour deux raisons : la
    phrase « la moitié de mes parts part, donc la moitié de ma mise part » se refait de tête,
    et les deux morceaux retombent exactement sur le capital d'avant, sans centime perdu.

    La plus-value réalisée se lit alors directement (glossaire §4) : ce qu'on encaisse, moins
    ce que ces parts avaient coûté.
    """
    if operation.quantite is None:
        signalement(
            "opération inexploitable",
            f"vente du {operation.date} sans quantité : elle ne peut pas être appliquée",
        )
        return LigneJournal(operation=operation, avant=etat, apres=etat, fiable=False)

    stock_insuffisant = etat.stock_insuffisant
    if operation.quantite > etat.quantite:
        # Des parts sont sorties sans jamais être entrées : il manque une entrée de titres
        # dans l'export (limite connue de D-15). On vide la position plutôt que d'afficher
        # une quantité négative, et on le dit (D-45).
        signalement(
            "stock insuffisant",
            f"vente de {tableur.nombre_lisible(operation.quantite)} part(s) le "
            f"{operation.date} alors que {tableur.nombre_lisible(etat.quantite)} "
            "seulement étaient comptée(s) : des titres sont entrés sans "
            "qu'aucune opération ne l'indique. La position est vidée et ses chiffres ne "
            "sont pas fiables",
        )
        stock_insuffisant = True

    if operation.quantite >= etat.quantite:
        # Tout part : le capital de l'actif retombe à zéro, sans reliquat d'arrondi.
        capital_retire = etat.capital_net_investi
        capital_fiscal_retire = etat.capital_fiscal
        quantite_apres = ZERO
    else:
        capital_retire = arrondi_au_centime(
            etat.capital_net_investi * operation.quantite / etat.quantite
        )
        # Même règle pour le capital fiscal : le prix de revient fiscal est un prix moyen
        # pondéré, que les ventes ne changent pas (D-57).
        capital_fiscal_retire = arrondi_au_centime(
            etat.capital_fiscal * operation.quantite / etat.quantite
        )
        quantite_apres = etat.quantite - operation.quantite

    apres = replace(
        etat,
        quantite=quantite_apres,
        capital_net_investi=etat.capital_net_investi - capital_retire,
        capital_fiscal=etat.capital_fiscal - capital_fiscal_retire,
        stock_insuffisant=stock_insuffisant,
    )

    montant = _montant_brut(operation)
    if montant is None:
        signalement(
            "prix à compléter",
            f"vente du {operation.date} sans montant brut connu : sa plus-value réalisée "
            "ne peut pas être calculée",
        )
        plus_value_brute = plus_value_nette = None
    else:
        plus_value_brute = montant - capital_retire
        plus_value_nette = plus_value_brute - operation.frais - operation.taxes

    return LigneJournal(
        operation=operation,
        avant=etat,
        apres=apres,
        capital_retire=capital_retire,
        plus_value_brute=plus_value_brute,
        plus_value_nette=plus_value_nette,
        fiable=not apres.historique_incomplet,
    )


def _sans_effet(
    etat: EtatPosition, operation: Operation, signalement: Callable[[str, str], None]
) -> LigneJournal:
    """Dividende : ni les parts ni le capital investi ne bougent (D-14).

    C'est un **revenu de l'actif**, pas un apport et pas un remboursement. Le montant retenu
    est le **brut** — la retenue d'impôt part dans les coûts (D-29). L'argent versé rejoint
    ensuite les espèces, qui sont hors périmètre (D-11).
    """
    if _montant_brut(operation) is None:
        signalement(
            "prix à compléter",
            f"dividende du {operation.date} sans montant brut connu : il n'entre dans "
            "aucun total",
        )
        return LigneJournal(operation=operation, avant=etat, apres=etat, fiable=False)

    return LigneJournal(
        operation=operation, avant=etat, apres=etat, fiable=not etat.historique_incomplet
    )


def _distribution_capital(
    etat: EtatPosition, operation: Operation, signalement: Callable[[str, str], None]
) -> LigneJournal:
    """Distribution de capital : une part de la mise revient, le capital investi baisse (D-14).

    Elle ne peut pas rendre plus que ce qui a été mis : au-delà, ce n'est plus un
    remboursement mais un gain. Le capital s'arrête donc à **zéro** et l'excédent est
    signalé (D-45).
    """
    montant = _montant_brut(operation)
    if montant is None:
        signalement(
            "prix à compléter",
            f"distribution de capital du {operation.date} sans montant brut connu : elle "
            "n'entre dans aucun total",
        )
        return LigneJournal(operation=operation, avant=etat, apres=etat, fiable=False)

    capital_retire = montant
    excedentaire = etat.distribution_excedentaire
    if montant > etat.capital_net_investi:
        excedentaire = True
        signalement(
            "distribution excédentaire",
            f"distribution de {tableur.nombre_lisible(montant)} € le {operation.date} "
            "alors que le capital investi n'est que de "
            f"{tableur.nombre_lisible(etat.capital_net_investi)} € : "
            "le capital s'arrête à zéro, "
            "l'excédent n'est pas un remboursement",
        )
        capital_retire = etat.capital_net_investi

    apres = replace(
        etat,
        capital_net_investi=etat.capital_net_investi - capital_retire,
        # Un remboursement d'apport réduit aussi le prix d'acquisition fiscal, avec le même
        # plancher à zéro.
        capital_fiscal=etat.capital_fiscal - min(montant, etat.capital_fiscal),
        distribution_excedentaire=excedentaire,
    )
    return LigneJournal(
        operation=operation,
        avant=etat,
        apres=apres,
        capital_retire=capital_retire,
        fiable=not apres.historique_incomplet,
    )


# --- Une position : un actif dans une poche, et toute son histoire ---------------------


@dataclass(frozen=True)
class Position:
    """Un actif détenu dans une poche, et le journal de tout ce qui lui est arrivé.

    La clé est le couple **(actif, poche)**, jamais l'actif seul : un même ETF peut être
    détenu à la fois dans le PEA et dans le CTO, avec deux prix de revient différents et
    deux fiscalités différentes. Les confondre mélangerait deux histoires.
    """

    actif: str
    poche: Poche
    journal: tuple[LigneJournal, ...]
    nom_actif: str | None = None
    """Affichage seulement, jamais un calcul (règle 4 de CLAUDE.md)."""

    # --- L'état ---------------------------------------------------------------

    @property
    def etat(self) -> EtatPosition:
        """L'état après la dernière opération connue."""
        return self.journal[-1].apres if self.journal else EtatPosition()

    def jusqu_au(self, date: Date) -> Position:
        """La même position, telle qu'elle était à la fin de ce jour-là.

        Tous les cumuls ci-dessous s'en déduisent : il suffit de couper le journal. C'est ce
        qui permettra de tracer l'évolution jour par jour à l'étape 5.
        """
        return replace(
            self, journal=tuple(ligne for ligne in self.journal if ligne.date <= date)
        )

    # --- Les cumuls, tous lus dans le journal ---------------------------------

    def _somme(self, valeur: Callable[[LigneJournal], Decimal | None]) -> Decimal:
        return sum((valeur(ligne) or ZERO for ligne in self.journal), Decimal("0.00"))

    def _somme_si(
        self, type_operation: TypeOperation, champ: str, *, seulement_comptables: bool = True
    ) -> Decimal:
        """Somme d'un champ du pivot sur les opérations d'un type donné.

        `seulement_comptables` écarte les opérations dont le montant brut attend encore une
        donnée externe : leurs parts sont comptées, leur montant ne l'est pas (D-15).
        """
        return sum(
            (
                getattr(ligne.operation, champ) or ZERO
                for ligne in self.journal
                if ligne.operation.type is type_operation
                and (not seulement_comptables or _montant_brut(ligne.operation) is not None)
            ),
            Decimal("0.00"),
        )

    @property
    def achats_bruts(self) -> Decimal:
        """Tout ce qui a été mis dans l'actif, avant toute vente (glossaire §4)."""
        return self._somme(lambda ligne: ligne.capital_ajoute)

    @property
    def ventes_brutes(self) -> Decimal:
        return self._somme_si(TypeOperation.VENTE, "montant_brut")

    @property
    def dividendes_bruts(self) -> Decimal:
        """Dividendes **bruts** : c'est eux qui comptent dans la performance (D-29)."""
        return self._somme_si(TypeOperation.DIVIDENDE, "montant_brut")

    @property
    def dividendes_taxes(self) -> Decimal:
        """Retenues sur les dividendes. Elles vont dans les coûts, pas dans la performance.

        Comptées même quand le montant brut du dividende attend une donnée externe : une
        retenue est un montant **structuré**, réellement prélevé, qui ne dépend d'aucun
        prix. L'écarter ferait disparaître de l'argent réellement payé.
        """
        return self._somme_si(TypeOperation.DIVIDENDE, "taxes", seulement_comptables=False)

    @property
    def distributions_capital(self) -> Decimal:
        """Ce qui est réellement sorti du capital investi (plancher à zéro compris, D-45)."""
        return self._somme(
            lambda ligne: ligne.capital_retire
            if ligne.operation.type is TypeOperation.DISTRIBUTION_CAPITAL
            else ZERO
        )

    @property
    def plus_values_realisees_brutes(self) -> Decimal:
        return self._somme(lambda ligne: ligne.plus_value_brute)

    @property
    def plus_values_realisees_nettes(self) -> Decimal:
        return self._somme(lambda ligne: ligne.plus_value_nette)

    # --- Les coûts, tenus séparément de la performance (D-21) -----------------

    @property
    def frais(self) -> Decimal:
        """Frais réellement facturés sur cet actif. N'entrent dans aucune performance."""
        return self._somme(lambda ligne: ligne.operation.frais)

    @property
    def taxes(self) -> Decimal:
        """Taxes réellement prélevées sur cet actif. N'entrent dans aucune performance."""
        return self._somme(lambda ligne: ligne.operation.taxes)

    def couts_par_moment(self) -> dict[str, Decimal]:
        """Les coûts payés, rangés par moment : entrée, sortie, revenus.

        Prépare les trois niveaux de la vue « frais et taxes » (Q-21, étape 6), sans rien
        estimer : ce sont les coûts **réellement** prélevés, lus dans les données.

        **La somme de ce tableau vaut toujours `frais + taxes`**, à l'euro près. La dernière
        ligne, « autres prélèvements », ramasse tout ce que les moments nommés ne couvrent
        pas — des frais sur une distribution de capital, par exemple. Sans elle, une colonne
        de rapport ne tomberait pas sur son propre total, et c'est exactement le genre
        d'écart qui fait douter de tout le reste.
        """
        moments = {
            "frais d'achat": (TypeOperation.ACHAT, "frais"),
            "taxes d'achat": (TypeOperation.ACHAT, "taxes"),
            "frais de vente": (TypeOperation.VENTE, "frais"),
            "taxes de vente": (TypeOperation.VENTE, "taxes"),
            "taxes sur revenus": (TypeOperation.DIVIDENDE, "taxes"),
        }
        detail = {
            nom: self._somme_si(type_operation, champ, seulement_comptables=False)
            for nom, (type_operation, champ) in moments.items()
        }
        detail["autres prélèvements"] = (
            self.frais + self.taxes - sum(detail.values(), Decimal("0.00"))
        )
        return detail

    # --- Fiabilité ------------------------------------------------------------

    @property
    def historique_incomplet(self) -> bool:
        return self.etat.historique_incomplet


def construire_positions(
    operations: Iterable[Operation],
) -> tuple[list[Position], list[Signalement]]:
    """Rejoue toutes les opérations et renvoie une position par couple (actif, poche).

    **L'ordre est imposé ici**, jamais supposé : les opérations sont triées par horodatage
    exact, puis par identifiant. L'horodatage donne l'ordre réel de la journée (D-36) ;
    l'identifiant ne sert qu'à départager deux opérations rigoureusement simultanées, pour
    que deux lectures du même export donnent toujours le même journal.
    """
    signalements: list[Signalement] = []
    journaux: dict[tuple[str, Poche], list[LigneJournal]] = {}
    etats: dict[tuple[str, Poche], EtatPosition] = {}
    noms: dict[tuple[str, Poche], str | None] = {}

    for operation in _dans_l_ordre(operations):
        cle = (operation.actif, operation.poche)
        etat = etats.get(cle, EtatPosition())

        ligne = appliquer(etat, operation, signalements.append)

        journaux.setdefault(cle, []).append(ligne)
        etats[cle] = ligne.apres
        # Le nom n'est là que pour l'affichage : on garde le premier rencontré, et on le
        # remplace s'il manquait. Aucun calcul n'en dépend.
        if noms.get(cle) is None:
            noms[cle] = operation.nom_actif

    positions = [
        Position(actif=actif, poche=poche, journal=tuple(lignes), nom_actif=noms[(actif, poche)])
        for (actif, poche), lignes in journaux.items()
    ]
    positions.sort(key=lambda position: (position.poche.value, position.actif))
    return positions, signalements


def _dans_l_ordre(operations: Iterable[Operation]) -> Sequence[Operation]:
    return sorted(operations, key=lambda operation: (operation.instant_utc, operation.identifiant))
