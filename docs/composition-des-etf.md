# Composition des ETF — comparatif

Le comparatif que [D-28](decisions.md) réclame avant d'écrire une ligne de code : quelles sources
gratuites peuvent dire **ce qu'il y a à l'intérieur** d'un ETF — sa répartition par pays et par
secteur — ce qu'elles couvrent vraiment, et ce qu'elles coûtent en fragilité. **C'est au
propriétaire de choisir** ; la dernière section dira ce qu'il a tranché.

> **État des vérifications.** Les points marqués ✅ ont été **testés en direct le 2026-09-27**
> (appel réel au service, réponse lue). Les points marqués 📄 viennent de la documentation ou d'un
> document public, sans essai. Les points marqués 🔶 n'ont pas pu être confirmés, ou ont été
> rapportés de deux façons différentes par deux recherches.
>
> **Aucune valeur du portefeuille n'apparaît ici.** Les ISIN cités sont des identifiants publics
> employés comme cas de test pendant la recherche, sans lien avec les actifs détenus
> ([D-03](decisions.md)).

---

## 1. Ce qu'on demande à une source

Neuf critères, écrits **avant** la recherche, dans l'ordre d'importance pour ce projet.

| # | Critère | Pourquoi il compte ici |
|---|---|---|
| 1 | **Gratuite, sans clé d'accès** | [D-18](decisions.md) et [D-28](decisions.md). Une clé gratuite « pour l'instant » est une dépendance qui se ferme |
| 2 | **Indexée par ISIN** | Trade Republic n'identifie un actif que par son ISIN. C'est l'obstacle de l'étape 4 ([sources-de-cours.md §4](sources-de-cours.md)), et il revient intact |
| 3 | **Couvre les ETF UCITS européens, dont les ETF « PEA »** | C'est le cœur du portefeuille. La liste Xetra du TER ne contient **pas** les ETF français éligibles au PEA ([couts-et-fiscalite.md §2](couts-et-fiscalite.md)) : le trou est connu, il ne doit pas se répéter |
| 4 | **Donne les deux répartitions, déjà agrégées en pourcentages** | Géographique (par pays) et sectorielle. La composition ligne à ligne est un moyen, pas le but |
| 5 | **Datée** | Une composition du mois dernier n'est pas celle d'il y a trois ans. Comme un taux, elle porte sa valeur, sa date et sa source ([D-58](decisions.md)) |
| 6 | **Classification sectorielle identifiable** | Additionner deux ETF suppose de savoir si l'un parle GICS et l'autre ICB. « Technology » et « Information Technology » ne se somment pas d'eux-mêmes, et un secteur est un **texte** : la règle 4 de `CLAUDE.md` s'applique |
| 7 | **Lisible par un programme, et stable** | Pas de page rendue en JavaScript, pas d'adresse qui change à chaque publication (le piège n° 2 de Xetra), et des conditions d'utilisation qui ne l'interdisent pas |
| 8 | **Vérifiable à la main** | Le propriétaire doit pouvoir comparer le résultat avec la **fiche de l'émetteur** d'un de ses ETF. Une source qu'on ne peut pas recouper ne sera pas crue |
| 9 | **Le reste du portefeuille** | Une **action** détenue en direct a un pays et un secteur : d'où viennent-ils ? Une **crypto** n'en a aucun : elle ne doit être rangée nulle part de force |

**Et deux obstacles transversaux, identifiés d'avance :**

- **un ETF synthétique ne détient pas son indice.** Sa poche de collatéral peut être faite
  d'obligations d'État ou d'actions sans rapport avec l'indice suivi. Lire ses lignes donnerait une
  géographie **crédible et fausse** — le genre d'erreur que ce projet traque depuis l'étape 2. Une
  source qui publie des « holdings » sans dire si le fonds est physique ou synthétique est
  dangereuse ;
- **un actif non couvert sort des totaux, qui sont marqués partiels** ([D-53](decisions.md)). Une
  répartition géographique qui ignore 20 % du portefeuille doit le dire, et **jamais** normaliser à
  100 % en silence.

Les deux se sont vérifiés, et le premier est pire que prévu : c'est le §4.

---

## 2. Le verdict en une page

Quatorze familles de sources examinées, onze interrogées réellement.

| Source | Par ISIN | Pays | Secteurs | Date d'arrêté | ETF PEA | Codes machine | Clé | Blocage | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **extraETF** `api-v2/detail/?isin=` | ✅ 1 appel | ✅ complet (jusqu'à 55 pays) | ✅ 11 postes | ⚠️ champ au nom ambigu | ✅ | ✅ **ISO + codes secteur** | non | aucun | **Recommandée (source de calcul)** |
| **justETF** `etf-profile.html?isin=` | ✅ | ✅ complet | ✅ 13-14 postes | ✅ **explicite** | ✅ | ❌ libellés seuls | non | aucun | **Contrôle, et vérification à la main** |
| **Amundi** `mapi/ProductAPI` | ✅ 1 appel | ✅ **panier ET indice** | ✅ 9 + « Others » | ✅ | ✅ | partiels | non | aucun | **Référence de vérification du PEA** |
| **Vanguard** `gpx/graphql` | ✅ 1 appel | ✅ complet | ✅ complet (ICB) | ✅ | — | partiels | non | aucun | Référence de vérification |
| **iShares** `varnish-api` | ✅ 2 appels | ✅ par ligne | ✅ par ligne | ✅ | — | partiels | non | aucun | Référence de vérification |
| **Yahoo** `quoteSummary` | ⚠️ 2 appels | ❌ **aucune** | ✅ 11 postes | ❌ aucune | ✅ | ✅ `sectorKey` | non | jeton obligatoire | Utile pour les **actions en direct** seulement |
| ESMA FIRDS | ✅ | ❌ | ❌ | — | ✅ | ✅ code CFI | non | aucun | Garde-fou : prouver qu'un ISIN est un ETF |
| Xtrackers / DWS | — | ❌ | ❌ | — | — | — | — | — | Écartée : aucune composition publiée |
| **BNP Paribas Easy** | ❌ | ❌ | ❌ | — | ❌ | — | — | **403** | Écartée, **et c'est un trou dans le PEA** |
| fondsweb.de | ✅ | ⚠️ **10 premiers** | ⚠️ **10 premiers** | ✅ | — | ❌ | non | aucun | Écartée : tronquée sans reliquat |
| Trackinsight | — | 🔶 | 🔶 | 🔶 | 🔶 | — | non | **captcha** | Écartée |
| Morningstar (pages publiques) | ❌ id maison | 🔶 | 🔶 | 🔶 | 🔶 | — | non | **challenge** | Écartée |
| FMP, EODHD, Twelve Data, Alpha Vantage, Finnhub | ❌ ticker | variable | oui | rarement | ❌ | — | **oui** | 401 / 403 | Écartées : clé obligatoire, palier gratuit américain |
| ETFdb / VettaFi | ❌ | — | — | — | ❌ (404) | — | — | — | Écartée : États-Unis seulement |
| EET, base des DIC, GECO (AMF) | — | ❌ | ❌ | — | — | — | — | — | Écartées : n'existent pas sous forme interrogeable |

**Le fait central du dossier : aucune source gratuite interrogeable par ISIN ne donne du GICS.**
Le §6 en tire les conséquences, et elles sont plus contraignantes qu'il n'y paraît.

---

## 3. Les trois sources retenues, et leur rôle

Chacune répond à une question différente. Elles ne se mélangent **jamais** dans un même
pourcentage (§11, piège n° 16).

### 3.1 extraETF — la source de calcul

`https://extraetf.com/api-v2/detail/?isin=<ISIN>` — HTTP 200, environ 300 Ko de JSON, **un seul
appel, aucune clé, aucun jeton, aucun cookie**. ✅ Six ISIN de test sur six.

Ce qu'elle livre, et qui compte :

| Champ | Contenu |
|---|---|
| `country_stocks_exposure_list` | jusqu'à **55 pays**, chacun avec son **code ISO 3166-1 alpha-2** |
| `global_stock_exposure_list` | **11 secteurs**, chacun avec un **code machine** (`technology`, `real_estate`…) |
| `asset_allocation_exposure_list` | actions / obligations / liquidités / autres |
| `is_swap_based_etf`, `is_synthetic_replication` | **si le fonds est synthétique** (§4) |
| `index_date_last_update` | une date, différente d'un fonds à l'autre |
| `kiid_url`, `factsheet_url_en` | le lien vers les documents de l'émetteur, **pour vérifier** |

**Le point décisif : les libellés sont en allemand, et on n'en a pas besoin.** Les pays arrivent
par code ISO, les secteurs par code machine. C'est la seule source du dossier qui permette de
calculer **sans lire un texte affiché** — la règle 4 de `CLAUDE.md`.

**Ses trois limites, à assumer :**

1. **c'est une API interne, non documentée.** Son `robots.txt` porte même le commentaire « ne pas
   décommenter l'interdiction de `/api-v2/`, cela casserait les tests de Google » : extraETF a
   envisagé de la fermer aux robots et ne s'en est abstenu que pour Google. Elle peut disparaître
   sans préavis, et son usage n'est pas explicitement autorisé — usage personnel toléré, pas un
   droit. C'est la même forme de question que [D-49](decisions.md) pour pytr ;
2. **la date porte un nom ambigu** : `index_date_last_update` parle de l'**indice**, pas
   explicitement de l'arrêté du portefeuille. Les valeurs observées sont cohérentes et distinctes
   d'un fonds à l'autre (2026-08-31, 2026-09-22, 2026-09-24), mais on ne peut pas affirmer plus que
   ce que le champ dit ;
3. **elle ne connaît que les ETF.** Interrogée avec l'ISIN d'une action, elle répond `count: 0`.

### 3.2 justETF — le contrôle, et ta vérification à la main

`https://www.justetf.com/fr/etf-profile.html?isin=<ISIN>` — page **rendue côté serveur**, donc
lisible sans navigateur, **en français**, et avec sa date d'arrêté écrite en clair (« État :
31/08/2026 », différente d'un fonds à l'autre). Ses pays et ses secteurs somment exactement à
100,00 %.

C'est la page que tu peux ouvrir toi-même pour recouper un chiffre. Mais **sa classification est
différente** de celle d'extraETF (§5 et §6) : elle sert à détecter un écart anormal, **jamais** à
compléter un chiffre manquant.

### 3.3 Les émetteurs — la référence, pas la source

✅ Trois émetteurs sur onze publient leur composition à partir de l'ISIN seul, sans clé :
**Amundi** (un appel), **Vanguard** (un appel), **iShares** (deux appels). Ce sont les documents
qui font foi, et c'est là que la feuille de route te demande d'aller vérifier.

Pourquoi ils ne sont **pas** retenus comme source de calcul, malgré leur autorité :

- **trois émetteurs, trois nomenclatures, et deux sur trois ne la déclarent pas.** Vanguard dit
  utiliser ICB ; Amundi et iShares emploient visiblement GICS sans l'écrire, avec déjà des
  libellés qui divergent entre eux (« Communication » contre « Communication Services »).
  Additionner deux nomenclatures donne un total juste et une répartition fausse (§6) ;
- **leurs agrégats sont tronqués** : Amundi publie 9 secteurs et « Others », iShares 9 pays et
  « Other ». Seul Vanguard publie des listes complètes ;
- **deux émetteurs ne publient rien d'exploitable**, et l'un des deux est **BNP Paribas Easy**,
  deuxième émetteur d'ETF éligibles au PEA : son composant de données répond 403, et son
  `robots.txt` interdit franchement toute adresse à paramètres. **Xtrackers ne publie aucune
  composition.** Une partie d'un PEA resterait donc invisible par cette voie ;
- **les ruptures sont silencieuses.** L'adresse iShares que tout internet recopie ne fonctionne
  plus : elle répond **200 avec une page HTML** au lieu du fichier attendu. Un contrôle doit donc
  vérifier le **contenu**, jamais le code de réponse.

---

## 4. Le piège le plus grave : l'ETF synthétique

**Un ETF synthétique ne détient pas son indice.** Il détient un panier d'actions et un contrat
d'échange (*swap*) qui lui rend la performance de l'indice. Tout ETF « PEA » sur un indice non
européen est synthétique **par construction** : il doit détenir au moins 75 % de titres éligibles
au PEA — donc européens — tout en suivant un indice américain ou mondial.

**Les chiffres, relevés en direct le 2026-09-27** ✅ sur un ETF *MSCI World* à swap portant le
marqueur d'éligibilité au PEA de son émetteur (`FUND_PEA = true`, `Indirect(Swap Based)`) :

| Pays | Le panier réellement détenu | L'indice réellement suivi |
|---|---|---|
| Allemagne | **38,5 %** | 2,1 % |
| Pays-Bas | 17,2 % | 1,4 % |
| États-Unis | 15,6 % | **72,9 %** |
| Japon | absent | 5,8 % |

Ses 109 lignes sont Airbus, ASML, Deutsche Telekom, Siemens Energy — pour un fonds **monde**. Lire
la composition détenue afficherait donc « Allemagne 38 % » sur un ETF mondial. L'erreur est
énorme, et c'est une chance : elle se voit.

🔶 **Le cas vraiment dangereux serait l'inverse, et il reste à confirmer.** La recherche rapporte
un second ETF à swap dont le panier publié donnerait **96,7 % d'États-Unis** — un chiffre *presque*
crédible pour un fonds monde, donc indétectable à l'œil. Mais un panier à 96,7 % d'actions
américaines serait incompatible avec l'éligibilité au PEA du même fonds, et les deux recherches ne
décrivent pas cet ISIN de la même façon. **Le chiffre n'est donc pas retenu comme établi** : il est
gardé comme hypothèse de travail, parce qu'un panier « presque crédible » est précisément ce contre
quoi il faut se protéger, même sans exemple confirmé.

**Troisième variante du même piège, chez deux autres sources :**

- la source de cours du projet renvoie une **liste de lignes vide** pour un ETF synthétique ✅.
  Reconstruire la géographie à partir des lignes donnerait **zéro**, donc un ETF PEA absent des
  totaux sans qu'on sache pourquoi ;
- extraETF attribue au swap lui-même le pays **« USA »** ✅ : l'unique ligne détenue de l'ETF PEA
  testé est `TRS MSCI World NR USD`, `country: "USA"`, poids 100 %. Un calcul fondé sur les lignes
  afficherait **100 % États-Unis pour un ETF monde**.

**Ce qui sauve la situation :** les sources qui publient une répartition **agrégée** publient celle
de l'**indice**, pas celle du panier. ✅ Vérifié sur extraETF, qui donne 32 pays et 11 secteurs pour
ce même ETF PEA dont la seule ligne détenue est un swap. Et Amundi publie **les deux**, en les
distinguant de façon lisible par une machine (préfixes `FUND_` et `INDEX_`), ce qui permet de
contrôler.

**La règle qui en découle, et qui doit être écrite dans le code :** on lit les répartitions
**agrégées**, et **jamais** les lignes détenues. Un ETF dont on ne connaîtrait que les lignes est un
ETF qu'on n'affiche pas.

---

## 5. Ce que « pays » veut dire — et pourquoi ce n'est pas une grandeur unique

C'est la trouvaille la plus importante du dossier, et elle vient de l'émetteur lui-même.
BlackRock écrit, dans sa propre fiche de fonds (données au 31/08/2026) ✅ :

> « Geographic exposure relates **principally** to the domicile of the issuers of the securities
> held in the product […] **However, in some instances it can reflect the location where the
> issuer carries out much of their business.** »

Autrement dit **l'émetteur mélange deux définitions dans la même colonne, sans indicateur pour
dire laquelle s'applique à quelle ligne.** Une répartition géographique d'ETF n'est pas une
grandeur définie de façon unique. Ce n'est pas un défaut de nos sources : c'est la nature de la
donnée.

Les quatre réponses possibles à « de quel pays est cette société ? » :

| Règle | Qui l'emploie | Exemple qui les sépare |
|---|---|---|
| **Pays de domiciliation juridique** | justETF ; iShares, « principalement » | Accenture, Medtronic, Eaton, Aon sont **irlandais** |
| **Pays d'activité / de risque** | Morningstar, donc extraETF ; Amundi (`countryOfRisk`) | ces mêmes sociétés sont **américaines** |
| **Pays de cotation principale** | entre dans la règle MSCI, avec le pays de constitution | un certificat de dépôt coterait aux États-Unis |
| **Répartition du chiffre d'affaires** | personne, dans ce dossier | une société européenne vendant en Asie |

**L'écart mesuré** ✅ sur le même fonds, à la même date d'arrêté : **États-Unis 70,00 % contre
72,04 %**, Irlande **1,41 % contre 0,17 %**. Aucune des deux n'a tort. « 70 % ou 72 %
d'États-Unis » dépend de la règle, pas du fonds.

Et un même émetteur peut publier **trois** réponses pour le même fonds selon le référentiel
demandé ✅ : 61,68 % d'États-Unis au sens FTSE, 61,58 % au sens MSCI, 64,70 % par région. Un
programme qui ne filtrerait pas sur le référentiel additionnerait les trois et afficherait environ
300 %.

Deux conséquences pratiques :

- **la règle retenue doit être affichée**, avec le chiffre. Sans elle, le pourcentage n'est pas
  vérifiable, et un chiffre non vérifiable ne sera pas cru — la leçon de l'étape 6 ;
- **on ne déduit jamais un pays du préfixe de l'ISIN.** Taiwan Semiconductor se négocie sous
  `US8740391003` et n'est pas américain. Ce serait la même famille d'erreur qu'un ISIN lu dans la
  colonne du nom, à l'étape 6.

---

## 6. La nomenclature sectorielle : Morningstar, et jamais « GICS »

**Aucune source gratuite interrogeable par ISIN ne donne du GICS.** Les indices que suivent les
ETF détenus sont pourtant construits sur GICS ou sur ICB. Ce qui est accessible gratuitement,
c'est la classification **Morningstar** — 11 secteurs, celle qu'affichent Yahoo Finance,
Morningstar, justETF et extraETF. C'est donc aussi celle que tu verras en vérifiant.

Les 11 secteurs Morningstar, avec leurs codes officiels (*Morningstar Global Equity
Classification Structure*) 📄 :

| Super secteur | Code | Secteur | Proposition de libellé français |
|---|---|---|---|
| Cyclique | 101 | Basic Materials | Matériaux de base |
| | 102 | Consumer Cyclical | Consommation cyclique |
| | 103 | Financial Services | Services financiers |
| | 104 | Real Estate | Immobilier |
| Défensif | 205 | Consumer Defensive | Consommation de base |
| | 206 | Healthcare | Santé |
| | 207 | Utilities | Services aux collectivités |
| Sensible | 308 | Communication Services | Communication |
| | 309 | Energy | Énergie |
| | 310 | Industrials | Industrie |
| | 311 | Technology | Technologie |

Les 11 secteurs de niveau 1 sont stables depuis le 15/10/2010 📄. Les niveaux inférieurs, eux, ont
changé (69 groupes d'industries en 2011, 145 industries aujourd'hui) : on s'en tient au niveau 1.

**Pourquoi il est interdit d'additionner deux nomenclatures**, même quand elles se ressemblent :

- **Alphabet et Meta** (environ 5 % d'un indice monde) sont en *Communication* chez GICS et chez
  Morningstar, mais en *Technology* chez ICB. Mesuré ✅ sur le même fonds à la même date :
  technologie **35,71 %** chez justETF contre **30,61 %** chez extraETF. L'écart, c'est exactement
  ces deux sociétés qui changent de camp ;
- **justETF n'a pas de secteur « immobilier »** ✅ : son poste *Finance* à 18,01 % vaut exactement
  services financiers 16,34 % + immobilier 1,66 % de l'autre source ;
- **les codes eux-mêmes se télescopent** : le code 10 vaut *Technology* chez ICB et *Energy* chez
  GICS. Rapprocher par le code sans nommer la nomenclature inverserait deux secteurs ;
- **GICS a déplacé Visa, Mastercard et PayPal** de la technologie vers la finance en mars 2023,
  soit environ 1,5 % d'un indice monde. Une source en retard les classe encore en technologie ;
- **aucune table de correspondance officielle n'existe** entre GICS et ICB, et elle ne pourrait
  pas être bijective. Le document Morningstar, lui, ne mentionne **pas une seule fois** GICS ✅ :
  tout rapprochement entre les deux est une déduction, et doit être signalé comme telle.

**La règle : une seule nomenclature, nommée à l'écran, et jamais de rapprochement par libellé.**
Si la source retenue est Morningstar, l'interface écrit « classification Morningstar », jamais
« GICS ». Et le tableau ci-dessus — code, libellé, source, date — devient un fichier de paramètres
comme ceux de l'étape 6, dans l'esprit de [D-58](decisions.md).

*À surveiller, sans rien coder :* une consultation GICS est ouverte du 17/07/2026 au 30/10/2026
(intelligence artificielle, semi-conducteurs, sociétés d'investissement cotées), avec des
changements annoncés « avant novembre 2026 » et une date d'effet non publiée 🔶.

---

## 7. Les zones géographiques

Tu as demandé les pays **regroupés en zones**. Le regroupement n'est pas une donnée : c'est une
convention, et il faut en choisir une.

| Besoin | Norme utilisable | Verdict |
|---|---|---|
| **Les pays** | **ISO 3166-1 alpha-2** | ✅ La bonne clé : stable, gratuite, avec des libellés officiels **en français** |
| **Un découpage purement géographique** | **ONU M49** (continents et sous-régions) | ✅ Gratuit, neutre, stable, sans licence |
| **« Développés / émergents »** | Aucune norme. Seulement MSCI et FTSE, propriétaires | 🔶 Il faut nommer le fournisseur **et** dater sa liste |

**Et les deux fournisseurs ne sont pas d'accord en ce moment même :**

- la **Corée du Sud** est développée chez FTSE, émergente chez MSCI ;
- la **Grèce** est développée chez FTSE depuis le 21/09/2026, et ne le sera chez MSCI qu'en
  mai 2027 : **nous sommes dans la fenêtre de désaccord** ;
- la **Pologne** change aussi de camp selon le fournisseur ;
- la **zone euro** elle-même bouge : la Bulgarie a adopté l'euro le 01/01/2026.

Trois pièges de lecture, pour mémoire : le Mexique n'est **jamais** en Amérique du Nord dans ces
classifications ; le Royaume-Uni est toujours séparé de l'Europe, et une somme naïve le compterait
deux fois ; ISO 3166-1 nomme Taïwan « Taiwan, Province of China », ce que les émetteurs n'écrivent
pas — d'où l'intérêt de coder sur `TW`, `HK`, `CN` et de gérer l'affichage à part.

---

## 8. Les ETF obligataires, les fonds de fonds, et les autres pièges de structure

### 8.1 Les ETF obligataires — tu en as

**« Secteur » n'a pas le même sens, et « pays » peut vouloir dire « devise ».** La méthodologie
GICS l'écrit : aucun secteur n'est attribué aux emprunts d'État 📄. Ce que les ETF obligataires
publient à la place, c'est une ventilation par type d'émetteur (Trésor, entreprises, titrisé), par
notation, par maturité. Et surtout, relevé sur une fiche iShares du 31/08/2026 ✅ :

> « Bonds are included in US bond indices when the securities are denominated in U.S. dollars
> **regardless of the domicile of the issuer**. »

Sur un ETF obligataire, « États-Unis » peut donc signifier « libellé en dollars ». Fusionner ses
secteurs avec ceux d'un ETF d'actions fabriquerait des postes « Trésor 18 % » à côté de
« Technologie 25 % », qui ne sont pas de même nature — ou rangerait tout l'obligataire en
« finance », ce qui est absurde.

**Ce que je propose :** une **répartition par classe d'actifs** (actions, obligations, liquidités)
à côté des deux autres, et les ETF obligataires **hors** des répartitions géographique et
sectorielle, avec leur montant affiché. C'est la même logique que [D-11](decisions.md) : on ne
force pas une grandeur dans une catégorie où elle n'a pas de sens.

### 8.2 Les fonds de fonds

Un ETF qui détient d'autres ETF ne se lit pas au premier niveau. ✅ Vérifié sur la fiche d'un fonds
*LifeStrategy* (données au 31/08/2026) : elle ne publie **aucune** ventilation sectorielle ou
géographique, seulement la liste de ses 14 ETF cibles. Au premier niveau, sa composition est
« 100 % fonds d'investissement » — et une source qui applique ICB à ces lignes répond
**« 100 % finance, Irlande »**. Crédible, absurde.

**Ce que je propose :** on ne transparise qu'**un** niveau. Au-delà, l'actif est affiché comme
**non transparisé**, jamais deviné.

### 8.3 Deux pièges plus discrets

- **le prêt de titres** : le collatéral en espèces réinvesti apparaît comme une ligne de plus, et
  la somme des poids peut **dépasser 100 %** 📄. Un contrôle de vraisemblance doit donc accepter un
  dépassement léger, et non le prendre pour une erreur ;
- **les parts multiples d'un même fonds** : un même portefeuille peut porter plusieurs ISIN (part
  capitalisante, part distribuante, part couverte). Les pourcentages restent justes et les poids
  s'additionnent correctement, mais la **diversification apparente est surestimée** — « six
  fonds » au lieu de cinq. À signaler, pas à corriger.

---

## 9. Les actions en direct et la crypto

**Les actions en direct.** extraETF ne les connaît pas (`count: 0`) ✅. La source de cours du
projet, en revanche, donne pour une action un `sectorKey` qui est un **code machine sur la même
nomenclature à 11 secteurs** ✅ — les deux sont donc additionnables sur les **secteurs**. Mais son
champ pays est le **siège social**, soit une troisième règle de pays, et un libellé texte sans code
ISO. La géographie d'un portefeuille mêlant ETF et actions en direct ne serait donc pas homogène.

**La crypto.** Aucune source ne s'applique, et aucune convention n'existe : tous les outils la
mettent à part (Morningstar écrit « Not classified ») 📄. C'est ce que tu as choisi — une ligne à
part, hors géographie et hors secteur.

---

## 10. Les sources écartées, et pourquoi

| Source | Motif d'écartement |
|---|---|
| **Trackinsight** | Application monopage : le HTML ne contient aucune donnée. L'API est derrière un **captcha AWS WAF** |
| **Morningstar** (pages publiques) | **Challenge AWS WAF** (réponse vide), et indexé par identifiant maison, pas par ISIN. Reste la source de fond : les autres revendent sa classification |
| **fondsweb.de** | Ne publie que les **10 premiers** pays et secteurs, **sans reliquat** : totaux à 99,02 % et 97,89 %. Deux points manquants sans dire lesquels. Et il présente « Welt » comme un pays |
| **Boerse Frankfurt** | Répond `{}` sans en-têtes signés, et ne publie pas de transparence de portefeuille |
| **FMP, EODHD, Twelve Data, Alpha Vantage, Finnhub** | **Clé obligatoire** (401 / 403 sans elle), interrogation par **ticker** et non par ISIN, palier gratuit limité aux États-Unis ou à 20-25 appels par jour. C'est la dépendance « gratuite pour l'instant » que [D-18](decisions.md) refuse |
| **ETFdb / VettaFi** | 404 sur un ETF européen : États-Unis seulement |
| **EET, base publique des DIC, GECO (AMF)** | N'existent pas sous forme interrogeable par ISIN. L'EET est un gabarit échangé entre professionnels, et il ne porte ni géographie ni secteurs |
| **Xtrackers / DWS** | Ne publie aucun fichier de composition |
| **BNP Paribas Easy** | Composant de données en **403**, certificat non vérifiable, et `robots.txt` interdisant toute adresse à paramètres. **C'est un trou dans le PEA** |
| **UBS, WisdomTree** | 403 à tout client non navigateur |
| **SPDR, Invesco, VanEck, HSBC** | 🔶 Non aboutis, faute de temps. Invesco a beaucoup de fonds synthétiques : à reprendre si besoin |

Deux sources gratuites et officielles sont retenues comme **garde-fous**, sans donner de
composition : **ESMA FIRDS**, dont le code CFI prouve qu'un ISIN est un ETF **sans lire un
libellé** ✅ — ce qui satisfait la règle 4 — et **OpenFIGI**, pont de l'ISIN vers le ticker.
Attention : le nom du fonds chez ESMA est **périmé** ✅ (un ETF rebaptisé y porte encore son ancien
nom) ; il ne doit jamais être affiché.

---

## 11. Les pièges vérifiés, en une page

**Gravité 1 — un pourcentage franchement faux et parfaitement crédible**

| # | Piège | Conséquence |
|---|---|---|
| 1 | **ETF synthétique lu sur ses titres détenus** ✅ | « Allemagne 38 % » sur un ETF monde |
| 2 | **Le swap porte un pays chez extraETF** ✅ (`country: "USA"`, poids 100 %) | **100 % États-Unis** pour un ETF monde |
| 3 | **La source de cours renvoie une liste vide** pour un ETF synthétique ✅ | L'ETF PEA sortirait des totaux sans motif |
| 4 | **Additionner deux nomenclatures** (GICS, ICB, Morningstar) ✅ | Total juste, répartition fausse. Et le code 10 vaut *Technology* chez l'un, *Energy* chez l'autre |
| 5 | **Fonds de fonds non transparisé** ✅ | « 100 % finance, Irlande » |
| 6 | **Déduire le pays du préfixe ISIN** | Taiwan Semiconductor classé américain |
| 7 | **Source en retard sur GICS mars 2023** 📄 | Visa, Mastercard, PayPal encore en technologie (≈ 1,5 % d'un indice monde) |
| 8 | **Prendre les 10 premières lignes pour la composition**, puis renormaliser ✅ | Biais massif vers les grosses lignes |

**Gravité 2 — quelques points d'écart, ou une vérification impossible**

| # | Piège | Conséquence |
|---|---|---|
| 9 | **Deux règles de pays** (domiciliation contre activité) ✅ | 70,00 % contre 72,04 % d'États-Unis |
| 10 | **Rien ne somme à 100 %** ✅ (99,43 à 99,96 % selon le fonds) | Un contrôle « ça fait 100 » échouerait à tort |
| 11 | **Les deux vues d'un même fonds ne somment pas pareil** ✅ | Pays 99,43 %, secteurs 98,56 % : 0,87 point d'écart |
| 12 | **Renormaliser en silence** | Un camembert qui fait 100 % par construction cache ce qu'il ignore |
| 13 | **ETF obligataires : « pays » peut valoir « devise »** ✅ | Des dollars comptés comme des États-Unis |
| 14 | **Désaccord MSCI / FTSE** sur la Corée, la Pologne, la Grèce ✅ | Une zone « émergents » différente selon le fournisseur |
| 15 | **Dates d'arrêté hétérogènes** entre fonds ✅ (31/08 à 25/09) | Une photo prise à plusieurs instants |
| 16 | **Mélanger deux sources dans un même graphique** ✅ | Trois sources donnent trois « technologie » : 35,71 / 30,61 / 29,52 |
| 17 | **Prêt de titres** : collatéral réinvesti 📄 | Somme des poids **supérieure** à 100 % |
| 18 | **Ruptures silencieuses** : l'adresse iShares répond 200 avec du HTML ✅ | Il faut vérifier le **contenu**, pas le code de réponse |
| 19 | **Trois référentiels dans une même réponse d'émetteur** ✅ | Une somme naïve donnerait environ 300 % |

**Gravité 3 — du bruit à documenter, pour ne pas s'inquiéter**

Arrondis ; parts multiples d'un même fonds (diversification apparente surestimée) ; libellés
traduits d'une langue à l'autre ; « Türkiye » contre « Turkey » ; Belgique et Luxembourg fusionnés
par un fournisseur ; « Cash and/or Derivatives » présenté comme un douzième secteur.

---

## 12. Les cinq tests à passer avant de coder

Chacun attrape un piège de gravité 1, et chacun est refaisable à la main en quelques minutes.

| Test | Cas | Réponse attendue | Ce qu'un échec révèle |
|---|---|---|---|
| **T1** | Visa | *Financial Services* (Morningstar) ou *Financials* (GICS) | Si « Technology » : source antérieure à mars 2023 |
| **T2** | Alphabet | *Communication* chez GICS et Morningstar, *Technology* chez ICB | **Quelle nomenclature parle vraiment la source** |
| **T3** | Taiwan Semiconductor, certificat de dépôt en `US…` | Pays = **Taïwan** | Lecture du préfixe ISIN ou de la place de cotation |
| **T4** | Un ETF PEA sur indice non européen | Environ **96 % d'États-Unis** | Si l'Europe domine : **on lit le panier de swap** |
| **T5** | Somme des poids d'une composition | Entre 99,5 % et 100,5 %, **avec sa date** | 40 % : on n'a que les dix premières lignes. 100,0000 % exact : **renormalisation silencieuse** |

Ces cinq tests deviendront des tests du projet, sur des réponses écrites à la main — aucun test ne
sort de la machine.

---

## 13. Recommandation

1. **extraETF comme source de calcul**, pour une raison qui n'est pas la richesse mais la
   cohérence : **une seule nomenclature, une seule règle de pays, des codes machine**, et une
   réponse correcte sur un ETF PEA synthétique. Ses limites — API interne, date au nom ambigu —
   sont à afficher, pas à cacher.
2. **Les répartitions agrégées, jamais les lignes détenues.** C'est la règle qui neutralise les
   pièges n° 1, 2 et 3 d'un seul coup.
3. **Trois répartitions, pas deux** : classe d'actifs (actions, obligations, liquidités), puis
   géographie et secteurs **de la seule partie actions**. Tes ETF obligataires trouvent ainsi leur
   place sans fausser les deux autres.
4. **Chaque pourcentage porte sa nomenclature, sa source et sa date** — transposition directe de
   [D-58](decisions.md). Sans les trois, il est refusé.
5. **Le reliquat reste visible**, sous le nom de « non attribué », et **rien n'est jamais
   renormalisé à 100 %** ([D-53](decisions.md)).
6. **Les pays par code ISO 3166-1**, regroupés en zones **ONU M49** — gratuit, neutre, stable — et
   pas en « développés / émergents », dont les deux fournisseurs sont en désaccord en ce moment.
7. **Les émetteurs et justETF servent à vérifier**, pas à compléter. Et extraETF fournit lui-même
   le lien vers la fiche de l'émetteur, ce qui rend cette vérification facile.

---

## 14. Ce qui a été tranché

Le propriétaire a répondu le **2026-09-27**, et les sept points sont dans
[questions-ouvertes.md](questions-ouvertes.md) sous Q-39 à Q-45, avec leurs décisions D-63 à D-70.

| Question | Retenu |
|---|---|
| **Q-39** La source de calcul | **extraETF**, agrégats seuls. Limite acceptée en connaissance de cause : API interne, usage personnel toléré, échec propre si elle ferme |
| **Q-40** Synthétique : l'indice ou le panier ? | **L'indice suivi**, le fonds étant marqué « synthétique » à l'écran |
| **Q-41** La nomenclature | Les **11 secteurs Morningstar**, nommés comme tels, jamais « GICS » |
| **Q-42** La règle de pays | **Pays d'activité** pour un fonds, **siège social** pour une action en direct, et l'écran dit que les deux cohabitent |
| **Q-43** Les zones | Les **zones d'investisseur**, dans un fichier daté et sourcé. Le découpage neutre de l'ONU est écarté : il met la Chine et le Japon dans la même case |
| **Q-44** Actions en direct et ETF obligataires | Les actions entrent dans **les deux** répartitions ; les ETF obligataires comptent dans une **troisième**, par classe d'actifs, et restent hors des deux autres |
| **Q-45** Un actif qu'on ne peut pas ouvrir | **« Non couvert »**, avec son montant, la répartition marquée partielle. Jamais estimé |

**Un arbitrage rendu contre la recommandation, et il a élargi le projet.** Il était recommandé de ne
**pas** traiter les actions détenues en direct, le propriétaire n'en ayant aucune. Il a répondu
l'inverse : l'application doit viser **l'utilisateur type de Trade Republic**, chez qui l'achat
d'actions à l'unité est courant, puisqu'il compte la partager. C'est devenu
[D-62](decisions.md), une évolution de cap qui dépasse l'étape 7 et vaut pour toutes les suivantes —
y compris la conception de l'interface.

**Ce qui reste à la charge du propriétaire**, et qui est écrit dans le
[cahier de l'étape 7](verification/etape-7.md) : ouvrir la **fiche de l'émetteur** de deux ou trois
de ses ETF et comparer les pays et les secteurs. L'écart attendu n'est **pas nul** — un à trois
points — et le §5 et le §6 disent pourquoi. Pour un ETF synthétique, la comparaison doit porter sur
l'**exposition de l'indice**, et non sur la liste des titres détenus.

---

## 15. Les questions laissées ouvertes

Trois points n'ont pas été tranchés, faute de réponse certaine, et aucun n'est bloquant.

| Point | État |
|---|---|
| Le **sens exact de la date** livrée par la source | Le champ employé parle de l'indice. On affiche la date **et** ce que le champ dit d'elle-même, sans affirmer plus (§3.1) |
| La **couverture des émetteurs absents** (BNP Paribas Easy, Xtrackers) | Non testée sur la source retenue. Un ETF absent sortira des totaux avec son montant : c'est la limite de [D-63](decisions.md), pas un défaut |
| L'**éligibilité PEA des ETF synthétiques** | 🔶 Deux informations de presse se contredisent (note du 24/07/2026 annonçant la fin, renoncement rapporté le 26/08/2026), aucune sur un texte officiel. **Rien n'est codé là-dessus** |

