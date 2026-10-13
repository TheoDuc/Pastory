# Des réglages qui se trouvent seuls — comparatif des sources (étape 8 quater)

L'utilisateur dépose l'export, et c'est tout ([D-80](decisions.md)). Ce document rassemble ce
que la recherche du 2026-10-05 a établi pour trouver **seul** chaque réglage qui manquait, avec la
mesure de fiabilité de chaque source, et ce qui a été retenu ou écarté. Trois agents de recherche
l'ont faite en parallèle, sur des **ISIN publics** ; aucune donnée personnelle n'y figure.

Critères, pour chaque source : gratuite, sans clé, interrogeable par ISIN, valeur **datée**,
conditions d'utilisation qui ne l'interdisent pas, et **fiabilité mesurée** sur un échantillon,
comme le TER de Xetra l'avait été à [D-61](decisions.md).

| Réglage | D'où il vient | Contrôle | Décision |
|---|---|---|---|
| Type d'un actif | l'export (`asset_class`) | une seule classe pour l'actif | [D-82](decisions.md) |
| Cotation (ticker, devise) | recherche Yahoo, par ISIN puis par nom | prix payé, change | [D-85](decisions.md), [D-88](decisions.md) |
| Frais courants (TER) | l'émetteur (Amundi), puis la liste de Xetra | fourchette, date | [D-90](decisions.md) |
| Contenu d'un fonds | extraETF (code et libellé) | code CFI de l'ESMA | [D-89](decisions.md) |
| Source de secours | essayée d'elle-même | — | [D-91](decisions.md) |
| Date d'ouverture du PEA | l'export (mouvements d'espèces du PEA) | aucun titre avant | [D-86](decisions.md), [D-87](decisions.md) |

---

## 1. La cotation : de l'ISIN au ticker

### 1.1 Ce que donne la recherche, mesuré sur 62 ISIN publics

Échantillon : 12 ETF « PEA » et Amundi, 18 ETF UCITS irlandais et luxembourgeois, 3 ETC d'or, 9
actions du CAC 40, 6 allemandes, 4 néerlandaises, 10 titres américains.

| Stratégie | Bon ticker en euros | Faux ticker appliqué | Trou |
|---|---|---|---|
| A — premier résultat de la recherche par ISIN, refusé s'il n'est pas en euros | 33 (53 %) | 0 | 29 |
| B — premier résultat **en euros** de la même liste | 33 | 4 (pseudo-ticker sans cours), sauf à exiger un historique | 29 |
| C — B, puis une recherche **par le nom**, contrôlée par le change | 53 (85 %), 56 (90 %) avec le nom court | 0 | 6 |

- **Les 33 cotations en euros trouvées par l'ISIN sont toutes le bon instrument.** Les échecs de A
  sont des refus de devise : la vérification de [D-48](decisions.md) fonctionne. Ce sont les ETF
  irlandais ou jersiais cotés **à Londres en dollars** (13), des cotations suisses en dollars (3),
  et les titres américains (9).
- **B n'apporte rien** : la liste ne contient presque jamais d'autre cotation en euros, sinon un
  pseudo-ticker de Stuttgart (`<ISIN>.SG`) qui annonce l'euro et un cours du jour, mais **aucun
  historique**.
- **C fonctionne** : relancer la recherche avec le nom du premier résultat ramène les cotations
  en euros de Xetra ou d'Amsterdam. Mais elle mêle les parts d'un même fonds (capitalisante,
  distribuante, couverte), les classes A et C d'une même société, des ETF à levier : un nom ne
  suffit jamais à identifier, il faut un contrôle.
- La recherche rend **sept résultats au plus**, quel que soit le nombre demandé, et l'ordre change
  avec le paramètre de région.
- Quatre ISIN publics sont **absents** de la recherche, même en réessayant (dont un ETC d'or et
  une action américaine de classe A).

### 1.2 Le contrôle par le prix payé

L'export donne, sur chaque achat et chaque vente, le **prix d'exécution** par part. Le cours de
clôture d'une bonne cotation, le même jour, en est proche ; celui d'une mauvaise s'en écarte.

Écart entre un prix pris pendant la séance et la clôture, mesuré sur 250 séances (365 jours pour
les cryptos), en % de la clôture, percentiles 50 / 95 / 99 / max :

| Groupe | (haut − bas) / clôture | pire écart possible pour un ordre |
|---|---|---|
| ETF en euros (15) | 0,84 / 2,26 / 3,45 / 5,91 | 0,73 / 2,15 / 3,17 / 5,71 |
| ETC d'or (2) | 1,26 / 3,74 / 5,68 / 8,12 | 1,11 / 3,25 / 5,74 / 7,96 |
| Actions en euros (10) | 2,06 / 4,57 / 7,23 / 12,71 | 1,65 / 4,16 / 6,66 / 12,99 |
| Actions américaines cotées en euros (8) | 2,28 / 5,16 / 7,08 / 12,76 | 1,83 / 4,79 / 7,03 / 11,15 |
| Cryptos (4) | 3,64 / 9,42 / 17,0 / 55,9 | 2,7 / 7,57 / 13,6 / 35,2 |

En simulant des ordres à une heure tirée au hasard dans la séance, la **médiane sur six ordres**
avec le bon ticker ne dépasse plus 1,2 % (ETF, ETC), 3,3 % (actions), 4,3 % (cryptos). D'où les
tolérances retenues, sur l'écart médian, selon le nombre d'ordres comparés :

| Type | 1–2 ordres | 3–5 ordres | 6 ou plus |
|---|---|---|---|
| ETF (et ETC, que l'export range aussi sous « fonds ») | 6 % | 4 % | 2 % |
| Action | 12 % | 6 % | 4 % |
| Crypto | 20 % | 10 % | 5 % |

**Ce que le contrôle attrape** (écart médian mesuré) : la cotation londonienne en pence
(− 99 %) ; un autre ETF sur le même indice (+ 73 % à + 1 586 %) ; la part couverte au lieu de la
non couverte (+ 182 %) ; une part au prix très éloigné (+ 898 %) ; la cotation en dollars (− 14 %
tant que l'euro vaut environ 1,16 dollar).

**Ce qu'il laisse passer** : deux parts capitalisante et distribuante à prix proches (1,6 à
2,6 %) ; deux classes d'une même société (0,4 %) ; une cotation en dollars ou en francs suisses
les jours où le change est proche de 1 (l'euro est resté à moins de 3 % du dollar 3,4 % des jours
de 2016 à 2026, à moins de 5 % du franc 23,5 % des jours). **La vérification de la devise reste
donc le premier contrôle**, et le contrôle de change sert pour les candidats trouvés par le nom.

### 1.3 Le contrôle de change

Pour un candidat trouvé par le nom, on compare ses clôtures, sur une soixantaine de séances, à
celles de la cotation trouvée par l'ISIN dans une autre monnaie, convertie au taux du jour
(`EURUSD=X`, `EURGBP=X`… ; les pence divisés par cent). Rapport médian mesuré : 1,0002 à 1,0006
pour le bon ETF, 0,998 à 1,0015 pour une action ; **1,020** et **1,033** pour l'autre part d'un
fonds S&P 500 et d'un fonds monde. Tolérance retenue : **1 %**.

### 1.4 Les actions américaines

La recherche par ISIN ne propose aucune cotation en euros d'une action américaine : il faut la
recherche par nom, avec le **nom court** (« Amazon », pas « Amazon.com, Inc. », qui ramène aussi
une autre société). Sur cinq ans, les cotations de Xetra (`.DE`) et de Francfort (`.F`) de neuf
grandes valeurs ont **toutes les séances**, sans trou. Écart au cours américain converti : médiane
nulle ; au 99ᵉ centile, ± 1,5 à 2 % à Francfort (qui cote jusque vers 22 h), ± 2,6 à 4,9 % à Xetra
(qui ferme à 17 h 30). Un titre peu échangé sur Xetra y a des clôtures figées. D'où
[D-88](decisions.md).

**Le nom court n'a été cherché qu'à partir du 2026-10-13.** Jusque-là, le code demandait les
deux noms exacts — celui que la source associe à l'ISIN (« Société, Inc. ») et celui de la
banque (« Société (B) », la classe de l'action) — et ni l'un ni l'autre ne ramène de cotation
en euros pour certaines valeurs : le premier ramène New York et une autre société, le second
rien. Le premier export d'un autre utilisateur l'a montré sur une action américaine très
courante, restée sans cours. La recherche a désormais un **second recours** : les mêmes noms
sans ce qui est entre parenthèses, sans ce qui suit une virgule, sans forme sociale. Il ne
sert que si les noms exacts n'ont rien donné, et chaque candidat passe les deux mêmes
contrôles : le prix payé (§1.2) et le change (§1.3).

### 1.5 Les cryptos, et le jour d'un ordre

`CODE-EUR` existe chez la source pour 18 codes sur 25 relevés ; pour les autres, elle ajoute un
numéro (`UNI7083-EUR`) ou n'a que le dollar : la règle donne alors un **trou**, jamais un faux.
Les bougies des cryptos sont découpées en **temps universel** : le jour d'un ordre se lit alors
dans son horodatage, pas dans la colonne `date` (jour à Paris). 1,8 % des bougies ont une clôture
hors de leur propre fourchette : un contrôle doit garder une marge.

Un ordre passé un jour où la place du candidat ne cote pas (jour férié propre à cette place)
n'est **pas** comparé à la veille, qui ajouterait une séance de bruit. Si aucun ordre ne tombe un
jour coté, la clôture la plus proche à quatre jours près sert, avec la tolérance d'un ordre unique.

---

## 2. Les frais courants (TER)

### 2.1 Le service produit d'Amundi — retenu

- **Requête** : `POST https://www.amundietf.fr/mapi/ProductAPI/getProductsData`, le même service
  que la source de secours ([D-77](decisions.md)), avec seulement
  `"characteristics": ["ISIN", "TER", "TER_EFFECTIVE_DATE"]` — ni répartition, ni lignes
  détenues.
- **Réponse** : `TER` **en pour cent** (`0.2` vaut 0,20 %, alors que les répartitions de ce même
  service sont des fractions) ; `TER_EFFECTIVE_DATE`, la **date d'effet** du taux (lancement ou
  dernier changement) — pas la date du document d'information clé.
- **Couverture** : les 636 fonds du plan du site répondent ; **116** sont déclarés éligibles au
  PEA, tous avec un TER et une date. **54 d'entre eux sont absents de Xetra**, dont les ETF « PEA »
  les plus courants de l'émetteur.
- **Fiabilité** : les 116 documents d'information clés téléchargés et lus ; **116 sur 116
  concordent exactement**. C'est une mesure de cohérence (le service reprend le document du même
  émetteur), pas une vérification indépendante.
- **Contre Xetra** : 402 fonds dans les deux sources, 394 identiques ; les 8 écarts arbitrés au
  document donnent raison à l'émetteur — Xetra en retard sur une baisse (trois cas), une hausse,
  un arrondi à deux décimales là où l'émetteur en donne trois (0,165), et un cas où le service est
  **en avance** sur le document (sa date d'effet est postérieure).
- **Conditions d'utilisation** : aucune clause sur la lecture automatique ; la récupération « pour
  votre usage personnel » est permise. Même cadre que [D-77](decisions.md).

### 2.2 Écartés

- **BNP Paribas Easy** : les frais sont chargés par un composant qui refuse tout client autre
  qu'un navigateur, et ses documents passent par un code interne. Inutile de toute façon : ses ETF
  « PEA » sont **dans** la liste de Xetra.
- **La liste de BlackRock** (JSON par la page « product-list », colonne `onGoingCharges`) : elle
  couvre les ETF iShares « Swap PEA », eux aussi absents de Xetra, et concorde avec le document
  d'information clé sur 3 parts sur 4 ; mais elle n'a **aucune date**, et la part couverte s'en
  écarte (0,20 contre 0,22). Écartée par le propriétaire ([D-90](decisions.md)) : le trou est
  affiché.

### 2.3 Un piège ancien, trouvé en route : le lien de la liste de Xetra

Selon le serveur qui répond, la page de Deutsche Börse écrit le lien du fichier en adresse
**relative** ou **complète**. Le motif de l'étape 6 ne reconnaissait que la première : la liste
manquait **trois fois sur quatre** à certaines heures, avec pour seul signe « lien non trouvé ».
Corrigé, et un test garde les deux écritures. Une source en panne n'est plus gardée en mémoire
comme un trou : la recherche est refaite au lancement suivant.

---

## 3. Le contenu d'un fonds

### 3.1 extraETF, code et libellé — retenu

La réponse détaillée d'extraETF (`api-v2/detail/?isin=`) porte `asset_class_id` **et**
`asset_class_name`, toujours concordants : 2 « Aktien », 3 « Anleihen », 4 « Rohstoffe »,
5 « Geldmarkt », 9 « Portfoliokonzepte », 1160 « Immobilien ». La table des codes n'est publiée
nulle part. Mesuré sur 310 fonds (un échantillon de 30, 24 cas choisis où le code CFI se trompe,
260 tirés au hasard dans la liste de Xetra) : **307 trouvés, aucune erreur franche**. Un cas limite
(un fonds structuré « autocallable », classé en actions) et une frontière floue entre obligations
et monétaire (un fonds de bons du Trésor à 1–3 mois en 3, un fonds de liquidités en 5).

**Pourquoi cela contredit [D-71](decisions.md)**, qui l'avait trouvé « faux sur deux actifs sur
trois » : l'hypothèse la plus probable est que le sens des nombres avait été deviné, décalé d'un
rang (1 actions, 2 obligations, 3 matières premières), ce qui donne exactement deux erreurs sur un
trio actions, obligations, or. Refait sur les fonds du propriétaire, en lisant le libellé : **juste
cinq fois sur cinq**.

**Ne pas confondre** avec la répartition par classes du même service (`asset_allocation_
exposure_list`), qui décrit le panier détenu : un ETC d'or y est « other » à 100 %, un fonds
monétaire à swap « stock » à 99,9 % (son collatéral, le piège de [D-64](decisions.md)).

### 3.2 Le code CFI du registre de l'ESMA — témoin

Requête : `GET https://registers.esma.europa.eu/solr/esma_registers_firds/select` avec
`q=isin:<ISIN>`, `fq=type_s:parent`, et une facette sur `gnr_cfi_code` (les codes reviennent **en
minuscules**). Norme ISO 10962:2021 : pour un fonds coté (`CE…`), la 5ᵉ lettre dit le contenu —
E actions, B dette, C matières premières, L mixte, M autres ; pour un produit structuré (`EY…`,
là où tombent les ETC), la 6ᵉ lettre T dit « matières premières ».

Mesuré sur les 3 574 ISIN de la liste de Xetra : présents à 100 %, mais **30 % muets** (presque tous
les ISIN luxembourgeois portent le code par défaut `CECGMS`, « fermé, capitalisant, autres », faux
en prime), et **une trentaine d'erreurs franches** (un fonds MSCI Europe classé en dette, un fonds
d'emprunts d'État classé en actions). La lettre L couvre surtout des fonds d'actions. 124 ISIN
portent deux codes selon la plateforme. Un code **normé**, donc, mais déclaré sans contrôle : il ne
décide jamais seul ; il transforme chacune de ses erreurs en trou, jamais en chiffre faux.

### 3.3 Écartés

- **La liste de Xetra** : aucune colonne de classe d'actifs. Seul `PRODUCT TYPE = ETC` dit
  « matières premières », et un ETF de matières premières à swap y est typé « ETF ».
- **Le service d'Amundi** (`ASSET_CLASS`) : juste sur ses 415 fonds, mais ne connaît qu'eux ;
  gardé en réserve comme second témoin possible.
- **OpenFIGI** : « Equity / ETP / Mutual Fund » quel que soit le fonds.

---

## 4. Ce que l'export donne lui-même

- **Le type** : `asset_class` (`FUND`, `STOCK`, `CRYPTO`), sur chaque ligne d'actif
  ([D-82](decisions.md)).
- **La date d'ouverture du PEA** : les lignes d'espèces du compte `PEA` — `TRANSFER_IN`
  (versement), `PEA_MARKETING` (prime d'ouverture), `TRANSFER_OUT` (sortie) — lues par leur
  **jour et leur sens seulement** ([D-11](decisions.md)). Le cas du propriétaire, en jours fictifs :
  prime d'ouverture le jour J, sortie et seconde prime à J + 6 (plan fermé puis rouvert), premiers
  versements à J + 15. La date retenue est J + 6 ([D-86](decisions.md)).

---

## 5. Les pièges, à connaître avant de toucher à ce code

1. La recherche par ISIN renvoie **Londres en dollars** pour presque tous les ETF irlandais.
2. Le pseudo-ticker de Stuttgart annonce l'euro et un cours, **sans historique**.
3. La recherche rend sept résultats au plus, et leur ordre dépend de la région.
4. Le type annoncé par la recherche est faux pour un ETC d'or (« EQUITY ») : il n'est jamais lu.
5. Une recherche par nom mêle les parts d'un fonds et les classes d'une société : seul un contrôle
   par le prix ou le change les sépare.
6. Deux cotations du même titre sur deux places diffèrent de quelques dixièmes au hasard des
   heures de clôture : les départager à l'écart, c'est tirer au sort (d'où l'équivalence à 1 point).
7. Le TER d'Amundi est en pour cent, ses répartitions en fractions.
8. `TER_EFFECTIVE_DATE` n'est pas un nom documenté : s'il disparaît, le service l'ignorera sans
   erreur, et le TER, sans date, ne sera plus retenu.
9. La date d'effet d'un TER peut être ancienne sans être périmée : « taux en vigueur depuis le »,
   et non « au ».
10. Le lien de la liste de Xetra s'écrit de deux façons (§2.3).
11. Un nom de caractéristique inconnu est **ignoré sans erreur** par le service d'Amundi.
12. Le code d'extraETF ne se lit qu'avec son libellé (§3.1).
13. Les codes CFI reviennent en minuscules.
14. Une sortie d'espèces du PEA avant cinq ans est une **clôture**, et la sortie qui clôt un plan,
    le jour même d'une réouverture, n'est pas un retrait du plan suivant.
15. Une panne passagère n'est jamais gardée en mémoire comme un trou.

La relecture indépendante de l'étape a trouvé dix défauts, tous corrigés et gardés par un test ;
quatre méritent d'être retenus :

16. **Une panne ne doit jamais ressembler à « rien trouvé ».** Une recherche ou une série qui
    échoue faute de réseau remonte comme une panne, et rien n'est gardé ; seule une réponse de la
    source (« inconnu », « autre devise », « aucun cours ») écarte un candidat.
17. **Une cotation qui change ne mêle jamais deux places.** Le cache des cours est tenu par actif :
    un cours pris sur une autre cotation que celle retenue n'est jamais employé, et, en ligne, il
    est oublié et la série reprise à la source.
18. **L'export d'un tiers ne fait aucun appel réseau**, ni recherche, ni cours, ni composition :
    depuis que le type vient de la banque et que le secours s'essaie seul, chacun de ses ISIN
    serait sinon parti vers une source.
20. **Un nom simplifié ne sert qu'à demander des candidats** : c'est un texte, donc jamais une
    preuve (règle 4). Une société au nom voisin qui coterait par hasard au prix payé est
    écartée par le contrôle de change, et un test le garde.
19. **Une valeur connue survit à une panne** : un TER ou un contenu périmé reste servi tant que sa
    source ne répond pas ; et quand la source de confiance est en panne, la valeur de repli n'est
    pas gardée pour un mois.

---

## 6. Le critère de l'étape : combien de valeurs ne se trouvent pas ?

Sur le portefeuille du propriétaire (cinq fonds et une crypto, un PEA), sans aucune correction :
**22 valeurs trouvées seules, 1 introuvable** — les frais courants d'un ETF iShares « Swap PEA »,
dont la seule source n'a pas de date ([D-90](decisions.md)). Toutes les valeurs qu'il avait
validées à la main sont retrouvées à l'identique ; la date d'ouverture du PEA l'est depuis
[D-86](decisions.md).

Sur un portefeuille type, les trous qui restent sont connus et dits à l'écran :

| Trou | Pourquoi | Ce que l'écran dit |
|---|---|---|
| TER d'un ETF absent de Xetra et dont l'émetteur ne publie rien de daté (iShares PEA, petits émetteurs) | aucune source datée | « frais courants introuvables », le reste est compté |
| Cotation d'un actif sans ordre (titres reçus seulement) et inconnu de la recherche par ISIN | rien pour contrôler | « aucun achat ni aucune vente ne donne un prix payé » |
| Cotation d'une crypto que la source nomme autrement | `CODE-EUR` n'existe pas | « la recherche ne connaît aucune cotation » |
| Contenu d'un fonds monétaire, multi-actifs ou immobilier | non traduit ([Q-60](questions-ouvertes.md)) | la classe annoncée est nommée |
| Date d'un PEA plus ancien que les exports, ou transféré | invisible dans le fichier | « le plan est plus ancien que vos exports » |
