# Feuille de route

Les grandes étapes pour construire l'application, dans l'ordre. Pour chacune : le but, ce que
Claude fait, **ce que tu dois faire**, et quand changer de session ou d'agent.

Chaque étape se termine par un point de validation. **On ne passe pas à la suivante sans ton
accord.**

État : ✅ terminé · 🔜 prochaine · ⏳ à venir

---

## Méthode commune à toutes les étapes

### Une étape = une nouvelle session Claude
Une longue conversation accumule du contexte et finit par se perdre. Ouvre une **nouvelle
conversation** au début de chaque étape et copie le message préparé dans
[prompt-session-suivante.md](prompt-session-suivante.md).

Tout ce qui doit survivre d'une session à l'autre est écrit dans `docs/` : c'est la mémoire du
projet. **Chaque étape met à jour `prompt-session-suivante.md` avant sa fusion dans `main`**, pour
que la session d'après sache d'où elle part.

### Déroulé type d'une étape
1. **Plan d'abord.** Claude propose un plan (mode plan). Tu le lis et tu l'acceptes ou le corriges.
   Rien n'est écrit avant.
2. **Questions.** Si une interprétation est ambiguë, Claude l'ajoute à
   [questions-ouvertes.md](questions-ouvertes.md) et te la pose.
3. **Réalisation** sur une branche git dédiée, avec des tests.
4. **Relecture** par un agent séparé (`/code-review`), qui n'a pas écrit le code.
5. **Vérification par toi**, à l'aide du *cahier de vérification* de l'étape (voir ci-dessous).
6. **Fusion** dans `main` et envoi sur GitHub, après ton accord.

### Le cahier de vérification
Toute étape qui calcule des chiffres produit un fichier `docs/verification/etape-N.md` avec :
- **des cas fictifs calculés à la main**, pas à pas, que tu peux refaire sur papier ou dans un
  tableur, et le résultat que donne le programme ;
- **une liste de contrôles sur tes vraies données** à comparer avec l'application Trade Republic
  (ex. « quantité de chaque actif », « valeur de chaque position »). Les résultats sur tes données
  vont dans un fichier séparé `docs/verification/etape-N.local.md`, que le `.gitignore` exclut :
  il reste sur ta machine.

### Quand changer d'agent
| Situation | Agent |
|---|---|
| Écrire ou modifier du code | Session principale, en mode plan puis exécution |
| Comparer des sources externes (cours, TER, composition des ETF) | **Agent de recherche** (recherche web), lancé par la session principale. Il rend un comparatif, pas de code |
| Relire le code d'une étape | `/code-review` (agent indépendant) |
| Avant de rendre le dépôt public | `/security-review` + recherche de données personnelles dans tout l'historique git |
| Concevoir l'interface | Session dédiée, avec des prototypes visuels à comparer avant tout code |

### Tes réflexes permanents
- **Ne jamais** coller de vraies valeurs dans un fichier du dépôt ni dans une issue GitHub.
- Relancer `pytr` pour rafraîchir `data/` avant de vérifier des chiffres.
- Quand un chiffre te semble faux : le dire à Claude avec l'actif, la date et la valeur attendue.
  Le problème part alors dans les questions ouvertes ou devient un test.

---

## Étape 0 · Cadrage et données ✅
Dépôt protégé, documentation, inventaire des données, arbitrages (D-01 à D-30). Seule question
encore ouverte : Q-21 (présentation des frais), qui attend l'étape 8. Les points d'architecture
notés en chemin sont dans [architecture-notes.md](architecture-notes.md).

## Étape 1 · Derniers arbitrages et choix techniques ✅
**But :** figer ce qui conditionne tout le code.

**Fait :** format pivot écrit et validé ([format-pivot.md](format-pivot.md)), choix techniques
arbitrés (D-31 à D-38 : Dash, uv, `Decimal`, vocabulaire français, heure de Paris, fichiers
personnels hors OneDrive, TOML et `pytest`), squelette du dépôt en wagons avec les contrôles de
cohérence et leurs tests. La relecture indépendante a trouvé cinq défauts, tous corrigés — dont un
montant brut illisible qui passait sans alerte.

**Claude :**
- Propose l'outillage : langage (Python, imposé par pytr), bibliothèque d'interface locale,
  organisation des dossiers, tests, gestion des dépendances. Chaque option est présentée avec ses
  avantages, ses inconvénients et une recommandation.
- Décrit l'**architecture en wagons** (D-26) : adaptateur par banque → format pivot documenté →
  moteur → interface. Le **format pivot** (liste des champs d'une opération sur actif) est écrit
  dans `docs/format-pivot.md`, avec des exemples fictifs, **avant** le code.
- Consigne les choix dans `decisions.md`.

**Toi :**
- Relire les options techniques et en choisir une par sujet (Claude recommande, tu tranches).
- Relire le format pivot : chaque champ doit avoir un sens clair pour toi.
- Valider les choix techniques. Critère simple pour toi : « un autre utilisateur pourra-t-il
  l'installer en quelques commandes ? ».

**Session :** nouvelle session, mode plan.

## Étape 2 · Lecture des données ✅
**But :** transformer `all_events.json` en une liste propre d'opérations sur actifs **au format
pivot**, sans rien perdre en silence. C'est l'adaptateur Trade Republic, le premier wagon.

**Fait :** adaptateur complet (`dashboard_tr/adaptateurs/trade_republic/`), quatre commandes
(`rafraichir`, `comptes`, `lire`, `exporter-pivot`), recoupement automatique avec le CSV, et le
[cahier de vérification](verification/etape-2.md). Sur les deux exports disponibles : 80
opérations produites, **zéro contrôle de cohérence en échec**, un seul événement inconnu — le
transfert de PEA du tiers (Q-10), affiché au lieu d'être rangé.

Quatre décisions nouvelles (D-39 à D-42) et trois confirmations (D-06, D-08, D-09). La lecture
des textes s'est révélée plus piégeuse que l'inventaire ne le laissait voir : les dix constats
sont dans [inventaire-donnees.md §11](inventaire-donnees.md). Le principal — **un même export
mélange deux écritures des nombres** — aurait donné des quantités un million de fois trop
grandes sans déclencher la moindre alerte.

**Claude :**
- Écrit l'adaptateur : classement explicite de chaque type (traité, hors périmètre,
  écarté, **inconnu**), contrôle du statut, rapport des événements ignorés.
- Écrit le **module de lecture des textes** (quantité, prix, frais, taxes, poche), avec le
  dictionnaire allemand et français. Chaque valeur tirée d'un texte est marquée.
- Définit la configuration « nommer ses comptes ».
- Écrit les tests avec des événements fictifs, y compris des types inconnus et des libellés non
  reconnus.

**Toi :**
- Lancer le lecteur sur tes données (Claude te donne la commande).
- Vérifier dans le rapport qu'il n'y a **aucun type inconnu**, que chaque achat et vente de l'app
  Trade Republic figure dans la liste, avec la bonne quantité, les bons frais et la bonne poche.
- Si possible, le faire aussi sur un autre export (ton ami) : Claude ne regarde que le rapport de
  comptages.

**Session :** nouvelle session. Relecture `/code-review` à la fin.

## Étape 3 · Moteur de positions ✅
**But :** pour chaque actif et chaque date, calculer la quantité détenue, le capital net investi,
le PRU, les frais, les taxes, les dividendes et les plus-values réalisées. Tout est défini dans le
[glossaire](glossaire.md).

**Fait :** moteur complet (`dashboard_tr/moteur/`), trois commandes (`positions`,
`exporter-positions`, `positions-reelles`) et le [cahier de vérification](verification/etape-3.md).

Le moteur ne produit pas qu'un résultat : il tient un **journal**, une ligne par opération avec
l'état d'avant et l'état d'après, exporté en CSV. C'est ce qui permet de refaire un chiffre à la
main sans lire le code.

Trois décisions nouvelles (D-44 à D-46), issues de quatre arbitrages du propriétaire. La plus
structurante, [D-45](decisions.md) : **là où l'arithmétique n'a plus de sens, le moteur se tait
et le dit**. Un actif qui a reçu des parts sans prix connu n'affiche aucun prix de revient —
200 € pour 13 parts donneraient 15,38 €, un chiffre crédible et faux que rien ne signalerait.

Le format pivot gagne un **second contrat** ([§9](format-pivot.md)) : la photo du portefeuille
telle que la banque la donne. C'est le seul contrôle qui ne dépend d'aucune lecture de texte, et
le seul capable de révéler les titres entrés sans événement — la limite connue de D-15.

**Claude :**
- Implémente les règles D-12 à D-16. Le moteur ne lit **que** le format pivot, jamais les champs
  Trade Republic (D-26). Chaque formule du code renvoie à sa définition du glossaire.
- Calcule à part les **coûts payés** (frais et taxes par opération, D-21), sans les mélanger aux
  montants bruts.
- Produit le cahier de vérification : au moins un cas fictif par règle (achat avec frais, vente
  partielle au prorata, dividende taxé, distribution de capital, action gratuite, crypto).
- Prévoit la **comparaison avec les positions réelles** : pytr sait récupérer le portefeuille
  actuel. Tout écart de quantité entre ce portefeuille et le moteur est affiché. C'est ce qui
  détectera les titres entrés sans événement (limite de D-15).

**Toi :**
- Refaire à la main 2 ou 3 cas fictifs du cahier.
- Comparer, actif par actif, les quantités et le capital investi du moteur avec l'app Trade
  Republic.
- Signaler tout écart, même de quelques centimes.

**Dépendance :** le prix des titres reçus sans achat (D-15) a besoin des cours (étape 4). En
attendant, ils sont marqués « prix à compléter ».

**Session :** nouvelle session. `/code-review` à la fin.

## Étape 4 · Cours de marché 🔜
**But :** obtenir des cours fiables, actuels et historiques, gratuitement (D-18).

**Claude :**
- Lance un **agent de recherche** qui compare les sources Python gratuites selon des critères
  écrits : ETF européens et PEA, actions, cryptos, historique disponible, fiabilité, limites
  d'usage, pérennité.
- Traite un point délicat : Trade Republic identifie les actifs par **ISIN**, alors que la plupart
  des sources gratuites utilisent des **tickers** et des places de cotation. Il faut une
  correspondance ISIN → ticker, vérifiable et corrigeable par l'utilisateur.
- Met en place un cache local, pour ne pas retélécharger ni dépendre du réseau à chaque ouverture.

**Toi :**
- Choisir la source à partir du comparatif.
- Vérifier la correspondance ISIN → ticker de tes actifs, et comparer quelques cours avec l'app
  Trade Republic à la même date.

**Session :** nouvelle session : recherche d'abord, code ensuite.

## Étape 5 · Valorisation et rendements ⏳
**But :** capital brut dans le temps et les trois chiffres clés (D-22) : **gain en €**, **TRI**,
**TWRR**. Par actif, par poche et au total, selon la période choisie. Tout en montants bruts, sans
frais ni taxes (D-21).

**Claude :**
- Implémente les formules du glossaire (et Q-25 pour les dividendes).
- Produit le cahier de vérification : cas fictifs de TRI et de TWRR reproductibles dans un tableur
  (Excel et LibreOffice ont une fonction `TRI.PAIEMENTS`), avec la démarche.

**Toi :**
- Refaire un TRI fictif dans un tableur.
- Comparer la valeur totale et la valeur par position avec l'app Trade Republic à la même date.

**Session :** nouvelle session. `/code-review` à la fin.

## Étape 6 · Frais, taxes et valeur réelle ⏳
**But :** tout ce qui se passe à l'entrée et à la sortie, traité à part de l'évolution (D-21), et la
valeur « si on retirait tout » (D-23).

**Claude :**
- Présente le détail des **coûts payés** (issus de l'étape 3) : par opération, actif, poche et
  période, avec le poids de chaque coût dans son opération.
- Lance un agent de recherche :
  - base de données gratuite de TER ;
  - valeurs de spread par défaut par type d'actif, appliquées à l'achat et à la vente (D-30) ;
  - **règles fiscales françaises par poche** (PEA selon son ancienneté, CTO, crypto), avec les
    sources officielles.
- Implémente les **coûts estimés** (D-17) et la **valeur réelle** : capital brut − frais de vente
  estimés − impôts estimés. Les taux sont des paramètres datés et sourcés, faciles à mettre à jour
  quand la loi change.
- Cahier de vérification : cas fictifs d'impôt par poche, calculables à la main.

**Toi :**
- Vérifier le TER de 2 ou 3 de tes ETF sur la fiche de l'émetteur.
- Valider les spreads par défaut et les règles fiscales retenues (idéalement, avec une personne à
  l'aise avec la fiscalité).

## Étape 7 · Diversification ⏳
**But :** répartition géographique et sectorielle réelle, en regardant à l'intérieur des ETF
(Q-22).

**Claude :** agent de recherche sur les sources **gratuites et fiables** de composition des ETF
(D-28), avec critères écrits et comparatif. Puis implémentation, avec la date des données affichée.

**Toi :** choisir la source et comparer le résultat avec la fiche émetteur d'un ETF.

## Étape 8 · Conception de l'interface ⏳
**But :** concevoir l'application à neuf. La maquette du PDF n'est pas un modèle (D-20).

**Claude :**
- Part des **besoins** : questions auxquelles l'utilisateur veut une réponse en un coup d'œil,
  onglets des notes, style éditorial (crème, sauge, terracotta, sobre).
- Respecte la séparation voulue :
  - **synthèse** = cœur de l'évolution, brut : gain en €, TRI, TWRR (D-22) ;
  - **frais et taxes** à part ;
  - **valeur réelle** à part (D-23).
- Fait trancher Q-21 (présentation des frais).
- Propose plusieurs prototypes visuels cliquables **avant tout code**. Chaque déduction et chaque
  estimation y est signalée visuellement.

**Toi :** choisir et corriger les prototypes. C'est l'étape où ton avis compte le plus.

**Session :** session dédiée à la conception.

## Étape 9 · Réalisation de l'interface ⏳
**But :** brancher l'interface retenue sur le moteur.

**Claude :** implémente écran par écran, en commençant par la synthèse. Affiche les types inconnus,
les déductions et les estimations.

**Toi :** utiliser l'application sur tes données et noter tout ce qui est faux, lent ou peu clair.

## Étape 10 · Installation pour d'autres utilisateurs ⏳
**But :** qu'un investisseur non développeur l'installe en quelques étapes.

**Claude :**
- Écrit le guide d'installation (README).
- **Identifiants (D-25)** :
  - vérifie d'abord ce que pytr stocke exactement : session, PIN éventuel, durée de validité,
    emplacement du fichier, et si cet emplacement est synchronisé par OneDrive ;
  - supprime le PIN passé en argument de commande ;
  - propose à l'installation les trois modes (rien d'enregistré / gestionnaire d'identifiants du
    système / session pytr seule), avec les risques de chacun ;
  - ne met jamais de PIN en clair dans le projet, un `.env` ou OneDrive.
- Écrit l'assistant « nommer ses comptes », le rafraîchissement des données et les messages
  d'erreur compréhensibles.
- Documente comment écrire un **adaptateur pour une autre banque** à partir du format pivot (D-26).

**Toi :**
- Faire installer l'application par quelqu'un d'autre (ton ami ?) en suivant **seulement** le
  README, et noter chaque blocage.
- Relire l'explication des trois modes de stockage : est-elle compréhensible sans être
  développeur ?

## Étape 11 · Publication ⏳
**But :** rendre le dépôt public sans risque.

**Claude :**
- Lance `/security-review`.
- Cherche noms, IBAN, numéros de compte et jetons **dans tout l'historique git**, pas seulement
  dans les fichiers actuels.
- Écrit la licence et la page d'accueil du dépôt.

**Toi :** relire le README, choisir la licence (elle doit autoriser les forks pour d'autres
banques, D-26), passer le dépôt en public sur GitHub (Settings → Danger Zone → Change visibility).

## Étape 12 · Simulation Monte-Carlo ⏳ (fonctionnalité indépendante, D-27)
**But :** projection du patrimoine selon un montant épargné et un rendement cible. Rien d'autre
n'en dépend : cette étape peut venir quand tu le souhaites, après le cœur.

**Claude :** définit d'abord les hypothèses dans le glossaire (loi des rendements, volatilité,
horizon), puis les implémente.

**Toi :** valider les hypothèses, qui devront être affichées à l'écran.
