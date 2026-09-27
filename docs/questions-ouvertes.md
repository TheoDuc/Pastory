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
  cette application. **Deux pièges connus**, rencontrés en écrivant le diagnostic : `login()` a
  pour défaut `waf_token="playwright"`, qui réclame un navigateur — il faut `"default"` avec
  `v2=True` ; et `login()` journalise le JSON complet du compte en niveau *debug*, qu'il faut
  filtrer. Les deux sont détaillés dans
  [prompt-session-suivante.md](prompt-session-suivante.md).
- (c) **Le signaler en amont**, à pytr, et attendre que l'outil sache demander tous les
  comptes-titres. Gratuit pour nous, sans garantie de délai.

**Recommandation :** (a) pour l'instant, puis (c). Le rapprochement du PEA est un confort, pas un
préalable : les chiffres du PEA sont justes, ils sont seulement non confirmés par une seconde
source. À reprendre si le diagnostic montre que le second compte est facile à atteindre.

### Q-21 · Comment présenter les frais et les taxes ?
*Le découpage en trois niveaux plaît au propriétaire (2026-09-17). Correction apportée : le
spread est un coût d'entrée et de sortie, pas un coût courant.*

> **Partiellement répondue à l'étape 6 (2026-09-27).** Les **calculs** des trois niveaux existent
> et s'affichent dans `dashboard positions` : coûts payés avec leur poids, coûts estimés (spread
> et TER), et valeur réelle dans un bloc à part — la recommandation (a). Ce qui reste ouvert est
> la **présentation à l'écran** de l'interface, à reprendre à l'étape 8 avec les prototypes.

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
| Q-22 Diversification | Sources gratuites et fiables, à rechercher. **Close par le lot 6** (2026-09-27) : extraETF, les 11 secteurs Morningstar, les pays par code ISO | D-28, D-63 |
| Q-23 Frais dans les rendements | **Non** : performance sur montants bruts, frais et taxes à part (recommandation écartée) | D-21 |
| Q-24 Gain total | Trois chiffres clés : gain en €, TRI, TWRR ; synthèse brute + vue « valeur réelle » | D-22, D-23 |
| Q-25 Dividendes | **Bruts** dans la performance ; la retenue va dans les coûts | D-29 |

### Lot 3 (2026-09-26) — les cours de marché
Posées après le [comparatif des sources de cours](sources-de-cours.md), tranchées le même jour.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-27 Place de cotation de référence | a | **Marché principal en euros** (Xetra, Euronext Paris…). Devise attendue déclarée par actif, et un cours dans une autre devise est refusé et signalé. Écart de quelques centimes avec l'application Trade Republic assumé et affiché | D-48 |
| Q-28 Interface tierce interdite par les conditions générales | a | **pytr reste l'unique porte d'entrée**, en connaissance de la clause, et **aucun cours** ne passe par Trade Republic. Lecture seule, connexion à l'initiative de l'utilisateur | D-49 |
| Q-29 Durée de vie d'un cours en cache | a | **Définitif** : un cours écrit n'est jamais redemandé. Une commande explicite vide le cache d'un actif (corrections de la source, *splits*) | D-50 |

### Lot 4 (2026-09-27) — la valorisation et les rendements
Posées dans le plan de l'étape 5, tranchées avec lui.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-30 Valoriser « aujourd'hui » | a | **La dernière clôture connue, datée** dans le rapport. Aucun prix de séance en cours, rien hors du cache. Le prix courant est à reconsidérer pour l'interface (étape 9) | D-52 |
| Q-31 Un actif sans cours dans les totaux | a | **Totaux sur les actifs valorisés seulement, marqués partiels**, avec la liste de ce qui manque. Jamais un zéro, jamais un total muet pour un seul ticker manquant | D-53 |

Ce que le pivot avait déjà tranché, et que l'étape a seulement aligné dans le glossaire : la
distribution de capital est un **flux positif** dans le gain, le TRI et le TWRR
([format-pivot §3](format-pivot.md), [D-54](decisions.md)).

### Lot 5 (2026-09-27) — les frais, les taxes et la valeur réelle
Posées dans le plan de l'étape 6, après trois recherches
([couts-et-fiscalite.md](couts-et-fiscalite.md)). Le propriétaire a répondu « on part sur tes
recommandations », et, sur la relecture des taux par un tiers : « je ne m'y connais pas, base-toi
sur tes recherches ». Les sept recommandations s'appliquent donc telles quelles, et chacune reste
corrigeable sans toucher au code ([D-58](decisions.md)).

| Question | Retenu | Décision |
|---|---|---|
| Q-32 Comment connaître le type d'un actif ? | **Déclaré** dans `actifs.toml`, proposé par l'assistant. Le champ `instrumentType` de l'export est écarté : il n'existe que sur les ordres | D-55 |
| Q-33 Quels spreads par défaut ? | **Par côté** : ETF 0,05 %, action 0,10 %, crypto 0,50 %, chacun avec sa fourchette dans le fichier ; un actif peut recevoir son propre taux. L'heure de l'ordre n'est pas prise en compte | D-56 |
| Q-34 D'où vient le TER ? | La liste des ETF de **Xetra**, proposée puis **validée**. Les ETF français « PEA » en sont absents : saisie à la main | D-61 |
| Q-35 Quelle base pour l'impôt du CTO ? | Les **plus-values latentes** seulement, compensées, plancher à zéro. Les plus-values déjà réalisées de l'année et les dividendes déjà reçus restent dehors | D-60 |
| Q-36 Comment estimer l'impôt du PEA ? | Le **gain du plan** approché depuis les titres, sur une **date de premier versement déclarée**. Hypothèses affichées | D-59 |
| Q-37 Comment traiter la crypto ? | Prix d'acquisition **hors frais** (lecture prudente), réduction **au prorata des parts** au lieu de la valeur, seuil de 305 € appliqué à la valeur vendue, tout supposé chez Trade Republic. Les trois approximations sont affichées | D-60 |
| Q-38 Qui valide les taux de 2026 ? | **Personne d'autre que les sources officielles** : le propriétaire ne se sent pas compétent et ne fait pas relire. Les taux sont datés et sourcés dans `parametres/fiscalite.toml`, et le principal (31,4 %) a été recoupé sur impots.gouv.fr | D-58 |

**Ce qui reste à la charge du propriétaire, et qui n'est pas une question mais une vérification :**
ouvrir la **liste des prix française** dans son application (le document public refuse les
téléchargements automatiques) pour confirmer les quatre montants retenus — 1 € par ordre à l'achat
comme à la vente, 0 € par exécution de plan, 1 € par ordre crypto. C'est écrit dans le
[cahier de l'étape 6](verification/etape-6.md) §B.7.

### Lot 6 (2026-09-27) — la diversification
Posées après le [comparatif des sources de composition](composition-des-etf.md) — quatorze familles
de sources examinées, onze interrogées réellement — et tranchées le même jour. **Q-22** est close
par ce lot.

Le propriétaire a d'abord répondu à quatre questions de cadrage, avant la recherche : son
portefeuille contient des **ETF d'actions, des ETF obligataires et de la crypto**, la crypto doit
figurer sur une **ligne à part** hors géographie et hors secteur, les pays doivent être **regroupés
en zones**, et la composition doit se mettre à jour **automatiquement**, sans relecture préalable,
avec sa date et sa source toujours affichées.

| Question | Retenu | Décision |
|---|---|---|
| Q-39 Quelle source de composition ? | **extraETF**, par ISIN, en lisant les **répartitions agrégées** et jamais les lignes détenues. Les émetteurs et justETF servent à **vérifier**, pas à compléter. Limite acceptée : API interne non documentée, usage personnel toléré, échec propre si elle ferme | D-63 |
| Q-40 Pour un ETF synthétique : l'indice ou le panier ? | **L'indice suivi** — l'exposition économique réelle — l'actif étant marqué « synthétique » à l'écran | D-64 |
| Q-41 Quelle nomenclature sectorielle ? | Les **11 secteurs Morningstar**, nommés comme tels et **jamais** « GICS ». Aucune source gratuite par ISIN ne donne du GICS, et deux nomenclatures ne s'additionnent pas | D-65 |
| Q-42 Quelle règle de pays ? | Celle de la source (**pays d'activité**) pour un ETF, le **siège social** pour une action en direct. Les deux cohabitent et l'écran le dit : une répartition géographique n'est pas une grandeur unique | D-66 |
| Q-43 Quelles zones ? | Les **zones d'investisseur** (Amérique du Nord, Europe, Japon, Asie-Pacifique développée, émergents), dans un fichier **daté et sourcé**. Le découpage neutre de l'ONU est écarté : il met la Chine et le Japon dans la même case | D-67 |
| Q-44 Les actions en direct et les ETF obligataires ? | Les actions entrent dans **les deux** répartitions, malgré la règle de pays différente, parce que l'achat d'actions à l'unité est courant sur cette banque. Les ETF obligataires comptent dans une **troisième** répartition, par classe d'actifs, et restent hors des deux autres | D-62, D-68 |
| Q-45 Un actif dont on ne voit pas l'intérieur ? | Affiché **« non couvert »** avec son montant, la répartition étant marquée partielle. Jamais estimé, jamais masqué, jamais renormalisé. Le cas est réel : BNP Paribas Easy, deuxième émetteur d'ETF éligibles au PEA, ne publie rien d'exploitable | D-69 |

**Un arbitrage rendu contre la recommandation, et pour une bonne raison.** Il était recommandé de
**ne pas** traiter les actions en direct, le propriétaire n'en détenant aucune. Il a répondu
l'inverse, en expliquant que le projet doit viser **l'utilisateur type de Trade Republic** et non
son propre portefeuille, puisqu'il compte partager l'application. C'est devenu une évolution de cap
([D-62](decisions.md)), plus large que l'étape 7, et elle vaut désormais pour toutes les étapes
suivantes.

**Ce qui reste à la charge du propriétaire :** ouvrir la **fiche de l'émetteur** de deux ou trois de
ses ETF et comparer ses pays et ses secteurs avec ceux qu'affiche l'application. L'écart attendu
n'est **pas nul** — c'est tout l'objet de Q-41 et de Q-42 — et le
[cahier de l'étape 7](verification/etape-7.md) dit quoi regarder.
