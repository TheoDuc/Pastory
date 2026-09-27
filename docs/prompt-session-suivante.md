# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-27**, fin de l'étape 5.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 6 : les frais, les taxes et la valeur réelle.
```

---

## Où en est le projet

- **Étapes 0 à 5 terminées.** L'application lit un export Trade Republic, en sort des opérations
  au format pivot, va chercher les **cours de marché**, en déduit **quantité détenue, capital net
  investi, prix de revient, frais, taxes, dividendes et plus-values réalisées**, puis **la valeur
  des actifs** et les **trois chiffres clés** — gain en €, TRI, TWRR (D-22) — par actif, par
  poche et au total, sur une période choisie. Elle peut aussi comparer ses quantités avec ce que
  la banque dit détenir.
- **Prochaine : étape 6**, les frais, les taxes et la valeur réelle — les coûts **estimés**
  (spread, TER, D-17), les règles fiscales par poche, et la valeur « si on retirait tout » (D-23).
  Elle commence par un **agent de recherche** (TER, spreads, fiscalité française), comme l'étape 4.
- Deux questions ouvertes : **Q-21** (présentation des frais), qui attend l'étape 8, et
  **Q-26** (rapprocher le PEA), qui n'est pas bloquante.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat**, en deux parties : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | **Comment c'est construit** : les couches, leurs frontières, le trajet d'un chiffre |
| [glossaire.md](glossaire.md) | Chaque formule, dont celles du gain, du TRI et du TWRR (§4 et §5) telles que le code les applique |
| `dashboard_tr/pivot/` | `Operation`, `PositionReelle`, les contrôles de cohérence et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/donnees_externes/` | `cours.py` (le contrat), `cache.py`, `yahoo.py`, `completion.py` |
| `dashboard_tr/moteur/` | `position.py` (le rejeu), `portefeuille.py`, `valorisation.py`, `rendements.py`, `rapprochement.py`, `export_csv.py` (six CSV), `rapport.py` |
| `dashboard_tr/tableur.py` | Les conventions d'écriture des nombres, communes à tous les CSV |
| `dashboard_tr/cli.py` | 10 commandes, options `--au` et `--depuis` ; `ouvrir` arrive à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-54. L'étape 5 a ajouté D-52 à D-54 |
| [verification/etape-5.md](verification/etape-5.md) | Le cahier de vérification des rendements, avec la démarche `TRI.PAIEMENTS` |
| [scripts/diagnostic_comptes_titres.py](../scripts/diagnostic_comptes_titres.py) | Diagnostic structurel pour Q-26. **Jamais lancé pour l'instant** |

**Ce qui n'existe pas encore :** les coûts estimés (TER, spread), la fiscalité et la valeur
réelle, la diversification, l'interface.

---

## Ce que l'étape 6 doit savoir de l'étape 5

- **La valeur brute d'une position existe et se demande en une ligne** :
  `valorisation.valoriser(portefeuille, date, source)` rend une `Valorisation` avec, par position,
  la quantité, le cours retenu (et sa date), la valeur et la plus-value latente. C'est le point de
  départ de la **valeur réelle** (D-23) : valeur brute − frais de vente estimés − spread estimé −
  impôt estimé. Ne pas recalculer la valeur ailleurs.
- **Les coûts payés sont déjà rangés par moment** (`Position.couts_par_moment()` : frais et taxes
  d'achat, de vente, sur revenus) et le rapport les affiche dans le bloc « Coûts réellement
  payés ». Les coûts **estimés** doivent vivre à côté, jamais mélangés (D-17, D-21) : la
  `Provenance.ESTIMATION` du pivot est réservée à ça, et n'a encore jamais servi.
- **Le moteur reçoit les cours par un protocole qu'il déclare** (`SourceDeValorisation`, dans
  `moteur/valorisation.py`) et **n'importe toujours pas `donnees_externes/`**. Si l'étape 6 a
  besoin d'une donnée externe dans le moteur (un TER, un taux de spread, un taux d'impôt), la bonne
  façon est la même : déclarer la forme attendue dans le moteur, la fournir depuis `cli.py`. Pas
  d'import en sens inverse (D-26).
- **Les paramètres datés et sourcés** (taux fiscaux, spreads par défaut) sont prévus en fichiers
  lisibles, mis à jour sans toucher au code (architecture-notes §6). Le TOML de `config/` est le
  modèle. Chaque taux doit porter sa **date** et sa **source officielle**.
- **Un seul `FournisseurDeCours` par commande**, construit par `cli._fournisseur_de_cours()`, sert
  à la complétion des prix et à la valorisation. Ses refus couvrent les deux et sont listés dans
  le bloc « Cours de marché ». Une troisième utilisation doit passer par le même objet.
- **La valeur d'« aujourd'hui » est celle de la dernière clôture** (D-52) : le cache ne contient
  jamais le jour même, et rien de la séance en cours n'est affiché. L'interface (étape 9) pourra
  reposer la question ; l'étape 6 n'a pas à y toucher.
- **Ce qui n'a pas de cours sort des totaux, marqués partiels** (D-53). Toute vue « valeur
  réelle » doit hériter de ce comportement : un actif non valorisé n'a pas de valeur réelle, et le
  total le dit.
- **Le TWRR est calculé aux cours de clôture**, pas aux prix d'exécution (D-54, glossaire §5).
  C'est un choix écrit, né d'un cas fictif où la formule littérale donnait −100 % sur un actif
  gagnant. Ne pas « corriger » en revenant à `V_avant + F`.
- **La formule du gain compte les distributions de capital** (D-54). Le glossaire d'origine les
  omettait ; le pivot les comptait déjà. Un test vérifie l'identité gain = latente + réalisée +
  dividendes.
- **Six CSV sortent d'`exporter-positions`.** `flux.csv` est la table de `TRI.PAIEMENTS`,
  `sous_periodes_twrr.csv` celle du TWRR, `evolution.csv` la valeur jour par jour. Un nouveau
  fichier suit les conventions de `tableur.py` et jamais une case vide pour une valeur absente
  (`VALEUR_SANS_OBJET` / `VALEUR_A_COMPLETER`).
- **Tout nouveau bloc de rapport a son test cp1252** (trois existent : lecture, moteur, cours ; le
  moteur en a un de plus pour la synthèse).

**Ce que le propriétaire a vérifié à l'étape 5 (2026-09-27) :** il a comparé la valeur totale de
ses actifs à celle de son application Trade Republic. L'écart est de **moins de deux dixièmes de
pour cent**, réparti sur les poches, et il l'accepte : c'est l'écart de place et de source annoncé
par [D-48](decisions.md). Son essai a révélé un piège d'usage, pas de calcul : **une crypto n'a pas
d'ISIN**, Trade Republic l'identifie par un code interne `XF…` qu'aucune source ne connaît, donc
`dashboard actifs` ne peut rien proposer et sa ligne reste vide — la poche crypto sortait des
totaux. Il a rempli la ligne à la main (`BTC-EUR`), et l'assistant le dit désormais en toutes
lettres pour toute crypto. Il a aussi trouvé un défaut d'affichage, corrigé : une poche
entièrement non valorisée montrait « 0,00 » d'achats au lieu de « - ».

**Sa question, et la réponse à garder en tête :** « si je vends tout, l'écart entre le cours Yahoo
et le prix de Trade Republic va-t-il laisser quelques centimes ? » Non : le moteur ne travaille
que sur les **quantités** et sur les **montants réels** des opérations. Une vente totale ramène la
quantité à zéro exactement, le capital à zéro sans reliquat, et la plus-value réalisée part du
montant brut réellement encaissé. Le cours de la source ne sert qu'à valoriser ce qui est **encore
détenu** : zéro part, zéro valeur, aucun cours demandé. Le seul risque de reliquat vient d'une
quantité mal lue dans un texte, et c'est le rapprochement avec la banque qui le verrait.

**Ce qu'il n'a pas pu vérifier, et c'est à garder en tête :** son portefeuille est **jeune**. TRI
et TWRR y sont exacts et **peu significatifs**, et le rapport le dit. Les règles délicates de
l'étape — période commençant en cours de route, distribution de capital comme flux, tout vendre
puis racheter — ne sont prouvées que par les cas fictifs du cahier, dont chacun est un test. Les
étapes suivantes ne doivent pas prendre « vérifié sur les vraies données » pour acquis au-delà de
ce qui l'a réellement été.

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu
  de certificats par défaut ne le reconnaît pas. `uv sync --native-tls`, `uv run --native-tls …`.
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
- **L'éditeur applique une limite de 88 caractères, le projet en fixe 100** (`pyproject.toml`).
  Les diagnostics E501 de l'IDE sous 100 caractères ne sont pas des erreurs du projet :
  `uv run ruff check .` fait foi.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- **La console Windows écrit en cp1252** : elle ne sait afficher ni les traits de tableau, ni les
  coches, ni les flèches. Un rapport qui en contiendrait ferait échouer la commande **au moment
  de l'afficher**, alors que le calcul, lui, s'est bien passé. Le CLI force la sortie en UTF-8
  par précaution, et des tests vérifient que les rapports restent affichables en cp1252. En
  ajouter un pour tout nouveau rapport.
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
