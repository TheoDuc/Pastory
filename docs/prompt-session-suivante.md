# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-26**, fin de l'étape 4.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 5 : la valorisation et les rendements.
```

---

## Où en est le projet

- **Étapes 0 à 4 terminées.** L'application lit un export Trade Republic, en sort des opérations
  au format pivot, va chercher les **cours de marché**, et en déduit **quantité détenue, capital
  net investi, prix de revient, frais, taxes, dividendes et plus-values réalisées**. Elle peut
  aussi comparer ses quantités avec ce que la banque dit détenir.
- **Prochaine : étape 5**, la valorisation et les rendements — la valeur des actifs aujourd'hui et
  dans le temps, puis le **gain en €**, le **TRI** et le **TWRR** (D-22).
- Deux questions ouvertes : **Q-21** (présentation des frais), qui attend l'étape 8, et
  **Q-26** (rapprocher le PEA, voir plus bas), qui n'est pas bloquante.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat**, en deux parties : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | **Comment c'est construit** : les couches, leurs frontières, le trajet d'un chiffre |
| `dashboard_tr/pivot/` | `Operation`, `PositionReelle`, les contrôles de cohérence et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/donnees_externes/` | `cours.py` (le contrat), `cache.py`, `yahoo.py`, `completion.py` |
| `dashboard_tr/moteur/` | `position.py` (le rejeu), `portefeuille.py`, `rapprochement.py`, `export_csv.py`, `rapport.py` |
| `dashboard_tr/tableur.py` | Les conventions d'écriture des nombres, communes à tous les CSV |
| `dashboard_tr/cli.py` | 10 commandes ; `ouvrir` arrive à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-51. L'étape 4 a ajouté D-48 à D-51 |
| [sources-de-cours.md](sources-de-cours.md) | Le comparatif des sources de cours, et les pièges vérifiés |
| [verification/etape-4.md](verification/etape-4.md) | Le cahier de vérification des cours |
| [scripts/diagnostic_comptes_titres.py](../scripts/diagnostic_comptes_titres.py) | Diagnostic structurel pour Q-26. **Jamais lancé pour l'instant** |

**Ce qui n'existe pas encore :** les rendements, les coûts estimés (TER, spread), la
diversification, l'interface.

---

## Ce que l'étape 5 doit savoir de l'étape 4

- **Un cours se demande en une ligne.** `FournisseurDeCours.cours(actif, date)` rend un `Cours` ou
  `None`. Il ne lève jamais d'exception sur un cours manquant : il accumule des `Refus` avec leur
  motif, que l'appelant affiche. Le construire se fait par `cli._fournisseur_de_cours()`, **le seul
  endroit de l'application qui nomme Yahoo**.
- **Un `Cours` porte sa propre date**, qui peut être **antérieure** à celle demandée : un samedi
  prend le cours du vendredi (jusqu'à dix jours de recul, au-delà c'est un refus). Rien n'est
  interpolé. La valorisation devra donc afficher *quel jour* elle a utilisé, comme le fait déjà le
  bloc « Cours de marché » du rapport.
- **Le cache est déjà rempli jour par jour** depuis la première opération de chaque actif, moins
  trente jours. `dashboard cours` le complète, et un cours écrit n'est jamais redemandé
  ([D-50](decisions.md)). Une valorisation sur toute la durée de détention ne demandera donc aucun
  appel réseau supplémentaire.
- **`Portefeuille.au(date)` existe depuis l'étape 3** : l'état à n'importe quel jour passé s'obtient
  en coupant le journal, sans rien rejouer. Avec le cache, la valeur du portefeuille jour par jour
  est à portée.
- **Le moteur ne connaît pas les cours, et cela doit rester vrai.** Les prix manquants sont
  complétés **avant** lui, dans `donnees_externes/completion.py`, qui transforme du pivot en pivot
  ([architecture.md §5.7](architecture.md)). Si l'étape 5 a besoin d'un cours dans `moteur/`, la
  bonne façon est de **lui passer les cours en paramètre** — pas d'importer `donnees_externes`
  depuis le moteur, ce qui casserait [D-26](decisions.md).
- **Trois pièges de la source sont déjà neutralisés**, et il ne faut pas les réintroduire :
  1. `adjclose` n'est **jamais** lu — il réinjecte les dividendes, que le moteur compte déjà
     ([D-29](decisions.md)). L'erreur est **invisible sur un ETF capitalisant** ;
  2. la **devise** annoncée est confrontée à celle déclarée ([D-48](decisions.md)) ; un cours dans
     une autre monnaie est refusé, jamais converti ;
  3. une plage nommée (`range=max`) renvoie du **mensuel** en annonçant du quotidien : les périodes
     sont toujours bornées par dates explicites.
- **Le cache ne contient jamais le jour même**, et c'est volontaire : la séance en cours n'a pas de
  cours de clôture, et le cache étant définitif, l'y écrire figerait un prix intermédiaire pour
  toujours. La source s'arrête à la dernière séance close. **L'étape 5 devra donc prévoir un chemin
  à part** pour valoriser « aujourd'hui » — un cours du jour qu'on affiche sans l'enregistrer.
- **Ce qui n'est pas valorisé est dit, jamais estimé** ([D-45](decisions.md)). Un actif sans
  correspondance ISIN → ticker, ou sans cours, doit ressortir comme **non valorisé** dans les
  totaux de l'étape 5 — un zéro silencieux ferait un gain faux.
- **Le rapprochement ne couvre pas le PEA** ([D-47](decisions.md)), et ce n'est pas un défaut du
  moteur : `pytr` ne demande les positions que d'**un seul** compte-titres, et Trade Republic loge
  le PEA dans un second. **Conséquence pour la suite : sur le PEA, aucune seconde source ne
  confirme les quantités.** Q-26 reste ouverte, et le
  [diagnostic](../scripts/diagnostic_comptes_titres.py) écrit pour la trancher **n'a pas encore été
  lancé** — le proposer au propriétaire quand l'occasion se présente, il ne prend qu'une minute et
  n'affiche aucune valeur personnelle.

**Ce que le propriétaire a vérifié à l'étape 3 (2026-09-21) :** il a lancé le moteur sur ses données
et **confirme que les chiffres sont bons**. Un seul écart, expliqué et corrigé depuis : tous ses
actifs de PEA ressortaient « absent de la banque » au rapprochement, ce qui a donné D-47 et Q-26.

**Ce que le propriétaire a vérifié à l'étape 4 (2026-09-26) :** il a confronté les cours du cache à
son application, sur plusieurs actifs. Les écarts sont **de l'ordre du demi-pour-cent**, et il les
accepte : Trade Republic a sa propre source. C'est le contrôle B.2 du cahier, et il valide ce qu'il
devait valider — la correspondance ISIN → ticker est juste, car une mauvaise ligne de cotation
donnerait un écart de plusieurs pour cent, ou un facteur.

**Conséquence pour l'étape 5, et il faut l'assumer dès la conception :** la valeur du portefeuille
affichée par cette application **ne tombera pas** sur celle de l'application Trade Republic. Un
demi-pour-cent d'écart sur chaque cours se retrouvera sur le total, et donc sur le gain. Ce n'est
pas un défaut ([D-48](decisions.md)), mais c'est le premier chiffre que le propriétaire comparera :
l'interface doit **dire** d'où viennent les cours et à quelle date, sans quoi il croira à une
erreur de calcul.

**Ce qu'il n'a pas pu vérifier, et c'est à garder en tête :** son portefeuille est **jeune**. Peu de
ventes, peu de dividendes, pas de distribution de capital, aucun recul dans le temps. Les règles les
plus délicates du moteur — vente partielle au prorata, plus-values réalisées — sont donc validées
par les cas fictifs du cahier, **pas par ses données**. Cela vaut aussi pour l'étape 5 : un TRI et
un TWRR sur un portefeuille de quelques mois ne diront pas grand-chose, et les cas fictifs
refaisables dans un tableur seront la seule vraie preuve. Les étapes suivantes ne doivent pas
prendre « vérifié sur les vraies données » pour acquis au-delà de ce qui l'a réellement été.

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu
  de certificats par défaut ne le reconnaît pas. `uv sync --native-tls`.
- **L'antivirus peut couper Claude Code en pleine session.** Le 2026-09-26, **Avast WebShield** a
  bloqué `api.anthropic.com` en annonçant un contenu « malveillant » — un faux positif de son
  inspection HTTPS, même mécanisme que le point précédent. Conséquences en chaîne, à reconnaître
  du premier coup d'œil :
  1. une erreur **403 « blocked by Avast WebShield »** apparaît ;
  2. les agents de recherche en cours meurent tous en même temps, laissant le tour de conversation
     **incomplet** ;
  3. chaque relance renvoie alors cet état invalide et répond **400 Bad Request**, indéfiniment.
     Se reconnecter ne sert à rien : **il faut ouvrir une nouvelle session.** Le travail déjà
     écrit sur le disque est intact, et les résultats des recherches restent récupérables dans les
     journaux de la session (`~/.claude/projects/<projet>/<session>/subagents/`).

  **Prévention :** ajouter `api.anthropic.com` aux exclusions d'Avast (*Menu → Paramètres →
  Protection → Web Shield*). Et pour toute recherche en ligne longue : écrire les trouvailles dans
  un fichier au fur et à mesure, plutôt que de les garder dans la conversation.
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
- **Utiliser pytr comme bibliothèque réserve deux pièges**, tous deux rencontrés en écrivant le
  diagnostic des comptes-titres. La commande `pytr` ne les a pas, parce qu'elle règle ces deux
  points elle-même :
  1. `pytr.account.login()` a pour défaut `waf_token="playwright"`, qui exige un navigateur à
     installer à part. Message obtenu : « playwright is not installed ». La ligne de commande,
     elle, passe `"default"`, qui se résout à **aucun jeton** dès lors qu'on est en `v2`. Il faut
     donc écrire `login(v2=True, waf_token="default")` ;
  2. `login()` se termine par `log.debug(get_settings(tr))` — **le JSON complet du compte**, nom
     et numéros compris. Il ne s'imprime pas aujourd'hui, le journal s'installant au niveau
     « info » par défaut, mais c'est un défaut de bibliothèque tierce. Tout script qui promet de
     n'afficher aucune valeur doit poser un **filtre** sur le logger `account`, comme le fait
     `museler_le_journal_de_pytr()` : pytr remet son niveau à `DEBUG` et réinstalle ses
     gestionnaires à chaque appel, mais ne touche jamais aux filtres déjà posés.
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
