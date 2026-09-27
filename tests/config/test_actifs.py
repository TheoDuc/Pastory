"""La configuration « déclarer ses actifs » : ISIN → ticker, et devise attendue (D-48, D-51).

Elle est relue par quelqu'un qui ne code pas. Deux exigences en découlent, et ce sont les
mêmes que pour les comptes : un message d'erreur qui dit **quoi écrire**, et une ligne laissée
vide traitée comme « pas encore fait » plutôt que comme une panne.

Le cas le plus important est celui du §4 du comparatif : une correspondance proposée dans une
autre monnaie que l'euro ne doit **jamais** pouvoir servir par inadvertance.
"""

from __future__ import annotations

import tomllib
from datetime import date
from decimal import Decimal

import pytest

from dashboard_tr.config import ConfigurationInvalide
from dashboard_tr.config.actifs import (
    CONTENUS_ACCEPTES,
    Configuration,
    ContenuActif,
    Declaration,
    FraisCourantsProposes,
    Proposition,
    TypeActif,
    charger,
    modele,
)
from dashboard_tr.parametres.referentiels import charger_classes

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

    def test_un_nom_d_actif_biscornu_ne_casse_pas_le_fichier(self):
        # Le nom vient de la banque, le ticker d'une source : ni l'un ni l'autre n'est sous
        # notre contrôle. Un guillemet ou un retour à la ligne rendrait le fichier illisible,
        # et c'est l'assistant censé le réparer qui refuserait alors de démarrer.
        texte = modele(
            {ACTIF: 'ETF « Exemple » "spécial"\nsur deux lignes'},
            {ACTIF: Proposition('AAA".DE', "XETRA", "EUR", 'Nom avec " et\nretour')},
            Configuration(),
        )

        relu = tomllib.loads(texte)["actifs"]
        assert relu[ACTIF]["devise"] == "EUR"
        assert relu[ACTIF]["ticker"] == 'AAA".DE'

    def test_un_ticker_deja_declare_avec_un_guillemet_se_relit(self):
        deja = Configuration(declarations={ACTIF: Declaration('AAA".DE', "EUR")})

        texte = modele({}, {}, deja)

        assert tomllib.loads(texte)["actifs"][ACTIF]["ticker"] == 'AAA".DE'

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


# --- Étape 6 : le type de l'actif et ses frais courants (D-55, D-61) -----------------


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


class TestModeleAvecLesFraisCourants:
    def test_une_proposition_complete_s_ecrit_en_ligne_active(self):
        proposition = Proposition(
            "AAAA.DE",
            "XETRA",
            "EUR",
            "ETF Exemple",
            type=TypeActif.ETF,
            frais_courants=FraisCourantsProposes(
                Decimal("0.20"), "Xetra", "ETF Exemple", "Accumulating", date(2026, 9, 28)
            ),
        )

        texte = modele({}, {ACTIF: proposition}, Configuration())

        assert tomllib.loads(texte)["actifs"][ACTIF] == {
            "ticker": "AAAA.DE",
            "devise": "EUR",
            "type": "etf",
            "ter_pour_cent": 0.20,
        }
        assert "À vérifier sur la fiche de l'émetteur" in texte
        assert "Accumulating" in texte

    def test_le_ter_propose_pour_un_actif_deja_declare_reste_en_commentaire(self):
        """L'utilisateur a validé son ticker : on ne réécrit pas sa ligne, on lui souffle."""
        deja = Configuration(declarations={ACTIF: Declaration("AAAA.DE", "EUR")})
        proposition = Proposition(
            "AAAA.DE",
            type=TypeActif.ETF,
            frais_courants=FraisCourantsProposes(Decimal("0.20"), "Xetra"),
        )

        texte = modele({}, {ACTIF: proposition}, deja)

        assert tomllib.loads(texte)["actifs"][ACTIF] == {
            "ticker": "AAAA.DE",
            "devise": "EUR",
        }
        assert "# type proposé par la source" in texte
        assert "TER proposé : 0.2 %" in texte

    def test_un_type_deja_declare_n_est_jamais_contredit(self):
        deja = Configuration(
            declarations={ACTIF: Declaration("AAAA.DE", "EUR", type=TypeActif.ACTION)}
        )

        texte = modele({}, {ACTIF: Proposition("AAAA.DE", type=TypeActif.ETF)}, deja)

        assert tomllib.loads(texte)["actifs"][ACTIF]["type"] == "action"
        assert "type proposé" not in texte

    def test_une_proposition_en_dollars_emporte_le_ter_avec_elle(self):
        """Tout reste inactif : la ligne commentée montre ce qui aurait été écrit."""
        proposition = Proposition(
            "BBBB.L",
            "London",
            "USD",
            type=TypeActif.ETF,
            frais_courants=FraisCourantsProposes(Decimal("0.20"), "Xetra"),
        )

        texte = modele({}, {ACTIF: proposition}, Configuration())

        assert tomllib.loads(texte)["actifs"][ACTIF] == ""
        assert "ATTENTION" in texte

    def test_un_ter_declare_se_relit_apres_reecriture(self, tmp_path):
        deja = Configuration(
            declarations={
                ACTIF: Declaration(
                    "AAAA.DE",
                    "EUR",
                    type=TypeActif.ETF,
                    ter_pour_cent=Decimal("0.07"),
                    spread_pour_cent=Decimal("0.25"),
                )
            }
        )

        texte = modele({}, {}, deja)

        relu = charger(ecrire(tmp_path, texte)).declaration(ACTIF)
        assert relu.ter_pour_cent == Decimal("0.07")
        assert relu.spread_pour_cent == Decimal("0.25")
        assert relu.type is TypeActif.ETF


# --- Défauts trouvés à la relecture indépendante --------------------------------------


class TestPropositionSansTicker:
    """Trouvé à la relecture : une source peut connaître les frais courants d'un actif sans
    qu'aucune n'ait trouvé son ticker. La ligne s'écrivait alors avec un ticker **vide**,
    d'apparence valide, et la lecture l'écartait en silence."""

    def test_une_proposition_sans_ticker_laisse_la_ligne_a_completer(self):
        proposition = Proposition(
            "",
            type=TypeActif.ETF,
            frais_courants=FraisCourantsProposes(Decimal("0.20"), "Xetra"),
        )

        texte = modele({}, {ACTIF: proposition}, Configuration())

        assert tomllib.loads(texte)["actifs"][ACTIF] == ""
        assert "aucun ticker proposé" in texte
        # Le TER trouvé n'est pas perdu : il reste en commentaire, à recopier.
        assert "TER proposé : 0.2 %" in texte

    def test_aucune_ligne_active_ne_porte_jamais_un_ticker_vide(self, tmp_path):
        proposition = Proposition(
            "   ", frais_courants=FraisCourantsProposes(Decimal("0.07"), "Xetra")
        )

        texte = modele({}, {ACTIF: proposition}, Configuration())

        # Relu par la vraie lecture, l'actif reste non déclaré — et le fichier le dit.
        assert charger(ecrire(tmp_path, texte)).declaration(ACTIF) is None
        assert "à compléter à la main" in texte


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
