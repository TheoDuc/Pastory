# L'export officiel de Trade Republic

Ce que contient le fichier « Export des transactions » que Trade Republic propose dans son
application depuis **avril 2026**, ce qu'il apporte au projet, et ce qui reste à confirmer. Il
remplace pytr comme porte d'entrée des opérations ([D-79](decisions.md)).

Premier relevé : **2026-10-01**, sur un export du propriétaire (46 lignes, environ six semaines
d'historique). Structure seulement : **toutes les valeurs citées ici sont fictives**
([D-03](decisions.md)). Les comptages d'opérations sont reproduits.

Légende : ✅ vérifié sur le fichier · 📄 rapporté par une source publique · 🔶 à confirmer

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
- **Ce n'est pas le CSV de pytr** (`account_transactions.csv`, [inventaire §8](inventaire-donnees.md)) :
  colonnes, codes et conventions n'ont rien à voir.

## 2. La forme du fichier ✅

- Encodage UTF-8, séparateur virgule, **tous les champs entre guillemets**, une ligne d'en-tête.
- **Une ligne par opération**, espèces comprises : paiements par carte, virements, intérêts.
- Les lignes **ne sont pas triées** par date : il faut trier à la lecture.
- **Point décimal partout**, sans séparateur de milliers. Le piège n° 1 de pytr — deux écritures
  des nombres dans un même export ([inventaire §11.1](inventaire-donnees.md)) — n'existe pas ici.

## 3. Les 23 colonnes ✅

| Colonne | Rempli | Contenu | Pour Pastory |
|---|---|---|---|
| `datetime` | toujours | instant **en temps universel**, ISO 8601 suffixé `Z`, de 3 à 6 décimales de seconde | `instant_utc` |
| `date` | toujours | le **jour à Paris** de cet instant (`AAAA-MM-JJ`) — vérifié sur les 46 lignes, dont 3 où le jour UTC diffère | `date` ([D-36](decisions.md)) |
| `account_type` | toujours | `DEFAULT` (compte-titres ordinaire) ou `PEA` | **la poche**, directement |
| `category` | toujours | `TRADING` ou `CASH` | premier tri |
| `type` | toujours | code de l'opération, en anglais majuscule (§4) | le classement |
| `asset_class` | sur les lignes d'actif | `FUND`, `CRYPTO` vus ; 🔶 `STOCK`, `BOND`… probables | poche crypto, type d'actif (§6) |
| `name` | souvent | nom de l'actif, ou de la contrepartie pour une ligne d'espèces | affichage seulement |
| `symbol` | sur les lignes d'actif | **l'ISIN** pour un fonds, le **code** (fictif : `ETH`) pour une crypto | `actif` |
| `shares` | sur les ordres | quantité, 10 décimales | `quantite` |
| `price` | sur les ordres | prix d'exécution, 10 décimales | `prix_unitaire` |
| `amount` | toujours | montant signé (négatif = sortie), de 2 à 6 décimales | `montant_brut` (§5) |
| `fee` | si facturés | frais, **négatifs** (`-1.00`) | `frais` |
| `tax` | si prélevées | taxes, **négatives** | `taxes` |
| `currency` | toujours | `EUR` vu partout | `devise` |
| `original_amount`, `original_currency`, `fx_rate` | jamais vus remplis | opérations en devise étrangère 🔶 | contrôle de devise |
| `description` | toujours | texte libre **en anglais**, même quand l'application est en français : `Savings plan execution …`, `Buy trade …` | `nature_source`, **marqué texte** |
| `transaction_id` | toujours | identifiant unique (UUID) | `identifiant`, `reference_source`, dédoublonnage |
| `counterparty_name`, `counterparty_iban` | virements | **données personnelles** | jamais lues |
| `payment_reference` | jamais vu rempli | — | jamais lue |
| `mcc_code` | paiements carte | catégorie du commerçant | jamais lue |

## 4. Les types d'opération rencontrés ✅

| `category` | `type` | Lignes | Ce que c'est | Classement proposé |
|---|---|---|---|---|
| `TRADING` | `BUY` | 6 | achat : plan d'épargne ou ordre ponctuel, fonds ou crypto, PEA ou CTO | **traité** → `achat` |
| `CASH` | `BENEFITS_SAVEBACK` | 1 | Saveback : montant crédité, avec l'ISIN du fonds, **sans quantité ni prix** | **à confirmer** (§7) |
| `CASH` | `CARD_TRANSACTION`, `CARD_TRANSACTION_INTERNATIONAL` | 19 | paiements par carte | espèces, hors périmètre ([D-11](decisions.md)) |
| `CASH` | `TRANSFER_INBOUND`, `TRANSFER_INSTANT_INBOUND` | 9 | virements reçus | espèces, hors périmètre |
| `CASH` | `TRANSFER_IN`, `TRANSFER_OUT` | 8 | mouvements d'argent, dont **versements et retraits PEA** | espèces, hors périmètre |
| `CASH` | `PEA_MARKETING` | 2 | prime d'ouverture du PEA (« PEA activation ») | espèces, hors périmètre ([D-43](decisions.md)) |
| `CASH` | `INTEREST_PAYMENT` | 1 | intérêts sur espèces, avec leur retenue dans `tax` | espèces, hors périmètre |

**Le doublon du PEA a disparu.** Avec pytr, un achat en PEA apparaissait deux fois, versement et
exécution ([inventaire §9.1](inventaire-donnees.md)). Ici le versement est une ligne d'espèces
(`TRANSFER_IN` sur `PEA`) et l'achat une ligne `BUY` : aucun rapprochement à faire.

**Types connus ailleurs, jamais vus ici** 📄 — à confirmer sur un vrai fichier avant d'être
traités : un dividende (le forum de Portfolio Performance cite un dividende **et** sa correction
comme deux lignes séparées), une vente, une action gratuite (`BONUS_ISSUE`, vu dans un projet
français), une réception crypto (`DELIVERY`, `FREE_RECEIPT`), des gains de staking.

## 5. Les montants : ce qui est vérifié ✅

Sur les 6 achats :

- **`amount` vaut `shares × price`** à moins d'un centime près. C'est donc le **montant brut** du
  format pivot ([D-21](decisions.md)), lu directement, et non reconstitué.
- **Les frais ne sont pas dans `amount`.** Exemple fictif : un ordre ponctuel facturé 1 € porte
  `amount = -50.00` et `fee = -1.00` ; le compte est débité de 51 €.
- **Aucune colonne ne donne le montant réellement débité.** Le contrôle du
  [§5 du format pivot](format-pivot.md) (`montant_regle`) doit donc être revu : il comparait deux
  valeurs indépendantes, il n'en reste qu'une.
- **Un achat crypto s'écarte de pytr de quelques centimes** 🔶. pytr annonce un débit rond
  (fictif : `20,00 €`, frais « gratuit ») ; l'export donne `shares × price`, quelques centimes en
  dessous, sans frais. Le montant brut est juste dans les deux cas. Ce qu'on ignore, c'est ce qui a
  été **réellement débité**, et si l'écart est un coût, un arrondi ou un reste en espèces.
  À vérifier dans l'application, sur l'ordre lui-même.

## 6. Ce que le fichier rend automatique

| Ce qui était manuel ou déduit | Avec pytr | Avec l'export officiel |
|---|---|---|
| Le rôle de chaque compte espèces (`comptes.toml`, [D-10](decisions.md)) | déclaré par l'utilisateur, étape obligatoire | **inutile** : la poche est écrite sur chaque ligne |
| La poche d'une opération ([D-40](decisions.md)) | **déduite** du compte | **donnée** (`account_type`) |
| La poche crypto ([D-16](decisions.md)) | déduite du code `XF…` | **donnée** (`asset_class = CRYPTO`) |
| Quantité, prix, frais, taxes | **lus dans un texte allemand** ([D-09](decisions.md)) | **données** |
| Le recoupement avec un second fichier ([D-42](decisions.md)) | indispensable | sans objet : rien n'est lu dans un texte |
| Le ticker d'une crypto | saisi à la main | proposable depuis `symbol` (`ETH` → `ETH-EUR`) |
| Le type d'un actif ([D-55](decisions.md)) | proposé par la source de cours | proposable depuis `asset_class` — [Q-51](questions-ouvertes.md) |
| La connexion | numéro, PIN, confirmation sur le téléphone, à chaque appel | **aucune** : un fichier téléchargé |

Seul `nature_source` (plan d'épargne ou ordre ponctuel) se lit encore dans un texte, la
`description`. Le format pivot le déclare informatif : le moteur ne calcule jamais dessus. Il est
donc marqué `texte` et ne peut rien fausser.

## 7. Ce qui reste à confirmer 🔶

| Point | Pourquoi c'est important | Comment le lever |
|---|---|---|
| **Dividende** : brut et retenue séparés ? | [D-21](decisions.md) et [D-29](decisions.md) exigent le brut ; une correction arrive en seconde ligne 📄 | un export qui contient un dividende |
| **Vente** | réduit la quantité et le capital investi | un export qui contient une vente |
| **Titres reçus sans achat** (actions gratuites, action gagnée, transfert de titres entrant) | [D-15](decisions.md) | un export qui en contient |
| **Saveback** : où sont les parts achetées ? | la ligne n'a ni quantité ni prix ; soit le montant est investi au plan d'épargne suivant (il apparaîtrait alors dans un `BUY`), soit des parts entrent sans ligne | l'export du mois suivant |
| **Crypto** : montant débité réel | contrôle du §5 | l'ordre dans l'application |
| **Devise étrangère** | `original_*` et `fx_rate` jamais vus remplis | une action ou un dividende en dollars |
| **Autres valeurs d'`asset_class`** | type d'actif, poche | un export d'un autre utilisateur |
| **Un export partiel** | une période qui ne commence pas à l'ouverture du compte donne une histoire incomplète ([D-45](decisions.md)) | rien dans le fichier ne le dit : afficher la période couverte |

Le moyen le plus rapide : l'**export officiel d'un autre utilisateur**, lu en structure seulement
(règle 2 de `CLAUDE.md`), comme pour pytr à l'étape 0.

## 8. Les données personnelles du fichier

Le fichier mêle les actifs et **toute la vie du compte courant** : IBAN et noms des
contreparties, commerçants, catégories de dépenses. L'adaptateur doit :

- classer les lignes d'espèces **par leur `type`**, dans une liste explicite, et ne jamais en lire
  les autres colonnes ;
- ne les afficher qu'en **comptage par type**, jamais ligne à ligne ;
- ne rien en recopier dans le format pivot, un journal ou un cache.

## 9. Sources

- [Annonce de Trade Republic](https://x.com/traderepublic/status/2054197402664394967)
- [DivvyDiary, 15 avril 2026](https://divvydiary.com/en/blog/115)
- [Forum Portfolio Performance : import du Transaktionsexport](https://forum.portfolio-performance.info/t/import-trade-republic-csv-transaktionsexport/39126)
- [OZAXE/portfolio-app : séparer le PEA et le CTO](https://github.com/OZAXE/portfolio-app/pull/3)
- [CoinTracking : import Trade Republic](https://cointracking.info/blog/cointracking-trade-republic-import/)
