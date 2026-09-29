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
 * Les chiffres se recoupent. Chaque total est la somme de ses lignes, et les
 * commentaires « = » donnent le calcul pour qu'il soit refaisable à la main.
 *
 * Fichier en .js et non en .json : le .gitignore exclut *.json (règle 1).
 */

window.MAQUETTE = (function () {
  "use strict";

  // --- Le jeu complet -----------------------------------------------------------

  const positions = [
    {
      code: "XX0000000011",
      nom: "Boréal Monde Développé PEA UCITS ETF",
      poche: "PEA",
      type: "ETF",
      quantite: "42,3180",
      prixDeRevient: "28,40",
      capitalNetInvesti: 1201.83,
      cours: "32,73",
      dateCours: "2026-09-25",
      place: "Euronext Paris",
      valeur: 1385.23,
      plusValueLatente: 183.4,
      tri: 0.146,
      twrr: 0.131,
      synthetique: true,
      ter: "0,25",
      terMontant: 3.46,
    },
    {
      code: "XX0000000012",
      nom: "Alizé Europe 600 UCITS ETF",
      poche: "PEA",
      type: "ETF",
      quantite: "18,0000",
      prixDeRevient: "24,10",
      capitalNetInvesti: 433.8,
      cours: "26,14",
      dateCours: "2026-09-25",
      place: "Euronext Paris",
      valeur: 470.52,
      plusValueLatente: 36.72,
      tri: 0.081,
      twrr: 0.078,
      ter: "0,12",
      terMontant: 0.56,
    },
    {
      code: "XX0000000021",
      nom: "Cardinal Monde Développé UCITS ETF",
      poche: "CTO",
      type: "ETF",
      quantite: "12,4000",
      prixDeRevient: "76,20",
      capitalNetInvesti: 944.88,
      cours: "84,10",
      dateCours: "2026-09-25",
      place: "Xetra",
      valeur: 1042.8,
      plusValueLatente: 97.92,
      tri: 0.112,
      twrr: 0.104,
      ter: "0,18",
      terMontant: 1.88,
    },
    {
      code: "XX0000000022",
      nom: "Alizé Obligations Euro UCITS ETF",
      poche: "CTO",
      type: "ETF",
      contenuDeclare: "obligations",
      quantite: "5,8000",
      prixDeRevient: "104,90",
      capitalNetInvesti: 608.42,
      cours: "105,59",
      dateCours: "2026-09-25",
      place: "Xetra",
      valeur: 612.4,
      plusValueLatente: 3.98,
      tri: 0.009,
      twrr: 0.009,
      ter: "0,10",
      terMontant: 0.61,
    },
    {
      code: "XX0000000023",
      nom: "Boréal Marchés Émergents PEA UCITS ETF",
      poche: "CTO",
      type: "ETF",
      quantite: "21,0000",
      prixDeRevient: "24,55",
      capitalNetInvesti: 515.55,
      cours: "25,15",
      dateCours: "2026-09-25",
      place: "Euronext Paris",
      valeur: 528.15,
      plusValueLatente: 12.6,
      tri: 0.031,
      twrr: 0.03,
      synthetique: true,
      nonCouvert: true,
      ter: "0,30",
      terMontant: 1.58,
    },
    {
      code: "XX0000000031",
      nom: "Nordvent SA",
      poche: "CTO",
      type: "Action",
      quantite: "9,0000",
      prixDeRevient: "32,80",
      capitalNetInvesti: 295.2,
      cours: "35,40",
      dateCours: "2026-09-25",
      place: "Euronext Paris",
      valeur: 318.6,
      plusValueLatente: 23.4,
      tri: 0.094,
      twrr: 0.088,
      pays: "France",
      secteur: "Industrie",
      regleDePays: "siège social",
      ter: null,
    },
    {
      code: "XX0000000032",
      nom: "Kaito Denki",
      poche: "CTO",
      type: "Action",
      quantite: "15,0000",
      prixDeRevient: "15,10",
      capitalNetInvesti: 226.5,
      cours: "16,27",
      dateCours: "2026-09-25",
      place: "Xetra",
      valeur: 244.05,
      plusValueLatente: 17.55,
      tri: 0.086,
      twrr: 0.081,
      pays: "Japon",
      secteur: "Technologie",
      regleDePays: "siège social",
      ter: null,
    },
    {
      code: "XX0000000024",
      nom: "Alizé Or Physique ETC",
      poche: "CTO",
      type: "ETF",
      contenuDeclare: "matières premières",
      quantite: "5,0000",
      prixDeRevient: "52,30",
      capitalNetInvesti: 261.5,
      cours: "57,58",
      dateCours: "2026-09-25",
      place: "Xetra",
      valeur: 287.9,
      plusValueLatente: 26.4,
      tri: 0.118,
      twrr: 0.109,
      ter: "0,15",
      terMontant: 0.43,
    },
    {
      code: "XX0000000041",
      nom: "Bitcoin",
      poche: "Crypto",
      type: "Crypto",
      quantite: "0,0061",
      prixDeRevient: "52 180,00",
      capitalNetInvesti: 318.3,
      cours: "66 028,00",
      dateCours: "2026-09-25",
      place: "Trade Republic",
      valeur: 402.77,
      plusValueLatente: 84.47,
      tri: 0.312,
      twrr: 0.265,
      ter: null,
    },
    {
      code: "XX0000000042",
      nom: "Ethereum",
      poche: "Crypto",
      type: "Crypto",
      quantite: "0,0480",
      prixDeRevient: "2 940,00",
      capitalNetInvesti: 141.12,
      cours: "3 256,25",
      dateCours: "2026-09-25",
      place: "Trade Republic",
      valeur: 156.3,
      plusValueLatente: 15.18,
      tri: 0.204,
      twrr: 0.188,
      ter: null,
    },
    {
      // La position qui rend tous les totaux PARTIELS. Volontaire : c'est l'état le
      // plus difficile à afficher honnêtement, et il doit être visible d'emblée.
      code: "XX0000000033",
      nom: "Meridian Therapeutics",
      poche: "CTO",
      type: "Action",
      quantite: "6,0000",
      prixDeRevient: "18,90",
      capitalNetInvesti: 113.4,
      cours: null,
      dateCours: null,
      place: null,
      valeur: null,
      motifSansCours:
        "aucun cours utilisable au 2026-09-25 : la source ne cote plus ce titre depuis le 2026-08-11",
      ter: null,
    },
  ];

  // valeur totale = 1385,23 + 470,52 + 1042,80 + 612,40 + 528,15
  //               + 318,60 + 244,05 + 287,90 + 402,77 + 156,30 = 5 448,72
  const VALEUR_TOTALE = 5448.72;

  // capital net investi = 5 186,00 d'achats nets de frais − 125,50 retirés au prorata
  //                       des ventes = 5 060,50. C'est aussi la somme de la colonne
  //                       « capital net investi » des onze lignes, ligne sans cours comprise.
  const CAPITAL_NET_INVESTI = 5060.5;

  // gain = valeur finale − valeur initiale + somme des flux BRUTS (D-21)
  //      = 5 448,72 − 0,00 + (−5 200,00 d'achats + 186,40 de ventes + 63,20 de dividendes)
  //      = 498,32
  //
  // ATTENTION, et c'est une information à afficher, pas un défaut : le gain n'est PAS la
  // somme de la colonne « +/− latente » (501,62). Les deux ne se rejoignent pas, parce que
  // le gain se calcule sur les montants BRUTS (D-21) tandis que le capital net investi est
  // net de frais et réduit au prorata des ventes (D-12). L'écran doit donc donner la
  // formule du gain, et ne jamais laisser croire qu'on l'obtient en additionnant une colonne.
  const GAIN = 498.32;
  const PLUS_VALUE_LATENTE = 501.62; // 5 448,72 − 4 947,10 (capital des lignes valorisées)

  const synthese = {
    arreteAu: "2026-09-25",
    sourceDesCours: "Yahoo Finance",
    debut: "2025-03-14",
    dureeEnClair: "1 an et 6 mois",
    gain: GAIN,
    tri: 0.114,
    twrr: 0.098,
    twrrAnnualise: 0.086,
    peuSignificatif: false,
    valeurTotale: VALEUR_TOTALE,
    capitalNetInvesti: CAPITAL_NET_INVESTI,
    partiel: true,
    nonValorisees: ["Meridian Therapeutics"],
    achatsBruts: 5200.0,
    ventesBrutes: 186.4,
    dividendesBruts: 63.2,
    fraisPayes: 14.0,
    taxesPayees: 7.58,
    plusValueLatente: PLUS_VALUE_LATENTE,
    formuleGain:
      "5 448,72 − 5 200,00 d'achats + 186,40 de ventes + 63,20 de dividendes = 498,32",
    // Par poche : valeur, capital et plus-value latente, qui eux s'additionnent.
    // 1 635,63 + 2 965,45 + 459,42 = 5 060,50   ·   220,12 + 181,85 + 99,65 = 501,62
    parPoche: [
      { poche: "PEA", valeur: 1855.75, capitalNetInvesti: 1635.63, plusValueLatente: 220.12 },
      { poche: "CTO", valeur: 3033.9, capitalNetInvesti: 2965.45, plusValueLatente: 181.85 },
      { poche: "Crypto", valeur: 559.07, capitalNetInvesti: 459.42, plusValueLatente: 99.65 },
    ],
  };

  // --- La courbe : capital brut et capital net investi ---------------------------
  // Une valeur par semaine du 2025-03-14 au 2026-09-25, construite pour finir
  // exactement sur VALEUR_TOTALE et CAPITAL_NET_INVESTI. Le capital net investi
  // monte EN ESCALIER (il ne bouge qu'aux achats), la valeur ondule autour.

  function courbe() {
    const points = [];
    const depart = new Date("2025-03-14T00:00:00Z");
    const semaines = 80;
    // Ondulation déterministe : deux sinusoïdes déphasées, pas d'aléatoire, pour que
    // la maquette soit identique à chaque ouverture.
    for (let i = 0; i <= semaines; i++) {
      const jour = new Date(depart.getTime() + i * 7 * 86400000);
      const t = i / semaines;
      const investi = CAPITAL_NET_INVESTI * Math.min(1, t * 1.12);
      const tendance = investi * (1 + 0.118 * t);
      const houle =
        investi * (0.052 * Math.sin(i / 5.3) + 0.028 * Math.sin(i / 2.1 + 1.4));
      points.push({
        date: jour.toISOString().slice(0, 10),
        investi: Math.round(investi * 100) / 100,
        valeur: Math.round((tendance + houle) * 100) / 100,
      });
    }
    // On force le dernier point sur les vraies valeurs : la courbe doit finir sur le
    // chiffre affiché en haut de l'écran, sans quoi la maquette mentirait.
    points[points.length - 1] = {
      date: "2026-09-25",
      investi: CAPITAL_NET_INVESTI,
      valeur: VALEUR_TOTALE,
    };
    return points;
  }

  // --- Diversification ------------------------------------------------------------
  // Base de tous les pourcentages = VALEUR_TOTALE (5 448,72). Jamais la somme des
  // parts attribuées : ce serait renormaliser (D-69).

  const diversification = {
    base: VALEUR_TOTALE,
    arreteDu: "2026-07-31",
    arreteAu: "2026-08-31",
    sources: ["extraETF", "GLEIF"],
    nomenclature: "Morningstar, 11 secteurs",

    // 3 447,31 + 612,40 + 287,90 + 559,07 + 13,89 + 528,15 = 5 448,72
    classes: {
      postes: [
        { libelle: "Actions", montant: 3447.31, pourCent: 63.27 },
        { libelle: "Obligations", montant: 612.4, pourCent: 11.24 },
        { libelle: "Matières premières", montant: 287.9, pourCent: 5.28 },
        { libelle: "Actifs numériques", montant: 559.07, pourCent: 10.26 },
      ],
      restes: [
        { libelle: "Non attribué", montant: 13.89, pourCent: 0.25, mot: "non-attribue" },
        { libelle: "Non couvert", montant: 528.15, pourCent: 9.69, mot: "non-couvert" },
      ],
    },

    // 3 447,31 attribués + 13,89 non attribués + 900,30 hors actions
    //          + 559,07 numériques + 528,15 non couverts = 5 448,72
    pays: {
      regleDominante: "pays d'activité",
      postes: [
        { libelle: "États-Unis", zone: "Amérique du Nord", montant: 2043.8, pourCent: 37.51, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Japon", zone: "Japon", montant: 421.36, pourCent: 7.73, source: "extraETF", regle: "pays d'activité" },
        { libelle: "France", zone: "Europe", montant: 268.94, pourCent: 4.94, source: "extraETF + GLEIF", regle: "mixte" },
        { libelle: "Royaume-Uni", zone: "Europe", montant: 152.6, pourCent: 2.8, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Allemagne", zone: "Europe", montant: 138.22, pourCent: 2.54, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Canada", zone: "Amérique du Nord", montant: 96.4, pourCent: 1.77, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Suisse", zone: "Europe", montant: 84.15, pourCent: 1.54, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Pays-Bas", zone: "Europe", montant: 71.3, pourCent: 1.31, source: "extraETF", regle: "pays d'activité" },
        { libelle: "Autres pays (18)", zone: "—", montant: 170.54, pourCent: 3.13, source: "extraETF", regle: "pays d'activité" },
      ],
      zones: [
        { libelle: "Amérique du Nord", montant: 2140.2, pourCent: 39.28 },
        { libelle: "Europe", montant: 777.51, pourCent: 14.27 },
        { libelle: "Japon", montant: 421.36, pourCent: 7.73 },
        { libelle: "Asie-Pacifique développée", montant: 54.2, pourCent: 0.99 },
        { libelle: "Marchés émergents", montant: 54.04, pourCent: 0.99 },
      ],
      restes: [
        { libelle: "Non attribué par les fonds", montant: 13.89, pourCent: 0.25, mot: "non-attribue" },
        { libelle: "Obligations", montant: 612.4, pourCent: 11.24, mot: "hors-actions" },
        { libelle: "Matières premières", montant: 287.9, pourCent: 5.28, mot: "hors-actions" },
        { libelle: "Actifs numériques", montant: 559.07, pourCent: 10.26, mot: "hors-classification" },
        { libelle: "Non couvert", montant: 528.15, pourCent: 9.69, mot: "non-couvert" },
      ],
    },

    secteurs: {
      postes: [
        { libelle: "Technologie", montant: 823.4, pourCent: 15.11 },
        { libelle: "Services financiers", montant: 574.1, pourCent: 10.54 },
        { libelle: "Santé", montant: 421.85, pourCent: 7.74 },
        { libelle: "Consommation cyclique", montant: 372.6, pourCent: 6.84 },
        { libelle: "Industrie", montant: 358.9, pourCent: 6.59 },
        { libelle: "Services de communication", montant: 289.45, pourCent: 5.31 },
        { libelle: "Consommation défensive", montant: 241.3, pourCent: 4.43 },
        { libelle: "Énergie", montant: 152.7, pourCent: 2.8 },
        { libelle: "Services aux collectivités", montant: 98.4, pourCent: 1.81 },
        { libelle: "Immobilier", montant: 78.25, pourCent: 1.44 },
        { libelle: "Matériaux de base", montant: 36.36, pourCent: 0.67 },
      ],
      restes: [
        { libelle: "Non attribué par les fonds", montant: 13.89, pourCent: 0.25, mot: "non-attribue" },
        { libelle: "Obligations", montant: 612.4, pourCent: 11.24, mot: "hors-actions" },
        { libelle: "Matières premières", montant: 287.9, pourCent: 5.28, mot: "hors-actions" },
        { libelle: "Actifs numériques", montant: 559.07, pourCent: 10.26, mot: "hors-classification" },
        { libelle: "Non couvert", montant: 528.15, pourCent: 9.69, mot: "non-couvert" },
      ],
    },

    actifsNonCouverts: [
      {
        nom: "Boréal Marchés Émergents PEA UCITS ETF",
        montant: 528.15,
        motif: "la source ne publie aucune répartition pour cet ISIN",
      },
    ],
    actifsSynthetiques: [
      "Boréal Monde Développé PEA UCITS ETF",
      "Boréal Marchés Émergents PEA UCITS ETF",
    ],
    declareesALaMain: ["Alizé Obligations Euro UCITS ETF", "Alizé Or Physique ETC"],
  };

  // --- Frais, taxes et valeur réelle ----------------------------------------------

  const couts = {
    fraisPayes: 14.0,
    taxesPayees: 7.58,
    coutPaye: 21.58, // 14,00 + 7,58
    nombreOrdres: 14,
    poidsMoyen: 0.0027,
    spreadEstimeEntree: 3.42,
    terAnnuel: 8.52, // 3,46 + 0,56 + 1,88 + 0,61 + 1,58 + 0,43
    sansTer: ["Nordvent SA", "Kaito Denki", "Meridian Therapeutics", "Bitcoin", "Ethereum"],
    exemple: {
      libelle: "Achat du 2025-04-03 · Cardinal Monde Développé UCITS ETF",
      montantBrut: 600.0,
      frais: 1.0,
      poids: 0.0017,
      formuleSpread: "600,00 x 0,05 % = 0,30",
      taux: "0,05 %",
      fourchette: "entre 0,02 % et 0,09 %",
      source: "relevés Xetra, vérifié le 2026-09-27",
    },
  };

  const valeurReelle = {
    valeurBrute: VALEUR_TOTALE,
    fraisDeVente: 9.0,
    spreadDeSortie: 3.68,
    impot: 96.4,
    // 5 448,72 − 9,00 − 3,68 − 96,40 = 5 339,64
    valeurReelle: 5339.64,
    minoree: true,
    horsDesTitres: 63.2,
    partielle: true,
    parPoche: [
      { poche: "PEA", valeurBrute: 1855.75, fraisDeVente: 2.0, spread: 0.93, impot: 0.0, valeurReelle: 1852.82, regle: "plan de moins de cinq ans : le gain du plan est approché depuis les titres", minoree: true },
      { poche: "CTO", valeurBrute: 3033.9, fraisDeVente: 6.0, spread: 2.12, impot: 54.87, valeurReelle: 2970.91, regle: "prélèvement forfaitaire unique sur les seules plus-values latentes", minoree: false },
      { poche: "Crypto", valeurBrute: 559.07, fraisDeVente: 1.0, spread: 0.63, impot: 41.53, valeurReelle: 515.91, regle: "prélèvement forfaitaire unique, seuil de cession de 305 € dépassé", minoree: false },
    ],
    hypotheses: [
      "Tous les titres sont supposés vendus le même jour, au dernier cours connu.",
      "Les plus-values déjà réalisées cette année et les dividendes déjà reçus ne sont pas comptés.",
      "L'impôt du PEA est approché depuis les titres, sur une date de premier versement déclarée.",
      "Les frais de vente sont ceux de la liste des prix, un euro par ordre.",
    ],
    exclues: [
      { nom: "Meridian Therapeutics", motif: "sans cours (D-53)" },
    ],
  };

  // --- Ce que le moteur signale ----------------------------------------------------

  const aSurveiller = [
    {
      categorie: "prix à compléter",
      message:
        "Un achat du 2025-06-12 sur Nordvent SA est arrivé sans son montant : le prix de revient de cette ligne est incomplet.",
      reference: "evt-2025-06-12-0043",
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
        "Meridian Therapeutics n'est plus coté par la source depuis le 2026-08-11. La position est exclue des totaux, qui sont marqués partiels.",
      reference: "XX0000000033",
    },
  ];

  // --- Les variantes, pour éprouver les écrans (D-62) -------------------------------
  // Un écran qui ne tient que sur le jeu complet n'est pas un écran.

  const variantes = {
    complet: {
      nom: "Portefeuille complet",
      description:
        "Onze lignes : ETF actions, ETF obligataire, ETC sur l'or, deux actions en direct, crypto, un fonds non couvert, une position sans cours.",
    },
    uneLigne: {
      nom: "Une seule ligne",
      description:
        "Un plan d'épargne démarré il y a deux mois sur un seul ETF. Le TRI et le TWRR sont là, mais ne veulent rien dire.",
      synthese: {
        arreteAu: "2026-09-25",
        sourceDesCours: "Yahoo Finance",
        debut: "2026-07-21",
        dureeEnClair: "2 mois",
        gain: 7.43,
        tri: 0.418,
        twrr: 0.037,
        twrrAnnualise: 0.248,
        peuSignificatif: true,
        valeurTotale: 207.43,
        // 200,00 d'achats bruts − 2,00 de frais = 198,00 réellement placés
        capitalNetInvesti: 198.0,
        plusValueLatente: 9.43, // 207,43 − 198,00
        formuleGain: "207,43 − 200,00 d'achats = 7,43",
        partiel: false,
        nonValorisees: [],
        achatsBruts: 200.0,
        ventesBrutes: 0,
        dividendesBruts: 0,
        fraisPayes: 2.0,
        taxesPayees: 0,
        parPoche: [
          { poche: "PEA", valeur: 207.43, capitalNetInvesti: 198.0, plusValueLatente: 9.43 },
        ],
      },
    },
    sansPea: {
      nom: "Sans PEA",
      description:
        "Un CTO et de la crypto seulement. L'écran ne doit pas laisser une case vide là où le PEA serait.",
    },
    toutNonCouvert: {
      nom: "Tout non couvert",
      description:
        "Aucune composition disponible. La répartition est entièrement vide : c'est le cas qui casse les camemberts, et celui qu'il faut réussir.",
    },
  };

  return {
    positions: positions,
    synthese: synthese,
    courbe: courbe(),
    diversification: diversification,
    couts: couts,
    valeurReelle: valeurReelle,
    aSurveiller: aSurveiller,
    variantes: variantes,
  };
})();
