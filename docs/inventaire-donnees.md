# Inventaire des données pytr

Relevé réalisé le 2026-09-17 sur deux exports :

| Jeu | Événements JSON | Lignes CSV | Remarque |
|---|---|---|---|
| **Propriétaire** | 29 | 13 | Compte récent, peu d'opérations |
| **Tiers** (prêté pour observation) | 171 | 98 | Seules la structure et les comptages sont repris ici, jamais les valeurs |

**Pour reproduire :** `python scripts/inventaire_structure.py <dossier>`. Le script n'affiche
aucune valeur. Tous les comptages de ce document en sont issus.

Les exemples de ce document utilisent des **valeurs fictives**.

Légende : ✅ champ structuré · ⚠️ **texte affiché** (dépend de la langue ou du format de
l'application, donc fragile) · 🔶 déduction (information absente, reconstituée par une règle).

---

## 1. Les deux fichiers

### `all_events.json` : la timeline Trade Republic

C'est une liste d'événements. Champs communs :

| Champ | Contenu | Fiabilité |
|---|---|---|
| `id` | Identifiant unique de l'événement | ✅ |
| `timestamp` | Date et heure UTC (`2026-01-15T08:30:00.000+0000`) | ✅ |
| `eventType` | Type technique (`TRADING_SAVINGSPLAN_EXECUTED`…). **Peut être `null`** | ✅ |
| `amount.value` / `amount.currency` | Montant signé (− sortie, + entrée), devise | ✅ |
| `cashAccountNumber` | Compte espèces concerné. **Absent sur certains événements monétaires** | ✅ |
| `status` | `EXECUTED`, `CANCELED`, ou absent | ✅ |
| `source` | `timelineTransaction` (argent) ou `timelineActivity` (information) | ✅ |
| `icon` | Chemin d'image, contient souvent l'ISIN : `logos/<ISIN>/v2` | ✅ mais détourné |
| `title`, `subtitle` | Textes affichés (nom d'actif, nom d'expéditeur, statut…) | ⚠️ |
| `details.sections[]` | Contenu de l'écran de détail : tableaux de lignes `titre → texte` | ⚠️ presque tout |
| `hidden`, `deleted` | Toujours `false` dans les deux jeux | ✅ |
| `subAmount` | Toujours vide dans les deux jeux | — |

Dans `details`, chaque ligne a la forme `{"title": "Gebühr", "detail": {"text": "1,00 €"}}`. Le
libellé (`Gebühr`) est dans la langue de l'application et le montant est formaté (virgule
décimale, point des milliers, symbole €).

Exemple fictif réduit d'un plan d'épargne exécuté :

```json
{
  "timestamp": "2026-01-02T08:00:00.000+0000",
  "eventType": "TRADING_SAVINGSPLAN_EXECUTED",
  "title": "ETF Exemple (Acc)",
  "icon": "logos/XX0000000001/v2",
  "amount": {"currency": "EUR", "value": -50.0},
  "cashAccountNumber": "0000000002",
  "status": "EXECUTED",
  "details": {"sections": [
    {"type": "header", "action": {"type": "instrumentDetail", "payload": "XX0000000001"}},
    {"title": "Übersicht", "data": [
      {"title": "Zahlung", "detail": {"text": "Cash"}},
      {"title": "Transaktion", "detail": {"text": "2 × 25,00 €", "action": {"type": "infoPage",
        "payload": {"sections": [{"data": [
          {"title": "Aktien", "detail": {"text": "2"}},
          {"title": "Aktienkurs", "detail": {"text": "25,00 €"}}]}]}}}},
      {"title": "Gebühr", "detail": {"text": "Kostenlos"}}]},
    {"title": "Sparplan", "data": [{"detail": {"action": {"type": "openSavingsPlanOverview",
        "payload": {"savingsPlanId": "00000000-0000-0000-0000-000000000000"}}}}]}
  ]}
}
```

### `account_transactions.csv` : export « Portfolio Performance »

Séparateur `;`, virgule décimale. Colonnes : `Date;Type;Valeur;Note;ISIN;Parts;Frais;Impôts / Taxes;ISIN2;Parts2`.
Types observés : `Achat`, `Vente`, `Dépôt`, `Retrait`, `Dividendes`, `Intérêts`, `SPLIT`.
Il est produit par pytr à partir des mêmes événements : ce n'est pas une source indépendante.
Voir la section 8 pour ce qu'il omet et ce qu'il déforme.

### Données sensibles présentes dans l'export

Au-delà des montants, `all_events.json` contient : **noms et IBAN complets** des expéditeurs de
virements, **numéros de compte**, commerçants des paiements carte, et des **liens de documents
pré-signés** (URL S3 avec jeton d'accès temporaire). Ces fichiers ne doivent jamais être versionnés
ni partagés.

---

## 2. Types d'opérations

**Familles :**
- **Externe** : flux qui franchit la frontière Trade Republic.
- **Revenu** : argent reçu qui ne vient pas de l'investisseur.
- **Achat/vente** : échange argent ↔ titres.
- **Interne** : transfert entre comptes Trade Republic.
- **Titres seuls** : titres reçus sans mouvement d'argent.
- **Écarté** : ni argent ni titre.

| `eventType` | Propriétaire | Tiers | Famille | Compte présent |
|---|---:|---:|---|---|
| `BANK_TRANSACTION_INCOMING` | 3 | 11 | Externe (apport) | oui |
| `CARD_TRANSACTION` | 1 | 1 | Externe (retrait, Q-02) | **non** |
| `TRADING_SAVINGSPLAN_EXECUTED` | 5 | 41 | Achat | oui |
| `TRADING_TRADE_EXECUTED` | 1 | 15 | Achat ou vente | oui |
| `PEA_SAVINGS_PLAN_PAY_IN` | 3 | 11 | Interne (courant → PEA) | oui |
| `PEA_DEPOSIT_DEBIT` | — | 3 | Interne (courant → PEA) | oui |
| `PEA_WITHDRAWAL_CASH` | 1 | — | Interne (PEA → courant) | oui |
| `INTEREST_PAYOUT` | — | 13 | Revenu (Q-01) | **9 oui, 4 non** |
| `SSP_CORPORATE_ACTION_CASH` | — | 15 | Revenu : dividende | oui |
| `SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND` | — | 1 | Revenu ou remboursement de capital (Q-07) | oui |
| `CASH_PERK` | — | 1 | Revenu : prime Trade Republic (Q-01) | oui |
| `GIFTING_LOTTERY_PRIZE_ACTIVITY` | — | 1 | Titres seuls : action gagnée | non |
| `SSP_CORPORATE_ACTION_NO_CASH` | — | 1 | Titres seuls : actions gratuites | non |
| `null` avec montant | 3 | — | Voir section 6 | oui |
| `null` sans montant | 2 | 1 | Voir section 6 | non |
| `TRADING_SAVINGSPLAN_EXECUTION_FAILED` | — | 3 | Écarté (a un montant mais statut `CANCELED`) | oui |
| `CARD_VERIFICATION` | — | 1 | Écarté (montant 0) | non |
| `TRADING_ORDER_CANCELLED` | — | 2 | Écarté | non |
| `SSP_CORPORATE_ACTION_INFORMATIVE` | — | 8 | Écarté (assemblée générale, annonce d'échange) | non |
| `SSP_CORPORATE_ACTION_UPCOMING` | — | 7 | Écarté (dividende annoncé, pas encore versé) | non |
| `SSP_CORPORATE_ACTION_INSTRUCTION` | — | 1 | Écarté (choix à faire : dividende en espèces ou en actions) | non |
| `DOCUMENTS_ACCEPTED` | 4 | 10 | Écarté | non |
| `DOCUMENTS_CREATED` | 1 | 1 | Écarté | non |
| `CUSTOMER_CREATED` | 1 | 1 | Écarté | non |
| `SECURITIES_ACCOUNT_CREATED` | 1 | 1 | Écarté | non |
| `EMAIL_VALIDATED` | 1 | 1 | Écarté | non |
| `PIN_CHANGED` | — | 1 | Écarté | non |
| `PIN_RESET` | — | 1 | Écarté | non |
| `CSX_CHAT_ACTIVITY` | 1 | 14 | Écarté (échange avec le support) | non |
| `QUARTERLY_NET_WORTH_STATEMENT_CREATED` | 1 | 1 | Écarté (relevé trimestriel) | non |
| `TAX_YEAR_END_REPORT_CREATED` | — | 1 | Écarté (rapport fiscal annuel) | non |
| `EX_POST_COST_REPORT_CREATED` | — | 1 | Écarté (rapport des coûts, **source possible des frais implicites**) | non |
| `CRYPTO_TNC_UPDATE_2025` | — | 1 | Écarté (conditions crypto) | non |
| **Total** | **29** | **171** | | |

Tous les montants observés sont en **EUR**.

> **Périmètre retenu depuis ce relevé ([D-11](decisions.md)) : les actifs, pas les espèces.**
> Les familles *Externe* et *Interne*, ainsi que les revenus en espèces (`INTEREST_PAYOUT`,
> `CASH_PERK`, euro d'activation PEA), sont **hors périmètre** : écartés mais comptés. Restent
> traités : *Achat/vente*, *Titres seuls*, et les revenus des actifs (`SSP_CORPORATE_ACTION_CASH`,
> `SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND`). Le compte espèces reste utile pour une seule chose :
> savoir si un achat a eu lieu dans le PEA.

> **Règle pour l'application :** un événement dont le type n'est ni dans les familles traitées ni
> dans la liste « Écarté » est **inconnu** et doit être affiché. On ne peut **pas** écarter un
> événement parce qu'il n'a pas de montant : l'action gagnée et les actions gratuites n'ont pas de
> montant mais modifient les positions. On ne peut pas non plus le traiter parce qu'il a un
> montant : un plan échoué porte un montant alors que rien n'a bougé. Il faut aussi vérifier
> `status = EXECUTED`.

Types probables mais **jamais observés** (ex. virement sortant, vente de crypto, investissement
de l'arrondi ou du « saveback ») : ils seront inconnus jusqu'à ce qu'un export en contienne.
L'événement carte du propriétaire annonce déjà une ligne « Saveback-Anteil ». Un événement de
crédit de titres lié au saveback apparaîtra donc probablement plus tard.

---

## 3. Comptes espèces

### Propriétaire : trois comptes

| Compte | Ce qu'on y voit | Rôle déduit 🔶 |
|---|---|---|
| **A** | Virements reçus (3), versements vers le PEA (3), plans d'épargne crypto et ETF hors PEA (2), achat ponctuel « Portfolio = Brokerage » (1), réception du transfert PEA (1) | **Compte courant** : CTO, crypto, point d'entrée et de sortie de l'argent |
| **B** | +1 € « PEA-Aktivierung », puis −1 € « PEA-Übertragung » vers le compte A six jours plus tard (même seconde que le `PEA_WITHDRAWAL_CASH` sur A). Plus rien ensuite | **Premier compte espèces PEA, vidé et inactif**. Confirmé : PEA ouvert, fermé puis rouvert ; l'euro d'activation est versé par Trade Republic |
| **C** | +1 € « PEA-Aktivierung » deux minutes après le vidage de B, puis les 3 achats de plans PEA | **Compte espèces du PEA actif** |

Le paiement carte n'a **aucun** numéro de compte. Rattachement probable au compte courant 🔶.

### Tiers : deux comptes

| Compte | Types | Rôle déduit 🔶 |
|---|---|---|
| **A** | Virements reçus, intérêts, dividendes, prime, versements PEA, achats « Brokerage », 4 plans d'épargne | Compte courant (CTO) |
| **B** | 37 plans d'épargne, 6 ordres « Portfolio = PEA » (dont 2 ventes), 1 dividende, 3 plans échoués | Compte espèces du PEA |

4 versements d'intérêts, tous antérieurs aux intérêts rattachés à un compte, n'ont pas de numéro de
compte. Rattachement probable au compte courant 🔶.

> **Conséquence :** le rôle d'un compte se devine mais ne s'affirme pas. L'application demandera à
> l'utilisateur de nommer chaque compte à l'installation, en lui montrant pour l'aider les types
> d'opérations de chaque compte.

---

## 4. Fiches par type : où est chaque information

### `BANK_TRANSACTION_INCOMING` : virement reçu
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (positif) |
| Compte | ✅ `cashAccountNumber` |
| Expéditeur, IBAN | ⚠️ `title`, lignes « Absender », « IBAN » (**données personnelles**) |
| Actif, quantité, poche | sans objet |

### `CARD_TRANSACTION` : paiement par carte
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (négatif) |
| Compte | ❌ absent : 🔶 compte courant |
| Commerçant | ⚠️ ligne « Händler » |
| État | ⚠️ ligne « Kartenzahlung » : observé « Ausstehend » (en attente) et « Fertig » (terminé). **Le montant peut encore changer tant que le paiement est en attente.** |
| Saveback | ⚠️ section « Vorteile » > ligne « Saveback-Anteil » (propriétaire) |

### `TRADING_SAVINGSPLAN_EXECUTED` : exécution d'un plan d'épargne
| Information | Emplacement |
|---|---|
| Montant payé | ✅ `amount.value` (négatif) |
| Actif (ISIN) | ✅ `details.sections[header].action.payload` (type `instrumentDetail`) et `icon`. Concordants 46/46 |
| Quantité | ⚠️ ligne « Transaktion » > page de détail > « Aktien » (`"0,5"`), ou préfixe du texte `"2 × 25,00 €"`. CSV : colonne `Parts` |
| Prix unitaire | ⚠️ « Aktienkurs » |
| Frais | ⚠️ « Gebühr » : seule valeur observée « Kostenlos » |
| Poche | ❌ **aucun libellé**. 🔶 compte de l'événement (compte PEA → PEA). Sinon CTO, ou crypto si le code commence par `XF` 🔶 |
| Plan | ✅ `savingsPlanId` (section « Sparplan ») |
| Moyen de paiement | ⚠️ « Zahlung » = « Cash » (46/46) |

### `TRADING_TRADE_EXECUTED` : ordre ponctuel (achat ou vente)
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value`. Négatif = achat, positif = vente. Frais inclus |
| Sens | ✅ signe du montant ; ⚠️ `subtitle` « Kauforder », « Verkaufsorder », « Stop-Sell-Order » |
| Actif (ISIN) | ✅ en-tête `instrumentDetail` et `icon` (16/16) |
| Type d'instrument | ✅ `contextParams.instrumentType` (`fund`, `stock` observés). Seul type à le porter |
| Quantité | ⚠️ « Aktien ». ✅ `orderbookSnapshot.orderSize` **seulement 1 fois sur 16** : non fiable. CSV `Parts` |
| Prix | ⚠️ « Aktienkurs ». ✅ `orderbookSnapshot.executionPrice` (1/16) |
| Frais | ⚠️ « Gebühr » (numérique). CSV `Frais` |
| Taxes | ⚠️ « Steuer » sur 6 achats du tiers (4 CTO, 2 PEA). CSV `Impôts / Taxes` |
| Poche | ⚠️ « Portfolio » = « Brokerage » ou « PEA ». **Concorde avec le compte** dans 16/16 cas |
| Gain de la vente | ⚠️ section « Performance » > « Gewinn », « Rendite » (calculé par Trade Republic, utile pour recouper) |

### `PEA_SAVINGS_PLAN_PAY_IN` et `PEA_DEPOSIT_DEBIT` : versement du compte courant vers le PEA
`PAY_IN` accompagne un plan d'épargne. `DEPOSIT_DEBIT` accompagne un ordre ponctuel
(« Ordertyp » = « Kauf »).

| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (négatif, débité du compte courant) |
| Compte débité | ✅ `cashAccountNumber` = compte courant |
| Compte crédité | ❌ absent : 🔶 compte PEA (aucun événement de crédit côté PEA) |
| Actif (ISIN) | ✅ en-tête `instrumentDetail` et `icon` (17/17) |
| Poche | ✅ le type lui-même ; ⚠️ « Konto » = « PEA », `subtitle` « PEA » |
| Identifiant du plan | ❌ **absent** (0/17) |
| Quantité | ❌ absente |

### `PEA_WITHDRAWAL_CASH` : retour d'argent du PEA vers le compte courant
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (positif, crédité sur le compte courant) |
| Contrepartie | Événement `eventType = null` de montant opposé sur le compte PEA, **à la même seconde** (1/1) |
| Libellé | ⚠️ `title` « Einzahlung », `subtitle` / « Ereignistyp » « PEA-Übertragung » |

### `INTEREST_PAYOUT` : intérêts sur espèces
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (positif). Net ou brut d'impôt : **à vérifier** en recoupant avec « Gesamt » et « Steuern » |
| Impôts | ⚠️ « Steuern ». CSV `Impôts / Taxes` (12/13) |
| Compte | ✅ 9/13 ; absent 4/13 🔶 compte courant |

### `SSP_CORPORATE_ACTION_CASH` : dividende
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (positif). Net ou brut d'impôt : **à vérifier** avec « Gesamt » et « Steuer » |
| Actif (ISIN) | ✅ **uniquement dans `icon`** (pas d'en-tête `instrumentDetail`) |
| Quantité détenue | ⚠️ section « Geschäft » > « Aktien ». CSV `Parts` |
| Dividende par action | ⚠️ « Dividende pro Aktie » (parfois non numérique) |
| Impôt | ⚠️ « Steuer ». CSV `Impôts / Taxes` (14/15) |
| Poche | ❌ 🔶 compte (14 sur le compte courant, 1 sur le compte PEA) |

### `SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND` : distribution non-dividende
Même structure que le dividende, avec « Bruttoertrag » (produit brut) et « Event » =
« Kapitalverteilung » (distribution de capital). **Le CSV la classe en `Dépôt`** (voir section 8).

### `CASH_PERK` : prime Trade Republic
| Information | Emplacement |
|---|---|
| Montant | ✅ `amount.value` (positif) |
| Nature | ⚠️ « Zahlungsart » = « Cash Gutschrift » ; `subtitle` « Trade Republic » |

### `GIFTING_LOTTERY_PRIZE_ACTIVITY` : action gagnée
**Pas de montant, pas de compte**, mais des titres entrent.
| Information | Emplacement |
|---|---|
| Actif (ISIN) | ✅ `icon` uniquement |
| Quantité | ⚠️ « Aktien » |
| Valeur | ⚠️ « Aktienkurs », « Summe », « Cash-Gutschrift » |
| CSV | **absent** |

### `SSP_CORPORATE_ACTION_NO_CASH` : actions gratuites
**Pas de montant, pas de compte**, mais des titres entrent.
| Information | Emplacement |
|---|---|
| Actif (ISIN) | ✅ `icon` uniquement |
| Nature | ⚠️ `subtitle` / « Orderart » = « Bonusaktien » |
| Quantité | ⚠️ « Aktien hinzugefügt ». CSV : ligne `SPLIT` même jour, même ISIN, colonne `Parts` |

---

## 5. Types à écarter à l'entrée

Aucun argent ni titre ne bouge. Ils sont écartés, mais l'application doit pouvoir montrer leur
nombre (« N événements d'information ignorés ») :

`DOCUMENTS_ACCEPTED`, `DOCUMENTS_CREATED`, `CUSTOMER_CREATED`, `SECURITIES_ACCOUNT_CREATED`,
`EMAIL_VALIDATED`, `PIN_CHANGED`, `PIN_RESET`, `CSX_CHAT_ACTIVITY`,
`QUARTERLY_NET_WORTH_STATEMENT_CREATED`, `TAX_YEAR_END_REPORT_CREATED`,
`EX_POST_COST_REPORT_CREATED`, `CRYPTO_TNC_UPDATE_2025`, `SSP_CORPORATE_ACTION_INFORMATIVE`,
`SSP_CORPORATE_ACTION_UPCOMING`, `SSP_CORPORATE_ACTION_INSTRUCTION`, `TRADING_ORDER_CANCELLED`.

Et, **sur condition** :
- `TRADING_SAVINGSPLAN_EXECUTION_FAILED` : a un montant mais `status = CANCELED` (motif ⚠️
  « Grund » = « Unzureichende Mittel », fonds insuffisants).
- `CARD_VERIFICATION` : montant 0.
- `eventType = null` **sans montant** (section 6).

---

## 6. Événements sans type (`eventType = null`)

| Jeu | Compte | Montant | Identification ⚠️ | Icône | Nature |
|---|---|---|---|---|---|
| Propriétaire (×2) | aucun | aucun | `title` « Rechtliche Dokumente » | `timeline_document` | Documents acceptés : **à écarter** |
| Propriétaire (×2) | PEA (B puis C) | **+** | « Ereignistyp » = « PEA-Aktivierung » | `timeline_plus_circle` | **Euro d'activation du PEA**, sans débit correspondant ailleurs 🔶 (Q-01) |
| Propriétaire (×1) | PEA (B) | **−** | « Ereignistyp » = « PEA-Übertragung », « An » = « Bankkonto » | `timeline_minus_circle` | **Côté PEA d'un transfert PEA → compte courant.** Contrepartie : `PEA_WITHDRAWAL_CASH` à la même seconde |
| Tiers (×1) | aucun | aucun | `title` « PEA-Übertragung » | `timeline_bank` | Inconnu : transfert de PEA depuis un autre établissement ? (Q-10) |

**Seule identification possible : un texte en allemand.** Alternative partielle sans texte :
compte + signe + icône (`plus_circle` / `minus_circle`) + contrepartie à la même seconde. Fragilité
à signaler dans l'application.

---

## 7. Différences entre les deux jeux

**Présents chez le tiers, absents chez le propriétaire (18 types) :**
`CARD_VERIFICATION`, `CASH_PERK`, `CRYPTO_TNC_UPDATE_2025`, `EX_POST_COST_REPORT_CREATED`,
`GIFTING_LOTTERY_PRIZE_ACTIVITY`, `INTEREST_PAYOUT`, `PEA_DEPOSIT_DEBIT`, `PIN_CHANGED`,
`PIN_RESET`, `SSP_CORPORATE_ACTION_CASH`, `SSP_CORPORATE_ACTION_CASH_NON_DIVIDEND`,
`SSP_CORPORATE_ACTION_INFORMATIVE`, `SSP_CORPORATE_ACTION_INSTRUCTION`,
`SSP_CORPORATE_ACTION_NO_CASH`, `SSP_CORPORATE_ACTION_UPCOMING`, `TAX_YEAR_END_REPORT_CREATED`,
`TRADING_ORDER_CANCELLED`, `TRADING_SAVINGSPLAN_EXECUTION_FAILED`.

**Présents chez le propriétaire, absents chez le tiers :** `PEA_WITHDRAWAL_CASH`, les événements
`null` **avec montant** (activation et transfert PEA), la crypto (code `XF…`), le saveback annoncé
sur un paiement carte.

**Autres différences :**
- Le tiers n'a aucune crypto : l'hypothèse `XF` n'a pu être vérifiée que sur un seul code.
- Chez le tiers, les libellés de `SSP_CORPORATE_ACTION_UPCOMING` sont **en français** (« Synthèse »,
  « Montant par action », « Statut »), alors que tout le reste est en allemand. **Un même export
  mélange donc les langues.**

---

## 8. Le CSV : ce qu'il apporte, ce qu'il déforme

Les montants des lignes rapprochées sont identiques au JSON (13/13 et 97/97). Mais :

| Problème | Propriétaire | Tiers | Effet si on utilisait le CSV |
|---|---|---|---|
| Versements PEA (`PAY_IN`, `DEPOSIT_DEBIT`) absents | 3 | 14 | Pas de double comptage, mais la répartition par poche est impossible |
| Transfert interne PEA → courant compté en `Dépôt` | 1 | — | **Apport fictif** |
| Euro d'activation PEA compté en `Dépôt` | 2 | — | Apport fictif (ou revenu mal classé, Q-01) |
| Côté PEA du transfert (−1 €) absent | 1 | — | Déséquilibre |
| Distribution de capital comptée en `Dépôt` | — | 1 | **Apport fictif** |
| Prime `CASH_PERK` absente | — | 1 | Revenu manquant |
| Action gagnée absente | — | 1 | Position manquante |
| Actions gratuites notées `SPLIT` | — | 1 | Libellé trompeur, mais quantité présente |
| Paiement carte noté `Retrait` | 1 | 1 | Correct |

**Conclusion :** le CSV ne peut pas servir à calculer les apports. Il reste utile pour recouper
les quantités, les frais et les taxes, qu'il donne sous forme de nombres.

---

## 9. Vérification des 9 observations du propriétaire

### 1. « Chaque investissement PEA apparaît deux fois » : **partiellement vrai, corrigé**
- ✅ Deux événements sur deux comptes : une exécution sur le compte PEA et un versement débité du
  compte courant. Additionner les deux double bien le capital investi.
- ❌ **L'ordre est inversé** : l'achat est exécuté **avant** le versement dans 17 cas sur 17
  (3 propriétaire, 14 tiers). Le versement comble ensuite le découvert du compte PEA.
- ❌ **Ce n'est pas systématique** : chez le tiers, **27 achats PEA sur 41 n'ont aucun versement**
  dans l'export, et le solde reconstitué du compte PEA finit négatif. Il manque donc des entrées
  d'argent vers le PEA (Q-09). Chez le propriétaire, 3/3 achats sont appariés et le solde
  reconstitué du PEA retombe exactement à 0.
- ➕ Il existe **deux** types de versement : `PEA_SAVINGS_PLAN_PAY_IN` (plans) et
  `PEA_DEPOSIT_DEBIT` (ordres ponctuels).
- ➕ Le CSV omet les versements : il ne double pas le capital, mais il a d'autres défauts
  (section 8).

**Conséquence pour la conception :** d'abord, calculer le capital net investi global à partir des
flux externes (D-07). Puis le périmètre a été recentré sur les actifs (D-11) : **on ne lit que les
achats et les ventes**, et les versements PEA sont hors périmètre. Le piège du double comptage et
les versements manquants n'ont donc plus d'effet.

### 2. « Pas de rapprochement par montant ni par temps ; passer par l'identifiant de plan » : **montant et temps confirmés, identifiant de plan infirmé**
- ✅ Montants différents dans 1 cas sur 3 (propriétaire, 1 €) et 3 cas sur 14 (tiers). Chez le
  propriétaire, l'écart s'explique par l'euro d'activation déjà présent sur le compte PEA : le
  versement n'a couvert que la différence, et le solde reconstitué retombe à 0. Hypothèse 🔶 : le
  versement vaut ce qui manque au compte PEA, pas le prix de l'achat. Elle n'a pas pu être
  vérifiée chez le tiers à cause des versements manquants.
- ✅ Écart de temps : 19 à 76 min (propriétaire), 2 à 71 min pour les plans et 0 à 3 min pour les
  ordres ponctuels (tiers).
- ❌ **Le `savingsPlanId` n'est présent que côté exécution** (0 versement sur 17 le porte).
- ✅ Clé commune disponible : l'**ISIN**, présent des deux côtés dans un champ structuré. Règle
  testée : même ISIN, comptes différents, exécution avant le versement, fenêtre de 3 jours →
  **un seul candidat dans 17 cas sur 17**. Cette règle devient ambiguë si deux achats du même
  actif ont lieu le même jour : c'est une déduction 🔶 (Q-16).

### 3. « Le numéro de compte identifie l'argent, pas la poche » : **vrai, mais nuancé**
- ✅ Le compte courant porte à la fois les versements PEA, le CTO et la crypto.
- ➕ En revanche, **l'achat PEA lui-même a lieu sur le compte espèces du PEA**. Pour les ordres
  ponctuels, le compte de l'exécution et le libellé ⚠️ « Portfolio » concordent 16 fois sur 16.
  La distinction PEA / hors PEA peut donc se faire par le compte de l'achat (✅, une fois les
  comptes nommés par l'utilisateur).
- 🔶 Sur le compte courant, **CTO et crypto ne se distinguent que par l'actif** (code `XF`, voir
  point 8). Les plans d'épargne n'ont aucun libellé de poche.
- ⚠️ Le nom de l'actif n'indique pas la poche : un ETF dont le nom contient « PEA » a été acheté
  en « Brokerage » (CTO).

### 4. « Trois comptes, dont un inconnu » : **confirmé**
A = compte courant, B = premier compte espèces PEA vidé et inactif, C = compte espèces PEA actif
(section 3). L'hypothèse d'un PEA ouvert deux fois est à confirmer (Q-11). La décision de faire
nommer les comptes à l'installation est retenue ([decisions.md](decisions.md), D-10).

### 5. « Des événements ont un compte mais aucun type » : **confirmé, et complété**
- ✅ Ce sont l'**activation du PEA** (+1 €, deux fois) et le **côté PEA du transfert PEA → compte
  courant** (−1 €). Identification uniquement par texte allemand ⚠️ (section 6).
- ➕ D'autres `null` n'ont ni compte ni montant (documents, transfert de PEA chez le tiers).
- ➕ **Inverse aussi vrai :** des événements **avec type et montant n'ont pas de compte**
  (`CARD_TRANSACTION`, 4 `INTEREST_PAYOUT`). « Pas de compte » ne veut donc pas dire « pas
  d'argent ».

### 6. « Les textes sont dans la langue de l'application » : **confirmé, et plus grave que prévu**
- ✅ Libellés allemands et nombres au format allemand (`69.249,71 €`).
- ➕ **Un même export mélange l'allemand et le français** (section 7).
- ➕ Seuls ces éléments sont structurés : type, montant, date, compte, statut, ISIN (en-tête et
  icône), identifiant de plan, type d'instrument (ordres ponctuels). **Quantité, prix, frais,
  taxes et poche n'existent qu'en texte** (liste en section 10).

### 7. « Un retrait PEA → compte courant n'est pas une sortie » : **confirmé**
Le `PEA_WITHDRAWAL_CASH` (+) a sa contrepartie exacte (−) sur le compte PEA, à la même seconde.
Flux externes observés : `BANK_TRANSACTION_INCOMING` et `CARD_TRANSACTION`. **Depuis D-11, ces
flux sont hors périmètre** : les rendements se mesurent sur les flux entre espèces et actifs
(achats, ventes, dividendes).

### 8. « La crypto est identifiée par un code XF » : **cohérent, mais non vérifiable sur plusieurs cas**
Un seul code crypto dans les deux jeux (propriétaire), de forme `XF000` + lettres + 4 chiffres.
Aucun autre code ne commence par `X`. Le tiers n'a pas de crypto. La règle reste une déduction 🔶
à confirmer sur d'autres exports (Q-12).

### 9. « Frais nuls ≠ absence de coût » : **vrai en principe, non mesurable dans ces données**
Les plans d'épargne crypto et ETF affichent tous deux « Kostenlos ». Aucun champ ne donne l'écart
de prix ni les frais des fonds. Source potentielle : le document `EX_POST_COST_REPORT_CREATED`
(rapport des coûts, PDF non inclus dans l'export). Autre constat : des **taxes** apparaissent sur
des achats d'actions (« Steuer »), y compris en PEA (Q-08, Q-13).

---

## 10. Fragilités recensées

| Information | Source unique | Pourquoi c'est fragile |
|---|---|---|
| Quantité (achats, ventes, dividendes, titres reçus) | ⚠️ « Aktien », « Aktien hinzugefügt » | Libellé allemand, format numérique allemand. CSV `Parts` sans doute issu du même texte |
| Prix unitaire | ⚠️ « Aktienkurs » | idem (calculable : montant hors frais / quantité) |
| Frais | ⚠️ « Gebühr » | idem, et « Kostenlos » est un mot |
| Impôts et taxes | ⚠️ « Steuer », « Steuern » | idem |
| Poche d'un ordre ponctuel | ⚠️ « Portfolio » | Doublé par le compte ✅ |
| Poche d'un plan d'épargne | 🔶 compte + code `XF` | Déduction |
| Nature des événements `null` | ⚠️ « Ereignistyp », `title` | Seule source |
| Nature d'une distribution / d'actions gratuites | ⚠️ « Event », « Orderart » | Seule source |
| ISIN des dividendes et titres reçus | `icon` uniquement | Détournement d'un chemin d'image |
| Paiement carte définitif ou non | ⚠️ « Kartenzahlung » | Seule source |
| Rattachement carte et anciens intérêts à un compte | 🔶 | Aucun compte dans l'événement |
