# DashBoard Trade Republic

Tableau de bord **local** et **gratuit** pour suivre les actifs d'un portefeuille Trade Republic
(PEA, CTO, crypto), destiné aux investisseurs long terme. Les données ne quittent jamais la
machine.

> **Projet en construction.** Étape 2 sur 12 : l'application sait **lire** un export Trade
> Republic et en sortir la liste des opérations, mais elle ne calcule encore aucune performance
> et n'a pas d'interface. L'avancement est suivi dans
> [docs/feuille-de-route.md](docs/feuille-de-route.md). Le guide d'installation complet viendra à
> l'étape 10.

## Installation, pour l'instant

Le projet utilise [uv](https://docs.astral.sh/uv/) ([D-32](docs/decisions.md)).

```bash
uv sync                  # installe Python et les dépendances
uv run pytest            # vérifie que tout fonctionne
uv run dashboard --help  # liste les commandes disponibles
```

`uv run dashboard emplacements` indique où l'application rangera les fichiers personnels
(exports, cache, configuration), en dehors du dossier du projet.

## Lire ses données

```bash
uv run dashboard rafraichir       # récupère l'export auprès de Trade Republic
uv run dashboard comptes          # une seule fois : à quoi sert chaque compte espèces
uv run dashboard lire             # le rapport de lecture, sans rien écrire
uv run dashboard exporter-pivot   # les opérations en CSV, à ouvrir dans un tableur
```

`rafraichir` ne manipule aucun identifiant : c'est Trade Republic qui demande le numéro et le
PIN, et **rien n'est enregistré** ([D-41](docs/decisions.md)).

> **En tapant le PIN, rien ne s'affiche** — ni les chiffres, ni des étoiles, ni le curseur qui
> avance. C'est normal, la saisie est masquée : tapez le PIN et appuyez sur Entrée.
> Sous Windows, cette saisie a besoin d'une **vraie console** : lancez la commande depuis
> PowerShell, `cmd` ou le terminal de VS Code. Depuis Git Bash, elle resterait bloquée.

`comptes` est nécessaire parce que rien, dans l'export, ne dit à quoi sert un compte espèces —
alors que c'est lui qui détermine la poche d'un achat. L'application ne le devine pas
([D-40](docs/decisions.md)) : elle montre les opérations vues sur chaque compte et vous laisse
les nommer.

Le **rapport de lecture** affiche tout ce qui n'a pas été compris : types d'événements inconnus,
libellés non reconnus, écarts avec le CSV de Trade Republic. Un type inconnu n'est jamais ignoré
([D-08](docs/decisions.md)).

Pour examiner un export rangé ailleurs — celui de quelqu'un d'autre, par exemple — sans le
copier dans le projet : `uv run dashboard lire --export <dossier>`. Avec `--export`, la commande
`comptes` se contente d'**afficher** les comptes trouvés : elle n'enregistre rien, parce que les
comptes d'un autre export ne sont pas les vôtres.

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
| [docs/format-pivot.md](docs/format-pivot.md) | Le format des opérations, champ par champ |
| [docs/glossaire.md](docs/glossaire.md) | Chaque notion financière et sa formule |
| [docs/decisions.md](docs/decisions.md) | Les décisions prises, avec leurs raisons |
| [docs/inventaire-donnees.md](docs/inventaire-donnees.md) | Ce que contiennent les exports pytr, et leurs pièges |
| [docs/verification/](docs/verification/) | Comment vérifier les chiffres soi-même, étape par étape |

## Vie privée

Aucune donnée réelle n'entre dans ce dépôt : exports, identifiants et résultats de vérification
sont exclus par le `.gitignore` et rangés hors du projet. La documentation n'utilise que des
valeurs fictives.
