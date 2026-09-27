# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-28**, fin de l'étape 7.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 8 : la conception de l'interface.
```

---

## Où en est le projet

- **Étapes 0 à 7 terminées.** L'application lit un export Trade Republic, en sort des opérations au
  format pivot, va chercher les **cours de marché**, en déduit **quantité détenue, capital net
  investi, prix de revient, frais, taxes, dividendes et plus-values réalisées**, puis **la valeur
  des actifs** et les **trois chiffres clés** — gain en €, TRI, TWRR (D-22). Elle sait dire **ce que
  tout cela coûte** et **ce qu'on récupérerait en vendant tout** (D-23). Et elle sait désormais dire
  **où est l'argent** : répartition par **classe d'actifs**, par **pays** regroupés en zones, et par
  **secteur**, en regardant à l'intérieur des ETF (D-63 à D-70).
- **Prochaine : étape 8**, la conception de l'interface. **Session dédiée, avec des prototypes
  visuels à comparer avant tout code.** C'est l'étape où l'avis du propriétaire compte le plus.
- **Questions ouvertes** : **Q-26** (rapprocher le PEA), non bloquante ; **Q-21** (présentation des
  frais) et **Q-47** (la source de secours), qui attendent toutes deux l'étape 8.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat**, en deux parties : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | **Comment c'est construit** : les couches, leurs frontières, le trajet d'un chiffre |
| [glossaire.md](glossaire.md) | Chaque formule, dont le gain, le TRI, le TWRR (§4, §5), les coûts et l'impôt (§6), et la **diversification** (§8) |
| [composition-des-etf.md](composition-des-etf.md) | **Comparatif de l'étape 7** : les sources de composition, et les 19 pièges vérifiés |
| `dashboard_tr/pivot/` | `Operation`, `PositionReelle`, les contrôles de cohérence et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/donnees_externes/` | `cours.py`, `cache.py`, `yahoo.py`, `completion.py`, `xetra.py`, puis `composition.py`, `cache_compositions.py`, `extraetf.py`, `actions.py` |
| `dashboard_tr/parametres/` | Les taux datés et sourcés (`fiscalite.toml`, `couts.toml`) et les **référentiels** (`secteurs.toml`, `zones.toml`, `classes_actifs.toml`) |
| `dashboard_tr/moteur/` | `position.py`, `portefeuille.py`, `valorisation.py`, `rendements.py`, `couts.py`, `fiscalite.py`, `valeur_reelle.py`, `diversification.py`, `rapprochement.py`, `export_csv.py` (onze CSV), `rapport.py` |
| `dashboard_tr/cli.py` | 12 commandes, options `--au`, `--depuis`, `--hors-ligne` ; `ouvrir` arrive à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-72. L'étape 7 a ajouté D-62 à D-72 |
| [verification/etape-7.md](verification/etape-7.md) | Le cahier de la diversification |

**Ce qui n'existe pas encore :** l'interface. C'est tout ce qui reste du cœur.

---

## Ce que l'étape 8 doit savoir de l'étape 7

### Le changement de cap, et il vaut pour toute la conception

**[D-62](decisions.md) : les choix de fonctionnalités visent l'utilisateur type de Trade Republic,
pas le portefeuille du propriétaire.** Il compte partager l'application. Jusqu'ici seule
l'*installation* par un tiers était un objectif (étape 10) ; désormais le **contenu** l'est aussi.

Trois conséquences concrètes, déjà écrites dans la [feuille de route](feuille-de-route.md) :

1. **les prototypes se testent sur des cas que le propriétaire ne détient pas** : des actions en
   direct, un ETF obligataire, un actif non couvert, un portefeuille à une seule ligne, un
   portefeuille sans PEA. C'est le premier effet de D-62 : les actions en direct ont été
   implémentées alors qu'il n'en a aucune, parce que l'achat d'actions à l'unité est courant ;
2. **les messages d'absence sont du contenu d'interface**, pas des notes techniques. « non couvert »,
   « non attribué », « non transparisé », « synthétique », « minoré », « à compléter » doivent
   s'expliquer **là où ils s'affichent** ;
3. **deux règles de pays cohabitent** dans la répartition géographique ([D-66](decisions.md)) : la
   conception doit trouver comment le dire sans alourdir l'écran.

**Et un travail de fond qui attend l'étape 8 : la source de secours par actif**
([D-72](decisions.md)). Elle est reportée ici parce qu'elle est d'abord un problème de
**présentation** : deux sources n'ont ni la même nomenclature sectorielle ni la même règle de pays,
donc la source de chaque chiffre doit être **visible ligne par ligne**. C'est elle qui fera
disparaître les fonds « non couverts ».

### Ce sur quoi la conception peut s'appuyer sans se méfier

- **le moteur fournit tout ce qu'il faut afficher, y compris ce qui manque et pourquoi.** Chaque
  refus, chaque estimation et chaque déduction voyage avec son motif en français, prêt à être
  repris tel quel. Rien n'est à recalculer côté vues ;
- **une donnée externe entre dans le moteur par un protocole, jamais par un import.** C'est fait
  **quatre** fois, de la même façon : les cours, les paramètres de coûts, les règles fiscales, et
  désormais les compositions et les référentiels. `cli.py` reste le seul assembleur, et un test le
  prouve. Les vues suivront le même principe : elles n'appellent que le moteur ;
- **onze CSV** couvrent tout ce que le moteur calcule. Ils sont la référence pour vérifier un
  chiffre à la main, et l'interface n'a pas à les remplacer ;
- **le rapport texte a sa limite de largeur (100) et son test cp1252.** Il restera utile après
  l'interface : c'est lui qu'on colle dans une discussion quand un chiffre semble faux.

### Les leçons de l'étape 7, dans l'ordre de leur importance pour l'interface

**1. Une répartition géographique n'est pas une mesure, c'est une convention.** BlackRock l'écrit
dans ses propres fiches : l'exposition géographique se rapporte « principalement » au domicile de
l'émetteur, « mais, dans certains cas, elle peut refléter le lieu où l'émetteur réalise l'essentiel
de son activité ». Deux sources sérieuses donnent **70,00 %** et **72,04 %** d'États-Unis sur le même
fonds au même arrêté. L'interface ne doit donc **jamais** présenter ces chiffres comme exacts au
centième, et doit porter la règle employée à côté d'eux.

**2. Rien n'est jamais ramené à 100 %** ([D-69](decisions.md)). Les camemberts de l'étape 8 vont se
heurter à cela de plein fouet : une répartition honnête **ne fait pas le tour du cercle**. Sur les
données du propriétaire, plus d'un tiers du portefeuille est « non couvert ». Un graphique qui
normalise, ou qui range le reste dans une part « autres » muette, annulerait tout le travail de
l'étape. **La part manquante est une information, pas un défaut de présentation.**

**3. Un ETF synthétique ne détient pas son indice**, et l'application affiche l'**indice**
([D-64](decisions.md)). Conséquence pour l'interface : quand l'utilisateur ouvrira la fiche de son
émetteur, il verra **autre chose**. Il faut le prévenir à l'endroit où il regarde, pas dans une note
de bas de page.

**4. Une seule nomenclature, nommée à l'écran** ([D-65](decisions.md)) : les 11 secteurs
Morningstar, et **jamais** le mot « GICS ». Deux nomenclatures ne s'additionnent pas — l'écart
mesuré est de 5 points sur la technologie, et ce sont Alphabet et Meta qui changent de camp.

**5. « Inconnu » et « sans objet » ne sont pas la même chose**, et les confondre a produit le
dernier défaut de l'étape. Un ETF d'obligations et un ETF de matières premières s'affichaient
« non couvert : composition inconnue » alors qu'ils ont bien une composition — elle n'a simplement ni
pays ni secteur, comme un actif numérique. D'où le **contenu déclaré** ([D-71](decisions.md)), et
des montants hors géographie affichés **classe par classe** au lieu d'un fourre-tout qui faisait
passer de l'or pour de la dette.

**6. Les codes, pas les libellés.** Pays en ISO 3166-1, secteurs en code de nomenclature. Le seul
endroit où un libellé de source est lu est isolé dans `donnees_externes/actions.py`, signalé comme
fragilité, et incapable de produire un chiffre faux — seulement un poste visiblement non reconnu.

### Les défauts trouvés en chemin, et ce qu'ils enseignent

La relecture indépendante a rendu **quatre** remarques, toutes traitées et chacune couverte par un
test. Deux méritent d'être retenues pour l'étape 8 :

- **un poste éclaté en deux lignes** : l'agrégation se faisait sur le code de la source et non sur
  celui du référentiel, donc `stock` et `preferred` faisaient deux lignes « Actions ». Toute
  agrégation doit passer par la clé canonique **avant** de cumuler ;
- **un signalement calculé mais jamais affiché.** Il était produit, transporté… et perdu. Un
  signalement qu'on ne montre pas n'existe pas (règle 6). **À vérifier systématiquement dans les
  vues** : chaque chose que le moteur signale doit avoir sa place à l'écran.

Et **deux défauts trouvés en lançant simplement la commande sur les vraies données**, que ni les
tests ni la relecture n'avaient vus :

- **un pourcentage multiplié par cent** : « 6264,00 % » au lieu de 62,64 %. Le moteur rend des
  **pour cent** (`Repartition.pour_cent()`), là où `rapport._pourcentage()` attend un **taux**
  (0,6264). Les deux existent toujours, et ils ont maintenant chacun leur fonction de mise en
  forme. **Piège à connaître pour l'interface**, qui affichera beaucoup de pourcentages ;
- **une source qui répond sans rien savoir** : pour certains ETF, elle renvoie une réponse
  parfaitement formée — date, drapeau de réplication — mais range **100 % du fonds dans
  « autres »**. Sans garde-fou, ces actifs étaient présentés comme de l'obligataire et des
  liquidités : un chiffre faux et crédible. Ils sont désormais refusés et déclarés **non couverts**.

**La règle qui en sort, et c'est la même qu'à l'étape 6 sous un autre visage : lancer la commande
sur les vraies données trouve ce que les tests ne trouvent pas.** Les deux défauts ci-dessus
sautaient aux yeux en trois secondes d'affichage réel, et aucun des 814 tests ne les voyait.

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu de
  certificats par défaut ne le reconnaît pas. `uv sync --native-tls`, `uv run --native-tls …`.
- **L'antivirus peut couper Claude Code en pleine session.** Le 2026-09-26, **Avast WebShield** a
  bloqué `api.anthropic.com` en annonçant un contenu « malveillant » — un faux positif de son
  inspection HTTPS. Conséquences en chaîne, à reconnaître du premier coup d'œil :
  1. une erreur **403 « blocked by Avast WebShield »** apparaît ;
  2. les agents de recherche en cours meurent tous en même temps, laissant le tour de conversation
     **incomplet** ;
  3. chaque relance renvoie alors cet état invalide et répond **400 Bad Request**, indéfiniment.
     Se reconnecter ne sert à rien : **il faut ouvrir une nouvelle session.**

  **Prévention :** ajouter `api.anthropic.com` aux exclusions d'Avast. Et pour toute recherche en
  ligne longue : **écrire les trouvailles dans un fichier au fur et à mesure**. Les trois agents de
  l'étape 7 l'ont fait, et aucun n'a rien perdu — l'un d'eux a tourné près d'une heure.
- **Écrire un fichier long : passer par les outils d'édition, pas par le shell.** Deux échecs
  distincts, tous deux rencontrés à l'étape 7 :
  1. un `cat > fichier <<'FIN'` **suivi d'une autre commande** dans le même appel casse
     l'interpréteur (« unexpected EOF »), même avec un seul bloc ;
  2. **les antislashs d'un script Python inline sont mangés en route** : un `"\n"` écrit dans une
     chaîne est arrivé sous forme de **vraie nouvelle ligne** et a coupé un fichier de tests en deux
     (`SyntaxError: unterminated f-string`). Dès qu'un contenu comporte un antislash, utiliser
     l'outil d'édition.
- **L'éditeur applique une limite de 88 caractères, le projet en fixe 100** (`pyproject.toml`). Les
  diagnostics E501 de l'IDE sous 100 caractères ne sont pas des erreurs du projet :
  `uv run ruff check .` fait foi.
- **La console Windows écrit en cp1252** : ni traits de tableau, ni coches, ni flèches. Un rapport
  qui en contiendrait ferait échouer la commande **au moment de l'afficher**, alors que le calcul,
  lui, s'est bien passé. Des tests vérifient que chaque bloc reste affichable en cp1252 ; **en
  ajouter un pour tout nouveau bloc**. *(C'est pourquoi le rapport écrit « VALEUR REELLE » et
  « REPARTITION DU PORTEFEUILLE » sans accents sur les capitales.)*
- **Vérifier qu'un libellé tient dans sa colonne.** Un libellé trop long est **tronqué à
  l'affichage**, et il n'explique alors plus rien : c'est arrivé à l'étape 7 avec « Hors répartition
  actions (obligations, liqu. ». Un test compare désormais chaque libellé à la largeur de sa
  colonne.
- **Aucun test ne sort de la machine, et trois fixtures automatiques le garantissent** dans
  `tests/test_cli.py` : l'une détourne le dossier personnel, l'autre coupe la liste des ETF de
  Xetra, la troisième coupe les **sources de composition**. Si un test devient lent, c'est la
  première piste.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- **La saisie du PIN n'affiche rien du tout.** Sous Windows, `getpass` lit les caractères
  directement depuis la console : ni chiffres, ni étoiles, ni curseur. **Corollaire :** `msvcrt`
  exige une **vraie console Windows** — dans Git Bash (MinTTY) la saisie ne fonctionne pas et la
  commande reste bloquée. Lancer `rafraichir` et `positions-reelles` depuis PowerShell, `cmd` ou le
  terminal intégré de VS Code.
- **Chaque appel à pytr est une connexion complète** : rien n'est enregistré (D-41), donc numéro,
  PIN et confirmation sont redemandés à chaque fois. D'où `positions-reelles` en commande à part
  (D-46).
- **Utiliser pytr comme bibliothèque réserve deux pièges** : `login()` a pour défaut
  `waf_token="playwright"`, qui exige un navigateur — écrire `login(v2=True, waf_token="default")` ;
  et `login()` se termine par un `log.debug` du **JSON complet du compte**, d'où le filtre posé par
  `museler_le_journal_de_pytr()`.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run dashboard emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run dashboard lire --export <dossier>` (idem pour `positions`).
- Le propriétaire **ne code pas** : il vérifie les chiffres. Tout calcul doit être refaisable à la
  main, et les options techniques lui sont présentées avec leurs avantages et inconvénients. Il
  tranche vite, et **il tranche parfois contre la recommandation avec de bonnes raisons** : c'est
  ainsi qu'est né D-62, la décision la plus large de l'étape 7. Quand il va contre un conseil,
  demander pourquoi plutôt que réexpliquer.

---

## Comment mettre à jour ce fichier

À la fin d'une étape, avant la fusion dans `main` :

1. remplacer **le message à copier** par celui de l'étape suivante ;
2. mettre à jour **où en est le projet** : ce qui vient d'être ajouté, ce qui reste à faire, les
   questions encore ouvertes ;
3. écrire **ce que l'étape suivante doit savoir** : les pièges rencontrés, et ce sur quoi elle peut
   s'appuyer sans se méfier ;
4. compléter **à savoir pour travailler sur cette machine** si un piège nouveau est apparu ;
5. changer la date de la dernière mise à jour.

Ce fichier reste **court** : il oriente, il ne duplique pas la documentation. Et comme tout le
dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)).
