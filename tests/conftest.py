"""Les garde-fous de toute la suite : voir `tests/garde_fous.py`.

Ils valent pour chaque test, et c'est voulu : aucun test n'écrit dans le vrai dossier personnel,
aucun ne sort de la machine — y compris ceux de l'interface, qui traversent l'assembleur comme
la ligne de commande.
"""

from tests.garde_fous import (  # noqa: F401 - des fixtures automatiques, actives par l'import
    aucun_appel_a_xetra,
    aucune_recherche_de_reglages,
    aucune_source_de_composition,
    dossier_personnel,
    rien_ne_touche_au_bureau,
)
