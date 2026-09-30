"""« Déclarer ses actifs » : de l'ISIN au ticker, la devise attendue, et depuis l'étape 6 le
type de l'actif et ses frais courants (D-48, D-51, D-55, D-61).

Trade Republic identifie un actif par son **ISIN** ; les sources de cours gratuites, elles,
travaillent au **ticker** et à la place de cotation. Personne ne peut établir cette
correspondance à notre place de façon sûre : un même ETF cote sur des dizaines de places, et
la recherche automatique se trompe. Le comparatif en a trouvé un cas franc — pour un ETF qui
cote aussi à Xetra en euros, la recherche renvoie la cotation londonienne **en dollars**
(`docs/sources-de-cours.md` §4).

D'où ce fichier : l'application **propose**, l'utilisateur **valide**, et la devise attendue
est écrite noir sur blanc pour que le cours reçu puisse être confronté à elle (D-48). Un
actif non déclaré n'est pas valorisé : il est signalé, jamais estimé (D-45).

Le même schéma vaut pour ce que l'étape 6 a ajouté : le **type** de l'actif (ETF, action,
crypto), qui choisit son taux de spread par défaut, et le **TER** d'un ETF, proposé depuis la
liste Xetra et relu par l'utilisateur sur la fiche de l'émetteur — la liste est en retard sur
environ 5 % des lignes (`docs/couts-et-fiscalite.md` §2). Sans type : pas de spread estimé ;
sans TER : pas de frais courants estimés. Jamais une valeur par défaut silencieuse.

Le fichier vit dans le dossier personnel, hors du dossier synchronisé et hors de git
(D-37, D-01).
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pastory.config import ConfigurationInvalide, emplacements
from pastory.pivot.operation import DEVISE_UNIQUE

NOM_FICHIER = "actifs.toml"

FORME_ATTENDUE = '"<ISIN>" = { ticker = "AAAA.DE", devise = "EUR" }'
"""Ce qu'il faut écrire au minimum, cité tel quel dans les messages d'erreur."""

FORME_COMPLETE = (
    '"<ISIN>" = { ticker = "AAAA.DE", devise = "EUR", type = "etf", ter_pour_cent = 0.20 }'
)

TER_MINIMUM = Decimal("0.03")
TER_MAXIMUM = Decimal("1.00")
"""En pour cent. Hors de cette fourchette, c'est presque toujours une erreur d'unité : 0.20 écrit
pour 0,20 % vaudrait 20 % par an (`docs/couts-et-fiscalite.md` §2.4)."""

SPREAD_MAXIMUM = Decimal("5")
"""En pour cent, par côté. Au-delà, l'actif n'est plus négociable, ou l'unité est fausse."""

FORME_REPARTITION = 'pays = { US = 70.0, FR = 2.1 }  (et de même pour  secteurs )'
"""Comment corriger à la main la composition d'un actif (D-70)."""

TOTAL_MAXIMAL = Decimal("105")
"""Le total accepté pour une répartition déclarée, en pour cent.

Pourquoi pas 100 : le prêt de titres peut faire dépasser légèrement 100 % dans les données des
fonds (`docs/composition-des-etf.md` §8.3), et une répartition déclarée peut légitimement recopier
une telle source. Au-delà de 105, c'est une erreur de saisie.
"""


class TypeActif(StrEnum):
    """Ce qui choisit le taux de spread par défaut, et dit si un TER est attendu (D-55)."""

    ETF = "etf"
    ACTION = "action"
    CRYPTO = "crypto"


TYPES_ACCEPTES = tuple(type_actif.value for type_actif in TypeActif)


class ContenuActif(StrEnum):
    """**De quoi l'actif est fait à l'intérieur** (D-71). À ne pas confondre avec son `type`.

    Le `type` dit ce qu'on détient — un ETF, une action, une crypto — et c'est lui qui choisit le
    taux de spread et décide si un TER est attendu ([D-55](../../docs/decisions.md),
    [D-61](../../docs/decisions.md)). Le `contenu`, lui, dit ce qu'il y a dedans, et c'est lui qui
    décide de la place de l'actif dans les répartitions : un ETF obligataire reste un **ETF** avec
    ses frais courants, mais son contenu n'a ni pays ni secteur au sens des actions
    ([D-68](../../docs/decisions.md)).

    Les valeurs sont **les clés de `parametres/classes_actifs.toml`** : c'est ce qui permet au
    contenu déclaré d'être nommé et rangé comme celui qu'une source aurait annoncé.
    """

    ACTIONS = "actions"
    OBLIGATIONS = "obligations"
    MATIERES_PREMIERES = "matieres_premieres"


CONTENUS_ACCEPTES = tuple(contenu.value for contenu in ContenuActif)

SECOURS_ACCEPTES = ("amundi",)
"""Les sources de secours qu'on sait interroger (D-77).

Une valeur inconnue est **refusée à la lecture du fichier**, et non ignorée : un utilisateur qui
écrit « amundy » doit l'apprendre tout de suite, et non découvrir six écrans plus loin que son
fonds est resté non couvert.
"""


@dataclass(frozen=True)
class Declaration:
    """Ce que l'utilisateur déclare pour un actif : où chercher son cours, en quoi, et ce
    qu'il coûte."""

    ticker: str
    """Identifiant de l'actif chez la source, place comprise (« AAAA.DE », « BBB-EUR »)."""

    devise: str = DEVISE_UNIQUE
    """Devise **attendue**. Un cours qui arrive dans une autre est refusé, pas converti."""

    type: TypeActif | None = None
    """ETF, action ou crypto. Sans lui, pas de spread estimé pour cet actif."""

    ter_pour_cent: Decimal | None = None
    """Frais courants annuels d'un ETF, en pour cent, **validés** par l'utilisateur."""

    spread_pour_cent: Decimal | None = None
    """Un taux de spread par côté propre à cet actif, qui remplace celui de son type."""

    contenu: ContenuActif | None = None
    """De quoi l'actif est fait : actions, obligations, matières premières (D-71).

    Déclaré par l'utilisateur quand la source ne sait pas le dire. Sans lui, un ETF obligataire ou
    un ETF de matières premières serait annoncé « composition inconnue », alors que la vérité est
    qu'il n'a **ni pays ni secteur** — ce qui n'est pas un manque de données.
    """

    pays: Mapping[str, Decimal] | None = None
    """Répartition par pays **déclarée à la main**, qui l'emporte sur la source (D-70).

    La porte de sortie du choix « mise à jour automatique » : si la source se trompe sur un
    actif, on corrige ici sans attendre qu'elle se corrige. Les clés sont des codes ISO 3166-1
    alpha-2, les valeurs des pourcentages.
    """

    secteurs: Mapping[str, Decimal] | None = None
    """Répartition par secteur déclarée à la main. Mêmes règles ; les clés sont les codes de la
    nomenclature retenue (`parametres/secteurs.toml`)."""

    secours: str | None = None
    """La **source de secours** à interroger pour cet actif, quand la principale ne sait pas
    l'ouvrir (D-72, D-77).

    Déclarée **par actif**, et jamais devinée. La raison est que deux sources n'ont ni la même
    nomenclature sectorielle ni la même règle de pays : les mélanger en silence donnerait un
    total juste et une répartition fausse — 5 points d'écart mesurés sur la technologie. Le
    secours n'est donc employé que là où l'utilisateur l'a demandé, et la source de chaque
    chiffre reste affichée ligne par ligne.

    Une seule valeur existe aujourd'hui : `"amundi"`, qui ne sert que la **géographie** — les
    secteurs de cette source sont du GICS, et restent non couverts.
    """


@dataclass(frozen=True)
class FraisCourantsProposes:
    """Un TER trouvé dans une source, avec de quoi le reconnaître et le vérifier."""

    ter_pour_cent: Decimal
    source: str
    nom: str | None = None
    """Nom de la part dans la source : pour vérifier que c'est bien la sienne."""

    politique: str | None = None
    """« Accumulating » / « Distributing » : idem."""

    date: Date | None = None
    """La date d'effet annoncée par la source."""


@dataclass(frozen=True)
class Proposition:
    """Une correspondance trouvée par une source, à soumettre à l'utilisateur.

    Elle n'est jamais utilisée pour calculer : elle sert à remplir le fichier avec, en
    commentaire, de quoi la reconnaître ou la rejeter d'un coup d'œil.
    """

    ticker: str
    place: str | None = None
    devise: str | None = None
    nom: str | None = None
    """Nom affiché par la source. Aide à reconnaître l'actif, ne sert à aucun calcul
    (règle 4 de CLAUDE.md)."""

    type: TypeActif | None = None
    """Ce que la source dit de la nature de l'actif (ETF, action)."""

    frais_courants: FraisCourantsProposes | None = None

    @property
    def douteuse(self) -> bool:
        """Vrai si la devise proposée n'est pas celle que l'application sait traiter.

        C'est le piège du §4 du comparatif. Une proposition douteuse est écrite en
        commentaire et **pas** en ligne active : elle ne peut pas servir par inadvertance.
        """
        return self.devise is not None and self.devise.strip().upper() != DEVISE_UNIQUE


@dataclass(frozen=True)
class Configuration:
    """Ce que l'utilisateur a déclaré."""

    declarations: Mapping[str, Declaration] = field(default_factory=dict)
    """Actif (ISIN ou code crypto) → où chercher son cours."""

    def declaration(self, actif: str) -> Declaration | None:
        """La déclaration d'un actif, ou `None` s'il n'en a pas encore."""
        return self.declarations.get(actif)

    @property
    def actifs_declares(self) -> frozenset[str]:
        return frozenset(self.declarations)

    def manquants(self, actifs: Iterable[str]) -> list[str]:
        """Les actifs sans déclaration, dans l'ordre alphabétique."""
        return sorted(set(actifs) - self.actifs_declares)


def chemin(environnement: Mapping[str, str] | None = None) -> Path:
    return emplacements.dossier_configuration(environnement) / NOM_FICHIER


def charger(
    fichier: Path | None = None, environnement: Mapping[str, str] | None = None
) -> Configuration:
    """Lit la configuration. Un fichier absent donne une configuration vide, pas une erreur.

    C'est le cas du premier lancement, avant `pastory actifs`. Ce n'est pas à la lecture du
    fichier de protester : ce sont les commandes qui ont besoin des cours qui diront quels
    actifs ne sont pas encore déclarés, et quoi faire.
    """
    fichier = chemin(environnement) if fichier is None else fichier
    if not fichier.exists():
        return Configuration()

    try:
        contenu = tomllib.loads(fichier.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        raise ConfigurationInvalide(
            f"{fichier} n'est pas un fichier TOML valide : {erreur}"
        ) from erreur

    return Configuration(declarations=_lire_declarations(contenu.get("actifs", {}), fichier))


def _lire_declarations(brut: object, fichier: Path) -> dict[str, Declaration]:
    if not isinstance(brut, dict):
        raise ConfigurationInvalide(f"{fichier} : la section [actifs] doit être un tableau")

    declarations: dict[str, Declaration] = {}
    for actif, valeur in brut.items():
        # Une ligne laissée vide est un actif que l'utilisateur n'a pas encore déclaré :
        # travail en cours, pas erreur de fichier. Même règle que pour les comptes.
        if isinstance(valeur, str):
            if valeur.strip() == "":
                continue
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} doit déclarer un ticker et une devise. "
                f"Écrivez  {FORME_ATTENDUE}"
            )

        if not isinstance(valeur, dict):
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} est déclaré d'une façon que je ne comprends "
                f"pas. Écrivez  {FORME_ATTENDUE}"
            )

        ticker = valeur.get("ticker")
        if not isinstance(ticker, str):
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} n'a pas de « ticker ». Écrivez  {FORME_ATTENDUE}"
            )
        if ticker.strip() == "":
            continue

        declarations[actif] = Declaration(
            ticker=ticker.strip(),
            devise=_lire_devise(valeur.get("devise"), actif, fichier),
            type=_lire_type(valeur.get("type"), actif, fichier),
            ter_pour_cent=_lire_taux(
                valeur.get("ter_pour_cent"), "ter_pour_cent", TER_MINIMUM, TER_MAXIMUM,
                actif, fichier,
            ),
            spread_pour_cent=_lire_taux(
                valeur.get("spread_pour_cent"), "spread_pour_cent", Decimal("0"),
                SPREAD_MAXIMUM, actif, fichier,
            ),
            contenu=_lire_contenu(valeur.get("contenu"), actif, fichier),
            pays=_lire_repartition(valeur.get("pays"), "pays", actif, fichier),
            secteurs=_lire_repartition(valeur.get("secteurs"), "secteurs", actif, fichier),
            secours=_lire_secours(valeur.get("secours"), actif, fichier),
        )
    return declarations


def _lire_contenu(valeur: object, actif: str, fichier: Path) -> ContenuActif | None:
    """Le contenu, facultatif : absent, c'est la source qui décide (D-71)."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in CONTENUS_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « contenu » que je ne connais pas : {valeur!r}. "
            f"Contenus acceptés : {', '.join(CONTENUS_ACCEPTES)}. Le contenu dit de quoi l'actif "
            f"est fait à l'intérieur ; le « type », lui, dit ce que vous détenez (etf, action, "
            f"crypto)."
        )
    return ContenuActif(valeur.strip().lower())


def _lire_secours(valeur: object, actif: str, fichier: Path) -> str | None:
    """La source de secours, facultative. Une valeur inconnue est refusée, pas ignorée."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in SECOURS_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} demande une source de secours que je ne connais pas : "
            f"{valeur!r}. Sources acceptées : {', '.join(SECOURS_ACCEPTES)}."
        )
    return valeur.strip().lower()


def _lire_repartition(
    valeur: object, champ: str, actif: str, fichier: Path
) -> dict[str, Decimal] | None:
    """Une répartition déclarée à la main, facultative, qui l'emporte sur la source (D-70).

    Trois refus, et chacun protège d'un chiffre faux et crédible :

    - un poids qui n'est pas un nombre, ou négatif ;
    - un total au-delà de `TOTAL_MAXIMAL` : c'est presque toujours une ligne oubliée en double,
      ou des fractions écrites pour des pourcentages ;
    - un total nul, qui ferait disparaître l'actif des totaux sans le dire.

    Un total **inférieur** à 100 est en revanche accepté tel quel : le reste devient du « non
    attribué », exactement comme pour une source (D-69). On ne complète jamais à 100.
    """
    if valeur is None:
        return None
    if not isinstance(valeur, dict) or not valeur:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » que je ne comprends pas. "
            f"Écrivez  {FORME_REPARTITION}"
        )

    repartition: dict[str, Decimal] = {}
    for code, poids in valeur.items():
        if isinstance(poids, bool) or not isinstance(poids, int | float):
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} déclare {champ}.{code} = {poids!r}, qui n'est pas "
                f"un nombre. Écrivez un pourcentage, par exemple  {code} = 12.5"
            )
        part = Decimal(str(poids))
        if part < 0:
            raise ConfigurationInvalide(
                f"{fichier} : l'actif {actif} déclare {champ}.{code} = {poids}, un poids négatif."
            )
        repartition[str(code).strip()] = part

    total = sum(repartition.values(), Decimal("0"))
    if total <= 0:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » dont le total est nul. L'actif "
            f"disparaîtrait de la répartition sans que rien ne le dise. Retirez la ligne plutôt."
        )
    if total > TOTAL_MAXIMAL:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare un « {champ} » dont le total fait {total} %, "
            f"au-delà de {TOTAL_MAXIMAL} %. C'est presque toujours une ligne comptée deux fois, "
            f"ou des fractions écrites pour des pourcentages (0.72 au lieu de 72)."
        )
    return repartition


def _lire_devise(valeur: object, actif: str, fichier: Path) -> str:
    """La devise attendue, exigée explicitement (D-48).

    Elle n'est pas devinée : sans elle, un cours en dollars passerait pour des euros. Et elle
    ne peut être que l'euro tant que l'application ne traite qu'une devise (D-26) — déclarer
    autre chose, c'est presque toujours avoir retenu la mauvaise place de cotation.
    """
    if not isinstance(valeur, str) or valeur.strip() == "":
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} n'a pas de « devise ». Elle n'est pas devinée : "
            f"sans elle, un cours dans une autre monnaie passerait pour des euros. "
            f"Écrivez  {FORME_ATTENDUE}"
        )

    devise = valeur.strip().upper()
    if devise != DEVISE_UNIQUE:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} est déclaré en {devise}, or l'application ne traite "
            f"que l'euro (D-26) et ne convertit rien. Retenez la cotation en {DEVISE_UNIQUE} "
            f"de cet actif — un même titre cote souvent sur plusieurs places, dans plusieurs "
            f"monnaies."
        )
    return devise


def _lire_type(valeur: object, actif: str, fichier: Path) -> TypeActif | None:
    """Le type, facultatif : absent ou vide, l'actif n'aura pas de spread estimé."""
    if valeur is None or (isinstance(valeur, str) and valeur.strip() == ""):
        return None
    if not isinstance(valeur, str) or valeur.strip().lower() not in TYPES_ACCEPTES:
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « type » que je ne connais pas : {valeur!r}. "
            f"Types acceptés : {', '.join(TYPES_ACCEPTES)}."
        )
    return TypeActif(valeur.strip().lower())


def _lire_taux(
    valeur: object,
    champ: str,
    minimum: Decimal,
    maximum: Decimal,
    actif: str,
    fichier: Path,
) -> Decimal | None:
    """Un taux en pour cent, facultatif, et refusé hors de sa fourchette de vraisemblance.

    Écrit par un humain, un taux se trompe d'unité plus souvent que de valeur : 0.002 pour
    0,20 %, ou 20 pour 0,20 %. Les deux donneraient des frais absurdes sans rien dire.
    """
    if valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, int | float):
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} a un « {champ} » qui n'est pas un nombre : "
            f"{valeur!r}. Écrivez par exemple  {champ} = 0.20  pour 0,20 %."
        )
    taux = Decimal(str(valeur))
    if not (minimum <= taux <= maximum) or (champ == "spread_pour_cent" and taux <= 0):
        raise ConfigurationInvalide(
            f"{fichier} : l'actif {actif} déclare {champ} = {valeur}, hors de la fourchette "
            f"attendue ({minimum} à {maximum} pour cent). C'est presque toujours une erreur "
            f"d'unité : 0,20 % s'écrit  {champ} = 0.20"
        )
    return taux


def modele(
    apercu: Mapping[str, str],
    propositions: Mapping[str, Proposition],
    configuration: Configuration,
) -> str:
    """Le texte du fichier à écrire : un actif par ligne, à valider.

    `apercu` donne, par actif, de quoi le reconnaître (son nom tel que la banque l'affiche,
    ses poches). `propositions` donne ce qu'une source a trouvé pour les actifs pas encore
    déclarés — ou, pour un actif déjà déclaré, ce qu'elle propose de compléter (un type, un
    TER), écrit en commentaire au-dessus de sa ligne.

    **Tout ce que l'utilisateur avait déjà écrit est repris**, y compris ses actifs absents de
    cet export-ci : l'assistant réécrit le fichier entier, et n'en recopier qu'une partie
    effacerait le reste en silence. C'est la leçon de `comptes.py`.
    """
    deja_declares = configuration.declarations
    lignes = [
        "# De l'ISIN au ticker : où chercher le cours de chaque actif, en quelle monnaie,",
        "# et ce que l'actif coûte.",
        "#",
        "# Votre banque identifie un actif par son ISIN ; les sources de cours travaillent au",
        "# ticker, place de cotation comprise. Un même titre cote sur plusieurs places, dans",
        "# plusieurs monnaies : c'est à vous de dire laquelle fait référence.",
        "#",
        f"# Forme d'une ligne :  {FORME_COMPLETE}",
        "#   ticker : l'identifiant chez la source, suffixe de place compris",
        "#            (« .DE » Xetra, « .PA » Euronext Paris, « -EUR » pour une crypto)",
        f"#   devise : la monnaie attendue. Seul « {DEVISE_UNIQUE} » est accepté : un cours",
        "#            reçu dans une autre monnaie est refusé, jamais converti.",
        f"#   type   : {', '.join(TYPES_ACCEPTES)}. Choisit le spread estimé par défaut ;",
        "#            sans type, aucun spread n'est estimé pour cet actif.",
        "#   ter_pour_cent : les frais courants annuels d'un ETF, en pour cent (0.20 pour",
        "#            0,20 %). Proposés depuis la liste Xetra, parfois en retard sur une",
        "#            baisse de frais : vérifiez sur la fiche de l'émetteur. Sans TER, aucun",
        "#            frais courant n'est estimé.",
        "#   spread_pour_cent : facultatif, un taux par côté propre à cet actif (ETF de niche,",
        "#            petite capitalisation, altcoin), qui remplace celui de son type.",
        "#",
        f"#   contenu : facultatif — {', '.join(CONTENUS_ACCEPTES)}. Dit de quoi l'actif est",
        "#            fait à l'intérieur, là où « type » dit ce que vous détenez. Un ETF",
        "#            d'obligations ou de matières premières n'a ni pays ni secteur : le",
        "#            déclarer ici le range à sa place, au lieu de l'annoncer « composition",
        "#            inconnue ». Sans contenu, c'est la source qui décide.",
        f"#   secours : facultatif — {', '.join(SECOURS_ACCEPTES)}. La source de secours à",
        "#            interroger si la source principale ne sait pas ouvrir ce fonds. Utile",
        "#            surtout pour un ETF « PEA » à swap, que la source principale ne",
        "#            transparise pas toujours. « amundi » ne sert que la répartition par",
        "#            PAYS : ses secteurs suivent une autre nomenclature, et resteraient",
        "#            faux mélangés aux autres. À ne mettre que sur un fonds Amundi.",
        "#   pays, secteurs : facultatifs, pour corriger une composition que la source donne",
        f"#            fausse ou ne donne pas :  {FORME_REPARTITION}",
        "#            Ce que vous écrivez l'emporte sur la source. Les totaux n'ont pas besoin",
        "#            de faire 100 : le reste devient du « non attribué », jamais comblé.",
        "#",
        "# Un actif laissé vide n'est pas valorisé — il est signalé, jamais estimé.",
        "# Ce fichier reste sur votre machine : il n'entre jamais dans git.",
        "",
        "[actifs]",
    ]

    for actif in sorted(set(apercu) | set(propositions) | set(deja_declares)):
        description = _commentaire(apercu.get(actif, ""))
        if description:
            lignes.append(f"# {description}")

        declaration = deja_declares.get(actif)
        proposition = propositions.get(actif)
        if declaration is not None:
            lignes.extend(_complements_proposes(declaration, proposition))
            lignes.append(_ligne(actif, declaration))
        else:
            lignes.extend(_lignes_a_valider(actif, proposition))
        lignes.append("")

    return "\n".join(lignes)


def _texte_toml(valeur: str) -> str:
    """Échappe une valeur écrite dans une chaîne TOML.

    Un ticker ou un nom d'actif vient d'ailleurs — de la banque, ou d'une source de cours. Un
    guillemet ou un retour à la ligne suffirait à rendre `actifs.toml` illisible, et c'est
    précisément l'assistant censé le réparer qui refuserait alors de démarrer.
    """
    propre = valeur.replace("\\", "\\\\").replace('"', '\\"')
    return "".join(caractere for caractere in propre if caractere.isprintable())


def _commentaire(texte: str) -> str:
    """Une ligne de commentaire : tout tient sur une ligne, sinon le reste cesse d'être un
    commentaire et devient du TOML invalide."""
    return " ".join(texte.split())


def _taux_toml(taux: Decimal) -> str:
    """Un taux écrit en TOML : un nombre à point décimal, sans zéros inutiles."""
    return format(taux.normalize(), "f") if taux != taux.to_integral() else str(int(taux))


def _ligne(actif: str, declaration: Declaration) -> str:
    champs = [
        f'ticker = "{_texte_toml(declaration.ticker)}"',
        f'devise = "{_texte_toml(declaration.devise)}"',
    ]
    if declaration.type is not None:
        champs.append(f'type = "{declaration.type.value}"')
    if declaration.ter_pour_cent is not None:
        champs.append(f"ter_pour_cent = {_taux_toml(declaration.ter_pour_cent)}")
    if declaration.spread_pour_cent is not None:
        champs.append(f"spread_pour_cent = {_taux_toml(declaration.spread_pour_cent)}")
    return f'"{_texte_toml(actif)}" = {{ {", ".join(champs)} }}'


def _commentaire_frais_courants(frais: FraisCourantsProposes) -> str:
    details = ", ".join(
        partie
        for partie in (
            frais.nom,
            frais.politique,
            f"au {frais.date.isoformat()}" if frais.date else None,
            frais.source,
        )
        if partie
    )
    return _commentaire(
        f"TER proposé : {_taux_toml(frais.ter_pour_cent)} % ({details}). À vérifier sur la "
        "fiche de l'émetteur : la liste est parfois en retard sur une baisse de frais."
    )


def _complements_proposes(
    declaration: Declaration, proposition: Proposition | None
) -> list[str]:
    """Pour un actif déjà déclaré : ce que la source propose d'ajouter, en commentaire.

    La déclaration prime toujours ; un type ou un TER que l'utilisateur a déjà écrit n'est
    jamais contredit par une proposition. Ce qui manque encore est proposé au-dessus de la
    ligne, pour qu'il n'ait qu'à le recopier.
    """
    if proposition is None:
        return []
    lignes = []
    if declaration.type is None and proposition.type is not None:
        lignes.append(f'# type proposé par la source :  type = "{proposition.type.value}"')
    if (
        declaration.ter_pour_cent is None
        and proposition.frais_courants is not None
        and (declaration.type in (None, TypeActif.ETF))
    ):
        lignes.append(f"# {_commentaire_frais_courants(proposition.frais_courants)}")
    return lignes


def _lignes_a_valider(actif: str, proposition: Proposition | None) -> list[str]:
    """La ligne d'un actif pas encore déclaré, avec ce que la source en dit.

    **Sans ticker, pas de ligne active.** Une source peut connaître les frais courants d'un
    actif sans qu'aucune n'ait trouvé son ticker : la ligne serait alors écrite avec un ticker
    vide, d'apparence valide, et la lecture l'écarterait en silence — l'utilisateur ne verrait
    ni l'avertissement « à compléter », ni l'actif dans ses cours. Le TER proposé reste écrit
    en commentaire, pour qu'il n'ait qu'à le recopier.
    """
    if proposition is None:
        return [
            "# aucune correspondance proposée : à compléter à la main",
            f'"{actif}" = ""',
        ]

    if not proposition.ticker.strip():
        lignes = []
        if proposition.frais_courants is not None:
            lignes.append(f"# {_commentaire_frais_courants(proposition.frais_courants)}")
        lignes += [
            "# aucun ticker proposé : à compléter à la main",
            f'"{actif}" = ""',
        ]
        return lignes

    trouve = _commentaire(
        ", ".join(
            partie
            for partie in (
                proposition.nom,
                proposition.place,
                proposition.devise,
                proposition.type.value if proposition.type else None,
            )
            if partie
        )
    )
    lignes = [f"# proposé par la source : {trouve}" if trouve else "# proposé par la source"]
    if proposition.frais_courants is not None:
        lignes.append(f"# {_commentaire_frais_courants(proposition.frais_courants)}")

    proposee = Declaration(
        ticker=proposition.ticker,
        devise=proposition.devise or "",
        type=proposition.type,
        ter_pour_cent=(
            proposition.frais_courants.ter_pour_cent if proposition.frais_courants else None
        ),
    )

    if proposition.douteuse:
        # Écrite en commentaire, donc inactive : une cotation dans une autre monnaie ne doit
        # pas pouvoir servir par simple inattention (D-48).
        lignes += [
            f"# ATTENTION : cette cotation est en {_commentaire(proposition.devise or '')}, "
            f"pas en {DEVISE_UNIQUE}. Ce n'est probablement pas la bonne place.",
            f"#   {_ligne(actif, proposee)}",
            f'"{actif}" = ""',
        ]
        return lignes

    lignes.append(
        _ligne(
            actif,
            Declaration(
                ticker=proposee.ticker,
                devise=DEVISE_UNIQUE,
                type=proposee.type,
                ter_pour_cent=proposee.ter_pour_cent,
            ),
        )
    )
    return lignes
