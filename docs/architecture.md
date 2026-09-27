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

> État à la dernière mise à jour (fin de l'étape 5) : les couches **adaptateur**, **pivot**,
> **moteur** (rejeu, valorisation et rendements compris) et **données externes** sont écrites.
> La couche **vues** existe comme dossier vide, avec sa place déjà définie. Le §10 dit ce qui
> s'y branchera.

---

## 1. En une image

```
  ┌─ hors de l'application ─┐
  │                         │
  │   Trade Republic        │
  │        │  pytr          │
  │        ▼                │
  │   all_events.json       │
  │   account_transactions  │
  │   portfolio.csv         │
  └────────┬────────────────┘
           │                     ce que l'utilisateur seul sait
           │                     (rôle des comptes)  ──────┐
           ▼                                              ▼
   ┌───────────────────────────────────────────────────────────┐
   │  ADAPTATEUR  trade_republic/                              │
   │  classer · lire les textes · résoudre la poche · recouper │
   └───────────────────────┬───────────────────────────────────┘
                           │  opérations + photo du portefeuille
                           ▼
   ┌───────────────────────────────────────────────────────────┐
   │  PIVOT  pivot/            ◄── le contrat, figé (D-35)     │
   │  Operation · PositionReelle · contrôles de cohérence      │
   └───────────────────────┬───────────────────────────────────┘
                           │                  ▲
                           │                  └── DONNÉES EXTERNES  donnees_externes/
                           │                      cours (D-51) · cache (D-50)
                           │                      complète les prix manquants (D-15)
                           │                      et rend du pivot ; sert aussi de
                           │                      source de cours au moteur, **par
                           │                      paramètre** (cli.py fait le lien)
                           ▼  et rien d'autre
   ┌───────────────────────────────────────────────────────────┐
   │  MOTEUR  moteur/                                          │
   │  rejeu par actif · journal · agrégation · rapprochement   │
   │  valorisation · gain, TRI, TWRR (D-22)                    │
   └───────────────────────┬───────────────────────────────────┘
                           │  positions, valeurs, rendements, signalements
                           ▼
   ┌───────────────────────────────────────────────────────────┐
   │  SORTIES   cli.py (aujourd'hui) · vues/ (étape 9)         │
   │  rapports en français · CSV pour le tableur               │
   └───────────────────────────────────────────────────────────┘
```

La forme en « wagons » vient de [D-26](decisions.md) : le moteur ne lit que le pivot, et changer
de banque ne demande d'écrire qu'un adaptateur.

---

## 2. Les six couches, et ce que chacune s'interdit

L'interdiction compte autant que le rôle : c'est elle qui garantit qu'un défaut reste local.

| Couche | Son travail | Ce qu'elle ne sait pas, volontairement |
|---|---|---|
| `config/` | Où sont les fichiers personnels ; ce que seul l'utilisateur peut dire (le rôle de chaque compte) | Ce qu'on fera de ces réponses |
| `adaptateurs/` | Comprendre les fichiers d'**une** banque et les traduire en pivot | Ce qu'est un prix de revient, un gain, un rendement |
| `pivot/` | Décrire une opération et une position réelle, et vérifier qu'une ligne se tient | Qui l'a produite, qui va la lire |
| `donnees_externes/` | Aller chercher un cours, le garder, et **compléter un prix manquant** | Ce qu'est une position, un prix de revient, une plus-value |
| `moteur/` | Rejouer les opérations, tenir le journal, agréger, rapprocher, **valoriser** et calculer gain, TRI et TWRR | Le nom d'un champ Trade Republic, l'emplacement d'un fichier, **d'où viennent les cours** — il dit seulement la forme qu'il en attend |
| `vues/` (étape 9) | Montrer, expliquer, laisser filtrer | Tout calcul — elle n'appelle que le moteur |

Deux conséquences pratiques :

- **un chiffre faux se cherche dans une seule couche.** Mal lu dans un libellé allemand →
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
       donnees_externes/ ──┘           │
                       │               │
                       └──► tableur.py ◄┘

cli.py ──► tout ce qui précède
```

Ce qui en découle, et qui se vérifie en lisant les imports :

- **rien n'importe `adaptateurs/` sauf `cli.py`.** Le moteur ignore l'existence de Trade
  Republic ([D-26](decisions.md)) ;
- **`pivot/` n'importe ni l'adaptateur ni le moteur.** C'est un contrat : il ne dépend d'aucun
  de ses deux usagers, sinon il cesserait d'en être un ;
- **`moteur/` n'importe que `pivot/`, `tableur.py` et lui-même.** C'est la propriété la plus
  importante du projet, et la plus facile à casser par inadvertance : un seul import
  d'adaptateur dans `moteur/` annulerait l'ouverture aux autres banques ;
- **`moteur/` n'importe pas `donnees_externes/` non plus**, et c'est ce qui surprend le plus.
  Les cours y entrent de deux façons, et aucune n'est un import : les prix manquants
  **complètent des opérations pivot avant lui** (§5.7) ; et pour valoriser, le moteur
  **déclare ce qu'il attend** d'une source — un protocole d'une méthode, `cours(actif, date)`,
  dans `moteur/valorisation.py` — que le fournisseur de `donnees_externes/` satisfait sans le
  savoir. C'est `cli.py` qui passe l'un à l'autre, et un test (`tests/moteur/test_valorisation.py`)
  prouve que les deux s'emboîtent. Changer de source de cours ne toucherait donc toujours que
  `cli.py`.

Deux flèches surprennent à la lecture, et sont voulues :

| Flèche | Pourquoi |
|---|---|
| `config/comptes.py` → `pivot.operation.Poche` | L'utilisateur déclare des poches (`PEA`, `CTO`, `crypto`). Ce vocabulaire appartient au pivot ; le redéfinir ailleurs créerait deux listes à tenir à jour |
| `adaptateurs/…/lecture.py` → `pivot.validation.controler` | Les contrôles de cohérence du pivot ([format-pivot §5](format-pivot.md)) tournent **pendant la lecture**, pas dans le moteur. Une ligne douteuse est repérée là où on peut encore dire de quel événement elle vient |

`tableur.py` est le seul module partagé hors contrat : il n'écrit que de la mise en forme de
nombres, et il vit à la racine pour qu'aucun export n'invente ses propres conventions.

---

## 4. Carte des fichiers

```
dashboard_tr/
├── cli.py                     le seul point d'entrée, et le seul assembleur
├── tableur.py                 comment on écrit un nombre (CSV et phrases)
├── config/
│   ├── emplacements.py        où vivent les fichiers personnels (D-37)
│   ├── comptes.py             le rôle de chaque compte espèces, déclaré par l'utilisateur (D-10)
│   └── actifs.py              de l'ISIN au ticker, et la devise attendue (D-48, D-51)
├── adaptateurs/
│   └── trade_republic/
│       ├── source.py          où sont les fichiers, et comment les rafraîchir via pytr
│       ├── evenements.py      où est rangée chaque information dans un événement
│       ├── classement.py      quatre catégories, aucune par défaut (D-08)
│       ├── lexique.py         tous les libellés affichés, et rien qu'ici (D-09, D-19)
│       ├── nombres.py         les deux écritures de nombres, jamais devinées
│       ├── poche.py           PEA, CTO ou crypto : trois règles dans l'ordre (D-40)
│       ├── lecture.py         le cœur : un événement devient une opération pivot
│       ├── recoupement_csv.py second avis sur quantité, frais et taxes (D-42)
│       ├── portefeuille.py    la photo du portefeuille, en PositionReelle (D-46)
│       └── rapport.py         tout ce qui n'a pas été compris
├── pivot/
│   ├── operation.py           le contrat n° 1 : une opération sur un actif
│   ├── position_reelle.py     le contrat n° 2 : ce que la banque dit détenir
│   ├── validation.py          les contrôles de cohérence d'une ligne
│   └── export_csv.py          les opérations, pour le tableur
├── moteur/
│   ├── position.py            le rejeu, opération par opération, et le journal (D-44)
│   ├── portefeuille.py        toutes les positions : par poche, et au total
│   ├── rapprochement.py       nos quantités contre celles de la banque (D-46, D-47)
│   ├── valorisation.py        ce que valent les actifs à une date, et ce qu'il attend d'une
│   │                          source de cours (D-52, D-53)
│   ├── rendements.py          gain, TRI, TWRR par actif, poche et total (D-22, D-54)
│   ├── signalement.py         ce que le moteur n'a pas pu calculer normalement (D-45)
│   ├── rapport.py             le rapport de « dashboard positions »
│   └── export_csv.py          les six CSV : positions, journal, valorisation, flux,
│                              sous-périodes du TWRR, évolution
├── donnees_externes/
│   ├── cours.py               le contrat : un cours, un refus, une source interchangeable
│   ├── cache.py               un CSV par actif, définitif et oubliable (D-50)
│   ├── yahoo.py               la source retenue, et ses trois garde-fous (D-51)
│   └── completion.py          les prix manquants complétés, du pivot vers du pivot (D-15)
└── vues/                      vide — l'interface Dash (étapes 8 et 9)

scripts/
├── inventaire_structure.py       relevé structurel d'un export, sans aucune valeur (D-05)
└── diagnostic_comptes_titres.py  diagnostic pour Q-26, sans aucune valeur

tests/                         même arborescence que dashboard_tr/, données fictives (D-38)
```

---

## 5. Couche par couche

### 5.1 `config/` — les fichiers, et ce que seul l'utilisateur sait

**`emplacements.py` : rien de personnel n'est écrit dans le projet.** Le dossier du projet est
synchronisé par OneDrive ([D-24](decisions.md)) ; tout ce qui est réécrit souvent va donc
ailleurs ([D-37](decisions.md)), dans un dossier propre au système (`LOCALAPPDATA` sous Windows),
avec trois sous-dossiers : `exports/`, `cache/`, `configuration/`. La variable
`DASHBOARD_TR_DOSSIER` permet d'en choisir un autre — c'est ce dont se servent les tests, qui
n'écrivent donc jamais dans le vrai dossier de l'utilisateur.

**`comptes.py` : le seul endroit où l'application pose une question.** Le rôle d'un compte
espèces n'est écrit **nulle part** dans l'export, et c'est pourtant lui qui détermine la poche
d'un achat ([D-10](decisions.md)). L'application ne le devine pas : elle écrit un TOML commenté
([D-38](decisions.md)), montre les opérations vues sur chaque compte, et attend. Les numéros de
compte ne sortent jamais de cette couche et de l'adaptateur : ils n'entrent pas dans le pivot.

### 5.2 `adaptateurs/trade_republic/` — de l'export aux opérations

C'est la couche la plus fragile du projet, parce que c'est la seule qui lise du texte affiché.
Elle est donc découpée en modules qui font chacun une seule chose, testables séparément.

| Module | Ce qu'il fait | Pourquoi il est séparé |
|---|---|---|
| `source.py` | Trouve `all_events.json` et `account_transactions.csv`, les rafraîchit via `pytr` | C'est le seul module qui parle au réseau et à un sous-processus |
| `evenements.py` | Sait **où** est rangée chaque information dans un événement | Il ne décide de rien : il isole la forme de l'export de son sens |
| `classement.py` | Range chaque `eventType` en `TRAITE`, `HORS_PERIMETRE`, `ECARTE` ou `INCONNU` | Liste explicite, aucun classement par défaut ([D-08](decisions.md), règle 5 de CLAUDE.md) |
| `lexique.py` | Tous les libellés allemands et français, indexés par **(section, libellé)** | Le reste du code parle de notions (`Notion.QUANTITE`), jamais de mots. Un libellé inconnu part au rapport ([D-19](decisions.md)) |
| `nombres.py` | Lit un nombre selon la convention **déclarée** pour son libellé | Un même export mélange virgule et point décimaux ; deviner ferait lire `1.234567` comme 1 234 567 (inventaire §11.1) |
| `poche.py` | PEA, CTO ou crypto, par trois règles dans l'ordre | La poche décide de la fiscalité : elle n'est jamais inventée ([D-40](decisions.md)) |
| `lecture.py` | Assemble tout ça en `Operation` | C'est le seul module qui décide du **sens** d'un événement |
| `recoupement_csv.py` | Compare quantité, frais et taxes avec le CSV | Second avis indépendant sur les trois valeurs qui n'existent qu'en texte ([D-42](decisions.md)) |
| `portefeuille.py` | Traduit `portfolio.csv` en `PositionReelle` | La photo de la banque est un second contrat, pas une source de calcul ([D-46](decisions.md)) |
| `rapport.py` | Accumule tout ce qui n'a pas été compris | Un défaut de lecture doit ressortir à l'écran, pas disparaître |

**La chaîne d'une lecture**, dans l'ordre :

1. `source.charger_evenements()` ouvre le JSON — **c'est la source** ([D-06](decisions.md)) ;
2. `classement.classer()` range l'événement. `INCONNU` → il est compté et affiché, jamais deviné ;
3. `evenements.lignes()` indexe les couples (section, libellé) ; `lexique` les traduit en notions,
   `nombres` en `Decimal` ;
4. `lecture.Lecteur` décide du type d'opération. **Les champs structurés priment** : le sens d'un
   ordre vient du signe du montant, pas du mot « Kauf » — qui ne sert qu'à recouper
   ([D-09](decisions.md)) ;
5. `poche.resoudre()` répond PEA, CTO ou crypto ; si aucune règle ne répond, **l'opération n'est
   pas produite** et l'export s'arrête en disant quoi déclarer ;
6. `pivot.validation.controler()` vérifie la ligne (quantité × prix = brut, brut ± frais et taxes
   = réglé…). Rien n'est corrigé : l'écart part au rapport ;
7. `recoupement_csv.recouper()` confronte le résultat au CSV de la banque.

**L'adaptateur a une seule sortie : un `Rapport`.** Il porte les opérations *et* tout ce qui a
résisté — types inconnus, libellés non reconnus, anomalies, comptes à nommer, opérations non
produites. Les deux voyagent ensemble pour qu'on ne puisse pas lire les chiffres sans voir leurs
réserves.

Un garde-fou traverse toute la couche : **aucun texte venu de l'écran n'est recopié tel quel**
dans un message. Il passe par `rapport.sur()`, parce qu'un titre de section contient parfois un
montant réel.

### 5.3 `pivot/` — le contrat

Figé à l'étape 1 ([D-35](decisions.md)), décrit champ par champ dans
[format-pivot.md](format-pivot.md). Trois règles de forme portent tout le reste :

1. **tous les nombres sont positifs** ; le sens est porté par le `type` ;
2. **les montants sont des `Decimal`**, jamais des flottants ([D-33](decisions.md)) ;
3. **aucun numéro de compte n'entre dans le pivot.**

Cinq types seulement, et la liste est **fermée** : `achat`, `vente`, `dividende`,
`distribution_capital`, `titres_recus`. Un cas qui n'y entre pas est signalé comme inconnu,
jamais rangé de force dans un type voisin.

Chaque valeur porte sa **provenance** : `donnee` (champ structuré), `texte` (lu dans un libellé,
fragile), `deduction` (règle écrite), `estimation`, `a_completer` (attend un cours). C'est ce qui
permet à l'interface de montrer d'un coup d'œil ce qui est solide et ce qui ne l'est pas.

`position_reelle.py` est le **second contrat** : la photo du portefeuille telle que la banque
l'affiche. Il existe pour que le moteur puisse se faire contredire sans ouvrir un fichier de
banque.

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

`rapprochement.py` est **le contrôle le plus fort du projet** : il ne dépend d'aucune lecture de
texte ni d'aucune déduction. La quantité est un contrôle, le prix de revient de la banque une
simple information ([D-46](decisions.md)). Une poche que la photo ne couvre pas du tout est
signalée **une fois**, et ses actifs sortent en « hors périmètre » plutôt que de crier au loup
ligne par ligne ([D-47](decisions.md)).

`signalement.py` est le pendant, côté moteur, du rapport de lecture. Il existe séparément parce
que le moteur ne connaît pas l'adaptateur.

**Deux comptabilités séparées dès le moteur** ([D-21](decisions.md)) : la *performance* sur
montants bruts, et les *coûts* — frais et taxes réels, déjà rangés par moment (achat, vente,
revenus). Elles ne se mélangent dans aucun chiffre.

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

### 5.6 `cli.py` — le seul assembleur

C'est le seul module qui connaisse toutes les couches, et c'est son rôle : il branche
l'adaptateur sur le moteur. Aucune couche n'appelle l'autre d'elle-même.

| Commande | Ce qu'elle traverse | Écrit quelque chose ? |
|---|---|---|
| `emplacements` | `config` | crée les dossiers |
| `rafraichir` | `config` → `pytr` | l'export, dans le dossier personnel |
| `comptes` | adaptateur → `config` | le TOML des rôles de comptes |
| `lire` | adaptateur | **non** — un rapport à l'écran |
| `exporter-pivot` | adaptateur → `pivot` | les opérations en CSV |
| `positions` | adaptateur → `pivot` → `donnees_externes` → moteur | **non** — un rapport à l'écran |
| `exporter-positions` | adaptateur → `pivot` → `donnees_externes` → moteur | les six CSV du moteur |
| `positions-reelles` | `pytr` → adaptateur → moteur | **non** — le rapprochement à l'écran |
| `ouvrir` | *(étape 9)* | — |

Trois options traversent plusieurs commandes : `--export <dossier>` pour examiner un export
rangé ailleurs sans le copier dans le projet ; `--au AAAA-MM-JJ` pour arrêter les chiffres à une
date, qui est aussi la date de valorisation et la fin de la période des rendements (sans elle :
aujourd'hui, à la dernière clôture connue, [D-52](decisions.md)) ; `--depuis AAAA-MM-JJ` pour
faire commencer cette période ailleurs qu'à la première opération.

Pour `positions` et `exporter-positions`, **un seul** `FournisseurDeCours` sert à la fois à la
complétion des prix manquants et à la valorisation : ses refus couvrent les deux, et le bloc
« Cours de marché » du rapport les liste tous.

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

Ce qui reste vide : `vues/`, dont le §10 dit ce qui s'y branchera.

---

## 6. Le trajet d'un chiffre, de bout en bout

Un achat de 10 parts à 20,00 €, avec 1,00 € de frais et 0,60 € de taxe *(valeurs fictives,
celles de [format-pivot §6](format-pivot.md))* :

| Où | Ce qui se passe | Ce qu'on peut vérifier |
|---|---|---|
| Export | Un événement, dont la quantité et le prix ne sont lisibles que dans des libellés | — |
| `classement` | `TRAITE`, famille « ordre ponctuel » | Le type apparaît dans le rapport de lecture |
| `lexique` + `nombres` | « 20,00 € » → `Decimal("20.00")`, convention **déclarée**, pas devinée | Le rapport compte les valeurs lues en `texte` |
| `poche` | Compte du PEA → poche `PEA`, marquée `deduction` | Le libellé « Portfolio » doit être d'accord, sinon signalement |
| `pivot` | `quantite` 10, `prix_unitaire` 20,00, `montant_brut` 200,00, `frais` 1,00, `taxes` 0,60, `montant_regle` 201,60 | 10 × 20,00 = 200,00 · 200,00 + 1,60 = 201,60 |
| `recoupement_csv` | La colonne `Parts` du CSV doit dire 10 | Un écart part au rapport |
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
| **Vocabulaire métier en français** ([D-34](decisions.md)) | Noms de modules, de classes et de champs. Le propriétaire doit pouvoir lire un nom de fonction |
| **Aucune donnée réelle nulle part** ([D-01](decisions.md), [D-03](decisions.md)) | Dossier personnel hors projet, tests sur données fictives, valeurs fictives dans toute la doc, scripts de diagnostic qui n'affichent aucune valeur |
| **Affichable sur une console Windows** | La console écrit en cp1252 : ni trait de tableau, ni coche, ni flèche dans un rapport. Le CLI force UTF-8, et deux tests vérifient que les rapports restent imprimables. **En ajouter un pour tout nouveau rapport** |

---

## 8. Où vivent les données

| Quoi | Où | Dans git ? |
|---|---|---|
| Le code, la documentation, les tests | Dossier du projet (OneDrive) | oui |
| Exports `pytr` (`all_events.json`, CSV) | Dossier personnel → `exports/` | **non** |
| Cours, TER, compositions en cache *(étape 4)* | Dossier personnel → `cache/` | **non** |
| Rôles des comptes, corrections de poche, ISIN | Dossier personnel → `configuration/` | **non** |
| Les CSV de vérification (opérations, positions, journal) | Dossier personnel | **non** |
| Résultats de vérification sur vraies données | `docs/verification/etape-N.local.md` | **non** (exclu) |
| Identifiants Trade Republic | **nulle part** : `pytr` les redemande à chaque appel ([D-41](decisions.md)) | **non** |

Le dossier personnel est **hors du dossier synchronisé**, pour éviter les conflits OneDrive sur
des fichiers réécrits à chaque commande. `uv run dashboard emplacements` dit où il est.

---

## 9. Les tests suivent les couches

`tests/` reproduit l'arborescence de `dashboard_tr/`, et chaque couche se teste sans la
précédente :

| Test | Part de | Ce que ça prouve |
|---|---|---|
| `tests/adaptateurs/` | Événements fictifs (`evenements_fictifs.py`) | La lecture comprend l'export, et signale ce qu'elle ne comprend pas |
| `tests/pivot/` | Opérations écrites à la main (`exemples.py`) | Les contrôles de cohérence attrapent ce qu'ils doivent |
| `tests/moteur/` | Opérations pivot fictives (`operations_fictives.py`) | Les calculs sont justes — **sans aucune banque** |
| `tests/donnees_externes/` | Réponses écrites à la main, source factice (`cours_fictifs.py`) | Les pièges de la source sont attrapés — **sans aucun réseau** |
| `tests/test_cli.py` | Un dossier d'export temporaire | Les commandes s'enchaînent, et les rapports s'affichent en cp1252 |

**Aucune donnée réelle dans les tests** ([D-38](decisions.md)). La vérification sur vraies
données est un exercice séparé, fait par le propriétaire, guidé par un
[cahier de vérification](verification/) par étape.

---

## 10. Ce qui n'existe pas encore, et où ça se branchera

| À venir | Où | Ce qui ne changera pas |
|---|---|---|
| Spread, TER, valeur réelle *(étape 6)* | `moteur/`, côté **coûts** | La séparation performance / coûts est déjà en place ([D-21](decisions.md)) ; la valeur brute de `valorisation.py` est le point de départ de la valeur réelle ([D-23](decisions.md)) |
| Diversification *(étape 7)* | `donnees_externes/` + `moteur/` | — |
| Interface Dash *(étapes 8 et 9)* | `vues/` | Les vues n'appellent que le moteur — jamais l'adaptateur ni une source externe |
| Monte-Carlo *(étape 12)* | Module indépendant, branché sur les résultats du moteur | Rien ne dépendra de lui ([D-27](decisions.md)) |

Les deux branchements des cours sont **faits** : les **titres reçus sans prix**
([D-15](decisions.md)) reçoivent le cours de leur jour d'apparition (étape 4), et le moteur
**valorise** et calcule les rendements en recevant la source de cours en paramètre (étape 5).

Ce que l'étape 6 trouvera en place : la valeur brute de chaque position à une date, ses
plus-values latentes et réalisées, ses coûts payés rangés par moment — tout ce qu'il faut pour
poser à côté les coûts **estimés** (spread, TER) et la **valeur réelle** ([D-23](decisions.md)),
sans toucher à la performance brute.

---

## 11. Comment étendre

**Ajouter une banque** — c'est le cas prévu par [D-26](decisions.md) :

1. un dossier `adaptateurs/<banque>/`, qui produit des `Operation` et des `PositionReelle` ;
2. ses propres tests, sur des exports fictifs ;
3. une branche dans `cli.py` pour le choisir.

Rien d'autre. Si l'ajout demande de toucher `moteur/`, c'est le signe que le pivot manque d'un
champ : voir [format-pivot §8](format-pivot.md), qui dit comment le format évolue.

**Ajouter ou remplacer une source de cours** : un module dans `donnees_externes/` qui suit le
protocole `SourceDeCours` (une méthode, `serie`), et une ligne dans `cli._fournisseur_de_cours` —
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

- **Le rapprochement ne couvre pas le PEA** ([D-47](decisions.md)). `pytr` ne demande les
  positions que d'un seul compte-titres, et Trade Republic loge le PEA dans un second.
  Conséquence : sur le PEA, **aucune seconde source ne confirme les quantités**. Les chiffres
  restent justes, ils sont seulement calculés sans second avis.
  [Q-26](questions-ouvertes.md) reste ouverte, et le
  [diagnostic](../scripts/diagnostic_comptes_titres.py) écrit pour la trancher n'a pas encore
  été lancé.
- **Un titre entré sans aucun événement est invisible** à l'adaptateur — un PEA transféré depuis
  un autre établissement, par exemple. Seul le rapprochement peut le révéler, d'où le point
  précédent.
- **La lecture de textes reste le point faible**, par construction : quantité, frais et taxes
  n'existent que dans des libellés en allemand ou en français. Trois choses la protègent — le
  lexique isolé, les conventions de nombres déclarées, le recoupement CSV — mais un changement
  d'affichage chez Trade Republic se verra ici d'abord. Il se verra : un libellé inconnu n'est
  jamais ignoré.
- **`pytr` utilisé comme bibliothèque réserve des pièges** (jeton WAF, journal de débogage qui
  imprime le compte complet). Les contourner est documenté dans
  [prompt-session-suivante.md](prompt-session-suivante.md).
- **Les règles les plus délicates du moteur ne sont validées que par des cas fictifs.** Le
  portefeuille du propriétaire est jeune : peu de ventes, peu de dividendes, aucune distribution
  de capital. La vente partielle au prorata et les plus-values réalisées sont donc prouvées par
  le [cahier de l'étape 3](verification/etape-3.md), **pas par de vraies données**. Il en va de
  même du TRI et du TWRR ([cahier de l'étape 5](verification/etape-5.md)) : sur quelques mois,
  ils sont exacts et peu significatifs.
- **La valeur affichée n'est pas celle de Trade Republic**, par construction
  ([D-48](decisions.md)) : cours du marché principal, à la clôture, contre un prix courant de la
  banque. Le demi-pour-cent mesuré par cours se retrouve sur le total et sur le gain.
- **Le TWRR est calculé aux cours de clôture**, la valeur après un flux étant prise « parts après
  × clôture du jour » et non « valeur avant + montant du flux » ([D-54](decisions.md)). L'écart
  entre prix d'exécution et clôture n'est donc attribué à aucune sous-période. C'est un choix, et
  il est écrit ; un autre calculateur peut donner un TWRR légèrement différent sur les jours de
  flux.
