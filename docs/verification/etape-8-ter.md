# Cahier de vérification — étape 8 ter : l'export officiel de Trade Republic

Ce que l'étape a changé, et comment le vérifier **toi-même**. Comme les autres cahiers : des cas
refaisables à la main d'abord, des contrôles sur tes vraies données ensuite.

**Ce qui a changé, en trois phrases.** Les opérations viennent maintenant de l'**export des
transactions** que Trade Republic fournit dans son application, et plus de pytr
([D-79](../decisions.md), [D-81](../decisions.md)). Tu le télécharges, tu le déposes dans le
dossier `exports` de Pastory, et c'est tout : plus de connexion, plus de PIN, plus de comptes à
nommer. Le moteur, lui, n'a pas changé d'une ligne de calcul.

Toutes les valeurs de ce cahier sont **fictives**.

---

## 1. Où trouver l'export, et où le mettre

1. Dans l'application Trade Republic : **Profil → Relevés → Export des transactions**.
2. Choisis **toutes les transactions**, puis *Créer*. Tu reçois `Exportation de transactions.csv`.
3. `uv run pastory emplacements` te dit où est le dossier `exports`. Dépose le fichier dedans.

Tu peux y laisser plusieurs exports, même s'ils se recouvrent : une opération présente dans deux
fichiers n'est comptée qu'une fois (son identifiant, `transaction_id`, est le même).

---

## 2. Les cas que tu peux refaire à la main

Pour chacun : la ligne telle qu'elle est dans le fichier (ouvre-le dans un tableur), puis ce que
Pastory en fait. Le principe est toujours le même : **les montants sont des colonnes**, plus des
textes allemands à décoder.

### 2.1 Un achat en PEA, avec frais et taxe

| Colonne | Valeur |
|---|---|
| `account_type` | `PEA` |
| `type` | `BUY` |
| `shares` | `10` |
| `price` | `20.00` |
| `amount` | `-200.00` |
| `fee` | `-1.00` |
| `tax` | `-0.60` |

- **Le brut** se lit directement : `amount` = 200,00 €. Vérifie : 10 × 20,00 = 200,00. Pastory
  fait ce contrôle sur chaque achat et chaque vente, et signale tout écart de plus d'un centime.
- **Les frais et la taxe sont à côté**, en négatif : 1,00 € et 0,60 €. Ton compte a été débité de
  201,60 €, mais **aucune colonne ne le dit** : Pastory ne le recalcule pas ([D-83](../decisions.md)).
- **Le capital investi** augmente de **200,00 €**, pas de 201,60 : les 1,60 € vont dans les coûts
  ([D-12](../decisions.md), [D-21](../decisions.md)). C'est inchangé depuis l'étape 3.
- **La poche** vient de `account_type` : `PEA`. Elle n'est plus déduite d'un compte.

### 2.2 Un ordre exécuté en deux fois

Un ordre de 4 actions peut être exécuté en deux morceaux. L'export donne alors **deux lignes**,
à quelques secondes d'écart, au même prix :

| `datetime` | `shares` | `price` | `amount` | `fee` |
|---|---|---|---|---|
| 14:30:00 | `2` | `50.00` | `-100.00` | `-1.00` |
| 14:30:01 | `2` | `50.00` | `-100.00` | *(vide)* |

Pastory en fait **deux achats**. Additionne : 4 actions, 200,00 € bruts, 1,00 € de frais — ce que
pytr donnait en une seule ligne. Le prix de revient est le même.

### 2.3 Une vente

| `type` | `shares` | `price` | `amount` | `fee` |
|---|---|---|---|---|
| `SELL` | `-1` | `80.00` | `80.00` | `-1.00` |

La quantité est **négative** dans l'export, parce que des parts sortent. Pastory écrit 1 part
vendue, 80,00 € bruts, 1,00 € de frais : dans le format pivot, le sens est porté par le type,
jamais par un signe.

### 2.4 Un dividende français ou américain

| `category` | `type` | `shares` | `amount` | `tax` |
|---|---|---|---|---|
| `CASH` | `DIVIDEND` | `4` | `10.00` | `-4.50` |

- Le dividende est rangé par la banque dans les **espèces** (`CASH`), mais il porte l'actif : Pastory
  le traite.
- **Brut 10,00 €, retenue 4,50 €, net 5,50 €.** Le net est ce qui arrive sur ton compte.

### 2.5 Un dividende néerlandais — la limite à connaître ⚠️

Un dividende néerlandais de **10,00 € bruts** arrive ainsi :

| `amount` | `tax` |
|---|---|
| `8.50` | `-2.55` |

La banque a **déjà retiré** la retenue des Pays-Bas (15 %, soit 1,50 €) avant d'écrire `amount`,
et **elle ne l'écrit nulle part**. `tax` ne contient que l'impôt français. Le net, lui, est juste :
8,50 − 2,55 = 5,95 €, ce que tu as reçu.

Pastory prend `amount` pour le brut ([D-84](../decisions.md)), comme tous les logiciels qui lisent
ce fichier. Conséquence : sur ce dividende, **le gain est sous-estimé de 1,50 €**, et les taxes
payées aussi. Le rapport de lecture le rappelle dès qu'il y a un dividende.

*Comment on l'a su :* sur l'export de ton ami, comparé ligne à ligne à son export pytr, les
5 dividendes néerlandais avaient le même net, mais un brut d'environ 85 % — exactement la retenue
des Pays-Bas. Pour les 10 autres, tout concordait.

### 2.6 Un dividende en dollars

| `amount` | `original_amount` | `original_currency` | `fx_rate` |
|---|---|---|---|
| `10.80` | `12.00` | `USD` | `0.90` |

`fx_rate` est le nombre d'euros pour un dollar : 12,00 $ × 0,90 = **10,80 €**. Pastory refait cette
multiplication sur chaque dividende en devise, et signale un écart de plus d'un centime.

### 2.7 Une ligne qui ne ressemble à rien de connu

Un dividende **négatif** (`amount = -10.00`) existe chez d'autres utilisateurs : c'est l'annulation
d'un dividende, avant sa correction — l'original, son annulation, puis le nouveau. On n'en a jamais
vu sur vos fichiers. Pastory ne l'interprète pas, et le rapport dit **« annulation non
interprétée »** : l'original reste compté, donc les dividendes de cet actif sont sans doute
**surestimés**. Compare-les à l'application.

Une obligation, un compte enfant (`JUNIOR`), une devise autre que l'euro donnent de même
« forme jamais vue », avec le fichier et la ligne : **aucune opération** n'est produite.

C'est un trou affiché plutôt qu'un chiffre deviné. Si tu en vois un, c'est le signal qu'il faut
regarder ensemble cette ligne-là.

---

## 3. Ce que dit le rapport de lecture

`uv run pastory lire` affiche, dans l'ordre :

| Bloc | Ce qu'il faut y regarder |
|---|---|
| **Exports lus** | La **période couverte**. Le premier jour doit être celui de ta première opération : sinon l'export ne remonte pas assez loin, et il manque des achats. Un **trou** entre deux fichiers est signalé |
| **Lecture de N lignes** | Combien de lignes sont traitées, laissées de côté (espèces), non traitées |
| **ATTENTION - types non traités** | Chaque type que Pastory ne sait pas encore traiter, et ce qu'on en sait. **Ces lignes ne comptent dans aucun chiffre** |
| **Espèces, comptées et laissées de côté** | Les paiements et virements, **comptés par type seulement** : aucun montant, aucun commerçant, aucun IBAN n'est lu |
| **Opérations produites** | Par type et par poche |
| **Limite connue : le brut des dividendes** | Le rappel du §2.5 |
| **Contrôles de cohérence en échec** | Doit être vide |

---

## 4. La preuve par comparaison : pytr et l'export officiel donnent-ils la même chose ?

Avant de retirer pytr, les deux adaptateurs ont tourné sur la **même période**, sur tes données et
sur celles de ton ami. Le script de comparaison regroupait les opérations par jour, actif et type,
et comparait les sommes. Il n'affichait que des comptages ; il a été retiré avec pytr, et reste
dans l'historique git.

**Sur l'export de ton ami** (environ un an de période commune) :

| Ce qui est comparé | Résultat |
|---|---|
| Achats : quantité, brut, frais, taxes | identiques sur 52 groupes sur 52 ; 3 de ces groupes sont des ordres exécutés en deux fois (§2.2) |
| Ventes | identiques, 2 sur 2 |
| Dividendes : net | identique, 15 sur 15 |
| Dividendes : brut et taxe | identiques sur 10 ; les **5** autres sont néerlandais (§2.5) |
| Distribution de capital | identique, 1 sur 1 — l'export donne en plus le nombre de parts, que pytr ne lisait pas |
| Une opération d'un seul côté | 1 achat, que pytr n'avait pas su rattacher à un compte. L'export, lui, le lit |

**Sur ton export** (16 jours de période commune) : 5 achats identiques en tout point, poche
comprise. Le sixième, ta **crypto**, a la même quantité, les mêmes frais et la même poche, mais un
brut de **quelques centimes de moins** : pytr donnait le montant rond débité, l'export donne
`quantité × prix` ([export-officiel.md §5.2](../export-officiel.md)).

---

## 5. Sur tes vraies données

### 5.1 Ce qui a été fait pour toi

Une **photo « avant »** de tes positions a été prise avec l'ancien code, et une photo « après »
avec le nouveau. Elles sont dans `docs/verification/etape-8-ter-avant.local.md` et
`etape-8-ter-apres.local.md`, sur ta machine, hors de git.

Résultat : **toutes tes positions sont identiques**, à deux différences près, toutes deux
attendues :

- **le capital investi de ta crypto** baisse de quelques centimes (§4) ;
- **ta crypto n'est plus valorisée.** pytr l'appelait par un code interne (`XF…`), l'export par son
  code de marché (fictif : `BTC`). Ta déclaration de ticker, rangée sous l'ancien code, ne la
  retrouve plus. Elle apparaît comme « non valorisée », et les totaux sont marqués partiels.
  L'étape 8 quater proposera le ticker toute seule à partir de ce code.

### 5.2 Les contrôles à faire

1. **Le dossier.** Ta configuration est encore dans l'ancien dossier, au nom de « DashBoard Trade
   Republic » : `uv run pastory emplacements` te le dit. Déplace son contenu dans le dossier
   `Pastory` qu'il indique, puis dépose ton export dans `exports`.
2. **`uv run pastory lire`** : la période doit commencer à ta première opération, et le seul type
   non traité doit être ton Saveback (§6).
3. **`uv run pastory positions`**, puis **compare chaque quantité à l'écran de l'application
   Trade Republic**, actif par actif. C'est désormais le contrôle le plus sûr, et le seul qui
   puisse révéler des titres entrés sans aucune ligne dans l'export ([D-81](../decisions.md)).
4. **Le capital investi**, actif par actif, en face de la photo « avant » : seul celui de ta crypto
   doit avoir bougé, de quelques centimes.

**Vérifié par le propriétaire le 2026-10-05 :** les quantités de chaque actif sont identiques à
celles de l'application Trade Republic.

### 5.3 Ce que je ne peux pas vérifier à ta place

- **Ton Saveback.** C'était la dernière ligne de ton export : on ne sait pas encore où vont les
  parts. D'après d'autres utilisateurs, elles arrivent par un achat séparé, un jour ou deux plus
  tard. **Ton prochain export le dira** : s'il contient un achat du même fonds et du même
  montant, le Saveback n'est qu'un crédit d'espèces.
- **Q-54**, chez ton ami : des actions gratuites reçues, puis retirées un mois plus tard par une
  « migration ». Demande-lui ce que l'application montre pour cette action à ces deux dates.

---

## 6. Ce que cette étape ne fait pas

- **Les titres reçus sans achat ne sont pas encore traités** — actions gratuites, action offerte
  ([Q-54](../questions-ouvertes.md)). Ils sont affichés, et leurs parts manquent aux chiffres tant
  qu'ils le restent.
- **Le Saveback** n'est pas traité (§5.3).
- **Le ticker de ta crypto** n'est pas encore proposé tout seul : c'est l'étape 8 quater, comme le
  type de chaque actif, qui vient désormais de l'export ([D-82](../decisions.md)) mais n'est pas
  encore appliqué aux estimations.
- **Plus aucun rapprochement automatique** avec les quantités de la banque : c'est ton contrôle à
  l'écran (§5.2).
