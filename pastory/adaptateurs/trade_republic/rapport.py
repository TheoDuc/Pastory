"""Le rapport de lecture : ce que l'adaptateur a compris, et ce qu'il n'a pas compris.

C'est la pièce qui rend la règle 5 de CLAUDE.md vérifiable : **un type d'opération inconnu
n'est jamais ignoré**, il apparaît ici. Il dit aussi ce que l'export lui-même ne dit pas : la
**période couverte**, et la **limite du brut des dividendes** (D-84).

Les lignes d'espèces n'y figurent qu'en **comptage par type**, jamais ligne à ligne
(docs/export-officiel.md §8). Le rapport s'écrit en cp1252, la console Windows par défaut, et
aucune de ses lignes ne dépasse 100 caractères.
"""

from __future__ import annotations

import textwrap
from collections import Counter
from dataclasses import dataclass, field

from pastory.adaptateurs.trade_republic.classement import Categorie, Classement
from pastory.adaptateurs.trade_republic.depot import Depot
from pastory.pivot.operation import Operation, Provenance, TypeOperation
from pastory.pivot.validation import Anomalie

LARGEUR = 96
"""Largeur des phrases enveloppées : 100 colonnes moins le retrait."""

LIMITE_DES_DIVIDENDES = (
    "Le brut d'un dividende est celui que donne Trade Republic. Pour certains pays (vérifié : "
    "Pays-Bas), la banque le donne déjà diminué de la retenue à la source étrangère, sans la "
    "montrer. Sur ces dividendes, le gain et les taxes payées sont alors un peu sous-estimés "
    "(environ 15 % du dividende néerlandais) ; le montant net reçu, lui, est exact (D-84)."
)

PERIODE_A_VERIFIER = (
    "La période est celle des opérations trouvées dans les fichiers. Si votre compte est plus "
    "ancien que le premier jour, il manque des opérations : refaites l'export en choisissant "
    "« toutes les transactions »."
)


def envelopper(texte: str, retrait: str = "  ") -> list[str]:
    return textwrap.wrap(
        texte,
        width=LARGEUR,
        initial_indent=retrait,
        subsequent_indent=retrait + "  ",
        break_on_hyphens=False,
    )


@dataclass(frozen=True)
class Signalement:
    """Quelque chose qui mérite l'attention de l'utilisateur, sans être une anomalie de calcul."""

    categorie: str
    """Nom court, pour regrouper : « non traité », « forme jamais vue »…"""
    message: str
    """Phrase en français. Elle ne cite que des codes de la banque, jamais un texte libre."""
    ou: str | None = None
    """Où retrouver la ligne : « Exportation de transactions.csv, ligne 12 »."""


@dataclass
class Rapport:
    """Ce qu'une lecture a produit, et tout ce qu'elle n'a pas su faire."""

    depot: Depot = field(default_factory=Depot)

    lignes_lues: int = 0
    par_categorie: Counter[str] = field(default_factory=Counter)
    types_inconnus: Counter[str] = field(default_factory=Counter)
    """`CATEGORY/TYPE` → nombre de lignes non traitées. Le nom reste celui de l'ancien
    adaptateur : c'est ce que l'utilisateur doit examiner avant de se fier aux chiffres."""
    motifs: dict[str, str] = field(default_factory=dict)
    """`CATEGORY/TYPE` → pourquoi ce type n'est pas traité."""
    especes_par_type: Counter[str] = field(default_factory=Counter)

    operations: list[Operation] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    signalements: list[Signalement] = field(default_factory=list)

    operations_non_produites: int = 0
    """Lignes d'un type traité dont aucune opération n'a pu être tirée : chacune est un
    **trou** dans les chiffres, compté à part pour que le moteur puisse le dire."""

    classes_par_actif: dict[str, set[str]] = field(default_factory=dict)
    """Actif → valeurs d'`asset_class` vues sur ses opérations. Le type d'un actif est une
    donnée de la banque (D-82) ; il est appliqué aux estimations à l'étape 8 quater."""

    # --- Accumulation ---------------------------------------------------------

    def compter(self, classement: Classement) -> None:
        self.lignes_lues += 1
        self.par_categorie[classement.categorie.value] += 1
        match classement.categorie:
            case Categorie.INCONNU:
                self.types_inconnus[classement.type_affiche] += 1
                if classement.motif is not None:
                    self.motifs.setdefault(classement.type_affiche, classement.motif)
            case Categorie.HORS_PERIMETRE:
                self.especes_par_type[classement.type_affiche] += 1
            case Categorie.TRAITE:
                pass

    def signaler(self, categorie: str, message: str, ou: str | None = None) -> None:
        self.signalements.append(Signalement(categorie, message, ou))

    # --- Lecture du résultat --------------------------------------------------

    @property
    def tout_est_reconnu(self) -> bool:
        return not self.types_inconnus

    @property
    def operations_incompletes(self) -> list[Operation]:
        """Opérations dont un champ attend une donnée externe (les cours, étape 4)."""
        return [operation for operation in self.operations if not operation.complete]

    @property
    def a_des_dividendes(self) -> bool:
        return any(operation.type is TypeOperation.DIVIDENDE for operation in self.operations)

    def valeurs_par_provenance(self) -> Counter[str]:
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
            # ne sait pas écrire les caractères de dessin.
            lignes.append("-" * len(texte))

        self._exports(lignes, titre)

        titre(f"Lecture de {self.lignes_lues} lignes")
        for categorie in (Categorie.TRAITE, Categorie.HORS_PERIMETRE, Categorie.INCONNU):
            lignes.append(f"  {categorie.value:<16} {self.par_categorie[categorie.value]:>5}")

        if self.types_inconnus:
            titre("ATTENTION - types non traités, à examiner avant de se fier aux chiffres")
            lignes.extend(
                envelopper(
                    "Ces lignes ne sont dans aucune liste de types traités. Elles ne sont pas "
                    "comptées, et elles peuvent faire entrer ou sortir des parts de vos actifs."
                )
            )
            for type_affiche, nombre in self.types_inconnus.most_common():
                lignes.append(f"  {type_affiche:<46} {nombre:>5}")
                motif = self.motifs.get(type_affiche)
                if motif:
                    lignes.extend(envelopper(motif, retrait="      "))
        else:
            lignes.append("")
            lignes.append("Aucun type inconnu.")

        if self.especes_par_type:
            titre("Espèces, comptées et laissées de côté (D-11)")
            for type_affiche, nombre in sorted(self.especes_par_type.items()):
                lignes.append(f"  {type_affiche:<46} {nombre:>5}")

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
            for nom in (Provenance.DONNEE, Provenance.TEXTE, Provenance.DEDUCTION):
                if provenances[nom.value]:
                    lignes.append(f"  {nom.value:<16} {provenances[nom.value]:>5}")
            lignes.extend(
                envelopper(
                    "« texte » = la nature de l'opération (plan d'épargne, ordre ponctuel), lue "
                    "dans la description. Elle est seulement affichée : aucun calcul n'en dépend."
                )
            )

        if self.a_des_dividendes:
            titre("Limite connue : le brut des dividendes")
            lignes.extend(envelopper(LIMITE_DES_DIVIDENDES))

        if self.anomalies:
            titre(f"Contrôles de cohérence en échec : {len(self.anomalies)}")
            lignes.append("  L'opération est conservée telle quelle, rien n'est corrigé.")
            for anomalie in self.anomalies:
                lignes.extend(envelopper(f"[{anomalie.regle}] {anomalie.message}"))
                lignes.append(f"      opération {anomalie.reference_source}")

        if self.signalements:
            titre(f"Signalements : {len(self.signalements)}")
            for categorie, groupe in _grouper(self.signalements):
                lignes.append(f"  {categorie} ({len(groupe)})")
                for signalement in groupe:
                    lignes.extend(envelopper(f"- {signalement.message}", retrait="    "))
                    if signalement.ou:
                        lignes.append(f"      {signalement.ou}")

        return "\n".join(lignes)

    def _exports(self, lignes: list[str], titre) -> None:
        depot = self.depot
        titre(f"Exports lus : {len(depot.fichiers)}")
        for lu in depot.fichiers:
            periode = (
                f"du {lu.premier_jour} au {lu.dernier_jour}"
                if lu.premier_jour is not None
                else "aucune date lisible"
            )
            lignes.extend(envelopper(lu.nom))
            lignes.append(f"      {lu.lignes} lignes, {periode}")
        if depot.premier_jour is not None:
            lignes.append(f"  Période couverte : du {depot.premier_jour} au {depot.dernier_jour}")
            lignes.extend(envelopper(PERIODE_A_VERIFIER))
        for trou in depot.trous():
            lignes.extend(
                envelopper(
                    f"ATTENTION - aucun fichier ne couvre la période du {trou.du} au {trou.au} : "
                    "des opérations peuvent y manquer. Déposez un export qui la couvre."
                )
            )
        if depot.doublons:
            lignes.append(
                f"  {depot.doublons} ligne(s) présente(s) dans plusieurs fichiers, "
                "comptée(s) une seule fois."
            )
        for nom, raison in depot.fichiers_ignores:
            lignes.extend(envelopper(f"Fichier ignoré : {nom} ({raison})."))


def _grouper(signalements: list[Signalement]) -> list[tuple[str, list[Signalement]]]:
    """Regroupe les signalements par catégorie, en gardant l'ordre d'apparition."""
    groupes: dict[str, list[Signalement]] = {}
    for signalement in signalements:
        groupes.setdefault(signalement.categorie, []).append(signalement)
    return list(groupes.items())
