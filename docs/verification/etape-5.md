# Cahier de vérification — étape 5 : la valorisation et les rendements

L'étape 4 allait chercher les cours. **L'étape 5 s'en sert pour répondre aux questions qui
comptent** : ce que valent tes actifs, et ce qu'ils t'ont rapporté — en euros, en **TRI** et en
**TWRR** ([D-22](../decisions.md)). Par actif, par poche et au total, sur la période que tu
choisis. Tout en montants bruts, frais et taxes à part ([D-21](../decisions.md)).

Deux parties, comme aux cahiers précédents :

1. **les cas fictifs de la partie A**, à refaire sur papier ou dans un tableur — pour le TRI, avec
   la fonction `TRI.PAIEMENTS` d'Excel ou de LibreOffice ;
2. **tes vraies valeurs**, en face de l'application Trade Republic (partie B).

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à toi
vont dans `etape-5.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## Les trois arbitrages de l'étape, en une page

| Décision | Ce qui s'applique |
|---|---|
| [D-52](../decisions.md) | La valeur d'« aujourd'hui » est celle de la **dernière clôture connue**, et le rapport écrit quel jour. Rien de la séance en cours |
| [D-53](../decisions.md) | Un actif **sans cours** n'est pas valorisé : il sort de la valeur et des trois chiffres, **achats compris**, et les totaux sont marqués **partiels** |
| [D-54](../decisions.md) | Les conventions qui rendent les chiffres refaisables : période bornes comprises, flux signés, TRI façon `TRI.PAIEMENTS`, TWRR aux cours de clôture |

---

## Les trois chiffres, en une phrase chacun

- **Gain en euros** : ce que tu as à la fin, moins ce que tu avais au début, moins ce que tu as mis,
  plus ce que tu as retiré (ventes, dividendes, distributions). C'est le chiffre principal.
- **TRI** (taux de rendement interne) : le taux annuel qu'aurait servi un livret pour te donner
  exactement le même résultat, avec tes dates et tes montants. Il mesure **ton** rendement.
- **TWRR** (rendement pondéré dans le temps) : ce qu'aurait fait 1 € laissé dedans du début à la
  fin, sans tenir compte de quand tu as ajouté ou retiré. Il mesure le rendement de **la
  stratégie**, pas de tes choix de date.

Sur moins d'un an, TRI et TWRR sont **peu significatifs**, et le rapport le dit : +20 % en un mois
fait plus de 700 % par an, un chiffre exact et sans intérêt.

---

## A. Cas fictifs, à refaire à la main

Ces cas sont **exactement ceux que les tests font calculer au programme**
(`tests/moteur/test_rendements.py`, même numérotation). Si ce document et le code divergeaient,
les tests le diraient. Les valeurs sont choisies pour tomber juste : quand un TRI vaut 10 %, c'est
10,000000 %, pas 9,99 %.

### A.1 — Le gain, et sa décomposition

L'enchaînement du cahier de l'étape 3 : 10 parts à 20 € le 5 janvier, 10 parts à 30 € le 5 février,
5 parts vendues à 40 € le 5 mars ; puis un dividende de **5,00 € brut** le 20 mars (1,50 € de
retenue). Le **31 mars 2026**, le cours de clôture est **40,00 €**.

| | Calcul | Résultat |
|---|---|---|
| Valeur à la fin | 15 parts × 40,00 | **600,00 €** |
| Valeur au début | rien détenu avant le 5 janvier | 0,00 € |
| Achats | 200 + 300 | 500,00 € |
| Ventes | 5 × 40 | 200,00 € |
| Dividendes | brut, pas 3,50 ([D-29](../decisions.md)) | 5,00 € |
| **Gain** | 600 − 0 − 500 + 200 + 5 | **+305,00 €** |

**La décomposition, à vérifier toi-même :** plus-value latente (600 − 375 de capital investi =
225) + plus-value réalisée brute (75, cahier de l'étape 3) + dividendes (5) = **305**. Les deux
comptabilités — celle du journal et celle des cours — retombent sur le même chiffre. Un test le
vérifie au centime.

### A.2 — Le TRI le plus simple : 10 %, exactement

1 000 € investis le **1er janvier 2025** (10 parts à 100 €). Le **1er janvier 2026**, le cours est
de 110 € : la position vaut 1 100 €. Aucun autre flux.

**Dans un tableur** (Excel ou LibreOffice) :

| | A (dates) | B (montants) |
|---|---|---|
| 1 | 01/01/2025 | −1000 |
| 2 | 01/01/2026 | 1100 |
| 3 | | `=TRI.PAIEMENTS(B1:B2;A1:A2)` |

Résultat : **10,00 %**. Le programme trouve **0,100000**, soit 10,0000 %. Comme la période fait
exactement 365 jours, le TWRR vaut aussi 10 % et il n'y a rien à annualiser.

> C'est le cas à refaire en premier. Si tu retombes sur 10 %, tu as compris ce que le programme
> fait ; tout le reste n'est que des lignes de plus dans la même table.

### A.3 — Deux achats, et un TRI qui vaut encore 10 %

10 parts à 100 € le **1er janvier 2025**, 10 parts à 100 € le **1er janvier 2026** (le cours n'a pas
bougé). Le **1er janvier 2027**, le cours est de **115,50 €** : 20 parts valent **2 310 €**.

| | A (dates) | B (montants) |
|---|---|---|
| 1 | 01/01/2025 | −1000 |
| 2 | 01/01/2026 | −1000 |
| 3 | 01/01/2027 | 2310 |
| 4 | | `=TRI.PAIEMENTS(B1:B3;A1:A3)` |

Résultat : **10,00 %**. (Pour les curieux : −1000 − 1000/(1+r) + 2310/(1+r)² = 0 a pour solution
1/(1+r) = 10/11.)

**Et le TWRR ?** Année 1 : de 100 à 100, soit **0 %**. Année 2 : de 100 à 115,50, soit **+15,5 %**.
TWRR sur deux ans = 1,00 × 1,155 − 1 = **15,5 %**, soit **7,47 % par an** (racine carrée de 1,155,
moins un). Il est plus bas que le TRI : le second achat est tombé la bonne année, et c'est ton
timing, pas la stratégie, qui a fait la différence.

### A.4 — Acheter juste avant la baisse : la stratégie fait 0 %, toi −26,8 % ⚠️

10 parts à 100 € le 1er janvier 2025. Le cours **double** : 200 € le 1er janvier 2026, et tu
rachètes 10 parts à 200 €. Le cours **retombe** à 100 € le 1er janvier 2027 : 20 parts valent
2 000 €.

| | A (dates) | B (montants) |
|---|---|---|
| 1 | 01/01/2025 | −1000 |
| 2 | 01/01/2026 | −2000 |
| 3 | 01/01/2027 | 2000 |
| 4 | | `=TRI.PAIEMENTS(B1:B3;A1:A3)` |

Résultat : **−26,79 %** par an. Tu as mis 3 000 € et tu as 2 000 € : le gain est **−1 000 €**.

**Et le TWRR ?** Année 1 : +100 %. Année 2 : −50 %. TWRR = 2,00 × 0,50 − 1 = **0 %**. La stratégie
« détenir cet actif » n'a rien gagné ni rien perdu sur deux ans ; c'est le fait d'avoir mis le plus
gros au plus haut qui a coûté.

**Ce qu'il faut retenir :** les deux taux répondent à deux questions différentes, et **aucun n'est
faux**. Le TRI dit ce que ton argent a fait ; le TWRR dit ce que l'actif a fait.

### A.5 — Une période qui commence après le premier achat

Le portefeuille du A.3, regardé **du 1er janvier 2026 au 1er janvier 2027** seulement.

| | Calcul | Résultat |
|---|---|---|
| Valeur au début | 10 parts × 100 €, au soir de la **veille** (31 décembre 2025) | 1 000,00 € |
| Achats de la période | celui du 1er janvier 2026 | 1 000,00 € |
| Valeur à la fin | 20 × 115,50 | 2 310,00 € |
| **Gain** | 2 310 − 1 000 − 1 000 | **+310,00 €** |

Dans la table du TRI, la valeur au début devient un **achat à la veille** : une ligne
`31/12/2025 ; −1000`. Le TRI est alors presque 15,5 % (un jour de plus qu'une année pleine), et le
TWRR exactement 15,5 %.

> **La convention à connaître :** la période est **bornes comprises**. Les opérations du jour de
> début en font partie, et la valeur de départ est celle de la veille au soir ([D-54](../decisions.md)).

### A.6 — Dividende et distribution de capital : les deux comptent comme de l'argent qui sort

10 parts à 30 € le 5 janvier (300 €). Un dividende de 5 € brut le 1er février, une **distribution
de capital** de 12 € le 1er mars. Le cours reste à 30 € : la position vaut 300 € le 31 mars.

| | Calcul | Résultat |
|---|---|---|
| Gain | 300 − 300 + 5 + 12 | **+17,00 €** |
| Vérification | plus-value latente (300 − 288 de capital investi) 12 + dividende 5 | 17 |

La distribution a fait baisser le capital investi ([D-14](../decisions.md)) : elle est bien un
flux qui te revient, et c'est ce qui fait tenir la décomposition.

### A.7 — Ce que le programme refuse de calculer, et pourquoi

| Situation | Ce qui s'affiche |
|---|---|
| Des titres reçus **sans prix** dans la période (actions gratuites pas encore valorisées, [D-15](../decisions.md)) | la **valeur** de la position (les parts sont là), mais gain et TRI **« non calculables »**, avec la raison : on ne sait pas ce qui a été mis |
| Les mêmes titres reçus **avant** la période | tout se calcule : les parts sont là au début comme à la fin |
| Une vente au-delà des parts comptées (histoire trouée, [D-45](../decisions.md)) | les chiffres, mais marqués **« non fiable »** |
| Un actif **sans cours** à la date de fin | il sort de tout, et les totaux sont **« PARTIEL »**, avec son nom ([D-53](../decisions.md)) |
| Aucun cours un **jour de flux** ou à la veille du début | le gain se calcule s'il peut ; le TWRR ou le TRI dit **quel jour** manque |
| Aucune opération dans la période | rien n'est calculé, et c'est dit |

**Rien n'est jamais remplacé par zéro en silence.**

### A.8 — Moins d'un an : peu significatif. Plus d'un an : le TWRR s'annualise

- Le A.1 dure 85 jours : le rapport écrit « TRI et TWRR portent sur moins d'un an : peu
  significatifs ».
- 10 parts à 100 € le 1er janvier 2025, cours 121 € le 1er janvier 2027 : TWRR **21 %** sur deux
  ans, **10 % par an** (1,21^(365/730) = 1,1). Le TRI vaut aussi 10 %.

### A.9 — Là où un tableur rendrait une erreur

- Des flux tous du même signe : pas de TRI, `TRI.PAIEMENTS` rend `#NOMBRE!`, le programme écrit
  pourquoi.
- Tout vendre le 5 février (à 22,50 €, au-dessus de la clôture de 22 €), puis racheter le 5 mars :
  entre les deux, rien n'est détenu, et cette sous-période **ne compte pas**. TWRR = 1,10 × 1,20 −
  1 = **32 %**. Avec la formule « valeur avant + flux », la base de la sous-période vide aurait été
  **négative** (220 − 225 = −5 €) et le TWRR aurait dit −100 % sur un actif gagnant : c'est pour
  cela que la valeur après un flux est prise aux **cours de clôture** ([D-54](../decisions.md)).

---

## B. Contrôles sur tes vraies données

```
uv run dashboard cours                          au besoin : complète le cache
uv run dashboard positions                      valeur à la dernière clôture, gain, TRI, TWRR
uv run dashboard positions --au 2026-06-30      arrêté et valorisé à une date
uv run dashboard positions --depuis 2026-01-01  le gain de l'année seulement
uv run dashboard exporter-positions             les six CSV, dont flux.csv
```

Aucune de ces commandes ne demande ton PIN : **rien ne passe par Trade Republic**
([D-49](../decisions.md)). Avec `--hors-ligne`, aucun appel réseau non plus.

### B.1 — Le contrôle principal : la valeur, actif par actif

Dans le bloc **« Valeur des actifs au … »**, pour chaque ligne :

- [ ] la **quantité** est celle du bloc des positions (et de Trade Republic, cahier de l'étape 3) ;
- [ ] le **cours** est celui de la clôture indiquée — compare-le à l'historique de ton application
      ou au site de la place, **à la même date** ;
- [ ] **quantité × cours = valeur**, au centime ;
- [ ] la **date** du cours : un lundi, c'est la clôture du vendredi, et c'est écrit.

> **L'écart avec Trade Republic est attendu.** Tu l'as mesuré à l'étape 4 : de l'ordre du
> demi-pour-cent par cours. Il se retrouve sur la valeur totale, donc sur le gain. Ce n'est pas une
> erreur de calcul ([D-48](../decisions.md)) : ce sont deux places, et Trade Republic affiche un
> prix courant là où l'application prend une clôture. Ce qui doit t'alerter : un écart de plusieurs
> pour cent sur un actif, ou un ordre de grandeur.

### B.2 — La valeur totale

- [ ] la **valeur totale** est la somme des lignes valorisées ;
- [ ] s'il y a des **« Non valorisés »**, ils sont bien ceux que tu attends (un actif laissé vide
      dans `actifs.toml`, par exemple), et le bloc « Cours de marché » en donne la raison ;
- [ ] compare au total de ton application, en gardant l'écart du B.1 en tête.

> **Si ta poche crypto sort en « non valorisé »**, c'est presque sûrement sa ligne dans
> `actifs.toml`. Une crypto n'a pas d'ISIN : Trade Republic l'identifie par un code interne
> `XF…`, qu'aucune source de cours ne connaît. L'assistant `dashboard actifs` ne peut donc rien
> proposer, et la ligne reste vide. Écris-la toi-même, sur le modèle
> `"XF000…" = { ticker = "BTC-EUR", devise = "EUR" }`, puis `dashboard cours --actif XF000…`.
> *Constaté par le propriétaire le 2026-09-27 : une fois la ligne remplie, l'écart avec son
> application était de moins de deux dixièmes de pour cent sur la valeur totale.*

### B.3 — Le gain

Depuis le début, le gain doit valoir **plus-values latentes + plus-values réalisées brutes +
dividendes bruts** :

- [ ] latente : valeur totale − capital net investi total (bloc « Ce qui est placé ») ;
- [ ] réalisées brutes et dividendes bruts : dans le même bloc ;
- [ ] la somme des trois est le **GAIN** du bloc des chiffres clés, au centime.

Si un actif est « non valorisé », fais la même somme **sans lui** : le gain partiel exclut aussi
ses achats et son capital ([D-53](../decisions.md)).

### B.4 — Le TRI, dans ton tableur

- [ ] `uv run dashboard exporter-positions`, puis ouvre `flux.csv` ;
- [ ] filtre la colonne `groupe` sur `total` ;
- [ ] `=TRI.PAIEMENTS(montants ; dates)` sur les deux colonnes ;
- [ ] tu dois retomber sur le **TRI (annuel)** du rapport, à la deuxième décimale près.

La dernière ligne du groupe est la **valeur à la fin**, en positif : c'est elle qui « solde » le
placement. Refais-le pour une poche (`PEA`, `CTO`, `crypto`) ou un actif : chaque groupe a sa
table.

### B.5 — Le TWRR, dans ton tableur

- [ ] ouvre `sous_periodes_twrr.csv`, filtre `groupe` sur `total` ;
- [ ] pour chaque ligne : `valeur_fin / valeur_debut − 1` doit donner la colonne `rendement` ;
- [ ] le produit des `(1 + rendement)`, moins 1, doit donner le **TWRR (sur la période)** ;
- [ ] `valeur_debut` d'une ligne est bien « parts détenues après les opérations du jour `du` ×
      clôture de ce jour » : prends une ligne et refais-la avec `journal.csv` et le cache des cours.

### B.6 — La période

- [ ] `--depuis` le 1er janvier : la **valeur au début** est celle du 31 décembre au soir, et les
      achats de la période ne comptent que ceux de l'année ;
- [ ] `--depuis` après `--au` : la commande refuse, avec un message.

### B.7 — L'évolution

`evolution.csv` donne la valeur du portefeuille **jour par jour** depuis la première opération, avec
le capital net investi en face. Ouvre-le dans un tableur et trace les deux colonnes : l'écart entre
les deux courbes est la plus-value latente, jour après jour. La colonne
`positions_non_valorisees` dit les jours où la valeur est partielle.

### B.8 — Ce que ton portefeuille ne peut pas prouver

Ton portefeuille a quelques mois. Le TRI et le TWRR y sont **peu significatifs**, et le rapport le
dit. Les règles délicates — période qui commence en cours de route, distribution de capital, tout
vendre puis racheter — ne sont prouvées que par les cas fictifs de la partie A. C'est normal, et
c'est pour cela qu'ils sont refaisables dans un tableur.

---

## Ce que cette étape ne vérifie pas encore

- **Le prix de la séance en cours.** La valeur affichée est celle de la dernière clôture
  ([D-52](../decisions.md)). Un prix « en direct » est une question pour l'interface (étape 9).
- **Les coûts estimés** — spread, TER — et la **valeur réelle** après frais de sortie et impôts :
  étape 6 ([D-17](../decisions.md), [D-23](../decisions.md)). Les trois chiffres de cette étape
  sont volontairement **bruts**.
- **Un regroupement d'actions** (*split*) : il fausserait la valeur des jours d'avant tant que le
  cache n'est pas repris (`oublier-cours`). Rien ne le détecte automatiquement.
