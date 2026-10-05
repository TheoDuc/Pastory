# Pastory

Tableau de bord **local** et **gratuit** pour suivre les actifs d'un portefeuille Trade Republic
(PEA, CTO, crypto), destiné aux investisseurs long terme. Les données ne quittent jamais la
machine.

> **Projet en construction.** Étape 8 ter sur 12 : l'application lit l'export officiel des
> transactions de Trade Republic,
> va chercher les cours de marché, et en tire par actif la quantité détenue, le capital investi,
> le prix de revient, la valeur, le gain, le TRI et le TWRR — puis ce que tout cela **coûte**
> (frais et taxes payés, spread et frais courants estimés), ce qu'on récupérerait en **vendant
> tout** impôt estimé compris, et **où est l'argent** (classes d'actifs, pays, secteurs).
>
> Tout cela s'utilise aujourd'hui **en ligne de commande**, et les réglages se font en éditant un
> fichier. Il lui manque donc l'essentiel pour qui ne code pas : une **interface**, et des
> **écrans de réglages** ([D-78](docs/decisions.md)) — c'est l'étape 9. L'avancement est suivi
> dans [docs/feuille-de-route.md](docs/feuille-de-route.md), et le guide d'installation complet
> viendra à l'étape 10.

## Installation, pour l'instant

Le projet utilise [uv](https://docs.astral.sh/uv/) ([D-32](docs/decisions.md)).

```bash
uv sync                  # installe Python et les dépendances
uv run pytest            # vérifie que tout fonctionne
uv run pastory --help    # liste les commandes disponibles
```

`uv run pastory emplacements` indique où l'application range les fichiers personnels
(exports, cache, configuration), en dehors du dossier du projet.

## Lire ses données

**Vous ne faites qu'une chose** : télécharger l'export de vos transactions et le déposer dans le
dossier `exports` de Pastory ([D-80](docs/decisions.md)).

1. Dans l'application Trade Republic : **Profil → Relevés → Export des transactions**. Choisissez
   **toutes les transactions**, puis *Créer*. Vous obtenez un fichier
   `Exportation de transactions.csv`.
2. Déposez-le dans le dossier `exports` que donne `uv run pastory emplacements` (il est créé à la
   première commande). Vous pouvez y laisser plusieurs exports : ils sont lus ensemble, et une
   opération présente dans deux fichiers n'est comptée qu'une fois.

```bash
uv run pastory lire             # le rapport de lecture, sans rien écrire
uv run pastory exporter-pivot   # les opérations en CSV, à ouvrir dans un tableur
```

Aucune connexion, aucun identifiant : c'est un fichier fourni par la banque elle-même
([D-79](docs/decisions.md)). La poche de chaque opération (PEA, CTO, crypto) y est écrite : rien à
déclarer.

Le **rapport de lecture** affiche tout ce qui n'a pas été compris, et ce que le fichier ne dit
pas :

- **les types d'opération non traités.** Trade Republic ne publie aucune liste de ses types : un
  type jamais vu sur un vrai fichier n'est jamais rangé par défaut, il est affiché
  ([D-08](docs/decisions.md)). Ce que l'on en sait est dans
  [export-officiel.md](docs/export-officiel.md) ;
- **la période couverte.** Un export qui ne remonte pas à l'ouverture du compte donne une histoire
  incomplète, et rien dans le fichier ne le dit : vérifiez que le premier jour affiché est bien
  celui de votre première opération ;
- **une limite des dividendes.** Pour certains pays (vérifié : Pays-Bas), Trade Republic donne le
  dividende déjà diminué de la retenue à la source étrangère, sans la montrer : le montant net
  est juste, le brut et les taxes sont un peu sous-estimés ([D-84](docs/decisions.md)).

Les lignes d'espèces (paiements, virements) ne sont que **comptées par type** : leurs montants,
commerçants et IBAN ne sont jamais lus ni recopiés.

Pour examiner un export rangé ailleurs — celui de quelqu'un d'autre, par exemple — sans le
copier dans le projet : `uv run pastory lire --export <dossier>`. Avec `--export`, `actifs`
n'enregistre rien et ne lance aucune recherche.

## Les cours de marché

```bash
uv run pastory actifs   # une seule fois : où chercher le cours de chaque actif
uv run pastory cours    # récupère les cours et les garde en cache
```

Votre banque identifie un actif par son **ISIN** ; les sources de cours travaillent au **ticker**,
place de cotation comprise — et un même titre cote souvent sur plusieurs places, dans plusieurs
monnaies. `actifs` **propose** une correspondance, **vous la validez** dans un fichier lisible. Un
actif que vous laissez vide n'est pas valorisé : il est signalé, jamais estimé.

Le même fichier porte, depuis l'étape 6, le **type** de chaque actif (ETF, action, crypto) et les
**frais courants** d'un ETF (TER). Les deux sont proposés — le type par la source de cours, le TER
par la liste publique des ETF de Xetra — et **relus par vous** : cette liste est parfois en retard
sur une baisse de frais, et les ETF français de type « PEA » n'y figurent pas
([D-61](docs/decisions.md)). Sans type, aucun écart de prix n'est estimé pour cet actif ; sans
TER, aucun frais courant.

La devise attendue est déclarée à côté du ticker. Un cours qui arrive dans une autre monnaie est
**refusé, jamais converti** ([D-48](docs/decisions.md)) : c'est ce qui empêche des dollars d'être
comptés comme des euros.

Un cours enregistré est **définitif** ([D-50](docs/decisions.md)) : le chiffre vu hier est celui
que vous revoyez aujourd'hui, et l'application s'ouvre sans réseau. Pour reprendre un actif à la
source — une correction, un regroupement d'actions —, `uv run pastory oublier-cours --actif
<ISIN>`.

D'où viennent ces cours et pourquoi cette source : [sources-de-cours.md](docs/sources-de-cours.md).

## Voir ses positions

```bash
uv run pastory positions           # quantités, capital investi, prix de revient,
                                     # valeur des actifs, gain, TRI et TWRR,
                                     # coûts payés et estimés, valeur réelle
uv run pastory exporter-positions  # douze CSV pour le tableur, dont le journal et les flux
```

`positions` et `exporter-positions` acceptent `--hors-ligne` : les mêmes chiffres, avec les seuls
cours déjà en cache et aucun appel réseau.

**La valeur des actifs et les trois chiffres clés** ([D-22](docs/decisions.md)) — gain en euros,
TRI, TWRR — sont calculés en montants bruts, frais et taxes à part ([D-21](docs/decisions.md)),
sur une période choisie : `--depuis AAAA-MM-JJ` pour le début (sinon la première opération),
`--au AAAA-MM-JJ` pour la fin (sinon aujourd'hui). La valeur d'aujourd'hui est celle de la
**dernière clôture connue**, et le rapport dit laquelle ([D-52](docs/decisions.md)). Les cours
sont ceux du marché principal en euros, pas ceux de Trade Republic : un écart de quelques
dixièmes de pour cent est normal ([D-48](docs/decisions.md)). Un actif sans cours n'est pas
valorisé et sort des totaux, qui sont alors marqués **partiels** ([D-53](docs/decisions.md)).
Sur moins d'un an, TRI et TWRR sont affichés comme **peu significatifs**.

Pour refaire un taux dans un tableur : `flux.csv` est la table de `TRI.PAIEMENTS`, et
`sous_periodes_twrr.csv` donne chaque morceau du TWRR. La démarche est dans le
[cahier de vérification de l'étape 5](docs/verification/etape-5.md).

Le **journal** (`journal.csv`) est la pièce à ouvrir pour vérifier : une ligne par opération,
avec l'état d'avant et l'état d'après. Sur chaque ligne, *capital avant + ajouté − retiré =
capital après*. C'est ce qui permet de refaire un chiffre à la main, sans lire le code
([D-44](docs/decisions.md)). La démarche complète est dans le
[cahier de vérification de l'étape 3](docs/verification/etape-3.md).

**Là où l'arithmétique n'a plus de sens, l'application se tait et le dit**
([D-45](docs/decisions.md)). Des parts reçues gratuitement reçoivent le cours de leur jour
d'apparition ([D-15](docs/decisions.md)), et le rapport dit lequel, pour que vous puissiez refaire
la multiplication. Mais tant qu'aucun cours n'est disponible — actif non déclaré, ticker inconnu —
les parts sont comptées et le prix de revient de l'actif reste « à compléter » : le calculer quand
même donnerait un chiffre crédible et faux, que rien ne signalerait.

**Comparez les quantités à l'écran de l'application Trade Republic.** L'export ne donne que
l'histoire des opérations : des titres entrés **sans aucune ligne** — un transfert de titres
depuis une autre banque, par exemple — n'y apparaissent pas, et aucun calcul ne peut les deviner.
C'est le contrôle le plus sûr, et le rapport le rappelle ([D-81](docs/decisions.md)).

Les deux premières commandes acceptent `--au AAAA-MM-JJ` pour arrêter les chiffres à une date,
qui devient aussi la date de valorisation.

## Ce que ça coûte, et ce qu'il reste si on vend tout

Trois blocs de plus dans `pastory positions`, tenus **à part** de la performance, qui reste
brute ([D-21](docs/decisions.md)) :

- **les coûts payés**, opération par opération, avec leur **poids** : 1 € de frais sur un achat de
  25 € pèse 4 %. C'est ce qui montre qu'un petit ordre ponctuel coûte cher ;
- **les coûts estimés** ([D-17](docs/decisions.md)) : l'**écart de prix** (spread) payé à chaque
  achat et à chaque vente ([D-30](docs/decisions.md)), et les **frais courants** d'un ETF. Le
  spread n'apparaît sur aucun relevé — il est fondu dans le prix d'exécution — d'où l'estimation,
  par un taux par côté selon le type d'actif ([D-56](docs/decisions.md)) ;
- **la valeur réelle** ([D-23](docs/decisions.md)) : valeur de marché − frais de vente − écart de
  prix − **impôt estimé**, poche par poche. Le PEA selon son ancienneté, le CTO avec ses pertes
  compensées, la crypto avec son seuil d'exonération.

**C'est une estimation, pas une déclaration** ([D-26](docs/decisions.md)). Chaque taux vit dans un
fichier avec sa **date** et sa **source** ([D-58](docs/decisions.md)) : le rapport les cite sous
chaque chiffre, et corriger un taux quand la loi change ne demande aucune ligne de code. Les
hypothèses du calcul sont écrites à l'écran, et ce qui manque est nommé plutôt que compté pour
zéro : un actif sans type, un ETF sans TER, un PEA dont la date de premier versement n'a pas été
déclarée.

L'impôt du PEA a besoin de cette date, parce que cinq ans changent le taux de 31,4 % à 18,6 %.
Écrivez-la dans `fiscalite.toml`, dans votre dossier de configuration :

```toml
[pea]
premier_versement = 2024-03-15
```

D'où viennent les taux, les spreads et le TER, et ce qu'ils valent :
[couts-et-fiscalite.md](docs/couts-et-fiscalite.md). Comment les vérifier vous-même :
[cahier de l'étape 6](docs/verification/etape-6.md).

## Comment c'est construit

```
export d'une banque ──► adaptateur ──► format pivot ──► moteur ──► vues
```

Le moteur ne lit que le **format pivot**, décrit dans
[docs/format-pivot.md](docs/format-pivot.md). Utiliser l'application avec une autre banque ne
demande que d'écrire un nouvel adaptateur ([D-26](docs/decisions.md)).

## Documentation

| Fichier | Contenu |
|---|---|
| [docs/feuille-de-route.md](docs/feuille-de-route.md) | Les étapes du projet et l'étape en cours |
| [docs/architecture.md](docs/architecture.md) | Comment c'est construit, couche par couche |
| [docs/format-pivot.md](docs/format-pivot.md) | Le format des opérations, champ par champ |
| [docs/glossaire.md](docs/glossaire.md) | Chaque notion financière et sa formule |
| [docs/sources-de-cours.md](docs/sources-de-cours.md) | D'où viennent les cours, et pourquoi cette source |
| [docs/couts-et-fiscalite.md](docs/couts-et-fiscalite.md) | D'où viennent les spreads, le TER et les règles fiscales |
| [docs/decisions.md](docs/decisions.md) | Les décisions prises, avec leurs raisons |
| [docs/export-officiel.md](docs/export-officiel.md) | Ce que contient l'export officiel de Trade Republic, et ses pièges |
| [docs/verification/](docs/verification/) | Comment vérifier les chiffres soi-même, étape par étape |

## Vie privée

Aucune donnée réelle n'entre dans ce dépôt : exports, identifiants et résultats de vérification
sont exclus par le `.gitignore` et rangés hors du projet. La documentation n'utilise que des
valeurs fictives.
