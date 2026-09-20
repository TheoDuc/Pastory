# Questions ouvertes

Arbitrages en attente du propriétaire. Une question tranchée est déplacée dans la section
« Tranchées » avec la réponse, et la décision correspondante est ajoutée à
[decisions.md](decisions.md).

Chaque question donne le contexte, les options et une recommandation. **La recommandation n'est
pas une décision.**

---

## En attente

### Q-26 · Faut-il aller chercher le second compte-titres, pour rapprocher le PEA ?
*Ouverte le 2026-09-21, après le premier essai du rapprochement sur de vraies données.*

**Le constat.** `pytr portfolio` ne demande les positions que d'**un seul** compte-titres : le
`securitiesAccountNumber` unique que renvoie `/api/v2/auth/account`. Trade Republic logeant le
PEA dans un second compte-titres, ses positions ne remontent jamais. Le rapprochement fonctionne
donc sur le CTO et la crypto, mais **pas sur le PEA** ([D-47](decisions.md) évite les fausses
alertes que cela produisait).

**Ce qui est perdu :** sur le PEA, on ne peut ni confirmer les quantités, ni détecter des titres
entrés sans événement — la limite connue de [D-15](decisions.md), précisément celle que le
rapprochement devait lever.

**Ce qu'il faut savoir avant de trancher :** le diagnostic
[`scripts/diagnostic_comptes_titres.py`](../scripts/diagnostic_comptes_titres.py) affiche, sans
aucune valeur personnelle, combien de comptes-titres le compte contient. **Plusieurs** confirme
l'explication ; **un seul** l'infirme, et la cause est ailleurs.

**Options :**
- (a) **Laisser en l'état.** Le rapprochement couvre le CTO et la crypto ; le PEA est signalé
  comme non couvert, une fois, sans bruit. Rien à écrire.
- (b) **Écrire notre propre récupération**, compte-titres par compte-titres, en utilisant pytr
  comme bibliothèque. Contrepartie sérieuse : c'est nous qui gérerions alors le dialogue de
  connexion, ce que [D-41](decisions.md) a justement évité pour que le PIN ne transite jamais par
  cette application.
- (c) **Le signaler en amont**, à pytr, et attendre que l'outil sache demander tous les
  comptes-titres. Gratuit pour nous, sans garantie de délai.

**Recommandation :** (a) pour l'instant, puis (c). Le rapprochement du PEA est un confort, pas un
préalable : les chiffres du PEA sont justes, ils sont seulement non confirmés par une seconde
source. À reprendre si le diagnostic montre que le second compte est facile à atteindre.

### Q-21 · Comment présenter les frais et les taxes ?
*Le découpage en trois niveaux plaît au propriétaire (2026-09-17). À reprendre en détail à
l'étape 8. Correction apportée : le spread est un coût d'entrée et de sortie, pas un coût
courant.*

Tu es ouvert aux suggestions. Voici une proposition en **trois niveaux**, qui suit ta séparation
entre le cœur (synthèse) et ce qui se passe à l'entrée et à la sortie.

**1. Coûts d'entrée (à l'achat)**
- Réels, issus des données : frais d'ordre, taxes à l'achat, taxes sur dividendes. Totaux par
  période, poche et actif.
- Estimé : **spread payé à l'achat** (D-17), toujours distingué des coûts réels.
- Poids de chaque coût dans son opération : `frais / montant brut` (ex. 1 € sur 25 € = 4 %). Utile
  pour voir qu'un ordre ponctuel de petite taille coûte cher, et qu'un plan d'épargne gratuit est
  préférable.
- Cumul dans le temps : « depuis le début, tes frais et taxes représentent X € ».

**2. Coûts courants (pendant la détention, estimés, D-17)**
- Frais annuels des ETF (TER) en € par an, par actif.
- Toujours affichés comme estimations, avec leur source.

**3. Coûts de sortie (à la vente)**
- Ventes passées : frais, taxes et spread estimé de chaque vente.
- Vue « valeur réelle » (D-23), si tu vendais tout aujourd'hui : frais de vente estimés + spread de
  vente estimé + impôts estimés selon la poche.
- Résultat : **valeur réelle** = capital brut − coût de sortie.
- Et l'écart « synthèse brute → valeur réelle », décomposé en coûts d'entrée, coûts courants et
  coûts de sortie.

**Options :**
- (a) Un onglet « Frais et taxes » (niveaux 1 et 2) + une vue « Valeur réelle » (niveau 3).
- (b) Un seul onglet regroupant les trois niveaux.
- (c) Autre découpage à ta convenance.

**Recommandation :** (a). La valeur réelle répond à « combien j'ai vraiment ? », qui est une autre
question que « combien ça m'a coûté ? ». Cette question peut rester ouverte jusqu'à l'étape de
conception de l'interface (étape 8), mais les calculs des niveaux 1 et 3 se préparent avant.

---

## Tranchées

### Lot 1 (2026-09-17)
Quand une réponse courte contredisait les explications du propriétaire, les explications ont
prévalu, à sa demande.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-01 Revenus : rendement ou apport ? | a | Rendement pour les revenus **des actifs** (dividendes). Intérêts sur espèces, primes et euro d'activation : **hors périmètre** | D-11, D-14 |
| Q-02 Carte = retrait ? | a | **Hors périmètre** (espèces ignorées) : contradiction résolue | D-11 |
| Q-03 Espèces dans le capital brut ? | a | **Non, espèces exclues** : contradiction résolue | D-11 |
| Q-04 Capital net investi | explication | Montant brut investi, net de frais et taxes, réduit au prorata des ventes | D-12 |
| Q-05 Méthode de prix de revient | a | PMP, mais **hors frais** (cohérent avec Q-04) | D-13 |
| Q-06 Gains relatifs | a | ~~`gain total / capital net investi`~~ → **remplacé** par un gain en € (D-22) | D-22 |
| Q-07 Distribution de capital | b | Réduit le capital net investi | D-14 |
| Q-08 Taxe à l'achat | a | Catégorie « taxes » séparée des frais, **exclue** du capital investi | D-12 |
| Q-09 Achats PEA sans versement | explication | Sans objet : on ne suit plus l'origine de l'argent | D-11 |
| Q-10 PEA transféré chez le tiers | explication | Prix d'achat = cours le jour d'apparition | D-15 |
| Q-11 Trois comptes | explication | PEA ouvert, fermé, rouvert ; l'euro vient de Trade Republic | — |
| Q-12 Poche crypto | a | Code `XF`, déduit et corrigeable | D-16 |
| Q-13 Frais implicites | explication | Estimation : TER depuis une base d'actifs, spread par défaut par type | D-17 |
| Q-14 Cours de marché | explication | Outil Python gratuit, après comparatif | D-18 |
| Q-15 Langues | a | Allemand + français, extensible | D-19 |
| Q-16 Appariement ambigu | — | Sans objet | D-11 |

### Lot 2 (2026-09-17)

| Question | Retenu | Décision |
|---|---|---|
| Q-17 OneDrive | Le projet reste dans OneDrive | D-24 |
| Q-18 PIN | PIN retiré de la ligne de commande ; trois modes de stockage au choix, jamais en clair ; vérifier d'abord ce que stocke pytr ; à l'étape 10 | D-25 |
| Q-19 Hors périmètre | Euro seul, lecture seule, pas de conseil ni de déclaration ; autres banques non prises en charge mais possibles via un format pivot et des adaptateurs | D-26 |
| Q-20 Monte-Carlo | Fonctionnalité indépendante, reportée | D-27 |
| Q-22 Diversification | Sources gratuites et fiables, à rechercher | D-28 |
| Q-23 Frais dans les rendements | **Non** : performance sur montants bruts, frais et taxes à part (recommandation écartée) | D-21 |
| Q-24 Gain total | Trois chiffres clés : gain en €, TRI, TWRR ; synthèse brute + vue « valeur réelle » | D-22, D-23 |
| Q-25 Dividendes | **Bruts** dans la performance ; la retenue va dans les coûts | D-29 |
