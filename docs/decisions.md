# Journal des décisions

Chaque décision structurante : date, décision, raison, ce qu'elle écarte. Une décision n'est
jamais effacée. Si elle est remplacée, on ajoute une nouvelle entrée qui la cite.

Statuts : **Validée** (arbitrée par le propriétaire) · **Proposée** (en attente de confirmation).

---

### D-01 · 2026-09-17 · Exclure largement les données de git · Validée
**Décision :** le `.gitignore` exclut tous les dossiers `data/` et `data_*/`, et **tous** les
fichiers `*.json`, `*.csv`, `*.pdf`, `*.xlsx`, bases locales, `.env` et fichiers d'identifiants,
où qu'ils soient. Il a été versionné seul, avant tout autre fichier.
**Raison :** un fichier entré dans l'historique git y reste. Les exports contiennent noms, IBAN,
numéros de compte et jetons d'accès.
**Écarte :** une liste fichier par fichier. Contrepartie : un futur fichier JSON légitime (ex.
configuration d'exemple) devra être autorisé explicitement par une exception `!chemin`.

### D-02 · 2026-09-17 · Dépôt GitHub privé · Validée
**Décision :** dépôt créé en privé. Passage en public quand l'application sera prête.
**Raison :** le projet démarre, et la vérification de l'absence de données se fera dans la durée.
**Écarte :** la publication immédiate.

### D-03 · 2026-09-17 · Valeurs fictives dans toute la documentation · Validée
**Décision :** montants, ISIN, identifiants, numéros de compte et noms sont inventés dans la doc,
y compris pour les données du propriétaire. Seuls les noms de champs, les types et les libellés
d'interface sont réels. Les comptages d'événements sont reproduits.
**Écarte :** citer les vraies valeurs du propriétaire.

### D-04 · 2026-09-17 · Notes manuscrites : markdown versionné, PDF hors dépôt · Validée
**Décision :** [notes-initiales.md](notes-initiales.md) est la référence des intentions. Le PDF
reste local.
**Écarte :** versionner le PDF.

### D-05 · 2026-09-17 · Script d'exploration versionné, sans affichage de valeurs · Validée
**Décision :** `scripts/inventaire_structure.py` est gardé. Il lit les données et n'affiche que
des comptages, des noms de champs et des libellés techniques. Les comptes sont anonymisés
(A, B, C). Les textes libres sont réduits à « texte » ou « numérique ».
**Raison :** l'inventaire doit pouvoir être refait par n'importe qui sur son propre export, et
vérifié.
**Écarte :** un script jetable ; un script qui affiche les valeurs.

### D-06 · 2026-09-17 · Le JSON est la source ; le CSV sert seulement à recouper · Proposée
**Décision :** le moteur lira `all_events.json`. Le CSV ne servira qu'à recouper les quantités,
les frais et les taxes.
**Raison :** le CSV omet les versements PEA, les primes et les actions gagnées. Il compte des
transferts internes et une distribution de capital comme des dépôts
([inventaire §8](inventaire-donnees.md#8-le-csv--ce-quil-apporte-ce-quil-déforme)).
**Écarte :** le CSV comme source principale, malgré ses quantités déjà converties en nombres.

### D-07 · 2026-09-17 · Capital net investi global = flux externes uniquement · **Remplacée par D-11**
**Décision :** le capital net investi global et les rendements (TRI, TWRR) ne reposent que sur les
flux qui franchissent la frontière Trade Republic. L'appariement versement PEA ↔ achat ne sert
qu'à **répartir** entre les poches, jamais à calculer le total.
**Raison :** l'observation 7 du propriétaire, confirmée. Et l'appariement n'est pas toujours
possible : chez le tiers, 27 achats PEA sur 41 n'ont pas de versement. Un total qui en dépendrait
serait faux.
**Écarte :** calculer le capital investi à partir des achats ; additionner achats et versements.

### D-08 · 2026-09-17 · Classement par liste explicite de types · Proposée
**Décision :** chaque `eventType` est rangé explicitement dans une famille (externe, revenu,
achat/vente, interne, titres seuls, écarté). Un événement ne compte que si `status = EXECUTED`.
Tout type absent des listes est **inconnu** et affiché à l'utilisateur. Le nombre d'événements
écartés est consultable.
**Raison :** la présence d'un montant ne permet pas de décider. Un plan échoué a un montant, et des
titres reçus n'en ont pas.
**Écarte :** « sans montant = ignorer », « avec montant = compter », et tout classement par défaut.

### D-09 · 2026-09-17 · Champs structurés d'abord ; textes isolés et marqués · Proposée
**Décision :** type, montant, date, compte, statut et ISIN viennent de champs structurés. Ce qui
n'existe qu'en texte (quantité, prix, frais, taxes, poche d'un ordre, nature des événements `null`)
est lu par un module unique, avec un dictionnaire de libellés par langue. Chaque valeur issue d'un
texte est marquée comme telle.
**Raison :** textes en allemand, **et mélange allemand/français dans un même export**.
**Écarte :** chercher des libellés un peu partout dans le code.

### D-10 · 2026-09-17 · Les comptes sont nommés par l'utilisateur · Validée
**Décision :** à l'installation, l'utilisateur associe chaque numéro de compte à un rôle (compte
courant, espèces PEA, ancien compte…). L'application l'aide en montrant les types d'opérations
vus sur chaque compte.
**Raison :** le rôle d'un compte n'est écrit nulle part. Le propriétaire a découvert un troisième
compte dont il ignorait l'existence.
**Écarte :** deviner les rôles automatiquement.

---

*Arbitrages du propriétaire du 2026-09-17. Quand une réponse courte contredisait ses explications,
les explications ont prévalu, à sa demande. Les contradictions résolues sont indiquées.*

### D-11 · 2026-09-17 · Périmètre = les actifs ; les espèces sont ignorées · Validée
**Décision :** l'application suit uniquement les actifs achetés : achat, évolution, revenus,
vente, frais et taxes à l'entrée et à la sortie. Les espèces sont exclues partout, y compris
l'argent en attente sur le compte espèces du PEA. Les types d'événements qui ne concernent que les
espèces (virements, carte, versements et transferts PEA, intérêts sur espèces, primes en espèces,
euro d'activation) sont classés **hors périmètre** : écartés, mais comptés et distincts des types
inconnus.
**Raison :** « ce qui m'intéresse est l'évolution des actifs que j'ai achetés ». Le compte espèces
sert à la vie courante et son évolution est sans intérêt ici.
**Écarte :** D-07 (capital net investi fondé sur les apports externes) ; l'appariement des
versements PEA (Q-09, Q-16 sans objet) ; une poche « Espèces ».
**Contradictions résolues :** Q-03 (a, espèces incluses) → exclues. Q-02 (a, carte = retrait) →
hors périmètre. Q-01 (a) ne s'applique qu'aux revenus des actifs : intérêts sur espèces, primes et
euro d'activation sont hors périmètre.
**Conséquence :** le problème des 27 achats PEA sans versement chez le tiers disparaît. Seuls
comptent les achats eux-mêmes.

### D-12 · 2026-09-17 · Capital net investi = net de frais et de taxes, réduit au prorata des ventes · Validée
**Décision :** un achat ajoute son **montant brut** (montant payé − frais − taxes) au capital net
investi de l'actif. Une vente le réduit au prorata de la fraction des parts vendues. Frais et taxes
sont suivis dans deux catégories séparées.
**Raison :** Q-04, avec l'exemple « je mets 201 €, −1 € de frais, la valeur passe à 200 ».
Permet de comparer avec ce qui est réellement placé.
**Écarte :** inclure frais et taxes dans le coût.
**Contradictions résolues :** Q-05 (a) proposait un PMP « frais inclus » et Q-08 (a) une taxe
« incluse dans le prix de revient » → frais et taxes exclus, conformément à Q-04. La séparation
frais / taxes de Q-08 est conservée.

### D-13 · 2026-09-17 · Prix de revient = prix moyen pondéré, hors frais et taxes · Validée
**Décision :** PRU = capital net investi / quantité détenue. Il change à l'achat, pas à la vente.
**Raison :** Q-05 (a), rendu cohérent avec D-12.
**Écarte :** FIFO. **Limite connue :** le prix de revient fiscal français inclut les frais d'achat.
Il faudra un calcul séparé si l'impôt est un jour estimé.

### D-14 · 2026-09-17 · Dividendes = rendement ; distribution de capital = baisse du capital investi · Validée
**Décision :** un dividende est un revenu de l'actif (brut, taxe, net conservés). Une distribution
de capital réduit le capital net investi de l'actif.
**Raison :** Q-01 (a), Q-07 (b).
**Écarte :** traiter les dividendes comme apports ; la distribution de capital comme revenu.

### D-15 · 2026-09-17 · Titres reçus sans achat : prix = cours du jour d'apparition · Validée
**Décision :** action gagnée, actions gratuites, titres transférés : le prix d'achat retenu est le
cours de l'actif le jour où les titres apparaissent. La valeur est marquée comme déduite.
**Raison :** Q-10. L'origine importe peu, il faut un point de départ.
**Écarte :** prix d'achat nul ; exclusion de ces titres.
**Limite connue :** des titres entrés **sans aucun événement** (transfert de PEA) sont invisibles dans
la timeline. Ils ne pourront être détectés qu'en comparant avec les positions réelles du compte
(voir [feuille-de-route.md](feuille-de-route.md)).

### D-16 · 2026-09-17 · Poche crypto déduite du code `XF` · Validée
**Décision :** un actif dont le code commence par `XF` est rangé en crypto, avec mention « poche
déduite » et correction possible par l'utilisateur.
**Raison :** Q-12 (a).

### D-17 · 2026-09-17 · Coûts implicites estimés · Validée
**Décision :** le TER des ETF est cherché dans une base de données d'actifs. Le spread est estimé
avec une valeur par défaut par type d'actif. Les deux sont affichés comme estimations, séparés des
frais réels, avec leur source.
**Raison :** Q-13.
**Écarte :** simple mention qualitative. **À faire :** trouver la base TER et documenter les valeurs
par défaut.

### D-18 · 2026-09-17 · Cours de marché : outil Python gratuit, choisi après comparatif · Validée
**Décision :** comparer les sources gratuites accessibles en Python (ex. Yahoo Finance) sur des
critères écrits : couverture des ISIN européens et des cryptos, historique, fiabilité, limites
d'usage. Puis retenir la meilleure.
**Raison :** Q-14.

### D-19 · 2026-09-17 · Libellés allemands et français, extensible · Validée
**Décision :** le dictionnaire de libellés couvre l'allemand et le français. Un libellé non reconnu
déclenche une alerte visible.
**Raison :** Q-15 (a).

### D-20 · 2026-09-17 · La maquette du PDF n'est pas un modèle · Validée
**Décision :** la maquette est un premier jet. Disposition, filtres, légendes, graphiques et choix
des chiffres clés ne sont pas contraignants. Le contenu voulu est celui du texte des notes et des
décisions. L'interface sera conçue à neuf.
**Raison :** précision du propriétaire.

---

*Arbitrages du propriétaire du 2026-09-17 (second lot).*

### D-21 · 2026-09-17 · La performance ignore frais et taxes, analysés à part · Validée
**Décision :** gain, TRI et TWRR se calculent sur les **montants bruts** (quantité × prix). Frais et
taxes d'entrée et de sortie n'entrent pas dans la performance. Ils sont analysés à part, dans leur
propre vue.
**Raison :** Q-23. « Si on met 201 € avec 1 € de frais, seuls 200 € entrent dans le coffre. Le
−1 € sera examiné indépendamment. » La performance décrit l'évolution de ce qui est dans le coffre.
**Écarte :** des rendements nets de frais dans la synthèse (la recommandation (a) de Q-23).
**Complétée par :** D-29 (dividendes bruts).

### D-22 · 2026-09-17 · Trois chiffres clés : gain en €, TRI, TWRR · Validée
**Décision :** la synthèse montre trois chiffres clés, recalculés selon les filtres (période,
poches) :
1. **Gain en €** : combien les actifs ont rapporté. C'est le chiffre principal, le seul parlant pour
   un portefeuille jeune.
2. **TRI** et 3. **TWRR** : précisions, utiles quand le portefeuille a de l'âge.

L'interface pourra signaler que TRI et TWRR sont peu significatifs sur une courte durée.
**Raison :** Q-24.
**Écarte :** le pourcentage « gain total / capital net investi » retenu en Q-06. **Contradiction
résolue :** « gain relatif… combien j'ai gagné en euros » → montant en €.

### D-23 · 2026-09-17 · Deux lectures : synthèse brute et valeur réelle · Validée
**Décision :**
- La **synthèse** montre le cœur des investissements, sans frais ni taxes. Elle est volontairement
  flatteuse.
- Une **vue « valeur réelle »** montre ce qu'on récupérerait en vendant tout aujourd'hui : capital
  brut − frais de vente estimés − impôts estimés sur les plus-values selon la poche.

**Raison :** Q-24.
**Écarte :** une seule vue qui mélangerait les deux.
**Limite :** l'impôt est une **estimation** (pas de déclaration, D-26). Les règles fiscales par poche
sont à documenter avec leur source (feuille de route, étape 6). Le prix de revient fiscal inclut
les frais d'achat (voir D-13).

### D-24 · 2026-09-17 · Le projet reste dans OneDrive · Validée
**Décision :** pas de déplacement. **Raison :** Q-17 ; sauvegarde automatique imposée par la
machine, aucun conflit constaté. **À surveiller :** en cas d'erreur git inexpliquée, penser à
OneDrive en premier.

### D-25 · 2026-09-17 · Identifiants : choix de l'utilisateur, jamais de PIN en clair · Validée
**Décision :** le passage du PIN en argument de commande est supprimé. À l'installation,
l'utilisateur choisit, avec une explication des risques :
1. rien d'enregistré, le PIN est redemandé à chaque fois (le plus sûr) ;
2. PIN dans le gestionnaire d'identifiants du système (keyring) ;
3. seulement la session pytr, si elle existe.

**Jamais** de PIN en clair dans le dossier du projet, dans un `.env` ou dans OneDrive.
**Préalable :** vérifier ce que pytr stocke exactement (session, PIN éventuel, durée de validité,
emplacement du fichier). Si ce fichier est dans un dossier synchronisé, le signaler.
**Quand :** étape 10 (installation). **Raison :** Q-18.

### D-26 · 2026-09-17 · Périmètre fonctionnel et ouverture aux autres banques · Validée
**Décision :**
- Euro uniquement pour l'instant.
- Lecture seule : on visualise, on ne passe aucun ordre.
- Aucun conseil d'investissement. Aucune production de déclaration fiscale.
- Autres banques **non prises en charge**, mais **l'application doit pouvoir changer de source** :
  - le moteur ne lit qu'un **format pivot** documenté (opérations sur actifs) ;
  - l'export Trade Republic / pytr est un **adaptateur** parmi d'autres possibles ;
  - quelqu'un qui forke le projet pour une autre banque n'écrit qu'un nouvel adaptateur produisant
    ce format.

**Raison :** Q-19. « La locomotive avance, et on peut changer de wagon (banque) tant que les données
sont bien formatées. »
**Écarte :** un moteur qui lirait directement les champs Trade Republic.

### D-27 · 2026-09-17 · Monte-Carlo : fonctionnalité indépendante, reportée · Validée
**Décision :** développée séparément, après le cœur de l'application. Rien n'en dépend.
**Raison :** Q-20.

### D-28 · 2026-09-17 · Données de marché et de diversification : gratuites et fiables · Validée
**Décision :** comme les cours (D-18), les compositions géographiques et sectorielles viennent de
sources **gratuites**, choisies sur des critères de **fiabilité** écrits, avec la date des données
affichée.
**Raison :** Q-22.

### D-29 · 2026-09-17 · Dividendes bruts dans la performance · Validée
**Décision :** le gain, le TRI et le TWRR comptent le dividende **brut**. La retenue d'impôt va dans
les coûts.
**Raison :** Q-25, cohérent avec D-21.
**Écarte :** le dividende net dans la performance.

### D-30 · 2026-09-17 · Le spread est un coût d'entrée et de sortie · Validée
**Décision :** le spread estimé (D-17) est compté à chaque achat et à chaque vente, et dans le coût
de sortie de la valeur réelle. Seuls les frais courants des fonds (TER) sont des coûts de
détention.
**Raison :** correction du propriétaire sur la proposition de Q-21.
**Écarte :** le spread classé en coût courant.

---

*Choix techniques de l'étape 1, arbitrés par le propriétaire le 2026-09-17. Chaque option lui a
été présentée avec ses avantages et ses inconvénients ; les huit décisions suivent ses réponses.*

### D-31 · 2026-09-17 · Interface : Dash · Validée
**Décision :** l'interface est écrite avec Dash, qui tourne en local et s'ouvre dans le navigateur.
**Raison :** on y écrit du vrai HTML et du vrai CSS, donc le style éditorial voulu (crème, sauge,
terracotta) est obtenu tel quel, et le prototype de l'étape 8 devient directement l'écran final.
Les filtres (période, poches) fonctionnent sans écrire de JavaScript, et les graphiques comme les
polices sont livrés avec l'application, qui s'ouvre donc **sans réseau**.
**Écarte :** Streamlit, dont le style et la mise en page sont bridés — or l'étape 8 est celle où
l'avis du propriétaire compte le plus, et l'outil ne doit pas lui dire non. Écarte aussi un site
fait main (FastAPI + HTML), qui obligerait à écrire toute l'interactivité, donc le plus de code et
de bugs possibles.

### D-32 · 2026-09-17 · Installation et dépendances : uv · Validée
**Décision :** le projet est décrit par un `pyproject.toml` et un `uv.lock`. Installation et
lancement : `uv sync` puis `uv run`.
**Raison :** critère du propriétaire, « un autre utilisateur pourra-t-il l'installer en quelques
commandes ? ». uv installe Python **et** les bibliothèques, et verrouille les versions exactes :
deux utilisateurs ont rigoureusement le même environnement, ce qui rend les écarts de chiffres
reproductibles.
**Écarte :** `pip` + `venv` (3 à 4 commandes, versions moins bien verrouillées, pièges Windows).
**Contrepartie assumée :** outil récent ; l'installation de uv elle-même est une étape du guide
(étape 10).

### D-33 · 2026-09-17 · Calculs en Python simple, montants en `Decimal` · Validée
**Décision :** le moteur traite les opérations **une par une**, dans l'ordre, avec des structures
de données Python ordinaires. Les montants et les quantités sont des `Decimal`, jamais des nombres
à virgule flottante. `pandas` reste utilisé, mais **seulement** pour les séries de cours et les
tableaux d'affichage.
**Raison :** le propriétaire vérifie les chiffres à la main ; une règle doit se relire ligne à
ligne et se refaire sur papier (cahiers de vérification). `Decimal` évite en prime les écarts de
centimes.
**Écarte :** des calculs vectoriels `pandas` sur les montants, plus courts à écrire mais
impossibles à suivre pas à pas.

### D-34 · 2026-09-17 · Vocabulaire métier en français · Validée
**Décision :** les noms de champs, de fonctions et de variables qui portent une notion métier sont
en français et **identiques au [glossaire](glossaire.md)** : `capital_net_investi`,
`prix_unitaire`, `poche`, `montant_brut`. Les termes purement techniques restent en anglais.
**Raison :** le propriétaire doit pouvoir ouvrir une formule et y reconnaître la définition qu'il
a validée.
**Écarte :** un code entièrement en anglais, plus habituel et plus accueillant pour un
contributeur extérieur, mais dont les noms ne renverraient plus au glossaire.

### D-35 · 2026-09-17 · Format pivot figé · Validée
**Décision :** le format pivot est décrit dans [format-pivot.md](format-pivot.md) et fait foi.
Points structurants : **tous les nombres sont positifs**, le sens étant porté par le `type` ; la
liste des types est **fermée** (`achat`, `vente`, `dividende`, `distribution_capital`,
`titres_recus`) ; chaque valeur porte sa **provenance** ; des **contrôles de cohérence**
(`montant_brut = quantité × prix`, `montant réglé = brut ± frais ± taxes`) s'appliquent à chaque
ligne. La tolérance de ces contrôles tient compte des deux arrondis en jeu : un centime pour le
montant, plus un demi-centime par part pour le prix affiché, lui aussi arrondi.
**Raison :** c'est le contrat entre l'adaptateur et le moteur (D-26). Écrit avant le code, il peut
être relu par le propriétaire.
**Écarte :** conserver le signe des montants de Trade Republic ; forcer un cas nouveau dans un
type existant. Un cas hors liste est **inconnu**, affiché, et n'étend le format que par une
nouvelle décision.
**Ajout à la traçabilité :** une cinquième provenance, `a_completer`, pour un prix qui attend les
cours de l'étape 4 (D-15). Une ligne incomplète est visible mais ne compte dans aucun total.

### D-36 · 2026-09-17 · Instant en UTC, jour en heure de Paris · Validée
**Décision :** chaque ligne pivot conserve l'horodatage exact tel que fourni (UTC) **et** la date
calendaire correspondante en heure de Paris. Tous les regroupements par jour et les
rapprochements avec les cours utilisent cette seconde date.
**Raison :** sans cela, une opération passée en soirée est comptée le lendemain, et les chiffres
ne correspondent plus à ce que le propriétaire lit dans son application.
**Écarte :** ne garder que l'UTC ; ne garder que la date locale (on perdrait l'ordre exact des
opérations d'une même journée). Écarte aussi un horodatage **sans fuseau** (comme la colonne
`Date` du CSV) : il serait interprété dans le fuseau de la machine, et deux ordinateurs ne
donneraient pas le même jour à partir du même export. L'application le refuse explicitement.

### D-37 · 2026-09-17 · Fichiers personnels hors du dossier synchronisé · Validée
**Décision :** exports, cache de cours, configuration de l'utilisateur, correspondances ISIN et
résultats `*.local.md` sont écrits dans un dossier **local, non synchronisé** (sous
`%LOCALAPPDATA%` sur Windows), dont l'emplacement est affiché par l'application. Le dépôt ne
contient que du code et de la documentation.
**Raison :** le projet vit dans OneDrive (D-24). Un cache réécrit en permanence dans un dossier
synchronisé provoque des conflits et ralentit la machine.
**Écarte :** un dossier `data/` dans le projet comme emplacement de travail. Il reste toléré pour
un export déposé à la main, et reste exclu de git (D-01).

### D-38 · 2026-09-17 · Configuration en TOML, tests avec `pytest` sur données fictives · Validée
**Décision :** les fichiers de configuration (noms des comptes, corrections de poche,
correspondances ISIN, taux fiscaux et spreads datés) sont en **TOML**. Un exemple fictif est
versionné. Les tests sont écrits avec `pytest` et n'utilisent **que** des données fictives.
**Raison :** le TOML se lit et se corrige sans être développeur, Python le lit nativement, et il
ne se heurte pas à l'exclusion globale des `*.json` du `.gitignore` (D-01), qui aurait obligé à
une exception par fichier.
**Écarte :** la configuration en JSON ou en YAML.
