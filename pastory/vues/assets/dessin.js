/* Le dessin de Pastory : la courbe, les anneaux, les drapeaux, les pictogrammes, le
 * planisphère, le logo — et le placement des bulles « ? ».
 *
 * REPRIS DE maquettes/maquette.js, et c'est voulu (D-93) : ces dessins ont passé neuf
 * relectures du propriétaire, dont trois arrangements de la boîte de lecture. On ne
 * recommence pas le tour.
 *
 * CE QUE CE SCRIPT NE FAIT PAS : il ne calcule aucun chiffre et n'en met aucun en forme.
 * Python pose dans l'attribut `data-donnees` d'un élément `[data-dessin]` les valeurs qui
 * servent à placer les traits ET les libellés déjà écrits ; le script trace, c'est tout.
 * Un montant affiché ici vient toujours de pastory/vues/format.py.
 *
 * Quand Dash change les données d'un élément (un filtre, une période), l'observateur le
 * voit et redessine.
 */

(function () {
  "use strict";

  /* LA PALETTE, EN VALEURS LITTÉRALES — et c'est une nécessité, pas une négligence :
   * `stroke="var(--poche-1)"` dans un ATTRIBUT SVG n'est pas interprété par Chrome ni
   * Safari. Une couleur posée en attribut s'écrit en clair ; une couleur posée en CSS
   * passe par la variable. Un test vérifie que ces valeurs concordent avec pastory.css. */
  const COULEURS = {
    papier: "#ece3d0",
    surface: "#f3ecdd",
    encreTresDouce: "#6f6559",
    courbeBrut: "#1d6c93",
    courbeInvesti: "#665c51",
    absent: "#ada08a",
  };

  const NS = "http://www.w3.org/2000/svg";

  function el(balise, attributs, enfants) {
    const noeud = document.createElement(balise);
    for (const cle in attributs || {}) {
      const valeur = attributs[cle];
      if (valeur === null || valeur === undefined || valeur === false) continue;
      if (cle === "class") noeud.className = valeur;
      else if (cle === "texte") noeud.textContent = valeur;
      else noeud.setAttribute(cle, valeur);
    }
    for (const enfant of [].concat(enfants || [])) {
      if (enfant === null || enfant === undefined) continue;
      noeud.append(enfant);
    }
    return noeud;
  }

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

  let compteurIds = 0;

  // ==========================================================================
  // LES DRAPEAUX, LES PICTOGRAMMES, LE PLANISPHÈRE, LE LOGO
  // Dessinés en SVG, dans le dépôt : les drapeaux en emoji ne s'affichent pas sous
  // Windows, et une image distante est interdite (D-31). Ce sont des drapeaux
  // SIMPLIFIÉS : ils servent à repérer une ligne, pas à représenter un pays.
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

  /** Un drapeau simplifié, ou un globe quand le pays n'a pas de drapeau dessiné. */
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

  /* LE PLANISPHÈRE DES ZONES. Une zone n'a pas de drapeau : chaque zone porte le même
   * planisphère, avec SA part du monde remplie d'encre. Projection plate, boîte 26 × 17 :
   *   x = 13 + longitude × 0,0694 ;  y = 1,5 + (75 − latitude) × 0,1077.
   * Le Japon et la Nouvelle-Zélande sont dessinés PLUS GRANDS que l'échelle : à l'échelle,
   * ils font un pixel et disparaissent, y compris quand c'est eux qu'on allume. La carte
   * SITUE la zone, elle ne la délimite pas (conception §3.2). */
  const CONTINENTS = {
    amNord:
      "M1.6 2.3 L6.1 2 L8.8 3.1 L9.2 4.4 L8.5 4.8 L8.1 5.2 L7.7 5.9 L7.5 6.8 L6.8 6.5" +
      " L6.9 7.3 L7.6 8.6 L7.2 8.7 L6.4 7.8 L5.7 7.4 L5 6.4 L4.4 5.3 L4.3 4.3 L3.6 3.3" +
      " L2.2 3.1 Z",
    amSud:
      "M7.6 8.6 L8.7 8.4 L9.2 9 L9.5 9.6 L10.6 10.5 L10.3 11.2 L10 12.1 L9.3 13.3" +
      " L8.7 13.8 L8.3 15.5 L7.8 14.7 L8 13.4 L7.6 11.2 L7.4 9.8 Z",
    europe:
      "M12.4 5.75 L12.4 5.15 L13 4.95 L12.75 4.4 L13.3 3.95 L13.75 3.5 L14.45 2" +
      " L15.15 2.3 L14.95 3.4 L15.15 4.6 L14.7 5.65 L14.35 5.3 L13.7 4.95 L13.25 5.3 Z" +
      " M12.5 3.5 L12.9 3.8 L12.95 4.4 L12.68 4.45 L12.7 3.95 L12.4 3.75 Z",
    afrique:
      "M12.35 6.4 L13.7 6.1 L15.15 6.4 L15.6 7.3 L16.5 8.4 L15.95 9.5 L15.8 10.4" +
      " L15.5 11.7 L15.15 12.8 L14.4 13.4 L14 12.3 L13.8 10.9 L13.55 9.7 L13.2 9.05" +
      " L12.3 9 L11.8 7.9 L11.9 6.9 Z",
    asie:
      "M15 5.5 L16.1 5.1 L17.2 2 L21.3 1.7 L25.1 2.5 L24.1 3.7 L22.7 4.2 L22 5.7" +
      " L21.5 6.2 L20.9 7.2 L20.6 8.4 L20.2 9.4 L19.8 8.5 L19.3 7.2 L18.6 7.9" +
      " L18.4 8.8 L18.05 7.5 L17.7 6.9 L17 6.9 L17.15 7.3 L16.15 8.25 L15.75 7.3" +
      " L15.45 6 L15.1 5.6 Z",
    indonesie:
      "M19.6 8.6 L19.95 8.7 L20.5 9.9 L21.15 10.05 L21.1 10.45 L20.3 10.3 L19.75 9.2 Z",
    japon: "M23.2 4.1 L23.65 4.45 L23.2 5.25 L22.8 6 L22.5 6.7 L22 6.5 L22.4 5.7 L22.8 4.9 Z",
    oceanie:
      "M22.1 10.85 L22.45 11.35 L22.9 10.8 L23.6 12.5 L23.1 13.7 L22.6 13.35" +
      " L21.05 13.05 L20.9 11.95 Z" +
      " M24.5 13.85 L24.85 14.25 L24.8 14.85 L24.45 14.4 Z",
  };

  function planisphere(terres) {
    const fond = [];
    const dessus = [];
    for (const nom of Object.keys(CONTINENTS)) {
      const allumee = (terres || []).indexOf(nom) >= 0;
      (allumee ? dessus : fond).push(
        svgEl("path", {
          class: allumee ? "planisphere__zone" : "planisphere__terre",
          d: CONTINENTS[nom],
        })
      );
    }
    // Les terres allumées passent en dernier : là où deux tracés se touchent, c'est la
    // zone de la ligne qui doit rester lisible.
    return svgEl(
      "svg",
      { class: "planisphere", viewBox: "0 0 26 17", "aria-hidden": "true" },
      fond.concat(dessus)
    );
  }

  /* LE LOGO, TEMPORAIRE : une page, et dessus une valeur qui monte. Clair sur le bandeau
   * d'encre, et son trait en ENCRE, pas en sauge : la sauge veut dire « gain » partout
   * ailleurs, et un logo vert se lirait comme un état du portefeuille. */
  function logo() {
    return svgEl("svg", { class: "logo", viewBox: "0 0 20 20", "aria-hidden": "true" }, [
      svgEl("rect", { class: "logo__papier", x: 1.5, y: 1.5, width: 17, height: 17, rx: 4.8 }),
      svgEl("path", { class: "logo__trait", d: "M5.4 14 L8.2 10.8 L10.6 12.3 L14.3 7.4" }),
      svgEl("circle", { class: "logo__point", cx: 14.3, cy: 7.4, r: 2 }),
    ]);
  }

  // ==========================================================================
  // LA COURBE, ET LA BOÎTE DE LECTURE QUI SUIT LA SOURIS
  // ==========================================================================

  /* Poser sur un axe la boîte qui suit la souris : décalée du curseur, et basculée du
   * côté opposé plutôt que coupée près d'un bord. Les deux axes suivent la même règle. */
  function placerSurUnAxe(pointe, mesure, libre, ecart) {
    let pose = pointe + ecart;
    if (pose + mesure > libre) pose = pointe - ecart - mesure;
    return Math.max(0, Math.min(pose, Math.max(0, libre - mesure)));
  }

  const ECART_INFOBULLE = 16;

  function placerLInfobulle(infobulle, boite, evenement) {
    const largeur = infobulle.offsetWidth || 210;
    const hauteur = infobulle.offsetHeight || 86;
    const cx = evenement.clientX - boite.left;
    const cy = evenement.clientY - boite.top;
    infobulle.style.left = placerSurUnAxe(cx, largeur, boite.width, ECART_INFOBULLE) + "px";
    infobulle.style.top = placerSurUnAxe(cy, hauteur, boite.height, ECART_INFOBULLE) + "px";
  }

  /* `d` = {hauteur, aria, plafond, graduations: [{valeur, texte}],
   *        points: [{d (date écrite), v (valeur), i (investi), tv, ti, te, ce}]}
   * `v` et `i` servent à PLACER les traits ; `tv`, `ti`, `te` sont les montants déjà
   * écrits par Python, et `ce` la classe de signe de l'écart. */
  function courbe(d) {
    const points = d.points;
    const L = 1000;
    const H = d.hauteur || 250;
    const mg = { g: 62, d: 14, h: 12, b: 24 };
    const larg = L - mg.g - mg.d;
    const haut = H - mg.h - mg.b;
    const plafond = d.plafond;

    const x = function (i) {
      return mg.g + (i / (points.length - 1)) * larg;
    };
    const y = function (v) {
      return mg.h + haut - (v / plafond) * haut;
    };

    const svg = svgEl("svg", {
      class: "graphique", viewBox: "0 0 " + L + " " + H, role: "img", "aria-label": d.aria,
    });

    // La grille est un trait PLEIN très pâle : en pointillé, elle se confondait avec la
    // courbe du capital net investi, qui est elle-même en pointillé.
    for (const g of d.graduations) {
      svg.append(svgEl("line", { class: "grille", x1: mg.g, x2: L - mg.d, y1: y(g.valeur), y2: y(g.valeur) }));
      const etiquette = svgEl("text", { x: mg.g - 8, y: y(g.valeur) + 3.5, "text-anchor": "end" });
      etiquette.textContent = g.texte;
      svg.append(etiquette);
    }

    const combien = Math.min(5, points.length);
    for (let k = 0; k < combien; k++) {
      const i = Math.round((k / (combien - 1)) * (points.length - 1));
      const t = svgEl("text", {
        x: x(i), y: H - 6,
        "text-anchor": k === 0 ? "start" : k === combien - 1 ? "end" : "middle",
      });
      t.textContent = points[i].d;
      svg.append(t);
    }

    let traceBrut = "";
    for (let i = 0; i < points.length; i++) {
      traceBrut += (i ? " L " : "M ") + x(i).toFixed(1) + " " + y(points[i].v).toFixed(1);
    }
    svg.append(
      svgEl("path", {
        class: "aire-brut",
        d: traceBrut + " L " + x(points.length - 1).toFixed(1) + " " + y(0) +
          " L " + x(0).toFixed(1) + " " + y(0) + " Z",
      })
    );

    // Le capital net investi monte en escalier : il ne bouge qu'aux opérations.
    let traceInvesti = "";
    for (let i = 0; i < points.length; i++) {
      const px = x(i).toFixed(1);
      if (i === 0) traceInvesti = "M " + px + " " + y(points[i].i).toFixed(1);
      else {
        traceInvesti += " L " + px + " " + y(points[i - 1].i).toFixed(1) +
          " L " + px + " " + y(points[i].i).toFixed(1);
      }
    }
    svg.append(svgEl("path", { class: "serie serie--investi", d: traceInvesti }));
    svg.append(svgEl("path", { class: "serie serie--brut", d: traceBrut }));

    const dernier = points[points.length - 1];
    svg.append(
      svgEl("circle", {
        cx: x(points.length - 1), cy: y(dernier.v), r: 3.5,
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

    /* LA LECTURE AU SURVOL SUIT LA SOURIS, SUR LE GRAPHIQUE — l'arbitrage du propriétaire,
     * gardé avec ses raisons au §3.2 du contrat : décalée du curseur (16 px), basculée près
     * d'un bord, étroite et verticale, et `pointer-events: none` en CSS. */
    const infobulle = el("div", { class: "infobulle" });
    infobulle.hidden = true;

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
      pointBrut.setAttribute("cy", y(p.v));
      pointInvesti.setAttribute("cx", x(i));
      pointInvesti.setAttribute("cy", y(p.i));

      infobulle.innerHTML = "";
      const lignes = [
        el("b", { class: "infobulle__date", texte: p.d }),
        el("span", { class: "infobulle__ligne" }, [
          el("i", { style: "border-top-color: var(--courbe-brut)" }),
          el("span", { texte: "Capital brut" }),
          el("b", { texte: p.tv }),
        ]),
        el("span", { class: "infobulle__ligne" }, [
          el("i", { style: "border-top-color: var(--courbe-investi); border-top-style: dashed" }),
          el("span", { texte: "Capital net investi" }),
          el("b", { texte: p.ti }),
        ]),
        el("span", { class: "infobulle__ligne infobulle__ecart" }, [
          el("span", { texte: "Écart" }),
          el("b", { class: p.ce || null, texte: p.te }),
        ]),
        // Un jour où un actif n'a pas de cours : la valeur est celle des seuls actifs cotés.
        p.tp ? el("span", { class: "infobulle__ligne reference", texte: p.tp }) : null,
      ];
      // `append(null)` écrirait le mot « null » : seules les lignes présentes sont posées.
      for (const ligne of lignes) if (ligne) infobulle.append(ligne);
      infobulle.hidden = false;
      placerLInfobulle(infobulle, boite, evenement);
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

    return [svg, infobulle];
  }

  // ==========================================================================
  // L'ANNEAU
  // En ARCS EXPLICITES, un chemin par part : on peut lire le code et savoir ce qui
  // sera dessiné. Les parts « absent » sont hachurées : ce qui manque se voit, sans se
  // confondre avec un poste réel. AUCUN CHIFFRE N'EST ÉCRIT SUR L'ANNEAU, hors le total
  // au centre : le classement chiffré à côté fait foi.
  // `d` = {taille, centre (texte), sous (texte), parts: [{montant, couleur, absent}]}
  // ==========================================================================

  function anneau(d) {
    const parts = d.parts;
    const taille = d.taille;
    const total = parts.reduce(function (s, p) {
      return s + p.montant;
    }, 0);
    if (total <= 0) return null;

    const epaisseur = Math.round(taille * 0.15);
    const r = taille / 2 - epaisseur / 2 - 1;
    const centre = taille / 2;
    const ECART_DEGRES = 1.2;

    const idHachures = "hachures-" + ++compteurIds;
    const motif = svgEl(
      "pattern",
      { id: idHachures, patternUnits: "userSpaceOnUse", width: 5, height: 5, patternTransform: "rotate(45)" },
      [
        svgEl("rect", { width: 5, height: 5, fill: COULEURS.papier }),
        svgEl("line", { x1: 0, y1: 0, x2: 0, y2: 5, stroke: COULEURS.absent, "stroke-width": 2.6 }),
      ]
    );

    const svg = svgEl(
      "svg",
      { viewBox: "0 0 " + taille + " " + taille, width: taille, height: taille, class: "anneau", "aria-hidden": "true" },
      [svgEl("defs", {}, [motif])]
    );

    function point(angleDegres) {
      const rad = ((angleDegres - 90) * Math.PI) / 180;
      return [centre + r * Math.cos(rad), centre + r * Math.sin(rad)];
    }

    let angle = 0;
    for (const part of parts) {
      const ouverture = (part.montant / total) * 360;
      const couleur = part.absent ? "url(#" + idHachures + ")" : part.couleur;
      if (ouverture >= 359.9) {
        svg.append(svgEl("circle", { cx: centre, cy: centre, r: r, fill: "none", stroke: couleur, "stroke-width": epaisseur }));
      } else if (ouverture > ECART_DEGRES) {
        const debutArc = angle + ECART_DEGRES / 2;
        const finArc = angle + ouverture - ECART_DEGRES / 2;
        const p1 = point(debutArc);
        const p2 = point(finArc);
        svg.append(
          svgEl("path", {
            d: "M " + p1[0].toFixed(2) + " " + p1[1].toFixed(2) + " A " + r + " " + r + " 0 " +
              (finArc - debutArc > 180 ? 1 : 0) + " 1 " + p2[0].toFixed(2) + " " + p2[1].toFixed(2),
            fill: "none", stroke: couleur, "stroke-width": epaisseur,
          })
        );
      } else if (ouverture > 0) {
        // Une part minuscule reste visible : un trait, plutôt que rien du tout.
        const p1 = point(angle);
        const p2 = point(angle + ouverture);
        svg.append(
          svgEl("path", {
            d: "M " + p1[0].toFixed(2) + " " + p1[1].toFixed(2) + " L " + p2[0].toFixed(2) + " " + p2[1].toFixed(2),
            fill: "none", stroke: part.absent ? COULEURS.absent : part.couleur,
            "stroke-width": epaisseur, "stroke-linecap": "butt",
          })
        );
      }
      angle += ouverture;
    }

    if (d.centre) {
      const t1 = svgEl("text", { x: centre, y: centre + 1, "text-anchor": "middle", class: "anneau__centre" });
      t1.textContent = d.centre;
      const t2 = svgEl("text", { x: centre, y: centre + 15, "text-anchor": "middle", class: "anneau__sous" });
      t2.textContent = d.sous || "au total";
      svg.append(t1, t2);
    }
    return svg;
  }

  // ==========================================================================
  // LE BRANCHEMENT : chaque `[data-dessin]` est tracé, et retracé si ses données changent
  // ==========================================================================

  const DESSINS = {
    logo: function () {
      return logo();
    },
    drapeau: drapeau,
    picto: icone,
    planisphere: planisphere,
    courbe: courbe,
    anneau: anneau,
  };

  function tracer(noeud) {
    const donnees = noeud.getAttribute("data-donnees");
    if (noeud.__trace === donnees) return;
    noeud.__trace = donnees;
    const fabrique = DESSINS[noeud.getAttribute("data-dessin")];
    noeud.innerHTML = "";
    if (!fabrique) return;
    let resultat;
    try {
      resultat = fabrique(JSON.parse(donnees));
    } catch (erreur) {
      // Un dessin qui échoue le DIT, plutôt que de laisser un vide qui passerait pour une
      // absence de données.
      resultat = el("span", { class: "reference", texte: "Ce dessin n'a pas pu être tracé." });
      console.error(erreur);
    }
    for (const enfant of [].concat(resultat || [])) noeud.append(enfant);
  }

  function toutTracer() {
    document.querySelectorAll("[data-dessin]").forEach(tracer);
  }

  new MutationObserver(toutTracer).observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["data-donnees"],
  });

  // ==========================================================================
  // LES BULLES « ? »
  // Posées en `position: fixed`, avec des coordonnées calculées depuis le bouton puis
  // RAMENÉES DANS L'ÉCRAN : la correction d'un défaut vu à l'étape 8, où la moitié du
  // texte sortait de la page.
  // ==========================================================================

  let bulleOuverte = null;

  function placerLaBulle(bouton, bulle) {
    const marge = 10;
    const cadreBouton = bouton.getBoundingClientRect();
    const cadreBulle = bulle.getBoundingClientRect();
    let gauche = cadreBouton.left + cadreBouton.width / 2 - cadreBulle.width / 2;
    gauche = Math.max(marge, Math.min(gauche, window.innerWidth - cadreBulle.width - marge));
    let haut = cadreBouton.bottom + 7;
    if (haut + cadreBulle.height > window.innerHeight - marge) {
      haut = Math.max(marge, cadreBouton.top - cadreBulle.height - 7);
    }
    bulle.style.left = Math.round(gauche) + "px";
    bulle.style.top = Math.round(haut) + "px";
  }

  function fermerLaBulle() {
    if (!bulleOuverte) return;
    bulleOuverte.bouton.setAttribute("aria-expanded", "false");
    bulleOuverte.bulle.hidden = true;
    bulleOuverte = null;
  }

  document.addEventListener("click", function (evenement) {
    const bouton = evenement.target.closest && evenement.target.closest(".aide");
    if (!bouton) {
      // Un clic dans la bulle ouverte ne la ferme pas : on peut y sélectionner le texte.
      if (bulleOuverte && bulleOuverte.bulle.contains(evenement.target)) return;
      fermerLaBulle();
      return;
    }
    const bulle = document.getElementById(bouton.getAttribute("aria-controls"));
    if (!bulle) return;
    const dejaOuverte = bulleOuverte && bulleOuverte.bouton === bouton;
    fermerLaBulle();
    if (dejaOuverte) return;
    bulle.hidden = false;
    bouton.setAttribute("aria-expanded", "true");
    bulleOuverte = { bouton: bouton, bulle: bulle };
    placerLaBulle(bouton, bulle);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermerLaBulle();
  });
  window.addEventListener("resize", fermerLaBulle);
  window.addEventListener("scroll", fermerLaBulle, true);
})();
