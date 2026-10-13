# Cahier de vérification — étape 11 : la publication

Rendre le dépôt public sans risque ([D-115](../decisions.md), [D-116](../decisions.md)). L'étape
ne calcule aucun chiffre : ce cahier dit **ce qui a été cherché, comment, et ce qui a été
trouvé**, puis ce qu'il reste à faire à la main sur GitHub.

---

## 1. Aucune donnée personnelle dans l'historique

### Ce qui a été cherché

Un dépôt public montre **tout son passé**, pas seulement ses fichiers d'aujourd'hui. Chaque ligne
ajoutée par chacun des 115 commits a donc été relue — 94 000 lignes, messages de commit compris
— de deux façons :

- **avec des aiguilles**, tirées des vrais exports rangés sur la machine du propriétaire : leurs
  identifiants d'opération, leurs IBAN, leurs noms de fichiers (donc les noms de portefeuille),
  leurs textes libres, leurs codes de titres. Ces valeurs n'ont été ni affichées ni écrites : le
  relevé ne rend que des comptes et des noms de fichiers ;
- **avec des motifs** : tout ce qui a la forme d'un IBAN, d'une adresse de courriel, d'un numéro
  de téléphone, d'un identifiant unique, d'un chemin d'utilisateur, d'un mot de passe ou d'un
  jeton suivi d'une valeur.

### Ce qui a été trouvé

| Recherché | Trouvé |
|---|---|
| Identifiants d'opération des vrais exports | **aucun** |
| IBAN des vrais exports | **aucun** |
| Noms de portefeuille | **aucun** |
| Nom du dossier d'un tiers | **aucun** |
| Fichiers de données (CSV, JSON, tableur, PDF) passés un jour par l'historique | **aucun** |
| Chemins d'utilisateur de la machine | **aucun** |
| Mots de passe, jetons, clés | **aucun** |
| Quelque chose en forme d'IBAN | un seul, tout en zéros : celui de la démonstration |
| Quelque chose en forme de téléphone | un seul : le numéro d'exemple d'une ancienne invite |
| Adresse de courriel dans les fichiers | une seule, celle de l'assistant, dans les messages de commit |

Deux choses à savoir, qui ne sont pas des fuites :

- **deux codes de fonds publics** présents dans un vrai export figurent aussi dans la
  documentation, comme exemples de mesure (un fonds « PEA Monde » à swap, un fonds « PEA
  Émergent » de la démonstration). Rien n'y dit qu'ils sont détenus ;
- **deux libellés de la banque** (« Versement PEA », « PEA activation ») : ce sont ses mots, pas
  des données.

### L'adresse de courriel du propriétaire

Elle n'était dans aucun fichier, mais dans **la signature de chaque commit**. Le propriétaire a
choisi de la retirer : tout l'historique a été réécrit avec l'adresse anonyme que GitHub fournit
à cet effet. Tous les identifiants de commit ont changé.

### À vérifier par toi

- [ ] Sur GitHub, ouvre un commit au hasard : il porte ton nom, et pas ton adresse.
- [ ] Dans les réglages de ton compte GitHub (*Settings → Emails*), coche **« Keep my email
  addresses private »** et **« Block command line pushes that expose my email »** : GitHub
  refusera alors tout envoi qui la contiendrait.

---

## 2. La revue de sécurité

Faite par un agent indépendant, par lecture de tout le code (rien n'a été lancé) : le serveur
local, les dépôts de fichiers, les caches, les commandes, le fichier d'installation, l'affichage,
les téléchargements, et ce qui quitte l'ordinateur.

### Le seul constat, corrigé

**Le serveur ne vérifiait pas à quel nom on s'adressait à lui.**

Pastory n'écoute que l'ordinateur où il tourne (`127.0.0.1`). Cela arrête les autres machines,
pas les autres **sites** ouverts dans le même navigateur. D'ordinaire le navigateur interdit à un
site de lire les réponses d'un autre. Mais un site malveillant peut faire pointer **son propre
nom** vers `127.0.0.1` : pour le navigateur, c'est alors « le même site » que Pastory, et
l'interdiction tombe. La page aurait pu lire les écrans — donc le portefeuille —, et supprimer un
export.

Une telle demande porte forcément le nom de l'attaquant. Pastory refuse désormais toute demande
qui ne porte pas le sien :

| Demande adressée à | Avant | Après |
|---|---|---|
| `127.0.0.1:8050` ou `localhost:8050` | servie | servie |
| `un-autre-nom.example:8050` | **servie** | **refusée (403)** |

Vérifié sur un vrai serveur, et le lanceur reconnaît toujours son propre Pastory. L'attaque n'a
pas été jouée pour de vrai : elle demande un nom de domaine et un serveur de noms.

### Ce qui a été examiné et trouvé sain

- **Un autre site ne peut pas déclencher une action** (déposer, renommer, supprimer) : Pastory
  n'accepte que des demandes d'un type que le navigateur ne laisse pas partir d'un autre site
  sans permission, et il n'en donne aucune.
- **Aucun nom de fichier ne sort du dossier** : ni celui d'un export déposé, ni un nom de
  portefeuille saisi à l'écran, ni un code de titre venu d'un export ou d'une source.
- **Aucun texte venu d'un export ou d'une source n'est interprété par la page** : il est
  toujours écrit comme du texte.
- **Les téléchargements** vérifient les certificats et visent des adresses fixes ; le fichier de
  la liste de Xetra est lu sans être décompressé sur le disque.
- **Ce qui quitte l'ordinateur** : des codes de titres, des noms, une période. Jamais un montant,
  une quantité ni une identité ; et rien du tout pour l'export d'un tiers ou hors ligne.
- **Le fichier d'installation** : chaque chemin y est entre guillemets, et il ne lance que le
  script officiel d'`uv`, après une touche.

### Ce qui est connu et laissé

- **Une formule dans un CSV exporté.** Un export forgé, dont un nom de titre commencerait par
  `=`, verrait sa formule évaluée par un tableur si l'on ouvre le fichier que produit `pastory
  exporter-pivot`. Il faut pour cela déposer soi-même un fichier forgé par quelqu'un d'autre, puis
  l'exporter depuis un terminal. Non corrigé.

### À vérifier par toi

- [ ] Ouvre Pastory par son icône : tout marche comme avant.
- [ ] Pastory ouvert, ouvre `http://localhost:8050` dans ton navigateur habituel : la page
  s'affiche — c'est l'un des deux noms acceptés. (Le refus d'un autre nom, lui, ne se vérifie pas
  à la main sans nom de domaine : il est tenu par des tests.)

---

## 3. Ce que le dépôt public montre

- **La page d'accueil** ([README.md](../../README.md)) : ce que fait Pastory, quatre captures du
  **portefeuille de démonstration** — des opérations inventées —, l'installation, ce qu'il n'est
  pas, ses sources et leurs limites, comment il a été fait, sa licence.
- **La licence MIT** ([LICENSE](../../LICENSE)), et à côté de chaque œuvre de tiers la sienne.
- **Tous les documents de travail** : les décisions, la feuille de route, les règles données à
  l'assistant (`CLAUDE.md`), le prompt de la session suivante. Ils ne contiennent aucune donnée,
  mais ils racontent le chantier tel qu'il s'est passé — les essais ratés, les défauts trouvés,
  l'antivirus de ta machine. C'est un choix : dis-le si tu préfères en retirer.

### À vérifier par toi

- [ ] Relis le [README](../../README.md) comme si tu ne connaissais pas le projet. En
  particulier la section « Comment ce projet a été fait », qui dit que tu ne codes pas.
- [ ] Vérifie que les quatre captures sont bien celles de la démonstration.

---

## 4. Les gestes qui restent, sur GitHub

Le dépôt qui existe aujourd'hui sur GitHub — renommé `Pastory` le 2026-10-13, toujours privé —
ne doit **pas** être rendu public : il porte l'historique d'avant la réécriture, avec ton
adresse, et un dépôt garde la trace de ce qu'on y a écrasé. On publie un dépôt neuf.

1. **Écarte l'ancien dépôt** : renomme-le `Pastory-archive` (*Settings → General → Repository
   name*) et laisse-le privé. Tu pourras le supprimer plus tard ; ton ordinateur a tout.
2. **Crée un dépôt neuf** nommé `Pastory`, **privé**, et **vide** : ne coche ni README, ni
   licence, ni `.gitignore`.
3. **Envoie le code** : dans un terminal ouvert dans le dossier du projet, `git push -u origin
   main` (l'adresse `github.com/TheoDuc/Pastory` est déjà réglée).
4. **Regarde-le en privé** : la page d'accueil, les images, la licence que GitHub reconnaît, un
   commit sans ton adresse.
5. **Rends-le public** : *Settings → General → Danger Zone → Change repository visibility*.
6. Sur la page du dépôt, renseigne la description et quelques mots-clés (*About* → la roue
   dentée) : c'est ce que montrent les recherches.

Une sauvegarde complète du dépôt d'avant la réécriture est rangée hors du projet, dans ton
dossier personnel (`Pastory-avant-reecriture.bundle`). Elle contient ton adresse : supprime-la
quand tu n'en as plus besoin, et ne l'envoie nulle part.
