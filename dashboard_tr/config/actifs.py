"""« Déclarer ses actifs » : de l'ISIN au ticker, et la devise attendue (D-48, D-51).

Trade Republic identifie un actif par son **ISIN** ; les sources de cours gratuites, elles,
travaillent au **ticker** et à la place de cotation. Personne ne peut établir cette
correspondance à notre place de façon sûre : un même ETF cote sur des dizaines de places, et
la recherche automatique se trompe. Le comparatif en a trouvé un cas franc — pour un ETF qui
cote aussi à Xetra en euros, la recherche renvoie la cotation londonienne **en dollars**
(`docs/sources-de-cours.md` §4).

D'où ce fichier : l'application **propose**, l'utilisateur **valide**, et la devise attendue
est écrite noir sur blanc pour que le cours reçu puisse être confronté à elle (D-48). Un
actif non déclaré n'est pas valorisé : il est signalé, jamais estimé (D-45).

Le fichier vit dans le dossier personnel, hors du dossier synchronisé et hors de git
(D-37, D-01).
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dashboard_tr.config import ConfigurationInvalide, emplacements
from dashboard_tr.pivot.operation import DEVISE_UNIQUE

NOM_FICHIER = "actifs.toml"

FORME_ATTENDUE = '"<ISIN>" = { ticker = "AAAA.DE", devise = "EUR" }'
"""Ce qu'il faut écrire, cité tel quel dans les messages d'erreur."""


@dataclass(frozen=True)
class Declaration:
    """Ce que l'utilisateur déclare pour un actif : où chercher son cours, et en quoi."""

    ticker: str
    """Identifiant de l'actif chez la source, place comprise (« AAAA.DE », « BBB-EUR »)."""

    devise: str = DEVISE_UNIQUE
    """Devise **attendue**. Un cours qui arrive dans une autre est refusé, pas converti."""


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

    C'est le cas du premier lancement, avant `dashboard actifs`. Ce n'est pas à la lecture du
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
        )
    return declarations


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


def modele(
    apercu: Mapping[str, str],
    propositions: Mapping[str, Proposition],
    configuration: Configuration,
) -> str:
    """Le texte du fichier à écrire : un actif par ligne, à valider.

    `apercu` donne, par actif, de quoi le reconnaître (son nom tel que la banque l'affiche,
    ses poches). `propositions` donne ce qu'une source a trouvé pour les actifs pas encore
    déclarés.

    **Tout ce que l'utilisateur avait déjà écrit est repris**, y compris ses actifs absents de
    cet export-ci : l'assistant réécrit le fichier entier, et n'en recopier qu'une partie
    effacerait le reste en silence. C'est la leçon de `comptes.py`.
    """
    deja_declares = configuration.declarations
    lignes = [
        "# De l'ISIN au ticker : où chercher le cours de chaque actif, et en quelle monnaie.",
        "#",
        "# Votre banque identifie un actif par son ISIN ; les sources de cours travaillent au",
        "# ticker, place de cotation comprise. Un même titre cote sur plusieurs places, dans",
        "# plusieurs monnaies : c'est à vous de dire laquelle fait référence.",
        "#",
        f"# Forme d'une ligne :  {FORME_ATTENDUE}",
        "#   ticker : l'identifiant chez la source, suffixe de place compris",
        "#            (« .DE » Xetra, « .PA » Euronext Paris, « -EUR » pour une crypto)",
        f"#   devise : la monnaie attendue. Seul « {DEVISE_UNIQUE} » est accepté : un cours",
        "#            reçu dans une autre monnaie est refusé, jamais converti.",
        "#",
        "# Un actif laissé vide n'est pas valorisé — il est signalé, jamais estimé.",
        "# Ce fichier reste sur votre machine : il n'entre jamais dans git.",
        "",
        "[actifs]",
    ]

    for actif in sorted(set(apercu) | set(propositions) | set(deja_declares)):
        description = apercu.get(actif, "").strip()
        if description:
            lignes.append(f"# {description}")

        declaration = deja_declares.get(actif)
        if declaration is not None:
            lignes.append(_ligne(actif, declaration))
        else:
            lignes.extend(_lignes_a_valider(actif, propositions.get(actif)))
        lignes.append("")

    return "\n".join(lignes)


def _ligne(actif: str, declaration: Declaration) -> str:
    return f'"{actif}" = {{ ticker = "{declaration.ticker}", devise = "{declaration.devise}" }}'


def _lignes_a_valider(actif: str, proposition: Proposition | None) -> list[str]:
    """La ligne d'un actif pas encore déclaré, avec ce que la source en dit."""
    if proposition is None:
        return [
            "# aucune correspondance proposée : à compléter à la main",
            f'"{actif}" = ""',
        ]

    trouve = ", ".join(
        partie
        for partie in (proposition.nom, proposition.place, proposition.devise)
        if partie
    )
    lignes = [f"# proposé par la source : {trouve}" if trouve else "# proposé par la source"]

    if proposition.douteuse:
        # Écrite en commentaire, donc inactive : une cotation dans une autre monnaie ne doit
        # pas pouvoir servir par simple inattention (D-48).
        lignes += [
            f"# ATTENTION : cette cotation est en {proposition.devise}, pas en "
            f"{DEVISE_UNIQUE}. Ce n'est probablement pas la bonne place.",
            f"#   {_ligne(actif, Declaration(proposition.ticker, proposition.devise or ''))}",
            f'"{actif}" = ""',
        ]
        return lignes

    lignes.append(_ligne(actif, Declaration(proposition.ticker, DEVISE_UNIQUE)))
    return lignes
