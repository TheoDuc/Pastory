"""La configuration « déclarer ses actifs » : ISIN → ticker, et devise attendue (D-48, D-51).

Elle est relue par quelqu'un qui ne code pas. Deux exigences en découlent, et ce sont les
mêmes que pour les comptes : un message d'erreur qui dit **quoi écrire**, et une ligne laissée
vide traitée comme « pas encore fait » plutôt que comme une panne.

Le cas le plus important est celui du §4 du comparatif : une correspondance proposée dans une
autre monnaie que l'euro ne doit **jamais** pouvoir servir par inadvertance.
"""

from __future__ import annotations

import tomllib

import pytest

from dashboard_tr.config import ConfigurationInvalide
from dashboard_tr.config.actifs import (
    Configuration,
    Declaration,
    Proposition,
    charger,
    modele,
)

ACTIF = "XX0000000001"
AUTRE_ACTIF = "XX0000000002"
CRYPTO = "XF000EXEMPLE01"


def ecrire(tmp_path, contenu):
    fichier = tmp_path / "actifs.toml"
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


class TestLecture:
    def test_un_fichier_absent_donne_une_configuration_vide(self, tmp_path):
        # Le premier lancement, avant `dashboard actifs` : ce n'est pas une erreur ici.
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

    def test_un_actif_laisse_vide_est_un_travail_en_cours(self, tmp_path):
        fichier = ecrire(tmp_path, f'[actifs]\n"{ACTIF}" = ""\n')
        assert charger(fichier).declarations == {}

    def test_un_ticker_laisse_vide_est_un_travail_en_cours(self, tmp_path):
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = "", devise = "EUR" }}\n'
        )
        assert charger(fichier).declarations == {}

    def test_les_espaces_autour_du_ticker_sont_ignores(self, tmp_path):
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = " AAAA.DE ", devise = " eur " }}\n'
        )
        assert charger(fichier).declaration(ACTIF) == Declaration("AAAA.DE", "EUR")

    def test_les_actifs_non_declares_se_listent(self, tmp_path):
        fichier = ecrire(
            tmp_path, f'[actifs]\n"{ACTIF}" = {{ ticker = "AAAA.DE", devise = "EUR" }}\n'
        )
        configuration = charger(fichier)

        # Ordre alphabétique : « XF » (crypto) précède « XX ».
        assert configuration.manquants([ACTIF, AUTRE_ACTIF, CRYPTO]) == [CRYPTO, AUTRE_ACTIF]


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


class TestModele:
    def test_le_modele_se_relit_tout_seul(self):
        # Le fichier écrit par l'assistant doit repasser par sa propre lecture : sans cela,
        # l'assistant pourrait produire un fichier que l'application refuse.
        texte = modele(
            {ACTIF: "ETF Exemple - PEA"},
            {ACTIF: Proposition("AAAA.DE", "XETRA", "EUR", "ETF Exemple")},
            Configuration(),
        )
        assert tomllib.loads(texte)["actifs"][ACTIF] == {
            "ticker": "AAAA.DE",
            "devise": "EUR",
        }

    def test_une_proposition_en_euros_est_active(self):
        texte = modele(
            {}, {ACTIF: Proposition("AAAA.DE", "XETRA", "EUR")}, Configuration()
        )
        assert f'"{ACTIF}" = {{ ticker = "AAAA.DE", devise = "EUR" }}' in texte

    def test_une_proposition_dans_une_autre_monnaie_reste_inactive(self):
        # Elle est écrite en commentaire, avec un avertissement : la ligne active reste
        # vide. C'est le garde-fou de D-48 au niveau du fichier.
        texte = modele(
            {}, {ACTIF: Proposition("BBBB.L", "London", "USD")}, Configuration()
        )

        assert f'"{ACTIF}" = ""' in texte
        assert "ATTENTION" in texte
        assert '#   "XX0000000001" = { ticker = "BBBB.L", devise = "USD" }' in texte
        assert tomllib.loads(texte)["actifs"][ACTIF] == ""

    def test_un_actif_sans_proposition_est_a_completer_a_la_main(self):
        texte = modele({ACTIF: "ETF Exemple"}, {}, Configuration())

        assert f'"{ACTIF}" = ""' in texte
        assert "à compléter à la main" in texte

    def test_l_apercu_aide_a_reconnaitre_l_actif(self):
        texte = modele({ACTIF: "ETF Exemple - PEA, CTO"}, {}, Configuration())
        assert "# ETF Exemple - PEA, CTO" in texte

    def test_le_modele_ne_perd_rien_de_ce_qui_etait_declare(self):
        # La leçon de comptes.py : l'assistant réécrit le fichier entier. Un actif déjà
        # déclaré mais absent de cet export-ci doit être recopié, sinon relancer
        # l'assistant effacerait un travail de relecture déjà fait.
        deja = Configuration(
            declarations={
                ACTIF: Declaration("AAAA.DE", "EUR"),
                CRYPTO: Declaration("BBB-EUR", "EUR"),
            }
        )

        texte = modele({AUTRE_ACTIF: "Action Exemple"}, {}, deja)

        relu = tomllib.loads(texte)["actifs"]
        assert relu[ACTIF] == {"ticker": "AAAA.DE", "devise": "EUR"}
        assert relu[CRYPTO] == {"ticker": "BBB-EUR", "devise": "EUR"}
        assert relu[AUTRE_ACTIF] == ""

    def test_une_declaration_existante_prime_sur_une_proposition(self):
        # L'utilisateur a validé : on ne lui repropose pas autre chose, et surtout on
        # n'écrase pas son choix.
        deja = Configuration(declarations={ACTIF: Declaration("AAAA.DE", "EUR")})

        texte = modele({}, {ACTIF: Proposition("ZZZZ.MI", "Milan", "EUR")}, deja)

        assert tomllib.loads(texte)["actifs"][ACTIF] == {
            "ticker": "AAAA.DE",
            "devise": "EUR",
        }
        assert "ZZZZ.MI" not in texte
