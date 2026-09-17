# Glossaire

Chaque notion a **une seule** définition dans le projet. Quand une formule dépend d'un arbitrage
non rendu, elle renvoie à la question concernée ([questions-ouvertes.md](questions-ouvertes.md))
et porte le statut **provisoire**.

Exemples : valeurs **fictives**.

---

## 1. Comptes, poches et frontière

### Compte espèces
Compte d'argent chez Trade Republic, identifié dans les données par `cashAccountNumber`. Un client
peut en avoir plusieurs (ex. compte courant, compte espèces du PEA). **Un compte n'est pas une
poche** : il dit d'où part l'argent, pas forcément où vit le titre.

### Poche
Enveloppe dans laquelle un actif est détenu, avec sa propre fiscalité :
- **PEA** : Plan d'Épargne en Actions.
- **CTO** : compte-titres ordinaire (Trade Republic l'appelle « Brokerage »).
- **Crypto** : cryptoactifs, détenus hors PEA et hors CTO. *Définition à confirmer : Q-12.*
- **Espèces** : argent non investi. *Son inclusion dans les totaux est à trancher : Q-03.*

### Frontière Trade Republic
Limite entre « chez Trade Republic » et « le reste du monde ». **Seuls les flux qui franchissent
cette frontière sont des apports ou des retraits.**

### Flux externe
Mouvement d'argent qui franchit la frontière.
- **Apport** (+) : argent qui entre, ex. virement reçu depuis une banque.
- **Retrait** (−) : argent qui sort, ex. virement sortant, paiement par carte (*Q-02*).

### Transfert interne
Mouvement d'argent entre deux comptes Trade Republic du même client, ex. compte courant → compte
espèces du PEA. **Ce n'est ni un apport ni un retrait.** Il ne compte jamais dans le capital net
investi global. Il ne sert qu'à répartir ce capital entre les poches.

### Revenu
Argent reçu sans qu'il vienne de la poche de l'investisseur : dividende, intérêt, prime.
*Le fait de le compter comme rendement plutôt que comme apport est à trancher : Q-01.*

---

## 2. Montants du patrimoine

### Capital net investi (global)
Ce que l'investisseur a réellement apporté de sa poche, net de ce qu'il a retiré.

```
Capital net investi(t) = Σ apports externes jusqu'à t − Σ retraits externes jusqu'à t
```

Exemple : virements reçus 1 000 € + 500 €, dépense carte 20 € → 1 480 €.

Ne contient **jamais** : les achats, les ventes, les transferts internes, les revenus (sous réserve
de Q-01).

### Capital net investi par poche — **provisoire (Q-04)**
Proposition : flux nets entrés dans la poche.
- PEA : Σ versements compte courant → PEA − Σ retraits PEA → compte courant.
- CTO et crypto : Σ achats − Σ produits de ventes, frais inclus.

### Capital brut (valeur du portefeuille)
Valeur de marché de ce qui est détenu à la date t.

```
Capital brut(t) = Σ_actifs (quantité détenue(t) × cours(t)) [+ espèces(t) : Q-03]
```

Dépend d'une source de cours : Q-14.

### Gain total (en €)
```
Gain total(t) = Capital brut(t) − Capital net investi(t)
```

### Gains relatifs (en %) — **provisoire (Q-06)**
Proposition : `Gain total(t) / Capital net investi(t)`. Ce pourcentage ne tient pas compte de la
date des apports : il n'est **pas** un rendement annuel. Voir TRI et TWRR.

---

## 3. Coût et plus-values

### Quantité détenue
```
Quantité(t) = Σ quantités achetées − Σ quantités vendues + Σ quantités reçues sans paiement
```
Les « quantités reçues sans paiement » sont par exemple les actions gratuites ou une action gagnée
(voir l'inventaire).

### Prix de revient unitaire (PRU) — **méthode provisoire (Q-05)**
Proposition : prix moyen pondéré d'acquisition (PMP), frais d'achat inclus.

```
PRU = (Σ montants payés à l'achat, frais inclus) / (Σ quantités achetées)
```
recalculé à chaque achat. Une vente ne modifie pas le PRU. Exemple : 2 parts à 10 €, puis 2 parts
à 14 € → PRU = 12 €.

### Plus-value latente
```
Plus-value latente = quantité détenue × cours actuel − quantité détenue × PRU
```

### Plus-value réalisée
```
Plus-value réalisée = produit de la vente (net de frais) − quantité vendue × PRU au moment de la vente
```
Exemple : vente de 1 part à 15 € avec 1 € de frais, PRU 12 € → 15 − 1 − 12 = +2 €.

---

## 4. Rendements

### TRI (taux de rendement interne, XIRR) — « rendement réel du capital »
Rendement annuel réellement obtenu **par l'investisseur**, compte tenu de la date et du montant
de ses apports. Il est sensible au calendrier des apports.

Le TRI est le taux `r` qui annule :

```
Σ_k  F_k / (1 + r)^((t_k − t_0) / 365)  +  V_T / (1 + r)^((T − t_0) / 365)  = 0
```

- `F_k` : flux **externes** vus par l'investisseur. Apport = négatif (il sort de sa poche),
  retrait = positif.
- `V_T` : capital brut à la date de fin `T`.
- `t_0` : date du premier flux de la période.
- Si la période ne commence pas au premier apport, la valeur du portefeuille au début compte comme
  un apport initial.

Exemple : 1 000 € apportés le 1er janvier, portefeuille à 1 100 € le 31 décembre → TRI ≈ 10 %.

### TWRR (taux de rendement pondéré dans le temps) — « rendement théorique de la stratégie »
Rendement des placements **indépendamment** du calendrier des apports. On découpe la période à
chaque flux externe et on enchaîne les rendements des sous-périodes :

```
TWRR = Π_i (1 + r_i) − 1        avec   r_i = V_fin,i / (V_début,i + F_i) − 1
```

- `V_début,i` : capital brut juste avant le flux `F_i`.
- `F_i` : flux externe au début de la sous-période (apport +, retrait −).
- `V_fin,i` : capital brut juste avant le flux suivant.

Annualisé si la période dépasse un an : `(1 + TWRR)^(365 / jours) − 1`.

Il faut une valorisation du portefeuille **à chaque date de flux**, donc un historique de cours
(Q-14).

---

## 5. Coûts

### Frais explicites
Frais facturés et affichés par Trade Republic (libellé « Gebühr »), ex. 1 € par ordre ponctuel.
Les plans d'épargne affichent « Kostenlos » (gratuit).

### Impôts et taxes
Montants prélevés au titre de la fiscalité (libellés « Steuer », « Steuern ») : taxe sur les
transactions financières à l'achat de certaines actions, retenues sur dividendes, prélèvements sur
intérêts. *Classement frais ou impôts : Q-08.*

### Frais implicites
Coûts non affichés comme frais :
- **Écart de prix (spread)** : différence entre le prix payé et le prix de marché. Notable sur la
  crypto. Des frais « Kostenlos » **ne signifient pas** coût nul.
- **Frais courants des fonds (TER)** : prélevés dans la valeur des ETF, jamais visibles dans les
  transactions.

Non mesurables dans les données pytr. Affichage à trancher : Q-13.

### Coût annuel estimé d'un actif
```
Coût annuel estimé = valeur détenue × TER annuel
```
Nécessite une source de TER. Hors données pytr.

---

## 6. Données

### Événement
Une entrée de `all_events.json`. Voir [inventaire-donnees.md](inventaire-donnees.md).

### Type d'événement
Valeur du champ `eventType`. Il peut être `null`.

### Type inconnu
Type absent de la liste des types traités et de la liste des types écartés. L'application doit
**l'afficher**, jamais l'ignorer ni le ranger par défaut.

### Déduction
Information absente des champs structurés, reconstituée par une règle. Elle doit être isolée dans
le code, documentée ici ou dans l'inventaire, et **signalée dans l'interface**.

### Fragilité
Dépendance à un texte affiché (libellé en langue de l'application, montant formaté). Elle peut
casser si Trade Republic change un mot ou si l'utilisateur change de langue.
