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
puis la couche `dashboard_tr/donnees_externes/`, trois commandes (`actifs`, `cours`,
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
dans `dashboard positions` (« Valeur des actifs au … » et « Les trois chiffres clés »), quatre
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
(`dashboard_tr/parametres/`), une source de TER (`donnees_externes/xetra.py`), trois blocs de plus
dans `dashboard positions`, deux CSV de plus, et le [cahier de vérification](verification/etape-6.md).

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
`dashboard positions`, trois CSV de plus, deux commandes (`composition`, `oublier-composition`) et
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

## Étape 8 · Conception de l'interface 🔜
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
    techniques : « non couvert », « non attribué », « non transparisé », « synthétique », « minoré »
    doivent s'expliquer là où ils s'affichent, pour un lecteur qui découvre l'application ;
  - **deux règles de pays cohabitent** dans la répartition géographique ([D-66](decisions.md)) : la
    conception doit trouver comment le dire sans alourdir l'écran.

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
