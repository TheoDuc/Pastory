# Coûts estimés et fiscalité — comparatif

Le comparatif que [D-17](decisions.md) et [D-23](decisions.md) réclament avant d'écrire une ligne
de code de l'étape 6 : d'où viendront les **frais courants des ETF** (TER), quelles valeurs de
**spread** retenir par défaut, ce que Trade Republic facture **réellement** à la vente, et quelles
**règles fiscales** françaises s'appliquent pour estimer « ce que je récupérerais si je vendais
tout aujourd'hui ». La dernière section dit ce que le propriétaire a tranché le 2026-09-27
([D-55](decisions.md) à [D-61](decisions.md)).

> **État des vérifications.** Trois recherches ont été menées le 2026-09-27. Les points marqués ✅
> ont été **lus en direct** (page officielle ouverte, fichier téléchargé et dépouillé, texte de loi
> ou du BOFiP lu). Les points marqués 📄 viennent de la presse ou de blogs, sans vérification
> officielle. Les points marqués 🔶 n'ont pas pu être vérifiés.
>
> **Aucune valeur du portefeuille n'apparaît ici.** Les ISIN cités sont des identifiants publics
> d'ETF très répandus, employés comme cas de test, sans lien avec les actifs détenus
> ([D-03](decisions.md)). Les montants des exemples sont inventés.
>
> **Sur la fiscalité, le propriétaire n'a pas de relecteur expert** (dit le 2026-09-27) : les
> taux retenus reposent sur les textes officiels cités, dont le principal a été recoupé sur
> impots.gouv.fr. Ils vivent dans un fichier de paramètres daté et sourcé
> (`pastory/parametres/fiscalite.toml`) : une correction ne touche pas au code.

---

## 1. L'essentiel en une page

| Sujet | Ce qui a été établi | Ce qui en découle |
|---|---|---|
| **Prélèvements sociaux 2026** | ✅ **18,6 %** (CSG 10,6 % + CRDS 0,5 % + solidarité 7,5 %) et non plus 17,2 % : la LFSS 2026 a relevé la CSG sur les revenus du capital. IR forfaitaire toujours 12,8 %. **PFU = 31,4 %** | Un seul jeu de taux pour les trois poches, daté du 1er janvier 2026 |
| **CTO** | ✅ Prix de revient fiscal = moyenne pondérée **frais et taxes d'achat inclus**, inchangé par les ventes ; frais de cession déductibles ; gains et pertes compensés | Le moteur tient un **capital fiscal** à côté du capital net investi ([D-57](decisions.md)) |
| **PEA** | ✅ Gain apprécié **au niveau du plan** ; ancienneté depuis le **premier versement** ; < 5 ans : 31,4 % et clôture ; ≥ 5 ans : 18,6 % seuls | Le gain du plan se déduit des seuls titres si aucun retrait n'a eu lieu (§5.3) ; la date du premier versement est **déclarée** ([D-59](decisions.md)) |
| **Crypto** | ✅ 31,4 % ; exonération si les cessions de l'année ≤ 305 € ; prix d'acquisition réduit à chaque vente **en valeur** ; frais d'acquisition non nommés par la loi | Base = valeur − capital net investi (sans frais), prorata des parts : approximation écrite |
| **TER** | ✅ La liste des ETF négociables de **Xetra**, fichier public sans clé, une ligne par ISIN, 2 989 ETF. ~5 % de valeurs en retard, ETF français « PEA » absents | L'application **propose**, l'utilisateur **valide** ([D-61](decisions.md)) |
| **Frais fixes** | ✅ 1 € par ordre exécuté (achat ou vente), 0 € par exécution de plan, 1 € par ordre crypto, 2 € en « Direct Price » | Frais de vente estimés = 1 € par ligne vendue |
| **Spread** | ✅ Aucune promesse chiffrée de Trade Republic ; Xetra publie par ISIN le coût aller-retour des ETF ; les régulateurs mesurent +5 à +15 pb par ordre ; crypto 0,5 à 1,5 % (📄), témoignages 2,7 à 4 % | Un **taux par côté** par type d'actif : ETF 0,05 %, action 0,10 %, crypto 0,50 % ([D-56](decisions.md)) |

---

## 2. Les frais courants des ETF (TER)

### 2.1 Ce qu'on demande à une source

Gratuite ; couvrant les **ETF UCITS européens** ; interrogeable **par ISIN** (Trade Republic
n'identifie les actifs qu'ainsi) ; lisible depuis Python sans bibliothèque lourde ; et surtout
**sans risque de confusion entre parts** : un même fonds a des parts capitalisantes, distribuantes
et couvertes en devise, avec des frais différents. Une valeur mal attribuée est pire qu'une
absence.

### 2.2 Le verdict

| Source | Gratuit | ETF européens | Par ISIN | Accès | Fraîcheur | Verdict |
|---|---|---|---|---|---|---|
| **Xetra, « List of Tradable ETFs & ETPs »** | oui, sans clé | ✅ 3 116 lignes, 2 989 ISIN | ✅ | fichier Excel téléchargeable | ✅ daté (« As of ») ; ~5 % en retard | **Retenue** |
| Yahoo Finance `quoteSummary` | oui, cookie + jeton | ✅ ~60 % des ETF testés ; **aucun Vanguard**, presque aucun ETF « PEA » français | par ticker | JSON non documenté | non datée | Secours documenté, non implémenté |
| justETF | fiche web | ✅ complète | ✅ | pas d'API ni d'export ; scraping fragile | à jour | **Vérification manuelle** par le propriétaire |
| Listes des émetteurs (iShares, Amundi, Vanguard, Xtrackers, SPDR, BNP) | oui | chacun ses fonds | oui | JSON non documenté (iShares) ou PDF | émetteur | Écartées : un adaptateur par émetteur |
| Euronext | oui | Paris | fiche | liste sans colonne de frais | — | Écartée |
| Boursorama | fiche web | oui | oui | **récupération automatique interdite par ses CGU** ✅ | — | Écartée |
| Trackinsight | **non** (≥ 5 000 USD/an) | oui | oui | API | — | Écartée |
| Morningstar, Quantalys | fiche web | oui | oui | scraping seulement | — | Écartées |
| OpenFIGI, registres AMF/ESMA | oui | oui | oui | **aucun champ de frais** | — | Écartées |
| DIC/KID (PDF de l'émetteur) | oui | oui | un PDF par part | pas d'annuaire | annuel | La **référence** pour vérifier à la main |
| Trade Republic / pytr | — | — | — | — | — | Écarté par principe ([D-49](decisions.md)) |

### 2.3 Le fichier Xetra, testé en direct

- Page : `https://www.cashmarket.deutsche-boerse.com/cash-en/Data-Tech/statistics/etf-etp-statistics/etp-list`
  (l'ancienne adresse `xetra.com/.../list-of-tradable-etfs` y redirige). Un seul lien de
  téléchargement, dont l'adresse **change à chaque publication** : il faut relire la page pour
  trouver le lien courant.
- ✅ Le fichier s'appelle `Master_DataSheet_Download.xls` mais **l'extension ment** : c'est un
  `.xlsx`, lisible en bibliothèque standard (`zipfile` + `xml.etree`). 515 Ko, téléchargé sans
  cookie ni blocage. Cellule A2 : « As of AAAA-MM-JJ », la date d'effet.
- Colonnes utiles : `PRODUCT TYPE` (ETF, Active ETF, ETN, ETC), `PRODUCT NAME`, `ISIN`,
  `ONGOING CHARGES`, `USE OF PROFITS` (Accumulating / Distributing), `FUND CURRENCY`.
- ✅ **Une part = une ligne, la clé est l'ISIN** : les parts capitalisantes et distribuantes ont
  des ISIN distincts. Aucun ISIN n'a deux valeurs différentes. Risque de confusion nul si l'on
  joint sur l'ISIN, jamais sur le nom.
- ✅ La valeur est une **fraction** (0.002 = 0,20 %), parfois avec un bruit de flottant
  (« 0.0007000000000000001 ») : arrondir à quatre décimales.
- ✅ Vérifié sur 18 ISIN publics, tous trouvés, dont : IE00B4L5Y983 (iShares Core MSCI World,
  0,20 %), LU1681043599 (Amundi MSCI World, 0,38 %), IE00BK5BQT80 (Vanguard FTSE All-World,
  0,14 %), IE00B5BMR087 (iShares Core S&P 500, 0,07 %).

**Deux limites, à afficher plutôt qu'à cacher :**

1. ✅ **Environ 5 % des valeurs sont en retard** sur des baisses de frais, toujours dans le sens
   « trop haut » (520 ISIN comparés au fichier de l'émetteur iShares : 28 écarts, tous dans ce
   sens, par exemple 0,20 % au lieu de 0,09 % pour un ETF obligataire). D'où le schéma
   « proposé, puis validé » : l'utilisateur relit sur la fiche de l'émetteur.
2. ✅ **Seuls 45 ISIN français** figurent dans le fichier, et les ETF « PEA » d'Amundi (par
   exemple FR0011871128, Amundi PEA S&P 500) en sont **absents** — Yahoo est vide pour eux
   aussi. Pour ceux-là, l'utilisateur saisit la valeur depuis le DIC ou la fiche justETF par ISIN.

### 2.4 Fourchettes de vraisemblance

Sur les 2 484 ETF (hors actifs) du fichier Xetra du 2026-09-25 : minimum 0,03 %, médiane
0,20 %, quartiles 0,12 %–0,35 %, maximum 3,50 %. Par famille (fichier Xetra et pages justETF
d'août-septembre 2026, 📄) : monde 0,05–0,50 %, S&P 500 0,03–0,17 %, émergents 0,09–0,55 %,
obligataire ~0,04–0,65 %. **L'application refuse un TER hors de 0,03 %–1,00 %** : c'est presque
toujours une erreur d'unité (0.20 écrit pour 0,20 % vaudrait 20 %).

---

## 3. Ce que Trade Republic facture

### 3.1 Documents lus

| Document | Version | Statut |
|---|---|---|
| Liste des prix et prestations, Allemagne (`FURTHER_INFORMATION_PRICE_LIST_20230426144143.pdf`) | 04.2023 | ✅ lu intégralement |
| Communiqué « Best Price / Direct Price » (EQS, 2026-07-02) | 2026-07-02 | ✅ |
| Politique d'exécution France, avec la politique crypto (`FR_ExecutionPolicy.pdf`) | 07.2026 | ✅ |
| Pages d'aide : exécution des ordres, frais crypto, exécution des plans, heures d'ordre | 2026 | ✅ |
| **Liste des prix et services, France** (`assets.traderepublic.com/assets/files/FR/Liste_des_prix_et_services.pdf`) | inconnue | 🔶 **refusée aux robots (403)** : à ouvrir dans l'application (Profil → Documents légaux) |

### 3.2 Les montants

| Poste | Montant | Source |
|---|---|---|
| Ordre ponctuel (action, ETF), achat **ou** vente | **1,00 €** de « frais externes » par exécution ; exécutions partielles : une fois par jour de bourse | ✅ liste DE 2023 ; ✅ communiqué 2026 (« only a 1 € settlement fee ») |
| Exécution de plan d'épargne | **0,00 €** | ✅ liste DE 2023 ; ✅ aide |
| Ordre crypto | **1,00 €** ; « pas d'autres frais » — le mot *spread* n'apparaît pas | ✅ aide fr-fr/1489 |
| Ordre « Direct Price » (place choisie parmi 30) | 2,00 € | ✅ communiqué 2026 |
| Tenue de compte, garde, inactivité | 0 € | ✅ document tarifaire compte de paiement FR 2025 ; 📄 blogs |
| PEA : mêmes tarifs que le CTO | 📄 | signal-alpha, avenuedesinvestisseurs (2026) |
| Transfert sortant de PEA | 📄 **discordant** : 150 € selon deux blogs, 25 € par ligne selon un troisième, gratuit dans la liste DE 2023 | hors périmètre de la valeur réelle |

**Ce qui a changé le 2 juillet 2026.** ✅ L'interdiction européenne de la rémunération du flux
d'ordres (PFOF) s'applique en Allemagne depuis le 1er juillet 2026. Trade Republic n'envoie plus
les ordres à la LS Exchange : par défaut (« Best Price »), l'ordre est exécuté **contre Trade
Republic lui-même**, qui se rémunère sur l'écart, « au meilleur prix parmi les places
pertinentes ». La politique d'exécution de juillet 2026 ne nomme aucune place, ne chiffre aucun
spread et ne promet rien selon l'heure. Avant cette date, la LS Exchange promettait des écarts
« liés au marché de référence Xetra » **pendant ses heures (9h–17h30) seulement**.

Les 1 € par ordre sont inchangés depuis 2019 ; ils figurent sur chaque événement de l'export et
sont **lus**, jamais estimés. Seule la vente future (« tout vendre aujourd'hui ») les estime :
**1 € par ligne vendue**, y compris les fractions.

---

## 4. Le spread

### 4.1 Pourquoi il faut l'estimer

Quand on achète, on paie un peu au-dessus du « vrai » prix du moment ; quand on vend, un peu en
dessous. Cette différence rémunère la contrepartie. Elle est **fondue dans le prix d'exécution** :
aucune ligne « spread » n'existe nulle part — ni dans l'application, ni dans l'export, ni dans le
relevé fiscal. C'est le coût que « Kostenlos » ne dit pas.

On ne peut pas le retrouver ordre par ordre à partir des cours de clôture : un ETF monde bouge de
0,5 à 1 % dans une journée, et l'écart cherché est de 0,01 à 0,1 % — le bruit vaut dix à
cinquante fois le signal. Il faut donc un **taux moyen, par type d'actif, affiché comme
estimation**.

### 4.2 La convention : un taux **par côté**

L'écart publié est l'écart total achat/vente. **Un** achat coûte la moitié (du milieu au prix
vendeur), **une** vente l'autre moitié. ✅ La mesure de liquidité de Deutsche Börse (XLM) est
explicitement un aller-retour, décomposée en deux moitiés. Le projet retient donc :

```
spread estimé d'un achat ou d'une vente = montant brut × taux par côté
```

Un écart total de 0,10 % donne un taux par côté de 0,05 % ([D-56](decisions.md)).

### 4.3 Les mesures

| Source | Périmètre | Résultat | Statut |
|---|---|---|---|
| **Deutsche Börse, XLM ETF** (août 2026, 3 084 ETF, aller-retour de 100 000 €) | Xetra | ETF monde très liquides : 1,7–2,4 pb aller-retour ; **médiane 24,7 pb** ; 90e centile 74 pb ; première demi-heure +30 % | ✅ fichier dépouillé |
| **Deutsche Börse, XLM DAX 40** (2026-09-25, aller-retour de 25 000 €) | Xetra | 2,6 pb (SAP) à 14,5 pb ; par côté 0,013–0,07 % | ✅ |
| AFM (Pays-Bas, 2022) | actions, places PFOF vs Euronext | +4,8 à +11,5 pb par transaction, moins bons dans 69–83 % des cas | ✅ |
| CNMV (Espagne, 2022) | actions espagnoles, un courtier PFOF | −0,14 % sur 86 % des ordres | ✅ |
| BaFin (2022) | actions allemandes | avantageux pour les petits ordres (≤ 2 000 € DAX), perdu au-delà | 📄 |
| Étude WHU (2021), **financée par Trade Republic** | 2,2 millions d'ordres | +0,052 % **en faveur** du client | ✅ |
| Comparatifs crypto (extraETF 11/2025, kryptovergleich, finanzwissen 09/2026, Handelsblatt 09/2026) | Bitcoin chez Trade Republic | écart total **0,5 à 1,5 %** | 📄 |
| Témoignages (forum Finanztip 2024, blogs 2024–2026) | Bitcoin, Solana | **2,6 à 4 %** de moins-value immédiate après achat | 📄 |
| Blogs français et allemands (2026) | ETF liquides / actions / hors heures | 0,05–0,15 % / 0,10–0,25 % / 0,5–2 % d'écart total | 📄 |

Aucune mesure indépendante du régime « Best Price » (depuis juillet 2026) n'existe encore.

### 4.4 Les valeurs par défaut retenues (par côté)

| Type d'actif | Défaut | Fourchette | Justification |
|---|---|---|---|
| **ETF** | **0,05 %** | 0,01–0,15 % | Xetra 0,008–0,03 % par côté pour les ETF larges ; surcoût courtier 0 à +0,12 % ; médiane Xetra 0,12 % pour un ETF de niche |
| **Action** | **0,10 %** | 0,02–0,25 % | DAX 0,013–0,07 % ; régulateurs +0,05 à +0,14 % ; petites capitalisations bien au-delà |
| **Crypto** | **0,50 %** | 0,25–1,50 % | comparatifs 0,5–1,5 % d'écart total ; témoignages 2,7–4 % : la borne haute est réaliste |

Un ETF de niche, une petite capitalisation ou un altcoin peuvent recevoir **leur propre taux**
dans `actifs.toml` (`spread_pour_cent`). L'heure de l'ordre n'est pas prise en compte : hors
heures Xetra, les écarts sont trois à cinq fois plus larges, mais l'horodatage de l'export et le
régime d'exécution ont changé en cours d'histoire ; deviner ferait pire que le taux moyen.

### 4.5 Deux façons de vérifier, pour le propriétaire

- **L'information sur les coûts ex post** que Trade Republic doit fournir chaque année (MiFID II
  range « les majorations incorporées dans le prix de transaction » dans les coûts) : à comparer
  avec l'estimation de l'application sur l'année.
- **Le carnet d'ordres agrégé** affiché avant chaque ordre depuis juillet 2026 : noter l'écart
  achat/vente affiché et le prix obtenu sur quelques ordres, et comparer au taux par défaut.

---

## 5. Les règles fiscales

Sources officielles seulement : Légifrance (CGI, CSS, CMF), BOFiP, impots.gouv.fr,
service-public.fr. Toutes lues le 2026-09-27 ; les adresses sont dans
`pastory/parametres/fiscalite.toml`.

### 5.1 Les taux 2026

| Paramètre | Valeur | Source |
|---|---|---|
| IR forfaitaire (CTO, PEA < 5 ans) | 12,8 % | ✅ CGI 200 A, 1, B, 1° |
| IR forfaitaire (crypto) | 12,8 % | ✅ CGI 200 C |
| CSG sur les revenus du capital | **10,6 %** | ✅ CSS L. 136-8, I, 2° ; LFSS 2026 (loi 2025-1403 du 30/12/2025), art. 12 |
| CRDS | 0,5 % | ✅ ordonnance 96-50, art. 19 |
| Prélèvement de solidarité | 7,5 % | ✅ CGI 235 ter |
| **Prélèvements sociaux** | **18,6 %** | ✅ service-public F2329 (30/06/2026) ; ✅ impots.gouv (page PEA, 17/07/2026), recoupée par le projet |
| **PFU** | **31,4 %** | ✅ service-public F21618 (15/04/2026) |
| Exonération d'IR du PEA | après **5 ans** depuis le premier versement | ✅ CMF L. 221-32 ; BOI-RPPM-RCM-40-50-40 § 310 |
| Exonération crypto | cessions de l'année ≤ **305 €** | ✅ CGI 150 VH bis, II, B |

Entrée en vigueur du 18,6 % : plus-values mobilières et crypto « à compter de l'imposition des
revenus de l'année 2025 » ; gain du PEA pour les retraits « à compter du 1er janvier 2026 », sur
la **totalité** du gain d'un plan ouvert depuis 2018 (LFSS 2018, art. 8, V ; LFSS 2026, art. 12,
II, 2°). Le BOFiP crypto (23/04/2024) affiche encore 17,2 % : il est **obsolète**, la loi prime.

✅ Rien dans la loi de finances pour 2026 (loi 2026-103 du 19/02/2026) n'impose les plus-values
latentes des particuliers ; la « taxe Zucman » a été rejetée. La CDHR (imposition minimale des
revenus > 250 000 €) est hors périmètre. 📄 Le PLF 2027 (présenté le 30/09/2026) n'annonce rien
sur ces taux.

### 5.2 CTO : plus-values de cession

- ✅ **Prix de revient fiscal** = prix moyen pondéré d'acquisition, obligatoire (CGI 150-0 D, 3 ;
  BOI-RPPM-PVBMI-20-10-20-40 § 20 et § 50 : « n'est pas affectée par les ventes »), **majoré des
  frais d'acquisition** (BOI-RPPM-PVBMI-20-10-20-10 § 40-50 : courtages, commissions, « impôts
  supportés par le cédant lors de l'acquisition » — donc, par déduction, la taxe sur les
  transactions financières, 0,4 % depuis le 01/04/2025 🔶).
- ✅ **Prix de cession** net des frais de cession (150-0 D, 1).
- ✅ **Moins-values** : compensées avec les plus-values de même nature de l'année, puis
  reportables dix ans (150-0 D, 11). L'application ne connaît pas les reports antérieurs.
- ✅ **Courtier étranger** : aucun prélèvement à la source ; tout se calcule et se paie à la
  déclaration. Idem pour les dividendes reçus en CTO : le 12,8 % et les prélèvements sociaux sont
  dus à la déclaration (BOI-RPPM-RCM-30-20-50), avec crédit d'impôt pour la retenue étrangère.
- ✅ Un ETF en CTO est traité comme une action (BOI-RPPM-PVBMI-10-10-10).

**Formule « tout vendre aujourd'hui »** : base = Σ sur les lignes du CTO de
(valeur de cession nette − capital fiscal), gains et pertes compensés, plancher à zéro ;
impôt = base × 31,4 %. Le projet prend comme valeur de cession nette : valeur brute − spread de
vente estimé − 1 € de frais de vente.

### 5.3 PEA : le gain du plan

- ✅ Le gain est **celui du plan**, pas des titres : valeur liquidative (titres au cours + espèces)
  − versements depuis l'ouverture (BOI-RPPM-RCM-40-50-40 § 270). Les gains réalisés dans le plan
  ne sont pas des versements (BOI-RPPM-RCM-40-50-20-10 § 30).
- ✅ Retrait **avant 5 ans** : clôture du plan (CMF L. 221-32) ; gain imposé au PFU de 31,4 %
  (CGI 200 A, 5) ou au barème sur option.
- ✅ Retrait **après 5 ans** : exonéré d'IR, prélèvements sociaux de 18,6 % ; retraits partiels
  sans clôture.
- ✅ Ancienneté depuis le **premier versement** (BOI-RPPM-RCM-40-50-50 § 1) ; un plan clos puis
  rouvert repart de zéro. Plafond de versements 150 000 €, sans effet sur l'impôt.

**L'application ne suit pas les espèces du PEA** ([D-11](decisions.md)). Elle ne connaît que les
titres. Or, si aucun retrait n'a eu lieu, les espèces du plan valent exactement :

```
espèces = versements − achats bruts − frais et taxes payés + ventes brutes + dividendes bruts − taxes sur dividendes
```

d'où, en ajoutant la valeur des titres et en retranchant les versements :

```
gain du plan = (valeur des titres − capital net investi)      ← plus-value latente
             + (ventes brutes − capital retiré par les ventes) ← plus-values réalisées brutes
             + dividendes bruts
             − frais − taxes                                   ← tous les coûts payés dans le PEA
```

C'est le **gain brut depuis le début** ([glossaire §4](glossaire.md)) **moins les coûts payés**.
Exact sous trois hypothèses, affichées : aucun retrait passé ; ni intérêt ni frais sur les
espèces ; tout mouvement d'espèces est un versement ou la contrepartie d'une opération sur titres
connue. Un PEA **transféré** d'un autre établissement met l'approximation en défaut (l'histoire
d'avant manque, et la date d'origine avec).

### 5.4 Crypto : les actifs numériques (CGI 150 VH bis)

- ✅ Seule la cession contre monnaie (ou bien, ou service) est imposable ; les échanges crypto
  contre crypto sont en sursis.
- ✅ Exonération si la somme des prix de cession de l'année ≤ 305 € ; au-delà, tout est imposable.
- ✅ Plus-value = P − PTA × P / VG, avec P le prix de cession **net des frais**, PTA le prix total
  d'acquisition de **tout** le portefeuille, VG sa valeur globale au moment de la cession — toutes
  les cryptos du contribuable, **où qu'elles soient** (BOI-RPPM-PVBMC-30-20 § 140). Le PTA est
  réduit, après chaque cession, de la fraction P / VG **en valeur** et non au prorata des unités.
- 🔶 Les frais d'acquisition ne sont nommés ni dans la loi ni dans le BOFiP lu : lecture prudente,
  ils n'entrent pas dans le PTA.
- ✅ « Tout vendre » : P = VG − frais, donc PV = (VG − frais) × (1 − PTA / VG) ; sans frais,
  VG − PTA.
- ✅ Moins-values imputables sur les seules plus-values crypto de la même année, jamais reportées,
  jamais sur le CTO.
- ✅ Comptes d'actifs numériques ouverts chez un prestataire étranger : déclaration annuelle
  (formulaire 3916-bis). 🔶 Que le service crypto de Trade Republic en soit un n'a pas été vérifié
  sur source officielle.

**Ce que le projet fait** : base = Σ (valeur brute − spread − frais de vente − capital net
investi), plancher à zéro ; impôt = base × 31,4 %. Le **seuil de 305 €** est mesuré sur
**l'année civile entière** — les cessions crypto déjà faites, lues dans l'export, plus celle qu'on
simule : ne regarder que la vente simulée annoncerait « exonéré » à tort, et l'erreur serait
invisible puisqu'elle donne zéro. Les cessions déjà faites comptent dans le seuil mais pas dans la
base ([D-60](decisions.md)). Deux approximations écrites : le prorata des parts remplace la
réduction en valeur du PTA après une vente passée (identique tant qu'il n'y a pas eu de vente
partielle), et tout le portefeuille crypto est supposé chez Trade Republic.

### 5.5 Exemples chiffrés (valeurs inventées)

- **CTO** : 10 actions achetées 99,90 € plus 1 € de frais → capital fiscal 1 000 €. Cours 150 € :
  1 500 € − 1 € de frais de vente = 1 499 € de cession nette → gain 499 €. Une seconde ligne
  perd 201 €. Base 298 € ; impôt 298 × 31,4 % = **93,57 €**.
- **PEA** ouvert en mars 2021 : plus-value latente 3 000 €, dividendes 200 €, 10 € de frais →
  gain du plan 3 190 € ; après 5 ans, impôt 3 190 × 18,6 % = **593,34 €** ; avant 5 ans,
  3 190 × 31,4 % = **1 001,66 €** et clôture.
- **Crypto** : 1 000 € achetés, valeur 1 500 €, 1 € de frais de vente → base 499 € ; impôt
  499 × 31,4 % = **156,69 €**. Si la valeur vendue était de 300 € : rien, sous le seuil.

### 5.6 Ce que l'estimation ne couvre pas

PFU de plein droit (pas d'option barème, ni de CSG déductible) ; moins-values reportées
d'années antérieures ; plus-values et dividendes déjà encaissés dans l'année (impôts dus quoi
qu'il arrive, pas un coût de sortie) ; titres acquis avant 2018 (abattements) ; plans ouverts
avant 2018 (taux historiques) ; PEA-PME ; activité professionnelle ; produits dérivés ;
contribution sur les hauts revenus ; changement de résidence fiscale ; impôt allemand (🔶 a
priori aucun pour un résident français).

---

## 6. Les paramètres retenus

Ils vivent dans `pastory/parametres/couts.toml` et `pastory/parametres/fiscalite.toml`,
chacun avec sa valeur, sa date d'entrée en vigueur, sa source et la date de vérification
([D-58](decisions.md)).

| Paramètre | Valeur | Depuis |
|---|---|---|
| IR forfaitaire | 12,8 % | 2018-01-01 |
| Prélèvements sociaux | 18,6 % | 2026-01-01 |
| Exonération d'IR du PEA | 5 ans | 2019-05-24 (loi PACTE) |
| Seuil d'exonération crypto | 305 € | 2019-01-01 |
| Frais par ordre, titres | 1,00 € | 2019 |
| Frais par ordre, crypto | 1,00 € | 2019 |
| Frais par exécution de plan | 0,00 € | 2019 |
| Spread par côté, ETF | 0,05 % [0,01–0,15] | 2026-09-27 |
| Spread par côté, action | 0,10 % [0,02–0,25] | 2026-09-27 |
| Spread par côté, crypto | 0,50 % [0,25–1,50] | 2026-09-27 |

---

## 7. Les pièges, pour qui touchera au code

1. **Le fichier Xetra** : extension `.xls` trompeuse (c'est un `.xlsx`), lien qui change à chaque
   publication, valeur en fraction avec bruit de flottant, ISIN répété une fois par devise de
   négociation (prendre la ligne EUR), ~5 % de valeurs en retard, ETF français absents.
2. **Le spread est déjà dans le prix** : ne jamais l'ajouter au prix de revient ni le retrancher
   du produit d'une vente passée. Il est estimé **à côté** ([D-21](decisions.md),
   [D-30](decisions.md)).
3. **Les 1 € par ordre passés sont dans l'export** : les lire, pas les ré-estimer. Seule la vente
   future les estime.
4. **Deux régimes d'exécution** dans l'histoire (LS Exchange jusqu'au 2026-07-01, Trade Republic
   contrepartie depuis le 2026-07-02) : mêmes taux par défaut, faute de mesure du second.
5. **Crypto** : les cours viennent d'une source externe ([D-49](decisions.md)) ; l'écart entre ce
   cours et le prix de sortie de Trade Republic est précisément le spread par côté, et 0,50 % est
   optimiste au vu des témoignages. La fourchette est dans le fichier.
6. **Prélèvements sociaux** : 17,2 % traîne encore dans beaucoup de pages, y compris un BOFiP.
   La loi dit 18,6 % pour 2026.
7. **Le gain du PEA** est celui du plan : un impôt « partiel » (une position PEA sans cours) n'a
   pas de sens, le PEA est alors non calculable en entier.
8. **La valeur réelle du PEA est structurellement minorée**, et c'est le piège le plus subtil de
   l'étape. L'impôt du plan compte les ventes passées et les dividendes ; leur argent est dans les
   espèces du plan, hors périmètre ([D-11](decisions.md)). On retranche donc un impôt dont la
   contrepartie n'est pas à l'actif. Le rapport l'écrit avec le montant concerné, et refuse
   d'afficher un chiffre si le résultat devient négatif — ce qui arrive sur un PEA presque
   entièrement vendu.
9. **Le seuil crypto est annuel, pas « par vente »** : il faut additionner les cessions déjà
   faites dans l'année civile. C'est une erreur qui donne zéro, donc invisible.

---

## 8. Ce qui a été tranché

**Tranché le 2026-09-27 par le propriétaire** (Q-32 à Q-38, lot 5 de
[questions-ouvertes.md](questions-ouvertes.md)), en suivant les recommandations :

| Décision | Ce qui s'applique |
|---|---|
| [D-55](decisions.md) | Le type d'actif (ETF, action, crypto) est **déclaré** dans `actifs.toml`, proposé par l'assistant, jamais dans le pivot |
| [D-56](decisions.md) | Le spread est un **taux par côté**, par type d'actif, remplaçable par actif |
| [D-57](decisions.md) | Le **capital fiscal** est tenu dans le rejeu, côté coûts |
| [D-58](decisions.md) | Les paramètres sont des TOML versionnés, datés et sourcés |
| [D-59](decisions.md) | L'impôt du PEA repose sur « gain brut depuis le début − coûts payés » et une date de premier versement **déclarée** |
| [D-60](decisions.md) | PFU de plein droit ; ce qui est déjà encaissé est hors de la valeur réelle |
| [D-61](decisions.md) | Le TER est proposé depuis Xetra et **validé** par l'utilisateur |

**Ce que le propriétaire n'a pas pu vérifier :** la liste des prix française (à ouvrir dans
l'application) et les taux fiscaux par un tiers compétent. Il a choisi de s'appuyer sur les
sources officielles ci-dessus.

---

*Trois recherches menées le 2026-09-27 (355 requêtes web et fichiers dépouillés localement), sans
interruption.*
