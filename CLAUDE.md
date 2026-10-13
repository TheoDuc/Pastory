# Pastory

Tableau de bord local et gratuit pour suivre **les actifs** d'un portefeuille Trade Republic
(PEA, CTO, crypto ; les espèces ne sont pas suivies), destiné à des investisseurs long terme. Les données viennent de
l'**export officiel des transactions** que Trade Republic fournit dans son application (CSV, D-79),
que l'utilisateur dépose dans le dossier `exports` de Pastory. pytr a été retiré à l'étape 8 ter (D-81).
Le propriétaire du projet ne code pas : il vérifie les chiffres. Tout calcul doit donc être
lisible et vérifiable à la main.

## Où trouver quoi

| Fichier | Contenu |
|---|---|
| [docs/prompt-session-suivante.md](docs/prompt-session-suivante.md) | **À lire en premier** : où en est le projet, et ce que la session en cours doit savoir. À mettre à jour à la fin de chaque étape |
| [docs/feuille-de-route.md](docs/feuille-de-route.md) | **Étapes du projet**, étape en cours, méthode de travail |
| [docs/notes-initiales.md](docs/notes-initiales.md) | **Référence** des intentions du propriétaire (notes + évolutions de cap) |
| [docs/format-pivot.md](docs/format-pivot.md) | **Le format des opérations** : le contrat entre les adaptateurs et le moteur |
| [docs/conception-interface.md](docs/conception-interface.md) | **Le contrat de l'interface** (étape 8) : ce que le moteur produit et où ça s'affiche, le vocabulaire d'écran, les règles d'affichage |
| [docs/charte-graphique.md](docs/charte-graphique.md) | **La charte graphique** (étape 9 bis) : le livre relié, la palette et ses contrastes mesurés, les polices, la structure en chapitres, les graphiques, les animations, le logo. **Fait référence** pour toute modification d'interface |
| [maquettes/logo/](maquettes/logo/) | Les variantes du logo, et celle qui a été choisie. Les maquettes d'écran de l'étape 8 ont été retirées à l'étape 10 (D-108) : **l'application fait foi**, et elles restent dans l'historique git |
| [pastory/lanceur.py](pastory/lanceur.py) | **Ce que fait le raccourci** (étape 10, D-106) : la fenêtre à part, la veille qui arrête Pastory quand on la ferme, le journal |
| [pastory/demonstration/](pastory/demonstration/) | **Le portefeuille de démonstration** (étape 10, D-107) : un export fictif sur de vrais titres, dans un dossier à part |
| [docs/architecture.md](docs/architecture.md) | **Comment c'est construit** : les couches, leurs frontières, et le trajet d'un chiffre de bout en bout |
| [docs/architecture-notes.md](docs/architecture-notes.md) | Points d'architecture notés en chemin |
| [docs/contexte-produit.md](docs/contexte-produit.md) | Objectif, public, contraintes, hors périmètre |
| [docs/glossaire.md](docs/glossaire.md) | Notions financières : définition et formule retenue |
| [docs/sources-de-cours.md](docs/sources-de-cours.md) | **Comparatif des sources de cours** (étape 4) : ce qui est vérifié, ce qui est écarté, et les pièges |
| [docs/couts-et-fiscalite.md](docs/couts-et-fiscalite.md) | **Comparatif des coûts estimés et des règles fiscales** (étape 6) : TER, spreads, impôt par poche, avec les sources officielles |
| [docs/composition-des-etf.md](docs/composition-des-etf.md) | **Comparatif des sources de composition d'ETF** (étape 7) : ce qui est retenu, ce qui est écarté, et les 19 pièges vérifiés |
| [docs/reglages-automatiques.md](docs/reglages-automatiques.md) | **Comparatif des sources des réglages** (étape 8 quater) : cotation contrôlée par le prix payé, TER de l'émetteur, contenu d'un fonds, date du PEA — mesures et pièges |
| [docs/export-officiel.md](docs/export-officiel.md) | **L'export officiel de Trade Republic** (D-79) : ses colonnes, les types vus, ce qui est vérifié et ce qui reste à confirmer |
| [docs/inventaire-donnees.md](docs/inventaire-donnees.md) | *Historique* : la structure des données pytr, retiré à l'étape 8 ter (D-81). Ses pièges expliquent bien des décisions |
| [docs/verification/](docs/verification/) | Cahiers de vérification : cas fictifs refaisables à la main, et contrôles sur les vraies données |
| [docs/decisions.md](docs/decisions.md) | Journal des décisions (raison + ce qui est écarté) |
| [docs/questions-ouvertes.md](docs/questions-ouvertes.md) | Arbitrages en attente du propriétaire |
| [scripts/inventaire_structure.py](scripts/inventaire_structure.py) | Relevé structurel d'un export officiel, sans afficher aucune valeur : à lancer sur l'export d'un tiers pour y chercher des types jamais vus |

## Règles de travail

1. **Aucune donnée dans git.** Pas d'export, de JSON, de CSV, d'identifiant. Vérifier `git status` avant chaque commit.
2. **Tout dossier `data_*/` (autre que `data/`) appartient à un tiers.** Lecture de structure uniquement : ne jamais copier, citer une valeur ou versionner.
3. **Valeurs fictives dans la doc**, y compris pour les données du propriétaire (montants, ISIN, comptes, noms).
4. **Pas de calcul fondé sur un texte affiché** (libellés allemands/français). Si c'est inévitable, isoler et marquer comme fragilité.
5. **Un type d'événement inconnu n'est jamais ignoré ni classé par défaut** : l'application l'affiche.
6. **Toute déduction est explicite, isolée, et signalée à l'utilisateur** dans l'interface.
7. **En cas de doute entre deux interprétations : ne pas trancher.** Ajouter la question dans `docs/questions-ouvertes.md` et demander.
8. **Principes d'architecture** (détail dans `docs/decisions.md`) :
   - les espèces ne sont jamais suivies (D-11) ;
   - la performance est calculée en montants bruts, les frais et taxes à part (D-21) ;
   - le moteur ne lit que le format pivot, Trade Republic n'étant qu'un adaptateur (D-26) ;
   - les opérations viennent de l'**export officiel** de la banque, jamais d'une interface non
     officielle (D-79). **Aucune liste des types n'est publiée** : un type jamais vu sur un vrai
     fichier n'est pas traité, il est affiché ;
   - **l'utilisateur dépose l'export, et c'est tout** (D-80) : toute autre valeur est trouvée
     automatiquement, contrôlée et affichée avec sa source. Une correction à la main est possible,
     jamais nécessaire ; ce qui ne se trouve pas de façon fiable est un trou affiché, jamais une
     question ni une valeur par défaut ;
   - **un fichier déposé est un portefeuille** (D-109) : les exports ne se cumulent jamais, et
     Pastory n'en lit qu'un à la fois. Deux exports se comparent par leurs identifiants
     d'opération, jamais par leur nom ;
   - les cours sont **bruts** (jamais retraités des dividendes) et leur **devise est vérifiée**,
     jamais convertie (D-48, D-51). Aucun cours ne passe par Trade Republic (D-49) ;
   - **un taux estimé (spread, TER, impôt) porte sa valeur, sa date et sa source**, dans un
     fichier de `pastory/parametres/` ; sans date ni source, il est refusé (D-58). Les
     estimations ne se mélangent jamais aux coûts payés ni à la performance (D-17) ;
   - **une répartition se calcule sur des codes, jamais sur des libellés** (pays en ISO 3166-1,
     secteurs en code de nomenclature), avec **une seule nomenclature nommée à l'écran** — jamais
     « GICS » (D-65, D-66). On lit les **agrégats** d'un fonds, jamais ses lignes détenues : un ETF
     synthétique ne détient pas son indice (D-63, D-64). Ce qui n'est pas attribué reste visible, et
     rien n'est jamais renormalisé à 100 % (D-69) ;
   - **l'interface suit la charte graphique** ([docs/charte-graphique.md](docs/charte-graphique.md),
     D-98) : toutes les couleurs, polices et espacements viennent de
     `pastory/vues/assets/theme.css`, et **aucune couleur n'est écrite en dur ailleurs**. Une
     modification visuelle ne change jamais un chiffre.
   - **le serveur local ne répond qu'à l'ordinateur où il tourne, et par son nom** (D-115) :
     il n'écoute que `127.0.0.1` et refuse toute demande adressée à un autre nom. Ce qu'un
     écran ne propose pas (déposer en démonstration), le serveur le refuse aussi. **Le dépôt
     est public** : rien de personnel n'y entre, pas même dans un message de commit.
9. Toute décision structurante est ajoutée à `docs/decisions.md`. Tout point d'architecture qui apparaît en discussion est noté dans `docs/architecture-notes.md`. Les notes initiales évoluent quand le propriétaire change de cap.
10. **Les choix de fonctionnalités visent l'utilisateur type de Trade Republic**, pas le
    portefeuille du propriétaire (D-62). Un cas courant chez cette banque est traité même s'il ne le
    concerne pas ; et tout message d'absence, de déduction ou d'estimation est écrit pour quelqu'un
    qui n'a pas suivi la construction du projet.
