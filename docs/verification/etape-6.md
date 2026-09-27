# Cahier de vérification — étape 6 : les frais, les taxes et la valeur réelle

Les étapes précédentes répondaient à « combien j'ai ? » et « combien ça a rapporté ? », **en
montants bruts** ([D-21](../decisions.md)). **L'étape 6 répond aux deux autres questions de tes
notes** : ce que ça coûte, et ce que tu récupérerais si tu retirais tout
([D-23](../decisions.md)).

Trois choses nouvelles, dans cet ordre :

1. **les coûts payés**, détaillés par opération et par actif, avec leur **poids** — 1 € de frais
   sur un achat de 25 € pèse 4 % ;
2. **les coûts estimés** ([D-17](../decisions.md)) : l'**écart de prix** (spread) payé à chaque
   achat et à chaque vente ([D-30](../decisions.md)), et les **frais courants** d'un ETF (TER) ;
3. **la valeur réelle** : valeur de marché − frais de vente − écart de prix − **impôt estimé**,
   poche par poche.

Deux parties, comme aux cahiers précédents :

1. **les cas fictifs de la partie A**, à refaire sur papier ou dans un tableur ;
2. **tes vrais chiffres** (partie B), et ce que **toi seul** peux vérifier.

Toutes les valeurs de la partie A sont **inventées** ([D-03](../decisions.md)). Tes résultats à
toi vont dans `etape-6.local.md`, que le `.gitignore` exclut : il reste sur ta machine.

---

## Ce qui est estimé, et ce qui ne l'est pas

C'est la distinction la plus importante de l'étape. Si tu n'en retiens qu'une chose, c'est
celle-ci.

| Chiffre | D'où il vient | Fiabilité |
|---|---|---|
| Frais et taxes **payés** | lus dans ton export, opération par opération | **Certains** (au risque de lecture près, étape 2) |
| **Écart de prix** (spread) | un taux moyen × le montant de l'opération | **Estimé**. Personne ne le facture, personne ne le publie |
| **Frais courants** d'un ETF (TER) | le taux que **tu** as validé × la valeur de l'actif | **Estimé**, sur une donnée que tu as relue |
| **Impôt** de sortie | les règles fiscales françaises × la plus-value calculée | **Estimé**. Ce n'est pas une déclaration ([D-26](../decisions.md)) |

L'application écrit « estimé » partout où ça l'est, et cite pour chaque taux sa **date** et sa
**source**. Rien de tout cela n'entre dans le gain, le TRI ou le TWRR, qui restent bruts
([D-21](../decisions.md)).

---

## Les sept arbitrages de l'étape, en une page

| Décision | Ce qui s'applique |
|---|---|
| [D-55](../decisions.md) | Le **type** d'un actif (ETF, action, crypto) est **déclaré** par toi dans `actifs.toml`. Sans type, aucun spread n'est estimé pour cet actif |
| [D-56](../decisions.md) | Le spread est un **taux par côté** (la moitié de l'écart achat/vente), par type d'actif, remplaçable actif par actif |
| [D-57](../decisions.md) | Le **prix de revient fiscal** (frais d'achat compris) est tenu à côté du prix de revient, et n'entre dans aucune performance |
| [D-58](../decisions.md) | Chaque taux vit dans un fichier, avec sa **valeur**, sa **date** et sa **source**. Corriger un taux ne touche pas au code |
| [D-59](../decisions.md) | L'impôt du PEA repose sur le **gain du plan**, approché depuis les titres, et sur une **date de premier versement que tu déclares** |
| [D-60](../decisions.md) | L'impôt appliqué est le **prélèvement forfaitaire unique**. Ce qui est déjà encaissé n'est pas compté : ce n'est pas un coût de sortie |
| [D-61](../decisions.md) | Le **TER** est proposé depuis la liste des ETF de Xetra, et **validé par toi** |

---

## A. Cas fictifs, à refaire à la main

Ces cas sont **exactement ceux que les tests font calculer au programme**
(`tests/moteur/test_couts.py`, `test_fiscalite.py`, `test_valeur_reelle.py`, même numérotation).
Si ce document et le code divergeaient, les tests le diraient.

**Les taux employés partout ci-dessous** : impôt sur le revenu **12,8 %**, prélèvements sociaux
**18,6 %**, donc **31,4 %** au total. Le 18,6 % est le taux de 2026 : la loi de financement de la
sécurité sociale pour 2026 a relevé la CSG sur les revenus du capital de 9,2 à 10,6 %. Le
détail et les sources sont dans [couts-et-fiscalite.md](../couts-et-fiscalite.md) §5.

### A.1 — Le poids d'un coût : ce qu'un petit ordre coûte vraiment

Achat de 5 parts à 5,00 € avec 1,00 € de frais.

| | Calcul | Résultat |
|---|---|---|
| Montant brut | 5 × 5,00 | 25,00 € |
| Coût payé | frais + taxes | 1,00 € |
| **Poids** | 1,00 / 25,00 | **4,00 %** |

**Ce qu'il faut en retenir :** 1 € de frais est indolore sur un achat de 1 000 €, et coûte 4 %
sur un achat de 25 €. C'est tout l'intérêt de la colonne : elle montre qu'un ordre ponctuel de
petite taille est cher, et qu'un plan d'épargne gratuit ne l'est pas.

**Deux garde-fous à vérifier :**
- un plan d'épargne sans frais pèse **0,00 %**, pas « rien » ;
- des titres reçus **sans prix connu** ([D-15](../decisions.md)) n'ont **aucun poids** — la case
  est vide, pas à zéro : diviser par un montant inconnu ne veut rien dire.

### A.2 — L'écart de prix (spread), à l'achat comme à la vente

Le spread est la différence entre ce que tu paies et le « vrai » prix du moment. **Il est déjà
dans le prix d'exécution** : aucune ligne de ton relevé ne le montre. Il faut donc l'estimer.

Achat de 10 parts à 20,00 € — 200,00 € bruts — sur un ETF (taux par défaut **0,05 % par côté**) :

| | Calcul | Résultat |
|---|---|---|
| Spread estimé de cet achat | 200,00 × 0,05 % | **0,10 €** |
| Le même montant sur une action | 200,00 × 0,10 % | 0,20 € |
| Le même montant sur une crypto | 200,00 × 0,50 % | 1,00 € |

**Pourquoi « par côté » :** l'écart publié est celui entre le prix d'achat et le prix de vente.
Tu en paies la moitié quand tu achètes, l'autre moitié quand tu vends. Un écart annoncé de
0,10 % est donc un taux de **0,05 % par côté** ([D-56](../decisions.md)).

**Ce que tu dois voir :**
- un **dividende** ou des **titres reçus** ne paient aucun spread : aucun ordre n'a été passé ;
- un actif dont le **type n'est pas déclaré** n'a **aucune estimation**, et le rapport écrit
  « PARTIEL » avec son nom. Il ne compte pas pour zéro ([D-55](../decisions.md)).

### A.3 — Les frais courants d'un ETF (TER)

C'est le seul coût que tu paies **pendant** la détention : il est prélevé dans la valeur du
fonds, sans jamais apparaître sur ton compte.

15 parts valant 40,00 €, soit **600,00 €**, sur un ETF dont le TER est **0,20 %** :

| | Calcul | Résultat |
|---|---|---|
| **Frais courants estimés, par an** | 600,00 × 0,20 % | **1,20 €** |

**Ce que tu dois voir :**
- un ETF **sans TER validé** n'affiche rien, avec le motif « TER non déclaré » — jamais un zéro
  ([D-61](../decisions.md)) ;
- une **action** n'apparaît pas du tout dans ce bloc : elle ne prélève rien ;
- un actif **sans cours** n'a pas de base, donc pas d'estimation.

### A.4 — Le prix de revient fiscal : deux prix de revient, et c'est normal ⚠️

C'est le point le plus contre-intuitif de l'étape. L'application tient **deux** prix de revient
pour chaque actif, et ils sont tous les deux justes :

| | Ce qu'il mesure | Frais d'achat |
|---|---|---|
| **Prix de revient** ([D-13](../decisions.md)) | ce que tu as réellement placé dans l'actif | **exclus** |
| **Prix de revient fiscal** ([D-57](../decisions.md)) | ce que le fisc retient pour calculer ta plus-value | **inclus** |

Reprenons le premier achat du [cahier de l'étape 3](etape-3.md) : 10 parts à 20,00 €, avec
1,00 € de frais. Ton compte est débité de 201,00 €.

| | Calcul | Résultat |
|---|---|---|
| Capital net investi | le montant brut | 200,00 € |
| Prix de revient | 200,00 / 10 | **20,00 €** |
| Capital fiscal | montant brut + frais + taxes | 201,00 € |
| **Prix de revient fiscal** | 201,00 / 10 | **20,10 €** |

**Puis une vente de 5 parts sur 10 :** les deux capitaux partent **au prorata des parts**, comme
le capital investi ([D-12](../decisions.md)) :

| | Calcul | Résultat |
|---|---|---|
| Capital fiscal retiré | 201,00 × 5/10 | 100,50 € |
| Capital fiscal restant | 201,00 − 100,50 | **100,50 €** |
| Prix de revient fiscal | 100,50 / 5 | **20,10 €**, inchangé |

C'est bien la règle française : le prix de revient fiscal est une **moyenne pondérée**, que les
ventes ne modifient pas. Les frais de la **vente**, eux, n'y entrent pas : ils se déduisent du
prix de cession.

> **Où le vérifier :** les colonnes `capital_fiscal_apres` et `prix_de_revient_fiscal_apres` de
> `journal.csv`. Sur chaque ligne, le capital fiscal se suit exactement comme le capital
> investi, une colonne à côté.

**Et quand l'histoire est trouée** ([D-45](../decisions.md)) : si des parts sont entrées sans
prix connu, **aucun** des deux prix de revient n'est affiché. Le fiscal se tait exactement quand
l'autre se tait.

### A.5 — L'impôt du compte-titres : les pertes comptent

Deux lignes en CTO, vendues aujourd'hui. Les frais de vente sont de 1,00 € par ligne.

| | Calcul | Résultat |
|---|---|---|
| Ligne A, prix de revient fiscal | 10 × 99,90 + 1,00 de frais | 1 000,00 € |
| Ligne A, cession nette | 10 × 150,00 − 1,00 | 1 499,00 € |
| **Ligne A, plus-value** | 1 499,00 − 1 000,00 | **+499,00 €** |
| Ligne B, prix de revient fiscal | 20 × 49,95 + 1,00 | 1 000,00 € |
| Ligne B, cession nette | 20 × 40,00 − 1,00 | 799,00 € |
| **Ligne B, moins-value** | 799,00 − 1 000,00 | **−201,00 €** |
| **Base imposable** | 499,00 − 201,00 | **298,00 €** |
| **Impôt estimé** | 298,00 × 31,4 % | **93,57 €** |

**Deux règles à vérifier :**
- **les pertes se déduisent des gains** : c'est la loi, et c'est ce qui fait qu'un portefeuille
  mi-figue mi-raisin paie moins qu'il n'y paraît ;
- **si le total est négatif, l'impôt est zéro**, jamais un remboursement. Le rapport montre
  alors la somme négative *et* la base à zéro, pour que tu voies les deux.

### A.6 — L'impôt du PEA : cinq ans changent tout

Le PEA ne s'impose pas titre par titre, mais **au niveau du plan** : sur son gain total.

Un PEA avec : 9 000 € d'achats, 10 € de frais, 200 € de dividendes encaissés, et des titres
valant aujourd'hui 12 000 €.

| | Calcul | Résultat |
|---|---|---|
| Plus-value latente | 12 000 − 9 000 | 3 000,00 € |
| Dividendes reçus (brut) | | 200,00 € |
| Coûts payés dans le plan | frais et taxes | −10,00 € |
| **Gain du plan** | 3 000 + 200 − 10 | **3 190,00 €** |

Et maintenant, **le même gain, deux impôts** :

| Ancienneté du plan | Taux | Impôt | Conséquence |
|---|---|---|---|
| **Moins de 5 ans** | 31,4 % | **1 001,66 €** | retirer **clôture le plan** |
| **5 ans ou plus** | 18,6 % | **593,34 €** | retraits partiels possibles, le plan reste ouvert |

**L'écart est de 408,32 € sur le même portefeuille.** C'est le chiffre qui justifie toute la
vue : attendre le cinquième anniversaire du plan change le résultat de 12,8 points.

**Pourquoi l'application te demande une date.** L'ancienneté se compte depuis le **premier
versement**, et cette date n'est nulle part dans ton export de façon sûre : un PEA fermé puis
rouvert repart de zéro, un PEA transféré garde sa date d'origine. Sans elle, l'impôt du PEA
affiche « non calculable » et te dit où l'écrire ([D-59](../decisions.md)).

**Ce que l'approximation suppose** (le rapport l'écrit) : aucun retrait passé, ni intérêt ni
frais sur les espèces du plan, et tout mouvement d'espèces correspond à une opération connue.
La démonstration est dans [couts-et-fiscalite.md](../couts-et-fiscalite.md) §5.3.

> **Une ligne entièrement vendue compte aussi** : sa plus-value réalisée fait partie du gain du
> plan. C'est pour cela que `valeur_reelle.csv` garde les positions soldées.

### A.7 — L'impôt de la crypto : un seuil, et une règle à part

| | Calcul | Résultat |
|---|---|---|
| Acheté | 1 unité à 1 000,00 € (+ 1,00 € de frais) | 1 000,00 € de prix d'acquisition |
| Cession nette | 1 500,00 − 1,00 de frais | 1 499,00 € |
| **Base imposable** | 1 499,00 − 1 000,00 | **499,00 €** |
| **Impôt estimé** | 499,00 × 31,4 % | **156,69 €** |

**Le seuil :** si le total de tes cessions crypto de l'année ne dépasse pas **305 €**, tout est
**exonéré**. Le rapport l'écrit alors en toutes lettres. Un euro au-dessus, et tout redevient
imposable.

⚠️ **Le seuil compte l'année entière.** Si tu as déjà vendu 200 € de crypto en mars et que la
vente simulée en ferait 200 € de plus, le total est de 400 € : plus d'exonération. L'application
additionne les ventes déjà faites dans l'année civile, et le dit dans la règle. *(Défaut trouvé à
la relecture indépendante : la première version ne regardait que la vente simulée, et annonçait
« exonéré » à tort — une erreur qui donne zéro, donc qu'on ne voit pas.)*

**Trois différences avec le CTO, toutes affichées :**
- les **frais d'achat n'entrent pas** dans le prix d'acquisition : la loi ne les nomme pas, et
  l'application retient la lecture prudente (celle qui ne te fait pas payer moins qu'il ne
  faut) ;
- la loi compte **tout** ton portefeuille crypto, où qu'il soit. L'application suppose que tout
  est chez Trade Republic ;
- après une vente partielle passée, la loi réduit le prix d'acquisition **en valeur** ;
  l'application le réduit au prorata des unités. Identique tant que tu n'as pas vendu une partie
  d'une crypto.

### A.8 — La valeur réelle, ligne par ligne

10 parts d'un ETF en CTO valant 30,00 €, achetées 20,00 € avec 1,00 € de frais.

| | Calcul | Résultat |
|---|---|---|
| Valeur brute | 10 × 30,00 | 300,00 € |
| − frais de vente estimés | 1 € par ligne vendue | −1,00 € |
| − écart de prix estimé | 300,00 × 0,05 % | −0,15 € |
| = ce que la vente rapporterait | | 298,85 € |
| Prix de revient fiscal | 200,00 + 1,00 | 201,00 € |
| Base imposable | 298,85 − 201,00 | 97,85 € |
| − impôt estimé | 97,85 × 31,4 % | −30,72 € |
| **VALEUR RÉELLE** | 298,85 − 30,72 | **268,13 €** |

**L'écart entre la valeur brute et la valeur réelle est de 31,87 €**, soit 10,6 % de la valeur.
C'est ce que la sortie coûterait, et c'est précisément ce que la synthèse brute ne montre pas
([D-23](../decisions.md)).

**Refais-le toi-même** dans `valeur_reelle.csv` : une ligne par position, puis une par poche
(c'est là qu'est l'impôt, parce qu'il se calcule sur la poche entière), puis le total.

### A.9 — Ce que le programme refuse de calculer, et pourquoi

| Situation | Ce qui s'affiche |
|---|---|
| Un actif **sans cours** ([D-53](../decisions.md)) | il sort de la valeur réelle, qui est marquée **PARTIEL**, avec son nom |
| Un actif **sans type déclaré** | aucun spread estimé, donc **pas de valeur réelle** pour lui, et le rapport dit de compléter `actifs.toml` |
| Un ETF **sans TER validé** | pas de frais courants, avec le motif — jamais un zéro |
| Un **PEA sans date** de premier versement | impôt « non calculable », et le rapport dit dans quel fichier l'écrire |
| Un **PEA dont une ligne n'a pas de cours** | **aucun** impôt pour la poche entière : le gain du plan ne se calcule pas à moitié |
| Un **PEA presque entièrement vendu** | aucune valeur réelle pour la poche, avec la raison : l'essentiel de son gain est déjà en espèces, hors de ce que l'application voit |
| Une **histoire trouée** ([D-45](../decisions.md)) | les chiffres, marqués **NON FIABLE** |
| Un **TER hors de 0,03 %–1,00 %** dans ton fichier | refusé à la lecture, comme une erreur d'unité (0,20 % s'écrit `0.20`) |

**Rien n'est jamais remplacé par zéro en silence.** C'est la même règle qu'aux étapes
précédentes.

---

## B. Contrôles sur tes vraies données

```
uv run dashboard actifs              propose le type et le TER de chaque actif
uv run dashboard positions           les trois nouveaux blocs, après les anciens
uv run dashboard exporter-positions  huit CSV, dont couts.csv et valeur_reelle.csv
```

Aucune de ces commandes ne demande ton PIN : **rien ne passe par Trade Republic**
([D-49](../decisions.md)).

### B.1 — D'abord : déclarer le type et le TER de tes actifs

`dashboard actifs` te propose désormais, pour chaque actif, son **type** (d'après la source de
cours) et son **TER** (d'après la liste des ETF de Xetra). Ouvre le fichier et relis chaque
ligne :

- [ ] chaque actif a un **type** (`etf`, `action` ou `crypto`). Sans lui, il n'aura ni spread
      estimé ni valeur réelle ;
- [ ] pour chaque ETF, le **TER proposé** est celui de la fiche de l'émetteur. **C'est le
      contrôle que la feuille de route te demande** : prends deux ou trois de tes ETF, va sur la
      page de l'émetteur (ou son document d'information clé), et compare ;
- [ ] un ETF **français de type « PEA »** n'aura probablement aucune proposition : la liste de
      Xetra ne les contient pas. Écris la valeur à la main.

> **Pourquoi te faire relire :** la liste de Xetra est en retard sur environ **5 % des lignes**,
> toujours dans le sens « trop élevé » — un ETF dont les frais ont baissé y garde son ancien
> taux. C'est mesuré, pas supposé ([couts-et-fiscalite.md](../couts-et-fiscalite.md) §2.3).

### B.2 — Puis : déclarer l'ancienneté de ton PEA

Crée le fichier `fiscalite.toml` dans ton dossier de configuration
(`uv run dashboard emplacements` dit où il est) :

```toml
[pea]
premier_versement = 2024-03-15
```

- [ ] la date est celle de ton **premier versement** sur le PEA **actuel** (un plan rouvert
      repart de sa réouverture) ;
- [ ] elle s'écrit `AAAA-MM-JJ`, **sans guillemets** ;
- [ ] relance `positions` : l'impôt du PEA doit apparaître, avec le bon taux (18,6 % au-delà de
      cinq ans, 31,4 % en dessous) et la date citée dans la règle.

### B.3 — Le contrôle principal : les coûts que tu as vraiment payés

Dans le bloc **« Coûts payés du … au … »** :

- [ ] le **total payé** est le même que celui du bloc « Coûts réellement payés » juste au-dessus
      (quand la période couvre tout) ;
- [ ] les trois niveaux — entrée, sortie, revenus — s'additionnent en ce total ;
- [ ] pour deux ou trois opérations, compare les **frais** avec ce que ton application Trade
      Republic affiche pour le même ordre ;
- [ ] le **poids** d'un ordre ponctuel de petite taille te paraît-il élevé ? C'est l'information
      que la vue existe pour donner.

Dans `couts.csv` : additionne la colonne `cout_paye`, elle doit valoir le total affiché.
Recalcule un `poids` en divisant `cout_paye` par `montant_brut`.

### B.4 — Les coûts estimés : à valider, pas à croire

- [ ] le **spread estimé** total te paraît-il plausible ? Les taux par défaut sont 0,05 % par
      côté sur un ETF, 0,10 % sur une action, 0,50 % sur une crypto. Ils viennent de mesures
      publiées, pas de Trade Republic, qui ne publie rien ;
- [ ] si tu détiens un **ETF de niche**, une **petite capitalisation** ou un **altcoin**, leur
      spread réel est plus large. Tu peux leur donner leur propre taux dans `actifs.toml`
      (`spread_pour_cent = 0.25`) ;
- [ ] les **frais courants** annuels de tes ETF : additionne-les mentalement sur dix ans, et
      compare au gain espéré. C'est l'ordre de grandeur qui compte, pas le centime.

> **Un moyen de vérifier le spread, une fois par an :** Trade Republic doit te fournir une
> « information sur les coûts ex post », qui inclut « les majorations incorporées dans le prix
> de transaction ». Compare-la au spread estimé de l'année. Et depuis juillet 2026,
> l'application de la banque affiche l'écart achat/vente avant que tu ne passes un ordre : note-le
> sur quelques ordres et compare au taux par défaut.

### B.5 — La valeur réelle

- [ ] les cinq lignes de chaque poche se suivent : valeur brute, moins les frais, moins l'écart
      de prix, moins l'impôt, égale la valeur réelle ;
- [ ] pour la poche **CTO**, refais la base imposable : somme de (valeur − prix de revient
      fiscal) sur tes lignes, avec `valeur_reelle.csv` ;
- [ ] pour le **PEA**, refais le gain du plan : plus-value latente + plus-values réalisées +
      dividendes − frais − taxes. Les quatre composantes sont affichées ;
- [ ] pour la **crypto**, si tu vends moins de 305 € dans l'année, l'impôt doit être zéro et le
      rapport doit dire « exonéré » ;
- [ ] si la ligne **MINORÉE** apparaît, lis-la : elle veut dire que tu toucherais **plus** que
      le chiffre affiché. L'impôt du PEA porte sur le gain du plan, dont une partie est déjà en
      espèces (tes ventes passées, tes dividendes) ; cet argent n'est pas compté dans la valeur,
      son impôt l'est. Le montant concerné est indiqué ;
- [ ] lis les **hypothèses** en bas du bloc. Si l'une est fausse chez toi (un retrait passé sur
      le PEA, de la crypto ailleurs que chez Trade Republic), le chiffre de cette poche est à
      prendre avec prudence : **dis-le, ça deviendra une question ouverte ou un test**.

### B.6 — Ce que les anciens chiffres doivent devenir : rien

C'est le contrôle de non-régression, et il est important :

- [ ] la **valeur totale**, le **gain**, le **TRI** et le **TWRR** sont **exactement** les mêmes
      qu'avant l'étape 6. Aucun coût estimé n'entre dans la performance
      ([D-21](../decisions.md)) ;
- [ ] le **capital net investi** et le **prix de revient** de chaque actif sont inchangés. Le
      prix de revient **fiscal** est un chiffre **de plus**, dans une colonne à côté
      ([D-57](../decisions.md)).

### B.7 — Ce que toi seul peux vérifier

Deux choses ne sont pas vérifiables depuis cette machine, et elles sont écrites ici pour que tu
ne les oublies pas :

1. **La grille tarifaire française de Trade Republic.** Le document public refuse les
   téléchargements automatiques : les montants retenus (1 € par ordre à l'achat comme à la
   vente, 0 € par exécution de plan, 1 € par ordre crypto) viennent de la version allemande et
   du communiqué de juillet 2026. **Ouvre la liste des prix dans ton application** (Profil →
   Documents légaux) et vérifie ces quatre montants, ainsi que la présence éventuelle de frais
   de transfert.
2. **Les taux fiscaux.** Ils sont sourcés sur Légifrance, le BOFiP et impots.gouv.fr, et le
   principal (31,4 %) a été recoupé. Tu as choisi de t'en tenir là plutôt que de demander à un
   tiers : si un jour tu fais relire ces règles, `dashboard_tr/parametres/fiscalite.toml`
   contient chaque taux avec sa source, et corriger un chiffre ne demande aucune ligne de code.

---

## Ce que cette étape ne vérifie pas

- **Le montant exact de l'impôt que tu paierais.** C'est une estimation, sur des hypothèses
  affichées. Elle ne connaît ni tes moins-values reportées des années précédentes, ni tes autres
  comptes, ni ton option pour le barème si tu l'avais choisie ([D-60](../decisions.md)).
- **Le spread réellement payé.** Il n'existe dans aucune donnée : seule une comparaison avec le
  carnet d'ordres à la seconde de l'exécution le donnerait, et Trade Republic ne le fournit pas.
- **Les frais courants réellement prélevés.** Le TER est un taux annoncé ; le coût réel d'un
  fonds peut s'en écarter légèrement.
- **La diversification** de tes actifs : étape 7. **L'interface** : étapes 8 et 9.
