# Cahier de vérification — étape 10 bis

**Un fichier, un portefeuille** ([D-109](../decisions.md)). L'étape ne calcule aucun chiffre
nouveau : ce cahier vérifie que deux comptes ne se mélangent plus, et que rien n'a bougé pour qui
n'a qu'un export. Toutes les valeurs écrites ici sont fictives ([D-03](../decisions.md)).

---

## 1. Avec un seul portefeuille, rien ne change

Chaque nombre de chaque écran a été relevé sur une copie des données du propriétaire, hors ligne,
le même jour, avec le code d'avant l'étape puis avec celui d'après : 105 états, plus de 12 000
nombres, **identiques au caractère près**.

Ce qui change à l'écran, sans toucher à un chiffre :

- la zone de dépôt s'intitule « Déposer un export » et dit ce qu'il deviendra ;
- le volet « Détail de la lecture » permet de renommer et de supprimer le portefeuille ;
- les mentions de « trou entre deux fichiers » ont disparu, avec le cumul qui les justifiait.

### À vérifier par toi

- [ ] Ouvre Pastory : la couverture dit toujours « Votre livre », sans proposer de choix, et tes
  chiffres sont ceux d'avant.

---

## 2. Deux comptes ne se mélangent plus

### Le cas fictif, refaisable à la main

Deux exports, donnés ici par leurs opérations (les lettres sont des identifiants d'opération) :

| Fichier déposé | Ses opérations | Déjà dans le dossier | Ce que fait Pastory |
|---|---|---|---|
| le mien, en mars | A, B | rien | premier portefeuille, qui garde le nom du fichier |
| celui d'un proche | X | {A, B} | aucune opération commune : **nouveau portefeuille** |
| le mien, en avril | A, B, C | {A, B} et {X} | contient {A, B} en entier : il le **met à jour** (1 ligne de plus) ; {X} n'est pas touché |
| le mien de mars, par erreur | A, B | {A, B, C} et {X} | tout entier dans {A, B, C} : **version plus ancienne**, rien ne change |
| un export partiel du mien | B, C, D | {A, B, C} et {X} | recoupe sans contenir (il manque A) : **nouveau portefeuille**, et Pastory dit pourquoi |

La règle tient en une ligne : **un export n'en remplace un autre que s'il le contient en entier**.
Rien n'est donc jamais perdu par un remplacement.

### Ce qui a été essayé en vrai, dans un navigateur

Sur une copie de ton dossier, avec l'export de la démonstration dans le rôle du second compte
(aucune donnée d'un tiers) :

| Geste | Résultat |
|---|---|
| Dépôt d'une version tronquée du second compte | « Nouveau portefeuille : … devient « Portefeuille » », ouvert aussitôt ; le choix apparaît sur la couverture |
| Ouverture du livre | le nom « Portefeuille » est écrit à droite de la navigation |
| Dépôt de la version complète du même compte | « « Portefeuille » est mis à jour : 40 lignes de plus » ; toujours deux portefeuilles |
| Renommage depuis le volet du détail | « … s'appelle désormais … » ; le fichier est renommé |
| Clic sur l'autre portefeuille | la couverture porte son nom, les chiffres sont les siens |
| « Supprimer », puis « Oui, supprimer » | le premier clic pose la question, le second efface le fichier ; il reste un portefeuille, et le choix disparaît |

### À vérifier par toi

- [ ] Dépose de nouveau l'export de ton ami : il devient un **second portefeuille**, et le tien
  n'a pas bougé d'un centime.
- [ ] Passe de l'un à l'autre sur la couverture : chaque fois, les chiffres sont ceux d'un seul
  compte, et son nom est écrit en haut à droite dans le livre.
- [ ] Renomme-les à ton goût, dans « Détail de la lecture ».
- [ ] Supprime celui de ton ami : la question est posée avant, et après il ne reste que le tien.
- [ ] Le mois prochain, dépose ton nouvel export : Pastory doit dire « mis à jour », avec le nombre
  de lignes de plus, et **ne pas** créer un second portefeuille. Si ce n'est pas le cas, dis-le-moi :
  cela voudrait dire que la banque a modifié ou retiré une ligne ancienne.

---

## 3. La date du PEA corrigée à la main

Elle se trouve seule dans chaque export : dans le cas normal, rien à faire. Seule une date écrite
dans `fiscalite.toml` est concernée.

| Ce qui est écrit | Portefeuilles | Ce qui s'applique |
|---|---|---|
| `[pea] premier_versement = 2021-03-01` | un seul | la date, comme avant |
| la même | deux | **rien** : on ne sait pas à qui elle est. Pastory le dit en tête des chiffres |
| `[portefeuille."Camille".pea] …` | deux, dont Camille | la date, pour Camille seulement |
| la même | Camille a été renommée | rien, et la correction est signalée comme sans objet |

Tu n'as pas de `fiscalite.toml` aujourd'hui : rien à vérifier, sauf si tu en écris un.

---

## 4. Ce qu'il faut savoir

- **Les titres d'un autre portefeuille sont cherchés en ligne**, comme les tiens : seuls leurs codes
  et leurs noms partent, jamais des quantités ni des montants. Pour lire un export sans rien
  envoyer : `pastory ouvrir --export <fichier>`, depuis un terminal.
- **Chaque portefeuille est calculé comme celui d'une personne seule.** Pour un couple qui déclare
  ensemble, le seuil de la crypto et les pertes du compte-titres sont partagés : l'impôt estimé de
  chacun est alors un peu faux.
- **Supprimer un portefeuille efface son fichier**, pas les cours gardés en mémoire pour ses
  titres : ils sont publics, et peuvent servir à un autre portefeuille.
- **Une correction d'actif** (`actifs.toml`) vaut pour tous les portefeuilles qui détiennent ce
  titre : elle décrit le titre, pas la personne.

---

## 5. La relecture indépendante

Un agent qui n'avait pas écrit le code l'a relu. Dix remarques, toutes traitées, chacune gardée
par un test :

| Ce qui a été trouvé | Ce qui a été fait |
|---|---|
| Un dépôt échouait sans un mot si le fichier du portefeuille était ouvert ailleurs | il dit pourquoi, et quoi faire |
| Une correction d'actif était dite « sans actif » dans le portefeuille qui ne détient pas le titre : la retirer cassait le réglage de l'autre | elle n'est dite sans actif que si aucun portefeuille ne détient le titre |
| Un fichier déjà contenu dans un portefeuille pouvait en remplacer un autre, partiel | une version plus ancienne se reconnaît d'abord, et rien ne change |
| Un nouveau portefeuille ne disait pas qu'une autre période du même compte n'est pas assemblée | le message le dit |
| Une date de PEA écrite au mauvais endroit du fichier était ignorée en silence | elle est refusée, avec la bonne forme |
| Un portefeuille illisible un instant sortait de la liste : Pastory basculait sur un autre sans le dire | il compte toujours, et aucun dépôt n'est rangé tant qu'il est illisible |
| Le rapport renvoyait à la couverture pour changer de portefeuille, même avec `--export` | il donne les deux voies |
| Un export copié à la main dans le dossier échappait à la règle du dépôt | un portefeuille périmé se dit dès la couverture |
| Chaque geste relisait tout le dossier plusieurs fois | un geste sans effet ne recalcule plus rien |
| Un fichier nommé « Exportation de transactions Camille » perdait son nom | seul le nom de la banque tel quel est remplacé |

### À vérifier par toi

- [ ] Copie **à la main** un de tes anciens exports dans le dossier (« Ouvrir le dossier »,
  dans le détail de la lecture), puis ouvre-le dans Pastory : la couverture doit dire
  **« Périmé »**, et nommer le portefeuille à jour. Supprime-le ensuite.

## 6. Les tests

1 441 tests, tous au vert, soit 101 de plus qu'à la fin de l'étape 10 (ceux du cumul sont
réécrits) : la liste des portefeuilles et celui qui est ouvert ;
les quatre cas d'un dépôt ; le renommage et ses noms refusés ; la suppression et sa confirmation ;
l'écran avec un et avec deux portefeuilles ; la date du PEA par portefeuille ; et, de bout en
bout, que les chiffres d'un compte sont les mêmes avec ou sans le fichier d'un autre à côté.
