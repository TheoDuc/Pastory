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

### D-06 · 2026-09-17 · Le JSON est la source ; le CSV sert seulement à recouper · Validée
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

### D-08 · 2026-09-17 · Classement par liste explicite de types · Validée
**Décision :** chaque `eventType` est rangé explicitement dans une famille (externe, revenu,
achat/vente, interne, titres seuls, écarté). Un événement ne compte que si `status = EXECUTED`.
Tout type absent des listes est **inconnu** et affiché à l'utilisateur. Le nombre d'événements
écartés est consultable.
**Raison :** la présence d'un montant ne permet pas de décider. Un plan échoué a un montant, et des
titres reçus n'en ont pas.
**Écarte :** « sans montant = ignorer », « avec montant = compter », et tout classement par défaut.

### D-09 · 2026-09-17 · Champs structurés d'abord ; textes isolés et marqués · Validée
**Décision :** type, montant, date, compte, statut et ISIN viennent de champs structurés. Ce qui
n'existe qu'en texte (quantité, prix, frais, taxes, poche d'un ordre, nature des événements `null`)
est lu par un module unique, avec un dictionnaire de libellés par langue. Chaque valeur issue d'un
texte est marquée comme telle.
**Raison :** textes en allemand, **et mélange allemand/français dans un même export**.
**Écarte :** chercher des libellés un peu partout dans le code.

### D-10 · 2026-09-17 · Les comptes sont nommés par l'utilisateur · **Remplacée par D-81**
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

### D-16 · 2026-09-17 · Poche crypto déduite du code `XF` · **Remplacée par D-81**
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
**Amendée par [D-99](#d-99) (2026-10-09) :** à l'écran, la **valeur des actifs** devient le point
d'entrée de la synthèse ; le gain reste le premier des trois chiffres clés, en seconde ligne.

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

### D-25 · 2026-09-17 · Identifiants : choix de l'utilisateur, jamais de PIN en clair · **Remplacée par D-81**
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

---

*Étape 2 (lecture des données). Les quatre premières décisions sont des arbitrages du
propriétaire du 2026-09-18 ; les trois précédentes (D-06, D-08, D-09), proposées à l'étape 0,
passent en « Validée » parce que l'adaptateur les met en œuvre telles quelles.*

### D-39 · 2026-09-18 · Tolérance symétrique des contrôles de cohérence · Validée
**Décision :** l'écart acceptable entre `montant_brut` et `quantité × prix` vaut

```
1 centime  +  quantité × (½ dernier chiffre du prix affiché)
           +  prix × (½ dernier chiffre de la quantité affichée)
```

Le nombre de décimales n'est pas supposé : il est **lu sur la valeur elle-même**, qui conserve
l'écriture exacte du libellé dont elle vient. Remplace la formule de [D-35](#d-35) et du §5 de
[format-pivot.md](format-pivot.md).

**Raison :** l'ancienne formule ne tenait compte que de l'arrondi du **prix**. Or un achat de
crypto a une quantité minuscule écrite avec six décimales et un prix de plusieurs dizaines de
milliers d'euros : la moitié du dernier chiffre de la quantité pèse alors bien plus qu'un
centime. Tous les achats de crypto étaient signalés comme anormaux, à tort — et un rapport qui
crie au loup à chaque ligne ne sert plus à rien. L'ancienne formule supposait aussi un prix
affiché à deux décimales, alors qu'on en observe à deux, trois et quatre.
**Écarte :** garder la formule et apprendre à ignorer les fausses alertes ; une tolérance
forfaitaire en pourcentage, qui laisserait passer de vraies erreurs sur les gros montants.
**Vérifié :** zéro anomalie sur les 80 opérations des deux exports disponibles.

### D-40 · 2026-09-18 · La poche n'est jamais devinée · Validée
**Décision :** la poche se reconstitue dans cet ordre — poche déclarée par l'utilisateur pour
cet actif, puis code commençant par `XF` (crypto, D-16), puis rôle du compte espèces de
l'opération (D-10). Si aucune règle ne répond, **l'opération n'est pas produite** : elle est
signalée, et `exporter-pivot` s'arrête **sans écrire de fichier** en disant quoi déclarer.
**Raison :** un classement par défaut mettrait des chiffres faux dans la bonne colonne, ce qui
est pire que pas de chiffre du tout : rien ne signalerait l'erreur. Cohérent avec D-08.
**Écarte :** supposer « CTO » pour un compte non nommé.
**Contrepartie assumée :** `pastory comptes` est une étape obligatoire au premier lancement.
Le libellé « Portfolio » de l'écran ne sert qu'à **contrôler** la poche, jamais à la décider :
c'est un texte (D-09), et un désaccord avec le compte part au rapport.
**Précisions ajoutées après relecture :** l'assistant réécrit le fichier entier, donc il y
recopie **tout** ce que l'utilisateur y avait mis — rôles, comptes absents de cet export-ci et
corrections de poche. Sans cela, le relancer effacerait les poches déclarées à la main et des
opérations disparaîtraient sans message. Et avec `--export`, il **n'écrit rien** : les numéros
de compte d'un export qui n'est pas le sien appartiennent à quelqu'un d'autre (règle 2 de
CLAUDE.md).

### D-41 · 2026-09-18 · `rafraichir` ne manipule aucun identifiant · **Remplacée par D-81**
**Décision :** `pastory rafraichir` appelle pytr **sans** `-n`, **sans** `-p` et **sans**
`--store_credentials`. C'est pytr qui demande lui-même le numéro et le PIN, la saisie du PIN
étant masquée. Rien n'est enregistré.
**Raison :** c'est le plus sûr des trois modes de [D-25](#d-25), et il se trouve qu'il est
aussi le plus simple : le PIN ne transite jamais par cette application. Il n'apparaît donc ni
dans la ligne de commande — visible des autres programmes de la machine — ni dans l'historique
du terminal.
**Écarte :** reprendre le `-p` du premier script (supprimé), et reporter toute la commande à
l'étape 10.
**Reste à l'étape 10 :** les deux autres modes (gestionnaire d'identifiants du système,
session pytr seule) et le choix à l'installation.

### D-42 · 2026-09-18 · Recoupement systématique avec le CSV · **Remplacée par D-81**
**Décision :** à chaque lecture, la quantité, les frais et les taxes lus dans les textes sont
comparés aux colonnes du CSV. Tout désaccord part au rapport. Le CSV ne fait **jamais**
autorité (D-06) : un désaccord est une invitation à aller vérifier, pas une correction.
**Raison :** ces trois valeurs n'existent qu'en texte allemand, et le CSV les donne en nombres
déjà convertis. C'est un second avis indépendant sur la partie la plus fragile de la lecture —
et c'est précisément ce qui aurait attrapé tout seul le piège du séparateur décimal
(inventaire §11).
**Écarte :** s'en remettre à la seule relecture humaine du CSV pivot.
**Limite connue :** le CSV omet les actions gagnées et range les distributions de capital
parmi les « Dépôt » (inventaire §8). Ces absences-là sont attendues et ne déclenchent pas
d'alerte. Sa colonne `Date` ne portant aucun fuseau, elle sert à **rapprocher** une ligne d'une
opération, jamais à décider d'un jour (D-36).

---

### D-43 · 2026-09-18 · L'euro d'activation du PEA reste dans le capital investi · Validée
**Décision :** l'euro versé par Trade Republic à l'ouverture d'un PEA est compté comme investi
dès lors qu'il a servi à acheter des parts. Le capital net investi de l'actif concerné vaut donc
le prix de l'achat entier, et non le montant prélevé sur le compte courant.
**Raison :** arbitrage du propriétaire, après vérification sur ses données (un achat en PEA dont
le versement associé était inférieur d'un euro). C'est cohérent avec [D-11](#d-11) — « peu
importe d'où vient l'argent » — et avec le fait que cet euro est bien dans l'actif : il en suit
l'évolution comme le reste.
**Écarte :** retrancher l'euro du capital investi, ce qui obligerait à suivre l'origine de
chaque euro, précisément ce que le périmètre exclut.
**Conséquence assumée :** le capital investi total est majoré d'un euro, **une seule fois** dans
la vie du PEA. C'est sans effet sur la valeur des actifs et sur leur évolution ; seul le rapport
« ce que j'ai mis de ma poche » s'en trouve flatté d'un euro.
**Vérifié :** le solde reconstitué du compte espèces du PEA retombe exactement à zéro, ce qui
confirme au passage qu'aucune opération PEA ne manque dans l'export.

---

*Étape 3 (moteur de positions). Les trois décisions suivantes répondent à quatre arbitrages
rendus par le propriétaire le 2026-09-20, avant l'écriture du code.*

### D-44 · 2026-09-20 · Le moteur rejoue les opérations et tient un journal vérifiable · Validée
**Décision :** le moteur traite les opérations **une par une**, dans l'ordre de leur horodatage
(puis de leur identifiant pour départager deux opérations simultanées), et conserve **une ligne
par opération** : l'état d'avant, ce que l'opération ajoute ou retire, l'état d'après. Le capital
net investi est **arrondi au centime après chaque opération**, et une vente retire
`capital × quantité vendue / quantité détenue` plutôt que de multiplier le capital par un
complément. La clé d'une position est le couple **(actif, poche)**, jamais l'actif seul.
**Raison :** le propriétaire ne code pas, il vérifie les chiffres. Un journal se lit comme un
relevé bancaire et répond à « d'où sort ce prix de revient ? » sans ouvrir le code. L'arrondi à
chaque pas est ce qu'une main ferait ; sans lui, une vente au prorata laisse une traînée de
décimales que personne ne peut refaire. Écrire le retrait plutôt que le reste garantit en prime
que les deux morceaux retombent exactement sur le capital d'avant, sans centime perdu.
Le couple (actif, poche) est nécessaire parce qu'un même ETF peut être détenu en PEA **et** en
CTO, avec deux prix de revient et deux fiscalités différents.
**Écarte :** un moteur qui ne produirait que l'état final ; un arrondi unique à la fin ; l'ordre
du fichier d'export comme ordre de traitement.
**Conséquence assumée :** le prix de revient est arrêté à six décimales, donc
`prix de revient × quantité` peut s'écarter du capital investi de quelques centièmes de centime.
**C'est le capital investi qui fait foi.**

### D-45 · 2026-09-20 · Ce que fait le moteur devant une histoire incomplète · Validée
**Décision :** trois situations où l'arithmétique n'a plus de sens, traitées explicitement et
jamais en silence. Chacune produit un **signalement** visible dans le rapport et dans l'interface.

| Situation | Ce que fait le moteur |
|---|---|
| Des parts entrent **sans prix connu** ([D-15](#d-15)) | les parts sont comptées, leur montant n'entre dans aucun total, et le **prix de revient de l'actif est affiché « à compléter »** au lieu d'un nombre |
| Une vente porte sur **plus de parts** que le moteur n'en a comptées | la quantité tombe à 0 — jamais négative — le capital investi tombe à 0, et l'actif est marqué « historique incomplet » |
| Une **distribution de capital dépasse** le capital investi ([D-14](#d-14)) | le capital s'arrête à zéro, l'excédent est signalé, et l'actif est marqué « historique incomplet » |

Dans les trois cas, **le prix de revient de l'actif n'est plus affiché** : le capital investi
ne décrit plus ce qui a réellement été mis dedans, donc la division ne veut plus rien dire.

**Raison :** arbitrages du propriétaire du 2026-09-20. Le fil commun : **ne jamais afficher un
chiffre qui n'a pas de sens, et ne jamais le corriger sans le dire.** Le cas du prix de revient
est le plus insidieux : 200 € de capital connu divisés par 13 parts dont 3 sont entrées sans
prix donnent 15,38 €, un prix de revient faussement bas et parfaitement crédible — rien, à
l'écran, ne dirait qu'il est faux. Le laisser vide oblige à se poser la question. Une quantité
négative, elle, polluerait tous les totaux de la poche. Et une distribution ne peut pas rendre
plus que ce qui a été mis : au-delà, c'est un gain, pas un remboursement.
**Écarte :** afficher le prix de revient dilué ; laisser la quantité devenir négative ; faire
disparaître l'actif des totaux ; appliquer la formule du glossaire à la lettre jusqu'au capital
négatif.
**Limite connue, et c'est le sujet de D-46 :** une vente au-delà du stock est le **symptôme** de
titres entrés sans événement. Le moteur seul ne peut pas les retrouver.

### D-46 · 2026-09-20 · Les positions réelles entrent dans le pivot ; la quantité contrôle, le PRU informe · **Remplacée par D-81**
**Décision :**
- le format pivot reçoit un **second contrat**, la `PositionReelle` : ce que la banque dit
  détenir aujourd'hui (actif, quantité, nom, prix de revient de la banque). Décrit au
  [§9 de format-pivot.md](format-pivot.md). Le moteur ne lit aucun fichier de banque
  ([D-26](#d-26)) ;
- **la quantité est un contrôle** : tout écart est signalé, et les quantités du moteur sont
  additionnées toutes poches confondues, la banque ne listant que des ISIN ;
- **le prix de revient de la banque est une information** : affiché à côté du nôtre, étiqueté,
  il ne déclenche jamais d'alerte ;
- la récupération est une **commande à part**, `pastory positions-reelles`.

Deux précautions, ajoutées après la relecture indépendante de l'étape :

- **avec `--au`, aucun rapprochement.** La banque ne sait montrer que son portefeuille
  d'aujourd'hui ; le comparer à des chiffres arrêtés à une date passée signalerait à tort
  tout ce qui a bougé depuis ;
- **un fichier dont des lignes n'ont pas pu être lues ne permet pas de conclure.** Un actif
  qui s'y trouvait ressortirait « absent de la banque », exactement le faux diagnostic que
  le comptage des lignes illisibles sert à éviter. Le rapport le dit avant le tableau.

**Raison :** c'est le contrôle le plus fort du projet — il ne dépend d'aucune lecture de texte,
d'aucune déduction et d'aucune règle — et **le seul capable de révéler les titres entrés sans
aucun événement**, limite connue de [D-15](#d-15). Le prix de revient, lui, n'est pas
comparable : on ignore si Trade Republic y inclut les frais d'achat, que [D-13](#d-13) exclut
explicitement. En faire un contrôle déclencherait une alerte sur presque chaque actif, à tort —
et un rapport qui crie au loup partout ne sert plus à rien ([D-39](#d-39)).
La commande séparée découle de [D-41](#d-41) : comme rien n'est enregistré sur la machine,
chaque appel à pytr redemande le numéro, le PIN et la confirmation dans l'application. Réunir
les deux récupérations obligerait à le faire **deux fois à chaque rafraîchissement**.
**Écarte :** comparer les prix de revient ; ignorer celui de la banque ; intégrer la
récupération à `rafraichir`.
**Précision technique :** pytr est appelé **sans** `--decimal-localization`, donc les nombres
arrivent à point décimal. La convention est imposée à la source plutôt que devinée à la lecture,
et une écriture qui ne la respecte pas est refusée — c'est exactement le piège qui a coûté le
plus cher à l'étape 2 ([inventaire §11.1](inventaire-donnees.md)).

---

### D-47 · 2026-09-21 · Une poche que la photo ne couvre pas n'est pas un désaccord · **Remplacée par D-81**
**Décision :** si **aucun** actif d'une poche n'apparaît dans le portefeuille réel donné par la
banque, cette poche est déclarée **non couverte** : elle fait l'objet d'**un seul** signalement,
et ses actifs sortent en `hors périmètre`, sans alerte individuelle. Leur quantité reste
affichée — ils sont bien détenus, ils n'ont simplement pas pu être confrontés.

**Raison :** constaté par le propriétaire sur ses vraies données dès le premier essai. `pytr`
ne demande les positions que d'**un seul** compte-titres — le `securitiesAccountNumber` unique
renvoyé par `/api/v2/auth/account`, voir `compact_portfolio` dans `pytr/api.py`. Trade Republic
logeant le PEA dans un second compte-titres, aucune de ses lignes ne remonte, et **chaque actif
du PEA ressortait « absent de la banque » à chaque lancement**. Ce n'est pas N désaccords, c'est
un fait, et un rapport qui crie au loup partout ne sert plus à rien — c'est le même raisonnement
que [D-39](#d-39).

**Comment la couverture est jugée :** sur les actifs **exclusifs** à la poche. La photo ne dit
pas dans quelle enveloppe un titre est détenu ; un ISIN présent à la fois en PEA et en CTO ne
prouve donc la couverture ni de l'un ni de l'autre. Quand une poche est déclarée non couverte,
ses parts sont **retirées de la comparaison** des actifs partagés : sans cela, un ETF détenu dans
les deux poches verrait ses parts PEA s'ajouter à ses parts CTO et produirait un écart de toutes
pièces.

**Trois garde-fous**, pour ne pas étouffer une vraie alerte :
- il faut qu'au moins un actif soit confirmé ailleurs. Une photo qui ne confirme **rien** n'est
  pas partielle, elle est inutilisable : aucune poche n'est alors mise de côté ;
- une poche sans aucun actif exclusif n'est **jamais** déclarée non couverte : on ne peut rien en
  dire, et l'écart s'affiche tel quel plutôt que d'être masqué sans preuve ;
- la règle ne dit pas *pourquoi* la poche est absente. Une poche ne contenant qu'un seul actif,
  réellement vendu hors de l'export, entre dans ce cas sans qu'on puisse l'en distinguer. Le
  rapport donne donc toujours le nombre d'actifs concernés.

**Écarte :** garder une alerte par actif — le propriétaire apprendrait à ne plus lire ce bloc et
raterait la vraie alerte le jour venu ; refuser tout rapprochement dès qu'une poche manque, ce
qui ferait perdre le contrôle sur le CTO et la crypto, qui fonctionnent parfaitement.
**Conséquence :** `Rapprochement` distingue désormais **`tout_concorde`** (tout ce qui a pu être
comparé concorde) de **`complet`** (tout a pu être comparé). Un « rien à signaler » sur un
rapprochement incomplet serait une fausse impression de contrôle.
**Reste ouvert :** [Q-26](questions-ouvertes.md) — faut-il aller chercher ce second compte-titres
pour que le PEA soit rapproché lui aussi ?

### D-48 · 2026-09-26 · Le cours de référence est celui du marché principal, en euros · Validée ; la cotation est trouvée et contrôlée par le prix payé depuis D-85, Francfort pour une action américaine (D-88)
**Décision :** le cours d'un actif est celui de sa **place principale cotant en euros** — Xetra
pour un ETF ou une action allemande, Euronext Paris pour une française, et ainsi de suite. La
**devise attendue est déclarée** dans la correspondance ISIN → ticker, et un cours dont la devise
ne correspond pas est **refusé et signalé**, jamais converti ni utilisé.

**Raison :** Q-27 (a). Le comparatif ([sources-de-cours.md §4](sources-de-cours.md)) a trouvé un
ISIN pour lequel la recherche automatique renvoie la cotation **londonienne en dollars** d'un ETF
qui cote aussi à Xetra en euros. Sans vérification de la devise, cet actif aurait été valorisé en
dollars sous une étiquette « € » — un chiffre crédible et faux, ce que [D-45](#d-45) interdit.
Le marché principal est en outre vérifiable dans n'importe quel journal et disponible en
historique quotidien profond.

**Ce que ça écarte :** la LS Exchange comme référence — l'ancienne place de Trade Republic, encore
interrogeable mais qui n'exécute plus ses ordres depuis juillet 2026 et dont le volume s'est
effondré ; et toute conversion de devise, qui ajouterait une source d'erreur pour un besoin que ce
portefeuille n'a pas.

**Conséquence à assumer devant l'utilisateur :** la valeur affichée **ne sera pas** au centime
près celle de l'application Trade Republic. Deux places ne cotent jamais exactement pareil au même
instant, et Trade Republic exécute désormais lui-même. L'interface doit le dire, et **la place et
la source de chaque cours doivent être visibles**.

**Cas particulier :** la correspondance ISIN → ticker étant un fichier relu et corrigeable par
l'utilisateur, un actif peut y recevoir une autre place — c'est un choix explicite de sa part,
ligne par ligne, pas un comportement automatique.

### D-49 · 2026-09-26 · pytr reste l'unique porte d'entrée, et aucun cours ne passe par Trade Republic · Validée
**Décision :** le projet continue d'utiliser `pytr` pour l'export d'événements, en connaissance de
la clause ci-dessous, et **aucune source de cours ne passe par Trade Republic** — ni le point
d'accès `ticker`/`aggregateHistory` de pytr, ni la LS Exchange comme source de production.

**Raison :** Q-28 (a). Les conditions générales de Trade Republic interdisent « l'utilisation de
voies d'accès, de programmes et/ou d'autres interfaces non fournis par Trade Republic en dehors de
l'application », avec droit de **résiliation extraordinaire**. Le texte exact et le numéro
d'article n'ont pas pu être relevés dans le contrat lui-même et **restent à confirmer**. Le
propriétaire a tranché en connaissance de ce risque, qui porte sur son compte.

**Ce qui limite ce risque, et qui ne doit pas changer :** l'application ne fait que **lire** —
aucun ordre n'est passé, rien n'est modifié ([D-41](#d-41), [D-46](#d-46)) — et chaque appel reste
une connexion complète, initiée par l'utilisateur, sans identifiant conservé.

**Deux raisons techniques s'ajoutent** pour écarter pytr des cours : un tableau de bord doit
pouvoir s'ouvrir et afficher une valeur **sans demander le PIN** (d'où le cache, [D-50](#d-50)) ;
et le `exchange="LSX"` par défaut de pytr ne désigne plus la place d'exécution réelle.

**Écarte :** demander les cours par ISIN à Trade Republic, ce qui aurait supprimé le besoin d'une
correspondance ISIN → ticker ; et l'inverse, renoncer à pytr, qui retirerait au projet sa raison
d'être.

### D-50 · 2026-09-26 · Un cours en cache est définitif, et s'oublie sur demande · Validée
**Décision :** un cours de clôture écrit dans le cache local n'est **jamais redemandé**. Une
commande explicite permet de **vider le cache d'un actif** — ou de tous — quand un chiffre paraît
faux.

**Raison :** Q-29 (a). Un jour passé ne change plus, et le cache est ce qui rend le tableau de bord
utilisable sans réseau et à l'abri des limitations de débit de la source
([sources-de-cours.md §7](sources-de-cours.md)). Surtout, c'est ce qui rend les chiffres
**stables** : le montant vu hier est celui qu'on revoit aujourd'hui, condition d'une vérification
à la main.

**Ce que ça écarte :** une fenêtre glissante de rafraîchissement, et le rechargement complet à
chaque ouverture — tous deux plus coûteux en appels et, pire, capables de faire bouger un chiffre
déjà vérifié sans que rien ne le signale.

**Ce que la commande d'oubli traite :** la correction d'une erreur par la source après coup, et le
**regroupement d'actions** (*split*), qui réécrit d'un coup toute la série passée d'un actif. Ces
deux cas sont rares et se voient à l'œil ; les traiter par une commande explicite vaut mieux que
de rendre le fonctionnement courant imprévisible.
**À prévoir dans l'interface :** la **date de récupération** de chaque cours reste affichée, sans
quoi un cache définitif deviendrait un cache opaque.

### D-51 · 2026-09-26 · Les cours viennent de Yahoo Finance, en cours brut · Validée
**Décision :** la source de cours retenue est **Yahoo Finance**, pour les ETF, les actions **et** la
crypto — une seule source, un seul cache, un seul mode de panne. Le cours utilisé est le **cours de
clôture brut**, jamais la série retraitée des dividendes.

**Raison :** Q-14 et [D-18](#d-18), qui demandaient un comparatif écrit avant de choisir ; il est
dans [sources-de-cours.md](sources-de-cours.md). Yahoo est la seule source gratuite qui couvre à la
fois Xetra, Euronext Paris et la crypto en euros avec un historique quotidien profond — donc la
seule compatible avec [D-48](#d-48). Toutes les autres échouent sur un critère rédhibitoire :
Stooq est fermée aux programmes, `pandas-datareader` a supprimé ses lecteurs, Alpha Vantage limite
le gratuit à 100 jours, Twelve Data et Finnhub facturent l'Europe, EODHD et Marketstack donnent un
an, Börse Frankfurt exige un jeton recalculé depuis son propre JavaScript, et Trade Republic est
écarté par [D-49](#d-49).

**Le cours brut n'est pas un détail :** la valeur par défaut de la bibliothèque réinjecte les
dividendes dans le cours passé. Comme le moteur les compte déjà ([D-29](#d-29)), ils seraient
comptés **deux fois**. L'écart mesuré sur une action distribuante dépasse 5 % au début d'une série
d'un an — et il est **nul sur un ETF capitalisant**, donc invisible tant qu'on ne détient rien de
distribuant.

**Trois contraintes qui viennent avec cette source**, toutes vérifiées et à traiter dans le code :
- demander un historique par **dates explicites**, jamais par plage nommée : « tout l'historique »
  renvoie des points **mensuels** en annonçant du quotidien ;
- **vérifier la devise** à chaque cours ([D-48](#d-48)) ;
- accepter les **trous** : un jour sans cours n'est pas une erreur. Le moteur remonte au dernier
  jour coté **et le dit** ; il n'interpole jamais.

**Écarte :** une source par type d'actif (crypto ailleurs), qui multiplierait les mécanismes pour un
portefeuille qui tient dans une page ; et toute source payante, contraire à [D-18](#d-18).
**Fragilité connue et acceptée :** Yahoo n'offre aucune interface officielle et limite le débit
sans prévenir. C'est la raison d'être du cache définitif ([D-50](#d-50)) et du refus explicite
([D-45](#d-45)) : l'application doit continuer à afficher les cours déjà connus, et dire clairement
ce qu'elle ignore. Changer de source ne touchera pas le moteur ([D-26](#d-26)).
**Deuxième avis** disponible sur demande : la LS Exchange (`ls-tc.de`), hors production.

### D-52 · 2026-09-27 · La valeur d'« aujourd'hui » est celle de la dernière clôture connue · Validée
**Décision :** la valeur du portefeuille sans date demandée est prise aux **cours de clôture de
la dernière séance close**, et le rapport écrit **quel jour** il a valorisé (« Valeur des actifs
au 2026-09-26 »). Aucun prix de la séance en cours n'est demandé ni affiché.
**Raison :** Q-30 (a). Le cache est définitif ([D-50](#d-50)) et ne contient jamais le jour même :
un prix intermédiaire y figerait pour toujours une valeur qui n'est pas une clôture. Un cours
courant hors cache, lui, changerait à chaque lancement — et un chiffre qui bouge tout seul n'est
pas vérifiable, alors que c'est le premier que le propriétaire comparera à son application. Le
fournisseur de l'étape 4 fait déjà ce repli sur le dernier jour coté : rien à écrire de plus,
rien à inventer.
**Écarte :** aller chercher le prix courant chez la source sans le mettre en cache (Q-30 b). À
reconsidérer pour l'interface (étape 9), pas avant.
**Conséquence :** la valeur affichée a jusqu'à trois jours d'âge un lundi matin. C'est écrit
dans le rapport, jamais deviné par le lecteur.

### D-53 · 2026-09-27 · Un actif sans cours sort des totaux, qui sont marqués partiels · Validée
**Décision :** une position détenue dont aucun cours n'est utilisable — actif non déclaré, ticker
inconnu, devise inattendue, dernier cours trop ancien — n'est **pas valorisée**. Elle sort de la
valeur totale **et** des trois chiffres clés, **achats compris**, et ces totaux sont marqués
**partiels**, avec la liste de ce qui manque et pourquoi. Elle n'est jamais comptée pour zéro.
**Raison :** Q-31 (a), et [D-45](#d-45) : un zéro silencieux ferait un gain faux, et un total muet
dès qu'un ticker manque cacherait tout le reste. Le chiffre partiel décrit exactement ce qu'il
dit décrire — les actifs valorisés — et le lecteur voit ce qui n'y est pas.
**Écarte :** aucun total tant qu'un actif manque (Q-31 b) ; compter l'actif à son capital investi
ou à zéro.
**Conséquence :** le gain partiel exclut aussi les achats de l'actif manquant. Sans cela, on
retrancherait des achats sans la valeur qu'ils ont produite, et le gain serait faux d'un autre
côté.

### D-54 · 2026-09-27 · Conventions de calcul des rendements : ce qui les rend refaisables · Validée
**Décision :** quatre conventions, écrites dans le [glossaire](glossaire.md) §4 et §5 :
1. **Période** `[début, fin]`, bornes comprises ; `V_début` = capital brut au soir de la veille du
   début, 0 sans début ; `V_fin` = capital brut au soir de la fin.
2. **Flux** = montants bruts signés selon le [format pivot §3](format-pivot.md) : achats et titres
   reçus négatifs, ventes, dividendes **et distributions de capital** positifs. La formule du gain
   compte les distributions, ce que le glossaire omettait : sans elles, gain ≠ plus-values latentes
   + réalisées + dividendes.
3. **TRI** par dichotomie, années de 365 jours, entre −99 % et +100 000 % par an, six décimales.
   C'est la convention de `TRI.PAIEMENTS`, et `flux.csv` en donne la table.
4. **TWRR** découpé à chaque jour de flux ; la valeur qui ouvre une sous-période est prise
   **après le flux, aux cours de clôture du jour** (parts après × clôture), celle qui la ferme
   **avant le flux suivant** (parts de la veille × clôture). Annualisé seulement au-delà de
   365 jours.
**Raison :** le propriétaire doit pouvoir refaire chaque chiffre dans un tableur, et le seul
moyen est que la convention soit écrite et unique. Le point 4 s'écarte de la formule littérale du
glossaire d'origine (`V_avant + F`) parce que celle-ci, avec des cours de clôture et un flux au
prix d'exécution, donne une **base négative** dès qu'on vend tout légèrement au-dessus de la
clôture — et un TWRR de −100 % sur un actif gagnant. L'écriture retenue n'invente rien entre
exécution et clôture, et se refait à partir des seules quantités et clôtures.
**Écarte :** la journée de 365,25 jours ; l'interpolation des cours manquants ; un TWRR aux prix
d'exécution ; un TRI par la méthode de Newton (plus rapide, mais qui peut ne pas converger sans le
dire).
**Limite connue :** un taux annuel sur trois mois est exact et ne veut rien dire ; c'est le
drapeau « peu significatif » (sous 365 jours) qui porte ce jugement, pas une borne de calcul.


---

*Étape 6 (frais, taxes et valeur réelle). Les sept décisions suivantes suivent les
recommandations du plan, approuvées par le propriétaire le 2026-09-27, après trois recherches
dont le comparatif est dans [couts-et-fiscalite.md](couts-et-fiscalite.md).*

### D-55 · 2026-09-27 · Le type d'un actif est déclaré par l'utilisateur, jamais deviné · **Remplacée par D-82**
**Décision :** le type d'un actif — `etf`, `action` ou `crypto` — est **déclaré** dans
`actifs.toml`, à côté du ticker. L'assistant `pastory actifs` le **propose** (la recherche de la
source de cours l'annonce), l'utilisateur **valide**. Une crypto l'est d'office par sa poche
([D-16](#d-16)). Le type **n'entre pas dans le format pivot** : il ne décrit pas une opération, il
sert à choisir un taux d'estimation.
**Raison :** c'est lui qui choisit le taux de spread par défaut ([D-56](#d-56)) et qui dit si un
TER est attendu. L'export ne le donne pas de façon exploitable : le champ `instrumentType` de
Trade Republic n'existe que sur les **ordres**, donc pas pour un actif reçu sans achat, et il ne
distingue pas un ETF de niche d'un ETF large. Deviner un type, c'est deviner un coût.
**Écarte :** déduire le type de l'export ; appliquer un taux « moyen tous actifs » quand le type
manque. **Conséquence assumée :** un actif sans type n'a **aucun** spread estimé et **aucune**
valeur réelle ; il est listé, jamais compté pour zéro ([D-45](#d-45)).

### D-56 · 2026-09-27 · Le spread est un taux par côté, par type d'actif · Validée
**Décision :** le spread estimé d'un achat ou d'une vente vaut `montant brut × taux par côté`.
Le taux par côté est la **moitié** de l'écart achat/vente publié. Trois valeurs par défaut, avec
leur fourchette mesurée : **ETF 0,05 %** [0,01 – 0,15], **action 0,10 %** [0,02 – 0,25],
**crypto 0,50 %** [0,25 – 1,50]. Un actif peut recevoir son propre taux dans `actifs.toml`.
L'heure de l'ordre n'est **pas** prise en compte.
**Raison :** précise [D-30](#d-30), qui disait « à chaque achat et à chaque vente » sans dire
combien. Les valeurs viennent de trois familles de sources : la mesure de liquidité que
Deutsche Börse publie par ISIN (1,7 point de base aller-retour pour un ETF monde, médiane 25),
les études des régulateurs néerlandais et espagnol (surcoût de 5 à 15 points de base par ordre),
et les comparatifs crypto (0,5 à 1,5 % d'écart total). La convention « par côté » est celle de la
mesure de Deutsche Börse, explicitement un aller-retour.
**Écarte :** un taux unique pour tous les actifs ; un taux dépendant de l'heure (hors des heures
de Xetra les écarts sont trois à cinq fois plus larges, mais l'horodatage de l'export et le
régime d'exécution de la banque ont changé en cours d'histoire : deviner ferait pire) ; déduire
le spread réel des cours de clôture, impossible — un ETF bouge de 0,5 % dans la journée, l'écart
cherché vaut 0,01 à 0,1 %.
**Limite connue :** aucune mesure indépendante n'existe depuis que Trade Republic exécute les
ordres lui-même (2 juillet 2026, fin de la rémunération du flux d'ordres). Les taux sont ceux de
l'ancien régime, et le comparatif le dit.

### D-57 · 2026-09-27 · Le capital fiscal est tenu dans le rejeu, à côté du capital investi · Validée
**Décision :** `EtatPosition` porte un **capital fiscal** en plus du capital net investi : un
achat y ajoute `montant brut + frais + taxes`, une vente en retire la part vendue **au prorata
des parts**, une distribution de capital le réduit, avec un plancher à zéro. On en déduit un
**prix de revient fiscal**, affiché à côté du prix de revient et exporté dans `positions.csv` et
`journal.csv`. Il est rangé côté **coûts** : aucun chiffre de performance ne le lit
([D-21](#d-21)).
**Raison :** [D-13](#d-13) l'annonçait — « le prix de revient fiscal français inclut les frais
d'achat ; il faudra un calcul séparé si l'impôt est un jour estimé ». Le BOFiP est explicite : le
prix d'acquisition est majoré des frais (courtages, commissions, impôts supportés à
l'acquisition), et c'est obligatoirement une moyenne pondérée que les ventes ne modifient pas.
Le tenir **dans le rejeu**, et non dans un module séparé, fait que la règle du prorata n'existe
qu'une fois et que le propriétaire la vérifie dans le journal, une colonne à côté de l'autre.
**Écarte :** recalculer le prix de revient fiscal après coup à partir des totaux (la règle du
prorata serait écrite deux fois) ; inclure les frais dans le capital net investi, ce que
[D-12](#d-12) interdit.
**Conséquence :** pour la **crypto**, la base imposable part du capital net investi (frais
exclus), la loi ne nommant pas les frais d'acquisition : les deux colonnes servent, chacune à sa
poche.

### D-58 · 2026-09-27 · Un taux est une valeur, une date et une source · Validée
**Décision :** les taux fiscaux et les paramètres de coûts vivent dans deux fichiers TOML
**versionnés** (`pastory/parametres/fiscalite.toml` et `couts.toml`). Chaque paramètre porte
`valeur`, `unite`, `en_vigueur_depuis`, `source` (le texte de loi ou la mesure, avec son adresse)
et `verifie_le`. **Un paramètre sans date ou sans source est refusé à la lecture.** Le rapport
cite, sous chaque impôt estimé, le taux employé et d'où il vient.
**Raison :** la loi change, et le propriétaire ne code pas. Mettre à jour un taux doit être une
ligne de TOML, jamais une ligne de Python. Et un chiffre dont on ne peut plus retrouver l'origine
ne se vérifie plus : le refuser à la lecture est le seul moyen d'empêcher qu'il s'installe.
**Écarte :** des taux en constantes dans le code ; un fichier de taux sans dates (on ne saurait
plus si 17,2 % est un oubli ou un choix).
**Précision :** les valeurs sont converties en `Decimal` **par le texte** — TOML lit `18.6` comme
un flottant, et `Decimal(18.6)` vaut 18,600000000000001421… ([D-33](#d-33)).

### D-59 · 2026-09-27 · Le gain du PEA est approché depuis les titres, sur une date déclarée · Validée ; la date est trouvée depuis D-86, l'hypothèse « aucun retrait » vérifiée depuis D-87
**Décision :** l'impôt du PEA se calcule sur le **gain du plan**, approché par
`plus-values latentes + plus-values réalisées brutes + dividendes bruts − frais − taxes`, sur
**toutes** les positions du PEA, soldées comprises. L'ancienneté vient d'une date de **premier
versement déclarée** par l'utilisateur dans `fiscalite.toml`. Sans cette date, l'impôt du PEA est
« non calculable » et le rapport dit où l'écrire. Si **une seule** position du PEA n'a pas de
cours, la poche entière est non calculable.
**Raison :** le fisc apprécie le gain d'un PEA **au niveau du plan** (valeur liquidative moins
versements), or l'application ne suit pas les espèces ([D-11](#d-11)). La démonstration
([couts-et-fiscalite.md](couts-et-fiscalite.md) §5.3) montre que les deux écritures sont
**exactement égales** sous trois hypothèses, affichées dans le rapport : aucun retrait passé, ni
intérêt ni frais sur les espèces, tout mouvement d'espèces rattaché à une opération connue.
L'ancienneté, elle, ne se déduit pas : un PEA fermé puis rouvert repart de zéro
([Q-11](questions-ouvertes.md)), et un PEA transféré garde une date d'origine invisible ici.
**Écarte :** approcher l'ancienneté par la date du premier achat (prudent, mais faux après un
transfert ou une réouverture, et un impôt faux par excès reste un impôt faux) ; calculer l'impôt
du PEA sur les seules positions valorisées, ce qui donnerait un impôt de plan partiel — un
chiffre qui n'existe pas.
**Limite connue :** un PEA **transféré** d'un autre établissement met l'approximation en défaut,
l'histoire d'avant manquant. C'est le cas du tiers ([Q-10](questions-ouvertes.md)).

### D-60 · 2026-09-27 · L'impôt estimé est le PFU, sur les seules plus-values latentes · Validée
**Décision :** l'impôt estimé applique le **prélèvement forfaitaire unique** de plein droit
(12,8 % d'impôt sur le revenu + 18,6 % de prélèvements sociaux en 2026, soit **31,4 %**). La base
ne compte que ce qui **serait réalisé par la vente** : les plus-values latentes, gains et pertes
compensés par poche, avec un plancher à zéro. Ce qui est **déjà encaissé** — dividendes reçus,
plus-values déjà réalisées dans l'année — n'entre **pas** dans la valeur réelle, et le rapport le
dit en une ligne.
**Raison :** la valeur réelle répond à « combien je récupérerais si je vendais tout »
([D-23](#d-23)) : c'est un **coût de sortie**. L'impôt sur un dividende déjà encaissé est dû que
l'on vende ou non ; le compter ferait payer deux fois la même question. Le PFU est le régime de
plein droit ; l'option pour le barème dépend de l'ensemble du foyer, que l'application ne connaît
pas.
**Écarte :** l'option pour le barème progressif ; les moins-values reportées des années
antérieures (inconnues) ; l'ajout des plus-values déjà réalisées de l'année, qui relèvent de la
déclaration et non de la sortie.
**Limite connue, et assumée :** ce n'est pas le montant que l'utilisateur paiera. Les hypothèses
sont affichées, et la production de déclarations reste hors périmètre ([D-26](#d-26)).

### D-61 · 2026-09-27 · Le TER est proposé depuis la liste de Xetra, et validé par l'utilisateur · Validée ; l'émetteur passe avant Xetra depuis D-90, sans validation (D-80)
**Décision :** les frais courants d'un ETF sont **proposés** depuis la « List of Tradable ETFs &
ETPs » de Deutsche Börse — fichier public, sans clé, une ligne par ISIN — et **validés** par
l'utilisateur dans `actifs.toml`. Un ETF sans TER validé n'a **aucun** frais courant estimé, avec
le motif. Un TER hors de **0,03 %–1,00 %** est refusé à la lecture comme une erreur d'unité.
**Raison :** même schéma que la correspondance ISIN → ticker ([D-48](#d-48)), et pour la même
raison : la source se trompe. Mesuré le 2026-09-27 sur 520 ISIN comparés au fichier d'un
émetteur, **28 valeurs (5,4 %) sont en retard** sur une baisse de frais, toutes dans le sens
« trop élevé ». Et les ETF **français de type « PEA »** sont absents du fichier. La proposition
porte le nom de la part, sa politique de distribution et la date du fichier, pour que
l'utilisateur reconnaisse la bonne part avant de valider.
**Écarte :** Yahoo Finance (60 % de couverture seulement, aucun Vanguard, pas de date) — gardé
comme secours documenté, non implémenté ; justETF (pas d'interface, extraction fragile) ;
Boursorama (extraction automatique interdite par ses conditions) ; les listes des émetteurs (un
adaptateur par émetteur) ; Trade Republic ([D-49](#d-49)).
**Pièges traités, tous vérifiés :** le fichier porte l'extension `.xls` mais c'est un `.xlsx` ;
son adresse change à chaque publication, donc elle est relue sur la page ; la valeur est une
**fraction** avec du bruit de flottant, arrondie à quatre décimales ; un ISIN apparaît une fois
par devise de négociation.

### D-62 · 2026-09-27 · Les fonctionnalités visent l'utilisateur type, pas le portefeuille du propriétaire · Validée
**Décision :** le **choix des fonctionnalités** se fait pour un investisseur type de Trade
Republic, et non pour le portefeuille du propriétaire à un instant donné. Un cas de figure
courant chez Trade Republic est traité **même si le propriétaire n'est pas concerné
aujourd'hui** ; à l'inverse, un cas rare reste hors périmètre même s'il le concerne.
**Raison :** évolution de cap du propriétaire, qui compte partager l'application. Jusqu'ici, seule
l'**installation** par un tiers était un objectif ([étape 10](feuille-de-route.md)) ; le contenu,
lui, suivait ses propres actifs. Premier effet concret : les **actions détenues en direct**
entrent dans les répartitions de l'étape 7 alors qu'il n'en détient aucune, parce que l'achat
d'actions à l'unité est courant sur cette banque.
**Conséquence sur la rédaction :** tout message d'absence, de déduction ou d'estimation est écrit
pour quelqu'un qui **n'a pas suivi la construction du projet**. « Cet actif n'est pas couvert »
doit dire pourquoi et ce qu'il faut faire.
**Écarte :** dimensionner les fonctionnalités sur le portefeuille du propriétaire. **N'écarte
pas** la règle inverse, qui reste vraie : les **valeurs** vérifiées restent les siennes, et les
choix de calcul se valident sur ses chiffres ([D-03](#d-03)).

### D-63 · 2026-09-27 · La composition d'un ETF vient d'extraETF, par ISIN, en lisant les répartitions agrégées · Validée
**Décision :** la répartition par pays et par secteur d'un ETF est obtenue auprès d'**extraETF**
(`api-v2/detail/?isin=`), interrogé par **ISIN**, en lisant **les répartitions agrégées** et
**jamais les lignes détenues**. Les pays arrivent en **code ISO 3166-1**, les secteurs en **code
machine** : aucun calcul ne repose sur un libellé affiché (règle 4 de `CLAUDE.md`).
**Raison :** [Q-39](questions-ouvertes.md), après le
[comparatif des sources](composition-des-etf.md). Quatorze familles de sources examinées, onze
interrogées. C'est la seule source gratuite, sans clé, interrogeable par ISIN en un appel, qui
donne **les deux répartitions avec des codes**, et qui réponde correctement sur un **ETF PEA
synthétique**.
**Écarte :** les émetteurs comme source de calcul — trois nomenclatures dont deux non déclarées,
agrégats tronqués à neuf postes, et **rien d'exploitable chez BNP Paribas Easy ni Xtrackers**, donc
un PEA partiellement invisible ; justETF (libellés sans code, classification différente) ; Yahoo
Finance (**aucune** répartition par pays, aucune date) ; fondsweb (dix premières lignes sans
reliquat) ; Trackinsight et Morningstar (captcha) ; les API à clé (palier gratuit américain, et la
dépendance que [D-18](#d-18) refuse) ; l'EET et la base des DIC (n'existent pas sous forme
interrogeable).
**Limite assumée :** c'est une **API interne non documentée**, dont l'usage n'est pas explicitement
autorisé — usage personnel toléré, pas un droit. Même forme de question que [D-49](#d-49) pour
pytr. Elle peut fermer sans préavis : l'application doit alors le dire et continuer sans
répartition, jamais afficher un chiffre faute de données.
**Pièges traités :** le swap d'un ETF synthétique porte le pays « USA » dans les lignes détenues,
ce qui afficherait **100 % États-Unis pour un ETF monde** ; les libellés sont en allemand même sur
`/en/` ; aucune répartition ne somme à 100 %.

### D-64 · 2026-09-27 · Pour un ETF synthétique, on affiche l'indice suivi · Validée
**Décision :** la répartition d'un ETF **synthétique** est celle de l'**indice suivi**, pas celle
du panier détenu. L'actif est marqué **« synthétique »** à l'écran, pour que l'écart avec les
titres listés sur la fiche de l'émetteur soit compréhensible.
**Raison :** [Q-40](questions-ouvertes.md). C'est l'**exposition économique** réelle : si l'indice
monte, l'ETF monte, quoi qu'il détienne. Mesuré le 2026-09-27 sur un ETF *MSCI World* à swap
éligible au PEA : son panier donne **Allemagne 38,5 %** et **États-Unis 15,6 %**, son indice
**États-Unis 72,9 %**. Afficher le panier décrirait un risque que l'utilisateur ne porte pas. Et
tout ETF « PEA » sur un indice non européen est synthétique **par construction**, puisqu'il doit
détenir au moins 75 % de titres éligibles au PEA.
**Écarte :** le panier détenu (la détention juridique) ; l'affichage des deux côte à côte, qui
double la lecture et repose sur l'utilisateur la question « lequel est le bon chiffre ».
**Conséquence de code :** on ne lit **jamais** les lignes détenues ([D-63](#d-63)). Un actif dont
on ne connaîtrait que les lignes n'est pas affiché.

### D-65 · 2026-09-27 · Une seule nomenclature sectorielle, nommée : les 11 secteurs Morningstar · Validée
**Décision :** les secteurs sont les **11 secteurs de niveau 1 de Morningstar**, désignés comme
tels à l'écran — **jamais** le mot « GICS ». La table code → libellé français vit dans
`pastory/parametres/secteurs.toml`, avec sa source et sa date ([D-58](#d-58)). **Aucun
rapprochement par libellé**, et aucune addition de deux nomenclatures.
**Raison :** [Q-41](questions-ouvertes.md). **Aucune source gratuite interrogeable par ISIN ne
donne du GICS**, alors que les indices suivis sont bâtis sur GICS ou sur ICB. Morningstar est la
classification accessible, et c'est aussi celle que l'utilisateur verra en vérifiant (Yahoo,
Morningstar, justETF). Mélanger deux nomenclatures donne un total juste et une répartition fausse :
mesuré sur un même fonds à une même date, la technologie vaut **35,71 %** chez l'un et **30,61 %**
chez l'autre, l'écart étant exactement Alphabet et Meta, qui changent de camp. Le code 10 lui-même
vaut *Technology* chez ICB et *Energy* chez GICS.
**Écarte :** GICS (inaccessible gratuitement par ISIN) ; ICB ; toute table de passage entre les
deux, qui n'existe pas officiellement et ne pourrait pas être bijective.
**À surveiller, sans rien coder :** une consultation GICS est ouverte du 17/07/2026 au 30/10/2026,
avec des changements annoncés avant novembre 2026 et une date d'effet non publiée.

### D-66 · 2026-09-27 · Les pays ont pour clé leur code ISO, et la règle de pays est affichée · Validée
**Décision :** un pays est identifié par son **code ISO 3166-1 alpha-2**, jamais par un libellé, et
**jamais déduit du préfixe de l'ISIN**. La **règle de pays** employée est affichée avec les
chiffres : pour un ETF, le pays d'activité au sens de la source ; pour une **action détenue en
direct**, le **siège social**. Les deux règles cohabitent dans la même répartition, et l'écran
**le dit**.
**Raison :** [Q-42](questions-ouvertes.md). Une répartition géographique n'est **pas une grandeur
définie de façon unique** : BlackRock écrit lui-même que son exposition géographique se rapporte
« principalement » au domicile de l'émetteur, « mais, dans certains cas, elle peut refléter le lieu
où l'émetteur réalise l'essentiel de son activité ». L'écart mesuré entre les deux règles, sur un
même fonds à une même date, est de **2 points sur les États-Unis** (70,00 % contre 72,04 %) et d'un
facteur huit sur l'Irlande. Un chiffre dont on ignore la règle n'est pas vérifiable, et
l'expérience de l'étape 6 dit qu'un chiffre non vérifiable n'est pas cru.
**Écarte :** convertir une règle dans l'autre (impossible sans les lignes) ; taire la différence ;
renoncer aux actions en direct, courantes sur cette banque ([D-62](#d-62)).
**Piège traité :** Taiwan Semiconductor se négocie sous un ISIN commençant par `US` et n'est pas
américain — même famille d'erreur qu'un ISIN lu dans la colonne du nom, à l'étape 6.

### D-67 · 2026-09-27 · Les zones sont une liste datée et sourcée, pas une notion · Validée
**Décision :** les pays sont regroupés en **zones d'investisseur** — Amérique du Nord, Europe,
Japon, Asie-Pacifique développée, marchés émergents — et la liste des pays de chaque zone vit dans
`pastory/parametres/zones.toml`, avec sa **source et sa date**. Elle est corrigeable sans
toucher au code.
**Raison :** [Q-43](questions-ouvertes.md). C'est le vocabulaire des outils du marché, donc celui
dont l'utilisateur a besoin pour juger sa diversification. Le découpage « neutre » des Nations
unies a été écarté parce qu'il place la **Chine et le Japon dans la même case**, ce qui ne décrit
aucune décision d'investissement.
**Limite affichée :** il n'existe **aucune norme** pour « développé » et « émergent ». MSCI et FTSE
ne sont pas d'accord, et le désaccord est actif : la **Corée du Sud** et la **Pologne** changent de
camp selon le fournisseur, et la **Grèce** est développée chez FTSE depuis le 21/09/2026 mais ne le
sera chez MSCI qu'en mai 2027. Le fichier nomme donc son fournisseur et sa date, et l'écran signale
que la zone est une convention.
**Écarte :** ONU M49 seul ; les pays sans regroupement (30 à 55 lignes, la plupart sous 1 %).

### D-68 · 2026-09-27 · Trois répartitions, et l'obligataire hors de la géographie et des secteurs · Validée
**Décision :** l'application affiche **trois** répartitions : par **classe d'actifs** (actions,
obligations, liquidités), puis par **pays** et par **secteur** de la **seule partie actions**. Un
ETF obligataire compte dans la première et reste **hors** des deux autres, son montant affiché.
Une **crypto** reste hors des trois classifications, sur une ligne à part.
**Raison :** [Q-44](questions-ouvertes.md) et le point de cap ([D-62](#d-62)) : les portefeuilles
mixtes actions/obligations sont fréquents. Et sur un ETF obligataire, « secteur » ne veut pas dire
la même chose (Trésor, entreprises, titrisé — la méthodologie GICS n'attribue aucun secteur à un
emprunt d'État), tandis que « pays » peut vouloir dire **devise** : « Bonds are included in US bond
indices when the securities are denominated in U.S. dollars **regardless of the domicile of the
issuer** » (fiche iShares, 31/08/2026). Fusionner les deux fabriquerait des postes « Trésor 18 % »
à côté de « Technologie 25 % », qui ne sont pas de même nature.
**Raison de forme :** c'est la logique de [D-11](#d-11) — on ne force pas une grandeur dans une
catégorie où elle n'a pas de sens.
**Écarte :** un camembert sectoriel unique mêlant actions et obligations ; ranger la crypto dans un
secteur « technologie » ; l'exclure sans le dire.

### D-69 · 2026-09-27 · Le reliquat reste visible, et rien n'est renormalisé à 100 % · Validée
**Décision :** ce qu'une composition n'attribue pas est affiché sous le nom **« non attribué »**, et
ce que l'application ne sait pas ouvrir est affiché **« non couvert »**, avec son montant. **Aucune
renormalisation à 100 %**, jamais.
**Raison :** application directe de [D-53](#d-53) à la diversification. Et une mesure : **aucune
répartition ne somme à 100 %** (99,43 % à 99,96 % selon le fonds), et les deux vues d'un même fonds
ne somment pas au même total — 0,87 point d'écart mesuré entre ses pays et ses secteurs. Un
contrôle « ça fait 100 » échouerait donc à tort, et une renormalisation cacherait précisément ce
qu'on ignore. Le prêt de titres peut même faire **dépasser** 100 % : le contrôle de vraisemblance
l'accepte.
**Écarte :** compléter un poste manquant depuis une autre source (ce serait mélanger deux
nomenclatures, [D-65](#d-65)) ; répartir le reliquat au prorata ; masquer un actif non couvert.
**Conséquence de rédaction :** ces deux libellés sont lus par quelqu'un qui n'a pas suivi le projet
([D-62](#d-62)). Ils disent **pourquoi** et **ce qu'il faut faire**.

### D-70 · 2026-09-27 · Une composition est datée et remplaçable, contrôlée, et corrigeable à la main · Validée
**Décision :** contrairement à un cours, définitif en cache ([D-50](#d-50)), une **composition est
datée et remplaçable** : elle porte sa date d'arrêté et sa source, une commande la rafraîchit, une
autre l'oublie. Chaque composition reçue passe des **contrôles de vraisemblance** — somme des poids
dans une fourchette, code ISO connu, code secteur connu, aucune lecture des lignes détenues — et
tout code inconnu est **affiché**, jamais rangé par défaut (règle 5 de `CLAUDE.md`). Une
**correction manuelle** est possible dans `actifs.toml` et l'emporte sur la source.
**Raison :** un portefeuille d'ETF change de composition chaque mois, alors qu'un cours de clôture
passé ne change jamais. Et le propriétaire a choisi la mise à jour **automatique**, sans relecture
préalable ([Q-39](questions-ouvertes.md)) : sans contrôles ni porte de sortie, ce choix serait sans
filet. La date est affichée telle que la source la donne, avec la réserve du
[comparatif §3.1](composition-des-etf.md) : le champ employé parle de l'**indice**, et on n'en
affirme pas plus.
**Écarte :** le cache définitif ([D-50](#d-50)) pour ce type de donnée ; la validation préalable
obligatoire, écartée par le propriétaire ; une composition sans date, refusée.
**Le contrôle ajouté après l'avoir constaté sur de vraies données (2026-09-27) :** pour certains
fonds, la source **répond normalement** — date, drapeau de réplication — mais range **100 % du fonds
dans « autres »** et ne donne ni pays ni secteur. Ce n'est pas un fonds fait d'« autres choses » :
c'est un fonds dont elle ignore le contenu. Sans garde-fou, ces actifs tombaient dans « obligations,
liquidités et autres », c'est-à-dire présentés comme de la dette et des liquidités — **un chiffre
faux et crédible**, exactement ce que ce projet traque. Une composition dont les classes d'actifs
**renseignées** (actions, obligations, titres assimilés) pèsent moins de **50 %** est donc refusée,
et l'actif devient **non couvert**. Le contrôle vit dans le module de la source, seul endroit qui
connaît son vocabulaire.

### D-71 · 2026-09-28 · Le contenu d'un actif se déclare, et n'avoir ni pays ni secteur n'est pas un manque · Validée ; le contenu est trouvé depuis D-89, qui revient sur l'écart d'extraETF
**Décision :** l'utilisateur peut déclarer le **contenu** d'un actif dans `actifs.toml` —
`contenu = "obligations"`, `"matieres_premieres"` ou `"actions"`. Un actif dont le contenu est
déclaré compte **à 100 % dans sa classe** et reste **hors** de la géographie et des secteurs, sans
être annoncé « composition inconnue ». Les **matières premières** deviennent une classe d'actifs à
part entière dans `parametres/classes_actifs.toml`, et non un cas de « autres ». Et chaque montant
sorti de la géographie porte **le nom de sa classe** — « Obligations (hors actions) », « Matières
premières (hors actions) » — au lieu d'un fourre-tout unique.
**Raison :** une observation du propriétaire sur ses propres actifs. Un ETF d'obligations et un ETF
de matières premières s'affichaient **« non couvert : composition inconnue »**, ce qui est faux :
ils ont bien une composition, elle n'a simplement ni pays ni secteur **au sens des actions** —
exactement comme un actif numérique ([D-68](#d-68)). Dire « inconnu » là où la réponse est « sans
objet » fabrique un doute pour rien, et le libellé unique « obligations, liquidités et autres »
faisait de surcroît passer de l'or pour de la dette.
**Pourquoi un champ nouveau et non le `type` existant :** le `type` dit **ce qu'on détient**, et
c'est lui qui choisit le spread et décide si un TER est attendu ([D-55](#d-55), [D-61](#d-61)). Un
ETF obligataire reste un **ETF** : lui changer son type pour décrire son contenu lui ferait perdre
ses frais courants estimés. Les deux questions sont distinctes, elles ont désormais deux champs.
**Écarte :** déduire le contenu du champ numérique `asset_class` de la source. Il existe et il est
tentant, mais il n'est pas documenté, et le rapprochement tenté le 2026-09-28 s'est révélé **faux
sur deux actifs sur trois**. Une déclaration se vérifie, un code deviné non.
**Conséquence de forme :** une composition déclarée n'a **pas** de date d'arrêté, et n'entre donc pas
dans la fourchette de dates affichée en tête du bloc — sans quoi elle la tirerait jusqu'à
aujourd'hui. Le rapport nomme ces actifs et prévient que leurs chiffres ne vieillissent pas tout
seuls.

### D-72 · 2026-09-28 · Une source de secours par actif, nommée à l'écran · Validée, à réaliser à l'étape 8
**Décision :** quand la source principale ne sait pas ouvrir un fonds **d'actions**, l'application
pourra aller chercher sa composition auprès d'une **source de secours choisie par actif**, à
condition que **la source de chaque chiffre soit visible à l'écran**. Amundi, par exemple, publie
pour ses ISIN français la répartition de l'**indice suivi** — exactement ce que [D-64](#d-64)
demande.
**Raison :** [Q-47](questions-ouvertes.md). La lacune est réelle et documentée : la source retenue
n'a pas la transparence de certains fonds **à swap**, fonds par fonds. Le diagnostic du 2026-09-28 a
écarté les explications faciles — ce n'est ni un problème de part, ni un défaut rattrapable par une
répartition par région, ni une lacune générale sur les marchés émergents (deux fonds émergents
**physiques** testés donnent 35 et 28 pays).
**La contrainte qui commande la forme, et non l'inverse :** deux sources n'ont ni la même
nomenclature sectorielle ni la même règle de pays. Les mélanger dans un même graphique est le
**piège n° 16** du [comparatif](composition-des-etf.md) : 5 points d'écart mesurés sur la
technologie. La source doit donc être affichée **ligne par ligne**, ce qui est un choix de
présentation — d'où le report à l'étape 8, où l'écran sera conçu.
**Écarte :** compléter en silence un camembert avec une seconde source ; renoncer et laisser le trou
sans recours. **N'écarte pas** la déclaration à la main ([D-70](#d-70)), qui reste disponible et qui
est le seul recours d'ici là.
**En attendant :** l'actif reste **non couvert**, avec son montant affiché, et la répartition est
marquée partielle ([D-69](#d-69)).

---

*Arbitrage du propriétaire du 2026-09-30, rendu sur les maquettes de l'étape 8.*

### D-73 · 2026-09-30 · Les frais et taxes tiennent sur un seul écran, en trois niveaux · Validée
**Décision :** l'onglet « Frais et taxes » présente les trois niveaux **à la file, sur un seul
écran** : ce qui a déjà été prélevé, ce qui court pendant la détention, et ce qu'il resterait à la
sortie — la valeur réelle ([D-23](#d-23)) étant le dernier de ces niveaux, et non une vue séparée.
**Raison :** [Q-21](questions-ouvertes.md). Le propriétaire a comparé les deux arrangements sur la
maquette et a choisi celui-ci : les trois niveaux se suivent et se lisent d'un trait, là où deux
vues séparées obligent à des allers-retours pour répondre à une seule question — combien tout cela
coûte.
**Écarte :** la recommandation d'origine de Q-21, qui proposait un onglet « Frais et taxes » et une
vue « Valeur réelle » distincte. C'est le deuxième arbitrage rendu **contre** une recommandation,
après [D-62](#d-62), et pour une raison de même nature : l'usage réel prime sur la symétrie du
découpage.
**Ne change pas :** [D-17](#d-17) — les estimations ne se mélangent jamais aux coûts payés. Ici la
séparation est portée par le découpage lui-même, le premier niveau étant le réel et les deux
suivants l'estimé. C'est d'ailleurs ce qui a ouvert [Q-49](questions-ouvertes.md), sur la place de
la retenue à la source des dividendes.

---

### D-74 · 2026-09-30 · L'application s'appelle Pastory · Validée
**Décision :** le nom de l'application est **Pastory**. Il remplace « DashBoard Trade Republic »
partout : le paquet Python (`pastory/`), la commande unique (`uv run pastory …`), le nom de
distribution, la feuille de style livrée (`pastory/vues/assets/pastory.css`, [D-31](#d-31)), le
bandeau de l'interface, le dossier personnel de l'utilisateur, et la documentation.
**Raison :** arbitrage du propriétaire. « DashBoard Trade Republic » décrivait un outil attaché à
une banque, alors que le moteur ne lit que le format pivot et que Trade Republic n'est **qu'un
adaptateur** ([D-26](#d-26)) : un nom propre est cohérent avec cette architecture, et il le reste
le jour où un deuxième adaptateur existe.
**Écarte :** garder le nom de la banque dans celui de l'application. Le nom « Trade Republic »
subsiste **là où il désigne la banque** — l'adaptateur `pastory/adaptateurs/trade_republic/`, les
messages qui parlent de l'export, la documentation des données — et nulle part ailleurs.
**Conséquence sur les fichiers de l'utilisateur :** le dossier personnel ([D-37](#d-37)) s'appelle
désormais `Pastory` au lieu de `DashBoardTradeRepublic`, et la variable d'emplacement
`PASTORY_DOSSIER` au lieu de `DASHBOARD_TR_DOSSIER`. **Rien n'est déplacé automatiquement** : un
cours en cache est définitif ([D-50](#d-50)), et le déplacer en silence reviendrait à changer des
chiffres dans le dos de l'utilisateur. L'application **signale** l'ancien dossier — dans
`pastory emplacements`, et dans l'erreur d'export introuvable quand l'ancien dossier en contient un
— et laisse l'utilisateur décider. C'est une application de [la règle 6](../CLAUDE.md) : toute
déduction est explicite et signalée.
**Reste à faire par le propriétaire, hors dépôt :** renommer le dépôt GitHub
(`Dashboard-Trade-Republic`) et le dossier local du projet (`DashBoard-Trade_Republic`). Ni l'un ni
l'autre n'est touché par le code, et les renommer depuis une session de travail casserait le
chemin courant.

### D-75 · 2026-09-30 · Le premier niveau des frais est « ce qui a déjà été prélevé » · Validée
**Décision :** le premier des trois niveaux de l'onglet « Frais et taxes » ([D-73](#d-73))
rassemble **ce qui a déjà été prélevé**, quel qu'en soit le moment — frais d'ordre, taxes de
transaction, et **retenue à la source sur les dividendes**, qui y reste. Il est nommé ainsi à
l'écran, et le « ? » qui l'accompagne le dit.
**Raison :** [Q-49](questions-ouvertes.md), ouverte par le propriétaire en butant sur la retenue.
Le découpage en trois niveaux n'est donc **pas une chronologie** mais la séparation qui compte le
plus ici : ce qui a été payé, ce qui est estimé pendant la détention, ce qui est estimé à la sortie
([D-17](#d-17)). Une chronologie dont la première étape contient un événement postérieur trompe le
lecteur, et c'est exactement ce qui vient de se produire.
**Écarte :** (a) la chronologie stricte, qui aurait descendu la retenue au niveau 2 en y mélangeant
un coût réel et une estimation — ce que D-17 interdit de confondre, et qu'il aurait fallu séparer à
l'intérieur du bloc ; (c) un quatrième niveau (entrée, détention réelle, détention estimée,
sortie), plus juste sur les deux axes mais qui défait le bénéfice de [D-73](#d-73) : un seul écran
qui se lit d'un trait.
**Conséquence pour l'étape 9 :** le titre du niveau dit le critère, jamais le moment. Écrire
« Déjà prélevé » ou « Ce qui a déjà été prélevé », et **pas** « À l'achat » ni « En entrant ».

---

*Compléments de l'étape 8 bis, après la recherche de la source de secours.*

### D-76 · 2026-09-30 · « Non transparisé » reste au glossaire, et n'est jamais affiché · Validée
**Décision :** la notion de **fonds non transparisé** — un fonds dont les lignes sont elles-mêmes
des fonds — est **définie au [glossaire](glossaire.md)**, et **aucun écran ne l'emploie**. Un fonds
de fonds que la source ne sait pas ouvrir est affiché **« non couvert »** ([D-69](#d-69)), et la
bulle d'aide de « non couvert » **explique que certains fonds détiennent d'autres fonds** — sans
prétendre que c'est le cas de celui-là.
**Raison :** [Q-48](questions-ouvertes.md), tranchée après la recherche de l'étape 8 bis. Le
constat est net : **aucune source accessible n'indique qu'un fonds est un fonds de fonds.**
extraETF n'a que six classes d'actifs (`stock`, `bond`, `preferred`, `convertible`, `cash`,
`other`) et un fonds de fonds y tombe dans `other` — que le garde-fou de [D-70](#d-70) refuse déjà,
l'actif devenant non couvert. Le service d'Amundi ([D-77](#d-77)) n'a pas de marqueur non plus : son
vocabulaire est celui des **instruments** (`EQUITY_ORDINARY`, `GOVERNMENT`), pas des véhicules.
**Pourquoi le garder au glossaire plutôt que le supprimer :** la notion explique **pourquoi** un
fonds peut être non couvert, et c'est une information vraie et utile. Un « non couvert » sans
explication laisse l'utilisateur devant un trou ; un « non couvert » qui dit qu'un fonds peut en
contenir d'autres lui apprend quelque chose de son portefeuille.
**Écarte :** le produire en le devinant à partir de `other : ~100 %`. Cela confondrait « c'est un
fonds de fonds » avec « la source ne voit rien dedans » — exactement l'erreur de [D-71](#d-71), où
un code non documenté s'est révélé faux sur deux actifs sur trois. Écarte aussi le retrait pur et
simple de la notion des trois documents qui la portaient.
**Conséquence de rédaction :** le [comparatif §8.2](composition-des-etf.md) et la
[feuille de route](feuille-de-route.md) sont corrigés : ils annonçaient un affichage.
**La mesure qui reste au dossier**, faite à l'étape 7 : sur un fonds *LifeStrategy*, la composition
de premier niveau est « 100 % fonds d'investissement », et une source qui applique une nomenclature
sectorielle à ces lignes répond **« 100 % finance, Irlande »**. Crédible, absurde. C'est ce chiffre
que le refus évite.

### D-77 · 2026-09-30 · La source de secours est le service produit d'Amundi, et elle ne sert que la géographie · Validée ; essayée d'elle-même depuis D-91
**Décision :** la source de secours de [D-72](#d-72) est le **service produit d'Amundi**
(`POST /mapi/ProductAPI/getProductsData`, champ `breakDown.aggregationFields`), déclarée **par
actif** dans `actifs.toml` comme le contenu de [D-71](#d-71). Elle fournit **la répartition par pays
de l'indice suivi**, et **rien d'autre** : ses secteurs ne sont **pas** employés.
**Raison :** la recherche de l'étape 8 bis, le 2026-09-30. Elle répond à la question que D-72
posait, et elle y répond bien là où ça compte : sur `FR001400U5Q4` — un **ETF PEA à swap**, la
famille même que D-72 a identifiée comme le trou d'extraETF — elle rend **États-Unis 72,93 %**, là
où D-64 avait mesuré **15,6 % pour le panier** et **72,9 % pour l'indice**. C'est donc bien
l'**indice** qu'elle publie, à 0,03 point de la mesure de l'étape 7, pour exactement les fonds qui
manquaient. Couverture relevée : **10 ISIN Amundi sur 10**, en FR, LU et IE, y compris tous les PEA
à swap. Ses répartitions somment à **99,9998 %** — bien plus près de 100 qu'extraETF (99,43 % à
99,96 %) sans l'atteindre : le reliquat devient du « non attribué » comme pour toute autre source,
et rien n'est renormalisé ([D-69](#d-69)). Elle est gratuite, sans clé, interrogeable par ISIN, et elle porte une **date d'arrêté
propre à l'indice** (`INDEX_BREAKDOWNS_AS_OF_DATE`), distincte de celle du fonds.
**Pourquoi la géographie seulement :** ses secteurs sont du **GICS** — `Information Technology`,
`Health Care`, `Consumer Discretionary` — là où [D-65](#d-65) impose **les 11 secteurs
Morningstar, et une seule nomenclature**. Les mélanger donnerait « un total juste et une
répartition fausse » : 5 points d'écart mesurés sur la technologie, c'est le **piège n° 16** du
[comparatif](composition-des-etf.md). **Les secteurs d'un actif servi par le secours restent donc
non couverts**, et l'écran le dit.
**La fragilité, assumée et isolée :** le service rend des **libellés anglais**
(`"United States"`), pas des codes — le seul des quatre critères qu'il rate. La traduction en code
ISO 3166-1 passe par une **table déclarée, datée et sourcée** dans `parametres/`, de la même forme
que `secteurs.toml` et `zones.toml` ([D-58](#d-58)). C'est l'échappatoire que la **règle 4** de
`CLAUDE.md` autorise explicitement — « si c'est inévitable, isoler et marquer comme fragilité » — et
la **règle 5** s'applique : un libellé non reconnu est **affiché**, jamais rangé par défaut. La
fragilité est bornée (47 libellés de pays relevés sur 10 fonds, tous normalisables) et **sans danger
silencieux** : un nom qu'on ne reconnaît pas ne peut pas être rangé au mauvais endroit.
**Écarte :** les **fiches mensuelles PDF** d'Amundi, dont l'URL est pourtant libre et prévisible par
ISIN. Leur texte n'est **pas extractible** — polices sous-ensemble sans table de correspondance,
**77 chaînes lisibles sur 311** — et résoudre les polices casserait en silence au premier
changement de sous-ensemble. Le service JSON rend la même donnée sans ce risque.
**Le piège à ne jamais approcher :** le même service expose `composition.compositionFields`, qui est
la **liste des lignes détenues**. [D-63](#d-63) et [D-64](#d-64) l'interdisent : pour un fonds à
swap, elle décrit le panier de collatéral et non l'exposition. Ne jamais l'appeler.
**Le piège de l'interface :** le champ de requête est `breakDown` **au singulier**, et ses valeurs
sont `INDEX_COUNTRIES` / `INDEX_SECTORS` / `INDEX_ASSETCLASSES`. Mal nommé, **le service répond 200
avec une liste vide** au lieu de se plaindre. Un test doit donc vérifier qu'une réponse **non vide**
arrive, et pas seulement qu'il n'y a pas d'erreur.
**Limite de couverture, et pourquoi elle est acceptable :** la source ne connaît **que les fonds
Amundi** — un ISIN iShares rend « aucun produit ». Le trou d'extraETF est celui des fonds **à
swap**, et dans l'univers du PEA ils sont très majoritairement des fonds Amundi (dont l'ancien
Lyxor). Xtrackers a été re-testé le 2026-09-30 : **aucune route JSON devinable**, tout son site est
rendu côté client — ce qui confirme le constat de l'étape 7. Un fonds à swap d'un autre émetteur
reste donc non couvert, avec son montant affiché, et la déclaration à la main ([D-71](#d-71))
demeure son recours.

---

*Arbitrage du propriétaire du 2026-10-01, sur la mise en route de l'application.*

### D-78 · 2026-10-01 · Un fichier de configuration est un format de stockage, jamais une interface · Validée
**Décision :** **toute** configuration dont l'application a besoin se fait **dans l'application**,
par un écran. Le fichier TOML reste le **format de stockage** — lisible, vérifiable à la main, hors
du dépôt — mais il **cesse d'être le moyen de configurer**. Quatre conséquences, qui sont les
termes exacts de l'engagement :

1. **chaque réglage a un écran** : le rôle des comptes espèces, le ticker et la devise d'un actif,
   son type, son TER, son `contenu` ([D-71](#d-71)), sa source de secours ([D-77](#d-77)), et tout
   réglage ajouté plus tard. Aucun n'est accessible **seulement** par le fichier ;
2. **l'édition à la main reste possible**, pour qui la préfère et pour réparer sans l'interface.
   L'application **ne doit jamais écraser** ce qui a été écrit à la main — c'est déjà la règle pour
   les poches déclarées, et un test la garde ;
3. **l'application propose, l'utilisateur décide.** Quand elle peut deviner un réglage, elle le
   **propose** avec sa raison, et ne l'applique pas sans accord. C'est ce qui réconcilie cette
   décision avec celles qui exigent qu'un choix soit explicite ([D-70](#d-70),
   [D-71](#d-71), [D-77](#d-77)) : ce qu'elles interdisent, c'est de **basculer en silence**, pas
   de demander en un clic ;
4. **aucune étape n'est terminée** avec un réglage qui n'existe qu'en fichier.

**Raison :** le propriétaire, le 2026-10-01, après avoir vu arriver un quatrième réglage à écrire
à la main : « je trouve les étapes de configuration particulièrement chiantes et peu pratiques […]
pour ton truc de `secours = "amundi"`, je ne vais jamais de la vie demander à l'utilisateur de
faire ça ». Il a raison, et le constat qui l'accompagne est plus grave que l'inconfort : **une
bidouille qui fait peur n'est pas seulement désagréable, elle fait douter de l'application
entière.** Or ce projet a une exigence de confiance dans les chiffres ; elle ne survit pas à une
mise en route qui ressemble à du dépannage.

**Ce qu'elle corrige, et qui était une erreur d'analyse :** [D-38](#d-38) a choisi le TOML parce
qu'il « se lit et se corrige sans être développeur ». C'est vrai, et **ce n'était pas la bonne
question**. Qu'un format soit lisible ne rend pas l'acte d'éditer un fichier acceptable pour
quelqu'un qui n'édite jamais de fichiers. D-38 reste valide sur le **format** ; elle est corrigée
sur ce qu'on en déduisait.

**Le cas d'école, et pourquoi il était évitable :** la source de secours ([D-77](#d-77)) a été
livrée comme un champ TOML, alors que **l'application a déjà tout pour la proposer elle-même** —
elle sait quels fonds sont non couverts, et elle sait reconnaître un fonds Amundi puisque la source
répond « aucun produit » pour les autres émetteurs. L'écran peut donc dire : « ce fonds n'est pas
couvert ; Amundi publie la répartition de l'indice qu'il suit — l'utiliser ? », et rien à taper. La
décision reste explicite, le geste devient un clic.

**Écarte :** l'assistant en ligne de commande comme réponse suffisante — il écrit un fichier bien
commenté, ce qui est mieux que rien, mais renvoie quand même vers un éditeur de texte ; et le
report de ces écrans à l'étape 10, où la feuille de route les plaçait vaguement. Le propriétaire a
arbitré pour l'**étape 9, dès le début** : concevoir l'interface sans la configuration reviendrait
à la concevoir pour quelqu'un qui a déjà tout configuré, c'est-à-dire pour personne — et c'est
justement pendant l'étape 9 qu'il utilise l'application sur ses données.

**La contrainte technique à traiter à l'étape 9, dite d'avance :** un écran qui écrit dans le
fichier doit le **relire et le réécrire sans perdre les commentaires** que les assistants y
mettent — ce sont eux qui rendent le fichier compréhensible à la main, et les perdre viderait le
point 2 de son sens. C'est faisable et ce n'est pas gratuit : à traiter comme un sujet, pas comme
un détail.

---

*Hors étape (2026-10-01). Un changement de cap rendu par le propriétaire après la découverte de
l'export officiel de Trade Republic.*

### D-79 · 2026-10-01 · L'export officiel de Trade Republic devient la porte d'entrée des opérations · Validée
**Décision :** les opérations sont lues dans le fichier **« Export des transactions »** que Trade
Republic fournit dans son application depuis avril 2026, et non plus dans l'export de pytr. Un
**nouvel adaptateur** le transforme en format pivot ; le moteur ne change pas ([D-26](#d-26)).
L'utilisateur télécharge le fichier dans l'application et le donne à Pastory : **aucune connexion,
aucun identifiant**. Le relevé du fichier est dans [export-officiel.md](export-officiel.md).

**Raison :** trois gains d'un coup, chacun suffisant.
1. **La clause des conditions générales ne s'applique plus.** [D-49](#d-49) acceptait d'utiliser
   pytr malgré l'interdiction des « interfaces non fournies par Trade Republic ». Le fichier est
   fourni par la banque elle-même : le projet peut être publié sans cette réserve.
2. **Des données plus sûres.** La poche, la quantité, le prix, les frais et les taxes sont des
   **colonnes**, là où pytr obligeait à les lire dans des textes allemands ([D-09](#d-09)), à
   déduire la poche d'un compte ([D-40](#d-40)) et à surveiller deux écritures des nombres dans un
   même fichier. Il ne reste qu'un champ informatif lu dans un texte.
3. **Une mise en route sans dépannage.** Plus de commande en ligne, plus de PIN, plus de
   comptes à nommer : c'est l'esprit de [D-78](#d-78), et c'est ce qui rend l'application
   utilisable par l'utilisateur type ([D-62](#d-62)).

Le propriétaire : « le changement de cap est assuré, j'ai confiance en les données de Trade
Republic ».

**Ce qu'elle remplace :** la première moitié de [D-49](#d-49) (« pytr reste l'unique porte
d'entrée »). **La seconde moitié reste valide** : aucun cours ne passe par Trade Republic.

**Ce qui devient propre à l'ancien adaptateur**, et ne s'applique pas au nouveau : le JSON
source et le CSV de recoupement ([D-06](#d-06), [D-42](#d-42)), les comptes nommés
([D-10](#d-10)), la poche déduite du compte ([D-40](#d-40)) et du code `XF` ([D-16](#d-16)), et
les deux tiers de [D-41](#d-41) et [D-25](#d-25) qui portent sur la connexion. Le principe de
[D-40](#d-40) — **la poche n'est jamais devinée** — reste entier : elle est désormais donnée.

**Ce qui ne change pas :** un type inconnu est affiché, jamais rangé par défaut (règle 5 de
`CLAUDE.md`) — et c'est plus important qu'avant, puisque **aucune liste des types n'est
publiée**. Les lignes d'espèces, qui sont dans le même fichier avec leurs IBAN et leurs
commerçants, sont classées par leur seul `type` et jamais lues plus loin ([D-11](#d-11)).

**Reste ouvert :** le sort de pytr pour la **photo du portefeuille** ([D-46](#d-46)), que l'export
ne fournit pas — [Q-50](questions-ouvertes.md) ; et ce que le fichier dit des opérations encore
jamais vues (dividende, vente, titres reçus, Saveback) — [export-officiel.md §7](export-officiel.md).
**Écarte :** garder pytr comme porte d'entrée principale ; lire les deux sources à égalité, ce qui
doublerait le code à maintenir pour un gain nul une fois l'adaptateur vérifié.

### D-80 · 2026-10-01 · Tout est trouvé automatiquement ; la fiabilité passe par la transparence, pas par la validation · Validée
**Décision :** l'utilisateur ne fait **qu'une chose** : télécharger l'export dans l'application
Trade Republic et le **déposer dans un dossier de Pastory**. Tout le reste — ticker, devise, type,
frais courants, contenu d'un fonds, source de composition, date d'ouverture du PEA — est **cherché
et appliqué par l'application**, à partir d'une source fiable. Trois règles en font une décision
sûre, et non un pari :

1. **Chaque valeur trouvée porte sa source et sa date**, visibles là où elle sert. Une valeur
   appliquée sans être montrée reste interdite ([D-70](#d-70), [D-72](#d-72)).
2. **Chaque valeur trouvée passe un contrôle** avant d'être appliquée : devise d'un cours
   ([D-48](#d-48)), fourchette d'un TER ([D-61](#d-61)), vraisemblance d'une composition
   ([D-70](#d-70)). Une valeur qui échoue n'est **pas** appliquée.
3. **Sans source fiable, rien n'est inventé ni demandé** : le trou est affiché, expliqué, là où il
   se voit (« non couvert », « TER inconnu »), et le reste du portefeuille s'affiche quand même. Une
   correction à la main reste **possible**, jamais **nécessaire**.

**Raison :** la vision du propriétaire, le 2026-10-01 : « j'aimerais automatiser tout sauf le
chargement des données Trade Republic et le dépôt dans un dossier de l'application. Tout le reste
devrait idéalement être trouvé quelque part, de manière fiable, plutôt que de laisser l'utilisateur
se débrouiller. Je comprends que cela peut créer des incertitudes […] mais pour que l'appli soit
vraiment intéressante, il faut qu'elle mêle fiabilité et facilité d'utilisation. » Un utilisateur
non connaisseur ne sait de toute façon pas juger un ticker ou un TER qu'on lui demande de valider :
lui faire cliquer « valider » ne le rend pas plus fiable, cela déplace seulement la responsabilité.
Ce qui protège réellement contre une valeur fausse, ce sont les **contrôles** et la **visibilité**.

**Ce qu'elle change dans les décisions précédentes :**
- [D-78](#d-78), règle 3 (« l'application propose, l'utilisateur décide ») devient : **l'application
  trouve, applique et montre ; l'utilisateur peut corriger**. Les écrans de réglages de l'étape 9
  deviennent des écrans de **correction**, facultatifs ([conception-interface.md §6](conception-interface.md),
  à réécrire à l'étape 9) ;
- la **validation** exigée par [D-48](#d-48) (ticker), [D-55](#d-55) (type), [D-61](#d-61) (TER),
  [D-59](#d-59) (date du PEA), [D-71](#d-71) (contenu) et [D-77](#d-77) (source de secours) est
  remplacée par les règles 1 et 2. Les raisons de ces décisions restent vraies — la Xetra a des TER
  en retard, une recherche par ISIN peut renvoyer des dollars : c'est pourquoi la règle 2 existe ;
- [D-71](#d-71) écartait l'`asset_class` d'extraETF parce qu'il s'était révélé **faux** : cela reste
  vrai. Une source jugée non fiable n'est pas promue par cette décision ; elle reste écartée, et le
  trou s'affiche.

**Écarte :** la validation d'un clic comme passage obligé ; un réglage requis pour afficher le
reste ; une valeur « par défaut » sans source pour combler un trou.
**Conséquence pour l'étape 8 quater :** son critère de réussite est le **nombre de valeurs que
l'application ne sait pas trouver** sur un portefeuille type, et non plus le nombre de clics.

### D-81 · 2026-10-05 · pytr est retiré entièrement ; les quantités se comparent à l'écran de la banque · Validée
**Décision :** une fois prouvé que l'export officiel donne les mêmes opérations que pytr sur la
même période (étape 8 ter), **pytr et tout ce qui en dépend disparaissent** : l'adaptateur,
les commandes `rafraichir`, `comptes` et `positions-reelles`, le rapprochement automatique avec
les positions réelles, la configuration des comptes (`comptes.toml`, rôles et corrections de
poche) et la dépendance elle-même. Pour confirmer les quantités, Pastory les affiche par actif et
par poche, et le cahier de vérification demande de les comparer **à l'écran de l'application**
Trade Republic.
**Raison :** [Q-50](questions-ouvertes.md) (a). Le rapprochement n'a jamais couvert le PEA
([Q-26](questions-ouvertes.md)), qui est la poche principale de l'utilisateur type français ; il
exigeait une connexion complète (numéro, PIN, confirmation) à chaque appel ; et il était la
dernière raison de garder une interface non officielle, que [D-79](#d-79) écarte.
**Écarte :** garder pytr pour cette seule commande, facultative — la clause des conditions
générales serait revenue pour ceux qui l'utilisent, et le PEA serait resté non couvert ; lire le
relevé de titres officiel en PDF, qui reste possible plus tard sans rien bloquer, mais oblige à
lire un texte (règle 4 de `CLAUDE.md`).
**Conséquence assumée :** la limite connue de [D-15](#d-15) — des titres entrés **sans aucune
ligne** dans l'historique — n'est plus détectée automatiquement. Elle l'est par la comparaison à
l'écran de la banque.
**Remplace :** [D-10](#d-10) et [D-40](#d-40) pour leur moitié « compte » (la poche est
désormais écrite sur chaque ligne de l'export) ; [D-16](#d-16) (la crypto est désignée par
`asset_class`) ; [D-25](#d-25) et [D-41](#d-41) (plus aucun identifiant) ; [D-42](#d-42) (plus
aucun texte à recouper) ; [D-46](#d-46) et [D-47](#d-47) (plus de photo du portefeuille).

### D-82 · 2026-10-05 · Le type d'un actif est une donnée de la banque · Validée
**Décision :** le type d'un actif vient de la colonne `asset_class` de l'export officiel, sans
validation : `FUND` → ETF, `STOCK` → action, `CRYPTO` → crypto. L'utilisateur peut le corriger,
il n'a jamais à le faire. Toute autre valeur (`BOND`, `DERIVATIVE`, `PRIVATE_FUND`, relevées par
la recherche, ou une valeur jamais vue) est **affichée** et n'est pas traduite.
**Raison :** [Q-51](questions-ouvertes.md) (a). Les trois valeurs ont un sens sans ambiguïté, et
la colonne est remplie sur **chaque** ligne d'actif, y compris un actif reçu sans achat — ce qui
manquait à `instrumentType` de pytr et motivait [D-55](#d-55). [D-80](#d-80) va dans le même
sens : une validation qu'un non-connaisseur ne sait pas juger ne rend pas la valeur plus sûre.
**Écarte :** une proposition à valider d'un clic ; la déclaration à la main.
**Ce qui reste vrai de D-55 :** `asset_class` ne distingue pas un ETF de niche d'un ETF large ; le
spread estimé reste celui de la classe ([D-56](#d-56)).
**Réalisation :** l'étape 8 ter lit la classe et la garde dans le rapport de lecture ; son
application aux estimations est faite à l'étape 8 quater.
**Remplace :** [D-55](#d-55), pour l'origine du type.

### D-83 · 2026-10-05 · Le montant réglé reste vide quand la banque ne le donne pas · Validée
**Décision :** le champ `montant_regle` du format pivot devient **facultatif**. L'export officiel
ne donne pas le montant réellement débité ou crédité : il reste vide, et le contrôle « montant
réglé » n'est pas fait. Le contrôle `quantité × prix = montant brut`, qui compare deux colonnes
indépendantes, reste fait sur chaque achat et chaque vente.
**Raison :** [Q-52](questions-ouvertes.md) (b). Calculer le champ à partir du brut, des frais et
des taxes produirait une valeur qui **ressemble** à une donnée de la banque sans en être une — ce
que la règle 6 de `CLAUDE.md` demande d'éviter — et le contrôle deviendrait une tautologie.
**Vérifié avant de trancher :** sur les 72 opérations communes de l'export officiel et de l'export
pytr d'un second utilisateur, brut ± frais ± taxes retombe **exactement** sur le montant réglé que
pytr annonçait. Les colonnes de l'export sont donc cohérentes avec ce qui a été débité ; seule
manque la colonne qui permettrait de le contrôler.
**Écarte :** un montant réglé calculé et marqué `deduction`.
**Conséquence :** le moteur ne change pas — il n'a jamais lu ce champ.

### D-84 · 2026-10-05 · Le brut d'un dividende est celui de la banque ; sa limite est affichée · Validée
**Décision :** le montant brut d'un dividende est la colonne `amount` de l'export officiel, et sa
taxe la colonne `tax`. Un **message permanent**, partout où les dividendes s'affichent, dit que
pour certains pays ce brut est **déjà diminué d'une retenue étrangère que la banque ne montre
pas**, et que le gain et les taxes de ces dividendes sont alors légèrement sous-estimés, le net
restant exact.
**Le constat :** sur l'export d'un second utilisateur, comparé ligne à ligne à son export pytr, le
net de **chaque** dividende concorde. Mais pour les actions **néerlandaises**, `amount` vaut
environ 85 % du brut que pytr lisait : la retenue des Pays-Bas (15 %) est déduite avant `amount`
et n'apparaît pas dans `tax`. Pour les actions françaises et américaines, `amount` est bien le
brut et `tax` contient toute la retenue. **Rien dans le fichier ne distingue les deux cas.**
Aucun importeur connu (Portfolio Performance compris) ne le corrige : tous prennent `amount` pour
le brut. Le relevé PDF de la banque, lui, montre la retenue néerlandaise sur une ligne à part.
**Raison :** [Q-53](questions-ouvertes.md) (a). C'est la seule option qui n'invente rien et qui
garde les dividendes dans les calculs : le chiffre affiché est celui de la banque, et sa limite est
dite.
**Écarte :** reconstituer le brut par pays (`amount ÷ 0,85` pour un ISIN néerlandais), qui
demanderait une table de taux datée et sourcée ([D-58](#d-58)), alors que le pays d'un ISIN n'est
pas toujours celui de l'impôt et qu'une retenue peut être réduite par convention — le risque est
d'**inventer** un brut faux ; ne pas traiter les dividendes, qui retirerait tous les dividendes
des calculs pour un écart de quelques pour cent sur certains.
**Limite assumée :** sur les dividendes concernés, le gain est sous-estimé de la retenue
étrangère (environ 15 % du dividende néerlandais) et les taxes payées le sont du même montant.

---

*Étape 8 quater (2026-10-05). Les réglages se trouvent seuls (D-80) : ce que la recherche a
établi, et ce que le propriétaire a tranché. Le comparatif est
[reglages-automatiques.md](reglages-automatiques.md).*

### D-85 · 2026-10-05 · Une cotation n'est retenue que si elle retombe sur le prix payé · Validée
**Décision :** la cotation de chaque actif est **cherchée** par l'application, puis **contrôlée par
le prix que la banque a fait payer** : sur les six derniers achats ou ventes, le cours de clôture
du candidat, le jour même, doit retomber sur le prix d'exécution à une tolérance près (écart
médian). Trois étages, du plus sûr au moins sûr :
1. **par l'ISIN**, une cotation en euros qui a des cours : la recherche l'associe à l'ISIN, et elle
   doit en plus retomber sur le prix payé quand l'export en donne un ;
2. **par le nom**, une cotation en euros : elle doit retomber sur le prix payé **et** suivre, une
   fois convertie, la cotation que la recherche par ISIN a trouvée dans une autre monnaie (à 1 %
   près) ;
3. pour une crypto, `CODE-EUR` (le code donné par la banque), contrôlé par le prix payé.

La tolérance dépend du type et du nombre d'ordres comparés (ETF 6 / 4 / 2 %, action 12 / 6 / 4 %,
crypto 20 / 10 / 5 % pour 1–2, 3–5 et 6 ordres ou plus). Une cotation trouvée est **gardée pour
toujours** (`cache/reglages.csv`) : ses cours le sont aussi (D-50), et changer de ticker en route
mêlerait deux places dans une même série. `pastory oublier-reglages` la fait rechercher.
**Raison :** mesuré le 2026-10-05 sur 62 ISIN publics, la recherche par ISIN ne donne une
cotation en euros que pour 53 % d'entre eux — elle renvoie d'abord **Londres en dollars** pour
presque tous les ETF irlandais, et New York pour les actions américaines — mais ces 33 cotations
en euros sont **toutes** le bon instrument. La recherche par nom trouve les autres (85 %), en
mêlant les parts d'un même fonds : le prix payé, donné par la banque sur chaque ordre, est le
contrôle qui manquait. Il attrape les pence (− 99 %), un autre fonds sur le même indice (+ 73 %
et plus), la part couverte, le dollar (− 14 % au change de 2026) ; le contrôle de change attrape
les parts capitalisante et distribuante, que le prix payé, trop bruité, ne sépare pas toujours
(1,6 à 2,6 % d'écart).
**Écarte :** prendre le premier résultat (47 % de trous) ; le premier résultat en euros (un
pseudo-ticker de Stuttgart sans aucun historique, choisi 8 fois sur 62) ; appliquer une cotation
trouvée par le nom sans contrôle.
**Limites connues :** un actif sans aucun achat ni vente (titres reçus seulement) ne peut être
retenu que par son ISIN, avec une réserve affichée ; deux classes d'une même société (Alphabet A
et C, 0,4 % d'écart) ne se distinguent pas par le prix.
**Remplace :** la validation de [D-48](#d-48), déjà retirée par [D-80](#d-80). La devise reste
vérifiée, jamais convertie.

### D-86 · 2026-10-05 · La date d'ouverture du PEA se lit dans l'histoire de ses mouvements · Validée
**Décision :** la date d'ouverture du PEA est trouvée dans les mouvements d'espèces du compte
`PEA` de l'export — **leur jour et leur sens, jamais leur montant** ([D-11](#d-11)). Le plan
commence au premier crédit (versement `TRANSFER_IN`, ou prime d'ouverture `PEA_MARKETING`) ; une
sortie (`TRANSFER_OUT`) **avant cinq ans clôt le plan** (CMF art. L. 221-32), et le crédit suivant
en ouvre un nouveau. Contrôle : aucun titre n'est entré sur le PEA avant cette date (sauf dans un
plan clos) ; sinon le plan est plus ancien que les exports, et la date est un trou. La réserve est
affichée en permanence : un PEA transféré d'une autre banque, ou des exports qui ne remontent pas
à l'ouverture, donnent une date trop récente.
**Raison :** le propriétaire, le 2026-10-05, sur ses propres données : une prime d'ouverture,
une sortie d'espèces six jours plus tard, une seconde prime le même jour, puis ses premiers
versements une semaine après. « J'ai ouvert une fois, puis fermé et rouvert mon PEA : c'est la
réouverture qui ouvre mon PEA actuel. » La première règle essayée — le premier `TRANSFER_IN` —
donnait la date de son premier versement, une semaine trop tard ; la date qu'il avait écrite à la
main dans `fiscalite.toml` est celle que la nouvelle règle retrouve seule.
**Écarte :** le premier `TRANSFER_IN` seul ; le premier mouvement de l'export quel qu'il soit (il
ignore la clôture) ; ne rien proposer dès qu'une prime précède un versement (un trou pour presque
tout nouvel utilisateur de la banque).
**Remplace :** [D-59](#d-59) pour l'**origine** de la date (déclarée → trouvée). Le calcul de
l'impôt ne change pas.

### D-87 · 2026-10-05 · L'hypothèse « aucun retrait passé » est vérifiée, sans lire de montant · Validée
**Décision :** [D-59](#d-59) approche le gain du PEA depuis les titres sous l'hypothèse « aucun
retrait n'a jamais été fait ». Les sorties d'espèces du PEA postérieures à son ouverture sont
désormais relevées — **leur date seulement** — et, s'il y en a, l'hypothèse affichée est remplacée
par ce que montrent les exports : « contredit : de l'argent est sorti du PEA le … ».
`pastory actifs` le dit aussi.
**Raison :** la piste que la feuille de route demandait de soumettre. Le propriétaire a retenu la
vérification (a) : elle rend l'hypothèse contrôlable sans toucher à [D-11](#d-11).
**Écarte :** calculer le gain du plan comme le fisc (valeur − versements nets), qui demanderait
de lire les montants d'espèces — une décision nouvelle, non prise ; ne rien changer.

### D-88 · 2026-10-05 · Pour une action américaine, Francfort avant Xetra · Validée
**Décision :** quand deux cotations en euros d'un même titre passent les contrôles avec des écarts
comparables (à 1 point près), la place décide : **Francfort d'abord pour un ISIN américain**,
Xetra d'abord pour les autres.
**Raison :** Francfort cote jusque vers 22 h, au plus près de la clôture de New York et de l'heure
où ferme la banque ; Xetra ferme à 17 h 30. Mesuré sur cinq ans pour neuf actions américaines :
± 1,5 à 2 % du cours américain converti au pire jour à Francfort, ± 2,6 à 4,9 % à Xetra, et des
clôtures figées sur Xetra pour un titre peu échangé.
**Écarte :** Xetra pour tout. Et le départage au plus petit écart : entre deux places du même
titre, l'écart tient au hasard des heures de clôture.

### D-89 · 2026-10-05 · Le contenu d'un fonds vient d'extraETF, recoupé par le code CFI · Validée
**Décision :** le contenu d'un fonds ([D-71](#d-71)) est trouvé chez extraETF, dans son **code de
classe d'actifs et son libellé** (`asset_class_id`, `asset_class_name`), traduits par une table
datée et sourcée (`parametres/contenus.toml`) qui exige qu'ils concordent : 2 « Aktien » →
actions, 3 « Anleihen » → obligations, 4 « Rohstoffe » → matières premières. Le **code CFI** que
les plateformes déclarent au registre public de l'ESMA sert de **témoin** : s'il concorde, c'est
dit ; s'il se tait (30 % des fonds), le contenu est retenu « non recoupé » ; s'il contredit, rien
n'est retenu et les deux réponses sont affichées. Un contenu « actions » trouvé est montré mais
**ne s'applique pas** : il ferait passer le fonds avant sa composition, et lui ferait perdre ses
pays et ses secteurs. Le monétaire, les fonds multi-actifs et l'immobilier ne sont pas traduits
([Q-60](questions-ouvertes.md)).
**Raison :** mesuré le 2026-10-05 sur 310 fonds : le couple code-libellé d'extraETF est juste
**307 fois sur 307** trouvés, y compris là où le code CFI se trompe ; il est juste sur les cinq
fonds du propriétaire. Le code CFI, normé mais déclaré sans contrôle, a une trentaine d'erreurs
franches sur 3 574 ISIN : il ne décide jamais seul, mais il transforme chacune de ses erreurs en
trou affiché, jamais en chiffre faux.
**Ce qu'elle corrige :** [D-71](#d-71) avait écarté l'`asset_class` d'extraETF, « faux sur deux
actifs sur trois ». L'hypothèse la plus probable : la table des codes n'est publiée nulle part, et
le sens deviné des nombres était décalé d'un rang — ce qui donne exactement deux erreurs sur un
trio actions, obligations, or. Lu avec son libellé, le code ne se devine plus.
**Écarte :** la colonne `PRODUCT TYPE` de la liste de Xetra (seulement « ETC », et des ETF de
matières premières y sont typés « ETF ») ; la répartition par classes d'extraETF (un fonds
monétaire à swap y est à 99,9 % en actions : son collatéral) ; OpenFIGI (toujours « fonds ») ; le
code CFI seul.

### D-90 · 2026-10-05 · Le TER vient de l'émetteur, puis de Xetra ; une source sans date est écartée · Validée
**Décision :** les frais courants d'un ETF viennent d'abord de **l'émetteur** quand il les publie
— le service produit d'Amundi, celui de [D-77](#d-77), champ `TER` en pour cent, avec sa **date
d'effet** — puis de la liste de Xetra ([D-61](#d-61)). Contrôle : la fourchette de vraisemblance ;
quand les deux sources répondent et diffèrent, l'émetteur fait foi et l'écart est dit. Un TER sans
date n'est pas retenu ([D-58](#d-58)). La date d'Amundi s'affiche « taux en vigueur depuis le »,
qui n'est pas la même chose que l'état d'une liste.
**Raison :** les ETF « PEA » de droit français sont absents de Xetra. Mesuré le 2026-10-05 : le
service d'Amundi répond pour ses 116 ETF éligibles au PEA, et sa valeur est **égale au DIC sur les
116** ; sur 402 fonds présents dans les deux sources, 394 concordent et les 8 écarts donnent
raison à l'émetteur (Xetra en retard). Le propriétaire a écarté la liste de BlackRock, qui couvre
les ETF iShares « Swap PEA » également absents de Xetra : elle n'a **pas de date**, et une part
couverte s'y écarte de son DIC.
**Écarte :** BNP Paribas Easy (aucune interface lisible, et ses ETF PEA sont dans la liste de
Xetra) ; la liste de BlackRock, sans date.
**Limite connue :** la date d'effet d'Amundi (`TER_EFFECTIVE_DATE`) n'est pas un nom documenté :
s'il disparaît, le TER n'a plus de date et n'est plus retenu — un trou, jamais un chiffre faux.

### D-91 · 2026-10-05 · La source de secours est essayée d'elle-même · Validée
**Décision :** quand la source principale ne sait pas ouvrir un ETF, le service d'Amundi
([D-77](#d-77)) est **essayé de lui-même** ; il ne répond que pour ses propres fonds. Une
correction `secours = "aucun"` le refuse pour un actif, `secours = "amundi"` l'impose. Essayé de
lui-même et muet, il se tait : c'est le motif de la source principale qui s'affiche.
**Raison :** [D-80](#d-80) et le cas d'école de [D-78](#d-78). La condition que [D-72](#d-72)
posait pour mélanger deux sources — la source et la règle de pays de chaque actif affichées ligne
par ligne — est remplie depuis l'étape 8 bis.
**Remplace :** [D-77](#d-77) pour le déclenchement (déclaré par actif → essayé de lui-même).

### D-92 · 2026-10-05 · `actifs.toml` devient un fichier de corrections, que l'application ne réécrit jamais · Validée
**Décision :** l'assistant qui réécrivait `actifs.toml` disparaît. Le fichier ne contient plus
que des **corrections**, champ par champ et toutes facultatives : un ticker corrigé, un TER, un
type, un contenu, un spread, une répartition, un refus de secours. Ce qui est écrit l'emporte ; le
reste reste trouvé ; quand une correction contredit la source, les deux sont montrées côte à côte.
Une correction qui ne désigne aucun actif des exports est signalée. `pastory actifs` **montre**
chaque réglage avec sa source, sa date, ce qui a été vérifié — ou le motif du trou — et n'écrit
rien. Tout message qui renvoyait vers un fichier à éditer est réécrit pour dire ce qui manque et
pourquoi.
**Raison :** [D-78](#d-78) (point 2 : l'édition à la main n'est jamais écrasée) et [D-80](#d-80)
(une correction est possible, jamais nécessaire). Vérifié sur les données du propriétaire :
toutes les valeurs qu'il avait validées à la main sont retrouvées à l'identique par la recherche,
sauf la date d'ouverture du PEA, que la première règle donnait une semaine trop tard
([D-86](#d-86)).
**Écarte :** garder l'assistant en ligne de commande ; réécrire le fichier en y ajoutant les
valeurs trouvées (il redeviendrait une configuration).
**Précisée par [D-94](#d-94) (étape 9) :** « jamais réécrit » veut dire **jamais de lui-même**.
L'écran de correction écrit ce que l'utilisateur y a saisi, et rien d'autre.

---

*Étape 9 (2026-10-08). La réalisation de l'interface : trois arbitrages du propriétaire, rendus au
début de l'étape, avant toute ligne de code.*

### D-93 · 2026-10-08 · Python construit la page ; un dessin repris de la maquette trace les graphiques · Validée
**Décision :** l'interface Dash est construite **en Python** : chaque bloc, chaque texte, chaque
chiffre **mis en forme** (`pastory/vues/format.py`, une fonction par unité, conception-interface
§3.1). Les dessins — la courbe, les anneaux, les drapeaux, le planisphère, le logo — sont tracés
par un fichier JavaScript **repris de `maquettes/maquette.js`** (`pastory/vues/assets/dessin.js`).
Python pose les données d'un dessin dans un attribut `data-…` d'un élément vide, libellés déjà
écrits ; le script les trace, place la boîte de lecture qui suit la souris et les bulles d'aide.
**Il ne calcule rien et n'écrit aucun chiffre.**
**Raison :** Dash ne sait pas produire d'éléments SVG, or tous les dessins des maquettes en sont.
Les reprendre tels quels garde exactement ce que neuf passes de relecture ont arrêté — la boîte de
lecture a été essayée dans trois arrangements (conception-interface §3.2). Et la mise en forme
reste en Python, sous les tests, là où le piège des pour cent ([§3.1](conception-interface.md)) a
déjà produit un « 6264,00 % ».
**Écarte :** les graphiques Plotly fournis avec Dash, sans JavaScript écrit à la main — leur boîte
de lecture n'est pas celle retenue, et un anneau Plotly fait toujours le tour complet : il faudrait
le tromper par une part invisible pour ne pas renormaliser ([D-69](#d-69)) ; et la maquette entière
en JavaScript comme affichage, alimentée par Python — moins de code nouveau, mais la mise en forme
des chiffres sortirait des tests Python.
**Contrepartie assumée :** du JavaScript dans l'application, que [D-31](#d-31) espérait éviter.
Il est cantonné au dessin, et ce qui s'affiche en chiffres vient toujours de Python.

### D-94 · 2026-10-08 · L'écran écrit une correction, et rien d'autre, en gardant le fichier intact · Validée
**Décision :** l'écran de correction écrit dans `actifs.toml` (ou `fiscalite.toml` pour la date du
PEA) **un seul champ d'un seul actif**, celui que l'utilisateur vient de saisir. Le fichier est
relu et réécrit avec **tomlkit**, qui garde ses commentaires, son ordre et sa mise en page ; le
résultat passe par la **même lecture** que d'habitude (`config/actifs.py`, `config/fiscalite.py`
et leurs contrôles : devise, fourchette du TER…) **avant** de remplacer le fichier. Une saisie
refusée n'écrit rien et dit pourquoi. « Revenir à la valeur trouvée » efface la correction, et
rien d'autre.
**Raison :** [D-78](#d-78), point 2 — l'édition à la main reste possible et n'est jamais écrasée,
et les commentaires sont ce qui rend le fichier compréhensible à la main. Faire passer l'écriture
par la lecture existante garantit qu'un écran ne peut pas écrire un fichier que l'application
refuserait ensuite de lire.
**Écarte :** un éditeur de TOML écrit pour le projet — sans dépendance, mais plus de code et plus
de risques de casser un fichier écrit à la main ; et la réécriture complète du fichier depuis la
configuration en mémoire, qui perdrait les commentaires.
**Précise :** [D-92](#d-92) — l'application ne réécrit jamais ce fichier **d'elle-même** ; elle
n'y ajoute jamais une valeur trouvée.

### D-95 · 2026-10-08 · L'export se dépose dans l'application · Validée
**Décision :** l'écran d'accueil porte une **zone de dépôt** : l'utilisateur y glisse l'export
téléchargé dans l'application Trade Republic, Pastory le **copie dans le dossier de dépôt**
([D-80](#d-80)) et relit tout. Un fichier qui n'est pas un export est **refusé et n'est pas
copié**, avec la raison. L'écran montre aussi le dossier, avec un bouton pour l'ouvrir : y copier
un fichier à la main reste possible.
**Raison :** [D-78](#d-78) — un geste qui demande d'ouvrir un explorateur de fichiers et de
retrouver un dossier caché est exactement la mise en route qui ressemble à du dépannage. La
seule chose que l'utilisateur ait à faire doit se faire dans l'application.
**Écarte :** montrer seulement le chemin du dossier et un bouton « relire ».

### D-96 · 2026-10-08 · Chaque poche a sa couleur, la même partout · Validée
**Décision :** les trois poches reçoivent trois **teintes distinctes**, et non plus trois clartés
d'un même bleu : PEA **bleu** (`#4167ad`), CTO **bleu-vert canard** (`#14938d`), crypto **prune**
(`#76386a`). C'est **leur couleur** partout où elles apparaissent : l'anneau de la synthèse, la
pastille de leur nom (`jeton`), et tout écran à venir. Aucune n'est la sauge, la terracotta ni
l'ocre, réservées au gain, à la perte et à l'estimé. Le texte reste à l'encre : la couleur dit
l'identité, jamais le mot.
**Raison :** le propriétaire, en voyant l'anneau : les poches doivent être « plus distinguées »,
leur couleur doit « persister » et « évoquer la poche », en restant dans la direction
artistique. Le validateur du skill dataviz a donné raison à l'œil : les trois bleus d'avant
**échouaient**, trop peu saturés (ils se lisaient comme des gris) et le plus foncé hors de la
bande de clarté. La palette retenue a été **calculée**, pas choisie à l'œil : parmi les teintes
qui évoquent chaque poche, la plus sobre qui passe tous les contrôles sur le fond des blocs —
séparation sous vision daltonienne 11,0 (cible 8), vision normale 15,3 (plancher 15), contraste
d'au moins 3:1.
**Écarte :** un bleu et un violet de même clarté (indiscernables pour un daltonien : écart de 1 à
3) ; des teintes vives, hors de l'esprit papier et encre ; la couleur du texte de la poche, qui
ferait dépendre la lecture de la couleur.
**Limite connue :** sur le fond de page (`--papier`), le bleu-vert est à 2,95:1, juste sous le
seuil ; il n'y est jamais seul — le nom de la poche l'accompagne toujours.
**Amendée par [D-98](#d-98) (2026-10-09) :** le principe demeure — une couleur par poche, la même
partout, jamais seule à porter le nom —, mais les trois teintes deviennent **trois bruns
d'encre**, et l'anneau une barre empilée.

### D-97 · 2026-10-09 · La prédiction de l'évolution rejoint l'étape 9 bis · Validée
**Décision :** la simulation Monte-Carlo de [D-27](#d-27), prévue à l'étape 12, devient une
section de l'interface, « **Prédiction de l'évolution** », réalisée à l'étape **9 bis** avec la
refonte de l'identité visuelle. Ses entrées : une valeur de départ (par défaut le **capital brut**
du portefeuille, modifiable), un taux annuel, une durée, un versement mensuel. Son résultat : une
courbe et le montant atteint ; avec l'option « taux aléatoire », **10 000 simulations** résumées
par les quantiles 5 %, 25 %, 50 %, 75 % et 95 %. D-27 tient toujours : rien d'autre n'en dépend,
et elle ne lit du portefeuille que sa valeur de départ.
**Raison :** le propriétaire, en fin d'étape 9.4 : la section fait partie de l'application qu'il
veut utiliser, pas d'une étape lointaine après la publication.
**Reste à trancher :** la loi des rendements et le lien entre le taux et la dispersion
([Q-61](questions-ouvertes.md)). Rien n'est codé avant.

### D-98 · 2026-10-09 · L'identité de Pastory : un livre ancien relié · Validée
**Décision :** l'interface prend la direction artistique d'un **livre ancien relié, à la dorure
discrète** — reliure brun profond (navigation, couverture), pages en papier crème (contenu), or en
touches rares. La métaphore passe par la **structure et la typographie**, jamais par l'imitation
de matières : ni texture, ni ombre, ni dégradé métallique, ni relief. Tout est fixé par la
[charte graphique](charte-graphique.md), qui fait référence, et toutes les valeurs vivent dans
un seul fichier de thème (`pastory/vues/assets/theme.css`). Concrètement :
- l'accueil devient la **couverture**, et chaque session s'ouvre sur elle ; on en sort par
  « Ouvrir le livre » (une animation, rejouée à chaque ouverture depuis [D-101](#d-101)) ;
- les onglets deviennent des **chapitres numérotés** (I à IV, V pour les projections à venir),
  chacun ouvert par son numéro, son titre et une phrase ; le détail des calculs devient l'**annexe** ;
- l'onglet actif est marqué d'un **signet** ; la bande d'état devient le **colophon**, sans rien
  perdre de ses informations ;
- les blocs perdent leurs cadres, les indicateurs leurs barres de couleur ; on sépare par
  l'espace et le filet ;
- EB Garamond (titres, grand chiffre) et IBM Plex Sans (données) ; chiffres à chasse fixe partout ;
- la palette du propriétaire, plus six variantes **mesurées** pour le texte (la sauge et l'ocre de
  la consigne échouent au niveau AA des WCAG sur le papier) ;
- les poches en **trois bruns d'encre** (amende [D-96](#d-96)), validés en rampe par le
  validateur du skill dataviz ; l'anneau devient une **barre empilée fine** ;
- le logo : un livre fermé en aplat d'or, un signet qui dépasse (variante B, choisie parmi trois).
**Raison :** le propriétaire, à l'ouverture de l'étape 9 bis : l'application s'appelle *Past +
Story*, elle raconte l'histoire d'un patrimoine ; l'interface de l'étape 9 était propre mais sans
caractère. Pour les poches, arbitrage rendu en séance : la sauge et l'ocre, proposées dans la
consigne, ont déjà un sens partout ailleurs (gain, estimé), et une poche sauge se lirait comme un
état. Les trois bruns passent le plancher de vision normale que les trois bleus d'avant D-96
manquaient (écarts 19,4 et 17,9, plancher 15).
**Écarte :** deux ou trois pistes concurrentes en maquette, prévues par la feuille de route — la
consigne du propriétaire fixait une direction précise ; les trois fonds essayés à la fin de
l'étape 9 (`maquettes/apercus-fond/`, papier épais, registre, vergé), que la règle « aucune
texture » écarte ; un mode sombre (finalement admis par [D-100](#d-100), dans la même identité).
**Limite connue :** une rampe de bruns n'a pas la saturation d'une palette catégorielle : une
poche n'est donc **jamais** désignée par sa seule couleur, son nom est toujours écrit à côté.

### D-99 · 2026-10-09 · La valeur des actifs est le point d'entrée de la synthèse · Validée
**Décision :** la synthèse s'ouvre sur **la valeur des actifs**, en grand, en serif : le seul
point d'entrée de la page. En seconde ligne, plus petits et sans cadre : le **gain** (toujours le
premier des trois chiffres clés de [D-22](#d-22)), le **TRI** — avec son signalement « Peu fiable »,
conservé à l'identique —, le **TWRR** et le **capital net investi**. Aucun chiffre ne change : seule
leur place change.
**Raison :** la consigne d'identité du propriétaire (étape 9 bis) : chaque page a un point d'entrée
nettement plus grand que le reste, et sur la synthèse c'est la valeur du portefeuille. Arbitrage
rendu en séance, la contradiction avec D-22 lui ayant été soumise.
**Écarte :** garder le gain en grand ; mettre valeur et gain côte à côte (deux points d'entrée,
donc aucun).

### D-100 · 2026-10-09 · Une lecture de nuit, dans la même identité · Validée
**Décision :** Pastory a un **mode sombre**, la « lecture de nuit » : le même livre, lu à la lampe.
Les pages deviennent un brun très profond, un cran plus clair que la reliure ; l'encre devient
crème ; l'or ne change pas. Il **suit le réglage clair / sombre du système**, et un **bouton
jour / nuit** (navigation, coin de la couverture) permet de choisir ; le choix est retenu par le
navigateur. Techniquement, la nuit ne redéfinit que les **rôles** du thème : la feuille et les
graphiques suivent d'eux-mêmes, et toute couleur nouvelle se déclare dans les deux thèmes. Chaque
couleur de nuit est mesurée ([charte](charte-graphique.md) §2.8) et un test recalcule les contrastes
des deux thèmes.
**Raison :** le propriétaire, après discussion avec un ami : un mode sombre serait apprécié, **à condition de garder la direction artistique**. Ce qui était écarté
(notes initiales, D-98), c'était le « style moderne sombre » générique, pas l'obscurité elle-même.
**Écarte :** des pages gris anthracite, avec le brun réservé à la reliure (plus courant, moins
« livre ») ; un mode sombre sans bouton, ou sans suivi du système ; le mode sombre automatique du
navigateur, toujours refusé en clair (`color-scheme: only light`) parce qu'il inverse les clartés.

### D-101 · 2026-10-09 · La couverture tient sur un écran, et le livre s'y referme par son nom · Validée
**Décision :** trois retouches de la couverture, demandées par le propriétaire en la voyant :
- **le nom « Pastory »**, en tête de la navigation, ramène à la couverture (le lien « vos exports »
  du colophon reste) ;
- **la couverture tient sans défiler** : le détail de la lecture passe dans un volet replié de
  l'étiquette ; **les alertes restent hors du volet**, toujours visibles (règle 5) ;
- **l'ouverture du livre se rejoue à chaque ouverture**, et non plus une fois par session.
**Raison :** « vos exports » était trop discret pour revenir à l'accueil ; le bas de l'écran (la
page de garde) obligeait à défiler pour des informations utiles mais secondaires ; et l'ouverture
est le geste qui donne son sens à la couverture.
**Écarte :** déplacer le détail de la lecture dans l'annexe (on le cherche là où l'on dépose
l'export) ; une étiquette qui se retourne (une manipulation de plus).

### D-102 · 2026-10-09 · Des boîtes, et une synthèse qui tient sur un écran · Validée
**Décision :** retouches de la synthèse et des pages, demandées par le propriétaire en les voyant :
- **les éléments redeviennent des boîtes** : fond de page, bordure d'un filet, posées sur un fond
  de livre un ton plus sombre. Elles remplacent les filets seuls de [D-98](#d-98) ; ni ombre ni
  relief pour autant ;
- **la synthèse tient sur un écran** : l'ouverture des chapitres tient sur une ligne (numéro,
  titre, phrase), et la valeur des actifs devient la plus grande boîte de la première rangée, à
  côté des quatre indicateurs, au lieu d'occuper une ligne à elle seule ([D-99](#d-99) tient : elle
  reste le point d'entrée) ;
- **« Peu fiable » s'explique sur la marque elle-même**, au survol : la période est trop courte
  pour se fier au TRI. Le « ? » de l'étiquette dit désormais ce qu'est le TRI ;
- **les cartes d'actifs glissent** d'une page à l'autre, très vite, dans le sens de la lecture ;
- **de nuit, la bande des filtres** passe à `#3A2C20`, nettement distincte du colophon.
**Raison :** le propriétaire : la synthèse avait perdu sa qualité d'écran unique ; le titre et la
valeur prenaient trop de place ; les boîtes donnaient « une vraie frontière bien marquée » ; et
« Peu fiable » sans explication à portée de souris n'apprenait rien.
**Écarte :** garder une ouverture de chapitre en grand sur la synthèse seule (deux styles
d'ouverture dans un même livre) ; une bulle native du navigateur (`title`), lente à paraître et
impossible à mettre en forme.
**Limite connue :** sur un portable en 768 px de haut, la synthèse défile encore d'une centaine de
pixels.

### D-103 · 2026-10-09 · Plus de troisième bande : le colophon rejoint le titre du chapitre · Validée
**Décision :** la bande « état des données » disparaît. Ses informations sont **rangées là où
elles ont un sens**, sans qu'aucune soit supprimée :
- la **période retenue** par les filtres va à droite de la bande des filtres ;
- à droite du titre de chaque chapitre, **la date des cours** — la seule information utile d'un
  coup d'œil — et une **valeur partielle** s'il y en a une ;
- la **source, l'export, les compositions et le nombre de positions** s'ouvrent dans une bulle,
  par un lien discret « d'où viennent ces chiffres » ;
- le lien « vos exports » disparaît : le nom « Pastory » ramène déjà à la couverture ([D-101](#d-101)).

Avec elle : plus d'air entre les groupes de filtres, et **un fleuron de chapitre** — un filet d'or
sur toute la largeur, le losange au centre — entre l'ouverture d'un chapitre et sa page.
**Raison :** le propriétaire : la bande « fait beaucoup trop paramètre », un fourre-tout de
petites informations et un lien, à l'opposé de l'aspect aéré du reste ; et sa couleur était trop
proche de celle de la page. Trois pistes ont été essayées à l'écran sur ses données ; il a retenu
celle-ci. Pour le losange, il a préféré le chapitre aux séparations internes d'un bloc.
**Écarte :** deux lignes de colophon à droite du titre (tout visible, mais encore dense) ; un vrai
colophon en pied de chapitre (le plus « livre », mais il sortait de l'écran sur la synthèse) ; un
losange entre le graphique des poches et leurs valeurs (un ornement répété partout ne sépare plus
rien).

### D-104 · 2026-10-09 · Un chapitre sans filtre a son sommaire dans la bande · Validée
**Décision :** la bande sous la navigation existe sur **tous** les chapitres, à la même hauteur.
Là où il n'y a pas de filtre, elle porte **le sommaire du chapitre** : les quatre rubriques de la
Diversification (qui quittent la page), des liens vers les trois niveaux des Frais et taxes (la
page défile jusqu'à la section), et pour les Projections une phrase : « une hypothèse sur
l'avenir, jamais une prévision ni un conseil ». La règle du contrat tient : **aucun faux filtre**,
on y choisit ce qu'on regarde, rien n'est retiré.
**Raison :** le propriétaire : sans bande, les chapitres III et IV paraissaient plus vides que
I et II. Trois pistes essayées à l'écran ; il a retenu celle-ci.
**Écarte :** une phrase qui explique l'absence de filtres (juste, mais elle ne sert à rien) ; un
ornement centré (il doublait le fleuron du chapitre, juste en dessous) ; des filtres inactifs
(un filtre qui n'agit sur rien fait douter du chiffre affiché).

### D-105 · 2026-10-09 · Les hypothèses de la prédiction de l'évolution · Validée
**Décision :** la prédiction du chapitre V ([D-97](#d-97)) repose sur cinq hypothèses, écrites au
[glossaire](glossaire.md) §9 et **affichées à l'écran** :
1. le taux saisi est celui de la **médiane** : la courbe du milieu retombe sur la courbe sans aléa,
   et l'option « taux aléatoire » ajoute un éventail autour d'elle ;
2. les rendements sont **log-normaux, tirés mois par mois, indépendants** ;
3. **la volatilité annuelle vaut deux fois le taux** — aucune valeur historique ;
4. le taux est **nominal**, avant impôt, frais et inflation ;
5. le hasard a une **graine fixe** : 10 000 tirages, toujours les mêmes pour les mêmes entrées.
Le calcul vit dans un module indépendant (`pastory/projection.py`), qui ne reçoit du portefeuille
que la valeur de départ ([D-27](#d-27)).
**Raison :** Q-61, tranchée par le propriétaire. Pour la dispersion, sa réponse : un taux faible
va avec peu de variations, un taux élevé avec beaucoup, sans s'appuyer sur l'histoire d'un indice.
**Écarte :** le taux comme moyenne (la courbe du milieu passerait sous la courbe simple, d'autant
plus que le taux et la durée sont grands) ; rejouer l'histoire d'un indice ; des repères de classes
d'actifs sourcés ; une volatilité saisie à la main ; une case d'inflation.
**Limite connue :** la loi log-normale sous-estime les krachs, et l'écran le dit.
**Précisée le même jour, à l'écran :** les extrêmes affichés sont les quantiles **10 % et 90 %**
(« dans 8 cas sur 10 »), et non 5 % et 95 %, que le propriétaire a jugés peu pertinents ; la page
se lit de haut en bas — le montant atteint, la courbe, puis les hypothèses — et tient sur un
écran ; le « taux aléatoire » est un choix à deux boutons, « une courbe | 10 000 simulations ».

### D-106 · 2026-10-12 · Pastory s'ouvre par un raccourci, dans sa fenêtre, et s'arrête avec elle · Validée
**Décision :** on lance Pastory **comme un logiciel**. Un raccourci (bureau et menu Démarrer,
avec le logo) appelle `pythonw -m pastory.lanceur`, qui :
1. ouvre Pastory dans **une fenêtre à part, sans barre d'adresse** — Edge ou Chrome en mode
   application ; à défaut des deux, un onglet du navigateur habituel ;
2. **s'arrête quand on ferme la fenêtre** : la page donne signe de vie au serveur toutes les cinq
   secondes et lui dit adieu en se fermant ; le serveur s'arrête quand plus aucune page n'est
   ouverte (`pastory/vues/veille.py`) ;
3. **ne démarre jamais deux fois** : le port est pris avant le chargement de l'interface, et un
   second lancement ramène la fenêtre existante au premier plan ;
4. **ne reste jamais muet** : sans terminal, ce qui s'écrirait à l'écran va dans `journal.txt`
   (dossier personnel), et une panne de démarrage s'affiche dans une boîte de message.

Les raccourcis sont créés par `pastory installer` (et retirés par `--retirer`) ; un nouvel
utilisateur double-clique sur `Installer Pastory.cmd`, qui installe l'environnement puis les crée.
Le raccourci appelle le Python de l'environnement **par son chemin, jamais `uv run`**.
`pastory ouvrir`, dans un terminal, reste ce qu'il était.
**Raison :** le propriétaire, le 2026-10-09 : « plus de commande à taper ». Et sur sa machine,
`uv run` échoue dès que `pyproject.toml` change (OneDrive, antivirus), alors que l'environnement
installé fonctionne.
**Trois réglages de la veille, chacun né d'un cas réel :** le silence se compte en **battements**
et non à l'horloge (un ordinateur mis en veille n'arrête rien) ; une page se tait **cinq minutes**
avant d'être tenue pour fermée (un navigateur ralentit une fenêtre réduite à un signe par minute,
et l'antivirus du propriétaire coupe une connexion locale sur dix) ; Pastory **ne s'arrête pas au
milieu d'un travail** (un cache à moitié écrit). Fenêtre fermée, il s'arrête en une dizaine de
secondes ; si l'adieu s'est perdu, en cinq minutes au plus.
**Écarte :** un `.exe` empaqueté (lourd, et signalé comme suspect par les antivirus déjà
rencontrés) ; une fenêtre native (une dépendance de plus pour peu de gain) ; attendre la fin du
processus du navigateur (il se confond avec les autres fenêtres d'Edge) ; un arrêt dès le premier
signe manqué.
**Précisée le même jour, par la relecture indépendante :** la recherche d'un Pastory déjà ouvert
regarde **toute la plage de ports**, et pas seulement jusqu'au premier libre (lancé un jour où le
premier était pris, il tourne sur le suivant) ; le lanceur **annonce la fenêtre qu'il amène** à un
Pastory déjà ouvert, qui l'attend alors comme la première (sans quoi, rouvert dans les secondes
qui suivent sa fermeture, il s'éteignait sous la nouvelle fenêtre) ; le journal s'ouvre **avant**
tout ce qui peut échouer ; et le nom, l'hôte, le port et le titre de la fenêtre sont dits **une
seule fois**, dans `veille.py`, pour le lanceur comme pour l'application.
**Limites connues :** sous Windows seulement pour les raccourcis — le lanceur ne dépend pas de
Windows, mais aucun raccourci Mac n'a pu être essayé ; l'icône de la fenêtre dans la barre des
tâches est celle que le navigateur lui donne ; les raccourcis pointent sur le dossier du projet,
et sont à recréer s'il est déplacé ou renommé.
**Une limite non mesurée :** un navigateur peut **endormir tout à fait** une page masquée depuis
longtemps ; elle ne donnerait plus signe de vie, et Pastory s'arrêterait sous une fenêtre
simplement réduite. La page tient un verrou du navigateur, que Chrome et Edge disent respecter
avant d'endormir une page — **ce n'est pas vérifié sur la durée**. Si cela arrive, la page le dit
(« Pastory est arrêté… »), aucun chiffre n'est en jeu, et le remède est d'allonger le silence
toléré ou de faire prévenir le serveur par la page qui s'endort.

### D-107 · 2026-10-12 · Un portefeuille de démonstration : opérations inventées, titres réels, dossier à part · Validée
**Décision :** Pastory sait s'ouvrir sur un **portefeuille fictif** (`pastory/demonstration/`),
pour être montré sans révéler un vrai portefeuille.
- C'est un **export des transactions fictif, au format officiel**, que Pastory lit comme un
  vrai : il y cherche seul les cours, les frais des fonds et leur composition. La démonstration
  montre donc la vraie chaîne, y compris ses trous et ses réserves.
- **Les opérations sont inventées ; les titres sont réels**, publics et courants, jamais choisis
  d'après un portefeuille réel. **Les prix d'achat sont les vraies clôtures** des jours choisis
  (`clotures.py`, relevé par `scripts/releve_de_demonstration.py`) : sans cela, le contrôle par le
  prix payé ([D-85](#d-85)) refuserait la bonne cotation.
- **Seules des formes déjà vues sur de vrais fichiers** sont écrites
  ([export-officiel.md](export-officiel.md) §4.1) : pas de dividende de fonds, par exemple.
- **Un dossier personnel à part**, voisin du vrai (`Pastory-demonstration`), avec son export, son
  cache et sa configuration : rien ne se mêle. L'export y est **écrit par le programme** — aucun
  fichier de données n'entre dans git ([D-01](#d-01)).
- **L'écran le dit partout** : « Données de démonstration » sur la couverture et dans la
  navigation de chaque chapitre, un autre titre de fenêtre, et **aucun dépôt possible**.
- **C'est le dossier qui dit si c'est une démonstration**, et lui seul
  (`emplacements.est_une_demonstration`) : aucune option n'est passée à l'écran. La mention et les
  fichiers lus ne peuvent donc pas se contredire — ni un vrai portefeuille s'afficher sous
  « démonstration », ni l'inverse.
**Raison :** le propriétaire, le 2026-10-09, puis son arbitrage du 2026-10-12 entre de vrais titres
et des actifs entièrement fictifs.
**Écarte :** des actifs fictifs livrés avec des cours inventés (fonctionne sans réseau et donne
toujours les mêmes chiffres, mais ne montre pas la recherche automatique, et chaque source
affichée serait « valeur de démonstration ») ; un CSV versionné ; un bouton qui bascule un Pastory
ouvert sur la démonstration (le dossier personnel se lit dans l'environnement du programme : deux
programmes, deux ports, aucun mélange possible).
**Conséquences :** la première ouverture demande Internet, et les chiffres bougent avec le marché.
Les **ISIN du scénario sont réels** : c'est la seule exception à « valeurs fictives » ([D-03](#d-03)),
et elle ne porte que sur des titres publics. Le scénario s'arrête en septembre 2026 ; le prolonger
demande de relancer le relevé.
**Ce que la démonstration a trouvé en chemin :** une cotation étrangère créée après l'achat faisait
répondre « 400 » à la source de cours, pris pour une panne ; l'action restait sans cours. Ce refus
écarte désormais un candidat, pas la recherche (`PeriodeSansCours`). Son message dit ce que la
source dit — aucun cours sur la période — sans supposer pourquoi : c'est un texte de la source qui
est lu ici, faute de code (règle 4), et il ne dit pas si le titre n'était pas encore coté ou ne
l'est plus.

### D-108 · 2026-10-12 · Le ménage : ce que l'application a remplacé s'en va · Validée
**Décision :** maintenant que Pastory fonctionne de bout en bout, ce qui ne sert plus est retiré.
- **Du dépôt :** les maquettes d'écran de l'étape 8 (l'application fait foi ; `maquettes/logo/`
  reste, citée par la charte) ; le signalement de l'ancien dossier « DashBoardTradeRepublic », qui
  ne servait qu'à la machine du propriétaire ; les douze branches d'étape, toutes fusionnées.
- **De la machine du propriétaire :** `data/` (ses fichiers pytr, et une copie de son export
  entièrement contenue dans celui du dossier de dépôt), les deux fichiers pytr de son ami, le PDF
  de la maquette d'origine, l'ancien dossier personnel, et pytr lui-même.
**Raison :** le propriétaire. L'historique git garde tout ce qui était versionné.
**Ce qui a été vérifié avant d'effacer :** chaque correction manuelle de l'ancienne configuration
a été comparée à ce que Pastory trouve seul. Toutes sont retrouvées à l'identique, sauf un taux de
frais courants, reporté dans le fichier de corrections du nouveau dossier.
**Gardé volontairement :** les documents de l'époque pytr ([inventaire-donnees.md](inventaire-donnees.md),
le cahier de l'étape 2) — leurs pièges expliquent des décisions ; l'export officiel du tiers, seule
pièce de [Q-54](questions-ouvertes.md) ; les relevés de vérification locaux du propriétaire.
