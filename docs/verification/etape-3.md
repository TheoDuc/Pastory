# Cahier de vérification — étape 3 : le moteur de positions

L'étape 2 lisait les opérations. **L'étape 3 en tire des chiffres** : quantité détenue, capital
net investi, prix de revient, frais, taxes, dividendes et plus-values réalisées.

Ce qu'elle ne calcule **pas encore** : la valeur de tes actifs aujourd'hui, le gain, le TRI et le
TWRR. Tous ont besoin des cours de marché, qui arrivent à l'étape 4.

Deux parties, comme au cahier précédent :

1. **les cas fictifs de la partie A**, que tu peux refaire sur papier ou dans un tableur ;
2. **tes vraies positions**, en face de l'application Trade Republic (partie B).

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à
toi vont dans `etape-3.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## Le journal : la pièce à ouvrir en premier

Le moteur ne se contente pas de donner un résultat : il garde **une ligne par opération**, avec
l'état d'avant et l'état d'après. Ça se lit comme un relevé bancaire.

```
date        type     quantité   prix   | qté avant  qté après  capital avant  ajouté  retiré  capital après  PRU après
2026-01-05  achat        10    20,00   |         0         10           0,00  200,00    0,00         200,00     20,00
2026-02-05  achat        10    30,00   |        10         20         200,00  300,00    0,00         500,00     25,00
2026-03-05  vente         5    40,00   |        20         15         500,00    0,00  125,00         375,00     25,00
```

Sur chaque ligne : **capital avant + ajouté − retiré = capital après**. Si un chiffre te
surprend, c'est là que tu trouves d'où il vient, sans avoir à lire le code.

C'est le fichier `journal.csv`, écrit par `dashboard exporter-positions`.

---

## A. Cas fictifs, à refaire à la main

Ces cas sont **exactement ceux que les tests font calculer au programme**. Si ce document et le
code divergeaient un jour, les tests le diraient.

### A.1 — Un achat : le capital monte du montant brut, pas du montant payé

Achat de 10 parts à 20,00 €, avec 1,00 € de frais et 0,60 € de taxe. Le compte est débité de
**201,60 €**.

| | Calcul | Résultat |
|---|---|---|
| Montant brut | 10 × 20,00 | 200,00 € |
| **Capital net investi** | + le montant brut | **200,00 €** |
| Prix de revient | 200,00 / 10 | **20,00 €** |
| Frais et taxes | suivis à part | 1,00 € et 0,60 € |

**Ce qu'il faut retenir : le capital monte de 200,00 €, pas de 201,60 €** ([D-12](../decisions.md)).
Les 1,60 € existent, ils sont comptés, mais **ailleurs** — dans le bloc « coûts réellement
payés » du rapport ([D-21](../decisions.md)).

### A.2 — Un deuxième achat : le prix de revient est une moyenne pondérée

Suite du A.1 : achat de 10 parts de plus, à 30,00 €, sans frais.

| | Calcul | Résultat |
|---|---|---|
| Capital | 200,00 + 300,00 | **500,00 €** |
| Quantité | 10 + 10 | 20 parts |
| **Prix de revient** | 500,00 / 20 | **25,00 €** |

C'est un prix **moyen pondéré** ([D-13](../decisions.md)) : ni le premier prix, ni le dernier, ni
la moyenne des deux prix — la moyenne des mises, par part.

### A.3 — Une vente partielle : le capital part au prorata des parts, pas de l'argent reçu ⚠️

Suite du A.2 : vente de 5 parts sur 20, à 40,00 €, avec 1,00 € de frais. Le compte est crédité de
**199,00 €**.

C'est le calcul le plus important du moteur, et le moins intuitif.

| | Calcul | Résultat |
|---|---|---|
| Part des parts vendues | 5 / 20 | un quart |
| **Capital retiré** | 500,00 × 5 / 20 | **125,00 €** |
| Capital restant | 500,00 − 125,00 | **375,00 €** |
| Quantité restante | 20 − 5 | 15 parts |
| Prix de revient | 375,00 / 15 | **25,00 €**, inchangé |

> **Le piège :** on encaisse 200,00 € et le capital ne baisse que de 125,00 €. C'est normal —
> les 75,00 € d'écart sont le **gain**, pas de la mise qui revient. Une vente ne change jamais le
> prix de revient ([D-13](../decisions.md)) : on vend des parts, pas la moyenne.

**La plus-value réalisée** se lit alors directement :

| | Calcul | Résultat |
|---|---|---|
| Plus-value brute | 200,00 − 125,00 | **+75,00 €** |
| Plus-value nette | 75,00 − 1,00 de frais | **+74,00 €** |

> **À refaire soi-même :** prends une de tes ventes. Multiplie ton capital investi d'avant par
> (parts vendues / parts détenues avant). Tu dois tomber sur la colonne « capital retiré » du
> journal, au centime près.

### A.4 — Un dividende : rien ne bouge, mais il compte

10 parts détenues, 0,50 € de dividende par action, 1,50 € de retenue. Le compte est crédité de
**3,50 €**.

| | Résultat |
|---|---|
| Quantité détenue | **inchangée** : un dividende n'ajoute aucune part |
| Capital net investi | **inchangé** : ce n'est pas un apport ([D-14](../decisions.md)) |
| Dividende compté | **5,00 € bruts**, pas 3,50 € ([D-29](../decisions.md)) |
| Les 1,50 € de retenue | dans les coûts, ligne « taxes sur revenus » |

### A.5 — Une distribution de capital : là, le capital baisse

12,00 € distribués sur un fonds dont le capital investi vaut 300,00 €.

| | Calcul | Résultat |
|---|---|---|
| Capital | 300,00 − 12,00 | **288,00 €** |
| Quantité | inchangée | — |

Ce n'est **pas** un revenu : c'est une part de la mise qui revient ([D-14](../decisions.md)).
D'où la différence de traitement avec le dividende du A.4.

**Et si la distribution dépassait le capital ?** Le capital s'arrête à **zéro**, et le rapport te
le signale ([D-45](../decisions.md)) : au-delà de ce qui a été mis, ce n'est plus un
remboursement, c'est un gain. L'actif est alors marqué « historique incomplet » et son prix de
revient disparaît, comme en A.6 et A.7 — ou bien une acquisition manque, ou bien la distribution
a été mal lue, et dans les deux cas le capital ne décrit plus ce qui a été mis dans l'actif.

### A.6 — Des actions gratuites : les parts comptent, le prix de revient se tait ⚠️

10 parts achetées 20,00 € (capital 200,00 €), puis **3 parts reçues gratuitement**, dont le cours
du jour n'est pas encore connu ([D-15](../decisions.md)).

| | Résultat |
|---|---|
| Quantité détenue | **13 parts** — elles sont bien à toi |
| Capital net investi | **200,00 €**, et c'est **sous-estimé** |
| Prix de revient | **« à compléter »** |

> **Pourquoi pas de prix de revient ?** Le calcul donnerait 200,00 / 13 = **15,38 €**. Ce chiffre
> est faux — il fait comme si les 3 parts n'avaient rien coûté — mais il est parfaitement
> crédible, et **rien à l'écran ne dirait qu'il est faux**. L'application préfère se taire et te
> dire pourquoi ([D-45](../decisions.md)). Le nombre reviendra quand les cours de l'étape 4
> auront rempli le prix manquant.

Une **action gagnée** dont le cours est affiché à l'écran, elle, entre normalement : 2 parts à
10,00 € font 20,00 € de capital, et le prix de revient existe.

### A.7 — Une vente de plus de parts qu'on n'en a comptées

4 parts achetées, puis une vente de 10 parts. Impossible en apparence — et pourtant ça peut
arriver : des titres ont pu entrer **sans aucun événement** dans l'export (un PEA transféré
depuis un autre établissement, par exemple). C'est la limite connue de [D-15](../decisions.md).

| | Résultat |
|---|---|
| Quantité | **0**, jamais un nombre négatif |
| Capital | **0,00 €** |
| L'actif | marqué « historique incomplet », prix de revient « à compléter » |
| Le rapport | te dit lequel, et pourquoi |

C'est la partie B.3 qui permet de retrouver les parts manquantes.

### A.8 — Une crypto : la précision ne se perd pas

Deux achats : 0,000833 unité à 30 000,00 €, puis 0,000400 unité à 31 250,00 €.

| | Calcul | Résultat |
|---|---|---|
| Quantité | 0,000833 + 0,000400 | **0,001233** |
| Capital | 24,99 + 12,50 | **37,49 €** |
| Prix de revient | 37,49 / 0,001233 | **30 405,515004 €** |

Le prix de revient est arrêté à **six décimales** : c'est le résultat d'une division, il faut bien
l'arrêter quelque part ([D-44](../decisions.md)). Conséquence : `prix de revient × quantité` peut
s'écarter du capital de quelques centièmes de centime. **C'est le capital qui fait foi** ; le
prix de revient est un indicateur qu'on en déduit.

### A.9 — Vérifier que rien ne se perd dans les arrondis

7 parts achetées à 14,29 € (capital 100,03 €), puis vente de 2 parts.

```
capital retiré = 100,03 × 2 / 7 = 28,58 €   (28,5800... arrondi au centime)
capital restant = 100,03 − 28,58 = 71,45 €
```

Les deux morceaux font **exactement** 100,03 €. C'est voulu : le moteur calcule ce qui **sort**,
puis le retranche, plutôt que de multiplier le capital par ce qui reste
([D-44](../decisions.md)). Aucun centime ne se perd, même quand le prorata tombe mal.

---

## B. Contrôles sur tes vraies données

```
uv run dashboard rafraichir          au besoin : récupère l'export
uv run dashboard positions           le rapport du moteur
uv run dashboard exporter-positions  positions.csv et journal.csv, pour le tableur
uv run dashboard positions-reelles   demande à Trade Republic ce qu'il dit détenir
uv run dashboard positions           à nouveau : le rapprochement apparaît
```

> **`positions-reelles` redemande ton numéro et ton PIN**, plus la confirmation dans
> l'application. C'est normal : rien n'est enregistré sur cette machine
> ([D-41](../decisions.md)). C'est aussi la raison pour laquelle c'est une commande à part, et
> non un morceau de `rafraichir` ([D-46](../decisions.md)).

### B.1 — Avant tout : la lecture est-elle propre ?

Les deux premières lignes de `dashboard positions` te disent combien d'opérations ont été lues et
si un type d'événement est resté inconnu. **Si un type est inconnu, ne te fie à aucun chiffre**
avant qu'on l'ait examiné : il peut cacher des opérations sur tes actifs. Lance
`dashboard lire` pour le détail.

### B.2 — Le contrôle principal : actif par actif, en face de l'application

Pour **chaque** ligne du tableau des positions :

- [ ] la **quantité détenue** est celle que montre Trade Republic ;
- [ ] le **capital net investi** correspond à ce que tu as réellement mis dans cet actif ;
- [ ] la **poche** est la bonne ;
- [ ] le **prix de revient** est cohérent avec les prix auxquels tu as acheté.

> **Attention au capital investi.** Trade Republic n'affiche pas ce chiffre-là tel quel. Le plus
> simple : ouvre `journal.csv`, filtre sur un actif, et additionne la colonne `capital_ajoute`
> moins la colonne `capital_retire`. Tu dois retomber sur le capital de `positions.csv`.

**Un écart de quelques centimes compte aussi** : signale-le, avec l'actif, la date et la valeur
que tu attendais.

### B.3 — Le rapprochement : le contrôle le plus sûr du projet

C'est le seul contrôle qui ne dépend **d'aucune** lecture de texte, d'aucune déduction, d'aucune
règle. Soit les quantités tombent juste, soit il manque quelque chose.

| Ce que tu lis | Ce que ça veut dire | Quoi faire |
|---|---|---|
| `accord` | les deux quantités concordent | rien |
| `écart` | les deux comptent des parts, mais pas le même nombre | une opération manque ou a été mal lue : dis-le |
| **`absent du moteur`** | **la banque détient des parts dont aucune opération ne parle** | **c'est le cas à examiner** : des titres sont entrés sans événement |
| `absent de la banque` | le moteur compte des parts que la banque ne montre pas | l'actif a été vendu hors de l'export, ou une opération a été comptée deux fois |

La ligne **`absent du moteur`** est exactement ce que l'étape 2 ne pouvait pas trouver toute
seule : c'est la limite connue de [D-15](../decisions.md), et c'est probablement là qu'apparaîtra
le transfert de PEA sans événement (Q-10).

> **Si le rapport annonce des lignes du fichier « non lues »**, ne conclus rien : un actif marqué
> `absent de la banque` peut très bien se trouver dans l'une d'elles. Relance
> `dashboard positions-reelles` d'abord.

Le rapprochement ne se fait **pas** avec `--au` : la banque ne sait montrer que son portefeuille
d'aujourd'hui, et le comparer à des chiffres arrêtés dans le passé signalerait à tort tout ce qui
a bougé depuis. Le rapport le dit au lieu de comparer de travers.

### B.4 — Les deux prix de revient : à regarder, pas à corriger

Sous le rapprochement, l'application montre **son** prix de revient et celui de Trade Republic,
côte à côte.

**Un écart n'est pas une anomalie.** On ignore ce que Trade Republic met dans le sien — frais
d'achat compris ou non, quelle méthode de moyenne — alors que celui de l'application les exclut
explicitement ([D-13](../decisions.md)). Les deux chiffres ne mesurent probablement pas la même
chose, et l'application ne prétend pas savoir lequel a raison ([D-46](../decisions.md)).

Ce qui mérite un signalement : un écart **énorme** (du simple au double), pas quelques dizaines
de centimes.

### B.5 — Les signalements

Chacun doit être lu, et aucun ne doit rester sans explication.

| Signalement | Ce qu'il dit |
|---|---|
| `prix à compléter` | des parts sont entrées sans prix connu (A.6). Normal tant que l'étape 4 n'est pas faite |
| `stock insuffisant` | une vente a dépassé les parts comptées (A.7). Il manque une entrée de titres |
| `distribution excédentaire` | une distribution de capital a dépassé le capital investi (A.5) |
| `titres sans opération` | le rapprochement a trouvé des parts inconnues du moteur (B.3) |
| `écart de quantité` | le moteur et la banque ne comptent pas pareil (B.3) |

### B.6 — Ce que les fichiers contiennent

| Fichier | Une ligne par | Pour quoi faire |
|---|---|---|
| `positions.csv` | actif dans une poche | comparer avec l'application, actif par actif |
| `journal.csv` | opération | **refaire un chiffre à la main** |

Les positions **entièrement vendues** restent dans `positions.csv`, avec une quantité de zéro :
leurs plus-values et leurs frais comptent dans les totaux, et les faire disparaître les rendrait
impossibles à refaire.

Ces fichiers contiennent de vraies données : ils sont écrits dans ton dossier personnel et
n'entrent jamais dans git ([D-01](../decisions.md), [D-37](../decisions.md)).

### B.7 — Arrêter les chiffres à une date

```
uv run dashboard positions --au 2026-06-30
```

Utile pour comparer avec un relevé daté. C'est aussi le mécanisme qui servira à tracer
l'évolution dans le temps, à l'étape 5.

---

## Ce que cette étape ne vérifie pas encore

- **La valeur de tes actifs aujourd'hui** : il faut les cours (étape 4).
- **Le gain en €, le TRI et le TWRR** : ils ont besoin de cette valeur (étape 5).
- **Les coûts estimés** — spread et frais courants des ETF : ce sont des estimations, et elles
  ont leurs propres arbitrages (étape 6, [D-17](../decisions.md)).
- **L'impôt et la valeur réelle** : étape 6 également ([D-23](../decisions.md)).

Les coûts **réellement payés**, eux, sont déjà là : le rapport les montre, rangés par moment
(achat, vente, revenus), et toujours séparés de la performance ([D-21](../decisions.md)).
