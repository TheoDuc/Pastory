# Questions ouvertes

Arbitrages en attente du propriétaire. Une question tranchée est déplacée en bas (section
« Tranchées ») avec la réponse, et la décision correspondante est ajoutée à
[decisions.md](decisions.md).

Chaque question donne le contexte, les options et une recommandation. **La recommandation n'est
pas une décision.**

---

## A. À trancher avant d'écrire le moteur

### Q-01 · Les revenus sont-ils du rendement ou des apports ?
**Contexte :** certains montants entrent sans venir de la poche de l'investisseur : intérêts,
dividendes, distribution de capital, prime Trade Republic (`CASH_PERK`), euro d'activation du PEA,
action gagnée, saveback sur paiement carte.
**Options :** (a) rendement : ils augmentent le capital brut sans augmenter le capital net investi ;
(b) apports : ils augmentent les deux ; (c) au cas par cas.
**Recommandation :** (a) pour tous. Le capital net investi reste alors « ce qui est sorti de ma
poche », et le TRI mesure bien ce que l'argent a rapporté.

### Q-02 · Un paiement par carte est-il un retrait ?
**Contexte :** la carte Trade Republic dépense l'argent du compte courant. L'argent quitte Trade
Republic.
**Options :** (a) retrait externe, qui diminue le capital net investi ; (b) hors sujet, qui
n'apparaît pas.
**Recommandation :** (a). Sinon, le capital brut baisse sans explication et le rendement paraît
négatif.

### Q-03 · Les espèces non investies font-elles partie du capital brut ?
**Options :** (a) oui, affichées comme une poche « Espèces » ; (b) non, seulement les titres.
**Recommandation :** (a). Un virement reçu mais pas encore investi augmente le capital net investi.
S'il n'augmente pas aussi le capital brut, on affiche une perte fictive.

### Q-04 · Que veut dire « capital net investi » pour une seule poche ?
**Contexte :** la maquette filtre le graphique par poche. Or l'argent entre toujours par le compte
courant, puis est réparti.
**Options :** (a) PEA : versements nets courant → PEA ; CTO et crypto : achats − ventes ;
(b) pas de capital net investi par poche, seulement la valeur par poche.
**Recommandation :** (a), avec une mention dans l'interface. Attention : c'est irréalisable pour
un export où des versements PEA manquent (Q-09).

### Q-05 · Méthode du prix de revient
**Options :** (a) prix moyen pondéré (PMP), frais inclus ; (b) premier entré, premier sorti (FIFO).
**Recommandation :** (a), la règle fiscale française pour les titres. La crypto suit en France une
règle différente (prix d'acquisition global) : à traiter plus tard si la fiscalité est affichée.

### Q-06 · Que calcule la tuile « Gains relatifs » ?
**Contexte :** la maquette affiche un pourcentage sans formule.
**Options :** (a) gain total / capital net investi ; (b) TRI ; (c) TWRR.
**Recommandation :** (a), sous un nom explicite (« plus-value globale »), avec TRI et TWRR affichés
à part dans les chiffres clés.

### Q-07 · Distribution de capital (« Kapitalverteilung »)
**Options :** (a) revenu, comme un dividende ; (b) remboursement de capital, qui diminue le prix de
revient.
**Recommandation :** (b), plus juste économiquement. Mais le traitement fiscal réel est à vérifier.

### Q-08 · Taxe à l'achat (« Steuer » sur des ordres) : frais ou impôt ?
**Contexte :** 6 achats d'actions du tiers portent une taxe, en CTO comme en PEA. C'est
probablement la taxe française sur les transactions financières.
**Options :** (a) impôts et taxes, catégorie séparée ; (b) frais.
**Recommandation :** (a), incluse dans le prix de revient dans les deux cas.

### Q-09 · Achats PEA sans versement chez ton ami
**Contexte :** 27 achats PEA sur 41 n'ont aucun versement associé, et le solde reconstitué du
compte PEA finit négatif. Il manque des entrées d'argent vers le PEA.
**À faire :** demander à ton ami comment il alimente son PEA (virement direct vers le PEA ?
transfert depuis une autre banque ?), et si l'export est complet (date de début).
**Impact :** aucun sur le capital net investi global (D-07). Bloquant pour la répartition par
poche (Q-04).

### Q-10 · Événement « PEA-Übertragung » sans montant chez ton ami
**Contexte :** type `null`, sans compte ni montant, icône « banque ». Il est antérieur au premier
achat PEA.
**Hypothèse :** transfert d'un PEA depuis un autre établissement. Si des titres ont été
transférés, ils sont entrés **sans aucun événement d'achat**. Leurs quantités et leur prix de
revient seraient alors inconnus.
**À faire :** confirmer auprès de ton ami.

### Q-11 · Tes trois comptes
**Contexte :** compte B activé (+1 €), vidé vers le compte courant six jours plus tard, puis
compte C activé deux minutes après.
**Question :** as-tu ouvert le PEA deux fois, ou fait une manipulation particulière à ces dates ?
L'euro d'activation vient-il de Trade Republic, sans que tu l'aies versé ?

### Q-12 · Définition de la poche crypto
**Contexte :** le code `XF…` n'est vérifié que sur un seul actif crypto.
**Options :** (a) crypto = code commençant par `XF`, à confirmer sur d'autres exports ;
(b) liste d'actifs crypto tenue à la main.
**Recommandation :** (a), en affichant « poche déduite » et en laissant l'utilisateur corriger.
As-tu d'autres cryptos, ou quelqu'un qui en a plusieurs ?

### Q-13 · Frais implicites (écart de prix crypto, frais des ETF)
**Contexte :** rien ne les mesure dans l'export.
**Options :** (a) mention qualitative seulement ; (b) estimation à partir d'un taux saisi par
l'utilisateur, affichée à part ; (c) exploiter le rapport des coûts annuel de Trade Republic (PDF).
**Recommandation :** (a) pour commencer, puis (b). Jamais mélangé aux frais réels.

### Q-14 · Source des cours de marché
**Contexte :** capital brut, TWRR, évolution par actif et diversification exigent des cours, y
compris historiques. Les notes insistent sur la fiabilité.
**Options :** à étudier (source gratuite non officielle, données pytr du portefeuille courant,
saisie manuelle…).
**Recommandation :** en faire l'objet d'une session dédiée avant l'étape de valorisation.

### Q-15 · Langues d'application prises en charge
**Contexte :** les libellés sont dans la langue de l'application, et un export mélange déjà deux
langues.
**Options :** (a) allemand + français au départ, extensible ; (b) allemand seulement.
**Recommandation :** (a). Un libellé non reconnu déclenche une alerte visible, jamais une valeur
par défaut.

### Q-16 · Règle d'appariement versement PEA ↔ achat
**Contexte :** la règle testée (même ISIN, comptes différents, achat avant versement, fenêtre de
3 jours) donne un candidat unique dans 17 cas sur 17.
**Question :** en cas d'ambiguïté (deux achats du même actif le même jour), que fait-on ?
(a) apparier par ordre chronologique et signaler la déduction ; (b) ne pas apparier et
afficher le cas.
**Recommandation :** (b).

---

## B. Peuvent attendre

### Q-17 · Dépôt git dans OneDrive
OneDrive peut créer des conflits dans le dossier `.git`. Rien de cassé aujourd'hui. Option :
déplacer le projet hors OneDrive, GitHub assurant la sauvegarde.

### Q-18 · Code PIN passé en argument dans `src/data_loader.py`
Le PIN apparaît dans la liste des processus pendant l'export. À revoir quand on travaillera sur
l'installation (pytr sait gérer sa propre connexion).

### Q-19 · Hors périmètre
Confirmer la liste proposée dans [contexte-produit.md](contexte-produit.md#hors-périmètre).

### Q-20 · Simulateur Monte-Carlo
La maquette le marque « ??? ». Fait-il partie de la première version ?

### Q-21 · « Frais fixes » ou « frais fiscaux » ?
Lecture incertaine dans les notes (onglet Frais). Selon la réponse, on parle de frais par ordre ou
d'impôts.

### Q-22 · Source de la diversification géographique et sectorielle
Il faut la composition des ETF (pays, secteurs), absente des données pytr.

---

## Tranchées

*(aucune pour l'instant)*
