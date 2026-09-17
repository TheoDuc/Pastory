"""
Inventaire STRUCTUREL d'un export pytr (all_events.json + account_transactions.csv).

Usage :
    python scripts/inventaire_structure.py data
    python scripts/inventaire_structure.py data_tiers

Ce script ne fait que LIRE. Il n'écrit aucun fichier.

Il n'affiche AUCUNE valeur personnelle : ni montant, ni quantité, ni nom,
ni IBAN, ni numéro de compte, ni identifiant d'événement ou de plan.
Il affiche seulement :
  - des comptages ;
  - des noms de champs et des libellés d'interface (ex. "Gebühr") ;
  - des catégories (ex. "numérique", "positif", "négatif").
Les comptes sont renommés "compte A", "compte B"... dans leur ordre d'apparition.
Tout texte contenant un chiffre ou un @ est masqué par «masqué».
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
NOMBRE_RE = re.compile(r"^[+\-−]?\s*[\d.,\s]+\s*(€|%)?$")

# Libellés de lignes qui désignent une poche ou un moyen de paiement.
LIBELLES_POCHE = {"Portfolio", "Konto", "Depot", "Zahlung"}
# Libellés dont la valeur est une catégorie technique (jamais une donnée personnelle) :
# seules ces valeurs-là sont affichées en clair, les autres sont réduites à une catégorie.
LIBELLES_VALEUR_AFFICHABLE = LIBELLES_POCHE | {"Ordertyp", "Ereignistyp", "Gebühr", "An", "Von",
                                              "Status", "Typ", "Art", "Ereignis"}


def sur(texte):
    """Renvoie le texte s'il ne peut pas contenir de donnée personnelle, sinon «masqué»."""
    if texte is None:
        return "(vide)"
    if not isinstance(texte, str):
        return f"({type(texte).__name__})"
    if re.search(r"[\d@]", texte) or len(texte) > 60:
        return "«masqué»"
    return texte


def categorie_valeur(texte, affichable):
    """Classe une valeur affichée sans la révéler (sauf libellé technique autorisé)."""
    if texte is None:
        return "(vide)"
    t = str(texte).replace("\xa0", " ").strip()
    if NOMBRE_RE.match(t):
        return "numérique"
    if "×" in t and re.search(r"\d", t):
        return "texte 'quantité × prix'"
    return sur(t) if affichable else "texte"


def masquer_isin(texte):
    return ISIN_RE.sub("<ISIN>", texte or "")


def isin_de(evt):
    """Cherche un code ISIN dans les champs structurés (pas dans les textes)."""
    icone = ISIN_RE.search(evt.get("icon") or "")
    entete = None
    for s in (evt.get("details") or {}).get("sections", []):
        if s.get("type") == "header":
            action = s.get("action") or {}
            if action.get("type") == "instrumentDetail":
                entete = action.get("payload")
    return (icone.group(0) if icone else None), entete


def parcourir_sections(sections, chemin, lignes, cles):
    """Collecte les libellés (titre de section > titre de ligne [type]) et la valeur-catégorie."""
    for s in sections or []:
        titre_s = "(en-tête)" if s.get("type") == "header" else sur(s.get("title"))
        donnees = s.get("data")
        if isinstance(donnees, list):
            for ligne in donnees:
                if not isinstance(ligne, dict):
                    continue
                detail = ligne.get("detail")
                if isinstance(detail, dict):
                    typ = detail.get("type")
                    # Le titre d'un élément imbriqué est un nom d'actif ou de personne : masqué.
                    titre_l = "«nom»" if typ in ("embeddedTimelineItem",) else sur(ligne.get("title"))
                    affichable = typ == "status" or ligne.get("title") in LIBELLES_VALEUR_AFFICHABLE
                    cle = f"{chemin}{titre_s} > {titre_l} [{typ}]"
                    lignes[cle].add(categorie_valeur(detail.get("text"), affichable))
                    action = detail.get("action") or {}
                    charge = action.get("payload")
                    if isinstance(charge, dict):
                        cles.update(f"action {action.get('type')} → {k}" for k in charge.keys())
                        if "sections" in charge:
                            parcourir_sections(charge["sections"], f"{chemin}{titre_s} > {titre_l} ⤷ ", lignes, cles)
                        for sous in ("contextParams",):
                            if isinstance(charge.get(sous), dict):
                                cles.update(f"action {action.get('type')} → {sous}.{k}" for k in charge[sous])
        elif isinstance(donnees, dict):
            cles.update(f"section {s.get('type')} → data.{k}" for k in donnees.keys())


def lire_evenements(dossier):
    with open(dossier / "all_events.json", encoding="utf-8") as f:
        evts = json.load(f)
    return sorted(evts, key=lambda e: e.get("timestamp") or "")


def date_de(evt):
    return datetime.strptime(evt["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")


def titre(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main(dossier):
    dossier = Path(dossier)
    evts = lire_evenements(dossier)
    nom_type = lambda e: e.get("eventType") or "(null)"

    # --- Comptes anonymisés -------------------------------------------------
    alias = {}
    for e in evts:
        n = e.get("cashAccountNumber")
        if n and n not in alias:
            alias[n] = f"compte {chr(ord('A') + len(alias))}"
    compte = lambda e: alias.get(e.get("cashAccountNumber"), "(aucun compte)")

    titre(f"1. TYPES D'ÉVÉNEMENTS ({len(evts)} événements)")
    par_type = Counter(nom_type(e) for e in evts)
    for t, n in sorted(par_type.items()):
        avec_montant = sum(1 for e in evts if nom_type(e) == t and e.get("amount"))
        statuts = Counter(e.get("status") for e in evts if nom_type(e) == t)
        sources = Counter(e.get("source") for e in evts if nom_type(e) == t)
        cachés = sum(1 for e in evts if nom_type(e) == t and (e.get("hidden") or e.get("deleted")))
        print(f"{t:45} {n:4}  avec montant: {avec_montant:3}  statuts: {dict(statuts)}  "
              f"source: {dict(sources)}  caché/supprimé: {cachés}")

    titre("2. COMPTES × TYPES (signe du montant : + / − / 0)")
    matrice = defaultdict(Counter)
    for e in evts:
        v = (e.get("amount") or {}).get("value")
        signe = "sans montant" if v is None else ("+" if v > 0 else "−" if v < 0 else "0")
        matrice[compte(e)][f"{nom_type(e)} ({signe})"] += 1
    for c in sorted(matrice):
        print(f"\n{c}")
        for t, n in sorted(matrice[c].items()):
            print(f"    {t:55} {n}")

    titre("3. DEVISES ET SOUS-MONTANTS")
    print("devises:", dict(Counter((e.get("amount") or {}).get("currency") for e in evts if e.get("amount"))))
    print("subAmount renseigné par type:",
          dict(Counter(nom_type(e) for e in evts if e.get("subAmount"))))

    titre("4. FICHE PAR TYPE : où sont les informations")
    for t in sorted(par_type):
        groupe = [e for e in evts if nom_type(e) == t]
        lignes, cles = defaultdict(set), Counter()
        for e in groupe:
            parcourir_sections((e.get("details") or {}).get("sections"), "", lignes, cles)
        isin_icone = sum(1 for e in groupe if isin_de(e)[0])
        isin_entete = sum(1 for e in groupe if isin_de(e)[1])
        coherent = sum(1 for e in groupe if isin_de(e)[0] and isin_de(e)[0] == isin_de(e)[1])
        print(f"\n--- {t} ({len(groupe)}) ---")
        print(f"  comptes         : {dict(Counter(compte(e) for e in groupe))}")
        print(f"  montant (amount.value) présent : {sum(1 for e in groupe if e.get('amount'))}/{len(groupe)}")
        print(f"  ISIN dans icon  : {isin_icone}/{len(groupe)} ; dans en-tête instrumentDetail : "
              f"{isin_entete}/{len(groupe)} ; identiques : {coherent}")
        print(f"  préfixes ISIN   : {dict(Counter((isin_de(e)[0] or isin_de(e)[1] or '--')[:2] for e in groupe))}")
        print(f"  sous-titres     : {dict(Counter(sur(e.get('subtitle')) for e in groupe))}")
        print(f"  icônes          : {dict(Counter(masquer_isin(e.get('icon')) for e in groupe))}")
        if lignes:
            print("  lignes affichées (section > libellé [type] : catégories de valeur) :")
            for cle in sorted(lignes):
                print(f"      {cle} : {sorted(lignes[cle])}")
        if cles:
            print("  champs structurés dans les actions :")
            for cle, n in sorted(cles.items()):
                print(f"      {cle} ({n})")

    titre("5. POCHES : valeurs des libellés Portfolio / Konto / Zahlung par compte et type")
    poches = defaultdict(Counter)
    for e in evts:
        for s in (e.get("details") or {}).get("sections", []):
            if isinstance(s.get("data"), list):
                for ligne in s["data"]:
                    if isinstance(ligne, dict) and ligne.get("title") in LIBELLES_POCHE:
                        d = ligne.get("detail") or {}
                        poches[(compte(e), nom_type(e))][f"{ligne['title']}={sur(d.get('text'))}"] += 1
    for (c, t), cpt in sorted(poches.items()):
        print(f"  {c:15} {t:40} {dict(cpt)}")

    titre("6. CRYPTO : codes commençant par XF")
    xf = [e for e in evts if (isin_de(e)[0] or isin_de(e)[1] or "").startswith("XF")]
    codes = {isin_de(e)[0] or isin_de(e)[1] for e in xf}
    print(f"  événements : {len(xf)} ; codes distincts : {len(codes)}")
    print(f"  forme XF000 + lettres + 4 chiffres : {sum(1 for c in codes if re.fullmatch(r'XF000[A-Z]+[0-9]{4}', c))}/{len(codes)}")
    print(f"  types : {dict(Counter(nom_type(e) for e in xf))} ; comptes : {dict(Counter(compte(e) for e in xf))}")
    autres_x = {c for e in evts for c in [isin_de(e)[0] or isin_de(e)[1]] if c and c.startswith("X") and not c.startswith("XF")}
    print(f"  autres codes commençant par X (non XF) : {len(autres_x)}")

    titre("7. APPARIEMENT versement PEA ↔ exécution (même ISIN, ±3 jours)")
    executions = [e for e in evts if nom_type(e) in ("TRADING_SAVINGSPLAN_EXECUTED", "TRADING_TRADE_EXECUTED")
                  and e.get("status") == "EXECUTED"]
    for t_versement in ("PEA_SAVINGS_PLAN_PAY_IN", "PEA_DEPOSIT_DEBIT"):
        versements = [e for e in evts if nom_type(e) == t_versement]
        if not versements:
            continue
        print(f"\n  {t_versement} : {len(versements)}")
        nb_candidats, ecarts, montants, types_exec, comptes_exec, plan_id = Counter(), [], Counter(), Counter(), Counter(), Counter()
        for v in versements:
            isin = isin_de(v)[0] or isin_de(v)[1]
            plan_id["savingsPlanId présent dans le versement" if "savingsPlanId" in json.dumps(v) else
                    "savingsPlanId absent du versement"] += 1
            cands = [x for x in executions if (isin_de(x)[0] or isin_de(x)[1]) == isin
                     and x.get("cashAccountNumber") != v.get("cashAccountNumber")
                     and abs((date_de(x) - date_de(v)).total_seconds()) <= 3 * 86400]
            nb_candidats[len(cands)] += 1
            if len(cands) >= 1:
                x = min(cands, key=lambda x: abs((date_de(x) - date_de(v)).total_seconds()))
                ecarts.append((date_de(v) - date_de(x)).total_seconds() / 60)
                d = abs(abs(v["amount"]["value"]) - abs(x["amount"]["value"]))
                montants["montant identique" if d < 0.005 else "écart ≤ 1 €" if d <= 1.005 else "écart > 1 €"] += 1
                types_exec[nom_type(x)] += 1
                comptes_exec[compte(x)] += 1
        print(f"    nombre de candidats par versement : {dict(nb_candidats)}")
        if ecarts:
            avant = sum(1 for m in ecarts if m > 0)
            print(f"    exécution AVANT le versement : {avant}/{len(ecarts)} ; APRÈS : {len(ecarts) - avant}/{len(ecarts)}")
            print(f"    écart en minutes (versement − exécution) : min {min(ecarts):.0f}, "
                  f"médiane {median(ecarts):.0f}, max {max(ecarts):.0f}")
            print(f"    comparaison des montants : {dict(montants)}")
            print(f"    type de l'exécution appariée : {dict(types_exec)} ; compte : {dict(comptes_exec)}")
        print(f"    {dict(plan_id)}")
    with_plan = Counter((nom_type(e), compte(e)) for e in evts if "savingsPlanId" in json.dumps(e))
    print(f"\n  événements portant un savingsPlanId (type, compte) : {dict(with_plan)}")

    # Compte PEA = compte où ont lieu les exécutions appariées à un versement.
    versements = [e for e in evts if nom_type(e) in ("PEA_SAVINGS_PLAN_PAY_IN", "PEA_DEPOSIT_DEBIT")]
    apparies, comptes_pea = set(), Counter()
    for v in versements:
        isin = isin_de(v)[0] or isin_de(v)[1]
        cands = [x for x in executions if (isin_de(x)[0] or isin_de(x)[1]) == isin
                 and x.get("cashAccountNumber") != v.get("cashAccountNumber")
                 and abs((date_de(x) - date_de(v)).total_seconds()) <= 3 * 86400]
        if cands:
            x = min(cands, key=lambda x: abs((date_de(x) - date_de(v)).total_seconds()))
            apparies.add(x["id"])
            comptes_pea[x.get("cashAccountNumber")] += 1
    for numero in comptes_pea:
        achats = [x for x in executions if x.get("cashAccountNumber") == numero
                  and x["amount"]["value"] < 0]
        sans = [x for x in achats if x["id"] not in apparies]
        print(f"\n  {alias[numero]} (compte PEA) : achats {len(achats)}, "
              f"dont SANS versement associé : {len(sans)}")
        # Solde reconstitué : événements du compte PEA + versements reçus du compte courant.
        solde = sum(e["amount"]["value"] for e in evts if e.get("cashAccountNumber") == numero
                    and e.get("amount") and e.get("status") == "EXECUTED")
        solde += sum(abs(v["amount"]["value"]) for v in versements)
        etat = "≈ 0" if abs(solde) < 0.005 else "positif" if solde > 0 else "NÉGATIF (entrées manquantes)"
        print(f"  solde espèces reconstitué de ce compte en fin de fichier : {etat}")

    titre("8. ÉVÉNEMENTS SANS TYPE (eventType null)")
    for e in evts:
        if e.get("eventType"):
            continue
        ereignis = None
        for s in (e.get("details") or {}).get("sections", []):
            for ligne in s.get("data") if isinstance(s.get("data"), list) else []:
                if isinstance(ligne, dict) and ligne.get("title") == "Ereignistyp":
                    ereignis = (ligne.get("detail") or {}).get("text")
        v = (e.get("amount") or {}).get("value")
        signe = "sans montant" if v is None else ("+" if v > 0 else "−")
        titre_evt = e.get("title") if (e.get("title") == ereignis or v is None) else "«autre»"
        print(f"  {compte(e):15} {signe:13} titre={sur(titre_evt):28} Ereignistyp={sur(ereignis):25} "
              f"icône={masquer_isin(e.get('icon'))}")

    titre("9. TRANSFERTS INTERNES SIMULTANÉS (même seconde, montants opposés, comptes différents)")
    paires = Counter()
    for i, a in enumerate(evts):
        for b in evts[i + 1:]:
            if b["timestamp"][:19] != a["timestamp"][:19]:
                if b["timestamp"][:19] > a["timestamp"][:19]:
                    break
                continue
            va, vb = (a.get("amount") or {}).get("value"), (b.get("amount") or {}).get("value")
            if va is not None and vb is not None and abs(va + vb) < 0.005 and va != 0 \
                    and a.get("cashAccountNumber") != b.get("cashAccountNumber"):
                paires[tuple(sorted([f"{nom_type(a)}@{compte(a)}", f"{nom_type(b)}@{compte(b)}"]))] += 1
    for p, n in paires.items():
        print(f"  {p[0]}  ↔  {p[1]} : {n}")
    if not paires:
        print("  aucun")

    titre("10. CSV (format Portfolio Performance)")
    chemin_csv = dossier / "account_transactions.csv"
    with open(chemin_csv, encoding="utf-8", newline="") as f:
        lignes_csv = list(csv.DictReader(f, delimiter=";"))
    print(f"  {len(lignes_csv)} lignes ; colonnes : {list(lignes_csv[0].keys()) if lignes_csv else []}")
    for typ, n in sorted(Counter(l["Type"] for l in lignes_csv).items()):
        remplies = Counter(k for l in lignes_csv if l["Type"] == typ for k, v in l.items() if v)
        print(f"  Type={typ:20} {n:4}  colonnes renseignées : {dict(remplies)}")
    index = defaultdict(list)
    for e in evts:
        index[e["timestamp"][:19]].append(e)
    correspondances, sans_json = Counter(), Counter()
    montants_ok, parts_ok = Counter(), Counter()
    vus = set()
    for l in lignes_csv:
        cands = [e for e in index.get(l["Date"][:19], []) if e.get("amount")]
        if not cands:
            sans_json[l["Type"]] += 1
            continue
        valeur = float(l["Valeur"].replace(",", ".")) if l["Valeur"] else None
        e = min(cands, key=lambda e: abs(e["amount"]["value"] - (valeur or 0)))
        vus.add(e["id"])
        correspondances[(l["Type"], nom_type(e))] += 1
        montants_ok["identique" if valeur is not None and abs(e["amount"]["value"] - valeur) < 0.005 else "différent"] += 1
    print("\n  correspondance CSV → JSON (même horodatage à la seconde) :")
    for (tc, tj), n in sorted(correspondances.items()):
        print(f"      {tc:20} ← {tj:45} {n}")
    print(f"  montants CSV vs JSON : {dict(montants_ok)}")
    print(f"  lignes CSV sans événement JSON : {dict(sans_json)}")
    absents = Counter(nom_type(e) for e in evts if e.get("amount") and e["id"] not in vus)
    print(f"  événements JSON avec montant ABSENTS du CSV : {dict(absents)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
