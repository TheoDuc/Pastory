# DashBoard Trade Republic

Tableau de bord local et gratuit pour suivre un portefeuille Trade Republic, destiné à des
investisseurs long terme. Les données viennent de `pytr` (export JSON d'événements + CSV).
Le propriétaire du projet ne code pas : il vérifie les chiffres. Tout calcul doit donc être
lisible et vérifiable à la main.

## Où trouver quoi

| Fichier | Contenu |
|---|---|
| [docs/notes-initiales.md](docs/notes-initiales.md) | **Référence** des intentions du propriétaire (retranscription de ses notes) |
| [docs/contexte-produit.md](docs/contexte-produit.md) | Objectif, public, contraintes, hors périmètre |
| [docs/glossaire.md](docs/glossaire.md) | Notions financières : définition et formule retenue |
| [docs/inventaire-donnees.md](docs/inventaire-donnees.md) | Structure des données pytr, type par type, et pièges |
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
8. Toute décision structurante est ajoutée à `docs/decisions.md`. Les notes initiales évoluent quand le propriétaire change de cap.
