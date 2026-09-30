# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-30**, fin de l'étape 8 bis (la source de secours, Q-48 et Q-49
> tranchées, et le document de conception fermé).

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 9 : la réalisation de l'interface.
```

---

## Où en est le projet

- **Étapes 0 à 8 bis terminées.** Le moteur est complet, l'interface est **conçue**, et le
  document de conception est **fermé** : ses §4 (les écrans retenus) et §5 (leurs quatre états)
  ont été écrits à l'étape 8 bis. L'étape 9 peut s'appuyer dessus sans rien rouvrir.
- Les maquettes vivent dans [maquettes/](../maquettes/) : de vrais fichiers HTML et CSS, ouvrables
  tels quels, avec un portefeuille fictif d'utilisateur type et quatre jeux de données
  commutables. Cinq onglets : Synthèse, Les actifs, Diversification, Frais et taxes, Détail des
  calculs. **La feuille de style deviendra `pastory/vues/assets/pastory.css` telle quelle**
  ([D-31](decisions.md)) : c'est le livrable, pas une illustration.
- **Prochaine : étape 9**, brancher l'interface retenue sur le moteur, écran par écran, en
  commençant par la synthèse.
- **Questions ouvertes** : **Q-26** seule (aller chercher le second compte-titres pour rapprocher
  le PEA), et elle n'est pas bloquante. Q-48 et Q-49 ont été tranchées à l'étape 8 bis.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [maquettes/](../maquettes/) | **Les écrans**, en HTML et CSS. `index.html` s'ouvre directement ; `style.css` est le livrable ; `maquette.js` construit les écrans ; `donnees/` porte le portefeuille fictif |
| [conception-interface.md](conception-interface.md) | **Le contrat de l'étape 9, complet.** §1 l'inventaire de ce que le moteur produit, §2 le vocabulaire d'écran, §3 les règles d'affichage, §4 les cinq écrans retenus, §5 leurs quatre états (vide, partiel, estimé, en erreur) |
| [format-pivot.md](format-pivot.md) | **Le contrat** : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | Les couches, leurs frontières, le trajet d'un chiffre |
| [glossaire.md](glossaire.md) | Chaque formule, dont le gain, le TRI, le TWRR (§4, §5), les coûts (§6), la diversification (§8) |
| `pastory/` | Le moteur complet : pivot, adaptateur, données externes, paramètres, moteur, `cli.py` (12 commandes) |
| [decisions.md](decisions.md) | D-01 à D-77. L'étape 8 bis a ajouté **D-74** (le nom Pastory), **D-75** (le premier niveau des frais), **D-76** (« non transparisé » au glossaire seul) et **D-77** (la source de secours Amundi) |

**Ce qui n'existe pas encore :** le branchement de l'interface sur le moteur. C'est toute
l'étape 9.

---

## Ce que l'étape 9 doit savoir

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
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run pastory emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run pastory lire --export <dossier>` (idem pour `positions`).
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
