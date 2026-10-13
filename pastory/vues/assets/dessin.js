/* Le dessin de Pastory : la courbe, le globe des pays sans drapeau, les pictogrammes, le
 * planisphère, le logo — le placement des bulles « ? », et l'ouverture du livre.
 *
 * REPRIS DES MAQUETTES de l'étape 8 (maquette.js, dans l'historique git depuis l'étape 10),
 * et c'est voulu (D-93) : ces dessins ont passé neuf relectures du propriétaire, dont trois
 * arrangements de la boîte de lecture. On ne recommence pas le tour.
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

  /* AUCUNE COULEUR ICI (charte graphique, étape 9 bis). `stroke="var(--…)"` dans un ATTRIBUT
   * SVG n'est pas interprété par Chrome ni Safari ; une PROPRIÉTÉ CSS, si. Chaque trait porte
   * donc une classe, et `pastory.css` le colore avec les jetons de `theme.css`. */

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

  // ==========================================================================
  // LE GLOBE, LES PICTOGRAMMES, LE PLANISPHÈRE, LE LOGO
  // Un pays porte son drapeau en IMAGE (assets/drapeaux, posé par diversification.py) ;
  // un code sans drapeau garde ce globe — repéré, jamais confondu avec un autre. La table
  // des drapeaux dessinés est retirée à l'étape 9 bis : les onze pays qu'elle portait ont
  // tous leur fichier, et elle était la dernière couleur écrite en clair de ce script.
  // ==========================================================================

  function drapeau() {
    return svgEl("svg", { class: "fanion", viewBox: "0 0 20 14", "aria-hidden": "true" }, [
      svgEl("circle", { class: "globe", cx: 10, cy: 7, r: 5.6, "stroke-width": 1.2 }),
      svgEl("path", {
        class: "globe",
        d: "M4.4 7h11.2M10 1.4c2.5 2.7 2.5 8.5 0 11.2M10 1.4c-2.5 2.7-2.5 8.5 0 11.2",
        "stroke-width": 1,
      }),
    ]);
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

  /* LE LOGO : un livre fermé, de face, en aplat d'or ; le dos est un trait en creux, et un
   * signet à queue fendue dépasse en bas (variante « B · Signet », choisie par le
   * propriétaire à l'étape 9 bis — maquettes/logo/). Deux couleurs, l'or et la reliure ; le
   * même tracé que assets/favicon.svg. */
  function logo() {
    return svgEl("svg", { class: "logo", viewBox: "0 0 32 32", "aria-hidden": "true" }, [
      svgEl("rect", { class: "logo__plat", x: 7, y: 3, width: 18, height: 22.5, rx: 1.6 }),
      svgEl("path", { class: "logo__dos", d: "M11.2 3v22.5" }),
      svgEl("path", { class: "logo__signet", d: "M17.5 25.5h4v5.5l-2-1.9-2 1.9z" }),
    ]);
  }

  /* LE BOUTON JOUR / NUIT : une lune et un soleil au trait ; la feuille de style n'en montre
   * qu'un, selon le thème (la lune le jour, pour passer à la nuit). */
  function bascule() {
    return svgEl("svg", { class: "bascule", viewBox: "0 0 16 16", "aria-hidden": "true" }, [
      svgEl("path", { class: "bascule__lune", d: "M12.6 10.4A5.4 5.4 0 015.6 3.4a5.4 5.4 0 107 7z" }),
      svgEl("g", { class: "bascule__soleil" }, [
        svgEl("circle", { cx: 8, cy: 8, r: 3 }),
        svgEl("path", {
          d: "M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1" +
            "M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1",
        }),
      ]),
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

  /* `d` = {hauteur, aria, plafond, graduations: [{valeur, texte}], libelles: {brut, investi},
   *        points: [{d (date écrite), v (valeur), i (investi), tv, ti, te, ce}]}
   * `v` et `i` servent à PLACER les traits ; `tv`, `ti`, `te` sont les montants déjà
   * écrits par Python, `ce` la classe de signe de l'écart, et `libelles` les mots posés au
   * bout des courbes. Le gabarit (couleurs, épaisseurs, pointillés) est dans le thème. */
  function courbe(d) {
    const points = d.points;
    const libelles = d.libelles || {};
    const L = 1000;
    const H = d.hauteur || 250;
    // À droite, la place des libellés posés au bout des courbes (charte §6).
    const mg = { g: 70, d: libelles.brut ? 150 : 14, h: 14, b: 28 };
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

    // Une grille HORIZONTALE très pâle, en trait plein : en pointillé, elle se confondait avec
    // la courbe du capital net investi, elle-même en pointillé. Aucune grille verticale.
    for (const g of d.graduations) {
      svg.append(svgEl("line", { class: "grille", x1: mg.g, x2: L - mg.d, y1: y(g.valeur), y2: y(g.valeur) }));
      const etiquette = svgEl("text", { x: mg.g - 10, y: y(g.valeur) + 4.5, "text-anchor": "end" });
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

    // Aucun remplissage sous ni entre les courbes (charte §6) : deux traits, c'est tout.
    let traceBrut = "";
    for (let i = 0; i < points.length; i++) {
      traceBrut += (i ? " L " : "M ") + x(i).toFixed(1) + " " + y(points[i].v).toFixed(1);
    }

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
      svgEl("circle", { class: "point point--brut", cx: x(points.length - 1), cy: y(dernier.v), r: 3.5 })
    );

    /* LES LIBELLÉS AU BOUT DES COURBES, à la place d'une légende. Quand les deux bouts sont
     * proches, les libellés s'écartent l'un de l'autre autour de leur milieu, sans quitter
     * le cadre : ils restent lisibles, et chacun reste du côté de sa courbe. */
    if (libelles.brut && libelles.investi) {
      const ECART_MINIMAL = 22;
      let yBrut = y(dernier.v);
      let yInvesti = y(dernier.i);
      if (Math.abs(yBrut - yInvesti) < ECART_MINIMAL) {
        const milieu = (yBrut + yInvesti) / 2;
        const brutAuDessus = yBrut <= yInvesti;
        yBrut = milieu + (brutAuDessus ? -1 : 1) * ECART_MINIMAL / 2;
        yInvesti = milieu + (brutAuDessus ? 1 : -1) * ECART_MINIMAL / 2;
      }
      const borne = function (v) {
        return Math.max(mg.h + 6, Math.min(mg.h + haut, v));
      };
      const xLibelle = L - mg.d + 12;
      const tBrut = svgEl("text", {
        class: "graphique__libelle graphique__libelle--brut", x: xLibelle, y: borne(yBrut),
      });
      tBrut.textContent = libelles.brut;
      const tInvesti = svgEl("text", {
        class: "graphique__libelle graphique__libelle--investi", x: xLibelle, y: borne(yInvesti),
      });
      tInvesti.textContent = libelles.investi;
      svg.append(tBrut, tInvesti);
    }

    const viseur = svgEl("line", { class: "viseur", y1: mg.h, y2: mg.h + haut });
    const pointBrut = svgEl("circle", { class: "point point--brut", r: 4 });
    const pointInvesti = svgEl("circle", { class: "point point--investi", r: 3.5 });
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
          el("i", { class: "trait trait--brut" }),
          el("span", { texte: "Capital brut" }),
          el("b", { texte: p.tv }),
        ]),
        el("span", { class: "infobulle__ligne" }, [
          el("i", { class: "trait trait--investi" }),
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
  // LA PROJECTION (chapitre V, D-105) : le total versé, puis la courbe sans aléa ou les cinq
  // quantiles des 10 000 chemins. Des LIGNES SEULES, aucun remplissage (charte §6) ; les
  // libellés au bout des courbes ; la même boîte de lecture qui suit la souris.
  // `d` = {hauteur, aria, plafond, graduations: [{valeur, texte}], axe: [{i, texte}],
  //        series: [{classe, libelle, valeurs}], lecture: [{d, lignes: [[libellé, montant]]}]}
  // Les montants de la lecture sont déjà écrits par Python.
  // ==========================================================================

  function projection(d) {
    const series = d.series;
    const n = series[0].valeurs.length;
    // Pleine largeur : 1 200 unités, pour que les textes gardent la taille de la synthèse.
    const L = 1200;
    const H = d.hauteur || 250;
    const mg = { g: 78, d: 120, h: 14, b: 28 };
    const larg = L - mg.g - mg.d;
    const haut = H - mg.h - mg.b;
    const x = function (i) {
      return mg.g + (i / (n - 1)) * larg;
    };
    const y = function (v) {
      return mg.h + haut - (v / d.plafond) * haut;
    };

    const svg = svgEl("svg", {
      class: "graphique", viewBox: "0 0 " + L + " " + H, role: "img", "aria-label": d.aria,
    });

    for (const g of d.graduations) {
      svg.append(svgEl("line", { class: "grille", x1: mg.g, x2: L - mg.d, y1: y(g.valeur), y2: y(g.valeur) }));
      const etiquette = svgEl("text", { x: mg.g - 10, y: y(g.valeur) + 4.5, "text-anchor": "end" });
      etiquette.textContent = g.texte;
      svg.append(etiquette);
    }
    for (const repere of d.axe) {
      const t = svgEl("text", { x: x(repere.i), y: H - 6, "text-anchor": "middle" });
      t.textContent = repere.texte;
      svg.append(t);
    }

    for (const serie of series) {
      let trace = "";
      for (let i = 0; i < n; i++) {
        trace += (i ? " L " : "M ") + x(i).toFixed(1) + " " + y(serie.valeurs[i]).toFixed(1);
      }
      // La classe se compose de celle de la série : « serie--mediane », « serie--verse »…
      const classeDeLaSerie = ["serie", "serie--" + serie.classe].join(" ");
      svg.append(svgEl("path", { class: classeDeLaSerie, d: trace }));
    }

    /* Les libellés au bout des courbes, écartés d'au moins 20 unités, du haut vers le bas, sans
     * quitter le cadre. */
    const ECART_MINIMAL = 20;
    const bouts = series
      .map(function (serie) {
        return { serie: serie, y: y(serie.valeurs[n - 1]) };
      })
      .sort(function (a, b) {
        return a.y - b.y;
      });
    for (let k = 1; k < bouts.length; k++) {
      if (bouts[k].y - bouts[k - 1].y < ECART_MINIMAL) bouts[k].y = bouts[k - 1].y + ECART_MINIMAL;
    }
    const debordement = bouts.length ? bouts[bouts.length - 1].y - (mg.h + haut) : 0;
    if (debordement > 0) for (const b of bouts) b.y -= debordement;
    for (const b of bouts) {
      const classeDuLibelle = ["graphique__libelle", "graphique__libelle--" + b.serie.classe];
      const t = svgEl("text", { class: classeDuLibelle.join(" "), x: L - mg.d + 10, y: b.y });
      t.textContent = b.serie.libelle;
      svg.append(t);
    }

    const viseur = svgEl("line", { class: "viseur", y1: mg.h, y2: mg.h + haut });
    const groupeSurvol = svgEl("g", {}, [viseur]);
    groupeSurvol.style.display = "none";
    svg.append(groupeSurvol);
    const infobulle = el("div", { class: "infobulle" });
    infobulle.hidden = true;

    function montrer(evenement) {
      const boite = svg.getBoundingClientRect();
      const relatif = ((evenement.clientX - boite.left) / boite.width) * L;
      let i = Math.round(((relatif - mg.g) / larg) * (n - 1));
      i = Math.max(0, Math.min(n - 1, i));
      const p = d.lecture[i];
      groupeSurvol.style.display = "";
      viseur.setAttribute("x1", x(i));
      viseur.setAttribute("x2", x(i));
      infobulle.innerHTML = "";
      infobulle.append(el("b", { class: "infobulle__date", texte: p.d }));
      for (const ligne of p.lignes) {
        infobulle.append(
          el("span", { class: "infobulle__ligne" }, [
            el("span", { texte: ligne[0] }),
            el("b", { texte: ligne[1] }),
          ])
        );
      }
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
  // LE BRANCHEMENT : chaque `[data-dessin]` est tracé, et retracé si ses données changent.
  // L'anneau a disparu à l'étape 9 bis : la répartition par poche est une barre empilée,
  // posée en HTML par synthese.py (charte §6).
  // ==========================================================================

  const DESSINS = {
    logo: function () {
      return logo();
    },
    drapeau: drapeau,
    picto: icone,
    planisphere: planisphere,
    courbe: courbe,
    projection: projection,
    bascule: bascule,
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

  /* LE CHANGEMENT DE CHAPITRE (charte §7) : un léger glissement et un fondu, joués par la
   * classe `chapitre--anime` — seulement quand le NOM du chapitre change. Dash recrée le
   * contenu à chaque rappel, filtre compris : sans cette comparaison, chaque filtre rejouerait
   * la transition. La classe est posée dans l'observateur, avant que la page ne soit peinte :
   * aucun éclair. Revenir de la couverture compte comme un changement. */
  let dernierChapitre = null;
  let dernierePageDesCartes = null;

  function jouerUneFois(element, classe) {
    element.classList.add(classe);
    // Jouée une fois : si Dash garde l'élément au prochain rappel, rien ne se rejoue.
    element.addEventListener("animationend", function () {
      element.classList.remove(classe);
    }, { once: true });
  }

  function feuilleter() {
    const chapitre = document.querySelector(".chapitre");
    if (!chapitre) {
      if (document.querySelector(".couverture")) dernierChapitre = "couverture";
      dernierePageDesCartes = null;
      return;
    }
    if (!chapitre.__vu) {
      chapitre.__vu = true;
      const nom = chapitre.getAttribute("data-chapitre");
      if (dernierChapitre !== null && nom !== dernierChapitre) {
        jouerUneFois(chapitre, "chapitre--anime");
        dernierePageDesCartes = null;
      }
      dernierChapitre = nom;
    }
    /* LES CARTES D'ACTIFS, d'une page à l'autre : un glissement très court, dans le sens où
     * l'on feuillette (charte §7). Seulement quand le numéro de page change. */
    const cartes = document.querySelector(".cartes[data-page]");
    if (!cartes) {
      dernierePageDesCartes = null;
      return;
    }
    if (cartes.__vu) return;
    cartes.__vu = true;
    const page = Number(cartes.getAttribute("data-page"));
    if (dernierePageDesCartes !== null && page !== dernierePageDesCartes) {
      jouerUneFois(cartes, page > dernierePageDesCartes ? "cartes--suivantes" : "cartes--precedentes");
    }
    dernierePageDesCartes = page;
  }

  function toutTracer() {
    document.querySelectorAll("[data-dessin]").forEach(tracer);
    feuilleter();
  }

  new MutationObserver(toutTracer).observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["data-donnees"],
  });

  // ==========================================================================
  // L'ATTENTE (D-110)
  // Pendant une longue lecture, la page demande au serveur où il en est, et pose sa réponse
  // dans le bloc d'attente : l'étape, le détail, et la largeur de la barre. Les textes
  // arrivent DÉJÀ ÉCRITS par Python (`vues/attente.py`) : rien n'est mis en forme ici. Hors
  // d'une lecture — un simple recalcul — la barre et la note restent cachées.
  // ==========================================================================

  let attenteEnVol = false;

  function montrerLAttente(attente, etat) {
    const etape = attente.querySelector(".attente__etape");
    const piste = attente.querySelector(".attente__piste");
    const barre = attente.querySelector(".attente__barre");
    const detail = attente.querySelector(".attente__detail");
    const note = attente.querySelector(".attente__note");
    if (!etape || !piste || !barre || !detail || !note) return;
    if (!etat.en_cours) {
      etape.textContent = attente.getAttribute("data-repos");
      detail.textContent = "";
      piste.hidden = true;
      note.hidden = true;
      return;
    }
    etape.textContent = etat.etape;
    detail.textContent = etat.detail;
    piste.hidden = false;
    note.hidden = false;
    barre.style.width = etat.part + "%";
    piste.setAttribute("aria-valuenow", String(Math.round(etat.part)));
    piste.setAttribute("aria-valuetext", etat.detail);
  }

  function suivreLAttente() {
    const attente = document.querySelector(".attente");
    // Sans bloc d'attente à l'écran, aucune question n'est posée.
    if (!attente || !attente.getClientRects().length || attenteEnVol || !window.fetch) return;
    attenteEnVol = true;
    fetch(attente.getAttribute("data-adresse"), { cache: "no-store" })
      .then(function (reponse) { return reponse.ok ? reponse.json() : null; })
      .then(function (etat) {
        const present = document.querySelector(".attente");
        if (etat && present) montrerLAttente(present, etat);
      })
      .catch(function () {})
      .then(function () { attenteEnVol = false; });
  }

  window.setInterval(suivreLAttente, 400);

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

  /* Deux déclencheurs : le bouton « ? », qui s'ouvre au clic, et la MARQUE EXPLIQUÉE
   * (« Peu fiable »…), qui s'ouvre aussi au survol et au clavier — une marque sans explication à
   * portée de souris inquiète sans rien apprendre. Une bulle ouverte par un clic est
   * « épinglée » : quitter la marque ne la ferme pas. */
  const DECLENCHEURS = ".aide, .mot--explique";

  function ouvrirLaBulle(bouton, epinglee) {
    const bulle = document.getElementById(bouton.getAttribute("aria-controls"));
    if (!bulle) return;
    fermerLaBulle();
    bulle.hidden = false;
    bouton.setAttribute("aria-expanded", "true");
    bulleOuverte = { bouton: bouton, bulle: bulle, epinglee: epinglee };
    placerLaBulle(bouton, bulle);
  }

  document.addEventListener("click", function (evenement) {
    const bouton = evenement.target.closest && evenement.target.closest(DECLENCHEURS);
    if (!bouton) {
      // Un clic dans la bulle ouverte ne la ferme pas : on peut y sélectionner le texte.
      if (bulleOuverte && bulleOuverte.bulle.contains(evenement.target)) return;
      fermerLaBulle();
      return;
    }
    const memeBouton = bulleOuverte && bulleOuverte.bouton === bouton;
    if (memeBouton && bulleOuverte.epinglee) {
      fermerLaBulle();
      return;
    }
    if (memeBouton) {
      bulleOuverte.epinglee = true; // ouverte au survol, le clic la garde
      return;
    }
    ouvrirLaBulle(bouton, true);
  });
  document.addEventListener("mouseover", function (evenement) {
    const marque = evenement.target.closest && evenement.target.closest(".mot--explique");
    if (!marque || (bulleOuverte && bulleOuverte.bouton === marque)) return;
    if (bulleOuverte && bulleOuverte.epinglee) return;
    ouvrirLaBulle(marque, false);
  });
  document.addEventListener("mouseout", function (evenement) {
    const marque = evenement.target.closest && evenement.target.closest(".mot--explique");
    if (!marque || marque.contains(evenement.relatedTarget)) return;
    if (bulleOuverte && bulleOuverte.bouton === marque && !bulleOuverte.epinglee) fermerLaBulle();
  });
  document.addEventListener("focusin", function (evenement) {
    const marque = evenement.target.closest && evenement.target.closest(".mot--explique");
    if (marque && !(bulleOuverte && bulleOuverte.bouton === marque)) ouvrirLaBulle(marque, false);
  });
  document.addEventListener("focusout", function (evenement) {
    const marque = evenement.target.closest && evenement.target.closest(".mot--explique");
    if (marque && bulleOuverte && bulleOuverte.bouton === marque && !bulleOuverte.epinglee) {
      fermerLaBulle();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermerLaBulle();
    const marque = e.target.closest && e.target.closest(".mot--explique");
    if (marque && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      ouvrirLaBulle(marque, true);
    }
  });
  window.addEventListener("resize", fermerLaBulle);
  window.addEventListener("scroll", fermerLaBulle, true);

  // ==========================================================================
  // L'OUVERTURE DU LIVRE (charte §7)
  // Un seul moment marquant, rejoué À CHAQUE ouverture (retour du propriétaire, étape 9 bis) :
  // au clic sur « Ouvrir le livre », un voile brun — la couverture — est posé par-dessus la
  // page et s'efface vers la gauche en moins de 800 ms. Le clic, lui, poursuit son chemin :
  // Dash dessine le chapitre I DESSOUS, tout de suite. Le voile ne capte pas la souris et
  // disparaît de lui-même : il ne retarde ni ne bloque rien. Avec `prefers-reduced-motion`, la
  // feuille de style en fait un simple fondu.
  // ==========================================================================

  document.addEventListener("click", function (evenement) {
    const bouton = evenement.target.closest && evenement.target.closest(".ouvrir-le-livre");
    if (!bouton) return;
    const voile = el("div", { class: "voile-d-ouverture", "aria-hidden": "true" });
    document.body.append(voile);
    voile.addEventListener("animationend", function () {
      voile.remove();
    });
    // Le filet, si l'animation ne se termine pas (onglet masqué, animations coupées).
    window.setTimeout(function () {
      voile.remove();
    }, 1500);
  });

  // ==========================================================================
  // LA LECTURE DE NUIT (D-100, charte §2.8)
  // Le thème est posé avant le premier affichage par application.py. Ici : le bouton jour /
  // nuit, qui change le thème et retient le choix ; et, tant qu'aucun choix n'est fait, le
  // réglage du système, suivi s'il change en cours de route. Aucun appel à Dash : rien ne se
  // recalcule, seules les couleurs changent.
  // ==========================================================================

  const CLE_THEME = "pastory-theme";

  function themeActuel() {
    return document.documentElement.getAttribute("data-theme") === "sombre" ? "sombre" : "clair";
  }

  function decrireLesBascules() {
    const nuit = themeActuel() === "sombre";
    document.querySelectorAll(".bascule-theme").forEach(function (bouton) {
      bouton.setAttribute("aria-pressed", nuit ? "true" : "false");
      bouton.title = nuit ? "Passer à la lecture de jour" : "Passer à la lecture de nuit";
    });
  }

  function poserLeTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    decrireLesBascules();
  }

  document.addEventListener("click", function (evenement) {
    const bouton = evenement.target.closest && evenement.target.closest(".bascule-theme");
    if (!bouton) return;
    const theme = themeActuel() === "sombre" ? "clair" : "sombre";
    try {
      localStorage.setItem(CLE_THEME, theme);
    } catch (e) {
      // Sans stockage, le choix vaut pour cette page seulement : c'est sans conséquence.
    }
    poserLeTheme(theme);
  });

  if (window.matchMedia) {
    const systeme = window.matchMedia("(prefers-color-scheme: dark)");
    const suivre = function () {
      let choix = null;
      try {
        choix = localStorage.getItem(CLE_THEME);
      } catch (e) {
        choix = null;
      }
      if (!choix) poserLeTheme(systeme.matches ? "sombre" : "clair");
    };
    if (systeme.addEventListener) systeme.addEventListener("change", suivre);
  }

  new MutationObserver(decrireLesBascules).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
