/* Construit les maquettes de l'étape 8 à partir du jeu de données fictif.
 *
 * CE QUI EST VRAIMENT CALCULÉ ICI, et non recopié :
 *   - le gain, par la formule du glossaire : valeur finale − valeur initiale + flux ;
 *   - le TRI, par dichotomie sur les flux datés, comme le moteur ;
 *   - le TWRR, en chaînant les sous-périodes bornées par les jours de flux ;
 *   - la variation de chaque actif sur la période choisie.
 * Conséquence voulue : changer de période ou décocher une poche donne des chiffres
 * cohérents entre eux, et l'onglet « Détail des calculs » montre les tables qui les
 * produisent.
 *
 * Rien ici ne préjuge du code de l'étape 9 : Dash reconstruira ces blocs en Python.
 * Ce qui se transmet, c'est la feuille de style et la disposition.
 */

(function () {
  "use strict";

  const D = window.MAQUETTE;
  const POCHES = D.poches;

  /* LA PALETTE, EN VALEURS LITTERALES.
   *
   * Elle double les variables de la feuille de style, et c'est une necessite, pas une
   * negligence : `stroke="var(--poche-1)"` dans un ATTRIBUT SVG n'est pas interprete par
   * Chrome ni Safari — seule une declaration CSS substitue une variable. Tous les SVG de
   * la maquette avaient donc des couleurs invalides, et l'anneau des poches ne montrait
   * pas les couleurs de ses poches. C'est le defaut signale par le proprietaire.
   *
   * Regle qui en sort, et qui vaut pour l'etape 9 : une couleur posee en attribut SVG
   * est ecrite en clair ; une couleur posee en CSS passe par la variable. */
  const COULEURS = {
    papier: "#ece3d0",
    surface: "#f3ecdd",
    surfaceCreuse: "#e0d5bd",
    trait: "#d2c7ae",
    encre: "#2c2722",
    encreDouce: "#665c51",
    encreTresDouce: "#6f6559",
    courbeBrut: "#1d6c93",
    courbeInvesti: "#665c51",
    absent: "#ada08a",
    poche: { PEA: "#1b4a63", CTO: "#37738c", Crypto: "#6fa0b4" },
  };
  const COULEUR_POCHE = COULEURS.poche;

  /** Une teinte d'une rampe d'une seule couleur, du fonce au clair, rendue en
   *  hexadecimal : il faut une valeur lisible par calcul pour choisir la couleur du
   *  texte pose dessus. */
  function hslEnHex(teinteDegres, saturation, clarte) {
    const s = saturation / 100;
    const l = clarte / 100;
    const k = function (n) {
      return (n + teinteDegres / 30) % 12;
    };
    const a = s * Math.min(l, 1 - l);
    const f = function (n) {
      const valeur = l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
      return Math.round(255 * valeur)
        .toString(16)
        .padStart(2, "0");
    };
    return "#" + f(0) + f(8) + f(4);
  }

  /** Une copie triee de la plus grosse part a la plus petite. Les anneaux et les
   *  classements se lisent ainsi de haut en bas et dans le sens horaire, ce qui rend le
   *  sens de lecture evident — sans quoi la petite part collee avant midi se confond
   *  avec la premiere ligne de la legende. */
  function parTaille(liste, champ) {
    return liste.slice().sort(function (a, b) {
      return (b[champ] || 0) - (a[champ] || 0);
    });
  }

  // ==========================================================================
  // 1. MISE EN FORME
  // Deux unités, deux fonctions. Les confondre a déjà produit « 6264,00 % » au
  // lieu de 62,64 % (étape 7). On ne multiplie jamais par cent ailleurs.
  // ==========================================================================

  const fNombre = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const fQuantite = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  });
  const fEntier = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

  function euros(n) {
    return n === null || n === undefined ? "–" : fNombre.format(n) + " €";
  }

  function eurosSignes(n) {
    if (n === null || n === undefined) return "–";
    return (n > 0 ? "+" : n < 0 ? "−" : "") + fNombre.format(Math.abs(n)) + " €";
  }

  /** Reçoit un TAUX (0,6264). Pour le TRI, le TWRR, une variation, un poids. */
  function tauxEnPourCent(t, avecSigne) {
    if (t === null || t === undefined || !isFinite(t)) return "–";
    const signe = avecSigne === false ? "" : t > 0 ? "+" : t < 0 ? "−" : "";
    return signe + fNombre.format(Math.abs(t) * 100) + " %";
  }

  /** Reçoit un POUR CENT déjà calculé (62,64). Pour les répartitions. */
  function pourCent(p) {
    return p === null || p === undefined ? "–" : fNombre.format(p) + " %";
  }

  function quantite(n) {
    return n === null || n === undefined ? "–" : fQuantite.format(n);
  }

  /** Un cours, dans la devise de sa place. Jamais converti (D-51). */
  function cours(n) {
    return n === null || n === undefined ? "–" : fNombre.format(n) + " €";
  }

  function classe(n) {
    return n > 0 ? "gain" : n < 0 ? "perte" : "";
  }

  function dateCourte(iso) {
    if (!iso) return "–";
    const m = iso.split("-");
    return m[2] + "/" + m[1] + "/" + m[0];
  }

  function nombreDeJours(a, b) {
    return Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  }

  function dureeEnClair(j) {
    if (j === null) return "–";
    if (j < 31) return j + " jours";
    const mois = Math.round(j / 30.44);
    if (mois < 24) return mois + " mois";
    const annees = Math.floor(j / 365);
    const reste = Math.round((j - annees * 365) / 30.44);
    return annees + " an" + (annees > 1 ? "s" : "") + (reste ? " et " + reste + " mois" : "");
  }

  function el(balise, attributs, enfants) {
    const noeud = document.createElement(balise);
    for (const cle in attributs || {}) {
      const valeur = attributs[cle];
      if (valeur === null || valeur === undefined || valeur === false) continue;
      if (cle === "class") noeud.className = valeur;
      else if (cle === "html") noeud.innerHTML = valeur;
      else if (cle === "texte") noeud.textContent = valeur;
      else noeud.setAttribute(cle, valeur);
    }
    for (const enfant of [].concat(enfants || [])) {
      if (enfant === null || enfant === undefined) continue;
      noeud.append(enfant);
    }
    return noeud;
  }

  const NS = "http://www.w3.org/2000/svg";

  function svgEl(balise, attributs, enfants) {
    const noeud = document.createElementNS(NS, balise);
    for (const cle in attributs || {}) {
      if (attributs[cle] === null || attributs[cle] === undefined) continue;
      noeud.setAttribute(cle, String(attributs[cle]));
    }
    for (const enfant of [].concat(enfants || [])) {
      if (enfant === null || enfant === undefined) continue;
      noeud.append(enfant);
    }
    return noeud;
  }

  // ==========================================================================
  // 2. LES DRAPEAUX ET LES ICÔNES
  // Dessinés en SVG, dans le dépôt : les drapeaux en emoji ne s'affichent pas sous
  // Windows — le système rend les deux lettres du code au lieu du drapeau — et une
  // image distante est interdite (D-31).
  // Ce sont des drapeaux SIMPLIFIÉS : ils servent à repérer une ligne d'un coup
  // d'œil, pas à représenter un pays fidèlement.
  // ==========================================================================

  const DRAPEAUX = {
    US: [["#b22234", 0, 0, 20, 14], ["#ffffff", 0, 2, 20, 2], ["#ffffff", 0, 6, 20, 2],
         ["#ffffff", 0, 10, 20, 2], ["#3c3b6e", 0, 0, 9, 8]],
    FR: [["#002395", 0, 0, 6.67, 14], ["#ffffff", 6.67, 0, 6.66, 14],
         ["#ed2939", 13.33, 0, 6.67, 14]],
    DE: [["#000000", 0, 0, 20, 4.67], ["#dd0000", 0, 4.67, 20, 4.66],
         ["#ffce00", 0, 9.33, 20, 4.67]],
    NL: [["#ae1c28", 0, 0, 20, 4.67], ["#ffffff", 0, 4.67, 20, 4.66],
         ["#21468b", 0, 9.33, 20, 4.67]],
    JP: [["#ffffff", 0, 0, 20, 14]],
    GB: [["#012169", 0, 0, 20, 14], ["#ffffff", 0, 5, 20, 4], ["#ffffff", 8, 0, 4, 14],
         ["#c8102e", 0, 6, 20, 2], ["#c8102e", 9, 0, 2, 14]],
    CH: [["#d52b1e", 0, 0, 20, 14], ["#ffffff", 8.2, 3, 3.6, 8], ["#ffffff", 6, 5.2, 8, 3.6]],
    CA: [["#ff0000", 0, 0, 5, 14], ["#ffffff", 5, 0, 10, 14], ["#ff0000", 15, 0, 5, 14],
         ["#ff0000", 9, 4.5, 2, 5]],
    SE: [["#006aa7", 0, 0, 20, 14], ["#fecc00", 0, 5.5, 20, 3], ["#fecc00", 6, 0, 3, 14]],
    AU: [["#00008b", 0, 0, 20, 14], ["#ffffff", 0, 0, 8.6, 6.6],
         ["#00008b", 0.9, 0.9, 6.8, 4.8], ["#ffffff", 13.4, 8.4, 2, 2]],
    TW: [["#fe0000", 0, 0, 20, 14], ["#000095", 0, 0, 10, 7],
         ["#ffffff", 4, 2.4, 2.2, 2.2]],
  };

  /** Un drapeau simplifié, ou un globe quand la ligne n'est pas un pays. */
  function drapeau(code) {
    if (!code || !DRAPEAUX[code]) {
      return svgEl("svg", { class: "fanion", viewBox: "0 0 20 14", "aria-hidden": "true" }, [
        svgEl("circle", {
          cx: 10, cy: 7, r: 5.6, fill: "none",
          stroke: COULEURS.encreTresDouce, "stroke-width": 1.2,
        }),
        svgEl("path", {
          d: "M4.4 7h11.2M10 1.4c2.5 2.7 2.5 8.5 0 11.2M10 1.4c-2.5 2.7-2.5 8.5 0 11.2",
          fill: "none", stroke: COULEURS.encreTresDouce, "stroke-width": 1,
        }),
      ]);
    }
    const parties = DRAPEAUX[code].map(function (r) {
      return svgEl("rect", { fill: r[0], x: r[1], y: r[2], width: r[3], height: r[4] });
    });
    if (code === "JP") parties.push(svgEl("circle", { cx: 10, cy: 7, r: 4, fill: "#bc002d" }));
    parties.push(
      svgEl("rect", {
        x: 0.3, y: 0.3, width: 19.4, height: 13.4, fill: "none",
        stroke: "rgba(44,39,34,.3)", "stroke-width": 0.6,
      })
    );
    return svgEl("svg", { class: "fanion", viewBox: "0 0 20 14", "aria-hidden": "true" }, parties);
  }

  // Onze secteurs et quatre classes d'actifs : un pictogramme au trait par ligne.
  const ICONES = {
    technologie: "M5 5h10v8H5zM8 16h4M9.5 13v3M7.5 8h5M7.5 10.5h3.5",
    finance: "M3 8l7-4 7 4M5 8.5v6.5h10V8.5M8 15v-3.5h4V15",
    sante: "M10 4.5v11M4.5 10h11",
    cyclique: "M4 6h11l-1.2 6H6.2zM7.2 16a1 1 0 100-2 1 1 0 000 2M12.8 16a1 1 0 100-2 1 1 0 000 2",
    industrie: "M3.5 15.5V9l3.5 2.2V9l3.5 2.2V6.2l5.5 2.8v6.5zM3.5 15.5h12.5",
    communication: "M10 13.5V7M6.8 9.6a4.6 4.6 0 016.4 0M4.4 12a8 8 0 0111.2 0M9 16h2",
    defensive: "M6.2 7.2h7.6l.9 8.3H5.3zM8.2 7.2V5.4a1.8 1.8 0 013.6 0v1.8",
    energie: "M10 3.5c2.8 3.8 4.2 5.7 4.2 7.6a4.2 4.2 0 01-8.4 0c0-1.9 1.4-3.8 4.2-7.6z",
    collectivites: "M11 3.5L5.5 11H9l-1 5.5L14.5 9H11z",
    immobilier: "M3.5 9.2L10 4.5l6.5 4.7M5.2 9.5v6h9.6v-6M8.6 15.5v-3.6h2.8v3.6",
    materiaux: "M10 3.5l6 3.4v6.8l-6 3.4-6-3.4V6.9zM10 3.5v13M4 6.9l6 3.4 6-3.4",
    actions: "M3.5 14l4-5 3 3 4-6 2.5 4M3.5 16h13",
    obligations: "M4.5 5h8.5l3 3v7.5H4.5zM13 5v3.2h3M7.5 11h5M7.5 13.2h3.5",
    matieres: "M10 4l5.5 3.2v6.4L10 16.8 4.5 13.6V7.2zM10 4v12.8",
    numeriques: "M10 3.5l6 3.4v6.8L10 17l-6-3.3V6.9zM7 8.6l3 1.7 3-1.7M10 10.3v4.2",
    // Une zone n'a pas de drapeau : toutes portent le meme reperage.
    zone: "M10 3.2a6.8 6.8 0 100 13.6 6.8 6.8 0 000-13.6M3.4 10h13.2M10 3.2c2.7 3 2.7 10.6 0 13.6M10 3.2c-2.7 3-2.7 10.6 0 13.6",
  };

  function icone(nom) {
    const chemin = ICONES[nom];
    return svgEl("svg", { class: "picto", viewBox: "0 0 20 20", "aria-hidden": "true" }, [
      chemin
        ? svgEl("path", {
            d: chemin, fill: "none", stroke: "currentColor", "stroke-width": 1.4,
            "stroke-linecap": "round", "stroke-linejoin": "round",
          })
        : svgEl("circle", {
            cx: 10, cy: 10, r: 5.6, fill: "none", stroke: "currentColor", "stroke-width": 1.4,
          }),
    ]);
  }

  // ==========================================================================
  // 3. LE VOCABULAIRE D'ÉCRAN
  // Chaque explication tient dans un bouton « ? », jamais dans le corps du texte.
  // Voir docs/conception-interface.md §2.
  // ==========================================================================

  const AIDES = {
    gain: {
      titre: "Le gain",
      texte:
        "Ce que vos actifs ont rapporté sur la période : <b>leur valeur d'aujourd'hui, moins leur valeur au départ, plus tout ce qui est entré et sorti entre-temps</b>. Les frais et les taxes n'y sont pas : ils sont traités dans l'onglet « Frais et taxes ». Le calcul complet est dans l'onglet « Détail des calculs ».",
    },
    tri: {
      titre: "TRI — le rendement de votre argent",
      texte:
        "Le taux annuel qui, appliqué à chacun de vos versements <b>à sa date</b>, aboutirait à la valeur actuelle. Il récompense le bon moment : verser avant une hausse le fait monter. C'est le rendement de votre argent, pas celui de vos choix d'actifs.",
    },
    twrr: {
      titre: "TWRR — le rendement de la stratégie",
      texte:
        "Le même calcul, mais <b>en neutralisant les dates de vos versements</b>. C'est ce qu'aurait gagné un euro resté investi du début à la fin : le rendement de vos choix d'actifs, comparable à celui d'un indice.",
    },
    peuSignificatif: {
      titre: "Pourquoi ce taux est peu fiable",
      texte:
        "Sur moins d'un an, un rendement <b>annualisé</b> s'emballe : quelques semaines de hausse, ramenées à l'année, donnent un pourcentage énorme qui ne décrit rien de durable. Le gain en euros, lui, reste lisible dès le premier jour.",
    },
    valeur: {
      titre: "La valeur des actifs",
      texte:
        "La quantité détenue multipliée par le <b>dernier cours de clôture connu</b>, actif par actif. Les cours sont bruts : jamais retraités des dividendes. Aucun prix de séance en cours.",
    },
    capital: {
      titre: "Le capital net investi",
      texte:
        "Ce que vous avez <b>réellement placé</b> : vos achats, moins les frais et taxes prélevés dessus. Si vous versez 201 € avec 1 € de frais, 200 € entrent. À chaque vente, il diminue au prorata de la part vendue.",
    },
    partiel: {
      titre: "Pourquoi « partiel »",
      texte:
        "Ce total ne porte que sur les actifs dont nous connaissons le cours. Ceux qui manquent sont <b>nommés</b>, jamais comptés pour zéro : un portefeuille dont une ligne n'a pas de prix n'est pas un portefeuille plus petit.",
    },
    variation: {
      titre: "La variation d'un actif",
      texte:
        "La performance de <b>l'actif lui-même</b> sur la période, indépendamment de vos versements. Un actif acheté en cours de période est marqué « depuis l'achat » : sa variation ne commence pas avant qu'il existe dans votre portefeuille.",
    },
    synthetique: {
      titre: "ETF synthétique",
      texte:
        "Ce fonds <b>ne détient pas</b> les titres de son indice : il reproduit sa performance par un contrat d'échange. Nous affichons donc la composition de <b>l'indice suivi</b>, c'est-à-dire ce à quoi votre argent est réellement exposé. Si vous ouvrez la fiche de l'émetteur, vous y verrez une liste de titres très différente — souvent des sociétés européennes pour un fonds mondial.",
    },
    nonCouvert: {
      titre: "Non couvert",
      texte:
        "Nous n'avons pas la composition de cet actif : la source ne publie rien pour lui, ou ce qu'elle publie n'a pas passé nos contrôles. Son montant est affiché <b>à part et à sa vraie taille</b>, jamais réparti au hasard sur les autres postes.",
    },
    nonAttribue: {
      titre: "Non attribué",
      texte:
        "La part d'un fonds que sa propre documentation n'attribue à aucun pays ni secteur : liquidités, produits dérivés, lignes non classées. <b>Aucun fonds ne somme exactement à 100 %.</b>",
    },
    horsActions: {
      titre: "Hors actions",
      texte:
        "Cette part n'est pas investie en actions. Elle compte dans la répartition par classe d'actifs, mais <b>pas</b> dans les pays ni les secteurs, où ces notions n'ont pas le même sens. Elle est détaillée classe par classe, pour ne pas faire passer de l'or pour de la dette.",
    },
    numeriques: {
      titre: "Actifs numériques",
      texte:
        "Une crypto n'a <b>ni pays ni secteur</b> : ce n'est pas un oubli de notre part. Elle compte dans la répartition par classe d'actifs, et nulle part ailleurs.",
    },
    regleDePays: {
      titre: "Deux règles de pays cohabitent",
      texte:
        "« De quel pays est cette société ? » a plusieurs réponses justes. Pour un fonds, nous retenons le pays où la société <b>exerce son activité</b> ; pour une action que vous détenez en direct, son <b>siège social</b>. C'est pourquoi la règle est indiquée sur chaque ligne. Un émetteur écrit lui-même que son exposition géographique se rapporte « principalement » au domicile de l'émetteur, « mais, dans certains cas », au lieu de son activité.",
    },
    secteurs: {
      titre: "Secteurs Morningstar",
      texte:
        "Les secteurs suivent la nomenclature <b>Morningstar</b>, en 11 postes. Il en existe d'autres, qui ne découpent pas au même endroit : elles ne s'additionnent pas, donc nous n'en mélangeons jamais deux dans un même graphique.",
    },
    zones: {
      titre: "Les zones",
      texte:
        "Le regroupement des pays en zones est une <b>convention</b>, pas une donnée : la liste est un fichier daté et sourcé, que vous pouvez corriger. Il n'existe aucune norme officielle du « développé » et de l'« émergent », et les deux grands fournisseurs sont en désaccord sur plusieurs pays.",
    },
    pasCent: {
      titre: "Pourquoi le total ne fait pas 100 %",
      texte:
        "C'est <b>voulu</b>. Ce qui n'a pas pu être attribué reste visible, à sa vraie taille. Ramener le graphique à 100 % ferait disparaître exactement l'information qui manque — et c'est celle-là qu'il faut voir.",
    },
    arrete: {
      titre: "Arrêté au",
      texte:
        "Les fonds ne publient pas leur composition en temps réel : chacun l'arrête à une date, et ces dates <b>diffèrent d'un fonds à l'autre</b>. La fourchette indiquée est celle de vos fonds.",
    },
    estime: {
      titre: "Estimé",
      texte:
        "Ce montant n'a <b>pas été payé</b> : il est calculé à partir d'un taux publié, avec sa date et sa source. Il ne se mélange jamais aux frais réellement prélevés sur votre compte.",
    },
    spread: {
      titre: "Le spread",
      texte:
        "L'écart entre le prix d'achat et le prix de vente d'un actif à un instant donné. Vous le payez <b>deux fois</b> : à l'entrée et à la sortie, sans qu'il apparaisse jamais sur un relevé. Le taux affiché est la moyenne de vos actifs, pondérée par ce qu'ils pèsent — c'est lui qui se compare à un taux publié, là où le montant en euros dépend de la taille de votre portefeuille.",
    },
    ter: {
      titre: "Les frais courants (TER)",
      texte:
        "Les frais annuels d'un fonds, prélevés en continu sur sa valeur. Vous ne les voyez jamais passer : ils sont déjà dans le cours. Le montant affiché est une <b>estimation à un an</b>, sur la valeur d'aujourd'hui.",
    },
    valeurReelle: {
      titre: "La valeur réelle",
      texte:
        "Ce que vous récupéreriez <b>si vous vendiez tout aujourd'hui</b> : la valeur des actifs, moins les frais de vente, le spread de sortie et l'impôt estimé selon la poche. C'est une estimation, pas une déclaration.",
    },
    baseImposable: {
      titre: "La base imposable",
      texte:
        "Les plus-values <b>latentes</b> seulement, compensées entre elles, avec un plancher à zéro. Les plus-values déjà réalisées cette année et les dividendes déjà reçus n'y sont pas. Les frais et le spread de sortie viennent en déduction.",
    },
    minoree: {
      titre: "Estimation minorée",
      texte:
        "Volontairement <b>prudente</b> : une partie de l'impôt ne peut pas être calculée depuis les seuls titres, elle est donc laissée de côté. Le montant réellement dû serait plus élevé, donc la valeur réelle un peu plus basse.",
    },
    coutsPreleves: {
      titre: "Ce qui a déjà été prélevé",
      texte:
        "Ces montants sont <b>réels</b> : ils ont été retirés de votre compte, et ils figurent sur vos relevés. Les deux blocs suivants, eux, sont des <b>estimations</b> — c'est ce qui sépare ce niveau des autres.",
    },
    retenueDividendes: {
      titre: "Pourquoi la retenue sur dividendes est ici",
      texte:
        "Elle n'est pas prélevée à l'achat : elle l'est <b>à chaque versement de dividende</b>, donc pendant que vous détenez l'actif. Elle figure dans ce bloc parce qu'il rassemble tout ce qui a <b>déjà été payé</b>, par opposition aux deux suivants qui estiment ce qui court et ce qui resterait. Si vous préférez la voir au moment où elle tombe, elle a sa place dans le bloc « pendant la détention » : dites-le.",
    },
    contenuDeclare: {
      titre: "Contenu déclaré",
      texte:
        "Vous avez indiqué vous-même de quoi cet actif est fait. Il compte à 100 % dans sa classe, et il <b>sort</b> des pays et des secteurs — là où ces notions ne veulent rien dire pour lui.",
    },
  };

  let compteurIds = 0;
  let bulleOuverte = null;

  /* Le bouton « ? » et sa bulle.
   *
   * La bulle est posée en `position: fixed`, à la racine du document, avec des
   * coordonnées calculées depuis le bouton puis RAMENÉES DANS L'ÉCRAN. C'est la
   * correction d'un défaut signalé par le propriétaire : en position absolue dans un
   * bloc, la moitié du texte sortait de la page, et une bulle ancrée au bord d'une
   * tuile s'affichait loin de son bouton. */
  function aide(cle) {
    const a = AIDES[cle];
    if (!a) return null;
    const id = "bulle-" + ++compteurIds;
    const bouton = el("button", {
      class: "aide",
      type: "button",
      "aria-expanded": "false",
      "aria-controls": id,
      "aria-label": "Qu'est-ce que « " + a.titre + " » ?",
      texte: "?",
    });
    const bulle = el("div", { class: "bulle", id: id, role: "note" }, [
      el("b", { class: "bulle__titre", texte: a.titre }),
      el("span", { html: a.texte }),
    ]);
    bulle.hidden = true;

    bouton.addEventListener("click", function (evenement) {
      evenement.stopPropagation();
      const ouvert = bouton.getAttribute("aria-expanded") === "true";
      fermerLaBulle();
      if (ouvert) return;
      document.body.append(bulle);
      bulle.hidden = false;
      bouton.setAttribute("aria-expanded", "true");
      bulleOuverte = { bouton: bouton, bulle: bulle };
      placerLaBulle(bouton, bulle);
    });
    return [bouton, bulle];
  }

  function placerLaBulle(bouton, bulle) {
    const marge = 10;
    const cadreBouton = bouton.getBoundingClientRect();
    const cadreBulle = bulle.getBoundingClientRect();
    let gauche = cadreBouton.left + cadreBouton.width / 2 - cadreBulle.width / 2;
    gauche = Math.max(marge, Math.min(gauche, window.innerWidth - cadreBulle.width - marge));
    let haut = cadreBouton.bottom + 7;
    if (haut + cadreBulle.height > window.innerHeight - marge) {
      // Pas de place en dessous : la bulle passe au-dessus du bouton.
      haut = Math.max(marge, cadreBouton.top - cadreBulle.height - 7);
    }
    bulle.style.left = Math.round(gauche) + "px";
    bulle.style.top = Math.round(haut) + "px";
  }

  function fermerLaBulle() {
    if (!bulleOuverte) return;
    bulleOuverte.bouton.setAttribute("aria-expanded", "false");
    bulleOuverte.bulle.hidden = true;
    if (bulleOuverte.bulle.parentNode === document.body) {
      document.body.removeChild(bulleOuverte.bulle);
    }
    bulleOuverte = null;
  }

  document.addEventListener("click", fermerLaBulle);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermerLaBulle();
  });
  window.addEventListener("resize", fermerLaBulle);

  /** Un titre de bloc, suivi IMMÉDIATEMENT de son « ? » : le bouton reste collé au mot
   *  qu'il explique, et non repoussé au bord du bloc. */
  function entete(titre, cleAide, note) {
    const secours = aide(cleAide);
    return el("div", { class: "bloc__entete" }, [
      el("h2", { class: "bloc__titre", texte: titre }),
      secours ? secours[0] : null,
      note ? el("span", { class: "bloc__note", texte: note }) : null,
    ]);
  }

  // ==========================================================================
  // 4. LES CALCULS
  // Les mêmes formules que le glossaire, pour que la maquette reste cohérente quand
  // on change de période ou de poche — pas pour remplacer le moteur, qui les fait
  // sur les opérations réelles.
  // ==========================================================================

  /** Le gain : valeur finale − valeur initiale + somme des flux (glossaire §4). */
  function calculerGain(valeurDebut, valeurFin, flux) {
    let somme = 0;
    for (const f of flux) somme += f.montant;
    return Math.round((valeurFin - valeurDebut + somme) * 100) / 100;
  }

  /** Le TRI, par dichotomie sur la valeur actuelle nette, comme le moteur. */
  function calculerTri(dateDebut, valeurDebut, dateFin, valeurFin, flux) {
    const lignes = [];
    if (valeurDebut > 0) lignes.push({ date: dateDebut, montant: -valeurDebut });
    for (const f of flux) lignes.push({ date: f.date, montant: f.montant });
    lignes.push({ date: dateFin, montant: valeurFin });
    if (lignes.length < 2) return null;

    const van = function (taux) {
      let total = 0;
      for (const l of lignes) {
        total += l.montant / Math.pow(1 + taux, nombreDeJours(dateDebut, l.date) / 365);
      }
      return total;
    };

    let bas = -0.9899;
    let haut = 9.99;
    const vBas = van(bas);
    const vHaut = van(haut);
    if (!isFinite(vBas) || !isFinite(vHaut) || vBas * vHaut > 0) return null;
    for (let i = 0; i < 120; i++) {
      const milieu = (bas + haut) / 2;
      if (van(milieu) > 0) bas = milieu;
      else haut = milieu;
    }
    return (bas + haut) / 2;
  }

  /** Les sous-périodes du TWRR, bornées par les jours de flux.
   *
   * Une sous-période commence JUSTE APRÈS un flux et s'arrête JUSTE AVANT le suivant :
   * elle ne contient donc aucun flux, et son rendement est un simple rapport de valeurs.
   * C'est la convention qui rend le calcul refaisable à la main — et celle qui a coûté
   * deux essais, parce que compter les flux à la fin d'une sous-période donnait un TWRR
   * de −126 %.
   *
   * Le TWRR est le produit de ces rendements, moins un : l'écran montre les deux, et ils
   * ne peuvent donc pas se contredire.
   */
  function calculerSousPeriodes(points, flux) {
    if (points.length < 2) return [];

    const indexParDate = {};
    points.forEach(function (p, i) {
      indexParDate[p.date] = i;
    });

    const premierValorise = points.findIndex(function (p) {
      return p.valeur > 0;
    });
    if (premierValorise === -1) return [];
    const debut = points[premierValorise].date;
    const fin = points[points.length - 1].date;

    const bornes = [debut];
    for (const f of flux) {
      if (f.date > debut && f.date < fin && bornes[bornes.length - 1] !== f.date) {
        bornes.push(f.date);
      }
    }
    bornes.push(fin);

    const sousPeriodes = [];
    for (let i = 0; i < bornes.length - 1; i++) {
      const du = bornes[i];
      const au = bornes[i + 1];
      const iDu = indexParDate[du];
      const iAu = indexParDate[au];
      if (iDu === undefined || iAu === undefined) continue;
      // Le flux qui OUVRE la sous-période est déjà dans la valeur de départ ; celui qui
      // la ferme ne l'est pas encore, puisqu'on s'arrête la veille.
      let entrees = 0;
      for (const f of flux) if (f.date === du) entrees += -f.montant;
      const valeurDebut = points[iDu].valeur;
      const valeurFin = au === fin ? points[points.length - 1].valeur : points[iAu - 1].valeur;
      if (valeurDebut <= 0 || valeurFin === undefined) continue;
      sousPeriodes.push({
        du: du,
        au: au,
        valeurDebut: valeurDebut,
        entrees: Math.round(entrees * 100) / 100,
        valeurFin: valeurFin,
        rendement: valeurFin / valeurDebut - 1,
      });
    }
    return sousPeriodes;
  }

  function chainer(sousPeriodes) {
    if (!sousPeriodes.length) return null;
    let produit = 1;
    for (const s of sousPeriodes) produit *= 1 + s.rendement;
    return produit - 1;
  }

  function annualiser(taux, jours) {
    if (taux === null || jours <= 0 || taux <= -1) return null;
    return Math.pow(1 + taux, 365 / jours) - 1;
  }

  // ==========================================================================
  // 5. L'ÉTAT, ET CE QU'ON EN DÉDUIT
  // ==========================================================================

  const PERIODES = [
    { cle: "1m", nom: "1 mois", jours: 31 },
    { cle: "6m", nom: "6 mois", jours: 183 },
    { cle: "1a", nom: "1 an", jours: 365 },
    { cle: "5a", nom: "5 ans", jours: 1826 },
    { cle: "tout", nom: "Tout", jours: null },
  ];

  const etat = {
    onglet: "synthese",
    periode: "tout",
    poches: new Set(POCHES),
    jeu: "complet",
    tri: { colonne: "valeur", sens: -1 },
    filtreType: "tous",
    rubrique: "classes",
    pageActifs: 0,
  };

  const JEUX = {
    complet: {
      nom: "Complet",
      aide: "Onze lignes : ETF actions, ETF obligataire, or, deux actions en direct, crypto, un fonds non couvert, une position sans cours.",
      positions: function () {
        return D.positions;
      },
    },
    uneLigne: {
      nom: "Une seule ligne",
      aide: "Un seul ETF. Sur une courte période, le TRI et le TWRR existent mais ne veulent rien dire — et l'écran doit le dire.",
      positions: function () {
        return D.positions.filter(function (p) {
          return p.code === "XX0000000012";
        });
      },
    },
    sansPea: {
      nom: "Sans PEA",
      aide: "Un CTO et de la crypto seulement. L'écran ne doit pas laisser un trou là où le PEA serait.",
      positions: function () {
        return D.positions.filter(function (p) {
          return p.poche !== "PEA";
        });
      },
    },
    aucunCours: {
      nom: "Aucun cours",
      aide: "La source de cours est muette sur tout le portefeuille. C'est le cas qui casse les tableaux de bord : il ne doit afficher ni zéro, ni total vide.",
      positions: function () {
        return D.positions.map(function (p) {
          return Object.assign({}, p, {
            cours: null,
            valeur: null,
            plusValueLatente: null,
            terMontant: null,
            motifSansCours:
              "aucun cours utilisable au 25/09/2026 : la source n'a répondu pour aucun actif",
          });
        });
      },
    },
  };

  /** Tout ce que l'écran affiche, recalculé selon la période et les poches. */
  function contexte() {
    const toutes = JEUX[etat.jeu].positions();
    const pochesPresentes = POCHES.filter(function (poche) {
      return toutes.some(function (p) {
        return p.poche === poche;
      });
    });
    const actives = pochesPresentes.filter(function (p) {
      return etat.poches.has(p);
    });
    const positions = toutes.filter(function (p) {
      return actives.includes(p.poche);
    });

    // Les positions valorisées commandent la performance : une ligne sans cours en sort,
    // avec ses flux, et le total est marqué partiel (D-53).
    const valorisees = positions.filter(function (p) {
      return p.valeur !== null;
    });
    const codesValorises = valorisees.map(function (p) {
      return p.code;
    });
    const nonValorisees = positions
      .filter(function (p) {
        return p.valeur === null;
      })
      .map(function (p) {
        return p.nom;
      });

    let courbe = codesValorises.length ? D.construireCourbe(codesValorises) : [];

    const periode = PERIODES.find(function (p) {
      return p.cle === etat.periode;
    });
    if (courbe.length) {
      if (periode.jours === null) {
        const premier = courbe.findIndex(function (p) {
          return p.valeur > 0;
        });
        courbe = courbe.slice(Math.max(0, premier - 1));
      } else {
        const finMs = Date.parse(courbe[courbe.length - 1].date);
        const seuil = new Date(finMs - periode.jours * 86400000).toISOString().slice(0, 10);
        const coupe = courbe.filter(function (p) {
          return p.date >= seuil;
        });
        courbe = coupe.length >= 2 ? coupe : courbe.slice(-2);
      }
    }

    /* La borne de gauche est INCLUSIVE quand la période commence à une valeur nulle, et
     * STRICTE sinon. C'est la seule convention qui donne un gain juste dans les deux
     * cas : depuis l'origine, les tout premiers achats font partie de la période ; au
     * milieu de la vie du portefeuille, ils sont déjà dans la valeur de départ. */
    const debut = courbe.length ? courbe[0].date : null;
    const fin = courbe.length ? courbe[courbe.length - 1].date : null;
    const borneInclusive = courbe.length > 0 && courbe[0].valeur === 0;
    const flux = D.flux.filter(function (f) {
      if (!codesValorises.includes(f.actif)) return false;
      if (debut === null) return false;
      return (borneInclusive ? f.date >= debut : f.date > debut) && f.date <= fin;
    });

    let valeur = 0;
    let capital = 0;
    let latente = 0;
    for (const p of positions) {
      capital += p.capitalNetInvesti;
      if (p.valeur !== null) {
        valeur += p.valeur;
        latente += p.plusValueLatente;
      }
    }
    const rienDeValorise = positions.length > 0 && valorisees.length === 0;

    let gain = null;
    let tri = null;
    let twrr = null;
    let twrrAnnualise = null;
    let sousPeriodes = [];
    let jours = null;
    if (courbe.length >= 2) {
      jours = nombreDeJours(debut, fin);
      gain = calculerGain(courbe[0].valeur, courbe[courbe.length - 1].valeur, flux);
      tri = calculerTri(debut, courbe[0].valeur, fin, courbe[courbe.length - 1].valeur, flux);
      sousPeriodes = calculerSousPeriodes(courbe, flux);
      twrr = chainer(sousPeriodes);
      twrrAnnualise = annualiser(twrr, jours);
    }

    return {
      positions: positions,
      valorisees: valorisees,
      courbe: courbe,
      flux: flux,
      debut: debut,
      fin: fin,
      jours: jours,
      pochesPresentes: pochesPresentes,
      pochesActives: actives,
      valeur: rienDeValorise ? null : Math.round(valeur * 100) / 100,
      capital: Math.round(capital * 100) / 100,
      latente: rienDeValorise ? null : Math.round(latente * 100) / 100,
      gain: gain,
      tri: tri,
      twrr: twrr,
      twrrAnnualise: twrrAnnualise,
      sousPeriodes: sousPeriodes,
      partiel: nonValorisees.length > 0,
      nonValorisees: nonValorisees,
      peuSignificatif: jours !== null && jours < 365,
      arreteAu: D.dateArrete,
      source: D.synthese.sourceDesCours,
      toutesPoches: actives.length === pochesPresentes.length,
      motif: rienDeValorise
        ? "aucune position n'a de cours : la valeur ne peut pas être calculée"
        : null,
    };
  }

  // ==========================================================================
  // 6. LES BRIQUES
  // ==========================================================================

  function bloc(titre, note, contenu, classes, cleAide) {
    return el("section", { class: "bloc" + (classes ? " " + classes : "") }, [
      titre ? entete(titre, cleAide, note) : null,
      contenu,
    ]);
  }

  function tuile(etiquette, valeurTexte, options) {
    const o = options || {};
    const secours = aide(o.aide);
    return el("div", { class: "tuile tuile--" + (o.ton || "neutre") }, [
      el("div", { class: "tuile__haut" }, [
        el("span", { class: "etiquette", texte: etiquette }),
        secours ? secours[0] : null,
      ]),
      el("span", {
        class: "tuile__valeur" + (o.petit ? " tuile__valeur--petit" : "") + " " + (o.classe || ""),
        texte: valeurTexte,
      }),
      el("span", { class: "tuile__pied" }, o.pied || null),
    ]);
  }

  function piedAvecMot(mot, texte, variante) {
    return [
      el("span", { class: "mot" + (variante ? " mot--" + variante : ""), texte: mot }),
      texte ? document.createTextNode(" " + texte) : null,
    ];
  }

  // --- Le graphique, avec le survol ----------------------------------------

  function graphique(points, hauteurVoulue) {
    const cadre = el("div", { class: "cadre-graphique" });

    if (points.length < 2) {
      cadre.append(
        el("p", {
          class: "vide",
          texte:
            "Pas de courbe : aucun cours connu sur la période. Rien n'est tracé, plutôt qu'une ligne à zéro.",
        })
      );
      return cadre;
    }

    const L = 1000;
    const H = hauteurVoulue || 250;
    const mg = { g: 62, d: 14, h: 12, b: 24 };
    const larg = L - mg.g - mg.d;
    const haut = H - mg.h - mg.b;

    let maxi = 0;
    for (const p of points) maxi = Math.max(maxi, p.valeur, p.investi);
    const pas = Math.pow(10, Math.floor(Math.log10(maxi || 1))) / 2;
    const plafond = Math.max(pas, Math.ceil((maxi * 1.06) / pas) * pas);

    const x = function (i) {
      return mg.g + (i / (points.length - 1)) * larg;
    };
    const y = function (v) {
      return mg.h + haut - (v / plafond) * haut;
    };

    const svg = svgEl("svg", {
      class: "graphique",
      viewBox: "0 0 " + L + " " + H,
      role: "img",
      "aria-label":
        "Évolution du capital brut et du capital net investi, du " +
        dateCourte(points[0].date) + " au " + dateCourte(points[points.length - 1].date) + ".",
    });

    // La grille est un trait PLEIN très pâle : en pointillé, elle se confondait avec la
    // courbe du capital net investi, qui est elle-même en pointillé.
    for (let i = 0; i <= 4; i++) {
      const v = (plafond / 4) * i;
      svg.append(svgEl("line", { class: "grille", x1: mg.g, x2: L - mg.d, y1: y(v), y2: y(v) }));
      const etiquette = svgEl("text", { x: mg.g - 8, y: y(v) + 3.5, "text-anchor": "end" });
      etiquette.textContent = fEntier.format(v) + " €";
      svg.append(etiquette);
    }

    const combien = 5;
    for (let k = 0; k < combien; k++) {
      const i = Math.round((k / (combien - 1)) * (points.length - 1));
      const t = svgEl("text", {
        x: x(i),
        y: H - 6,
        "text-anchor": k === 0 ? "start" : k === combien - 1 ? "end" : "middle",
      });
      t.textContent = dateCourte(points[i].date);
      svg.append(t);
    }

    let traceBrut = "";
    for (let i = 0; i < points.length; i++) {
      traceBrut += (i ? " L " : "M ") + x(i).toFixed(1) + " " + y(points[i].valeur).toFixed(1);
    }
    svg.append(
      svgEl("path", {
        class: "aire-brut",
        d:
          traceBrut + " L " + x(points.length - 1).toFixed(1) + " " + y(0) +
          " L " + x(0).toFixed(1) + " " + y(0) + " Z",
      })
    );

    // Le capital net investi monte en escalier : il ne bouge qu'aux opérations.
    let traceInvesti = "";
    for (let i = 0; i < points.length; i++) {
      const px = x(i).toFixed(1);
      if (i === 0) traceInvesti = "M " + px + " " + y(points[i].investi).toFixed(1);
      else {
        traceInvesti +=
          " L " + px + " " + y(points[i - 1].investi).toFixed(1) +
          " L " + px + " " + y(points[i].investi).toFixed(1);
      }
    }
    svg.append(svgEl("path", { class: "serie serie--investi", d: traceInvesti }));
    svg.append(svgEl("path", { class: "serie serie--brut", d: traceBrut }));

    const dernier = points[points.length - 1];
    svg.append(
      svgEl("circle", {
        cx: x(points.length - 1), cy: y(dernier.valeur), r: 3.5,
        fill: COULEURS.courbeBrut, stroke: COULEURS.surface, "stroke-width": 2,
      })
    );

    const viseur = svgEl("line", { class: "viseur", y1: mg.h, y2: mg.h + haut });
    const pointBrut = svgEl("circle", {
      r: 4, fill: COULEURS.courbeBrut, stroke: COULEURS.surface, "stroke-width": 2,
    });
    const pointInvesti = svgEl("circle", {
      r: 3.5, fill: COULEURS.courbeInvesti, stroke: COULEURS.surface, "stroke-width": 2,
    });
    const groupeSurvol = svgEl("g", {}, [viseur, pointBrut, pointInvesti]);
    groupeSurvol.style.display = "none";
    svg.append(groupeSurvol);

    const infobulle = el("div", { class: "infobulle" });
    infobulle.hidden = true;
    cadre.append(svg, infobulle);

    function montrer(evenement) {
      const boite = svg.getBoundingClientRect();
      const relatif = ((evenement.clientX - boite.left) / boite.width) * L;
      let i = Math.round(((relatif - mg.g) / larg) * (points.length - 1));
      i = Math.max(0, Math.min(points.length - 1, i));
      const p = points[i];

      groupeSurvol.style.display = "";
      viseur.setAttribute("x1", x(i));
      viseur.setAttribute("x2", x(i));
      pointBrut.setAttribute("cx", x(i));
      pointBrut.setAttribute("cy", y(p.valeur));
      pointInvesti.setAttribute("cx", x(i));
      pointInvesti.setAttribute("cy", y(p.investi));

      const ecart = Math.round((p.valeur - p.investi) * 100) / 100;
      infobulle.innerHTML = "";
      infobulle.append(
        el("b", { class: "infobulle__date", texte: dateCourte(p.date) }),
        el("span", { class: "infobulle__ligne" }, [
          el("i", { style: "border-top-color: var(--courbe-brut)" }),
          el("span", { texte: "Capital brut" }),
          el("b", { texte: euros(p.valeur) }),
        ]),
        el("span", { class: "infobulle__ligne" }, [
          el("i", { style: "border-top-color: var(--courbe-investi); border-top-style: dashed" }),
          el("span", { texte: "Capital net investi" }),
          el("b", { texte: euros(p.investi) }),
        ]),
        el("span", { class: "infobulle__ligne infobulle__ecart" }, [
          el("span", { texte: "Écart" }),
          el("b", { class: classe(ecart), texte: eurosSignes(ecart) }),
        ])
      );
      infobulle.hidden = false;
      const largeurBulle = infobulle.offsetWidth || 200;
      const gauche = Math.min(
        Math.max(0, (x(i) / L) * boite.width - largeurBulle / 2),
        Math.max(0, boite.width - largeurBulle)
      );
      infobulle.style.left = gauche + "px";
    }

    function cacher() {
      groupeSurvol.style.display = "none";
      infobulle.hidden = true;
    }

    svg.addEventListener("mousemove", montrer);
    svg.addEventListener("mouseleave", cacher);
    svg.addEventListener("touchmove", function (e) {
      if (e.touches.length) montrer(e.touches[0]);
    });
    svg.addEventListener("touchend", cacher);

    return cadre;
  }

  function legendeCourbe() {
    return el("ul", { class: "legende" }, [
      el("li", {}, [
        el("i", { style: "border-top-color: var(--courbe-brut)" }),
        document.createTextNode("Capital brut — ce que valent les actifs"),
      ]),
      el("li", {}, [
        el("i", { style: "border-top-color: var(--courbe-investi); border-top-style: dashed" }),
        document.createTextNode("Capital net investi — ce qui a été placé, net de frais"),
      ]),
    ]);
  }

  // --- L'anneau ------------------------------------------------------------

  /** Un anneau, dessine en ARCS EXPLICITES, un chemin par part.
   *
   * La version precedente empilait un seul cercle par part avec `stroke-dasharray` et
   * `stroke-dashoffset`. C'est la technique habituelle, mais elle est impossible a
   * verifier a l'oeil : rien ne dit qu'une part est au bon endroit ni a la bonne taille.
   * Ici chaque part est un arc de son angle de depart a son angle d'arrivee, et sa
   * couleur est ecrite en clair. On peut lire le code et savoir ce qui sera dessine.
   *
   * `parts` = [{libelle, montant, couleur, absent}]. Les parts « absent » sont hachurees :
   * ce qui manque se voit, sans se confondre avec un poste reel.
   *
   * AUCUN CHIFFRE N'EST ECRIT SUR L'ANNEAU. Un pourcentage pose dans une part doit
   * choisir sa couleur selon celle de la part, et il finit par etre peu lisible sur les
   * teintes intermediaires. Chaque anneau est donc accompagne — d'une legende sur la
   * synthese, du classement chiffre a cote sur la diversification — et l'anneau ne
   * porte que la forme.
   */
  function anneau(parts, taille, legendeAuCentre) {
    const total = parts.reduce(function (s, p) {
      return s + p.montant;
    }, 0);
    if (total <= 0) return null;

    const epaisseur = Math.round(taille * 0.15);
    const r = taille / 2 - epaisseur / 2 - 1;
    const centre = taille / 2;
    const ECART_DEGRES = 1.2; // le filet de papier entre deux parts

    const idHachures = "hachures-" + ++compteurIds;
    const motif = svgEl(
      "pattern",
      {
        id: idHachures,
        patternUnits: "userSpaceOnUse",
        width: 5,
        height: 5,
        patternTransform: "rotate(45)",
      },
      [
        svgEl("rect", { width: 5, height: 5, fill: COULEURS.papier }),
        svgEl("line", {
          x1: 0, y1: 0, x2: 0, y2: 5,
          stroke: COULEURS.absent, "stroke-width": 2.6,
        }),
      ]
    );

    const svg = svgEl(
      "svg",
      {
        viewBox: "0 0 " + taille + " " + taille,
        width: taille,
        height: taille,
        class: "anneau",
        "aria-hidden": "true",
      },
      [svgEl("defs", {}, [motif])]
    );

    /** Un point du cercle, l'angle etant compte depuis le haut, dans le sens horaire. */
    function point(angleDegres) {
      const rad = ((angleDegres - 90) * Math.PI) / 180;
      return [centre + r * Math.cos(rad), centre + r * Math.sin(rad)];
    }

    let angle = 0;
    for (const part of parts) {
      const ouverture = (part.montant / total) * 360;
      const couleur = part.absent ? "url(#" + idHachures + ")" : part.couleur;

      if (ouverture >= 359.9) {
        // Une part unique ne peut pas se dessiner comme un arc : c'est un cercle.
        svg.append(
          svgEl("circle", {
            cx: centre, cy: centre, r: r,
            fill: "none", stroke: couleur, "stroke-width": epaisseur,
          })
        );
      } else if (ouverture > ECART_DEGRES) {
        const debutArc = angle + ECART_DEGRES / 2;
        const finArc = angle + ouverture - ECART_DEGRES / 2;
        const [x1, y1] = point(debutArc);
        const [x2, y2] = point(finArc);
        svg.append(
          svgEl("path", {
            d:
              "M " + x1.toFixed(2) + " " + y1.toFixed(2) +
              " A " + r + " " + r + " 0 " +
              (finArc - debutArc > 180 ? 1 : 0) + " 1 " +
              x2.toFixed(2) + " " + y2.toFixed(2),
            fill: "none",
            stroke: couleur,
            "stroke-width": epaisseur,
          })
        );
      } else if (ouverture > 0) {
        // Une part minuscule reste visible : un trait, plutot que rien du tout.
        const [x1, y1] = point(angle);
        const [x2, y2] = point(angle + ouverture);
        svg.append(
          svgEl("path", {
            d: "M " + x1.toFixed(2) + " " + y1.toFixed(2) + " L " + x2.toFixed(2) + " " + y2.toFixed(2),
            fill: "none",
            stroke: part.absent ? COULEURS.absent : part.couleur,
            "stroke-width": epaisseur,
            "stroke-linecap": "butt",
          })
        );
      }
      angle += ouverture;
    }

    if (legendeAuCentre) {
      const t1 = svgEl("text", {
        x: centre, y: centre + 1, "text-anchor": "middle", class: "anneau__centre",
      });
      t1.textContent = legendeAuCentre;
      const t2 = svgEl("text", {
        x: centre, y: centre + 15, "text-anchor": "middle", class: "anneau__sous",
      });
      t2.textContent = "au total";
      svg.append(t1, t2);
    }
    return svg;
  }

  function listeDeParts(parts, total) {
    return el(
      "ul",
      { class: "liste-parts" },
      parts.map(function (p) {
        return el("li", {}, [
          el("span", {
            class: "puce" + (p.absent ? " puce--absent" : ""),
            style: p.absent ? null : "background:" + p.couleur,
          }),
          el("span", { class: "liste-parts__nom", texte: p.libelle }),
          el("span", { class: "nb", texte: euros(p.montant) }),
          el("span", { class: "part nb", texte: pourCent((p.montant / total) * 100) }),
        ]);
      })
    );
  }

  function blocPoches(c) {
    const parts = [];
    for (const poche of c.pochesActives) {
      let valeur = 0;
      for (const p of c.positions) {
        if (p.poche === poche && p.valeur !== null) valeur += p.valeur;
      }
      if (valeur > 0) {
        parts.push({
          libelle: poche,
          montant: Math.round(valeur * 100) / 100,
          couleur: COULEUR_POCHE[poche],
        });
      }
    }
    if (!parts.length) {
      return bloc(
        "Où est l'argent",
        null,
        el("p", { class: "vide", texte: "Aucune poche valorisée : il n'y a rien à répartir." })
      );
    }
    const total = parts.reduce(function (s, p) {
      return s + p.montant;
    }, 0);
    // Triees de la plus grosse a la plus petite : l'anneau part alors de midi avec la
    // part principale, et la legende se lit dans le meme ordre.
    const triees = parTaille(parts, "montant");
    // L'anneau en haut, au milieu, et les lignes en dessous.
    return bloc(
      "Où est l'argent que j'investis",
      null,
      el("div", { class: "anneau-bloc anneau-bloc--colonne" }, [
        anneau(triees, 156, fEntier.format(total) + " €"),
        listeDeParts(triees, total),
      ])
    );
  }

  // --- Les cartes d'actifs de la synthèse ----------------------------------

  const PAR_PAGE = 5;

  /** Les actifs, en cartes, triés par variation sur la période. C'est la demande du
   *  propriétaire : sur la synthèse on veut voir ce qui monte et ce qui descend, pas
   *  recopier le tableau de l'onglet « Les actifs ». */
  function cartesActifs(c) {
    const avecVariation = c.positions.map(function (p) {
      return {
        position: p,
        variation: p.valeur === null || !c.debut ? null : D.variationActif(p.code, c.debut, c.fin),
      };
    });
    avecVariation.sort(function (a, b) {
      if (!a.variation && !b.variation) return 0;
      if (!a.variation) return 1;
      if (!b.variation) return -1;
      return b.variation.taux - a.variation.taux;
    });

    const pages = Math.max(1, Math.ceil(avecVariation.length / PAR_PAGE));
    if (etat.pageActifs > pages - 1) etat.pageActifs = pages - 1;
    if (etat.pageActifs < 0) etat.pageActifs = 0;
    const visibles = avecVariation.slice(
      etat.pageActifs * PAR_PAGE,
      etat.pageActifs * PAR_PAGE + PAR_PAGE
    );

    const cartes = el(
      "div",
      { class: "cartes" },
      visibles.map(function (ligne) {
        const p = ligne.position;
        const v = ligne.variation;
        const taux = v ? v.taux : null;
        return el(
          "article",
          { class: "carte carte--" + (taux === null ? "neutre" : taux >= 0 ? "gain" : "perte") },
          [
            el("div", { class: "carte__haut" }, [
              el("span", { class: "jeton", texte: p.poche }),
              el("span", { class: "carte__type", texte: p.type }),
            ]),
            el("span", { class: "carte__nom", texte: p.nom, title: p.nom }),
            el("span", {
              class: "carte__taux nb " + (taux === null ? "" : classe(taux)),
              texte: taux === null ? "–" : tauxEnPourCent(taux),
            }),
            el("span", {
              class: "carte__precision",
              texte: v
                ? v.depuisLAchat
                  ? "depuis l'achat du " + dateCourte(v.depuis)
                  : "sur la période"
                : p.valeur === null
                ? "sans cours"
                : "non détenu sur la période",
            }),
            el("dl", { class: "carte__chiffres" }, [
              el("dt", { texte: "Quantité" }),
              el("dd", { class: "nb", texte: quantite(p.quantite) }),
              el("dt", { texte: "Valeur" }),
              el("dd", { class: "nb", texte: euros(p.valeur) }),
            ]),
          ]
        );
      })
    );

    const precedent = el("button", {
      class: "fleche", type: "button", "aria-label": "Cinq actifs précédents", texte: "‹",
    });
    const suivant = el("button", {
      class: "fleche", type: "button", "aria-label": "Cinq actifs suivants", texte: "›",
    });
    precedent.disabled = etat.pageActifs === 0;
    suivant.disabled = etat.pageActifs >= pages - 1;
    precedent.addEventListener("click", function () {
      etat.pageActifs--;
      dessiner();
    });
    suivant.addEventListener("click", function () {
      etat.pageActifs++;
      dessiner();
    });

    const secours = aide("variation");
    return el("section", { class: "bloc" }, [
      el("div", { class: "bloc__entete" }, [
        el("h2", { class: "bloc__titre", texte: "Vos actifs, du plus au moins performant" }),
        secours ? secours[0] : null,
        el("span", { class: "bloc__note" }, [
          document.createTextNode(
            avecVariation.length + " actifs · " + (etat.pageActifs + 1) + " / " + pages + " "
          ),
          precedent,
          suivant,
        ]),
      ]),
      cartes,
    ]);
  }

  // --- Le tableau des actifs, triable et filtrable --------------------------

  const COLONNES = [
    { cle: "nom", nom: "Actif", tri: "texte" },
    { cle: "poche", nom: "Poche", tri: "texte" },
    { cle: "quantite", nom: "Quantité", num: true, tri: "nombre" },
    { cle: "prixDeRevient", nom: "Prix de revient", num: true, tri: "nombre" },
    { cle: "capitalNetInvesti", nom: "Capital net investi", num: true, tri: "nombre" },
    { cle: "cours", nom: "Cours", num: true, tri: "nombre" },
    { cle: "valeur", nom: "Valeur", num: true, tri: "nombre" },
    { cle: "plusValueLatente", nom: "+/− latente", num: true, tri: "nombre" },
    { cle: "remarque", nom: "", tri: null },
  ];

  function trier(positions) {
    const colonne = etat.tri.colonne;
    const sens = etat.tri.sens;
    const def = COLONNES.find(function (col) {
      return col.cle === colonne;
    });
    return positions.slice().sort(function (a, b) {
      const va = a[colonne];
      const vb = b[colonne];
      // Ce qui n'a pas de valeur va TOUJOURS en bas, dans les deux sens de tri : une
      // ligne sans cours n'est pas la plus petite, elle est inconnue.
      const na = va === null || va === undefined;
      const nb = vb === null || vb === undefined;
      if (na && nb) return 0;
      if (na) return 1;
      if (nb) return -1;
      if (def && def.tri === "nombre") return (va - vb) * sens;
      return String(va).localeCompare(String(vb), "fr") * sens;
    });
  }

  function tableauActifs(c) {
    let positions = c.positions;
    if (etat.filtreType !== "tous") {
      positions = positions.filter(function (p) {
        return p.type === etat.filtreType;
      });
    }
    positions = trier(positions);

    const entetes = COLONNES.map(function (col) {
      if (!col.tri) return el("th", { texte: col.nom });
      const actif = etat.tri.colonne === col.cle;
      const th = el(
        "th",
        {
          class: "triable" + (col.num ? " num" : ""),
          role: "button",
          tabindex: "0",
          "aria-sort": actif ? (etat.tri.sens === 1 ? "ascending" : "descending") : "none",
        },
        [
          document.createTextNode(col.nom),
          actif ? el("span", { class: "fleche-tri", texte: etat.tri.sens === 1 ? "▲" : "▼" }) : null,
        ]
      );
      const basculer = function () {
        if (etat.tri.colonne === col.cle) etat.tri.sens = -etat.tri.sens;
        else etat.tri = { colonne: col.cle, sens: col.tri === "texte" ? 1 : -1 };
        dessiner();
      };
      th.addEventListener("click", basculer);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          basculer();
        }
      });
      return th;
    });

    const corps = positions.map(function (p) {
      const sansCours = p.valeur === null;
      // Pas de bouton « ? » dans une cellule : le tableau défile, et la bulle s'y
      // ferait couper. Ici la marque porte son explication en clair juste à côté.
      const remarque = el("td", {});
      if (sansCours) {
        remarque.append(
          el("span", { class: "mot mot--absent", texte: "Sans cours" }),
          el("span", { class: "actif__code", style: "display:block", texte: p.motifSansCours })
        );
      } else if (p.synthetique) {
        remarque.append(
          el("span", { class: "mot", texte: "Synthétique" }),
          el("span", {
            class: "actif__code", style: "display:block",
            texte: "la répartition affichée est celle de l'indice suivi",
          })
        );
      } else if (p.contenuDeclare) {
        remarque.append(
          el("span", { class: "mot", texte: "Contenu déclaré" }),
          el("span", {
            class: "actif__code", style: "display:block",
            texte: p.contenuDeclare + " : ni pays ni secteur",
          })
        );
      }

      return el("tr", { class: sansCours ? "sans-valeur" : null }, [
        el("td", {}, [
          el("span", { class: "actif__nom", texte: p.nom }),
          el("span", { class: "actif__code", texte: p.code + " · " + p.type }),
        ]),
        el("td", { texte: p.poche }),
        el("td", { class: "num", texte: quantite(p.quantite) }),
        el("td", { class: "num", texte: cours(p.prixDeRevient) }),
        el("td", { class: "num", texte: euros(p.capitalNetInvesti) }),
        el("td", { class: "num", texte: cours(p.cours) }),
        el("td", { class: "num", texte: euros(p.valeur) }),
        el("td", {
          class: "num " + (sansCours ? "" : classe(p.plusValueLatente)),
          texte: sansCours ? "–" : eurosSignes(p.plusValueLatente),
        }),
        remarque,
      ]);
    });

    let valeur = 0;
    let capital = 0;
    let latente = 0;
    let sansCoursCompte = 0;
    for (const p of positions) {
      capital += p.capitalNetInvesti;
      if (p.valeur === null) sansCoursCompte++;
      else {
        valeur += p.valeur;
        latente += p.plusValueLatente;
      }
    }
    // Quand AUCUNE ligne n'a de cours, le total n'est pas zéro : il est inconnu.
    const rien = positions.length > 0 && sansCoursCompte === positions.length;

    const pied = el("tr", {}, [
      el("td", { colspan: 4, texte: "Total — " + positions.length + " lignes" }),
      el("td", { class: "num", texte: euros(Math.round(capital * 100) / 100) }),
      el("td", {}),
      el("td", { class: "num", texte: rien ? "–" : euros(Math.round(valeur * 100) / 100) }),
      el("td", {
        class: "num " + (rien ? "" : classe(latente)),
        texte: rien ? "–" : eurosSignes(Math.round(latente * 100) / 100),
      }),
      el("td", {
        class: "actif__code",
        texte: rien
          ? "aucune ligne valorisée"
          : sansCoursCompte
          ? sansCoursCompte + " sans cours"
          : "",
      }),
    ]);

    return el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, entetes)),
        el("tbody", {}, corps),
        el("tfoot", {}, pied),
      ]),
    ]);
  }

  // ==========================================================================
  // 7. LES ONGLETS
  // ==========================================================================

  function ongletSynthese(c) {
    const page = el("div", {});
    const tuiles = el("div", { class: "tuiles" });

    tuiles.append(
      tuile("Gain", eurosSignes(c.gain), {
        ton: c.gain === null ? "neutre" : c.gain >= 0 ? "gain" : "perte",
        classe: classe(c.gain),
        aide: "gain",
        pied: c.gain === null ? c.motif || "non calculable" : "sur " + dureeEnClair(c.jours),
      })
    );
    tuiles.append(
      tuile("TRI", tauxEnPourCent(c.tri), {
        ton: c.tri === null ? "neutre" : c.tri >= 0 ? "gain" : "perte",
        classe: classe(c.tri),
        aide: c.peuSignificatif ? "peuSignificatif" : "tri",
        pied: c.peuSignificatif && c.tri !== null ? piedAvecMot("Peu fiable") : "annualisé",
      })
    );
    tuiles.append(
      tuile("TWRR", tauxEnPourCent(c.twrr), {
        ton: c.twrr === null ? "neutre" : c.twrr >= 0 ? "gain" : "perte",
        classe: classe(c.twrr),
        aide: c.peuSignificatif ? "peuSignificatif" : "twrr",
        pied:
          c.twrrAnnualise === null
            ? "sur la période"
            : "annualisé " + tauxEnPourCent(c.twrrAnnualise),
      })
    );
    tuiles.append(
      tuile("Valeur des actifs", euros(c.valeur), {
        petit: true,
        aide: "valeur",
        pied: c.partiel
          ? piedAvecMot("Partiel", c.nonValorisees.length + " sans cours", "absent")
          : "au " + dateCourte(c.arreteAu),
      })
    );
    tuiles.append(
      tuile("Capital net investi", euros(c.capital), {
        petit: true,
        aide: "capital",
        pied:
          c.latente === null
            ? "valeur inconnue : pas de plus-value calculable"
            : [
                document.createTextNode("plus-value latente "),
                el("b", { class: classe(c.latente), texte: eurosSignes(c.latente) }),
              ],
      })
    );
    page.append(tuiles);

    page.append(
      el("div", { class: "rangee rangee--apres" }, [
        bloc(
          "Évolution du capital",
          c.debut ? dateCourte(c.debut) + " → " + dateCourte(c.fin) : null,
          el("div", {}, [graphique(c.courbe, 250), legendeCourbe()])
        ),
        blocPoches(c),
      ])
    );

    page.append(el("div", { class: "rangee rangee--large rangee--apres" }, [cartesActifs(c)]));
    return page;
  }

  function ongletActifs(c) {
    return el("div", {}, [bloc(null, null, tableauActifs(c), "bloc--plein")]);
  }

  // --- Diversification ------------------------------------------------------

  // Les classes d'actifs et les zones tenaient chacune dans un bloc trop petit pour
  // ce qu'elles disent. Elles partagent desormais une vue d'ensemble : ce sont les deux
  // reponses larges, avant d'entrer dans le detail des pays et des secteurs.
  /* Une rubrique par onglet, dans l'ordre où on se pose les questions : de quoi mon
   * argent est-il fait, où dans le monde, dans quel pays précisément, dans quels
   * métiers. Les mettre toutes sur un même écran écrasait chacune d'elles. */
  const RUBRIQUES = [
    { cle: "classes", nom: "Actifs" },
    { cle: "zones", nom: "Zone géographique" },
    { cle: "pays", nom: "Pays" },
    { cle: "secteurs", nom: "Secteur" },
  ];

  function cleAideDuReste(mot) {
    if (mot === "non-couvert") return "nonCouvert";
    if (mot === "non-attribue") return "nonAttribue";
    if (mot === "hors-classification") return "numeriques";
    return "horsActions";
  }

  /** Une ligne de répartition : le repère visuel, le libellé, la barre, le montant, la
   *  part. Toutes les barres sont rapportées à la MÊME base — jamais renormalisées. */
  function ligneMesuree(poste, maxi, options) {
    const o = options || {};
    const libelle = el("span", { class: "rang__libelle" }, [
      o.drapeau ? drapeau(poste.code) : icone(poste.icone),
      el("span", { class: "rang__texte", texte: poste.libelle }),
    ]);
    return el("div", { class: "rang" + (o.absent ? " rang--absent" : "") }, [
      libelle,
      el("span", { class: "rang__piste" }, [
        el("span", {
          class: "rang__barre" + (o.absent ? " rang__barre--absent" : ""),
          style: "width:" + Math.max(0.8, (poste.pourCent / maxi) * 100) + "%",
        }),
      ]),
      el("span", { class: "rang__montant nb", texte: euros(poste.montant) }),
      el("span", { class: "rang__part nb", texte: pourCent(poste.pourCent) }),
    ]);
  }

  function blocClassement(rubrique, avecDrapeaux) {
    const restes = rubrique.restes || [];
    const tout = rubrique.postes.concat(restes);
    const maxi = Math.max.apply(
      null,
      tout.map(function (p) {
        return p.pourCent;
      })
    );
    const liste = el("div", { class: "classement" });
    for (const poste of parTaille(rubrique.postes, "pourCent")) {
      liste.append(ligneMesuree(poste, maxi, { drapeau: avecDrapeaux }));
    }
    if (restes.length) {
      const coupure = el("div", { class: "classement__coupure" }, [
        el("span", { texte: "Ce qui n'entre pas dans cette répartition" }),
      ]);
      const secoursCent = aide("pasCent");
      if (secoursCent) coupure.append(secoursCent[0]);
      liste.append(coupure);
      for (const reste of parTaille(restes, "pourCent")) {
        const ligne = ligneMesuree(reste, maxi, { drapeau: false, absent: true });
        const secours = aide(cleAideDuReste(reste.mot));
        if (secours) ligne.firstChild.append(secours[0]);
        liste.append(ligne);
      }
    }
    return liste;
  }

  /** La rampe d'une seule teinte, du fonce au clair. Une couleur suit TOUJOURS son
   *  poste, jamais son rang : on la calcule sur la position canonique du poste, et on
   *  trie ensuite pour l'affichage. */
  function teinte(i, combien) {
    return hslEnHex(197, 58, 26 + (i / Math.max(1, combien - 1)) * 40);
  }

  function remarquesDiversification(d) {
    return el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "Fonds synthétiques : on affiche l'indice suivi, pas le panier détenu",
        }),
        el("span", { class: "part", texte: d.actifsSynthetiques.length + " fonds" }),
      ]),
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "Composition déclarée à la main, donc sans date d'arrêté",
        }),
        el("span", { class: "part", texte: d.declareesALaMain.length + " actifs" }),
      ]),
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "Non couvert : " + d.actifsNonCouverts[0].motif,
        }),
        el("span", { class: "part nb", texte: euros(d.actifsNonCouverts[0].montant) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "Nomenclature sectorielle employée" }),
        el("span", { class: "part", texte: d.nomenclature }),
      ]),
    ]);
  }

  function ongletDiversification(c) {
    const d = D.diversification;
    const page = el("div", {});

    // On CHOISIT ce qu'on regarde. Il n'y a pas de filtre sur cet écran, parce qu'il n'y
    // a rien à filtrer : une répartition est la photo d'un tout.
    page.append(
      el(
        "div",
        { class: "onglets onglets--secondaires", role: "tablist" },
        RUBRIQUES.map(function (r) {
          const b = el("button", {
            type: "button",
            role: "tab",
            "aria-selected": String(etat.rubrique === r.cle),
            texte: r.nom,
          });
          b.addEventListener("click", function () {
            etat.rubrique = r.cle;
            dessiner();
          });
          return b;
        })
      )
    );

    if (c.valeur === null) {
      page.append(
        bloc(
          "Répartition",
          null,
          el("p", {
            class: "vide",
            texte:
              "Sans cours, aucune position n'a de valeur : il n'y a rien à répartir. Une répartition est la photo d'une valeur à une date, pas une liste d'actifs.",
          })
        )
      );
      return page;
    }

    /* Les parts de l'anneau. Une couleur suit son POSTE, jamais son rang : elle est
     * calculee sur la position canonique du poste dans le referentiel, puis les parts
     * sont triees par taille pour l'affichage. Sans cela, decocher une poche
     * repeindrait les survivants.
     *
     * Au-dela de deux postes hors repartition, ils sont REGROUPES en une seule part
     * hachuree et nommee, avec son montant : une quinzaine d'arcs d'une meme teinte
     * serait illisible. Rien n'est masque — le classement a cote les detaille un par
     * un, et le total du regroupement est ecrit. */
    function partsDeLAnneau(rubrique) {
      const restes = rubrique.restes || [];
      const postes = rubrique.postes.map(function (poste, i) {
        return {
          libelle: poste.libelle,
          montant: poste.montant,
          couleur: teinte(i, rubrique.postes.length),
        };
      });
      let absentes;
      if (restes.length > 2) {
        const total = restes.reduce(function (s, poste) {
          return s + poste.montant;
        }, 0);
        absentes = [
          {
            libelle: "Hors cette répartition",
            montant: Math.round(total * 100) / 100,
            absent: true,
          },
        ];
      } else {
        absentes = restes.map(function (poste) {
          return { libelle: poste.libelle, montant: poste.montant, absent: true };
        });
      }
      return parTaille(postes, "montant").concat(absentes);
    }

    /** Un écran de répartition : le classement chiffré à gauche, l'anneau à droite.
     *  L'anneau ne porte ni légende ni chiffre — le classement les donne tous, et à
     *  côté. C'est lui qui fait foi. */
    function ecranDeRepartition(titre, note, cleAide, rubrique, avecDrapeaux) {
      return el("div", { class: "rangee rangee--trois-quarts rangee--apres" }, [
        bloc(titre, note, blocClassement(rubrique, avecDrapeaux), null, cleAide),
        bloc(
          "Vu en anneau",
          "base " + euros(d.base),
          el("div", { class: "anneau-bloc anneau-bloc--colonne" }, [
            anneau(partsDeLAnneau(rubrique), 170, fEntier.format(d.base) + " €"),
            el("p", {
              class: "reference",
              style: "text-align:center; margin:10px 0 0",
              texte: "Les montants et les parts sont dans le classement, à gauche.",
            }),
          ])
        ),
      ]);
    }

    if (etat.rubrique === "classes") {
      page.append(
        ecranDeRepartition(
          "Par classe d'actifs",
          "base " + euros(d.base),
          "pasCent",
          d.classes,
          false
        )
      );
    } else if (etat.rubrique === "zones") {
      page.append(
        ecranDeRepartition(
          "Par zone d'investisseur",
          "convention datée et sourcée",
          "zones",
          { postes: d.pays.zones, restes: d.pays.restes },
          false
        )
      );
    } else if (etat.rubrique === "pays") {
      page.append(
        ecranDeRepartition(
          "Par pays",
          "règle dominante : " + d.pays.regleDominante,
          "regleDePays",
          d.pays,
          true
        )
      );
      // Les compléments passent en dessous : ils expliquent, ils ne se comparent pas.
      page.append(
        el("div", { class: "rangee rangee--large rangee--apres" }, [
          bloc("Ce qu'il faut savoir de ces chiffres", null, remarquesDiversification(d)),
        ])
      );
    } else {
      page.append(
        ecranDeRepartition("Par secteur", d.nomenclature, "secteurs", d.secteurs, false)
      );
    }

    return page;
  }

  // --- Frais et taxes -------------------------------------------------------

  function ongletFrais() {
    const k = D.couts;
    const v = D.valeurReelle;
    const page = el("div", {});

    page.append(
      el("div", { class: "tuiles" }, [
        tuile("Payé depuis le début", euros(k.coutPaye), {
          petit: true,
          ton: "perte",
          pied:
            k.nombreOrdres + " ordres · " + euros(k.fraisPayes) + " de frais, " +
            euros(k.taxesPayees) + " de taxes",
        }),
        tuile("Poids moyen d'un coût", tauxEnPourCent(k.poidsMoyen, false), {
          petit: true,
          pied: "du montant brut de l'opération",
        }),
        tuile("Spread d'entrée estimé", euros(k.spreadEstimeEntree), {
          petit: true,
          aide: "spread",
          pied: piedAvecMot("Estimé", tauxEnPourCent(k.tauxSpreadEntree, false) + " en moyenne"),
        }),
        tuile("Spread de sortie estimé", euros(k.spreadEstimeSortie), {
          petit: true,
          aide: "spread",
          pied: piedAvecMot("Estimé", tauxEnPourCent(k.tauxSpreadSortie, false) + " en moyenne"),
        }),
        tuile("Frais courants à un an", euros(k.terAnnuel), {
          petit: true,
          aide: "ter",
          pied: piedAvecMot("Estimé", tauxEnPourCent(k.tauxTerMoyen, false) + " en moyenne"),
        }),
      ])
    );

    // Ce tableau grandit avec le portefeuille : il occupe donc toute la largeur, seul
    // sur sa rangée. Le mettre à côté d'un bloc de hauteur fixe creuserait un vide qui
    // grandirait avec lui.
    const parActif = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Actif" }),
          el("th", { texte: "Poche" }),
          el("th", { class: "num", texte: "Valeur" }),
          el("th", { class: "num", texte: "TER" }),
          el("th", { class: "num", texte: "Frais courants / an" }),
          el("th", { class: "num", texte: "Spread de sortie" }),
        ])),
        el("tbody", {}, D.positions.map(function (p) {
          const tauxSpread = k.spreads[p.type];
          return el("tr", { class: p.valeur === null ? "sans-valeur" : null }, [
            el("td", {}, [el("span", { class: "actif__nom", texte: p.nom })]),
            el("td", { texte: p.poche }),
            el("td", { class: "num", texte: euros(p.valeur) }),
            el("td", {
              class: "num",
              texte: p.ter === null ? "–" : fNombre.format(p.ter) + " %",
            }),
            el("td", { class: "num" }, [
              p.terMontant
                ? document.createTextNode(euros(p.terMontant))
                : el("span", {
                    class: "actif__code",
                    texte:
                      p.valeur === null
                        ? "sans cours"
                        : p.type === "Action"
                        ? "sans objet : une action n'a pas de TER"
                        : p.type === "Crypto"
                        ? "sans objet"
                        : "TER non déclaré",
                  }),
            ]),
            el("td", { class: "num" }, [
              p.valeur === null
                ? el("span", { class: "actif__code", texte: "sans cours" })
                : document.createTextNode(
                    euros(Math.round(((p.valeur * tauxSpread) / 100) * 100) / 100) +
                      " · " + fNombre.format(tauxSpread) + " %"
                  ),
            ]),
          ]);
        })),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 4, texte: "Total estimé" }),
          el("td", { class: "num", texte: euros(k.terAnnuel) }),
          el("td", { class: "num", texte: euros(k.spreadEstimeSortie) }),
        ])),
      ]),
    ]);

    const cascade = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "Valeur brute des actifs" }),
        el("span", { class: "nb", texte: euros(v.valeurBrute) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "− frais de vente estimés" }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.fraisDeVente) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "− spread de sortie estimé" }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.spreadDeSortie) }),
      ]),
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "− impôt estimé, sur " + euros(v.baseImposable) + " de base imposable",
        }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.impot) }),
      ]),
      el("li", { class: "liste-parts__total" }, [
        el("span", { class: "liste-parts__nom", texte: "Valeur réelle" }),
        el("span", { class: "nb", texte: euros(v.valeurReelle) }),
      ]),
    ]);

    const enteteValeurReelle = el("div", { class: "bloc__entete" }, [
      el("h2", { class: "bloc__titre", texte: "Si vous vendiez tout aujourd'hui" }),
    ]);
    const secoursVr = aide("valeurReelle");
    if (secoursVr) enteteValeurReelle.append(secoursVr[0]);
    const noteMinoree = el("span", { class: "bloc__note" }, [
      el("span", { class: "mot", texte: "Minorée" }),
    ]);
    const secoursMin = aide("minoree");
    if (secoursMin) noteMinoree.append(secoursMin[0]);
    enteteValeurReelle.append(noteMinoree);
    const blocValeurReelle = el("section", { class: "bloc" }, [enteteValeurReelle, cascade]);

    const parPoche = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Poche" }),
          el("th", { class: "num", texte: "Valeur brute" }),
          el("th", { class: "num", texte: "Base imposable" }),
          el("th", { class: "num", texte: "Taux" }),
          el("th", { class: "num", texte: "Impôt estimé" }),
          el("th", { class: "num", texte: "Valeur réelle" }),
          el("th", { texte: "Règle appliquée" }),
        ])),
        el("tbody", {}, v.parPoche.map(function (p) {
          return el("tr", {}, [
            el("td", { texte: p.poche }),
            el("td", { class: "num", texte: euros(p.valeurBrute) }),
            el("td", { class: "num", texte: euros(p.baseImposable) }),
            el("td", {
              class: "num",
              texte: p.tauxImpot === null ? "–" : fNombre.format(p.tauxImpot) + " %",
            }),
            el("td", { class: "num", texte: euros(p.impot) }),
            el("td", { class: "num", texte: euros(p.valeurReelle) }),
            el("td", {}, [
              document.createTextNode(p.regle),
              p.minoree
                ? el("span", { class: "mot", style: "margin-left:6px", texte: "Minorée" })
                : null,
            ]),
          ]);
        })),
        el("tfoot", {}, el("tr", {}, [
          el("td", { texte: "Total" }),
          el("td", { class: "num", texte: euros(v.valeurBrute) }),
          el("td", { class: "num", texte: euros(v.baseImposable) }),
          el("td", { class: "num" }),
          el("td", { class: "num", texte: euros(v.impot) }),
          el("td", { class: "num", texte: euros(v.valeurReelle) }),
          el("td", {}),
        ])),
      ]),
    ]);

    page.append(
      el("div", { class: "rangee rangee--large rangee--apres" }, [
        bloc(
          "1. Ce qui a déjà été prélevé",
          "réel, sauf le spread",
          el("ul", { class: "liste-parts" }, [
            el("li", {}, [
              el("span", {
                class: "liste-parts__nom",
                texte: "Frais d'ordre payés, sur " + k.nombreOrdres + " ordres",
              }),
              el("span", { class: "nb perte", texte: euros(k.fraisPayes) }),
            ]),
            el("li", {}, [
              el("span", { class: "liste-parts__nom" }, [
                document.createTextNode("Retenue à la source sur les dividendes "),
                (aide("retenueDividendes") || [null])[0],
              ]),
              el("span", { class: "nb perte", texte: euros(k.taxesPayees) }),
            ]),
            el("li", {}, [
              el("span", { class: "liste-parts__nom" }, [
                document.createTextNode(
                  "Spread d'entrée, " + tauxEnPourCent(k.tauxSpreadEntree, false) + " en moyenne "
                ),
                el("span", { class: "mot", texte: "Estimé" }),
                (aide("spread") || [null])[0],
              ]),
              el("span", { class: "nb", texte: euros(k.spreadEstimeEntree) }),
            ]),
          ]),
          null,
          "coutsPreleves"
        ),
      ])
    );
    page.append(
      el("div", { class: "rangee rangee--large rangee--apres" }, [
        bloc(
          "2. Pendant la détention — les frais courants",
          "estimés",
          parActif,
          "bloc--plein",
          "ter"
        ),
      ])
    );
    page.append(
      el("div", { class: "rangee rangee--apres" }, [
        bloc("3. À la sortie — par poche", null, parPoche, "bloc--plein", "baseImposable"),
        blocValeurReelle,
      ])
    );

    return page;
  }

  // --- Détail des calculs ---------------------------------------------------

  function ongletDetail(c) {
    const page = el("div", {});

    page.append(
      el("p", {
        class: "chapeau",
        texte:
          "Cet onglet existe pour une seule raison : pouvoir refaire chaque chiffre à la main. " +
          "Les autres écrans montrent les résultats, celui-ci montre les tables qui les produisent.",
      })
    );

    const debut = c.courbe.length ? c.courbe[0] : null;
    const fin = c.courbe.length ? c.courbe[c.courbe.length - 1] : null;
    let sommeFlux = 0;
    for (const f of c.flux) sommeFlux += f.montant;

    const calculGain = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "Valeur des actifs au " + dateCourte(c.fin),
        }),
        el("span", { class: "nb", texte: euros(fin ? fin.valeur : null) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "− valeur au " + dateCourte(c.debut) }),
        el("span", { class: "nb", texte: eurosSignes(debut ? -debut.valeur : null) }),
      ]),
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "+ somme des flux de la période (" + c.flux.length + " opérations)",
        }),
        el("span", { class: "nb " + classe(sommeFlux), texte: eurosSignes(sommeFlux) }),
      ]),
      el("li", { class: "liste-parts__total" }, [
        el("span", { class: "liste-parts__nom", texte: "= gain" }),
        el("span", { class: "nb " + classe(c.gain), texte: eurosSignes(c.gain) }),
      ]),
    ]);

    const ecart = el("div", {}, [
      el("ul", { class: "liste-parts" }, [
        el("li", {}, [
          el("span", { class: "liste-parts__nom", texte: "Gain, sur les flux bruts" }),
          el("span", { class: "nb " + classe(c.gain), texte: eurosSignes(c.gain) }),
        ]),
        el("li", {}, [
          el("span", {
            class: "liste-parts__nom",
            texte: "Somme de la colonne « +/− latente »",
          }),
          el("span", { class: "nb " + classe(c.latente), texte: eurosSignes(c.latente) }),
        ]),
        el("li", { class: "liste-parts__total" }, [
          el("span", { class: "liste-parts__nom", texte: "Écart, qui est normal" }),
          el("span", {
            class: "nb",
            texte:
              c.gain === null || c.latente === null
                ? "–"
                : eurosSignes(Math.round((c.gain - c.latente) * 100) / 100),
          }),
        ]),
      ]),
      el("p", {
        class: "chapeau",
        style: "margin:10px 0 0",
        texte:
          "Le gain se calcule sur les montants bruts, sans les frais. La plus-value latente se " +
          "mesure contre le capital net investi, qui est net de frais et réduit au prorata des " +
          "ventes. Les deux sont justes, et ils ne se rejoignent pas." +
          (c.partiel
            ? " S'ajoute ici le capital des lignes sans cours, exclues de la performance : " +
              c.nonValorisees.join(", ") + "."
            : ""),
      }),
    ]);

    page.append(
      el("div", { class: "rangee rangee--deux" }, [
        bloc("Comment le gain est obtenu", "glossaire §4", calculGain),
        bloc("Pourquoi il ne tombe pas sur la somme de la colonne", null, ecart),
      ])
    );

    const lignesFlux = [];
    if (debut && debut.valeur > 0) {
      lignesFlux.push(
        el("tr", {}, [
          el("td", { texte: dateCourte(debut.date) }),
          el("td", { texte: "Valeur au début de la période" }),
          el("td", { texte: "—" }),
          el("td", { class: "num perte", texte: eurosSignes(-debut.valeur) }),
        ])
      );
    }
    for (const f of c.flux) {
      lignesFlux.push(
        el("tr", {}, [
          el("td", { texte: dateCourte(f.date) }),
          el("td", { texte: f.libelle }),
          el("td", {}, [
            el("span", { class: "actif__nom", texte: D.parCode[f.actif].nom }),
            el("span", { class: "actif__code", texte: f.poche }),
          ]),
          el("td", { class: "num " + classe(f.montant), texte: eurosSignes(f.montant) }),
        ])
      );
    }
    if (fin) {
      lignesFlux.push(
        el("tr", {}, [
          el("td", { texte: dateCourte(fin.date) }),
          el("td", { texte: "Valeur à la fin de la période" }),
          el("td", { texte: "—" }),
          el("td", { class: "num gain", texte: eurosSignes(fin.valeur) }),
        ])
      );
    }

    const tableFlux = el("div", { class: "cadre-tableau", style: "--hauteur-tableau:330px" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Date" }),
          el("th", { texte: "Opération" }),
          el("th", { texte: "Actif" }),
          el("th", { class: "num", texte: "Montant brut" }),
        ])),
        el("tbody", {}, lignesFlux),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 3, texte: "Taux qui annule la valeur actuelle nette = TRI" }),
          el("td", { class: "num " + classe(c.tri), texte: tauxEnPourCent(c.tri) }),
        ])),
      ]),
    ]);

    const tableSous = el("div", { class: "cadre-tableau", style: "--hauteur-tableau:330px" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Du" }),
          el("th", { texte: "Au" }),
          el("th", { class: "num", texte: "Valeur début" }),
          el("th", { class: "num", texte: "Entrées" }),
          el("th", { class: "num", texte: "Valeur fin" }),
          el("th", { class: "num", texte: "Rendement" }),
        ])),
        el("tbody", {}, c.sousPeriodes.map(function (s) {
          return el("tr", {}, [
            el("td", { texte: dateCourte(s.du) }),
            el("td", { texte: dateCourte(s.au) }),
            el("td", { class: "num", texte: euros(s.valeurDebut) }),
            el("td", { class: "num", texte: eurosSignes(s.entrees) }),
            el("td", { class: "num", texte: euros(s.valeurFin) }),
            el("td", {
              class: "num " + classe(s.rendement),
              texte: tauxEnPourCent(s.rendement),
            }),
          ]);
        })),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 5, texte: "Produit des rendements, moins un = TWRR" }),
          el("td", { class: "num " + classe(c.twrr), texte: tauxEnPourCent(c.twrr) }),
        ])),
      ]),
    ]);

    page.append(
      el("div", { class: "rangee rangee--deux rangee--apres" }, [
        bloc(
          "Les flux datés, qui donnent le TRI",
          c.flux.length + " opérations",
          tableFlux,
          "bloc--plein"
        ),
        bloc(
          "Les sous-périodes, qui donnent le TWRR",
          c.sousPeriodes.length + " sous-périodes",
          tableSous,
          "bloc--plein"
        ),
      ])
    );

    const e = D.couts.exemple;
    const formule = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: e.libelle }),
        el("span", { class: "nb", texte: euros(e.montantBrut) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "Frais d'ordre réellement prélevés" }),
        el("span", { class: "nb", texte: euros(e.frais) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "Poids dans l'opération" }),
        el("span", { class: "nb", texte: tauxEnPourCent(e.poids, false) }),
      ]),
      el("li", {}, [
        el("span", { class: "liste-parts__nom", texte: "Spread estimé : " + e.formuleSpread }),
        el("span", { class: "mot", texte: "Estimé" }),
      ]),
      el("li", {}, [
        el("span", {
          class: "liste-parts__nom",
          texte: "Taux employé : " + e.taux + " (" + e.fourchette + ")",
        }),
        el("span", { class: "reference", texte: e.source }),
      ]),
    ]);

    const hypotheses = el(
      "ul",
      { class: "liste-parts" },
      D.valeurReelle.hypotheses.map(function (h) {
        return el("li", {}, [el("span", { class: "liste-parts__nom", texte: h })]);
      })
    );

    page.append(
      el("div", { class: "rangee rangee--deux rangee--apres" }, [
        bloc("Une estimation, de bout en bout", "un exemple", formule, null, "estime"),
        bloc(
          "Ce que le calcul d'impôt suppose",
          D.valeurReelle.hypotheses.length + " hypothèses",
          hypotheses,
          null,
          "baseImposable"
        ),
      ])
    );

    page.append(
      el("div", { class: "rangee rangee--large rangee--apres", id: "a-surveiller" }, [
        bloc(
          "À surveiller",
          D.aSurveiller.length + (D.aSurveiller.length > 1 ? " points" : " point"),
          el("div", { class: "surveiller" }, [
            el("ul", {}, D.aSurveiller.map(function (s) {
              return el("li", {}, [
                el("b", { texte: s.categorie }),
                el("span", { texte: s.message }),
                s.reference
                  ? el("span", {
                      class: "reference",
                      style: "display:block; margin-top:2px",
                      texte: "référence : " + s.reference,
                    })
                  : null,
              ]);
            })),
          ])
        ),
      ])
    );

    return page;
  }

  // ==========================================================================
  // 8. L'ASSEMBLAGE
  // ==========================================================================

  const ONGLETS = [
    {
      cle: "synthese", nom: "Synthèse", dessin: ongletSynthese,
      periode: true, type: false, poches: true,
    },
    {
      cle: "actifs", nom: "Les actifs", dessin: ongletActifs,
      periode: false, type: true, poches: true,
    },
    {
      // Aucun filtre ici : une répartition est la photo d'un tout, il n'y a rien à
      // filtrer. Un filtre qui n'agit sur rien est pire qu'absent.
      cle: "diversification", nom: "Diversification", dessin: ongletDiversification,
      periode: false, type: false, poches: false,
    },
    {
      cle: "frais", nom: "Frais et taxes", dessin: ongletFrais,
      periode: false, type: false, poches: false,
    },
    {
      cle: "detail", nom: "Détail des calculs", dessin: ongletDetail,
      periode: true, type: false, poches: true,
    },
  ];

  function squelette() {
    const onglets = el(
      "nav",
      { class: "onglets", role: "tablist", "aria-label": "Sections" },
      ONGLETS.map(function (o) {
        const b = el("button", {
          type: "button",
          role: "tab",
          "data-onglet": o.cle,
          "aria-selected": String(etat.onglet === o.cle),
          texte: o.nom,
        });
        b.addEventListener("click", function () {
          etat.onglet = o.cle;
          etat.pageActifs = 0;
          dessiner();
        });
        return b;
      })
    );

    const entete = el("header", { class: "entete" }, [
      el("div", { class: "bande bande--titre" }, [
        el("span", { class: "marque" }, [
          el("span", { class: "marque__point", "aria-hidden": "true" }),
          el("span", { texte: "Tableau de bord" }),
        ]),
        onglets,
        el("div", { class: "pousse", id: "signalements" }),
      ]),
      el("div", { class: "bande bande--filtres", id: "filtres" }),
      el("div", { class: "bande bande--etat", id: "etat" }),
    ]);

    const page = el("main", { class: "page" }, [el("div", { id: "corps" })]);
    const pied = el("footer", { class: "pied" }, [el("div", { class: "bande", id: "pied" })]);
    (document.getElementById("app") || document.body).append(entete, page, pied);
  }

  function groupe(valeurs, actuelle, surChoix) {
    return el(
      "div",
      { class: "groupe" },
      valeurs.map(function (v) {
        const b = el("button", {
          type: "button",
          "aria-pressed": String(v.cle === actuelle),
          texte: v.nom,
        });
        b.addEventListener("click", function () {
          surChoix(v.cle);
        });
        return b;
      })
    );
  }

  function dessiner() {
    fermerLaBulle();
    const c = contexte();
    const onglet = ONGLETS.find(function (o) {
      return o.cle === etat.onglet;
    });

    // --- Les filtres, qui ne s'affichent QUE là où ils servent ---
    const filtres = document.getElementById("filtres");
    filtres.innerHTML = "";
    if (onglet.periode) {
      filtres.append(
        el("span", { class: "etiquette", texte: "Période" }),
        groupe(PERIODES, etat.periode, function (cle) {
          etat.periode = cle;
          dessiner();
        })
      );
    }
    if (onglet.type) {
      filtres.append(
        el("span", { class: "etiquette", texte: "Type d'actif" }),
        groupe(
          [
            { cle: "tous", nom: "Tous" },
            { cle: "ETF", nom: "ETF" },
            { cle: "Action", nom: "Actions" },
            { cle: "Crypto", nom: "Crypto" },
          ],
          etat.filtreType,
          function (cle) {
            etat.filtreType = cle;
            dessiner();
          }
        )
      );
    }
    if (onglet.poches) {
      filtres.append(
      el("span", { class: "etiquette", texte: "Poches" }),
      el(
        "div",
        { class: "groupe" },
        POCHES.map(function (poche) {
          const presente = c.pochesPresentes.includes(poche);
          const b = el("button", {
            type: "button",
            class: "poche-eteinte",
            "aria-pressed": String(presente && etat.poches.has(poche)),
            texte: poche,
            title: presente ? "" : "Ce portefeuille n'a pas de " + poche,
          });
          b.disabled = !presente;
          b.addEventListener("click", function () {
            // On ne décoche jamais la dernière poche : un écran sans aucune poche ne dit
            // rien, et laisserait croire à un portefeuille vide.
            if (etat.poches.has(poche)) {
              if (etat.poches.size > 1) etat.poches.delete(poche);
            } else {
              etat.poches.add(poche);
            }
            etat.pageActifs = 0;
            dessiner();
          });
          return b;
        })
      )
      );
    }
    // Une bande de filtres vide n'a pas lieu d'exister : elle se retire.
    filtres.hidden = filtres.childNodes.length === 0;

    // --- Le compteur de signalements, qui mène au détail ---
    const zoneSignalements = document.getElementById("signalements");
    zoneSignalements.innerHTML = "";
    const bouton = el("button", {
      class: "bouton bouton--surveiller",
      type: "button",
      texte: "À surveiller · " + D.aSurveiller.length,
    });
    bouton.addEventListener("click", function () {
      etat.onglet = "detail";
      dessiner();
      const cible = document.getElementById("a-surveiller");
      if (cible) cible.scrollIntoView({ block: "center" });
    });
    zoneSignalements.append(bouton);

    // --- L'état des données : toujours visible, jamais en bas de page ---
    const etatBande = document.getElementById("etat");
    etatBande.innerHTML = "";
    etatBande.append(
      el("span", { html: "Cours arrêtés au <b>" + dateCourte(c.arreteAu) + "</b>" }),
      el("span", { texte: "Source : " + c.source }),
      el("span", {
        texte:
          c.debut === null
            ? "Aucune période valorisable"
            : "Du " + dateCourte(c.debut) + " au " + dateCourte(c.fin) +
              " · " + dureeEnClair(c.jours),
      }),
      el("span", { texte: c.positions.length + " positions" }),
      c.partiel
        ? el("span", {}, [
            el("span", { class: "mot mot--absent", texte: "Partiel" }),
            document.createTextNode(" " + c.nonValorisees.join(", ")),
          ])
        : null,
      !c.toutesPoches
        ? el("span", { texte: "Poches retenues : " + c.pochesActives.join(", ") })
        : null
    );

    // --- Le corps ---
    const corps = document.getElementById("corps");
    corps.innerHTML = "";
    corps.append(onglet.dessin(c));

    document.querySelectorAll("[data-onglet]").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.dataset.onglet === etat.onglet));
    });

    // --- Le pied : les réglages de la MAQUETTE, hors de l'application ---
    // Ils sont ici, et non dans l'en-tête, pour que l'écran se lise comme l'application
    // et non comme une démonstration.
    const pied = document.getElementById("pied");
    pied.innerHTML = "";
    pied.append(
      el("span", { class: "etiquette", texte: "Maquette · jeu fictif" }),
      groupe(
        Object.keys(JEUX).map(function (cle) {
          return { cle: cle, nom: JEUX[cle].nom };
        }),
        etat.jeu,
        function (cle) {
          etat.jeu = cle;
          etat.poches = new Set(POCHES);
          etat.pageActifs = 0;
          dessiner();
        }
      ),
      el("span", { class: "reference", texte: JEUX[etat.jeu].aide })
    );
  }

  /* Filet de sécurité : une maquette qui plante doit le DIRE. Une page blanche
   * laisserait croire que l'écran est vide, alors que c'est le code qui a échoué —
   * exactement l'erreur que l'application s'interdit de commettre sur les chiffres. */
  function demarrer() {
    try {
      squelette();
      dessiner();
    } catch (erreur) {
      const avis = document.createElement("pre");
      avis.style.cssText =
        "margin:24px;padding:16px;border:1px solid #a34b2e;color:#a34b2e;" +
        "white-space:pre-wrap;font-family:monospace;font-size:13px";
      avis.textContent =
        "La maquette n'a pas pu se dessiner.\n\n" +
        (erreur && erreur.stack ? erreur.stack : String(erreur)) +
        "\n\nCopie ce message et donne-le à Claude : c'est un défaut de la maquette, " +
        "pas de tes données.";
      document.body.prepend(avis);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
