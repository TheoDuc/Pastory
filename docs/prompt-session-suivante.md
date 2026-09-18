# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-18**, fin de l'étape 2.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 3 : le moteur de positions.
```

---

## Où en est le projet

- **Étapes 0, 1 et 2 terminées.** L'application **lit** un export Trade Republic et en sort des
  opérations au format pivot. Elle ne calcule encore **aucune** performance.
- **Prochaine : étape 3**, le moteur — quantité détenue, capital net investi, PRU, frais, taxes,
  dividendes, plus-values réalisées. Le moteur ne lit **que** le format pivot (D-26).
- Une seule question ouverte : **Q-21** (présentation des frais), qui attend l'étape 8.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat.** Le moteur ne lit rien d'autre que ces lignes |
| `dashboard_tr/pivot/` | `Operation`, ses contrôles de cohérence, et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/config/` | Emplacements des fichiers personnels, et rôles des comptes |
| `dashboard_tr/cli.py` | `rafraichir`, `comptes`, `lire`, `exporter-pivot` ; `ouvrir` à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-42. L'étape 2 a ajouté D-39 à D-42 |
| [inventaire-donnees.md](inventaire-donnees.md) | Ce que contient un export, **et son §11 : les pièges trouvés en écrivant le code** |
| [verification/etape-2.md](verification/etape-2.md) | Le cahier de vérification de la lecture |

**Ce qui n'existe pas encore :** le moteur, les sources de cours, l'interface.

---

## Ce que l'étape 3 doit savoir de l'étape 2

- **Le pivot est déjà rempli et vérifié.** Sur les deux exports disponibles : 80 opérations,
  **zéro contrôle de cohérence en échec**. Le moteur peut partir de là sans se méfier.
- **Une opération peut être incomplète.** Des actions gratuites entrent sans prix : leur
  `montant_brut` est marqué `a_completer` en attendant les cours (étape 4, D-15). Le moteur doit
  **compter les parts** — elles sont bien détenues — mais ne mettre leur montant dans aucun
  total. La propriété `Operation.complete` le dit.
- **Le brut d'un dividende n'est pas ce qui arrive sur le compte** : c'est `net + taxe`. C'est
  déjà fait par l'adaptateur ; le moteur lit `montant_brut` et n'a rien à recalculer (D-29).
- **`nature_source` est informative.** Le moteur ne calcule jamais dessus (format-pivot §2).
- **La tolérance des contrôles a changé** (D-39) : elle tient compte de l'arrondi de la quantité
  *et* de celui du prix, lus sur les valeurs elles-mêmes. Utile si le moteur ajoute ses propres
  contrôles.
- **Le rapprochement avec les positions réelles** (portefeuille actuel via pytr) reste à faire :
  c'est ce qui révélera les titres entrés sans aucun événement, limite connue de D-15. Le seul
  événement inconnu des deux exports en est justement un cas possible (Q-10).

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu
  de certificats par défaut ne le reconnaît pas. `uv sync --native-tls`.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- **La console Windows écrit en cp1252** : elle ne sait afficher ni les traits de tableau, ni les
  coches, ni les flèches. Un rapport qui en contiendrait ferait échouer la commande **au moment
  de l'afficher**, alors que le calcul, lui, s'est bien passé. Le CLI force la sortie en UTF-8
  par précaution, et un test vérifie que le rapport reste affichable en cp1252.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run dashboard emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run dashboard lire --export <dossier>`.
- Le propriétaire **ne code pas** : il vérifie les chiffres. Tout calcul doit être refaisable à
  la main, et les options techniques lui sont présentées avec leurs avantages et inconvénients.

---

## Comment mettre à jour ce fichier

À la fin d'une étape, avant la fusion dans `main` :

1. remplacer **le message à copier** par celui de l'étape suivante ;
2. mettre à jour **où en est le projet** : ce qui vient d'être ajouté, ce qui reste à faire, les
   questions encore ouvertes ;
3. écrire **ce que l'étape suivante doit savoir** : les pièges rencontrés, et ce sur quoi elle
   peut s'appuyer sans se méfier ;
4. compléter **à savoir pour travailler sur cette machine** si un piège nouveau est apparu ;
5. changer la date de la dernière mise à jour.

Ce fichier reste **court** : il oriente, il ne duplique pas la documentation. Et comme tout le
dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)).
