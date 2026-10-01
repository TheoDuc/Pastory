# Notes d'architecture

Points d'architecture relevés au fil des sessions. L'**étape 1** en a repris une partie et l'a
figée : le format pivot (§2) et les choix d'outillage (D-31 à D-38). Le reste attend l'étape qui
le concerne.

Ce fichier est un **carnet** : il garde les points au fur et à mesure qu'ils apparaissent.
La description d'ensemble de ce qui est construit est dans [architecture.md](architecture.md).

- Un point qui renvoie à une décision (`D-xx`) est **acquis**.
- Un point marqué *(à étudier)* est une piste ou une contrainte à traiter.
- Les outils retenus sont dans [decisions.md](decisions.md) : Dash (D-31), uv (D-32), Python
  simple et `Decimal` (D-33), noms métier en français (D-34), TOML et `pytest` (D-38).

Ajouter un point dès qu'une discussion en fait apparaître un.

---

## 1. Chaîne de traitement en « wagons »

```
 Source bancaire        Adaptateur            Format pivot         Moteur              Vues
 (export pytr)   ──►   Trade Republic   ──►   (opérations    ──►   (positions,   ──►   synthèse, frais,
                       (1 par banque)          sur actifs)          gains, coûts)       valeur réelle…
                                                                        ▲
                                    Données externes (cours, TER, compositions, fiscalité)
```

- Le **moteur ne lit que le format pivot**. Trade Republic n'est qu'un adaptateur. Un fork pour une
  autre banque n'écrit qu'un adaptateur ([D-26](decisions.md)).
- Chaque couche est testable seule : un adaptateur avec des exports fictifs, le moteur avec des
  opérations pivot fictives.
- Monte-Carlo est un module indépendant, branché sur les résultats du moteur, dont rien ne dépend
  ([D-27](decisions.md)).

## 2. Format pivot — **figé à l'étape 1**

L'ébauche de cette section a été reprise, complétée et validée : le format fait désormais foi dans
[format-pivot.md](format-pivot.md) ([D-35](decisions.md)). Ce qui s'y est ajouté depuis :

- tous les nombres sont **positifs**, le sens est porté par le `type` ;
- `montant_regle` (le montant réellement débité ou crédité) entre dans le format, pour que les
  contrôles de cohérence soient vérifiables ligne à ligne ;
- `instant_utc` **et** `date` en heure de Paris ([D-36](decisions.md)) ;
- `nature_source`, informative, qui garde la nature d'origine sans que le moteur calcule dessus ;
- une cinquième provenance, `a_completer`, pour un prix qui attend les cours de l'étape 4.

## 3. Adaptateur Trade Republic — **écrit à l'étape 2**

Réalisé dans `pastory/adaptateurs/trade_republic/`, en couches testables séparément.
Ce que l'écriture a confirmé, et ce qu'elle a changé :

- **Classement explicite de chaque `eventType`** en quatre catégories : traité, hors périmètre
  (espèces), écarté (information), **inconnu**. Aucun classement par défaut
  ([D-08](decisions.md), [D-11](decisions.md)). ✅ `classement.py`
- Contrôle du statut — mais **assoupli** : un plan échoué porte un montant, *et* les deux
  événements de titres reçus n'ont **aucun champ `status`**. La règle est donc « un statut
  présent doit valoir `EXECUTED` », pas « le statut doit être présent et valoir `EXECUTED` »
  (inventaire §11.10).
- **Rapport de lecture** produit à chaque chargement ([`rapport.py`](../pastory/adaptateurs/trade_republic/rapport.py)) :
  comptages par catégorie, types inconnus, libellés non reconnus, désaccords. L'interface
  l'affichera (étape 9). Tout texte venu de l'écran y passe par un **garde-fou** : le titre
  d'une section contient parfois un montant réel.
- **Lecteur de textes isolé** ([D-09](decisions.md), [D-19](decisions.md)), en deux modules :
  - `nombres.py` : les écritures localisées. **Un même export en mélange deux** — virgule
    décimale pour les montants et les quantités d'ordres, **point décimal** pour les quantités
    de dividendes. La convention n'est jamais devinée, elle est déclarée par libellé, et une
    écriture qui ne la respecte pas est refusée (inventaire §11.1) ;
  - `lexique.py` : le dictionnaire, indexé par **(section, libellé)** et non par libellé seul,
    parce que `Aktien` désigne des parts à un endroit et des euros à un autre. Il se vérifie
    lui-même au chargement : deux libellés de même notion doivent annoncer la même écriture.
- Poche : ordre de résolution figé par [D-40](decisions.md) — déclaration de l'utilisateur, puis
  code `XF` ([D-16](decisions.md)), puis rôle du compte ([D-10](decisions.md)). Si rien ne
  répond, **l'opération n'est pas produite** et l'export s'arrête. Le libellé « Portfolio » n'est
  qu'un contrôle.
- Les numéros de compte ne sortent jamais de l'adaptateur : ils n'entrent pas dans le pivot, et
  la configuration qui les porte vit dans le dossier personnel.
- **Recoupement avec le CSV** à chaque lecture ([D-42](decisions.md)) : second avis indépendant
  sur la quantité, les frais et les taxes — les trois valeurs qui n'existent qu'en texte.

**Contrôles internes, gratuits, qui ne dépendent d'aucun fichier extérieur :** la quantité est
écrite à deux endroits de l'écran et doit concorder ; le total affiché doit valoir le montant
structuré ; le mot « Kauf » / « Verkaufen » doit s'accorder avec le signe du montant. Chacun
alimente le rapport sans jamais bloquer une opération par ailleurs cohérente.

## 3 bis. Adaptateur de l'export officiel — **à écrire à l'étape 8 ter** ([D-79](decisions.md))

Relevé du fichier : [export-officiel.md](export-officiel.md). Ce que la discussion du 2026-10-01 a
fait apparaître :

- **Un second adaptateur, pas une modification du premier.** C'est le premier vrai usage de
  [D-26](decisions.md) : si le moteur doit changer pour l'accueillir, la frontière était mal
  placée, et c'est à noter comme défaut d'architecture. L'adaptateur pytr reste le temps de
  comparer les deux pivots sur la même période *(à étudier : où vit la comparaison — un test, une
  commande, un script du cahier ?)*.
- **Le classement explicite reste la règle**, sur la paire `(category, type)` : traité, espèces
  hors périmètre, **inconnu**. Aucune liste n'étant publiée, l'inconnu est le cas normal des
  premiers mois, pas une anomalie.
- **Plus de lecteur de textes**, sauf pour `nature_source` (`description`, en anglais), qui est
  informatif. `nombres.py` et `lexique.py` restent propres à l'adaptateur pytr.
- **La poche est une donnée** : `account_type` et `asset_class`. `comptes.toml` et l'assistant
  « nommer ses comptes » deviennent propres à l'ancien adaptateur.
- **Plusieurs fichiers, une histoire** *(à étudier)* : un utilisateur exportera plusieurs fois,
  sur des périodes qui se recouvrent. Union dédoublonnée par `transaction_id` ; mais que faire si
  une même ligne revient **modifiée** (une correction de dividende arrive en seconde ligne
  d'après le forum de Portfolio Performance) ? Ne pas trancher sans un cas réel.
- **La période couverte doit s'afficher.** Rien dans le fichier ne dit qu'il commence à
  l'ouverture du compte ; un export partiel fait un capital investi faux sans aucune alerte. Le
  contrôle de [D-45](decisions.md) (une vente de parts jamais achetées) en attrape une partie.
- **Le dossier personnel** ([D-37](decisions.md)) : le fichier est importé, c'est-à-dire copié
  hors de OneDrive, et l'application ne lit que sa copie.
- **Données personnelles** : le fichier contient IBAN, contreparties et commerçants. Le rapport de
  lecture n'en montre que des comptages par type, et aucun cache ne les recopie.
- **Un contrôle nouveau devient possible** *(à étudier, à soumettre au propriétaire)* : les lignes
  d'espèces de la poche `PEA` permettraient de reconstituer le solde d'espèces du plan, comme
  [D-43](decisions.md) l'a fait une fois à la main. Un solde qui ne retombe pas juste signale une
  opération manquante. C'est lire des montants d'espèces, que [D-11](decisions.md) exclut de
  l'**affichage** — pas forcément du **contrôle**.

## 4. Traçabilité : chaque chiffre dit d'où il vient

Condition pour qu'un non-développeur puisse vérifier.

- Chaque valeur porte sa **provenance** : `donnee` (champ structuré), `texte` (lu dans un libellé,
  fragile), `deduction` (règle), `estimation` (spread, TER, impôt).
- L'interface montre visuellement déductions et estimations, et permet de remonter d'un chiffre aux
  opérations qui le composent.
- Chaque formule du code renvoie à sa définition du [glossaire](glossaire.md).

## 5. Moteur — **écrit à l'étape 3** (la partie qui ne dépend pas des cours)

Réalisé dans `pastory/moteur/`, en couches testables séparément, comme l'adaptateur. Ce que
l'écriture a confirmé, et ce qu'elle a ajouté :

- Calcule par actif puis agrège par poche et au total. Les filtres (période, poches) s'appliquent
  à l'agrégation, pas à la lecture. ✅ `position.py`, `portefeuille.py`
- La clé d'une position est le couple **(actif, poche)**, jamais l'actif seul : un même ETF peut
  être détenu en PEA *et* en CTO, avec deux prix de revient et deux fiscalités
  ([D-44](decisions.md)).
- **Le moteur tient un journal** ([D-44](decisions.md)) : une ligne par opération, avec l'état
  d'avant et l'état d'après. C'est ce qui rend un chiffre refaisable à la main sans lire le code,
  et c'est la pièce centrale du [cahier de l'étape 3](verification/etape-3.md). Exporté en CSV à
  côté des positions. ✅ `export_csv.py`
- **L'ordre est imposé, jamais supposé** : horodatage exact, puis identifiant pour départager
  deux opérations simultanées. L'ordre du fichier d'export ne fait pas foi.
- Le capital net investi est **arrondi au centime après chaque opération**, et une vente retire
  `capital × vendues / détenues` plutôt que de multiplier le capital par un complément : les deux
  morceaux retombent exactement sur le capital d'avant.
- Deux comptabilités **séparées** dès le moteur ([D-21](decisions.md)) :
  - **performance** sur montants bruts : capital net investi, PRU, gain, TRI, TWRR ;
  - **coûts** : frais et taxes réels, rangés par moment (achat, vente, revenus), les trois
    niveaux de Q-21 ; puis, **écrits à l'étape 6**, le spread estimé à l'achat et à la vente et
    le TER pendant la détention ([D-30](decisions.md), [D-56](decisions.md)).
- **Valeur réelle** = valeur brute − frais de vente − spread − impôt estimés
  ([D-23](decisions.md)). ✅ `valeur_reelle.py`
- Titres reçus sans achat : prix = cours du jour d'apparition, marqué `deduction`
  ([D-15](decisions.md)). Tant qu'il manque, **les parts comptent et le montant non** — et le
  prix de revient de l'actif est affiché « à compléter » plutôt que dilué
  ([D-45](decisions.md)).
- **Trois refus explicites** ([D-45](decisions.md)), chacun accompagné d'un signalement : prix
  inconnu, vente au-delà du stock compté (la quantité ne devient jamais négative), distribution
  de capital au-delà du capital investi (plancher à zéro). Le fil commun : **ne jamais afficher
  un chiffre qui n'a pas de sens, et ne jamais le corriger sans le dire**.
- **Rapprochement avec les positions réelles** ([D-46](decisions.md)) : la quantité est un
  contrôle, le prix de revient de la banque une simple information. C'est le seul contrôle qui ne
  dépend d'aucune lecture de texte, et le seul capable de révéler les titres entrés sans
  événement. La photo du portefeuille entre dans le pivot comme **second contrat**
  ([format-pivot §9](format-pivot.md)), pour que le moteur n'ouvre aucun fichier de banque.
  ✅ `rapprochement.py`, `pivot/position_reelle.py`
- **La photo de la banque ne couvre pas forcément tout** ([D-47](decisions.md)), constaté au
  premier essai sur de vraies données : `pytr` ne demande les positions que d'un seul
  compte-titres, et le PEA est dans un autre. Une poche entièrement absente est signalée **une
  fois** au lieu de lever une alerte par actif. Le rapprochement distingue donc « tout ce qui a
  pu être comparé concorde » de « tout a pu être comparé ». Suite dans
  [Q-26](questions-ouvertes.md).
- **Valorisation et rendements — écrits à l'étape 5.** ✅ `valorisation.py`, `rendements.py`.
  Le moteur **déclare** ce qu'il attend d'une source de cours (un protocole d'une méthode,
  `cours(actif, date)`) et c'est `cli.py` qui lui passe le fournisseur de l'étape 4 : aucun
  import entre `moteur/` et `donnees_externes/`, dans aucun sens, et un test prouve que les deux
  s'emboîtent. Le gain, le TRI et le TWRR se calculent par groupe de positions (un actif, une
  poche, le tout) sur une période `[début, fin]` ([D-54](decisions.md)). Ce qui n'a pas de cours
  sort des totaux, marqués partiels ([D-53](decisions.md)) ; la valeur « aujourd'hui » est celle
  de la dernière clôture ([D-52](decisions.md)). Chaque taux a sa pièce de vérification :
  `flux.csv` pour le TRI (la table de `TRI.PAIEMENTS`), `sous_periodes_twrr.csv` pour le TWRR.
- TRI et TWRR sur courte durée : l'indicateur « peu significatif » existe (`Rendements.
  peu_significatif`, sous 365 jours) et le rapport l'affiche ; l'interface le reprendra. ✅

## 6. Données externes

- Sources **gratuites et fiables**, choisies par comparatif écrit ([D-18](decisions.md),
  [D-28](decisions.md)).
- **Chaque source derrière une interface interchangeable**, comme les banques : changer de
  fournisseur de cours ne touche pas le moteur. *(à étudier)*
- **Correspondance ISIN → identifiant de la source** (ticker, place de cotation), stockée dans la
  configuration locale, vérifiable et corrigeable par l'utilisateur.
- **La devise se vérifie à chaque cours, et n'est jamais supposée.** Le comparatif de l'étape 4
  ([sources-de-cours.md §4](sources-de-cours.md)) a trouvé un ISIN pour lequel la recherche
  automatique renvoie une cotation **en dollars** : un cours dont la devise n'est pas attendue doit
  être **refusé et signalé**, jamais utilisé ([D-45](decisions.md)). C'est le garde-fou principal
  de cette couche. *(à étudier : où il vit exactement)*
- **Un cours brut, jamais retraité des dividendes** : le moteur les compte déjà
  ([D-29](decisions.md)). Une série « ajustée » les compterait deux fois, de façon invisible sur un
  ETF capitalisant.
- **Cache local** des cours, TER et compositions, avec la date de récupération. L'application doit
  s'ouvrir sans réseau, sur les dernières données connues, et afficher leur date.
- **Paramètres datés et sourcés**, dans des fichiers lisibles, mis à jour sans toucher au code :
  taux fiscaux par poche, spreads par défaut, frais par ordre. **Réglé à l'étape 6** : deux TOML
  versionnés dans `pastory/parametres/`, et un paramètre sans `en_vigueur_depuis` ni `source`
  est **refusé à la lecture** ([D-58](decisions.md)). Le rapport cite, sous chaque impôt estimé,
  le taux employé et son origine.
- **Les frais courants des ETF (TER)** viennent de la liste publique des ETF négociables de Xetra,
  indexée par ISIN. Elle est **proposée puis validée** par l'utilisateur, comme la correspondance
  ISIN → ticker, et pour la même raison : elle est en retard sur environ 5 % des lignes et ignore
  les ETF français « PEA » ([D-61](decisions.md), [couts-et-fiscalite.md](couts-et-fiscalite.md)).

## 7. Configuration et données locales

- Fichiers **propres à l'utilisateur**, tous exclus de git : exports, cache, noms des comptes,
  corrections de poche, correspondances ISIN, résultats `*.local.md`.
- La configuration de l'utilisateur est séparée de la configuration par défaut livrée avec
  l'application (exemples fictifs versionnés). **Réglé à l'étape 1 :** la configuration est en
  **TOML** ([D-38](decisions.md)), ce qui évite l'exclusion globale des `*.json` du `.gitignore`
  ([D-01](decisions.md)).
- **Identifiants** : trois modes au choix, jamais de PIN en clair dans le projet, un `.env` ou
  OneDrive ([D-25](decisions.md)).
- Le projet vit dans OneDrive ([D-24](decisions.md)). **Réglé à l'étape 1 :** tous les fichiers
  personnels (exports, cache, configuration, `*.local.md`) sont écrits dans un dossier local non
  synchronisé, dont l'application affiche l'emplacement ([D-37](decisions.md)).

## 8. Vues

- Séparation voulue par le propriétaire :
  - **synthèse** : cœur brut, trois chiffres clés gain / TRI / TWRR ([D-22](decisions.md)) ;
  - **frais et taxes**, en trois niveaux entrée / détention / sortie (Q-21) ;
  - **valeur réelle** ([D-23](decisions.md)) ;
  - **diversification** ;
  - **Monte-Carlo**, plus tard.
- La maquette du PDF n'est pas un modèle ([D-20](decisions.md)).
- Les vues n'appellent que le moteur, jamais l'adaptateur ni les sources externes directement.
- Affichage permanent possible des alertes de lecture : types inconnus, libellés non reconnus,
  écarts avec les positions réelles.

## 9. Qualité et vérification

- Tests `pytest` sur **données fictives uniquement**, versionnés ([D-38](decisions.md)). Aucune
  donnée réelle dans les tests.
- Un **cahier de vérification** par étape de calcul, avec des cas refaisables à la main
  ([feuille-de-route.md](feuille-de-route.md)).
- Le script [inventaire_structure.py](../scripts/inventaire_structure.py) peut servir à
  diagnostiquer un nouvel export (types jamais vus) sans exposer de valeurs.
