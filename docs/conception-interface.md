# Conception de l'interface

> **Ce document est le contrat de l'étape 9.** Il dit *ce qui s'affiche, où, et sous quels mots*.
> Il ne dit pas comment l'écrire en Dash : c'est le travail de l'étape 9.
>
> Écrit à l'**étape 8**. Dernière mise à jour : **2026-09-29**.
>
> Comme tout le dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)). Les chiffres
> qui l'illustrent sont inventés.

## Sommaire

| § | Contenu |
|---|---|
| [1](#1-linventaire--ce-que-le-moteur-produit-et-où-ça-saffiche) | **L'inventaire** : chaque chose que le moteur produit, et l'écran qui la porte |
| [2](#2-le-vocabulaire-décran) | **Le vocabulaire d'écran** : les mots que l'utilisateur va lire sans les avoir choisis |
| [3](#3-les-règles-daffichage) | **Les règles d'affichage** : unités, alignement, troncature, couleurs |
| 4 | Les écrans retenus *(à écrire après les arbitrages sur les maquettes)* |

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

Relevé le 2026-09-29 sur `dashboard_tr/moteur/`. **Colonne « aujourd'hui »** : `rapport` si le
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
| **Compteur « à surveiller »**, qui ouvre le panneau du §1.7 | Les trois listes de `Signalement` | rapport |

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

Deux mots du vocabulaire officiel ne sont adossés à rien :

- **« non transparisé »** (fonds de fonds) est promis par le [glossaire §8](glossaire.md), la
  [feuille de route](feuille-de-route.md) et le [comparatif](composition-des-etf.md).
  **Aucun champ du code ne le produit.** → [Q-48](questions-ouvertes.md).
- **La règle de pays** n'est portée par aucune donnée : elle est seulement implicite dans la
  source retenue (`donnees_externes/actions.py` = siège social, `extraetf.py` = pays d'activité).
  Le rapport en dit un texte générique, sans jamais dire **quel actif** relève de quelle règle.
  Or [D-66](decisions.md) demande qu'elle soit affichée, et [D-72](decisions.md) qu'elle le soit
  **ligne par ligne**. → traité en phase 5, par un champ de plus dans le protocole
  `CompositionDUnActif`.

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
- **Aucune police, aucun graphique, aucun script appelé sur le réseau** : l'application s'ouvre
  hors ligne ([D-31](decisions.md)).

---

*Les §4 et suivants — les écrans retenus — sont écrits après les arbitrages sur les maquettes.*
