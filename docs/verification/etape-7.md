# Cahier de vérification — étape 7 : la diversification

Les étapes précédentes répondaient à « combien j'ai ? », « combien ça a rapporté ? » et « ce que ça
coûte ». **L'étape 7 répond à une question de nature différente** : *où* est mon argent ? Dans quels
pays, dans quels secteurs, dans quelles classes d'actifs — en regardant **à l'intérieur** des ETF
([Q-22](../questions-ouvertes.md), [D-28](../decisions.md)).

Trois répartitions, dans cet ordre ([D-68](../decisions.md)) :

1. **par classe d'actifs** : actions, obligations, liquidités ;
2. **par pays**, regroupés en zones ([D-67](../decisions.md)) ;
3. **par secteur**, sur les 11 secteurs Morningstar ([D-65](../decisions.md)).

Deux parties, comme aux cahiers précédents :

1. **les cas fictifs de la partie A**, à refaire sur papier ou à la calculatrice ;
2. **tes vrais chiffres** (partie B), et ce que **toi seul** peux vérifier.

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à toi
vont dans `etape-7.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## La chose à comprendre avant tout le reste

**Une répartition géographique n'est pas une mesure, c'est une convention.** Ce n'est pas une
faiblesse de l'application : c'est la nature de la donnée. BlackRock l'écrit dans ses propres
fiches — son exposition géographique se rapporte « principalement » au pays de domiciliation de
l'émetteur, « mais, dans certains cas, elle peut refléter le lieu où l'émetteur réalise l'essentiel
de son activité ».

Conséquence pratique, et il faut la garder en tête pendant toute la partie B : **si tu compares les
chiffres de l'application à la fiche d'un émetteur ou à un autre site, tu trouveras des écarts de
l'ordre d'un à trois points, et ce ne sera pas une erreur.** Mesuré pendant la recherche, sur le
même fonds à la même date d'arrêté :

| | Site A | Site B | Écart |
|---|---|---|---|
| États-Unis | 70,00 % | 72,04 % | 2,04 points |
| Irlande | 1,41 % | 0,17 % | facteur 8 |
| Technologie | 35,71 % | 30,61 % | 5,10 points |

Les causes sont connues et identifiées : le pays de **domiciliation juridique** contre le pays
**d'activité** (Accenture est irlandaise sur le papier, américaine en pratique), et deux sociétés —
Alphabet et Meta — qui changent de secteur selon la nomenclature.

**Ce que l'application garantit**, en revanche, et ce que tu peux vraiment vérifier :

- **une seule source par graphique**, nommée à l'écran, jamais un mélange ;
- **une seule nomenclature**, nommée à l'écran (« Morningstar », jamais « GICS ») ;
- **rien n'est jamais ramené à 100 %** : ce qui n'est pas attribué reste visible ;
- **la somme des montants d'un fichier CSV vaut exactement la valeur de tes actifs**. C'est le
  contrôle le plus fort du cahier, et c'est le B.3.

---

## Le piège que cette étape désamorce, et qu'il faut connaître

**Un ETF synthétique ne détient pas son indice.** Il détient un panier d'actions et un contrat
d'échange qui lui rend la performance de l'indice. Tout ETF « PEA » sur un indice non européen est
synthétique **par construction** : il doit détenir au moins 75 % de titres européens tout en suivant
un indice américain ou mondial.

Relevé en direct le 2026-09-27 sur un ETF *MSCI World* à swap éligible au PEA :

| Pays | Le panier qu'il détient | L'indice qu'il suit |
|---|---|---|
| Allemagne | **38,5 %** | 2,1 % |
| Pays-Bas | 17,2 % | 1,4 % |
| États-Unis | 15,6 % | **72,9 %** |
| Japon | absent | 5,8 % |

Ses lignes réelles sont Airbus, ASML, Deutsche Telekom, Siemens Energy — pour un fonds **monde**.

**L'application affiche l'indice** ([D-64](../decisions.md)), parce que c'est ton exposition
économique réelle, et elle marque le fonds « synthétique » à l'écran. **Donc si tu ouvres la fiche
de l'émetteur et que tu regardes la liste des titres détenus, tu ne verras pas du tout la même
chose. C'est normal, et c'est même le but.** Sur la fiche, compare la section « exposition
géographique » ou « composition de l'indice », pas la liste des lignes.

---

## A. Cas fictifs, à refaire à la main

Toutes les compositions et toutes les valeurs sont inventées. Chaque cas est aussi un test du
programme : si un chiffre du cahier changeait, un test tomberait.

### A.1 — La mécanique de base : un poids, c'est une multiplication

Un seul ETF, 10 parts à 100,00 € = **1 000,00 €**. Sa composition annonce :

| Pays | Poids annoncé |
|---|---|
| États-Unis | 60 % |
| France | 30 % |
| Japon | 10 % |

Le calcul, pays par pays :

```
États-Unis = 1 000,00 × 60 / 100 = 600,00 €
France     = 1 000,00 × 30 / 100 = 300,00 €
Japon      = 1 000,00 × 10 / 100 = 100,00 €
                                 ----------
                                  1 000,00 €
```

Et les zones, qui ne sont qu'un regroupement de ces mêmes montants :

| Zone | Montant | Part |
|---|---|---|
| Amérique du Nord | 600,00 € | 60,00 % |
| Europe développée | 300,00 € | 30,00 % |
| Japon | 100,00 € | 10,00 % |

**Ce que donne le programme :** exactement ces chiffres.

### A.2 — Ce qui n'est pas attribué reste visible ⚠️

Le cas le plus important du cahier, parce que c'est celui où un autre outil mentirait.

Même ETF, 1 000,00 €, mais sa composition n'attribue que **90 %** de ses pays — le cas réel :
aucune composition ne somme à 100 % (mesuré de 98,56 % à 99,96 % selon le fonds).

| Pays | Poids annoncé |
|---|---|
| États-Unis | 70 % |
| Allemagne | 20 % |
| *rien* | *10 %* |

```
États-Unis    = 1 000,00 × 70 / 100 = 700,00 €   →  70,00 % du portefeuille
Allemagne     = 1 000,00 × 20 / 100 = 200,00 €   →  20,00 %
Non attribué  = 1 000,00 − 900,00   = 100,00 €   →  10,00 %
                                     ----------
                                      1 000,00 €
```

**Ce qu'un outil malhonnête afficherait :** États-Unis 77,8 %, Allemagne 22,2 %, total 100 %. C'est
ce qu'on obtient en ramenant 70 et 20 à un total de 90. Les deux chiffres seraient **faux**, et
rien ne le dirait.

**Ce que donne le programme :** 70,00 %, 20,00 %, et une ligne « Non attribué par la source »
à 10,00 %. **Le total ne fait pas 100 %, et c'est voulu** ([D-69](../decisions.md)).

### A.3 — Un ETF obligataire n'a pas de secteur, et ce n'est pas un manque

Portefeuille : 1 000,00 € d'ETF d'actions (comme en A.1) et 500,00 € d'ETF obligataire.
Valeur totale : **1 500,00 €**.

L'ETF obligataire annonce 100 % d'obligations, et aucun pays ni secteur d'actions. C'est normal :
pour un indice obligataire, « secteur » veut dire Trésor, entreprises ou titrisé, et « pays » peut
même vouloir dire **devise d'émission**.

**Par classe d'actifs :**

| Poste | Montant | Part |
|---|---|---|
| Actions | 1 000,00 € | 66,67 % |
| Obligations | 500,00 € | 33,33 % |

**Par pays :** les 500 € d'obligataire sortent, sous le libellé « Obligations, liquidités et
autres ».

| Poste | Montant | Part |
|---|---|---|
| États-Unis | 600,00 € | 40,00 % |
| France | 300,00 € | 20,00 % |
| Japon | 100,00 € | 6,67 % |
| Obligations, liquidités et autres | 500,00 € | 33,33 % |

**À remarquer :** les États-Unis passent de 60,00 % (en A.1) à **40,00 %**. Le montant n'a pas
changé — 600 € — mais le portefeuille est plus grand. C'est bien la part du **portefeuille entier**
qui est affichée, jamais la part de la seule poche actions.

### A.4 — Un fonds mixte : la part actions est isolée

Un seul fonds, 1 000,00 €, qui annonce 60 % d'actions et 40 % d'obligations, et une répartition
géographique de 60 % d'États-Unis.

```
part actions   = 1 000,00 × 60 / 100 = 600,00 €
États-Unis     = 1 000,00 × 60 / 100 = 600,00 €
hors périmètre = 1 000,00 − 600,00   = 400,00 €   (la part obligataire)
non attribué   = 600,00 − 600,00     =   0,00 €
```

La part actions est **entièrement** attribuée : il n'y a pas de « non attribué ». Le calcul
distingue donc bien deux choses différentes — ce qui **n'entre pas** dans la géographie (les
obligations) et ce que la source **n'a pas attribué** (rien, ici).

### A.5 — La crypto est à part, dans les trois répartitions

Portefeuille : 1 000,00 € d'ETF d'actions et 200,00 € de crypto. Valeur totale : **1 200,00 €**.

| Poste | Montant | Part |
|---|---|---|
| États-Unis | 600,00 € | 50,00 % |
| France | 300,00 € | 25,00 % |
| Japon | 100,00 € | 8,33 % |
| Actifs numériques, ni pays ni secteur | 200,00 € | 16,67 % |

**La crypto n'est ni « non couverte » ni rangée dans un secteur « technologie ».** Elle a sa ligne,
dans les trois répartitions, y compris celle des classes d'actifs — un actif numérique n'est ni une
action, ni une obligation, ni une liquidité de fonds. Le libellé le dit en clair, pour qu'on ne
croie pas à un oubli du programme.

### A.6 — Un actif dont la composition est inconnue

Portefeuille : 1 000,00 € d'ETF connu, 300,00 € d'un actif dont aucune source ne donne la
composition. Valeur totale : **1 300,00 €**.

| Poste | Montant | Part |
|---|---|---|
| États-Unis | 600,00 € | 46,15 % |
| France | 300,00 € | 23,08 % |
| Japon | 100,00 € | 7,69 % |
| Non couvert : composition inconnue | 300,00 € | 23,08 % |

La répartition est marquée **partielle**, l'actif est **nommé**, et le rapport dit qu'on peut le
déclarer à la main dans `actifs.toml`. **Rien n'est estimé à sa place** ([D-69](../decisions.md)).

### A.7 — Un code que le référentiel ne connaît pas

Si une source renvoie un jour un code de pays inconnu — disons `ZZ` — le programme **ne le jette
pas** et **ne le range pas** dans « autres ». Il l'affiche tel quel, avec la mention « code non
reconnu », dans une zone appelée « Zone non renseignee ».

C'est la règle 5 de `CLAUDE.md` appliquée aux codes : un type inconnu n'est jamais ignoré ni classé
par défaut. Un euro reste un euro, et il reste visible.

### A.8 — Ce que le programme refuse d'utiliser

Puisque tu as choisi la mise à jour **automatique**, plus personne ne relit entre la source et
l'écran. Cinq contrôles remplacent cette relecture, et **aucun ne corrige** : ils refusent, et la
composition est alors traitée comme absente (cas A.6).

| Ce qui arrive | Ce que fait le programme |
|---|---|
| Une composition **sans date** | Refusée : une répartition qu'on ne peut pas dater n'est pas vérifiable |
| Un total de poids **au-delà de 105 %** | Refusé : ce ne sont pas des pourcentages, ou une ligne est comptée deux fois |
| Un total de **101,5 %** | **Accepté** : le prêt de titres fait légitimement dépasser 100 % |
| Un code pays qui n'est pas un code ISO (« Welt ») | Refusé : on ne lit pas la colonne qu'on croit |
| Un poids **négatif** | Refusé |
| Un poste **sans code**, avec seulement un libellé | Refusé : un libellé ne se calcule pas (règle 4) |
| Un fonds dont la source range **tout dans « autres »** | Refusé, et l'actif devient « non couvert ». Voir l'encadré ci-dessous |

---

## B. Contrôles sur tes vraies données

### B.1 — D'abord : vérifier que le type de chaque actif est déclaré

L'application doit savoir si un actif est un ETF, une action ou une crypto : les trois ne se
regardent pas au même endroit, et une crypto ne se regarde nulle part. Tu as déjà déclaré ces types
à l'étape 6, dans `actifs.toml` — il n'y a donc normalement rien à faire.

```
uv run pastory composition
```

La commande affiche, actif par actif, ce qu'elle sait de son intérieur. Lis la liste et vérifie :

- [ ] **aucun actif ne dit « type non déclaré »** ;
- [ ] chaque ETF annonce un nombre de pays et de secteurs, et une **date d'arrêté** ;
- [ ] les fonds marqués **« synthétique »** sont ceux que tu crois (typiquement tes ETF PEA sur
      indices non européens) ;
- [ ] les actifs sans composition sont listés, avec un motif compréhensible.

**Note ce que tu trouves dans `etape-7.local.md`** : combien d'ETF ont une composition, combien
n'en ont pas, et lesquels.

> ⚠️ **Le trou connu d'avance.** Deux émetteurs d'ETF ne publient rien d'exploitable —
> **BNP Paribas Easy** et **Xtrackers** — et rien ne garantit que la source retenue les couvre. BNP
> Paribas Easy est le deuxième émetteur d'ETF éligibles au PEA : si l'un de tes ETF vient de chez
> eux, il est possible qu'il apparaisse « non couvert ». Ce n'est pas une panne, c'est la limite
> écrite dans [D-63](../decisions.md).

> ⚠️ **Et le trou constaté en lançant la commande, le 2026-09-27, puis diagnostiqué le 2026-09-28.**
> Une partie des ETF suivis n'a aucune composition chez la source. Elle répond pourtant normalement
> pour eux — avec une date et un drapeau de réplication — mais range **100 % du fonds dans
> « autres »**, ce qui veut dire qu'elle n'en connaît pas le contenu. L'application refuse cette
> réponse plutôt que de la présenter comme de l'obligataire et des liquidités, ce qui serait faux.
>
> **Il faut distinguer deux situations très différentes, et la commande le fait maintenant :**
>
> 1. **l'actif n'a réellement ni pays ni secteur** — un ETF d'obligations, un ETF de matières
>    premières. Ce n'est **pas** un manque de données : c'est sa nature, comme pour un actif
>    numérique. Déclare son **contenu** dans `actifs.toml` (`contenu = "obligations"` ou
>    `contenu = "matieres_premieres"`) et il sera rangé dans sa classe, hors géographie et hors
>    secteurs, avec un libellé qui l'explique. Ce champ ne remplace pas le `type`, qui reste
>    « etf » : c'est lui qui porte le TER et le spread ([D-71](../decisions.md)) ;
> 2. **l'actif est un fonds d'actions dont la source ignore la composition.** Là, c'est un vrai
>    trou. Diagnostiqué le 2026-09-28 : ce n'est ni un problème de **part** (l'autre part du même
>    compartiment est tout aussi vide), ni un problème de **région** (les répartitions par région et
>    par marché développé/émergent sont vides aussi). La source **couvre bien** ce genre de fonds
>    quand il est à **réplication physique** — 35 et 28 pays sur deux fonds émergents testés — et
>    ne couvre pas certains fonds **à swap**. C'est une lacune fonds par fonds de la source.
>
> **Ce que tu peux faire dans le second cas** : relever l'exposition géographique et sectorielle sur
> la fiche de l'émetteur et la déclarer à la main (voir B.6). C'est du travail, et c'est le seul
> moyen honnête tant qu'aucune source gratuite unique ne le couvre.
>
> Note dans ton fichier local combien d'actifs relèvent de chaque cas.

### B.2 — Le contrôle principal : la somme doit tomber juste

C'est **le** contrôle de l'étape, et il ne demande aucune connaissance financière : juste un
tableur.

```
uv run pastory exporter-positions
```

Ouvre **`repartition_pays.csv`**. Il contient une ligne par pays, puis des lignes de « reste »
(non attribué, non couvert, obligations et liquidités, actifs numériques).

- [ ] fais la **somme de la colonne `montant`** ;
- [ ] compare-la à la colonne **`base`**, identique sur toutes les lignes.

**Les deux doivent être exactement égales, au centime.** Si elles ne le sont pas, un montant s'est
évaporé et **aucun pourcentage du rapport n'est fiable** : dis-le-moi immédiatement.

> **La seule exception, et elle s'annonce d'elle-même.** Si le rapport affiche un bloc
> « **Ce qui cloche dans ces chiffres** », c'est qu'une source attribue plus que la valeur d'un
> actif — le prêt de titres le fait légitimement. La somme dépasse alors la base, et le message dit
> **de combien**, au centime. Rien n'est raboté ([D-69](../decisions.md)), donc l'écart est
> exactement celui annoncé. Sans ce bloc, l'égalité doit être parfaite.

Refais la même vérification sur `repartition_secteurs.csv` et `repartition_classes.csv`.

- [ ] et vérifie que la colonne `base` vaut bien la **valeur de tes actifs** affichée par
      `pastory positions` au même jour.

### B.3 — La comparaison avec la fiche d'un émetteur

Prends **deux ou trois** de tes ETF, de préférence un physique et un synthétique.

Pour chacun :

1. relève ce que l'application affiche dans `repartition_pays.csv` (colonne `montant` et
   `part_pour_cent`) — mais attention, ce fichier donne la répartition de **tout ton
   portefeuille**, pas celle d'un ETF pris seul. Pour un ETF isolé, ouvre plutôt le lien du
   document d'information que `pastory composition` affiche à côté de lui ;
2. ouvre la **fiche de l'émetteur** ou son document d'information clé (le lien est donné par
   `pastory composition`) ;
3. compare les **trois ou quatre premiers pays** et les **trois premiers secteurs**.

- [ ] les **gros postes** se retrouvent, dans le même ordre ;
- [ ] les écarts sont de l'ordre de **un à trois points**, pas de dizaines de points ;
- [ ] pour un ETF **synthétique**, tu as bien comparé à l'**exposition de l'indice**, et non à la
      liste des titres détenus (voir l'encadré au début de ce cahier).

**Un écart de dizaines de points, ou un pays qui domine alors qu'il ne devrait pas** (« Allemagne
38 % » sur un fonds monde, « France 40 % » sur un fonds américain) est un **signal grave** : cela
voudrait dire qu'on lit le panier de swap et non l'indice. Dis-le-moi tout de suite.

### B.4 — Les zones, et ce qu'elles valent

- [ ] la somme des pays de chaque zone vaut bien le montant affiché pour la zone ;
- [ ] les pays que tu ne t'attendais pas à voir dans une zone sont explicables : le **Mexique**
      n'est jamais en Amérique du Nord, la **Corée du Sud**, la **Pologne** et la **Grèce** sont
      comptées en marchés émergents, et **Israël** est dans « Autres pays et territoires ».

Si un rattachement ne te convient pas, **tu peux le changer sans toucher au code** : le fichier
`pastory/parametres/zones.toml` porte une ligne par pays, avec sa zone, sa source et sa date
([D-67](../decisions.md)).

### B.5 — Ce que les chiffres des étapes précédentes doivent devenir : rien

Cette étape n'ajoute que de l'affichage : elle ne touche ni aux quantités, ni au capital investi,
ni aux rendements, ni aux coûts.

- [ ] relance `pastory positions --au <la même date qu'avant>` et vérifie que la **valeur de tes
      actifs**, le **gain**, le **TRI**, le **TWRR** et la **valeur réelle** sont **identiques** à
      ce qu'ils étaient avant l'étape 7.

Si l'un d'eux a bougé d'un centime, c'est un défaut : signale-le.

### B.6 — Le rafraîchissement, et la porte de sortie

Une composition n'est pas définitive, contrairement à un cours : celle d'un ETF change chaque mois.

- [ ] `uv run pastory oublier-composition --actif <ISIN>` puis `pastory composition` : la
      composition est redemandée, et sa date d'arrêté peut avoir avancé.

Et si la composition d'un actif te paraît fausse, tu peux **la corriger à la main**. Dans
`actifs.toml`, sur la ligne de l'actif :

```toml
"<ISIN>" = { ticker = "AAAA.DE", devise = "EUR", type = "etf", ter_pour_cent = 0.20,
             pays = { US = 70.0, FR = 2.1 }, secteurs = { technology = 30.0 } }
```

Ce que tu écris **l'emporte sur la source** ([D-70](../decisions.md)). Les totaux n'ont pas besoin
de faire 100 : ce qui manque devient du « non attribué », comme pour une source.

Et pour un actif qui n'a **ni pays ni secteur** par nature, il n'y a rien à relever : une seule
mention suffit ([D-71](../decisions.md)).

```toml
"<ISIN>" = { ticker = "AAAA.PA", devise = "EUR", type = "etf", ter_pour_cent = 0.20,
             contenu = "obligations" }
```

- [ ] après avoir déclaré un contenu, `pastory composition` dit « Obligations : ni pays ni secteur
      au sens des actions (ce n'est pas une donnée manquante) » au lieu d'un motif d'échec ;
- [ ] et le bloc de répartition montre une ligne « Obligations (hors actions) » plutôt qu'un
      « Non couvert ».

> **Une composition déclarée n'a pas de date d'arrêté.** Elle n'entre donc pas dans la fourchette de
> dates affichée en tête du bloc, et le rapport te nomme les actifs concernés : leurs chiffres ne
> vieillissent pas tout seuls, c'est à toi de les revoir si la composition change.

### B.7 — Ce que toi seul peux vérifier

Deux points restent à ta charge, et ils ne sont pas vérifiables par le programme :

1. **la source des compositions n'est pas une source officielle.** C'est une interface interne,
   non documentée, dont l'usage n'est pas explicitement autorisé — usage personnel toléré, pas un
   droit ([D-63](../decisions.md)). Elle peut fermer sans préavis ; l'application le dira et
   continuera sans répartition. Tu as accepté cette limite en connaissance de cause, comme pour
   pytr ([D-49](../decisions.md)) ;
2. **la nomenclature affichée est celle de Morningstar, et non GICS.** Les indices que suivent tes
   ETF sont pourtant construits sur GICS ou sur ICB. Aucune source gratuite interrogeable par ISIN
   ne donne du GICS. Les chiffres sectoriels de l'application sont donc comparables à Yahoo
   Finance, à Morningstar et à justETF, **mais pas** à un document d'émetteur qui parle GICS —
   l'écart y sera de quelques points sur la technologie et la communication.

---

## Ce que cette étape ne vérifie pas

- **elle ne transparise qu'un niveau.** Un ETF qui détient d'autres ETF (gamme « LifeStrategy »,
  « Portfolio », « Multi-Asset ») ne se lit pas : il apparaît **non couvert** plutôt que deviné.
  *Depuis l'étape 8 bis, on sait pourquoi il n'est pas nommé autrement : aucune source ne reconnaît
  un fonds de fonds ([D-76](../decisions.md)) ;*
- **elle ne dit rien de la qualité de ta diversification.** Elle montre où est ton argent ; elle ne
  juge pas, et ne conseille pas ([D-26](../decisions.md)) ;
- **elle ne suit pas la répartition dans le temps.** Une répartition est une photo du jour, pas une
  série. L'évolution des poids dans le temps n'est pas au programme ;
- **elle ne compte ni les espèces ni les ETC.** Les espèces ne sont jamais suivies
  ([D-11](../decisions.md)) ; un ETC sur l'or, s'il y en avait un, serait traité comme un actif sans
  composition — donc non couvert, avec son montant affiché.
