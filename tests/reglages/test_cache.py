"""Le cache des valeurs trouvées : relu tel qu'il a été écrit, et périmé à bon escient."""

from __future__ import annotations

from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

import pytest

from pastory.config.actifs import ContenuActif
from pastory.donnees_externes.cache import CacheIllisible
from pastory.reglages import Cotation, Origine, Trou, Trouvee
from pastory.reglages.cache import (
    DUREE_D_UN_TROU,
    DUREE_D_UNE_VALEUR,
    CacheDesReglages,
    Champ,
)

ACTIF = "XX0000000001"
LE = Date(2026, 9, 1)
ORIGINE = Origine(
    source="source de test", date=Date(2026, 8, 28), controle="contrôlé", reserve="à savoir"
)


def relu(tmp_path) -> CacheDesReglages:
    """Un second cache sur le même fichier : ce qui est relu vient bien du disque."""
    return CacheDesReglages(tmp_path / "reglages.csv")


class TestAllerRetour:
    def test_une_cotation_se_relit_avec_son_origine(self, tmp_path):
        cotation = Trouvee(Cotation("AAAA.DE", "EUR", "XETRA", "ETF; Fictif"), ORIGINE)
        CacheDesReglages(tmp_path / "reglages.csv").ecrire(ACTIF, Champ.COTATION, cotation, LE)

        en_memoire = relu(tmp_path).lire(ACTIF, Champ.COTATION)
        assert en_memoire.resultat == cotation
        assert en_memoire.recupere_le == LE

    def test_un_ter_se_relit_sans_passer_par_un_flottant(self, tmp_path):
        ter = Trouvee(Decimal("0.07"), ORIGINE)
        CacheDesReglages(tmp_path / "reglages.csv").ecrire(ACTIF, Champ.TER, ter, LE)

        assert relu(tmp_path).lire(ACTIF, Champ.TER).resultat.valeur == Decimal("0.07")

    def test_un_contenu_se_relit(self, tmp_path):
        contenu = Trouvee(ContenuActif.OBLIGATIONS, ORIGINE)
        CacheDesReglages(tmp_path / "reglages.csv").ecrire(ACTIF, Champ.CONTENU, contenu, LE)

        assert relu(tmp_path).lire(ACTIF, Champ.CONTENU).resultat == contenu

    def test_un_trou_se_relit_avec_son_motif(self, tmp_path):
        CacheDesReglages(tmp_path / "reglages.csv").ecrire(
            ACTIF, Champ.COTATION, Trou("aucune cotation en euros"), LE
        )
        assert relu(tmp_path).lire(ACTIF, Champ.COTATION).resultat == Trou(
            "aucune cotation en euros"
        )

    def test_un_fichier_absent_ne_connait_rien(self, tmp_path):
        assert relu(tmp_path).lire(ACTIF, Champ.COTATION) is None

    def test_oublier_un_actif_le_fait_rechercher(self, tmp_path):
        cache = CacheDesReglages(tmp_path / "reglages.csv")
        cache.ecrire(ACTIF, Champ.TER, Trouvee(Decimal("0.2"), ORIGINE), LE)
        cache.ecrire("XX0000000002", Champ.TER, Trouvee(Decimal("0.3"), ORIGINE), LE)

        assert cache.oublier(ACTIF) == [ACTIF]
        assert relu(tmp_path).lire(ACTIF, Champ.TER) is None
        assert relu(tmp_path).lire("XX0000000002", Champ.TER) is not None

    def test_une_ligne_illisible_dit_quoi_faire(self, tmp_path):
        fichier = tmp_path / "reglages.csv"
        fichier.write_text("actif;reglage;valeur\n;cotation;AAAA.DE\n", encoding="utf-8-sig")

        with pytest.raises(CacheIllisible, match="supprimez-le"):
            relu(tmp_path).lire(ACTIF, Champ.COTATION)


class TestPeremption:
    def test_une_cotation_trouvee_ne_se_recherche_jamais_d_elle_meme(self, tmp_path):
        # Changer de ticker en route mêlerait deux places dans la série de cours (D-50).
        cache = CacheDesReglages(tmp_path / "reglages.csv")
        cache.ecrire(ACTIF, Champ.COTATION, Trouvee(Cotation("A.DE", "EUR"), ORIGINE), LE)

        assert not cache.lire(ACTIF, Champ.COTATION).perimee(
            Champ.COTATION, LE + timedelta(days=3650)
        )

    def test_un_ter_se_reverifie_au_bout_d_un_mois(self, tmp_path):
        cache = CacheDesReglages(tmp_path / "reglages.csv")
        cache.ecrire(ACTIF, Champ.TER, Trouvee(Decimal("0.2"), ORIGINE), LE)
        en_memoire = cache.lire(ACTIF, Champ.TER)

        assert not en_memoire.perimee(Champ.TER, LE + DUREE_D_UNE_VALEUR - timedelta(days=1))
        assert en_memoire.perimee(Champ.TER, LE + DUREE_D_UNE_VALEUR)

    def test_un_trou_se_retente_au_bout_d_une_semaine(self, tmp_path):
        cache = CacheDesReglages(tmp_path / "reglages.csv")
        cache.ecrire(ACTIF, Champ.COTATION, Trou("rien"), LE)
        en_memoire = cache.lire(ACTIF, Champ.COTATION)

        assert not en_memoire.perimee(Champ.COTATION, LE + timedelta(days=1))
        assert en_memoire.perimee(Champ.COTATION, LE + DUREE_D_UN_TROU)
