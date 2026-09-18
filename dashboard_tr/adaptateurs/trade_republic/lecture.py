"""Des événements Trade Republic aux opérations du format pivot.

C'est le cœur de l'adaptateur. Il ne produit **que** des lignes du format pivot : le moteur
ne saura jamais qu'elles viennent de Trade Republic (D-26).

Trois principes, qui expliquent la forme du code :

- **rien n'est deviné.** Un libellé non reconnu, une nature inconnue, une poche
  indéterminable : l'opération n'est pas produite au petit bonheur, elle est signalée ;
- **chaque valeur dit d'où elle vient.** Un champ structuré est `donnee`, un libellé lu à
  l'écran est `texte`, une règle écrite est `deduction` (D-09) ;
- **les champs structurés priment.** Le sens d'un ordre vient du signe du montant, pas du
  mot « Kauf » ; le libellé sert à recouper, et un désaccord part au rapport.

Les correspondances exactes entre libellés et notions sont dans `lexique.py`, les écritures
des nombres dans `nombres.py`, et le classement des types dans `classement.py`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from dashboard_tr.adaptateurs.trade_republic import evenements, lexique
from dashboard_tr.adaptateurs.trade_republic import poche as module_poche
from dashboard_tr.adaptateurs.trade_republic.classement import Categorie, Famille, classer
from dashboard_tr.adaptateurs.trade_republic.lexique import NatureSource, Notion, Section
from dashboard_tr.adaptateurs.trade_republic.nombres import (
    LectureImpossible,
    NombreLu,
    lire_nombre,
)
from dashboard_tr.adaptateurs.trade_republic.rapport import Rapport, sur
from dashboard_tr.config.comptes import Configuration
from dashboard_tr.pivot.operation import (
    DEVISE_UNIQUE,
    Operation,
    Provenance,
    TypeOperation,
    jour_a_paris,
)
from dashboard_tr.pivot.validation import controler

ZERO = Decimal("0")


@dataclass(frozen=True)
class ValeurLue:
    """Un nombre lu, et l'origine à inscrire dans la provenance de l'opération."""

    nombre: NombreLu
    provenance: Provenance

    @property
    def valeur(self) -> Decimal:
        return self.nombre.valeur


class OperationNonProduite(Exception):
    """L'opération ne peut pas être construite sans inventer quelque chose.

    Le message explique quoi, en français : il part tel quel au rapport de lecture.
    """

    def __init__(self, categorie: str, message: str) -> None:
        self.categorie = categorie
        super().__init__(message)


class Lecteur:
    """Lit un export complet et produit le rapport de lecture."""

    def __init__(self, configuration: Configuration | None = None) -> None:
        self.configuration = configuration or Configuration()

    def lire(self, evenements_bruts: Iterable[dict[str, Any]]) -> Rapport:
        rapport = Rapport()

        for evenement in evenements_bruts:
            rapport.evenements_lus += 1
            classement = classer(evenement)
            rapport.compter(classement.categorie, classement.type_affiche)

            reference = evenements.identifiant(evenement)

            if classement.categorie is Categorie.INCONNU:
                rapport.signaler(
                    "type inconnu",
                    f"{classement.type_affiche} : {classement.motif}",
                    reference,
                )
                continue

            if classement.categorie is not Categorie.TRAITE:
                continue

            assert classement.famille is not None
            self._signaler_libelles_non_reconnus(evenement, rapport, reference)

            try:
                operation = self._construire(evenement, classement.famille, rapport)
            except OperationNonProduite as refus:
                rapport.signaler(refus.categorie, str(refus), reference)
                continue

            rapport.operations.append(operation)
            rapport.anomalies.extend(controler(operation))

        return rapport

    # --- Repérage des valeurs dans l'écran ------------------------------------

    def _index(self, evenement: dict[str, Any]) -> dict[tuple[Section, Notion], str | None]:
        """Associe (section, notion) au texte affiché, une fois les libellés traduits."""
        index: dict[tuple[Section, Notion], str | None] = {}
        for ligne in evenements.lignes(evenement):
            section = lexique.section_connue(ligne.section)
            if section is None or section is Section.SANS_INFORMATION:
                continue
            entree = lexique.entree(section, ligne.titre)
            if entree is not None:
                index[(section, entree.notion)] = ligne.texte
        return index

    def _signaler_libelles_non_reconnus(
        self, evenement: dict[str, Any], rapport: Rapport, reference: str | None
    ) -> None:
        """Un libellé inconnu n'est jamais ignoré : il part au rapport (D-19)."""
        for ligne in evenements.lignes(evenement):
            section = lexique.section_connue(ligne.section)
            if section is None:
                rapport.signaler(
                    "section non reconnue",
                    f"section {sur(ligne.section)}, ligne {sur(ligne.titre)}",
                    reference,
                )
                continue
            if section is Section.SANS_INFORMATION:
                continue
            if lexique.entree(section, ligne.titre) is not None:
                continue
            if ligne.titre in lexique.NATURES_EN_TITRE:
                continue
            rapport.signaler(
                "libellé non reconnu",
                f"« {sur(ligne.titre)} » dans la section {section.value}",
                reference,
            )

    def _nombre(
        self,
        index: dict[tuple[Section, Notion], str | None],
        section: Section,
        notion: Notion,
        *,
        obligatoire: bool,
        devise_attendue: bool = True,
    ) -> NombreLu | None:
        """Lit un nombre en imposant l'écriture déclarée par le lexique."""
        texte = index.get((section, notion))
        if texte is None:
            if obligatoire:
                raise OperationNonProduite(
                    "valeur absente",
                    f"la valeur « {notion.value} » est absente de l'écran, alors qu'elle est "
                    "indispensable au calcul",
                )
            return None

        convention = lexique.convention(section, notion)
        if convention is None:  # pragma: no cover - toute notion numérique en déclare une
            raise OperationNonProduite(
                "écriture non déclarée",
                f"le lexique ne dit pas comment « {notion.value} » est écrit dans "
                f"la section {section.value}",
            )
        try:
            lu = lire_nombre(texte, convention)
        except LectureImpossible as echec:
            raise OperationNonProduite(
                "nombre illisible",
                f"« {notion.value} » : {echec.raison} (texte {sur(texte)})",
            ) from echec

        if devise_attendue and lu.devise is not None and lu.devise != DEVISE_UNIQUE:
            raise OperationNonProduite(
                "devise étrangère",
                f"« {notion.value} » est libellé en {lu.devise} ; "
                f"seul l'euro est pris en charge (D-26)",
            )
        return lu

    # --- Construction d'une opération ----------------------------------------

    def _construire(
        self, evenement: dict[str, Any], famille: Famille, rapport: Rapport
    ) -> Operation:
        index = self._index(evenement)

        match famille:
            case Famille.PLAN_EPARGNE | Famille.ORDRE_PONCTUEL:
                return self._achat_ou_vente(evenement, index, famille, rapport)
            case Famille.DIVIDENDE:
                return self._dividende(evenement, index, rapport)
            case Famille.VERSEMENT_NON_DIVIDENDE:
                return self._distribution(evenement, index, rapport)
            case Famille.ACTION_GAGNEE:
                return self._action_gagnee(evenement, index, rapport)
            case Famille.ACTIONS_GRATUITES:
                return self._actions_gratuites(evenement, index, rapport)

        raise OperationNonProduite(  # pragma: no cover - la liste des familles est fermée
            "famille inconnue", f"famille {famille} non prévue par la lecture"
        )

    def _achat_ou_vente(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        famille: Famille,
        rapport: Rapport,
    ) -> Operation:
        """Plan d'épargne ou ordre ponctuel.

        Le **sens vient du signe du montant** (champ structuré) : négatif = achat,
        positif = vente. Le mot « Kauf » ou « Verkaufen » ne fait que le recouper.
        """
        reference = _reference(evenement)
        montant = _montant(evenement)
        type_operation = TypeOperation.ACHAT if montant < 0 else TypeOperation.VENTE
        self._controler_sens(evenement, type_operation, rapport, reference)

        detail = Section.DETAIL_TRANSACTION
        quantite = self._nombre(index, detail, Notion.QUANTITE, obligatoire=True)
        prix = self._nombre(index, detail, Notion.PRIX_UNITAIRE, obligatoire=True)
        brut = self._nombre(index, detail, Notion.MONTANT_BRUT, obligatoire=True)

        assert quantite is not None
        self._controler_quantite_du_resume(index, quantite, rapport, reference)

        frais = self._frais(index)
        taxes = self._taxes(index, Section.APERCU)
        montant_regle = abs(montant)
        self._controler_total_affiche(index, Section.APERCU, montant_regle, rapport, reference)

        actif, provenance_actif = self._actif(evenement)
        resolution = self._poche(
            actif,
            evenements.compte(evenement),
            index.get((Section.APERCU, Notion.POCHE)),
            rapport,
            reference,
        )

        nature = self._nature_en_titre(evenement) or (
            NatureSource.PLAN_EPARGNE
            if famille is Famille.PLAN_EPARGNE
            else NatureSource.ORDRE_PONCTUEL
        )

        return self._assembler(
            evenement=evenement,
            type_operation=type_operation,
            nature=nature,
            actif=actif,
            provenance_actif=provenance_actif,
            resolution=resolution,
            index=index,
            quantite=ValeurLue(quantite, Provenance.TEXTE),
            prix=ValeurLue(prix, Provenance.TEXTE),
            brut=ValeurLue(brut, Provenance.TEXTE),
            frais=frais,
            taxes=taxes,
            montant_regle=montant_regle,
        )

    def _dividende(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
    ) -> Operation:
        """Dividende en espèces.

        `Gesamt` est le montant **net** reçu, et il vaut le montant structuré. Le **brut**,
        qui seul compte dans la performance (D-29), est donc `net + taxe`. Vérifié sur les
        dividendes libellés en euros : parts × dividende par action retombe bien sur ce brut.
        """
        self._exiger_nature(index, NatureSource.DIVIDENDE_ESPECES, "dividende")
        return self._versement(
            evenement,
            index,
            rapport,
            TypeOperation.DIVIDENDE,
            NatureSource.DIVIDENDE_ESPECES,
            notion_brut=None,
        )

    def _distribution(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
    ) -> Operation:
        """Distribution de capital (« Kapitalverteilung »).

        Ce type d'événement peut porter autre chose qu'une distribution de capital (Q-07) :
        la nature doit donc être écrite noir sur blanc, sinon rien n'est produit. Ici le brut
        est affiché directement (« Bruttoertrag »), et il vaut bien net + taxe.
        """
        self._exiger_nature(index, NatureSource.DISTRIBUTION_CAPITAL, "distribution de capital")
        return self._versement(
            evenement,
            index,
            rapport,
            TypeOperation.DISTRIBUTION_CAPITAL,
            NatureSource.DISTRIBUTION_CAPITAL,
            notion_brut=Notion.PRODUIT_BRUT,
        )

    def _versement(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
        type_operation: TypeOperation,
        nature: NatureSource,
        notion_brut: Notion | None,
    ) -> Operation:
        """Tronc commun d'un dividende et d'une distribution : de l'argent, pas de parts."""
        reference = _reference(evenement)
        montant = _montant(evenement)
        if montant < 0:
            raise OperationNonProduite(
                "sens inattendu",
                "un versement sur un actif devrait faire entrer de l'argent, "
                "or le montant est négatif",
            )

        affaire = Section.AFFAIRE
        taxes = self._taxes(index, affaire)
        montant_regle = montant
        self._controler_total_affiche(index, affaire, montant_regle, rapport, reference)

        if notion_brut is None:
            # Le brut n'est pas affiché : il se reconstitue à partir du net et de la taxe.
            # Il dépend donc d'un texte, et sa provenance le dit.
            brut = ValeurLue(
                NombreLu(montant_regle + taxes.valeur, decimales=2), Provenance.TEXTE
            )
        else:
            lu = self._nombre(index, affaire, notion_brut, obligatoire=True)
            assert lu is not None
            brut = ValeurLue(lu, Provenance.TEXTE)

        quantite = self._quantite_informative(index, rapport, reference)
        prix = self._dividende_par_action(index, rapport, reference)

        actif, provenance_actif = self._actif(evenement)
        resolution = self._poche(
            actif, evenements.compte(evenement), None, rapport, reference
        )

        return self._assembler(
            evenement=evenement,
            type_operation=type_operation,
            nature=nature,
            actif=actif,
            provenance_actif=provenance_actif,
            resolution=resolution,
            index=index,
            quantite=quantite,
            prix=prix,
            brut=brut,
            frais=ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE),
            taxes=taxes,
            montant_regle=montant_regle,
        )

    def _action_gagnee(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
    ) -> Operation:
        """Action gagnée : des titres entrent, rien n'est payé (D-15).

        Trade Republic affiche ici le cours du jour : c'est exactement le prix que D-15
        demande de retenir, et il est vérifiable à l'écran. Il est donc lu plutôt que laissé
        à compléter. La part en espèces du lot, elle, est hors périmètre (D-11).
        """
        reference = _reference(evenement)
        apercu, transaction = Section.APERCU, Section.TRANSACTION

        quantite = self._nombre(index, apercu, Notion.QUANTITE, obligatoire=True)
        prix = self._nombre(index, apercu, Notion.PRIX_UNITAIRE, obligatoire=True)
        brut = self._nombre(index, transaction, Notion.VALEUR_DES_TITRES, obligatoire=True)

        if index.get((transaction, Notion.CREDIT_ESPECES)) is not None:
            rapport.signaler(
                "part en espèces ignorée",
                "ce lot comporte aussi un crédit en espèces, laissé de côté : "
                "les espèces ne sont pas suivies (D-11)",
                reference,
            )

        actif, provenance_actif = self._actif(evenement)
        resolution = self._poche(
            actif, evenements.compte(evenement), None, rapport, reference
        )

        return self._assembler(
            evenement=evenement,
            type_operation=TypeOperation.TITRES_RECUS,
            nature=NatureSource.ACTION_GAGNEE,
            actif=actif,
            provenance_actif=provenance_actif,
            resolution=resolution,
            index=index,
            quantite=ValeurLue(quantite, Provenance.TEXTE),
            prix=ValeurLue(prix, Provenance.TEXTE),
            brut=ValeurLue(brut, Provenance.TEXTE),
            frais=ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE),
            taxes=ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE),
            montant_regle=ZERO,
        )

    def _actions_gratuites(
        self,
        evenement: dict[str, Any],
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
    ) -> Operation:
        """Actions gratuites : des titres entrent, et **aucun prix n'est affiché**.

        Le prix retenu sera le cours du jour d'apparition (D-15), disponible à l'étape 4.
        En attendant, le prix et le montant brut sont marqués « à compléter » : la ligne est
        visible, signalée, et ne compte dans aucun total.
        """
        reference = _reference(evenement)
        self._exiger_nature(index, NatureSource.ACTIONS_GRATUITES, "actions gratuites")

        quantite = self._nombre(index, Section.APERCU, Notion.QUANTITE, obligatoire=True)
        actif, provenance_actif = self._actif(evenement)
        resolution = self._poche(
            actif, evenements.compte(evenement), None, rapport, reference
        )

        return self._assembler(
            evenement=evenement,
            type_operation=TypeOperation.TITRES_RECUS,
            nature=NatureSource.ACTIONS_GRATUITES,
            actif=actif,
            provenance_actif=provenance_actif,
            resolution=resolution,
            index=index,
            quantite=ValeurLue(quantite, Provenance.TEXTE),
            prix=None,
            brut=None,
            frais=ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE),
            taxes=ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE),
            montant_regle=ZERO,
            en_attente_de_cours=True,
        )

    # --- Briques communes -----------------------------------------------------

    def _assembler(
        self,
        *,
        evenement: dict[str, Any],
        type_operation: TypeOperation,
        nature: NatureSource,
        actif: str,
        provenance_actif: Provenance,
        resolution: module_poche.Resolution,
        index: dict[tuple[Section, Notion], str | None],
        quantite: ValeurLue | None,
        prix: ValeurLue | None,
        brut: ValeurLue | None,
        frais: ValeurLue,
        taxes: ValeurLue,
        montant_regle: Decimal,
        en_attente_de_cours: bool = False,
    ) -> Operation:
        """Assemble la ligne pivot et son dictionnaire de provenance.

        `en_attente_de_cours` distingue les deux raisons pour lesquelles un prix peut
        manquer, que le format pivot ne confond pas :

        - des titres sont entrés **sans prix affiché** : le cours du jour les complétera à
          l'étape 4, donc `a_completer`, et la ligne ne compte dans aucun total (D-15) ;
        - un dividende par action est libellé en devise étrangère : il est simplement
          **absent**, ce qui est permis pour une valeur informative (format-pivot §3). Le
          montant brut, lui, est connu : rien n'attend de donnée externe.
        """
        instant = evenements.horodatage(evenement)
        if instant is None:
            raise OperationNonProduite(
                "horodatage absent", "l'événement n'a pas d'horodatage exploitable (D-36)"
            )

        devise = evenements.devise(evenement)
        if devise is not None and devise != DEVISE_UNIQUE:
            raise OperationNonProduite(
                "devise étrangère", f"opération en {devise} ; seul l'euro est pris en charge"
            )

        assert resolution.poche is not None
        assert resolution.provenance is not None

        provenance: dict[str, Provenance] = {
            "actif": provenance_actif,
            "poche": resolution.provenance,
            "montant_regle": Provenance.DONNEE,
            "frais": frais.provenance,
            "taxes": taxes.provenance,
        }
        if quantite is not None:
            provenance["quantite"] = quantite.provenance
        if prix is not None:
            provenance["prix_unitaire"] = prix.provenance
        elif en_attente_de_cours:
            provenance["prix_unitaire"] = Provenance.A_COMPLETER
        if brut is not None:
            provenance["montant_brut"] = brut.provenance
        elif en_attente_de_cours:
            provenance["montant_brut"] = Provenance.A_COMPLETER

        nom_actif = index.get((Section.APERCU, Notion.NOM_ACTIF))
        if nom_actif is not None:
            provenance["nom_actif"] = Provenance.TEXTE

        reference = _reference(evenement)
        return Operation(
            identifiant=f"tr-{reference}",
            instant_utc=instant,
            date=jour_a_paris(instant),
            type=type_operation,
            nature_source=nature.value,
            actif=actif,
            nom_actif=nom_actif,
            poche=resolution.poche,
            quantite=quantite.valeur if quantite else None,
            prix_unitaire=prix.valeur if prix else None,
            montant_brut=brut.valeur if brut else None,
            frais=frais.valeur,
            taxes=taxes.valeur,
            montant_regle=montant_regle,
            reference_source=reference,
            provenance=provenance,
        )

    def _actif(self, evenement: dict[str, Any]) -> tuple[str, Provenance]:
        """Identifiant de l'actif, et la solidité de cette information.

        L'en-tête `instrumentDetail` est la bonne source. Pour les dividendes et les titres
        reçus, elle n'existe pas : l'ISIN ne se lit que dans le **chemin de l'icône**. C'est
        exact, mais c'est le détournement d'une image, donc une déduction.
        """
        entete = evenements.isin_entete(evenement)
        icone = evenements.isin_icone(evenement)

        if entete is not None:
            if icone is not None and icone != entete:
                raise OperationNonProduite(
                    "actif incertain",
                    "l'en-tête et l'icône ne désignent pas le même actif",
                )
            return entete, Provenance.DONNEE

        if icone is not None:
            return icone, Provenance.DEDUCTION

        raise OperationNonProduite(
            "actif introuvable", "aucun identifiant d'actif dans cet événement"
        )

    def _poche(
        self,
        actif: str,
        compte: str | None,
        poche_affichee: str | None,
        rapport: Rapport,
        reference: str | None,
    ) -> module_poche.Resolution:
        resolution = module_poche.resoudre(actif, compte, self.configuration, poche_affichee)

        if not resolution.trouvee:
            if compte is not None:
                rapport.comptes_a_nommer.add(compte)
            else:
                rapport.actifs_sans_poche.add(actif)
            raise OperationNonProduite("poche indéterminable", resolution.motif or "")

        if resolution.desaccord:
            rapport.signaler("poche en désaccord", resolution.desaccord, reference)
        return resolution

    def _frais(self, index: dict[tuple[Section, Notion], str | None]) -> ValeurLue:
        """Frais de l'opération. « Gebühr » vaut parfois un **mot** (« Kostenlos »).

        Un mot inconnu à cette place n'est pas traité comme zéro : ce serait effacer un frais
        réel. L'opération est alors refusée et signalée.
        """
        texte = index.get((Section.APERCU, Notion.FRAIS))
        if texte is None:
            return ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE)

        if texte.strip() in lexique.MOTS_SANS_FRAIS:
            return ValeurLue(NombreLu(ZERO, decimales=2), Provenance.TEXTE)

        lu = self._nombre(index, Section.APERCU, Notion.FRAIS, obligatoire=True)
        assert lu is not None
        return ValeurLue(lu.absolu(), Provenance.TEXTE)

    def _taxes(
        self, index: dict[tuple[Section, Notion], str | None], section: Section
    ) -> ValeurLue:
        """Taxes prélevées. Elles sont **affichées négatives** ; le pivot n'accepte que des
        nombres positifs, le signe est donc retiré ici, explicitement."""
        if index.get((section, Notion.TAXES)) is None:
            return ValeurLue(NombreLu(ZERO, decimales=2), Provenance.DONNEE)

        lu = self._nombre(index, section, Notion.TAXES, obligatoire=True)
        assert lu is not None
        return ValeurLue(lu.absolu(), Provenance.TEXTE)

    def _quantite_informative(
        self,
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
        reference: str | None,
    ) -> ValeurLue | None:
        """Parts détenues au moment d'un versement : utile pour vérifier, jamais pour compter.

        Son absence n'empêche rien (format-pivot §3), donc une lecture ratée est signalée
        plutôt que bloquante.
        """
        if index.get((Section.AFFAIRE, Notion.QUANTITE)) is None:
            return None
        try:
            lu = self._nombre(index, Section.AFFAIRE, Notion.QUANTITE, obligatoire=True)
        except OperationNonProduite as echec:
            rapport.signaler("quantité illisible", str(echec), reference)
            return None
        assert lu is not None
        return ValeurLue(lu, Provenance.TEXTE)

    def _dividende_par_action(
        self,
        index: dict[tuple[Section, Notion], str | None],
        rapport: Rapport,
        reference: str | None,
    ) -> ValeurLue | None:
        """Dividende par action, quand il est libellé en euros.

        Il est parfois affiché dans la devise d'origine de l'actif. Il n'est alors pas
        comparable au montant brut en euros : il est laissé vide plutôt que recopié, et le
        contrôle « quantité × prix » est simplement sans objet.
        """
        if index.get((Section.AFFAIRE, Notion.DIVIDENDE_PAR_ACTION)) is None:
            return None
        try:
            lu = self._nombre(
                index, Section.AFFAIRE, Notion.DIVIDENDE_PAR_ACTION, obligatoire=True
            )
        except OperationNonProduite as echec:
            rapport.signaler("dividende par action non retenu", str(echec), reference)
            return None
        assert lu is not None
        return ValeurLue(lu, Provenance.TEXTE)

    # --- Contrôles qui ne bloquent pas, mais qui parlent ----------------------

    def _controler_sens(
        self,
        evenement: dict[str, Any],
        type_operation: TypeOperation,
        rapport: Rapport,
        reference: str | None,
    ) -> None:
        """Le mot affiché doit dire la même chose que le signe du montant."""
        for titre in _titres_apercu(evenement):
            sens = lexique.SENS_EN_TITRE.get(titre)
            if sens is not None and sens != type_operation.value:
                rapport.signaler(
                    "sens en désaccord",
                    f"le montant indique « {type_operation.value} » alors que l'écran "
                    f"affiche « {sur(titre)} »",
                    reference,
                )

    def _controler_quantite_du_resume(
        self,
        index: dict[tuple[Section, Notion], str | None],
        quantite: NombreLu,
        rapport: Rapport,
        reference: str | None,
    ) -> None:
        """La quantité est écrite à **deux endroits** de l'écran : elles doivent coïncider.

        L'écran d'un achat résume l'opération par « quantité × prix », et la page de détail
        qu'il ouvre redonne la quantité seule. C'est un contrôle gratuit, qui ne dépend
        d'aucun fichier extérieur : si la lecture d'un nombre dérape, les deux ne tombent
        plus sur la même valeur.
        """
        resume = index.get((Section.APERCU, Notion.RESUME_TRANSACTION))
        if resume is None or "×" not in resume:
            return

        convention = lexique.convention(Section.DETAIL_TRANSACTION, Notion.QUANTITE)
        if convention is None:  # pragma: no cover - déclarée par le lexique
            return
        try:
            depuis_le_resume = lire_nombre(resume.split("×")[0], convention)
        except LectureImpossible:
            rapport.signaler(
                "quantité du résumé illisible",
                "la quantité rappelée par le résumé « quantité × prix » n'a pas pu être lue",
                reference,
            )
            return

        if depuis_le_resume.valeur != quantite.valeur:
            rapport.signaler(
                "quantité en désaccord",
                "les deux endroits où l'écran affiche la quantité ne donnent pas la même "
                "valeur : la lecture de l'un des deux est faussée",
                reference,
            )

    def _controler_total_affiche(
        self,
        index: dict[tuple[Section, Notion], str | None],
        section: Section,
        montant_regle: Decimal,
        rapport: Rapport,
        reference: str | None,
    ) -> None:
        """Le total affiché doit valoir le montant structuré. Sinon, la lecture a dérapé."""
        notion = (
            Notion.MONTANT_REGLE if section is Section.APERCU else Notion.MONTANT_NET_RECU
        )
        if index.get((section, notion)) is None:
            return
        try:
            lu = self._nombre(index, section, notion, obligatoire=True)
        except OperationNonProduite as echec:
            rapport.signaler("total affiché illisible", str(echec), reference)
            return
        assert lu is not None
        if abs(lu.absolu().valeur - montant_regle) > Decimal("0.01"):
            rapport.signaler(
                "total en désaccord",
                "le total affiché à l'écran ne correspond pas au montant enregistré "
                "par la banque : la lecture des textes est peut-être faussée",
                reference,
            )

    def _exiger_nature(
        self,
        index: dict[tuple[Section, Notion], str | None],
        attendue: NatureSource,
        nom_lisible: str,
    ) -> None:
        """Certaines natures ne sont écrites que dans un libellé, et rien ne les remplace.

        Le type d'événement d'une distribution de capital sert aussi à d'autres versements
        (Q-07) : sans le mot, on ne sait pas ce qu'on lit, et on ne produit rien.
        """
        texte = index.get((Section.APERCU, Notion.NATURE))
        if texte is None:
            raise OperationNonProduite(
                "nature absente",
                f"rien n'indique qu'il s'agit d'un(e) {nom_lisible} : "
                "le libellé qui le dirait est absent",
            )
        nature = lexique.NATURES_EN_VALEUR.get(texte.strip())
        if nature is not attendue:
            raise OperationNonProduite(
                "nature non reconnue",
                f"le libellé {sur(texte)} n'est pas celui d'un(e) {nom_lisible} ; "
                "l'événement doit être examiné avant d'être compté",
            )

    def _nature_en_titre(self, evenement: dict[str, Any]) -> NatureSource | None:
        for titre in _titres_apercu(evenement):
            nature = lexique.NATURES_EN_TITRE.get(titre)
            if nature is not None:
                return nature
        return None


def _titres_apercu(evenement: dict[str, Any]) -> list[str]:
    """Titres des lignes de la section « Übersicht », quelle que soit la langue.

    Trade Republic y range parfois l'information **dans le titre** : la ligne s'appelle
    « Kauf » ou « Verkaufen » et sa valeur est le statut.
    """
    return [
        ligne.titre
        for ligne in evenements.lignes(evenement)
        if lexique.section_connue(ligne.section) is Section.APERCU
    ]


def _montant(evenement: dict[str, Any]) -> Decimal:
    montant = evenements.montant_signe(evenement)
    if montant is None:
        raise OperationNonProduite(
            "montant absent", "l'événement ne porte aucun montant alors qu'il devrait"
        )
    return montant


def _reference(evenement: dict[str, Any]) -> str:
    reference = evenements.identifiant(evenement)
    if reference is None:
        raise OperationNonProduite(
            "identifiant absent", "l'événement n'a pas d'identifiant : il serait introuvable"
        )
    return reference
