# Pastory

Tableau de bord **local** et **gratuit** pour suivre les actifs d'un portefeuille Trade Republic
(PEA, compte-titres, crypto), destiné aux investisseurs long terme. Vous déposez l'export de vos
transactions ; Pastory en tire ce que valent vos actifs, ce qu'ils ont rapporté, ce qu'ils coûtent,
et où se trouve votre argent. **Vos données ne quittent jamais votre ordinateur.**

Projet indépendant, sans lien avec Trade Republic : il lit le fichier que la banque fournit à ses
clients.

> **Où en est le projet.** Pastory fonctionne de bout en bout et s'ouvre comme un logiciel
> (étape 10 sur 11). Il reste à écrire les écrans de correction, le raccourci pour Mac, et à
> publier le dépôt. Le détail est dans [docs/feuille-de-route.md](docs/feuille-de-route.md).

## Installer Pastory (Windows)

Trois étapes, une seule fois.

1. **Installez `uv`**, l'outil qui installera Python et les bibliothèques dont Pastory a besoin.
   Ouvrez PowerShell (menu Démarrer → tapez « PowerShell »), collez cette ligne, validez :

   ```
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   C'est la méthode officielle ([documentation de uv](https://docs.astral.sh/uv/getting-started/installation/)).
   Fermez ensuite PowerShell : vous n'en aurez plus besoin.

2. **Téléchargez Pastory** (sur GitHub : *Code* → *Download ZIP*) et décompressez le dossier où
   vous voulez le garder — **de préférence hors de OneDrive**, qui gêne l'installation.

3. **Double-cliquez sur `Installer Pastory.cmd`**, dans ce dossier. Il installe l'environnement
   (quelques minutes la première fois), puis crée l'icône **Pastory** sur le bureau et dans le menu
   Démarrer.

Si l'installation échoue, la fenêtre dit pourquoi. Les deux causes rencontrées jusqu'ici : un
**antivirus qui inspecte les connexions sécurisées** (message « invalid peer certificate » :
suspendez son analyse HTTPS le temps de l'installation) et un dossier rangé dans **OneDrive**
(message « Accès refusé »).

Si vous déplacez ou renommez le dossier de Pastory, relancez `Installer Pastory.cmd` : les icônes
pointent sur lui.

**Sur Mac ou Linux**, il n'y a pas encore d'icône : après `uv sync`, Pastory s'ouvre par
`uv run pastory ouvrir`.

## Obtenir l'export de vos transactions

Dans l'application Trade Republic : **Profil → Relevés → Export des transactions**. Choisissez
**toutes les transactions**, depuis l'ouverture du compte, puis *Créer*. Vous obtenez un fichier
`Exportation de transactions.csv`.

Un export qui commence plus tard donne une histoire incomplète, et rien dans le fichier ne le
dit : Pastory affiche la période couverte, vérifiez que son premier jour est bien celui de votre
première opération.

## Ouvrir Pastory

**Double-cliquez sur l'icône Pastory.** Une fenêtre s'ouvre sur la couverture du livre :

1. **déposez-y votre export** (glissez le fichier, ou cliquez pour le choisir). C'est la seule
   chose à faire : les cours, les frais des fonds et leur composition sont trouvés seuls, et chaque
   valeur dit d'où elle vient ;
2. **ouvrez le livre** : synthèse, actifs, diversification, frais et taxes, projections.

La première ouverture interroge les sources de cours et de composition : elle demande Internet et
peut prendre une minute. Ensuite, tout est gardé sur votre ordinateur.

**Fermer la fenêtre arrête Pastory.** Pour un export plus récent, déposez-le de la même façon : il
s'ajoute aux précédents, et une opération présente dans deux fichiers n'est comptée qu'une fois.

Si Pastory ne s'ouvre pas, un message le dit, et le détail est écrit dans le fichier `journal.txt`
de son dossier personnel (`%LOCALAPPDATA%\Pastory` sous Windows).

## Essayer sans son portefeuille : la démonstration

Dans le menu Démarrer, **« Pastory (démonstration) »** ouvre un **portefeuille fictif** : des
opérations inventées, sur des titres réels et courants (des fonds indiciels, deux actions, du
bitcoin), répartis entre un PEA, un compte-titres et la crypto. Pastory le lit comme un vrai
export.

La démonstration a son propre dossier, à part du vôtre : rien ne se mêle. L'écran porte
« Données de démonstration » en permanence, et on ne peut pas y déposer d'export.

## Ce que Pastory montre, et ce qu'il ne fait pas

- **La performance est calculée en montants bruts** : gain en euros, TRI et TWRR. Les frais et les
  taxes sont montrés à part, jamais mélangés.
- **Ce qui est estimé est marqué comme tel** : l'écart de prix à l'achat et à la vente, les frais
  courants des fonds, l'impôt si l'on vendait tout. Chaque taux porte sa date et sa source. C'est
  une estimation, pas une déclaration fiscale.
- **Ce qui n'est pas trouvé de façon fiable est un trou affiché**, jamais une valeur inventée ni
  une question posée.
- **Un type d'opération que Pastory ne connaît pas est affiché**, jamais ignoré : Trade Republic
  ne publie aucune liste de ses types.
- **Les cours sont ceux du marché principal en euros**, à la clôture, pas ceux de Trade Republic :
  un écart de quelques dixièmes de pour cent avec votre application est normal.
- **Les espèces ne sont pas suivies**, et les lignes d'espèces de l'export (paiements, virements)
  ne sont que comptées : leurs montants, commerçants et IBAN ne sont jamais lus.
- **Comparez les quantités à celles de votre application.** Des titres entrés sans aucune ligne
  dans l'export — un transfert depuis une autre banque — n'y apparaissent pas.

## Pour aller plus loin : la ligne de commande

Tout ce que montre la fenêtre existe aussi en texte et en CSV, pour vérifier un chiffre dans un
tableur. Dans un terminal, à la racine du dossier :

```
uv run pastory emplacements        où sont rangés vos fichiers (exports, cache, corrections)
uv run pastory lire                le rapport de lecture de vos exports
uv run pastory actifs              ce que Pastory a trouvé seul pour chaque actif, avec sa source
uv run pastory positions           quantités, valeur, gain, TRI, TWRR, coûts, valeur réelle
uv run pastory exporter-positions  les mêmes chiffres en CSV, dont le journal de chaque opération
uv run pastory ouvrir              la fenêtre, depuis un terminal (--demonstration pour l'exemple)
uv run pastory installer           recréer les icônes (--retirer pour les enlever)
uv run pastory --help              toutes les commandes
```

Une valeur trouvée qui vous semble fausse se corrige dans `actifs.toml` (dossier `configuration`,
voir `pastory emplacements`) : la correction l'emporte. Ce n'est jamais nécessaire pour voir le
reste du portefeuille.

Comment refaire un chiffre à la main : les [cahiers de vérification](docs/verification/), étape
par étape.

## Comment c'est construit

```
export d'une banque ──► adaptateur ──► format pivot ──► moteur ──► vues
```

Le moteur ne lit que le **format pivot**, décrit dans [docs/format-pivot.md](docs/format-pivot.md).
Utiliser Pastory avec une autre banque ne demande que d'écrire un nouvel adaptateur
([D-26](docs/decisions.md)).

| Fichier | Contenu |
|---|---|
| [docs/feuille-de-route.md](docs/feuille-de-route.md) | Les étapes du projet et l'étape en cours |
| [docs/architecture.md](docs/architecture.md) | Comment c'est construit, couche par couche |
| [docs/format-pivot.md](docs/format-pivot.md) | Le format des opérations, champ par champ |
| [docs/glossaire.md](docs/glossaire.md) | Chaque notion financière et sa formule |
| [docs/export-officiel.md](docs/export-officiel.md) | Ce que contient l'export de Trade Republic, et ses pièges |
| [docs/sources-de-cours.md](docs/sources-de-cours.md) | D'où viennent les cours, et pourquoi cette source |
| [docs/couts-et-fiscalite.md](docs/couts-et-fiscalite.md) | D'où viennent les spreads, le TER et les règles fiscales |
| [docs/composition-des-etf.md](docs/composition-des-etf.md) | D'où vient la composition des fonds |
| [docs/decisions.md](docs/decisions.md) | Les décisions prises, avec leurs raisons |
| [docs/verification/](docs/verification/) | Comment vérifier les chiffres soi-même |

## Vie privée

Aucune donnée réelle n'entre dans ce dépôt : exports et résultats de vérification sont exclus par
le `.gitignore` et rangés hors du dossier du projet. La documentation n'utilise que des valeurs
fictives. Pastory n'a besoin d'aucun identifiant : il ne se connecte jamais à votre banque.

Pour chercher un cours ou la composition d'un fonds, Pastory envoie le **code du titre** (son
ISIN) ou son nom à des sources publiques — jamais vos quantités, vos montants ni votre identité.
