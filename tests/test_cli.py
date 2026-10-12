"""La ligne de commande, de bout en bout, sur un export fictif.

Tous les tests détournent `PASTORY_DOSSIER` vers un dossier temporaire : **aucun ne
doit écrire dans le vrai dossier personnel** de la personne qui lance la suite.
"""

from __future__ import annotations

import csv
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

import pytest

from pastory import assembleur, cli, tableur
from pastory.config import actifs as config_actifs
from pastory.config import emplacements
from pastory.config import fiscalite as config_fiscalite
from pastory.config.actifs import FraisCourantsProposes, Proposition
from pastory.donnees_externes.cache import Cache
from pastory.donnees_externes.cache_compositions import CacheDeCompositions
from pastory.donnees_externes.composition import Composition, Part
from pastory.donnees_externes.cours import Cours, ErreurDeSource
from tests.adaptateurs.trade_republic import export_fictif
from tests.adaptateurs.trade_republic import export_ligne_de_commande as fictifs


class ListeFictive:
    """La liste des ETF réduite à un dictionnaire : `{actif: (ter, nom, politique)}`."""

    def __init__(self, contenu, date_deffet=Date(2026, 9, 28)):
        self.contenu = contenu
        self.date = date_deffet

    def __len__(self):
        return len(self.contenu)

    def frais_courants(self, actif):
        if actif not in self.contenu:
            return None
        ter, nom, politique = self.contenu[actif]
        return FraisCourantsProposes(
            ter_pour_cent=Decimal(ter),
            source="liste de test",
            nom=nom,
            politique=politique,
            date=self.date,
        )


def brancher_la_liste_des_etf(monkeypatch, contenu):
    """Remplace la liste des ETF par une liste écrite à la main."""
    monkeypatch.setattr(assembleur, "liste_des_etf", lambda: ListeFictive(contenu))


def lire_csv(fichier):
    """Relit un CSV du moteur comme le ferait un tableur : point-virgule et BOM (tableur.py)."""
    with fichier.open(encoding=tableur.ENCODAGE, newline="") as flux:
        return list(csv.DictReader(flux, delimiter=tableur.SEPARATEUR))


def montant(texte):
    """Un nombre écrit à la française, relu comme le tableur le relirait."""
    return Decimal(texte.replace(",", "."))


def _deposer_export(dossier):
    return fictifs.deposer(dossier)


def ajouter_a_l_export(dossier, *lignes):
    """Réécrit l'export avec des lignes de plus. Un fichier est un portefeuille (D-109) :
    déposer un second fichier ne compléterait pas le premier, il en ferait un autre."""
    export_fictif.deposer(dossier, [*fictifs.lignes(), *lignes])


@pytest.fixture(autouse=True)
def avec_les_titres_recus(monkeypatch):
    """Ajoute à chaque lecture les deux titres reçus que l'export officiel ne produit pas
    encore (Q-54), pour que la complétion de leur prix (D-15) reste vérifiée de bout en bout.

    Voir `export_ligne_de_commande.py`. Les tests de la lecture pure demandent la fixture
    `lecture_pure`, qui retire cet ajout.
    """
    vraie_lecture = assembleur.lire

    def lecture_completee(dossier):
        rapport = vraie_lecture(dossier)
        rapport.operations = sorted(
            rapport.operations + fictifs.titres_recus(),
            key=lambda operation: operation.instant_utc,
        )
        return rapport

    monkeypatch.setattr(assembleur, "lire", lecture_completee)
    return vraie_lecture


@pytest.fixture
def lecture_pure(monkeypatch, avec_les_titres_recus):
    """La lecture telle que l'adaptateur la fait, sans rien ajouter."""
    monkeypatch.setattr(assembleur, "lire", avec_les_titres_recus)


@pytest.fixture
def export(dossier_personnel):
    """L'export de l'utilisateur, là où l'application le range (D-37)."""
    return _deposer_export(dossier_personnel / "exports")


@pytest.fixture
def export_ailleurs(tmp_path):
    """Un export rangé ailleurs : celui de quelqu'un d'autre, lu avec --export."""
    return _deposer_export(tmp_path / "ailleurs")


class TestBases:
    def test_la_version_repond(self, capsys):
        with pytest.raises(SystemExit) as sortie:
            cli.main(["--version"])

        assert sortie.value.code == 0
        assert "pastory" in capsys.readouterr().out

    def test_sans_commande_l_aide_s_affiche(self, capsys):
        assert cli.main([]) == 0
        assert "usage" in capsys.readouterr().out.lower()

    def test_les_emplacements_s_affichent(self, capsys):
        assert cli.main(["emplacements"]) == 0
        affichage = capsys.readouterr().out
        assert "exports" in affichage
        assert "pas encore créé" in affichage

    def test_ouvrir_lance_l_application_avec_ses_options(self, monkeypatch, tmp_path):
        from pastory.vues import application

        lancements = []
        monkeypatch.setattr(application, "lancer", lambda **options: lancements.append(options))

        assert cli.main(["ouvrir", "--hors-ligne", "--port", "8123"]) == 0
        assert cli.main(["ouvrir", "--export", str(tmp_path)]) == 0

        assert lancements == [
            {"hors_ligne": True, "dossier_export": None, "port": 8123},
            {"hors_ligne": False, "dossier_export": tmp_path, "port": 8050},
        ]


class TestExportIntrouvable:
    @pytest.mark.parametrize("commande", ["lire", "exporter-pivot", "positions", "actifs"])
    def test_un_export_absent_dit_ou_le_trouver_et_ou_le_deposer(
        self, commande, capsys, dossier_personnel
    ):
        assert cli.main([commande]) == cli.CODE_ECHEC

        erreur = capsys.readouterr().err
        assert "Export des transactions" in erreur
        assert "toutes les transactions" in erreur
        assert str(dossier_personnel / "exports") in erreur

    def test_le_dossier_de_depot_est_cree_pour_qu_on_puisse_y_deposer(self, dossier_personnel):
        cli.main(["lire"])
        assert (dossier_personnel / "exports").is_dir()

    def test_un_fichier_qui_n_est_pas_un_export_est_nomme(self, dossier_personnel, capsys):
        depot = dossier_personnel / "exports"
        depot.mkdir(parents=True)
        (depot / "releve.csv").write_text("Date;Montant\n", encoding="utf-8")

        assert cli.main(["lire"]) == cli.CODE_ECHEC
        assert "releve.csv" in capsys.readouterr().err


class TestLire:
    def test_le_rapport_montre_les_operations(self, export, capsys):
        code = cli.main(["lire"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Opérations produites : 8" in affichage

    def test_le_rapport_met_en_avant_les_types_inconnus(self, export, capsys):
        cli.main(["lire"])
        affichage = capsys.readouterr().out

        assert "types non traités" in affichage
        assert fictifs.TYPE_INCONNU in affichage

    def test_lire_n_ecrit_aucun_fichier(self, export, dossier_personnel):
        cli.main(["lire"])

        assert not (dossier_personnel / cli.NOM_EXPORT_PIVOT).exists()

    def test_un_export_range_ailleurs_se_lit_avec_export(self, export_ailleurs, capsys):
        # C'est ainsi qu'on regarde l'export de quelqu'un d'autre sans le copier dans le
        # projet : seuls les comptages et les types inconnus comptent alors.
        cli.main(["lire", "--export", str(export_ailleurs)])
        assert f"Lecture de {fictifs.NOMBRE_DE_LIGNES} lignes" in capsys.readouterr().out

    def test_la_lecture_pure_ne_traite_pas_les_actions_gratuites(
        self, export, lecture_pure, capsys
    ):
        # Les titres reçus ne sont pas encore traités (Q-54) : affichés, jamais comptés.
        assert cli.main(["lire"]) == 0
        affichage = capsys.readouterr().out

        assert f"Opérations produites : {fictifs.OPERATIONS_LUES}" in affichage
        assert "CORPORATE_ACTION/BONUS_ISSUE" in affichage
        assert "CASH/STOCKPERK" in affichage

    def test_la_periode_couverte_est_dite(self, export, capsys):
        cli.main(["lire"])
        assert "Période couverte : du 2026-01-02 au 2026-08-01" in capsys.readouterr().out

    def test_les_especes_ne_sont_jamais_recopiees(self, export, capsys):
        cli.main(["lire"])
        affichage = capsys.readouterr().out

        assert "CASH/CARD_TRANSACTION" in affichage
        assert "Boulangerie" not in affichage
        assert "4321" not in affichage


class TestExporterPivot:
    def test_le_csv_est_ecrit_dans_le_dossier_personnel(
        self, export, dossier_personnel, capsys
    ):

        code = cli.main(["exporter-pivot"])
        fichier = dossier_personnel / cli.NOM_EXPORT_PIVOT

        assert code == 0
        assert fichier.exists()
        assert "opération(s) écrite(s)" in capsys.readouterr().out

    def test_le_csv_contient_une_ligne_par_operation(self, export, dossier_personnel):
        cli.main(["exporter-pivot"])

        lignes = (dossier_personnel / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        ).strip().splitlines()
        assert len(lignes) == 9  # huit opérations, plus l'en-tête


class TestPositions:
    def test_le_rapport_montre_les_positions_par_poche(self, export, capsys):
        code = cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Positions détenues" in affichage
        # Cinq parts restent sur l'action du PEA : dix achetées, cinq vendues.
        assert fictifs.ACTIF_ACTION in affichage
        assert "PEA" in affichage and "crypto" in affichage

    def test_une_ligne_ecartee_est_dite_en_tete_des_chiffres(self, export, capsys):
        # Une ligne écartée ne produit aucune anomalie : sans cette réserve, des achats
        # pourraient manquer aux chiffres sans que rien ne le dise hors de « pastory lire ».
        ajouter_a_l_export(export, export_fictif.achat_plan_epargne(transaction_id=""))

        cli.main(["positions", "--hors-ligne"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "1 ligne(s) sans identifiant" in affichage
        assert "pastory lire" in affichage

    def test_un_second_fichier_est_un_autre_portefeuille_pas_un_complement(
        self, export, capsys
    ):
        """D-109 : déposé à côté du premier, l'export d'un proche n'entre pas dans ses
        chiffres. C'est le mélange que le cumul d'avant produisait."""
        from pastory.adaptateurs.trade_republic import depot

        cli.main(["positions", "--hors-ligne"])
        seul = capsys.readouterr().out
        export_fictif.deposer(
            export,
            [export_fictif.achat_ordre_cto(symbol="XX0000000099", name="Titre d'un autre")],
            nom="Un proche.csv",
        )
        depot.ouvrir(export, "Exportation de transactions")

        cli.main(["positions", "--hors-ligne"])
        a_deux = capsys.readouterr().out

        assert "XX0000000099" not in a_deux
        assert a_deux == seul

    def test_le_rapport_previent_qu_un_type_est_inconnu(self, export, capsys):
        # L'export fictif en contient un : aucun chiffre ne peut être tenu pour complet
        # tant qu'on ne l'a pas examiné (règle 5 de CLAUDE.md).

        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "type non traité" in affichage
        assert "pastory lire" in affichage

    def test_les_actions_gratuites_sont_comptees_mais_sans_prix(self, export, capsys):
        cli.main(["positions"])
        affichage = capsys.readouterr().out

        assert "histoire est incomplète" in affichage
        assert "prix à compléter" in affichage

    def test_le_rapport_invite_a_comparer_les_quantites_a_l_application(self, export, capsys):
        # Sans photo du portefeuille, c'est le contrôle qui reste (D-81).
        cli.main(["positions"])

        assert "Contrôle des quantités" in capsys.readouterr().out

    def test_positions_n_ecrit_aucun_fichier(self, export, dossier_personnel):
        cli.main(["positions"])

        assert not (dossier_personnel / "positions.csv").exists()

    def test_au_arrete_les_chiffres_a_la_date_demandee(self, export, capsys):
        code = cli.main(["positions", "--au", "2026-01-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Chiffres arrêtés au 2026-01-31" in affichage
        # Seul le plan d'épargne du 2 janvier a eu lieu : l'action du PEA n'existe pas.
        assert fictifs.ACTIF_ACTION not in affichage

    def test_a_une_date_passee_la_comparaison_des_quantites_est_sans_objet(
        self, export, capsys
    ):
        # L'application ne montre qu'aujourd'hui : comparer à des chiffres de janvier
        # signalerait à tort tout ce qui a bougé depuis.
        cli.main(["positions", "--au", "2026-01-31"])

        assert "Sans objet" in capsys.readouterr().out

    def test_un_evenement_traite_sans_operation_declenche_l_avertissement(
        self, export, capsys, monkeypatch
    ):
        # Un événement traité dont aucune opération n'est sortie est un trou franc dans les
        # totaux : rien d'autre que cette bannière ne le dirait.
        lecture_reelle = assembleur.Lecteur.lire

        def lecture_avec_un_refus(self, depot):
            rapport = lecture_reelle(self, depot)
            rapport.operations_non_produites += 1
            return rapport

        monkeypatch.setattr(assembleur.Lecteur, "lire", lecture_avec_un_refus)

        cli.main(["positions"])

        assert "sans opération produite" in capsys.readouterr().out

    def test_une_date_mal_ecrite_explique_comment_l_ecrire(self, export, capsys):
        with pytest.raises(SystemExit):
            cli.main(["positions", "--au", "31/01/2026"])

        assert "2026-03-15" in capsys.readouterr().err

class TestExporterPositions:
    def test_les_deux_fichiers_sont_ecrits_dans_le_dossier_personnel(
        self, export, dossier_personnel, capsys
    ):

        code = cli.main(["exporter-positions"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert (dossier_personnel / "positions.csv").exists()
        assert (dossier_personnel / "journal.csv").exists()
        assert "ligne(s) de journal" in affichage

    def test_le_journal_a_une_ligne_par_operation(self, export, dossier_personnel):
        cli.main(["exporter-positions"])

        lignes = (
            (dossier_personnel / "journal.csv")
            .read_text(encoding="utf-8-sig")
            .strip()
            .splitlines()
        )
        assert len(lignes) == 9  # huit opérations, plus l'en-tête

# --- Étape 4 : les cours de marché -----------------------------------------------------



def declarer_les_actifs(*actifs: str) -> None:
    """Le fichier qu'aurait laissé « pastory actifs » après relecture (valeurs fictives)."""
    fichier = config_actifs.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    lignes = ["[actifs]"] + [
        f'"{actif}" = {{ ticker = "T{numero}.DE", devise = "EUR" }}'
        for numero, actif in enumerate(actifs, start=1)
    ]
    fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def deposer_un_cours(actif: str, jour: Date, valeur: str, ticker: str | None = None) -> None:
    """Écrit un cours dans le cache, comme si la source l'avait déjà donné.

    Sans ticker, le cours est présumé pris sur la cotation retenue, quelle qu'elle soit : un
    cours pris sur une **autre** cotation n'est jamais employé (D-50, D-85)."""
    Cache().ecrire(
        actif,
        [
            Cours(
                actif=actif,
                date=jour,
                valeur=Decimal(valeur),
                devise="EUR",
                place="XETRA",
                source="Source de test",
                recupere_le=Date(2026, 9, 26),
                ticker=ticker,
            )
        ],
    )


class FauxYahoo:
    """Une source qui ne sort pas de la machine. Aucun test n'appelle le vrai service."""

    nom = "Source de test"

    def __init__(self, propositions=None, series=None):
        self._propositions = propositions or {}
        self._series = series or {}

    def chercher(self, actif):
        return self._propositions.get(actif)

    def serie(self, actif, declaration, debut, fin):
        return [
            Cours(
                actif=actif,
                date=jour,
                valeur=Decimal(valeur),
                devise="EUR",
                place="XETRA",
                source=self.nom,
                recupere_le=Date(2026, 9, 26),
                ticker=declaration.ticker,
            )
            for jour, valeur in self._series.get(actif, [])
            if debut <= jour <= fin
        ]


def brancher(monkeypatch, faux):
    """Remplace la source Yahoo par une fausse, partout où le CLI la construit."""
    monkeypatch.setattr(assembleur, "Yahoo", lambda *args, **kwargs: faux)


class CotationsFictives:
    """Une recherche de cotations qui ne sort pas de la machine (étape 8 quater).

    `recherches` : requête → tickers trouvés. `cours` : ticker → (devise, cours constant). Les
    cours couvrent tous les jours ouvrés, pour que le contrôle par le prix payé puisse se faire.
    """

    nom = "recherche de test"

    def __init__(self, recherches=None, cours=None):
        self.recherches = recherches or {}
        self.cours = cours or {}
        self.requetes: list[str] = []

    def candidats(self, requete):
        self.requetes.append(requete)
        return [Proposition(ticker=ticker) for ticker in self.recherches.get(requete, [])]

    def serie(self, actif, declaration, debut, fin):
        if declaration.ticker not in self.cours:
            raise ErreurDeSource("ticker inconnu")
        devise, valeur = self.cours[declaration.ticker]
        if devise != declaration.devise:
            raise ErreurDeSource(f"coté en {devise}")
        jours = [debut + timedelta(days=n) for n in range((fin - debut).days + 1)]
        return [
            Cours(actif, jour, Decimal(valeur), devise, "XETRA", self.nom, Date(2026, 9, 26),
                  declaration.ticker)
            for jour in jours
            if jour.weekday() < 5
        ]

    def serie_brute(self, ticker, debut, fin):
        raise ErreurDeSource("aucune cotation de référence dans ce test")


def brancher_les_cotations(monkeypatch, faux):
    """Remplace la recherche des cotations par une fausse."""
    monkeypatch.setattr(assembleur, "source_des_cotations", lambda: faux)


class TestLesReglagesTrouves:
    """`pastory actifs` : ce que l'application a trouvé seule, avec sa source (D-80)."""

    def test_le_type_vient_de_l_export_avec_sa_source(self, export, capsys):
        code = cli.main(["actifs", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Réglages de vos actifs" in affichage
        assert "ETF (fonds)" in affichage
        assert "export Trade Republic (colonne asset_class)" in affichage

    def test_la_commande_n_ecrit_jamais_le_fichier_des_corrections(self, export):
        # D-78 : un fichier écrit à la main n'est jamais réécrit par l'application.
        cli.main(["actifs", "--hors-ligne"])
        assert not config_actifs.chemin().exists()

    def test_hors_ligne_une_cotation_jamais_cherchee_est_un_trou_explique(self, export, capsys):
        cli.main(["actifs", "--hors-ligne"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "INTROUVABLE" in affichage
        assert "sans accès au réseau" in affichage
        assert "introuvable(s)" in affichage

    def test_une_cotation_trouvee_s_affiche_avec_son_controle(
        self, export, monkeypatch, capsys
    ):
        # L'ETF fictif a été acheté 25,00 € le 2 janvier : une clôture à 25,10 € le confirme.
        brancher_les_cotations(
            monkeypatch,
            CotationsFictives({fictifs.ACTIF_ETF: ["AAAA.DE"]}, {"AAAA.DE": ("EUR", "25.10")}),
        )

        cli.main(["actifs"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "AAAA.DE, en EUR" in affichage
        assert "trouvée par son ISIN" in affichage
        assert "du prix payé" in affichage

    def test_une_cotation_en_dollars_n_est_jamais_retenue(self, export, monkeypatch, capsys):
        # Le piège de D-48 : la cotation londonienne en dollars d'un ETF qui cote aussi en euros.
        brancher_les_cotations(
            monkeypatch,
            CotationsFictives({fictifs.ACTIF_ETF: ["BBBB.L"]}, {"BBBB.L": ("USD", "29")}),
        )

        cli.main(["actifs"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "BBBB.L, en" not in affichage
        assert "aucune en euros" in affichage

    def test_la_cotation_d_une_crypto_vient_du_code_de_la_banque(
        self, export, monkeypatch, capsys
    ):
        brancher_les_cotations(
            monkeypatch, CotationsFictives(cours={"BTC-EUR": ("EUR", "30200")})
        )

        cli.main(["actifs"])

        assert "BTC-EUR, en EUR" in capsys.readouterr().out

    def test_une_correction_l_emporte_et_se_dit(self, export, capsys):
        declarer_les_actifs(fictifs.ACTIF_ETF)

        cli.main(["actifs", "--hors-ligne"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "T1.DE, en EUR" in affichage
        assert "corrigé par vous dans actifs.toml" in affichage

    def test_une_correction_orpheline_est_signalee(self, export, capsys):
        # L'ancien code pytr d'une crypto ne désigne plus rien depuis l'export officiel.
        declarer_les_actifs("XF000ANCIEN01")

        cli.main(["actifs", "--hors-ligne"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "XF000ANCIEN01" in affichage
        assert "ne désignent aucun actif de vos exports" in affichage

    def test_avec_un_export_d_ailleurs_aucune_recherche_n_est_lancee(
        self, export_ailleurs, monkeypatch, capsys
    ):
        # Envoyer les ISIN de quelqu'un d'autre à un service extérieur, ce serait divulguer ce
        # qu'il détient (règle 2 de CLAUDE.md). Aucune requête ne doit partir.
        espion = CotationsFictives()
        brancher_les_cotations(monkeypatch, espion)
        demandes = []
        monkeypatch.setattr(assembleur, "liste_des_etf", lambda: demandes.append(1))

        assert cli.main(["actifs", "--export", str(export_ailleurs)]) == 0

        assert espion.requetes == []
        assert demandes == []
        assert "l'export de quelqu'un d'autre" in " ".join(capsys.readouterr().out.split())

    def test_le_rapport_s_affiche_en_cp1252_sans_depasser_100_colonnes(
        self, export, monkeypatch, capsys
    ):
        brancher_les_cotations(
            monkeypatch,
            CotationsFictives({fictifs.ACTIF_ETF: ["AAAA.DE"]}, {"AAAA.DE": ("EUR", "25.10")}),
        )
        cli.main(["actifs"])
        affichage = capsys.readouterr().out

        affichage.encode("cp1252")
        assert max(len(ligne) for ligne in affichage.splitlines()) <= 100

    def test_les_positions_annoncent_les_reglages_introuvables(self, export, capsys):
        cli.main(["positions", "--hors-ligne"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "réglage(s) introuvable(s)" in affichage
        assert "pastory actifs" in affichage


class TestOublierReglages:
    def test_sans_precision_la_commande_refuse_d_agir(self, capsys):
        assert cli.main(["oublier-reglages"]) == cli.CODE_ECHEC
        assert "--tout" in capsys.readouterr().err

    def test_une_cotation_oubliee_est_recherchee_de_nouveau(self, export, monkeypatch, capsys):
        faux = CotationsFictives(
            {fictifs.ACTIF_ETF: ["AAAA.DE"]}, {"AAAA.DE": ("EUR", "25.10")}
        )
        brancher_les_cotations(monkeypatch, faux)
        cli.main(["actifs"])
        faux.requetes.clear()
        cli.main(["actifs"])
        assert fictifs.ACTIF_ETF not in faux.requetes

        assert cli.main(["oublier-reglages", "--actif", fictifs.ACTIF_ETF]) == 0
        cli.main(["actifs"])
        assert fictifs.ACTIF_ETF in faux.requetes


class TestCours:
    def test_sans_actif_declare_la_commande_dit_quoi_faire(self, export, capsys):
        code = cli.main(["cours"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "pastory actifs" in capsys.readouterr().err

    def test_les_cours_sont_recuperes_et_mis_en_cache(self, export, monkeypatch, capsys):
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(
            monkeypatch,
            FauxYahoo(
                series={
                    fictifs.ACTIF_ACTION_B: [
                        (Date(2026, 2, 26), "20.00"),
                        (Date(2026, 2, 27), "21.00"),
                    ]
                }
            ),
        )

        code = cli.main(["cours"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "2 cours ajouté(s) au cache" in affichage
        serie = Cache().lire(fictifs.ACTIF_ACTION_B)
        assert serie[Date(2026, 2, 27)].valeur == Decimal("21.00")

    def test_relancer_la_commande_ne_redemande_rien(self, export, monkeypatch, capsys):
        # D-50 : un cours en cache est définitif. La seconde exécution n'ajoute rien.
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(
            monkeypatch,
            FauxYahoo(series={fictifs.ACTIF_ACTION_B: [(Date(2026, 2, 27), "21.00")]}),
        )

        cli.main(["cours"])
        capsys.readouterr()
        cli.main(["cours"])

        assert "0 cours ajouté(s) au cache" in capsys.readouterr().out

    def test_un_actif_sans_cotation_demande_explicitement_est_refuse(self, export, capsys):
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)

        code = cli.main(["cours", "--actif", fictifs.ACTIF_ETF])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        erreur = capsys.readouterr().err
        assert "n'a pas de cotation" in erreur
        assert "pastory actifs" in erreur

    def test_un_actif_sans_aucun_cours_est_signale(self, export, monkeypatch, capsys):
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        brancher(monkeypatch, FauxYahoo())

        code = cli.main(["cours"])

        assert code == cli.CODE_DECLARATION_ATTENDUE
        assert "sans cours" in capsys.readouterr().err


class TestOublierCours:
    def test_sans_precision_la_commande_refuse_d_agir(self, capsys):
        assert cli.main(["oublier-cours"]) == cli.CODE_ECHEC
        assert "--tout" in capsys.readouterr().err

    def test_un_actif_s_oublie_seul(self, capsys):
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 2, 27), "10.00")
        deposer_un_cours(fictifs.ACTIF_ACTION, Date(2026, 2, 27), "20.00")

        code = cli.main(["oublier-cours", "--actif", fictifs.ACTIF_ETF])

        assert code == 0
        assert "1 actif(s) oublié(s)" in capsys.readouterr().out
        assert Cache().lire(fictifs.ACTIF_ETF) == {}
        assert Cache().lire(fictifs.ACTIF_ACTION) != {}

    def test_tout_le_cache_s_oublie_sur_demande_explicite(self, capsys):
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 2, 27), "10.00")
        deposer_un_cours(fictifs.ACTIF_ACTION, Date(2026, 2, 27), "20.00")

        assert cli.main(["oublier-cours", "--tout"]) == 0
        assert Cache().actifs() == []
        assert "oublié(s)" in capsys.readouterr().out

    def test_un_cache_vide_ne_fait_pas_echouer_la_commande(self, capsys):
        assert cli.main(["oublier-cours", "--tout"]) == 0
        assert "Rien à oublier" in capsys.readouterr().out

    @pytest.mark.parametrize("saisie", ["", "   ", "..."])
    def test_un_identifiant_inutilisable_donne_un_message_et_non_une_trace(
        self, saisie, capsys
    ):
        # L'ISIN est tapé à la main : une faute de frappe ne doit pas produire une trace
        # Python à l'écran.
        assert cli.main(["oublier-cours", "--actif", saisie]) == cli.CODE_ECHEC
        assert "identifiant d'actif utilisable" in capsys.readouterr().err


class TestPositionsAvecCours:
    """Le contrôle qui prouve l'étape : D-15 branché de bout en bout."""

    def test_un_titre_recu_sans_prix_est_valorise_au_dernier_jour_cote(self, export, capsys):
        # Les actions gratuites de l'export fictif tombent un dimanche (2026-03-01) : le cours
        # retenu est celui du vendredi, et le rapport doit le dire.
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "1 prix complété(s)" in affichage
        # 3 parts x 12,50 = 37,50
        assert "37,50" in affichage
        assert "dernier jour coté avant le 2026-03-01" in affichage
        # Le moteur ne réclame plus de prix pour cet actif : c'est le signe que D-15 est
        # branché. (L'export fictif garde une position incomplète pour une autre raison —
        # une distribution de capital sur un actif jamais acheté — que les cours ne peuvent
        # pas réparer.)
        assert "prix à compléter" not in affichage

    def test_sans_cours_le_rapport_explique_ce_qui_manque(self, export, capsys):
        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "attendent toujours un prix" in affichage
        assert "pastory actifs" in affichage
        # Le moteur continue de dire que le capital est sous-estimé (D-45).
        assert "histoire est incomplète" in affichage

    def test_hors_ligne_aucun_appel_n_est_fait(self, export, monkeypatch, capsys):
        appels = []

        class YahooInterdit:
            nom = "interdit"

            def __init__(self, *args, **kwargs):
                appels.append("construit")

            def serie(self, *args, **kwargs):  # pragma: no cover - ne doit pas être appelé
                appels.append("serie")
                raise AssertionError("aucun appel réseau ne doit partir en hors-ligne")

        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        monkeypatch.setattr(assembleur, "Yahoo", YahooInterdit)

        assert cli.main(["positions", "--hors-ligne"]) == 0
        assert "serie" not in appels
        assert "pastory cours" in capsys.readouterr().out

    def test_le_rapport_des_cours_s_affiche_en_cp1252(self, export, capsys):
        # La console Windows écrit en cp1252 : un rapport juste mais inaffichable ferait
        # échouer la commande au moment de l'imprimer. Un test par rapport, comme pour la
        # lecture et le moteur.
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        cli.main(["positions", "--hors-ligne"])

        capsys.readouterr().out.encode("cp1252")

    def test_le_journal_porte_le_montant_deduit(self, export, capsys):
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        assert cli.main(["exporter-positions", "--hors-ligne"]) == 0
        capsys.readouterr()

        journal = (emplacements.dossier_personnel() / "journal.csv").read_text(
            encoding="utf-8-sig"
        )
        assert "37,50" in journal

    def test_le_csv_des_operations_dit_que_le_montant_est_deduit(self, export, capsys):
        # Le rapport affirme que les CSV marquent ces montants : c'est `operations.csv`, avec
        # sa colonne de provenance, qui le fait. Sans complétion ici, ce fichier afficherait
        # « à compléter » là où les positions montrent un montant.
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")

        assert cli.main(["exporter-pivot", "--hors-ligne"]) == 0
        affichage = capsys.readouterr().out

        operations = (emplacements.dossier_personnel() / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        )
        # L'export fictif contient deux entrées de titres reçus : une action gagnée, dont le
        # prix est lu dans le texte, et les actions gratuites, qui n'en ont aucun. C'est de
        # cette seconde qu'il s'agit.
        ligne_des_titres = next(
            ligne for ligne in operations.splitlines() if "evt-gratuites-1" in ligne
        )
        assert "37,50" in ligne_des_titres
        assert "deduction" in ligne_des_titres
        assert tableur.VALEUR_A_COMPLETER not in ligne_des_titres
        assert "1 prix complété(s)" in affichage

    def test_sans_cours_le_csv_des_operations_dit_a_completer(self, export, capsys):
        assert cli.main(["exporter-pivot", "--hors-ligne"]) == 0
        capsys.readouterr()

        operations = (emplacements.dossier_personnel() / cli.NOM_EXPORT_PIVOT).read_text(
            encoding="utf-8-sig"
        )
        # L'export fictif contient deux entrées de titres reçus : une action gagnée, dont le
        # prix est lu dans le texte, et les actions gratuites, qui n'en ont aucun. C'est de
        # cette seconde qu'il s'agit.
        ligne_des_titres = next(
            ligne for ligne in operations.splitlines() if "evt-gratuites-1" in ligne
        )
        assert tableur.VALEUR_A_COMPLETER in ligne_des_titres


# --- Étape 5 : la valorisation et les rendements ------------------------------------------


class TestValorisationEtRendements:
    """Les deux blocs de l'étape 5 dans « positions », et les quatre CSV de plus."""

    def preparer(self) -> None:
        declarer_les_actifs(fictifs.ACTIF_ACTION_B)
        # Le cours qui complète les actions gratuites du 1er mars (D-15)...
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 2, 27), "12.50")
        # ...et celui qui valorise la position à la fin de la période.
        deposer_un_cours(fictifs.ACTIF_ACTION_B, Date(2026, 3, 27), "13.00")

    def test_la_valeur_et_les_chiffres_cles_s_affichent(self, export, capsys):
        self.preparer()

        code = cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert "Valeur des actifs au 2026-03-31" in affichage
        # 3 actions gratuites x 13,00, au cours du vendredi 27 mars.
        assert "39,00" in affichage
        assert "cours du 2026-03-27 (dernier jour coté avant le 2026-03-31)" in affichage
        assert "Les trois chiffres clés (D-22)" in affichage
        assert "GAIN en euros" in affichage

    def test_les_actifs_non_declares_sortent_des_totaux_et_les_refus_sont_listes(
        self, export, capsys
    ):
        self.preparer()

        cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert "Non valorisés, exclus de tous les totaux (D-53)" in affichage
        assert "PARTIEL" in affichage
        # Le bloc « Cours de marché » explique pourquoi : ces actifs n'ont pas de cotation,
        # parce que hors ligne rien n'a pu être cherché.
        assert "aucune cotation trouvée" in affichage
        assert "sans accès au réseau" in " ".join(affichage.split())

    def test_depuis_borne_la_periode(self, export, capsys):
        self.preparer()

        code = cli.main(
            ["positions", "--hors-ligne", "--depuis", "2026-03-01", "--au", "2026-03-31"]
        )
        affichage = capsys.readouterr().out

        assert code == 0
        assert "du 2026-03-01 jusqu'au 2026-03-31" in affichage

    def test_une_periode_a_l_envers_est_refusee_avant_toute_lecture(self, export, capsys):
        self.preparer()

        code = cli.main(
            ["positions", "--hors-ligne", "--depuis", "2026-06-01", "--au", "2026-03-31"]
        )
        sortie = capsys.readouterr()

        assert code == 1
        assert "après la fin" in sortie.err
        # Rien n'a été lu ni calculé : une période impossible se refuse tout de suite.
        assert sortie.out == ""

    def test_exporter_positions_ecrit_les_six_fichiers(self, export, capsys):
        self.preparer()

        code = cli.main(["exporter-positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = capsys.readouterr().out

        assert code == 0
        personnel = emplacements.dossier_personnel()
        for nom in (
            "positions.csv",
            "journal.csv",
            "valorisation.csv",
            "flux.csv",
            "sous_periodes_twrr.csv",
            "evolution.csv",
        ):
            assert (personnel / nom).exists(), nom
        assert "TRI.PAIEMENTS" in affichage

        valorisation = (personnel / "valorisation.csv").read_text(encoding="utf-8-sig")
        assert "39,00" in valorisation
        # Le bloc « Cours de marché » est écrit après la construction de l'évolution : les
        # refus qu'elle rencontre y figurent. Ici, entre le 27 février et le 27 mars, il n'y a
        # aucun cours : dès le 10 mars, le dernier connu a plus de dix jours, et l'évolution le
        # dit — ce que ni la complétion ni la valorisation au 31 mars n'auraient signalé.
        assert "cours indisponible" in affichage
        assert "2026-03-10" in affichage
        evolution = (personnel / "evolution.csv").read_text(encoding="utf-8-sig").splitlines()
        # Un jour par ligne, de la première opération (2 janvier) au 31 mars : 89 jours.
        assert len(evolution) == 1 + 89
        assert evolution[-1].startswith("2026-03-31;")

    def test_les_deux_blocs_s_affichent_en_cp1252(self, export, capsys):
        self.preparer()

        cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])

        capsys.readouterr().out.encode("cp1252")

    def test_sans_au_la_valeur_est_celle_de_la_derniere_cloture_connue(self, export, capsys):
        # Le cache ne contient jamais le jour même (D-52) : sans cours récent, la position
        # n'est simplement pas valorisée, et le rapport le dit — jamais un zéro.
        self.preparer()

        code = cli.main(["positions", "--hors-ligne"])
        affichage = capsys.readouterr().out

        assert code == 0
        assert f"Valeur des actifs au {Date.today().isoformat()}" in affichage
        assert "Non valorisés" in affichage


# --- Étape 6 : les coûts estimés, la valeur réelle, et le TER proposé ------------------


def declarer_les_actifs_complets(*declarations):
    """Le fichier qu'aurait laissé l'assistant après relecture, type et TER compris.

    Chaque déclaration est un triplet `(actif, type, TER)` ; un TER à `None` est un actif dont
    l'utilisateur n'a pas encore validé les frais courants.
    """
    fichier = config_actifs.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    lignes = ["[actifs]"]
    for numero, (actif, type_actif, ter) in enumerate(declarations, start=1):
        champs = [f'ticker = "T{numero}.DE"', 'devise = "EUR"', f'type = "{type_actif}"']
        if ter is not None:
            champs.append(f"ter_pour_cent = {ter}")
        lignes.append(f'"{actif}" = {{ {", ".join(champs)} }}')
    fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def declarer_le_pea(premier_versement="2021-03-01"):
    fichier = config_fiscalite.chemin()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(
        f"[pea]\npremier_versement = {premier_versement}\n", encoding="utf-8"
    )


class TestCoutsEstimesEtValeurReelle:
    """Les trois blocs de l'étape 6, sur l'export fictif, avec des cours en cache."""

    def preparer(self, avec_type=True):
        """Les deux positions détenues au 28 février : un ETF en CTO, une action en PEA.

        Les déclarer toutes les deux est nécessaire : la valeur réelle d'une poche n'existe
        que si **toutes** ses positions ont un cours (D-53), et l'impôt du PEA se calcule sur
        le plan entier.
        """
        if avec_type:
            declarer_les_actifs_complets(
                (fictifs.ACTIF_ETF, "etf", "0.20"), (fictifs.ACTIF_ACTION, "action", None)
            )
        else:
            declarer_les_actifs(fictifs.ACTIF_ETF, fictifs.ACTIF_ACTION)
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 2, 27), "30.00")
        deposer_un_cours(fictifs.ACTIF_ACTION, Date(2026, 2, 27), "25.00")

    def test_le_rapport_montre_les_couts_payes_avec_leur_poids(self, export, capsys):
        self.preparer()

        assert cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"]) == 0

        affichage = capsys.readouterr().out
        assert "Coûts payés du" in affichage
        assert "poids" in affichage

    def test_le_rapport_montre_le_spread_et_les_frais_courants_estimes(self, export, capsys):
        self.preparer()

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = capsys.readouterr().out
        assert "Coûts estimés, jamais facturés" in affichage
        assert "ECART DE PRIX (SPREAD)" in affichage
        assert "FRAIS COURANTS DES ETF" in affichage
        # Le spread est déjà dans le prix : le rapport doit le dire, sinon on le croit facturé.
        assert "aucun relevé ne le montre" in affichage

    def test_le_rapport_montre_la_valeur_reelle_et_ses_retenues(self, export, capsys):
        self.preparer()
        declarer_le_pea()

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = capsys.readouterr().out
        assert "Valeur réelle au 2026-02-28" in affichage
        assert "frais de vente estimés" in affichage
        assert "écart de prix estimé" in affichage
        assert "impôt estimé" in affichage
        assert "VALEUR REELLE" in affichage
        # Chaque taux dit d'où il vient, et le calcul dit ce qu'il suppose.
        assert "D'où viennent les taux" in affichage
        assert "Ce que ce calcul suppose" in affichage
        # Les deux poches détenues ont chacune leur colonne et leur règle.
        assert "PEA" in affichage and "CTO" in affichage

    def test_le_rapport_cite_le_taux_de_2026_et_sa_source(self, export, capsys):
        self.preparer()
        declarer_le_pea()

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = capsys.readouterr().out
        assert "18,6 %" in affichage
        assert "legifrance" in affichage

    def test_un_plan_plus_ancien_que_l_export_n_a_pas_de_date(self, export, capsys):
        """D-59 : l'ancienneté décide du taux. Un achat sur le PEA **avant** le premier
        versement que montre l'export prouve que le plan est plus ancien : la date n'est pas
        retenue, et rien n'est inventé à sa place (D-80)."""
        self.preparer()
        ajouter_a_l_export(
            export,
            export_fictif.achat_plan_epargne(
                datetime="2026-01-05T09:15:00.000Z", date="2026-01-05"
            ),
        )

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = " ".join(capsys.readouterr().out.split())
        assert "date d'ouverture du PEA inconnue" in affichage
        assert "fiscalite.toml" not in affichage

    def test_la_date_du_pea_trouvee_dans_l_export_se_dit(self, export, capsys):
        self.preparer()
        ajouter_a_l_export(
            export,
            export_fictif.versement_pea(datetime="2026-01-02T07:00:00.000Z", date="2026-01-02"),
        )

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = " ".join(capsys.readouterr().out.split())
        assert "premier versement le 2026-01-02, trouvée dans votre export" in affichage
        assert "transféré" in affichage

    def test_une_date_de_pea_mal_ecrite_est_expliquee_sans_trace(self, export, capsys):
        self.preparer()
        declarer_le_pea('"2021-03-01"')

        code = cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        assert code == cli.CODE_ECHEC
        assert "sans guillemets" in capsys.readouterr().err

    def test_le_type_vient_de_l_export_sans_rien_declarer(self, export, capsys):
        """D-82 : le type est une donnée de la banque. Sans le déclarer, le spread de l'ETF et
        de l'action est estimé quand même."""
        self.preparer(avec_type=False)

        cli.main(["positions", "--hors-ligne", "--au", "2026-02-28"])

        affichage = capsys.readouterr().out
        assert "leur type (ETF, action, crypto) n'est pas connu" not in affichage
        assert "spread estimé, total" in affichage

    def test_les_deux_csv_de_l_etape_sont_ecrits(self, export, dossier_personnel, capsys):
        self.preparer()
        declarer_le_pea()

        assert cli.main(["exporter-positions", "--hors-ligne", "--au", "2026-02-28"]) == 0

        couts = dossier_personnel / "couts.csv"
        valeur = dossier_personnel / "valeur_reelle.csv"
        assert couts.exists()
        assert valeur.exists()
        affichage = capsys.readouterr().out
        assert "couts.csv" in affichage
        assert "valeur_reelle.csv" in affichage

    def test_le_csv_des_couts_retombe_sur_celui_des_positions(
        self, export, dossier_personnel
    ):
        """Le contrôle du cahier : les deux fichiers doivent dire le même total, sinon on ne
        sait plus lequel croire."""
        self.preparer()

        cli.main(["exporter-positions", "--hors-ligne", "--au", "2026-02-28"])

        couts = lire_csv(dossier_personnel / "couts.csv")
        positions = lire_csv(dossier_personnel / "positions.csv")
        paye = sum(montant(ligne["cout_paye"]) for ligne in couts)
        attendu = sum(
            montant(ligne["frais"]) + montant(ligne["taxes"]) for ligne in positions
        )
        assert paye == attendu
        # Les colonnes que le propriétaire utilise doivent être là, nommées en français.
        assert {"poids", "spread_estime", "moment"} <= set(couts[0])

    def test_le_csv_de_la_valeur_reelle_a_trois_niveaux(self, export, dossier_personnel):
        self.preparer()
        declarer_le_pea()

        cli.main(["exporter-positions", "--hors-ligne", "--au", "2026-02-28"])

        lignes = lire_csv(dossier_personnel / "valeur_reelle.csv")
        niveaux = {ligne["niveau"] for ligne in lignes}
        assert niveaux == {"position", "poche", "total"}
        # L'impôt ne figure qu'au niveau de la poche : on n'additionne pas des impôts de ligne.
        position = next(ligne for ligne in lignes if ligne["niveau"] == "position")
        assert position["impot_estime"] == tableur.VALEUR_SANS_OBJET


class TestLeTerTrouve:
    """Les frais courants d'un ETF : trouvés, contrôlés, montrés avec leur source (D-61, D-80)."""

    def test_le_ter_de_la_liste_s_applique_avec_sa_source_et_sa_reserve(
        self, export, monkeypatch, capsys
    ):
        brancher_la_liste_des_etf(
            monkeypatch, {fictifs.ACTIF_ETF: ("0.20", "ETF Exemple", "Accumulating")}
        )

        assert cli.main(["actifs"]) == 0
        affichage = " ".join(capsys.readouterr().out.split())

        assert "0,2 % par an" in affichage
        assert "liste de test, au 2026-09-28" in affichage

    def test_le_ter_de_l_emetteur_fait_foi(self, export, monkeypatch, capsys):
        brancher_la_liste_des_etf(monkeypatch, {fictifs.ACTIF_ETF: ("0.20", None, None)})
        monkeypatch.setattr(
            assembleur, "frais_courants_de_l_emetteur", lambda: FraisDeLEmetteur("0.12")
        )

        cli.main(["actifs"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "0,12 % par an" in affichage
        assert "liste de test donne 0,2 %" in affichage

    def test_une_liste_injoignable_laisse_un_trou_explique(self, export, monkeypatch, capsys):
        monkeypatch.setattr(
            assembleur,
            "liste_des_etf",
            lambda: (_ for _ in ()).throw(ErreurDeSource("injoignable")),
        )

        assert cli.main(["actifs"]) == 0
        affichage = " ".join(capsys.readouterr().out.split())
        assert "injoignable" in affichage

    def test_hors_ligne_aucune_liste_n_est_demandee(self, export, monkeypatch):
        demandes = []
        monkeypatch.setattr(assembleur, "liste_des_etf", lambda: demandes.append(1))

        assert cli.main(["actifs", "--hors-ligne"]) == 0

        assert demandes == []

    def test_le_ter_n_est_cherche_que_pour_un_etf(self, export, monkeypatch, capsys):
        """Une action ou une crypto ne prélève aucun frais courant : chercher son TER
        enverrait chercher un chiffre qui n'existe pas."""
        brancher_la_liste_des_etf(monkeypatch, {fictifs.ACTIF_ACTION: ("0.20", None, None)})

        cli.main(["actifs"])
        affichage = capsys.readouterr().out
        bloc_de_l_action = affichage.split(fictifs.ACTIF_ACTION, 1)[1].split("\n\n", 1)[0]

        assert "frais courants" not in bloc_de_l_action

    def test_le_ter_trouve_sert_au_calcul_et_sa_source_s_affiche(
        self, export, monkeypatch, capsys
    ):
        declarer_les_actifs(fictifs.ACTIF_ETF)
        deposer_un_cours(fictifs.ACTIF_ETF, Date(2026, 3, 31), "26.00")
        brancher_la_liste_des_etf(monkeypatch, {fictifs.ACTIF_ETF: ("0.20", None, None)})
        cli.main(["actifs"])  # trouve et garde le TER
        capsys.readouterr()

        cli.main(["positions", "--hors-ligne", "--au", "2026-03-31"])
        affichage = " ".join(capsys.readouterr().out.split())

        assert "D'où viennent les TER" in affichage
        assert "liste de test, au 2026-09-28" in affichage


class FraisDeLEmetteur:
    nom = "émetteur de test"

    def __init__(self, ter):
        self.ter = ter

    def frais_courants(self, actif):
        return FraisCourantsProposes(
            ter_pour_cent=Decimal(self.ter), source=self.nom, date=Date(2026, 6, 1)
        )


"""La poche que l'export fictif ne permet pas de déduire, déclarée comme le ferait l'utilisateur."""


def deposer_une_composition(actif: str, pays: str = "US", arrete_le: str = "2026-08-31") -> None:
    """Écrit une composition dans le cache, comme si la source l'avait déjà donnée."""
    CacheDeCompositions().ecrire(
        Composition(
            actif=actif,
            pays=(Part(pays, Decimal("70")),),
            secteurs=(Part("technology", Decimal("60")),),
            classes=(Part("stock", Decimal("100")),),
            arrete_le=Date.fromisoformat(arrete_le),
            intitule_de_la_date="champ de la source de test",
            source="Source de test",
            recupere_le=Date(2026, 9, 27),
            replication="physique",
            document="https://exemple.test/dic.pdf",
        )
    )


class TestComposition:
    """La commande qui montre ce qu'il y a à l'intérieur des actifs détenus (étape 7)."""

    def test_elle_dit_ce_qu_elle_sait_de_chaque_actif(self, export, capsys):
        declarer_les_actifs_complets(
            (fictifs.ACTIF_ETF, "etf", "0.20"),
            (fictifs.ACTIF_ACTION, "action", None),
            (fictifs.ACTIF_FONDS, "etf", "0.25"),
            (fictifs.ACTIF_ACTION_B, "action", None),
            (fictifs.ACTIF_CRYPTO, "crypto", None),
        )
        deposer_une_composition(fictifs.ACTIF_ETF)

        code = cli.main(["composition"])

        affichage = capsys.readouterr().out
        assert code == 0
        assert "Morningstar" in affichage
        assert "1 pays, 1 secteur(s), arrêté au 2026-08-31" in affichage
        assert "https://exemple.test/dic.pdf" in affichage

    def test_une_crypto_est_presentee_comme_telle_et_non_comme_un_manque(self, export, capsys):
        # D-62 : le message est lu par quelqu'un qui n'a pas suivi la construction du projet.
        declarer_les_actifs_complets((fictifs.ACTIF_CRYPTO, "crypto", None))

        cli.main(["composition"])

        affichage = capsys.readouterr().out
        assert "ni pays ni secteur" in affichage
        assert "pas une donnée manquante" in affichage

    def test_les_origines_des_referentiels_sont_affichees(self, export, capsys):
        declarer_les_actifs_complets((fictifs.ACTIF_ETF, "etf", "0.20"))

        cli.main(["composition"])

        affichage = capsys.readouterr().out
        assert "Secteurs :" in affichage
        assert "Zones :" in affichage
        assert "vérifiée le" in affichage

    def test_un_actif_sans_composition_recoit_un_motif(self, export, capsys):
        declarer_les_actifs_complets((fictifs.ACTIF_ETF, "etf", "0.20"))

        cli.main(["composition", "--hors-ligne"])

        affichage = capsys.readouterr().out
        assert "aucune composition" in affichage
        assert "--hors-ligne" in affichage


class TestOublierComposition:
    def test_sans_precision_la_commande_refuse(self, capsys):
        assert cli.main(["oublier-composition"]) == cli.CODE_ECHEC
        assert "--tout" in capsys.readouterr().err

    def test_une_composition_s_oublie_seule(self, capsys):
        deposer_une_composition(fictifs.ACTIF_ETF)
        deposer_une_composition(fictifs.ACTIF_ACTION)

        code = cli.main(["oublier-composition", "--actif", fictifs.ACTIF_ETF])

        assert code == 0
        assert "1 composition(s) oubliée(s)" in capsys.readouterr().out
        assert CacheDeCompositions().lire(fictifs.ACTIF_ETF) is None
        assert CacheDeCompositions().lire(fictifs.ACTIF_ACTION) is not None

    def test_tout_s_oublie_sur_demande_explicite(self, capsys):
        deposer_une_composition(fictifs.ACTIF_ETF)

        assert cli.main(["oublier-composition", "--tout"]) == 0
        assert CacheDeCompositions().actifs() == []

    def test_un_cache_vide_ne_fait_pas_echouer_la_commande(self, capsys):
        assert cli.main(["oublier-composition", "--tout"]) == 0
        assert "Rien à oublier" in capsys.readouterr().out


class TestPositionsAvecRepartition:
    """Le contrôle qui prouve l'étape : la répartition branchée de bout en bout."""

    def test_le_bloc_de_repartition_apparait_dans_le_rapport(self, export, capsys):
        declarer_les_actifs_complets(
            (fictifs.ACTIF_ETF, "etf", "0.20"),
            (fictifs.ACTIF_ACTION, "action", None),
            (fictifs.ACTIF_FONDS, "etf", "0.25"),
            (fictifs.ACTIF_ACTION_B, "action", None),
            (fictifs.ACTIF_CRYPTO, "crypto", None),
        )
        declarer_le_pea()
        for actif in (
            fictifs.ACTIF_ETF,
            fictifs.ACTIF_ACTION,
            fictifs.ACTIF_FONDS,
            fictifs.ACTIF_ACTION_B,
            fictifs.ACTIF_CRYPTO,
        ):
            deposer_un_cours(actif, Date(2026, 2, 27), "10.00")
        deposer_une_composition(fictifs.ACTIF_ETF)

        code = cli.main(["positions", "--au", "2026-02-27"])

        affichage = capsys.readouterr().out
        assert code == 0
        assert "REPARTITION DU PORTEFEUILLE" in affichage
        assert "Par zone et par pays" in affichage
        assert "Amérique du Nord" in affichage
        # Les actifs dont la composition est inconnue sortent des totaux, et le disent : c'est
        # le comportement qui distingue une répartition honnête d'un camembert qui fait 100 %.
        assert "Non couvert : composition inconnue" in affichage
        assert "ne font donc pas 100 %" in affichage

    def test_les_trois_csv_de_repartition_sont_ecrits(self, export, capsys, dossier_personnel):
        declarer_les_actifs_complets(
            (fictifs.ACTIF_ETF, "etf", "0.20"),
            (fictifs.ACTIF_ACTION, "action", None),
            (fictifs.ACTIF_FONDS, "etf", "0.25"),
            (fictifs.ACTIF_ACTION_B, "action", None),
            (fictifs.ACTIF_CRYPTO, "crypto", None),
        )
        declarer_le_pea()
        for actif in (
            fictifs.ACTIF_ETF,
            fictifs.ACTIF_ACTION,
            fictifs.ACTIF_FONDS,
            fictifs.ACTIF_ACTION_B,
            fictifs.ACTIF_CRYPTO,
        ):
            deposer_un_cours(actif, Date(2026, 2, 27), "10.00")
        deposer_une_composition(fictifs.ACTIF_ETF)

        assert cli.main(["exporter-positions", "--au", "2026-02-27"]) == 0

        for nom in ("repartition_classes.csv", "repartition_pays.csv", "repartition_secteurs.csv"):
            assert (dossier_personnel / nom).exists(), nom

        # L'origine de chaque composition, dans le tableur et pas seulement à l'écran : sans
        # elle, on ne peut pas contrôler quel actif a suivi quelle règle de pays (D-66, D-72).
        origines = dossier_personnel / "origines_des_compositions.csv"
        assert origines.exists()
        contenu = origines.read_text(encoding="utf-8-sig")
        assert fictifs.ACTIF_ETF in contenu

        affichage = capsys.readouterr().out
        assert "Répartition, avec ce qui n'y entre pas" in affichage
        assert "Source et règle de pays de chaque composition" in affichage


class TestLExportDUnTiers:
    """Relecture de l'étape 8 quater : avec `--export`, **aucun** appel réseau (règle 2).

    Depuis que le type vient de la banque et que le secours s'essaie seul, chaque ISIN d'un tiers
    serait parti vers les sources de composition si `positions` restait en ligne."""

    @pytest.mark.parametrize("commande", ["positions", "exporter-pivot", "composition"])
    def test_rien_n_est_demande_en_ligne(self, commande, export_ailleurs, monkeypatch):
        en_ligne = []
        vrai_cours = assembleur.fournisseur_de_cours
        vraies_compositions = assembleur.fournisseur_de_compositions

        def cours(configuration, hors_ligne=False):
            en_ligne.append(("cours", hors_ligne))
            return vrai_cours(configuration, hors_ligne=True)

        def compositions(configuration, hors_ligne=False):
            en_ligne.append(("compositions", hors_ligne))
            return vraies_compositions(configuration, hors_ligne=True)

        monkeypatch.setattr(assembleur, "fournisseur_de_cours", cours)
        monkeypatch.setattr(assembleur, "fournisseur_de_compositions", compositions)

        cli.main([commande, "--export", str(export_ailleurs)])

        assert en_ligne
        assert all(hors_ligne for _, hors_ligne in en_ligne)
