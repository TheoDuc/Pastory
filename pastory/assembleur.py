"""L'assembleur : le seul module qui branche les couches entre elles.

Il lit le dossier de dépôt, trouve les réglages, réunit les sources de cours et de compositions,
puis passe le tout au moteur. La ligne de commande (`cli.py`) et l'interface (`vues/`) l'appellent
**toutes les deux** : un seul assemblage, donc les mêmes chiffres à l'écran et dans
`pastory positions`.

C'est aussi **le seul endroit qui nomme les sources extérieures** — Yahoo, l'émetteur Amundi,
la liste de Xetra, extraETF, le registre de l'ESMA, GLEIF. Le moteur ne sait pas d'où viennent les
cours, les taux et les compositions : il déclare la forme qu'il en attend, et c'est ici qu'on la
lui donne (D-26). Les tests remplacent ces fonctions-là, et seulement elles : aucun test ne sort de
la machine.

Sorti de `cli.py` à l'étape 9, sans changer une ligne de calcul.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pastory.adaptateurs.trade_republic import depot as depot_export
from pastory.adaptateurs.trade_republic.lecture import Lecteur
from pastory.adaptateurs.trade_republic.rapport import Rapport
from pastory.config import actifs as config_actifs
from pastory.config import emplacements
from pastory.config import fiscalite as config_fiscalite
from pastory.donnees_externes import actions as source_actions
from pastory.donnees_externes import amundi, extraetf, firds, xetra
from pastory.donnees_externes import completion as completion_cours
from pastory.donnees_externes import composition as composition_externe
from pastory.donnees_externes.cache import Cache
from pastory.donnees_externes.cache_compositions import CacheDeCompositions
from pastory.donnees_externes.completion import Completion
from pastory.donnees_externes.cours import FournisseurDeCours
from pastory.donnees_externes.yahoo import Yahoo
from pastory.moteur import couts as couts_moteur
from pastory.moteur import diversification as diversification_moteur
from pastory.moteur import rendements as rendements_moteur
from pastory.moteur import valeur_reelle as valeur_reelle_moteur
from pastory.moteur.portefeuille import Portefeuille
from pastory.parametres import contenus as parametres_contenus
from pastory.parametres import couts as parametres_couts
from pastory.parametres import fiscalite as parametres_fiscalite
from pastory.parametres import referentiels as parametres_referentiels
from pastory.reglages import Trouvee
from pastory.reglages import assemblage as assemblage_reglages
from pastory.reglages.assemblage import Reglages
from pastory.reglages.cache import CacheDesReglages
from pastory.reglages.recherche import Recherche


def dossier_de_lecture(dossier_export: Path | None) -> Path:
    """Où lire : ce qu'indique `--export` (un dossier, ou directement un fichier), ou le
    dossier de dépôt.

    Le dossier de dépôt est créé s'il n'existe pas encore : c'est là que l'utilisateur doit
    déposer son export (D-80), et le message qui l'y invite doit désigner un dossier réel.
    """
    if dossier_export is not None:
        return dossier_export
    dossier = emplacements.dossier_exports()
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def lire(dossier: Path) -> Rapport:
    """Lecture commune à tout : **un** portefeuille — le fichier désigné, ou le
    portefeuille ouvert du dossier (D-109)."""
    return Lecteur().lire(depot_export.lire(dossier))


# --- Les sources : le seul endroit qui les nomme --------------------------------------


def source_des_cotations() -> Yahoo:
    """**Le seul endroit qui nomme Yahoo** pour la recherche des cotations (D-51), et celui que
    les tests remplacent : aucun test ne sort de la machine."""
    return Yahoo()


def frais_courants_de_l_emetteur() -> amundi.FraisCourantsAmundi:
    """Les frais courants publiés par l'émetteur (Amundi), première source de TER."""
    return amundi.FraisCourantsAmundi()


def liste_des_etf() -> xetra.ListeXetra:
    """La liste des ETF de Xetra, seconde source des frais courants (D-61).

    Fonction à part, et non un appel direct, pour la même raison que `source_des_cotations` :
    c'est **le seul endroit** qui nomme la source, et les tests la remplacent ici — aucun test
    du projet ne sort de la machine.
    """
    return xetra.telecharger()


def classes_d_actifs() -> extraetf.SourceExtraEtf:
    """La classe d'actifs d'un fonds (D-89). La construire n'appelle rien."""
    return extraetf.SourceExtraEtf()


def registre_cfi() -> firds.RegistreFirds:
    """Le registre de l'ESMA, témoin du contenu d'un fonds (D-89). Le construire n'appelle rien."""
    return firds.RegistreFirds()


def reglages(rapport: Rapport, hors_ligne: bool = False, tiers: bool = False) -> Reglages:
    """Tout ce que l'application trouve seule, contrôle et montre (D-80).

    Ce que dit la banque, ce que les sources trouvent — gardé dans `cache/reglages.csv` — et
    les corrections de l'utilisateur, qui l'emportent. Hors ligne, seul le cache sert ; pour
    l'export d'un tiers (`--export`), rien n'est cherché (règle 2 de CLAUDE.md).

    Les sources de TER sont rangées **par ordre de confiance** : l'émetteur, qui publie le
    chiffre de son document d'information clé, puis la liste de Xetra, parfois en retard.
    """
    recherche = Recherche(
        CacheDesReglages(),
        None if hors_ligne else source_des_cotations(),
        (lambda: frais_courants_de_l_emetteur(), lambda: liste_des_etf()),
        classes=classes_d_actifs(),
        registre=registre_cfi(),
        lecture_des_contenus=parametres_contenus.charger(),
        tiers=tiers,
    )
    banque = rapport.ce_que_dit_la_banque()
    duree = parametres_fiscalite.charger().pea_duree_exoneration_ir.valeur
    corrections = config_actifs.charger()
    # Une date de PEA corrigée à la main est celle d'une personne : elle ne vaut que pour
    # le portefeuille qu'elle désigne (D-109).
    depot = rapport.depot
    du_pea = config_fiscalite.charger().pour(
        depot.portefeuille, [*depot.autres], tiers=tiers
    )
    return assemblage_reglages.assembler(
        banque,
        recherche.trouver(banque, rapport.operations, corrections),
        corrections,
        config_fiscalite.ConfigurationFiscale(premier_versement_pea=du_pea.date),
        duree_avant_retrait_libre=int(duree),
        corrections_ecartees=du_pea.ecartees,
    )


def fournisseur_de_cours(
    configuration: config_actifs.Configuration, hors_ligne: bool = False
) -> FournisseurDeCours:
    """Réunit la cotation de chaque actif, le cache local et la source.

    **C'est le seul endroit de l'application qui nomme Yahoo pour les cours** (D-51). Le moteur
    ne sait pas d'où viennent les cours, et changer de source ne toucherait que cette fonction
    (D-26).
    """
    return FournisseurDeCours(
        configuration,
        Cache(),
        None if hors_ligne else Yahoo(),
        hors_ligne=hors_ligne,
    )


def parametres_des_couts(reglages: Reglages) -> couts_moteur.ParametresDeCouts:
    """Le barème livré avec l'application, croisé avec les réglages de chaque actif.

    C'est **le seul endroit** qui réunit les deux : le moteur, lui, ne connaît qu'un protocole
    (`ParametresDeCouts`) et ne sait ni ce qu'est un fichier TOML, ni ce qu'est un ETF (D-26).
    """
    return parametres_couts.ParametresDuPortefeuille(parametres_couts.charger(), reglages)


def fournisseur_de_compositions(
    configuration: config_actifs.Configuration, hors_ligne: bool = False
) -> composition_externe.FournisseurDeCompositions:
    """Réunit le cache local, la source des fonds et celle des actions (D-63, D-70).

    **C'est le seul endroit de l'application qui nomme extraETF et GLEIF.** Le moteur ne sait pas
    d'où viennent les compositions : il déclare un protocole, et changer de source ne toucherait
    que cette fonction (D-26).

    Le type de chaque actif décide de la source interrogée : un ETF et une action ne se
    regardent pas au même endroit, et une crypto ne se regarde nulle part (D-68). La source de
    secours est essayée d'elle-même pour un ETF que la principale n'ouvre pas (D-80) ; la source
    de chaque chiffre reste affichée ligne par ligne.
    """
    return composition_externe.FournisseurDeCompositions(
        cache=CacheDeCompositions(),
        source_etf=None if hors_ligne else extraetf.SourceExtraEtf(),
        source_action=None if hors_ligne else source_actions.SourceDActions(),
        actifs=configuration,
        hors_ligne=hors_ligne,
        secours={} if hors_ligne else sources_de_secours(),
    )


def sources_de_secours() -> dict[str, composition_externe.SourceDeCompositionDEtf]:
    """Les sources de secours, par le nom sous lequel une correction les désigne (D-77).

    Une seule pour l'instant. Sa table de libellés de pays est chargée ici, parce que c'est ici
    qu'on sait qu'elle existe : le moteur n'a jamais à connaître ni Amundi, ni un fichier TOML.
    """
    return {"amundi": amundi.SourceAmundi(parametres_referentiels.charger_libelles_de_pays())}


def referentiels() -> parametres_referentiels.Referentiels:
    """Les secteurs, les pays et leurs zones, avec leur source et leur date (D-65 à D-67)."""
    return parametres_referentiels.charger_tout()


def regles_fiscales(reglages: Reglages) -> parametres_fiscalite.ReglesFiscales:
    """Les taux datés et sourcés, plus la date d'ouverture du PEA et son origine (D-59, D-80)."""
    pea = reglages.premier_versement_pea
    retenu = pea.retenu if pea is not None else None
    if not isinstance(retenu, Trouvee):
        return parametres_fiscalite.charger()
    alerte = None
    if reglages.retraits_pea:
        alerte = (
            "aucun retrait n'a jamais été fait sur le plan - CONTREDIT par vos exports : de "
            "l'argent est sorti du PEA le "
            + ", le ".join(jour.isoformat() for jour in reglages.retraits_pea)
            + ". Le gain du plan est alors mal approché, et l'impôt estimé aussi"
        )
    origine = (
        "corrigée par vous dans fiscalite.toml"
        if retenu.origine.corrigee
        else f"trouvée dans votre {retenu.origine.source}"
    )
    return parametres_fiscalite.charger(
        premier_versement_pea=retenu.valeur,
        origine_de_la_date=origine,
        reserve=None if retenu.origine.corrigee else retenu.origine.reserve,
        alerte=alerte,
    )


# --- Le moteur, branché -----------------------------------------------------------------


@dataclass(frozen=True)
class Construit:
    """Tout ce que le moteur a produit après la lecture et le rejeu, et ce qui l'a nourri."""

    portefeuille: Portefeuille
    """Arrêté à la fin de la période."""

    rapport: Rapport
    completion: Completion
    fournisseur: FournisseurDeCours
    """Le même pour la complétion et la valorisation : ses refus couvrent les deux."""

    periode: rendements_moteur.Periode
    synthese: rendements_moteur.Synthese

    detail_des_couts: couts_moteur.DetailDesCouts
    """Les coûts payés de la période et les coûts estimés (étape 6)."""

    valeur_reelle: valeur_reelle_moteur.ValeurReelle
    """Ce qu'on récupérerait en vendant tout à la date de valorisation (D-23)."""

    diversification: diversification_moteur.Diversification | None = None
    """Les trois répartitions (étape 7). `None` si aucune composition n'est disponible."""

    compositions: composition_externe.FournisseurDeCompositions | None = None
    """Gardé pour que les refus de compositions soient affichés après les chiffres."""

    reglages: Reglages | None = None
    """Ce qui a été trouvé seul pour chaque actif, et ce qui ne l'a pas été (D-80)."""


def construire(
    dossier: Path,
    periode: rendements_moteur.Periode,
    hors_ligne: bool = False,
    tiers: bool = False,
) -> Construit:
    """Lecture, complétion des prix, rejeu, puis valorisation et rendements.

    La complétion s'insère **entre** la lecture et le moteur, et ne produit que du format
    pivot : le moteur ne gagne pas une ligne et ne sait rien des cours (D-26). La
    valorisation, elle, reçoit le fournisseur de cours **en paramètre** : le moteur déclare
    ce dont il a besoin, et c'est ici, et seulement ici, qu'on le lui donne.
    """
    rapport = lire(dossier)
    # L'export d'un tiers : aucun appel réseau, ni recherche, ni cours, ni composition. Envoyer
    # ses ISIN à un service extérieur, ce serait divulguer ce qu'il détient (règle 2).
    hors_ligne = hors_ligne or tiers
    trouves = reglages(rapport, hors_ligne, tiers)
    configuration = trouves.configuration()

    fournisseur = fournisseur_de_cours(configuration, hors_ligne)
    completion = completion_cours.completer_les_prix(rapport.operations, fournisseur)

    portefeuille = Portefeuille.construire(completion.operations).au(periode.fin)
    synthese = rendements_moteur.synthese(portefeuille, periode, fournisseur)

    # Les coûts et la valeur réelle partent de la **même** valorisation que les rendements :
    # deux valorisations du même jour pourraient différer d'un centime, et le propriétaire
    # verrait deux valeurs brutes dans le même rapport.
    parametres = parametres_des_couts(trouves)
    detail = couts_moteur.detailler(
        portefeuille, periode, synthese.valorisation, parametres
    )
    valeur = valeur_reelle_moteur.valeur_reelle(
        portefeuille, synthese.valorisation, parametres, regles_fiscales(trouves)
    )

    # La répartition part de la **même** valorisation que tout le reste : c'est elle qui fournit
    # les poids, et deux valorisations du même jour pourraient différer d'un centime.
    compositions = fournisseur_de_compositions(configuration, hors_ligne)
    diversification = diversification_moteur.diversifier(
        synthese.valorisation, compositions, referentiels()
    )
    return Construit(
        portefeuille=portefeuille,
        rapport=rapport,
        completion=completion,
        fournisseur=fournisseur,
        periode=periode,
        synthese=synthese,
        detail_des_couts=detail,
        valeur_reelle=valeur,
        diversification=diversification,
        compositions=compositions,
        reglages=trouves,
    )
