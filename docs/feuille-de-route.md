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
- Télécharger un nouvel **export des transactions** dans l'application Trade Republic (Profil →
  Relevés → Export des transactions, « toutes les transactions ») et le déposer dans le dossier
  `exports` de Pastory avant de vérifier des chiffres.
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

**Fait :** adaptateur complet (`pastory/adaptateurs/trade_republic/`), quatre commandes
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

**Fait :** moteur complet (`pastory/moteur/`), trois commandes (`positions`,
`exporter-positions`, `positions-reelles`) et le [cahier de vérification](verification/etape-3.md).

Le moteur ne produit pas qu'un résultat : il tient un **journal**, une ligne par opération avec
l'état d'avant et l'état d'après, exporté en CSV. C'est ce qui permet de refaire un chiffre à la
main sans lire le code.

Quatre décisions nouvelles (D-44 à D-47). La plus structurante, [D-45](decisions.md) : **là où
l'arithmétique n'a plus de sens, le moteur se tait et le dit**. Un actif qui a reçu des parts
sans prix connu n'affiche aucun prix de revient — 200 € pour 13 parts donneraient 15,38 €, un
chiffre crédible et faux que rien ne signalerait.

Le format pivot gagne un **second contrat** ([§9](format-pivot.md)) : la photo du portefeuille
telle que la banque la donne. C'est le seul contrôle qui ne dépend d'aucune lecture de texte, et
le seul capable de révéler les titres entrés sans événement — la limite connue de D-15.

**Le propriétaire a vérifié ses chiffres et les confirme.** Son essai a révélé une limite de
l'outil, et non du calcul : `pytr` ne demande les positions que d'un seul compte-titres, alors
que Trade Republic loge le PEA dans un second. Le rapprochement ne couvre donc pas le PEA, ce
qui est désormais signalé une fois au lieu de produire une alerte par actif
([D-47](decisions.md)). La suite est ouverte en [Q-26](questions-ouvertes.md).

La relecture indépendante a trouvé sept défauts, tous aux frontières du moteur — le cœur du
calcul a tenu. Tous corrigés, et chacun couvert par un test.

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

## Étape 4 · Cours de marché ✅
**But :** obtenir des cours fiables, actuels et historiques, gratuitement (D-18).

**Fait :** le [comparatif des sources](sources-de-cours.md) — quatorze sources, 134 requêtes web —
puis la couche `pastory/donnees_externes/`, trois commandes (`actifs`, `cours`,
`oublier-cours`) et le [cahier de vérification](verification/etape-4.md).

**Quatre décisions** : la source est Yahoo Finance en cours brut ([D-51](decisions.md)), la
référence est le marché principal en euros avec vérification de la devise ([D-48](decisions.md)),
aucun cours ne passe par Trade Republic ([D-49](decisions.md)), un cours en cache est définitif
([D-50](decisions.md)).

Le premier branchement est fait : les **titres reçus sans prix** ([D-15](decisions.md)) ont
désormais un prix, donc un capital investi et un prix de revient. **Le moteur n'a pas changé d'une
ligne** — la complétion transforme du pivot en pivot, et le moteur ignore toujours qu'une source
de cours existe.

Trois pièges trouvés en interrogeant réellement le service, chacun capable de produire un chiffre
crédible et faux, chacun désormais couvert par un test : le cours **retraité des dividendes**
(qui les compterait deux fois, et qui est invisible sur un ETF capitalisant) ; la **devise** qui
change avec la place, dont un cas où la recherche par ISIN renvoie des dollars ; et la série
**mensuelle** qui se présente comme quotidienne.

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

## Étape 5 · Valorisation et rendements ✅
**But :** capital brut dans le temps et les trois chiffres clés (D-22) : **gain en €**, **TRI**,
**TWRR**. Par actif, par poche et au total, selon la période choisie. Tout en montants bruts, sans
frais ni taxes (D-21).

**Fait :** deux modules dans le moteur (`valorisation.py`, `rendements.py`), deux blocs de plus
dans `pastory positions` (« Valeur des actifs au … » et « Les trois chiffres clés »), quatre
CSV de plus dans `exporter-positions` (valorisation, flux, sous-périodes du TWRR, évolution jour
par jour), l'option `--depuis`, et le [cahier de vérification](verification/etape-5.md).

**Trois décisions** : la valeur d'« aujourd'hui » est celle de la **dernière clôture connue**,
datée ([D-52](decisions.md)) ; un actif sans cours **sort des totaux**, qui sont marqués partiels
([D-53](decisions.md)) ; et les **conventions de calcul** qui rendent les chiffres refaisables
dans un tableur — période bornes comprises, flux signés selon le pivot, TRI façon
`TRI.PAIEMENTS`, TWRR aux cours de clôture ([D-54](decisions.md)).

**Le moteur n'importe toujours pas la couche des cours** : il déclare la forme qu'il attend
d'une source (une méthode), le fournisseur de l'étape 4 la satisfait sans le savoir, et
`cli.py` fait le lien. Un test prouve l'emboîtement.

Deux corrections au glossaire en chemin, toutes deux nées d'un cas fictif : la formule du gain
**omettait les distributions de capital** (le pivot les comptait déjà comme flux, et sans elles
la décomposition latente + réalisée + dividendes ne tenait plus) ; et la formule littérale du
TWRR, avec des clôtures et un flux au prix d'exécution, donnait **−100 % sur un actif gagnant**
dès qu'on vendait tout légèrement au-dessus de la clôture.

Les cas du cahier sont construits pour tomber juste — 10,00 % exactement, un TWRR de 0 % contre
un TRI de −26,79 % sur le même portefeuille — et chacun est un test.

La relecture indépendante a rendu dix remarques, toutes traitées : le garde-fou de devise
manquait dans la chaîne du TWRR (il est désormais le même partout), un pourcentage s'arrondissait
« au pair », une période à l'envers n'était refusée qu'après avoir tout lu, les refus rencontrés
en construisant l'évolution n'étaient pas affichés, et la table de `flux.csv` était écrite
séparément de celle qui sert au TRI (elles sont maintenant une seule). Le fournisseur de cours
cherche le dernier jour coté par dichotomie : l'évolution jour par jour ne ralentit plus avec la
taille du cache.

**Le propriétaire a vérifié ses chiffres et les confirme (2026-09-27).** La valeur totale de ses
actifs s'écarte de celle de son application de moins de deux dixièmes de pour cent, l'écart de
place annoncé par [D-48](decisions.md). Son essai a montré qu'une crypto, identifiée par un code
interne et non par un ISIN, doit recevoir son ticker **à la main** : l'assistant le dit désormais.

**Reste à faire avant la fusion :** son accord.

**Claude :**
- Implémente les formules du glossaire (et Q-25 pour les dividendes).
- Produit le cahier de vérification : cas fictifs de TRI et de TWRR reproductibles dans un tableur
  (Excel et LibreOffice ont une fonction `TRI.PAIEMENTS`), avec la démarche.

**Toi :**
- Refaire un TRI fictif dans un tableur.
- Comparer la valeur totale et la valeur par position avec l'app Trade Republic à la même date.

**Session :** nouvelle session. `/code-review` à la fin.

## Étape 6 · Frais, taxes et valeur réelle ✅
**But :** tout ce qui se passe à l'entrée et à la sortie, traité à part de l'évolution (D-21), et la
valeur « si on retirait tout » (D-23).

**Fait :** trois recherches ([couts-et-fiscalite.md](couts-et-fiscalite.md) — TER, spreads et
tarifs, fiscalité française sur sources officielles), puis trois modules dans le moteur
(`couts.py`, `fiscalite.py`, `valeur_reelle.py`), un paquet de **paramètres datés et sourcés**
(`pastory/parametres/`), une source de TER (`donnees_externes/xetra.py`), trois blocs de plus
dans `pastory positions`, deux CSV de plus, et le [cahier de vérification](verification/etape-6.md).

**Sept décisions** (D-55 à D-61). La plus structurante, [D-58](decisions.md) : **un taux est une
valeur, une date et une source**, dans un fichier TOML versionné — sans date ni source, il est
refusé à la lecture. Corriger un taux quand la loi change ne demande aucune ligne de code.

La recherche fiscale a trouvé ce qu'aucune mémoire n'aurait donné : **les prélèvements sociaux
sont passés de 17,2 % à 18,6 %** en 2026 (la loi de financement de la sécurité sociale a relevé la
CSG sur les revenus du capital), donc le prélèvement forfaitaire unique vaut **31,4 %**. Recoupé
sur impots.gouv.fr. Un projet qui aurait gardé 30 % de tête se serait trompé sur tous ses chiffres
d'impôt.

[D-57](decisions.md) règle une dette laissée par [D-13](decisions.md) : le moteur tient désormais
un **capital fiscal** à côté du capital investi — le prix de revient au sens de l'impôt inclut les
frais d'achat, celui du projet les exclut. Les deux sont justes, ils ne répondent pas à la même
question, et le journal les montre côte à côte.

**Le moteur n'importe toujours ni les paramètres ni la configuration** : il déclare deux
protocoles de plus (`ParametresDeCouts`, `ReglesFiscales`), et `cli.py` fait le lien — le même
chemin que la source de cours à l'étape 5.

La relecture indépendante a rendu six remarques, toutes traitées, et chacune couverte par un
test. Les deux premières étaient des erreurs de calcul, et toutes deux venaient du **même angle
mort** — ce que l'application ne voit pas :

- **la valeur réelle du PEA pouvait être négative.** L'impôt du plan porte sur son gain entier,
  ventes passées et dividendes compris, mais leur argent est dans les **espèces du plan**, hors
  périmètre ([D-11](decisions.md)) : on retranchait un impôt dont la contrepartie manquait à
  l'actif. Un PEA entièrement vendu affichait « VALEUR REELLE −30,77 ». Désormais la valeur du PEA
  est marquée **minorée**, avec le montant concerné, et aucun chiffre n'est affiché si le résultat
  devient négatif ;
- **le seuil d'exonération de la crypto ignorait les ventes déjà faites dans l'année.** Le seuil
  de 305 € est annuel : deux ventes de 200 € le dépassent. L'application annonçait « exonéré » et
  un impôt nul là où il y en avait un — une erreur qui donne zéro, donc invisible.

Les quatre autres étaient des pièges de robustesse : une proposition de TER sans ticker écrivait
dans `actifs.toml` une ligne d'apparence valide que la lecture écartait en silence ; le fichier
`.xlsx` de Xetra était lu **par le rang des cellules**, alors qu'un tableur omet les cases vides —
un ISIN pouvait être lu dans la colonne du nom ; une date de PEA écrite avec une heure faisait
remonter une trace technique au lieu du message prévu ; et « TER à compléter » s'affichait pour une
action, qui n'en a pas.

Deux choses restent à sa charge, écrites dans le cahier : ouvrir la **liste des prix française**
dans son application (le document public refuse les téléchargements automatiques) pour confirmer
les 1 € par ordre, et savoir que les taux fiscaux n'ont **pas** été relus par un tiers — il a
choisi de s'en tenir aux sources officielles (Q-38).

**Le propriétaire a configuré ses actifs, vérifié ses chiffres et les confirme (2026-09-27).**
Sa vérification a produit la dernière amélioration de l'étape, et elle vaut d'être retenue : il a
buté sur des **plus-values plus faibles que prévu**, dont une **négative** sur une petite position
en crypto, alors que celle-ci avait gagné. La cause n'était pas un calcul faux mais un affichage
incomplet — la ligne arrivait **déjà nette** des coûts de sortie, sans montrer l'étape d'avant.
Deux facteurs se cumulaient, et aucun n'était visible : l'euro de frais de vente, facturé **par
ligne** et non par poche, qui pèse plusieurs pour cent d'une petite position ; et l'écart entre le
cours de clôture du marché principal et le prix courant de la banque ([D-48](decisions.md)).

Le détail de chaque impôt montre donc désormais la plus-value **en deux temps** : avant coûts de
sortie — la ligne qui se compare à l'application de la banque — puis ces coûts retranchés. La
leçon est générale et vaut pour les étapes suivantes : **un chiffre juste mais impossible à
rapprocher d'une autre source est un chiffre qu'on ne croit pas.**

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

## Étape 7 · Diversification ✅
**But :** répartition géographique et sectorielle réelle, en regardant à l'intérieur des ETF
(Q-22).

**Fait :** trois recherches ([composition-des-etf.md](composition-des-etf.md) — quatorze familles de
sources examinées, onze interrogées réellement), puis `moteur/diversification.py`, trois
référentiels datés et sourcés (`parametres/secteurs.toml`, `zones.toml`, `classes_actifs.toml`),
deux sources de composition (`donnees_externes/extraetf.py` pour les fonds,
`donnees_externes/actions.py` pour les sociétés), un cache **remplaçable**, un bloc de plus dans
`pastory positions`, trois CSV de plus, deux commandes (`composition`, `oublier-composition`) et
le [cahier de vérification](verification/etape-7.md).

**Neuf décisions** (D-62 à D-70). La plus large dépasse l'étape : [D-62](decisions.md), **les
choix de fonctionnalités visent l'utilisateur type de Trade Republic**, et non le portefeuille du
propriétaire — qui compte partager l'application. Elle est née d'un arbitrage rendu **contre** la
recommandation : traiter les actions détenues en direct, alors qu'il n'en détient aucune, parce que
l'achat d'actions à l'unité est courant sur cette banque.

La recherche a trouvé ce qu'aucune mémoire n'aurait donné, et c'est le piège central de l'étape :
**un ETF synthétique ne détient pas son indice**. Mesuré sur un ETF *MSCI World* à swap éligible au
PEA : son panier donne **Allemagne 38,5 %** et États-Unis 15,6 %, son indice **États-Unis 72,9 %**.
Ses lignes réelles sont Airbus, ASML, Siemens Energy — pour un fonds monde. Et tout ETF « PEA » sur
un indice non européen est synthétique **par construction**. L'application affiche donc l'indice
([D-64](decisions.md)), en marquant le fonds.

Deuxième trouvaille, et elle gouverne tout l'affichage : **une répartition géographique n'est pas
une grandeur définie de façon unique**. BlackRock l'écrit dans ses propres fiches — l'exposition
géographique se rapporte « principalement » au domicile de l'émetteur, « mais, dans certains cas,
elle peut refléter le lieu où l'émetteur réalise l'essentiel de son activité ». Deux sources
sérieuses donnent 70,00 % et 72,04 % d'États-Unis sur le même fonds au même arrêté. La règle
retenue est donc **affichée** ([D-66](decisions.md)), et une seule source sert par graphique.

**Aucune source gratuite interrogeable par ISIN ne donne du GICS** : la nomenclature est celle de
Morningstar, nommée comme telle et jamais appelée « GICS » ([D-65](decisions.md)). Les codes — ISO
3166-1 pour les pays, codes machine pour les secteurs — permettent de calculer **sans lire un seul
libellé affiché**, ce qui satisfait la règle 4.

**Claude :** agent de recherche sur les sources **gratuites et fiables** de composition des ETF
(D-28), avec critères écrits et comparatif. Puis implémentation, avec la date des données affichée.

**Toi :** choisir la source et comparer le résultat avec la fiche émetteur d'un ETF.

**Le propriétaire a vérifié ses chiffres et les confirme (2026-09-28).** Sa vérification a produit
les deux dernières corrections de l'étape, et elles se ressemblent : **l'application disait
« inconnu » là où la réponse était « sans objet »**. Un ETF d'obligations et un ETF de matières
premières étaient annoncés « non couvert : composition inconnue » alors qu'ils ont bien une
composition — elle n'a simplement ni pays ni secteur au sens des actions, comme un actif numérique.
D'où le **contenu déclaré** ([D-71](decisions.md)), les matières premières promues en classe
d'actifs, et des montants hors géographie affichés **classe par classe** au lieu d'un fourre-tout
qui faisait passer de l'or pour de la dette. Sur ses données, « non couvert » est passé de 35,3 % à
17,9 %.

Il a aussi demandé d'investiguer le seul fonds d'**actions** resté sans composition, plutôt que de
le masquer par une déclaration. Le diagnostic a écarté trois fausses pistes — ce n'est pas un
problème de **part**, rien n'est récupérable par **région**, et la source **couvre bien** les fonds
émergents à réplication **physique** (35 et 28 pays sur deux fonds testés). La lacune porte sur
certains fonds **à swap**, fonds par fonds. Il a tranché une **source de secours par actif, nommée à
l'écran** ([D-72](decisions.md)), à réaliser à l'étape 8 parce que c'est d'abord un problème de
présentation.

## Étape 8 · Conception de l'interface ✅
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
- **Réalise la source de secours par actif** ([D-72](decisions.md)), reportée ici depuis l'étape 7
  parce qu'elle est d'abord un problème de présentation : deux sources n'ont pas la même
  nomenclature, donc la source de chaque chiffre doit être **visible ligne par ligne**. C'est ce qui
  fera disparaître les fonds « non couverts » du portefeuille du propriétaire.
- **Conçoit pour l'utilisateur type, pas pour le portefeuille du propriétaire** ([D-62](decisions.md),
  décidé pendant l'étape 7). Trois conséquences concrètes pour la conception :
  - les prototypes se testent sur des cas que le propriétaire **ne détient pas** : des actions en
    direct, un ETF obligataire, un actif non couvert par les sources, un portefeuille à une seule
    ligne, un portefeuille sans PEA ;
  - les **messages d'absence** sont du contenu d'interface à part entière, pas des notes
    techniques : « non couvert », « non attribué », « synthétique », « minoré » doivent
    s'expliquer là où ils s'affichent, pour un lecteur qui découvre l'application. *« Non
    transparisé » n'en fait pas partie : il reste au glossaire et ne s'affiche jamais, faute d'une
    source qui sache reconnaître un fonds de fonds ([D-76](decisions.md)) ;*
  - **deux règles de pays cohabitent** dans la répartition géographique ([D-66](decisions.md)) : la
    conception doit trouver comment le dire sans alourdir l'écran.

**Toi :** choisir et corriger les prototypes. C'est l'étape où ton avis compte le plus.

**Session :** session dédiée à la conception.

**Fait (2026-09-30) : la conception, en sept passes de relecture.** Les maquettes vivent dans
[maquettes/](../maquettes/) : de vrais fichiers HTML et CSS, avec un portefeuille fictif
d'utilisateur type plus large que celui du propriétaire (actions en direct, ETF obligataire, or,
fonds non couvert, position sans cours) et quatre jeux commutables pour éprouver les écrans sur ce
qu'il ne détient pas. Cinq onglets : Synthèse, Les actifs, Diversification, Frais et taxes, Détail
des calculs. La feuille de style deviendra `pastory/vues/assets/pastory.css` telle quelle
([D-31](decisions.md)).

**Q-21 est tranchée** ([D-73](decisions.md)) : les trois niveaux à la file, sur un seul écran.

**Ce que les relectures du propriétaire ont trouvé, et qui vaut pour l'étape 9 :**
- `var()` **n'est pas interprété dans un attribut SVG** : une couleur posée en attribut s'écrit en
  clair, une couleur posée en CSS passe par la variable ;
- sans `color-scheme: only light`, le mode sombre automatique du navigateur **inverse les clartés**,
  et les couleurs ne veulent plus rien dire — un gain en sauge peut virer au rouge ;
- un **SVG sans règle de taille** prend sa taille intrinsèque, qui remplit la page ;
- un anneau ne porte pas de chiffre : l'étiquette doit choisir sa couleur selon la part, et devient
  illisible sur les teintes intermédiaires. Le classement chiffré à côté fait foi ;
- **le gain n'est pas la somme d'une colonne** : il se calcule sur les montants bruts (D-21) là où
  le capital net investi est net de frais et réduit au prorata des ventes (D-12).

## Étape 8 bis · Compléments de décision ✅
**But :** finir ce que l'étape 8 laisse ouvert, avant de brancher quoi que ce soit.

**Claude :**
- ✅ **La source de secours par actif est faite** ([D-77](decisions.md)). La recherche a trouvé le
  service produit d'Amundi, qui publie la répartition de l'**indice suivi** par ISIN, gratuitement
  et avec sa date d'arrêté : sur un PEA Monde à swap — la famille même qui manquait — il rend
  **États-Unis 72,93 %**, contre 15,6 % pour le panier détenu. Couverture : 10 ISIN Amundi sur 10.
  Elle ne sert **que la géographie**, ses secteurs étant du GICS là où [D-65](decisions.md)
  n'admet qu'une nomenclature. Elle se déclare **par actif** (`secours = "amundi"`), et la source
  **et** la règle de pays sont désormais visibles **ligne par ligne**. Cahier :
  [verification/etape-8-bis.md](verification/etape-8-bis.md).
- ✅ **[Q-48](questions-ouvertes.md) est tranchée** ([D-76](decisions.md)) : aucune source
  accessible ne reconnaît un fonds de fonds. La notion reste au **glossaire** et ne s'affiche
  jamais ; un tel fonds est « non couvert », et la bulle de « non couvert » explique que certains
  fonds en contiennent d'autres. Les trois documents qui promettaient le mot sont corrigés.
- ✅ **[Q-49](questions-ouvertes.md) est tranchée** ([D-75](decisions.md)) : le premier niveau des
  frais est **« ce qui a déjà été prélevé »**, quel qu'en soit le moment, et la retenue sur
  dividendes y reste. Le découpage porte la séparation réel / estimé, et non une chronologie.
- ✅ **Écrit le document de conception** [conception-interface.md](conception-interface.md) : ses §1
  (l'inventaire), §2 (le vocabulaire d'écran), §3 (les règles d'affichage), §4 (les écrans retenus)
  et §5 (leurs quatre états). C'est le contrat que l'étape 9 exécute.

**Toi :**
- ✅ Q-48 et Q-49 tranchées.
- 🔜 vérifier la répartition de tes fonds aujourd'hui non couverts, maintenant que la source de
  secours est en place — le cahier [etape-8-bis.md](verification/etape-8-bis.md) dit comment.

**Session :** session dédiée.

---

> **Changement de cap du 2026-10-01 ([D-79](decisions.md)).** Trade Republic fournit depuis avril
> 2026 un **export officiel des transactions**, en CSV, dans son application. Il devient la porte
> d'entrée des opérations à la place de pytr : plus de connexion ni d'identifiant, plus de comptes
> à nommer, des données en colonnes au lieu de textes allemands, et plus de clause des conditions
> générales. Deux étapes s'intercalent avant l'interface, et les étapes 9 à 11 s'en trouvent
> allégées. Relevé du fichier : [export-officiel.md](export-officiel.md).

## Étape 8 ter · La nouvelle porte d'entrée : l'export officiel ✅
**But :** lire l'export officiel au format pivot, sans rien perdre en silence, et prouver qu'il
donne **les mêmes opérations** que pytr. Le moteur ne change pas d'une ligne ([D-26](decisions.md)).

**Fait :** l'adaptateur de l'export officiel (`pastory/adaptateurs/trade_republic/`), le dossier
de dépôt, le retrait complet de pytr ([D-81](decisions.md)), et le
[cahier de vérification](verification/etape-8-ter.md). Le moteur n'a pas changé d'une ligne de
calcul : seul le pivot a rendu facultatif le montant réglé ([D-83](decisions.md)).

Le premier export d'un **second utilisateur** a tout changé à la portée de l'étape : 149 lignes
sur un an, avec ventes, dividendes, actions gratuites et dividendes en dollars. Comparé ligne à
ligne à son export pytr, il concorde partout — à une exception près, découverte ici et que
personne ne documentait : **pour les dividendes néerlandais, l'export donne un brut déjà diminué
de la retenue des Pays-Bas**, sans la montrer ([D-84](decisions.md)). La recherche a confirmé
qu'aucun logiciel ne le corrige. Quatre décisions (D-81 à D-84), une question nouvelle
([Q-54](questions-ouvertes.md) : actions gratuites puis « migration »), et une règle de lecture
qui s'ajoute au classement explicite : **une forme jamais vue d'un type connu n'est pas
interprétée** — un dividende négatif, une obligation, un compte enfant restent des trous affichés.

Sur les données du propriétaire, toutes les positions sont identiques avant et après, sauf la
crypto : quelques centimes de capital investi, et son ticker à redéclarer sous son nouveau code.
Le propriétaire a vérifié le 2026-10-05 que les quantités sont celles de l'application.

**Claude :**
- **Recherche d'abord** (agent de recherche) : aucune liste des types n'est publiée. Rassembler
  les valeurs de `type` et d'`asset_class` connues des importeurs libres qui lisent déjà ce fichier
  (Portfolio Performance, DivvyDiary, convertisseurs pour Ghostfolio, projets français), en priorité
  le **dividende** (brut et retenue séparés ?), la **vente**, les **titres reçus** (actions
  gratuites, action gagnée, transfert entrant), le **Saveback** et la crypto reçue. Compléter le
  [§4 et le §7 d'export-officiel.md](export-officiel.md). Chaque type non vu sur un vrai fichier
  reste marqué 🔶 et n'est **pas** traité : il est affiché comme inconnu.
- **Écrit l'adaptateur** (à côté de celui de pytr, qui reste le temps de la comparaison) :
  - classement par liste explicite de `(category, type)` : traité, espèces hors périmètre,
    **inconnu affiché** ([D-08](decisions.md), règle 5) ;
  - la poche vient de `account_type` et `asset_class` — **aucun fichier `comptes.toml`** ;
  - les valeurs sont `donnee` ; seul `nature_source`, lu dans `description`, est marqué `texte` ;
  - **plusieurs fichiers** se cumulent, dédoublonnés par `transaction_id`, et la **période couverte**
    est affichée (un export partiel donne une histoire incomplète, [D-45](decisions.md)) ;
  - les lignes d'espèces ne sont lues que par leur `type`, et comptées, jamais recopiées
    ([export-officiel.md §8](export-officiel.md)) ;
  - le contrôle du montant réglé est revu selon [Q-52](questions-ouvertes.md).
- **Le dossier de dépôt** ([D-80](decisions.md)) : un dossier de Pastory, dans le dossier
  personnel hors OneDrive ([D-37](decisions.md)), où l'utilisateur dépose ses exports ;
  l'application lit tout ce qui s'y trouve. Il remplace `rafraichir`.
- **La preuve par comparaison** : les deux adaptateurs sur la **même période** doivent produire les
  mêmes opérations, aux écarts près qui sont listés et expliqués (l'achat de crypto, §5 du relevé).
  C'est le cœur du [cahier de vérification](verification/) de l'étape.
- Selon [Q-50](questions-ouvertes.md) : retire pytr et son adaptateur, ou le réduit à la photo du
  portefeuille. Met à jour [architecture.md](architecture.md), [format-pivot.md](format-pivot.md)
  §4 (provenances) et `CLAUDE.md`.

**Toi :**
- Trancher [Q-50](questions-ouvertes.md), [Q-51](questions-ouvertes.md) et
  [Q-52](questions-ouvertes.md) — pour Q-52, regarder d'abord dans l'application ce qui a été
  réellement débité sur ton achat de crypto.
- Demander à ton ami un **export officiel** : l'application n'en lit que la structure (règle 2), et
  il contient sûrement des types que tu n'as pas — c'est le plus sûr moyen de couvrir les
  dividendes et les ventes.
- Le mois prochain, un nouvel export : il dira où vont les parts du **Saveback**.
- Vérifier, actif par actif, que les quantités et le capital investi n'ont pas bougé en changeant
  de source.

**Session :** nouvelle session : recherche d'abord, code ensuite. `/code-review` à la fin.

## Étape 8 quater · Des réglages qui se proposent seuls ✅
**But :** que l'application **trouve et applique seule** chaque réglage restant, avec sa source,
sa date et un contrôle ([D-80](decisions.md)). L'utilisateur ne fait que déposer l'export ; il
peut corriger, il n'a jamais à le faire.

**Fait :** une couche `pastory/reglages/` trouve, contrôle et montre chaque réglage ; `actifs.toml`
n'est plus qu'un fichier de **corrections**, jamais réécrit ([D-92](decisions.md)) ; `pastory
actifs` montre chaque valeur avec sa source, sa date, ce qui a été vérifié — ou le motif du trou.
Comparatif : [reglages-automatiques.md](reglages-automatiques.md). Cahier :
[verification/etape-8-quater.md](verification/etape-8-quater.md).

| Réglage | Trouvé où | Contrôle | Décision |
|---|---|---|---|
| Type d'un actif | l'export (`asset_class`) | une seule classe | [D-82](decisions.md) |
| Cotation | recherche par ISIN, puis par nom ; `CODE-EUR` pour une crypto | **prix payé** à la banque, et change pour un candidat trouvé par nom | [D-85](decisions.md), [D-88](decisions.md) |
| TER | l'émetteur (Amundi), puis la liste de Xetra | fourchette, date, accord des sources | [D-90](decisions.md) |
| Contenu d'un fonds | extraETF, code et libellé | code CFI du registre de l'ESMA | [D-89](decisions.md) |
| Source de secours | essayée d'elle-même | — | [D-91](decisions.md) |
| Date d'ouverture du PEA | mouvements d'espèces du PEA, jour et sens seulement | aucun titre avant ; un retrait avant 5 ans clôt le plan | [D-86](decisions.md) |
| Hypothèse « aucun retrait » | sorties d'espèces du PEA, dates seulement | — | [D-87](decisions.md) |

**Le critère**, sur le portefeuille du propriétaire sans aucune correction : **22 valeurs
trouvées, 1 introuvable** (le TER d'un ETF iShares « Swap PEA », dont la seule source n'a pas de
date). Toutes les valeurs qu'il avait validées à la main sont retrouvées à l'identique ; la date
d'ouverture de son PEA l'est depuis sa propre réponse sur une fermeture-réouverture.

En route, deux défauts anciens trouvés sur ses données : le lien de la liste de Xetra, écrit de
deux façons selon le serveur (la liste manquait trois fois sur quatre à certaines heures), et une
panne passagère qui aurait été gardée une semaine comme « TER introuvable ».

**Toi :**
- ✅ tranché les cinq pistes ([questions-ouvertes.md](questions-ouvertes.md), lot 12).
- 🔜 suivre le [cahier](verification/etape-8-quater.md) : déplacer ta configuration dans le dossier
  `Pastory`, alléger `actifs.toml`, comparer les cotations et les TER à ton application et aux
  documents des émetteurs.
- [Q-60](questions-ouvertes.md) (monétaire, multi-actifs, immobilier) et [Q-54](questions-ouvertes.md)
  restent ouvertes, sans urgence.

**Session :** réalisée en une session : trois agents de recherche en parallèle, puis le code.

## Étape 9 · Réalisation de l'interface 🔜
**But :** brancher l'interface retenue sur le moteur, **et faire disparaître l'édition de
fichiers**.

**Claude :**
- **Commence par l'écran d'accueil** : où déposer l'export, avec le chemin dans l'application
  Trade Republic (Profil → Relevés → Export des transactions), la période couverte une fois le
  fichier lu, et les types inconnus. C'est le premier écran d'un nouvel utilisateur.
- Implémente écran par écran, en commençant par la synthèse. Affiche les types inconnus, les
  déductions et les estimations.
- **Réalise les écrans de réglages** ([D-78](decisions.md), [§6 du contrat](conception-interface.md)).
  Depuis [D-80](decisions.md), ce sont des écrans de **correction, facultatifs** : chaque valeur
  trouvée (ticker, devise, type, TER, `contenu`, source de secours, date du PEA) y est montrée avec
  sa source, et peut être corrigée. Aucun n'est un passage obligé. Le fichier TOML reste le format
  de stockage. **L'étape n'est pas terminée tant qu'une correction n'existe qu'en fichier.** Le
  [§6 du contrat](conception-interface.md) est à réécrire en conséquence, en premier. Le contenu
  de ces écrans existe déjà : c'est `pastory/reglages` (une valeur, sa source, sa date, son
  contrôle, ou le motif du trou), et `pastory actifs` en est la version texte.
- Traite la contrainte annoncée : un écran qui écrit dans le fichier doit le **relire et le
  réécrire sans perdre ses commentaires**, sans quoi l'édition à la main perd son sens.

**Toi :** utiliser l'application sur tes données et noter tout ce qui est faux, lent ou peu clair.
Et **vérifier que tu n'ouvres plus aucun fichier** pour t'en servir.

**Avancement (2026-10-09) :** 9.0 à 9.4 faits : le contrat, l'accueil et le dépôt, la synthèse,
les actifs, la diversification, les frais et taxes, et le détail des calculs, devenu une page
discrète ouverte depuis la droite de la manchette (il remplace le compteur « À surveiller »).
Restent 9.5 (les écrans de correction) et 9.6 (cahier, revue, documents).

## Étape 9 bis · Une identité propre, et la prédiction de l'évolution ✅
**But :** passer d'une interface qui marche à une interface qu'on reconnaît, et ajouter la
section « Prédiction de l'évolution » ([D-97](decisions.md)). L'étape vient **après** la 9 :
elle reprend des écrans finis, elle ne les remplace pas.

**Claude :**
- **L'identité visuelle.** Aujourd'hui l'interface est propre mais sans caractère (le fond en
  particulier). Proposer une identité **en maquette d'abord** (`maquettes/`), en deux ou trois
  pistes comparables côte à côte : fond, typographie, couleurs, logo, rythme des blocs. Rien ne
  change dans les chiffres ni dans les règles d'affichage du contrat
  ([conception-interface.md](conception-interface.md) §3). Les couleurs de poche (D-96) et la
  palette des données restent contrôlées par le validateur (daltonisme, contraste).
- **La prédiction de l'évolution** (ce qui était l'étape 12) : une section à part, qui ne lit
  rien d'autre que la valeur de départ. Ce que le propriétaire a demandé :
  - les entrées : une **valeur de départ** (par défaut le capital brut du portefeuille, modifiable),
    un **taux annuel**, une **durée**, un **versement mensuel** ;
  - le résultat simple : **une courbe et le montant atteint** ;
  - une option **« taux aléatoire »** : **10 000 simulations**, d'autant plus dispersées que le
    taux visé est élevé, résumées par cinq courbes, les quantiles **5 %, 25 %, médiane, 75 % et
    95 %**.
  - **Les hypothèses s'écrivent d'abord** dans le glossaire (loi des rendements, lien entre taux
    et dispersion, pas mensuel ou annuel, ce que représente le taux), puis le propriétaire les
    valide ([Q-61](questions-ouvertes.md)). Elles sont **affichées à l'écran**, et la
    section dit clairement que c'est une hypothèse, pas une prévision ni un conseil.
  - Le cas sans aléa se refait à la main (intérêts composés plus versements) : c'est le cas de
    test, et le cahier de vérification le donne.

**Toi :** choisir une piste d'identité ; trancher [Q-61](questions-ouvertes.md) ; refaire le cas
sans aléa à la calculatrice.

**Avancement (2026-10-09) : l'identité visuelle est faite** ([D-98](decisions.md),
[D-99](decisions.md)). Le propriétaire a fixé une direction précise plutôt que de choisir entre
des pistes : **un livre ancien relié**. La [charte graphique](charte-graphique.md) fait référence ;
toutes les valeurs vivent dans `pastory/vues/assets/theme.css`. La couverture remplace l'accueil,
les onglets deviennent des chapitres numérotés (le V attend la prédiction), la valeur des actifs
ouvre la synthèse, l'anneau des poches devient une barre empilée, le logo est choisi (un livre
fermé et son signet). Après une première relecture du propriétaire : le nom « Pastory » ramène à
la couverture, qui tient désormais sans défiler, l'ouverture du livre se rejoue à chaque fois, et
une **lecture de nuit** suit le réglage du système ([D-100](decisions.md), [D-101](decisions.md)) ;
puis les éléments redeviennent des boîtes, la synthèse tient sur un écran ([D-102](decisions.md)),
et la troisième bande du bandeau disparaît : le colophon rejoint le titre de chaque chapitre, sous
lequel un fleuron sépare la page ([D-103](decisions.md)).
**Aucun chiffre n'a changé** : les 6 786 nombres relevés écran par écran sur
les données du propriétaire sont ceux d'avant, aux seules données de l'anneau retiré près.
**Fait ensuite (2026-10-09) : la prédiction de l'évolution**, au chapitre V. Q-61 tranchée par
le propriétaire ([D-105](decisions.md)) : le taux est celui de la médiane, des rendements
log-normaux mois par mois, une volatilité égale à deux fois le taux (sans valeur historique), un
taux nominal, une graine fixe. Le calcul vit dans `pastory/projection.py`, indépendant du moteur ;
le cas sans aléa se refait à la calculatrice ([cahier](verification/etape-9-bis.md)) : 1 000 €,
5 %, 10 ans, 100 €/mois donnent 17 065,21 €.

**Toi :** refaire ce cas à la calculatrice, et choisir « 10 000 simulations » pour comparer au
tableau du cahier.

**Validée par le propriétaire le 2026-10-09**, après une relecture `/code-review` dont les neuf
remarques sont traitées (bornes hautes des montants, valeur de départ partielle signalée, aide du
TWRR, courbe partant de la date de la valeur, ancres simples pour les Frais, tirages gardés en
mémoire, dessin allégé au-delà de 20 ans, champ vide sans valeur connue). Le logo de l'onglet est
désormais aussi un `favicon.ico`, que le navigateur ne peut plus confondre avec celui de Dash.

## Étape 10 · Installation pour d'autres utilisateurs 🔜
**But :** qu'un investisseur non développeur l'installe en quelques étapes, et qu'il **lance
Pastory comme un logiciel**, sans jamais ouvrir de terminal.

**Ce que le propriétaire a demandé (2026-10-09) :**
- **plus de commande à taper** pour lancer l'application : idéalement un **raccourci sur le
  bureau** qui l'ouvre « comme un logiciel classique » ;
- **un jeu de données de démonstration** : un export CSV fictif, au format officiel, pour montrer
  Pastory sans révéler son portefeuille ;
- **le ménage** : effacer du dépôt et de la machine les fichiers et dossiers devenus inutiles
  (anciennes données, restes de pytr…).

**Recommandation pour le lancement (à trancher en début d'étape) :**
- un **raccourci Pastory** (bureau et menu Démarrer), avec le logo (`assets/favicon.ico`), créé une
  fois pour toutes par l'installation ;
- il démarre Pastory **sans fenêtre noire** et ouvre l'application dans **une fenêtre à part, sans
  barre d'adresse** (le mode « application » d'Edge ou de Chrome) : elle a son icône dans la barre
  des tâches, comme un logiciel ;
- **fermer la fenêtre arrête Pastory** : la page donne régulièrement signe de vie au serveur, qui
  s'arrête seul quand elle se tait ; relancer le raccourci quand Pastory tourne déjà ramène la
  fenêtre existante ;
- **écarté a priori** : un `.exe` empaqueté (PyInstaller) — lourd, et les antivirus déjà rencontrés
  sur cette machine (Norton, Avast) signalent souvent ces fichiers comme suspects ; une fenêtre
  native (pywebview) — une dépendance de plus pour peu de gain sur le mode application ;
- **à prévoir** pour l'utilisateur type ([D-62](decisions.md)) : l'équivalent sur Mac.

**Le jeu de démonstration (à concevoir) :** un export fictif, au format officiel, qui couvre ce
que le propriétaire ne détient pas (actions en direct, dividendes, ventes, plusieurs poches) ; ouvert
dans un dossier **à part**, pour ne jamais se mêler aux vrais exports, et repérable à l'écran
(« données de démonstration »). Le générateur des tests (`tests/adaptateurs/trade_republic/
export_fictif.py`) en est le point de départ.

**Le ménage (liste à valider, rien n'est effacé sans accord) :** les dossiers de données locales
de l'époque pytr (`data/`, l'ancien dossier `DashBoardTradeRepublic` dans `AppData`), les
maquettes de l'étape 8 que l'application a remplacées (`maquettes/`, hors `maquettes/logo/`), et
les documents purement historiques à archiver plutôt qu'à garder en tête du dépôt.

**Claude :**
- Écrit le guide d'installation (README), dont **comment obtenir l'export** dans l'application
  Trade Republic, avec la période à choisir.
- **Identifiants :** il n'y en a plus aucun depuis l'étape 8 ter ([D-81](decisions.md)) : cette
  partie a disparu.
- Écrit les messages d'erreur compréhensibles : fichier qui n'est pas un export, colonnes
  inattendues, export partiel.
- Documente comment écrire un **adaptateur pour une autre banque** à partir du format pivot (D-26).
  L'export officiel en est désormais l'exemple le plus simple.

**Toi :**
- Faire installer l'application par quelqu'un d'autre (ton ami ?) en suivant **seulement** le
  README, et noter chaque blocage.

**Avancement (2026-10-12) : les trois demandes du propriétaire sont faites**, sur la branche
`etape-10`. Ses arbitrages du jour : une fenêtre à part ; de vrais titres pour la démonstration ;
et la liste du ménage. Trois décisions ([D-106](decisions.md) à [D-108](decisions.md)), le
[cahier de vérification](verification/etape-10.md), et le [README](../README.md) réécrit en guide
d'installation.

- **Le lancement** ([D-106](decisions.md)) : l'icône Pastory (bureau et menu Démarrer) ouvre une
  fenêtre sans barre d'adresse ni fenêtre noire ; fermer la fenêtre arrête Pastory ; un second
  double-clic ramène la fenêtre existante. Essayé en vrai sur la machine du propriétaire, par le
  raccourci lui-même : réponse en 3 à 5 secondes, arrêt 8 secondes après la fermeture.
- **La démonstration** ([D-107](decisions.md)) : « Pastory (démonstration) », dans le menu
  Démarrer, ouvre un portefeuille fictif de 8 positions sur les trois poches, dans un dossier à
  part. Pastory y trouve seul **27 valeurs sur 27** (cotation, type, frais courants, contenu, date
  du PEA), et la diversification y montre d'elle-même les cas délicats : fonds synthétique, source
  de secours, obligations, matières premières.
- **Le ménage** ([D-108](decisions.md)) : maquettes, branches, code de l'ancien nom, anciennes
  données et pytr.

**Ce que la démonstration a trouvé, et qui vaut pour de vrais utilisateurs :** une action
américaine restait sans cours. Cherchée par son nom, elle a aussi une cotation étrangère créée
après l'achat ; la source refuse cette période par une erreur 400, que Pastory prenait pour une
panne de réseau, et il abandonnait la recherche à chaque fois. Corrigé, avec son test.

**La relecture indépendante a rendu dix remarques, toutes traitées**, et chaque défaut de
comportement est gardé par un test. Les deux plus sérieuses tenaient au même angle mort que le
lanceur devait justement couvrir — **savoir si Pastory tourne déjà** : un second pouvait démarrer
si le premier s'était installé sur un port de repli, et rouvrir Pastory dans les secondes qui
suivent sa fermeture lui amenait une fenêtre juste avant qu'il ne s'éteigne. Elle a aussi trouvé
le nom réel du dossier d'un tiers dans le cahier de l'étape : retiré, y compris de l'historique
de la branche, qui n'avait pas été envoyée. Le détail est au [cahier](verification/etape-10.md) §5.

**Ce qui n'a pas pu être mesuré :** la tenue d'une fenêtre réduite **pendant des heures**. Un
navigateur peut endormir une page masquée, qui ne donnerait plus signe de vie ; une précaution est
posée, non vérifiée sur la durée ([D-106](decisions.md)). Le cahier demande l'essai au
propriétaire.

**Ce qui n'a pas pu être essayé sur la machine du propriétaire :** `Installer Pastory.cmd` jusqu'au
bout. Son antivirus bloque le téléchargement des bibliothèques (« invalid peer certificate »), ce
que le fichier explique ; la création des raccourcis, elle, a été essayée par la commande que ce
fichier appelle.

**Reste de l'étape 10 :**
- **l'installation par un tiers**, en suivant le seul README : c'est le vrai test du fichier
  d'installation, et il n'a pas encore eu lieu ;
- **le raccourci pour Mac** ([D-62](decisions.md)) : le lanceur ne dépend pas de Windows, mais rien
  n'a pu être essayé sur un Mac ;
- la **relecture des messages d'erreur** (un fichier qui n'est pas un export, des colonnes
  inattendues, un export partiel) : ceux du dépôt existent depuis l'étape 9, ils n'ont pas été
  repassés un à un ;
- le guide **« écrire un adaptateur pour une autre banque »**.

## Étape 10 bis · Un fichier, un portefeuille ✅
**But :** que deux comptes ne puissent plus se mélanger, et qu'on puisse défaire un dépôt.

**D'où elle vient :** en vérifiant l'étape 10, le propriétaire a déposé l'export d'un proche à
côté du sien. Pastory a affiché la somme des deux comptes, sans rien dire, et rien à l'écran
ne permettait de revenir en arrière. C'était le cumul des exports de l'étape 8 ter, fait pour
qu'un export récent s'ajoute aux précédents.

**Fait (2026-10-13)**, sur la branche `etape-10-bis` ([D-109](decisions.md),
[cahier](verification/etape-10-bis.md)) : chaque fichier du dossier de dépôt est un
portefeuille, et Pastory n'en lit qu'un à la fois. La couverture propose le choix, le nom du
portefeuille ouvert reste affiché, et chacun se renomme et se supprime à l'écran. Un export
plus récent du même compte est reconnu **à ses opérations** et met le portefeuille à jour ; un
export sans opération commune devient un autre portefeuille.

Le propriétaire avait d'abord envisagé un dossier par personne, puis l'a écarté pour cette
idée plus simple, qui est la sienne. Avec un seul portefeuille, **aucun chiffre ni aucun écran
ne change** — relevé sur ses données, nombre par nombre.

**La relecture indépendante a rendu dix remarques, toutes traitées.** La plus instructive : la
règle du dépôt ne voyait que les fichiers déposés **par l'écran**. Un export copié à la main
dans le dossier — geste que Pastory propose lui-même — devenait un second portefeuille du même
compte, et l'on continuait à lire l'ancien. Un portefeuille périmé se dit désormais dès la
couverture.

**Une conséquence à connaître :** l'export d'une autre personne, une fois déposé, est
valorisé comme un autre — ses titres sont donc cherchés en ligne. La lecture sans réseau
reste possible depuis un terminal (`--export`).

**Toi :** suivre le [cahier](verification/etape-10-bis.md) ; et le mois prochain, vérifier que
ton nouvel export **met à jour** ton portefeuille au lieu d'en créer un second.

## Étape 11 · Publication ⏳
**But :** rendre le dépôt public sans risque.

**Claude :**
- Lance `/security-review`.
- Cherche noms, IBAN, numéros de compte et jetons **dans tout l'historique git**, pas seulement
  dans les fichiers actuels.
- Écrit la licence et la page d'accueil du dépôt, avec la mention : **projet indépendant, sans
  lien avec Trade Republic**, qui lit le fichier que la banque fournit à ses clients. Pas de logo
  ni d'identité visuelle de la banque.

**Toi :** relire le README, choisir la licence (elle doit autoriser les forks pour d'autres
banques, D-26), passer le dépôt en public sur GitHub (Settings → Danger Zone → Change visibility).

## ~~Étape 12 · Simulation Monte-Carlo~~ → déplacée dans l'étape 9 bis ([D-97](decisions.md))
