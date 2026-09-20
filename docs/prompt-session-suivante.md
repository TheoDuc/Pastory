# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-21**, fin de l'étape 3.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 4 : les cours de marché.
```

---

## Où en est le projet

- **Étapes 0 à 3 terminées.** L'application lit un export Trade Republic, en sort des opérations
  au format pivot, et en déduit **quantité détenue, capital net investi, prix de revient, frais,
  taxes, dividendes et plus-values réalisées**. Elle peut aussi comparer ses quantités avec ce
  que la banque dit détenir.
- **Prochaine : étape 4**, les cours de marché. C'est ce qui débloque le reste : la valeur des
  actifs, puis le gain, le TRI et le TWRR (étape 5).
- Deux questions ouvertes : **Q-21** (présentation des frais), qui attend l'étape 8, et
  **Q-26** (rapprocher le PEA, voir plus bas), qui n'est pas bloquante.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat**, en deux parties : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| `dashboard_tr/pivot/` | `Operation`, `PositionReelle`, les contrôles de cohérence et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/moteur/` | `position.py` (le rejeu), `portefeuille.py`, `rapprochement.py`, `export_csv.py`, `rapport.py` |
| `dashboard_tr/tableur.py` | Les conventions d'écriture des nombres, communes à tous les CSV |
| `dashboard_tr/cli.py` | 7 commandes ; `ouvrir` arrive à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-47. L'étape 3 a ajouté D-44 à D-47 |
| [verification/etape-3.md](verification/etape-3.md) | Le cahier de vérification du moteur |
| [scripts/diagnostic_comptes_titres.py](../scripts/diagnostic_comptes_titres.py) | Diagnostic structurel pour Q-26. **Jamais lancé pour l'instant** |

**Ce qui n'existe pas encore :** les cours, les rendements, l'interface.

---

## Ce que l'étape 4 doit savoir de l'étape 3

- **Le moteur est prêt à recevoir des cours.** Il ne leur demande qu'une chose :
  `cours(actif, date)`. La date à utiliser est `Operation.date`, déjà en heure de Paris (D-36).
- **`Portefeuille.au(date)` donne l'état à n'importe quel jour passé**, en coupant le journal.
  C'est le mécanisme sur lequel la valorisation dans le temps s'appuiera à l'étape 5 : rien à
  rejouer.
- **Deux endroits attendent les cours, et un seul est bloquant :**
  1. **les titres reçus sans prix** (D-15) : leur `montant_brut` est `a_completer`. Dès qu'un
     cours du jour d'apparition existe, le capital investi de l'actif cesse d'être sous-estimé
     et son prix de revient redevient un nombre (D-45). **C'est la première chose à brancher** ;
  2. la valeur de marché des positions, qui est l'objet de l'étape 5.
- **Un actif est identifié par son ISIN** — ou par un code commençant par `XF` pour la crypto
  (D-16). La correspondance ISIN → ticker est le point délicat de l'étape 4, annoncé dans la
  feuille de route.
- **La clé d'une position est le couple (actif, poche)**, pas l'actif seul (D-44) : un même ETF
  peut être en PEA et en CTO. Un cours, lui, ne dépend que de l'actif.
- **Le moteur ne lit que le pivot** (D-26). Une source de cours doit donc passer par une
  interface propre, comme les banques : `dashboard_tr/donnees_externes/` l'attend, vide.
- **Le prix de revient est arrêté à six décimales** (D-44) : c'est un résultat de division, et
  `prix de revient × quantité` peut s'écarter du capital de quelques centièmes de centime. **Le
  capital investi fait foi.**
- **Le rapprochement ne couvre pas le PEA** (D-47), et ce n'est pas un défaut du moteur : `pytr`
  ne demande les positions que d'**un seul** compte-titres, et Trade Republic loge le PEA dans un
  second. Une poche entièrement absente de la photo est signalée **une fois** et ses actifs
  sortent en « hors périmètre », sans alerte. **Conséquence pour la suite : sur le PEA, aucune
  seconde source ne confirme les quantités.** Q-26 reste ouverte, et le
  [diagnostic](../scripts/diagnostic_comptes_titres.py) écrit pour la trancher **n'a pas encore
  été lancé** — le proposer au propriétaire quand l'occasion se présente, il ne prend qu'une
  minute et n'affiche aucune valeur personnelle.

**Ce que le propriétaire a vérifié à l'étape 3 (2026-09-21) :** il a lancé le moteur sur ses
données et **confirme que les chiffres sont bons**. Un seul écart, expliqué et corrigé depuis :
tous ses actifs de PEA ressortaient « absent de la banque » au rapprochement, ce qui a donné
D-47 et Q-26.

**Ce qu'il n'a pas pu vérifier, et c'est à garder en tête :** son portefeuille est **jeune**. Peu
de ventes, peu de dividendes, pas de distribution de capital, aucun recul dans le temps. Les
règles les plus délicates du moteur — vente partielle au prorata, plus-values réalisées — sont
donc validées par les cas fictifs du cahier, **pas par ses données**. Les étapes suivantes ne
doivent pas prendre « vérifié sur les vraies données » pour acquis au-delà de ce qui l'a
réellement été. C'est aussi pour cela que le rapprochement compte : c'est le seul contrôle qui
ne dépende pas de ce que le portefeuille contient.

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu
  de certificats par défaut ne le reconnaît pas. `uv sync --native-tls`.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- **La console Windows écrit en cp1252** : elle ne sait afficher ni les traits de tableau, ni les
  coches, ni les flèches. Un rapport qui en contiendrait ferait échouer la commande **au moment
  de l'afficher**, alors que le calcul, lui, s'est bien passé. Le CLI force la sortie en UTF-8
  par précaution, et **deux tests** vérifient que les rapports restent affichables en cp1252 —
  celui de la lecture et celui du moteur. En ajouter un pour tout nouveau rapport.
- **La saisie du PIN n'affiche rien du tout.** Sous Windows, `getpass` lit les caractères
  directement depuis la console (`msvcrt.getwch`) : ni chiffres, ni étoiles, ni curseur qui
  avance. Le propriétaire a cru à un blocage la première fois. `rafraichir` et
  `positions-reelles` le préviennent maintenant en toutes lettres.
  **Corollaire :** `msvcrt` exige une **vraie console Windows**. Dans Git Bash (MinTTY), la
  saisie ne fonctionne pas et la commande reste bloquée. Il faut les lancer depuis PowerShell,
  `cmd` ou le terminal intégré de VS Code — pas depuis Git Bash.
- **Chaque appel à pytr est une connexion complète** : comme rien n'est enregistré (D-41), le
  numéro, le PIN et la confirmation dans l'application sont redemandés à chaque fois. C'est
  pourquoi `positions-reelles` est une commande à part et non un morceau de `rafraichir` (D-46).
  À garder en tête si l'étape 4 envisage d'appeler pytr pour des cours.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run dashboard emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run dashboard lire --export <dossier>` (idem pour `positions`).
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
