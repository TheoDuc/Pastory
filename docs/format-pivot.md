# Format pivot

Le **format pivot** est le contrat entre les deux moitiés de l'application
([D-26](decisions.md)) :

```
 Export d'une banque  ──►  Adaptateur  ──►  FORMAT PIVOT  ──►  Moteur  ──►  Vues
    (Trade Republic)      (1 par banque)     (ce document)     (calculs)
```

- L'**adaptateur** est le seul à connaître Trade Republic. Il traduit les événements en lignes de
  ce format.
- Le **moteur** ne lit que ce format. Il ne sait pas d'où viennent les données. Changer de banque,
  c'est écrire un nouvel adaptateur, rien d'autre.

Ce document est écrit **avant** le code. Toutes les valeurs qu'il contient sont **fictives**
([D-03](decisions.md)).

---

## 1. Ce qu'est une ligne

**Une ligne = une opération sur un actif.** Un achat d'ETF, une vente d'action, un dividende versé.

Ce qui n'est **pas** une ligne :

- tout ce qui ne concerne que l'argent liquide — virement reçu, paiement carte, versement vers le
  PEA, intérêts sur espèces, prime : les espèces sont hors périmètre ([D-11](decisions.md)) ;
- les événements d'information (documents, messages du support, annonces) ;
- un plan d'épargne qui a échoué : rien n'a bougé.

Ce qui devient une ligne alors qu'aucun argent ne bouge : les **titres reçus sans achat** (action
gagnée, actions gratuites, titres transférés). Des parts entrent dans le portefeuille, donc il se
passe quelque chose ([D-15](decisions.md)).

### Trois règles de forme

1. **Tous les nombres sont positifs.** Le sens de l'opération est porté par son `type`, jamais par
   un signe moins. Un achat et une vente se lisent pareil ; c'est le type qui dit ce que le moteur
   en fait.
2. **Les montants sont exacts au centime.** Ils ne sont jamais approchés par un nombre à virgule
   flottante ([D-33](decisions.md)).
3. **Aucun numéro de compte n'entre dans le pivot.** Le compte sert à l'adaptateur pour déduire la
   poche, puis il est oublié.

---

## 2. Les champs

| Champ | Contenu | Toujours présent ? |
|---|---|---|
| `identifiant` | Identifiant de la ligne, stable d'un chargement à l'autre | oui |
| `instant_utc` | Date et heure exactes de l'opération, en temps universel | oui |
| `date` | Date du jour correspondant, **heure de Paris**. C'est elle qui sert à tout regroupement par jour et au rapprochement avec les cours ([D-36](decisions.md)) | oui |
| `type` | `achat`, `vente`, `dividende`, `distribution_capital`, `titres_recus` | oui |
| `nature_source` | Nature d'origine de l'opération : `plan_epargne`, `ordre_ponctuel`, `action_gagnee`, `actions_gratuites`, `transfert_entrant`, `dividende_especes`, `distribution_capital`. **Informatif** : sert à l'affichage et au diagnostic, le moteur ne calcule jamais dessus | oui |
| `actif` | Identifiant de l'actif : ISIN, ou code interne pour la crypto | oui |
| `nom_actif` | Nom lisible de l'actif. **Affichage seulement**, jamais un calcul (règle 4 de CLAUDE.md) | non |
| `poche` | `PEA`, `CTO` ou `crypto` | oui |
| `quantite` | Nombre de parts concernées. Peut avoir des décimales (parts fractionnées, crypto) | voir §3 |
| `prix_unitaire` | Prix d'une part, ou dividende par action | voir §3 |
| `montant_brut` | **La base de toute la performance** ([D-21](decisions.md), [D-29](decisions.md)) : quantité × prix, ou dividende brut | voir §3 |
| `frais` | Frais réellement facturés sur cette opération. `0` si aucun. **N'entre jamais dans la performance** | oui |
| `taxes` | Taxes réellement prélevées sur cette opération. `0` si aucune. **N'entre jamais dans la performance** | oui |
| `montant_regle` | Montant réellement débité ou crédité, tel que la banque le donne. Sert au contrôle du §5 | oui |
| `devise` | `EUR` uniquement pour l'instant ([D-26](decisions.md)) | oui |
| `reference_source` | Identifiant de l'événement d'origine, pour remonter à la donnée brute | oui |
| `provenance` | Pour chaque champ rempli : d'où vient sa valeur (§4) | oui |

Ce que le format **ne contient pas**, volontairement :

| Absent | Pourquoi |
|---|---|
| Numéro de compte, nom, IBAN | Données personnelles ; inutiles au calcul (§1) |
| Solde d'espèces, virements, versements PEA | Hors périmètre ([D-11](decisions.md)) |
| Cours de marché, TER, spread, impôt estimé | Ce sont des données externes, ajoutées plus tard par le moteur. Le pivot ne décrit que ce qui s'est **réellement passé** |
| Capital investi, PRU, plus-value | Ce sont des **résultats**, calculés par le moteur à partir de ces lignes |
| Les anomalies de lecture | Elles vont dans le **rapport de lecture**, aux côtés des types inconnus, pas dans la ligne |

---

## 3. Les cinq types et ce qu'ils font

C'est le tableau à relire en premier : il dit, pour chaque type, ce que le moteur en fait.

| Type | Quantité détenue | Capital net investi | Compté comme flux (TRI, TWRR) |
|---|---|---|---|
| `achat` | **augmente** de `quantite` | **+ `montant_brut`** | argent qui entre dans l'actif |
| `vente` | **diminue** de `quantite` | **réduit au prorata** des parts vendues | argent qui sort de l'actif |
| `dividende` | **inchangée** | **inchangé** | argent qui sort de l'actif (montant **brut**, [D-29](decisions.md)) |
| `distribution_capital` | **inchangée** | **− `montant_brut`** ([D-14](decisions.md)) | argent qui sort de l'actif |
| `titres_recus` | **augmente** de `quantite` | **+ `montant_brut`**, qui est une **déduction** ([D-15](decisions.md)) | argent qui entre dans l'actif |

Les définitions correspondantes sont dans le [glossaire](glossaire.md) : capital net investi §3,
gain et rendements §4 et §5.

**Champs attendus selon le type :**

| Type | `quantite` | `prix_unitaire` | `montant_brut` | `montant_regle` |
|---|---|---|---|---|
| `achat` | parts achetées | prix d'exécution | quantité × prix | montant payé (frais et taxes compris) |
| `vente` | parts vendues | prix d'exécution | quantité × prix | montant reçu (frais et taxes déduits) |
| `dividende` | parts détenues au moment du versement *(informatif)* | dividende par action *(informatif)* | **dividende brut** | montant net reçu |
| `distribution_capital` | parts détenues *(informatif)* | montant par action *(informatif)* | montant brut distribué | montant net reçu |
| `titres_recus` | parts reçues | cours du jour d'apparition (**déduit**) | quantité × ce cours (**déduit**) | `0` : rien n'a été payé |

Pour un `dividende` et une `distribution_capital`, `quantite` est la quantité **déjà détenue**.
Elle est là pour vérifier (dividende par action × parts = brut), **elle n'ajoute aucune part**.
Elle peut être absente si la donnée n'est pas lisible : le reste du calcul n'en dépend pas.

---

## 4. La provenance : chaque valeur dit d'où elle vient

C'est ce qui permet de distinguer un chiffre certain d'un chiffre reconstitué. Chaque champ rempli
porte l'une de ces cinq origines :

| Provenance | Sens | Exemple |
|---|---|---|
| `donnee` | Champ structuré de l'export : solide | le montant réglé, la date, l'ISIN |
| `texte` | **Lu dans un texte affiché**, dans la langue de l'application : fragile | la quantité, le prix, les frais, les taxes ([D-09](decisions.md), [D-19](decisions.md)) |
| `deduction` | Reconstitué par une règle écrite | la poche d'un plan d'épargne, le prix de titres reçus ([D-15](decisions.md), [D-16](decisions.md)) |
| `estimation` | Valeur approchée, jamais issue des données | *(aucune dans le pivot ; réservé au moteur : spread, TER, impôt)* |
| `a_completer` | Valeur manquante, en attente d'une donnée externe | le prix de titres reçus, tant que les cours ne sont pas disponibles (étape 4) |

L'interface doit rendre visibles les `deduction` et les `a_completer`
([architecture-notes §4](architecture-notes.md)). Une ligne dont un champ est `a_completer` est
affichée, mais son montant brut ne compte dans aucun total tant qu'il n'est pas complété.

---

## 5. Les contrôles de cohérence

Appliqués à **chaque ligne**, dès sa création. Ils servent à attraper une lecture de texte
douteuse, plutôt que de laisser un chiffre faux se propager en silence.

| Contrôle | Règle | Types concernés |
|---|---|---|
| Jour | `date` = le jour de `instant_utc` en heure de Paris | tous |
| Montant brut présent | `montant_brut` renseigné, **ou** marqué `a_completer` | tous |
| Montant brut juste | `montant_brut = quantite × prix_unitaire`, à la tolérance ci-dessous | `achat`, `vente`, et `dividende` / `distribution_capital` **si** quantité et prix sont lisibles |
| Achat | `montant_regle = montant_brut + frais + taxes`, à 1 centime près | `achat` |
| Encaissement | `montant_regle = montant_brut − frais − taxes`, à 1 centime près | `vente`, `dividende`, `distribution_capital` |
| Titres reçus | `montant_regle = 0`, `frais = 0`, `taxes = 0` | `titres_recus` |
| Signes | aucun nombre négatif | tous |
| Quantité | strictement positive | `achat`, `vente`, `titres_recus` |
| Provenance | toute valeur renseignée dit d'où elle vient ; une valeur `a_completer` est bien vide | tous |
| Devise | `EUR` | tous |

**Pourquoi le montant brut doit exister.** C'est la base de tous les calculs de performance
([D-21](decisions.md)). S'il manquait sans que personne ne le dise, l'opération disparaîtrait de
tous les totaux en silence — exactement ce que le projet cherche à éviter. Un prix illisible est
donc marqué `a_completer`, jamais laissé vide sans explication.

**La tolérance sur « quantité × prix »** ([D-39](decisions.md)). Elle vaut :

```
1 centime                                       arrondi du montant par la banque
+ quantité × (½ dernier chiffre du prix)        le prix affiché est arrondi
+ prix × (½ dernier chiffre de la quantité)     la quantité affichée l'est aussi
```

Les deux derniers termes sont **symétriques**, et il faut les deux. Le nombre de décimales n'est
jamais supposé : il est **lu sur la valeur elle-même**, qui garde l'écriture exacte du libellé
dont elle vient. Une valeur écrite **sans décimale** est tenue pour exacte — Trade Republic écrit
les fractions de part avec des décimales, donc « 200 » veut dire deux cents parts, pas « entre
199,5 et 200,5 ».

| Cas | Calcul | Tolérance |
|---|---|---|
| 2 parts à 25,00 € | 0,01 + 2 × 0,005 + 25,00 × 0 | **0,02 €** |
| 200 parts à 0,33 € | 0,01 + 200 × 0,005 + 0,33 × 0 | **1,01 €** |
| 0,000833 part à 30 000,00 € | 0,01 + 0,000833 × 0,005 + 30 000 × 0,0000005 | **0,03 €** |

- **Deuxième ligne :** un dividende de 0,335 € par action sur 200 parts est affiché « 0,33 € ».
  Le calcul donne 66,00 € alors que 67,00 € ont été versés : ce n'est pas une erreur de lecture,
  et une tolérance fixe d'un centime l'aurait signalé à tort tous les trimestres.
- **Troisième ligne :** un achat de crypto. La quantité est écrite avec six décimales et le prix
  vaut des dizaines de milliers d'euros ; la moitié du dernier chiffre de la quantité pèse alors
  un centime et demi. Sans le troisième terme, **chaque achat de crypto serait signalé à tort**.

**Un écart plus grand n'est jamais corrigé en silence** : la ligne est conservée telle quelle et
l'anomalie apparaît dans le rapport de lecture, avec l'identifiant de l'événement d'origine.

Un contrôle dont un ingrédient est `a_completer` n'est pas exécuté : il est mis en attente.

---

## 6. Exemples fictifs

Un par type, plus un second achat pour montrer des frais et une taxe. Ces six exemples sont
**repris tels quels dans les tests** (`tests/pivot/exemples.py`) : si ce document et le code
divergent un jour, les tests le diront.

### Achat — plan d'épargne mensuel, sans frais

| Champ | Valeur | Provenance |
|---|---|---|
| `instant_utc` | 2026-01-02 08:00:00 | `donnee` |
| `date` | 2026-01-02 | `donnee` |
| `type` | `achat` | `donnee` |
| `nature_source` | `plan_epargne` | `donnee` |
| `actif` | XX0000000001 | `donnee` |
| `nom_actif` | ETF Exemple Monde (Acc) | `donnee` |
| `poche` | `CTO` | `deduction` *(compte de l'achat)* |
| `quantite` | 2 | `texte` |
| `prix_unitaire` | 25,00 € | `texte` |
| `montant_brut` | 50,00 € | `texte` |
| `frais` | 0,00 € | `texte` *(« Kostenlos »)* |
| `taxes` | 0,00 € | `donnee` |
| `montant_regle` | 50,00 € | `donnee` |

Contrôles : 2 × 25,00 = 50,00 ✔ · 50,00 + 0 + 0 = 50,00 ✔

### Achat — ordre ponctuel dans le PEA, avec frais et taxe

| Champ | Valeur | Provenance |
|---|---|---|
| `date` | 2026-02-10 | `donnee` |
| `type` | `achat` · `nature_source` `ordre_ponctuel` | `donnee` |
| `actif` | XX0000000002 — Action Exemple SA | `donnee` |
| `poche` | `PEA` | `deduction` *(compte de l'achat)* |
| `quantite` | 10 | `texte` |
| `prix_unitaire` | 20,00 € | `texte` |
| `montant_brut` | **200,00 €** | `texte` |
| `frais` | 1,00 € | `texte` |
| `taxes` | 0,60 € | `texte` |
| `montant_regle` | 201,60 € | `donnee` |

Contrôles : 10 × 20,00 = 200,00 ✔ · 200,00 + 1,00 + 0,60 = 201,60 ✔
Le capital net investi augmente de **200,00 €**, pas de 201,60 € ([D-12](decisions.md)). Les
1,60 € sont suivis à part, dans les coûts ([D-21](decisions.md)).

### Vente — vente partielle

| Champ | Valeur | Provenance |
|---|---|---|
| `date` | 2026-06-15 | `donnee` |
| `type` | `vente` · `nature_source` `ordre_ponctuel` | `donnee` |
| `actif` | XX0000000002 — Action Exemple SA | `donnee` |
| `poche` | `PEA` | `deduction` |
| `quantite` | 5 | `texte` |
| `prix_unitaire` | 40,00 € | `texte` |
| `montant_brut` | 200,00 € | `texte` |
| `frais` | 1,00 € | `texte` |
| `taxes` | 0,00 € | `donnee` |
| `montant_regle` | 199,00 € | `donnee` |

Contrôles : 5 × 40,00 = 200,00 ✔ · 200,00 − 1,00 − 0,00 = 199,00 ✔
Le moteur retire au capital net investi la **part vendue** (5 parts sur 10 détenues, soit la
moitié), pas les 200 € encaissés.

### Dividende

| Champ | Valeur | Provenance |
|---|---|---|
| `date` | 2026-04-20 | `donnee` |
| `type` | `dividende` · `nature_source` `dividende_especes` | `donnee` |
| `actif` | XX0000000002 — Action Exemple SA | `donnee` *(lu dans le chemin de l'icône)* |
| `poche` | `PEA` | `deduction` |
| `quantite` | 10 *(parts détenues, informatif)* | `texte` |
| `prix_unitaire` | 0,50 € *(par action, informatif)* | `texte` |
| `montant_brut` | **5,00 €** | `texte` |
| `frais` | 0,00 € | `donnee` |
| `taxes` | 1,50 € | `texte` |
| `montant_regle` | 3,50 € | `donnee` |

Contrôles : 10 × 0,50 = 5,00 ✔ · 5,00 − 0,00 − 1,50 = 3,50 ✔
La performance compte **5,00 €** ([D-29](decisions.md)) ; la retenue de 1,50 € va dans les coûts.
La quantité détenue ne bouge pas.

### Distribution de capital

| Champ | Valeur | Provenance |
|---|---|---|
| `date` | 2026-05-05 | `donnee` |
| `type` | `distribution_capital` | `donnee` |
| `nature_source` | `distribution_capital` | `texte` *(« Kapitalverteilung »)* |
| `actif` | XX0000000003 — Fonds Exemple | `donnee` |
| `poche` | `CTO` | `deduction` |
| `quantite` | 30 *(informatif)* | `texte` |
| `montant_brut` | 12,00 € | `texte` |
| `frais` / `taxes` | 0,00 € | `donnee` |
| `montant_regle` | 12,00 € | `donnee` |

Le capital net investi de cet actif **baisse de 12,00 €** : ce n'est pas un revenu, c'est une part
de la mise qui revient ([D-14](decisions.md)).

### Titres reçus sans achat — actions gratuites, prix pas encore connu

| Champ | Valeur | Provenance |
|---|---|---|
| `date` | 2026-03-01 | `donnee` |
| `type` | `titres_recus` · `nature_source` `actions_gratuites` | `texte` *(« Bonusaktien »)* |
| `actif` | XX0000000004 — Action Exemple B | `donnee` *(icône)* |
| `poche` | `CTO` | `deduction` |
| `quantite` | 3 | `texte` |
| `prix_unitaire` | *(vide)* | **`a_completer`** |
| `montant_brut` | *(vide)* | **`a_completer`** |
| `frais` / `taxes` / `montant_regle` | 0,00 € | `donnee` |

Les 3 parts entrent dans le portefeuille tout de suite. Le prix retenu sera le **cours du jour
d'apparition**, disponible à partir de l'étape 4 ([D-15](decisions.md)). Tant qu'il manque, la
ligne est visible, signalée, et son montant brut ne compte dans aucun total. Une fois complété, le
prix devient une `deduction`, toujours signalée dans l'interface.

---

## 7. Vérifier soi-même

Le pivot peut être exporté en **CSV lisible dans un tableur**, une ligne par opération, colonnes
dans l'ordre du §2, avec une colonne de provenance par champ concerné. C'est le fichier à ouvrir
pour comparer, opération par opération, avec l'application Trade Republic.

Ce fichier contient de vraies données : il est écrit dans le dossier des fichiers personnels et
n'entre jamais dans git ([D-01](decisions.md), [D-37](decisions.md)).

---

## 8. Comment ce format évolue

La liste des types est **fermée**. Un cas qui n'y entre pas — une scission, un échange de titres,
un investissement de l'arrondi — ne doit pas être forcé dans un type existant : il est signalé
comme **inconnu**, présenté à l'utilisateur, et le format n'est étendu que par une nouvelle
décision dans [decisions.md](decisions.md), suivie d'une mise à jour de ce document.

Un adaptateur pour une autre banque n'a rien d'autre à produire que ces lignes — **plus,
facultativement, celles du §9**.

---

## 9. Les positions réelles : la photo, à côté de l'histoire

*Ajouté à l'étape 3 ([D-46](decisions.md)).*

Les opérations racontent **l'histoire** d'un portefeuille. Une position réelle en donne la
**photo**, telle que la banque l'affiche à l'instant où on la lui demande.

Les deux doivent concorder, et c'est le seul moyen de découvrir des titres entrés **sans qu'aucun
événement ne le dise** — la limite connue de [D-15](decisions.md). Un PEA transféré depuis un
autre établissement fait exactement cela : les parts sont là, et rien dans la timeline ne les
explique.

| Champ | Contenu | Rôle |
|---|---|---|
| `actif` | ISIN, ou code interne pour la crypto. **Le même identifiant que dans les opérations** | — |
| `quantite` | Parts détenues | **contrôle** : tout écart avec le moteur est signalé |
| `nom_actif` | Nom lisible | affichage seulement |
| `prix_de_revient_banque` | Prix de revient calculé par la banque | **information seulement** |

**Pourquoi le prix de revient n'est pas un contrôle.** On ignore ce que la banque y met : frais
d'achat compris ou non, quelle méthode de moyenne. Le prix de revient du projet, lui, les exclut
explicitement ([D-13](decisions.md)). Les comparer automatiquement déclencherait une alerte sur
presque chaque actif, à tort. Il est donc affiché à côté du nôtre, étiqueté, et ne déclenche
jamais rien.

**Ce que le rapprochement peut trouver :**

| Cas | Ce que ça veut dire |
|---|---|
| Les deux quantités concordent | rien à faire |
| Elles diffèrent | une opération manque, ou a été mal lue |
| La banque détient, le moteur ignore | **le cas à examiner** : des titres sont entrés sans événement |
| Le moteur compte, la banque ne montre rien | l'actif a été vendu hors de l'export, ou une opération a été comptée deux fois |

Les quantités du moteur sont additionnées **toutes poches confondues** : la banque liste des
ISIN sans dire dans quelle enveloppe ils sont détenus, et un même ETF peut être à la fois en PEA
et en CTO.

Un adaptateur qui ne sait pas produire ces lignes reste un adaptateur valable : le rapprochement
est alors simplement indisponible, et l'application le dit.

**La tolérance sur la quantité** vaut un millionième de part : la banque publie ses quantités
arrondies à six décimales, et deux nombres qui ne diffèrent qu'au-delà décrivent la même
position.
