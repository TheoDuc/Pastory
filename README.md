# DashBoard Trade Republic

Tableau de bord **local** et **gratuit** pour suivre les actifs d'un portefeuille Trade Republic
(PEA, CTO, crypto), destiné aux investisseurs long terme. Les données ne quittent jamais la
machine.

> **Projet en construction.** Étape 1 sur 12 : les choix techniques et le format des données sont
> figés, l'application n'affiche encore rien. L'avancement est suivi dans
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
| [docs/inventaire-donnees.md](docs/inventaire-donnees.md) | Ce que contiennent les exports pytr |

## Vie privée

Aucune donnée réelle n'entre dans ce dépôt : exports, identifiants et résultats de vérification
sont exclus par le `.gitignore` et rangés hors du projet. La documentation n'utilise que des
valeurs fictives.
