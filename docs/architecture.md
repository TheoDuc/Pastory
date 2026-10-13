# Architecture

Comment l'application est construite : les couches, ce que chacune sait, ce qu'elle s'interdit,
et par où passe un chiffre entre l'export de la banque et l'écran.

**À qui ça sert.** Au propriétaire du projet, pour savoir où regarder quand un chiffre semble
faux — la réponse est presque toujours dans une seule couche. Et à toute session de travail qui
ajoute une étape, pour qu'elle branche son code au bon endroit plutôt qu'au plus court.

**Ce document décrit ce qui existe.** Les points encore ouverts, les pistes et l'historique des
réflexions restent dans [architecture-notes.md](architecture-notes.md) ; les raisons de chaque
choix dans [decisions.md](decisions.md) ; le détail du contrat entre couches dans
[format-pivot.md](format-pivot.md). Ici, aucune raison n'est réexpliquée : elle est citée
(`D-xx`).

> État à la dernière mise à jour (fin de l'étape 8 quater) : les couches **adaptateur** — celui
> de l'**export officiel** de Trade Republic, pytr ayant été retiré ([D-81](decisions.md)) —,
> **pivot**, **moteur** (rejeu, valorisation, rendements, coûts, fiscalité, valeur réelle et
> **diversification**) et **données externes** sont écrites, ainsi que les **paramètres** datés et
> sourcés, qui portent aussi les **référentiels**. Depuis l'étape 8 quater, une couche
> **réglages** trouve seule ce que l'utilisateur déclarait à la main ([D-80](decisions.md)), et
> `config/` ne porte plus que ses corrections. **L'étape 9 est en cours** : l'assemblage est sorti
> de `cli.py` dans `assembleur.py`, que la ligne de commande et l'interface (`vues/`) appellent
> toutes les deux ; l'accueil et le bandeau existent, les écrans s'ajoutent bloc par bloc.

---

## 1. En une image

```
  ┌─ hors de l'application ───────────────────────┐
  │                                               │
  │   application Trade Republic                  │
  │   Profil > Relevés > Export des transactions  │
  │        │  l'utilisateur dépose le fichier     │
  │        ▼                                      │
  │   Pastory/exports/*.csv                       │
  └────────┬──────────────────────────────────────┘
           ▼
   ┌───────────────────────────────────────────────────────────┐
   │  ADAPTATEUR  trade_republic/                              │
   │  lire le portefeuille ouvert · classer · lire les         │
   │  colonnes · refuser les formes jamais vues                │
   └───────────────────────┬───────────────────────────────────┘
                           │  opérations + ce qui n'a pas été compris
                           │  + ce que dit la banque (type, mouvements du PEA)
                           │        │
                           │        └──► RÉGLAGES  reglages/  (D-80)
                           │             banque + sources (contrôlées) + corrections
                           │             → la configuration effective, chaque valeur
                           │             avec sa source ; l'assembleur la passe aux cours,
                           │             aux coûts et aux compositions
                           ▼
   ┌───────────────────────────────────────────────────────────┐
   │  PIVOT  pivot/            ◄── le contrat, figé (D-35)     │
   │  Operation · contrôles de cohérence                       │
   └───────────────────────┬───────────────────────────────────┘
                           │                  ▲
                           │                  └── DONNÉES EXTERNES  donnees_externes/
                           │                      cours (D-51) · cache (D-50)
                           │                      complète les prix manquants (D-15)
                           │                      et rend du pivot ; sert aussi de
                           │                      source de cours au moteur, **par
                           │                      paramètre** (l'assembleur fait le lien)
                           ▼  et rien d'autre
   ┌───────────────────────────────────────────────────────────┐
   │  MOTEUR  moteur/                                          │
   │  rejeu par actif · journal · agrégation                   │
   │  valorisation · gain, TRI, TWRR (D-22)                    │
   │  coûts payés et estimés · impôt estimé · valeur réelle    │
   └───────────────────────┬───────────────────────────────────┘
                           │           ▲
                           │           └── PARAMÈTRES  parametres/
                           │               taux fiscaux, frais par ordre, spreads :
                           │               une valeur, une date, une source (D-58),
                           │               passés au moteur **par paramètre**
                           │  positions, valeurs, rendements, coûts, signalements
                           ▼
   ┌───────────────────────────────────────────────────────────┐
   │  SORTIES   cli.py · vues/ (Dash), par assembleur.py        │
   │  rapports en français · CSV pour le tableur               │
   └───────────────────────────────────────────────────────────┘
```

La forme en « wagons » vient de [D-26](decisions.md) : le moteur ne lit que le pivot, et changer
de banque ne demande d'écrire qu'un adaptateur.

---

## 2. Les couches, et ce que chacune s'interdit

L'interdiction compte autant que le rôle : c'est elle qui garantit qu'un défaut reste local.

| Couche | Son travail | Ce qu'elle ne sait pas, volontairement |
|---|---|---|
| `config/` | Où sont les fichiers personnels ; ce que l'utilisateur a **corrigé**, champ par champ (D-92) | Ce qu'on fera de ces corrections, et ce qui a été trouvé sans lui |
| `reglages/` | Trouver la cotation, le type, le TER, le contenu, la date du PEA ; les **contrôler** ; les fusionner avec les corrections ; dire d'où vient chaque valeur, ou pourquoi elle manque (D-80, D-85 à D-92) | Lire un export (l'adaptateur lui donne `CeQueDitLaBanque`), calculer quoi que ce soit sur une position |
| `adaptateurs/` | Comprendre les fichiers d'**une** banque et les traduire en pivot | Ce qu'est un prix de revient, un gain, un rendement |
| `pivot/` | Décrire une opération, et vérifier qu'une ligne se tient | Qui l'a produite, qui va la lire |
| `donnees_externes/` | Aller chercher un cours, **la composition d'un actif**, les garder, et **compléter un prix manquant** | Ce qu'est une position, un prix de revient, une plus-value. Et ce qu'est un secteur « Technologie » : elle ne transporte que des **codes** |
| `moteur/` | Rejouer les opérations, tenir le journal, agréger, **valoriser**, calculer gain, TRI et TWRR, puis les **coûts**, l'**impôt estimé**, la **valeur réelle** et la **répartition** | Le nom d'un champ Trade Republic, l'emplacement d'un fichier, **d'où viennent les cours, les taux et les compositions** — il dit seulement la forme qu'il en attend. Il ne sait pas ce qu'est un ETF : il demande un taux, ou une composition, pour un actif |
| `parametres/` | Porter les taux fiscaux, les frais par ordre, les spreads par défaut, et les **référentiels** (secteurs, pays, zones, classes d'actifs), chacun avec sa date et sa source | Ce qu'on en fera. Ils sont **livrés avec l'application** et versionnés : rien de personnel |
| `vues/` (étape 9) | Montrer, expliquer, laisser filtrer ; recevoir l'export déposé ; écrire une correction | Tout calcul — les chiffres viennent de l'assembleur, et sont seulement **mis en forme** (`vues/format.py`). Le script de dessin ne fait que tracer ([D-93](decisions.md)) |

Deux conséquences pratiques :

- **un chiffre faux se cherche dans une seule couche.** Mal lu dans l'export →
  adaptateur. Mal cumulé d'un achat à l'autre → moteur. Les deux ne se mélangent jamais ;
- **le moteur est testable sans aucune banque.** Ses tests partent d'opérations pivot fictives
  écrites à la main ([tests/moteur/operations_fictives.py](../tests/moteur/operations_fictives.py)),
  jamais d'un export ;
- **la couche des cours est testable sans réseau.** Ses tests partent de réponses écrites à la
  main et d'une source factice en mémoire, jamais d'un appel réel.

---

## 3. La règle de dépendance

**Une couche ne connaît que le contrat de la suivante.** Les flèches réelles du code, telles
qu'elles sortent des `import` :

```
config/  ──────────────┐
                       ▼
adaptateurs/  ──────► pivot/  ◄────── moteur/
       donnees_externes/ ──┤           │
             parametres/ ──┘           │
                       │               │
                       └──► tableur.py ◄┘

cli.py ─┐
        ├──► assembleur.py ──► tout ce qui précède
vues/ ──┘
```

`parametres/` lit `config/actifs.py`, `pivot/operation.py` et `reglages/`, pour croiser le barème
avec les réglages de chaque actif et parler des mêmes poches que tout le monde. **Aucune flèche ne
part de `moteur/`** : c'est lui qui déclare ce qu'il attend, et `assembleur.py` qui le lui donne.

**`reglages/`** (étape 8 quater) lit `config/` (les corrections), `pivot/` (les prix payés, pour
contrôler une cotation), `donnees_externes/` (les sources), `parametres/contenus` (la table de
lecture du contenu) et une seule fonction du moteur, `moteur.fiscalite.anniversaire` (compter cinq
ans comme le compte l'impôt). L'adaptateur, lui, ne connaît de `reglages/` que la forme neutre
qu'il remplit (`CeQueDitLaBanque`, `MouvementPea`) : `reglages/` ne sait pas lire un export, comme
le moteur ne sait pas lire un CSV de la banque.

Ce qui en découle, et qui se vérifie en lisant les imports :

- **rien n'importe `adaptateurs/` sauf les sorties** : `assembleur.py`, `cli.py`, et l'accueil de
  `vues/`, qui parle de l'export lui-même (le dossier de dépôt, la période couverte, un fichier
  déposé à vérifier). Le moteur ignore l'existence de Trade Republic ([D-26](decisions.md)) ;
- **`pivot/` n'importe ni l'adaptateur ni le moteur.** C'est un contrat : il ne dépend d'aucun
  de ses deux usagers, sinon il cesserait d'en être un ;
- **`moteur/` n'importe que `pivot/`, `tableur.py` et lui-même.** C'est la propriété la plus
  importante du projet, et la plus facile à casser par inadvertance : un seul import
  d'adaptateur dans `moteur/` annulerait l'ouverture aux autres banques ;
- **`moteur/` n'importe ni `parametres/` ni `config/`**, exactement comme il n'importe pas
  `donnees_externes/` : il déclare des protocoles (`ParametresDeCouts` dans `moteur/couts.py`,
  `ReglesFiscales` dans `moteur/fiscalite.py`, et depuis l'étape 7 `SourceDeComposition` et
  `Referentiels` dans `moteur/diversification.py`) et `assembleur.py` lui passe des objets qui les
  satisfont. Un taux fiscal entre dans le moteur comme un cours : **par paramètre** ;
- **la composition d'un actif suit exactement le même chemin**, et c'est la **quatrième** fois :
  le moteur déclare ce qu'il attend d'une source (`composition(actif)`) et de quoi nommer un code
  (`secteur`, `pays`, `zone_de`, `classe`), et `_fournisseur_de_compositions()` et
  `referentiels()`, dans `assembleur.py`, sont les **seuls** endroits qui nomment extraETF, GLEIF et
  les fichiers TOML. Changer de source de composition ne toucherait donc que l'assembleur ;
- **`moteur/` n'importe pas `donnees_externes/` non plus**, et c'est ce qui surprend le plus.
  Les cours y entrent de deux façons, et aucune n'est un import : les prix manquants
  **complètent des opérations pivot avant lui** (§5.7) ; et pour valoriser, le moteur
  **déclare ce qu'il attend** d'une source — un protocole d'une méthode, `cours(actif, date)`,
  dans `moteur/valorisation.py` — que le fournisseur de `donnees_externes/` satisfait sans le
  savoir. C'est `assembleur.py` qui passe l'un à l'autre, et un test (`tests/moteur/test_valorisation.py`)
  prouve que les deux s'emboîtent. Changer de source de cours ne toucherait donc toujours que
  `cli.py`.

Deux flèches surprennent à la lecture, et sont voulues :

| Flèche | Pourquoi |
|---|---|
| `config/actifs.py` → `pivot.operation.DEVISE_UNIQUE` | La devise déclarée d'un actif est confrontée à celle du pivot ([D-48](decisions.md)). La redéfinir ailleurs créerait deux valeurs à tenir à jour |
| `adaptateurs/…/lecture.py` → `pivot.validation.controler` | Les contrôles de cohérence du pivot ([format-pivot §5](format-pivot.md)) tournent **pendant la lecture**, pas dans le moteur. Une ligne douteuse est repérée là où on peut encore dire de quelle ligne de quel fichier elle vient |

`tableur.py` est le seul module partagé hors contrat : il n'écrit que de la mise en forme de
nombres, et il vit à la racine pour qu'aucun export n'invente ses propres conventions.

---

## 4. Carte des fichiers

```
pastory/
├── cli.py                     la ligne de commande : les messages et les fichiers écrits
├── assembleur.py              le seul assembleur, pour la ligne de commande et l'interface
├── avancement.py              où en est une longue lecture : un compteur d'actifs traités,
│                              que l'assembleur fait avancer et que l'écran lit (D-110)
├── tableur.py                 comment on écrit un nombre (CSV et phrases)
├── lanceur.py                 ce que fait le raccourci : la fenêtre à part, le port pris
│                              d'avance, le journal, l'arrêt quand on la ferme (D-106)
├── installation.py            les raccourcis du bureau et du menu Démarrer (D-106)
├── demonstration/             le portefeuille fictif (D-107)
│   ├── __init__.py            le scénario, l'export écrit par le programme, le dossier à part
│   └── clotures.py            les vraies clôtures qui servent de prix d'achat (fichier relevé)
├── config/
│   ├── emplacements.py        où vivent les fichiers personnels (D-37), et ceux de la
│   │                          démonstration (D-107)
│   ├── actifs.py              les corrections, champ par champ : jamais réécrites (D-92)
│   └── fiscalite.py           la date du PEA, corrigée à la main si besoin (D-86)
├── reglages/                  ce qui se trouve seul, et d'où ça vient (D-80)
│   ├── __init__.py            Origine, Trouvee, Trou, Reglage ; ce que dit la banque
│   ├── assemblage.py          correction > valeur trouvée > trou ; l'histoire du PEA (D-86)
│   ├── recherche.py           cotation contrôlée par le prix payé (D-85), TER (D-90),
│   │                          contenu (D-89)
│   ├── cache.py               reglages.csv : ce qui a été trouvé, avec son origine
│   └── rapport.py             le rapport de « pastory actifs »
├── adaptateurs/
│   └── trade_republic/        l'export officiel des transactions (D-79)
│       ├── fichier.py         lire un fichier, ses deux variantes, sans rien garder d'une
│       │                      ligne d'espèces que son type
│       ├── depot.py           le dossier de dépôt : un fichier, un portefeuille (D-109) ;
│       │                      celui qui est ouvert, sa période, et comparer deux exports
│       ├── classement.py      trois catégories, sur (category, type), aucune par défaut (D-08)
│       ├── lecture.py         le cœur : une ligne devient une opération pivot, ou un refus
│       └── rapport.py         tout ce qui n'a pas été compris, et ce que le fichier ne dit pas
├── pivot/
│   ├── operation.py           le contrat n° 1 : une opération sur un actif
│   ├── validation.py          les contrôles de cohérence d'une ligne
│   └── export_csv.py          les opérations, pour le tableur
├── moteur/
│   ├── position.py            le rejeu, opération par opération, et le journal (D-44)
│   ├── portefeuille.py        toutes les positions : par poche, et au total
│   ├── valorisation.py        ce que valent les actifs à une date, et ce qu'il attend d'une
│   │                          source de cours (D-52, D-53)
│   ├── rendements.py          gain, TRI, TWRR par actif, poche et total (D-22, D-54)
│   ├── couts.py               coûts payés (avec leur poids) et estimés : spread, TER (D-17)
│   ├── fiscalite.py           l'impôt estimé par poche, si on vendait tout (D-59, D-60)
│   ├── valeur_reelle.py       valeur brute moins frais, spread et impôt (D-23)
│   ├── diversification.py    par classe d'actifs, par pays, par secteur (D-66 à D-69), et ce
│   │                          qu'il attend d'une source de compositions et d'un référentiel
│   ├── signalement.py         ce que le moteur n'a pas pu calculer normalement (D-45)
│   ├── rapport.py             le rapport de « pastory positions »
│   └── export_csv.py          les onze CSV : positions, journal, valorisation, flux,
│                              sous-périodes du TWRR, évolution, coûts, valeur réelle,
│                              et trois répartitions
├── donnees_externes/
│   ├── cours.py               le contrat : un cours, un refus, une source interchangeable
│   ├── cache.py               un CSV par actif, définitif et oubliable (D-50)
│   ├── yahoo.py               la source retenue, et ses trois garde-fous (D-51)
│   ├── xetra.py               la liste des ETF : le TER par ISIN (D-61, D-90)
│   ├── amundi.py              le secours (pays de l'indice, D-77) et le TER de l'émetteur (D-90)
│   ├── firds.py               le code CFI du registre de l'ESMA, témoin du contenu (D-89)
│   ├── completion.py          les prix manquants complétés, du pivot vers du pivot (D-15)
│   ├── composition.py         le contrat : une composition, ses contrôles, le fournisseur (D-63)
│   ├── cache_compositions.py  un CSV par actif, daté et **remplaçable** (D-70)
│   ├── extraetf.py            la composition d'un ETF par ISIN, agrégats seuls (D-63, D-64),
│   │                          et sa classe d'actifs, code et libellé (D-89)
│   └── actions.py             le pays (GLEIF) et le secteur d'une action en direct (D-66)
├── parametres/
│   ├── lecture.py             un taux sans date ni source est refusé (D-58)
│   ├── referentiels.py        les secteurs, les pays, les zones, les classes d'actifs
│   ├── fiscalite.toml         12,8 % + 18,6 %, durée du PEA, seuil crypto — datés et sourcés
│   ├── couts.toml             frais par ordre, spreads par défaut avec leur fourchette
│   ├── secteurs.toml          les 11 secteurs Morningstar, jamais « GICS » (D-65)
│   ├── zones.toml             pays ISO 3166-1 → nom français et zone (D-66, D-67)
│   ├── classes_actifs.toml    actions, obligations, liquidités : qui entre dans quoi (D-68)
│   ├── contenus.toml          code d'extraETF et lettre CFI → contenu d'un fonds (D-89)
│   ├── contenus.py            sa lecture
│   ├── fiscalite.py           les règles fiscales, telles que le moteur les attend
│   └── couts.py               le barème croisé avec les réglages de chaque actif
└── vues/                      l'interface Dash (étape 9) : `pastory ouvrir`
    ├── application.py         la page, les trois rappels (choisir, rendre, déposer), le lancement,
    │                          l'adresse de vie et le signe de vie de la page (D-106)
    ├── veille.py              qui est encore là : Pastory s'arrête avec sa dernière page (D-106)
    ├── attente.py             ce que la page montre pendant une lecture : l'étape, le compte
    │                          d'actifs, la barre — et l'adresse où elle le demande (D-110)
    ├── chiffres.py            l'assembleur appelé une fois, la période et les poches recalculées
    ├── ecrans.py              quel écran pour quel état
    ├── etat.py                ce que l'utilisateur a choisi : l'onglet, la période, les poches…
    ├── format.py              une fonction par unité : montant, taux, pour cent (§3.1 du contrat)
    ├── vocabulaire.py         les bulles « ? », mot pour mot ceux de la maquette
    ├── briques.py             bloc, tuile, bulle, groupe de boutons, emplacement de dessin
    ├── bandeau.py             la manchette, les filtres, l'état des données
    ├── accueil.py             où trouver l'export, où le déposer, ce que la lecture a trouvé
    ├── reception.py           un export déposé : vérifié sur place, puis mis à jour, nouveau
    │                          portefeuille ou version ancienne, selon ses opérations (D-109)
    ├── portefeuilles.py       sur la couverture : en ouvrir un, le renommer, le supprimer
    ├── surveiller.py          « à surveiller » : tout ce que chaque couche signale
    ├── synthese.py            les tuiles, la courbe, les poches, les cartes d'actifs
    ├── actifs.py              le tableau des actifs, filtrable et triable, et sa remarque par ligne
    ├── diversification.py     les quatre rubriques : chiffres clés, classement, restes repliés,
    │                          et chaque ligne dépliable vers ses actifs (D-111)
    ├── frais.py               les trois niveaux : prélevé, détention, sortie
    ├── detail.py              la page discrète « Détail des calculs », et « à surveiller » en bas
    └── assets/                pastory.css (la feuille de la maquette), les polices, dessin.js,
                               les drapeaux (flag-icons, licence MIT)

scripts/
├── inventaire_structure.py    relevé structurel d'un export officiel, sans aucune valeur (D-05)
└── releve_de_demonstration.py écrit `demonstration/clotures.py` : à relancer si le scénario change

Installer Pastory.cmd          un double-clic : `uv` s'il manque, l'environnement, puis les
                               raccourcis (D-106, D-112)

tests/                         même arborescence que pastory/, données fictives (D-38)
```

---

## 5. Couche par couche

### 5.1 `config/` — les fichiers, et ce que seul l'utilisateur sait

**`emplacements.py` : rien de personnel n'est écrit dans le projet.** Le dossier du projet est
synchronisé par OneDrive ([D-24](decisions.md)) ; tout ce qui est réécrit souvent va donc
ailleurs ([D-37](decisions.md)), dans un dossier propre au système (`LOCALAPPDATA` sous Windows),
avec trois sous-dossiers : `exports/` — **le dossier de dépôt**, où l'utilisateur dépose ses
exports ([D-80](decisions.md)) —, `cache/`, `configuration/`. La variable
`PASTORY_DOSSIER` permet d'en choisir un autre — c'est ce dont se servent les tests, qui
n'écrivent donc jamais dans le vrai dossier de l'utilisateur.

**Plus aucune question préalable.** Jusqu'à l'étape 8 ter, `comptes.py` demandait le rôle de
chaque compte espèces, parce que pytr ne disait pas à quelle poche appartenait un achat. L'export
officiel l'écrit sur chaque ligne : la question a disparu avec lui ([D-81](decisions.md)). Ce qui
restait dans `config/` — ticker, type, TER, contenu, date du PEA — est **trouvé seul** depuis
l'étape 8 quater ([D-80](decisions.md)) : `actifs.toml` et `fiscalite.toml` ne portent plus que des
**corrections**, toutes facultatives, que l'application ne réécrit jamais ([D-92](decisions.md)).

### 5.2 `adaptateurs/trade_republic/` — de l'export aux opérations

L'export officiel est un fichier de **colonnes** ([export-officiel.md](export-officiel.md)) : la
poche, la quantité, le prix, le montant brut, les frais et les taxes y sont des données, et rien
n'est lu dans un texte, sauf la nature de l'opération, qui n'est qu'affichée. Le risque n'est donc
plus de mal lire, mais de **mal comprendre** : aucune liste des types n'est publiée. La couche est
découpée en conséquence.

| Module | Ce qu'il fait | Pourquoi il est séparé |
|---|---|---|
| `fichier.py` | Lit un fichier, virgule ou point-virgule, colonnes repérées **par leur nom** ; une ligne d'espèces y perd tout sauf son type, ses dates et son identifiant | Les données personnelles ne passent pas cette porte ([export-officiel.md §8](export-officiel.md)) |
| `depot.py` | Tient la liste des portefeuilles du dossier — **un fichier, un portefeuille** ([D-109](decisions.md)) —, lit celui qui est ouvert, dit sa période, et compare deux exports par leurs `transaction_id` | L'utilisateur dépose ses exports, et c'est tout ([D-80](decisions.md)) ; un export partiel ne se voit que par sa période ([D-45](decisions.md)) |
| `classement.py` | Range chaque couple `(category, type)` en `TRAITE`, `HORS_PERIMETRE` ou `INCONNU` | Liste explicite, aucun classement par défaut ([D-08](decisions.md), règle 5 de CLAUDE.md) |
| `lecture.py` | Fait d'une ligne traitée une `Operation`, ou la refuse | C'est le seul module qui décide du **sens** d'une ligne, et le seul qui refuse une **forme** jamais vue |
| `rapport.py` | Accumule tout ce qui n'a pas été compris | Un défaut de lecture doit ressortir à l'écran, pas disparaître |

**La chaîne d'une lecture**, dans l'ordre :

1. `depot.lire()` lit **un** portefeuille : le fichier désigné, ou celui qui est ouvert dans le
   dossier. Les autres fichiers ne sont pas lus ; un fichier qui n'est pas un export est cité
   et écarté ;
2. `classement.classer()` range la ligne. `INCONNU` → elle est comptée et affichée, avec ce que
   l'on sait du type ; une ligne d'espèces n'est que comptée ;
3. `lecture.Lecteur` vérifie que la ligne a **la forme vue sur de vrais fichiers** : une quantité
   positive et un montant négatif pour un achat, un montant positif et pas de prix pour un
   dividende, une classe d'actif connue, l'euro. Sinon, **l'opération n'est pas produite**, et le
   rapport dit pourquoi ;
4. la poche vient d'`account_type` et d'`asset_class` : une donnée, jamais une déduction ;
5. `pivot.validation.controler()` vérifie la ligne (le jour, les signes, quantité × prix = brut),
   et, sur un dividende en devise, `original_amount × fx_rate = amount`. Rien n'est corrigé :
   l'écart part au rapport.

**L'adaptateur a une seule sortie : un `Rapport`.** Il porte les opérations *et* tout ce qui a
résisté — types non traités, formes refusées, anomalies, période couverte, et la limite connue
du brut des dividendes ([D-84](decisions.md)). Les deux voyagent ensemble pour qu'on ne puisse pas
lire les chiffres sans voir leurs réserves.

### 5.3 `pivot/` — le contrat

Figé à l'étape 1 ([D-35](decisions.md)), décrit champ par champ dans
[format-pivot.md](format-pivot.md). Trois règles de forme portent tout le reste :

1. **tous les nombres sont positifs** ; le sens est porté par le `type` ;
2. **les montants sont des `Decimal`**, jamais des flottants ([D-33](decisions.md)) ;
3. **aucun numéro de compte n'entre dans le pivot.**

`montant_regle` est le seul champ facultatif d'un montant : l'export officiel ne donne pas ce qui
a été réellement débité, et le champ reste vide plutôt que recalculé ([D-83](decisions.md)).

Cinq types seulement, et la liste est **fermée** : `achat`, `vente`, `dividende`,
`distribution_capital`, `titres_recus`. Un cas qui n'y entre pas est signalé comme inconnu,
jamais rangé de force dans un type voisin.

Chaque valeur porte sa **provenance** : `donnee` (champ structuré), `texte` (lu dans un libellé,
fragile), `deduction` (règle écrite), `estimation`, `a_completer` (attend un cours). C'est ce qui
permet à l'interface de montrer d'un coup d'œil ce qui est solide et ce qui ne l'est pas.

### 5.4 `moteur/` — le rejeu et l'agrégation

**`position.py` est le module que le propriétaire doit pouvoir refaire sur papier.** Il rejoue
les opérations d'un actif une par une et tient, à chaque pas, la quantité détenue et le capital
net investi. Quatre propriétés le rendent vérifiable :

- **la clé d'une position est le couple (actif, poche)**, jamais l'actif seul : un même ETF
  détenu en PEA et en CTO a deux prix de revient et deux fiscalités ([D-44](decisions.md)) ;
- **l'ordre est imposé, jamais supposé** : horodatage exact, puis identifiant pour départager
  deux opérations simultanées. L'ordre du fichier d'export ne fait pas foi ;
- **le moteur tient un journal** : une ligne par opération, avec l'état d'avant et l'état d'après.
  Sur chaque ligne, *capital avant + ajouté − retiré = capital après* ([D-44](decisions.md)) ;
- **trois refus explicites**, chacun accompagné d'un signalement ([D-45](decisions.md)) : prix
  inconnu, vente au-delà du stock compté (la quantité ne devient jamais négative), distribution
  de capital au-delà du capital investi (plancher à zéro).

`portefeuille.py` **agrège, il ne calcule pas** : chaque total se retrouve en additionnant une
colonne du tableau des positions. `Portefeuille.au(date)` donne l'état de n'importe quel jour
passé en coupant le journal — rien n'est rejoué, et c'est là-dessus que s'appuient la
valorisation et les rendements.

`valorisation.py` **multiplie, et dit ce qu'il n'a pas pu multiplier** : parts détenues à une
date × cours de clôture retenu, au centime. Il déclare la forme d'un cours (`CoursDeMarche`) et
d'une source (`SourceDeValorisation`, une méthode) sans nommer aucune source. Une position sans
cours utilisable est **non valorisée**, sort des totaux, et les totaux sont marqués partiels
([D-53](decisions.md)). La valeur d'« aujourd'hui » est celle de la dernière clôture connue, et
chaque position dit quel jour l'a fournie ([D-52](decisions.md)). `evolution()` répète cela jour
par jour.

`rendements.py` **enchaîne, dans l'ordre où on le refait** : la valeur à la fin (et qui n'en a
pas), les flux signés de la période, la valeur au début, puis le gain, le TRI et le TWRR
([D-54](decisions.md)). Le TRI est cherché par dichotomie sur la même table que celle que
`flux.csv` donne au tableur ; le TWRR garde chacune de ses sous-périodes, avec la valeur qui
l'ouvre et celle qui la ferme. Tout se calcule par **groupe de positions** — un actif, une poche,
le portefeuille — et `Synthese` réunit les trois niveaux. Ce qui n'a pas de sens porte un
**motif** au lieu d'un nombre : montant encore à compléter, cours manquant un jour de flux,
flux tous du même signe.

`couts.py`, `fiscalite.py` et `valeur_reelle.py` sont l'étape 6, et ils ne touchent à rien de
ce qui précède. `couts.py` détaille les coûts **payés** — une ligne par opération, avec leur
**poids** dans l'opération — et estime ceux que personne ne facture : le spread à chaque achat et
à chaque vente ([D-30](decisions.md), [D-56](decisions.md)), le TER pendant la détention.
`fiscalite.py` calcule la base imposable et l'**impôt estimé** de chaque poche dans le scénario
« tout vendre aujourd'hui », chacune avec sa règle : plus-values compensées en CTO, gain **du
plan** en PEA ([D-59](decisions.md)), seuil d'exonération en crypto. `valeur_reelle.py` assemble :
valeur brute − frais de vente − spread − impôt ([D-23](decisions.md)), et hérite de
[D-53](decisions.md) — un actif sans cours n'a pas de valeur réelle, et le total le dit.

Trois propriétés les rendent vérifiables :

- **chaque estimation porte le paramètre qui l'a produite** (valeur, date, source), et le rapport
  l'écrit sous le chiffre. Un taux qu'on ne peut plus retrouver ne se vérifie plus ;
- **le capital fiscal est tenu dans le rejeu**, une colonne à côté du capital investi
  ([D-57](decisions.md)) : le prix de revient fiscal se suit dans `journal.csv` comme l'autre ;
- **ce qui manque est nommé** : actif sans type, ETF sans TER, PEA sans date. Jamais un zéro.

`diversification.py` est l'étape 7, et il ne touche à rien non plus : il part de la **même**
valorisation que les rendements et les coûts, et n'en tire que des poids. Sa seule règle vaut
d'être lue, parce qu'elle explique tous ses chiffres :

```
valeur de la position = part actions + part non-actions
part actions          = ce que la composition attribue + non attribué
```

La **part non-actions** sort de la géographie et des secteurs ([D-68](decisions.md)) : sur un indice
obligataire, « secteur » veut dire Trésor ou entreprises, et « pays » peut vouloir dire devise
d'émission. Le **non attribué** est ce que la source laisse de côté, et il reste visible : aucune
composition ne somme à 100 %, et rien n'est renormalisé ([D-69](decisions.md)). Un actif sans
composition est **non couvert**, une crypto est **hors classification** — ce qui n'est pas la même
chose, et l'écran ne les confond pas.

Deux propriétés le rendent vérifiable : **tout pourcentage se rapporte à la valeur totale des
actifs valorisés**, jamais à la somme des postes ; et **la somme des postes et des restes vaut
exactement cette valeur**, ce que les trois CSV permettent de contrôler dans un tableur.

Une troisième, depuis [D-111](decisions.md) : **chaque poste et chaque reste nomme les actifs qui
le font** (`Poste.contributions`, et `non_attribue_par_actif`, `non_couvert_par_actif`,
`hors_classification_par_actif` sur la répartition), et **leur somme est son montant, au
centime**. Ce n'est pas un second calcul : chaque euro rangé dans une case y est noté avec son
actif d'origine, au moment même où il est cumulé (`_Cumul`). L'écran les montre en dépliant la
ligne.

**Le contrôle des quantités n'est plus dans le moteur.** Le rapprochement avec la photo du
portefeuille de la banque est parti avec pytr ([D-81](decisions.md)). Le rapport de `positions`
se termine désormais par une invitation à comparer chaque quantité à l'écran de l'application :
c'est le seul moyen de repérer des titres entrés sans aucune ligne dans l'export.

`signalement.py` est le pendant, côté moteur, du rapport de lecture. Il existe séparément parce
que le moteur ne connaît pas l'adaptateur.

**Deux comptabilités séparées dès le moteur** ([D-21](decisions.md)) : la *performance* sur
montants bruts, et les *coûts* — frais et taxes réels rangés par moment, puis spread et TER
estimés, impôt estimé, valeur réelle. Elles ne se mélangent dans aucun chiffre, et l'étape 6 n'a
pas déplacé un centime de la première : les tests de l'étape 5 le prouvent, inchangés.

### 5.5 `tableur.py` — les CSV que le propriétaire ouvre

Trois conventions, au même endroit pour qu'aucun export n'en oublie une : point-virgule et
virgule décimale, pas de séparateur de milliers, UTF-8 **avec BOM**. Sans quoi Excel en français
lit « 25.00 » comme du texte ou comme une date, et affiche les accents de travers.

Sept fichiers en sortent : les opérations du pivot, puis les six du moteur — `positions.csv`,
`journal.csv`, `valorisation.csv`, `flux.csv`, `sous_periodes_twrr.csv`, `evolution.csv`. **Le
journal est la pièce à ouvrir pour vérifier un chiffre** sans lire une ligne de code ;
`flux.csv` joue le même rôle pour le TRI (c'est la table de `TRI.PAIEMENTS`), et
`sous_periodes_twrr.csv` pour le TWRR. Tous contiennent de vraies valeurs : ils sont écrits dans
le dossier personnel, hors du dossier synchronisé, et n'entrent jamais dans git
([D-01](decisions.md), [D-37](decisions.md)).

### 5.6 `assembleur.py` et `cli.py` — brancher, puis dire

`assembleur.py` est le seul module qui connaisse toutes les couches, et c'est son rôle : il
branche l'adaptateur sur le moteur. Aucune couche n'appelle l'autre d'elle-même. Il est sorti de
`cli.py` à l'étape 9, sans changer une ligne de calcul, pour que la ligne de commande **et**
l'interface l'appellent : un seul assemblage, donc les mêmes chiffres à l'écran et dans
`pastory positions`. `cli.py` garde ce qui est propre à la ligne de commande : les messages, et
les fichiers qu'elle écrit.

| Commande | Ce qu'elle traverse | Écrit quelque chose ? |
|---|---|---|
| `emplacements` | `config` | crée les dossiers |
| `lire` | adaptateur | **non** — un rapport à l'écran (crée le dossier de dépôt s'il manque) |
| `actifs` | adaptateur → `reglages` → `donnees_externes` | **non** dans les fichiers de l'utilisateur ; ce qui est trouvé va dans `cache/reglages.csv` |
| `exporter-pivot` | adaptateur → `pivot` | les opérations en CSV |
| `positions` | adaptateur → `pivot` → `donnees_externes` → `parametres` → moteur | **non** — un rapport à l'écran |
| `exporter-positions` | idem | les douze CSV du moteur |
| `ouvrir` | tout, par l'assembleur, puis `vues/` | **non**, sauf un export déposé dans l'accueil (rangé dans le dossier de dépôt) ; et, au bloc 9.5, une correction saisie à l'écran |

Trois options traversent plusieurs commandes : `--export <dossier>` pour lire les exports d'un
autre dossier que le dossier de dépôt — celui de quelqu'un d'autre, sans le copier dans le
projet ; `--au AAAA-MM-JJ` pour arrêter les chiffres à une
date, qui est aussi la date de valorisation et la fin de la période des rendements (sans elle :
aujourd'hui, à la dernière clôture connue, [D-52](decisions.md)) ; `--depuis AAAA-MM-JJ` pour
faire commencer cette période ailleurs qu'à la première opération.

Pour `positions` et `exporter-positions`, **un seul** `FournisseurDeCours` sert à la fois à la
complétion des prix manquants et à la valorisation : ses refus couvrent les deux, et le bloc
« Cours de marché » du rapport les liste tous. De même, **une seule** valorisation sert aux
rendements, aux coûts et à la valeur réelle : deux valorisations du même jour pourraient différer
d'un centime, et le rapport montrerait deux valeurs brutes.

C'est aussi dans l'assembleur que les **réglages** sont réunis, une fois par lecture : `reglages()` réunit
ce que dit la banque, ce que trouvent les sources et les corrections, et rend la configuration
effective que `fournisseur_de_cours()`, `parametres_des_couts()` et
`fournisseur_de_compositions()` reçoivent en paramètre. `regles_fiscales()` y prend la date du
PEA, son origine, sa réserve, et l'alerte d'un retrait ([D-87](decisions.md)).
`source_des_cotations()`, `frais_courants_de_l_emetteur()`, `liste_des_etf()`,
`classes_d_actifs()` et `registre_cfi()` sont les seuls endroits qui nomment ces sources — et
ceux que les tests remplacent (`tests/garde_fous.py`, actifs pour toute la suite), pour qu'aucun
ne sorte de la machine.

**Les trois temps longs d'une lecture, et qui les compte** ([D-110](decisions.md)). `construire()`
reçoit un `Suivi` (`pastory/avancement.py`) et y dit où il en est, actif par actif : les réglages
(`reglages()`, par `Recherche.trouver`), les cours (`remplir_les_cours()`), les compositions.
`avancement.py` ne connaît ni l'écran ni les sources : il compte. C'est `vues/attente.py` qui
écrit les mots et répond à la page. Deux choses à ne pas défaire :

- **`remplir_les_cours()` passe avant tout calcul**, et demande à la source **une fois par
  actif**, de sa première opération à hier. Sans lui, `FournisseurDeCours.cours()` remplit le
  cache par petites fenêtres, une par date d'opération : cinq fois plus lent sur un dossier vide,
  et quelques jours sans cours entre deux fenêtres ;
- **les compositions sont demandées dans l'ordre où `diversifier()` les demanderait** : le
  fournisseur garde ses réponses, et l'ordre des refus affichés ne change pas.

### 5.6 bis `lanceur.py`, `installation.py`, `demonstration/` — ouvrir Pastory comme un logiciel

Trois modules de l'étape 10, qui ne calculent rien et dont aucun calcul ne dépend.

**Le lanceur** ([D-106](decisions.md)) est ce qu'appelle le raccourci. Il ne charge l'interface
qu'après avoir **pris le port** et **ouvert la fenêtre** : Dash et pandas mettent plusieurs
secondes à se charger, et pendant ce temps la page attend à la porte au lieu de laisser croire
que rien ne se passe. Un second lancement trouve le port pris, demande « qui est là ? » à
l'adresse de vie (`/pastory/vie`), et ramène la fenêtre existante.

**La veille** (`vues/veille.py`) est le seul lien entre la fenêtre et le serveur : la page donne
signe de vie, le serveur compte les battements de silence, et s'arrête quand plus aucune page
n'est là. Elle ne connaît ni Dash ni le réseau, et se teste avec une horloge factice. Elle n'est
branchée que par le lanceur : `pastory ouvrir`, dans un terminal, s'arrête toujours par Ctrl+C.

**La démonstration** ([D-107](decisions.md)) ne touche à aucune couche : elle **écrit un export**
dans un autre dossier personnel et y pointe `PASTORY_DOSSIER` avant tout le reste. Le lecteur,
les réglages, le moteur et les vues font ensuite exactement ce qu'ils font pour un vrai export.
Deux choses seulement savent qu'il s'agit d'une démonstration : l'écran, qui le dit partout et
retire le dépôt, et l'adresse de vie, pour que la démonstration et le vrai portefeuille ne se
répondent jamais l'un à la place de l'autre. Toutes deux le lisent **au même endroit, le nom du
dossier personnel** (`emplacements.est_une_demonstration`) : il n'y a pas d'option à accorder
avec lui.

**Ce que le lanceur et l'application doivent dire de la même façon** — le nom, l'hôte, le port, le
titre de la fenêtre, l'adresse de vie et ce qu'elle répond — est écrit une fois, dans
`vues/veille.py`. C'est par ces valeurs que le lanceur reconnaît son propre Pastory : dites à deux
endroits, elles finiraient par différer, et un second Pastory démarrerait sans qu'aucun test ne
le voie.

### 5.7 `donnees_externes/` — les cours, et ce qu'on refuse d'inventer

Quatre fichiers, et un principe qui les explique tous : **on refuse plutôt que d'estimer**.

- **`cours.py` — le contrat.** Un `Cours` porte sa valeur, le **jour qu'il décrit**, sa place, sa
  source et le jour où il a été récupéré : sans cela, un cache définitif ([D-50](decisions.md))
  deviendrait un cache opaque. Un `Refus` porte son motif, en français. `SourceDeCours` est le
  protocole d'une source ; `FournisseurDeCours` réunit la configuration, le cache et la source, et
  **n'échoue jamais** — il rend `None` avec un motif.
- **`cache.py` — un CSV par actif**, aux conventions de `tableur.py`, donc relisible dans un
  tableur. Un cours déjà écrit n'est **jamais** réécrit ; `oublier()` est la seule sortie.
- **`yahoo.py` — la source** ([D-51](decisions.md)), en bibliothèque standard : `urllib` utilise le
  magasin de certificats de Windows, celui que l'antivirus de la machine ne casse pas, et
  `parse_float=Decimal` fait qu'aucun cours n'existe jamais sous forme de flottant
  ([D-33](decisions.md)). Quatre garde-fous, tous nés d'un piège vérifié : la devise annoncée est
  confrontée à celle déclarée ([D-48](decisions.md)) ; une série trop espacée est refusée (la
  source renvoie du mensuel en annonçant du quotidien) ; le champ `adjclose` n'est **jamais** lu,
  sinon les dividendes seraient comptés deux fois ([D-29](decisions.md)) ; et la **séance en
  cours** n'est pas rendue — son cours n'est pas une clôture, et le cache étant définitif, il
  figerait un prix intermédiaire pour toujours.
- **`completion.py` — le branchement de [D-15](decisions.md)**, et le point d'architecture de
  l'étape. Il transforme du pivot en pivot : un `montant_brut` marqué `a_completer` devient un
  montant marqué `deduction`, les deux provenances que
  [format-pivot §4](format-pivot.md) avait prévues. **Le moteur n'a pas gagné une ligne** : il
  savait déjà traiter les deux cas.

### 5.8 `reglages/` — ce qui se trouve seul, et d'où ça vient

Une seule forme pour tout réglage ([D-80](decisions.md)) : une **valeur trouvée** (`Trouvee`)
porte son `Origine` — la source, la date que décrit la source, ce qui a été **vérifié**, et ce
qu'il faut savoir pour s'y fier — ; un **trou** (`Trou`) porte son motif. `Reglage` réunit la
valeur retenue et, quand une correction l'a remplacée, celle que la source donnait, pour que les
deux se voient côte à côte.

- **`assemblage.py`** décide, réglage par réglage : la correction, sinon la valeur trouvée, sinon
  le trou. Il lit aussi l'**histoire du PEA** dans ses mouvements d'espèces ([D-86](decisions.md)).
  Il rend `Reglages`, dont `configuration()` donne la configuration effective : les cours, les
  coûts et les compositions la lisent comme avant, sans savoir qu'elle a été trouvée.
- **`recherche.py`** cherche ce que l'export ne donne pas et le **contrôle** : la cotation par le
  prix payé et le change ([D-85](decisions.md)), le TER par sa fourchette et l'accord des sources
  ([D-90](decisions.md)), le contenu par le témoin CFI ([D-89](decisions.md)). Rien n'est cherché
  pour l'export d'un tiers (règle 2 de CLAUDE.md).
- **`cache.py`** garde ce qui a été trouvé, origine comprise, dans un CSV ouvrable dans un
  tableur : une cotation pour toujours (ses cours le sont aussi), un TER ou un contenu un mois, un
  trou une semaine, une panne jamais.

Le trajet d'une valeur trouvée, pour la cotation d'un ETF *(valeurs fictives)* :

| Où | Ce qui se passe | Ce qu'on peut vérifier |
|---|---|---|
| `recherche` | Par l'ISIN : `AAAA.L` en dollars, écarté (D-48). Par le nom : `AAAA.DE` et `AAAD.DE`, en euros | — |
| `recherche` | Clôtures aux jours des quatre derniers achats : écart médian 0,3 % du prix payé pour l'un, 2,1 % pour l'autre ; change contre `AAAA.L` converti : 0,04 % et 2,0 % | `pastory actifs`, ligne « vérifié » |
| `cache` | `AAAA.DE` gardé, avec sa source, sa date et son contrôle | `cache/reglages.csv` |
| `assemblage` | Aucune correction : `AAAA.DE` s'applique | « trouvé : Yahoo Finance (recherche) » |
| `cours` | Les cours de `AAAA.DE`, refusés s'ils n'arrivent pas en euros | Le cache des cours |

---

## 6. Le trajet d'un chiffre, de bout en bout

Un achat de 10 parts à 20,00 €, avec 1,00 € de frais et 0,60 € de taxe *(valeurs fictives,
celles de [format-pivot §6](format-pivot.md))* :

| Où | Ce qui se passe | Ce qu'on peut vérifier |
|---|---|---|
| Export | Une ligne `TRADING / BUY`, `account_type = PEA`, `shares = 10`, `price = 20.00`, `amount = -200.00`, `fee = -1.00`, `tax = -0.60` | La même ligne, dans un tableur |
| `depot` | Une seule fois, même si deux exports la contiennent (`transaction_id`) | Le rapport compte les doublons |
| `classement` | `TRAITE` → achat | Le type apparaît dans le rapport de lecture |
| `lecture` | Forme vue sur de vrais fichiers : quantité positive, montant négatif, classe `STOCK`. Poche `PEA`, **donnée** | Une forme jamais vue part au rapport, sans opération |
| `pivot` | `quantite` 10, `prix_unitaire` 20,00, `montant_brut` 200,00, `frais` 1,00, `taxes` 0,60, `montant_regle` vide | 10 × 20,00 = 200,00 |
| `moteur/position` | Capital net investi **+ 200,00 €**, pas 201,60 ([D-12](decisions.md)). Les 1,60 € vont dans les coûts ([D-21](decisions.md)) | Une ligne de `journal.csv` : capital avant + 200,00 = capital après |
| `moteur/portefeuille` | La ligne entre dans le total du PEA | La somme de la colonne du tableau des positions |
| Sortie | `positions.csv`, `journal.csv`, le rapport à l'écran | Le tout, en face de l'application Trade Republic |

Chaque case est refaisable à la main, et chaque case a un endroit où elle se plaint. C'est toute
l'intention de l'architecture.

---

## 7. Ce qui traverse toutes les couches

Six règles ne sont la propriété d'aucune couche, et se retrouvent dans toutes.

| Règle | Comment elle se manifeste |
|---|---|
| **`Decimal`, jamais de flottant** ([D-33](decisions.md)) | Tout montant est écrit sous forme de texte : `Decimal("2")`. Une règle de `ruff` qui voudrait l'inverse est désactivée dans `pyproject.toml` |
| **Chaque valeur dit d'où elle vient** | `Provenance` sur chaque champ du pivot, colonne dédiée dans le CSV, affichage à l'étape 9 |
| **Aucun silence** (règles 5 et 6 de CLAUDE.md) | Deux canaux : le `Rapport` de l'adaptateur et les `Signalement` du moteur. Un cas bancal n'arrête rien et ne se corrige jamais tout seul |
| **Une estimation dit qu'elle en est une** ([D-17](decisions.md)) | Spread, TER et impôt sont dans des blocs à part, et chaque montant cite le taux qui l'a produit, avec sa date et sa source ([D-58](decisions.md)) |
| **Vocabulaire métier en français** ([D-34](decisions.md)) | Noms de modules, de classes et de champs. Le propriétaire doit pouvoir lire un nom de fonction |
| **Aucune donnée réelle nulle part** ([D-01](decisions.md), [D-03](decisions.md)) | Dossier personnel hors projet, tests sur données fictives, valeurs fictives dans toute la doc, scripts de diagnostic qui n'affichent aucune valeur |
| **Affichable sur une console Windows** | La console écrit en cp1252 : ni trait de tableau, ni coche, ni flèche dans un rapport. Le CLI force UTF-8, et deux tests vérifient que les rapports restent imprimables. **En ajouter un pour tout nouveau rapport** |

---

## 8. Où vivent les données

| Quoi | Où | Dans git ? |
|---|---|---|
| Le code, la documentation, les tests | Dossier du projet (OneDrive) | oui |
| Exports officiels : **un fichier par portefeuille** ([D-109](decisions.md)) | Dossier personnel → `exports/`, le dossier de dépôt | **non** |
| Le portefeuille ouvert, pour le lancement suivant (`.portefeuille-ouvert`) | Dossier de dépôt | **non** |
| Cours, compositions, et les réglages trouvés (`reglages.csv`) | Dossier personnel → `cache/` | **non** |
| Les corrections de l'utilisateur (`actifs.toml`, `fiscalite.toml`) | Dossier personnel → `configuration/` | **non** |
| Ce que Pastory aurait écrit à l'écran, lancé par son raccourci (`journal.txt`) | Dossier personnel | **non** |
| La démonstration : son export fictif, son cache, sa configuration ([D-107](decisions.md)) | Un **second** dossier personnel, voisin du premier (`Pastory-demonstration`) | **non** : l'export est écrit par le programme |
| Les clôtures qui servent de prix d'achat à la démonstration | `pastory/demonstration/clotures.py` | oui : des cours publics, aucun portefeuille |
| Les CSV de vérification (opérations, positions, journal) | Dossier personnel | **non** |
| Résultats de vérification sur vraies données | `docs/verification/etape-N.local.md` | **non** (exclu) |
| Identifiants Trade Republic | **nulle part** : aucune connexion depuis l'étape 8 ter ([D-81](decisions.md)) | **non** |

Le dossier personnel est **hors du dossier synchronisé**, pour éviter les conflits OneDrive sur
des fichiers réécrits à chaque commande. `uv run pastory emplacements` dit où il est.

---

## 9. Les tests suivent les couches

`tests/` reproduit l'arborescence de `pastory/`, et chaque couche se teste sans la
précédente :

| Test | Part de | Ce que ça prouve |
|---|---|---|
| `tests/adaptateurs/` | Lignes d'export fictives (`export_fictif.py`), une fabrique par forme vue | La lecture comprend l'export, refuse ce qu'elle n'a jamais vu, et ne laisse passer aucune donnée personnelle |
| `tests/pivot/` | Opérations écrites à la main (`exemples.py`) | Les contrôles de cohérence attrapent ce qu'ils doivent |
| `tests/moteur/` | Opérations pivot fictives (`operations_fictives.py`) | Les calculs sont justes — **sans aucune banque** |
| `tests/donnees_externes/` | Réponses écrites à la main, source factice (`cours_fictifs.py`) | Les pièges de la source sont attrapés — **sans aucun réseau** |
| `tests/reglages/` | Ce que dit une banque fictive, des sources factices qui reproduisent les pièges mesurés | Chaque contrôle refuse ce qu'il doit, une correction l'emporte, une panne n'est pas gardée |
| `tests/vues/` | Le même export fictif, lu hors ligne ; l'écran construit en Python, sans navigateur | Chaque écran dans ses états (vide, partiel…), chaque classe a sa règle CSS, aucune règle n'en écrase une autre |
| `tests/test_cli.py` | Un export officiel fictif (`export_ligne_de_commande.py`), plus deux titres reçus ajoutés à la lecture, en le disant ([architecture-notes §3 bis](architecture-notes.md)) | Les commandes s'enchaînent, et les rapports s'affichent en cp1252 |

**Aucune donnée réelle dans les tests** ([D-38](decisions.md)). La vérification sur vraies
données est un exercice séparé, fait par le propriétaire, guidé par un
[cahier de vérification](verification/) par étape.

---

## 10. Ce qui n'existe pas encore, et où ça se branchera

| À venir | Où | Ce qui ne changera pas |
|---|---|---|
| Interface Dash *(étape 9, en cours)* | `vues/`, et `assembleur.py` qui sort de `cli.py` pour servir aux deux | Les vues n'appellent que le moteur et les réglages, par l'assembleur — jamais l'adaptateur ni une source externe. Python met en forme chaque chiffre ; un script repris des maquettes ne fait que dessiner ([D-93](decisions.md)). L'écran de correction écrit un champ, et rien d'autre ([D-94](decisions.md)) |
| Un raccourci pour Mac *(reste de l'étape 10)* | `installation.py` ; le lanceur, lui, ne dépend pas de Windows | Le raccourci appelle le Python de l'environnement par son chemin, jamais `uv run` ([D-106](decisions.md)) |
| Prédiction de l'évolution, Monte-Carlo *(étape 9 bis, [D-97](decisions.md))* | Module indépendant, qui ne lit du moteur que la valeur de départ | Rien ne dépendra de lui ([D-27](decisions.md)) |

Les deux branchements des cours sont **faits** : les **titres reçus sans prix**
([D-15](decisions.md)) reçoivent le cours de leur jour d'apparition (étape 4), et le moteur
**valorise** et calcule les rendements en recevant la source de cours en paramètre (étape 5).
L'étape 6 a suivi le même chemin pour les taux : deux protocoles déclarés dans le moteur, deux
objets fournis par l'assembleur, et **aucun import nouveau** entre les couches.

**L'étape 7 l'a suivi une quatrième fois**, et c'est devenu la manière de faire du projet : la
composition d'un actif et les référentiels qui nomment ses codes entrent par deux protocoles de
plus, déclarés dans `moteur/diversification.py`, et l'assembleur reste le seul à brancher. Le moteur ne
sait toujours ni ce qu'est un ETF, ni ce qu'est un secteur « Technologie » — il reçoit des codes et
demande qu'on les lui nomme.

Ce que l'étape 8 trouvera en place : tous les chiffres que l'interface doit montrer, y compris ce
qui **manque** et pourquoi. Les libellés d'absence — « non couvert », « non attribué », « non
transparisé », « synthétique », « minoré » — sont du contenu d'interface à part entière
([D-62](decisions.md)), pas des notes techniques à reléguer en bas de page.

---

## 11. Comment étendre

**Ajouter une banque** — c'est le cas prévu par [D-26](decisions.md) :

1. un dossier `adaptateurs/<banque>/`, qui produit des `Operation` ;
2. ses propres tests, sur des exports fictifs ;
3. une branche dans `assembleur.py` pour le choisir.

Rien d'autre. Si l'ajout demande de toucher `moteur/`, c'est le signe que le pivot manque d'un
champ : voir [format-pivot §8](format-pivot.md), qui dit comment le format évolue.

**Ajouter ou remplacer une source de cours** : un module dans `donnees_externes/` qui suit le
protocole `SourceDeCours` (une méthode, `serie`), et une ligne dans `assembleur.fournisseur_de_cours` —
le seul endroit de l'application qui nomme Yahoo. Le cache, la correspondance ISIN → ticker et
tout le reste sont déjà communs. Une source doit **lever** une `ErreurDeSource` plutôt que de
rendre une valeur approchée : c'est ce qui garantit qu'un cours douteux devient un refus visible
et non un chiffre.

**Ajouter un type d'opération** : le pivot est une liste **fermée**. Ajouter un type se décide
d'abord ([format-pivot §8](format-pivot.md) et une entrée dans `decisions.md`), puis se propage
en trois endroits : `TypeOperation`, les contrôles de `validation.py`, et le tableau de
`moteur/position.py`.

**Ajouter un rapport** : un test qui vérifie qu'il s'affiche en cp1252 (§7).

---

## 12. Limites connues de l'architecture

Aucune n'est un défaut à corriger dans l'urgence, mais toutes doivent être connues avant de se
fier à un chiffre.

- **Une valeur trouvée vaut ce que vaut son contrôle.** Deux cotations du même titre sur deux
  places, deux classes d'une même société, une prime d'ouverture lue comme le début du plan : les
  limites de chaque contrôle sont dites dans [reglages-automatiques.md](reglages-automatiques.md),
  et chaque valeur est montrée avec sa source pour qu'on puisse la corriger.
- **Un titre entré sans aucune ligne est invisible** — un transfert de titres depuis un autre
  établissement, par exemple. Aucune seconde source ne confirme plus les quantités : la
  comparaison se fait à l'écran de l'application Trade Republic ([D-81](decisions.md)).
- **Aucune liste des types n'est publiée.** Un type jamais vu est affiché, jamais traité : dans
  les premiers mois, des lignes non traitées sont le cas normal, et leurs titres manquent aux
  chiffres tant qu'elles le restent. Les titres reçus sans achat (actions gratuites, action
  offerte) en font partie ([Q-54](questions-ouvertes.md)).
- **Le brut de certains dividendes est sous-estimé** ([D-84](decisions.md)) : pour les actions
  néerlandaises au moins, la banque donne un montant déjà diminué de la retenue étrangère, sans
  la montrer. Le net est juste ; le gain et les taxes payées sont un peu bas.
- **Un export partiel donne une histoire partielle.** Rien dans le fichier ne le dit : seule la
  période couverte, affichée, permet de le voir.
- **Les règles les plus délicates du moteur ne sont validées que par des cas fictifs.** Le
  portefeuille du propriétaire est jeune : peu de ventes, peu de dividendes, aucune distribution
  de capital. La vente partielle au prorata et les plus-values réalisées sont donc prouvées par
  le [cahier de l'étape 3](verification/etape-3.md), **pas par de vraies données**. Il en va de
  même du TRI et du TWRR ([cahier de l'étape 5](verification/etape-5.md)) : sur quelques mois,
  ils sont exacts et peu significatifs.
- **La valeur affichée n'est pas celle de Trade Republic**, par construction
  ([D-48](decisions.md)) : cours du marché principal, à la clôture, contre un prix courant de la
  banque. Le demi-pour-cent mesuré par cours se retrouve sur le total et sur le gain.
- **Le spread, le TER et l'impôt sont des estimations**, et trois d'entre elles ne pourront
  jamais être confirmées depuis cette machine : le spread n'existe dans aucune donnée (il est
  fondu dans le prix d'exécution), le TER est un taux annoncé, et l'impôt dépend de la situation
  fiscale entière du foyer. Les hypothèses sont affichées à côté de chaque chiffre, et les taux
  vivent dans des fichiers qu'on corrige sans toucher au code ([D-58](decisions.md)).
- **Le gain du PEA est approché depuis les titres** ([D-59](decisions.md)), l'application ne
  suivant pas les espèces. L'égalité avec « valeur liquidative − versements » est démontrée, mais
  elle tombe si un retrait a eu lieu, ou si le plan a été **transféré** d'un autre établissement.
- **La liste des ETF de Xetra est en retard sur environ 5 % des lignes** et ignore les ETF
  français de type « PEA ». C'est pourquoi le TER est proposé et non appliqué
  ([D-61](decisions.md)).
- **Le TWRR est calculé aux cours de clôture**, la valeur après un flux étant prise « parts après
  × clôture du jour » et non « valeur avant + montant du flux » ([D-54](decisions.md)). L'écart
  entre prix d'exécution et clôture n'est donc attribué à aucune sous-période. C'est un choix, et
  il est écrit ; un autre calculateur peut donner un TWRR légèrement différent sur les jours de
  flux.
