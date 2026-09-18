# Cahier de vérification — étape 2 : lecture des données

Ce que fait l'étape 2 : transformer les événements Trade Republic en **opérations**, sans rien
perdre en silence. Elle ne calcule encore aucune performance — ça, c'est l'étape 3. Ce cahier
sert donc à vérifier deux choses :

1. **les cas fictifs ci-dessous**, que tu peux refaire sur papier (partie A) ;
2. **tes vraies opérations**, une par une, en face de l'application Trade Republic (partie B).

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à
toi vont dans `etape-2.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## A. Cas fictifs, à refaire à la main

Ces six cas sont ceux de [format-pivot.md §6](../format-pivot.md), et ce sont exactement les
événements que les tests font lire au programme. Si le programme et ce document divergeaient un
jour, les tests le diraient.

### A.1 — Achat par plan d'épargne, sans frais

L'écran affiche : `Transaktion : 2 × 25,00 €`, `Gebühr : Kostenlos`, `Summe : 50,00 €`.

| | Calcul | Résultat |
|---|---|---|
| Montant brut | 2 × 25,00 | **50,00 €** |
| Frais | « Kostenlos » | 0,00 € |
| Montant réglé | 50,00 + 0 + 0 | **50,00 €** |

**Contrôle de cohérence.** Tolérance = 0,01 + 2 × 0,005 + 25,00 × 0 = **0,02 €**.
Le prix est écrit avec deux décimales, donc un demi-centime d'arrondi par part. La quantité est
écrite sans décimale : elle est exacte, d'où le troisième terme nul.
Écart constaté : 50,00 − 50,00 = 0. ✔

### A.2 — Achat ponctuel en PEA, avec frais et taxe

L'écran affiche : `10 × 20,00 €`, `Gebühr : 1,00 €`, `Steuer : 0,60 €`, `Summe : 201,60 €`.

| | Calcul | Résultat |
|---|---|---|
| Montant brut | 10 × 20,00 | **200,00 €** |
| Montant réglé | 200,00 + 1,00 + 0,60 | **201,60 €** |

Ce qui compte pour la suite : **le capital investi augmentera de 200,00 €, pas de 201,60 €**
([D-12](../decisions.md)). Les 1,60 € sont suivis à part, dans les coûts.

### A.3 — Vente partielle

`5 × 40,00 €`, `Gebühr : 1,00 €`, `Summe : 199,00 €`.

| | Calcul | Résultat |
|---|---|---|
| Montant brut | 5 × 40,00 | **200,00 €** |
| Montant reçu | 200,00 − 1,00 − 0,00 | **199,00 €** |

Note le **signe** : le montant est positif dans l'export, et c'est lui — pas le mot affiché —
qui dit qu'il s'agit d'une vente.

### A.4 — Dividende : le brut n'est pas ce qui arrive sur le compte ⚠️

L'écran affiche : `Aktien : 10`, `Dividende pro Aktie : 0,50 €`, `Steuer : -1,50 €`,
`Gesamt : 3,50 €`. Le compte est crédité de 3,50 €.

| | Calcul | Résultat |
|---|---|---|
| Montant reçu (net) | tel qu'affiché | 3,50 € |
| Taxe | le signe moins est retiré | 1,50 € |
| **Montant brut** | 3,50 + 1,50 | **5,00 €** |
| Vérification | 10 × 0,50 | **5,00 €** ✔ |

C'est **5,00 €** qui compteront dans la performance ([D-29](../decisions.md)), pas 3,50 €. La
quantité détenue ne bouge pas : un dividende n'ajoute aucune part.

> **À refaire soi-même :** additionne le montant reçu et la taxe de l'un de tes dividendes, puis
> multiplie ta quantité détenue par le dividende par action. Les deux doivent tomber sur le même
> nombre, à la tolérance près. Si le dividende par action est affiché en dollars, cette
> vérification-là n'est pas possible : l'application laisse alors la case vide plutôt que de
> recopier un chiffre qui n'est pas en euros.

### A.5 — Distribution de capital

`Bruttoertrag : 12,00 €`, `Gesamt : 12,00 €`, pas de taxe. Montant brut = **12,00 €**.

Ce n'est pas un revenu : à l'étape 3, ces 12,00 € **réduiront** le capital investi de l'actif
([D-14](../decisions.md)). C'est une part de la mise qui revient.

### A.6 — Titres reçus sans achat

Deux situations différentes, et l'application ne les traite pas pareil :

| Situation | Ce qu'affiche Trade Republic | Prix retenu |
|---|---|---|
| **Action gagnée** | 2 parts, `Aktienkurs : 10,00 €` | **10,00 €**, lu à l'écran → brut 20,00 € |
| **Actions gratuites** | 3 parts, aucun prix | **à compléter** : le cours du jour, étape 4 |

Dans les deux cas : montant réglé = 0, frais = 0, taxes = 0. Rien n'a été payé.

La ligne « à compléter » est **visible** dans le rapport et dans le CSV, et son montant ne
comptera dans aucun total tant que les cours ne seront pas disponibles
([D-15](../decisions.md)).

> Une action gagnée s'accompagne parfois d'un **crédit en espèces**. Il est laissé de côté : les
> espèces ne sont pas suivies ([D-11](../decisions.md)). Le rapport le signale, pour que tu ne
> croies pas à un oubli.

### A.7 — Pourquoi la tolérance n'est pas un simple centime

Un achat de crypto : 0,000833 part à 30 000,00 €.

La quantité est **affichée arrondie à six décimales**. La vraie quantité est donc quelque part
entre 0,0008325 et 0,0008335 — soit, à ce prix-là, entre 24,975 € et 25,005 €. Un écart de
trois centimes est ici parfaitement normal.

```
tolérance = 0,01 + 0,000833 × 0,005 + 30 000,00 × 0,0000005 ≈ 0,03 €
                   └ arrondi du prix ┘   └ arrondi de la quantité ┘
```

Sans le dernier terme, **chacun de tes achats de crypto serait signalé comme anormal**
([D-39](../decisions.md)).

---

## B. Contrôles sur tes vraies données

```
uv run dashboard rafraichir        récupère l'export (PIN demandé par Trade Republic, masqué)
uv run dashboard comptes           une seule fois : donne un rôle à chaque compte
uv run dashboard lire              le rapport
uv run dashboard exporter-pivot    le CSV à ouvrir dans un tableur
```

### B.1 — Le rapport : quatre choses à regarder

| À vérifier | Ce que tu dois voir |
|---|---|
| **Types inconnus** | « Aucun type inconnu. » Si un type apparaît, **ne te fie à aucun chiffre** avant qu'on l'ait examiné : il peut cacher des opérations sur tes actifs |
| **Nombre d'opérations** | autant d'achats et de ventes que dans ton application |
| **Répartition par poche** | le compte des opérations en PEA, en CTO et en crypto te paraît juste |
| **Signalements** | chacun est lu ; aucun ne doit rester sans explication |

### B.2 — Le CSV, opération par opération

Ouvre `operations.csv` (le rapport affiche son chemin) et, **pour chaque ligne**, compare avec
l'écran de l'opération dans Trade Republic :

- [ ] la **date** est celle que tu vois dans l'application (heure de Paris) ;
- [ ] la **quantité** est la bonne — c'est la valeur la plus fragile, elle est lue dans un texte ;
- [ ] le **prix unitaire** correspond ;
- [ ] le **montant brut** vaut bien quantité × prix ;
- [ ] les **frais** et les **taxes** correspondent ;
- [ ] la **poche** est la bonne (attention : le nom d'un actif peut contenir « PEA » sans qu'il
      soit dans ton PEA) ;
- [ ] le **montant réglé** est ce qui a bougé sur ton compte.

Les colonnes « origine … » disent d'où vient chaque valeur :

| Origine | Sens | Ce que ça implique |
|---|---|---|
| `donnee` | champ structuré de l'export | solide |
| `texte` | lu dans un libellé affiché | **fragile** : dépend de la langue de l'application. C'est ce qu'il faut vérifier en priorité |
| `deduction` | reconstitué par une règle écrite | à confirmer : poche déduite du compte, code `XF` pris pour de la crypto |
| `a_completer` | valeur manquante, attendue à l'étape 4 | la ligne ne compte dans aucun total |

### B.3 — Un chiffre qui surprend, mais qui est juste : l'euro d'activation du PEA

Sur **une** de tes opérations PEA, l'application Trade Republic montre un montant **inférieur
d'un euro** à celui de l'export. Ce n'est une erreur ni de l'un ni de l'autre : ce sont deux
événements différents, le même jour, sur le même actif.

Quand Trade Republic ouvre un PEA, il y verse **1 € d'activation** — son argent, pas le tien.
Cet euro dort sur le compte espèces du PEA. Au premier achat qui suit, le versement prélevé sur
ton compte courant ne couvre donc que **ce qui manque**, et pas le prix entier.

Exemple avec des valeurs fictives :

| Événement | Montant | Ce que c'est |
|---|---|---|
| Activation du PEA | **+ 1,00 €** | offert par Trade Republic, en attente sur le compte espèces |
| Versement depuis le compte courant | **− 99,00 €** | ce qui est parti de **ton** compte |
| **Achat de l'ETF** | **− 100,00 €** | ce qui est réellement **placé dans l'actif** |
| | **solde : 0,00 €** | le compte espèces du PEA retombe à zéro |

- Le chiffre que l'application affiche sur la ligne de **virement** est le 99,00 € ;
- le chiffre de l'écran de l'**achat** — et celui que l'application retient — est le 100,00 €.

**C'est bien 100,00 € que l'application compte comme investi dans l'actif**, parce que c'est ce
qui a acheté les parts. Le fait qu'un euro vienne d'un cadeau ne change ni la valeur de l'actif,
ni son évolution — et l'origine de l'argent est volontairement hors périmètre
([D-11](../decisions.md) : « peu importe d'où vient l'argent »).

> **Seule conséquence, une fois pour toutes :** ton capital investi total est flatté d'un euro,
> une seule fois dans la vie du PEA. Si tu préfères que cet euro n'y figure pas, dis-le : ce
> serait une nouvelle décision, à prendre avant l'étape 3.

Pour retrouver ce cas chez toi : c'est l'achat dont le versement associé est inférieur d'un euro.
Le reste de tes opérations PEA a un versement d'un montant identique à l'achat.

### B.4 — Les contrôles que le programme fait déjà pour toi

Tu n'as pas à les refaire, mais il est utile de savoir qu'ils existent : s'ils échouent, le
rapport te le dit, et **rien n'est corrigé en silence**.

- montant réglé = montant brut ± frais ± taxes ;
- montant brut = quantité × prix, à la tolérance de A.7 ;
- la quantité écrite aux **deux endroits** de l'écran donne la même valeur ;
- le total affiché à l'écran correspond au montant enregistré par la banque ;
- la quantité, les frais et les taxes correspondent au CSV de Trade Republic
  ([D-42](../decisions.md)) ;
- la poche déduite du compte correspond au libellé affiché.

### B.5 — Sur un deuxième export (celui de ton ami)

```
uv run dashboard lire --export <le dossier de son export>
```

Le dossier n'est jamais copié dans le projet. Regarde seulement **les comptages et les types
inconnus** : c'est ce qui dit si l'application tient devant un portefeuille qu'elle n'a pas
servi à construire.

---

## Ce que cette étape ne vérifie pas encore

Le capital investi, le prix de revient, les plus-values, le TRI et le TWRR : rien de tout cela
n'est calculé à l'étape 2. C'est l'objet de l'étape 3, qui aura son propre cahier.
