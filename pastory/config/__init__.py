"""Configuration de l'utilisateur et emplacement de ses fichiers."""

from __future__ import annotations


class ConfigurationInvalide(Exception):
    """Un fichier de configuration existe mais ne peut pas être utilisé tel quel.

    Commune à tous les fichiers de configuration — comptes, actifs — pour que l'appelant
    n'ait qu'une seule erreur à attraper : c'est toujours la même chose à dire à
    l'utilisateur, « votre fichier dit quelque chose que je ne comprends pas, voici où ».
    """
