# Contexte produit

Source des intentions : [notes-initiales.md](notes-initiales.md). Ce document en tire le cadre.

## Le problème

Trade Republic n'offre aucune vue analytique sur les données de ses clients : pas de capital net
investi, pas de rendement annualisé, pas de vue par poche, pas de suivi des frais. Les agrégateurs
existants (ex. Finary) se synchronisent mal et s'appuient sur des données de marché peu fiables.

## Objectif

Montrer clairement l'évolution des **actifs achetés** sur Trade Republic : ce qui y est réellement
placé, ce que ça vaut, ce que ça a rapporté (TRI, TWRR, plus-values, dividendes), comment c'est
réparti entre poches et actifs, et ce que ça coûte (frais, taxes, coûts cachés estimés).

**Les espèces ne sont pas suivies** ([D-11](decisions.md)) : ni le compte courant, ni l'origine de
l'argent, ni les dépenses. L'interface est à concevoir : la maquette des notes n'est pas un modèle
([D-20](decisions.md)).

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
| **Configuration minimale** | Aucun réglage à taper : l'application **propose**, l'utilisateur valide d'un clic ([D-78](decisions.md)). La poche est donnée par l'export ([D-79](decisions.md)) |
| **Chiffres vérifiables** | Chaque indicateur a une formule écrite dans le [glossaire](glossaire.md) et doit pouvoir être refait à la main |
| Données via l'**export officiel** de Trade Republic ([D-79](decisions.md)) | Aucune spécification publiée, et le format peut évoluer : les types inconnus doivent être affichés, pas ignorés. *Jusqu'au 2026-10-01 : pytr, une interface non officielle que les conditions générales de la banque interdisent* |

## Hors périmètre

Tirés des notes :

- Les outils pour **traders** (suivi intrajournalier, analyse technique, passage d'ordres).

Décidés :

- Le suivi des **espèces** : solde, virements, paiements carte, intérêts sur espèces, primes,
  origine de l'argent investi ([D-11](decisions.md)).

- Passer des ordres ou modifier quoi que ce soit chez Trade Republic : l'application est en
  **lecture seule**, elle sert à visualiser ce qu'on a ([D-26](decisions.md)).
- Le **conseil en investissement** ou les recommandations d'achat/vente. Le but est que
  l'utilisateur comprenne ce qui se passe dans ses investissements.
- La **production de déclarations fiscales**. L'appli peut *estimer* un impôt (vue « valeur
  réelle »), pas le déclarer.
- Les **devises autres que l'euro**, pour l'instant.
- Les **autres courtiers et banques** : non pris en charge. Mais le moteur lit un format pivot
  documenté, et quelqu'un qui forke le projet peut écrire un adaptateur pour sa banque
  ([D-26](decisions.md)).
- Tout hébergement en ligne, compte utilisateur ou synchronisation cloud (l'application tourne en
  local).
- La **simulation Monte-Carlo** n'est pas hors périmètre, mais reportée : fonctionnalité
  indépendante ([D-27](decisions.md)).
