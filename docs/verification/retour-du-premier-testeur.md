# Cahier de vérification — le retour du premier testeur

Trois changements, nés du premier essai de Pastory par quelqu'un d'autre que le propriétaire
(2026-10-13) : l'installation ([D-112](../decisions.md)), l'attente de la première ouverture
([D-110](../decisions.md)), et le détail par actif de la diversification
([D-111](../decisions.md)). Toutes les valeurs écrites ici sont fictives
([D-03](../decisions.md)).

---

## 1. Rien n'a bougé dans les chiffres

Les chiffres ont été relevés sur une copie des données du propriétaire, hors ligne, le même jour,
avec le code d'avant puis avec celui d'après : la synthèse, la valeur réelle, les coûts, les
positions, les trois répartitions, et le texte de chaque écran pour chaque période — 60 relevés,
près de 9 000 nombres.

- **60 relevés sur 60 identiques** ;
- dans les écrans de diversification, **aucun nombre d'avant n'a disparu**, et 2 100 nombres se
  sont ajoutés : ce sont les lignes d'actifs de la section 3.

### À vérifier par toi

- [ ] Ouvre Pastory : la valeur de tes actifs, ton gain, ton TRI et ton TWRR sont ceux d'avant.

---

## 2. L'attente

### Ce que la barre affirme, et comment le refaire de tête

La lecture a **trois étapes de même poids**, et chacune avance au rythme de ses actifs :

| N° | Étape | Compte |
|---|---|---|
| 1 | Recherche de la cotation et des frais de chaque actif | les actifs de l'export |
| 2 | Récupération des cours de chaque actif | les actifs de l'export |
| 3 | Lecture de la composition des fonds et des sociétés | les actifs valorisés, sans les cryptos |

La part de la barre : `(étapes finies + actifs traités ÷ actifs de l'étape) ÷ 3`.

**Cas fictif.** Un portefeuille de 8 actifs, dont une crypto. À l'étape 2, quand 4 actifs ont
leurs cours : `(1 + 4 ÷ 8) ÷ 3 = 0,5`. La barre est **à la moitié**, et l'écran dit « Étape 2 sur
3 · 4 actifs sur 8 ». À l'étape 3, la crypto n'a pas de composition à chercher : le compte va
jusqu'à 7, pas 8.

La barre **ne dit pas le temps qui reste** : elle ne le connaît pas.

### Ce qui a été mesuré

Une première ouverture de la démonstration (8 actifs), sur un dossier vide, en ligne :

| | Avant | Après |
|---|---|---|
| Recherche des cotations et des frais | 10 à 12 s | 10 à 12 s (inchangée) |
| Cours, et la valorisation qui les lit | 78 s | 3 s |
| Compositions, et la courbe | 2 s | 2 s |
| **En tout** | **93 s** | **15 s** (18 s par la fenêtre) |

Les cours sont demandés **une fois par actif** au lieu d'une fois par date d'opération. Les
séries obtenues ont été comparées ligne à ligne : **tous les cours communs sont identiques**, et
la nouvelle série contient en plus cinq séances (du 7 au 11 septembre) que l'ancienne méthode
laissait de côté — voir [Q-62](../questions-ouvertes.md).

### À vérifier par toi

- [ ] Dans le menu Démarrer, ouvre **« Pastory (démonstration) »** après avoir effacé son dossier
  (`%LOCALAPPDATA%\Pastory-demonstration`) : la barre apparaît, passe par les trois étapes, et la
  couverture s'affiche en moins d'une demi-minute.
- [ ] Rouvre-la aussitôt : l'attente est brève, et ne promet plus « une minute ».
- [ ] Essaie les deux lectures, de jour et de nuit : le filet s'encre, le losange est en or.
- [ ] Change de période dans la synthèse : aucune barre ne doit apparaître.

---

## 3. Quels actifs sont dans ce pays, dans ce secteur ?

### Le cas fictif, refaisable à la main

Un portefeuille de 2 500,00 € :

| Actif | Valeur | Ce que dit sa composition |
|---|---|---|
| ETF Monde fictif | 1 000,00 € | 100 % d'actions : États-Unis 60 %, France 30 %, Japon 10 % |
| Action française fictive | 500,00 € | France 100 % |
| ETF obligataire fictif | 500,00 € | 100 % d'obligations |
| Crypto fictive | 200,00 € | — (ni pays ni secteur) |
| Actif sans composition | 300,00 € | inconnue |

La répartition **par pays**, et ce que montre chaque ligne quand on la déplie :

| Ligne | Montant | Part de 2 500,00 € | Ses actifs |
|---|---|---|---|
| France | 800,00 € | 32,00 % | Action française 500,00 € (20,00 %) · ETF Monde 1 000 × 30 % = 300,00 € (12,00 %) |
| États-Unis | 600,00 € | 24,00 % | ETF Monde 1 000 × 60 % = 600,00 € |
| Japon | 100,00 € | 4,00 % | ETF Monde 1 000 × 10 % = 100,00 € |
| *Obligations* | 500,00 € | 20,00 % | ETF obligataire 500,00 € |
| *Non couvert* | 300,00 € | 12,00 % | Actif sans composition 300,00 € |
| *Actifs numériques* | 200,00 € | 8,00 % | Crypto 200,00 € |
| **Total** | **2 500,00 €** | **100,00 %** | |

Deux contrôles, à faire sur n'importe quelle ligne :

1. **la somme des actifs d'une ligne est son montant** (France : 500,00 + 300,00 = 800,00) ;
2. **la somme des lignes d'un même actif est sa valeur** (ETF Monde : 300,00 + 600,00 + 100,00 =
   1 000,00).

Ce cas est un test (`tests/moteur/test_diversification.py`, `TestCeQueChaqueActifApporte`), et un
autre vérifie le contrôle 1 pour chaque poste et chaque reste des trois répartitions.

**Ce sont tes actifs qui sont listés, jamais les sociétés qu'un fonds détient** : Pastory ne lit
que les agrégats d'un fonds ([D-63](../decisions.md)). Sous « Technologie », tu vois « ETF Monde »,
pas le nom d'un fabricant de téléphones.

### À vérifier par toi

- [ ] Chapitre III, rubrique **Pays** : clique sur ton premier pays. Additionne les montants de
  ses actifs : tu dois retrouver le montant de la ligne, au centime.
- [ ] Prends un de tes fonds, et additionne ce qu'il apporte à chaque pays, plus ce qu'il laisse
  dans « Sans pays » : tu dois retrouver sa valeur, celle du chapitre II.
- [ ] Rubrique **Zone géographique** : une zone s'ouvre sur ses pays, un pays sur ses actifs.
- [ ] Rubrique **Secteur** : un fonds servi par la source de secours n'apparaît sous aucun
  secteur, et se retrouve sous « Sans secteur → Non couvert ».

---

## 4. L'installation

### Ce qui a été essayé, sur une copie hors du projet

| Situation | Ce que fait le fichier |
|---|---|
| Lancé hors du dossier de Pastory (depuis l'archive ZIP) | le dit, n'installe rien |
| `uv` dans le chemin de recherche de Windows | « déjà installé », puis la suite |
| `uv` absent du chemin, présent dans le dossier personnel | le trouve, puis la suite |
| `uv` absent partout | le dit, attend une touche, le télécharge, l'installe, le trouve |

Le dernier cas a été joué pour de vrai, dans un dossier jetable : `uv` a été téléchargé et
installé, sans toucher à celui de la machine.

### Ce qui n'a pas pu être essayé

- **L'installation des bibliothèques** (`uv sync`) : l'antivirus de la machine du propriétaire la
  bloque toujours. Elle n'a pas changé, à deux réglages près (des copies plutôt que des liens, et
  un second essai) ;
- **la panne exacte du premier testeur** : elle n'est pas connue. Les trois causes plausibles sont
  couvertes — `uv` installé mais pas encore dans le chemin de Windows, le fichier lancé depuis
  l'archive, un dossier dans OneDrive.

### À vérifier par toi

- [ ] Demande à ton ami **quel message** il a eu après avoir installé `uv` : s'il ne ressemble à
  aucune des trois causes ci-dessus, il reste un défaut à trouver.
- [ ] Si quelqu'un d'autre peut l'essayer sur une machine sans `uv` : télécharger, décompresser,
  double-cliquer — et noter chaque blocage.
