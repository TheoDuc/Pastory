# Contexte produit

Source des intentions : [notes-initiales.md](notes-initiales.md). Ce document en tire le cadre.

## Le problème

Trade Republic n'offre aucune vue analytique sur les données de ses clients : pas de capital net
investi, pas de rendement annualisé, pas de vue par poche, pas de suivi des frais. Les agrégateurs
existants (ex. Finary) se synchronisent mal et s'appuient sur des données de marché peu fiables.

## Objectif

Montrer clairement l'évolution du patrimoine investi sur Trade Republic : ce qui a été apporté, ce
que ça vaut, ce que ça a rapporté (TRI, TWRR, plus-values), comment c'est réparti et ce que ça
coûte.

## Public visé

- Investisseurs **long terme** (plans d'épargne, achats réguliers, dividendes), pas des traders.
- Clients Trade Republic français en priorité (PEA, CTO, crypto). Leurs applications peuvent être
  réglées dans une autre langue (constaté : allemand).
- Personnes qui ne sont pas forcément développeurs : l'installation doit se limiter à quelques
  étapes guidées.

## Contraintes

| Contrainte | Conséquence |
|---|---|
| Tourne **en local** | Aucune donnée ne quitte la machine de l'utilisateur |
| **Gratuit** | Pas de service payant, pas de source de cours payante |
| Publié sur **GitHub** | Aucune donnée réelle dans le dépôt ; la doc utilise des valeurs fictives |
| **Configuration minimale** | L'utilisateur nomme ses comptes à l'installation (on ne devine pas) |
| **Chiffres vérifiables** | Chaque indicateur a une formule écrite dans le [glossaire](glossaire.md) et doit pouvoir être refait à la main |
| Données via **pytr** (API privée, non officielle) | Le format peut changer sans préavis : les types inconnus doivent être affichés, pas ignorés |

## Hors périmètre

Tirés des notes :

- Les outils pour **traders** (suivi intrajournalier, analyse technique, passage d'ordres).

Proposés, **à confirmer** (Q-19) :

- Passer des ordres ou modifier quoi que ce soit chez Trade Republic (lecture seule).
- Le conseil en investissement ou les recommandations d'achat/vente.
- Les autres courtiers et banques.
- Tout hébergement en ligne, compte utilisateur ou synchronisation cloud.
- La production de déclarations fiscales (l'appli peut *estimer* une fiscalité, pas la déclarer).
- Les devises autres que l'euro (toutes les données observées sont en EUR).
