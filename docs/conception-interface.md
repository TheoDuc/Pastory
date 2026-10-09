# Conception de l'interface

> **Ce document est le contrat de l'étape 9.** Il dit *ce qui s'affiche, où, et sous quels mots*.
> Il ne dit pas comment l'écrire en Dash : c'est le travail de l'étape 9.
>
> Écrit à l'**étape 8**, complété à l'**étape 8 bis**. Dernière mise à jour :
> **2026-10-08** — le §6 est réécrit au début de l'étape 9 : les écrans de réglages deviennent des
> écrans de **correction**, facultatifs, puisque tout est trouvé seul ([D-80](decisions.md),
> [D-94](decisions.md)). Avec les §4 (les écrans retenus) et §5 (leurs quatre états), **le
> document est complet : l'étape 9 peut s'appuyer dessus.**
>
> **2026-10-09, étape 9 bis :** l'identité « livre relié » ([D-98](decisions.md)) change la
> **forme** des écrans, pas ce qu'ils portent : la couverture, les chapitres numérotés, le signet,
> le colophon (§4.1), et la valeur des actifs en tête de la synthèse ([D-99](decisions.md), §4.2).
> Ce qui touche à l'apparence — couleurs, polices, graphiques, animations — est dans la
> [charte graphique](charte-graphique.md), qui fait référence.
>
> Comme tout le dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)). Les chiffres
> qui l'illustrent sont inventés.

## Sommaire

| § | Contenu |
|---|---|
| [1](#1-linventaire--ce-que-le-moteur-produit-et-où-ça-saffiche) | **L'inventaire** : chaque chose que le moteur produit, et l'écran qui la porte |
| [2](#2-le-vocabulaire-décran) | **Le vocabulaire d'écran** : les mots que l'utilisateur va lire sans les avoir choisis |
| [3](#3-les-règles-daffichage) | **Les règles d'affichage** : unités, alignement, troncature, couleurs |
| [4](#4-les-écrans-retenus) | **Les écrans retenus** : les quatre onglets, la page « Détail des calculs », et ce que chacun porte |
| [5](#5-les-quatre-états-de-chaque-écran) | **Les quatre états** de chaque écran : vide, partiel, estimé, en erreur — et ce qu'aucun n'autorise |
| [6](#6-les-écrans-de-correction) | **Les écrans de correction** : tout est trouvé seul, tout se corrige à l'écran, rien ne s'édite en fichier ([D-78](decisions.md), [D-80](decisions.md)) |

---

## 0. Les cinq principes, et d'où ils viennent

1. **Un signalement qu'on n'affiche pas n'existe pas** (règle 6). C'est le défaut trouvé en
   relecture à l'étape 7 : un signalement calculé, transporté, et perdu. Le §1 est la liste de
   contrôle qui l'empêche de se reproduire.
2. **Rien n'est renormalisé à 100 %** ([D-69](decisions.md)). Une répartition honnête ne fait pas
   le tour du cercle. **La part manquante est une information, pas un défaut de présentation.**
3. **Un chiffre porte sa source et sa date** ([D-58](decisions.md), [D-63](decisions.md)). Un taux
   estimé sans date ni source est refusé par le moteur ; à l'écran, il ne s'affiche jamais nu.
4. **Tout doit pouvoir se refaire à la main.** Le propriétaire ne code pas : il vérifie les
   chiffres. Chaque estimation montre son calcul, chaque pourcentage montre son dénominateur.
5. **On écrit pour quelqu'un qui découvre** ([D-62](decisions.md)). Les messages d'absence sont du
   contenu d'interface à part entière, pas des notes techniques reléguées en bas de page.

---

## 1. L'inventaire : ce que le moteur produit, et où ça s'affiche

Relevé le 2026-09-29 sur `pastory/moteur/`. **Colonne « aujourd'hui »** : `rapport` si le
rapport texte le montre déjà, `CSV` s'il n'existe que dans un export, `—` s'il n'est nulle part.

Les écrans nommés ici sont ceux des notes du propriétaire : **Synthèse**, **Les actifs**,
**Diversification**, **Frais et taxes**, **Valeur réelle**. La répartition définitive entre onglets
dépend des arbitrages sur les maquettes ; les *contenus*, eux, sont fixés.

### 1.1 Le bandeau permanent — les filtres et l'état des données

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Période retenue, et son origine (« depuis le premier achat ») | `Rendements.periode`, `.origine` (`rendements.py:365`) | rapport |
| Poches filtrées (PEA, CTO, crypto) | `Portefeuille.par_poche()` (`portefeuille.py:120`) | rapport |
| Date des cours : « arrêté au 12/09/2026 » | `Valorisation.date` (`valorisation.py:160`) | rapport |
| Source des cours, dédoublonnée | `Valorisation.sources` (`valorisation.py:190`) | rapport |
| Fourchette des arrêtés de composition : « du 31/07 au 31/08/2026 » | `Diversification.arrete_du` / `.arrete_au` | rapport |
| **Bouton « Détail des calculs »**, qui mène entre autres au panneau du §1.7 (le compteur prévu a été retiré à l'étape 9) | Les trois listes de `Signalement` | rapport |

### 1.2 Synthèse

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| **Gain en €** — le chiffre principal ([D-22](decisions.md)) | `Rendements.gain` (`rendements.py:333`) | rapport |
| **TRI** | `Rendements.tri` (`rendements.py:334`) — **un taux** | rapport |
| **TWRR**, et son annualisé | `Twrr.taux`, `.annualise` (`rendements.py:278`) — **des taux** | rapport |
| « Peu significatif sur moins d'un an » sur le TRI et le TWRR | `Rendements.peu_significatif` (`rendements.py:380`) | rapport |
| Pourquoi un chiffre clé manque | `.motif`, `.motif_tri`, `Twrr.motif` | rapport |
| **La courbe : capital brut et capital net investi** | **`evolution()` → `PointEvolution`** (`valorisation.py:261`) | **CSV** |
| La courbe par poche | `PointEvolution.par_poche` | **CSV** |
| Les jours où la valeur est partielle | `PointEvolution.non_valorisees` | **CSV** |
| Valeur totale des actifs, et par poche | `Valorisation.total`, `.par_poche()` | rapport |
| Capital net investi, total et par poche | `Totaux.capital_net_investi` (`portefeuille.py:28`) | rapport |
| Total marqué **partiel**, et la liste de ce qui manque | `TotauxValeur.complet`, `Valorisation.non_valorisees` | rapport |
| Les mêmes trois chiffres **par poche** | `Synthese.par_poche` | rapport |
| **`peu_significatif`, `partiel`, `fiable` par poche** | `Synthese.par_poche[…]` — lus aujourd'hui sur le seul total | **—** |
| Décomposition du TWRR, période par période | **`Twrr.sous_periodes`** (`rendements.py:238`) | **CSV** |
| La table du TRI, ligne à ligne, pour la refaire à la main | **`Rendements.table_du_tri`** (`rendements.py:406`) | **CSV** |

### 1.3 Les actifs

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Nom, code, poche | `Position.nom_actif`, `.actif`, `.poche` | rapport |
| Quantité détenue | `EtatPosition.quantite` | rapport |
| Prix de revient (PMP hors frais, [D-13](decisions.md)) | `EtatPosition.prix_de_revient` | rapport |
| Capital net investi de la ligne | `EtatPosition.capital_net_investi` | rapport |
| Cours retenu, sa date, sa place | `PositionValorisee.cours` | partiel |
| Valeur de la position | `PositionValorisee.valeur` | rapport |
| **Plus-value latente** | **`PositionValorisee.plus_value_latente`** (`valorisation.py:110`) | **CSV** |
| Gain de la ligne | `Synthese.de(position).gain` | rapport |
| **TRI et TWRR de la ligne** | **`Synthese.par_position`** (`rendements.py:611`) | **CSV** |
| Pourquoi la ligne n'est pas valorisée | `PositionValorisee.motif` | rapport |
| Dividendes bruts, et la retenue prélevée | `Position.dividendes_bruts` / **`.dividendes_taxes`** | partiel |
| Plus-values déjà réalisées | `Position.plus_values_realisees_brutes` / `_nettes` | rapport |
| Distributions de capital | `Position.distributions_capital` | rapport |
| Ligne dont l'histoire est trouée | `EtatPosition.historique_incomplet` | rapport |
| **Le journal de la ligne**, opération par opération | **`LigneJournal`** (`position.py:147`) | **CSV** |
| Prix de revient **fiscal** et capital fiscal | `EtatPosition.prix_de_revient_fiscal`, `.capital_fiscal` | **CSV** |
| Tri par évolution ou par valeur (demandé par les notes) | — *(tri d'écran)* | — |

### 1.4 Diversification

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Les trois répartitions : classes d'actifs, pays, secteurs | `Diversification.classes` / `.pays` / `.secteurs` | rapport |
| Chaque poste : libellé, montant, part | `Poste` (`diversification.py:137`), `Repartition.pour_cent()` — **des pour cent** | rapport |
| Les pays regroupés en **zones** | `Repartition.par_zone()`, `Poste.zone` | rapport |
| **Le dénominateur des pourcentages** | **`Repartition.base`** — sans lui, rien n'est vérifiable | **CSV** |
| **Non attribué** | `Repartition.non_attribue` | rapport |
| **Non couvert**, et la liste des actifs concernés | `Repartition.non_couvert`, `.actifs_non_couverts` | rapport |
| **Hors actions**, détaillé classe par classe ([D-71](decisions.md)) | `Repartition.hors_perimetre_postes` | rapport |
| **Le total hors périmètre** | **`Repartition.hors_perimetre`** — seul le détail est montré | **—** |
| Actifs numériques, ni pays ni secteur | `Repartition.hors_classification` | rapport |
| Actifs **synthétiques** : on affiche l'indice ([D-64](decisions.md)) | `Repartition.actifs_synthetiques` | rapport |
| Actifs à composition **déclarée à la main** | `Diversification.declarees_a_la_main` | rapport |
| Code non reconnu par le référentiel | `Poste.reconnu` | rapport |
| **La liste des postes non reconnus** | **`Repartition.postes_non_reconnus`** | **—** |
| Source des données, et intitulé de leur date | `Diversification.sources`, `.intitules_de_date` | rapport |
| La répartition dépasse la part en actions | `Diversification.signalements` | rapport |
| **La source et la règle de pays, ligne par ligne** ([D-72](decisions.md)) | *n'existe pas encore* — phase 5 | **—** |

### 1.5 Frais et taxes

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Frais d'ordre et taxes payés, par période, poche et actif | `TotauxCouts.frais`, `.taxes`, `.cout_paye` | rapport |
| Répartition entrée / sortie | `TotauxCouts.par_moment()` | rapport |
| **Le poids d'un coût dans son opération** (1 € sur 25 € = 4 %) | **`LigneDeCout.poids`** — seule la moyenne est montrée | **CSV** |
| Poids moyen | `TotauxCouts.poids_moyen` — **un taux** | rapport |
| Spread estimé, à l'achat et à la vente ([D-30](decisions.md)) | `LigneDeCout.spread_estime` | rapport |
| **Le calcul de chaque estimation : « 600,00 x 0,05 % = 0,30 »** | **`Estimation.formule`** (`couts.py:119`) — **écrit pour l'écran, jamais branché** | **—** |
| Taux employé, sa date, sa source | `Estimation.parametre` → `ParametreDate` | partiel |
| **La fourchette mesurée d'un taux** | **`ParametreDate.basse` / `.haute` / `.note`** | **—** |
| Frais courants annuels (TER) par actif | `FraisCourantsEstimes.estimation` | rapport |
| Pourquoi un TER manque | `FraisCourantsEstimes.motif` | rapport |
| Actifs sans type déclaré, donc sans spread estimable | `TotauxCouts.actifs_sans_type` | rapport |
| **Les spreads manquants, opération par opération** | **`TotauxCouts.spreads_manquants`** | **—** |

### 1.6 Valeur réelle ([D-23](decisions.md))

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Valeur brute, frais de vente, spread, impôt, **valeur réelle** | `ValeurReelle.*` (`valeur_reelle.py:156`) | rapport |
| Le détail par poche | `ValeurReellePoche` | rapport |
| La règle fiscale appliquée, en une phrase | `ImpotEstime.regle` | rapport |
| La décomposition de la base imposable | `ImpotEstime.composantes` | rapport |
| Ce que le calcul suppose | `ImpotEstime.hypotheses` | rapport |
| Les taux employés, avec date et source | `ValeurReelle.parametres_cites` | rapport |
| Estimation **minorée**, et de combien | `ValeurReelle.minoree`, `.hors_des_titres` | rapport |
| Positions exclues, et pourquoi | `Exclue.motif` | rapport |
| Poche non calculable, et pourquoi | `ValeurReellePoche.motif_incalculable` | rapport |
| **Poche partielle** | **`ValeurReellePoche.partielle`** — seul le total est testé | **—** |
| **Le détail cession par cession** | **`ImpotEstime.cessions`**, `Cession.*` | **CSV** |

### 1.7 Le panneau « à surveiller »

Tout ce que le moteur signale, en un seul endroit, **et** marqué à l'endroit où le chiffre
s'affiche. Les deux : le panneau se parcourt, la marque se remarque.

| Ce qui s'affiche | D'où ça vient | Auj. |
|---|---|---|
| Opération inexploitable, prix à compléter, stock insuffisant, distribution excédentaire | `Portefeuille.signalements` (`position.py:188`) | rapport |
| La référence de l'événement en cause | `Signalement.reference_source` | rapport |
| Poche non couverte, écart de quantité, titres sans opération, parts non confirmées | `Rapprochement.signalements` | rapport |
| **L'écart chiffré du rapprochement** | **`LigneRapprochement.ecart`** (`rapprochement.py:82`) | **—** |
| Refus de cours et de composition, actif par actif | `Refus` (`donnees_externes/cours.py:79`) — **produit hors du moteur**, imprimé par `cli.py` | rapport |
| Types d'événement inconnus (règle 5) | Rapport de lecture de l'adaptateur | rapport |

### 1.8 Ce que l'inventaire a trouvé de cassé

Deux choses n'étaient adossées à rien. **Les deux ont été traitées à l'étape 8 bis**, et elles
restent écrites ici : un défaut trouvé par un inventaire mérite de rester lisible, ne serait-ce que
pour se souvenir qu'un inventaire en trouve.

- **« non transparisé »** (fonds de fonds) était promis par le [glossaire](glossaire.md), la
  [feuille de route](feuille-de-route.md) et le [comparatif](composition-des-etf.md).
  **Aucun champ du code ne le produit**, et la recherche de l'étape 8 bis a montré qu'aucune source
  accessible ne le permettrait. ✅ **Tranché** ([Q-48](questions-ouvertes.md) →
  [D-76](decisions.md)) : la notion reste au glossaire, **aucun écran ne l'emploie**, et un tel
  fonds est affiché « non couvert » — dont la bulle d'aide mentionne que certains fonds en
  contiennent d'autres.
- **La règle de pays** n'était portée par aucune donnée : elle était seulement implicite dans la
  source (`donnees_externes/actions.py` = siège social, `extraetf.py` = pays d'activité), et le
  rapport en disait un texte générique sans jamais dire **quel actif** relevait de quelle règle.
  Or [D-66](decisions.md) demande qu'elle soit affichée, et [D-72](decisions.md) qu'elle le soit
  **ligne par ligne**. ✅ **Corrigé à l'étape 8 bis**, en trois endroits :
  `Composition.regle_de_pays` la porte, `Diversification.origines` la donne **par actif** avec sa
  source, et le rapport comme le CSV `origines_des_compositions.csv` l'affichent — ce dernier
  parce que c'est dans un tableur que le propriétaire vérifie ses chiffres. **Trois règles
  cohabitent** désormais : pays d'activité, siège social, et pays de classification de l'indice
  ([D-77](decisions.md)).

---

## 2. Le vocabulaire d'écran

Les mots que l'utilisateur va lire **sans les avoir choisis**. Chacun a trois formes : la **marque**
(ce qui s'affiche à côté du chiffre, très court), l'**explication** (ce qui s'ouvre au clic ou au
survol, écrit pour quelqu'un qui découvre), et le **lieu**.

Règle : **jamais de marque sans son explication à portée de clic, et jamais d'explication reléguée
en bas de page.** La définition de référence reste le [glossaire §8](glossaire.md) ; ici on écrit
la phrase que l'utilisateur lit.

### 2.1 Les absences — pourquoi un chiffre n'est pas là

| Marque | Explication affichée | Lieu |
|---|---|---|
| **Non couvert** | « Nous n'avons pas la composition de cet actif : la source ne publie rien pour lui, ou ce qu'elle publie n'a pas passé nos contrôles. Son montant est affiché à part et **n'est pas réparti au hasard**. » | Diversification, ligne de reste + liste |
| **Non attribué** | « La part de ce fonds que sa propre documentation n'attribue à aucun pays ni secteur : liquidités, produits dérivés, lignes non classées. Aucun fonds ne somme exactement à 100 %. » | Diversification, ligne de reste |
| **Hors actions** | « Cette part du portefeuille n'est pas investie en actions. Elle compte dans la répartition par classe d'actifs, mais pas dans les pays ni les secteurs, où ces notions n'ont pas le même sens. » | Diversification, détaillé **classe par classe** |
| **Ni pays ni secteur** | « Les actifs numériques n'ont ni pays ni secteur : ce n'est pas un oubli de notre part. Ils comptent dans la répartition par classe d'actifs. » | Diversification, ligne crypto |
| **Sans cours** | « Aucun cours utilisable à cette date pour cet actif. Sa valeur n'est donc comptée nulle part, et les totaux sont marqués partiels — plutôt que de compter zéro. » | Les actifs, Synthèse |
| **À compléter** | « Cette opération est arrivée sans son montant. Le chiffre est donc incomplet, et l'opération est listée dans « à surveiller » avec sa référence. » | Les actifs, panneau |
| **Sans objet** (« – ») | « Ce chiffre n'a pas de sens ici — ce n'est pas une donnée manquante. » | Partout |
| **Type inconnu** | « Cet événement a un type que l'application ne connaît pas. Il n'est ni ignoré ni rangé au hasard : il est affiché tel quel pour que vous puissiez le signaler. » | Panneau « à surveiller » |

### 2.2 Les réserves — le chiffre est là, mais il faut savoir quelque chose

| Marque | Explication affichée | Lieu |
|---|---|---|
| **Partiel** | « Ce total ne porte que sur les actifs pour lesquels nous avons un cours. Ceux qui manquent sont listés, avec leur nom. » | Tout total |
| **Estimé** | « Ce montant n'a pas été payé : il est calculé à partir d'un taux publié, avec sa date et sa source. Il ne se mélange jamais aux frais réellement prélevés. » | Frais, Valeur réelle |
| **Minorée** | « Cette estimation est volontairement prudente : une partie de l'impôt ne peut pas être calculée depuis les seuls titres, elle est donc laissée de côté. Le vrai montant serait plus bas. » | Valeur réelle |
| **Synthétique** | « Ce fonds ne détient pas les titres de son indice : il en reproduit la performance par un contrat. Nous affichons donc la composition de **l'indice suivi**, c'est-à-dire ce à quoi votre argent est réellement exposé. Si vous ouvrez la fiche de l'émetteur, vous y verrez une liste de titres très différente. » | Diversification, à côté de l'actif |
| **Contenu déclaré** | « Vous avez indiqué vous-même de quoi cet actif est fait. Il compte dans sa classe d'actifs, et il sort des pays et des secteurs — là où ces notions ne veulent rien dire pour lui. » | Diversification |
| **Déclaré à la main** | « La composition de cet actif a été saisie, pas récupérée : elle ne porte donc pas de date d'arrêté officielle. » | Diversification |
| **Code non reconnu** | « La source a renvoyé un code que nos référentiels ne nomment pas. Le montant est conservé et affiché tel quel, sous son code, plutôt que d'être fondu dans « autres ». » | Diversification |
| **Histoire incomplète** | « Il manque des opérations avant celles que nous avons lues : la quantité est juste, mais le prix de revient et le gain de cette ligne ne le sont pas forcément. » | Les actifs |
| **Peu significatif** | « Sur moins d'un an, un rendement annualisé s'emballe : quelques semaines de hausse deviennent un pourcentage énorme qui ne veut rien dire. Le gain en euros, lui, reste lisible. » | Synthèse, sur le TRI et le TWRR |

### 2.3 Les conventions — ce qui n'a pas de réponse unique

| Marque | Explication affichée | Lieu |
|---|---|---|
| **Règle de pays** | « De quel pays est une société ? Il y a plusieurs réponses justes. Pour les fonds, nous retenons le pays où la société **exerce son activité** ; pour une action que vous détenez en direct, son **siège social**. Ces deux règles cohabitent dans le même graphique, et c'est pourquoi la règle employée est indiquée **sur chaque ligne**. » | Diversification, en-tête + par ligne |
| **Secteurs Morningstar** | « Les secteurs suivent la nomenclature **Morningstar**, en 11 postes. Il en existe d'autres, qui ne découpent pas au même endroit — elles ne s'additionnent pas, donc nous n'en mélangeons jamais deux. » | Diversification, en-tête |
| **Zones** | « Le regroupement des pays en zones est une **convention**, pas une donnée : la liste est un fichier daté et sourcé, que vous pouvez corriger. Il n'existe aucune norme officielle du « développé » et de l'« émergent », et les deux grands fournisseurs sont en désaccord sur plusieurs pays. » | Diversification |
| **Arrêté au** | « Les compositions de fonds ne sont pas publiées en temps réel : chaque fonds arrête la sienne à une date, et ces dates diffèrent d'un fonds à l'autre. » | Bandeau, Diversification |
| **Cours brut** | « Les cours sont bruts : jamais retraités des dividendes. C'est le prix affiché sur le marché. » | Les actifs |
| **Le total ne fait pas 100 %** | « C'est voulu. Ce qui n'a pas pu être attribué reste visible, à sa vraie taille. Ramener le graphique à 100 % ferait disparaître exactement l'information qui manque. » | Diversification, sous chaque graphique |

### 2.4 Les mots interdits à l'écran

| Interdit | Pourquoi | À la place |
|---|---|---|
| « GICS » | Aucune source gratuite par ISIN n'en fournit ([D-65](decisions.md)) | « secteurs Morningstar » |
| « Autres » pour un reste | Ça fait passer un manque pour une catégorie | « non couvert », « non attribué », « hors actions » |
| « Erreur » pour une absence | Une donnée absente n'est pas une panne | Le motif exact, en français |
| Un total ramené à 100 % | [D-69](decisions.md) | Le total réel, et la part manquante affichée |
| Le nom d'un champ technique | L'utilisateur ne code pas | Le mot du glossaire |

---

## 3. Les règles d'affichage

### 3.1 Le piège des pourcentages — **à lire avant d'écrire une seule ligne de vue**

Le moteur manipule **deux unités différentes**, et les confondre a déjà produit un « 6264,00 % »
au lieu de 62,64 % à l'étape 7.

| Unité | Ce que vaut 62,64 % | Qui la rend |
|---|---|---|
| **Pour cent** | `Decimal("62.64")` | `Repartition.pour_cent()`, `ImpotEstime.taux`, `ParametreDate.valeur` |
| **Taux (fraction)** | `Decimal("0.6264")` | `Rendements.tri`, `Twrr.taux`, `Twrr.annualise`, `SousPeriode.rendement`, `LigneDeCout.poids`, `TotauxCouts.poids_moyen` |

Le rapport texte a **une fonction de mise en forme par unité**, et c'est le modèle à reprendre :
`_pourcentage()` pour un taux (`rapport.py:59`), `_part_en_clair()` pour un pour cent
(`rapport.py:759`). **Aucune vue ne doit écrire `× 100` à la main.**

### 3.2 Les autres règles

- **Les chiffres s'alignent à droite**, en chiffres à chasse fixe (`font-variant-numeric:
  tabular-nums`), pour que deux montants se comparent d'un coup d'œil.
- **Un libellé n'est jamais tronqué sans recours.** Un libellé coupé n'explique plus rien : c'est
  arrivé à l'étape 7 avec « Hors répartition actions (obligations, liqu. ». À l'écran, on retourne
  à la ligne plutôt que de couper ; si la troncature est inévitable, le texte entier reste
  accessible au survol.
- **Les montants en euros** portent leur unité, avec l'espace insécable : `1 234,56 €`.
- **Un signe devant un gain** : `+132,40 €`, `−18,90 €`. Le signe se lit avant la couleur, pour
  ceux qui ne distinguent pas le vert du rouge.
- **La couleur ne porte jamais seule une information** : sauge et terracotta doublent un signe ou
  un mot, jamais ne le remplacent.
- **Rien n'est arrondi vers le haut pour faire joli** : deux décimales sur les montants, deux sur
  les pourcentages, et le dénominateur disponible.
- **Une lecture au survol suit la souris, sur le graphique.** Les montants à une date s'affichent
  dans une boîte posée **sur** le graphique, qui suit le curseur sur les deux axes. C'est
  l'arbitrage du propriétaire, rendu **contre la recommandation** après avoir essayé l'autre
  arrangement, et sa raison est meilleure que celle qu'il écarte : **descendre les yeux hors du
  graphique pour lire un chiffre casse la lecture**, et on regarde une courbe pour la suivre. La
  boîte recouvre donc une partie de la courbe — et c'est l'utilisateur qui la déplace, en montant ou
  en descendant la souris. Quatre points font tenir ce choix :
  - la boîte est **décalée du curseur** (16 px), jamais sous lui : le viseur, les deux points et le
    curseur restent visibles ;
  - elle **bascule du côté opposé près d'un bord**, au lieu d'être coupée ou de sortir du cadre.
    C'est ce qui manquait à la première version, dont la moitié du texte sortait de la page ;
  - elle reste **étroite et verticale**. En bandeau horizontal elle cachait une large tranche de
    dates ; en colonne elle ne masque qu'une bande fine, donc bien moins de la **forme** de la
    courbe, qui est ce qu'on lit ;
  - elle ne capte pas la souris (`pointer-events: none`). Sans cela, elle intercepte le déplacement
    dès qu'elle passe sous le curseur, et la lecture se figeait.

  **Ce qui est écarté, et pourquoi le garder écrit.** La boîte a été, un temps, un **bandeau posé
  sous la courbe**, de hauteur réservée, qui ne recouvrait rien. C'était la réponse au premier
  défaut signalé — une infobulle en haut du cadre masquait le haut de la courbe. Le bandeau a été
  jugé « trop en retrait » puis écarté pour la raison ci-dessus. Restent écartées aussi : la boîte
  qui **choisit automatiquement la moitié libre du cadre** — elle change de place sans qu'on sache
  pourquoi, et avec deux courbes plus une aire remplie la moitié « libre » est souvent étroite ; et
  la boîte **fixe en haut du cadre**, qui est le défaut d'origine. Trois arrangements essayés pour
  une seule boîte : **ne pas recommencer le tour à l'étape 9.**
- **Un repère de ligne situe, il ne mesure pas.** Les zones géographiques portent un **planisphère**
  avec leur part du monde remplie d'encre, là où elles portaient toutes le même globe — cinq fois le
  même repère, c'est-à-dire aucun. Ce qui vaut pour tout repère de ce genre : il allume des
  continents entiers alors qu'une zone ne suit pas leurs contours (« marchés émergents » n'est pas un
  continent), il est donc **explicitement présenté comme un repère et non une délimitation**, et ce
  sont les montants et les parts de la ligne qui font foi. Deux formes y sont volontairement
  **dessinées plus grandes que l'échelle** — le Japon et la Nouvelle-Zélande — parce qu'à cette
  taille un tracé exact fait un pixel et disparaît, y compris quand c'est lui qu'on allume.
- **Tous les repères d'une même liste occupent un créneau de même largeur.** Drapeau, pictogramme et
  planisphère n'ont pas la même largeur ; sans créneau fixe, le bord gauche des libellés est dentelé
  d'un groupe à l'autre de la même liste.
- **Aucune police, aucun graphique, aucun script appelé sur le réseau** : l'application s'ouvre
  hors ligne ([D-31](decisions.md)).

---

## 4. Les écrans retenus

Quatre chapitres, la place d'un cinquième, et une annexe, arbitrés sur les maquettes de l'étape 8
puis à l'écran pendant les étapes 9 et 9 bis. Les [maquettes](../maquettes/) en sont la version exécutable de l'étape 8 ; depuis
l'étape 9, **l'application fait foi** là où elles divergent (la diversification et le détail des
calculs ont changé à l'écran, sur arbitrage du propriétaire).

L'ordre des onglets est celui des questions qu'on se pose, de la plus large à la plus fine :
combien j'ai gagné → sur quoi → où est mon argent → ce que ça coûte. **Comment c'est calculé**
n'est pas un onglet : c'est une page qu'on ouvre quand on veut vérifier (§4.6).

| # | Chapitre | La question à laquelle il répond | Filtres actifs |
|---|---|---|---|
| I | **Synthèse** | Combien ai-je gagné, et comment ça a évolué ? | période, poches |
| II | **Les actifs** | Sur quoi, actif par actif ? | type, poches |
| III | **Diversification** | Où est mon argent ? | **aucun** |
| IV | **Frais et taxes** | Combien tout cela coûte ? | **aucun** |
| V | **Projections** *(place réservée, [D-97](decisions.md))* | Que pourrait devenir le portefeuille ? | **aucun** |
| Annexe | **Détail des calculs** (page à part, §4.6) | Comment ces chiffres sont-ils obtenus ? | période, poches |

**Pourquoi la diversification et les frais n'ont aucun filtre**, et c'est une règle et non un
oubli : une répartition est la **photo d'un tout**, et la valeur réelle est celle du portefeuille
entier. Il n'y a rien à y filtrer, et **un filtre qui n'agit sur rien est pire qu'absent** — il
fait douter du chiffre affiché.

### 4.0 La couverture

L'accueil est la **couverture** du livre ([D-98](decisions.md), charte §4.1), et **chaque session
s'ouvre sur elle**. La navigation et le colophon y sont masqués. Une étiquette porte :

- **sans export** : quel fichier déposer et où l'obtenir, puis la zone de dépôt (§5.1) ;
- **avec un export** : la période couverte, la dernière opération lue (l'export ne porte pas sa
  date de création), le nombre de fichiers, l'alerte s'il y a des types inconnus, puis **« Ouvrir le
  livre »** et **« Déposer un export plus récent »** — qui s'ajoute aux précédents
  ([D-95](decisions.md)).

La couverture **tient sur un écran** ([D-101](decisions.md)) : les fichiers lus, ce que la
lecture a trouvé et le dossier des exports sont dans un **volet replié** de l'étiquette ; les
alertes (type inconnu, période non couverte, fichier ignoré) n'y sont jamais. Rien de l'accueil de
l'étape 9 n'a disparu. On y revient par le **nom « Pastory »** en tête de la navigation, ou par le
lien « vos exports » du colophon.

### 4.1 Le bandeau permanent

Deux bandes, toujours visibles, de la plus sombre à la plus claire :

1. **la navigation**, en brun reliure : le logo et le nom (qui ramènent à la couverture), les
   chapitres numérotés (I à V), l'actif marqué d'un **signet** d'or ; à droite, un bouton discret,
   **« Annexe · Détail des calculs »**, qui ouvre la page du même nom, et le bouton **jour / nuit**
   ([D-100](decisions.md)). Il remplace le compteur « à surveiller » prévu à l'étape 8 : le
   bloc du même nom vit en bas de cette page. Sans export déposé, il n'y a **ni chapitres ni
   bouton** : seule la couverture existe (§5.1) ;
2. **les filtres** : période, type d'actif, poches. Chaque chapitre n'affiche que ceux qui
   **agissent sur lui** (voir le tableau ci-dessus) ;
   À droite des filtres, la période qu'ils ont retenue, en clair.

**Le colophon** (l'état des données) n'est plus une troisième bande ([D-103](decisions.md)) : il
est à droite du titre de chaque chapitre. La date des cours s'y lit d'un coup d'œil, une valeur
partielle aussi ; la source, la période de l'export, les arrêtés de composition et le nombre de
positions s'ouvrent dans la bulle « d'où viennent ces chiffres ». Il ne disparaît jamais : c'est ce
qui permet de dire « ces chiffres sont d'hier ».

Chaque chapitre **s'ouvre** sur son numéro romain, son titre et une phrase qui dit ce qu'il montre
(charte §4.2).

### 4.2 Synthèse

Dans cet ordre, de haut en bas :

- une première rangée de boîtes : **la valeur des actifs**, la plus grande, point d'entrée de la
  page ([D-99](decisions.md)) ; puis **quatre indicateurs** : le **gain** d'abord
  ([D-22](decisions.md)), le **TRI** (avec son signalement « Peu fiable », qui s'explique au
  survol), le **TWRR**, et le **capital net investi**, qui porte la plus-value latente ;
- **la courbe** — capital brut et capital net investi, du début de la période à sa fin. Le capital
  investi monte **en escalier** : il ne bouge qu'aux opérations, et la forme le dit mieux qu'une
  note. Les montants à une date se lisent dans la boîte qui suit la souris (§3.2) ;
- **les poches**, à côté de la courbe : une barre empilée fine, puis le montant et la part de
  chaque poche, alignés ;
- **les cartes d'actifs**, triées par variation. Elles ne répètent pas le tableau de l'onglet
  suivant : elles montrent ce qui a le plus bougé.

### 4.3 Les actifs

**Un seul tableau, pleine largeur**, une ligne par actif, filtrable par type et par poche.
Il porte les colonnes de `rapport.py` : quantité, capital investi, prix de revient, valeur, gain,
variation, TRI, TWRR, et la **remarque** qui dit quand un chiffre manque et pourquoi.

C'est le seul écran où une ligne peut être **partielle sans que l'écran entier le soit** : un actif
sans cours n'empêche pas les autres d'être justes. La remarque porte alors le motif, sur la ligne.

### 4.4 Diversification

**Quatre rubriques**, choisies dans la bande sous la navigation ([D-104](decisions.md)), dans l'ordre où l'on se pose les questions : **Actifs** (les classes),
**Zone géographique**, **Pays**, **Secteur**. Les quatre sur un même écran écrasaient chacun d'eux.

Les quatre sous-onglets ont **la même mise en page** (arbitrage du propriétaire, étape 9 : les
anneaux, puis les carrés découpés essayés à leur place, ont été retirés) :

- **des chiffres clés**, en tuiles, rapportés à la valeur totale comme le classement : pour les
  classes, la part en actions, hors actions et en actifs numériques ; ailleurs, le premier poste,
  le nombre de pays ou de secteurs représentés, les dix premiers pays, et ce qui reste sans pays
  ou sans secteur ;
- **le classement**, pleine largeur : une ligne par poste, avec son repère (un drapeau par pays,
  un pictogramme par classe ou secteur), sa barre, son montant et sa part. Les barres sont toutes
  rapportées à la **même base**, jamais renormalisées ([D-69](decisions.md)). Au-delà de 15
  postes, les autres se déplient (« Afficher les N autres ») ;
- en dessous, **ce qui n'entre pas dans cette répartition** (non attribué, non couvert, hors
  actions) sur **une seule ligne qui se déplie** pour montrer le détail par actif.

Puis, **repliée**, « ce qu'il faut savoir de ces chiffres » : les réserves qui rendent la
lecture honnête (origines des données, fonds synthétiques, contenus déclarés, fonds non
couverts), et non des notes techniques.

### 4.5 Frais et taxes

**Trois niveaux à la file, sur un seul écran** ([D-73](decisions.md)). Le découpage porte la
séparation **réel / estimé** ([D-17](decisions.md)), et **non une chronologie**
([D-75](decisions.md)) — d'où les titres, qui disent le critère et jamais le moment :

1. **« Ce qui a déjà été prélevé »** — frais d'ordre, taxes de transaction, et la **retenue à la
   source sur les dividendes**, qui y reste bien qu'elle tombe pendant la détention. Ces montants
   figurent sur les relevés ;
2. **« Pendant la détention — les frais courants »** — TER et spread, **estimés**, chacun avec sa
   valeur, sa date et sa source ([D-58](decisions.md)) ;
3. **« À la sortie — par poche »** — la valeur réelle ([D-23](decisions.md)), impôt estimé compris,
   poche par poche parce que la fiscalité l'est.

### 4.6 Détail des calculs

La page qui rend les chiffres **refaisables à la main**, et c'est sa seule raison d'être : le
propriétaire ne code pas, il vérifie. **Ce n'est pas un onglet** (arbitrage du propriétaire,
étape 9) : elle n'est pas aussi importante que le reste et ne doit pas en avoir l'air. Elle
s'ouvre par le bouton discret à droite de la manchette, et suit la période et les poches
choisies. Elle contient, dans cet ordre :

- **comment le gain est obtenu**, et **pourquoi il ne tombe pas sur la somme de la colonne** — le
  piège le plus coûteux de l'étape 8 : le gain se calcule sur les montants **bruts**
  ([D-21](decisions.md)) là où le capital net investi est net de frais et réduit au prorata des
  ventes ([D-12](decisions.md)) ;
- **les flux datés, qui donnent le TRI** ;
- **les sous-périodes, qui donnent le TWRR** ;
- **une estimation, de bout en bout** — un exemple chiffré d'un coût estimé ;
- **ce que le calcul d'impôt suppose**, et de quoi la base imposable est faite ;
- **« D'où viennent les réglages »**, replié (§6.3) ;
- **« à surveiller »** — le panneau des types d'événements inconnus, des déductions et des
  estimations.

---

### 4.7 Projections

**La prédiction de l'évolution** ([D-97](decisions.md), hypothèses [D-105](decisions.md),
formules au [glossaire](glossaire.md) §9). Une hypothèse sur l'avenir, jamais une prévision ni un
conseil : la bande le dit, la page le redit.

La page tient sur un écran et se lit de haut en bas :

- **« Le montant atteint »**, en une bande : le grand chiffre à gauche ; à côté, sans aléa, ce qui
  a été versé et ce que le taux a ajouté ; avec l'aléa, la médiane, « dans 8 cas sur 10, entre … et
  … », et les niveaux 90 %, 75 %, médiane, 25 %, 10 %, avec la valeur sans aléa et le total versé
  pour comparer ;
- **« L'évolution supposée »** : le total versé (pointillé ocre), puis la courbe sans aléa ou les
  cinq quantiles, en lignes seules, nommés à leur bout ; la boîte de lecture suit la souris ;
- **« Vos hypothèses »**, sur une ligne : la valeur de départ (proposée : la valeur des actifs,
  avec sa date ; modifiable), le taux annuel, la durée, le versement mensuel, et le choix de
  lecture « une courbe | 10 000 simulations ». Une saisie hors bornes affiche son **motif**,
  jamais une valeur remplacée en silence. À leur pied, replié, **« Ce que ce calcul suppose »** :
  les hypothèses en clair, et leurs limites (la loi sous-estime les krachs ; tout est nominal).

Le calcul (`pastory/projection.py`) ne dépend pas du moteur, et rien ne dépend de lui
([D-27](decisions.md)).

## 5. Les quatre états de chaque écran

Aucun écran n'a un seul état. Les quatre suivants sont **le contrat** : pour chaque bloc, l'étape 9
doit savoir lequel elle affiche, et un bloc qui n'en prévoit qu'un est incomplet.

### 5.1 Vide — il n'y a rien à montrer

**Ce n'est pas une erreur, et le message ne doit pas en avoir l'air.** Il dit ce qui manque et
**quoi faire**, pour quelqu'un qui n'a pas suivi la construction du projet
([D-62](decisions.md)).

| Cas | Ce que l'écran dit |
|---|---|
| Aucune opération lue | Où récupérer un export dans l'application Trade Republic, et où le déposer : la zone de dépôt de l'accueil ([D-95](decisions.md)). **Les onglets n'apparaissent pas** : ils ramèneraient tous au dépôt, et feraient croire qu'il y a quelque chose derrière. Ils viennent avec le premier export lu *(arbitrage du propriétaire, 2026-10-08)* |
| Une seule ligne au portefeuille | Les chiffres, sans camembert : un anneau à une part ne dit rien |
| Aucun cours connu sur la période | **Rien n'est tracé**, plutôt qu'une ligne à zéro — et la phrase le dit |
| Aucun actif dans le filtre choisi | Que le filtre est en cause, et non les données |
| Pas de PEA, pas de crypto | La poche **n'apparaît pas**. Une poche vide n'est pas une information |

**La règle qui gouverne cet état :** un zéro affiché et une donnée absente ne se ressemblent pas.
« 0,00 € » veut dire *mesuré à zéro* ; une absence se dit avec des mots.

### 5.2 Partiel — une partie manque, le reste est juste

L'état le plus fréquent, et le plus dangereux si on le tait : **un total partiel qui ne se dit pas
est un total faux**.

- le total porte la mention **partiel**, et **la liste de ce qui manque** est à un clic ;
- les lignes présentes restent affichées avec leurs chiffres : on ne masque pas un écran entier
  pour un actif sans cours ;
- dans une répartition, ce qui n'est pas attribué **reste visible** — non attribué, non couvert,
  hors actions — et **rien n'est renormalisé à 100 %** ([D-69](decisions.md)). Le camembert ne fait
  pas le tour, et **cela se voit** ;
- un actif servi par la **source de secours** ([D-77](decisions.md)) est un cas de cet état
  particulier : il a des **pays** et reste **non couvert en secteur**. Les deux écrans ne sont pas
  d'accord, et c'est juste.

### 5.3 Estimé — le chiffre n'a pas été payé

Un montant estimé ne se mélange **jamais** à un montant prélevé ([D-17](decisions.md)).

- il porte la marque **estimé**, et sa bulle donne **sa valeur, sa date et sa source**
  ([D-58](decisions.md)) ;
- l'écran ne les additionne pas dans un même total sans le dire. Dans « Frais et taxes », la
  séparation est portée par le **découpage lui-même** ([D-75](decisions.md)) ;
- une estimation **minorée** le dit, et dit dans quel sens elle se trompe : « le montant réellement
  dû serait plus élevé, donc la valeur réelle un peu plus basse ». Un utilisateur doit savoir de
  quel côté il est prudent.

### 5.4 En erreur — quelque chose n'a pas fonctionné

Distinguer trois choses que l'utilisateur confondra si on ne l'aide pas :

| Nature | Ce que l'écran dit | Ce qu'il ne fait jamais |
|---|---|---|
| **Source injoignable** (réseau, service en panne) | Que c'est temporaire, et que les chiffres affichés sont ceux du cache, avec leur date | Effacer les chiffres déjà connus |
| **Donnée refusée** (composition invraisemblable, cours dans la mauvaise devise) | **Pourquoi** elle est refusée, et comment la corriger à la main | Afficher la donnée douteuse « en attendant » |
| **Type d'événement inconnu** | L'affiche, dans « à surveiller », avec son libellé brut | Le ranger dans une catégorie par défaut (règle 5) |

**La règle qui les réunit :** un trou signalé vaut mieux qu'un chiffre crédible et faux. C'est la
phrase qui revient le plus souvent dans les décisions de ce projet, et c'est elle qui arbitre quand
aucune autre ne tranche.

### 5.5 Ce qu'aucun état n'autorise

Quatre choses, jamais, sur aucun écran :

1. **remplir un trou par une estimation silencieuse** — une déduction est explicite, isolée et
   signalée (règle 6 de `CLAUDE.md`) ;
2. **renormaliser une répartition à 100 %** ([D-69](decisions.md)) ;
3. **mélanger deux nomenclatures** ou deux règles de pays dans un même graphique sans le dire
   ([D-65](decisions.md), [D-66](decisions.md), [D-72](decisions.md)) ;
4. **faire dépendre un calcul d'un texte affiché** (règle 4). Si c'est inévitable, c'est isolé dans
   un fichier déclaré, daté et sourcé, et **marqué comme fragilité** — le seul cas existant est
   `parametres/pays_amundi.toml`.

---

## 6. Les écrans de correction

> **Réécrit au début de l'étape 9 (2026-10-08)**, selon [D-80](decisions.md) : l'application
> **trouve, applique et montre** chaque valeur, avec sa source et sa date ; l'utilisateur **peut**
> la corriger, il n'a **jamais** à le faire. La version d'avant — « l'application propose,
> l'utilisateur décide », écrite le 2026-10-01 pour [D-78](decisions.md) — est remplacée ; ses
> trois règles qui restent vraies sont reprises au §6.2.

**La raison de ces écrans**, un arbitrage du propriétaire qu'il faut lire avant d'écrire une ligne
([D-78](decisions.md)) :

> Une bidouille qui fait peur n'est pas seulement désagréable : **elle fait douter de l'application
> entière.** Ce projet demande à l'utilisateur de croire ses chiffres. Cette confiance ne survit pas
> à une mise en route qui ressemble à du dépannage.

Le fichier TOML reste le **format de stockage**. Il n'est plus le moyen de configurer, ni même
celui de corriger : **l'étape 9 n'est pas terminée tant qu'une correction n'existe qu'en fichier.**

### 6.1 Ce que chaque réglage montre, et ce qu'on peut y corriger

Le contenu de ces écrans existe déjà : c'est `pastory/reglages` (un `Reglage` par réglage), dont
`pastory actifs` est la version texte. L'écran le reprend tel quel, avec les mêmes mots.

**Pour chaque réglage, l'écran montre** :

| Cas | Ce qui s'affiche |
|---|---|
| **Trouvé** | la valeur ; « trouvé : » sa **source** et sa **date** (ou « taux en vigueur depuis le » pour un TER) ; « vérifié : » le contrôle passé ; « à savoir : » la réserve de la source, s'il y en a une |
| **Corrigé par vous** | la valeur ; « corrigé par vous » ; et **« la source donnait »** la valeur trouvée, si elle est différente — c'est ce qui rend visible une correction devenue inutile ou fausse. Un bouton **« revenir à la valeur trouvée »** |
| **Introuvable** | le **motif**, écrit pour quelqu'un qui découvre (règle 10). Jamais une valeur par défaut |
| **Sans objet** | rien — un TER pour une action, un contenu que rien n'annonce. Le réglage n'apparaît pas |

**Ce qui se corrige**, actif par actif (`config/actifs.py`, `Declaration`) :

| Réglage | Trouvé où | La correction à l'écran |
|---|---|---|
| **Cotation** : ticker et devise | recherche par ISIN, contrôlée par le prix payé ([D-85](decisions.md)) | un ticker et sa devise. Seul l'euro est accepté ([D-48](decisions.md)) : un autre est refusé avec la raison |
| **Type** | l'export ([D-82](decisions.md)) | un choix : ETF, action, crypto-actif |
| **Frais courants (TER)** | l'émetteur, puis Xetra ([D-90](decisions.md)) | un taux en pour cent, refusé hors de sa fourchette. ETF seulement |
| **Spread propre** | — *(le taux de son type s'applique)* | un taux en pour cent, par côté. Facultatif |
| **Contenu** | extraETF, contrôlé par le code CFI ([D-89](decisions.md)) | un choix : actions, obligations, matières premières |
| **Source de secours** | essayée d'elle-même ([D-91](decisions.md)) | **la refuser** pour cet actif, ou l'imposer |
| **Répartition déclarée** : pays, secteurs | — *(la source de composition)* | une liste de lignes code + pour cent ; le pays et le secteur se choisissent par leur **nom**, l'écran écrit le code ([D-65](decisions.md), [D-66](decisions.md)) |

Et pour le portefeuille entier : la **date d'ouverture du PEA** (`fiscalite.toml`), trouvée dans les
mouvements d'espèces du plan ([D-86](decisions.md)), avec sa réserve ; et les **retraits relevés**
([D-87](decisions.md)), qui se montrent et ne se corrigent pas — ce sont des faits de l'export.

### 6.2 Les trois règles de ces écrans

1. **L'application trouve, applique et montre ; l'utilisateur peut corriger** ([D-80](decisions.md)).
   Aucun réglage n'attend un clic pour s'appliquer, et aucun écran n'est un passage obligé. Ce qui
   protège d'une valeur fausse, ce sont les **contrôles** et la **visibilité de la source** — pas
   une validation qu'un utilisateur non connaisseur ne saurait pas juger.
2. **L'écran écrit une correction, et rien d'autre** ([D-94](decisions.md)). Un seul champ d'un
   seul actif, celui que l'utilisateur vient de saisir. Le fichier garde ses **commentaires**, son
   ordre et les lignes écrites à la main : l'écran et le fichier sont deux portes sur la même chose.
   Une saisie passe par **la même lecture** que le fichier : ce que l'application refuserait de lire,
   l'écran refuse de l'écrire, et dit pourquoi. Jamais une valeur trouvée n'est recopiée dans le
   fichier ([D-92](decisions.md)).
3. **Un manque se dit là où il se voit, et le lien vers sa correction est là.** Pas dans un écran
   de réglages qu'il faudrait penser à aller voir : un actif sans cotation le dit sur sa ligne du
   tableau des actifs ; un TER introuvable, dans les frais ; un fonds non couvert, dans la
   diversification ; la date du PEA, dans la règle d'impôt. Chacun ouvre la correction de **cet**
   actif.

### 6.3 Où sont ces écrans

Les onglets sont fixés (§4) : la correction n'en ajoute pas un de plus.

- **La fiche de réglages d'un actif** s'ouvre en volet, par-dessus l'onglet en cours, depuis
  chaque endroit où l'actif apparaît avec un réglage à dire — sa ligne dans « Les actifs », un
  fonds non couvert ou servi par le secours dans « Diversification », un TER introuvable dans
  « Frais et taxes ». Elle montre tous les réglages de l'actif (§6.1), dans l'ordre de
  `ReglagesDUnActif.reglages()`, puis ce qui ne se trouve jamais seul (spread, répartition,
  secours). La fermer ramène là où l'on était.
- **La date d'ouverture du PEA** s'ouvre de la même façon depuis la règle d'impôt du PEA, dans
  « Frais et taxes ».
- **« D'où viennent les réglages »**, dans « Détail des calculs », juste avant « à surveiller » :
  la version écran de `pastory actifs`. En tête, le compte — « 18 valeurs trouvées seules,
  1 corrigée par vous, 2 introuvables » —, puis chaque actif, chaque réglage et son origine, avec
  le lien vers sa fiche. C'est l'endroit où l'on vérifie **tout** d'un coup, sans rien chercher.
- **Les corrections sans actif** (une ligne d'`actifs.toml` qu'aucun export ne contient, souvent un
  ancien identifiant) sont listées au même endroit, avec un bouton pour les retirer.

Après une correction, les chiffres sont **recalculés** et l'écran le dit en une ligne. Une
correction de cotation n'a rien à faire des cours déjà gardés : ceux d'une autre cotation ne sont
jamais employés ([architecture-notes §7 bis](architecture-notes.md)).

### 6.4 Un exemple : un TER introuvable

Un ETF iShares « Swap PEA » n'est ni dans la liste de Xetra ni chez Amundi, et la seule source qui
le publie n'a pas de date ([D-90](decisions.md)). Dans « Frais et taxes », sa ligne des frais
courants dit :

> **TER introuvable** — aucune source datée ne publie les frais courants de ce fonds. Ils ne sont
> pas comptés dans l'estimation des frais pendant la détention, qui est donc plus basse que la
> réalité. [Indiquer le TER de ce fonds]

Le lien ouvre la fiche de l'actif, au champ des frais courants. L'utilisateur y écrit le taux de son
document d'informations clés ; l'écran vérifie la fourchette, écrit la ligne dans `actifs.toml`,
recalcule, et la ligne des frais affiche désormais le taux avec « corrigé par vous ». Rien n'a été
demandé à l'ouverture, et rien n'empêchait de lire le reste.

### 6.5 Ce que ces écrans n'ont pas le droit de faire

- **appliquer une valeur sans la montrer**, avec sa source ([D-80](decisions.md), règle 1) ;
- **masquer** un réglage introuvable pour faire propre : c'est ce qui produit un chiffre faux plus
  loin ;
- **écrire dans le fichier autre chose que ce que l'utilisateur a saisi**, ni une valeur trouvée
  ([D-92](decisions.md), [D-94](decisions.md)) ;
- **exiger un réglage pour afficher le reste.** Un portefeuille dont trois réglages sont
  introuvables s'affiche quand même, avec ses trois trous nommés — c'est l'état « partiel » du §5.2 ;
- **reposer une question** : un refus (de la source de secours, par exemple) est une correction
  comme une autre, écrite et retenue.
