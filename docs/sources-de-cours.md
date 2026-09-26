# Sources de cours — comparatif

Le comparatif que [D-18](decisions.md) réclame avant d'écrire une ligne de code : quelles sources
gratuites peuvent donner les **cours de marché** de ce portefeuille, ce qu'elles couvrent vraiment,
et ce qu'elles coûtent en fragilité. **C'est au propriétaire de choisir** ; la dernière section dit
ce qu'il a tranché le 2026-09-26 ([D-48](decisions.md) à [D-50](decisions.md)) et ce qui reste
ouvert.

> **État des vérifications.** Les points marqués ✅ ont été **testés en direct le 2026-09-26**
> (appel réel au service, réponse lue). Les points marqués 📄 viennent de la documentation ou de la
> presse spécialisée, sans essai. Les points marqués 🔶 n'ont pas pu être vérifiés : la session de
> recherche a été coupée en cours de route (voir la dernière section).
>
> **Aucune valeur du portefeuille n'apparaît ici.** Les ISIN cités sont des identifiants publics
> employés comme cas de test pendant la recherche, sans lien avec les actifs détenus
> ([D-03](decisions.md)).

---

## 1. Ce qu'on demande à une source

Sept critères, dans l'ordre d'importance pour ce projet :

| # | Critère | Pourquoi il compte ici |
|---|---|---|
| 1 | **Gratuite** | [D-18](decisions.md) et [D-28](decisions.md) |
| 2 | **Cours de clôture historiques, par jour** | Sans historique, pas de [D-15](decisions.md) (les titres reçus sans prix), pas de valeur dans le temps, donc pas d'étape 5 |
| 3 | **ETF UCITS européens** cotés à Xetra et Euronext Paris | C'est le cœur d'un portefeuille PEA/CTO |
| 4 | **Actions européennes** | Idem |
| 5 | **Crypto en euros** | La poche crypto ([D-16](decisions.md)) |
| 6 | **Cours brut, non retraité des dividendes** | [D-21](decisions.md) et [D-29](decisions.md) : le moteur compte les dividendes lui-même. Une source qui les réinjecte dans le cours les compterait **deux fois** |
| 7 | **Pérenne et vérifiable à la main** | Le propriétaire doit pouvoir comparer un cours avec son application, à une date donnée |

**Et un obstacle transversal :** Trade Republic identifie chaque actif par son **ISIN**, alors que
presque toutes les sources gratuites travaillent au **ticker** + place de cotation. Le §4 lui est
consacré : c'est le vrai point délicat de l'étape.

---

## 2. Le verdict en une page

| Source | Gratuite | ETF européens | Actions | Crypto € | Historique | Cours brut | Verdict |
|---|---|---|---|---|---|---|---|
| **Yahoo Finance** (`yfinance` ou point d'accès direct) | oui | ✅ Xetra, Paris, Milan, Amsterdam, Londres | ✅ | ✅ | ✅ depuis 2009 en quotidien | ✅ **si on le demande** (§7) | **Recommandée** |
| **LS Exchange** (`ls-tc.de`) | oui | ✅ | ✅ | non | ✅ ~10 ans en quotidien | 📄 à confirmer | **Deuxième avis utile**, pas source principale |
| **Alpha Vantage** | clé gratuite | 📄 oui (`.DE`, `.PA`) | 📄 oui | 📄 oui | ⚠️ **100 jours seulement** en gratuit | ✅ brut par construction | Écartée (§3) |
| **Börse Frankfurt** (`bf4py`) | oui | 📄 oui | 📄 oui | non | 📄 oui | 📄 réglable | Écartée (§3) |
| **Euronext** (`live.euronext.com`) | oui | 📄 oui (Paris) | 📄 oui | non | 📄 oui, export CSV | 📄 « Adjusted / Non-Adjusted » | Écartée (§3) |
| **Stooq** | oui | — | — | — | — | non (déjà retraité) | **Morte** ✅ (§3) |
| **Twelve Data**, **Finnhub** | clé gratuite | ❌ payant | ❌ payant | oui | — | — | Écartées (§3) |
| **EODHD** | clé gratuite | ⚠️ 20 appels/jour, 1 an | idem | non | ⚠️ 1 an | ✅ `close` et `adjusted_close` | Utile **seulement** pour l'ISIN (§4) |
| **Marketstack** | clé gratuite | 📄 oui | 📄 oui | non | ⚠️ 1 an, 100–1 000 appels/mois | ✅ les deux | Écartée (§3) |
| **pytr** (Trade Republic) | oui | ✅ | ✅ | ✅ | ✅ | 📄 | **Écartée, et pas pour une raison technique** (§6) |
| **CoinGecko** | clé gratuite | — | — | ✅ | ⚠️ **365 jours** en gratuit | ✅ | Crypto : d'appoint (§5) |
| **Kraken**, **Binance**, **Bitstamp** | oui, sans clé | — | — | ✅ | ✅ (avec pagination) | ✅ | Crypto : solides (§5) |
| **CryptoCompare / CoinDesk Data** | **non** | — | — | — | — | — | **Palier gratuit supprimé en mai 2026** 📄 |

---

## 3. Les sources écartées, et pourquoi

**Stooq — morte pour un programme.** ✅ Vérifié : l'adresse de téléchargement CSV ne renvoie plus
les données mais une page qui exige JavaScript pour « vérifier le navigateur ». Et
`pandas-datareader` 0.11.0 (juin 2026) a **supprimé** ses lecteurs Stooq, Yahoo, Tiingo et
quelques autres, « qui dépendaient d'API tierces disparues ou très abîmées ». Cette bibliothèque,
souvent citée comme la voie propre, ne sert donc plus à rien ici.

**Alpha Vantage — l'historique complet est payant.** 📄 La clé gratuite donne 25 requêtes par jour,
ce qui suffirait largement avec un cache. Mais `TIME_SERIES_DAILY` ne renvoie en gratuit que
l'option *compact* : **les 100 derniers jours**. L'historique complet (`outputsize=full`) demande
un abonnement. Or c'est précisément l'historique qu'on cherche.

**Twelve Data — l'Europe est payante.** 📄 Le plan gratuit couvre « les actions et ETF américains,
le forex et la crypto ». Xetra et Euronext demandent un plan payant (à partir de 29 $/mois). Le
paramètre `isin` existe, mais pas sur le plan gratuit.

**Finnhub — l'international est payant.** 📄 60 appels/minute en gratuit, ce qui est généreux, mais
« les données internationales sont premium », et l'historique (`/stock/candle`) renvoie une erreur
d'accès sur une clé gratuite.

**EODHD et Marketstack — un an d'historique, et presque pas d'appels.** 📄 EODHD : 20 appels/jour,
« l'année passée uniquement ». Marketstack : 100 requêtes/mois d'après la page produit, 1 000
d'après la FAQ (les deux chiffres se contredisent), 12 mois d'historique, usage non commercial.
Trop court dans les deux cas. EODHD garde pourtant un intérêt : son point d'accès de recherche
accepte un ISIN et renvoie la **devise** et la **place** (§4).

**Börse Frankfurt — un cadenas qu'il faut rouvrir à chaque fois.** ✅ Le point d'accès
`api.boerse-frankfurt.de` n'est pas documenté et réclame trois en-têtes calculés :
`client-date`, `x-client-traceid` (empreinte MD5 de l'horodatage + l'adresse + un **sel**) et
`x-security` (empreinte MD5 de la minute courante). Le sel est **extrait par expression régulière
du fichier JavaScript du site**, et la bourse le change à chaque reconstruction du site : la
requête tombe alors en 401. C'est une dépendance qui se casse sans prévenir, pour une donnée qu'on
obtient ailleurs.

**Euronext — une page qui charge en JavaScript.** ✅ La page d'historique existe et propose bien un
export CSV avec un choix « Adjusted / Non-Adjusted », mais elle se contente d'afficher
« Loading… Please wait » : les données arrivent par un second appel. Les *Web Services* officiels,
eux, se souscrivent par formulaire de contact — donc payants ou sous contrat.

**Tradegate BSX — pas d'historique.** ✅ La page d'un instrument s'affiche, en euros, avec
« Bid / Ask / Last / High / Low / Volume » et la mention « Trading Currency: EUR ». Mais **aucun
accès aux cours passés**, ni téléchargement. À noter au passage : Tradegate Exchange et la Börse
Berlin ont fusionné le 1ᵉʳ janvier 2026 sous le nom **Tradegate BSX**, et `tradegate.de` redirige
désormais vers `tradegatebsx.com` 📄.

---

## 4. Le point délicat : de l'ISIN au ticker

Quatre voies ont été examinées. Aucune n'est parfaite, et c'est pour cela que **la correspondance
doit rester un fichier que le propriétaire peut relire et corriger** — comme l'annonce déjà
[architecture.md §11](architecture.md).

### (a) La recherche de Yahoo — simple, mais elle choisit pour vous
✅ Testée sur six ISIN publics. Elle répond **une seule ligne** dans presque tous les cas, et
c'est presque toujours la bonne place :

| ISIN de test (valeur publique) | Réponse de Yahoo | Place | Devise |
|---|---|---|---|
| Action allemande | `SAP.DE` | Xetra | EUR ✅ |
| Action française | `TTE.PA` | Paris | EUR ✅ |
| Action néerlandaise | `INGA.AS` | Amsterdam | EUR ✅ |
| ETF monde synthétique | `CW8.PA` | Paris | EUR ✅ |
| ETF S&P 500 | `CSSPX.MI` | Milan | EUR ✅ |
| **ETF monde physique** | **`IWDA.L`** | **Londres** | **USD** ⚠️ |

La dernière ligne est tout le problème : pour cet ETF, Yahoo renvoie la cotation **londonienne en
dollars**, alors que le même ETF se négocie à Xetra en euros (`EUNL.DE`, ✅ vérifié : 
`"currency":"EUR"`, `"fullExchangeName":"XETRA"`). Une correspondance automatique acceptée sans
regarder donnerait donc, pour cet actif, **une valeur en dollars présentée comme des euros** —
exactement le genre de chiffre crédible et faux que [D-45](decisions.md) interdit.

**Conséquence pour le code :** la devise renvoyée par la source doit être **vérifiée à chaque
appel**, et un cours dont la devise n'est pas l'euro doit être **refusé et signalé**, jamais
utilisé. C'est le garde-fou principal de cette étape.

### (b) OpenFIGI — gratuit, officiel, et inutilisable seul
✅ Testé en direct. Sans clé : 25 requêtes/minute, 10 demandes par requête ; avec clé gratuite :
25 toutes les 6 secondes, 100 demandes (les en-têtes de limitation l'ont confirmé). `ID_ISIN` est
accepté en entrée. Deux obstacles :

1. un seul ISIN renvoie **193 lignes** (tickers `EUNL`, `IWDA`, `SWDA`, `IWDA1`, `SWDACHF`… sur
   des dizaines de places). Rien ne dit laquelle est la bonne ;
2. les codes de place d'OpenFIGI ne sont **pas** ceux de Yahoo : `LN` pour Londres là où Yahoo
   veut `.L`, `PW` pour Varsovie là où Yahoo veut `.WA`. Il faudrait écrire et entretenir une
   table de traduction — un projet à elle seule.

Le filtre `micCode` réduit bien le bruit (`XETR` → une seule ligne ✅), mais il faut alors déjà
savoir quelle place on veut.

### (c) ESMA FIRDS — la source officielle, et la plus lourde
✅ L'index des fichiers répond (une requête a listé 113 fichiers publiés sur une semaine). C'est
**la** référence européenne : par ISIN, elle donne le nom, la devise de cotation et **chaque place
de négociation** (code MIC). Mais les fichiers sont des archives XML de plusieurs centaines de
mégaoctets publiées chaque semaine 📄, et elles ne contiennent **aucun ticker**. Utile un jour pour
*vérifier* une correspondance ; disproportionné pour l'établir.

### (d) justETF — riche, mais du grattage de page
📄 La bibliothèque `justetf-scraping` (MIT, active en janvier 2026) donne les cotations par ISIN,
tickers compris, et des cours historiques. Mais elle dépend de la structure des pages de justETF,
qui n'offre aucune interface publique stable. Le fichier des conditions d'utilisation est
introuvable (404 ✅) ; `robots.txt` autorise l'essentiel du site 🔶. À garder en réserve pour
l'étape 6 (TER, composition), pas pour les cours.

### Ce que cela donne
**Yahoo pour proposer, le propriétaire pour valider.** Un fichier de correspondance
`ISIN → ticker + devise attendue`, pré-rempli par la recherche Yahoo, relu par le propriétaire,
et corrigeable ligne par ligne. Tout ISIN sans correspondance validée n'est pas valorisé : il est
**affiché comme non valorisé**, jamais estimé.

---

## 5. La crypto

**Bonne nouvelle : le code `XF` de Trade Republic se décode.** 📄 Des sources extérieures au
portefeuille confirment le motif `XF000` + abréviation + 4 chiffres, avec plusieurs exemples
publics concordants (Bitcoin `XF000BTC0017`, Ethereum `XF000ETH0019`, Solana `XF000SOL0012`,
XRP `XF000XRP0018`). [L'inventaire §8](inventaire-donnees.md) notait que la règle n'était vérifiée
que sur **un seul** code, dans les deux exports disponibles (Q-12). Elle reste une déduction, mais
elle est maintenant corroborée en dehors des données du propriétaire : **l'abréviation lisible dans
le code donne la crypto**, donc le couple à interroger (par exemple `BTC-EUR`).

Reste que cette lecture repose sur un texte, ce que la [règle 4](../CLAUDE.md) demande d'isoler et
de signaler. Elle doit rester dans le fichier de correspondance du §4, visible et corrigeable.

| Source | Clé | Historique | Limites | Remarque |
|---|---|---|---|---|
| **Yahoo** (`BTC-EUR`) | non | 📄 profond | celles de Yahoo (§7) | **Une seule source pour tout le portefeuille** |
| **Kraken** OHLC public | non | ✅ 720 bougies par appel, soit ~2 ans en quotidien ; au-delà, l'API refuse | 1 appel/seconde | Kraken publie aussi **tout l'historique en CSV** 📄, mais en morceaux de ~2 Go : bon pour une amorce unique, pas pour un usage courant |
| **Binance** klines | non | 📄 1 000 bougies/appel, paginables sans limite de profondeur | — | `BTCEUR` disponible |
| **Bitstamp** OHLC | non | 📄 1 000 bougies/appel | — | Pair `btceur` |
| **CoinGecko** | clé gratuite | ⚠️ **365 jours** sur le plan Demo ; 2 ans à 29–35 $/mois | 10 000 appels/mois, 100/min | Écarté comme source principale à cause des 365 jours |
| **CoinPaprika** | non | 📄 historique en EUR | ~25 000 appels/mois | Solution de repli honorable |

**Recommandation :** la même source que le reste (Yahoo), pour n'avoir qu'un seul mécanisme, un
seul cache et un seul mode de panne. Kraken ou Binance en second avis si un cours crypto paraît
faux.

---

## 6. L'option pytr : techniquement possible, et pourtant écartée

pytr sait demander des cours : ✅ son code expose `ticker(isin, exchange="LSX")`,
`performance_history(isin, timeframe, …)` (type `aggregateHistory`), `instrument_details(isin)`.
Par ISIN directement — la correspondance du §4 disparaîtrait. C'est séduisant. Trois raisons de ne
pas le faire, dont une qui suffit :

1. **Les conditions générales de Trade Republic l'interdisent.** 📄 « L'utilisation de voies
   d'accès, de programmes et/ou d'autres interfaces non fournis par Trade Republic en dehors de
   l'application est interdite », avec **droit de résiliation extraordinaire** en cas de
   manquement. La formulation exacte et le numéro d'article n'ont pas pu être relevés dans le
   contrat lui-même 🔶 (le PDF n'était pas lisible et la vérification a été coupée), mais la clause
   est rapportée de façon concordante. Elle vise l'usage de pytr **en général**, y compris pour
   l'export d'événements dont ce projet dépend déjà. Le propriétaire a tranché en connaissance de
   ce risque : [D-49](decisions.md).
2. **Chaque appel est une connexion complète** ([D-41](decisions.md), [D-46](decisions.md)) :
   numéro, PIN, confirmation dans l'application. Un tableau de bord qui s'ouvre doit pouvoir
   afficher une valeur **sans rien demander** ; les cours doivent venir du cache.
3. **La place par défaut n'est plus la bonne.** 📄 En juillet 2026, Trade Republic a cessé de
   router ses ordres vers la **LS Exchange** pour les exécuter lui-même comme teneur de marché ou
   les envoyer ailleurs. Le `exchange="LSX"` de pytr, et le point d'accès `ls-tc.de` du §2, ne
   pointent donc plus forcément vers le lieu où les ordres du propriétaire sont exécutés.

Le troisième point vaut pour **toute** source : le cours de clôture de Xetra ne sera pas au
centime près celui que l'application Trade Republic affiche. Il faudra le dire dans l'interface.

---

## 7. Les pièges vérifiés, à ne pas oublier en codant

Cinq points établis en direct, que le code devra traiter explicitement. Ce sont eux qui
transforment « on prend Yahoo » en travail d'ingénieur.

1. **Le cours par défaut est retraité des dividendes — il ne faut pas de celui-là.** ✅ Sur une
   action qui distribue, le premier point d'une série d'un an donne un cours de clôture de 53,38
   contre 50,54 pour le cours « ajusté » : plus de 5 % d'écart, qui s'efface à mesure qu'on
   approche d'aujourd'hui. `yfinance` a basculé son défaut `auto_adjust` de `False` à `True` en
   cours de route 📄 : le dividende est donc **réinjecté dans le cours**, et comme le moteur compte
   déjà les dividendes ([D-29](decisions.md)), ils seraient comptés deux fois. **Il faut le cours
   brut**, explicitement (`auto_adjust=False`, ou le champ `close` du point d'accès direct, pas
   `adjclose`). Sur un ETF capitalisant, les deux séries sont identiques ✅ — ce qui rend l'erreur
   invisible tant qu'on ne détient rien de distribuant.
2. **Demander « tout l'historique » donne du mensuel.** ✅ Une plage `max` renvoie **205 points**
   depuis 2009 (un par mois) ; la **même** période demandée par dates explicites en renvoie
   **4 316** (un par jour ouvré). Le champ qui annonce la granularité dit `1d` **dans les deux
   cas**. Il faut donc toujours borner par dates, et vérifier le nombre de points obtenus.
3. **Des trous existent.** ✅ Sur 4 316 jours, 3 cours de clôture sont vides. Un jour sans cours
   n'est pas une erreur : c'est un jour férié, une suspension, ou un trou. Le moteur devra
   remonter au dernier jour coté **et le dire**, jamais interpoler.
4. **La devise n'est pas garantie** (§4). À vérifier à chaque appel.
5. **La source peut se fermer.** 📄 Yahoo n'a pas d'interface officielle depuis 2017 ; les
   limitations de débit (« 429 Too Many Requests ») reviennent régulièrement, et les conditions
   d'utilisation parlent d'un « usage personnel ». D'où le **cache local** : une fois un cours de
   clôture écrit, il n'a plus à être redemandé. Un jour passé ne change plus.

---

## 8. Recommandation

**Yahoo Finance comme source unique**, en cours brut, derrière l'interface `donnees_externes/`
que le moteur connaît déjà (`cours(actif, date)`), avec :

- **un fichier de correspondance** `ISIN → ticker + devise attendue`, pré-rempli automatiquement,
  **relu et corrigeable par le propriétaire**, et une ligne par actif — y compris les cryptos ;
- **un refus explicite** plutôt qu'une estimation : pas de correspondance validée, devise
  inattendue, ou aucun cours à la date demandée ⇒ l'actif est affiché **non valorisé**, avec la
  raison ([D-45](decisions.md)) ;
- **un cache local daté**, qui rend l'ouverture du tableau de bord indépendante du réseau et
  protège des limitations de débit ;
- **la LS Exchange (`ls-tc.de`) comme deuxième avis** ponctuel quand un cours semble faux — pas
  comme source de production.

Ce qui suit immédiatement, et que [prompt-session-suivante.md](prompt-session-suivante.md) annonce
comme le premier branchement : les **titres reçus sans prix** ([D-15](decisions.md)), dont le
`montant_brut` est `a_completer`. Un cours du jour d'apparition suffit à leur rendre un capital
investi et un prix de revient.

---

## 9. Ce qui a été tranché, et ce qui reste ouvert

**Tranché le 2026-09-26 par le propriétaire** (Q-27, Q-28, Q-29, lot 3 de
[questions-ouvertes.md](questions-ouvertes.md)) :

| Décision | Ce qui s'applique désormais |
|---|---|
| [D-48](decisions.md) | Le cours de référence est celui du **marché principal en euros**. La devise attendue est déclarée par actif ; un cours dans une autre devise est **refusé et signalé**. L'écart de quelques centimes avec l'application Trade Republic est assumé, et la place de chaque cours reste visible |
| [D-49](decisions.md) | **pytr reste l'unique porte d'entrée**, en connaissance de la clause des conditions générales, et **aucun cours ne passe par Trade Republic** — ni son point d'accès, ni la LS Exchange en production |
| [D-50](decisions.md) | Un cours en cache est **définitif** ; une commande explicite vide le cache d'un actif, ce qui traite les corrections de la source et les *splits* |

**Et trois vérifications inachevées**, à reprendre quand une recherche en ligne sera possible :

- 🔶 la clause exacte des conditions générales de Trade Republic (numéro d'article, texte) ;
- 🔶 les conditions d'utilisation de justETF (page introuvable) et de Börse Frankfurt ;
- 🔶 la confirmation du motif `XF` sur un export contenant plusieurs cryptos (Q-12), qui ne peut
  venir que de vraies données.

---

*Recherche menée le 2026-09-26 sur 134 requêtes web, dont les résultats ont été dépouillés
localement. La session de recherche a été interrompue par l'antivirus de la machine avant ses
dernières vérifications ; les points concernés sont marqués 🔶.*
