# L'export officiel de Trade Republic

Ce que contient le fichier « Export des transactions » que Trade Republic propose dans son
application depuis **avril 2026**, ce qu'il apporte au projet, et ce qui reste à confirmer. Il
remplace pytr comme porte d'entrée des opérations ([D-79](decisions.md), [D-81](decisions.md)).

Relevés :
- **2026-10-01**, sur un export du propriétaire : 46 lignes, environ six semaines d'historique ;
- **2026-10-05**, sur l'export d'un second utilisateur : 149 lignes, environ quatorze mois,
  **comparé ligne à ligne à son export pytr** sur la période commune (§5). La même session a
  conduit une recherche sur les importeurs libres qui lisent déjà ce fichier (§9).

Structure seulement : **toutes les valeurs citées ici sont fictives** ([D-03](decisions.md)). Les
comptages d'opérations sont reproduits.

Légende : ✅ vérifié sur un de nos deux fichiers · 📄 rapporté par une source publique, avec un
vrai fichier à l'appui · 💬 affirmé par une source, sans preuve · 🔶 à confirmer

---

## 1. Comment l'obtenir

Dans l'application : **Profil → Relevés → Export des transactions**, choisir la période — **« toutes
les transactions »** pour Pastory — puis *Créer*. On reçoit un fichier CSV nommé
`Exportation de transactions.csv` (nom en français si l'application est en français ✅).

- 📄 La fonction est annoncée par Trade Republic lui-même, et lancée mi-avril 2026. Portfolio
  Performance, DivvyDiary, CoinTracking et Blockpit l'importent déjà.
- **Aucune spécification n'est publiée** : ni liste des colonnes, ni liste des types d'opération.
  Tout ce qui suit est relevé sur de vrais fichiers. Un type jamais vu reste donc possible à tout
  moment, et il est affiché, jamais rangé par défaut (règle 5 de `CLAUDE.md`).
- 💬 L'utilisateur choisit une date de début et une date de fin : **un export partiel est
  possible**, et rien dans le fichier ne le dit (§7).
- **Ce n'est pas le CSV de pytr** (`account_transactions.csv`, [inventaire §8](inventaire-donnees.md)) :
  colonnes, codes et conventions n'ont rien à voir.

## 2. La forme du fichier

- ✅ Encodage UTF-8, séparateur virgule, **tous les champs entre guillemets**, une ligne d'en-tête.
- 📄 **Une seconde variante existe** : séparateur **point-virgule**, champs sans guillemets, et une
  colonne `value_date` à la place de `mcc_code`. Son origine n'est pas documentée (version
  antérieure de l'export, ou fichier réenregistré par un tableur). Pastory lit donc les colonnes
  **par leur nom**, et accepte les deux séparateurs.
- ✅ Les en-têtes sont en anglais, quelle que soit la langue de l'application.
- ✅ **Une ligne par opération**, espèces comprises : paiements par carte, virements, intérêts.
- ✅ Les lignes **ne sont pas triées** par date : il faut trier à la lecture.
- ✅ **Point décimal partout**, sans séparateur de milliers. Le piège n° 1 de pytr — deux écritures
  des nombres dans un même export ([inventaire §11.1](inventaire-donnees.md)) — n'existe pas ici.
- ✅ `transaction_id` est unique sur chacun des deux fichiers : il sert à dédoublonner quand
  plusieurs exports se recouvrent.

## 3. Les colonnes ✅

| Colonne | Rempli | Contenu | Pour Pastory |
|---|---|---|---|
| `datetime` | toujours | instant **en temps universel**, ISO 8601 suffixé `Z`, de 3 à 6 décimales de seconde | `instant_utc` |
| `date` | toujours | le **jour à Paris** de cet instant (`AAAA-MM-JJ`) — vérifié sur les 46 lignes du premier fichier, dont 3 où le jour UTC diffère | `date` ([D-36](decisions.md)), contrôlée |
| `account_type` | toujours | `DEFAULT` (compte-titres ordinaire) ou `PEA` ; 📄 `JUNIOR` (compte enfant) existe | **la poche**, directement |
| `category` | toujours | `TRADING`, `CASH`, `CORPORATE_ACTION`, `DELIVERY` | premier tri |
| `type` | toujours | code de l'opération, en anglais majuscule (§4) | le classement |
| `asset_class` | sur les lignes d'actif | `FUND`, `STOCK`, `CRYPTO` ✅ ; 📄 `BOND`, `DERIVATIVE`, `PRIVATE_FUND` | poche crypto, type d'actif ([D-82](decisions.md)) |
| `name` | souvent | nom de l'actif, ou de la contrepartie pour une ligne d'espèces ; 📄 suit la langue de l'application | affichage, **sur une ligne d'actif seulement** |
| `symbol` | sur les lignes d'actif | **l'ISIN** pour un fonds ou une action, le **code** (fictif : `ETH`) pour une crypto | `actif` |
| `shares` | ordres, dividendes, titres reçus | quantité, **signée** : positive à l'achat, négative à la vente | `quantite`, en valeur absolue |
| `price` | sur les ordres | prix d'exécution, en euros | `prix_unitaire` |
| `amount` | presque toujours | montant signé (négatif = sortie), de 2 à 6 décimales ; **vide** sur des titres reçus | `montant_brut`, en valeur absolue (§5) |
| `fee` | si facturés | frais, **négatifs** | `frais` |
| `tax` | si prélevées | taxes, **négatives** | `taxes` |
| `currency` | presque toujours | `EUR` vu partout ; vide sur des titres reçus | `devise` |
| `original_amount`, `original_currency`, `fx_rate` | dividendes en devise étrangère | montant en devise, sa devise (`USD` vu), et le nombre d'euros pour une unité de devise | contrôle : `original_amount × fx_rate = amount` |
| `description` | toujours | texte libre **en anglais**, même quand l'application est en français : `Savings plan execution …`, `Buy trade …`, `Cash Dividend …` | `nature_source`, **marqué texte** |
| `transaction_id` | toujours | identifiant unique (UUID), y compris sur les lignes d'espèces | `identifiant`, `reference_source`, dédoublonnage |
| `counterparty_name`, `counterparty_iban` | virements | **données personnelles** | jamais lues |
| `payment_reference` | jamais vu rempli | — | jamais lue |
| `mcc_code` | paiements carte | catégorie du commerçant | jamais lue |
| `value_date` | 📄 variante point-virgule seulement | date de valeur | jamais lue |

## 4. Les types d'opération

### 4.1 Vus sur nos fichiers ✅, et ce que Pastory en fait

| `category` | `type` | `asset_class` | Lignes | Ce que c'est | Classement |
|---|---|---|---|---|---|
| `TRADING` | `BUY` | `FUND`, `STOCK`, `CRYPTO` | 68 | achat : plan d'épargne ou ordre ponctuel, PEA ou CTO | **achat** |
| `TRADING` | `SELL` | `STOCK` | 2 | vente | **vente** |
| `CASH` | `DIVIDEND` | `STOCK` | 16 | dividende — **dans la catégorie `CASH`** | **dividende** (§5.3) |
| `CASH` | `DIVIDEND_EQUIVALENT_PAYMENT` | `STOCK` | 1 | « Capital Distribution », versée le même jour qu'un dividende du même titre | **distribution de capital** ([D-14](decisions.md)), **à condition** que la description commence par « Capital Distribution » : le code dit « équivalent de dividende », et un revenu ne se calcule pas comme un remboursement (Q-07). Sinon, affiché |
| `CASH` | `BENEFITS_SAVEBACK` | `FUND` | 1 | Saveback : montant crédité, avec l'ISIN du fonds, **sans quantité ni prix** | **non traité, affiché** (§7) |
| `CORPORATE_ACTION` | `BONUS_ISSUE` | `STOCK` | 1 | actions gratuites : des parts reçues, sans prix ni montant | **non traité, affiché** ([Q-54](questions-ouvertes.md)) |
| `DELIVERY` | `MIGRATION` | `STOCK` | 1 | des parts qui **sortent**, avec un prix, sans montant | **non traité, affiché** ([Q-54](questions-ouvertes.md)) |
| `CASH` | `CARD_TRANSACTION`, `CARD_TRANSACTION_INTERNATIONAL` | — | 20 | paiements par carte | espèces, hors périmètre ([D-11](decisions.md)) |
| `CASH` | `TRANSFER_INBOUND`, `TRANSFER_INSTANT_INBOUND` | — | 22 | virements reçus | espèces |
| `CASH` | `TRANSFER_IN`, `TRANSFER_OUT` | — | 42 | mouvements d'argent, dont **versements et retraits PEA** | espèces |
| `CASH` | `PEA_MARKETING` | — | 2 | prime d'ouverture du PEA (« PEA activation ») ; avec `TRANSFER_IN` et `TRANSFER_OUT` sur le compte `PEA`, elle date le plan — jour et sens seulement ([D-86](decisions.md)) | espèces ([D-43](decisions.md)) |
| `CASH` | `INTEREST_PAYMENT` | — | 16 | intérêts sur espèces, avec leur retenue dans `tax` | espèces |
| `CASH` | `GIFT`, `MANUAL`, `MANUAL_CASH_TRANSFER` | — | 3 | crédits d'espèces divers | espèces |

**Une ligne d'espèces ne porte jamais d'actif** sur nos fichiers. Si un type classé « espèces »
arrive avec un `symbol` ou une quantité, Pastory ne le range pas : il le signale. C'est le cas 📄
d'une action offerte (`STOCKPERK`), rangée dans `CASH` mais qui désigne un titre.

**Le doublon du PEA a disparu.** Avec pytr, un achat en PEA apparaissait deux fois, versement et
exécution ([inventaire §9.1](inventaire-donnees.md)). Ici le versement est une ligne d'espèces
(`TRANSFER_IN` sur `PEA`) et l'achat une ligne `BUY` : aucun rapprochement à faire.

### 4.2 Connus ailleurs, jamais vus chez nous 📄 — affichés comme inconnus

La recherche (§9) a relevé ces couples sur de vrais fichiers d'autres utilisateurs. Aucun n'est
traité tant qu'il n'a pas été vu sur un fichier qu'on peut comparer :

| Couple | Ce qu'on en sait | Pourquoi ce n'est pas anodin |
|---|---|---|
| `TRADING / BUY_CANCELLED` | annule un `BUY` antérieur | sans lui, l'achat annulé resterait compté |
| `CORPORATE_ACTION / SPLIT` | `shares` = parts **supplémentaires** reçues, sans prix ni montant | une division change la quantité sans rien coûter |
| `CORPORATE_ACTION / SPIN_OFF`, `UNBUNDLING`, `STOCK_DIVIDEND`, `OPTIONAL_DIVIDEND`, `WRITE_OFF` | noms seulement, forme inconnue | parts qui entrent ou sortent |
| `CORPORATE_ACTION / REDEMPTION`, `FINAL_MATURITY`, `WARRANT_EXERCISE` | sortie de titres (obligation, warrant), l'argent sur une ligne `CASH` à part | parts qui sortent |
| `DELIVERY / FREE_RECEIPT` | titres ou crypto reçus sans paiement (transfert entrant) | parts qui entrent sans prix |
| `CASH / STOCKPERK` | action offerte : un crédit, puis un `BUY` du même titre et du même montant | parts payées par la banque |
| `CASH / DISTRIBUTION` | ancien nom du dividende de fonds (2023) | un revenu |
| `CASH / EARNINGS`, `TAX_OPTIMIZATION`, `PRE_DETERMINED_TAX_BASE`, `SEC_ACCOUNT` | impôt allemand : `amount` vaut 0, tout est dans `tax` | une taxe sur un actif |
| `CASH / PRIVATE_MARKET_BUY`, `PRIVATE_MARKET_SELL` | fonds de marchés privés, rangés dans `CASH` | des achats et ventes hors `TRADING` |

Une quarantaine d'autres types d'espèces sont nommés dans le code de Portfolio Performance
(`REFERRAL`, `BONUS`, `FEE`, `TAX`, `MERGER`…). Ils ne sont pas pour autant rangés en espèces par
Pastory : un type d'espèces jamais vu peut porter un titre (`MERGER`), et il est d'abord affiché.

## 5. Les montants

### 5.1 Achats et ventes ✅

- **`amount` vaut `shares × price`** à moins d'un centime près, sur les 70 ordres des deux
  fichiers. C'est donc le **montant brut** du format pivot ([D-21](decisions.md)), lu directement.
- **Les frais et les taxes ne sont pas dans `amount`**, et sont négatifs dans les deux sens.
  Exemple fictif : un ordre ponctuel facturé 1 € porte `amount = -50.00` et `fee = -1.00` ; le
  compte est débité de 51 €. Une vente de 80 € avec 1 € de frais porte `amount = 80.00`,
  `fee = -1.00`, `shares = -2`.
- 📄 Sur un achat en PEA d'une action française, `tax` est la **taxe sur les transactions
  financières** (0,4 %).
- **Un ordre exécuté en plusieurs fois donne plusieurs lignes** ✅ — à des instants différents, au
  même prix. pytr n'en donnait qu'une. Chaque ligne devient une opération : les quantités, les
  montants et les frais s'additionnent.
- **Aucune colonne ne donne le montant réellement débité.** Le champ `montant_regle` reste donc
  vide ([D-83](decisions.md)). La comparaison avec pytr montre toutefois que brut ± frais ± taxes
  retombe exactement sur ce qui a été réglé (§5.4).
- 📄 Sur une **obligation** (`BOND`), `amount` inclut les intérêts courus : `amount ≠ shares × price`.
  Pastory refuse donc cette classe tant qu'elle n'est pas étudiée.

### 5.2 La crypto

**Un achat crypto s'écarte de pytr de quelques centimes** 🔶. pytr annonce un débit rond (fictif :
`20,00 €`, frais « gratuit ») ; l'export donne `shares × price`, quelques centimes en dessous, sans
frais. Le montant brut est juste dans les deux cas ; ce qui a été réellement débité reste inconnu,
et c'est sans effet depuis [D-83](decisions.md).

### 5.3 Les dividendes ✅ — et leur piège

- `shares` donne le nombre de parts détenues, **positif** ; `price` est vide.
- `amount` est positif, `tax` est négatif.
- **Pour les actions françaises et américaines, `amount` est le brut** et `tax` contient **toute**
  la retenue, y compris celle des États-Unis. Exemple fictif : un dividende américain de 10,00 €
  bruts porte `amount = 10.00`, `tax = -4.50`, et le compte reçoit 5,50 €.
- **Pour les actions néerlandaises, `amount` est déjà diminué de la retenue des Pays-Bas** (15 %),
  qui n'apparaît **nulle part**. Exemple fictif : un dividende néerlandais de 10,00 € bruts porte
  `amount = 8.50` et `tax = -2.55` (l'impôt français seul) ; le compte reçoit 5,95 €. Le net est
  juste ; le brut ne l'est pas. Constaté sur 5 dividendes sur 5, en comparant à pytr.
  **Rien dans le fichier ne distingue ces lignes.** Pastory prend `amount` pour le brut et affiche
  cette limite en face des dividendes ([D-84](decisions.md)). Aucun autre pays n'a été vérifié.
- **En devise étrangère** : `original_amount × fx_rate = amount`, vérifié sur 6 dividendes en
  dollars ✅ et 📄 sur d'autres fichiers. `fx_rate` est donc le nombre d'euros pour un dollar, et
  `original_amount` est le montant de `amount` exprimé en devise. Ces colonnes sont vides sur les
  ordres, dont le prix est déjà en euros.
- 📄 **Un dividende corrigé** ne porte pas de type à part : c'est une **extourne** — la même ligne,
  tous signes inversés (`amount` négatif), avec un autre `transaction_id` — puis une nouvelle
  ligne. Jamais vu chez nous : un dividende à montant négatif est signalé, pas traité — et le
  message dit que l'original **reste compté**, donc que les dividendes de l'actif sont sans doute
  **surestimés**, pas qu'il manque quelque chose.

### 5.4 La comparaison avec pytr ✅

Sur la période commune aux deux exports du second utilisateur, ligne officielle contre opération
pytr, même jour et même actif :

| Ce qui est comparé | Résultat |
|---|---|
| Poche (`account_type` contre poche déduite du compte) | identique sur les 75 opérations |
| Ventes : quantité, brut, frais, taxes | identiques, 2 sur 2 |
| Achats : quantité, brut, frais, taxes | identiques sur 51 ; les **6 autres** sont des ordres exécutés en deux fois, dont **les sommes** sont identiques |
| Dividendes : net | identique, 15 sur 15 |
| Dividendes : brut et taxe | identiques sur 10 ; les **5 autres** sont néerlandais (§5.3) |
| Distribution de capital | identique, 1 sur 1 |
| Brut ± frais ± taxes contre montant réglé de pytr | identique partout |

## 6. Ce que le fichier rend automatique

| Ce qui était manuel ou déduit | Avec pytr | Avec l'export officiel |
|---|---|---|
| Le rôle de chaque compte espèces (`comptes.toml`, [D-10](decisions.md)) | déclaré par l'utilisateur, étape obligatoire | **inutile** : la poche est écrite sur chaque ligne |
| La poche d'une opération ([D-40](decisions.md)) | **déduite** du compte | **donnée** (`account_type`) |
| La poche crypto ([D-16](decisions.md)) | déduite du code `XF…` | **donnée** (`asset_class = CRYPTO`) |
| Quantité, prix, frais, taxes | **lus dans un texte allemand** ([D-09](decisions.md)) | **données** |
| Le recoupement avec un second fichier ([D-42](decisions.md)) | indispensable | sans objet : rien n'est lu dans un texte |
| Le ticker d'une crypto | saisi à la main | proposable depuis `symbol` (`ETH` → `ETH-EUR`), à l'étape 8 quater |
| Le type d'un actif ([D-55](decisions.md)) | proposé par la source de cours | **donné** par `asset_class` ([D-82](decisions.md)) |
| La connexion | numéro, PIN, confirmation sur le téléphone, à chaque appel | **aucune** : un fichier téléchargé |

Seul `nature_source` (plan d'épargne ou ordre ponctuel) se lit encore dans un texte, la
`description`. Le format pivot le déclare informatif : le moteur ne calcule jamais dessus. Il est
donc marqué `texte` et ne peut rien fausser.

**Ce que le fichier fait perdre :** le brut des dividendes de certains pays (§5.3), que pytr
lisait dans le détail de l'événement.

## 7. Ce qui reste à confirmer 🔶

| Point | Pourquoi c'est important | Comment le lever |
|---|---|---|
| **Saveback** : où sont les parts achetées ? | la ligne n'a ni quantité ni prix ; 📄 les parts arriveraient par un `BUY` séparé du même montant, environ un jour après — le Saveback serait alors un simple crédit d'espèces | le prochain export du propriétaire : son Saveback était la dernière ligne du fichier |
| **Actions gratuites, puis « migration »** | sur le seul cas vu, elles s'annulent exactement, et la fraction est payée le jour même par un `CASH / MANUAL` sans ISIN, aujourd'hui ignoré | [Q-54](questions-ouvertes.md) : choisir le traitement ; un second cas, en compte-titres ordinaire |
| **Les autres pays de dividende** | la retenue néerlandaise est perdue ; la suisse, l'allemande, l'espagnole ? | des dividendes de ces pays, comparés à leur relevé PDF |
| **Les types du §4.2** | parts qui entrent ou sortent | un export qui en contient |
| **Un export partiel** | une période qui ne commence pas à l'ouverture du compte donne une histoire incomplète ([D-45](decisions.md)) | rien dans le fichier ne le dit : Pastory affiche la période couverte, et signale un trou entre deux fichiers |
| **La variante point-virgule** | lue par nom, jamais vue chez nous | un fichier de ce format |

## 8. Les données personnelles du fichier

Le fichier mêle les actifs et **toute la vie du compte courant** : IBAN et noms des
contreparties, commerçants, catégories de dépenses. L'adaptateur :

- classe les lignes d'espèces **par leur `type`**, dans une liste explicite, et n'en lit aucune
  autre colonne que `symbol` et `shares`, pour vérifier qu'elles sont vides — à une exception
  près, depuis l'étape 8 quater : pour les versements, primes d'ouverture et retraits du compte
  `PEA`, il retient aussi `account_type` et le **jour**, jamais le montant, pour dater le plan
  ([D-86](decisions.md), [D-87](decisions.md)) ;
- ne les affiche qu'en **comptage par type**, jamais ligne à ligne ;
- n'en recopie rien dans le format pivot, un journal ou un cache ;
- ne garde jamais `counterparty_name`, `counterparty_iban`, `payment_reference`, `mcc_code` ni le
  `name` d'une ligne d'espèces au-delà de la lecture de la ligne. Un test le vérifie.

## 9. Sources

- [Annonce de Trade Republic](https://x.com/traderepublic/status/2054197402664394967)
- [DivvyDiary, 15 avril 2026](https://divvydiary.com/en/blog/115)
- **Portfolio Performance, lu dans le code** — la source la plus sûre :
  [`TradeRepublicCSVExtractor.java`](https://github.com/portfolio-performance/portfolio/blob/master/name.abuchen.portfolio/src/name/abuchen/portfolio/datatransfer/traderepublic/TradeRepublicCSVExtractor.java),
  ses [tests et six vrais exports anonymisés](https://github.com/portfolio-performance/portfolio/tree/master/name.abuchen.portfolio.tests/src/name/abuchen/portfolio/datatransfer/traderepublic)
  (relevés le 2026-10-05)
- [Forum Portfolio Performance : import du Transaktionsexport](https://forum.portfolio-performance.info/t/import-trade-republic-csv-transaktionsexport/39126)
  — dont les messages d'erreur qui nomment les types non pris en charge
- [OZAXE/portfolio-app](https://github.com/OZAXE/portfolio-app) : séparer le PEA et le CTO, et
  les actions gratuites
- [Importeur Wealthfolio](https://github.com/blastik/trade-republic-importer-addon) : `STOCKPERK`,
  `MIGRATION` (sans preuve)
- [CoinTracking : import Trade Republic](https://cointracking.info/blog/cointracking-trade-republic-import/)
- [Blockpit : import du CSV Trade Republic](https://intercom.help/blockpit/en/articles/15452549-how-to-import-data-via-trade-republic-csv-file)

**Écartées :** les convertisseurs pour Ghostfolio lisent le format de pytr, pas celui-ci ; deux
pages (DeclaRenta, PocketPortfolio) décrivent un format qui ne correspond à aucun vrai fichier.
