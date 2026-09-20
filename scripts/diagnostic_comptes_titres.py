"""
Diagnostic STRUCTUREL des comptes-titres d'un compte Trade Republic.

Usage :
    uv run python scripts/diagnostic_comptes_titres.py

À quoi il sert
--------------
`pytr portfolio` ne demande les positions que d'**un seul** compte-titres : le
`securitiesAccountNumber` que renvoie `/api/v2/auth/account`
(voir `compact_portfolio` dans `pytr/api.py`). Si Trade Republic loge le PEA dans un
second compte-titres, ses positions ne sont jamais réclamées — et le rapprochement de
l'étape 3 signale alors, à tort, que la banque « ne montre pas » les actifs du PEA.

Ce script répond à **une seule question** : combien de comptes-titres ce compte
Trade Republic contient-il, et sous quels noms de champs sont-ils rangés ?

Ce qu'il n'affiche pas
----------------------
**AUCUNE valeur.** Ni numéro de compte, ni nom, ni adresse, ni IBAN, ni montant, ni
identifiant. Seulement :
  - des noms de champs ;
  - des types (texte, nombre, liste, tableau…) ;
  - des comptages.

C'est la même règle que `scripts/inventaire_structure.py` (D-05), poussée un cran plus
loin : ici, la réponse cherchée est un **nombre d'éléments**, donc aucune valeur n'est
nécessaire. Le résultat peut être collé tel quel dans une discussion.

Ce qu'il ne fait pas
--------------------
Il ne **lit** que les réglages du compte : aucun ordre, aucun fichier écrit, aucune
donnée enregistrée. Comme `dashboard rafraichir`, il ne manipule aucun identifiant
(D-41) : c'est pytr qui demande le numéro et le PIN, la saisie du PIN étant masquée.

    ATTENTION : en tapant le PIN, rien ne s'affiche. C'est normal.
    Sous Windows, lancez ce script depuis PowerShell, cmd ou le terminal de VS Code —
    pas depuis Git Bash, où la saisie masquée reste bloquée.
"""

import logging
import sys

PROFONDEUR_MAXIMALE = 4
"""Au-delà, on s'arrête : la réponse cherchée est près de la racine, et descendre
indéfiniment ne ferait qu'allonger un affichage qu'on veut pouvoir relire d'un coup."""

MOTS_CLES = ("securitiesaccount", "secacc", "depot", "account", "portfolio", "pea")
"""Ce qu'on cherche dans les noms de champs. Volontairement large : on ne sait pas
comment Trade Republic nomme un second compte-titres, et passer à côté serait pire
qu'afficher trois lignes de trop."""


def museler_le_journal_de_pytr():
    """Empêche pytr d'imprimer les réglages du compte en clair.

    `pytr.account.login()` se termine par `log.debug(get_settings(tr))` : **le JSON complet
    du compte**, avec le nom, le téléphone et les numéros de compte. Il n'apparaît pas
    aujourd'hui, parce que le journal s'installe au niveau « info » par défaut — mais c'est
    un défaut de bibliothèque tierce, et la promesse de ce script (« aucune valeur ») ne
    doit pas en dépendre.

    Un **filtre sur le logger** tient là où un réglage de niveau ne tiendrait pas : pytr
    remet lui-même son niveau à `DEBUG` et réinstalle ses gestionnaires à chaque appel,
    mais il ne touche jamais aux filtres déjà posés.
    """
    logging.getLogger("account").addFilter(
        lambda enregistrement: enregistrement.levelno > logging.DEBUG
    )


def genre(valeur):
    """Le type d'une valeur, en français, sans jamais montrer la valeur elle-même."""
    if valeur is None:
        return "vide"
    if isinstance(valeur, bool):
        return "oui/non"
    if isinstance(valeur, (int, float)):
        return "nombre"
    if isinstance(valeur, str):
        return "texte"
    if isinstance(valeur, list):
        return f"liste de {len(valeur)} élément(s)"
    if isinstance(valeur, dict):
        return f"tableau de {len(valeur)} champ(s)"
    return type(valeur).__name__


def interessant(chemin):
    """Vrai si ce chemin de champs peut mener à un compte-titres."""
    return any(mot in chemin.lower() for mot in MOTS_CLES)


def decrire(valeur, chemin="", profondeur=0):
    """Affiche la structure, champ par champ. Aucune valeur n'est imprimée."""
    marge = "  " * profondeur

    if isinstance(valeur, dict):
        for cle, sous_valeur in valeur.items():
            sous_chemin = f"{chemin}.{cle}" if chemin else cle
            marque = "  <--" if interessant(cle) else ""
            print(f"{marge}{cle} : {genre(sous_valeur)}{marque}")
            if profondeur + 1 < PROFONDEUR_MAXIMALE:
                decrire(sous_valeur, sous_chemin, profondeur + 1)
        return

    if isinstance(valeur, list) and valeur:
        # On ne décrit que le premier élément : les suivants ont la même forme, et les
        # parcourir tous n'apprendrait rien de plus sur la structure.
        print(f"{marge}[forme d'un élément]")
        if profondeur + 1 < PROFONDEUR_MAXIMALE:
            decrire(valeur[0], f"{chemin}[]", profondeur + 1)


def compter_les_comptes_titres(reglages):
    """Cherche partout une liste qui ressemble à une liste de comptes-titres.

    Les champs **à l'intérieur** d'une liste sont laissés de côté : ils apparaissent
    déjà dans la structure ci-dessus, et les répéter une fois par élément noierait la
    seule ligne qui répond à la question.
    """
    trouves = {}

    def parcourir(valeur, chemin=""):
        if isinstance(valeur, dict):
            for cle, sous_valeur in valeur.items():
                sous_chemin = f"{chemin}.{cle}" if chemin else cle
                if interessant(cle) and "[]" not in sous_chemin:
                    if isinstance(sous_valeur, list):
                        trouves[sous_chemin] = len(sous_valeur)
                    elif isinstance(sous_valeur, str):
                        trouves[sous_chemin] = 1
                parcourir(sous_valeur, sous_chemin)
        elif isinstance(valeur, list):
            for element in valeur:
                parcourir(element, f"{chemin}[]")

    parcourir(reglages)
    return sorted(trouves.items())


def main():
    print("Diagnostic des comptes-titres Trade Republic.")
    print("Ce script ne lit que la structure de vos réglages de compte.")
    print("Il n'affiche AUCUNE valeur : ni numéro, ni nom, ni montant.\n")
    print("Trade Republic va vous demander votre numéro de téléphone, puis votre PIN.")
    print("  ATTENTION : en tapant le PIN, vous ne verrez RIEN s'afficher.")
    print("  C'est normal, la saisie est masquée. Tapez le PIN, puis Entrée.\n")

    try:
        from pytr.account import login
    except ImportError:
        print("pytr n'est pas installé. Lancez « uv sync » d'abord.", file=sys.stderr)
        return 1

    # `waf_token="default"` n'est pas une décoration : c'est ce que la commande `pytr`
    # passe elle-même, et ce qui, combiné à `v2=True`, fait qu'aucun jeton AWS WAF n'est
    # réclamé. La fonction `login()` de la bibliothèque, elle, a pour défaut "playwright",
    # qui exige un navigateur à installer à part — et l'écrase donc sans le dire.
    # Sans cette ligne : « playwright is not installed ».
    museler_le_journal_de_pytr()
    tr = login(v2=True, waf_token="default")

    try:
        reglages = tr.settings()
    except Exception as erreur:  # noqa: BLE001 - un diagnostic doit expliquer, pas planter
        print(f"\nLa lecture des réglages a échoué : {type(erreur).__name__}", file=sys.stderr)
        print("Si le message parle d'authentification, relancez la commande.", file=sys.stderr)
        return 1

    print("\nStructure des réglages du compte")
    print("-" * 32)
    print("(« <-- » marque un champ dont le nom peut désigner un compte-titres)\n")
    decrire(reglages)

    print("\nCe qui ressemble à un compte-titres")
    print("-" * 35)
    trouves = compter_les_comptes_titres(reglages)
    if not trouves:
        print("  Aucun champ de ce genre. L'explication est donc ailleurs :")
        print("  à signaler tel quel, avec le reste de cet affichage.")
    else:
        for chemin, nombre in trouves:
            print(f"  {chemin} : {nombre} élément(s)")

    print("\nCe qu'il faut en retenir")
    print("-" * 24)
    print("  - PLUSIEURS comptes-titres : l'explication est confirmée, pytr n'en demande")
    print("    qu'un seul, et le PEA est dans l'autre.")
    print("  - UN SEUL compte-titres : l'explication est fausse, et le PEA est ailleurs.")
    print("\nCollez cet affichage tel quel : il ne contient aucune de vos valeurs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
