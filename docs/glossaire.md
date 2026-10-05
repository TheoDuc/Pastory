# Glossaire

Chaque notion a **une seule** définition dans le projet. Quand une formule dépend d'un arbitrage
non rendu, elle renvoie à la question concernée ([questions-ouvertes.md](questions-ouvertes.md))
et porte le statut **provisoire**.

Exemples : valeurs **fictives**.

---

## 1. Périmètre

### Périmètre de l'application
**Les actifs achetés et ce qui leur arrive** : achat, évolution, revenus, vente, et les frais et
taxes appliqués à l'entrée et à la sortie ([D-11](decisions.md)).

**Hors périmètre : les espèces**, où qu'elles soient (compte courant, argent en attente sur le
compte espèces du PEA). Donc aussi : l'origine de l'argent, les virements, les paiements carte,
les intérêts sur espèces, les primes en espèces, l'euro d'activation du PEA, les transferts entre
comptes.

### Poche
Enveloppe dans laquelle un actif est détenu :
- **PEA** : Plan d'Épargne en Actions.
- **CTO** : compte-titres ordinaire (Trade Republic l'appelle « Brokerage »).
- **Crypto** : actifs dont le code commence par `XF`. C'est une déduction, que l'utilisateur peut
  corriger ([D-16](decisions.md)).

Il n'existe **pas** de poche « Espèces ».

### Compte espèces
Compte d'argent chez Trade Republic (`cashAccountNumber`). Il n'est pas suivi en tant que tel. Il
sert seulement à savoir dans quelle poche un achat a eu lieu (achat sur le compte espèces du PEA
→ poche PEA).

---

## 2. Opérations sur un actif

Pour un achat ou une vente, Trade Republic donne un **montant réglé** (`amount.value`) qui inclut
frais et taxes. On le décompose :

```
Achat :  montant payé  = montant brut + frais + taxes
Vente :  montant reçu  = montant brut − frais − taxes
avec     montant brut  = quantité × prix unitaire
```

Exemple : achat de 10 parts à 20 € avec 1 € de frais → payé 201 €, brut 200 €, frais 1 €.

### Frais
Frais facturés par Trade Republic (libellé « Gebühr »). Ex. 1 € par ordre ponctuel ; plans
d'épargne « Kostenlos ».

### Taxes
Impôts et taxes prélevés sur une opération (libellés « Steuer », « Steuern ») : taxe sur les
transactions financières à l'achat de certaines actions, retenues sur dividendes. **Catégorie
distincte des frais** ([D-12](decisions.md)).

### Titres reçus sans achat
Titres qui apparaissent sans paiement : action gagnée, actions gratuites, titres transférés depuis
un autre établissement. **Prix d'achat retenu = cours de l'actif le jour où il apparaît** (montant
brut = quantité × ce cours, frais 0, taxes 0). C'est une déduction, signalée dans l'application
([D-15](decisions.md)).

---

## 3. Capital

### Capital net investi (d'un actif)
Ce qui est **réellement placé dans l'actif**, après frais et taxes ([D-12](decisions.md)).

- **À l'achat :** il augmente du **montant brut**.
- **À la vente :** il diminue **au prorata des quantités vendues**.

```
Achat :  CNI ← CNI + montant brut
Vente :  CNI ← CNI × (1 − quantité vendue / quantité détenue avant la vente)
```

- **Distribution de capital** (« Kapitalverteilung ») : CNI ← CNI − montant brut distribué
  ([D-14](decisions.md)), **sans jamais passer sous zéro** ([D-45](decisions.md)) : une
  distribution ne peut pas rendre plus que ce qui a été mis, et l'excédent est signalé.

Exemple :
1. Achat de 10 parts pour 201 € dont 1 € de frais → CNI = 200 €.
2. Achat de 10 parts à 30 € sans frais → CNI = 500 €, 20 parts.
3. Vente de 5 parts (25 % des parts) → CNI = 500 × 0,75 = 375 €.

**Comment le moteur l'écrit** ([D-44](decisions.md)). À la vente, il calcule d'abord ce qui
**sort**, puis le retranche :

```
capital retiré = CNI × (quantité vendue / quantité détenue avant)
CNI            = CNI − capital retiré
```

C'est la même chose, écrite dans l'ordre où on la refait de tête — « la moitié de mes parts
part, donc la moitié de ma mise part » — et les deux morceaux retombent exactement sur le
capital d'avant, sans centime perdu. Le CNI est **arrondi au centime après chaque opération**,
comme le ferait une main.

### Capital net investi (d'une poche, du total)
Somme des capitaux nets investis des actifs de la poche, ou de tous les actifs.

### Prix de revient unitaire (PRU)
Prix moyen pondéré (PMP), **hors frais et hors taxes** ([D-13](decisions.md)) :

```
PRU = CNI / quantité détenue
```

Il change à chaque achat, pas à la vente. Dans l'exemple ci-dessus : 10 € après l'étape 1, 25 €
après l'étape 2, toujours 25 € après l'étape 3.

**Deux cas où l'application n'affiche aucun prix de revient** ([D-45](decisions.md)) :

- **plus aucune part détenue** : diviser par zéro ne veut rien dire ;
- **histoire incomplète** : des parts sont entrées sans prix connu ([D-15](decisions.md)), donc
  le capital connu ne couvre pas toutes les parts détenues. La division donnerait un prix de
  revient **artificiellement bas** — 200 € pour 13 parts dont 3 sans prix font 15,38 €, un
  chiffre crédible et faux. L'application écrit « à compléter » : le nombre reviendra quand les
  cours de l'étape 4 auront rempli les prix manquants.

> Le prix de revient **fiscal** français inclut les frais d'achat. L'application le tient
> désormais **à côté** de celui-ci, dans une colonne séparée, pour estimer l'impôt de sortie :
> voir le §6 ([D-57](decisions.md)).

### Capital brut (valeur)
Valeur de marché des actifs détenus. **Sans les espèces.**

```
Capital brut(t) = Σ_actifs quantité détenue(t) × cours(t)
```

- `cours(t)` : le **cours de clôture** du dernier jour coté au plus tard `t` (dix jours de recul
  au maximum, jamais d'interpolation). Un samedi prend le vendredi, et **la date du cours est
  affichée**. La valeur d'« aujourd'hui » est donc celle de la **dernière séance close**
  ([D-52](decisions.md)).
- La valeur d'une position est arrêtée au centime. Le cours, lui, est gardé tel quel pour que
  la multiplication se refasse à la main.
- Un actif **sans cours utilisable** (non déclaré, ticker inconnu, devise inattendue, cours
  trop ancien) n'est **pas valorisé** : il sort du total, qui est alors marqué **partiel** et
  dit lequel manque ([D-53](decisions.md)). Jamais un zéro silencieux.

Exemple : 15 parts, cours de clôture 40,00 € → capital brut **600,00 €**.

---

## 4. Gains

### Plus-value latente (d'un actif)
```
Plus-value latente = capital brut − CNI
```

### Plus-value réalisée (d'une vente)
```
PV réalisée brute = montant brut de la vente − CNI retiré par la vente
PV réalisée nette = PV réalisée brute − frais de la vente − taxes de la vente
```
Exemple, suite de l'étape 3 : 5 parts vendues à 40 € avec 1 € de frais. Montant brut 200 €, CNI
retiré 125 € → PV brute +75 €, PV nette +74 €.

### Revenus
Dividendes versés par un actif. **Comptent comme rendement de l'actif**, jamais comme apport
([D-14](decisions.md)). Le montant brut, la taxe et le montant net sont conservés. Une fois versé,
l'argent part dans les espèces et sort du périmètre.

### Période
Les trois chiffres clés se calculent sur une période `[début, fin]`, **bornes comprises**
([D-54](decisions.md)) :

- `V_début` est le capital brut **au soir de la veille** du début : les opérations du jour de
  début sont dans la période. Sans début (« depuis le début »), `V_début = 0` ;
- `V_fin` est le capital brut au soir de la fin. Sans `--au`, la fin est aujourd'hui, valorisé à
  la dernière clôture connue ([D-52](decisions.md)).

### Flux
Les mouvements d'argent entre les espèces (hors périmètre) et les actifs, **en montants bruts**,
vus par l'investisseur ([format-pivot §3](format-pivot.md)) :

| Type | Signe | Pourquoi |
|---|---|---|
| `achat`, `titres_recus` | **négatif** | de l'argent entre dans l'actif ; des titres reçus valent leur cours du jour ([D-15](decisions.md)) |
| `vente`, `dividende`, `distribution_capital` | **positif** | de l'argent en sort |

Frais et taxes n'y entrent pas ([D-21](decisions.md)) ; le dividende est **brut**
([D-29](decisions.md)). Une opération dont le montant brut attend encore un cours rend le gain,
le TRI et le TWRR de son actif **non calculables** sur toute période qui la contient
([D-45](decisions.md)) : la valeur reste affichée, les trois chiffres non.

### Gain (chiffre clé n° 1, en €)
Combien les actifs ont rapporté sur la période et les poches filtrées. **Montants bruts, sans frais
ni taxes** ([D-21](decisions.md), [D-22](decisions.md)).

```
Gain(période) = V_fin − V_début + Σ flux
              = V_fin − V_début − achats + ventes + dividendes + distributions de capital
```

Depuis le début, il se décompose **exactement** en : plus-values latentes + plus-values réalisées
brutes + dividendes. (C'est parce que la distribution de capital est un flux que l'identité
tient : elle a baissé le capital net investi, donc gonflé la plus-value latente d'autant.) Un
test du moteur vérifie cette identité.

Exemple depuis le début : achat de 200 € brut, vente de 50 € brut, dividende de 5 €, valeur
actuelle 180 € → gain = 180 − 0 − 200 + 50 + 5 = **+35 €**.

Un actif détenu sans cours à la date de fin sort du gain, **achats compris** : le chiffre décrit
les actifs valorisés, et il est marqué partiel ([D-53](decisions.md)).

---

## 5. Rendements

Chiffres clés n° 2 et 3. Ils mesurent le périmètre « actifs », sur les flux définis au §4.
**Sur moins de 365 jours, ces deux taux sont marqués « peu significatifs »** : un gain de 20 % en
un mois fait plus de 700 % par an, et le chiffre est exact sans rien vouloir dire
([D-22](decisions.md)). Les taux sont arrêtés à six décimales (0,0001 %).

### TRI (taux de rendement interne, XIRR) — « rendement réel du capital »
Rendement annuel réellement obtenu, compte tenu de la date et du montant de chaque flux.

Le TRI est le taux `r` qui annule :

```
−V_début  +  Σ_k  F_k / (1 + r)^((t_k − t_0) / 365)  +  V_fin / (1 + r)^((T − t_0) / 365)  = 0
```

- `F_k` : flux signés du §4, à leur date `t_k`. `t_0` est la première date de la table.
- `V_début`, s'il n'est pas nul, compte comme un achat **à la veille** du début.
- `V_fin` : capital brut à la date de fin `T`.
- C'est exactement la convention de `TRI.PAIEMENTS` (`XIRR`) dans un tableur, avec des années
  de 365 jours : `flux.csv` donne la table à coller ([D-54](decisions.md)).
- Le taux est cherché **par dichotomie** entre −99 % et +100 000 % par an. S'il n'y en a pas
  (flux tous du même signe, résultat hors de toute mesure), l'application le dit au lieu
  d'afficher un nombre.

Exemple : 1 000 € investis le 1er janvier 2025, valeur 1 100 € le 1er janvier 2026, aucun autre
flux → TRI = **10,00 %** exactement (365 jours).

### TWRR (taux de rendement pondéré dans le temps) — « rendement théorique de la stratégie »
Rendement des placements **indépendamment** du calendrier des achats et des ventes. On découpe la
période à chaque **jour** portant un flux et on enchaîne les sous-périodes :

```
TWRR = Π_i (1 + r_i) − 1        avec   r_i = V_fin,i / V_début,i − 1
```

- `V_début,i` : capital brut **juste après** les flux du jour qui ouvre la sous-période, pris
  **aux cours de clôture de ce jour** : parts détenues après les opérations × clôture.
- `V_fin,i` : capital brut **juste avant** les flux du jour qui la ferme : parts détenues la
  veille × clôture de ce jour. Pour la dernière sous-période, c'est `V_fin`.
- Si `V_début` n'est pas nul, une première sous-période part de lui.
- Une sous-période où rien n'est détenu d'un bout à l'autre ne compte pas (tout vendu, puis
  racheté plus tard).

> **Pourquoi « après le flux, aux cours de clôture » et non « avant le flux + le flux »** : avec
> des cours de clôture et des flux au prix d'exécution, la seconde écriture donne une base
> négative dès qu'on vend tout quelques centimes au-dessus de la clôture — et un TWRR de −100 %
> sur un actif qui a gagné. La première n'invente aucun rendement entre le prix d'exécution et la
> clôture : cet écart-là est attribué au moment du flux, pas à la stratégie
> ([D-54](decisions.md)). Les deux écritures se refont dans un tableur à partir des quantités et
> des cours ; `sous_periodes_twrr.csv` donne chaque `V_début,i` et `V_fin,i`.

**Annualisé** seulement si la période dépasse 365 jours : `(1 + TWRR)^(365 / jours) − 1`.

Exemple : 10 parts à 100 € ; le cours double ; on rachète 10 parts à 200 € ; le cours revient à
100 €. TWRR = (1 + 100 %) × (1 − 50 %) − 1 = **0 %** — la stratégie n'a rien gagné — alors que
le TRI vaut **−26,79 %** : l'investisseur a mis le plus gros au plus haut. C'est toute la
différence entre les deux.

---

## 6. Coûts et valeur réelle

La synthèse est volontairement « brute ». Les coûts sont analysés à part
([D-21](decisions.md), [D-23](decisions.md)). Présentation à l'écran à trancher à l'étape 8
(Q-21) ; les calculs, eux, sont écrits ici.

**Une distinction porte tout ce paragraphe** : ce qui est **payé** est lu dans les données ; ce
qui est **estimé** est reconstitué avec un taux. Les deux ne se mélangent jamais dans un total,
et l'application écrit « estimé » partout où ça l'est ([D-17](decisions.md)).

### Coûts payés
Frais et taxes réellement prélevés, lus dans les données : frais d'ordre, taxes à l'achat, taxes
sur dividendes. Ils se rangent par **moment** : à l'entrée, à la sortie, sur les revenus (les
trois niveaux de Q-21).

```
Poids d'un coût dans son opération = (frais + taxes) / montant brut de l'opération
```

Exemple : 1 € de frais sur un achat brut de 25 € → **4 %**. Le poids n'existe pas quand le
montant brut est inconnu ([D-15](decisions.md)) : la case reste vide, jamais à zéro.

### Coûts estimés

Coûts que Trade Republic n'affiche pas comme des frais. Ils sont **estimés**, toujours affichés
comme estimations, et **jamais** mélangés aux frais réels ([D-17](decisions.md)).

#### Écart de prix (spread)
Différence entre le prix d'exécution et le prix de marché. **C'est un coût d'entrée et de
sortie** : il est payé à l'achat et à la vente, pas pendant la détention
([D-30](decisions.md)). Notable sur la crypto : « Kostenlos » ne veut pas dire gratuit.

```
Spread estimé d'un achat ou d'une vente = montant brut × taux par côté du type d'actif
```

Le **taux par côté** est la moitié de l'écart achat/vente publié : on en paie une moitié en
achetant, l'autre en vendant ([D-56](decisions.md)). Les taux par défaut — ETF 0,05 %, action
0,10 %, crypto 0,50 % — vivent dans `parametres/couts.toml` avec leur fourchette et leur source
([couts-et-fiscalite.md §4](couts-et-fiscalite.md)). Un actif peut recevoir le sien dans
`actifs.toml`.

Un actif **sans type déclaré** n'a aucun spread estimé, et le total est marqué partiel
([D-55](decisions.md)). Une opération sans exécution — dividende, titres reçus — n'en paie aucun.

#### Frais courants d'un fonds (TER)
Frais annuels prélevés dans la valeur d'un ETF. **C'est le seul coût payé pendant la
détention.**

```
Coût annuel estimé = capital brut de l'actif × TER
```

Exemple : 600 € à 0,20 % → **1,20 € par an**. Le TER est **proposé** depuis la liste des ETF de
Xetra et **validé** par l'utilisateur ([D-61](decisions.md)) ; sans valeur validée, rien n'est
estimé.

### Prix de revient fiscal
Prix de revient au sens de l'impôt français : c'est une moyenne pondérée, **frais et taxes
d'acquisition compris** ([D-57](decisions.md)). Il vit à côté du prix de revient
([D-13](decisions.md)), qui les exclut — les deux sont justes, ils ne répondent pas à la même
question.

```
Achat :  capital fiscal ← capital fiscal + montant brut + frais + taxes
Vente :  capital fiscal ← capital fiscal − capital fiscal × (quantité vendue / quantité détenue)
Prix de revient fiscal = capital fiscal / quantité détenue
```

Comme le capital investi, il est arrêté au centime après chaque opération, et il n'est **pas
affiché** quand l'histoire est incomplète ([D-45](decisions.md)). Il n'entre dans aucune
performance ([D-21](decisions.md)). Pour la **crypto**, la base imposable part du capital net
investi, frais exclus : la loi ne nomme pas les frais d'acquisition, et l'application retient la
lecture prudente.

### Valeur réelle
Ce qu'on récupérerait en vendant tout aujourd'hui ([D-23](decisions.md)).

```
Cession nette d'une position = capital brut − spread de vente estimé − frais de vente estimés
Valeur réelle d'une poche    = Σ cessions nettes − impôt estimé de la poche
Valeur réelle totale         = Σ valeurs réelles des poches
```

Les frais de vente estimés valent **un ordre par ligne vendue** (1 € chez Trade Republic, titres
comme crypto, `parametres/couts.toml`). Une position détenue **sans cours** n'a pas de valeur
réelle : elle sort du total, qui est marqué partiel ([D-53](decisions.md)). Un actif **sans type**
en sort aussi, faute de pouvoir estimer son spread.

**Le cas du PEA, et pourquoi sa valeur réelle est minorée.** L'impôt du PEA porte sur le gain
**du plan**, qui compte les ventes passées et les dividendes. Leur argent est dans les **espèces
du plan**, que l'application ne suit pas ([D-11](decisions.md)) : son impôt est donc retranché,
alors que lui-même n'est pas compté dans la valeur. La valeur réelle du PEA est ainsi **inférieure
à ce qu'on toucherait**, et le rapport l'écrit avec le montant concerné. Si l'impôt du plan
dépassait ce que les titres rapporteraient — un PEA presque entièrement vendu —, **aucun chiffre
n'est affiché** : un nombre négatif laisserait croire à une perte.

### Impôt estimé
Une **estimation**, jamais une déclaration ([D-26](decisions.md)). Le prélèvement forfaitaire
unique s'applique de plein droit ([D-60](decisions.md)) ; les taux et leurs sources sont dans
`parametres/fiscalite.toml`. En 2026 : impôt sur le revenu **12,8 %**, prélèvements sociaux
**18,6 %**, soit **31,4 %**. Le détail des textes est dans
[couts-et-fiscalite.md §5](couts-et-fiscalite.md).

**CTO** — plus-values de cession de valeurs mobilières :
```
Base = Σ (cession nette − capital fiscal) sur les lignes du CTO, pertes comprises
       puis plancher à zéro
Impôt = base × (12,8 % + 18,6 %)
```
Les pertes se déduisent des gains ; si le total est négatif, l'impôt est nul.

**PEA** — le gain est celui du **plan**, pas des titres :
```
Gain du plan = Σ plus-values latentes (après spread et frais de vente)
             + Σ plus-values réalisées brutes
             + Σ dividendes bruts
             − Σ frais − Σ taxes payés dans le plan
Impôt = gain × 31,4 %   si le plan a moins de 5 ans (et retirer le clôture)
      = gain × 18,6 %   à partir de 5 ans (exonéré d'impôt sur le revenu)
```
Les cinq ans se comptent depuis le **premier versement**, une date que l'utilisateur déclare
([D-59](decisions.md)). L'égalité entre ce gain et « valeur liquidative − versements » est
démontrée dans [couts-et-fiscalite.md §5.3](couts-et-fiscalite.md), sous trois hypothèses que le
rapport affiche : aucun retrait passé, ni intérêt ni frais sur les espèces, tout mouvement
d'espèces rattaché à une opération connue. Si **une** position du PEA n'a pas de cours, la poche
entière est non calculable : un gain de plan à moitié n'existe pas.

**Crypto** — actifs numériques :
```
Base = Σ (cession nette − capital net investi), plancher à zéro
     = 0 si le total des cessions de l'année ne dépasse pas 305 €
Impôt = base × 31,4 %
```
Le seuil de 305 € porte sur **toutes les cessions de l'année civile** : celles déjà faites, lues
dans l'export, **plus** celle qu'on simule. Deux ventes de 200 € font 400 €, donc plus
d'exonération. Les cessions déjà faites comptent dans le seuil mais **pas dans la base** : leur
impôt est dû quoi qu'il arrive ([D-60](decisions.md)).
Trois approximations, affichées : les frais d'achat n'entrent pas dans le prix d'acquisition ; la
réduction du prix d'acquisition après une vente passée se fait au prorata des parts et non en
valeur comme le veut la loi ; tout le portefeuille crypto est supposé chez Trade Republic.

**Ce que l'impôt estimé ne compte pas** : les dividendes déjà reçus et les plus-values déjà
réalisées dans l'année. Ces impôts sont dus que l'on vende ou non : ce ne sont pas des coûts de
sortie ([D-60](decisions.md)).

---

## 7. Données

### Événement
Une entrée de `all_events.json`, l'export de pytr, retiré à l'étape 8 ter
([D-81](decisions.md)). Voir [inventaire-donnees.md](inventaire-donnees.md). Son équivalent dans
l'export officiel est une **ligne** ([export-officiel.md](export-officiel.md)).

### Type d'événement
Valeur du champ `eventType`. Il peut être `null`.

### Type hors périmètre
Type connu qui ne concerne que les espèces (virement, carte, versement PEA, intérêts…). Il est
écarté mais **compté**, jamais confondu avec un type inconnu.

### Type inconnu
Type absent de toutes les listes. L'application doit **l'afficher**, jamais l'ignorer ni le ranger
par défaut.

### Déduction
Information absente des champs structurés, reconstituée par une règle. Elle doit être isolée dans
le code, documentée, et **signalée dans l'interface**.

### Fragilité
Dépendance à un texte affiché (libellé en langue de l'application, montant formaté).

---

## 8. Diversification

Tout ce paragraphe porte sur **une date** : celle de la valorisation. Une répartition est une photo,
jamais une moyenne sur une période.

### Composition d'un actif
Ce qu'il y a à l'intérieur : la part de sa valeur attribuée à chaque **pays** et à chaque
**secteur**, plus sa ventilation par **classe d'actifs** (actions, obligations, liquidités). Elle
porte toujours **sa source, sa nomenclature et sa date d'arrêté** ([D-63](decisions.md)).

Pour un **ETF synthétique**, la composition retenue est celle de l'**indice suivi**, et non celle du
panier détenu ([D-64](decisions.md)).

Pour une **action détenue en direct**, la composition est triviale : un seul pays et un seul
secteur, à 100 %.

Une **crypto** n'a pas de composition : ni pays, ni secteur ([D-68](decisions.md)).

### Poids d'un pays (d'un secteur, d'une classe d'actifs)
La somme, sur toutes les positions détenues, de la valeur de la position multipliée par la part que
sa composition attribue à ce pays.

```
poids du pays P (en €) = Σ sur les positions  valeur de la position × part de P dans sa composition
```

La **valeur de la position** est celle du §3 : quantité × cours de clôture. Une position sans cours
n'a pas de valeur, donc ne pèse nulle part ([D-53](decisions.md)).

Le pourcentage affiché rapporte ce poids à la **valeur totale des actifs valorisés** — jamais à la
somme des poids attribués, ce qui reviendrait à renormaliser ([D-69](decisions.md)).

```
pourcentage du pays P = poids du pays P / valeur totale des actifs valorisés
```

### Non attribué
La part de la valeur d'un actif que sa composition **n'attribue à rien** : liquidités du fonds,
dérivés, lignes non classées. Aucune composition ne somme à 100 % (99,43 % à 99,96 % mesuré selon
le fonds), et le prêt de titres peut même la faire dépasser. Cette part est **affichée comme
telle**, jamais répartie sur les autres postes.

```
non attribué (en €) = Σ sur les positions  valeur × (100 % − somme des parts attribuées)
```

### Non couvert
La valeur des actifs pour lesquels l'application **n'a aucune composition** : source muette sur cet
ISIN, actif dont l'application ignore le type, ou refus d'un contrôle de vraisemblance. Ces actifs
sortent des totaux, qui sont alors marqués **partiels**, et la liste de ce qui manque est affichée
avec son montant ([D-69](decisions.md)).

Un **ETF obligataire** n'est pas « non couvert » : il est **hors périmètre** de la géographie et des
secteurs, où ces notions n'ont pas le même sens, tout en comptant normalement dans la répartition
par classe d'actifs ([D-68](decisions.md)).

### Contenu déclaré
De quoi un actif est fait — **actions**, **obligations** ou **matières premières** — quand
l'utilisateur le déclare lui-même dans `actifs.toml` ([D-71](decisions.md)). À distinguer du
**type** (ETF, action, crypto), qui dit ce qu'on détient et porte les frais.

Un contenu déclaré suffit à ranger l'actif : il compte à 100 % dans sa classe, et il sort de la
géographie et des secteurs **sans être annoncé « inconnu »**. Un ETF d'obligations et un ETF de
matières premières n'ont ni pays ni secteur au sens des actions : c'est leur nature, pas une donnée
manquante.

### Hors actions
La part d'un fonds qui n'est pas investie en actions : obligations, matières premières, liquidités.
Elle sort de la géographie et des secteurs, et elle y est affichée **classe par classe** — jamais
sous un libellé unique, qui ferait passer de l'or pour de la dette.

### Non transparisé
Un **fonds de fonds** : un ETF dont les lignes sont elles-mêmes des fonds. L'application ne
transparise qu'**un** niveau : au-delà, elle ne devine pas.

**Ce mot n'apparaît jamais à l'écran** ([D-76](decisions.md)), et il est ici pour expliquer un
« non couvert ». La raison est qu'**aucune source accessible ne dit qu'un fonds est un fonds de
fonds** : extraETF n'a que six classes d'actifs et un tel fonds y tombe dans « autres », que le
garde-fou de [D-70](decisions.md) refuse déjà ; le service d'Amundi ([D-77](decisions.md)) a un
vocabulaire d'instruments, pas de véhicules. Un fonds de fonds est donc affiché
**« non couvert »**, comme tout fonds qu'on ne sait pas ouvrir, et la bulle d'aide de
« non couvert » mentionne que certains fonds en contiennent d'autres — sans prétendre que c'est le
cas de celui-là.

*La mesure qui justifie le refus, faite à l'étape 7 : sur un fonds de fonds, la composition de
premier niveau est « 100 % fonds d'investissement », et une source qui applique une nomenclature
sectorielle à ces lignes répond « 100 % finance, Irlande ». Crédible, absurde.*

### Zone
Un regroupement de pays — Amérique du Nord, Europe, Japon, Asie-Pacifique développée, marchés
émergents. **Ce n'est pas une donnée, c'est une convention** : la liste vit dans un fichier de
paramètres avec sa source et sa date, et elle est corrigeable ([D-67](decisions.md)). Les zones
« développé » et « émergent » ne font l'objet d'**aucune norme**, et les deux fournisseurs de
référence sont en désaccord sur plusieurs pays.

### Règle de pays
La question « de quel pays est cette société ? » a plusieurs réponses justes : pays de
domiciliation juridique, pays d'activité, pays de cotation principale. L'application emploie le
**pays d'activité** pour les ETF (celui de sa source) et le **siège social** pour les actions
détenues en direct, et **affiche cette différence** ([D-66](decisions.md)).

Ce n'est pas une imprécision de nos sources : un émetteur écrit lui-même que son exposition
géographique se rapporte « principalement » au domicile de l'émetteur, « mais, dans certains cas,
elle peut refléter le lieu où l'émetteur réalise l'essentiel de son activité ».
