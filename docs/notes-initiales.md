# Notes initiales du propriétaire

> **Statut : document de référence.** C'est la retranscription des notes manuscrites
> (PDF « Dashboard Trade Republic », conservé hors dépôt). Il fait foi sur **ce que veut le propriétaire**,
> en particulier sur le contenu. Il évolue quand le propriétaire change de cap. Chaque
> modification est tracée dans [decisions.md](decisions.md).
>
> Les passages entre crochets `[…]` sont des remarques de retranscription, pas le texte original.

Dernière mise à jour : 2026-09-17 (retranscription initiale).

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

La maquette est indicative. Les chiffres qui y figurent sont des **exemples** et ne doivent pas
servir de référence de calcul.

- **Synthèse** : courbe « Capital brut » et courbe en escalier « Capital net investi » sur le même
  graphique. Filtres « Depuis [date] » et cases à cocher PEA / CTO / crypto. Trois tuiles :
  *Gains relatifs* (%), *Capital net investi* (€), *Capital brut* (€). Anneau « Répartition dans
  les poches » avec le montant de chaque poche.
- **Répartition des actifs** : blocs géographique et sectoriel (pourcentages). Tri par parts ou
  par évolution (↑↓). « Évolution depuis » : 1 semaine, 1 mois, 3 mois… Une carte par actif avec
  valeur possédée et évolution.
- **Simulateur de Monte-Carlo** : page titrée « ??? », sans contenu. Voir Q-20.
