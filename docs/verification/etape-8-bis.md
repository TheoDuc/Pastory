# Cahier de vérification — étape 8 bis : la source de secours

Ce que l'étape a ajouté, et comment le vérifier **toi-même**. Comme les autres cahiers : des cas
refaisables à la main d'abord, des contrôles sur tes vraies données ensuite.

**Ce qui a changé, en trois phrases.** Quand la source principale ne sait pas ouvrir un de tes
fonds d'actions, l'application peut désormais aller chercher sa répartition **par pays** chez
Amundi, à condition que tu le lui demandes **fonds par fonds** ([D-77](../decisions.md)). Les
**secteurs** de ce fonds restent non couverts, et c'est volontaire. Et chaque ligne de la
répartition géographique dit maintenant **d'où elle vient** et **sous quelle règle de pays**.

---

## 1. Pourquoi ce n'est pas automatique

C'est la première chose à comprendre, parce que ça peut surprendre : **rien ne bascule tout seul**.
Un fonds non couvert le reste jusqu'à ce que tu écrives `secours = "amundi"` sur sa ligne.

La raison est mesurée, pas théorique. Deux sources ne classent pas les sociétés de la même façon :

| | extraETF (source principale) | Amundi (secours) |
|---|---|---|
| Règle de pays | pays d'**activité** de la société | pays de **classification de l'indice** |
| Secteurs | 11 secteurs Morningstar | secteurs **GICS** |

Sur un même fonds à une même date, l'écart entre deux règles de pays est de **2 points sur les
États-Unis** et d'un **facteur huit sur l'Irlande**. Sur les secteurs, c'est **5 points sur la
technologie**, l'écart étant exactement Alphabet et Meta, qui changent de camp. Si l'application
basculait d'une source à l'autre en silence, ton camembert aurait un total juste et une répartition
fausse — le genre d'erreur que ce projet traque.

D'où : tu demandes, et l'écran dit ligne par ligne quelle source et quelle règle s'appliquent.

---

## 2. Le cas que tu peux refaire à la main

**Le fonds :** `FR001400U5Q4`, Amundi PEA Monde (MSCI World). C'est un ETF **à swap** — comme tout
ETF « PEA » sur un indice non européen, qui doit détenir 75 % de titres éligibles au PEA et ne peut
donc pas détenir le MSCI World.

**Ce que le programme trouve** (relevé le 2026-09-30) :

| Pays | Part |
|---|---|
| US — États-Unis | 72,9336 % |
| JP — Japon | 5,8608 % |
| GB — Royaume-Uni | 3,4178 % |
| CA — Canada | 3,3148 % |
| *(19 autres pays)* | |
| **Total** | **99,9998 %** |

Arrêté au **2026-09-28**.

**Comment le vérifier, sans nous croire.** Ouvre dans ton navigateur :

```
https://www.amundietf.fr/pdfDocuments/monthly-factsheet/FR001400U5Q4/FRA/FRA/RETAIL/ETF
```

La fiche mensuelle s'affiche. Va à « répartition géographique » et compare. Les noms y sont en
français, les chiffres sont les mêmes.

**Le contrôle qui compte le plus.** Cherche aussi, sur la même fiche, la liste des **titres
détenus**. Tu y verras des sociétés qui n'ont rien à voir avec un indice mondial — c'est le panier
de collatéral du swap. L'application **ne le lit jamais** : sur un fonds de ce genre, l'étape 7
avait mesuré **Allemagne 38,5 % / États-Unis 15,6 %** pour le panier, contre **États-Unis 72,9 %**
pour l'indice. Afficher le panier décrirait un risque que tu ne portes pas
([D-64](../decisions.md)).

- [ ] les quatre premiers pays de la fiche correspondent à ceux du tableau ci-dessus ;
- [ ] la date d'arrêté de la fiche est celle qu'affiche l'application ;
- [ ] les titres détenus de la fiche **ne** ressemblent **pas** à la répartition affichée — et
      c'est normal.

---

## 3. Le total ne fait pas 100 %, et c'est voulu

99,9998 %, pas 100. Le reliquat de **0,0002 point** devient du « non attribué », visible, et
**rien n'est renormalisé** ([D-69](../decisions.md)).

C'est plus près de 100 que la source principale, dont les répartitions vont de 99,43 % à 99,96 %.
Les deux sont acceptées : un contrôle « ça doit faire 100 » comme un contrôle « ça ne fait jamais
tout à fait 100 » seraient tous les deux faux.

- [ ] sur un fonds servi par le secours, le « non attribué » est minuscule et non nul.

---

## 4. Les trois refus, et pourquoi chacun est une bonne nouvelle

L'application refuse plus souvent qu'elle n'accepte, et chaque refus évite un chiffre faux.
Vérifié le 2026-09-30 contre le vrai service :

| Ce que tu demandes | Ce qui se passe | Pourquoi |
|---|---|---|
| Un fonds **obligataire** Amundi (`LU1650487413`) | **refusé** : « Amundi décrit cet actif comme contenant : GOVERNMENT » | Sur un indice obligataire, « pays » peut vouloir dire la **devise d'émission** et non le pays de l'émetteur. Déclare son `contenu` plutôt que de lui chercher une géographie ([D-71](../decisions.md)) |
| Un fonds d'un **autre émetteur** (`IE00B4L5Y983`, iShares) | **refusé** : « cette source ne couvre que les fonds Amundi » | C'est la limite de couverture assumée. Le fonds reste non couvert, avec son montant affiché |
| Un **pays que la table ne connaît pas** | **refusé**, en nommant le pays | Voir la section suivante |

- [ ] mets `secours = "amundi"` sur un ETF obligataire et vérifie que le message te dit d'utiliser
      `contenu` à la place ;
- [ ] mets-le sur un ETF d'un autre émetteur et vérifie que le message dit pourquoi.

---

## 5. La fragilité de cette source, en clair

**Amundi rend des noms de pays en anglais, pas des codes.** « United States », pas « US ». Or
l'application identifie un pays par son **code** ISO et jamais par son nom
([D-66](../decisions.md)) — un nom peut être traduit, renommé ou périmé.

La traduction se fait dans **un seul fichier**, `pastory/parametres/pays_amundi.toml`, qui porte
sa source et sa date. **47 noms** y ont été relevés, plus 9 variantes ajoutées par prudence.

**Ce que ça coûte, exactement.** Si Amundi renomme un pays, la ligne devient inconnue. Alors :

- l'application **refuse la répartition entière** de ce fonds, et **nomme le pays fautif** ;
- elle **ne garde pas** les autres pays en laissant le reste tomber dans « non attribué ». Ce
  libellé veut dire *la source n'a pas attribué ce montant* ; s'en servir pour dire *nous n'avons
  pas su traduire ce nom* mentirait sur la cause.

**Contrepartie assumée :** un seul pays exotique non déclaré fait perdre la répartition du fonds.
Le message dit alors quoi faire — ajouter le nom au fichier, ou déclarer la répartition à la main.

- [ ] si un jour un fonds servi par le secours devient non couvert, **lis le message** : s'il nomme
      un pays, c'est ce cas-là, et il se corrige en une ligne.

---

## 6. Les secteurs restent non couverts, et c'est la bonne réponse

Amundi publie aussi des secteurs. L'application **ne les lit pas**.

Ce sont des secteurs **GICS** — « Information Technology », « Health Care » — là où l'application
emploie les **11 secteurs Morningstar**, et une seule nomenclature
([D-65](../decisions.md)). Les additionner donnerait un total juste et une répartition fausse.

Donc : un fonds servi par le secours apparaît **dans la répartition par pays**, et reste **non
couvert dans la répartition par secteur**. Ce n'est pas un bug.

- [ ] sur un fonds où tu as mis `secours = "amundi"` : il a des pays, et il est non couvert en
      secteur. Les deux écrans ne sont pas d'accord, et c'est normal.

---

## 7. La règle de pays, désormais visible

Jusqu'ici, l'application disait une phrase générale : « pour un fonds c'est le pays d'activité,
pour une action c'est le siège social ». Elle ne disait jamais **quel actif** relevait de **quelle
règle**. Maintenant, dès que plusieurs origines se côtoient, le rapport ajoute :

```
    D'où vient la composition de chaque actif, et sous quelle règle de pays :
      XX0000000001 : extraETF (composition agrégée par ISIN) — pays d'activité de la société…
      XX0000000002 : Amundi (répartition de l'indice suivi, par ISIN) — pays de classification…
```

Le bloc **n'apparaît pas** quand tout vient du même endroit : vingt lignes identiques feraient
douter des chiffres au lieu de les éclairer.

**Et dans le tableur.** `pastory exporter-positions` écrit désormais
`origines_des_compositions.csv` — une ligne par actif, avec sa source et sa règle. C'est là que ça
compte : la colonne `source` des `repartition_*.csv` porte *toutes* les sources sur chaque ligne,
ce qui est juste (une ligne de pays agrège plusieurs actifs) mais ne te dit pas **quel actif a
suivi quelle règle**.

- [ ] ouvre `origines_des_compositions.csv` et vérifie qu'un fonds servi par le secours porte bien
      « Amundi » et la règle de l'indice, là où les autres portent « extraETF » et le pays
      d'activité.

- [ ] déclare `secours = "amundi"` sur un fonds, relance `pastory positions`, et vérifie que ce
      bloc apparaît et nomme bien deux sources.

---

## 8. Sur tes vraies données

Fais-le dans cet ordre.

1. **Repère tes fonds non couverts.** `pastory positions` les nomme, avec leur montant et le motif.
2. **Pour chacun, regarde son ISIN.** Est-ce un fonds **Amundi** ? Les ISIN commencent souvent par
   `FR` ou `LU`, et le nom contient « Amundi » ou « Lyxor ». Si non, le secours ne servira à rien.
3. **Ajoute `secours = "amundi"`** sur sa ligne dans `actifs.toml`. *C'est temporaire : à
   l'étape 9, l'application te le **proposera** là où le fonds est annoncé non couvert, et tu
   n'auras rien à écrire ([D-78](../decisions.md)).*
   (`pastory emplacements` dit où se trouve le fichier) :

   ```toml
   "FR001400U5Q4" = { ticker = "DCAM.PA", devise = "EUR", type = "etf", secours = "amundi" }
   ```

4. **Relance `pastory positions`.**

Puis vérifie :

- [ ] le fonds apparaît maintenant dans la répartition **par pays** ;
- [ ] il est toujours non couvert dans la répartition **par secteur** ;
- [ ] la part de portefeuille « non couverte » a **baissé** du montant de ce fonds, dans la
      géographie seulement ;
- [ ] le total de la répartition par pays **n'a pas été ramené à 100 %** ;
- [ ] le bloc « d'où vient la composition de chaque actif » nomme deux sources et deux règles ;
- [ ] les quatre premiers pays correspondent à la fiche mensuelle du fonds sur amundietf.fr, au
      même arrêté.

**Si un chiffre te paraît faux, dis-le sans chercher l'explication :** l'expérience des étapes
précédentes est que deux fois sur trois l'affichage avait tort et le calcul avait raison, et une
fois sur trois c'était un vrai bug de calcul. Dans les deux cas, c'est en le signalant qu'on le
trouve.

---

## 9. Ce que cette étape ne fait pas

- **elle ne couvre pas les fonds à swap des autres émetteurs.** Xtrackers a été re-testé le
  2026-09-30 : aucune donnée exploitable, tout son site est rendu côté client. BNP Paribas Easy
  était déjà dans ce cas à l'étape 7. Ces fonds restent non couverts, et la déclaration à la main
  demeure leur recours ;
- **elle ne donne pas de secteurs** pour les fonds qu'elle sert — voir §6 ;
- **elle ne reconnaît pas un fonds de fonds.** Aucune source accessible ne le dit : un fonds qui
  détient d'autres fonds reste « non couvert », et le mot « non transparisé » n'est jamais affiché
  ([D-76](../decisions.md)). La notion est expliquée au [glossaire](../glossaire.md), parce qu'elle
  explique **pourquoi** un fonds peut être non couvert ;
- **elle ne suit pas la répartition dans le temps.** Une répartition est une photo du jour.
