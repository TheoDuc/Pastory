"""Relève les clôtures dont le portefeuille de démonstration a besoin, et écrit
`pastory/demonstration/clotures.py`.

    .venv/Scripts/python.exe scripts/releve_de_demonstration.py

À relancer seulement quand le scénario change (`pastory/demonstration/__init__.py`) : un plan
prolongé, un ordre ajouté. Il interroge la source de cours du projet, une fois par titre.

Pour chaque jour **voulu** par le scénario (le 2 du mois, le 16…), il retient le **premier jour
coté** à partir de ce jour-là, et sa clôture brute. Un jour voulu sans cotation dans la semaine
qui suit arrête tout : mieux vaut un relevé absent qu'un prix pris au hasard.
"""

from __future__ import annotations

import sys
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from pastory import demonstration  # noqa: E402
from pastory.donnees_externes.yahoo import Yahoo  # noqa: E402

SORTIE = RACINE / "pastory" / "demonstration" / "clotures.py"
ATTENTE_MAXIMALE = timedelta(days=7)

EN_TETE = '''"""Les clôtures du portefeuille de démonstration. **Fichier écrit par un script** :
`scripts/releve_de_demonstration.py`. Ne pas le modifier à la main.

Relevé le {aujourd_hui}, sur {source}. Ce sont des cours de clôture **bruts** et publics, en
euros, sur la cotation nommée en face de chaque titre. Ils servent de prix d'achat aux
opérations inventées de la démonstration (`pastory/demonstration/__init__.py`), et à rien d'autre :
Pastory ne valorise jamais avec ce fichier, il cherche ses cours comme pour un vrai export.

Pour chaque titre : le jour voulu par le scénario, puis le premier jour coté à partir de ce
jour-là, et sa clôture.
"""

RELEVE_LE = "{aujourd_hui}"

CLOTURES: dict[str, dict[str, tuple[str, str]]] = {{
'''


def main() -> int:
    source = Yahoo()
    blocs: list[str] = []
    for titre, voulus in demonstration.jours_a_relever().items():
        devise, serie = source.serie_brute(
            titre.ticker, voulus[0] - timedelta(days=3), voulus[-1] + ATTENTE_MAXIMALE
        )
        if devise != "EUR":
            sys.exit(f"{titre.ticker} cote en {devise}, pas en euros : relevé abandonné.")
        cotes = dict(serie)
        lignes = [f"    # {titre.nom} · {titre.ticker}", f'    "{titre.code}": {{']
        for voulu in voulus:
            jour = next(
                (
                    voulu + timedelta(days=ecart)
                    for ecart in range(ATTENTE_MAXIMALE.days + 1)
                    if voulu + timedelta(days=ecart) in cotes
                ),
                None,
            )
            if jour is None:
                sys.exit(f"{titre.ticker} : aucune cotation dans la semaine du {voulu}.")
            lignes.append(f'        "{voulu}": ("{jour}", "{cotes[jour]:f}"),')
        lignes.append("    },")
        blocs.append("\n".join(lignes))
        print(f"{titre.ticker:<10} {len(voulus):>3} jours relevés")

    texte = EN_TETE.format(aujourd_hui=Date.today(), source=source.nom)
    SORTIE.write_text(texte + "\n".join(blocs) + "\n}\n", encoding="utf-8")
    print(f"Écrit : {SORTIE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
