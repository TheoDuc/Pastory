# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-30**, fin de la conception (étape 8).

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 8 bis : les compléments de décision.
```

---

## Où en est le projet

- **Étapes 0 à 8 terminées.** Le moteur est complet, et **l'interface est conçue**. Les maquettes
  vivent dans [maquettes/](../maquettes/) : de vrais fichiers HTML et CSS, ouvrables tels quels, avec
  un portefeuille fictif d'utilisateur type et quatre jeux de données commutables. Cinq onglets :
  Synthèse, Les actifs, Diversification, Frais et taxes, Détail des calculs. **La feuille de style
  deviendra `dashboard_tr/vues/assets/dashboard.css` telle quelle** ([D-31](decisions.md)) : c'est
  le livrable, pas une illustration.
- **Prochaine : étape 8 bis**, les compléments de décision. Trois choses, et la première est du
  code : **D-72** (la source de secours par actif), **Q-48** et **Q-49** à trancher, et le
  **document de conception** à finir.
- **Questions ouvertes** : **Q-26** (rapprocher le PEA), non bloquante ; **Q-48** (« non
  transparisé ») et **Q-49** (la place de la retenue sur dividendes), toutes deux pour l'étape 8 bis.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [maquettes/](../maquettes/) | **Les écrans**, en HTML et CSS. `index.html` s'ouvre directement ; `style.css` est le livrable ; `maquette.js` construit les écrans ; `donnees/` porte le portefeuille fictif |
| [conception-interface.md](conception-interface.md) | **Le contrat de l'étape 9.** §1 l'inventaire de ce que le moteur produit, §2 le vocabulaire d'écran, §3 les règles d'affichage. **Les écrans retenus restent à écrire** |
| [format-pivot.md](format-pivot.md) | **Le contrat** : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | Les couches, leurs frontières, le trajet d'un chiffre |
| [glossaire.md](glossaire.md) | Chaque formule, dont le gain, le TRI, le TWRR (§4, §5), les coûts (§6), la diversification (§8) |
| `dashboard_tr/` | Le moteur complet : pivot, adaptateur, données externes, paramètres, moteur, `cli.py` (12 commandes) |
| [decisions.md](decisions.md) | D-01 à D-73. L'étape 8 a ajouté **D-73** (les frais en trois niveaux) |

**Ce qui n'existe pas encore :** le branchement de l'interface sur le moteur (étape 9), et les trois
compléments de l'étape 8 bis.

---

## Ce que l'étape 8 bis doit savoir

### Le travail qui reste, dans l'ordre

1. **D-72, la source de secours par actif.** La seule partie qui est du code. Commencer par une
   **recherche** : ce qu'Amundi publie réellement par ISIN français — la répartition de l'**indice
   suivi**, ce que demande [D-64](decisions.md) — et un ou deux recours de plus. Critères : gratuit,
   interrogeable par ISIN, rend des **codes**, porte une date d'arrêté. Puis un module de plus dans
   `donnees_externes/`, branché par le **protocole existant** de `moteur/diversification.py`, la
   source se **déclarant par actif** dans `actifs.toml` comme le contenu déclaré ([D-71](decisions.md)).
   **Si la recherche ne trouve rien d'exploitable, c'est un résultat** : on l'écrit, l'actif reste
   « non couvert », et la déclaration à la main reste le recours.
2. **Q-48 et Q-49**, à poser au propriétaire — Q-48 après la recherche, qui dira si une source
   indique les fonds de fonds de façon fiable.
3. **Le document de conception**, §4 et suivants : les écrans retenus, leurs états, les règles.

### Un ajout au protocole, que l'étape 8 a identifié

La **règle de pays n'est portée par aucune donnée** : elle est seulement implicite dans la source
(`donnees_externes/actions.py` = siège social, `extraetf.py` = pays d'activité). Or
[D-66](decisions.md) demande qu'elle soit affichée et [D-72](decisions.md) qu'elle le soit **ligne
par ligne**. Il faut donc un champ de plus dans `CompositionDUnActif`
(`moteur/diversification.py:78`), à côté de la source.

### Ce que les relectures ont appris, et qui vaut pour l'étape 9

Sept passes de relecture par le propriétaire. Les pièges trouvés sont tous des pièges **d'affichage
qui font douter des chiffres** :

- **`var()` n'est pas interprété dans un attribut SVG** (Chrome, Safari). Toutes les couleurs des
  graphiques étaient invalides, et l'anneau ne montrait pas les couleurs de ses poches. Règle : une
  couleur posée en **attribut SVG** s'écrit en clair, une couleur posée en **CSS** passe par la
  variable. `maquettes/maquette.js` porte les deux palettes, et un script vérifie qu'elles
  concordent ;
- **sans `color-scheme: only light`**, le mode sombre automatique du navigateur inverse les
  clartés : le bleu le plus foncé s'affiche le plus clair. Le propriétaire l'a constaté sur une
  capture, et c'était bien un défaut — mais pas celui qu'on croyait. Conséquence plus grave que les
  anneaux : un gain en sauge inversé vire au rouge ;
- **un SVG sans règle de taille** prend sa taille intrinsèque et remplit la page. Arrivé en
  supprimant une classe voisine inutilisée, qui a emporté neuf règles avec elle ;
- **un anneau ne porte pas de chiffre** : l'étiquette doit choisir sa couleur selon la part, et
  devient illisible sur les teintes intermédiaires. Le classement chiffré à côté fait foi ;
- **une couleur suit son poste, jamais son rang** : sinon décocher une poche repeint les survivants ;
- **le sens de lecture d'un anneau n'est pas évident** : trier par taille décroissante, sans quoi la
  petite part collée avant midi se confond avec la première ligne de la légende ;
- **le gain n'est pas la somme d'une colonne**, et l'écran doit le dire. Il se calcule sur les
  montants bruts ([D-21](decisions.md)) là où le capital net investi est net de frais et réduit au
  prorata des ventes ([D-12](decisions.md)).

### Comment le propriétaire relit

Il regarde l'écran, pas le code, et il trouve des défauts réels — y compris ceux qui viennent de son
navigateur. **Quand il signale une incohérence de chiffres, la vérifier par le calcul avant de
conclure** : deux fois sur trois le code avait raison et l'affichage avait tort, une fois sur trois
c'était un vrai bug de calcul. Les scripts de contrôle écrits à l'étape 8 sont dans le dossier
temporaire de la session, pas dans le dépôt : les réécrire au besoin.

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
