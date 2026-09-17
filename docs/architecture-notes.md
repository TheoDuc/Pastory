# Notes d'architecture

Points d'architecture relevés au fil des sessions. L'**étape 1** en a repris une partie et l'a
figée : le format pivot (§2) et les choix d'outillage (D-31 à D-38). Le reste attend l'étape qui
le concerne.

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

## 3. Adaptateur Trade Republic

- **Classement explicite de chaque `eventType`** en quatre catégories : traité, hors périmètre
  (espèces), écarté (information), **inconnu**. Aucun classement par défaut
  ([D-08](decisions.md), [D-11](decisions.md)).
- Contrôle du statut (`EXECUTED`), car un plan échoué porte un montant.
- **Rapport de lecture** produit à chaque chargement : nombre d'événements par catégorie, liste des
  types inconnus, libellés non reconnus. L'interface doit pouvoir l'afficher.
- **Lecteur de textes isolé** dans un seul module, avec un dictionnaire de libellés allemand et
  français ([D-09](decisions.md), [D-19](decisions.md)). Formats numériques localisés (`1.234,56`).
- Poche : compte de l'achat (compte espèces du PEA → PEA), libellé « Portfolio » en contrôle, code
  `XF` → crypto ([D-16](decisions.md)).
- Les numéros de compte ne sortent jamais de l'adaptateur, sauf dans la configuration locale.

## 4. Traçabilité : chaque chiffre dit d'où il vient

Condition pour qu'un non-développeur puisse vérifier.

- Chaque valeur porte sa **provenance** : `donnee` (champ structuré), `texte` (lu dans un libellé,
  fragile), `deduction` (règle), `estimation` (spread, TER, impôt).
- L'interface montre visuellement déductions et estimations, et permet de remonter d'un chiffre aux
  opérations qui le composent.
- Chaque formule du code renvoie à sa définition du [glossaire](glossaire.md).

## 5. Moteur

- Calcule par actif puis agrège par poche et au total. Les filtres (période, poches) s'appliquent
  à l'agrégation, pas à la lecture.
- Deux comptabilités **séparées** dès le moteur ([D-21](decisions.md)) :
  - **performance** sur montants bruts : capital net investi, PRU, gain, TRI, TWRR ;
  - **coûts** : frais et taxes réels, spread estimé à l'achat et à la vente, TER pendant la détention
    ([D-30](decisions.md)).
- **Valeur réelle** = performance − coûts de sortie estimés ([D-23](decisions.md)).
- Titres reçus sans achat : prix = cours du jour d'apparition, marqué `deduction`
  ([D-15](decisions.md)).
- **Rapprochement avec les positions réelles** (portefeuille actuel via pytr) : tout écart de
  quantité est signalé. Il révèle les titres entrés sans événement.
- TRI et TWRR sur courte durée : fournir aussi un indicateur « peu significatif » à l'interface.

## 6. Données externes

- Sources **gratuites et fiables**, choisies par comparatif écrit ([D-18](decisions.md),
  [D-28](decisions.md)).
- **Chaque source derrière une interface interchangeable**, comme les banques : changer de
  fournisseur de cours ne touche pas le moteur. *(à étudier)*
- **Correspondance ISIN → identifiant de la source** (ticker, place de cotation), stockée dans la
  configuration locale, vérifiable et corrigeable par l'utilisateur.
- **Cache local** des cours, TER et compositions, avec la date de récupération. L'application doit
  s'ouvrir sans réseau, sur les dernières données connues, et afficher leur date.
- **Paramètres datés et sourcés**, dans des fichiers lisibles, mis à jour sans toucher au code : taux
  fiscaux par poche, spreads par défaut.

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
