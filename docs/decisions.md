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

### D-41 · 2026-09-18 · `rafraichir` ne manipule aucun identifiant · Validée
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

### D-42 · 2026-09-18 · Recoupement systématique avec le CSV · Validée
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

### D-46 · 2026-09-20 · Les positions réelles entrent dans le pivot ; la quantité contrôle, le PRU informe · Validée
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

### D-47 · 2026-09-21 · Une poche que la photo ne couvre pas n'est pas un désaccord · Validée
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

### D-48 · 2026-09-26 · Le cours de référence est celui du marché principal, en euros · Validée
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

### D-55 · 2026-09-27 · Le type d'un actif est déclaré par l'utilisateur, jamais deviné · Validée
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

### D-59 · 2026-09-27 · Le gain du PEA est approché depuis les titres, sur une date déclarée · Validée
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

### D-61 · 2026-09-27 · Le TER est proposé depuis la liste de Xetra, et validé par l'utilisateur · Validée
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

### D-71 · 2026-09-28 · Le contenu d'un actif se déclare, et n'avoir ni pays ni secteur n'est pas un manque · Validée
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

### D-77 · 2026-09-30 · La source de secours est le service produit d'Amundi, et elle ne sert que la géographie · Validée
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
