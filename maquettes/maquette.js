/* Construit les deux directions de la Synthèse à partir du MÊME jeu de données.
 *
 * Pourquoi du JavaScript plutôt que deux pages HTML écrites à la main : parce que
 * l'étape 8 doit éprouver chaque écran sur des portefeuilles différents (D-62), et
 * qu'une maquette figée ne montre que le cas riche. Ici, changer de jeu de données
 * redessine tout — c'est le seul moyen de voir si l'écran tient quand il n'y a qu'une
 * ligne, pas de PEA, ou aucun cours du tout.
 *
 * Rien ici ne préjuge du code de l'étape 9 : Dash reconstruira ces mêmes blocs en
 * Python. Ce qui se transmet, c'est la feuille de style et la disposition.
 */

(function () {
  "use strict";

  const D = window.MAQUETTE;

  // --- Mise en forme ------------------------------------------------------------
  // Deux unités, deux fonctions. Les confondre a déjà produit « 6264,00 % » au lieu
  // de 62,64 % (étape 7). On ne divise ni ne multiplie jamais par cent ailleurs.

  const fEuros = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  /** Un montant en euros. */
  function euros(n) {
    if (n === null || n === undefined) return "–";
    return fEuros.format(n) + " €";
  }

  /** Un montant signé : le signe se lit AVANT la couleur. */
  function eurosSignes(n) {
    if (n === null || n === undefined) return "–";
    const signe = n > 0 ? "+" : n < 0 ? "−" : "";
    return signe + fEuros.format(Math.abs(n)) + " €";
  }

  /** Reçoit un TAUX (0,6264) et écrit un pourcentage. Pour le TRI, le TWRR, le poids. */
  function tauxEnPourCent(t) {
    if (t === null || t === undefined) return "–";
    const signe = t > 0 ? "+" : t < 0 ? "−" : "";
    return signe + fEuros.format(Math.abs(t) * 100) + " %";
  }

  /** Reçoit un POUR CENT déjà calculé (62,64) et l'écrit. Pour les répartitions. */
  function pourCent(p) {
    if (p === null || p === undefined) return "–";
    return fEuros.format(p) + " %";
  }

  function classeSelonSigne(n) {
    return n > 0 ? "gain" : n < 0 ? "perte" : "";
  }

  function dateCourte(iso) {
    if (!iso) return "–";
    const [a, m, j] = iso.split("-");
    return `${j}/${m}/${a}`;
  }

  function el(balise, attributs, enfants) {
    const noeud = document.createElement(balise);
    for (const [cle, valeur] of Object.entries(attributs || {})) {
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

  // --- Le vocabulaire d'écran ----------------------------------------------------
  // Chaque marque porte son explication, écrite pour quelqu'un qui découvre
  // l'application (D-62). Voir docs/conception-interface.md §2.

  const MOTS = {
    partiel: {
      libelle: "Partiel",
      texte:
        "<b>Ce total ne porte que sur les actifs pour lesquels nous avons un cours.</b> Ceux qui manquent sont nommés juste à côté, avec leur quantité. Nous préférons un total incomplet et signalé à un total qui compterait zéro pour une ligne dont nous ignorons la valeur.",
    },
    sansCours: {
      libelle: "Sans cours",
      texte:
        "<b>Aucun cours utilisable à cette date pour cet actif.</b> Sa valeur n'est donc comptée nulle part, et les totaux sont marqués partiels. La quantité, elle, reste juste : c'est la valeur qui manque, pas les opérations.",
    },
    peuSignificatif: {
      libelle: "Peu significatif",
      texte:
        "<b>Sur moins d'un an, un rendement annualisé s'emballe.</b> Quelques semaines de hausse deviennent un pourcentage énorme qui ne décrit rien de durable. Le gain en euros, lui, reste lisible dès le premier jour — c'est pourquoi il est affiché en premier.",
    },
    brut: {
      libelle: "Brut",
      texte:
        "<b>Les frais et les taxes ne sont pas déduits ici.</b> C'est voulu : cette page montre l'évolution de ce qui est dans le coffre. Ce que tout cela coûte est traité à part, et ce que vous récupéreriez en vendant tout figure dans la vue « valeur réelle ».",
    },
    aCompleter: {
      libelle: "À compléter",
      texte:
        "<b>Une opération est arrivée sans son montant.</b> Le prix de revient de cette ligne est donc incomplet. L'opération est listée dans « à surveiller » avec sa référence, pour que vous puissiez la retrouver dans votre relevé.",
    },
    coursDecale: {
      libelle: "Cours décalé",
      texte:
        "<b>Le marché était fermé à la date demandée.</b> Nous retenons le dernier jour coté avant elle, et nous affichons cette date : rien n'est interpolé.",
    },
  };

  let compteurMots = 0;

  /** Une marque cliquable, suivie de son explication dépliable. */
  function marque(cle, variante) {
    const mot = MOTS[cle];
    const id = "exp-" + ++compteurMots;
    const bouton = el("button", {
      class: "mot" + (variante ? " mot--" + variante : ""),
      type: "button",
      "aria-expanded": "false",
      "aria-controls": id,
      texte: mot.libelle,
    });
    const panneau = el("span", { class: "explication", id: id, html: mot.texte });
    panneau.hidden = true;
    bouton.addEventListener("click", function () {
      const ouvert = bouton.getAttribute("aria-expanded") === "true";
      bouton.setAttribute("aria-expanded", String(!ouvert));
      panneau.hidden = ouvert;
    });
    return [bouton, panneau];
  }

  // --- Les jeux de données -------------------------------------------------------
  // Chaque variante est DÉRIVÉE des positions, pas écrite à la main : les totaux
  // restent donc cohérents quoi qu'on retire.

  /* Le total d'une colonne qui S'ADDITIONNE.
   *
   * La plus-value latente en fait partie ; le gain, non. Le gain se calcule sur les
   * montants bruts (D-21) alors que le capital net investi est net de frais et réduit
   * au prorata des ventes (D-12) : additionner la colonne ne le retrouve pas. L'écran
   * donne donc la formule du gain, et ne propose jamais sa colonne à sommer. */
  function totaliser(positions) {
    let valeur = 0;
    let capital = 0;
    let latente = 0;
    const sansCours = [];
    for (const p of positions) {
      capital += p.capitalNetInvesti;
      if (p.valeur === null) sansCours.push(p.nom);
      else {
        valeur += p.valeur;
        latente += p.plusValueLatente;
      }
    }
    return {
      valeur: Math.round(valeur * 100) / 100,
      capital: Math.round(capital * 100) / 100,
      latente: Math.round(latente * 100) / 100,
      sansCours: sansCours,
    };
  }

  const JEUX = {
    complet: {
      nom: "Portefeuille complet",
      aide: "Onze lignes : ETF actions, ETF obligataire, or, deux actions en direct, crypto, un fonds non couvert, une position sans cours.",
      construire: function () {
        return { positions: D.positions, synthese: D.synthese, courbe: D.courbe };
      },
    },
    uneLigne: {
      nom: "Une seule ligne",
      aide: "Un plan d'épargne démarré il y a deux mois. Le TRI et le TWRR existent, mais ne veulent rien dire.",
      construire: function () {
        const position = {
          code: "XX0000000012",
          nom: "Alizé Europe 600 UCITS ETF",
          poche: "PEA",
          type: "ETF",
          quantite: "7,9400",
          prixDeRevient: "24,94",
          capitalNetInvesti: 198.0,
          cours: "26,12",
          dateCours: "2026-09-25",
          place: "Euronext Paris",
          valeur: 207.43,
          plusValueLatente: 9.43,
          tri: 0.418,
          twrr: 0.037,
          ter: "0,12",
          terMontant: 0.25,
        };
        const courbe = D.courbe.slice(-10).map(function (point, i, tout) {
          const t = i / (tout.length - 1);
          return {
            date: point.date,
            investi: Math.round(200 * Math.min(1, t * 1.6) * 100) / 100,
            valeur: Math.round(200 * Math.min(1, t * 1.6) * (1 + 0.037 * t) * 100) / 100,
          };
        });
        courbe[courbe.length - 1] = { date: "2026-09-25", investi: 200.0, valeur: 207.43 };
        return {
          positions: [position],
          synthese: D.variantes.uneLigne.synthese,
          courbe: courbe,
        };
      },
    },
    sansPea: {
      nom: "Sans PEA",
      aide: "Un CTO et de la crypto seulement. L'écran ne doit pas laisser un trou là où le PEA serait.",
      construire: function () {
        const positions = D.positions.filter(function (p) {
          return p.poche !== "PEA";
        });
        const t = totaliser(positions);
        return {
          positions: positions,
          synthese: Object.assign({}, D.synthese, {
            // 3 592,97 − 3 520,00 d'achats + 63,20 de dividendes = 136,17
            gain: 136.17,
            formuleGain:
              "3 592,97 − 3 520,00 d'achats + 63,20 de dividendes = 136,17",
            plusValueLatente: t.latente,
            achatsBruts: 3520.0,
            ventesBrutes: 0,
            valeurTotale: t.valeur,
            capitalNetInvesti: t.capital,
            nonValorisees: t.sansCours,
            partiel: t.sansCours.length > 0,
            tri: 0.096,
            twrr: 0.089,
            twrrAnnualise: 0.079,
            parPoche: D.synthese.parPoche.filter(function (p) {
              return p.poche !== "PEA";
            }),
          }),
          courbe: D.courbe.map(function (point) {
            return {
              date: point.date,
              investi: Math.round(point.investi * 0.672 * 100) / 100,
              valeur: Math.round(point.valeur * 0.66 * 100) / 100,
            };
          }),
        };
      },
    },
    aucunCours: {
      nom: "Aucun cours",
      aide: "La source de cours est muette sur tout le portefeuille. C'est le cas qui casse les tableaux de bord : il ne doit afficher ni zéro, ni total muet.",
      construire: function () {
        const positions = D.positions.map(function (p) {
          return Object.assign({}, p, {
            cours: null,
            dateCours: null,
            place: null,
            valeur: null,
            plusValueLatente: null,
            tri: null,
            twrr: null,
            motifSansCours:
              "aucun cours utilisable au 2026-09-25 : la source n'a répondu pour aucun actif",
          });
        });
        const t = totaliser(positions);
        return {
          positions: positions,
          synthese: Object.assign({}, D.synthese, {
            gain: null,
            formuleGain: null,
            plusValueLatente: null,
            tri: null,
            twrr: null,
            twrrAnnualise: null,
            valeurTotale: null,
            capitalNetInvesti: t.capital,
            partiel: true,
            nonValorisees: t.sansCours,
            motif:
              "aucune position n'a de cours : la valeur du portefeuille ne peut pas être calculée.",
            parPoche: [],
          }),
          courbe: [],
        };
      },
    },
  };

  // --- La courbe -----------------------------------------------------------------

  function courbeSvg(points) {
    if (!points || points.length === 0) {
      return el("p", {
        class: "section__chapeau",
        texte:
          "Pas de courbe : aucun cours connu sur la période. Rien n'est tracé plutôt qu'une ligne à zéro.",
      });
    }

    const L = 1000;
    const H = 270;
    const mg = { g: 62, d: 138, h: 16, b: 30 };
    const larg = L - mg.g - mg.d;
    const haut = H - mg.h - mg.b;

    const maxi = Math.max.apply(
      null,
      points.map(function (p) {
        return Math.max(p.valeur, p.investi);
      })
    );
    const plafond = Math.ceil((maxi * 1.08) / 500) * 500 || 500;

    const x = function (i) {
      return mg.g + (i / (points.length - 1 || 1)) * larg;
    };
    const y = function (v) {
      return mg.h + haut - (v / plafond) * haut;
    };

    const ns = "http://www.w3.org/2000/svg";
    function s(balise, attributs, texte) {
      const noeud = document.createElementNS(ns, balise);
      for (const [cle, valeur] of Object.entries(attributs || {})) {
        if (valeur === null || valeur === undefined) continue;
        noeud.setAttribute(cle, String(valeur));
      }
      if (texte !== undefined) noeud.textContent = texte;
      return noeud;
    }

    const svg = s("svg", {
      class: "graphique",
      viewBox: `0 0 ${L} ${H}`,
      role: "img",
      "aria-label":
        "Évolution du capital brut et du capital net investi sur la période retenue.",
    });

    // Grille et graduations : quatre paliers, chacun nommé par une valeur que la
    // courbe atteint réellement.
    for (let i = 0; i <= 4; i++) {
      const v = (plafond / 4) * i;
      svg.append(s("line", { class: "grille", x1: mg.g, x2: mg.g + larg, y1: y(v), y2: y(v) }));
      svg.append(
        s(
          "text",
          { x: mg.g - 10, y: y(v) + 4, "text-anchor": "end" },
          fEuros.format(v).replace(",00", "") + " €"
        )
      );
    }

    // Dates : première, milieu, dernière.
    [0, Math.floor(points.length / 2), points.length - 1].forEach(function (i, rang) {
      svg.append(
        s(
          "text",
          {
            x: x(i),
            y: H - 8,
            "text-anchor": rang === 0 ? "start" : rang === 2 ? "end" : "middle",
          },
          dateCourte(points[i].date)
        )
      );
    });

    // L'aire sous le capital brut, puis la ligne.
    const traceBrut = points
      .map(function (p, i) {
        return (i ? "L" : "M") + x(i).toFixed(1) + " " + y(p.valeur).toFixed(1);
      })
      .join(" ");
    svg.append(
      s("path", {
        class: "aire-brut",
        d: `${traceBrut} L ${x(points.length - 1).toFixed(1)} ${y(0)} L ${x(0).toFixed(1)} ${y(0)} Z`,
      })
    );
    svg.append(s("path", { class: "serie serie--brut", d: traceBrut }));

    // Le capital net investi monte EN ESCALIER : il ne bouge qu'aux achats.
    let traceInvesti = "";
    points.forEach(function (p, i) {
      const px = x(i).toFixed(1);
      const py = y(p.investi).toFixed(1);
      if (i === 0) traceInvesti = `M ${px} ${py}`;
      else traceInvesti += ` L ${px} ${y(points[i - 1].investi).toFixed(1)} L ${px} ${py}`;
    });
    svg.append(s("path", { class: "serie serie--investi", d: traceInvesti }));

    // Le point d'arrivée est souligné : c'est le chiffre affiché en haut de l'écran.
    const dernier = points[points.length - 1];
    svg.append(
      s("circle", {
        cx: x(points.length - 1),
        cy: y(dernier.valeur),
        r: 4,
        fill: "var(--courbe-brut)",
        stroke: "var(--papier)",
        "stroke-width": 2,
      })
    );

    // Étiquettes posées directement au bout des courbes : l'identité ne repose
    // jamais sur la seule couleur.
    svg.append(
      s(
        "text",
        {
          x: x(points.length - 1) + 12,
          y: y(dernier.valeur) + 4,
          fill: "var(--courbe-brut)",
          "font-weight": "600",
        },
        "Capital brut"
      )
    );
    svg.append(
      s(
        "text",
        { x: x(points.length - 1) + 12, y: y(dernier.investi) + 4 },
        "Capital net investi"
      )
    );

    return svg;
  }

  function legendeCourbe() {
    return el("ul", { class: "legende" }, [
      el("li", {}, [
        el("i", { style: "border-top-color: var(--courbe-brut)" }),
        document.createTextNode("Capital brut — ce que valent les actifs"),
      ]),
      el("li", {}, [
        el("i", {
          style: "border-top-color: var(--encre-douce); border-top-style: dashed",
        }),
        document.createTextNode("Capital net investi — ce qui a été placé, net de frais"),
      ]),
    ]);
  }

  // --- La répartition par poche --------------------------------------------------

  const COULEURS_POCHE = {
    PEA: "var(--poche-1)",
    CTO: "var(--poche-2)",
    Crypto: "var(--poche-3)",
  };

  function barrePoches(parPoche, total) {
    if (!parPoche.length) {
      return el("p", {
        class: "section__chapeau",
        texte: "Aucune poche valorisée : il n'y a rien à répartir.",
      });
    }
    const barre = el(
      "div",
      { class: "barre" },
      parPoche.map(function (p) {
        return el("div", {
          class: "barre__part",
          style: `width:${(p.valeur / total) * 100}%; background:${COULEURS_POCHE[p.poche]}`,
          title: p.poche,
        });
      })
    );
    const legende = el(
      "ul",
      { class: "barre__legende" },
      parPoche.map(function (p) {
        return el("li", {}, [
          el("span", {
            class: "barre__puce",
            style: `background:${COULEURS_POCHE[p.poche]}`,
          }),
          el("span", { texte: p.poche }),
          el("span", {
            class: "nb",
            texte: euros(p.valeur) + "  ·  " + pourCent((p.valeur / total) * 100),
          }),
        ]);
      })
    );
    return el("div", {}, [barre, legende]);
  }

  function anneauPoches(parPoche, total) {
    if (!parPoche.length) {
      return el("p", {
        class: "section__chapeau",
        texte: "Aucune poche valorisée : il n'y a rien à répartir.",
      });
    }
    const ns = "http://www.w3.org/2000/svg";
    const taille = 190;
    const r = 72;
    const epaisseur = 26;
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", `0 0 ${taille} ${taille}`);
    svg.setAttribute("width", taille);
    svg.setAttribute("height", taille);
    svg.setAttribute("class", "anneau");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Répartition de la valeur entre les poches.");

    const circonference = 2 * Math.PI * r;
    let parcouru = 0;
    parPoche.forEach(function (p) {
      const part = p.valeur / total;
      const arc = document.createElementNS(ns, "circle");
      arc.setAttribute("cx", taille / 2);
      arc.setAttribute("cy", taille / 2);
      arc.setAttribute("r", r);
      arc.setAttribute("fill", "none");
      arc.setAttribute("stroke", COULEURS_POCHE[p.poche]);
      arc.setAttribute("stroke-width", epaisseur);
      // Un filet de papier de 2 px sépare deux segments.
      arc.setAttribute(
        "stroke-dasharray",
        `${Math.max(0, part * circonference - 2)} ${circonference}`
      );
      arc.setAttribute("stroke-dashoffset", -parcouru * circonference);
      arc.setAttribute("transform", `rotate(-90 ${taille / 2} ${taille / 2})`);
      svg.append(arc);
      parcouru += part;
    });

    const centre = document.createElementNS(ns, "text");
    centre.setAttribute("x", taille / 2);
    centre.setAttribute("y", taille / 2 + 5);
    centre.setAttribute("text-anchor", "middle");
    centre.setAttribute("font-size", "15");
    centre.setAttribute("font-weight", "600");
    centre.setAttribute("fill", "var(--encre)");
    centre.textContent = euros(total);
    svg.append(centre);

    const legende = el(
      "ul",
      { class: "barre__legende", style: "flex:1; min-width:230px" },
      parPoche.map(function (p) {
        return el("li", {}, [
          el("span", {
            class: "barre__puce",
            style: `background:${COULEURS_POCHE[p.poche]}`,
          }),
          el("span", { texte: p.poche }),
          el("span", {
            class: "nb",
            texte: euros(p.valeur) + "  ·  " + pourCent((p.valeur / total) * 100),
          }),
        ]);
      })
    );

    return el("div", { class: "anneau-bloc" }, [svg, legende]);
  }

  // --- Le tableau des actifs ------------------------------------------------------

  function tableauActifs(positions, dense) {
    const corps = positions.map(function (p) {
      const sansCours = p.valeur === null;
      const cellules = [
        el("td", {}, [
          el("span", { class: "actif__nom", texte: p.nom }),
          el("span", { class: "actif__code", texte: p.code + " · " + p.type }),
        ]),
        el("td", { texte: p.poche }),
        el("td", { class: "num nb", texte: p.quantite }),
      ];
      if (dense) {
        cellules.push(el("td", { class: "num nb", texte: p.prixDeRevient }));
        cellules.push(
          el("td", { class: "num nb", texte: p.cours === null ? "–" : p.cours })
        );
      }
      if (dense) {
        cellules.push(
          el("td", { class: "num nb", texte: euros(p.capitalNetInvesti) })
        );
      }
      cellules.push(
        el("td", { class: "num nb", texte: sansCours ? "–" : euros(p.valeur) })
      );
      cellules.push(
        el(
          "td",
          { class: "num nb " + (sansCours ? "" : classeSelonSigne(p.plusValueLatente)) },
          sansCours ? "–" : eurosSignes(p.plusValueLatente)
        )
      );
      const derniere = el("td", {}, []);
      if (sansCours) {
        const [bouton, panneau] = marque("sansCours", "absent");
        derniere.append(bouton, panneau);
        derniere.append(
          el("span", {
            class: "actif__code",
            style: "display:block; margin-top:5px",
            texte: p.motifSansCours,
          })
        );
      } else if (p.synthetique) {
        derniere.append(el("span", { class: "actif__code", texte: "ETF synthétique" }));
      }
      cellules.push(derniere);
      return el("tr", { class: sansCours ? "sans-valeur" : null }, cellules);
    });

    const entetes = [
      el("th", { texte: "Actif" }),
      el("th", { texte: "Poche" }),
      el("th", { class: "num", texte: "Quantité" }),
    ];
    if (dense) {
      entetes.push(el("th", { class: "num", texte: "Prix de revient" }));
      entetes.push(el("th", { class: "num", texte: "Capital net investi" }));
      entetes.push(el("th", { class: "num", texte: "Cours" }));
    }
    entetes.push(el("th", { class: "num", texte: "Valeur" }));
    entetes.push(el("th", { class: "num", texte: "+/− latente" }));
    entetes.push(el("th", { texte: "" }));

    // Le pied additionne les colonnes QUI S'ADDITIONNENT, et il le fait à la vue de
    // tous : c'est ainsi qu'on vérifie un écran sans ouvrir un CSV.
    const t = totaliser(positions);
    // Quand AUCUNE ligne n'a de cours, le total n'est pas zéro : il est inconnu.
    // Écrire « 0,00 € » ferait croire à un portefeuille vide (D-53).
    const rienDeValorise = t.sansCours.length === positions.length;
    const pied = el("tr", {}, [
      el("td", { colspan: 3, texte: `Total — ${positions.length} lignes` }),
      dense ? el("td", {}) : null,
      dense ? el("td", { class: "num nb", texte: euros(t.capital) }) : null,
      dense ? el("td", {}) : null,
      el("td", { class: "num nb", texte: rienDeValorise ? "–" : euros(t.valeur) }),
      el("td", {
        class: "num nb " + (rienDeValorise ? "" : classeSelonSigne(t.latente)),
        texte: rienDeValorise ? "–" : eurosSignes(t.latente),
      }),
      el("td", {
        class: "actif__code",
        texte: rienDeValorise ? "aucune ligne valorisée" : "",
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

  // --- Le panneau « à surveiller » -------------------------------------------------

  function panneauSurveiller() {
    const panneau = el("section", { class: "surveiller", id: "panneau-surveiller" }, [
      el("h3", { texte: "À surveiller" }),
      el("p", {
        class: "section__chapeau",
        style: "margin-bottom:0",
        texte:
          "Tout ce que l'application n'a pas su faire, ou a refusé de faire. Rien n'est écarté en silence.",
      }),
      el(
        "ul",
        {},
        D.aSurveiller.map(function (s) {
          return el("li", {}, [
            el("b", { texte: s.categorie }),
            el("span", { texte: s.message }),
            s.reference
              ? el("span", {
                  class: "reference",
                  style: "display:block; margin-top:3px",
                  texte: "référence : " + s.reference,
                })
              : null,
          ]);
        })
      ),
    ]);
    panneau.hidden = true;
    return panneau;
  }

  // --- Direction A : le relevé -----------------------------------------------------

  function directionA(jeu) {
    const s = jeu.synthese;
    const page = el("div", {});

    const bandeau = el("div", { class: "bandeau" });

    const caseGain = el("div", { class: "bandeau__case" }, [
      el("span", { class: "etiquette", texte: "Gain" }),
      el("span", {
        class: "bandeau__valeur " + classeSelonSigne(s.gain),
        texte: eurosSignes(s.gain),
      }),
    ]);
    if (s.gain === null) {
      caseGain.append(el("span", { class: "bandeau__note", texte: s.motif }));
    } else {
      const [b, p] = marque("brut");
      caseGain.append(
        el("span", { class: "bandeau__note" }, [b]),
        p,
        // La formule, en clair, sous le chiffre : le gain ne s'obtient pas en
        // additionnant une colonne, donc l'écran montre comment on l'obtient.
        el("span", { class: "bandeau__note nb", texte: s.formuleGain })
      );
    }
    bandeau.append(caseGain);

    const caseTri = el("div", { class: "bandeau__case" }, [
      el("span", { class: "etiquette", texte: "TRI" }),
      el("span", { class: "bandeau__valeur", texte: tauxEnPourCent(s.tri) }),
    ]);
    const caseTwrr = el("div", { class: "bandeau__case" }, [
      el("span", { class: "etiquette", texte: "TWRR" }),
      el("span", { class: "bandeau__valeur", texte: tauxEnPourCent(s.twrr) }),
      el("span", {
        class: "bandeau__note",
        texte:
          s.twrrAnnualise === null
            ? ""
            : "annualisé " + tauxEnPourCent(s.twrrAnnualise),
      }),
    ]);
    if (s.peuSignificatif) {
      const [b1, p1] = marque("peuSignificatif");
      caseTri.append(el("span", { class: "bandeau__note" }, [b1]), p1);
    }
    bandeau.append(caseTri, caseTwrr);

    const caseValeur = el("div", { class: "bandeau__case" }, [
      el("span", { class: "etiquette", texte: "Valeur des actifs" }),
      el("span", { class: "bandeau__valeur", texte: euros(s.valeurTotale) }),
    ]);
    if (s.partiel) {
      const [b, p] = marque("partiel", "absent");
      caseValeur.append(
        el("span", { class: "bandeau__note" }, [
          b,
          document.createTextNode(" " + s.nonValorisees.length + " ligne(s) sans cours"),
        ]),
        p
      );
    }
    bandeau.append(caseValeur);

    bandeau.append(
      el("div", { class: "bandeau__case" }, [
        el("span", { class: "etiquette", texte: "Capital net investi" }),
        el("span", { class: "bandeau__valeur", texte: euros(s.capitalNetInvesti) }),
        el("span", {
          class: "bandeau__note",
          texte: "net de frais et de taxes, réduit au prorata des ventes",
        }),
      ])
    );

    page.append(bandeau);

    // Les positions d'abord : c'est le relevé.
    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "section__titre", texte: "Positions détenues" }),
        el("p", {
          class: "section__chapeau",
          texte:
            "Une ligne par actif et par poche, comme sur un relevé. Les colonnes se recopient dans un tableur.",
        }),
        tableauActifs(jeu.positions, true),
      ])
    );

    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "section__titre", texte: "Répartition dans les poches" }),
        barrePoches(s.parPoche, s.valeurTotale || 1),
      ])
    );

    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "section__titre", texte: "Évolution" }),
        el("p", {
          class: "section__chapeau",
          texte:
            "Le capital brut est la valeur des actifs au jour le jour. Le capital net investi ne bouge qu'aux achats et aux ventes : d'où son escalier.",
        }),
        courbeSvg(jeu.courbe),
        legendeCourbe(),
      ])
    );

    return page;
  }

  // --- Direction B : la lecture guidée ----------------------------------------------

  function directionB(jeu) {
    const s = jeu.synthese;
    const page = el("div", {});

    // 1. La question principale, et sa réponse en une phrase.
    const reponse = el("p", { class: "reponse" });
    if (s.gain === null) {
      reponse.append(
        document.createTextNode("Nous ne pouvons pas le dire aujourd'hui. "),
        el("span", { texte: s.motif })
      );
    } else {
      reponse.append(
        el("span", {
          class: "enorme " + classeSelonSigne(s.gain),
          texte: eurosSignes(s.gain),
        }),
        document.createTextNode(
          ` depuis le ${dateCourte(s.debut)}, soit ${s.dureeEnClair} de placement. ` +
            `Vos actifs valent ${euros(s.valeurTotale)} pour ${euros(s.capitalNetInvesti)} réellement placés.`
        )
      );
    }

    const bloc1 = el("section", { class: "section", style: "margin-top:26px" }, [
      el("h2", { class: "question", texte: "Combien ai-je gagné ?" }),
      reponse,
    ]);
    if (s.gain !== null) {
      const [b, p] = marque("brut");
      bloc1.append(
        el("div", {}, [b]),
        p,
        el("p", {
          class: "section__chapeau nb",
          style: "margin-top:10px",
          texte: "Le calcul : " + s.formuleGain,
        })
      );
    }
    if (s.partiel) {
      const [b2, p2] = marque("partiel", "absent");
      bloc1.append(
        el("p", { class: "section__chapeau", style: "margin-top:10px" }, [
          b2,
          document.createTextNode(
            " " +
              s.nonValorisees.length +
              " ligne(s) sans cours ne sont pas comptées : " +
              s.nonValorisees.join(", ") +
              "."
          ),
        ]),
        p2
      );
    }
    page.append(bloc1);

    // 2. La courbe, en premier et en grand.
    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "question", texte: "Est-ce que ça progresse ?" }),
        el("p", {
          class: "section__chapeau",
          texte:
            "L'écart entre les deux courbes, c'est le gain. Quand elles se touchent, vous êtes à l'équilibre.",
        }),
        courbeSvg(jeu.courbe),
        legendeCourbe(),
      ])
    );

    // 3. Les deux rendements, expliqués sur place.
    const blocRendements = el("section", { class: "section" }, [
      el("h2", { class: "question", texte: "Et en rendement ?" }),
      el("p", {
        class: "section__chapeau",
        texte:
          "Deux façons de mesurer la même chose. Le TRI tient compte du moment de chaque versement : c'est le rendement de votre argent. Le TWRR les neutralise : c'est le rendement de la stratégie, comparable à un indice.",
      }),
    ]);
    const paire = el("div", { class: "bandeau" }, [
      el("div", { class: "bandeau__case" }, [
        el("span", { class: "etiquette", texte: "TRI — le rendement de votre argent" }),
        el("span", { class: "bandeau__valeur", texte: tauxEnPourCent(s.tri) }),
      ]),
      el("div", { class: "bandeau__case" }, [
        el("span", { class: "etiquette", texte: "TWRR — le rendement de la stratégie" }),
        el("span", { class: "bandeau__valeur", texte: tauxEnPourCent(s.twrr) }),
        el("span", {
          class: "bandeau__note",
          texte:
            s.twrrAnnualise === null ? "" : "annualisé " + tauxEnPourCent(s.twrrAnnualise),
        }),
      ]),
    ]);
    blocRendements.append(paire);
    if (s.peuSignificatif) {
      const [b, p] = marque("peuSignificatif");
      blocRendements.append(el("p", { style: "margin:12px 0 0" }, [b]), p);
    }
    page.append(blocRendements);

    // 4. Où est l'argent.
    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "question", texte: "Où est mon argent ?" }),
        anneauPoches(s.parPoche, s.valeurTotale || 1),
      ])
    );

    // 5. Les actifs, en lecture allégée.
    page.append(
      el("section", { class: "section" }, [
        el("h2", { class: "question", texte: "Que contient le portefeuille ?" }),
        el("p", {
          class: "section__chapeau",
          texte: "Le détail chiffré de chaque ligne s'ouvre depuis l'onglet « Les actifs ».",
        }),
        tableauActifs(jeu.positions, false),
      ])
    );

    return page;
  }

  // --- L'assemblage ------------------------------------------------------------------

  let direction = "A";
  let jeuChoisi = "complet";

  function dessiner() {
    const jeu = JEUX[jeuChoisi].construire();
    const s = jeu.synthese;

    // L'état des données : toujours visible, jamais en bas de page.
    const etat = document.getElementById("etat");
    etat.innerHTML = "";
    etat.append(
      el("span", {}, [
        document.createTextNode("Cours arrêtés au "),
        el("b", { texte: dateCourte(s.arreteAu) }),
      ]),
      el("span", { texte: "Source : " + s.sourceDesCours }),
      el("span", {
        texte:
          "Période : depuis le " + dateCourte(s.debut) + " (" + s.dureeEnClair + ")",
      }),
      el("span", { texte: "Poches : PEA, CTO, crypto" })
    );

    const bouton = el("button", {
      class: "bouton bouton--surveiller",
      type: "button",
      texte: "À surveiller (" + D.aSurveiller.length + ")",
    });
    const panneau = document.getElementById("panneau-surveiller");
    bouton.addEventListener("click", function () {
      panneau.hidden = !panneau.hidden;
      if (!panneau.hidden) panneau.scrollIntoView({ block: "nearest" });
    });
    etat.append(el("span", { style: "margin-left:auto" }, [bouton]));

    const corps = document.getElementById("corps");
    corps.innerHTML = "";
    corps.append(direction === "A" ? directionA(jeu) : directionB(jeu));

    document.getElementById("aide-jeu").textContent = JEUX[jeuChoisi].aide;

    document.querySelectorAll("[data-direction]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.direction === direction));
    });
    document.querySelectorAll("[data-jeu]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.jeu === jeuChoisi));
    });
  }

  /* La coquille est construite ici, et non écrite dans le HTML, pour qu'il n'existe
   * qu'UNE version du balisage : la page du dépôt et la page publiée en ligne ne
   * peuvent donc pas diverger. */
  function squelette() {
    const groupeDirections = el("div", { class: "groupe" }, [
      el("button", {
        type: "button",
        "data-direction": "A",
        "aria-pressed": "true",
        texte: "A · Le relevé",
      }),
      el("button", {
        type: "button",
        "data-direction": "B",
        "aria-pressed": "false",
        texte: "B · La lecture guidée",
      }),
    ]);

    const entete = el("header", { class: "entete" }, [
      el("div", { class: "entete__interieur" }, [
        el("h1", { class: "marque", html: "Tableau de bord <span>· maquette de l'étape 8</span>" }),
        el("div", { class: "entete__pousse commandes" }, [
          el("span", { class: "etiquette", texte: "Direction" }),
          groupeDirections,
        ]),
      ]),
      el("div", { class: "etat" }, [el("div", { class: "etat__interieur", id: "etat" })]),
    ]);

    const groupeJeux = el(
      "div",
      { class: "groupe" },
      Object.keys(JEUX).map(function (cle) {
        return el("button", {
          type: "button",
          "data-jeu": cle,
          "aria-pressed": String(cle === jeuChoisi),
          texte: JEUX[cle].nom,
        });
      })
    );

    const note = el("aside", { class: "note-maquette" }, [
      el("h2", { texte: "Ce que cette maquette sert à trancher" }),
      el("p", {
        html:
          "Les deux directions montrent <b>exactement les mêmes chiffres</b>, avec la même palette. " +
          "Elles ne diffèrent que par l'ordre de lecture et la densité. Rien n'est branché sur le moteur : " +
          "les valeurs sont inventées, mais <b>elles se recoupent</b> — la somme de la colonne « capital net " +
          "investi » fait bien le total affiché en haut, et celle des plus-values latentes aussi.",
      }),
      el("ul", {}, [
        el("li", {
          html:
            "<b>A · Le relevé.</b> Les chiffres en bandeau, puis le tableau des positions, puis la courbe. " +
            "Dense, comparable, recopiable dans un tableur. Fait le pari que tu viens vérifier un chiffre précis.",
        }),
        el("li", {
          html:
            "<b>B · La lecture guidée.</b> Chaque bloc pose une question en français et y répond en une phrase ; " +
            "la courbe passe en premier et en grand. Fait le pari que tu viens prendre la température.",
        }),
        el("li", {
          html:
            "<b>Les quatre jeux de données</b> éprouvent l'écran sur ce que tu ne détiens pas (D-62) : un " +
            "portefeuille à une ligne, un sans PEA, et le cas où la source de cours est muette sur tout — " +
            "celui qui ne doit afficher ni zéro, ni total vide.",
        }),
        el("li", {
          html:
            "<b>Le gain n'est pas la somme d'une colonne</b>, et l'écran le dit en donnant sa formule. " +
            "Il se calcule sur les montants bruts (D-21), alors que le capital net investi est net de frais " +
            "et réduit au prorata des ventes (D-12). C'est le genre d'écart qui ferait douter de tous les " +
            "chiffres s'il n'était pas expliqué là où il se voit.",
        }),
        el("li", {
          html:
            "<b>Les marques encadrées</b> (« partiel », « brut », « sans cours ») s'ouvrent au clic. C'est le " +
            "vocabulaire d'écran : jamais de jargon sans son explication à portée de clic.",
        }),
        el("li", {
          html:
            "<b>La typographie</b> n'appelle aucune police en ligne : l'application doit s'ouvrir hors réseau " +
            "(D-31). Ce sont des polices système à empattements. Embarquer un fichier de police libre reste " +
            "possible — dis-le si le rendu te paraît trop banal.",
        }),
      ]),
    ]);

    const page = el("main", { class: "page" }, [
      el("section", { class: "section", style: "margin-top:22px" }, [
        el("div", { class: "commandes" }, [
          el("span", { class: "etiquette", texte: "Jeu de données" }),
          groupeJeux,
        ]),
        el("p", { class: "section__chapeau", id: "aide-jeu", style: "margin-top:10px" }),
        panneauSurveiller(),
      ]),
      el("div", { id: "corps" }),
      note,
    ]);

    const racine = document.getElementById("app") || document.body;
    racine.append(entete, page);
  }

  function demarrer() {
    squelette();

    document.querySelectorAll("[data-direction]").forEach(function (b) {
      b.addEventListener("click", function () {
        direction = b.dataset.direction;
        dessiner();
      });
    });
    document.querySelectorAll("[data-jeu]").forEach(function (b) {
      b.addEventListener("click", function () {
        jeuChoisi = b.dataset.jeu;
        dessiner();
      });
    });

    dessiner();
  }

  /* Filet de sécurité : une maquette qui plante doit le DIRE. Une page blanche
   * laisserait croire que l'écran est vide, alors que c'est le code qui a échoué —
   * exactement l'erreur que l'application s'interdit de commettre sur les chiffres. */
  function demarrerSansCasser() {
    try {
      demarrer();
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
    document.addEventListener("DOMContentLoaded", demarrerSansCasser);
  } else {
    demarrerSansCasser();
  }
})();
