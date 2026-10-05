# Cahier de vérification — étape 8 quater : des réglages qui se trouvent seuls

Ce que l'étape a changé, et comment le vérifier **toi-même**. Comme les autres cahiers : des cas
refaisables à la main d'abord, des contrôles sur tes vraies données ensuite.

**Ce qui a changé, en trois phrases.** Tu n'as plus rien à déclarer : la cotation de chaque actif,
son type, ses frais courants, son contenu et la date d'ouverture de ton PEA sont **trouvés par
l'application**, contrôlés, et montrés avec leur source ([D-80](../decisions.md), D-85 à D-92).
`actifs.toml` n'est plus qu'un fichier de **corrections**, que l'application ne réécrit jamais.
`uv run pastory actifs` te montre tout ce qui a été trouvé, d'où, et ce qui a été vérifié.

Toutes les valeurs de ce cahier sont **fictives**.

---

## 1. Ce que tu lis dans `pastory actifs`

Pour chaque actif et chaque réglage, trois lignes au plus :

```
  XX0000000001 - ETF Monde Fictif - PEA
    cotation         AAAA.PA, en EUR (Paris, ETF Monde Fictif)
                     trouvé : Yahoo Finance (recherche), au 2026-10-05
                     vérifié : trouvée par son ISIN, cotée en euros avec des cours; sur 4 ordre(s),
                     son cours de clôture s'écarte en médiane de 0,3 % du prix payé (tolérance 4 %)
```

- **trouvé** : la source, et la date que décrit la source ;
- **vérifié** : le contrôle passé avant d'appliquer la valeur ;
- **à savoir** : la limite connue de la source, quand il y en a une ;
- **INTROUVABLE** : rien de fiable, et pourquoi. Rien n'est inventé à la place, et le reste du
  portefeuille s'affiche quand même ;
- **corrigé par vous** : ta correction l'emporte, et si la source disait autre chose, c'est écrit
  dessous (« la source donnait : … »).

En tête, le compte : *N valeurs trouvées seules, M corrigées par vous, K introuvables*. Et
`pastory positions` rappelle en une ligne, au-dessus des chiffres, s'il reste des trous.

---

## 2. Les cas que tu peux refaire à la main

### 2.1 Le contrôle d'une cotation par le prix payé

Tu as acheté un ETF quatre fois. L'export donne le prix payé (colonne `price`), Yahoo donne le
cours de clôture du même jour pour le ticker candidat :

| Jour | Prix payé | Clôture du candidat | Écart |
|---|---|---|---|
| 2 mars | 100,00 | 100,40 | 0,40 % |
| 9 mars | 102,00 | 101,70 | 0,29 % |
| 16 mars | 98,00 | 98,90 | 0,92 % |
| 23 mars | 99,00 | 99,10 | 0,10 % |

L'écart d'un jour, c'est |clôture − prix| ÷ prix : pour le 2 mars, 0,40 ÷ 100,00 = 0,40 %.
L'**écart médian** est la moyenne des deux du milieu une fois rangés : (0,29 + 0,40) ÷ 2 =
**0,345 %**. Quatre ordres → tolérance **4 %** pour un ETF. Le candidat est retenu.

Si le candidat était la cotation de Londres en **pence**, ses clôtures vaudraient environ 8 500 :
écart de plusieurs milliers de pour cent, refusé. Si c'était une autre part du même fonds, à
103,00 en moyenne : écart d'environ 3 %, **dans** la tolérance — c'est pourquoi, quand le candidat
a été trouvé par son **nom**, un second contrôle s'ajoute (§2.2).

| Type | 1 ou 2 ordres | 3 à 5 ordres | 6 ordres ou plus |
|---|---|---|---|
| ETF | 6 % | 4 % | 2 % |
| Action | 12 % | 6 % | 4 % |
| Crypto | 20 % | 10 % | 5 % |

### 2.2 Le contrôle de change

Un ETF irlandais : par son ISIN, la recherche ne trouve que **Londres, en dollars**, à 116,00 $. Par
son nom, elle trouve deux cotations en euros, à Xetra : 100,00 € et 102,00 €. Le jour même, un euro
vaut 1,16 dollar.

- Londres convertie en euros : 116,00 ÷ 1,16 = **100,00 €**.
- Premier candidat : 100,00 ÷ 100,00 = 1,000 → écart **0 %**, retenu.
- Second candidat : 102,00 ÷ 100,00 = 1,020 → écart **2 %**, au-delà de **1 %** : c'est l'autre
  part du fonds (distribuante, par exemple), écartée.

Pastory prend la médiane de ce rapport sur une soixantaine de séances. Pour une cotation en pence
(« GBp »), le cours est d'abord divisé par cent.

### 2.3 La date d'ouverture de ton PEA

Les lignes d'espèces du compte `PEA`, dans l'ordre (seuls le jour et le sens sont lus, jamais le
montant) :

| Jour | `type` | Sens | Ce qu'en tire Pastory |
|---|---|---|---|
| 1ᵉʳ juin | `PEA_MARKETING` | entrée | le plan commence le 1ᵉʳ juin |
| 7 juin | `TRANSFER_OUT` | sortie | moins de 5 ans après : **le plan est clos** |
| 7 juin | `PEA_MARKETING` | entrée | un nouveau plan commence le 7 juin |
| 16 juin | `TRANSFER_IN` | entrée | rien : le plan a déjà commencé |

Date retenue : **le 7 juin**. La règle vient de la loi (un retrait avant cinq ans clôt le PEA) et
de ton propre cas, que tu as confirmé ([D-86](../decisions.md)). Elle est écrite avec sa réserve :
un PEA transféré d'une autre banque, ou des exports qui ne remontent pas à l'ouverture, donnent une
date trop récente.

**Le contrôle** : un achat sur le PEA *avant* le premier crédit du plan — sans qu'un plan clos
puisse l'expliquer — prouverait que le plan est plus ancien que tes exports. La date serait alors
refusée, et l'impôt du PEA non calculé, plutôt que calculé sur une date fausse.

**Un retrait plus tard** : une sortie d'espèces du PEA **après cinq ans** ne clôt pas le plan, mais
l'impôt estimé suppose « aucun retrait passé » ([D-59](../decisions.md)). Pastory remplace alors
cette hypothèse par ce que montrent tes exports : « contredit : de l'argent est sorti du PEA le … »
([D-87](../decisions.md)).

### 2.4 Le contenu d'un fonds

extraETF annonce la classe d'un fonds par un **code et un libellé** : `3` et `Anleihen`
(obligations). Le registre de l'ESMA donne son code CFI, `CEOIBS` : la 5ᵉ lettre, **B**, veut dire
« titres de créance ». Les deux concordent : le fonds compte dans les **obligations**, hors de la
géographie et des secteurs, et l'écran le dit.

| extraETF | CFI | Résultat |
|---|---|---|
| 3 Anleihen | `CEOIBS` (B) | obligations, recoupé |
| 4 Rohstoffe | `CECGMS` (M, muet) | matières premières, « non recoupé » |
| 3 Anleihen | `CEOGES` (E) | **rien** : les deux sources se contredisent, et c'est écrit |
| 5 Geldmarkt | — | **rien** : le monétaire n'est pas encore traduit ([Q-60](../questions-ouvertes.md)) |
| 2 Aktien | `CEOGES` (E) | actions, montré mais **sans effet** : le fonds garde les pays et les secteurs de sa composition |

### 2.5 Les frais courants

Pour un fonds Amundi, c'est **l'émetteur** qui fait foi : « 0,2 % par an, Amundi (fiche produit de
l'émetteur), taux en vigueur depuis le 2025-10-01 ». La date est celle où le taux est entré en
vigueur : un taux de 2023 toujours en vigueur n'est pas périmé. Si la liste de Xetra donne autre
chose, c'est écrit (« Xetra donne 0,25 % : la première source fait foi »). Pour un autre émetteur,
c'est la liste de Xetra, avec sa réserve : elle est parfois en retard sur une baisse de frais.

---

## 3. Sur tes vraies données

### 3.1 Ce qui a été fait pour toi

Dans une **copie** de ton dossier personnel (rien n'a été écrit dans le tien), sur ton export :

- **sans aucune correction** : 22 valeurs trouvées seules, **1 introuvable** — les frais courants
  de ton ETF iShares « Swap PEA », que tu as choisi de laisser en trou affiché
  ([D-90](../decisions.md)) ;
- **avec ton ancien `actifs.toml`** : aucune valeur que tu avais validée n'est contredite par ce
  que l'application trouve seule ; la date d'ouverture du PEA, première version, donnait une
  semaine trop tard — d'où ta réponse et [D-86](../decisions.md), après quoi elle retombe sur la
  tienne ;
- ton ancien `actifs.toml` contient une ligne pour l'**ancien code pytr** de ta crypto : elle est
  signalée comme ne désignant plus rien, et peut être retirée.

Le détail chiffré est dans `etape-8-quater.local.md`, qui reste sur ta machine.

### 3.2 Les contrôles à faire

1. **Déplace ta configuration** si ce n'est pas fait : le contenu de
   `…\AppData\Local\DashBoardTradeRepublic\configuration` vers `…\AppData\Local\Pastory\configuration`
   (`uv run pastory emplacements` dit où). Puis **retire de `actifs.toml`** ce qui est désormais
   trouvé seul — ou tout le fichier : rien ne t'oblige à le garder.
2. `uv run pastory actifs` : lis chaque bloc. Pour chaque **cotation**, ouvre le cours dans ton
   application Trade Republic et vérifie qu'il ressemble au cours de clôture de la source (même
   ordre de grandeur, même devise).
3. Pour chaque **TER**, compare au document d'information clé de l'émetteur (fiche du fonds).
4. Pour chaque **contenu** non « actions », vérifie le nom du fonds : un fonds obligataire, un ETC
   d'or.
5. **La date d'ouverture de ton PEA** : celle de ton application (ou de ton contrat).
6. `uv run pastory positions` : les chiffres doivent être ceux d'avant, aux réglages près. Le bloc
   « D'où viennent les TER » nomme la source de chaque taux.

### 3.3 Ce que je ne peux pas vérifier à ta place

- qu'une cotation retenue est **la** bonne quand deux places du même titre coexistent (elles
  donnent le même cours, à quelques dixièmes) ;
- le sens fiscal exact d'une **prime d'ouverture** créditée par la banque : la règle la compte comme
  le premier crédit du plan, et c'est ce que ton cas a confirmé.

---

## 4. Ce que cette étape ne fait pas

- **Aucun écran** : la correction se fait encore dans `actifs.toml` ou `fiscalite.toml`, pour qui le
  souhaite. Les écrans de correction sont l'étape 9 ([D-78](../decisions.md)).
- **Le monétaire, les multi-actifs et l'immobilier** n'ont pas encore de contenu
  ([Q-60](../questions-ouvertes.md)).
- **Le gain du PEA calculé comme le fisc** (valeur moins versements) n'est pas fait : il faudrait
  lire les montants d'espèces ([D-87](../decisions.md)).
