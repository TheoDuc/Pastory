"""Pastory — tableau de bord local des actifs d'un portefeuille Trade Republic.

Organisation en « wagons » (D-26, docs/architecture-notes.md §1) :

    export d'une banque ─► adaptateurs ─► pivot ─► moteur ─► vues

Chaque couche est testable seule et ne connaît que la suivante.
"""
