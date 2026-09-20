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

> Le prix de revient **fiscal** français inclut les frais d'achat. Si l'application estime un jour
> l'impôt, il sera recalculé à part.

### Capital brut (valeur)
Valeur de marché des actifs détenus. **Sans les espèces.**

```
Capital brut(t) = Σ_actifs quantité détenue(t) × cours(t)
```

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

### Gain (chiffre clé n° 1, en €)
Combien les actifs ont rapporté sur la période et les poches filtrées. **Montants bruts, sans frais
ni taxes** ([D-21](decisions.md), [D-22](decisions.md)).

```
Gain(période) = V_fin − V_début − Σ achats bruts + Σ ventes brutes + Σ dividendes
```

- `V_début`, `V_fin` : capital brut au début et à la fin de la période (0 avant le premier achat).
- Achats et ventes **bruts** : quantité × prix.
- Dividendes : **bruts**. La retenue d'impôt va dans les coûts ([D-29](decisions.md)).

Depuis le début, il se décompose en : plus-values latentes + plus-values réalisées brutes +
dividendes.

Exemple depuis le début : achat de 200 € brut, vente de 50 € brut, dividende de 5 €, valeur
actuelle 180 € → gain = 180 − 0 − 200 + 50 + 5 = **+35 €**.

---

## 5. Rendements

Chiffres clés n° 2 et 3. Ils mesurent le périmètre « actifs ». Les **flux** sont les mouvements
d'argent entre les espèces (hors périmètre) et les actifs : achats, ventes, dividendes, **pris en
montants bruts**. Frais et taxes n'y entrent pas ([D-21](decisions.md)). Sur un portefeuille de
moins d'un an environ, ces deux taux sont peu significatifs, et l'interface peut le signaler.

### TRI (taux de rendement interne, XIRR) — « rendement réel du capital »
Rendement annuel réellement obtenu, compte tenu de la date et du montant de chaque flux.

Le TRI est le taux `r` qui annule :

```
Σ_k  F_k / (1 + r)^((t_k − t_0) / 365)  +  V_T / (1 + r)^((T − t_0) / 365)  = 0
```

- `F_k` : flux vu par l'investisseur. Achat = négatif, vente et dividende = positif.
- `V_T` : capital brut à la date de fin `T`.
- Si la période commence après le premier achat, le capital brut au début compte comme un achat
  à cette date.

Exemple : 1 000 € investis le 1er janvier, valeur 1 100 € le 31 décembre, aucun autre flux →
TRI ≈ 10 %.

### TWRR (taux de rendement pondéré dans le temps) — « rendement théorique de la stratégie »
Rendement des placements **indépendamment** du calendrier des achats et des ventes. On découpe la
période à chaque flux et on enchaîne les sous-périodes :

```
TWRR = Π_i (1 + r_i) − 1        avec   r_i = V_fin,i / (V_début,i + F_i) − 1
```

- `V_début,i` : capital brut juste avant le flux.
- `F_i` : flux au début de la sous-période (achat +, vente et dividende −, vus depuis le
  portefeuille).
- `V_fin,i` : capital brut juste avant le flux suivant.

Annualisé si la période dépasse un an : `(1 + TWRR)^(365 / jours) − 1`. Nécessite un historique
de cours.

---

## 6. Coûts et valeur réelle

La synthèse est volontairement « brute ». Les coûts sont analysés à part
([D-21](decisions.md), [D-23](decisions.md)). Présentation à trancher : Q-21.

### Coûts payés
Frais et taxes réellement prélevés, lus dans les données : frais d'ordre, taxes à l'achat, taxes sur
dividendes.
```
Poids d'un coût dans son opération = coût / montant brut de l'opération
```
Exemple : 1 € de frais sur un achat brut de 25 € → 4 %.

### Valeur réelle — **règles fiscales à documenter**
Ce qu'on récupérerait en vendant tout aujourd'hui.
```
Valeur réelle = capital brut − frais de vente estimés − spread de vente estimé − impôts estimés sur les plus-values
```
- Frais de vente estimés : selon le type d'ordre de la poche (ex. frais fixe d'un ordre ponctuel).
- Spread de vente estimé : voir ci-dessous.
- Impôts estimés : selon la poche (PEA, CTO, crypto), l'ancienneté du PEA, et avec le prix de revient
  **fiscal** (frais d'achat inclus). Taux et règles à documenter avec leur source officielle.
  Estimation seulement, jamais une déclaration ([D-26](decisions.md)).

### Coûts estimés

Coûts que Trade Republic n'affiche pas comme des frais. Ils sont **estimés**, toujours affichés
comme estimations, et **jamais** mélangés aux frais réels ([D-17](decisions.md)).

#### Écart de prix (spread)
Différence entre le prix d'exécution et le prix de marché. **C'est un coût d'entrée et de sortie** :
il est payé à l'achat et à la vente, pas pendant la détention. Notable sur la crypto : « Kostenlos »
ne veut pas dire gratuit.
```
Spread estimé d'un achat ou d'une vente = montant brut × taux de spread par défaut du type d'actif
```
Les taux par défaut sont à documenter avec leur source.

#### Frais courants d'un fonds (TER)
Frais annuels prélevés dans la valeur d'un ETF. **C'est le seul coût payé pendant la détention.**
```
Coût annuel estimé = capital brut de l'actif × TER
```
Le TER vient d'une base de données d'actifs, à trouver.

---

## 7. Données

### Événement
Une entrée de `all_events.json`. Voir [inventaire-donnees.md](inventaire-donnees.md).

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
