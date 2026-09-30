"""Le rapport de lecture : ce que l'adaptateur a compris, et ce qu'il n'a pas compris.

C'est la pièce qui rend la règle 5 de CLAUDE.md vérifiable : **un type d'événement inconnu
n'est jamais ignoré**, il apparaît ici. Le rapport sert à trois moments :

- après un `pastory lire`, pour vérifier qu'aucun type n'est inconnu ;
- dans l'interface (étape 9), en affichage permanent ;
- au moment de comparer avec l'application Trade Republic, pour savoir quelles valeurs
  viennent d'un texte et sont donc fragiles.

**Aucune valeur de l'utilisateur n'est écrite telle quelle** : tout texte venu de l'écran
passe par `sur()`. Le titre d'une section, par exemple, contient parfois un montant réel.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from pastory.adaptateurs.trade_republic.classement import Categorie
from pastory.pivot.operation import Operation, Provenance
from pastory.pivot.validation import Anomalie

LONGUEUR_MAXIMALE_AFFICHABLE = 60


def sur(texte: object) -> str:
    """Rend un texte venu de l'écran affichable sans risque de divulguer une valeur.

    Tout ce qui contient un chiffre ou une arobase est masqué : montants, quantités, IBAN,
    numéros de compte, adresses. Un texte long l'est aussi, parce qu'il peut être une phrase
    contenant un nom.

    C'est le même garde-fou que `scripts/inventaire_structure.py`, et pour la même raison :
    le rapport peut être collé dans une issue GitHub ou envoyé pour de l'aide.
    """
    if texte is None:
        return "(vide)"
    if not isinstance(texte, str):
        return f"({type(texte).__name__})"
    if re.search(r"[\d@]", texte) or len(texte) > LONGUEUR_MAXIMALE_AFFICHABLE:
        return "«masqué»"
    return texte


@dataclass(frozen=True)
class Signalement:
    """Quelque chose qui mérite l'attention de l'utilisateur, sans être une anomalie de calcul."""

    categorie: str
    """Nom court, pour regrouper : « type inconnu », « libellé non reconnu »…"""
    message: str
    """Phrase en français, déjà passée par `sur()` si elle cite un texte de l'écran."""
    reference_source: str | None = None
    """Identifiant de l'événement d'origine, pour le retrouver dans l'export."""


@dataclass
class Rapport:
    """Ce qu'une lecture a produit, et tout ce qu'elle n'a pas su faire."""

    evenements_lus: int = 0
    par_categorie: Counter[str] = field(default_factory=Counter)
    types_inconnus: Counter[str] = field(default_factory=Counter)
    types_hors_perimetre: Counter[str] = field(default_factory=Counter)
    types_ecartes: Counter[str] = field(default_factory=Counter)

    operations: list[Operation] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    signalements: list[Signalement] = field(default_factory=list)

    operations_non_produites: int = 0
    """Événements traités dont aucune opération n'a pu être tirée.

    Chacun a son signalement, mais le compte est gardé à part : c'est un **trou** dans les
    chiffres, et le moteur doit pouvoir prévenir que ses totaux sont incomplets sans avoir
    à relire les signalements un à un."""

    comptes_a_nommer: set[str] = field(default_factory=set)
    actifs_sans_poche: set[str] = field(default_factory=set)

    # --- Accumulation ---------------------------------------------------------

    def compter(self, categorie: Categorie, type_affiche: str) -> None:
        self.par_categorie[categorie.value] += 1
        match categorie:
            case Categorie.INCONNU:
                self.types_inconnus[type_affiche] += 1
            case Categorie.HORS_PERIMETRE:
                self.types_hors_perimetre[type_affiche] += 1
            case Categorie.ECARTE:
                self.types_ecartes[type_affiche] += 1
            case Categorie.TRAITE:
                pass

    def signaler(self, categorie: str, message: str, reference_source: str | None = None) -> None:
        self.signalements.append(Signalement(categorie, message, reference_source))

    # --- Lecture du résultat --------------------------------------------------

    @property
    def tout_est_reconnu(self) -> bool:
        """Vrai si aucun événement n'est resté inconnu. C'est le contrôle de l'étape 2."""
        return not self.types_inconnus

    @property
    def operations_incompletes(self) -> list[Operation]:
        """Opérations dont un champ attend une donnée externe (les cours, étape 4)."""
        return [operation for operation in self.operations if not operation.complete]

    @property
    def declarations_attendues(self) -> bool:
        """Vrai s'il manque quelque chose que seul l'utilisateur peut dire (D-40)."""
        return bool(self.comptes_a_nommer or self.actifs_sans_poche)

    def valeurs_par_provenance(self) -> Counter[str]:
        """Combien de valeurs viennent d'un champ structuré, d'un texte, d'une déduction.

        C'est la mesure de fragilité de la lecture : plus il y a de `texte`, plus les
        chiffres dépendent de la langue de l'application (D-09).
        """
        compte: Counter[str] = Counter()
        for operation in self.operations:
            for provenance in operation.provenance.values():
                compte[provenance.value] += 1
        return compte

    def par_type_d_operation(self) -> Counter[str]:
        return Counter(operation.type.value for operation in self.operations)

    def par_poche(self) -> Counter[str]:
        return Counter(operation.poche.value for operation in self.operations)

    # --- Affichage ------------------------------------------------------------

    def resume(self) -> str:
        """Le rapport tel qu'il s'affiche dans le terminal, en français."""
        lignes: list[str] = []

        def titre(texte: str) -> None:
            lignes.append("")
            lignes.append(texte)
            # Tiret ordinaire, et non un trait de tableau : la console Windows par défaut
            # ne sait pas écrire les caractères de dessin, et le rapport doit s'afficher
            # partout plutôt que d'être joli quelque part.
            lignes.append("-" * len(texte))

        titre(f"Lecture de {self.evenements_lus} événements")
        for categorie in (
            Categorie.TRAITE,
            Categorie.HORS_PERIMETRE,
            Categorie.ECARTE,
            Categorie.INCONNU,
        ):
            lignes.append(f"  {categorie.value:<16} {self.par_categorie[categorie.value]:>5}")

        if self.types_inconnus:
            titre("ATTENTION - types inconnus, à examiner avant de se fier aux chiffres")
            lignes.append("  Ces événements ne sont dans aucune liste. Ils ne sont pas comptés,")
            lignes.append("  et ils peuvent contenir des opérations sur vos actifs.")
            for type_evenement, nombre in self.types_inconnus.most_common():
                lignes.append(f"  {type_evenement:<46} {nombre:>5}")
        else:
            lignes.append("")
            lignes.append("Aucun type inconnu.")

        titre(f"Opérations produites : {len(self.operations)}")
        for nom, nombre in sorted(self.par_type_d_operation().items()):
            lignes.append(f"  {nom:<24} {nombre:>5}")
        if self.operations:
            lignes.append("  par poche :")
            for nom, nombre in sorted(self.par_poche().items()):
                lignes.append(f"    {nom:<22} {nombre:>5}")

        provenances = self.valeurs_par_provenance()
        if provenances:
            titre("D'où viennent les valeurs")
            for nom in (
                Provenance.DONNEE,
                Provenance.TEXTE,
                Provenance.DEDUCTION,
                Provenance.A_COMPLETER,
            ):
                if provenances[nom.value]:
                    lignes.append(f"  {nom.value:<16} {provenances[nom.value]:>5}")
            if provenances[Provenance.TEXTE.value]:
                lignes.append(
                    "  « texte » = lu dans un libellé affiché : dépend de la langue de"
                    " l'application."
                )

        incompletes = self.operations_incompletes
        if incompletes:
            titre(f"Opérations incomplètes : {len(incompletes)}")
            lignes.append("  Des titres sont entrés sans prix connu. Ils sont visibles, mais")
            lignes.append("  leur montant ne compte dans aucun total tant que les cours de")
            lignes.append("  l'étape 4 ne sont pas disponibles (D-15).")
            for operation in incompletes:
                lignes.append(
                    f"  {operation.date}  {operation.actif}  quantité {operation.quantite}"
                )

        if self.anomalies:
            titre(f"Contrôles de cohérence en échec : {len(self.anomalies)}")
            lignes.append("  L'opération est conservée telle quelle, rien n'est corrigé.")
            for anomalie in self.anomalies:
                lignes.append(f"  [{anomalie.regle}] {anomalie.message}")
                lignes.append(f"      événement {anomalie.reference_source}")

        if self.signalements:
            titre(f"Signalements : {len(self.signalements)}")
            for categorie, groupe in _grouper(self.signalements):
                lignes.append(f"  {categorie} ({len(groupe)})")
                for signalement in groupe:
                    lignes.append(f"    - {signalement.message}")
                    if signalement.reference_source:
                        lignes.append(f"      événement {signalement.reference_source}")

        if self.declarations_attendues:
            titre("ATTENTION - il manque des informations que vous seul pouvez donner")
            if self.comptes_a_nommer:
                lignes.append(
                    f"  {len(self.comptes_a_nommer)} compte(s) espèces sans rôle : "
                    "lancez « pastory comptes »."
                )
            if self.actifs_sans_poche:
                lignes.append("  Actifs dont la poche est indéterminable, à déclarer")
                lignes.append("  dans la section [poches] de votre configuration :")
                for actif in sorted(self.actifs_sans_poche):
                    lignes.append(f"    {actif}")

        return "\n".join(lignes)


def _grouper(signalements: list[Signalement]) -> list[tuple[str, list[Signalement]]]:
    """Regroupe les signalements par catégorie, en gardant l'ordre d'apparition."""
    groupes: dict[str, list[Signalement]] = {}
    for signalement in signalements:
        groupes.setdefault(signalement.categorie, []).append(signalement)
    return list(groupes.items())
