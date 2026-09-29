/* Portefeuille fictif d'utilisateur type — données des maquettes de l'étape 8.
 *
 * AUCUNE VALEUR RÉELLE (règle 3, D-03). Les ISIN commencent par « XX », qui n'est
 * attribué à aucun pays : ils ne peuvent désigner aucun titre existant. Les émetteurs
 * (Alizé, Boréal, Cardinal) et les sociétés (Nordvent, Kaito Denki, Meridian) sont
 * inventés.
 *
 * Le portefeuille est délibérément PLUS LARGE que celui du propriétaire (D-62) : il
 * contient ce qu'il ne détient pas — deux actions en direct, un ETF obligataire, un ETC
 * sur l'or, un fonds non couvert, une position sans cours.
 *
 * TOUT CE QUI PEUT ÊTRE CALCULÉ L'EST, et chaque ordre appartient à UN actif.
 * C'est ce qui permet d'afficher la variation d'un actif sur la période choisie, et
 * c'est aussi ce qui garantit que la courbe du portefeuille est la somme des courbes de
 * ses lignes. Les deux versions précédentes de cette maquette l'ont appris à leurs
 * dépens : des totaux écrits à la main se contredisaient, et une courbe qui montait
 * indépendamment des flux produisait un TWRR de −126 %.
 *
 * Fichier en .js et non en .json : le .gitignore exclut *.json (règle 1).
 */

window.MAQUETTE = (function () {
  "use strict";

  const FRAIS_PAR_ORDRE = 1.0; // liste des prix : 1 € par ordre
  const DATE_ARRETE = "2026-09-25";
  const DEBUT_COURBE = "2025-03-07"; // une semaine avant le premier achat, à zéro
  const JOURS = 567; // DEBUT_COURBE + 567 jours = DATE_ARRETE
  const POCHES = ["PEA", "CTO", "Crypto"];

  const sou = function (n) {
    return Math.round(n * 100) / 100;
  };

  // ==========================================================================
  // LES POSITIONS
  // valeur = quantité x cours, plus-value latente = valeur − capital net investi.
  // Ce sont les deux vérifications que le propriétaire fera en premier.
  // ==========================================================================

  const lignes = [
    {
      code: "XX0000000011",
      nom: "Boréal Monde Développé PEA UCITS ETF",
      poche: "PEA",
      type: "ETF",
      quantite: 40,
      cours: 34.65,
      capitalNetInvesti: 1300.0,
      synthetique: true,
      ter: 0.25,
    },
    {
      code: "XX0000000012",
      nom: "Alizé Europe 600 UCITS ETF",
      poche: "PEA",
      type: "ETF",
      quantite: 18,
      cours: 26.14,
      capitalNetInvesti: 468.5,
      ter: 0.12,
    },
    {
      code: "XX0000000021",
      nom: "Cardinal Monde Développé UCITS ETF",
      poche: "CTO",
      type: "ETF",
      quantite: 12.4,
      cours: 84.1,
      capitalNetInvesti: 890.0,
      ter: 0.18,
    },
    {
      code: "XX0000000022",
      nom: "Alizé Obligations Euro UCITS ETF",
      poche: "CTO",
      type: "ETF",
      quantite: 5.8,
      cours: 105.59,
      capitalNetInvesti: 570.0,
      contenuDeclare: "obligations",
      ter: 0.1,
    },
    {
      code: "XX0000000023",
      nom: "Boréal Marchés Émergents PEA UCITS ETF",
      poche: "CTO",
      type: "ETF",
      quantite: 21,
      cours: 25.15,
      capitalNetInvesti: 485.0,
      synthetique: true,
      nonCouvert: true,
      ter: 0.3,
    },
    {
      code: "XX0000000031",
      nom: "Nordvent SA",
      poche: "CTO",
      type: "Action",
      quantite: 9,
      cours: 35.4,
      capitalNetInvesti: 285.0,
      pays: "France",
      codePays: "FR",
      secteur: "Industrie",
      regleDePays: "siège social",
      ter: null,
    },
    {
      code: "XX0000000032",
      nom: "Kaito Denki",
      poche: "CTO",
      type: "Action",
      quantite: 15,
      cours: 16.27,
      capitalNetInvesti: 225.0,
      pays: "Japon",
      codePays: "JP",
      secteur: "Technologie",
      regleDePays: "siège social",
      ter: null,
    },
    {
      code: "XX0000000024",
      nom: "Alizé Or Physique ETC",
      poche: "CTO",
      type: "ETF",
      quantite: 5,
      cours: 57.58,
      capitalNetInvesti: 245.0,
      contenuDeclare: "matières premières",
      ter: 0.15,
    },
    {
      code: "XX0000000041",
      nom: "Bitcoin",
      poche: "Crypto",
      type: "Crypto",
      quantite: 0.0061,
      cours: 66028.0,
      capitalNetInvesti: 341.0,
      ter: null,
    },
    {
      code: "XX0000000042",
      nom: "Ethereum",
      poche: "Crypto",
      type: "Crypto",
      quantite: 0.048,
      cours: 3256.25,
      capitalNetInvesti: 153.0,
      ter: null,
    },
    {
      // La position qui rend tous les totaux PARTIELS. Volontaire : c'est l'état le
      // plus difficile à afficher honnêtement, et il doit être visible d'emblée.
      code: "XX0000000033",
      nom: "Meridian Therapeutics",
      poche: "CTO",
      type: "Action",
      quantite: 6,
      cours: null,
      capitalNetInvesti: 94.0,
      ter: null,
      motifSansCours:
        "aucun cours utilisable au 25/09/2026 : la source ne cote plus ce titre depuis le 11/08/2026",
    },
  ];

  const positions = lignes.map(function (l) {
    const valeur = l.cours === null ? null : sou(l.quantite * l.cours);
    return Object.assign({}, l, {
      valeur: valeur,
      plusValueLatente: valeur === null ? null : sou(valeur - l.capitalNetInvesti),
      prixDeRevient: sou(l.capitalNetInvesti / l.quantite),
      terMontant: l.ter === null || valeur === null ? null : sou((valeur * l.ter) / 100),
    });
  });

  const parCode = {};
  for (const p of positions) parCode[p.code] = p;

  // ==========================================================================
  // LES FLUX — un ordre, un actif
  //
  // `montant` est le montant BRUT, du point de vue de l'investisseur : un achat sort de
  // sa poche (négatif), une vente et un dividende y rentrent (positif). C'est lui qui
  // sert au gain et au TRI (D-21 : la performance se calcule sur les montants bruts).
  //
  // `frais` est prélevé en plus. Il ne compte PAS dans la performance : il réduit le
  // capital net investi (D-12), et il est analysé dans l'onglet « Frais et taxes ».
  //
  // `prorata` n'existe que sur une vente : la part du capital net investi qui sort, au
  // prorata des parts vendues — et non le produit de la vente.
  // ==========================================================================

  function achat(date, code, montant) {
    return { date: date, libelle: "Achat", actif: code, montant: -montant, frais: FRAIS_PAR_ORDRE };
  }
  function vente(date, code, montant, prorata) {
    return {
      date: date,
      libelle: "Vente",
      actif: code,
      montant: montant,
      frais: FRAIS_PAR_ORDRE,
      prorata: prorata,
    };
  }
  function dividende(date, code, montant) {
    return { date: date, libelle: "Dividende", actif: code, montant: montant, frais: 0 };
  }

  const flux = [
    achat("2025-03-14", "XX0000000011", 400),
    achat("2025-03-14", "XX0000000012", 200),
    achat("2025-03-14", "XX0000000021", 300),
    achat("2025-03-14", "XX0000000041", 120),

    achat("2025-06-13", "XX0000000012", 150),
    achat("2025-06-13", "XX0000000022", 300),
    achat("2025-06-13", "XX0000000031", 150),
    achat("2025-06-13", "XX0000000042", 80),

    achat("2025-09-05", "XX0000000011", 350),
    achat("2025-09-05", "XX0000000021", 300),
    achat("2025-09-05", "XX0000000023", 250),
    achat("2025-09-05", "XX0000000041", 120),

    achat("2025-11-21", "XX0000000032", 120),
    achat("2025-11-21", "XX0000000024", 130),
    dividende("2025-11-21", "XX0000000021", 18.4),

    achat("2026-01-16", "XX0000000011", 300),
    achat("2026-01-16", "XX0000000012", 150),
    achat("2026-01-16", "XX0000000022", 272),
    achat("2026-01-16", "XX0000000042", 75),

    vente("2026-03-06", "XX0000000012", 186.4, 125.5),

    achat("2026-04-24", "XX0000000012", 98),
    achat("2026-04-24", "XX0000000021", 293),
    achat("2026-04-24", "XX0000000031", 137),
    achat("2026-04-24", "XX0000000041", 104),

    achat("2026-06-12", "XX0000000023", 237),
    achat("2026-06-12", "XX0000000032", 107),
    achat("2026-06-12", "XX0000000033", 95),
    dividende("2026-06-12", "XX0000000022", 26.5),

    achat("2026-07-31", "XX0000000011", 254),
    achat("2026-07-31", "XX0000000024", 117),

    dividende("2026-09-11", "XX0000000031", 18.3),
  ];

  for (const f of flux) f.poche = parCode[f.actif].poche;

  // ==========================================================================
  // LA COURBE
  //
  // Chaque actif a sa propre histoire :
  //  - « base » est la valeur d'acquisition de ce qu'il détient : elle monte du montant
  //    brut à chaque achat, et descend à chaque vente et à chaque dividende, parce que
  //    l'argent quitte alors les actifs. C'est sur elle que la performance s'applique ;
  //  - « investi » est le capital net investi (D-12) : montant brut moins les frais,
  //    réduit au prorata des parts vendues. Il monte EN ESCALIER.
  //
  // La courbe du portefeuille est la SOMME des courbes de ses lignes. Une position sans
  // cours n'entre pas dans la valeur — elle n'a pas de valeur connue — mais son capital
  // entre dans le capital investi. C'est exactement ce que veut dire « partiel » (D-53).
  // ==========================================================================

  const fluxParActif = {};
  for (const f of flux) {
    if (!fluxParActif[f.actif]) fluxParActif[f.actif] = [];
    fluxParActif[f.actif].push(f);
  }

  function cumulsActif(code, date) {
    let base = 0;
    let investi = 0;
    for (const f of fluxParActif[code] || []) {
      if (f.date > date) break;
      base += -f.montant;
      if (f.libelle === "Achat") investi += -f.montant - f.frais;
      else if (f.libelle === "Vente") investi -= f.prorata || 0;
    }
    return { base: sou(base), investi: sou(investi) };
  }

  // La croissance de chaque actif est celle qui fait arriver sa courbe exactement sur
  // sa valeur du jour. Rien n'est ajusté après coup.
  const CROISSANCE = {};
  const AMPLITUDE = { ETF: 1, Action: 1.7, Crypto: 3.2 };
  const PHASE = {};
  positions.forEach(function (p, rang) {
    const base = cumulsActif(p.code, DATE_ARRETE).base;
    CROISSANCE[p.code] = p.valeur !== null && base > 0 ? p.valeur / base - 1 : 0;
    // Une phase par actif, tirée de son rang : déterministe, donc la maquette est
    // identique à chaque ouverture.
    PHASE[p.code] = (rang * 2.39) % 6.283;
  });

  const listeJours = (function () {
    const jours = [];
    const depart = Date.parse(DEBUT_COURBE + "T00:00:00Z");
    for (let i = 0; i <= JOURS; i++) {
      jours.push({
        indice: i,
        date: new Date(depart + i * 86400000).toISOString().slice(0, 10),
      });
    }
    return jours;
  })();

  /** Le facteur de performance d'un actif à une date : sa valeur rapportée à ce qu'il a
   *  coûté. C'est lui qui donne la variation en pour cent, indépendamment des versements. */
  function facteurActif(code, indice) {
    const t = indice / JOURS;
    const p = parCode[code];
    if (!p || p.valeur === null) return null;
    return (
      1 +
      CROISSANCE[code] * t +
      AMPLITUDE[p.type] *
        (0.026 * Math.sin(indice / 37 + PHASE[code]) + 0.014 * Math.sin(indice / 14.7 + PHASE[code]))
    );
  }

  /** La courbe du portefeuille, restreinte à un ensemble de codes d'actifs. */
  function construireCourbe(codes) {
    const retenus = codes || positions.map(function (p) {
      return p.code;
    });
    const points = [];
    for (const jour of listeJours) {
      let valeur = 0;
      let investi = 0;
      for (const code of retenus) {
        const cumuls = cumulsActif(code, jour.date);
        investi += cumuls.investi;
        if (parCode[code].valeur === null || cumuls.base <= 0) continue;
        valeur += Math.max(0, cumuls.base * facteurActif(code, jour.indice));
      }
      points.push({ date: jour.date, valeur: sou(valeur), investi: sou(investi) });
    }
    // Le dernier point est forcé sur les valeurs exactes des positions : la courbe doit
    // finir sur le chiffre affiché en haut de l'écran.
    let valeurFinale = 0;
    let investiFinal = 0;
    for (const code of retenus) {
      if (parCode[code].valeur !== null) valeurFinale += parCode[code].valeur;
      investiFinal += parCode[code].capitalNetInvesti;
    }
    points[points.length - 1] = {
      date: DATE_ARRETE,
      valeur: sou(valeurFinale),
      investi: sou(investiFinal),
    };
    return points;
  }

  const indiceDeDate = {};
  for (const jour of listeJours) indiceDeDate[jour.date] = jour.indice;

  /** La variation d'un actif entre deux dates, hors versements : c'est la performance
   *  de l'actif lui-même, pas celle de l'argent qu'on y a mis. Rend `null` quand l'actif
   *  n'était pas encore détenu au début. */
  function variationActif(code, debut, fin) {
    const p = parCode[code];
    if (!p || p.valeur === null) return null;
    const iDebut = indiceDeDate[debut];
    const iFin = indiceDeDate[fin];
    if (iDebut === undefined || iFin === undefined) return null;
    // On part du premier jour où l'actif est détenu, si l'achat est postérieur au début
    // de la période : sinon on annoncerait une variation depuis un capital nul.
    let depart = iDebut;
    while (depart <= iFin && cumulsActif(code, listeJours[depart].date).base <= 0) depart++;
    if (depart > iFin) return null;
    const f1 = facteurActif(code, depart);
    const f2 = facteurActif(code, iFin);
    if (!f1 || !f2) return null;
    return {
      taux: f2 / f1 - 1,
      depuisLAchat: depart > iDebut,
      depuis: listeJours[depart].date,
    };
  }

  // ==========================================================================
  // LES TOTAUX
  // ==========================================================================

  function totaliser(filtre) {
    let valeur = 0;
    let capital = 0;
    let latente = 0;
    for (const p of positions) {
      if (filtre && !filtre(p)) continue;
      capital += p.capitalNetInvesti;
      if (p.valeur !== null) {
        valeur += p.valeur;
        latente += p.plusValueLatente;
      }
    }
    return { valeur: sou(valeur), capital: sou(capital), latente: sou(latente) };
  }

  const TOTAL = totaliser(null);
  const PAR_POCHE = {};
  for (const poche of POCHES) {
    PAR_POCHE[poche] = totaliser(function (p) {
      return p.poche === poche;
    });
  }

  function sommeFlux(filtre) {
    let brut = 0;
    let frais = 0;
    for (const f of flux) {
      if (filtre && !filtre(f)) continue;
      brut += f.montant;
      frais += f.frais || 0;
    }
    return { brut: sou(brut), frais: sou(frais) };
  }

  const synthese = {
    arreteAu: DATE_ARRETE,
    sourceDesCours: "Yahoo Finance",
    valeurTotale: TOTAL.valeur,
    capitalNetInvesti: TOTAL.capital,
    plusValueLatente: TOTAL.latente,
    achatsBruts: sou(-sommeFlux(function (f) { return f.libelle === "Achat"; }).brut),
    ventesBrutes: sommeFlux(function (f) { return f.libelle === "Vente"; }).brut,
    dividendesBruts: sommeFlux(function (f) { return f.libelle === "Dividende"; }).brut,
    fraisPayes: sommeFlux(null).frais,
    // Retenue à la source sur les dividendes, à part des frais d'ordre.
    taxesPayees: 7.58,
    nombreOrdres: flux.filter(function (f) {
      return f.libelle !== "Dividende";
    }).length,
    parPoche: POCHES.map(function (poche) {
      return {
        poche: poche,
        valeur: PAR_POCHE[poche].valeur,
        capitalNetInvesti: PAR_POCHE[poche].capital,
        plusValueLatente: PAR_POCHE[poche].latente,
      };
    }),
  };

  // ==========================================================================
  // LA DIVERSIFICATION
  // Les montants sont écrits ; les pourcentages sont CALCULÉS sur la base, qui est la
  // valeur totale des actifs valorisés. Jamais sur la somme des parts attribuées : ce
  // serait renormaliser (D-69).
  // ==========================================================================

  const BASE = TOTAL.valeur;

  function enPourCent(liste) {
    return liste.map(function (p) {
      return Object.assign({}, p, { pourCent: sou((p.montant * 100) / BASE) });
    });
  }

  const NON_ATTRIBUE = 13.89; // liquidités des fonds, dérivés, lignes non classées
  const NON_COUVERT = parCode["XX0000000023"].valeur;
  const OBLIGATIONS = parCode["XX0000000022"].valeur;
  const MATIERES = parCode["XX0000000024"].valeur;
  const NUMERIQUES = PAR_POCHE.Crypto.valeur;
  // Les actions sont ce qui reste : tout est donc attribué, et le total fait la base.
  const ACTIONS = sou(BASE - NON_ATTRIBUE - NON_COUVERT - OBLIGATIONS - MATIERES - NUMERIQUES);

  const RESTES_GEO = [
    { libelle: "Non attribué par les fonds", montant: NON_ATTRIBUE, mot: "non-attribue" },
    { libelle: "Obligations", montant: OBLIGATIONS, mot: "hors-actions", icone: "obligations" },
    { libelle: "Matières premières", montant: MATIERES, mot: "hors-actions", icone: "matieres" },
    { libelle: "Actifs numériques", montant: NUMERIQUES, mot: "hors-classification", icone: "numeriques" },
    { libelle: "Non couvert", montant: NON_COUVERT, mot: "non-couvert" },
  ];

  // Tous les pays qui pèsent au moins 0,5 % du portefeuille sont nommés. En dessous,
  // ils sont regroupés — mais le regroupement dit combien ils sont, et il reste visible
  // à sa vraie taille.
  const SEUIL_PAYS = 0.5; // en pour cent de la base
  const PAYS_TETE = [
    { libelle: "États-Unis", code: "US", zone: "Amérique du Nord", montant: 2043.8, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Japon", code: "JP", zone: "Japon", montant: 421.36, source: "extraETF", regle: "pays d'activité" },
    { libelle: "France", code: "FR", zone: "Europe", montant: 268.94, source: "extraETF + GLEIF", regle: "mixte" },
    { libelle: "Royaume-Uni", code: "GB", zone: "Europe", montant: 152.6, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Allemagne", code: "DE", zone: "Europe", montant: 138.22, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Canada", code: "CA", zone: "Amérique du Nord", montant: 96.4, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Suisse", code: "CH", zone: "Europe", montant: 84.15, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Pays-Bas", code: "NL", zone: "Europe", montant: 71.3, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Australie", code: "AU", zone: "Asie-Pacifique développée", montant: 38.4, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Taïwan", code: "TW", zone: "Marchés émergents", montant: 34.2, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Suède", code: "SE", zone: "Europe", montant: 28.6, source: "extraETF", regle: "pays d'activité" },
  ];

  // Ce qui reste est le RELIQUAT des pays trop petits pour être nommés. Il est calculé,
  // pas écrit : la somme des pays doit faire exactement la part investie en actions,
  // sinon la répartition ne se recoupe plus.
  const AUTRES_PAYS = sou(
    ACTIONS -
      PAYS_TETE.reduce(function (s, p) {
        return s + p.montant;
      }, 0)
  );
  // Il se répartit entre trois zones ; la dernière absorbe l'arrondi.
  const AUTRES_PAR_ZONE = { Europe: 24.0, "Asie-Pacifique développée": 18.15 };
  AUTRES_PAR_ZONE["Marchés émergents"] = sou(
    AUTRES_PAYS - AUTRES_PAR_ZONE.Europe - AUTRES_PAR_ZONE["Asie-Pacifique développée"]
  );

  const PAYS = PAYS_TETE.concat([
    {
      libelle: "Autres pays (15), chacun sous " + SEUIL_PAYS.toFixed(1).replace(".", ",") + " %",
      code: null,
      zone: "—",
      montant: AUTRES_PAYS,
      source: "extraETF",
      regle: "pays d'activité",
    },
  ]);

  const ZONES = [
    "Amérique du Nord",
    "Europe",
    "Japon",
    "Asie-Pacifique développée",
    "Marchés émergents",
  ].map(function (zone) {
    let montant = AUTRES_PAR_ZONE[zone] || 0;
    for (const p of PAYS_TETE) if (p.zone === zone) montant += p.montant;
    // Une zone n'a pas de drapeau : il n'en existe pas pour l'Amérique du Nord ni pour
    // l'Asie-Pacifique. Elles portent donc TOUTES le même pictogramme — ou aucune
    // n'en porterait. Un seul drapeau au milieu de libellés nus était le vrai défaut.
    return { libelle: zone, icone: "zone", montant: sou(montant) };
  });

  // Les 11 secteurs Morningstar. Le dernier absorbe l'arrondi.
  const SECTEURS_TETE = [
    { libelle: "Technologie", icone: "technologie", montant: 823.4 },
    { libelle: "Services financiers", icone: "finance", montant: 574.1 },
    { libelle: "Santé", icone: "sante", montant: 421.85 },
    { libelle: "Consommation cyclique", icone: "cyclique", montant: 372.6 },
    { libelle: "Industrie", icone: "industrie", montant: 358.9 },
    { libelle: "Services de communication", icone: "communication", montant: 289.45 },
    { libelle: "Consommation défensive", icone: "defensive", montant: 241.3 },
    { libelle: "Énergie", icone: "energie", montant: 152.7 },
    { libelle: "Services aux collectivités", icone: "collectivites", montant: 98.4 },
    { libelle: "Immobilier", icone: "immobilier", montant: 78.25 },
  ];
  const SECTEURS = SECTEURS_TETE.concat([
    {
      libelle: "Matériaux de base",
      icone: "materiaux",
      montant: sou(
        ACTIONS - SECTEURS_TETE.reduce(function (s, p) { return s + p.montant; }, 0)
      ),
    },
  ]);

  const diversification = {
    base: BASE,
    arreteDu: "2026-07-31",
    arreteAu: "2026-08-31",
    sources: ["extraETF", "GLEIF"],
    nomenclature: "Morningstar, 11 secteurs",
    classes: {
      postes: enPourCent([
        { libelle: "Actions", icone: "actions", montant: ACTIONS },
        { libelle: "Obligations", icone: "obligations", montant: OBLIGATIONS },
        { libelle: "Matières premières", icone: "matieres", montant: MATIERES },
        { libelle: "Actifs numériques", icone: "numeriques", montant: NUMERIQUES },
      ]),
      restes: enPourCent([
        { libelle: "Non attribué par les fonds", montant: NON_ATTRIBUE, mot: "non-attribue" },
        { libelle: "Non couvert", montant: NON_COUVERT, mot: "non-couvert" },
      ]),
    },
    pays: {
      regleDominante: "pays d'activité",
      postes: enPourCent(PAYS),
      zones: enPourCent(ZONES),
      restes: enPourCent(RESTES_GEO),
    },
    secteurs: {
      postes: enPourCent(SECTEURS),
      restes: enPourCent(RESTES_GEO),
    },
    actifsNonCouverts: [
      {
        nom: parCode["XX0000000023"].nom,
        montant: NON_COUVERT,
        motif: "la source ne publie aucune répartition pour cet ISIN",
      },
    ],
    actifsSynthetiques: positions.filter(function (p) { return p.synthetique; }).map(function (p) { return p.nom; }),
    declareesALaMain: positions.filter(function (p) { return p.contenuDeclare; }).map(function (p) { return p.nom; }),
  };

  // ==========================================================================
  // LES COÛTS ET LA VALEUR RÉELLE
  // ==========================================================================

  // Les spreads par côté, par type d'actif (D-56), avec leur fourchette mesurée.
  const SPREAD = { ETF: 0.05, Action: 0.1, Crypto: 0.5 };
  const FOURCHETTE = {
    ETF: "entre 0,02 % et 0,09 %",
    Action: "entre 0,04 % et 0,21 %",
    Crypto: "entre 0,20 % et 1,10 %",
  };

  function spreadDe(position) {
    const taux = SPREAD[position.type];
    if (!taux || position.valeur === null) return 0;
    return sou((position.valeur * taux) / 100);
  }

  const spreadSortie = sou(
    positions.reduce(function (s, p) {
      return s + spreadDe(p);
    }, 0)
  );
  const spreadEntree = sou(
    flux.reduce(function (s, f) {
      if (f.libelle !== "Achat") return s;
      const taux = SPREAD[parCode[f.actif].type] || 0;
      return s + (-f.montant * taux) / 100;
    }, 0)
  );

  const couts = {
    fraisPayes: synthese.fraisPayes,
    taxesPayees: synthese.taxesPayees,
    coutPaye: sou(synthese.fraisPayes + synthese.taxesPayees),
    nombreOrdres: synthese.nombreOrdres,
    // ATTENTION : des TAUX (0,0035 pour 0,35 %), jamais des pour cent, et surtout pas
    // arrondis au centime — ils tomberaient à zéro.
    poidsMoyen: synthese.fraisPayes / (synthese.achatsBruts + synthese.ventesBrutes),
    spreadEstimeEntree: spreadEntree,
    // Le taux moyen, pondéré par ce qui a été acheté : c'est lui qui se compare à un
    // taux publié, là où le montant en euros dépend de la taille du portefeuille.
    tauxSpreadEntree: spreadEntree / synthese.achatsBruts,
    spreadEstimeSortie: spreadSortie,
    tauxSpreadSortie: spreadSortie / TOTAL.valeur,
    terAnnuel: sou(
      positions.reduce(function (s, p) {
        return s + (p.terMontant || 0);
      }, 0)
    ),
    tauxTerMoyen:
      positions.reduce(function (s, p) {
        return s + (p.terMontant || 0);
      }, 0) / TOTAL.valeur,
    spreads: SPREAD,
    fourchettes: FOURCHETTE,
    exemple: {
      libelle: "Achat du 16/01/2026 · Alizé Obligations Euro UCITS ETF",
      montantBrut: 272.0,
      frais: FRAIS_PAR_ORDRE,
      poids: FRAIS_PAR_ORDRE / 272.0,
      formuleSpread: "272,00 x 0,05 % = 0,14",
      taux: "0,05 %",
      fourchette: FOURCHETTE.ETF,
      source: "relevés Xetra, vérifié le 27/09/2026",
    },
  };

  // --- La valeur réelle : ce qu'on récupérerait en vendant tout aujourd'hui ---

  const TAUX_IMPOT = 31.4; // IR et prélèvements sociaux réunis, en pour cent
  const REGLE_PAR_POCHE = {
    // Un PEA de MOINS de cinq ans est imposé comme un compte-titres : afficher zéro
    // d'impôt sur lui était une erreur, et elle rendait la valeur réelle trop flatteuse.
    // Ce qui reste particulier, c'est que le gain du plan ne peut pas être calculé depuis
    // les seuls titres : il est approché, donc l'estimation est marquée minorée (D-59).
    PEA: "plan de moins de cinq ans, imposé comme un compte-titres ; le gain du plan est approché depuis les titres",
    CTO: "prélèvement forfaitaire unique sur les seules plus-values latentes",
    Crypto: "prélèvement forfaitaire unique, seuil de cession de 305 € dépassé",
  };

  const valeurReellePoches = POCHES.map(function (poche) {
    const detenues = positions.filter(function (p) {
      return p.poche === poche && p.valeur !== null;
    });
    const fraisDeVente = sou(detenues.length * FRAIS_PAR_ORDRE);
    const spread = sou(detenues.reduce(function (s, p) { return s + spreadDe(p); }, 0));
    const brute = PAR_POCHE[poche].valeur;
    // La base imposable : les plus-values latentes compensées, plancher à zéro (D-60).
    // Les frais et le spread de sortie viennent en déduction, puisqu'ils réduisent le
    // produit de la cession.
    const baseImposable = sou(
      Math.max(
        0,
        detenues.reduce(function (s, p) {
          return s + p.plusValueLatente;
        }, 0) -
          fraisDeVente -
          spread
      )
    );
    // Toutes les poches portent le même taux ici. Ce qui les distingue est la RÈGLE
    // qui définit la base, pas le taux — et un PEA de moins de cinq ans n'est pas exonéré.
    const impot = sou((baseImposable * TAUX_IMPOT) / 100);
    return {
      poche: poche,
      valeurBrute: brute,
      fraisDeVente: fraisDeVente,
      spread: spread,
      baseImposable: baseImposable,
      tauxImpot: TAUX_IMPOT,
      impot: impot,
      valeurReelle: sou(brute - fraisDeVente - spread - impot),
      regle: REGLE_PAR_POCHE[poche],
      minoree: poche === "PEA",
    };
  });

  function sommePoches(champ) {
    return sou(
      valeurReellePoches.reduce(function (s, p) {
        return s + p[champ];
      }, 0)
    );
  }

  const valeurReelle = {
    valeurBrute: sommePoches("valeurBrute"),
    fraisDeVente: sommePoches("fraisDeVente"),
    spreadDeSortie: sommePoches("spread"),
    baseImposable: sommePoches("baseImposable"),
    impot: sommePoches("impot"),
    valeurReelle: sommePoches("valeurReelle"),
    tauxImpot: TAUX_IMPOT,
    minoree: true,
    partielle: true,
    parPoche: valeurReellePoches,
    hypotheses: [
      "Tous les titres sont supposés vendus le même jour, au dernier cours connu.",
      "Les plus-values déjà réalisées cette année et les dividendes déjà reçus ne sont pas comptés.",
      "L'impôt du PEA est approché depuis les titres, sur une date de premier versement déclarée.",
      "Les frais de vente sont ceux de la liste des prix : un euro par ordre.",
    ],
    exclues: positions
      .filter(function (p) {
        return p.valeur === null;
      })
      .map(function (p) {
        return { nom: p.nom, motif: "sans cours (D-53)", capital: p.capitalNetInvesti };
      }),
  };

  // ==========================================================================
  // CE QUE LE MOTEUR SIGNALE
  // ==========================================================================

  const aSurveiller = [
    {
      categorie: "prix à compléter",
      message:
        "Un achat du 13/06/2025 sur Nordvent SA est arrivé sans son montant : le prix de revient de cette ligne est incomplet.",
      reference: "evt-2025-06-13-0043",
    },
    {
      categorie: "poche non couverte",
      message:
        "La banque ne renvoie les positions que d'un seul compte-titres : les quantités du PEA ne sont donc pas confirmées par une seconde source.",
      reference: null,
    },
    {
      categorie: "composition refusée",
      message:
        "Boréal Marchés Émergents PEA UCITS ETF : la source a répondu, mais en rangeant 100 % du fonds dans « autres ». La réponse est refusée plutôt que d'afficher un chiffre faux.",
      reference: "XX0000000023",
    },
    {
      categorie: "cours indisponible",
      message:
        "Meridian Therapeutics n'est plus coté par la source depuis le 11/08/2026. La position est exclue des totaux, qui sont marqués partiels.",
      reference: "XX0000000033",
    },
  ];

  return {
    positions: positions,
    parCode: parCode,
    poches: POCHES,
    synthese: synthese,
    flux: flux,
    construireCourbe: construireCourbe,
    variationActif: variationActif,
    dateArrete: DATE_ARRETE,
    debutCourbe: DEBUT_COURBE,
    diversification: diversification,
    couts: couts,
    valeurReelle: valeurReelle,
    aSurveiller: aSurveiller,
    parPoche: PAR_POCHE,
    total: TOTAL,
  };
})();
