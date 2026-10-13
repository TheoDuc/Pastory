# Questions ouvertes

Arbitrages en attente du propriétaire. Une question tranchée est déplacée dans la section
« Tranchées » avec la réponse, et la décision correspondante est ajoutée à
[decisions.md](decisions.md).

Chaque question donne le contexte, les options et une recommandation. **La recommandation n'est
pas une décision.**

---

## En attente

### Q-54 · Actions gratuites puis « migration » : que s'est-il passé ?
*Ouverte le 2026-10-05, en lisant l'export officiel d'un second utilisateur.*

*Enquête du 2026-10-05 : le mécanisme est presque élucidé (ci-dessous) ; reste à choisir le
traitement.*

**Le cas.** Une grande société française attribue **une action gratuite pour dix détenues**, une
opération courante chez les épargnants français. L'ami du propriétaire en détenait **moins de
dix**, sur son **PEA** : il n'avait donc droit qu'à une **fraction** d'action. L'export contient,
pour cette opération, **trois lignes** (et non deux, comme on l'avait d'abord cru) :

| Jour | Ligne | Ce qu'elle porte |
|---|---|---|
| J | `CORPORATE_ACTION / BONUS_ISSUE` | + la fraction (exactement un dixième des parts détenues), sans prix ni montant |
| J | `CASH / MANUAL`, sur le PEA | un crédit d'espèces en euros, **sans ISIN** ; sa description parle de « fraction » et de « corporate action » |
| J + 30 | `DELIVERY / MIGRATION` | − la même fraction, avec un prix, sans montant |

Exemple fictif : 7 actions détenues → `BONUS_ISSUE` de 0,7 ; `MANUAL` de 112,00 € (0,7 × 160 €) ;
30 jours plus tard, `MIGRATION` de −0,7 au prix de 164 €.

**Ce qui est établi** (vérifié sur l'export, sans en lire les valeurs) :
- les actions entières sont toutes restées : seule la fraction est repartie ;
- le crédit d'espèces divisé par la fraction donne un prix dans la fourchette du cours de
  l'action. Il est proche (entre 1 et 5 %) de quantité × prix de la `MIGRATION`, sans être égal :
  ce prix-là est celui du jour J + 30 ;
- c'est la seule ligne `MANUAL` de tout l'export ;
- **sur le PEA, toutes les autres quantités sont entières**, y compris les achats mensuels d'un
  ETF par plan d'épargne, alors que le compte-titres ordinaire en a des dizaines de
  fractionnaires. Trade Republic ne semble pas garder de fraction sur un PEA ;
- **l'application ne montre que la réception des actions gratuites** (événement « actions
  reçues », daté J + 3). Le crédit d'espèces et la sortie des parts n'y apparaissent pas. Le
  titulaire du compte croyait donc **avoir perdu de l'argent**.

**Ce qui reste supposé :**
- que le crédit `MANUAL` paie bien cette fraction. Le lien tient à la date, au compte, à la
  description et au montant cohérent, mais la ligne n'a pas d'ISIN ;
- la raison du délai de 30 jours. Le Code de commerce (art. L.225-130 et R.225-130) prévoit que
  les fractions d'une attribution gratuite ne sont pas livrées : les actions correspondantes sont
  vendues, et le produit est versé aux ayants droit **au plus tard 30 jours** après l'inscription
  des actions entières. Ici, Trade Republic aurait **avancé** l'argent le jour J, puis retiré les
  droits à la vente, à J + 30 ;
- ce qui se passe sur un **compte-titres ordinaire**, où Trade Republic garde des fractions, et
  quand une partie de l'attribution tombe en actions entières (12 actions détenues → 1 action
  gratuite + 0,2 indemnisé ?). On ne l'a jamais vu.

Le titulaire n'a pas d'autre information : l'avis d'opération joint à l'événement dans
l'application, ou le support de Trade Republic, pourrait confirmer le premier point.

**Pourquoi c'est important :** la quantité est déjà juste, puisque `BONUS_ISSUE` et `MIGRATION`
s'annulent. Mais le crédit d'espèces est ignoré (les espèces ne sont pas suivies, D-11). Or c'est
la **valeur des actions gratuites**, que l'actionnaire a bien reçue : sans elle, la performance de
la ligne est sous-estimée, et l'utilisateur ne voit nulle part l'argent qu'il a reçu.

**En attendant :** les trois lignes sont **affichées** : `BONUS_ISSUE` et `MIGRATION` comme non
traitées, avec une explication ; `MANUAL` est ignorée comme une ligne d'espèces.

**Options :**
- **(a) Rien de plus.** Les deux lignes de titres restent non traitées tant qu'elles s'annulent,
  et un cas où elles ne s'annulent pas est signalé. La valeur reçue reste invisible.
- **(b) Une vente.** `BONUS_ISSUE` devient des titres reçus (prix au cours du jour, [D-15](decisions.md)),
  et le crédit `MANUAL` devient leur vente, ce qui dégage un gain réalisé. Il faut alors un type
  « titres sortis sans montant » pour la `MIGRATION`, et décider de quel côté passent les 30 jours
  d'écart.
- **(c) Un revenu de l'actif.** Les deux lignes de titres s'annulent (quantité inchangée), et le
  crédit `MANUAL` compte comme un revenu de la ligne, comme un dividende : « valeur de la fraction
  d'action gratuite, versée en espèces ».

Pour (b) comme pour (c), il faut **rattacher à l'action une ligne d'espèces sans ISIN**. On ne
peut pas le faire par sa description (règle 4). Ce serait une **déduction affichée** (règle 6) :
un crédit `MANUAL`, le même jour qu'un `BONUS_ISSUE`, sur le même compte, et le seul ce jour-là.
Si l'appariement est ambigu, rien n'est rattaché, et le crédit est affiché.

**Recommandation (pas une décision) :** (c). C'est le plus simple à vérifier à la main, ça ne
crée pas de vente que l'utilisateur n'a pas passée, et ça rend visible l'argent qu'il croyait
perdu. À trancher par le propriétaire. Un deuxième cas, idéalement sur un compte-titres
ordinaire ou avec plus de dix actions, dirait si le schéma tient.

### Q-60 · Le monétaire, les fonds multi-actifs et l'immobilier : quel contenu ?
*Ouverte le 2026-10-05, en réalisant D-89.*

**Le constat.** extraETF range chaque fonds dans une classe : actions (2), obligations (3),
matières premières (4) — celles-là sont traduites (D-89) —, mais aussi **monétaire** (5
« Geldmarkt »), **multi-actifs** (9 « Portfoliokonzepte ») et **immobilier** (1160
« Immobilien »). L'application ne sait pas où ranger ces trois-là : leur contenu reste « non
trouvé », et l'écran le dit en nommant la classe.

**Pourquoi c'est important :** un ETF monétaire est un placement courant pour la trésorerie d'un
compte-titres. Sans contenu, il dépend de sa composition, que la source décrit mal (un fonds
monétaire à swap y est à 99,9 % en actions : son collatéral, D-64).

**Options :**
- **(a) Une classe « monétaire » à part**, à côté des obligations, hors de la géographie et des
  secteurs, avec son libellé ;
- **(b) Le monétaire avec les obligations** : c'est de la dette à très court terme. Le multi-actifs
  et l'immobilier restent des trous ;
- **(c) Rien de plus** : les trois restent des trous expliqués.

Pour le **multi-actifs**, un contenu unique n'a pas de sens : sa répartition vient de sa
composition, s'il en a une. Pour l'**immobilier** coté, Amundi le range en actions, extraETF à
part.

**Recommandation (pas une décision) :** (a) pour le monétaire, la plus fidèle à l'écran ; le
multi-actifs reste un trou ; l'immobilier compté en actions, comme le fait l'émetteur. Rien ne
presse : aucun des deux portefeuilles connus n'en détient.

### Q-62 · Les semaines sans cours d'un cache déjà construit : faut-il les combler ?
*Ouverte le 2026-10-13, en mesurant l'attente de la première ouverture (D-110).*

**Le constat.** Jusqu'à D-110, une première ouverture par la fenêtre demandait les cours par
petites fenêtres, une par date d'opération. Entre deux fenêtres voisines, quelques jours pouvaient
rester sans cours : mesuré sur la démonstration, **du 7 au 11 septembre**, sur les huit titres.
Sur ces jours-là, la **courbe** reprend le dernier cours connu : elle est plate, puis saute. Le
gain, le TRI, le TWRR et la valeur d'aujourd'hui **ne sont pas touchés** — ils se lisent aux dates
des opérations et à la dernière clôture, qui sont toutes là.

Depuis D-110, un cache neuf n'a plus ce trou. Mais un cache **déjà construit** le garde : Pastory
ne redemande une période que si plus de **dix jours** séparent deux cours connus, parce qu'un
écart plus court peut être un vrai pont (du jeudi au mardi de Pâques : cinq jours). Sont
concernés ceux qui ont ouvert Pastory pour la première fois par la fenêtre avant le 2026-10-13 —
le premier testeur. Le cache du propriétaire, rempli par `pastory cours`, ne l'est pas.

**Options :**
- **(a) Ne rien faire.** Le défaut ne touche que quelques points de la courbe, chez très peu de
  gens, et il disparaît en effaçant le dossier `cache/cours` (les cours sont alors redemandés
  d'un coup) ;
- **(b) Abaisser le seuil du trou à cinq jours.** Les trous existants se comblent seuls à la
  prochaine ouverture. Le prix : un titre réellement suspendu plus de cinq jours ferait
  redemander toute sa suite à **chaque** ouverture, sans jamais la combler ;
- **(c) Combler une fois** : à la première ouverture après la mise à jour, redemander la série
  entière de chaque actif, puis ne plus y revenir. Demande de retenir que c'est fait.

**Recommandation (pas une décision) :** (a), et dire au premier testeur d'effacer son dossier
`cache/cours` s'il veut une courbe sans palier. (b) change une règle qui protège la source, pour
un défaut passé.

---

## Tranchées

### Lot 1 (2026-09-17)
Quand une réponse courte contredisait les explications du propriétaire, les explications ont
prévalu, à sa demande.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-01 Revenus : rendement ou apport ? | a | Rendement pour les revenus **des actifs** (dividendes). Intérêts sur espèces, primes et euro d'activation : **hors périmètre** | D-11, D-14 |
| Q-02 Carte = retrait ? | a | **Hors périmètre** (espèces ignorées) : contradiction résolue | D-11 |
| Q-03 Espèces dans le capital brut ? | a | **Non, espèces exclues** : contradiction résolue | D-11 |
| Q-04 Capital net investi | explication | Montant brut investi, net de frais et taxes, réduit au prorata des ventes | D-12 |
| Q-05 Méthode de prix de revient | a | PMP, mais **hors frais** (cohérent avec Q-04) | D-13 |
| Q-06 Gains relatifs | a | ~~`gain total / capital net investi`~~ → **remplacé** par un gain en € (D-22) | D-22 |
| Q-07 Distribution de capital | b | Réduit le capital net investi | D-14 |
| Q-08 Taxe à l'achat | a | Catégorie « taxes » séparée des frais, **exclue** du capital investi | D-12 |
| Q-09 Achats PEA sans versement | explication | Sans objet : on ne suit plus l'origine de l'argent | D-11 |
| Q-10 PEA transféré chez le tiers | explication | Prix d'achat = cours le jour d'apparition | D-15 |
| Q-11 Trois comptes | explication | PEA ouvert, fermé, rouvert ; l'euro vient de Trade Republic | — |
| Q-12 Poche crypto | a | Code `XF`, déduit et corrigeable | D-16 |
| Q-13 Frais implicites | explication | Estimation : TER depuis une base d'actifs, spread par défaut par type | D-17 |
| Q-14 Cours de marché | explication | Outil Python gratuit, après comparatif | D-18 |
| Q-15 Langues | a | Allemand + français, extensible | D-19 |
| Q-16 Appariement ambigu | — | Sans objet | D-11 |

### Lot 2 (2026-09-17)

| Question | Retenu | Décision |
|---|---|---|
| Q-17 OneDrive | Le projet reste dans OneDrive | D-24 |
| Q-18 PIN | PIN retiré de la ligne de commande ; trois modes de stockage au choix, jamais en clair ; vérifier d'abord ce que stocke pytr ; à l'étape 10 | D-25 |
| Q-19 Hors périmètre | Euro seul, lecture seule, pas de conseil ni de déclaration ; autres banques non prises en charge mais possibles via un format pivot et des adaptateurs | D-26 |
| Q-20 Monte-Carlo | Fonctionnalité indépendante, reportée | D-27 |
| Q-22 Diversification | Sources gratuites et fiables, à rechercher. **Close par le lot 6** (2026-09-27) : extraETF, les 11 secteurs Morningstar, les pays par code ISO | D-28, D-63 |
| Q-23 Frais dans les rendements | **Non** : performance sur montants bruts, frais et taxes à part (recommandation écartée) | D-21 |
| Q-24 Gain total | Trois chiffres clés : gain en €, TRI, TWRR ; synthèse brute + vue « valeur réelle » | D-22, D-23 |
| Q-25 Dividendes | **Bruts** dans la performance ; la retenue va dans les coûts | D-29 |

### Lot 3 (2026-09-26) — les cours de marché
Posées après le [comparatif des sources de cours](sources-de-cours.md), tranchées le même jour.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-27 Place de cotation de référence | a | **Marché principal en euros** (Xetra, Euronext Paris…). Devise attendue déclarée par actif, et un cours dans une autre devise est refusé et signalé. Écart de quelques centimes avec l'application Trade Republic assumé et affiché | D-48 |
| Q-28 Interface tierce interdite par les conditions générales | a | **pytr reste l'unique porte d'entrée**, en connaissance de la clause, et **aucun cours** ne passe par Trade Republic. Lecture seule, connexion à l'initiative de l'utilisateur | D-49 |
| Q-29 Durée de vie d'un cours en cache | a | **Définitif** : un cours écrit n'est jamais redemandé. Une commande explicite vide le cache d'un actif (corrections de la source, *splits*) | D-50 |

### Lot 4 (2026-09-27) — la valorisation et les rendements
Posées dans le plan de l'étape 5, tranchées avec lui.

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-30 Valoriser « aujourd'hui » | a | **La dernière clôture connue, datée** dans le rapport. Aucun prix de séance en cours, rien hors du cache. Le prix courant est à reconsidérer pour l'interface (étape 9) | D-52 |
| Q-31 Un actif sans cours dans les totaux | a | **Totaux sur les actifs valorisés seulement, marqués partiels**, avec la liste de ce qui manque. Jamais un zéro, jamais un total muet pour un seul ticker manquant | D-53 |

Ce que le pivot avait déjà tranché, et que l'étape a seulement aligné dans le glossaire : la
distribution de capital est un **flux positif** dans le gain, le TRI et le TWRR
([format-pivot §3](format-pivot.md), [D-54](decisions.md)).

### Lot 5 (2026-09-27) — les frais, les taxes et la valeur réelle
Posées dans le plan de l'étape 6, après trois recherches
([couts-et-fiscalite.md](couts-et-fiscalite.md)). Le propriétaire a répondu « on part sur tes
recommandations », et, sur la relecture des taux par un tiers : « je ne m'y connais pas, base-toi
sur tes recherches ». Les sept recommandations s'appliquent donc telles quelles, et chacune reste
corrigeable sans toucher au code ([D-58](decisions.md)).

| Question | Retenu | Décision |
|---|---|---|
| Q-32 Comment connaître le type d'un actif ? | **Déclaré** dans `actifs.toml`, proposé par l'assistant. Le champ `instrumentType` de l'export est écarté : il n'existe que sur les ordres | D-55 |
| Q-33 Quels spreads par défaut ? | **Par côté** : ETF 0,05 %, action 0,10 %, crypto 0,50 %, chacun avec sa fourchette dans le fichier ; un actif peut recevoir son propre taux. L'heure de l'ordre n'est pas prise en compte | D-56 |
| Q-34 D'où vient le TER ? | La liste des ETF de **Xetra**, proposée puis **validée**. Les ETF français « PEA » en sont absents : saisie à la main | D-61 |
| Q-35 Quelle base pour l'impôt du CTO ? | Les **plus-values latentes** seulement, compensées, plancher à zéro. Les plus-values déjà réalisées de l'année et les dividendes déjà reçus restent dehors | D-60 |
| Q-36 Comment estimer l'impôt du PEA ? | Le **gain du plan** approché depuis les titres, sur une **date de premier versement déclarée**. Hypothèses affichées | D-59 |
| Q-37 Comment traiter la crypto ? | Prix d'acquisition **hors frais** (lecture prudente), réduction **au prorata des parts** au lieu de la valeur, seuil de 305 € appliqué à la valeur vendue, tout supposé chez Trade Republic. Les trois approximations sont affichées | D-60 |
| Q-38 Qui valide les taux de 2026 ? | **Personne d'autre que les sources officielles** : le propriétaire ne se sent pas compétent et ne fait pas relire. Les taux sont datés et sourcés dans `parametres/fiscalite.toml`, et le principal (31,4 %) a été recoupé sur impots.gouv.fr | D-58 |

**Ce qui reste à la charge du propriétaire, et qui n'est pas une question mais une vérification :**
ouvrir la **liste des prix française** dans son application (le document public refuse les
téléchargements automatiques) pour confirmer les quatre montants retenus — 1 € par ordre à l'achat
comme à la vente, 0 € par exécution de plan, 1 € par ordre crypto. C'est écrit dans le
[cahier de l'étape 6](verification/etape-6.md) §B.7.

### Lot 6 (2026-09-27) — la diversification
Posées après le [comparatif des sources de composition](composition-des-etf.md) — quatorze familles
de sources examinées, onze interrogées réellement — et tranchées le même jour. **Q-22** est close
par ce lot.

Le propriétaire a d'abord répondu à quatre questions de cadrage, avant la recherche : son
portefeuille contient des **ETF d'actions, des ETF obligataires et de la crypto**, la crypto doit
figurer sur une **ligne à part** hors géographie et hors secteur, les pays doivent être **regroupés
en zones**, et la composition doit se mettre à jour **automatiquement**, sans relecture préalable,
avec sa date et sa source toujours affichées.

| Question | Retenu | Décision |
|---|---|---|
| Q-39 Quelle source de composition ? | **extraETF**, par ISIN, en lisant les **répartitions agrégées** et jamais les lignes détenues. Les émetteurs et justETF servent à **vérifier**, pas à compléter. Limite acceptée : API interne non documentée, usage personnel toléré, échec propre si elle ferme | D-63 |
| Q-40 Pour un ETF synthétique : l'indice ou le panier ? | **L'indice suivi** — l'exposition économique réelle — l'actif étant marqué « synthétique » à l'écran | D-64 |
| Q-41 Quelle nomenclature sectorielle ? | Les **11 secteurs Morningstar**, nommés comme tels et **jamais** « GICS ». Aucune source gratuite par ISIN ne donne du GICS, et deux nomenclatures ne s'additionnent pas | D-65 |
| Q-42 Quelle règle de pays ? | Celle de la source (**pays d'activité**) pour un ETF, le **siège social** pour une action en direct. Les deux cohabitent et l'écran le dit : une répartition géographique n'est pas une grandeur unique | D-66 |
| Q-43 Quelles zones ? | Les **zones d'investisseur** (Amérique du Nord, Europe, Japon, Asie-Pacifique développée, émergents), dans un fichier **daté et sourcé**. Le découpage neutre de l'ONU est écarté : il met la Chine et le Japon dans la même case | D-67 |
| Q-44 Les actions en direct et les ETF obligataires ? | Les actions entrent dans **les deux** répartitions, malgré la règle de pays différente, parce que l'achat d'actions à l'unité est courant sur cette banque. Les ETF obligataires comptent dans une **troisième** répartition, par classe d'actifs, et restent hors des deux autres | D-62, D-68 |
| Q-45 Un actif dont on ne voit pas l'intérieur ? | Affiché **« non couvert »** avec son montant, la répartition étant marquée partielle. Jamais estimé, jamais masqué, jamais renormalisé. Le cas est réel : BNP Paribas Easy, deuxième émetteur d'ETF éligibles au PEA, ne publie rien d'exploitable | D-69 |

**Un arbitrage rendu contre la recommandation, et pour une bonne raison.** Il était recommandé de
**ne pas** traiter les actions en direct, le propriétaire n'en détenant aucune. Il a répondu
l'inverse, en expliquant que le projet doit viser **l'utilisateur type de Trade Republic** et non
son propre portefeuille, puisqu'il compte partager l'application. C'est devenu une évolution de cap
([D-62](decisions.md)), plus large que l'étape 7, et elle vaut désormais pour toutes les étapes
suivantes.

**Ce qui reste à la charge du propriétaire :** ouvrir la **fiche de l'émetteur** de deux ou trois de
ses ETF et comparer ses pays et ses secteurs avec ceux qu'affiche l'application. L'écart attendu
n'est **pas nul** — c'est tout l'objet de Q-41 et de Q-42 — et le
[cahier de l'étape 7](verification/etape-7.md) dit quoi regarder.

### Lot 7 (2026-09-28) — ce que la vérification du propriétaire a soulevé
Posées par le propriétaire en regardant ses propres chiffres, et tranchées le même jour. Les deux
partent du même constat — des actifs annoncés « non couvert » — mais **ce sont deux problèmes de
nature différente**, et les confondre aurait donné une mauvaise correction.

| Question | Retenu | Décision |
|---|---|---|
| Q-46 Un actif qui n'a ni pays ni secteur **par nature** (obligations, matières premières) | Ce n'est **pas** un manque : le propriétaire déclare le **contenu** de l'actif dans `actifs.toml`, à côté du `type` qui reste « etf ». L'actif compte dans sa classe et sort de la géographie et des secteurs, avec un libellé qui l'explique. Les matières premières deviennent une classe à part entière | D-71 |
| Q-47 Un fonds d'**actions** que la source ne sait pas ouvrir | Une **source de secours par actif, nommée à l'écran**. À réaliser à l'**étape 8**, quand la présentation sera conçue : mélanger deux nomenclatures dans un même graphique est interdit (piège n° 16), donc la source doit être visible ligne par ligne | D-72 |

**Le diagnostic qui a séparé les deux cas** (2026-09-28), et qui vaut d'être gardé parce qu'il a
écarté trois fausses pistes :

- ce **n'est pas** un problème de **part** : l'autre part du même compartiment est tout aussi vide ;
- ce **n'est pas** récupérable par une répartition moins fine : les listes par **région** et par
  **marché développé / émergent** sont vides elles aussi pour ces fonds ;
- ce **n'est pas** une lacune générale de la source sur les marchés émergents : deux fonds émergents
  à réplication **physique** ont été testés, avec 35 et 28 pays. La lacune porte sur certains fonds
  **à swap**, fonds par fonds.

**Et une fausse piste écartée dans l'autre sens :** la source publie un champ numérique
`asset_class` qui semblait pouvoir distinguer actions, obligations et matières premières sans rien
déclarer. Le rapprochement s'est révélé **faux sur deux actifs sur trois**. Une déclaration se
vérifie, un code non documenté deviné non ([D-71](decisions.md)).

### Lot 8 (2026-09-30) — la présentation des frais

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-21 Comment présenter les frais et les taxes ? | b | **Un seul écran, les trois niveaux à la file** : ce qui a déjà été prélevé, ce qui court pendant la détention, ce qu'il resterait à la sortie. L'arrangement (a) — deux vues séparées — est écarté après comparaison des deux maquettes | D-73 |

Le propriétaire a comparé les deux arrangements sur la maquette de l'étape 8 et a choisi (b),
contre la recommandation d'origine de Q-21 qui proposait (a). Sa raison : les trois niveaux se
suivent et se lisent d'un trait, là où deux vues séparées obligent à faire des allers-retours
pour répondre à une seule question — combien tout cela coûte.

Cette lecture a immédiatement produit **Q-49** : si les trois niveaux sont une chronologie, la
retenue sur dividendes n'est pas au bon endroit.

### Lot 9 (2026-09-30) — la place de la retenue sur dividendes

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-49 La retenue sur dividendes est-elle un coût d'entrée ? | b | **Le premier niveau est « ce qui a déjà été prélevé »**, quel qu'en soit le moment, et il est nommé ainsi. La retenue y reste. Le découpage porte donc la séparation réel / estimé de D-17, et non une chronologie | D-75 |

Le propriétaire a suivi la recommandation. Ce qui est écarté : (a), la chronologie stricte, qui
aurait descendu la retenue au niveau 2 en y mélangeant un coût réel et une estimation ; et (c), un
quatrième niveau, qui aurait défait le bénéfice de [D-73](decisions.md) — un seul écran qui se lit
d'un trait.

### Lot 10 (2026-09-30) — ce que la recherche de la source de secours a permis de trancher

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-48 « Non transparisé » : le retirer du vocabulaire, ou le faire produire ? | c | **Défini au glossaire, jamais affiché.** Aucune source accessible n'indique qu'un fonds est un fonds de fonds : un tel fonds tombe dans « non couvert », et la bulle de « non couvert » explique que certains fonds détiennent d'autres fonds — sans prétendre que c'est le cas de celui-là | D-76 |

La recommandation d'origine de Q-48 était conditionnelle — (b) **si** la recherche montrait qu'une
source l'indique de façon fiable, sinon (a). La recherche a répondu **non** : extraETF n'a que six
classes d'actifs et un fonds de fonds y tombe dans `other`, qu'un garde-fou refuse déjà ; le service
d'Amundi a un vocabulaire d'**instruments**, pas de véhicules. Le propriétaire a alors préféré (c) à
(a) : la notion explique **pourquoi** un fonds peut être non couvert, et un trou expliqué vaut mieux
qu'un trou muet.

### Lot 11 (2026-10-05) — la porte d'entrée de l'export officiel

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-50 Sans pytr, que devient la photo du portefeuille ? | a | **pytr est retiré entièrement**, après la comparaison des deux adaptateurs ; les quantités se comparent à l'écran de la banque | D-81 |
| Q-51 Le type d'un actif : donnée ou proposition ? | a | **Donnée de la banque** : `FUND` → ETF, `STOCK` → action, `CRYPTO` → crypto ; toute autre valeur est affichée | D-82 |
| Q-52 Le contrôle du montant réglé perd son second avis | b | **`montant_regle` reste vide** ; le contrôle `quantité × prix = montant` reste | D-83 |
| Q-53 Le brut des dividendes néerlandais est déjà net de la retenue des Pays-Bas | a | **Le brut est celui de la banque**, et la limite est affichée en face des dividendes | D-84 |
| Q-26 Aller chercher le second compte-titres, pour rapprocher le PEA ? | — | **Sans objet** : le rapprochement disparaît avec pytr | D-81 |

Le propriétaire a suivi les quatre recommandations. Q-53 est née pendant l'étape, en comparant
l'export officiel d'un second utilisateur à son export pytr : c'est la seule question où le
fichier officiel donne **moins** d'information que pytr. Pour Q-52, le propriétaire n'a pas eu
besoin de regarder le débit réel de son achat de crypto : la comparaison sur 72 opérations du
second utilisateur a montré que brut ± frais ± taxes retombe exactement sur ce que pytr annonçait
comme réglé.

### Lot 12 (2026-10-05) — des réglages qui se proposent seuls

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-55 Le contenu d'un fonds : peut-on le trouver ? | a | **extraETF, code et libellé ensemble, recoupé par le code CFI de l'ESMA**. Un désaccord donne un trou avec les deux réponses ; un contenu « actions » est montré sans s'appliquer | D-89 |
| Q-56 La date d'ouverture du PEA : laquelle retenir ? | — | **Le premier crédit du plan en cours** : une sortie d'espèces avant cinq ans clôt le plan, le crédit suivant en ouvre un nouveau | D-86 |
| Q-57 Le TER des ETF iShares « Swap PEA », absents de Xetra | a | **Écarté** : la liste de BlackRock n'a pas de date (D-58), et une part couverte s'écarte de son DIC. Le trou est affiché | D-90 |
| Q-58 Une action américaine : Xetra ou Francfort ? | a | **Francfort**, qui cote jusque vers 22 h ; la place ne départage que des cotations à écart comparable | D-88 |
| Q-59 Les versements et retraits du PEA : jusqu'où s'en servir ? | a | **Vérifier l'hypothèse** « aucun retrait passé », sur les seules dates. Le calcul du gain comme le fisc, qui lirait les montants, n'est pas retenu | D-87 |

Le propriétaire a suivi quatre recommandations sur cinq. Pour Q-56, aucune des trois options
proposées n'était la bonne, et c'est **sa réponse** qui a donné la règle : il avait ouvert son PEA,
l'avait fermé et rouvert six jours plus tard, et la date qui compte est celle de la réouverture.
La première règle essayée — le premier versement — la manquait d'une semaine. Q-55 revient sur
D-71, à partir d'une mesure refaite sur ses propres fonds : le code d'extraETF, lu avec son
libellé, y est juste cinq fois sur cinq.

### Lot 13 (2026-10-09) — les hypothèses de la prédiction de l'évolution

| Question | Réponse | Retenu | Décision |
|---|---|---|---|
| Q-61.1 Que veut dire le taux avec l'aléa ? | a | **La médiane** : la courbe du milieu retombe sur la courbe sans aléa | D-105 |
| Q-61.2 La loi des rendements | a | **Log-normale, mois par mois, indépendante** ; l'écran dit qu'elle sous-estime les krachs | D-105 |
| Q-61.3 Le lien entre le taux et la dispersion | — | **Pas de valeur historique** : volatilité = **2 × taux** (réponse du propriétaire, voir ci-dessous) | D-105 |
| Q-61.4 Ce que contient le taux | a | **Nominal**, avant impôt, frais et inflation, dit à l'écran | D-105 |
| Q-61.5 Le hasard est-il fixé ? | — | **Graine fixe** (recommandation retenue d'office : elle rend le résultat vérifiable) | D-105 |

Pour Q-61.3, le propriétaire a écarté les trois options : il ne voulait **aucune valeur
historique**, seulement que la dispersion grandisse avec le taux visé — « les obligations ont un
taux faible et sont peu risquées, le bitcoin un rendement plus important mais des performances bien
plus aléatoires ». Parmi trois règles chiffrées, il a retenu la plus simple : volatilité = deux
fois le taux.
