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
 * TOUT CE QUI PEUT ÊTRE CALCULÉ L'EST.
 * Les totaux, les plus-values, les pourcentages et la courbe sont dérivés des lignes et
 * des flux ci-dessous, jamais recopiés. C'est ce qui garantit qu'une somme affichée à
 * l'écran tombe juste — et la première version de cette maquette prouve que c'était
 * nécessaire : trois totaux écrits à la main se contredisaient, et la courbe, qui
 * montait de façon lisse alors que les flux arrivent par paliers, produisait un TWRR
 * de −126 %.
 *
 * Fichier en .js et non en .json : le .gitignore exclut *.json (règle 1).
 */

window.MAQUETTE = (function () {
  "use strict";

  const FRAIS_PAR_ORDRE = 1.0; // liste des prix : 1 € par ordre
  const sou = function (n) {
    return Math.round(n * 100) / 100;
  };

  // ==========================================================================
  // LES POSITIONS
  // La valeur et la plus-value latente sont CALCULÉES : valeur = quantité x cours,
  // plus-value latente = valeur − capital net investi. Ce sont les deux vérifications
  // que le propriétaire fera en premier.
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
      // Prix de revient : le capital rapporté à la quantité détenue.
      prixDeRevient: sou(l.capitalNetInvesti / l.quantite),
      terMontant: l.ter === null || valeur === null ? null : sou((valeur * l.ter) / 100),
    });
  });

  // ==========================================================================
  // LES FLUX
  // Chaque ordre est une ligne, avec sa poche : c'est ce qui permet de recalculer les
  // chiffres clés quand on décoche une poche, au lieu de les mettre à l'échelle.
  //
  // `montant` est le montant BRUT, du point de vue de l'investisseur : un achat sort de
  // sa poche (négatif), une vente et un dividende y rentrent (positif). C'est lui qui
  // sert au gain et au TRI (D-21 : la performance se calcule sur les montants bruts).
  //
  // `frais` est prélevé en plus, et ne compte PAS dans la performance : il réduit le
  // capital net investi (D-12), et il est analysé dans l'onglet « Frais et taxes ».
  //
  // `prorata` n'existe que sur une vente : c'est la part du capital net investi qui
  // sort, au prorata des parts vendues — et non le produit de la vente.
  // ==========================================================================

  const flux = [
    { date: "2025-03-14", libelle: "Achat", poche: "PEA", montant: -700.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-03-14", libelle: "Achat", poche: "CTO", montant: -400.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-03-14", libelle: "Achat", poche: "Crypto", montant: -100.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-06-13", libelle: "Achat", poche: "PEA", montant: -300.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-06-13", libelle: "Achat", poche: "CTO", montant: -500.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-06-13", libelle: "Achat", poche: "Crypto", montant: -100.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-09-05", libelle: "Achat", poche: "PEA", montant: -250.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-09-05", libelle: "Achat", poche: "CTO", montant: -500.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-09-05", libelle: "Achat", poche: "Crypto", montant: -100.0, frais: FRAIS_PAR_ORDRE },
    { date: "2025-11-21", libelle: "Dividende", poche: "CTO", montant: 18.4, frais: 0 },
    { date: "2026-01-16", libelle: "Achat", poche: "PEA", montant: -300.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-01-16", libelle: "Achat", poche: "CTO", montant: -650.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-01-16", libelle: "Achat", poche: "Crypto", montant: -100.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-03-06", libelle: "Vente", poche: "PEA", montant: 186.4, frais: FRAIS_PAR_ORDRE, prorata: 125.5 },
    { date: "2026-04-24", libelle: "Achat", poche: "PEA", montant: -200.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-04-24", libelle: "Achat", poche: "CTO", montant: -450.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-04-24", libelle: "Achat", poche: "Crypto", montant: -50.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-06-12", libelle: "Dividende", poche: "CTO", montant: 26.5, frais: 0 },
    { date: "2026-07-31", libelle: "Achat", poche: "PEA", montant: -150.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-07-31", libelle: "Achat", poche: "CTO", montant: -300.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-07-31", libelle: "Achat", poche: "Crypto", montant: -50.0, frais: FRAIS_PAR_ORDRE },
    { date: "2026-09-11", libelle: "Dividende", poche: "CTO", montant: 18.3, frais: 0 },
  ];

  const POCHES = ["PEA", "CTO", "Crypto"];
  const DATE_ARRETE = "2026-09-25";

  // --- Les totaux, calculés ---------------------------------------------------

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

  // ==========================================================================
  // LA COURBE
  // Elle est DÉRIVÉE DES FLUX, et c'est le point essentiel : deux séries qui ne
  // bougeraient pas aux mêmes dates rendraient le TWRR absurde.
  //
  //  - « base » est la valeur d'acquisition des actifs détenus : elle monte du montant
  //    brut à chaque achat, et descend à chaque vente et à chaque dividende (l'argent
  //    quitte les actifs). C'est sur elle que la performance s'applique ;
  //  - « investi » est le capital net investi (D-12) : montant brut moins les frais, et
  //    réduit au prorata des parts vendues. Il monte EN ESCALIER.
  // ==========================================================================

  function cumulsAu(date, poche) {
    let base = 0;
    let investi = 0;
    for (const f of flux) {
      if (f.date > date) break;
      if (poche && f.poche !== poche) continue;
      base += -f.montant;
      if (f.libelle === "Achat") investi += -f.montant - (f.frais || 0);
      else if (f.libelle === "Vente") investi -= f.prorata || 0;
    }
    return { base: sou(base), investi: sou(investi) };
  }

  // La croissance de chaque poche est celle qui fait arriver la courbe exactement sur
  // la valeur affichée en haut de l'écran. Rien n'est ajusté après coup.
  const CROISSANCE = {};
  for (const poche of POCHES) {
    const finale = cumulsAu(DATE_ARRETE, poche);
    CROISSANCE[poche] = finale.base > 0 ? PAR_POCHE[poche].valeur / finale.base - 1 : 0;
  }

  // La crypto ondule trois fois plus que le reste, comme dans la vie.
  const HOULE = { PEA: 1, CTO: 0.8, Crypto: 3.2 };

  function courbe() {
    const points = [];
    // UN POINT PAR JOUR, comme le fait `moteur/valorisation.evolution()`. C'est
    // nécessaire, pas décoratif : avec une maille hebdomadaire, l'effet d'un flux
    // n'apparaissait qu'au point suivant, et le TWRR perdait une semaine de croissance
    // à chaque opération — l'écart mesuré atteignait six points de rendement.
    //
    // On démarre une semaine AVANT le premier achat, à zéro : c'est ce qui permet de
    // compter les tout premiers achats dans la période « depuis le début ».
    const depart = new Date("2025-03-07T00:00:00Z");
    const jours = 567; // 2025-03-07 + 567 jours = 2026-09-25, la date d'arrêté
    for (let i = 0; i <= jours; i++) {
      const date = new Date(depart.getTime() + i * 86400000).toISOString().slice(0, 10);
      const t = i / jours;
      const parPoche = {};
      let valeur = 0;
      let investi = 0;
      for (const poche of POCHES) {
        const cumuls = cumulsAu(date, poche);
        const tendance = cumuls.base * (1 + CROISSANCE[poche] * t);
        const houle =
          cumuls.base *
          HOULE[poche] *
          (0.038 * Math.sin(i / 37 + (poche === "CTO" ? 1.1 : 0)) +
            0.02 * Math.sin(i / 14.7 + 1.4));
        parPoche[poche] = {
          valeur: sou(Math.max(0, tendance + houle)),
          investi: cumuls.investi,
        };
        valeur += parPoche[poche].valeur;
        investi += cumuls.investi;
      }
      points.push({ date: date, valeur: sou(valeur), investi: sou(investi), parPoche: parPoche });
    }
    // Le dernier point est forcé sur les valeurs exactes des positions.
    const parPocheFinal = {};
    for (const poche of POCHES) {
      parPocheFinal[poche] = {
        valeur: PAR_POCHE[poche].valeur,
        investi: cumulsAu(DATE_ARRETE, poche).investi,
      };
    }
    points[points.length - 1] = {
      date: DATE_ARRETE,
      valeur: TOTAL.valeur,
      investi: TOTAL.capital,
      parPoche: parPocheFinal,
    };
    return points;
  }

  // ==========================================================================
  // LA SYNTHÈSE
  // ==========================================================================

  const fluxTotaux = sommeFlux(null);

  const synthese = {
    arreteAu: DATE_ARRETE,
    sourceDesCours: "Yahoo Finance",
    valeurTotale: TOTAL.valeur,
    capitalNetInvesti: TOTAL.capital,
    plusValueLatente: TOTAL.latente,
    achatsBruts: sou(-sommeFlux(function (f) { return f.libelle === "Achat"; }).brut),
    ventesBrutes: sommeFlux(function (f) { return f.libelle === "Vente"; }).brut,
    dividendesBruts: sommeFlux(function (f) { return f.libelle === "Dividende"; }).brut,
    fraisPayes: fluxTotaux.frais,
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

  // Ce que les fonds n'attribuent à rien : liquidités, dérivés, lignes non classées.
  const NON_ATTRIBUE = 13.89;
  const NON_COUVERT = positions.find(function (p) {
    return p.nonCouvert;
  }).valeur;
  const OBLIGATIONS = positions.find(function (p) {
    return p.contenuDeclare === "obligations";
  }).valeur;
  const MATIERES = positions.find(function (p) {
    return p.contenuDeclare === "matières premières";
  }).valeur;
  const NUMERIQUES = PAR_POCHE.Crypto.valeur;
  // Les actions sont ce qui reste : tout est donc attribué, et le total fait la base.
  const ACTIONS = sou(BASE - NON_ATTRIBUE - NON_COUVERT - OBLIGATIONS - MATIERES - NUMERIQUES);

  const RESTES_GEO = [
    { libelle: "Non attribué par les fonds", montant: NON_ATTRIBUE, mot: "non-attribue" },
    { libelle: "Obligations", montant: OBLIGATIONS, mot: "hors-actions" },
    { libelle: "Matières premières", montant: MATIERES, mot: "hors-actions" },
    { libelle: "Actifs numériques", montant: NUMERIQUES, mot: "hors-classification" },
    { libelle: "Non couvert", montant: NON_COUVERT, mot: "non-couvert" },
  ];

  // Les pays. Le dernier poste absorbe l'arrondi, pour que la somme fasse exactement
  // le montant investi en actions.
  const PAYS_TETE = [
    { libelle: "États-Unis", zone: "Amérique du Nord", montant: 2043.8, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Japon", zone: "Japon", montant: 421.36, source: "extraETF", regle: "pays d'activité" },
    { libelle: "France", zone: "Europe", montant: 268.94, source: "extraETF + GLEIF", regle: "mixte" },
    { libelle: "Royaume-Uni", zone: "Europe", montant: 152.6, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Allemagne", zone: "Europe", montant: 138.22, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Canada", zone: "Amérique du Nord", montant: 96.4, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Suisse", zone: "Europe", montant: 84.15, source: "extraETF", regle: "pays d'activité" },
    { libelle: "Pays-Bas", zone: "Europe", montant: 71.3, source: "extraETF", regle: "pays d'activité" },
  ];
  const AUTRES_PAYS = sou(
    ACTIONS -
      PAYS_TETE.reduce(function (s, p) {
        return s + p.montant;
      }, 0)
  );
  const PAYS = PAYS_TETE.concat([
    { libelle: "Autres pays (18)", zone: "—", montant: AUTRES_PAYS, source: "extraETF", regle: "pays d'activité" },
  ]);

  // Les zones : un regroupement des pays ci-dessus, plus la part des « autres pays »
  // qui leur revient. C'est une convention, pas une donnée (D-67).
  const AUTRES_PAR_ZONE = { Europe: 62.3, "Asie-Pacifique développée": 54.2 };
  AUTRES_PAR_ZONE["Marchés émergents"] = sou(
    AUTRES_PAYS - AUTRES_PAR_ZONE.Europe - AUTRES_PAR_ZONE["Asie-Pacifique développée"]
  );
  const ZONES = ["Amérique du Nord", "Europe", "Japon", "Asie-Pacifique développée", "Marchés émergents"].map(
    function (zone) {
      let montant = AUTRES_PAR_ZONE[zone] || 0;
      for (const p of PAYS_TETE) if (p.zone === zone) montant += p.montant;
      return { libelle: zone, montant: sou(montant) };
    }
  );

  // Les secteurs, dans la nomenclature Morningstar en 11 postes. Le dernier absorbe
  // l'arrondi, pour la même raison que les pays.
  const SECTEURS_TETE = [
    { libelle: "Technologie", montant: 823.4 },
    { libelle: "Services financiers", montant: 574.1 },
    { libelle: "Santé", montant: 421.85 },
    { libelle: "Consommation cyclique", montant: 372.6 },
    { libelle: "Industrie", montant: 358.9 },
    { libelle: "Services de communication", montant: 289.45 },
    { libelle: "Consommation défensive", montant: 241.3 },
    { libelle: "Énergie", montant: 152.7 },
    { libelle: "Services aux collectivités", montant: 98.4 },
    { libelle: "Immobilier", montant: 78.25 },
  ];
  const SECTEURS = SECTEURS_TETE.concat([
    {
      libelle: "Matériaux de base",
      montant: sou(
        ACTIONS -
          SECTEURS_TETE.reduce(function (s, p) {
            return s + p.montant;
          }, 0)
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
        { libelle: "Actions", montant: ACTIONS },
        { libelle: "Obligations", montant: OBLIGATIONS },
        { libelle: "Matières premières", montant: MATIERES },
        { libelle: "Actifs numériques", montant: NUMERIQUES },
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
        nom: positions.find(function (p) {
          return p.nonCouvert;
        }).nom,
        montant: NON_COUVERT,
        motif: "la source ne publie aucune répartition pour cet ISIN",
      },
    ],
    actifsSynthetiques: positions
      .filter(function (p) {
        return p.synthetique;
      })
      .map(function (p) {
        return p.nom;
      }),
    declareesALaMain: positions
      .filter(function (p) {
        return p.contenuDeclare;
      })
      .map(function (p) {
        return p.nom;
      }),
  };

  // ==========================================================================
  // LES COÛTS ET LA VALEUR RÉELLE
  // ==========================================================================

  // Les spreads par côté, par type d'actif (D-56), avec leur fourchette mesurée.
  const SPREAD = { ETF: 0.05, Action: 0.1, Crypto: 0.5 };

  function spreadDe(position) {
    const taux = SPREAD[position.type];
    if (!taux || position.valeur === null) return 0;
    return sou((position.valeur * taux) / 100);
  }

  const terAnnuel = sou(
    positions.reduce(function (s, p) {
      return s + (p.terMontant || 0);
    }, 0)
  );

  const couts = {
    fraisPayes: synthese.fraisPayes,
    taxesPayees: synthese.taxesPayees,
    coutPaye: sou(synthese.fraisPayes + synthese.taxesPayees),
    nombreOrdres: synthese.nombreOrdres,
    // Le poids d'un coût dans son opération : frais rapportés au montant brut échangé.
    // Attention : c'est un TAUX (0,0035 pour 0,35 %), pas un pour cent. Et il ne doit
    // surtout pas être arrondi au centime, sinon il tombe à zéro.
    poidsMoyen: synthese.fraisPayes / (synthese.achatsBruts + synthese.ventesBrutes),
    spreadEstimeEntree: sou(
      flux.reduce(function (s, f) {
        if (f.libelle !== "Achat") return s;
        // Le spread d'entrée dépend du type d'actif acheté ; la poche crypto en porte
        // le plus, et c'est précisément ce qu'on veut rendre visible.
        const taux = f.poche === "Crypto" ? SPREAD.Crypto : SPREAD.ETF;
        return s + (-f.montant * taux) / 100;
      }, 0)
    ),
    terAnnuel: terAnnuel,
    spreads: SPREAD,
    exemple: {
      libelle: "Achat du 16/01/2026 · Cardinal Monde Développé UCITS ETF",
      montantBrut: 650.0,
      frais: FRAIS_PAR_ORDRE,
      poids: FRAIS_PAR_ORDRE / 650.0, // un taux, pas un pour cent
      formuleSpread: "650,00 x 0,05 % = 0,33",
      taux: "0,05 %",
      fourchette: "entre 0,02 % et 0,09 %",
      source: "relevés Xetra, vérifié le 27/09/2026",
    },
  };

  // --- La valeur réelle : ce qu'on récupérerait en vendant tout aujourd'hui ---

  const IMPOT_PAR_POCHE = { PEA: 0, CTO: 54.87, Crypto: 41.53 };
  const REGLE_PAR_POCHE = {
    PEA: "plan de moins de cinq ans : le gain du plan est approché depuis les titres",
    CTO: "prélèvement forfaitaire unique sur les seules plus-values latentes",
    Crypto: "prélèvement forfaitaire unique, seuil de cession de 305 € dépassé",
  };

  const valeurReellePoches = POCHES.map(function (poche) {
    const detenues = positions.filter(function (p) {
      return p.poche === poche && p.valeur !== null;
    });
    const fraisDeVente = sou(detenues.length * FRAIS_PAR_ORDRE);
    const spread = sou(
      detenues.reduce(function (s, p) {
        return s + spreadDe(p);
      }, 0)
    );
    const brute = PAR_POCHE[poche].valeur;
    const impot = IMPOT_PAR_POCHE[poche];
    return {
      poche: poche,
      valeurBrute: brute,
      fraisDeVente: fraisDeVente,
      spread: spread,
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
    impot: sommePoches("impot"),
    valeurReelle: sommePoches("valeurReelle"),
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
        return { nom: p.nom, motif: "sans cours (D-53)" };
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
    synthese: synthese,
    courbe: courbe(),
    flux: flux,
    diversification: diversification,
    couts: couts,
    valeurReelle: valeurReelle,
    aSurveiller: aSurveiller,
    parPoche: PAR_POCHE,
    total: TOTAL,
  };
})();
