/* Construit les maquettes de l'étape 8 à partir du jeu de données fictif.
 *
 * Pourquoi du JavaScript plutôt que des pages écrites à la main : parce que l'étape 8
 * doit éprouver chaque écran sur des portefeuilles différents (D-62) et sur plusieurs
 * périodes, et qu'une maquette figée ne montre qu'un seul cas.
 *
 * CE QUI EST VRAIMENT CALCULÉ ICI, et non recopié :
 *   - le gain, par la formule du glossaire : valeur finale − valeur initiale + flux ;
 *   - le TRI, par dichotomie sur les flux datés, comme le moteur ;
 *   - le TWRR, en chaînant les sous-périodes bornées par les jours de flux.
 * Conséquence voulue : changer de période ou décocher une poche donne des chiffres
 * cohérents entre eux, et l'onglet « Détail » montre les tables qui les produisent.
 * Une maquette dont les chiffres ne tiennent pas apprend à se méfier du vrai écran.
 *
 * Rien ici ne préjuge du code de l'étape 9 : Dash reconstruira ces blocs en Python.
 * Ce qui se transmet, c'est la feuille de style et la disposition.
 */

(function () {
  "use strict";

  const D = window.MAQUETTE;
  const POCHES = ["PEA", "CTO", "Crypto"];
  const COULEUR_POCHE = { PEA: "var(--poche-1)", CTO: "var(--poche-2)", Crypto: "var(--poche-3)" };

  // ==========================================================================
  // 1. MISE EN FORME
  // Deux unités, deux fonctions. Les confondre a déjà produit « 6264,00 % » au
  // lieu de 62,64 % (étape 7). On ne multiplie jamais par cent ailleurs.
  // ==========================================================================

  const fNombre = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function euros(n) {
    return n === null || n === undefined ? "–" : fNombre.format(n) + " €";
  }

  function eurosSignes(n) {
    if (n === null || n === undefined) return "–";
    return (n > 0 ? "+" : n < 0 ? "−" : "") + fNombre.format(Math.abs(n)) + " €";
  }

  /** Reçoit un TAUX (0,6264). Pour le TRI, le TWRR, un rendement, un poids. */
  function tauxEnPourCent(t, avecSigne) {
    if (t === null || t === undefined || !isFinite(t)) return "–";
    const signe = avecSigne === false ? "" : t > 0 ? "+" : t < 0 ? "−" : "";
    return signe + fNombre.format(Math.abs(t) * 100) + " %";
  }

  /** Reçoit un POUR CENT déjà calculé (62,64). Pour les répartitions. */
  function pourCent(p) {
    return p === null || p === undefined ? "–" : fNombre.format(p) + " %";
  }

  /** Une quantité de titres : jusqu'à quatre décimales, parce qu'un ETF s'achète
   *  en fractions et qu'une crypto en très petites fractions. */
  const fQuantite = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  });

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
    const [a, m, j] = iso.split("-");
    return j + "/" + m + "/" + a;
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

  // ==========================================================================
  // 2. LE VOCABULAIRE D'ÉCRAN
  // Chaque explication tient dans un bouton « ? », jamais dans le corps du
  // texte : un écran de tableau de bord se lit, il ne se récite pas.
  // Voir docs/conception-interface.md §2.
  // ==========================================================================

  const AIDES = {
    gain: {
      titre: "Le gain",
      texte:
        "Ce que vos actifs ont rapporté sur la période : <b>leur valeur d'aujourd'hui, moins leur valeur au départ, plus tout ce qui est entré et sorti entre-temps</b>. Les frais et les taxes n'y sont pas : ils sont traités dans l'onglet « Frais et taxes ». Le calcul complet est dans l'onglet « Détail ».",
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
    sansCours: {
      titre: "Sans cours",
      texte:
        "Aucun cours utilisable à cette date pour cet actif. Sa <b>quantité reste juste</b> — ce sont les opérations qui la donnent — mais sa valeur est inconnue, donc elle ne compte dans aucun total.",
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
        "L'écart entre le prix d'achat et le prix de vente d'un actif à un instant donné. Vous le payez <b>deux fois</b> : à l'entrée et à la sortie, sans qu'il apparaisse jamais sur un relevé. Il est estimé à partir d'un taux par type d'actif.",
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
    minoree: {
      titre: "Estimation minorée",
      texte:
        "Volontairement <b>prudente</b> : une partie de l'impôt ne peut pas être calculée depuis les seuls titres, elle est donc laissée de côté. Le montant réellement dû serait plus bas que la valeur réelle affichée.",
    },
    contenuDeclare: {
      titre: "Contenu déclaré",
      texte:
        "Vous avez indiqué vous-même de quoi cet actif est fait. Il compte à 100 % dans sa classe, et il <b>sort</b> des pays et des secteurs — là où ces notions ne veulent rien dire pour lui.",
    },
  };

  let compteurBulles = 0;

  /** Le bouton « ? » et sa bulle. Se ferme à l'Échap et au clic ailleurs. */
  function aide(cle) {
    const a = AIDES[cle];
    if (!a) return null;
    const id = "bulle-" + ++compteurBulles;
    const bouton = el("button", {
      class: "aide",
      type: "button",
      "aria-expanded": "false",
      "aria-controls": id,
      "aria-label": "Qu'est-ce que « " + a.titre + " » ?",
      texte: "?",
    });
    const bulle = el("span", { class: "bulle", id: id, role: "note" }, [
      el("b", { class: "bulle__titre", texte: a.titre }),
      el("span", { html: a.texte }),
    ]);
    bulle.hidden = true;
    bouton.addEventListener("click", function (evenement) {
      evenement.stopPropagation();
      const ouvert = bouton.getAttribute("aria-expanded") === "true";
      fermerLesBulles();
      if (!ouvert) {
        bouton.setAttribute("aria-expanded", "true");
        bulle.hidden = false;
      }
    });
    return [bouton, bulle];
  }

  function fermerLesBulles() {
    document.querySelectorAll(".aide[aria-expanded='true']").forEach(function (b) {
      b.setAttribute("aria-expanded", "false");
      const bulle = document.getElementById(b.getAttribute("aria-controls"));
      if (bulle) bulle.hidden = true;
    });
  }

  document.addEventListener("click", fermerLesBulles);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermerLesBulles();
  });

  // ==========================================================================
  // 3. LES CALCULS
  // Les mêmes formules que le glossaire. Elles sont ici pour que la maquette
  // soit cohérente quand on change de période ou de poche — pas pour remplacer
  // le moteur, qui les fait sur les opérations réelles.
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
        const annees = nombreDeJours(dateDebut, l.date) / 365;
        total += l.montant / Math.pow(1 + taux, annees);
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
   * La convention est celle qui rend le calcul refaisable à la main : une sous-période
   * commence JUSTE APRÈS un flux et s'arrête JUSTE AVANT le suivant. Elle ne contient
   * donc aucun flux, et son rendement est un simple rapport de valeurs — pas de
   * correction à appliquer, rien à retrancher.
   *
   * C'est ce qui a coûté deux essais : compter les flux à la fin d'une sous-période
   * donnait un TWRR de −60 %, parce que la valeur ne bouge qu'au point de courbe
   * suivant alors que le montant, lui, était compté tout de suite. Les dates de flux du
   * jeu fictif sont maintenant calées sur les points de la courbe, et le rendement
   * d'une sous-période est le rapport de deux valeurs voisines.
   *
   * Le TWRR est le produit de ces rendements, moins un : l'écran montre les deux, et
   * ils ne peuvent donc pas se contredire.
   */
  function calculerSousPeriodes(points, flux) {
    if (points.length < 2) return [];

    /** La valeur au dernier point STRICTEMENT avant cette date : juste avant le flux. */
    const valeurAvant = function (date) {
      let valeur = null;
      for (const p of points) {
        if (p.date < date) valeur = p.valeur;
        else break;
      }
      return valeur;
    };

    /** La valeur au premier point à cette date ou après : le flux y est déjà compris. */
    const valeurApres = function (date) {
      for (const p of points) if (p.date >= date) return p.valeur;
      return points[points.length - 1].valeur;
    };

    /* Le chaînage commence au premier jour où il y a quelque chose à faire fructifier.
     * Un rendement se mesure sur un capital : partir d'une valeur nulle ne donne pas
     * un rendement infini, ça ne donne pas de rendement du tout. */
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
      // Le flux qui OUVRE la sous-période : il est déjà dans la valeur de départ.
      let entrees = 0;
      for (const f of flux) if (f.date === du) entrees += -f.montant;
      const valeurDebut = valeurApres(du);
      const valeurFin = au === fin ? points[points.length - 1].valeur : valeurAvant(au);
      if (valeurDebut === null || valeurDebut <= 0 || valeurFin === null) continue;
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
    if (taux === null || jours <= 0) return null;
    return Math.pow(1 + taux, 365 / jours) - 1;
  }

  // ==========================================================================
  // 4. L'ÉTAT, ET CE QU'ON EN DÉDUIT
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
    traitementReste: "mesure",
    arrangementFrais: "a",
  };

  const JEUX = {
    complet: {
      nom: "Complet",
      aide: "Onze lignes : ETF actions, ETF obligataire, or, deux actions en direct, crypto, un fonds non couvert, une position sans cours.",
      construire: function () {
        return { positions: D.positions, courbe: D.courbe, flux: D.flux };
      },
    },
    uneLigne: {
      nom: "Une seule ligne",
      aide: "Un plan d'épargne démarré il y a deux mois. Le TRI et le TWRR existent, mais ne veulent rien dire — et l'écran doit le dire.",
      construire: function () {
        // 198,00 de capital net investi = 200,00 d'achats bruts − 2,00 de frais.
        // 7,94 titres à 26,12 = 207,39, soit 9,39 de plus-value latente.
        const quantiteDetenue = 7.94;
        const coursDuJour = 26.12;
        const valeur = Math.round(quantiteDetenue * coursDuJour * 100) / 100;
        const position = {
          code: "XX0000000012",
          nom: "Alizé Europe 600 UCITS ETF",
          poche: "PEA",
          type: "ETF",
          quantite: quantiteDetenue,
          prixDeRevient: Math.round((198.0 / quantiteDetenue) * 100) / 100,
          capitalNetInvesti: 198.0,
          cours: coursDuJour,
          valeur: valeur,
          plusValueLatente: Math.round((valeur - 198.0) * 100) / 100,
          ter: 0.12,
          terMontant: Math.round(valeur * 0.0012 * 100) / 100,
        };
        const flux = [
          { date: "2026-07-21", libelle: "Achat", poche: "PEA", montant: -100.0, frais: 1 },
          { date: "2026-08-25", libelle: "Achat", poche: "PEA", montant: -100.0, frais: 1 },
        ];
        // Comme pour le jeu complet, la courbe est dérivée des flux : elle démarre une
        // semaine avant le premier achat, à zéro, et monte par paliers.
        const courbe = [];
        const depart = Date.parse("2026-07-14T00:00:00Z");
        const pas = 10;
        const croissance = valeur / 200.0 - 1; // 200,00 d'achats bruts
        for (let i = 0; i <= pas; i++) {
          const date =
            i === pas
              ? "2026-09-25"
              : new Date(depart + i * 7 * 86400000).toISOString().slice(0, 10);
          let base = 0;
          let investi = 0;
          for (const f of flux) {
            if (f.date > date) continue;
            base += -f.montant;
            investi += -f.montant - f.frais;
          }
          const t = i / pas;
          const v =
            i === pas
              ? valeur
              : Math.round(base * (1 + croissance * t + 0.009 * Math.sin(i / 1.4)) * 100) / 100;
          courbe.push({
            date: date,
            valeur: v,
            investi: investi,
            parPoche: { PEA: { valeur: v, investi: investi } },
          });
        }
        return { positions: [position], courbe: courbe, flux: flux };
      },
    },
    sansPea: {
      nom: "Sans PEA",
      aide: "Un CTO et de la crypto seulement. L'écran ne doit pas laisser un trou là où le PEA serait.",
      construire: function () {
        return {
          positions: D.positions.filter(function (p) {
            return p.poche !== "PEA";
          }),
          courbe: D.courbe,
          flux: D.flux.filter(function (f) {
            return f.poche !== "PEA";
          }),
          pochesAbsentes: ["PEA"],
        };
      },
    },
    aucunCours: {
      nom: "Aucun cours",
      aide: "La source de cours est muette sur tout le portefeuille. C'est le cas qui casse les tableaux de bord : il ne doit afficher ni zéro, ni total vide.",
      construire: function () {
        return {
          positions: D.positions.map(function (p) {
            return Object.assign({}, p, {
              cours: null,
              dateCours: null,
              place: null,
              valeur: null,
              plusValueLatente: null,
              motifSansCours:
                "aucun cours utilisable au 25/09/2026 : la source n'a répondu pour aucun actif",
            });
          }),
          courbe: [],
          flux: D.flux,
          sansCours: true,
        };
      },
    },
  };

  /** Tout ce que l'écran affiche, recalculé selon la période et les poches. */
  function contexte() {
    const jeu = JEUX[etat.jeu].construire();
    const pochesPresentes = POCHES.filter(function (p) {
      return !(jeu.pochesAbsentes || []).includes(p);
    });
    const actives = pochesPresentes.filter(function (p) {
      return etat.poches.has(p);
    });

    const positions = jeu.positions.filter(function (p) {
      return actives.includes(p.poche);
    });

    // La courbe, recomposée sur les seules poches retenues, puis coupée à la période.
    let courbe = jeu.courbe.map(function (point) {
      let valeur = 0;
      let investi = 0;
      for (const poche of actives) {
        const part = point.parPoche && point.parPoche[poche];
        if (part) {
          valeur += part.valeur;
          investi += part.investi;
        }
      }
      return {
        date: point.date,
        valeur: Math.round(valeur * 100) / 100,
        investi: Math.round(investi * 100) / 100,
      };
    });

    const periode = PERIODES.find(function (p) {
      return p.cle === etat.periode;
    });
    let debutPeriode = null;
    if (courbe.length) {
      if (periode.jours === null) {
        // « Tout » part du premier jour où il y a quelque chose à valoriser.
        const premier = courbe.findIndex(function (p) {
          return p.valeur > 0;
        });
        courbe = courbe.slice(Math.max(0, premier - 1));
      } else {
        const fin = Date.parse(courbe[courbe.length - 1].date);
        const seuil = new Date(fin - periode.jours * 86400000).toISOString().slice(0, 10);
        const coupe = courbe.filter(function (p) {
          return p.date >= seuil;
        });
        courbe = coupe.length >= 2 ? coupe : courbe.slice(-2);
      }
      debutPeriode = courbe[0].date;
    }

    /* La borne de gauche est INCLUSIVE quand la période commence à une valeur nulle,
     * et STRICTE sinon. C'est la seule convention qui donne un gain juste dans les deux
     * cas : depuis l'origine, les tout premiers achats font partie de la période ;
     * au milieu de la vie du portefeuille, ils sont déjà dans la valeur de départ.
     * Sans cette distinction, « Tout » perdait le premier achat et surestimait le gain. */
    const borneInclusive = courbe.length > 0 && courbe[0].valeur === 0;
    const flux = jeu.flux.filter(function (f) {
      if (!actives.includes(f.poche)) return false;
      if (debutPeriode === null) return true;
      const apresLeDebut = borneInclusive ? f.date >= debutPeriode : f.date > debutPeriode;
      return apresLeDebut && f.date <= courbe[courbe.length - 1].date;
    });

    // Les totaux qui s'additionnent, pris sur les positions.
    let valeur = 0;
    let capital = 0;
    let latente = 0;
    const nonValorisees = [];
    for (const p of positions) {
      capital += p.capitalNetInvesti;
      if (p.valeur === null) nonValorisees.push(p.nom);
      else {
        valeur += p.valeur;
        latente += p.plusValueLatente;
      }
    }
    const rienDeValorise = positions.length > 0 && nonValorisees.length === positions.length;

    let gain = null;
    let tri = null;
    let twrr = null;
    let twrrAnnualise = null;
    let sousPeriodes = [];
    let jours = null;
    if (courbe.length >= 2) {
      const debut = courbe[0];
      const fin = courbe[courbe.length - 1];
      jours = nombreDeJours(debut.date, fin.date);
      gain = calculerGain(debut.valeur, fin.valeur, flux);
      tri = calculerTri(debut.date, debut.valeur, fin.date, fin.valeur, flux);
      sousPeriodes = calculerSousPeriodes(courbe, flux);
      twrr = chainer(sousPeriodes);
      twrrAnnualise = annualiser(twrr, jours);
    }

    return {
      jeu: jeu,
      pochesPresentes: pochesPresentes,
      pochesActives: actives,
      positions: positions,
      courbe: courbe,
      flux: flux,
      debut: debutPeriode,
      fin: courbe.length ? courbe[courbe.length - 1].date : null,
      jours: jours,
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
      arreteAu: D.synthese.arreteAu,
      source: D.synthese.sourceDesCours,
      toutesPoches: actives.length === pochesPresentes.length,
    };
  }

  // ==========================================================================
  // 5. LES BRIQUES
  // ==========================================================================

  function bloc(titre, note, contenu, classes) {
    return el("section", { class: "bloc" + (classes ? " " + classes : "") }, [
      titre
        ? el("div", { class: "bloc__entete" }, [
            el("h2", { class: "bloc__titre", texte: titre }),
            note ? el("span", { class: "bloc__note", texte: note }) : null,
          ])
        : null,
      contenu,
    ]);
  }

  /** Une tuile de chiffre clé : l'étiquette, le « ? », le chiffre, une note courte. */
  function tuile(etiquette, valeurTexte, options) {
    const o = options || {};
    const secours = aide(o.aide);
    const haut = el("div", { class: "tuile__haut" }, [
      el("span", { class: "etiquette", texte: etiquette }),
      secours ? secours[0] : null,
    ]);
    return el(
      "div",
      { class: "tuile tuile--" + (o.ton || "neutre") },
      [
        haut,
        secours ? secours[1] : null,
        el("span", {
          class: "tuile__valeur" + (o.petit ? " tuile__valeur--petit" : "") + " " + (o.classe || ""),
          texte: valeurTexte,
        }),
        el("span", { class: "tuile__pied" }, o.pied || null),
      ]
    );
  }

  /** La note du pied d'une tuile : un mot encadré, éventuellement suivi d'un texte. */
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
    const mg = { g: 60, d: 14, h: 12, b: 24 };
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

    const ns = "http://www.w3.org/2000/svg";
    function s(balise, attributs, texte) {
      const noeud = document.createElementNS(ns, balise);
      for (const cle in attributs || {}) {
        if (attributs[cle] === null || attributs[cle] === undefined) continue;
        noeud.setAttribute(cle, String(attributs[cle]));
      }
      if (texte !== undefined) noeud.textContent = texte;
      return noeud;
    }

    const svg = s("svg", {
      class: "graphique",
      viewBox: "0 0 " + L + " " + H,
      role: "img",
      "aria-label":
        "Évolution du capital brut et du capital net investi, du " +
        dateCourte(points[0].date) +
        " au " +
        dateCourte(points[points.length - 1].date) +
        ".",
    });

    for (let i = 0; i <= 4; i++) {
      const v = (plafond / 4) * i;
      svg.append(s("line", { class: "grille", x1: mg.g, x2: L - mg.d, y1: y(v), y2: y(v) }));
      svg.append(
        s(
          "text",
          { x: mg.g - 8, y: y(v) + 3.5, "text-anchor": "end" },
          fNombre.format(v).replace(",00", "") + " €"
        )
      );
    }

    const combien = points.length > 30 ? 5 : 3;
    for (let k = 0; k < combien; k++) {
      const i = Math.round((k / (combien - 1)) * (points.length - 1));
      svg.append(
        s(
          "text",
          {
            x: x(i),
            y: H - 6,
            "text-anchor": k === 0 ? "start" : k === combien - 1 ? "end" : "middle",
          },
          dateCourte(points[i].date)
        )
      );
    }

    let traceBrut = "";
    for (let i = 0; i < points.length; i++) {
      traceBrut += (i ? " L " : "M ") + x(i).toFixed(1) + " " + y(points[i].valeur).toFixed(1);
    }
    svg.append(
      s("path", {
        class: "aire-brut",
        d:
          traceBrut +
          " L " + x(points.length - 1).toFixed(1) + " " + y(0) +
          " L " + x(0).toFixed(1) + " " + y(0) + " Z",
      })
    );

    // Le capital net investi monte en escalier : il ne bouge qu'aux achats.
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
    svg.append(s("path", { class: "serie serie--investi", d: traceInvesti }));
    svg.append(s("path", { class: "serie serie--brut", d: traceBrut }));

    const dernier = points[points.length - 1];
    svg.append(
      s("circle", {
        cx: x(points.length - 1),
        cy: y(dernier.valeur),
        r: 3.5,
        fill: "var(--courbe-brut)",
        stroke: "var(--surface)",
        "stroke-width": 2,
      })
    );

    // --- Le survol : viseur, deux points, et une étiquette chiffrée ---
    const viseur = s("line", { class: "viseur", y1: mg.h, y2: mg.h + haut });
    const pointBrut = s("circle", {
      r: 4,
      fill: "var(--courbe-brut)",
      stroke: "var(--surface)",
      "stroke-width": 2,
    });
    const pointInvesti = s("circle", {
      r: 3.5,
      fill: "var(--courbe-investi)",
      stroke: "var(--surface)",
      "stroke-width": 2,
    });
    const groupeSurvol = s("g");
    groupeSurvol.style.display = "none";
    groupeSurvol.append(viseur, pointBrut, pointInvesti);
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
          el("i", {
            style: "border-top-color: var(--courbe-investi); border-top-style: dashed",
          }),
          el("span", { texte: "Capital net investi" }),
          el("b", { texte: euros(p.investi) }),
        ]),
        el("span", { class: "infobulle__ligne", style: "margin-top:4px" }, [
          el("span", { texte: "Écart" }),
          el("b", { class: classe(ecart), texte: eurosSignes(ecart) }),
        ])
      );
      infobulle.hidden = false;
      // L'étiquette suit la souris mais reste dans le cadre.
      const largeurBulle = 196;
      const gauche = Math.min(
        Math.max(0, ((x(i) - mg.g) / L) * boite.width - largeurBulle / 2 + mg.g),
        boite.width - largeurBulle
      );
      infobulle.style.left = gauche + "px";
      infobulle.style.top = "6px";
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
        el("i", {
          style: "border-top-color: var(--courbe-investi); border-top-style: dashed",
        }),
        document.createTextNode("Capital net investi — ce qui a été placé, net de frais"),
      ]),
    ]);
  }

  // --- La répartition dans les poches, en version compacte -----------------

  function partsDesPoches(c) {
    const lignes = [];
    for (const poche of c.pochesActives) {
      let valeur = 0;
      for (const p of c.positions) {
        if (p.poche === poche && p.valeur !== null) valeur += p.valeur;
      }
      if (valeur > 0) lignes.push({ poche: poche, valeur: Math.round(valeur * 100) / 100 });
    }
    return lignes;
  }

  function blocPoches(c) {
    const parts = partsDesPoches(c);
    if (!parts.length) {
      return bloc(
        "Où est l'argent",
        null,
        el("p", { class: "vide", texte: "Aucune poche valorisée : il n'y a rien à répartir." })
      );
    }
    const total = parts.reduce(function (s, p) {
      return s + p.valeur;
    }, 0);

    const barre = el(
      "div",
      { class: "barre" },
      parts.map(function (p) {
        return el("div", {
          class: "barre__part",
          style: "width:" + (p.valeur / total) * 100 + "%; background:" + COULEUR_POCHE[p.poche],
          title: p.poche + " — " + euros(p.valeur),
        });
      })
    );

    const liste = el(
      "ul",
      { class: "liste-parts" },
      parts.map(function (p) {
        return el("li", {}, [
          el("span", { class: "puce", style: "background:" + COULEUR_POCHE[p.poche] }),
          el("span", { texte: p.poche }),
          el("span", { class: "nb", texte: euros(p.valeur) }),
          el("span", { class: "part", texte: pourCent((p.valeur / total) * 100) }),
        ]);
      })
    );

    return bloc("Où est l'argent", "sur " + euros(total), el("div", {}, [barre, liste]));
  }

  function blocSurveiller(compact) {
    const liste = D.aSurveiller.slice(0, compact ? 3 : D.aSurveiller.length);
    return bloc(
      "À surveiller",
      D.aSurveiller.length + (D.aSurveiller.length > 1 ? " points" : " point"),
      el("div", { class: "surveiller" }, [
        el(
          "ul",
          {},
          liste.map(function (s) {
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
          })
        ),
        compact && D.aSurveiller.length > 3
          ? el("p", {
              class: "reference",
              style: "margin:8px 0 0",
              texte: "et " + (D.aSurveiller.length - 3) + " autre(s), dans l'onglet Détail.",
            })
          : null,
      ])
    );
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

  function nombreDepuis(valeur) {
    if (valeur === null || valeur === undefined) return null;
    if (typeof valeur === "number") return valeur;
    return parseFloat(String(valeur).replace(/\s/g, "").replace(",", "."));
  }

  function trier(positions) {
    const colonne = etat.tri.colonne;
    const sens = etat.tri.sens;
    const copie = positions.slice();
    copie.sort(function (a, b) {
      const va = a[colonne];
      const vb = b[colonne];
      // Ce qui n'a pas de valeur va TOUJOURS en bas, dans les deux sens de tri :
      // une ligne sans cours n'est pas la plus petite, elle est inconnue.
      const na = va === null || va === undefined;
      const nb = vb === null || vb === undefined;
      if (na && nb) return 0;
      if (na) return 1;
      if (nb) return -1;
      const def = COLONNES.find(function (col) {
        return col.cle === colonne;
      });
      if (def && def.tri === "nombre") {
        return (nombreDepuis(va) - nombreDepuis(vb)) * sens;
      }
      return String(va).localeCompare(String(vb), "fr") * sens;
    });
    return copie;
  }

  function tableauActifs(c, limite) {
    let positions = c.positions;
    if (etat.filtreType !== "tous") {
      positions = positions.filter(function (p) {
        return p.type === etat.filtreType;
      });
    }
    positions = trier(positions);
    const montrees = limite ? positions.slice(0, limite) : positions;

    const entetes = COLONNES.map(function (col) {
      if (!col.tri) return el("th", { texte: col.nom });
      const actif = etat.tri.colonne === col.cle;
      const th = el("th", {
        class: "triable" + (col.num ? " num" : ""),
        role: "button",
        tabindex: "0",
        "aria-sort": actif ? (etat.tri.sens === 1 ? "ascending" : "descending") : "none",
      }, [
        document.createTextNode(col.nom),
        actif ? el("span", { class: "fleche", texte: etat.tri.sens === 1 ? "▲" : "▼" }) : null,
      ]);
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

    const corps = montrees.map(function (p) {
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
            class: "actif__code",
            style: "display:block",
            texte: "la répartition affichée est celle de l'indice suivi",
          })
        );
      } else if (p.contenuDeclare) {
        remarque.append(
          el("span", { class: "mot", texte: "Contenu déclaré" }),
          el("span", {
            class: "actif__code",
            style: "display:block",
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
        el("td", { class: "num", texte: sansCours ? "–" : euros(p.valeur) }),
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
        texte: rien ? "aucune ligne valorisée" : sansCoursCompte ? sansCoursCompte + " sans cours" : "",
      }),
    ]);

    const cadre = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, entetes)),
        el("tbody", {}, corps),
        el("tfoot", {}, pied),
      ]),
    ]);
    if (limite && positions.length > limite) {
      cadre.append(
        el("p", {
          class: "reference",
          style: "padding:8px 9px 0",
          texte:
            "Les " + limite + " premières lignes selon le tri en cours. Les " +
            positions.length + " lignes sont dans l'onglet « Les actifs ».",
        })
      );
    }
    return cadre;
  }

  // --- Les répartitions ----------------------------------------------------

  /** La liste mesurée : chaque poste est une barre rapportée à la MÊME base.
   *  Rien n'est renormalisé : la somme des barres ne fait pas la largeur. */
  function listeMesuree(rubrique) {
    const grille = el("div", { class: "mesure" });
    const maxi = Math.max.apply(
      null,
      rubrique.postes.concat(rubrique.restes).map(function (p) {
        return p.pourCent;
      })
    );

    function ligne(poste, estReste) {
      const libelle = el("span", { class: "mesure__libelle", texte: poste.libelle });
      grille.append(
        estReste ? el("span", { class: "mesure__libelle", texte: poste.libelle }) : libelle,
        el("span", { class: "mesure__piste" }, [
          el("span", {
            class: "mesure__barre" + (estReste ? " mesure__barre--absent" : ""),
            style: "width:" + (poste.pourCent / maxi) * 100 + "%",
          }),
        ]),
        el("span", { class: "mesure__montant nb", texte: euros(poste.montant) }),
        el("span", { class: "mesure__part nb", texte: pourCent(poste.pourCent) })
      );
    }

    for (const poste of rubrique.postes) ligne(poste, false);
    if (rubrique.restes.length) {
      grille.append(el("hr", { class: "separateur" }));
      for (const reste of rubrique.restes) {
        const enveloppe = el("span", { class: "mesure__libelle", style: "position:relative" });
        enveloppe.append(el("span", { texte: reste.libelle + " " }));
        const cle =
          reste.mot === "non-couvert"
            ? "nonCouvert"
            : reste.mot === "non-attribue"
            ? "nonAttribue"
            : reste.mot === "hors-classification"
            ? "numeriques"
            : "horsActions";
        const secours = aide(cle);
        if (secours) enveloppe.append(secours[0], secours[1]);
        grille.append(
          enveloppe,
          el("span", { class: "mesure__piste" }, [
            el("span", {
              class: "mesure__barre mesure__barre--absent",
              style: "width:" + (reste.pourCent / maxi) * 100 + "%",
            }),
          ]),
          el("span", { class: "mesure__montant nb", texte: euros(reste.montant) }),
          el("span", { class: "mesure__part nb", texte: pourCent(reste.pourCent) })
        );
      }
    }
    return grille;
  }

  /** Le tour du portefeuille : une seule barre pour toute la valeur, dont la part
   *  non attribuée est un segment hachuré et NOMMÉ. Le total fait forcément la
   *  largeur, mais ce qui manque y est visible comme un trou. */
  function tourDuPortefeuille(rubrique) {
    const tout = rubrique.postes.concat(rubrique.restes);
    const total = tout.reduce(function (s, p) {
      return s + p.pourCent;
    }, 0);
    const barre = el(
      "div",
      { class: "tour" },
      tout.map(function (p, i) {
        const estReste = i >= rubrique.postes.length;
        return el("div", {
          class: "tour__part" + (estReste ? " tour__part--absent" : ""),
          style:
            "width:" + (p.pourCent / total) * 100 + "%" +
            (estReste ? "" : ";background:" + teintePoste(i, rubrique.postes.length)),
          title: p.libelle + " — " + euros(p.montant) + " (" + pourCent(p.pourCent) + ")",
        });
      })
    );
    const liste = el(
      "ul",
      { class: "liste-parts", style: "margin-top:10px" },
      tout.map(function (p, i) {
        const estReste = i >= rubrique.postes.length;
        return el("li", {}, [
          el("span", {
            class: "puce",
            style: estReste
              ? "background:var(--absent); opacity:.55"
              : "background:" + teintePoste(i, rubrique.postes.length),
          }),
          el("span", {
            texte: p.libelle,
            style: estReste ? "font-style:italic; color:var(--encre-douce)" : null,
          }),
          el("span", { class: "nb", texte: euros(p.montant) }),
          el("span", { class: "part", texte: pourCent(p.pourCent) }),
        ]);
      })
    );
    return el("div", {}, [barre, liste]);
  }

  /** Une rampe d'une seule teinte, du foncé au clair. Pas de teintes inventées :
   *  au-delà de huit postes, des couleurs catégorielles deviennent indiscernables. */
  function teintePoste(i, combien) {
    const clarte = 26 + (i / Math.max(1, combien - 1)) * 42;
    return "hsl(197 62% " + clarte.toFixed(0) + "%)";
  }

  function blocRepartition(titre, rubrique, note, cleAide) {
    const contenu =
      etat.traitementReste === "mesure" ? listeMesuree(rubrique) : tourDuPortefeuille(rubrique);
    const secours = aide(cleAide);
    const entete = el("div", { class: "bloc__entete" }, [
      el("h2", { class: "bloc__titre", texte: titre }),
      secours ? secours[0] : null,
      note ? el("span", { class: "bloc__note", texte: note }) : null,
    ]);
    return el("section", { class: "bloc", style: "position:relative" }, [
      entete,
      secours ? secours[1] : null,
      contenu,
    ]);
  }

  // ==========================================================================
  // 6. LES ONGLETS
  // ==========================================================================

  function ongletSynthese(c) {
    const page = el("div", {});

    // --- Les tuiles ---
    const tuiles = el("div", { class: "tuiles" });

    tuiles.append(
      tuile("Gain", eurosSignes(c.gain), {
        ton: c.gain === null ? "neutre" : c.gain >= 0 ? "gain" : "perte",
        classe: classe(c.gain),
        aide: "gain",
        pied:
          c.gain === null
            ? "aucun cours : le gain ne peut pas être calculé"
            : "sur " + dureeEnClair(c.jours),
      })
    );

    const piedTri = c.peuSignificatif && c.tri !== null ? piedAvecMot("Peu fiable") : null;
    tuiles.append(
      tuile("TRI", tauxEnPourCent(c.tri), {
        ton: c.tri === null ? "neutre" : c.tri >= 0 ? "gain" : "perte",
        classe: classe(c.tri),
        aide: c.peuSignificatif ? "peuSignificatif" : "tri",
        pied: piedTri || "annualisé, sur les flux datés",
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
            : "sur la période · annualisé " + tauxEnPourCent(c.twrrAnnualise),
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

    // --- La rangée principale : la courbe, et une colonne compacte ---
    const courbe = bloc(
      "Évolution",
      c.debut ? dateCourte(c.debut) + " → " + dateCourte(c.fin) : null,
      el("div", {}, [graphique(c.courbe, 250), legendeCourbe()])
    );

    page.append(
      el("div", { class: "rangee" }, [
        courbe,
        el("div", { class: "colonne" }, [blocPoches(c), blocSurveiller(true)]),
      ])
    );

    // --- Le tableau, en bas : les premières lignes seulement ---
    page.append(
      el("div", { class: "rangee rangee--large" }, [
        bloc(
          "Positions détenues",
          c.positions.length + " lignes",
          tableauActifs(c, 6),
          "bloc--plein-tableau"
        ),
      ])
    );

    return page;
  }

  function ongletActifs(c) {
    const filtres = el("div", { class: "bande", style: "padding:0 0 10px; max-width:none" }, [
      el("span", { class: "etiquette", texte: "Type" }),
      el(
        "div",
        { class: "groupe" },
        ["tous", "ETF", "Action", "Crypto"].map(function (t) {
          const b = el("button", {
            type: "button",
            "aria-pressed": String(etat.filtreType === t),
            texte: t === "tous" ? "Tous" : t,
          });
          b.addEventListener("click", function () {
            etat.filtreType = t;
            dessiner();
          });
          return b;
        })
      ),
      el("span", {
        class: "reference",
        texte: "Les poches se filtrent dans l'en-tête. Cliquez un titre de colonne pour trier.",
      }),
    ]);

    return el("div", {}, [
      filtres,
      bloc(null, null, tableauActifs(c, null)),
    ]);
  }

  function ongletDiversification(c) {
    const d = D.diversification;
    const page = el("div", {});

    const choix = el("div", { class: "bande", style: "padding:0 0 10px; max-width:none" }, [
      el("span", { class: "etiquette", texte: "Traitement de ce qui manque" }),
      el(
        "div",
        { class: "groupe" },
        [
          { cle: "mesure", nom: "Barres sur une base commune" },
          { cle: "tour", nom: "Le tour du portefeuille" },
        ].map(function (o) {
          const b = el("button", {
            type: "button",
            "aria-pressed": String(etat.traitementReste === o.cle),
            texte: o.nom,
          });
          b.addEventListener("click", function () {
            etat.traitementReste = o.cle;
            dessiner();
          });
          return b;
        })
      ),
      el("span", { class: "reference", texte: "C'est l'arbitrage à rendre sur cet écran." }),
    ]);
    page.append(choix);

    if (etat.jeu === "aucunCours") {
      page.append(
        bloc(
          "Répartition",
          null,
          el("p", {
            class: "vide",
            texte:
              "Sans cours, aucune position n'a de valeur : il n'y a rien à répartir. Une répartition est une photo d'une valeur à une date, pas une liste d'actifs.",
          })
        )
      );
      return page;
    }

    page.append(
      el("div", { class: "rangee rangee--deux" }, [
        blocRepartition(
          "Par classe d'actifs",
          d.classes,
          "base " + euros(d.base),
          "pasCent"
        ),
        blocRepartition(
          "Par secteur",
          d.secteurs,
          d.nomenclature,
          "secteurs"
        ),
      ])
    );

    page.append(
      el("div", { class: "rangee rangee--large", style: "margin-top:10px" }, [
        blocRepartition(
          "Par pays",
          d.pays,
          "règle dominante : " + d.pays.regleDominante,
          "regleDePays"
        ),
      ])
    );

    // Les zones, et ce que la source dit d'elle-même.
    const zones = el("div", { class: "mesure" });
    const maxZone = Math.max.apply(
      null,
      d.pays.zones.map(function (z) {
        return z.pourCent;
      })
    );
    for (const z of d.pays.zones) {
      zones.append(
        el("span", { class: "mesure__libelle", texte: z.libelle }),
        el("span", { class: "mesure__piste" }, [
          el("span", {
            class: "mesure__barre",
            style: "width:" + (z.pourCent / maxZone) * 100 + "%",
          }),
        ]),
        el("span", { class: "mesure__montant nb", texte: euros(z.montant) }),
        el("span", { class: "mesure__part nb", texte: pourCent(z.pourCent) })
      );
    }

    // La source et la règle, LIGNE PAR LIGNE : c'est ce que demande D-72, et la
    // seule façon de ne pas mélanger deux nomenclatures sans le dire.
    const sources = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Poste" }),
          el("th", { texte: "Source" }),
          el("th", { texte: "Règle de pays" }),
          el("th", { class: "num", texte: "Part" }),
        ])),
        el(
          "tbody",
          {},
          d.pays.postes.map(function (p) {
            return el("tr", {}, [
              el("td", { texte: p.libelle }),
              el("td", { texte: p.source }),
              el("td", { texte: p.regle }),
              el("td", { class: "num", texte: pourCent(p.pourCent) }),
            ]);
          })
        ),
      ]),
    ]);

    page.append(
      el("div", { class: "rangee rangee--deux", style: "margin-top:10px" }, [
        bloc("Par zone d'investisseur", "convention datée et sourcée", zones),
        bloc("D'où vient chaque chiffre", "arrêtés du " + dateCourte(d.arreteDu) + " au " + dateCourte(d.arreteAu), sources),
      ])
    );

    const remarques = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { texte: "Fonds synthétiques : on affiche l'indice suivi" }),
        el("span", { class: "part", texte: d.actifsSynthetiques.length + " fonds" }),
      ]),
      el("li", {}, [
        el("span", { texte: "Composition déclarée à la main, sans date d'arrêté" }),
        el("span", { class: "part", texte: d.declareesALaMain.length + " actifs" }),
      ]),
      el("li", {}, [
        el("span", { texte: "Non couverts : " + d.actifsNonCouverts[0].motif }),
        el("span", { class: "part nb", texte: euros(d.actifsNonCouverts[0].montant) }),
      ]),
    ]);
    page.append(
      el("div", { class: "rangee rangee--large", style: "margin-top:10px" }, [
        bloc("Ce qu'il faut savoir de ces chiffres", null, remarques),
      ])
    );

    return page;
  }

  function ongletFrais() {
    const k = D.couts;
    const v = D.valeurReelle;
    const page = el("div", {});

    const choix = el("div", { class: "bande", style: "padding:0 0 10px; max-width:none" }, [
      el("span", { class: "etiquette", texte: "Découpage (Q-21)" }),
      el(
        "div",
        { class: "groupe" },
        [
          { cle: "a", nom: "Frais d'un côté, valeur réelle de l'autre" },
          { cle: "b", nom: "Un seul écran, trois niveaux" },
        ].map(function (o) {
          const b = el("button", {
            type: "button",
            "aria-pressed": String(etat.arrangementFrais === o.cle),
            texte: o.nom,
          });
          b.addEventListener("click", function () {
            etat.arrangementFrais = o.cle;
            dessiner();
          });
          return b;
        })
      ),
      el("span", { class: "reference", texte: "C'est l'arbitrage à rendre sur cet écran." }),
    ]);
    page.append(choix);

    // --- Les tuiles de coûts ---
    const tuiles = el("div", { class: "tuiles" }, [
      tuile("Payé depuis le début", euros(k.coutPaye), {
        petit: true,
        ton: "perte",
        pied: k.nombreOrdres + " ordres · " + euros(k.fraisPayes) + " de frais, " + euros(k.taxesPayees) + " de taxes",
      }),
      tuile("Poids moyen d'un coût", tauxEnPourCent(k.poidsMoyen, false), {
        petit: true,
        pied: "du montant brut de l'opération",
      }),
      tuile("Spread d'entrée estimé", euros(k.spreadEstimeEntree), {
        petit: true,
        ton: "neutre",
        aide: "spread",
        pied: piedAvecMot("Estimé"),
      }),
      tuile("Frais courants à un an", euros(k.terAnnuel), {
        petit: true,
        ton: "neutre",
        aide: "ter",
        pied: piedAvecMot("Estimé", "sur la valeur d'aujourd'hui"),
      }),
    ]);
    page.append(tuiles);

    // --- Le détail par actif ---
    const parActif = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Actif" }),
          el("th", { texte: "Poche" }),
          el("th", { class: "num", texte: "Valeur" }),
          el("th", { class: "num", texte: "TER" }),
          el("th", { class: "num", texte: "Frais courants / an" }),
        ])),
        el(
          "tbody",
          {},
          D.positions.map(function (p) {
            return el("tr", {}, [
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
                        p.type === "Crypto"
                          ? "sans objet : pas de frais courants"
                          : p.type === "Action"
                          ? "sans objet : une action n'a pas de TER"
                          : "TER non déclaré",
                    }),
              ]),
            ]);
          })
        ),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 4, texte: "Total estimé à un an" }),
          el("td", { class: "num", texte: euros(k.terAnnuel) }),
        ])),
      ]),
    ]);

    // --- La valeur réelle ---
    const secoursVr = aide("valeurReelle");
    const secoursMin = aide("minoree");
    const cascade = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { texte: "Valeur brute des actifs" }),
        el("span", { class: "nb", texte: euros(v.valeurBrute) }),
      ]),
      el("li", {}, [
        el("span", { texte: "− frais de vente estimés" }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.fraisDeVente) }),
      ]),
      el("li", {}, [
        el("span", { texte: "− spread de sortie estimé" }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.spreadDeSortie) }),
      ]),
      el("li", {}, [
        el("span", { texte: "− impôt estimé" }),
        el("span", { class: "nb perte", texte: eurosSignes(-v.impot) }),
      ]),
      el("li", { style: "border-top:1px solid var(--trait-fort); font-weight:600" }, [
        el("span", { texte: "Valeur réelle" }),
        el("span", { class: "nb", texte: euros(v.valeurReelle) }),
      ]),
    ]);

    const blocValeurReelle = el("section", { class: "bloc", style: "position:relative" }, [
      el("div", { class: "bloc__entete" }, [
        el("h2", { class: "bloc__titre", texte: "Si vous vendiez tout aujourd'hui" }),
        secoursVr ? secoursVr[0] : null,
        el("span", { class: "bloc__note" }, [
          el("span", { class: "mot", texte: "Minorée" }),
          secoursMin ? secoursMin[0] : null,
        ]),
      ]),
      secoursVr ? secoursVr[1] : null,
      secoursMin ? secoursMin[1] : null,
      cascade,
    ]);

    const parPoche = el("div", { class: "cadre-tableau" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Poche" }),
          el("th", { class: "num", texte: "Valeur brute" }),
          el("th", { class: "num", texte: "Impôt estimé" }),
          el("th", { class: "num", texte: "Valeur réelle" }),
          el("th", { texte: "Règle appliquée" }),
        ])),
        el(
          "tbody",
          {},
          v.parPoche.map(function (p) {
            return el("tr", {}, [
              el("td", { texte: p.poche }),
              el("td", { class: "num", texte: euros(p.valeurBrute) }),
              el("td", { class: "num", texte: euros(p.impot) }),
              el("td", { class: "num", texte: euros(p.valeurReelle) }),
              el("td", {}, [
                document.createTextNode(p.regle),
                p.minoree ? el("span", { class: "mot", style: "margin-left:6px", texte: "Minorée" }) : null,
              ]),
            ]);
          })
        ),
      ]),
    ]);

    if (etat.arrangementFrais === "a") {
      // (a) Ce que ça coûte d'un côté, ce qu'il reste de l'autre : deux questions.
      page.append(
        el("div", { class: "rangee rangee--deux" }, [
          bloc("Frais courants, actif par actif", "estimés", parActif),
          el("div", { class: "colonne" }, [blocValeurReelle, bloc("Par poche", null, parPoche)]),
        ])
      );
    } else {
      // (b) Les trois niveaux à la file : entrée, détention, sortie.
      page.append(
        el("div", { class: "rangee rangee--large" }, [
          bloc("1. À l'entrée — ce qui a été prélevé", "réel, sauf le spread", el("div", {}, [
            el("p", { class: "chapeau", texte:
              "Frais d'ordre et taxes réellement payés : " + euros(k.coutPaye) +
              " sur " + k.nombreOrdres + " ordres. Le spread d'entrée, lui, est estimé : " +
              euros(k.spreadEstimeEntree) + "." }),
          ])),
        ])
      );
      page.append(
        el("div", { class: "rangee rangee--deux", style: "margin-top:10px" }, [
          bloc("2. Pendant la détention — les frais courants", "estimés", parActif),
          el("div", { class: "colonne" }, [
            bloc("3. À la sortie — ce qu'il resterait", null, cascade),
            bloc("Par poche", null, parPoche),
          ]),
        ])
      );
    }

    return page;
  }

  function ongletDetail(c) {
    const page = el("div", {});

    page.append(
      el("p", {
        class: "chapeau",
        texte:
          "Cet onglet existe pour une seule raison : pouvoir refaire chaque chiffre à la main. " +
          "Les écrans précédents montrent les résultats, celui-ci montre les tables qui les produisent.",
      })
    );

    // --- Le gain ---
    const debut = c.courbe.length ? c.courbe[0] : null;
    const fin = c.courbe.length ? c.courbe[c.courbe.length - 1] : null;
    let sommeFlux = 0;
    for (const f of c.flux) sommeFlux += f.montant;

    const calculGain = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { texte: "Valeur des actifs au " + dateCourte(c.fin) }),
        el("span", { class: "nb", texte: euros(fin ? fin.valeur : null) }),
      ]),
      el("li", {}, [
        el("span", { texte: "− valeur au " + dateCourte(c.debut) }),
        el("span", { class: "nb", texte: eurosSignes(debut ? -debut.valeur : null) }),
      ]),
      el("li", {}, [
        el("span", { texte: "+ somme des flux de la période (" + c.flux.length + " opérations)" }),
        el("span", { class: "nb " + classe(sommeFlux), texte: eurosSignes(sommeFlux) }),
      ]),
      el("li", { style: "border-top:1px solid var(--trait-fort); font-weight:600" }, [
        el("span", { texte: "= gain" }),
        el("span", { class: "nb " + classe(c.gain), texte: eurosSignes(c.gain) }),
      ]),
    ]);

    // --- Pourquoi le gain n'est pas la somme d'une colonne ---
    const ecart = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { texte: "Gain (sur les flux bruts)" }),
        el("span", { class: "nb " + classe(c.gain), texte: eurosSignes(c.gain) }),
      ]),
      el("li", {}, [
        el("span", { texte: "Somme de la colonne « +/− latente »" }),
        el("span", { class: "nb " + classe(c.latente), texte: eurosSignes(c.latente) }),
      ]),
      el("li", { style: "border-top:1px solid var(--trait-fort)" }, [
        el("span", { texte: "Écart, qui est normal" }),
        el("span", {
          class: "nb",
          texte:
            c.gain === null || c.latente === null
              ? "–"
              : eurosSignes(Math.round((c.gain - c.latente) * 100) / 100),
        }),
      ]),
    ]);

    page.append(
      el("div", { class: "rangee rangee--deux" }, [
        bloc("Comment le gain est obtenu", "glossaire §4", calculGain),
        bloc(
          "Pourquoi il ne tombe pas sur la somme de la colonne",
          null,
          el("div", {}, [
            ecart,
            el("p", {
              class: "chapeau",
              style: "margin:10px 0 0",
              texte:
                "Le gain se calcule sur les montants bruts, sans les frais. La plus-value latente, " +
                "elle, se mesure contre le capital net investi, qui est net de frais et réduit au " +
                "prorata des ventes. Les deux sont justes, et ils ne se rejoignent pas.",
            }),
          ])
        ),
      ])
    );

    // --- Les flux datés, qui donnent le TRI ---
    const tableFlux = el("div", { class: "cadre-tableau", style: "--hauteur-tableau:300px" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Date" }),
          el("th", { texte: "Opération" }),
          el("th", { texte: "Poche" }),
          el("th", { class: "num", texte: "Montant" }),
        ])),
        el(
          "tbody",
          {},
          [].concat(
            debut && debut.valeur > 0
              ? [
                  el("tr", {}, [
                    el("td", { texte: dateCourte(debut.date) }),
                    el("td", { texte: "Valeur au début de la période" }),
                    el("td", { texte: "—" }),
                    el("td", { class: "num perte", texte: eurosSignes(-debut.valeur) }),
                  ]),
                ]
              : [],
            c.flux.map(function (f) {
              return el("tr", {}, [
                el("td", { texte: dateCourte(f.date) }),
                el("td", { texte: f.libelle }),
                el("td", { texte: f.poche }),
                el("td", { class: "num " + classe(f.montant), texte: eurosSignes(f.montant) }),
              ]);
            }),
            fin
              ? [
                  el("tr", {}, [
                    el("td", { texte: dateCourte(fin.date) }),
                    el("td", { texte: "Valeur à la fin de la période" }),
                    el("td", { texte: "—" }),
                    el("td", { class: "num gain", texte: eurosSignes(fin.valeur) }),
                  ]),
                ]
              : []
          )
        ),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 3, texte: "Taux qui annule la valeur actuelle nette = TRI" }),
          el("td", { class: "num " + classe(c.tri), texte: tauxEnPourCent(c.tri) }),
        ])),
      ]),
    ]);

    // --- Les sous-périodes, qui donnent le TWRR ---
    const tableSous = el("div", { class: "cadre-tableau", style: "--hauteur-tableau:300px" }, [
      el("table", {}, [
        el("thead", {}, el("tr", {}, [
          el("th", { texte: "Du" }),
          el("th", { texte: "Au" }),
          el("th", { class: "num", texte: "Valeur début" }),
          el("th", { class: "num", texte: "Entrées" }),
          el("th", { class: "num", texte: "Valeur fin" }),
          el("th", { class: "num", texte: "Rendement" }),
        ])),
        el(
          "tbody",
          {},
          c.sousPeriodes.map(function (s) {
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
          })
        ),
        el("tfoot", {}, el("tr", {}, [
          el("td", { colspan: 5, texte: "Produit des rendements, moins un = TWRR" }),
          el("td", { class: "num " + classe(c.twrr), texte: tauxEnPourCent(c.twrr) }),
        ])),
      ]),
    ]);

    page.append(
      el("div", { class: "rangee rangee--deux", style: "margin-top:10px" }, [
        bloc("Les flux datés, qui donnent le TRI", c.flux.length + " opérations", tableFlux),
        bloc("Les sous-périodes, qui donnent le TWRR", c.sousPeriodes.length + " sous-périodes", tableSous),
      ])
    );

    // --- Les estimations, avec leur formule et leur source ---
    const e = D.couts.exemple;
    const formule = el("ul", { class: "liste-parts" }, [
      el("li", {}, [
        el("span", { texte: e.libelle }),
        el("span", { class: "nb", texte: euros(e.montantBrut) }),
      ]),
      el("li", {}, [
        el("span", { texte: "Frais d'ordre réellement prélevés" }),
        el("span", { class: "nb", texte: euros(e.frais) }),
      ]),
      el("li", {}, [
        el("span", { texte: "Poids dans l'opération" }),
        el("span", { class: "nb", texte: tauxEnPourCent(e.poids, false) }),
      ]),
      el("li", {}, [
        el("span", { texte: "Spread estimé : " + e.formuleSpread }),
        el("span", { class: "mot", texte: "Estimé" }),
      ]),
      el("li", {}, [
        el("span", { texte: "Taux employé : " + e.taux + " (" + e.fourchette + ")" }),
        el("span", { class: "reference", texte: e.source }),
      ]),
    ]);

    const hypotheses = el(
      "ul",
      { class: "liste-parts" },
      D.valeurReelle.hypotheses.map(function (h) {
        return el("li", {}, [el("span", { texte: h })]);
      })
    );

    page.append(
      el("div", { class: "rangee rangee--deux", style: "margin-top:10px" }, [
        bloc("Une estimation, de bout en bout", "un exemple", formule),
        bloc("Ce que le calcul d'impôt suppose", D.valeurReelle.hypotheses.length + " hypothèses", hypotheses),
      ])
    );

    page.append(
      el("div", { class: "rangee rangee--large", style: "margin-top:10px" }, [blocSurveiller(false)])
    );

    page.append(
      el("aside", { class: "note-maquette" }, [
        el("h2", { texte: "Une précision sur cette maquette" }),
        el("p", {
          texte:
            "Les trois chiffres clés ci-dessus sont réellement calculés par la maquette, à partir " +
            "de la courbe et des flux affichés : le TRI par dichotomie sur les flux datés, le TWRR " +
            "en chaînant les sous-périodes. Ils changent donc quand tu changes de période ou de " +
            "poche, et ils restent cohérents avec les tables. La différence avec l'application " +
            "finale est que le moteur travaille sur les opérations réelles, au jour près, là où la " +
            "maquette applique une croissance lissée là où le marché, lui, fait ce qu'il veut.",
        }),
      ])
    );

    return page;
  }

  // ==========================================================================
  // 7. L'ASSEMBLAGE
  // ==========================================================================

  const ONGLETS = [
    { cle: "synthese", nom: "Synthèse", dessin: ongletSynthese },
    { cle: "actifs", nom: "Les actifs", dessin: ongletActifs },
    { cle: "diversification", nom: "Diversification", dessin: ongletDiversification },
    { cle: "frais", nom: "Frais et taxes", dessin: ongletFrais },
    { cle: "detail", nom: "Détail des calculs", dessin: ongletDetail },
  ];

  /* La coquille est construite ici, et non écrite dans le HTML, pour qu'il n'existe
   * qu'UNE version du balisage : la page du dépôt et la page publiée en ligne ne
   * peuvent donc pas diverger. */
  function squelette() {
    const onglets = el(
      "div",
      { class: "onglets", role: "tablist" },
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
          dessiner();
        });
        return b;
      })
    );

    const periodes = el(
      "div",
      { class: "groupe" },
      PERIODES.map(function (p) {
        const b = el("button", {
          type: "button",
          "data-periode": p.cle,
          "aria-pressed": String(etat.periode === p.cle),
          texte: p.nom,
        });
        b.addEventListener("click", function () {
          etat.periode = p.cle;
          dessiner();
        });
        return b;
      })
    );

    const poches = el(
      "div",
      { class: "groupe" },
      POCHES.map(function (poche) {
        const b = el("button", {
          type: "button",
          class: "poche-eteinte",
          "data-poche": poche,
          "aria-pressed": String(etat.poches.has(poche)),
          texte: poche,
        });
        b.addEventListener("click", function () {
          if (etat.poches.has(poche)) {
            // On ne décoche jamais la dernière poche : un écran sans aucune poche
            // ne dit rien, et laisse croire à un portefeuille vide.
            if (etat.poches.size > 1) etat.poches.delete(poche);
          } else {
            etat.poches.add(poche);
          }
          dessiner();
        });
        return b;
      })
    );

    const jeux = el(
      "div",
      { class: "groupe" },
      Object.keys(JEUX).map(function (cle) {
        const b = el("button", {
          type: "button",
          "data-jeu": cle,
          "aria-pressed": String(etat.jeu === cle),
          texte: JEUX[cle].nom,
        });
        b.addEventListener("click", function () {
          etat.jeu = cle;
          etat.poches = new Set(POCHES);
          dessiner();
        });
        return b;
      })
    );

    const entete = el("header", { class: "entete" }, [
      el("div", { class: "bande bande--titre" }, [
        el("h1", {
          class: "marque",
          html: "Tableau de bord <span>maquette de l'étape 8</span>",
        }),
        el("div", { class: "pousse" }, [onglets]),
      ]),
      el("div", { class: "bande bande--filtres" }, [
        el("span", { class: "etiquette", texte: "Période" }),
        periodes,
        el("span", { class: "etiquette", texte: "Poches" }),
        poches,
        el("div", { class: "pousse", style: "display:flex; gap:10px; align-items:center" }, [
          el("span", { class: "etiquette", texte: "Jeu fictif" }),
          jeux,
        ]),
      ]),
      el("div", { class: "bande bande--etat", id: "etat" }),
    ]);

    const page = el("main", { class: "page" }, [el("div", { id: "corps" })]);
    (document.getElementById("app") || document.body).append(entete, page);
  }

  function dessiner() {
    const c = contexte();

    // L'état des données : toujours visible, jamais en bas de page.
    const etatBande = document.getElementById("etat");
    etatBande.innerHTML = "";
    etatBande.append(
      el("span", { html: "Cours arrêtés au <b>" + dateCourte(c.arreteAu) + "</b>" }),
      el("span", { texte: "Source : " + c.source }),
      el("span", {
        texte:
          c.debut === null
            ? "Période sans valorisation"
            : "Du " + dateCourte(c.debut) + " au " + dateCourte(c.fin) + " · " + dureeEnClair(c.jours),
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
        : null,
      el("span", { class: "pousse reference", texte: JEUX[etat.jeu].aide })
    );

    const corps = document.getElementById("corps");
    corps.innerHTML = "";
    const onglet = ONGLETS.find(function (o) {
      return o.cle === etat.onglet;
    });
    corps.append(onglet.dessin(c));

    document.querySelectorAll("[data-onglet]").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.dataset.onglet === etat.onglet));
    });
    document.querySelectorAll("[data-periode]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.periode === etat.periode));
    });
    document.querySelectorAll("[data-poche]").forEach(function (b) {
      const presente = c.pochesPresentes.includes(b.dataset.poche);
      b.setAttribute("aria-pressed", String(presente && etat.poches.has(b.dataset.poche)));
      b.disabled = !presente;
      b.title = presente ? "" : "Ce portefeuille n'a pas de " + b.dataset.poche;
    });
    document.querySelectorAll("[data-jeu]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.jeu === etat.jeu));
    });
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
