# DashBoard Trade Republic

Tableau de bord local et gratuit pour suivre **les actifs** d'un portefeuille Trade Republic
(PEA, CTO, crypto ; les espèces ne sont pas suivies), destiné à des investisseurs long terme. Les données viennent de `pytr` (export JSON d'événements + CSV).
Le propriétaire du projet ne code pas : il vérifie les chiffres. Tout calcul doit donc être
lisible et vérifiable à la main.

## Où trouver quoi

| Fichier | Contenu |
|---|---|
| [docs/prompt-session-suivante.md](docs/prompt-session-suivante.md) | **À lire en premier** : où en est le projet, et ce que la session en cours doit savoir. À mettre à jour à la fin de chaque étape |
| [docs/feuille-de-route.md](docs/feuille-de-route.md) | **Étapes du projet**, étape en cours, méthode de travail |
| [docs/notes-initiales.md](docs/notes-initiales.md) | **Référence** des intentions du propriétaire (notes + évolutions de cap) |
| [docs/format-pivot.md](docs/format-pivot.md) | **Le format des opérations** : le contrat entre les adaptateurs et le moteur |
| [docs/architecture.md](docs/architecture.md) | **Comment c'est construit** : les couches, leurs frontières, et le trajet d'un chiffre de bout en bout |
| [docs/architecture-notes.md](docs/architecture-notes.md) | Points d'architecture notés en chemin |
| [docs/contexte-produit.md](docs/contexte-produit.md) | Objectif, public, contraintes, hors périmètre |
| [docs/glossaire.md](docs/glossaire.md) | Notions financières : définition et formule retenue |
| [docs/sources-de-cours.md](docs/sources-de-cours.md) | **Comparatif des sources de cours** (étape 4) : ce qui est vérifié, ce qui est écarté, et les pièges |
| [docs/couts-et-fiscalite.md](docs/couts-et-fiscalite.md) | **Comparatif des coûts estimés et des règles fiscales** (étape 6) : TER, spreads, impôt par poche, avec les sources officielles |
| [docs/inventaire-donnees.md](docs/inventaire-donnees.md) | Structure des données pytr, type par type, et pièges. **Le §11 recense ceux trouvés en écrivant l'adaptateur** |
| [docs/verification/](docs/verification/) | Cahiers de vérification : cas fictifs refaisables à la main, et contrôles sur les vraies données |
| [docs/decisions.md](docs/decisions.md) | Journal des décisions (raison + ce qui est écarté) |
| [docs/questions-ouvertes.md](docs/questions-ouvertes.md) | Arbitrages en attente du propriétaire |
| [scripts/inventaire_structure.py](scripts/inventaire_structure.py) | Relevé structurel d'un export, sans afficher aucune valeur |

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
   - les cours sont **bruts** (jamais retraités des dividendes) et leur **devise est vérifiée**,
     jamais convertie (D-48, D-51). Aucun cours ne passe par Trade Republic (D-49) ;
   - **un taux estimé (spread, TER, impôt) porte sa valeur, sa date et sa source**, dans un
     fichier de `dashboard_tr/parametres/` ; sans date ni source, il est refusé (D-58). Les
     estimations ne se mélangent jamais aux coûts payés ni à la performance (D-17).
9. Toute décision structurante est ajoutée à `docs/decisions.md`. Tout point d'architecture qui apparaît en discussion est noté dans `docs/architecture-notes.md`. Les notes initiales évoluent quand le propriétaire change de cap.
