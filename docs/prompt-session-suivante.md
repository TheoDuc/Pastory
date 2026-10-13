# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-10-13**, à la fin de l'étape 11. **Le dépôt est public** (ou sur
> le point de l'être : vérifier sur GitHub). Tout est fusionné dans `main`.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
Pastory est publié. Voici ce que je veux faire maintenant : […]
```

**Les onze étapes sont faites.** Ce qui reste est facultatif, et le propriétaire choisira :
les écrans de correction (bloc 9.5), l'icône pour Mac, le guide d'adaptateur, les questions
Q-54 et Q-60 — ou un retour d'utilisateur, maintenant qu'il peut y en avoir.

**Le dépôt est public : trois réflexes nouveaux.**

- **Rien de personnel dans un commit**, message compris : ni nom, ni chemin de la machine, ni
  valeur. Ce qui était une règle de prudence est maintenant irréversible une fois envoyé.
- **L'historique a été réécrit le 2026-10-13** pour en retirer une adresse de courriel
  ([D-115](decisions.md)) : les identifiants de commit cités dans d'anciennes conversations
  n'existent plus. `git config user.email` porte l'adresse anonyme de GitHub : la vérifier avant
  un premier commit sur une autre machine.
- **Un retour d'inconnu arrive par une « issue » GitHub**, et peut contenir un vrai export :
  ne jamais le recopier dans le dépôt, et prévenir son auteur.

---

## Où en est le projet (2026-10-13)

- **Le moteur est complet** (étapes 0 à 8 quater) : positions, valorisation, rendements, coûts,
  impôt estimé, diversification. Les opérations viennent de l'**export officiel** de Trade Republic
  ([D-79](decisions.md)), et **tous les réglages se trouvent seuls** ([D-80](decisions.md)).
- **L'interface est faite** (étapes 9 et 9 bis) : la couverture et le dépôt, cinq chapitres
  (Synthèse, Les actifs, Diversification, Frais et taxes, Projections), l'annexe « Détail des
  calculs », l'identité « livre relié » et la lecture de nuit. **Toute modification d'interface
  suit [charte-graphique.md](charte-graphique.md).**
- **Pastory s'ouvre comme un logiciel** (étape 10, cette session) : une icône, une fenêtre à part,
  l'arrêt à la fermeture ([D-106](decisions.md)) ; un portefeuille de démonstration
  ([D-107](decisions.md)) ; et le ménage ([D-108](decisions.md)).
- **Un fichier déposé est un portefeuille** (étape 10 bis, [D-109](decisions.md)) : les exports
  ne se cumulent plus, Pastory n'en lit qu'un à la fois, et la couverture propose le choix.

**Ce qui reste, dans l'ordre que le propriétaire choisira :**

| Quoi | Où c'est décrit |
|---|---|
| **9.5** : les écrans de correction (tomlkit, [D-94](decisions.md)) | [conception-interface.md](conception-interface.md) §6, déjà réécrit |
| **9.6** : le cahier `docs/verification/etape-9.md` | il n'existe pas encore |
| **Fin de l'étape 10** : installation par un tiers, raccourci Mac, messages d'erreur, guide d'adaptateur | [feuille-de-route.md](feuille-de-route.md), « Reste de l'étape 10 » |
| **Étape 11** : la publication | [feuille-de-route.md](feuille-de-route.md) |

- **Le retour du premier testeur est traité** (cette session, [D-110](decisions.md) à
  [D-114](decisions.md)) : le fichier d'installation installe `uv` lui-même, et la version de
  Python est fixée ; l'attente dit où en est la lecture, et la première ouverture est cinq fois
  plus courte ; chaque ligne de la Diversification se déplie vers ses actifs ; chaque série de
  cours est reprise une fois pour combler ses jours manquants.

**Questions ouvertes** : **Q-54** (actions gratuites puis « migration ») et **Q-60** (le contenu du
monétaire, des multi-actifs, de l'immobilier). Aucune ne bloque.

- **Pastory est publié** (étape 11, [D-115](decisions.md), [D-116](decisions.md)) : licence MIT,
  page d'accueil, historique vérifié puis réécrit sans l'adresse du propriétaire, revue de
  sécurité (un constat, corrigé : le serveur ne répond qu'à son nom), pandas retiré.

**À la fin de la session du 2026-10-13** : l'étape 10 est **fusionnée dans `main` et envoyée**
sur GitHub, vérifiée par le propriétaire (il reste de son [cahier](verification/etape-10.md)
**l'essai d'une fenêtre réduite pendant une heure ou deux**, seul point non mesuré). L'étape
10 bis est **fusionnée dans `main`**, avec son accord, après qu'il a lui-même trouvé son
dernier défaut (un nom de portefeuille accentué). Il reste de son
[cahier](verification/etape-10-bis.md) ce qui demande du temps : son **export du mois
prochain**, qui doit mettre son portefeuille à jour et non en créer un second. **Vérifier
`git branch` et `git log` avant de supposer quoi que ce soit.**

---

## Ce que le retour du premier testeur laisse en main

- **Le compteur de l'attente** (`pastory/avancement.py`) ne connaît ni l'écran ni les sources.
  L'assembleur le fait avancer (`construire(..., suivi=)`), `vues/attente.py` écrit les mots et
  répond à `/pastory/avancement`, `dessin.js` pose la réponse. **Une étape nouvelle et longue
  dans `construire` se déclare dans `Etape`** — sans quoi la barre s'arrête pendant qu'elle tourne.
- **La reprise des séries** (`FournisseurDeCours.reprendre`, D-113) a lieu une fois par actif,
  puis le cache le retient (`cache/cours/_series_reprises.txt`). Elle est **muette** : ni refus,
  ni alerte, quoi que réponde la source. Dans les tests de l'assembleur, `deja_repris(...)` donne
  un cache en régime de croisière ; sans lui, la première demande est toujours la reprise.
- **`assembleur.remplir_les_cours` passe avant tout calcul**, une demande par actif. Ne pas le
  retirer « pour simplifier » : sans lui les cours reviennent par petites fenêtres, cinq fois
  plus lentement, avec des jours manquants entre deux fenêtres ([D-110](decisions.md)).
- **Chaque euro rangé par la répartition est noté avec son actif** (`_Cumul._noter`,
  `moteur/diversification.py`). Toute nouvelle case de la répartition doit passer par une
  méthode `ajouter_…` du cumul, jamais par un `+=` direct : un test vérifie que les apports d'une
  ligne somment à son montant, et c'est ce que l'écran promet ([D-111](decisions.md)).
- **Deux sortes de lignes dépliables** dans la Diversification : `deroulant` (un groupe : une
  zone, « Sans pays ») et `deroulant deroulant--actifs` (une ligne vers ses actifs). Les tests
  les distinguent par leur classe exacte.
- **`Installer Pastory.cmd` s'essaie sur une copie, jamais dans le projet**, et sa dernière étape
  **écrit de vrais raccourcis sur le bureau** : pour l'essayer, en faire une copie où la ligne
  `pastory.cli installer` est remplacée par un `echo`. Pour essayer l'installation de `uv` sans
  toucher à celui de la machine : `UV_INSTALL_DIR` vers un dossier jetable, `UV_NO_MODIFY_PATH=1`,
  et `USERPROFILE`, `LOCALAPPDATA`, `APPDATA` détournés (le reçu de l'installation s'y écrit).
  Lancer le fichier par PowerShell (`cmd /c ".\fichier.cmd"`) : Git Bash abîme le chemin.
- **Le fichier `.cmd` écrit par un outil d'édition perd ses fins de ligne Windows** : les lui
  rendre (`unix2dos`) avant de l'essayer, sans quoi ses `goto` et ses `call :étiquette` échouent.

## Les pièges de cette session

- **Retirer une bibliothèque : l'interdire d'abord.** `sys.modules["pandas"] = None` avant
  `pytest.main(...)` : pandas ne servait plus, mais apportait `tzdata`, dont l'heure de Paris a
  besoin sous Windows ([D-116](decisions.md)). `uv lock --offline` suffit pour retirer une
  dépendance **et** pour en ajouter une déjà connue du fichier de verrouillage.
- **`pyproject.toml` a changé à l'étape 11** : sur cette machine, `uv run` voudra resynchroniser
  et butera sur l'antivirus (voir plus bas). Les icônes et `.venv\Scripts\python.exe -m …`
  ne sont pas touchés. pandas reste installé dans `.venv` tant qu'aucune synchronisation n'a
  réussi : un test vérifie qu'il n'est plus **importé**, pas qu'il est absent.
- **Chercher une donnée personnelle dans l'historique sans l'afficher** : lire les vrais exports
  comme des aiguilles (identifiants d'opération, IBAN, noms de fichiers), parcourir chaque ligne
  **ajoutée** de `git log --all -p`, et n'écrire que des comptes et des noms de fichiers. Le
  script vivait dans le dossier temporaire : à réécrire au besoin.
- **Rendre public un dépôt après l'avoir écrasé ne suffit pas** : GitHub garde la trace des
  envois forcés, et l'ancien historique y reste consultable. D'où un dépôt neuf.
- **`/security-review` ne relit que ce qui n'est pas encore envoyé**, et il lui faut
  `git remote set-head origin main`. Pour une première publication, c'est tout le code qu'il faut
  faire relire : l'agent a reçu les deux périmètres.

- **Une installation dépend de la date à laquelle on la fait.** « failed to build pandas » : `uv`
  prenait le Python le plus récent (3.15, sorti ce mois-ci), pour lequel le fichier de
  verrouillage n'avait pas de pandas tout prêt. `.python-version` le fixe à 3.12, et
  `TestLaVersionDePython` vérifie `uv.lock`. **Toute mise à jour de `uv.lock` passe par ce test.**
- **Trois causes plausibles ne valent pas un message d'erreur.** Le fichier d'installation avait
  été durci contre trois pannes supposées ; aucune n'était la bonne. Demander le message d'abord.
- **Pour voir quel Python `uv` choisirait sur une machine neuve** : un `uv` récent, une copie du
  dépôt, `UV_PYTHON_PREFERENCE=only-managed`, `UV_CACHE_DIR` et `UV_PYTHON_INSTALL_DIR` vers un
  dossier jetable, puis `uv sync`. Sur cette machine le téléchargement échoue (l'antivirus), mais
  l'adresse refusée dit la version choisie.
- **`UV_NATIVE_TLS` est remplacé par `UV_SYSTEM_CERTS`** dans les `uv` récents, qui affichent un
  avertissement pour l'ancien nom. Le fichier d'installation regarde lequel `uv --help` connaît.
- **Une icône blanche sur un raccourci qui marche** : le dossier du projet a été renommé. Windows
  répare la cible d'un raccourci qu'on lance, pas son image. `pastory installer` recrée tout.
- **Un cache « sans trou » en avait sept.** La reprise des séries (D-113) a comblé des jours
  isolés dans le cache du propriétaire, rempli pourtant par `pastory cours`. Ne pas supposer
  l'état d'un cache : le mesurer.

- **Une demande de fonctionnalité peut cacher un défaut.** « Une barre de chargement » : la mesure
  a montré que 78 des 93 secondes d'attente étaient inutiles. Mesurer avant d'habiller.
- **Mesurer une première ouverture** : un dossier jetable dont le nom finit par `-demonstration`
  (c'est le dossier qui dit si c'en est une), `PASTORY_DOSSIER` pointé dessus, l'export fictif
  écrit par `demonstration.ecrire`, puis chaque appel de `assembleur.construire` chronométré un à
  un. Le script vivait dans le dossier temporaire de la session : à réécrire.
- **Sur cette machine, une page sur dix se charge mal** (l'antivirus, voir plus bas) : pendant un
  essai en navigateur sans fenêtre, la page est restée vide vingt secondes puis s'est rechargée
  seule. Ce n'est pas le code : le journal du serveur le montre (aucune demande `_dash-layout`).
- **Un scénario de capture ne se découpe pas sur les points-virgules** : le JavaScript en
  contient. Une instruction par ligne, dans un fichier.
- **`"uv" not in sortie` est vrai dans « ouvrez »** : chercher un mot court dans un texte
  français demande ses guillemets ou ses limites.
- **Comparer avant / après sans afficher une valeur** : le relevé écrit un fichier JSON, et la
  comparaison ne dit que le nom des rubriques qui diffèrent. Quand un écran **gagne** des lignes,
  comparer les nombres comme un multi-ensemble : aucun nombre d'avant ne doit avoir disparu.

## Ce que l'étape 10 laisse en main

- **Le lanceur** (`pastory/lanceur.py`) et **la veille** (`pastory/vues/veille.py`). La veille ne
  connaît ni Dash ni le réseau : elle se teste avec une horloge factice. Elle n'est branchée que
  par le lanceur ; `pastory ouvrir` s'arrête toujours par Ctrl+C.
- **L'adresse de vie**, `/pastory/vie` : la page y donne signe de vie, et le lanceur y demande « qui
  est là ? », puis y **annonce la fenêtre qu'il amène**. Sa réponse dit si c'est la démonstration.
- **Ce que le lanceur et l'application partagent est écrit une fois, dans `veille.py`** : le nom,
  l'hôte, le port, le titre de la fenêtre, l'adresse de vie. Ne pas les réécrire ailleurs : c'est
  par eux que le lanceur reconnaît son propre Pastory.
- **C'est le dossier personnel qui dit si c'est une démonstration**
  (`emplacements.est_une_demonstration`), et lui seul : aucune option n'est passée à l'écran.
- **`pastory installer`** (`pastory/installation.py`) crée les raccourcis ; `--retirer` les enlève.
- **La démonstration** (`pastory/demonstration/`) : le scénario est dans `__init__.py`, les
  clôtures dans `clotures.py`, **écrit par** `scripts/releve_de_demonstration.py`. Changer le
  scénario (un titre, un plan prolongé) demande de relancer ce script.
- **Le fichier de corrections du propriétaire existe désormais** :
  `%LOCALAPPDATA%\Pastory\configuration\actifs.toml`, avec **une** correction (les frais courants
  d'un ETF). C'est le premier cas réel pour les écrans de correction du bloc 9.5 — et il a été
  écrit à la main, ce que ces écrans doivent rendre inutile.

## Ce que l'étape 10 bis laisse en main

- **Le dossier de dépôt est une liste de portefeuilles** (`adaptateurs/trade_republic/depot.py`) :
  `inventaire`, `ouvrir`, `lire`, `comparer`, `renommer`, `supprimer`. Le nom d'un
  portefeuille est celui de son fichier ; celui qui est ouvert est retenu dans
  `.portefeuille-ouvert`. **`depot.lire(source)` ne lit qu'un fichier** : ne pas réintroduire
  un cumul.
- **Ce que devient un dépôt** est décidé dans `vues/reception.py`, sur les identifiants
  d'opération. L'écran est dans `vues/portefeuilles.py` ; `Chiffres.inventaire()` rend `None`
  là où l'on ne choisit pas (un tiers, la démonstration).
- **Jamais un texte de l'utilisateur dans l'identifiant d'un bouton.** Quand un identifiant
  Dash porte un caractère accentué, la valeur du clic arrive vide, et la garde contre les
  « boutons qui viennent d'apparaître » l'ignore : un portefeuille nommé « Zoé » ne s'ouvrait pas.
  Les boutons portent une clé (`portefeuilles.cle`), et un test vérifie qu'aucun identifiant
  d'aucun écran n'a d'accent. **Leçon de méthode :** ce défaut a passé 1 441 tests et un essai
  en navigateur, parce que tous utilisaient des noms sans accent et qu'aucun test ne passait
  par Dash. Un écran qui reçoit un texte libre s'essaie avec des accents, et ses rappels se
  testent par `/_dash-update-component` (voir `cliquer`, `tests/vues/test_portefeuilles.py`).
- **Le dossier se modifie aussi à la main** (le bouton « Ouvrir le dossier » y invite) : toute
  règle qui ne vit que dans le dépôt par l'écran est contournable. C'est `depot.inventaire`
  qui doit voir l'état du dossier — d'où `Inventaire.meme_compte` et le portefeuille « périmé ».
- **Un fichier illisible n'est pas un fichier absent** : `Inventaire.inaccessibles` compte
  parmi les portefeuilles. L'oublier, c'est dire « Votre livre » sur les chiffres d'un autre.
- **Pour le bloc 9.5** : une correction d'actif vaut pour tous les portefeuilles (elle décrit
  un titre) ; une correction fiscale vaut pour **un** portefeuille
  (`[portefeuille."Nom".pea]`), et un écran qui renomme un portefeuille devra renommer cette
  section avec lui — aujourd'hui, elle devient une correction sans objet, signalée.
- **Les tests qui veulent plus de lignes réécrivent l'export** (`ajouter_a_l_export`,
  `tests/test_cli.py`) : déposer un second fichier ferait un second portefeuille.
- **Sous Windows, deux chemins qui ne diffèrent que par la casse sont égaux** : comparer des
  noms de fichier, pas des chemins, quand la casse compte (le renommage).

## Les pièges de l'étape 10

- **Comparer des nombres « avant / après » : hors ligne, sur la même copie, et le même jour.** Un
  essai en ligne ajoute des cours au cache de la copie, et tous les chiffres bougent : cela a
  produit 2 548 faux écarts. Et une session qui passe minuit change « aujourd'hui », donc les
  durées et les taux annualisés : encore des faux écarts. La bonne méthode : une copie fraîche du
  dossier `Pastory`, le code d'avant extrait à part (`git archive main pastory tests | tar -x`,
  depuis un dossier temporaire — `git worktree` y laisse des restes que OneDrive empêche
  d'effacer), le code d'après dans le projet, les deux lancés **à la suite**, hors ligne, sur
  cette copie. Le script de relevé (`ecrans.rendre` sur 105 états) vivait dans le
  dossier temporaire de la session : à réécrire.
- **Le nom du dossier d'un tiers ne s'écrit dans aucun fichier versionné**, pas même dans un cahier
  de vérification : écrire « le dossier `data_*/` ». C'est arrivé dans le cahier de l'étape 10, et
  seule la relecture l'a vu. Avant un commit de documents : `git diff --cached | grep -i <nom>`.
- **Un long script passé au shell par heredoc peut casser l'interpréteur** (« unexpected EOF »),
  surtout s'il contient des apostrophes : l'écrire avec l'outil d'écriture de fichiers, puis le
  lancer. Vécu deux fois dans cette session.
- **« Déjà ouvert ? » est la question la plus piégeuse du lanceur.** Trois réponses fausses ont
  été corrigées : ne regarder que le premier port libre ; croire vivant un Pastory qui s'éteint ;
  prendre pour une panne un programme qui ne parle pas HTTP. Tout changement du lanceur se
  rejoue en vrai (ouvrir, relancer, fermer, rouvrir aussitôt), pas seulement en tests.
- **Un garde-fou de test ne doit pas remplacer un module partagé.** Remplacer `subprocess.Popen`
  pour interdire d'ouvrir une fenêtre a cassé l'écriture des raccourcis, qui s'en sert aussi : le
  garde-fou remplace `lanceur.subprocess` et `lanceur.webbrowser` par des doublures, pas le module.
- **De l'or en texte se déclare sur la reliure.** La mention de démonstration a été refusée par le
  test de la charte tant que son sélecteur ne commençait pas par `.entete`. C'est voulu : la règle
  dit où l'élément vit.
- **`pythonw` n'a ni sortie ni erreur** (`sys.stdout` vaut `None`). Tout ce qui écrit passe par le
  journal ; une erreur d'argument quitterait sans un mot, d'où `parse_known_args` dans le lanceur.
- **Un `.cmd` doit garder ses fins de ligne Windows**, y compris dans le ZIP de GitHub :
  `.gitattributes` le garantit. Il est écrit **sans accents** : la fenêtre de commandes ne les
  affiche pas de la même façon partout.
- **`uv sync --no-dev` retirerait pytest et ruff de l'environnement du projet** : ne jamais essayer
  le fichier d'installation dans le dossier du projet. L'essayer sur une copie
  (`git archive etape-10 | tar -x`, depuis le dossier de destination).
- **Bash et les chemins Windows** : `$LOCALAPPDATA` contient des antislashs ; `tar`, `cd` et
  consorts veulent `$(cygpath -u "$LOCALAPPDATA")`.
- **La fenêtre d'Edge en mode application porte le titre de la page**, exactement. C'est par ce
  titre, et par la classe `Chrome_WidgetWin_1`, que le lanceur retrouve sa fenêtre — le dossier
  « Pastory » ouvert dans l'explorateur porte le même titre.
- **Pour des captures d'écran** : Edge sans fenêtre (`--headless=new --remote-debugging-port`) et un
  petit client du protocole DevTools en Python standard. Le thème se force par
  `localStorage.setItem('pastory-theme', …)` **une fois sur l'adresse de Pastory** — posé avant,
  sur `about:blank`, il est sans effet. Script dans le dossier temporaire : à réécrire.
- **`.git/worktrees/` garde deux dossiers vides** (`ancien`, `code-de-main`) que OneDrive empêche
  d'effacer. Sans conséquence : `git worktree list` ne les voit pas.

## Les pièges de l'étape 9, toujours vrais

- **Dash 4 n'a pas de composants SVG** : tout graphique est un élément vide `data-dessin` dont
  `data-donnees` porte des libellés **déjà mis en forme** par Python ; `assets/dessin.js` dessine
  (D-93).
- **Coupures de connexion locales** (`ERR_CONNECTION_RESET` sur 127.0.0.1, sans doute
  l'antivirus) : page blanche. Le script `FILET_DE_CHARGEMENT` d'`application.py` recharge, puis
  affiche un message. La veille de l'étape 10 en tient compte : un signe de vie perdu n'arrête
  rien.
- **Yahoo rend la clôture d'hier vide (`null`) pendant plusieurs heures**, pour les ETF comme
  pour le bitcoin. Pastory ne l'invente pas. Un jour cherché **après** la fin du cache fait
  redemander la suite (`FournisseurDeCours._completer_la_fin`).
- **Yahoo répond 400 à une période où un titre ne cotait pas encore** (étape 10) : c'est
  `PeriodeSansCours`, un candidat écarté — pas une panne. Tout autre refus reste une panne, qui
  n'est jamais gardée en mémoire.
- **Dash recrée le contenu à chaque rappel**, filtre compris, quelle que soit la `key` React. Ce
  qui doit survivre à un filtre (la transition de chapitre) est décidé côté navigateur, dans
  `dessin.js`, par comparaison d'un attribut (`data-chapitre`).
- **Une modification Python demande de relancer le serveur** ; une modification de CSS ou de JS,
  seulement de recharger la page. Une vérification faite sur l'ancien serveur ment.
- **Vérifier à l'écran** : lancer sur une **copie** du dossier Pastory, jamais sur le vrai :
  `PASTORY_DOSSIER=<copie> .venv/Scripts/python.exe -c "from pastory.vues import application;
  application.lancer(hors_ligne=True, port=8085, navigateur=False)"`.
- **Il y a deux thèmes**, jour et nuit ([D-100](decisions.md)) : la nuit ne redéfinit que les rôles,
  donc une couleur nouvelle se déclare comme un rôle, dans les deux, et se vérifie dans les deux.
- `ruff check` est la règle ; `ruff format` n'est pas appliqué au dépôt : ne pas le lancer en masse.

## Les pièges des réglages et de la lecture, toujours vrais

- **Un contenu « actions » trouvé ne s'applique pas** : il ferait passer le fonds avant sa
  composition. Ne pas « corriger » cela sans relire [D-89](decisions.md).
- **Une panne n'est jamais gardée en mémoire** comme un trou ; un test le garde. La liste de Xetra
  écrit son lien de deux façons selon le serveur ([reglages-automatiques.md §2.3](reglages-automatiques.md)).
- **Avec `--export` (l'export d'un tiers), aucun appel réseau** n'est fait, ni recherche, ni
  cours, ni composition (règle 2). C'est voulu. La démonstration, elle, n'est pas un tiers : elle
  cherche en ligne comme un vrai portefeuille.
- **Les tests coupent six sources** par des fixtures automatiques (`tests/garde_fous.py`). Un test
  qui veut une recherche branche une source factice (`brancher_les_cotations`).
- **Les tests de la ligne de commande ajoutent deux titres reçus à la lecture**
  (`export_ligne_de_commande.titres_recus()`) ; la fixture `lecture_pure` retire l'ajout.
- **La date d'ouverture du PEA** se lit dans l'ordre des **horodatages** : une clôture et une
  réouverture tombent le même jour, et la sortie qui clôt un plan n'est pas un retrait du suivant.
- **Le brut des dividendes néerlandais est faux dans l'export**, sans marque ([D-84](decisions.md)).
  C'est une limite **affichée**, pas un réglage.
- **Le Saveback** est affiché comme non traité, en attendant un export plus récent du propriétaire.
  La démonstration en contient une ligne, exprès.

## Ce que le bloc 9.5 doit savoir

**L'édition de fichiers doit disparaître** ([D-78](decisions.md), et le
[§6 du contrat](conception-interface.md)). Sa raison porte loin : **une bidouille qui fait peur
fait douter de l'application entière**, or ce projet ne tient que sur la confiance dans ses
chiffres.

- **Le contenu des écrans existe** : pour chaque actif et chaque réglage, un `Reglage` dit la
  valeur retenue, sa source, sa date, ce qui a été vérifié, ou le motif de son absence ; et, si
  l'utilisateur a corrigé, ce que la source donnait. `pastory actifs`
  (`pastory/reglages/rapport.py`) en est la version texte : l'écran la reprend.
- **Ce que l'écran doit permettre de corriger** : ticker et devise, type, TER, contenu, spread,
  répartition, refus du secours (`secours = "aucun"`), date du PEA.
- **L'application trouve, applique et montre ; l'utilisateur peut corriger** ([D-80](decisions.md)).
  Ce qui protège d'une valeur fausse, ce sont les contrôles et la visibilité de la source, pas un
  clic de validation.
- **Un écran qui écrit dans le fichier doit le relire et le réécrire sans perdre ses
  commentaires** ([D-92](decisions.md), [D-94](decisions.md)) : ce sont eux qui rendent le fichier
  compréhensible à la main. tomlkit serait une **dépendance nouvelle**, donc un changement de
  `pyproject.toml` — voir, plus bas, ce que cela déclenche sur cette machine.
- **En démonstration, une correction s'écrirait dans le dossier de la démonstration** : c'est le
  comportement attendu, et à vérifier.

### Le contrat, et où il est

**Tout est dans [conception-interface.md](conception-interface.md).** Ne pas rouvrir les
arbitrages : les cinq onglets, leur ordre et leurs filtres sont fixés, et le §5 dit les quatre
états que chaque bloc doit prévoir. Là où le document et l'écran se contredisent, **l'application
a raison** et le document est à corriger : les maquettes de l'étape 8 ont été retirées du dépôt
([D-108](decisions.md)) et ne se lisent plus que dans l'historique git.

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

### Les pièges d'affichage trouvés à l'étape 8, qui valent pour tout écran nouveau

*(Les fichiers `maquette.js` et `style.css` cités ci-dessous sont ceux des maquettes, aujourd'hui
dans l'historique git ; leurs héritiers sont `assets/dessin.js` et `assets/pastory.css`.)*

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

- **Le logo est choisi** (étape 9 bis, variante « B · Signet » de `maquettes/logo/`) : un livre
  fermé en aplat d'or, le dos en creux, un signet qui dépasse. Il est dessiné dans `dessin.js`
  (`logo()`, coloré par le thème) et dans `assets/favicon.svg`.
- **L'application s'appelle Pastory** ([D-74](decisions.md)), et plus « DashBoard Trade
  Republic ». Le paquet est `pastory/`, la commande est `uv run pastory …`, le dossier personnel
  de l'utilisateur est `Pastory`. **Le nom « Trade Republic » ne subsiste que là où il désigne la
  banque** : l'adaptateur, l'export, la documentation des données. Deux choses restent à faire
  **par le propriétaire, hors dépôt** : renommer le dépôt GitHub et le dossier local du projet.
  **Renommer le dossier local casse les icônes** de l'étape 10, qui pointent sur lui : relancer
  ensuite `.venv\Scripts\python.exe -m pastory.cli installer`.
  *Attention en relisant les vieux documents :* `notes-initiales.md` cite volontairement l'ancien
  nom deux fois, parce qu'il y désigne un fichier PDF et un souvenir — ne pas les « corriger ».
- **`uv run` peut échouer deux fois de suite sur OneDrive, puis réussir.** Dès que
  `pyproject.toml` change, uv réinstalle le projet et bute sur OneDrive : d'abord
  `failed to hardlink` (os error 396), puis `failed to remove directory … Accès refusé`
  (os error 5). Remède : `$env:UV_LINK_MODE = "copy"`, puis **relancer la même commande** — la
  deuxième passe. Ce n'est pas un échec des tests, et le message le dit mal.
- **Après un changement de `pyproject.toml`, `uv run pastory ouvrir` échoue** (constaté le
  2026-10-09, après l'ajout de numpy) : uv veut réinstaller Pastory, bute d'abord sur OneDrive
  (`os error 396`, contourné par `UV_LINK_MODE=copy`), puis sur le certificat de l'antivirus en
  téléchargeant l'outil de construction `editables` (`UnknownIssuer`, même avec `--native-tls`).
  L'environnement, lui, est intact : **`uv run --no-sync pastory ouvrir`** lance Pastory. Pour
  lever le blocage, il faut une synchronisation réussie, l'analyse HTTPS de l'antivirus
  suspendue le temps de `UV_LINK_MODE=copy uv sync --native-tls`. **C'est pourquoi les icônes de
  l'étape 10 appellent `.venv\Scripts\pythonw.exe` directement, jamais `uv run`** — et pourquoi
  toute dépendance nouvelle (tomlkit, au bloc 9.5) demandera cette synchronisation, antivirus
  suspendu.
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
