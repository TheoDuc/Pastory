"""Les mots que l'utilisateur lit sans les avoir choisis (conception-interface §2).

Chaque explication tient dans une bulle « ? », jamais dans le corps du texte, et elle est écrite
pour quelqu'un qui découvre l'application (règle 10 de CLAUDE.md). Les textes sont ceux de la
maquette, mot pour mot : ils ont passé neuf relectures du propriétaire.

Le seul balisage admis est `<b>…</b>` (un mot appuyé) et `<br>` (un saut de paragraphe) ;
`riche()` en fait des composants. Rien d'autre n'est interprété : un texte ne peut pas injecter
de HTML dans la page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dash import html


@dataclass(frozen=True)
class Aide:
    titre: str
    texte: str


AIDES: dict[str, Aide] = {
    "gain": Aide(
        "Le gain",
        "Ce que vos actifs ont rapporté sur la période : <b>leur valeur d'aujourd'hui, moins "
        "leur valeur au départ, plus tout ce qui est entré et sorti entre-temps</b>. Les frais "
        "et les taxes n'y sont pas : ils sont traités dans l'onglet « Frais et taxes ». Le "
        "calcul complet est dans l'onglet « Détail des calculs ».",
    ),
    "tri": Aide(
        "TRI — le rendement de votre argent",
        "Le taux annuel qui, appliqué à chacun de vos versements <b>à sa date</b>, aboutirait "
        "à la valeur actuelle. Il récompense le bon moment : verser avant une hausse le fait "
        "monter. C'est le rendement de votre argent, pas celui de vos choix d'actifs.",
    ),
    "twrr": Aide(
        "TWRR — le rendement de la stratégie",
        "Le même calcul, mais <b>en neutralisant les dates de vos versements</b>. C'est ce "
        "qu'aurait gagné un euro resté investi du début à la fin : le rendement de vos choix "
        "d'actifs, comparable à celui d'un indice.",
    ),
    "peuSignificatif": Aide(
        "Pourquoi ce taux est peu fiable",
        "<b>La période examinée est trop courte pour se fier à ce taux.</b> Sur moins d'un an, "
        "un rendement <b>annualisé</b> s'emballe : quelques semaines de hausse, ramenées à "
        "l'année, donnent un pourcentage énorme qui ne décrit rien de durable. Le gain en "
        "euros, lui, reste lisible dès le premier jour.",
    ),
    "valeur": Aide(
        "La valeur des actifs",
        "La quantité détenue multipliée par le <b>dernier cours de clôture connu</b>, actif par "
        "actif. Les cours sont bruts : jamais retraités des dividendes. Aucun prix de séance en "
        "cours.",
    ),
    "capital": Aide(
        "Le capital net investi",
        "Ce que vous avez <b>réellement placé</b> : vos achats, moins les frais et taxes "
        "prélevés dessus. Si vous versez 201 € avec 1 € de frais, 200 € entrent. À chaque "
        "vente, il diminue au prorata de la part vendue.",
    ),
    "partiel": Aide(
        "Pourquoi « partiel »",
        "Ce total ne porte que sur les actifs dont nous connaissons le cours. Ceux qui manquent "
        "sont <b>nommés</b>, jamais comptés pour zéro : un portefeuille dont une ligne n'a pas "
        "de prix n'est pas un portefeuille plus petit.",
    ),
    "variation": Aide(
        "La variation d'un actif",
        "La performance de <b>l'actif lui-même</b> sur la période, indépendamment de vos "
        "versements. Un actif acheté en cours de période est marqué « depuis l'achat » : sa "
        "variation ne commence pas avant qu'il existe dans votre portefeuille.",
    ),
    "synthetique": Aide(
        "ETF synthétique",
        "Ce fonds <b>ne détient pas</b> les titres de son indice : il reproduit sa performance "
        "par un contrat d'échange. Nous affichons donc la composition de <b>l'indice suivi</b>, "
        "c'est-à-dire ce à quoi votre argent est réellement exposé. Si vous ouvrez la fiche de "
        "l'émetteur, vous y verrez une liste de titres très différente — souvent des sociétés "
        "européennes pour un fonds mondial.",
    ),
    "nonCouvert": Aide(
        "Non couvert",
        "Nous n'avons pas la composition de cet actif : la source ne publie rien pour lui, ou ce "
        "qu'elle publie n'a pas passé nos contrôles. Son montant est affiché <b>à part et à sa "
        "vraie taille</b>, jamais réparti au hasard sur les autres postes. Certains fonds en "
        "contiennent d'autres : leur composition ne peut pas être lue, et ils sont comptés ici.",
    ),
    "nonAttribue": Aide(
        "Non attribué",
        "La part d'un fonds que sa propre documentation n'attribue à aucun pays ni secteur : "
        "liquidités, produits dérivés, lignes non classées. <b>Aucun fonds ne somme exactement "
        "à 100 %.</b>",
    ),
    "horsActions": Aide(
        "Hors actions",
        "Cette part n'est pas investie en actions. Elle compte dans la répartition par classe "
        "d'actifs, mais <b>pas</b> dans les pays ni les secteurs, où ces notions n'ont pas le "
        "même sens. Elle est détaillée classe par classe, pour ne pas faire passer de l'or pour "
        "de la dette.",
    ),
    "numeriques": Aide(
        "Actifs numériques",
        "Une crypto n'a <b>ni pays ni secteur</b> : ce n'est pas un oubli de notre part. Elle "
        "compte dans la répartition par classe d'actifs, et nulle part ailleurs.",
    ),
    "regleDePays": Aide(
        "Plusieurs règles de pays cohabitent",
        "« De quel pays est cette société ? » a plusieurs réponses justes. Pour un fonds, nous "
        "retenons le pays où la société <b>exerce son activité</b> ; pour une action que vous "
        "détenez en direct, son <b>siège social</b> ; pour un fonds lu chez son émetteur, le "
        "pays que retient <b>son indice</b>. C'est pourquoi la règle est indiquée sur chaque "
        "ligne. Un émetteur écrit lui-même que son exposition géographique se rapporte "
        "« principalement » au domicile de l'émetteur, « mais, dans certains cas », au lieu de "
        "son activité.",
    ),
    "secteurs": Aide(
        "Secteurs Morningstar",
        "Les secteurs suivent la nomenclature <b>Morningstar</b>, en 11 postes. Il en existe "
        "d'autres, qui ne découpent pas au même endroit : elles ne s'additionnent pas, donc nous "
        "n'en mélangeons jamais deux dans un même graphique.",
    ),
    "zones": Aide(
        "Les zones",
        "Le regroupement des pays en zones est une <b>convention</b>, pas une donnée : la liste "
        "est un fichier daté et sourcé. Il n'existe aucune norme officielle du « développé » et "
        "de l'« émergent », et les deux grands fournisseurs sont en désaccord sur plusieurs "
        "pays.<br>La petite carte <b>situe</b> la zone, elle ne la délimite pas : elle allume "
        "des continents entiers, là où une zone ne suit pas leurs contours. Ce sont les montants "
        "et les parts de la liste qui font foi.",
    ),
    "pasCent": Aide(
        "Pourquoi le total ne fait pas 100 %",
        "C'est <b>voulu</b>. Ce qui n'a pas pu être attribué reste visible, à sa vraie taille. "
        "Ramener le graphique à 100 % ferait disparaître exactement l'information qui manque — "
        "et c'est celle-là qu'il faut voir.",
    ),
    "arrete": Aide(
        "Arrêté au",
        "Les fonds ne publient pas leur composition en temps réel : chacun l'arrête à une date, "
        "et ces dates <b>diffèrent d'un fonds à l'autre</b>. La fourchette indiquée est celle "
        "de vos fonds.",
    ),
    "estime": Aide(
        "Estimé",
        "Ce montant n'a <b>pas été payé</b> : il est calculé à partir d'un taux publié, avec sa "
        "date et sa source. Il ne se mélange jamais aux frais réellement prélevés sur votre "
        "compte.",
    ),
    "spread": Aide(
        "Le spread",
        "L'écart entre le prix d'achat et le prix de vente d'un actif à un instant donné. Vous "
        "le payez <b>deux fois</b> : à l'entrée et à la sortie, sans qu'il apparaisse jamais sur "
        "un relevé. Le taux affiché est la moyenne de vos actifs, pondérée par ce qu'ils pèsent "
        "— c'est lui qui se compare à un taux publié, là où le montant en euros dépend de la "
        "taille de votre portefeuille.",
    ),
    "ter": Aide(
        "Les frais courants (TER)",
        "Les frais annuels d'un fonds, prélevés en continu sur sa valeur. Vous ne les voyez "
        "jamais passer : ils sont déjà dans le cours. Le montant affiché est une <b>estimation "
        "à un an</b>, sur la valeur d'aujourd'hui.",
    ),
    "valeurReelle": Aide(
        "La valeur réelle",
        "Ce que vous récupéreriez <b>si vous vendiez tout aujourd'hui</b> : la valeur des "
        "actifs, moins les frais de vente, le spread de sortie et l'impôt estimé selon la poche. "
        "C'est une estimation, pas une déclaration.",
    ),
    "baseImposable": Aide(
        "La base imposable",
        "Les plus-values <b>latentes</b> seulement, compensées entre elles, avec un plancher à "
        "zéro. Les plus-values déjà réalisées cette année et les dividendes déjà reçus n'y sont "
        "pas. Les frais et le spread de sortie viennent en déduction.",
    ),
    "minoree": Aide(
        "Estimation minorée",
        "Volontairement <b>prudente</b> : une partie de l'impôt ne peut pas être calculée "
        "depuis les seuls titres, elle est donc laissée de côté. Le montant réellement dû serait "
        "plus élevé, donc la valeur réelle un peu plus basse.",
    ),
    "coutsPreleves": Aide(
        "Ce qui a déjà été prélevé",
        "Ces montants sont <b>réels</b> : ils ont été retirés de votre compte, et ils figurent "
        "sur vos relevés. Les deux blocs suivants, eux, sont des <b>estimations</b> — c'est ce "
        "qui sépare ce niveau des autres.",
    ),
    "retenueDividendes": Aide(
        "Pourquoi la retenue sur dividendes est ici",
        "Elle n'est pas prélevée à l'achat : elle l'est <b>à chaque versement de dividende</b>, "
        "donc pendant que vous détenez l'actif. Elle figure quand même dans ce bloc, parce que "
        "les trois blocs ne suivent pas le calendrier : ils séparent ce qui a <b>déjà été "
        "payé</b>, et qui figure sur vos relevés, de ce qui est seulement <b>estimé</b>.",
    ),
    "contenuDeclare": Aide(
        "Contenu déclaré",
        "Vous avez indiqué vous-même de quoi cet actif est fait. Il compte à 100 % dans sa "
        "classe, et il <b>sort</b> des pays et des secteurs — là où ces notions ne veulent rien "
        "dire pour lui.",
    ),
    # --- Ajoutées à l'étape 9 ------------------------------------------------------------
    "codeNonReconnu": Aide(
        "Code non reconnu",
        "La source a renvoyé un code que nos référentiels ne nomment pas. Le montant est "
        "<b>conservé et affiché tel quel</b>, sous son code, plutôt que d'être fondu dans "
        "« autres ».",
    ),
    "declareeALaMain": Aide(
        "Déclarée à la main",
        "La composition de cet actif a été <b>saisie, pas récupérée</b> : elle ne porte donc "
        "pas de date d'arrêté officielle, et ne se met pas à jour toute seule.",
    ),
    "histoireIncomplete": Aide(
        "Histoire incomplète",
        "Il manque des opérations avant celles que nous avons lues : la <b>quantité</b> est "
        "juste, mais le prix de revient et le gain de cette ligne ne le sont pas forcément. "
        "C'est souvent un export qui ne remonte pas à l'ouverture du compte, ou des titres "
        "reçus d'un type que l'application ne sait pas encore lire. La ligne en cause est "
        "dans « à surveiller ».",
    ),
    "periodeCouverte": Aide(
        "La période couverte",
        "Vous choisissez les dates de l'export dans l'application Trade Republic. Si elles ne "
        "remontent pas à l'<b>ouverture du compte</b>, des achats anciens manquent : les "
        "quantités peuvent rester justes, mais le prix de revient et le gain ne le sont plus. "
        "Rien dans le fichier ne permet de le savoir — c'est pourquoi la période est toujours "
        "affichée. Choisissez « toutes les transactions ».",
    ),
    "typeInconnu": Aide(
        "Type inconnu",
        "Cet événement a un type que l'application ne connaît pas. Il n'est <b>ni ignoré ni "
        "rangé au hasard</b> : il est affiché tel quel pour que vous puissiez le signaler. Tant "
        "qu'il est là, il peut manquer des parts à vos actifs.",
    ),
}

_BALISE = re.compile(r"(<b>.*?</b>|<br>)")


def riche(texte: str) -> list:
    """`<b>mot</b>` et `<br>` deviennent des composants ; tout le reste reste du texte."""
    morceaux: list = []
    for morceau in _BALISE.split(texte):
        if not morceau:
            continue
        if morceau == "<br>":
            morceaux.append(html.Br())
            morceaux.append(html.Br())
        elif morceau.startswith("<b>"):
            morceaux.append(html.B(morceau[3:-4]))
        else:
            morceaux.append(morceau)
    return morceaux
