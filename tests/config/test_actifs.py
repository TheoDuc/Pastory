"""Les corrections de l'utilisateur : `actifs.toml` (D-78, D-80).

Depuis l'étape 8 quater, tout est trouvé seul ; ce fichier ne sert qu'à corriger, et chaque champ
y est facultatif. Il est écrit à la main par quelqu'un qui ne code pas : un message d'erreur doit
dire **quoi écrire**, et une ligne laissée vide ne corrige rien plutôt que de tout bloquer.

Le cas le plus important reste celui du §4 du comparatif : une cotation dans une autre monnaie
que l'euro ne doit **jamais** pouvoir servir (D-48).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pastory.config import ConfigurationInvalide
from pastory.config.actifs import (
    CONTENUS_ACCEPTES,
    ContenuActif,
    Declaration,
    TypeActif,
    charger,
)
from pastory.parametres.referentiels import charger_classes

ACTIF = "XX0000000001"
AUTRE_ACTIF = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"


def ecrire(tmp_path, contenu):
    fichier = tmp_path / "actifs.toml"
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


class TestLecture:
    def test_un_fichier_absent_donne_une_configuration_vide(self, tmp_path):
        # Le cas normal : l'utilisateur n'a rien eu à corriger.
        assert charger(tmp_path / "rien.toml").declarations == {}

    def test_une_declaration_complete_est_lue(self, tmp_path):
        fichier = ecrire(
            tmp_path,
            f'[actifs]\n"{ACTIF}" = {{ ticker = "AAAA.DE", devise = "EUR" }}\n',
        )

        declaration = charger(fichier).declaration(ACTIF)
        assert declaration == Declaration(ticker="AAAA.DE", devise="EUR")

    def test_une_crypto_se_declare_comme_le_reste(self, tmp_path):
        fichier = ecrire(
            tmp_path,
            f'[actifs]\n"{CRYPTO}" = {{ ticker = "BBB-EUR", devise = "EUR" }}\n',
        )
        assert charger(fichier).declaration(CRYPTO).ticker == "BBB-EUR"

    def test_un_actif_laisse_vide_ne_corrige_rien(self, tmp_path):
        fichier = ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = ""\n')
        assert charger(fichier).declarations == {}

    def test_un_ticker_laisse_vide_laisse_la_cotation_trouvee(self, tmp_path):
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = "", devise = "EUR", type = "etf" }}\n'
        )
        declaration = charger(fichier).declaration(ACTIF)
        assert declaration.ticker is None
        assert declaration.type is TypeActif.ETF

    def test_une_correction_peut_ne_porter_que_sur_un_champ(self, tmp_path):
        # Corriger le seul TER, sans réécrire de ticker : le reste reste trouvé (D-80).
        fichier = ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = {{ ter_pour_cent = 0.07 }}\n')
        declaration = charger(fichier).declaration(ACTIF)
        assert declaration.ticker is None
        assert declaration.ter_pour_cent == Decimal("0.07")

    def test_les_espaces_autour_du_ticker_sont_ignores(self, tmp_path):
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = " AAAA.DE ", devise = " eur " }}\n'
        )
        assert charger(fichier).declaration(ACTIF) == Declaration("AAAA.DE", "EUR")

class TestMessagesDErreur:
    def test_un_ticker_seul_dit_quoi_ecrire(self, tmp_path):
        # Tentation naturelle en éditant à la main : n'écrire que le ticker. La devise n'est
        # pas devinée (D-48), et le message doit donner la forme exacte.
        fichier = ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = "AAAA.DE"\n')

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)
        assert "ticker" in str(erreur.value)
        assert "devise" in str(erreur.value)

    def test_une_devise_absente_dit_pourquoi_elle_compte(self, tmp_path):
        fichier = ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = "AAAA.DE" }}\n')

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)
        assert "devise" in str(erreur.value)
        assert "euros" in str(erreur.value)

    def test_une_devise_autre_que_l_euro_est_refusee(self, tmp_path):
        # Le piège du comparatif : la cotation londonienne en dollars d'un ETF qui cote
        # aussi en euros. L'application ne convertit rien (D-26) : elle refuse et explique.
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = "BBBB.L", devise = "USD" }}\n'
        )

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)
        assert "USD" in str(erreur.value)
        assert "EUR" in str(erreur.value)

    def test_un_fichier_mal_ecrit_le_dit(self, tmp_path):
        fichier = ecrire(tmp_path, "[actifs\nceci n'est pas du TOML")

        with pytest.raises(ConfigurationInvalide, match="TOML"):
            charger(fichier)

    def test_une_section_qui_n_est_pas_un_tableau_le_dit(self, tmp_path):
        fichier = ecrire(tmp_path, 'actifs = "AAAA.DE"\n')

        with pytest.raises(ConfigurationInvalide, match=r"\[actifs\]"):
            charger(fichier)


def declarer(tmp_path, champs):
    """Un fichier avec un seul actif, déclaré avec les champs donnés."""
    return ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = {{ {champs} }}\n')


BASE = 'ticker = "AAAA.DE", devise = "EUR"'


class TestTypeEtFraisCourants:
    def test_un_actif_declare_avec_son_type_et_son_ter_est_lu(self, tmp_path):
        fichier = declarer(tmp_path, f'{BASE}, type = "etf", ter_pour_cent = 0.20')

        declaration = charger(fichier).declaration(ACTIF)
        assert declaration.type is TypeActif.ETF
        assert declaration.ter_pour_cent == Decimal("0.20")

    def test_le_taux_passe_par_le_texte_jamais_par_le_flottant(self, tmp_path):
        """D-33 : `Decimal(0.07)` ferait 0,070000000000000006661338…"""
        fichier = declarer(tmp_path, f"{BASE}, ter_pour_cent = 0.07")

        assert str(charger(fichier).declaration(ACTIF).ter_pour_cent) == "0.07"

    def test_sans_type_ni_ter_la_declaration_reste_valable(self, tmp_path):
        """Les deux champs sont facultatifs : un actif déclaré à l'étape 4 se lit toujours."""
        declaration = charger(declarer(tmp_path, BASE)).declaration(ACTIF)

        assert declaration.type is None
        assert declaration.ter_pour_cent is None

    def test_un_type_inconnu_dit_lesquels_sont_acceptes(self, tmp_path):
        fichier = declarer(tmp_path, f'{BASE}, type = "obligation"')

        with pytest.raises(ConfigurationInvalide, match="Types acceptés"):
            charger(fichier)

    @pytest.mark.parametrize("valeur", ["0.002", "20", "0.01"])
    def test_un_ter_hors_fourchette_est_refuse_comme_erreur_d_unite(self, tmp_path, valeur):
        """0,002 et 20 sont les deux façons de se tromper d'unité pour 0,20 %."""
        fichier = declarer(tmp_path, f"{BASE}, ter_pour_cent = {valeur}")

        with pytest.raises(ConfigurationInvalide, match="erreur d'unité"):
            charger(fichier)

    def test_un_ter_qui_n_est_pas_un_nombre_dit_quoi_ecrire(self, tmp_path):
        fichier = declarer(tmp_path, f'{BASE}, ter_pour_cent = "0.20"')

        with pytest.raises(ConfigurationInvalide, match="ter_pour_cent = 0.20"):
            charger(fichier)

    def test_un_spread_propre_a_un_actif_est_lu(self, tmp_path):
        fichier = declarer(tmp_path, f"{BASE}, spread_pour_cent = 0.25")

        assert charger(fichier).declaration(ACTIF).spread_pour_cent == Decimal("0.25")

    def test_un_spread_nul_est_refuse(self, tmp_path):
        """Un spread de zéro n'existe pas : c'est une ligne à effacer, pas un taux."""
        fichier = declarer(tmp_path, f"{BASE}, spread_pour_cent = 0")

        with pytest.raises(ConfigurationInvalide, match="fourchette"):
            charger(fichier)


class TestLeContenuDeclare:
    """D-71 : de quoi l'actif est fait, à ne pas confondre avec ce qu'on détient."""

    def test_un_contenu_valide_est_lu(self, tmp_path):
        fichier = tmp_path / "actifs.toml"
        fichier.write_text(
            '[actifs]\n"XX0000000001" = { ticker = "T1.DE", devise = "EUR", type = "etf", '
            'contenu = "obligations" }\n',
            encoding="utf-8",
        )

        declaration = charger(fichier).declaration("XX0000000001")

        assert declaration.contenu is ContenuActif.OBLIGATIONS
        # Le type reste « etf » : c'est lui qui décide du spread et du TER attendu (D-55, D-61).
        assert declaration.type is TypeActif.ETF

    def test_un_contenu_absent_laisse_la_source_decider(self, tmp_path):
        fichier = tmp_path / "actifs.toml"
        fichier.write_text(
            '[actifs]\n"XX0000000001" = { ticker = "T1.DE", devise = "EUR", type = "etf" }\n',
            encoding="utf-8",
        )

        assert charger(fichier).declaration("XX0000000001").contenu is None

    def test_un_contenu_inconnu_explique_la_difference_avec_le_type(self, tmp_path):
        fichier = tmp_path / "actifs.toml"
        fichier.write_text(
            '[actifs]\n"XX0000000001" = { ticker = "T1.DE", devise = "EUR", '
            'contenu = "obligation" }\n',
            encoding="utf-8",
        )

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)

        message = str(erreur.value)
        assert "obligations" in message
        assert "matieres_premieres" in message
        assert "ce que vous détenez" in message

    def test_les_contenus_acceptes_sont_les_cles_des_classes_d_actifs(self):
        # C'est ce qui permet à un contenu déclaré d'être nommé comme celui d'une source.
        classes = charger_classes()

        for contenu in CONTENUS_ACCEPTES:
            assert classes.classe(contenu) is not None, contenu


LIGNE = '"{}" = {{ ticker = "A.DE", devise = "EUR", type = "etf"{} }}'


class TestLaSourceDeSecoursSeDeclare:
    """Le champ « secours » d'un actif (D-72, D-77, D-80).

    Sans correction, le secours est essayé de lui-même, et la source de chaque chiffre reste
    affichée ligne par ligne. La correction sert à l'imposer, ou à le refuser.
    """

    def test_un_actif_peut_imposer_une_source_de_secours(self, tmp_path):
        fichier = ecrire(tmp_path, "[actifs]\n" + LIGNE.format(ACTIF, ', secours = "amundi"'))

        declaration = charger(fichier).declaration(ACTIF)

        assert declaration is not None
        assert declaration.secours == "amundi"

    def test_un_actif_peut_refuser_toute_source_de_secours(self, tmp_path):
        fichier = ecrire(tmp_path, "[actifs]\n" + LIGNE.format(ACTIF, ', secours = "aucun"'))
        assert charger(fichier).declaration(ACTIF).secours == "aucun"

    def test_sans_le_champ_rien_n_est_corrige(self, tmp_path):
        fichier = ecrire(tmp_path, "[actifs]\n" + LIGNE.format(ACTIF, ""))

        assert charger(fichier).declaration(ACTIF).secours is None

    def test_une_source_inconnue_est_refusee_a_la_lecture(self, tmp_path):
        """« amundy » doit s'apprendre tout de suite, pas six écrans plus loin."""
        fichier = ecrire(tmp_path, "[actifs]\n" + LIGNE.format(ACTIF, ', secours = "amundy"'))

        with pytest.raises(ConfigurationInvalide) as erreur:
            charger(fichier)

        assert "amundy" in str(erreur.value)
        assert "amundi" in str(erreur.value)

    def test_la_casse_et_les_espaces_sont_tolerees(self, tmp_path):
        fichier = ecrire(tmp_path, "[actifs]\n" + LIGNE.format(ACTIF, ', secours = " Amundi "'))

        assert charger(fichier).declaration(ACTIF).secours == "amundi"
