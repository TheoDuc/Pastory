# Charte graphique de Pastory

**Ce document fait référence** pour toute modification de l'interface, dans cette session et
les suivantes. Il fixe l'identité décidée à l'étape 9 bis ([D-98](decisions.md)). Les règles
d'affichage des chiffres sont dans le [contrat d'interface](conception-interface.md) §3 : la
charte ne les remplace pas, elle les habille.

Les valeurs vivent dans **un seul fichier**, [`pastory/vues/assets/theme.css`](../pastory/vues/assets/theme.css) :
couleurs, polices, tailles, espacements, durées et gabarit des graphiques. **Aucune couleur n'est
écrite en dur ailleurs.** Un test le vérifie (`tests/vues/test_feuille_de_style.py`), et un
autre recalcule les contrastes de la table du §3.3 à partir de ce fichier.

---

## 1. Le concept

L'application s'appelle **Pastory** (*Past* + *Story*). Elle raconte l'histoire d'un patrimoine
qui s'écrit dans le temps. Sa direction artistique est celle d'un **livre ancien relié, à la
dorure discrète** :

- la **reliure** est brun profond : la navigation, la couverture ;
- les **pages** sont en papier crème : le contenu ;
- **l'or** n'apparaît qu'en touches rares.

### La règle cardinale

**La métaphore du livre passe par la STRUCTURE et la TYPOGRAPHIE, jamais par l'imitation de
matières.** On veut un livre bien composé, pas un faux livre.

Interdits, sans exception :

- texture de cuir ou de papier, en image comme en dégradé CSS ;
- dégradés métalliques pour simuler l'or ;
- ombres portées (`box-shadow`, `text-shadow`, `filter: drop-shadow`) ;
- effets de relief, biseaux, gaufrages ;
- coins de page cornés, pages en 3D qui se courbent.

Ce qui sépare, c'est **l'espace et le filet fin** — jamais la boîte ni l'ombre.

---

## 2. La palette

Douze couleurs de base, celles du propriétaire, plus six variantes mesurées (§2.3). Rien
d'autre.

### 2.1 La reliure — navigation, couverture

| Jeton | Valeur | Emploi |
|---|---|---|
| `--brun-reliure` | `#2B2118` | fond de la navigation et de la couverture |
| `--brun-reliure-clair` | `#3A2C20` | la bande des filtres, le survol sur la reliure |
| `--or-vieilli` | `#B8955A` | accents **sur fond sombre** ; ornements sur les pages (§2.4) |
| `--or-clair` | `#D4B87A` | survol et état actif sur fond sombre |

### 2.2 Les pages — contenu

| Jeton | Valeur | Emploi |
|---|---|---|
| `--papier` | `#F4ECDD` | le fond des pages |
| `--papier-ombre` | `#EAE0CC` | zones secondaires : colophon, en-têtes de tableau, champs |
| `--filet` | `#D8CBB3` | séparateurs fins |
| `--encre` | `#2A211A` | texte principal |
| `--encre-pale` | `#6B5B4B` | texte secondaire, libellés |

### 2.3 Les données, et les variantes mesurées

| Jeton | Valeur | Emploi |
|---|---|---|
| `--sauge` | `#5F7A5A` | gain : **traits et aplats** seulement |
| `--terracotta` | `#A4553A` | perte : traits et aplats |
| `--ocre` | `#9C7A3C` | mise en valeur : la courbe du capital net investi |
| `--sauge-texte` | `#4D6748` | gain **écrit** |
| `--terracotta-texte` | `#974B31` | perte écrite |
| `--ocre-texte` | `#7A5C24` | « Estimé », « Partiel », « Peu fiable »… écrits |
| `--reliure-texte-pale` | `#BFAF95` | texte secondaire sur la reliure (filtres, bouton discret) |
| `--filet-fort` | `#93826A` | contour d'une commande (bouton « ? », flèches), hachure de l'absent |
| `--poche-2` | `#625241` | la poche du milieu (§2.5) |
| `--poche-3` | `#9A8566` | la poche la plus claire (§2.5) |

**Pourquoi des variantes.** Mesurée au niveau AA des WCAG (4,5:1 pour du texte), la sauge de la
consigne fait **4,05:1** sur le papier et l'ocre **3,40:1** : lisibles en trait épais, pas en
texte. La consigne demande de corriger « en restant dans la famille » : chaque couleur garde sa
teinte pour les traits et les aplats (seuil 3:1), et reçoit une version plus foncée **de la même
famille** pour le texte. La terracotta passe de justesse sur le papier (4,54:1) mais pas sur le
papier ombré (4,08:1) : elle a aussi sa variante.

### 2.4 L'or : rare, et jamais en texte sur fond clair

- **Sur les pages, l'or n'est jamais du texte** : 2,39:1 sur le papier, très en dessous du
  seuil. Il y sert **uniquement d'ornement** — filets, fleurons, numéros de chapitre en grand —
  et l'information qu'il porte est toujours redite en encre (le titre du chapitre dit son
  numéro ; le numéro est `aria-hidden`).
- **Sur la reliure, il peut porter du texte** : le nom de l'application, l'onglet actif, les
  titres courts de la couverture (5,61:1 sur `--brun-reliure`).
- Le signet de l'onglet actif est un aplat d'or, sans texte.

### 2.5 Les poches : trois bruns d'encre

Une poche (PEA, CTO, Crypto) a **sa** couleur partout où elle apparaît ([D-96](decisions.md)).
Ce sont **trois bruns de la même famille**, distincts par la clarté : `#2A211A` (PEA),
`#625241` (CTO), `#9A8566` (Crypto). Arbitrage du propriétaire (étape 9 bis) : la sauge et l'ocre,
que la consigne proposait, ont déjà un sens partout ailleurs (gain, estimé), et une poche sauge
se lirait comme un état.

Mesurée par le validateur du skill *dataviz* en mode **rampe** (une teinte, clarté monotone) :
écarts de clarté OKLCH 0,19 et 0,18 (seuil 0,06), écarts OKLab ×100 de **19,4** et **17,9** en
vision normale (plancher 15), 17,7 au pire en vision protanope ou deutéranope (cible 8), et la plus
claire à **3,02:1** sur le papier (seuil 3). Une rampe de bruns échoue **par nature** au plancher de
saturation d'une palette catégorielle, et c'est voulu : une poche n'est **jamais** désignée par sa
seule couleur — son nom est toujours écrit à côté de sa pastille.

Une couleur suit sa poche, jamais son rang : décocher une poche ne repeint pas les autres.

### 2.6 Gains et pertes

**Jamais par la couleur seule** : un gain porte toujours `+`, une perte toujours `−` (le vrai
signe moins), écrits par `pastory/vues/format.py`. Le signe se lit avant la couleur ; un lecteur
daltonien ne perd rien.

### 2.7 Le mode sombre automatique du navigateur

Le thème de jour le refuse (`color-scheme: only light`) : sans cela, le navigateur assombrit la
page de lui-même, inverse les clartés, et un gain en sauge peut virer au rouge. Le seul sombre
admis est celui que Pastory dessine : la lecture de nuit (§2.8), qui dit au navigateur qu'elle est
déjà sombre (`color-scheme: dark`). La reliure brune, elle, n'est pas un mode sombre : c'est la
couverture du livre.

### 2.8 La lecture de nuit

Le même livre, lu à la lampe ([D-100](decisions.md)) : les **pages** deviennent un brun très
profond, un cran plus clair que la reliure pour que la navigation reste distincte ; l'**encre**
devient crème ; l'**or** ne change pas et reste rare. Ce n'est pas le « style moderne sombre »
que le propriétaire voulait éviter : c'est la même famille, inversée.

| Jeton (nuit) | Valeur | Rôle |
|---|---|---|
| `--nuit-reliure` | `#17110C` | navigation, couverture (la reliure, plus sombre que les pages) |
| `--brun-reliure-clair` | `#3A2C20` | la bande des filtres : nettement plus claire que la navigation et que le colophon (à `#2B2118`, l'écart avec le colophon était imperceptible) |
| `--nuit-livre` | `#1A140F` | le fond du livre, derrière les boîtes ; le colophon |
| `--nuit-page` | `#241C15` | le fond des boîtes |
| `--nuit-page-ombre` | `#2E241B` | colophon, zones secondaires |
| `--nuit-filet` | `#44372A` | séparateurs |
| `--nuit-filet-fort` | `#7D6B55` | contours, hachures de l'absent (3,28:1) |
| `--nuit-encre` | `#EDE3D0` | texte (13,18:1) |
| `--nuit-encre-pale` | `#B6A68C` | texte secondaire (7,05:1) |
| `--nuit-sauge-texte` | `#9DB894` | gain (7,76:1) |
| `--nuit-terracotta-texte` | `#E0967B` | perte (7,04:1) |
| `--nuit-ocre` / `--nuit-ocre-texte` | `#C49A55` / `#D7B46F` | mise en valeur : trait (6,47:1), texte (8,50:1) |
| poches | `#EDE3D0`, `#B09C7E`, `#7A6852` | la rampe inversée : la plus marquée reste au PEA |

Tous les textes passent le niveau AA sur la page et sur la page ombrée (6,37:1 au plus faible) ;
la rampe des poches passe le validateur dataviz en rampe (écarts OKLab ×100 de 21,7 et 17,4, la
plus sombre à 3,14:1).

**Comment c'est construit.** La nuit ne redéfinit que les **rôles** du thème (`--fond-page`,
`--texte`, `--gain`…), dans un bloc `:root[data-theme="sombre"]` de `theme.css`. La feuille et le
gabarit des graphiques ne lisent que des rôles : ils suivent d'eux-mêmes. **Une couleur nouvelle
se déclare donc dans les deux thèmes**, et le test des contrastes les vérifie tous les deux.

**Comment on y passe.** Par défaut, Pastory suit le réglage clair / sombre du système. Le bouton
jour / nuit (une lune le jour, un soleil la nuit), dans la navigation et dans le coin de la
couverture, permet de choisir ; le choix est retenu par le navigateur. Le thème est posé avant
le premier affichage : aucune page ne s'affiche un instant dans le mauvais thème.

---

## 3. La typographie

### 3.1 Deux familles, embarquées

Aucune police n'est chargée sur le réseau ([D-31](decisions.md)) : les fichiers sont dans
`pastory/vues/assets/polices/`, sous licence SIL Open Font 1.1.

- **Serif de caractère : EB Garamond** — titres, numéros de chapitre, le grand chiffre de chaque
  page, les phrases d'introduction en italique.
- **Sans-serif neutre : IBM Plex Sans** — données, libellés, tableaux, filtres.

**Pourquoi EB Garamond plutôt que Cormorant Garamond.** Cormorant est une coupe de **titrage** :
contraste très fort, œil petit, déliés qui disparaissent sous 20 px — or les phrases
d'introduction sont en italique vers 17 px, et l'écran de Windows rend mal les déliés fins. EB
Garamond est redessinée d'après les fontes de **texte** de Garamond : elle tient du corps de lecture
au grand chiffre de la synthèse, avec une vraie italique. Et ses **chiffres par défaut sont
alignés et à chasse fixe** (mesuré : `1111` et `0000` ont la même largeur), ce qu'il faut pour un
montant en grand.

**Ce que les fichiers n'ont pas.** La version de Google Fonts (paquet *fontsource*) a perdu les
petites capitales (`smcp`) et les chiffres elzéviriens (`onum`) : mesuré, ils ne changent rien. IBM
Plex Sans n'a pas de petites capitales dessinées non plus. Les « petites capitales » de la charte
sont donc des **capitales réduites et espacées** (§3.2), jamais une synthèse du navigateur
(`font-variant-caps`), qui donne des capitales maigres.

### 3.2 Les règles

- **Tous les montants et pourcentages en chiffres à chasse fixe** :
  `font-variant-numeric: tabular-nums lining-nums`, pour que les colonnes s'alignent. C'est la
  classe `.nb`, et les conteneurs de chiffres (tuiles, tableaux, colophon, axes) la portent.
- **Libellés courts** (en-têtes d'indicateurs, catégories, colophon) **en petites capitales** :
  capitales réduites (`--petites-capitales-taille`), espacées (`--petites-capitales-espace`).
- **Une hiérarchie nette** : chaque page a **un** point d'entrée nettement plus grand que le
  reste. Sur la synthèse, c'est la valeur des actifs ([D-99](decisions.md)) ; sur les autres
  chapitres, le titre du chapitre.
- L'échelle des tailles est dans le thème (`--taille-*`) ; aucune taille de police n'est
  inventée ailleurs sans raison.

---

## 4. La structure : un livre

### 4.1 La couverture

L'écran d'accueil et de dépôt des données, et **le premier écran de chaque session** : c'est
d'elle que le livre s'ouvre.

- Fond `--brun-reliure`. Au centre, le logo et le nom **Pastory** en or, un filet et un petit
  fleuron.
- En dessous, une **étiquette** en papier (un aplat, comme l'étiquette de titre d'une reliure —
  pas une texture) qui porte le dépôt :
  - **sans données** : en une ou deux phrases, quel fichier déposer (l'**export des
    transactions**, fichier CSV) et où l'obtenir dans l'application Trade Republic, puis la zone de
    dépôt. Le chemin des menus est une seule constante (`CHEMIN_DANS_L_APPLICATION`,
    `adaptateurs/trade_republic/depot.py`) ;
  - **avec données** : la période couverte, la date de la dernière opération lue, le nombre de
    fichiers, l'alerte s'il y a des types d'opération inconnus, et deux actions : **« Ouvrir le
    livre »** et **« Déposer un export plus récent »**.
- Un fichier qui n'est pas un export est **refusé, avec une phrase sans jargon** qui dit ce qui ne
  va pas et où obtenir le bon fichier.
- Un export plus récent **s'ajoute** aux précédents : une opération présente dans deux fichiers
  n'est comptée qu'une fois ([D-80](decisions.md), [D-95](decisions.md)). Un export complet plus
  récent donne donc le même résultat qu'un remplacement. L'export ne contient pas sa date de
  création : la couverture donne celle de **la dernière opération lue**, et ne l'invente pas.
- **La couverture tient sur un écran, sans défiler** (retour du propriétaire) : le détail — les
  fichiers lus, ce que la lecture a trouvé, le dossier des exports — est dans un **volet replié**
  de l'étiquette, « Détail de la lecture ». **Une alerte ne se replie jamais** : un type
  d'opération inconnu, une période qu'aucun fichier ne couvre, un fichier ignoré restent visibles
  au-dessus des actions. Sur un écran peu haut, la couverture se resserre (logo et titre plus
  petits) pour tenir.
- La seule source des données est l'export officiel. **Aucune mention de pytr** ne subsiste dans
  l'interface ni dans la documentation destinée à l'utilisateur.

### 4.2 Les chapitres

Les sections sont des chapitres numérotés en chiffres romains :

| | Chapitre | Phrase d'introduction |
|---|---|---|
| I | Synthèse | Ce que valent vos actifs, et le chemin parcouru depuis le premier achat. |
| II | Les actifs | Chaque ligne du portefeuille : ce qu'elle a coûté, ce qu'elle vaut, ce qu'elle a rapporté. |
| III | Diversification | Où se trouve votre argent, en regardant à l'intérieur des fonds. |
| IV | Frais et taxes | Ce qui a été prélevé, ce que coûte la détention, et ce que coûterait la sortie. |
| V | Projections | Ce que pourrait devenir le portefeuille. |
| — | Annexe : détail des calculs | De quoi refaire chaque chiffre à la main. |

Chaque chapitre **s'ouvre** sur son numéro romain (ornement or), son titre en EB Garamond, et
sa phrase d'introduction en italique, qui dit ce que montre la page — **sur une seule ligne**,
pour que la page reste aux chiffres (D-102). C'est la brique
`ouverture()` de `pastory/vues/briques.py` : un seul endroit.

Le **détail des calculs** reste une page discrète ([conception-interface.md](conception-interface.md)
§4.6) : c'est l'**annexe** du livre, ouverte depuis le bouton discret à droite de la navigation,
sans numéro romain.

### 4.3 La navigation

Une barre supérieure en `--brun-reliure`. **Le logo et le nom « Pastory » ramènent à la
couverture** : c'est le titre du livre, et le refermer est le geste qu'on attend d'un nom en tête
de page. Chaque onglet porte son numéro romain puis son nom.
**L'onglet actif est signalé par un signet** : un petit ruban d'or, plat, qui descend sous la
barre — à la place d'un bouton surligné. Le nom de l'onglet actif passe en or clair.

La bande des **filtres** (période, type, poches), quand l'onglet en a, suit la navigation en
`--brun-reliure-clair`. Chaque groupe de filtres garde son étiquette serrée contre ses boutons, et
les groupes respirent entre eux. À droite, en italique, **ce que les filtres ont retenu** : la
période en clair (« Du … au … · 2 mois »). **Il n'y a pas de troisième bande** ([D-103](decisions.md)).

**Un chapitre sans filtre garde sa bande**, de la même hauteur, pour que le livre ait le même
rythme d'une page à l'autre ([D-104](decisions.md)) : elle porte alors **le sommaire du
chapitre**, jamais un faux filtre — les rubriques de la Diversification, des liens vers les trois
niveaux des Frais, et pour les Projections une phrase qui rappelle que c'est une hypothèse.

### 4.4 Le colophon

Ce qui dit d'où viennent les chiffres et de quand ils datent est **le colophon du livre**. Ce
n'est plus une bande sous la navigation — elle empilait huit informations sur une ligne serrée et
faisait « paramètres » ([D-103](decisions.md)) : il est **à droite du titre de chaque chapitre**,
en petites capitales discrètes, et ne montre qu'**une** chose d'un coup d'œil, **la date des
cours** (« Cours arrêtés au … »). Un lien en italique, **« d'où viennent ces chiffres »**, ouvre le
reste dans une bulle : la source, la période de l'export, les arrêtés de composition, le nombre
de positions. **Une valeur partielle** (un actif sans cours) reste toujours visible à côté de la
date, jamais dans la bulle. Aucune information n'a été supprimée : c'est ce qui permet de dire
« ces chiffres sont d'hier ».

### 4.5 Le fleuron de chapitre

Entre l'ouverture d'un chapitre et sa page, un **filet d'or sur toute la largeur, le losange au
centre** : la seule séparation ornée des pages (retour du propriétaire, qui l'avait aimé sur la
couverture). À l'intérieur des boîtes, le filet ordinaire suffit : un ornement répété partout ne
sépare plus rien.

---

### 4.6 Les champs de saisie

Les seuls champs de l'application (chapitre V) sont des composants de Dash. Dash 4 les colore avec
ses propres variables (`--Dash-…` : un violet, des bleus) : le thème les fait **pointer vers nos
rôles** (`:root:root`, qui l'emporte sur la feuille de Dash), si bien qu'ils suivent la palette et
la lecture de nuit. Ni les boutons « − / + » de Dash ni les flèches du navigateur : un montant se
tape, et il est aligné à droite, en chiffres à chasse fixe.

## 5. Les pages

- Contenu limité à **environ 1 200 px** (`--largeur-page`), centré, marges généreuses. Le contenu
  ne s'étale plus sur toute la largeur de l'écran.
- **Des boîtes, bien marquées** ([D-102](decisions.md), retour du propriétaire, qui les a
  jugées « beaucoup plus classes » que les filets seuls) : chaque élément — bloc, indicateur,
  carte d'actif — est une boîte au fond de page (`--fond-page`), bordée d'un filet
  (`--bord-bloc`), posée sur le fond du livre (`--fond-livre`, un ton plus sombre). C'est la
  frontière qui sépare, **jamais une ombre ni un relief** : la règle cardinale tient.
- **Chaque page tient sur un écran autant que possible.** La synthèse tient sans défiler en
  1 366 × 900 et en 1 920 × 1 080 ; un portable en 768 px de haut défile d'une centaine de pixels.
- **Pas de barres colorées décoratives** au-dessus des indicateurs. La couleur d'un indicateur
  est celle de son chiffre (et le signe la double).
- Les tableaux ne gardent que des filets horizontaux.
- **Synthèse** : la valeur des actifs est le point d'entrée — la plus grande boîte de la première
  rangée, en serif, nettement plus grande que les quatre autres (gain, TRI, TWRR, capital net
  investi). Le signalement **« Peu fiable »** du TRI est conservé, et **il s'explique lui-même** :
  au survol (ou au clic, ou au clavier), la marque ouvre la bulle qui dit que la période est trop
  courte pour se fier à un taux annualisé. Une marque sans explication à portée de souris
  inquiète sans rien apprendre.

---

## 6. Les graphiques

**Un gabarit unique**, dans le thème (`--graphique-*`), réutilisé partout. Aucune couleur par
défaut d'une bibliothèque : il n'y en a pas — les graphiques sont dessinés en SVG par
`pastory/vues/assets/dessin.js`, et colorés **par classes CSS** (`fill` et `stroke` acceptent
`var()` en CSS ; un attribut SVG, lui, ne l'interprète pas — piège de l'étape 8).

- **Courbe principale** (capital brut) : `--encre`, 2 px.
- **Capital net investi** : `--ocre`, trait pointillé fin. Il monte en escalier.
- **Pas de remplissage** entre ou sous les courbes.
- **Grilles horizontales seulement**, très pâles (`--filet`) ; aucune grille verticale.
- **Libellés au bout des courbes**, plutôt qu'en légende ; écartés l'un de l'autre s'ils se
  chevauchent. Une ligne sous le graphique dit ce que chaque courbe représente.
- **Axes discrets**, en sans-serif, couleur `--encre-pale`, chiffres à chasse fixe.
- La **boîte de lecture qui suit la souris** ne change pas
  ([conception-interface.md](conception-interface.md) §3.2) : seules ses couleurs suivent la
  charte.
- **Répartition par poche** : une **barre horizontale empilée fine**, une poche par segment,
  séparés d'un filet de papier ; en dessous, les montants et les pourcentages alignés. Les poches
  dans leurs trois bruns (§2.5). Plus d'anneau.
- **La projection** (chapitre V) : le total versé en ocre pointillé, la courbe sans aléa ou la
  médiane en encre, les quantiles 25 % et 75 % en trait fin, 10 % et 90 % en pointillé pâle
  (`--graphique-eventail`) — des lignes seules, l'éventail n'est pas rempli.
- **Ce qui manque** (non couvert, non attribué) : hachures `--filet-fort` sur papier, pour ne
  jamais se confondre avec un poste réel.

---

## 7. Les animations

- **Ouverture du livre** (de la couverture au chapitre I) : **un seul moment marquant**, en moins
  de 800 ms — la couverture brune s'efface vers la gauche, comme on l'ouvre, et découvre la page.
  Elle se joue **à chaque ouverture** : chaque fois qu'on passe de la couverture à la synthèse par
  « Ouvrir le livre » (retour du propriétaire, qui l'a préféré à « une fois par session »).
- **Changement de chapitre** : une transition courte qui **évoque** la page sans l'imiter — un
  léger glissement horizontal combiné à un fondu, **300 ms au plus**. Jamais de page en 3D qui se
  courbe. Un changement de filtre n'est pas un changement de chapitre : rien ne bouge.
- **Les cartes d'actifs, d'une page à l'autre** : un glissement très court (170 ms), dans le sens
  où l'on feuillette.
- **`prefers-reduced-motion`** : si l'utilisateur a demandé moins d'animations à son système, tout
  est remplacé par un simple fondu.
- **Une transition ne retarde jamais l'affichage des données ni ne bloque un clic** : les données
  sont dessinées tout de suite, l'animation ne fait que les accompagner, et le voile de l'ouverture
  ne capte pas la souris.

Les durées sont des jetons du thème (`--duree-*`).

---

## 8. Le logo

Un **livre fermé**, dessiné en quelques traits simples, **en or sur fond brun reliure**. Au
maximum **un** détail évoquant l'ancienneté. Pas de dégradé, pas d'ombre, **pas plus de deux
couleurs**. Il doit rester **lisible à 16 px** (favicon).

Il existe en deux formes :

- le dessin `logo` de `dessin.js`, coloré par le thème : la navigation et la couverture ;
- `pastory/vues/assets/favicon.svg`, l'icône de l'onglet du navigateur.

Les variantes proposées et le choix du propriétaire sont dans [maquettes/logo/](../maquettes/logo/).

---

## 9. Les exceptions, assumées

- **Les drapeaux** de la diversification sont des images de vrais drapeaux
  (`assets/drapeaux/`), en couleurs : un drapeau désaturé ne se reconnaît plus, et il sert à
  **repérer** une ligne. Ce ne sont pas des couleurs d'interface.
- **Le favicon** est une image autonome, chargée hors de la page : une variable CSS ne s'y applique
  pas. Ses deux couleurs sont écrites en clair, et un test vérifie qu'elles sont celles du thème.

---

## 10. Vérifier une modification

Avant de considérer un changement d'interface comme fini :

1. **aucune couleur hors palette** à l'écran ni dans les graphiques (le test des couleurs en dur,
   puis un relevé des couleurs calculées dans le navigateur) ;
2. **aucun texte or sur fond clair** ;
3. **tous les montants en chasse fixe** ;
4. **les chiffres affichés sont identiques** à ceux d'avant : une modification visuelle ne change
   aucun calcul ;
5. le rendu tient à **1 366 px** (ordinateur portable) et en écran large ;
6. **les points 1 à 3 valent dans les deux thèmes**, jour et nuit (§2.8) ;
7. **la couverture tient sans défiler**, y compris sur un portable (environ 660 px de haut une
   fois la barre du navigateur déduite).
