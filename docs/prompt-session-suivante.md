# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-10-09**, au milieu de l'étape 9 (blocs 9.0 à 9.4 faits et
> fusionnés dans `main`). La section « Où en est l'étape 9 » ci-dessous prime sur le reste du
> fichier, qui date de la fin de l'étape 8 quater et sera réécrit au bloc 9.6.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 9 bis : l'identité visuelle et la prédiction de l'évolution.
```

---

## Où en est l'étape 9 (2026-10-09)

**Fait, sur la branche `etape-9`, fusionné dans `main` :** l'assembleur (`pastory/assembleur.py`),
`pastory ouvrir`, l'accueil avec le dépôt de l'export (D-95), la synthèse, les actifs, la
diversification, les frais et taxes, et le **détail des calculs**, devenu une **page discrète**
ouverte par un bouton à droite de la manchette (il remplace le compteur « À surveiller », dont
le bloc est en bas de cette page). Décisions D-93 à D-97. Le contrat d'écran
([conception-interface.md](conception-interface.md) §4) décrit ce qui est à l'écran.

**Reste :**
- **l'étape 9 bis**, que le propriétaire veut attaquer en premier
  ([feuille-de-route.md](feuille-de-route.md)) :
  - l'identité visuelle, en maquettes comparables d'abord ;
  - la prédiction de l'évolution (Monte-Carlo, D-97). **Rien n'est codé avant que Q-61 soit
    tranchée** : les hypothèses, avec la recommandation écrite.
- **Le choix du fond** : trois pistes (A, B, C) sont dans `maquettes/apercus-fond/`, non
  versionné. Le propriétaire n'a pas encore choisi ; à reprendre dans la 9 bis, puis supprimer
  le dossier.
- **9.5** : les écrans de correction (tomlkit, D-94 ; le §6 du contrat est déjà réécrit).
- **9.6** : le cahier `docs/verification/etape-9.md`, `/code-review`, et la réécriture de ce
  fichier.

**Les pièges de cette session :**
- **Dash 4 n'a pas de composants SVG** : tout graphique est un élément vide `data-dessin` dont
  `data-donnees` porte des libellés **déjà mis en forme** par Python ; `assets/dessin.js` dessine
  (D-93).
- **Coupures de connexion locales** (`ERR_CONNECTION_RESET` sur 127.0.0.1, sans doute
  l'antivirus) : page blanche. Le script `FILET_DE_CHARGEMENT` d'`application.py` recharge, puis
  affiche un message.
- **uv sur OneDrive** (« Accès refusé ») : `UV_LINK_MODE=copy uv sync --native-tls`.
- **Yahoo rend la clôture d'hier vide (`null`) pendant plusieurs heures**, pour les ETF comme
  pour le bitcoin. Pastory ne l'invente pas. Et depuis le 2026-10-09, un jour cherché **après**
  la fin du cache fait redemander la suite (`FournisseurDeCours._completer_la_fin`) : avant, les
  cours restaient figés au dernier `pastory cours`.
- **Vérifier à l'écran** : lancer sur une **copie** du dossier Pastory, jamais sur le vrai :
  `PASTORY_DOSSIER=<copie> .venv/Scripts/python.exe -c "from pastory.vues import application;
  application.lancer(hors_ligne=True, port=8085, navigateur=False)"`, puis une capture par Edge
  sans fenêtre (protocole DevTools). Le script de capture vivait dans le scratchpad : à réécrire.
- **Bash et les barres obliques inverses** : écrire les scripts avec l'outil d'écriture de
  fichiers, pas par heredoc.
- `ruff check` est la règle ; `ruff format` n'est pas appliqué au dépôt (66 fichiers le
  changeraient) : ne pas le lancer en masse.

---

## Où en est le projet

- **Étapes 0 à 8 quater terminées.** Le moteur est complet, l'interface est **conçue**, les
  opérations viennent de l'**export officiel** de Trade Republic ([D-79](decisions.md)), et
  **tous les réglages se trouvent seuls** ([D-80](decisions.md), D-85 à D-92) : cotation, type,
  TER, contenu d'un fonds, source de secours, date d'ouverture du PEA — chacun avec sa source,
  sa date et son contrôle, ou le motif de son absence.
- **La vision du propriétaire, à garder en tête ([D-80](decisions.md))** : l'utilisateur **dépose
  l'export, et c'est tout**. Une correction est possible, jamais nécessaire.
- **Prochaine : étape 9**, l'interface.
- **Questions ouvertes** : **Q-54** (actions gratuites puis « migration » : le propriétaire doit
  choisir le traitement, options a, b, c) et **Q-60** (le contenu du monétaire, des multi-actifs,
  de l'immobilier). Aucune ne bloque l'étape 9.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| `pastory/reglages/` | **Ce qui se trouve seul** : `Origine`, `Trouvee`, `Trou`, `Reglage` ; l'assemblage correction > trouvé > trou ; la recherche contrôlée ; le cache ; le rapport de `pastory actifs` ([architecture.md §5.8](architecture.md)) |
| [reglages-automatiques.md](reglages-automatiques.md) | Le comparatif des sources des réglages, leurs mesures et quinze pièges |
| [verification/etape-8-quater.md](verification/etape-8-quater.md) | Le cahier de l'étape |
| [export-officiel.md](export-officiel.md) | Le relevé de l'export officiel |
| `data/` et un dossier `data_*/` | Les exports officiels du propriétaire et de son ami. Le second est **à un tiers** : structure seulement (règle 2) |
| [decisions.md](decisions.md) | D-01 à D-92 |

---

## Ce que l'étape 9 doit savoir de l'étape 8 quater

### Ce qu'elle lui laisse en main

- **Le contenu des écrans de correction existe** : pour chaque actif et chaque réglage, un
  `Reglage` dit la valeur retenue, sa source, sa date, ce qui a été vérifié, ce qu'il faut savoir,
  ou le motif de son absence ; et, si l'utilisateur a corrigé, ce que la source donnait.
  `pastory actifs` (`pastory/reglages/rapport.py`) en est la version texte : l'écran la reprend.
- **Ce que l'écran doit permettre de corriger** : ticker et devise, type, TER, contenu, spread,
  répartition, refus du secours (`secours = "aucun"`), date du PEA. Le fichier reste le format de
  stockage ; **l'application ne l'a jamais réécrit jusqu'ici** ([D-92](decisions.md)), et l'écran
  sera le premier à le faire : garder les commentaires, c'est le sujet annoncé par D-78.
- **Une correction de ticker** est sans danger pour les cours : ceux d'une autre cotation ne
  sont jamais employés, et sont repris à la source ([architecture-notes §7 bis](architecture-notes.md)).
- **Avec `--export` (l'export d'un tiers), aucun appel réseau** n'est fait, ni recherche, ni
  cours, ni composition (règle 2). C'est voulu.
- **Les trous se disent là où ils se voient** : `positions` annonce déjà en une ligne les réglages
  introuvables ; le bloc « D'où viennent les TER » nomme la source de chaque taux ; la date du PEA
  porte son origine et sa réserve dans la règle de l'impôt ; un retrait trouvé remplace
  l'hypothèse « aucun retrait » ([D-87](decisions.md)).

### Les pièges de l'étape 8 quater, à connaître

- **Un contenu « actions » trouvé ne s'applique pas** : il ferait passer le fonds avant sa
  composition. Ne pas « corriger » cela sans relire [D-89](decisions.md).
- **Une panne n'est jamais gardée en mémoire** comme un trou ; un test le garde. La liste de Xetra
  écrit son lien de deux façons selon le serveur ([reglages-automatiques.md §2.3](reglages-automatiques.md)).
- **Les tests coupent désormais six sources** par des fixtures automatiques de `tests/test_cli.py`
  (cotations, TER de l'émetteur, Xetra, classe d'extraETF, registre de l'ESMA, compositions). Un
  test qui veut une recherche branche une source factice (`brancher_les_cotations`).
- **`actifs.toml` du propriétaire** contient encore l'ancien code pytr de sa crypto (signalé comme
  orphelin) et des valeurs désormais trouvées seules. Sa configuration est toujours dans l'ancien
  dossier `DashBoardTradeRepublic` : le cahier lui demande de la déplacer et de l'alléger.
- **La date d'ouverture du PEA** se lit dans l'ordre des **horodatages** : une clôture et une
  réouverture tombent le même jour, et la sortie qui clôt un plan n'est pas un retrait du suivant.

### Les pièges de l'étape 8 ter, toujours vrais

- **Le brut des dividendes néerlandais est faux dans l'export**, sans marque ([D-84](decisions.md)).
  C'est une limite **affichée**, pas un réglage.
- **Les tests de la ligne de commande ajoutent deux titres reçus à la lecture**
  (`export_ligne_de_commande.titres_recus()`) ; la fixture `lecture_pure` retire l'ajout.
- **Le Saveback** est affiché comme non traité, en attendant un export plus récent du
  propriétaire.

## Ce que l'étape 9 doit savoir, de l'étape 8 et du contrat d'interface

### La chose à ne pas rater de cette étape

**L'édition de fichiers doit disparaître** ([D-78](decisions.md), et le
[§6 du contrat](conception-interface.md)). C'est un arbitrage du propriétaire du 2026-10-01, rendu
en voyant arriver un quatrième réglage à écrire à la main, et sa raison porte loin : **une bidouille
qui fait peur fait douter de l'application entière**, or ce projet ne tient que sur la confiance
dans ses chiffres.

Concrètement : le ticker et la devise d'un actif, son type, son TER, son `contenu`, sa source de
secours et la date du PEA ont **tous** un écran — un écran de **correction**, facultatif, puisque
tout est désormais trouvé seul ([D-80](decisions.md), [D-92](decisions.md)). Le fichier TOML
reste le format de stockage. **L'étape n'est pas terminée tant qu'une correction n'existe qu'en
fichier.**

Deux points de méthode qui vont avec :

- **l'application trouve, applique et montre ; l'utilisateur peut corriger** ([D-80](decisions.md)
  remplace « l'application propose, l'utilisateur décide » de D-78). Ce qui protège d'une valeur
  fausse, ce sont les contrôles et la visibilité de la source, pas un clic de validation. Le
  [§6 du contrat](conception-interface.md) est à réécrire en conséquence, en premier ;
- **un écran qui écrit dans le fichier doit le relire et le réécrire sans perdre ses
  commentaires.** Ce sont eux qui rendent le fichier compréhensible à la main. C'est faisable et ce
  n'est pas gratuit : un sujet, pas un détail.

### Le contrat, et où il est

**Tout est dans [conception-interface.md](conception-interface.md).** Ne pas rouvrir les
arbitrages : les cinq onglets, leur ordre et leurs filtres sont fixés, et le §5 dit les quatre
états que chaque bloc doit prévoir. Là où le document et les maquettes se contredisent, **les
maquettes ont raison** et le document est à corriger.

Le point le plus facile à rater : **la diversification et les frais n'ont aucun filtre**, et c'est
une règle. Une répartition est la photo d'un tout ; un filtre qui n'agit sur rien fait douter du
chiffre affiché.

### Ce que l'étape 8 bis a ajouté au moteur, et qui change l'écran

- **`Diversification.origines`** : la source **et** la règle de pays de **chaque** actif
  (`moteur/diversification.py`, `OrigineDUnActif`). C'est la condition que
  [D-72](decisions.md) posait pour s'autoriser une source de secours, et l'écran doit les mettre
  **en face des lignes**. Le rapport texte le fait déjà, et n'affiche le bloc que s'il y a **plus
  d'une** origine — vingt lignes identiques feraient douter des chiffres ;
- **`Composition.regle_de_pays`** : le champ qui manquait. Trois règles cohabitent désormais —
  pays d'activité (extraETF), siège social (GLEIF), pays de classification de l'indice (Amundi) ;
- **la source de secours** ([D-77](decisions.md)) : un actif servi par elle a des **pays** et
  reste **non couvert en secteur**. Les deux écrans de diversification ne sont pas d'accord, et
  c'est juste — le §5.2 du contrat le dit.

### Les pièges d'affichage trouvés à l'étape 8, qui valent tous pour l'étape 9

Neuf passes de relecture par le propriétaire. Les pièges sont tous des pièges **d'affichage qui
font douter des chiffres** — jamais des pièges de calcul :

- **la boîte de lecture du graphique a été essayée dans TROIS arrangements**, et c'est le plus
  instructif des allers-retours. (1) Infobulle en haut du cadre : elle masquait le haut de la
  courbe, l'endroit même qu'on regarde. (2) Bandeau sous la courbe, hauteur réservée, ne
  recouvrant rien : jugé « trop en retrait », puis écarté pour une raison meilleure — **descendre
  les yeux hors du graphique pour lire un chiffre casse la lecture**. (3) Retenu : une boîte
  **sur** le graphique qui **suit la souris**, décalée du curseur et basculant près des bords,
  étroite et verticale pour ne masquer qu'une bande fine. Les trois sont gardés au §3.2 du
  contrat avec leurs raisons : **ne pas recommencer le tour.** Leçon générale : sur un graphique,
  *ne rien recouvrir* pèse moins que *ne pas faire bouger les yeux* ;
- **un repère répété à l'identique n'est pas un repère** : les cinq zones géographiques portaient
  toutes le même globe. Elles portent maintenant un **planisphère** dont leur part du monde est
  remplie d'encre. Ce qui en sort : un repère de ce genre **situe, il ne mesure pas** — il allume
  des continents entiers là où une zone ne suit pas leurs contours — et il doit le dire ; et le
  Japon comme la Nouvelle-Zélande sont dessinés **plus grands que l'échelle**, sans quoi ils font
  un pixel et disparaissent au moment même où on les allume ;
- **un nouveau repère plus large casse deux choses d'un coup** : le planisphère faisait 15 px de
  plus qu'un pictogramme, ce qui a (1) tronqué « Asie-Pacifique développée » à la largeur minimale
  de sa colonne — le défaut de l'étape 7, revenu par une autre porte — et (2) dentelé le bord
  gauche des libellés d'une même liste. D'où la colonne élargie, le créneau de repère à largeur
  fixe, et le `title` sur chaque libellé ;
- **`.carte` était déjà pris.** Le planisphère s'est d'abord appelé `.carte`, qui est le nom des
  cartes d'actifs de la synthèse : sa règle de largeur et de hauteur écrasait la leur. Il s'appelle
  `.planisphere`. **Un contrôle automatique l'a trouvé** — celui qui compare les classes posées par
  `maquette.js` aux sélecteurs de `style.css` et signale les sélecteurs définis deux fois. À
  réécrire au besoin : il n'est pas dans le dépôt ;
- **`var()` n'est pas interprété dans un attribut SVG** (Chrome, Safari). Toutes les couleurs des
  graphiques étaient invalides, et l'anneau ne montrait pas les couleurs de ses poches. Règle : une
  couleur posée en **attribut SVG** s'écrit en clair, une couleur posée en **CSS** passe par la
  variable. `maquettes/maquette.js` porte les deux palettes, et un script vérifie qu'elles
  concordent ;
- **sans `color-scheme: only light`**, le mode sombre automatique du navigateur inverse les
  clartés : le bleu le plus foncé s'affiche le plus clair. Conséquence plus grave que les anneaux :
  un gain en sauge inversé vire au rouge ;
- **un SVG sans règle de taille** prend sa taille intrinsèque et remplit la page. Arrivé en
  supprimant une classe voisine inutilisée, qui a emporté neuf règles avec elle ;
- **un anneau ne porte pas de chiffre** : l'étiquette doit choisir sa couleur selon la part, et
  devient illisible sur les teintes intermédiaires. Le classement chiffré à côté fait foi ;
- **une couleur suit son poste, jamais son rang** : sinon décocher une poche repeint les
  survivants ;
- **le sens de lecture d'un anneau n'est pas évident** : trier par taille décroissante, sans quoi
  la petite part collée avant midi se confond avec la première ligne de la légende ;
- **le gain n'est pas la somme d'une colonne**, et l'écran doit le dire. Il se calcule sur les
  montants bruts ([D-21](decisions.md)) là où le capital net investi est net de frais et réduit au
  prorata des ventes ([D-12](decisions.md)).

### Comment le propriétaire relit

Il regarde l'écran, pas le code, et il trouve des défauts réels — y compris ceux qui viennent de
son navigateur. **Quand il signale une incohérence de chiffres, la vérifier par le calcul avant de
conclure** : deux fois sur trois le code avait raison et l'affichage avait tort, une fois sur trois
c'était un vrai bug de calcul. Les scripts de contrôle écrits aux étapes 8 et 8 bis sont dans le
dossier temporaire de la session, pas dans le dépôt : les réécrire au besoin.

---

## À savoir pour travailler sur cette machine

- **Le logo est temporaire**, et dessiné en SVG dans `maquette.js` (`logo()`) : une page, et dessus
  une valeur qui monte. Il est **clair sur le bandeau d'encre**, et son trait est en **encre, pas en
  sauge** — la sauge veut dire « gain » partout ailleurs, et un logo vert se lirait comme un état du
  portefeuille. La manchette a donc perdu la note de couleur que portait le point sauge.
- **L'application s'appelle Pastory** ([D-74](decisions.md)), et plus « DashBoard Trade
  Republic ». Le paquet est `pastory/`, la commande est `uv run pastory …`, le dossier personnel
  de l'utilisateur est `Pastory`. **Le nom « Trade Republic » ne subsiste que là où il désigne la
  banque** : l'adaptateur, l'export, la documentation des données. Deux choses restent à faire
  **par le propriétaire, hors dépôt** : renommer le dépôt GitHub et le dossier local du projet.
  *Attention en relisant les vieux documents :* `notes-initiales.md` cite volontairement l'ancien
  nom deux fois, parce qu'il y désigne un fichier PDF et un souvenir — ne pas les « corriger ».
- **`uv run` peut échouer deux fois de suite sur OneDrive, puis réussir.** Dès que
  `pyproject.toml` change, uv réinstalle le projet et bute sur OneDrive : d'abord
  `failed to hardlink` (os error 396), puis `failed to remove directory … Accès refusé`
  (os error 5). Remède : `$env:UV_LINK_MODE = "copy"`, puis **relancer la même commande** — la
  deuxième passe. Ce n'est pas un échec des tests, et le message le dit mal.
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
- **`uv run` peut échouer sur le certificat même avec `--native-tls`** (« invalid peer
  certificate: UnknownIssuer » en voulant télécharger `hatchling`). Le 2026-10-05, la parade a été
  d'appeler directement `.venv/Scripts/python.exe -m pytest` (et `-m ruff`, `-m pastory.cli`), et
  de mettre `uv.lock` à jour avec `uv lock --offline` — ce qui suffit pour **retirer** une
  dépendance.
- **Pour retrouver le comportement d'un code retiré**, une copie de travail du commit d'avant
  (`git worktree add <dossier> <commit>`) permet de l'exécuter sans toucher à la branche. C'est
  ainsi que les 8 opérations de l'ancien export fictif ont été reproduites à l'identique.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run pastory emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run pastory lire --export <dossier>` (idem pour `positions`). Sur l'export d'un tiers,
  pointer `PASTORY_DOSSIER` vers un dossier vide, pour ne pas mélanger sa lecture avec la
  configuration du propriétaire. **Attention** : avec `--export`, aucune recherche de réglage
  n'est faite (règle 2) — c'est voulu, et le rapport le dit.
- **Pour essayer sur les vraies données du propriétaire sans rien écrire chez lui** : copier son
  export (et, au besoin, sa configuration) dans un dossier du scratchpad, et pointer
  `PASTORY_DOSSIER` dessus. C'est ainsi qu'ont été mesurés les résultats de l'étape 8 quater, et
  que la panne intermittente de la liste de Xetra a été trouvée.
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
