# Notes initiales du propriétaire

> **Statut : document de référence.** C'est la retranscription des notes manuscrites
> (PDF « Dashboard Trade Republic », conservé hors dépôt). Il fait foi sur **ce que veut le propriétaire**,
> en particulier sur le contenu. Il évolue quand le propriétaire change de cap. Chaque
> modification est tracée dans [decisions.md](decisions.md).
>
> Les passages entre crochets `[…]` sont des remarques de retranscription, pas le texte original.

Dernière mise à jour : 2026-09-27 (le public visé : l'utilisateur type, et non le seul propriétaire).

---

## Évolutions de cap

Ces précisions **priment** sur le texte d'origine ci-dessous.

### 2026-09-17 · La maquette n'est pas un modèle ([D-20](decisions.md))
> La maquette était un premier jet, sans réflexion préalable. La disposition des filtres, du
> graphique, des légendes et les chiffres clés ne sont pas réfléchis. Elle servait à donner une
> idée globale de la forme, et a fait naître le mot « Dashboard ». L'application devrait être bien
> différente dans sa configuration.

### 2026-09-17 · On suit les actifs, pas les espèces ([D-11](decisions.md))
> L'application ignore complètement la poche espèces. Le compte espèces sert plutôt aux achats de
> la vie quotidienne. Même s'il sert aussi à acheter dans le PEA, le CTO ou la crypto, son
> évolution n'a pas d'intérêt ici. Ce qui compte, c'est **l'évolution des actifs achetés** : quand
> un achat est fait, comment l'actif évolue, quand il est vendu. Et les entrées et sorties : taxes
> éventuelles, frais fixes… Peu importe d'où vient l'argent. On veut savoir si des frais ou des
> taxes ont été appliqués et comment ils font évoluer le capital investi.

### 2026-09-17 · Capital net investi ([D-12](decisions.md))
> Le capital net investi est le montant réellement placé, après frais et taxes. Exemple : je mets
> 201 € avec 1 € de frais fixes sur mon PEA, la valeur passe à 200 €. Idem pour toutes les poches.
> Lors d'une vente, le capital investi diminue au prorata de la part vendue de l'actif concerné.

### 2026-09-17 · Coûts cachés et cours de marché ([D-17](decisions.md), [D-18](decisions.md))
> Le spread et les frais des ETF doivent être **estimés** : frais des ETF trouvés dans une base de
> données d'actifs, spread avec une valeur par défaut selon l'actif. Les cours viendront d'un outil
> gratuit accessible en Python (Yahoo Finance ou autre), à choisir.

### 2026-09-17 · Les frais à part de l'évolution ([D-21](decisions.md))
> Les frais sont indépendants de la santé générale du portefeuille. Ils ne vont pas dans les
> performances générales mais dans un onglet à part. C'est la partie extérieure à l'évolution : ce
> qui se passe à l'entrée et à la sortie. On ne l'ignore pas, on la traite à part de l'évolution,
> qui est le cœur de l'application. Si on met 201 € avec 1 € de frais fixes, seuls 200 € entrent
> dans le « coffre ». Le −1 € est examiné indépendamment.

### 2026-09-17 · Trois chiffres clés et deux lectures ([D-22](decisions.md), [D-23](decisions.md))
> Trois chiffres clés :
> - le **gain** (selon les filtres, combien j'ai gagné en euros) ;
> - le **TRI** ;
> - le **TWRR**.
>
> Le premier est le seul intéressant pour un portefeuille jeune. Les deux autres précisent la
> performance et deviennent utiles après un certain âge du portefeuille.
>
> La page **synthèse** montre uniquement le cœur des investissements (un peu flatteuse). Une autre
> page, plus **réelle**, montre le capital possédé si on retirait tout (avec les taxes, plus
> correct).

### 2026-09-17 · Périmètre et ouverture ([D-26](decisions.md), [D-27](decisions.md), [D-28](decisions.md))
> Euro uniquement pour l'instant. Lecture seule, pas de conseil d'investissement : c'est juste pour
> visualiser ce qu'on a et comprendre ce qui se passe dans ses investissements. Pas de production de
> déclarations. Les autres banques ne sont pas prises en charge, mais le projet peut être forké et
> utilisé tant que les données correspondent à ce qu'attend l'application. « La locomotive avance,
> et on peut changer de wagon (banque) sans problème tant que les données sont bien formatées. »
>
> Monte-Carlo est une fonctionnalité indépendante, dont on peut se passer pour le moment.
>
> Les données de diversification, comme les cours, doivent être gratuites et fiables.

### 2026-09-17 · Identifiants ([D-25](decisions.md))
> Pas de PIN en argument de commande. À l'installation, l'utilisateur choisit, avec les risques
> expliqués : rien d'enregistré (le plus sûr), PIN dans le gestionnaire d'identifiants du système,
> ou seulement la session pytr. Jamais de PIN en clair dans le projet, un `.env` ou OneDrive.

### 2026-09-27 · Les fonctionnalités visent l'utilisateur type, pas mon portefeuille ([D-62](decisions.md))
> L'objectif du projet n'est pas seulement que l'application soit *installable* par un autre
> investisseur (étape 10) : les **choix de fonctionnalités** doivent être faits pour l'utilisateur
> type de Trade Republic, pas pour mon portefeuille du moment. Je compte partager l'application.
>
> Ce que ça implique :
> - les **actions détenues en direct** entrent dans les répartitions géographique et sectorielle,
>   même si je n'en détiens aucune : l'achat d'actions à l'unité est très courant chez Trade
>   Republic, et une répartition qui ne saurait pas les traiter serait inutilisable pour beaucoup.
>   La réserve sur la règle de pays — siège social pour une action, pays d'activité pour un ETF —
>   doit être écrite à l'écran ;
> - le volet **classe d'actifs** (actions / obligations / liquidités) est confirmé : les
>   portefeuilles mixtes sont fréquents ;
> - les **zones d'investisseur** (Amérique du Nord, Europe, Japon, Asie-Pacifique développée,
>   émergents) sont confirmées : c'est le vocabulaire de tous les outils du marché, et la liste
>   datée et sourcée reste corrigeable par qui voudra ;
> - les messages d'absence doivent être **soignés** : « cet actif n'est pas couvert » sera lu par
>   des gens qui n'ont pas suivi la construction du projet. Même chose pour la crypto — le libellé
>   doit expliquer que les actifs numériques n'ont ni pays ni secteur, pour qu'on ne croie pas à un
>   oubli.

---

## Objectif de l'application

Visualiser de façon claire l'évolution du patrimoine investi sur Trade Republic. L'application
servira des investisseurs (plutôt que des traders) utilisant Trade Republic.

Pour cela, l'utilisateur devra établir la connexion avec Trade Republic via pytr afin que cette
dernière permette d'actualiser régulièrement le fichier des transactions.

L'application sera maintenue sur GitHub et tournera en local après quelques configurations.
Elle sera complètement gratuite.

## Contenu important

- **Graphique d'évolution globale du capital sur Trade Republic**
  - Courbe d'évolution du capital
  - Courbe du capital net investi
  - Filtres pour sélectionner la date à laquelle commencera le graphique, sélection de certaines
    poches (PEA, CTO, Crypto, …)
- **Chiffres clés de l'évolution du capital sur T.R.**
  - Plus-value réalisée (+132 € par exemple)
  - TRI : rendement réel du capital (en %)
  - TWROR : rendement théorique de la stratégie (en %)
- **Graphiques / tableau sur la diversification des actifs**
  - Diversification géographique (50 % US, 15 % France, …)
  - Diversification sectorielle (30 % tech, 20 % santé, …)
- **Infos sur la performance des actifs**
  - nom
  - évolution (en %)
  - valeur possédée (en €)
  - trier par évolution ↘/↗ ou par valeur possédée ↘/↗
- **Infos des frais (à déterminer)**
  - historique des frais fixes et de leur part dans la transaction
    [lecture incertaine : « fixes » ou « fiscaux », voir Q-21]
  - frais par actif + coût estimé des pertes par an
  - taxes sur les gains via plus-value brute contre nette (selon la poche)
- **Simulations d'évolution du patrimoine avec Monte-Carlo**
  - graphique d'évolution estimé
  - montant épargné
  - rendement ciblé

### Problèmes à noter (constatés sur Finary)

- La synchronisation est compliquée à faire marcher.
- L'appli doit vraiment avoir des données fiables sur le marché.

## Style de l'application

- Style éditorial : tons crème/beige, papier texturé et typographie soignée, bordures fines gris
  très doux, vert sauge pour les gains et brique/terracotta pour les pertes.

L'objectif est de s'écarter du style moderne sombre sur-utilisé par tous. Pas d'artifices
inutiles, on reste sobre.

## Structure de l'application

L'application sera composée de plusieurs onglets :

1. **Synthèse**
   - graphique d'évolution globale
   - chiffres clés de l'évolution
   - performances et infos des actifs possédés
2. **Diversification**
   - géographique et sectorielle
3. **Les frais**
   - net vs brut, coûts estimés des actifs par an, frais fixes [même incertitude de lecture]
4. **Simulation de croissance**

---

## Annexe : maquette (résumé)

La maquette **n'est pas un modèle** (voir « Évolutions de cap »). Ce résumé sert seulement de
trace. Les chiffres sont des exemples, la disposition n'est pas à reproduire.

- **Synthèse** : courbe « Capital brut » et courbe en escalier « Capital net investi » sur le même
  graphique. Filtres « Depuis [date] » et cases à cocher PEA / CTO / crypto. Trois tuiles :
  *Gains relatifs* (%), *Capital net investi* (€), *Capital brut* (€). Anneau « Répartition dans
  les poches » avec le montant de chaque poche.
- **Répartition des actifs** : blocs géographique et sectoriel (pourcentages). Tri par parts ou
  par évolution (↑↓). « Évolution depuis » : 1 semaine, 1 mois, 3 mois… Une carte par actif avec
  valeur possédée et évolution.
- **Simulateur de Monte-Carlo** : page titrée « ??? », sans contenu. Voir Q-20.
