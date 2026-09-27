# Prompt pour la session suivante

Une étape = une nouvelle session Claude ([feuille-de-route.md](feuille-de-route.md)). Ce fichier
contient le message à copier-coller au début de la prochaine, et ce qu'elle doit savoir avant de
commencer.

> **À mettre à jour par l'instance qui termine une étape**, avant la fusion dans `main`. La
> dernière section dit comment.
>
> Dernière mise à jour : **2026-09-27**, fin de l'étape 6.

---

## Le message à copier

```
Lis CLAUDE.md puis docs/feuille-de-route.md, et docs/prompt-session-suivante.md.
On attaque l'étape 7 : la diversification géographique et sectorielle.
```

---

## Où en est le projet

- **Étapes 0 à 6 terminées.** L'application lit un export Trade Republic, en sort des opérations
  au format pivot, va chercher les **cours de marché**, en déduit **quantité détenue, capital net
  investi, prix de revient, frais, taxes, dividendes et plus-values réalisées**, puis **la valeur
  des actifs** et les **trois chiffres clés** — gain en €, TRI, TWRR (D-22). Elle sait désormais
  aussi dire **ce que tout cela coûte** (frais et taxes payés avec leur poids, spread et frais
  courants estimés) et **ce qu'on récupérerait en vendant tout** : valeur réelle, impôt estimé
  par poche (D-23). Elle peut enfin comparer ses quantités avec ce que la banque dit détenir.
- **Prochaine : étape 7**, la diversification géographique et sectorielle réelle, en regardant à
  l'intérieur des ETF (Q-22). Elle commence par un **agent de recherche** sur les sources
  gratuites de composition d'ETF (D-28), comme les étapes 4 et 6.
- **Une question ouverte** : **Q-26** (rapprocher le PEA), non bloquante. **Q-21** (présentation
  des frais) est répondue côté calculs ; il ne reste que la présentation à l'écran, pour
  l'étape 8.

**Ce qui existe déjà :**

| Où | Quoi |
|---|---|
| [format-pivot.md](format-pivot.md) | **Le contrat**, en deux parties : les opérations (§1 à §8) et la photo du portefeuille (§9) |
| [architecture.md](architecture.md) | **Comment c'est construit** : les couches, leurs frontières, le trajet d'un chiffre |
| [glossaire.md](glossaire.md) | Chaque formule, dont le gain, le TRI, le TWRR (§4 et §5) et les coûts, l'impôt et la valeur réelle (§6) |
| [couts-et-fiscalite.md](couts-et-fiscalite.md) | **Comparatif de l'étape 6** : d'où viennent le TER, les spreads et les règles fiscales, avec les pièges |
| `dashboard_tr/pivot/` | `Operation`, `PositionReelle`, les contrôles de cohérence et l'export CSV |
| `dashboard_tr/adaptateurs/trade_republic/` | L'adaptateur complet, en couches testables |
| `dashboard_tr/donnees_externes/` | `cours.py` (le contrat), `cache.py`, `yahoo.py`, `completion.py`, `xetra.py` (le TER) |
| `dashboard_tr/parametres/` | Les taux datés et sourcés : `fiscalite.toml`, `couts.toml`, et `lecture.py` qui les refuse s'ils ne le sont pas |
| `dashboard_tr/moteur/` | `position.py` (le rejeu), `portefeuille.py`, `valorisation.py`, `rendements.py`, `couts.py`, `fiscalite.py`, `valeur_reelle.py`, `rapprochement.py`, `export_csv.py` (huit CSV), `rapport.py` |
| `dashboard_tr/cli.py` | 10 commandes, options `--au`, `--depuis`, `--hors-ligne` ; `ouvrir` arrive à l'étape 9 |
| [decisions.md](decisions.md) | D-01 à D-61. L'étape 6 a ajouté D-55 à D-61 |
| [verification/etape-6.md](verification/etape-6.md) | Le cahier des coûts, de l'impôt et de la valeur réelle |

**Ce qui n'existe pas encore :** la diversification, et l'interface.

---

## Ce que l'étape 7 doit savoir de l'étape 6

- **Une donnée externe entre dans le moteur par un protocole, jamais par un import.** C'est
  désormais fait trois fois, de la même façon : les cours (`SourceDeValorisation`), les
  paramètres de coûts (`ParametresDeCouts`), les règles fiscales (`ReglesFiscales`). Le moteur
  déclare la forme qu'il attend, `cli.py` fournit l'objet. **La composition d'un ETF suivra le
  même chemin** : un protocole dans le moteur, une source dans `donnees_externes/`, un
  branchement dans `cli.py`. Aucun import de `moteur/` vers `donnees_externes/`, `config/` ou
  `parametres/` — un test et le §3 de l'architecture en font foi.
- **Le schéma « proposé, puis validé » est acquis, et il a fait ses preuves deux fois** : ISIN →
  ticker (étape 4), puis type d'actif et TER (étape 6). Une source qui se trompe 5 % du temps est
  utilisable **à condition** que l'utilisateur relise. Pour la composition d'un ETF, la même
  question se posera : que fait-on quand la source ignore un actif, et comment le dire.
- **Un taux, un ratio, un pourcentage doit porter sa date et sa source** (D-58). Le paquet
  `parametres/` existe pour ça, avec son contrôle de vraisemblance ; une composition d'ETF datée
  du mois dernier n'est pas la même chose qu'une composition d'il y a trois ans, et l'affichage
  doit le dire.
- **La liste des ETF de Xetra est déjà téléchargée par `donnees_externes/xetra.py`**, et elle
  contient plus que le TER : nom, politique de distribution, indice de référence, devise. Si la
  recherche de l'étape 7 en a besoin, le téléchargement et la lecture du fichier sont écrits, avec
  leurs quatre pièges traités (extension `.xls` qui ment, adresse qui change à chaque publication,
  valeur en fraction avec bruit de flottant, ISIN répété par devise).
- **Le type d'actif est déclaré dans `actifs.toml`** (D-55) : `etf`, `action` ou `crypto`. C'est
  déjà la distinction dont l'étape 7 a besoin pour savoir dans quoi regarder — seul un ETF a une
  composition à ouvrir.
- **Un actif sans donnée sort des totaux, qui sont marqués partiels.** C'est D-53, et l'étape 6 l'a
  appliqué trois fois de plus (actif sans cours, sans type, ETF sans TER). Une répartition
  géographique qui ignore 20 % du portefeuille doit le dire, et ne jamais normaliser à 100 % en
  silence.
- **Le rapport a sa limite de largeur et son test cp1252.** Cinq blocs en ont un aujourd'hui.
  **En ajouter un pour tout nouveau bloc**, et vérifier qu'aucune ligne ne dépasse 100 caractères :
  une répartition en colonnes est précisément le genre de bloc qui déborde.
- **Les huit CSV suivent les conventions de `tableur.py`**, et jamais une case vide pour une valeur
  absente (`VALEUR_SANS_OBJET` / `VALEUR_A_COMPLETER`).

**Ce que le propriétaire a vérifié à l'étape 6 (2026-09-27), et la leçon à garder.** Il a
configuré le type et le TER de ses actifs, déclaré la date de son PEA, et confirmé les chiffres.
Sa vérification a trouvé non pas une erreur de calcul mais un **défaut d'affichage**, et c'est le
point à retenir : la plus-value d'une poche arrivait **déjà nette** des coûts de sortie, sans
montrer l'étape d'avant. Il ne pouvait donc la rapprocher d'aucun chiffre de son application, et
une petite position en crypto affichait même une plus-value **négative** alors qu'elle avait
gagné — l'euro de frais de vente, facturé **par ligne**, pesant plusieurs pour cent d'une position
de quelques dizaines d'euros. Le détail de chaque impôt montre désormais la plus-value en deux
temps : avant coûts de sortie, puis ces coûts retranchés.

**La règle qui en sort, et qui vaut pour l'étape 7 :** un chiffre juste qu'on ne peut rapprocher
d'aucune autre source est un chiffre qu'on ne croit pas. Chaque fois qu'un résultat est **net**
de quelque chose, montrer le brut et la retenue séparément. Une répartition géographique
« hors actifs non couverts » posera exactement la même question.

**Ce qui n'a pas pu être vérifié à l'étape 6, et qui reste à la charge du propriétaire :**

1. **La grille tarifaire française de Trade Republic.** Le document public refuse les
   téléchargements automatiques (403) : les montants retenus — 1 € par ordre à l'achat comme à la
   vente, 0 € par exécution de plan, 1 € par ordre crypto — viennent de la version allemande
   (04.2023) et du communiqué du 2 juillet 2026. Il doit les confirmer dans son application
   (Profil → Documents légaux).
2. **Les taux fiscaux, non relus par un tiers.** Interrogé, le propriétaire a répondu : « je ne
   m'y connais pas, base-toi sur tes recherches » (Q-38). Les taux viennent donc de Légifrance, du
   BOFiP et d'impots.gouv.fr, et le principal (31,4 %) a été recoupé. **Ils sont datés et sourcés
   dans `parametres/fiscalite.toml` :** une correction future ne demande aucune ligne de code.
   À relire en janvier 2027, après la loi de finances.

**Le piège fiscal qu'une session future ne doit pas refaire :** en 2026, les prélèvements sociaux
sur les revenus du capital valent **18,6 %**, pas 17,2 %. La loi de financement de la sécurité
sociale pour 2026 a relevé la CSG de 9,2 à 10,6 %. Le PFU vaut donc **31,4 %**, pas 30 %. Beaucoup
de pages en ligne — et même un paragraphe du BOFiP sur la crypto — affichent encore l'ancien taux.
**La loi prime, et le fichier de paramètres porte la référence exacte.**

---

## À savoir pour travailler sur cette machine

- **`uv` a besoin de `--native-tls`** : l'antivirus Norton inspecte le trafic chiffré, et le jeu
  de certificats par défaut ne le reconnaît pas. `uv sync --native-tls`, `uv run --native-tls …`.
- **L'antivirus peut couper Claude Code en pleine session.** Le 2026-09-26, **Avast WebShield** a
  bloqué `api.anthropic.com` en annonçant un contenu « malveillant » — un faux positif de son
  inspection HTTPS, même mécanisme que le point précédent. Conséquences en chaîne, à reconnaître
  du premier coup d'œil :
  1. une erreur **403 « blocked by Avast WebShield »** apparaît ;
  2. les agents de recherche en cours meurent tous en même temps, laissant le tour de conversation
     **incomplet** ;
  3. chaque relance renvoie alors cet état invalide et répond **400 Bad Request**, indéfiniment.
     Se reconnecter ne sert à rien : **il faut ouvrir une nouvelle session.** Le travail déjà
     écrit sur le disque est intact, et les résultats des recherches restent récupérables dans les
     journaux de la session (`~/.claude/projects/<projet>/<session>/subagents/`).

  **Prévention :** ajouter `api.anthropic.com` aux exclusions d'Avast (*Menu → Paramètres →
  Protection → Web Shield*). Et pour toute recherche en ligne longue : **écrire les trouvailles
  dans un fichier au fur et à mesure**, plutôt que de les garder dans la conversation. Les trois
  agents de l'étape 6 l'ont fait, et aucun n'a rien perdu.
- **Une longue session peut atteindre la limite de crédits en pleine écriture.** Arrivé le
  2026-09-27 pendant l'étape 6. Rien n'est perdu : le disque est à jour, `git status` dit où on en
  est, et les tests disent si le dernier morceau écrit tient. Reprendre là où le fichier s'arrête.
- **Deux blocs `<<'EOF'` dans une même commande shell cassent l'interpréteur** (« unexpected EOF »).
  Et un texte français passé par un script inline voit ses `\\n` échappés une fois de trop, ce qui
  casse les f-strings. **Pour toute modification de fichier un peu longue, écrire un script dans
  le dossier de travail temporaire et le lancer** : c'est ce que l'étape 6 a fini par faire
  systématiquement.
- **L'éditeur applique une limite de 88 caractères, le projet en fixe 100** (`pyproject.toml`).
  Les diagnostics E501 de l'IDE sous 100 caractères ne sont pas des erreurs du projet :
  `uv run ruff check .` fait foi.
- **OneDrive synchronise le projet** (D-24). Si une commande échoue avec un « accès refusé »
  inexpliqué, c'est la première piste. Le `.venv` a déjà dû être recréé pour cette raison.
- **La console Windows écrit en cp1252** : elle ne sait afficher ni les traits de tableau, ni les
  coches, ni les flèches. Un rapport qui en contiendrait ferait échouer la commande **au moment
  de l'afficher**, alors que le calcul, lui, s'est bien passé. Le CLI force la sortie en UTF-8
  par précaution, et des tests vérifient que les rapports restent affichables en cp1252. En
  ajouter un pour tout nouveau bloc. *(C'est pourquoi le rapport écrit « VALEUR REELLE » et
  « ECART DE PRIX » sans accents sur les capitales.)*
- **Aucun test ne sort de la machine, et deux fixtures automatiques le garantissent** dans
  `tests/test_cli.py` : l'une détourne le dossier personnel, l'autre **coupe la liste des ETF de
  Xetra**. La seconde a été ajoutée après avoir constaté que deux tests appelaient réellement
  Deutsche Börse (ils duraient deux secondes). Si un test devient lent, c'est la première piste.
- **La saisie du PIN n'affiche rien du tout.** Sous Windows, `getpass` lit les caractères
  directement depuis la console (`msvcrt.getwch`) : ni chiffres, ni étoiles, ni curseur qui
  avance. Le propriétaire a cru à un blocage la première fois. `rafraichir` et
  `positions-reelles` le préviennent maintenant en toutes lettres.
  **Corollaire :** `msvcrt` exige une **vraie console Windows**. Dans Git Bash (MinTTY), la
  saisie ne fonctionne pas et la commande reste bloquée. Il faut les lancer depuis PowerShell,
  `cmd` ou le terminal intégré de VS Code — pas depuis Git Bash.
- **Chaque appel à pytr est une connexion complète** : comme rien n'est enregistré (D-41), le
  numéro, le PIN et la confirmation dans l'application sont redemandés à chaque fois. C'est
  pourquoi `positions-reelles` est une commande à part et non un morceau de `rafraichir` (D-46).
- **Utiliser pytr comme bibliothèque réserve deux pièges**, tous deux rencontrés en écrivant le
  diagnostic des comptes-titres. La commande `pytr` ne les a pas, parce qu'elle règle ces deux
  points elle-même :
  1. `pytr.account.login()` a pour défaut `waf_token="playwright"`, qui exige un navigateur à
     installer à part. Message obtenu : « playwright is not installed ». La ligne de commande,
     elle, passe `"default"`, qui se résout à **aucun jeton** dès lors qu'on est en `v2`. Il faut
     donc écrire `login(v2=True, waf_token="default")` ;
  2. `login()` se termine par `log.debug(get_settings(tr))` — **le JSON complet du compte**, nom
     et numéros compris. Il ne s'imprime pas aujourd'hui, le journal s'installant au niveau
     « info » par défaut, mais c'est un défaut de bibliothèque tierce. Tout script qui promet de
     n'afficher aucune valeur doit poser un **filtre** sur le logger `account`, comme le fait
     `museler_le_journal_de_pytr()` : pytr remet son niveau à `DEBUG` et réinstalle ses
     gestionnaires à chaque appel, mais ne touche jamais aux filtres déjà posés.
- Commandes utiles : `uv run pytest`, `uv run ruff check .`, `uv run dashboard emplacements`.
- Pour travailler sur un export sans le copier dans le projet :
  `uv run dashboard lire --export <dossier>` (idem pour `positions`).
- Le propriétaire **ne code pas** : il vérifie les chiffres. Tout calcul doit être refaisable à
  la main, et les options techniques lui sont présentées avec leurs avantages et inconvénients.
  Il tranche vite et fait confiance aux recommandations quand elles sont argumentées : les sept
  arbitrages de l'étape 6 ont été acceptés d'un bloc. **Cela oblige à recommander avec soin**, et
  à écrire ce qui n'a pas pu être vérifié.

---

## Comment mettre à jour ce fichier

À la fin d'une étape, avant la fusion dans `main` :

1. remplacer **le message à copier** par celui de l'étape suivante ;
2. mettre à jour **où en est le projet** : ce qui vient d'être ajouté, ce qui reste à faire, les
   questions encore ouvertes ;
3. écrire **ce que l'étape suivante doit savoir** : les pièges rencontrés, et ce sur quoi elle
   peut s'appuyer sans se méfier ;
4. compléter **à savoir pour travailler sur cette machine** si un piège nouveau est apparu ;
5. changer la date de la dernière mise à jour.

Ce fichier reste **court** : il oriente, il ne duplique pas la documentation. Et comme tout le
dépôt, il n'utilise **aucune valeur réelle** ([D-03](decisions.md)).
