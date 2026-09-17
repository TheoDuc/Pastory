# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-17**, fin de l'étape 1.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 2 : la lecture des données.
```

---

## Où en est le projet

- **Étapes 0 et 1 terminées**, fusionnées dans `main` et publiées sur GitHub.
- **Prochaine : étape 2**, l'adaptateur Trade Republic — transformer `all_events.json` en
  opérations au format pivot, sans rien perdre en silence.
- Une seule question ouverte : **Q-21** (présentation des frais), qui attend l'étape 8.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat à respecter.** L'adaptateur ne produit rien d'autre que ces lignes |
| `dashboard_tr/pivot/` | La dataclass `Operation` et ses contrôles de cohérence, testés |
| `dashboard_tr/config/emplacements.py` | Où sont rangés les fichiers personnels (hors OneDrive) |
| `dashboard_tr/cli.py` | `uv run dashboard <commande>` ; `rafraichir` et `exporter-pivot` sont à écrire à l'étape 2 |
| [decisions.md](decisions.md) | D-01 à D-38. Les choix techniques sont D-31 à D-38 |
| [inventaire-donnees.md](inventaire-donnees.md) | Ce que contient un export pytr, type par type, et ses pièges |
| `scripts/export_pytr_a_reprendre.py` | Premier jet de l'appel à pytr, **à corriger** avant réemploi (le PIN y est passé en argument, ce que D-25 interdit) |

**Ce qui n'existe pas encore :** l'adaptateur, le moteur, les sources de cours, l'interface.

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu de
  certificats par défaut ne le reconnaît pas. `uv sync --native-tls`.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run dashboard emplacements`.
- Le propriétaire **ne code pas** : il vérifie les chiffres. Tout calcul doit être refaisable à la
  main, et les options techniques lui sont présentées avec leurs avantages et inconvénients.

---

## Comment mettre à jour ce fichier

À la fin d'une étape, avant la fusion dans `main` :

1. remplacer **le message à copier** par celui de l'étape suivante ;
2. mettre à jour **où en est le projet** : ce qui vient d'être ajouté, ce qui reste à faire, les
   questions encore ouvertes ;
3. compléter **à savoir pour travailler sur cette machine** si un piège nouveau est apparu ;
4. changer la date de la dernière mise à jour.

Ce fichier reste **court** : il oriente, il ne duplique pas la documentation. Et comme tout le
dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)).
