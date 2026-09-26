# Cahier de vérification — étape 4 : les cours de marché

L'étape 3 tirait des chiffres de tes opérations. **L'étape 4 va chercher les cours de marché**,
et s'en sert pour une chose précise : donner un prix aux **titres entrés sans prix** — actions
gratuites, titres transférés ([D-15](../decisions.md)).

Avant, ces parts étaient comptées mais leur montant non : le capital investi de l'actif était
**sous-estimé**, et son prix de revient restait vide plutôt que d'afficher un nombre faussement
bas ([D-45](../decisions.md)). C'est ce trou que cette étape comble.

Ce qu'elle ne calcule **pas encore** : la valeur de tes actifs aujourd'hui, le gain, le TRI et le
TWRR. Ils arrivent à l'étape 5, et ils s'appuieront sur le même cache de cours.

Deux parties, comme aux cahiers précédents :

1. **les cas fictifs de la partie A**, que tu peux refaire sur papier ou dans un tableur ;
2. **tes vrais cours**, en face de l'application Trade Republic (partie B).

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à toi
vont dans `etape-4.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## Les trois choix de l'étape, en une page

Ce sont tes arbitrages du 26 septembre 2026. Tout le reste en découle.

| Décision | Ce qui s'applique |
|---|---|
| [D-51](../decisions.md) | Les cours viennent de **Yahoo Finance**, en **cours brut** — jamais la série retraitée des dividendes, que le moteur compte déjà |
| [D-48](../decisions.md) | Le cours de référence est celui du **marché principal en euros**. Un cours dans une autre monnaie est **refusé**, jamais converti |
| [D-50](../decisions.md) | Un cours en cache est **définitif**. `dashboard oublier-cours` est la seule façon d'en changer |

---

## Le fichier de correspondance : la pièce à ouvrir en premier

Ta banque identifie un actif par son **ISIN**. Les sources de cours, elles, travaillent au
**ticker** — un code court qui désigne un titre **sur une place donnée**. Un même ETF peut coter
à Xetra en euros et à Londres en dollars, avec deux tickers différents.

Personne ne peut faire cette correspondance à ta place en toute sécurité. L'application la
**propose**, tu la **valides** :

```toml
[actifs]
"XX0000000001" = { ticker = "AAAA.DE", devise = "EUR" }   # Xetra
"XF000EXEMPLE01" = { ticker = "BBB-EUR", devise = "EUR" } # une crypto
"XX0000000002" = ""                                       # pas encore déclaré
```

- `.DE` = Xetra, `.PA` = Euronext Paris, `-EUR` = une crypto en euros ;
- `devise` est la monnaie **attendue**. Si la source répond dans une autre, le cours est refusé.
  C'est ce qui empêche des dollars d'être comptés comme des euros ;
- une ligne vide veut dire « pas valorisé » : l'actif est **signalé**, jamais estimé.

Le fichier est dans ton dossier personnel (`dashboard emplacements` te dit où). Il n'entre jamais
dans git.

---

## A. Cas fictifs, à refaire à la main

Ces cas sont **exactement ceux que les tests font calculer au programme**. Si ce document et le
code divergeaient un jour, les tests le diraient.

### A.1 — Des titres reçus prennent le cours de leur jour d'apparition

Tu reçois **13 parts** sans prix le **vendredi 6 mars 2026**. Le cours de clôture de ce jour-là
est de **15,384615 €**.

| | Calcul | Résultat |
|---|---|---|
| Cours retenu | clôture du 2026-03-06 | 15,384615 € |
| Montant brut déduit | 13 × 15,384615 | **200,00 €** |
| Capital net investi | + le montant brut | **200,00 €** |
| Prix de revient | 200,00 / 13 | **15,384615 €** |

**Ce qu'il faut retenir :** le montant est *déduit*, pas donné par la banque. Les CSV le marquent
`deduction`, et le rapport le répète. Le prix de revient garde ses six décimales
([D-44](../decisions.md)) — c'est un résultat de division.

### A.2 — Reçus un dimanche : c'est le **vendredi** qui compte

Cette fois, **3 parts** arrivent le **dimanche 1ᵉʳ mars 2026**, et le cours de clôture du vendredi
précédent est de **12,50 €**. La bourse était fermée le dimanche : il n'y a **aucun** cours ce
jour-là.

Le programme prend alors le **dernier jour coté** — le vendredi 27 février, à 12,50 € — et il le
dit :

```
    XX0000000004   CTO     2026-03-01   3,00 x 12,50 = 37,50 EUR
                           cours du 2026-02-27 (dernier jour coté avant le 2026-03-01), XETRA
```

**Rien n'est jamais interpolé.** Le cours utilisé a réellement existé, un jour précis, et ce jour
est écrit. Si le dernier cours connu a plus de **dix jours**, le programme **refuse** : au-delà,
ce n'est plus un jour férié, c'est un titre qui ne cote plus ou un mauvais ticker.

### A.3 — Sans cours, rien n'est inventé

Reprends le cas A.1, mais l'actif n'est pas déclaré dans le fichier de correspondance — ou la
source ne le connaît pas.

| | Résultat |
|---|---|
| Quantité détenue | **13 parts** (elles sont bien là) |
| Capital net investi | **0,00 €**, et le rapport dit qu'il est sous-estimé |
| Prix de revient | **vide**, pas un nombre faussement bas |
| Rapport | « 1 opération attend toujours un prix », avec la raison |

**Ce qu'il faut retenir :** un montant manquant n'est **jamais** remplacé par zéro en silence
([D-45](../decisions.md)). C'est exactement le comportement de l'étape 3 : il reprend dès qu'un
cours manque.

### A.4 — Une cotation en dollars est refusée, pas convertie

Tu déclares un ETF avec le ticker d'une cotation **londonienne**, qui répond en dollars.

| | Résultat |
|---|---|
| Cours retenu | **aucun** |
| Message | « est coté en USD, or EUR est attendu. L'application ne convertit rien » |

C'est le garde-fou de [D-48](../decisions.md), et il agit à deux endroits : quand l'assistant
propose (la proposition est écrite en commentaire, donc inactive, avec un ATTENTION), et quand un
cours arrive.

### A.5 — Le cours brut, jamais le cours « ajusté »

Sur une action qui distribue des dividendes, la source propose deux séries pour le **même jour** :

| Série | Valeur | Ce qu'elle contient |
|---|---|---|
| clôture (**retenue**) | 53,38 € | le cours tel que la bourse l'a coté |
| clôture ajustée (**ignorée**) | 50,54 € | le cours corrigé des dividendes déjà versés |

L'écart dépasse **5 %** en début de série. Si on lisait la seconde, chaque dividende serait
compté **deux fois** : une fois dans le cours, une fois par le moteur ([D-29](../decisions.md)).

**Et le piège est invisible sur un ETF capitalisant**, où les deux séries sont identiques — donc
tant que tu ne détiens rien qui distribue, une erreur ici ne se verrait pas.

### A.6 — Le cache ne change jamais un cours déjà écrit

Un cours de 100,00 € est en cache pour le 6 mars. La source en renvoie 999,99 € pour le même jour.

| | Résultat |
|---|---|
| Cours conservé | **100,00 €** |
| Cours ajoutés | **0** |

C'est [D-50](../decisions.md) : le chiffre vu hier est celui que tu revois aujourd'hui. Pour en
changer — correction de la source, regroupement d'actions —, il faut le demander :
`dashboard oublier-cours --actif <ISIN>`.

---

## B. Contrôles sur tes vraies données

```
uv run dashboard actifs              dit où chercher le cours de chaque actif (une fois)
uv run dashboard cours               récupère les cours et les met en cache
uv run dashboard positions           les chiffres, avec le bloc « Cours de marché » à la fin
uv run dashboard positions --hors-ligne   les mêmes, sans réseau
uv run dashboard oublier-cours --actif <ISIN>   reprendre un actif à zéro
```

Aucune de ces commandes ne demande ton PIN : **rien ne passe par Trade Republic**
([D-49](../decisions.md)).

### B.1 — Relire le fichier de correspondance, ligne par ligne

`dashboard actifs` écrit le fichier et propose un ticker pour chaque actif. Ouvre-le et, pour
**chaque** ligne :

- [ ] le **ticker** désigne bien cet actif — le commentaire au-dessus rappelle le nom et la place
      trouvés par la source ;
- [ ] la **place** est celle que tu veux comme référence (Xetra, Euronext Paris…) ;
- [ ] la **devise** est `EUR` ;
- [ ] les lignes marquées **ATTENTION** ne sont pas retenues telles quelles : c'est une cotation
      dans une autre monnaie, donc presque sûrement la mauvaise place.

**Un actif que tu laisses vide n'est pas une erreur** : il ne sera simplement pas valorisé, et le
rapport le dira.

### B.2 — Le contrôle principal : trois cours, en face de l'application

Ouvre le cache : un fichier CSV par actif, dans le dossier `cache/cours` que
`dashboard emplacements` t'indique. Choisis **trois actifs** et, pour chacun :

- [ ] prends une **date précise** dans le fichier — de préférence un jour où tu te souviens du
      cours, ou un jour récent ;
- [ ] compare avec le cours de clôture de ce même jour dans ton application Trade Republic, ou sur
      le site de la place (Xetra, Euronext) ;
- [ ] vérifie que la **devise** et la **place** écrites dans le fichier sont celles attendues.

> **Un écart de quelques centimes est normal** : Trade Republic exécute désormais lui-même tes
> ordres et n'affiche pas forcément le cours de clôture de Xetra. Ce que tu vérifies ici, c'est
> qu'on est sur **le bon titre**, **la bonne place** et **le bon ordre de grandeur** — pas le
> centime.
>
> **Un écart important, en revanche, doit être signalé** : mauvais ticker, mauvaise place, ou
> mauvaise monnaie.

### B.3 — Le contrôle qui prouve l'étape : un prix retrouvé

Si tu as reçu des actions gratuites ou des titres transférés, `dashboard positions` affichait
jusqu'ici un prix de revient **vide** pour cet actif, et le rapport disait « histoire
incomplète ».

- [ ] le bloc **« Cours de marché »**, en fin de rapport, montre la ligne de ce titre : quantité,
      cours, et le produit des deux ;
- [ ] **refais la multiplication à la main** : quantité × cours = le montant annoncé ;
- [ ] le **prix de revient** de cet actif est maintenant un nombre, et il est cohérent avec le
      cours utilisé ;
- [ ] le **capital investi** de sa poche a augmenté du montant déduit — et la mention
      « sous-estimé » a disparu pour cet actif.

Si tu n'as reçu aucun titre sans prix, ce bloc n'apparaît pas : c'est normal, il n'y a rien à
compléter.

### B.4 — Ce que le rapport refuse de faire

Le bloc « Cours de marché » peut aussi dire ce qu'il n'a **pas** pu faire. Voici comment le lire :

| Ce que tu lis | Ce que ça veut dire | Quoi faire |
|---|---|---|
| **actif non déclaré** | pas de ticker dans le fichier de correspondance | `dashboard actifs`, puis remplis la ligne |
| **ticker inconnu** | la source ne connaît pas ce code | corrige le ticker dans `actifs.toml` |
| **devise inattendue** | la cotation trouvée n'est pas en euros | retiens une autre place, en euros |
| **cours indisponible** | aucun cours à cette date ni dans les 10 jours précédents | vérifie le ticker ; le titre cote-t-il encore ? |
| **source injoignable** | réseau, antivirus, ou limitation de débit | réessaie plus tard ; les cours déjà en cache restent utilisables |

Dans tous ces cas, **les chiffres déjà justes ne bougent pas** : seul l'actif concerné reste sans
valorisation.

### B.5 — Le cache tient sans réseau

- [ ] coupe le Wi-Fi, ou lance `dashboard positions --hors-ligne` ;
- [ ] les chiffres sont **les mêmes** qu'avec le réseau ;
- [ ] aucun appel n'est fait : c'est ce qui permettra à l'interface de s'ouvrir instantanément
      (étapes 8 et 9).

### B.6 — Et l'oubli fonctionne

- [ ] note le nombre de cours d'un actif affiché par `dashboard cours` ;
- [ ] `dashboard oublier-cours --actif <ISIN>` ;
- [ ] `dashboard cours` à nouveau : le même nombre revient, et les cours sont identiques.

---

## Ce que cette étape ne vérifie pas encore

- **La valeur de tes actifs aujourd'hui**, le gain, le TRI et le TWRR : étape 5. Le cache de cours
  est déjà ce qu'il leur faut.
- **La valorisation « aujourd'hui ».** Le cours du jour en cours n'est pas un cours de clôture :
  la séance n'est pas finie, et pour une crypto elle ne finit jamais. Comme le cache est définitif
  ([D-50](../decisions.md)), l'enregistrer figerait un prix intermédiaire pour toujours. La source
  **s'arrête donc à la dernière séance close**, et le cache ne contient jamais le jour même. C'est
  sans conséquence ici — on ne valorise que des jours passés — mais l'étape 5, qui voudra la valeur
  du portefeuille *maintenant*, devra prévoir un chemin à part pour ce cours-là.
- **Le TER et la composition des ETF** : étapes 6 et 7, avec leurs propres sources.
- **Un regroupement d'actions** (*split*). Il réécrit toute la série passée d'un actif chez la
  source, alors que le cache est définitif. Le cas est rare, il se voit à l'œil (un cours divisé
  d'un coup), et il se traite par `oublier-cours`. Rien ne le détecte automatiquement.
- **La justesse de la source elle-même.** Yahoo n'a aucune interface officielle
  ([sources-de-cours.md §7](../sources-de-cours.md)). C'est pourquoi chaque cours porte sa place et
  sa source, et pourquoi le contrôle B.2 existe : c'est toi qui confirmes qu'on interroge le bon
  titre.
