# Cahier de vérification — étape 10

Trois volets : **le lancement** par l'icône, **la démonstration**, et **le ménage**. L'étape ne
calcule aucun chiffre nouveau : ce cahier vérifie des comportements, et que rien n'a bougé dans les
chiffres. Toutes les valeurs écrites ici sont fictives ou publiques ([D-03](../decisions.md)).

---

## 1. Aucun chiffre n'a changé

Chaque nombre de chaque écran a été relevé sur une copie des données du propriétaire, hors ligne,
avec le code d'avant l'étape puis avec celui d'après : **105 états** (la couverture, la synthèse et
l'annexe pour chaque période et chaque choix de poches, les actifs pour chaque type, les quatre
rubriques de la diversification, les frais, les projections), **12 380 nombres**. Les deux relevés
sont identiques, au caractère près.

La comparaison a été refaite après les corrections de la relecture (§5) : identiques encore.

Deux faux écarts sont apparus en chemin, et aucun ne venait du code :

- la copie avait reçu des cours plus récents, par un essai en ligne fait entre les deux relevés ;
- la session avait passé minuit : « aujourd'hui » entre dans les durées, les taux annualisés et
  les dates affichées, qui bougent donc d'un jour à l'autre avec n'importe quel code.

**Une comparaison avant / après n'a de sens que hors ligne, sur la même copie, et le même jour.**

### À vérifier par toi

- [ ] Ouvre Pastory par son icône : la valeur des actifs, le gain, le TRI et le TWRR de la synthèse
  sont ceux que tu connais (aux cours du jour près).
- [ ] « Les actifs » → l'ETF dont tu avais saisi les frais courants à la main les affiche de
  nouveau, marqués **corrigés par vous** (c'est la seule valeur reprise de ton ancienne
  configuration, voir §4).

---

## 2. Le lancement ([D-106](../decisions.md))

### Ce qui a été essayé sur ta machine, par programme

| Essai | Résultat |
|---|---|
| Lancement par `pythonw`, sans terminal | aucune fenêtre noire ; la fenêtre « Pastory » s'ouvre, le serveur répond en 3 à 5 secondes |
| Second lancement pendant que Pastory tourne | la fenêtre existante revient ; **ni seconde fenêtre, ni second serveur** |
| Fermeture de la fenêtre | Pastory s'arrête seul **8 secondes** plus tard |
| Fermeture pendant le premier téléchargement des cours | il finit ce travail d'abord, puis s'arrête (73 secondes lors de l'essai) |
| Fenêtre fermée, puis **relancée 5 secondes après** | le Pastory qui allait s'arrêter est prévenu, sert la nouvelle fenêtre, et ne s'arrête qu'à sa fermeture (9 secondes après) |
| Le vrai raccourci « Pastory (démonstration) », ouvert comme un double-clic | même comportement ; le dossier `Pastory` n'a pas été touché |
| Les trois raccourcis relus | la cible existe, l'icône existe, le dossier de départ est celui du projet |

### À vérifier par toi, à l'écran

- [ ] L'icône **Pastory** est sur le bureau, avec le logo (le livre et son signet).
- [ ] Double-clic : **aucune fenêtre noire**, et une fenêtre **sans barre d'adresse ni onglets**.
- [ ] Dans la **barre des tâches**, note l'icône de cette fenêtre : le logo de Pastory, ou celle
  d'Edge ? C'est le navigateur qui la choisit ; dis-moi ce que tu vois.
- [ ] Double-clic une seconde fois : la même fenêtre revient au premier plan, sans en ouvrir une
  autre.
- [ ] Ferme la fenêtre, attends une quinzaine de secondes, ouvre le Gestionnaire des tâches
  (Ctrl+Maj+Échap) → onglet « Détails » : il n'y a plus de `pythonw.exe`.
- [ ] Réduis la fenêtre une dizaine de minutes, puis reviens : Pastory répond toujours.
- [ ] **Le même essai sur une heure ou deux**, fenêtre réduite, ordinateur allumé. C'est le seul
  point que je n'ai pas pu mesurer : un navigateur peut endormir une page masquée depuis
  longtemps, et Pastory s'arrêterait alors sans que tu aies rien fermé. Une précaution est en
  place, mais elle n'est pas vérifiée sur la durée ([D-106](../decisions.md)). Si tu retrouves
  « Pastory est arrêté » au bas de la fenêtre, dis-le-moi avec la durée.
- [ ] Menu Démarrer → tape « Pastory » : les deux entrées apparaissent.

### Si quelque chose ne va pas

- **Rien ne s'ouvre** : un message devrait le dire. Le détail est dans
  `%LOCALAPPDATA%\Pastory\journal.txt`.
- **« Pastory est arrêté : cette page ne répond plus »**, en bas de la fenêtre : le serveur s'est
  arrêté alors que la fenêtre est restée ouverte. Ferme-la et relance. Si cela arrive sans raison
  apparente, note ce que tu faisais : le délai de la veille est peut-être à allonger.
- **Tu renommes ou déplaces le dossier du projet** : les icônes ne marchent plus. Relance
  `Installer Pastory.cmd`, ou `.venv\Scripts\python.exe -m pastory.cli installer`.

### Ce qui n'a pas été essayé

- `Installer Pastory.cmd` **jusqu'au bout**. Sur une copie neuve du dépôt, il s'arrête à la
  première étape : ton antivirus bloque le téléchargement des bibliothèques (« invalid peer
  certificate: UnknownIssuer »). Le fichier l'explique et rend la main proprement ; la seconde
  étape (les raccourcis) a été essayée par la commande qu'il appelle. **Le vrai test est
  l'installation par quelqu'un d'autre**, sur une autre machine, en suivant le seul README.
- Tout ce qui concerne **Mac et Linux**.

---

## 3. La démonstration ([D-107](../decisions.md))

Menu Démarrer → **« Pastory (démonstration) »**. Première ouverture : Internet, et une minute.

### Ce que contient le portefeuille fictif

233 lignes d'export, de janvier 2023 à septembre 2026 : 158 ordres, 19 dividendes, 45 versements
sur le PEA, quelques lignes d'espèces, une ligne Saveback.

| Poche | Titre | Opérations inventées |
|---|---|---|
| PEA | un ETF Monde éligible, à réplication synthétique | plan de 150 € par mois depuis janvier 2023 |
| PEA | un ETF pays émergents éligible | plan de 50 € par mois depuis janvier 2024 |
| CTO | un ETF S&P 500 | plan de 100 € par mois depuis juin 2023 |
| CTO | un ETF d'obligations d'État de la zone euro | deux achats |
| CTO | un ETF de matières premières | deux achats |
| CTO | une action française | deux achats, une vente partielle à perte, sept dividendes |
| CTO | une action américaine | deux achats, douze dividendes en dollars |
| Crypto | du bitcoin | plan de 25 € par mois depuis mars 2024 |

Les **prix d'achat sont les vraies clôtures** des jours choisis ; tout le reste est inventé
(quantités, dates, dividendes, taxes, taux de change, lignes d'espèces).

### Ce que Pastory en a tiré, lors de l'essai du 2026-10-12

- **177 opérations** lues, **aucun contrôle de cohérence en échec**, un seul type non traité : le
  Saveback, mis là exprès.
- **27 valeurs trouvées seules sur 27** : la cotation de chaque titre (écart médian au prix payé :
  0 % à 0,02 %), son type, ses frais courants, son contenu, et la date d'ouverture du PEA.
- **8 positions**, toutes valorisées.
- La diversification montre d'elle-même les cas délicats : le fonds synthétique lu par son indice,
  le fonds émergent servi par la source de secours (des pays, et « non couvert » en secteur), les
  obligations et les matières premières « hors actions », le bitcoin « ni pays ni secteur ».

### À vérifier par toi

- [ ] La couverture porte l'avis **« Données de démonstration »**, s'intitule « Un portefeuille
  fictif », et **ne propose aucun dépôt**.
- [ ] Dans chaque chapitre, la mention **« Données de démonstration »** reste à côté du nom
  « Pastory », de jour comme de nuit.
- [ ] Le titre de la fenêtre est « Pastory · démonstration ».
- [ ] Ouvre **les deux** en même temps (Pastory et sa démonstration) : deux fenêtres, chacune avec
  ses chiffres. Ferme l'une : l'autre continue.
- [ ] Le dossier `%LOCALAPPDATA%\Pastory-demonstration` existe, à côté de `Pastory` ; ton dossier
  `Pastory\exports` ne contient toujours que tes exports.
- [ ] Regarde le portefeuille fictif comme tu regarderais le tien : est-ce un bon exemple à
  montrer ? Un titre à retirer ou à remplacer se change dans `pastory/demonstration/__init__.py`.

---

## 4. Le ménage ([D-108](../decisions.md))

### Ce qui a été retiré, et le contrôle fait avant

| Quoi | Contrôle avant d'effacer |
|---|---|
| Les maquettes d'écran (`maquettes/`, sauf `logo/`) | aucun code ne les lit ; elles restent dans l'historique git |
| Le code de l'ancien nom de l'application | les tests passent sans lui |
| 12 branches locales, 6 sur GitHub | chacune est contenue dans `main` ; pour celle que git ne voyait pas comme fusionnée, la différence avec son commit de fusion est **vide** |
| `data/` | les 46 lignes de sa copie de l'export sont **toutes** dans l'export du dossier de dépôt (61 lignes), identifiant par identifiant |
| Les deux fichiers pytr de ton ami | — (son export officiel reste, pour [Q-54](../questions-ouvertes.md)) |
| Le PDF de la maquette d'origine | — |
| L'ancien dossier personnel (27 fichiers) | **chaque correction manuelle comparée** à ce que Pastory trouve seul : voir ci-dessous |
| pytr (désinstallé d'Anaconda) et son dossier vide | — |

### Tes anciennes corrections

Ton ancienne configuration corrigeait six actifs à la main (cotation, devise, type, frais
courants, contenu) et donnait la date d'ouverture du PEA. Comparées une à une à ce que Pastory
trouve seul aujourd'hui :

- **toutes sont retrouvées à l'identique**, date du PEA comprise ;
- **sauf une** : les frais courants d'un ETF, que Pastory ne trouve pas. Avec ton accord, ce seul
  taux a été reporté dans `%LOCALAPPDATA%\Pastory\configuration\actifs.toml`, avec un commentaire
  qui dit d'où il vient. `pastory actifs` annonce désormais « 22 valeurs trouvées seules,
  1 corrigée par vous, 0 introuvable ».
- la sixième entrée était l'ancien code pytr de ta crypto, qui ne désigne plus rien.

### À faire par toi

- [ ] **Vérifie ce taux de frais courants** sur la fiche de l'émetteur : il vient de ta saisie de
  septembre, pas d'une source.
- [ ] **Vide la corbeille OneDrive en ligne** si tu veux que les anciennes données disparaissent
  vraiment : `data/`, les fichiers de ton ami et le PDF étaient dans un dossier synchronisé, et
  OneDrive garde ce qu'on efface une trentaine de jours.
- [ ] Le dossier `data_*/` de ton ami ne contient plus que son export officiel. Il partira quand
  [Q-54](../questions-ouvertes.md) sera tranchée.

---

## 5. La relecture indépendante

Un agent qui n'avait pas écrit le code l'a relu. Dix remarques, toutes traitées, et chaque défaut
de comportement est désormais gardé par un test :

| Ce qui a été trouvé | Ce qui a été fait |
|---|---|
| Un second Pastory pouvait démarrer si le premier tournait sur un port de repli | toute la plage de ports est regardée avant de s'installer |
| Rouvert dans les secondes qui suivent sa fermeture, Pastory s'éteignait sous la nouvelle fenêtre | le lanceur annonce la fenêtre qu'il amène ; essayé en vrai (§2) |
| Un programme qui ne parle pas HTTP sur le port faisait tomber le lancement en panne | il est sauté, comme tout autre programme |
| Une panne de la démonstration avant l'ouverture du journal ne laissait aucune trace | le journal s'ouvre d'abord ; sans journal, le message porte l'erreur elle-même |
| Un journal trop gros, tenu par un Pastory ouvert, empêchait d'ouvrir | sa remise à zéro n'est plus qu'une tentative |
| Le message « période sans cours » affirmait une cause que la source ne donne pas | il dit ce que la source dit, rien de plus |
| Une page endormie par le navigateur arrêterait Pastory sous une fenêtre réduite | une précaution est posée, **non mesurée sur la durée** : à vérifier par toi (§2) |
| Le nom réel du dossier d'un tiers figurait dans ce cahier | retiré, y compris de l'historique de la branche, qui n'avait pas été envoyée |
| La démonstration reposait sur deux réglages qui devaient concorder | il n'y en a plus qu'un : le dossier dit si c'en est une |
| Le nom, le port et le titre de la fenêtre étaient écrits à plusieurs endroits | écrits une fois, pour le lanceur comme pour l'application |

## 6. Les tests

1 340 tests, tous au vert : 93 nouveaux, et 6 retirés avec le code de l'ancien nom.

- **la veille** : une page qui donne signe de vie garde Pastory ouvert ; fermée, il s'arrête ;
  rechargée, il continue ; une seconde fenêtre réduite le garde ouvert ; il ne s'arrête jamais au
  milieu d'un travail ; une fenêtre annoncée est attendue, mais pas indéfiniment ;
- **le lanceur** : un vrai serveur démarré sur le port pris d'avance répond « c'est moi » ; un
  Pastory déjà ouvert n'en démarre pas un second, même sur un port de repli ; la démonstration et
  le vrai portefeuille ne se répondent jamais l'un pour l'autre ; une panne de démarrage ne reste
  jamais muette, avec ou sans journal ;
- **l'installation** : un vrai raccourci s'écrit dans un chemin accentué ; `--retirer` défait tout,
  et seulement cela ;
- **la démonstration** : Pastory lit l'export fictif sans réserve ; chaque prix d'achat est une
  clôture relevée ; seules des formes déjà vues sont écrites ; `preparer` ne touche pas au vrai
  dossier ; hors démonstration, l'écran n'en parle nulle part ;
- **la source de cours** : une période où le titre ne cotait pas n'est plus une panne.

Deux garde-fous s'ajoutent à ceux de la suite : aucun test n'écrit sur le vrai bureau, et aucun
n'ouvre de fenêtre.
