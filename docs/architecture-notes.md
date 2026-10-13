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

## 3. Adaptateur pytr — **écrit à l'étape 2, retiré à l'étape 8 ter** ([D-81](decisions.md))

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

## 3 bis. Adaptateur de l'export officiel — **écrit à l'étape 8 ter** ([D-79](decisions.md))

Relevé du fichier : [export-officiel.md](export-officiel.md). Les points notés le 2026-10-01, et
ce que l'étape en a fait :

- **Un second adaptateur, pas une modification du premier** — tenu. Le moteur n'a pas changé
  d'une ligne de calcul : seul le format pivot a rendu facultatif `montant_regle`, que le moteur
  ne lisait pas ([D-83](decisions.md)). La comparaison des deux adaptateurs a vécu dans un
  **script** du cahier, retiré avec pytr ; il est dans l'historique git, et ses résultats dans le
  [cahier de l'étape](verification/etape-8-ter.md).
- **Le classement explicite** — `classement.py`, sur la paire `(category, type)`. Une troisième
  règle s'y est ajoutée : **une forme jamais vue d'un type connu n'est pas traitée** (`lecture.py`).
  Un dividende à montant négatif (une extourne, chez d'autres utilisateurs), une obligation, un
  compte `JUNIOR` sont des trous affichés, pas des chiffres devinés.
- **Plus de lecteur de textes** — `nombres.py` et `lexique.py` sont partis avec pytr. Seule la
  nature (plan d'épargne, ordre ponctuel) est lue dans la `description`, marquée `texte`.
- **La poche est une donnée** — `comptes.toml` et l'assistant ont disparu, corrections de poche
  comprises.
- **Un fichier, un portefeuille** ([D-109](decisions.md), étape 10 bis) — *ce point a été
  renversé* : les fichiers du dossier ne se cumulent plus, `depot.py` n'en lit qu'un, celui
  qui est ouvert. Le cumul mélangeait deux comptes dès qu'un proche déposait son export. Ce
  qui en reste vaut **à l'intérieur d'un fichier**. *Texte de l'étape 8 ter :* `depot.py` lit
  tous les CSV du dossier, dédoublonne par
  `transaction_id`, et quand une même ligne revient **modifiée**, garde la première et l'affiche
  (aucun cas réel encore). La correction de dividende, elle, n'arrive pas modifiée mais en
  **extourne** suivie d'une nouvelle ligne : c'est le refus des formes jamais vues qui la couvre.
- **La période couverte s'affiche** — par fichier et au total, avec les **trous** entre deux
  fichiers.
- **Le dossier personnel** — l'utilisateur dépose ses exports dans `Pastory/exports`, hors
  OneDrive ([D-37](decisions.md)) : rien n'est copié. `--export` lit un dossier sur place.
- **Données personnelles** — une ligne d'espèces perd son nom, sa description et ses montants **dès
  la lecture du fichier** (`fichier.py`) : aucune couche ne les voit passer. Les colonnes de
  contrepartie ne sont même pas des attributs.
- **Le contrôle par le solde d'espèces du PEA** — *toujours à soumettre au propriétaire* : c'est la
  piste du PEA de l'[étape 8 quater](feuille-de-route.md).

**Deux points nouveaux, pour l'étape 8 quater :**

- **La crypto a changé d'identifiant.** pytr la nommait `XF…`, l'export la nomme par son code de
  marché (fictif : `BTC`). Une déclaration de ticker et des cours en cache rangés sous l'ancien
  code sont **orphelins** : l'actif paraît non déclaré. L'étape 8 quater, qui propose le ticker
  depuis `symbol`, doit aussi dire qu'une déclaration ne correspond plus à aucun actif.
- **Les tests de la ligne de commande ajoutent deux titres reçus à la lecture**
  (`tests/adaptateurs/trade_republic/export_ligne_de_commande.py`). L'export officiel n'en produit
  pas encore ([Q-54](questions-ouvertes.md)), mais la complétion de leur prix
  ([D-15](decisions.md)) reste un trajet de l'application, qu'il fallait garder vérifié de bout en
  bout. Le jour où un type de titres reçus est traité, cet ajout doit disparaître au profit d'une
  vraie ligne de l'export fictif.

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

## 7 bis. Réglages trouvés seuls — **écrits à l'étape 8 quater** ([D-80](decisions.md))

- **Une configuration effective, et non un second chemin.** Les cours, les coûts et les
  compositions lisent toujours une `Configuration` de `Declaration` ; `reglages/` la fabrique en
  fusionnant ce qui est trouvé et ce qui est corrigé. Rien en aval n'a eu à savoir qu'une valeur
  avait été trouvée, sauf pour **l'afficher** : le TER porte sa source jusqu'au rapport par son
  `Parametre`, le contenu par deux champs de `Declaration` (`source_du_contenu`,
  `date_du_contenu`), la date du PEA par `ReglesFiscales`.
- **Un contenu « actions » trouvé ne s'applique pas.** Un contenu déclaré passe **avant** la
  composition du fonds (`FournisseurDeCompositions._declaree`) : appliqué à un fonds d'actions, il
  lui ferait perdre ses pays et ses secteurs. Il est montré, avec cette réserve. Corrigé à la main,
  il s'applique comme avant (D-71).
- **Une cotation trouvée ne change jamais d'elle-même**, et quand elle change quand même
  (correction, `oublier-reglages`), les cours ne se mêlent pas : le cache des cours est par actif
  et garde le ticker de chaque cours ; `FournisseurDeCours` n'emploie jamais un cours pris sur une
  autre cotation que la cotation retenue, et, en ligne, oublie ces cours pour reprendre la série
  (trouvé par la relecture de l'étape).
- **Une panne n'est jamais gardée.** Une recherche interrompue par le réseau, ou un TER introuvable
  parce qu'une source n'a pas répondu, n'entre pas dans `cache/reglages.csv` : le lancement suivant
  refait la recherche. Le défaut a été vu sur les données du propriétaire, avec la liste de Xetra.
- **La date d'une source n'a pas toujours le même sens** : l'état d'une liste (« au »), ou la date
  d'effet d'un taux (« taux en vigueur depuis le »). `Origine.intitule_de_la_date` le dit, pour
  qu'un taux de 2023 encore en vigueur ne se lise pas comme périmé.
- **L'histoire du PEA se lit dans l'ordre des horodatages**, pas des jours : une clôture et une
  réouverture tombent le même jour. Et la sortie qui clôt un plan n'est pas un retrait du suivant.
- **Les tests coupent cinq sources** de plus par des fixtures automatiques de `tests/test_cli.py`
  (`_source_des_cotations`, `_frais_courants_de_l_emetteur`, `_classes_d_actifs`, `_registre_cfi`,
  en plus de la liste de Xetra et des compositions) : aucun test ne sort de la machine.

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

## 8 bis. Lancement, installation, démonstration — **écrits à l'étape 10** ([D-106](decisions.md), [D-107](decisions.md))

- **Le serveur ne voit pas sa fenêtre.** C'est la page qui lui donne signe de vie ; le reste
  (`vues/veille.py`) n'est que la règle qui décide quand conclure. Elle compte des **battements**,
  pas des secondes : c'est ce qui la rend testable sans horloge, et insensible à une mise en veille.
- **Prendre le port avant de charger l'interface** règle deux problèmes d'un coup : un second
  double-clic trouve la place occupée, et la fenêtre peut s'ouvrir tout de suite — sa demande attend
  dans la file du port pendant que Dash se charge.
- **Une adresse, deux usages** : `/pastory/vie` reçoit les signes de vie et répond « qui est là ».
  Sans la seconde moitié, un Pastory déjà ouvert serait indiscernable d'un autre programme sur le
  même port.
- **La démonstration ne traverse aucune couche** : elle écrit un export et détourne le dossier
  personnel (`PASTORY_DOSSIER`). Tout ce qui suit ignore qu'il s'agit d'un exemple, sauf l'écran.
  Conséquence utile : **la démonstration est un essai de bout en bout sur de vrais titres**, et
  elle a trouvé un défaut que les données fictives des tests ne pouvaient pas montrer (une
  période où un titre ne cotait pas, prise pour une panne).
- **Un raccourci ne doit dépendre de rien de fragile** : il appelle l'interpréteur de
  l'environnement par son chemin. `uv run`, qui resynchronise avant de lancer, peut échouer là où
  l'environnement installé fonctionne.
- **`pyproject.toml` n'a pas changé à l'étape 10**, et c'est voulu : ni point d'entrée graphique,
  ni dépendance. Le lanceur s'appelle par `-m pastory.lanceur`.
- **Une installation dépend de la date à laquelle on la fait** ([D-114](decisions.md)). Sans
  version de Python fixée, `uv` prend la plus récente ; le fichier de verrouillage, lui, ne
  connaît que les bibliothèques publiées le jour où il a été écrit. Entre les deux, une sortie de
  Python suffit à casser l'installation d'un dépôt qui n'a pas changé d'une ligne. D'où
  `.python-version`, et le test qui vérifie que chaque bibliothèque existe toute prête pour lui.
- **Une dépendance peut en cacher une autre** ([D-116](decisions.md)). pandas, déclaré depuis
  l'étape 1 et plus importé nulle part, apportait `tzdata` — dont `zoneinfo` a besoin sous
  Windows pour l'heure de Paris. Retirer l'inutile a révélé l'indispensable. Pour vérifier qu'on
  peut se passer d'une bibliothèque sans la désinstaller : `sys.modules["pandas"] = None` avant
  de lancer les tests, puis lire ce qui casse.
- **Le serveur est local, et cela ne suffit pas à le protéger** ([D-115](decisions.md)).
  N'écouter que `127.0.0.1` arrête les autres machines, pas les autres **sites** ouverts dans le
  même navigateur. Ce qui protège des sites : le navigateur refuse à un site de lire les réponses
  d'un autre, Dash n'accepte que du JSON (ce qu'un autre site ne peut envoyer sans permission),
  et — depuis l'étape 11 — Pastory refuse toute demande adressée à un autre nom que le sien. Tout
  rappel nouveau qui **écrit** (un dépôt, une suppression, demain une correction) repose sur ces
  trois barrières : ne pas en retirer une.
- **Renommer le dossier du projet laisse trois traces** : les raccourcis (à recréer par
  `pastory installer`), le chemin du projet dans l'environnement
  (`.venv/Lib/site-packages/_editable_impl_pastory.pth`, corrigé à la main le 2026-10-13), et les
  chemins gardés dans les fichiers compilés, sans conséquence. Windows répare seul la **cible**
  d'un raccourci qu'on lance, mais pas son **image** : d'où une icône blanche sur un raccourci qui
  marche.

## 9. Qualité et vérification

- Tests `pytest` sur **données fictives uniquement**, versionnés ([D-38](decisions.md)). Aucune
  donnée réelle dans les tests. *Seule exception, depuis l'étape 10 :* le portefeuille de
  démonstration et son test portent des ISIN réels de titres publics ([D-107](decisions.md)).
- **Aucun test n'écrit sur le bureau ni n'ouvre de fenêtre** : un garde-fou automatique de plus
  (`tests/garde_fous.py`), à côté de ceux qui coupent le réseau et détournent le dossier personnel.
- Un **cahier de vérification** par étape de calcul, avec des cas refaisables à la main
  ([feuille-de-route.md](feuille-de-route.md)).
- Le script [inventaire_structure.py](../scripts/inventaire_structure.py) peut servir à
  diagnostiquer un nouvel export (types jamais vus) sans exposer de valeurs.
