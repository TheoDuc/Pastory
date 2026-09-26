"""Le lecteur de réponses Yahoo, sur des réponses écrites à la main.

**Aucun test ne sort de la machine.** Ce qui est vérifié ici, c'est la lecture : les pièges que
la recherche de l'étape 4 a trouvés en interrogeant réellement le service sont reproduits sous
forme de réponses fabriquées, et chacun doit être attrapé.

Les quatre pièges, dans l'ordre où ils feraient des dégâts :

1. le cours retraité des dividendes, qui les compterait **deux fois** (D-29, D-51) ;
2. la devise qui change avec la place — des dollars pris pour des euros (D-48) ;
3. la série mensuelle qui se présente comme quotidienne ;
4. le bruit de flottant : `126.53500366210938` là où la bourse a coté 126,535.
"""

from __future__ import annotations

import json
import urllib.error
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from dashboard_tr.config.actifs import Declaration
from dashboard_tr.donnees_externes.cours import (
    DeviseInattendue,
    ReponseIncoherente,
    SourceInjoignable,
    TickerInconnu,
)
from dashboard_tr.donnees_externes.yahoo import Yahoo

ACTIF = "XX0000000001"
TICKER = "AAAA.DE"
EN_EUROS = Declaration(TICKER, "EUR")

DEBUT = Date(2026, 3, 1)
FIN = Date(2026, 3, 31)

FUSEAU_XETRA = "Europe/Berlin"


def horodatage(annee, mois, jour, heure=9, fuseau=FUSEAU_XETRA):
    """L'horodatage d'une séance, tel que la source les donne : l'heure d'ouverture locale."""
    return int(datetime(annee, mois, jour, heure, tzinfo=ZoneInfo(fuseau)).timestamp())


def reponse(
    horodatages,
    clotures,
    *,
    devise="EUR",
    place="XETRA",
    fuseau=FUSEAU_XETRA,
    ajustes=None,
):
    """Une réponse de série, dans la forme exacte que le service renvoie."""
    indicateurs = {"quote": [{"close": clotures}]}
    if ajustes is not None:
        indicateurs["adjclose"] = [{"adjclose": ajustes}]
    return json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": devise,
                            "fullExchangeName": place,
                            "exchangeTimezoneName": fuseau,
                            "gmtoffset": 3600,
                            "dataGranularity": "1d",
                        },
                        "timestamp": horodatages,
                        "indicators": indicateurs,
                    }
                ],
                "error": None,
            }
        }
    )


def source(texte):
    """Une source Yahoo qui répond toujours ce texte-là."""
    return Yahoo(ouvrir=lambda adresse: texte)


class TestSerieNormale:
    def test_les_cours_sont_lus_avec_leur_origine(self):
        texte = reponse(
            [horodatage(2026, 3, 4), horodatage(2026, 3, 5), horodatage(2026, 3, 6)],
            [126.53500366210938, 126.68000030517578, 127.12999725341797],
        )

        serie = source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert [un_cours.date for un_cours in serie] == [
            Date(2026, 3, 4),
            Date(2026, 3, 5),
            Date(2026, 3, 6),
        ]
        premier = serie[0]
        assert premier.actif == ACTIF
        assert premier.devise == "EUR"
        assert premier.place == "XETRA"
        assert premier.ticker == TICKER
        assert premier.source == "Yahoo Finance"

    def test_le_bruit_de_flottant_est_retire(self):
        # La réponse contient 126.53500366210938 ; la bourse a coté 126,535. Écrire le bruit
        # rendrait le cache invérifiable — c'est ce chiffre que le propriétaire compare avec
        # son application.
        texte = reponse([horodatage(2026, 3, 4)], [126.53500366210938])

        assert source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)[0].valeur == Decimal("126.535")

    def test_un_cours_deja_propre_n_est_pas_touche(self):
        texte = reponse([horodatage(2026, 3, 4)], [128.885])

        assert source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)[0].valeur == Decimal("128.885")

    def test_aucun_cours_n_est_un_flottant(self):
        # D-33 : un montant est un Decimal, sans exception. La réponse est lue avec
        # parse_float=Decimal, donc aucun cours ne passe jamais par un flottant.
        texte = reponse([horodatage(2026, 3, 4)], [126.535])

        valeur = source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)[0].valeur
        assert isinstance(valeur, Decimal)

    def test_le_cours_ajuste_est_ignore(self):
        # Le piège principal : `adjclose` réinjecte les dividendes, que le moteur compte déjà
        # (D-29). Le lire ferait compter deux fois chaque dividende de chaque actif.
        texte = reponse(
            [horodatage(2026, 3, 4)],
            [53.38],
            ajustes=[50.54],
        )

        assert source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)[0].valeur == Decimal("53.38")

    def test_un_trou_est_saute_sans_etre_invente(self):
        texte = reponse(
            [horodatage(2026, 3, 4), horodatage(2026, 3, 5), horodatage(2026, 3, 6)],
            [100.0, None, 102.0],
        )

        serie = source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert [un_cours.date for un_cours in serie] == [Date(2026, 3, 4), Date(2026, 3, 6)]

    def test_le_jour_retenu_est_celui_de_la_place(self):
        # Une séance ouverte à 00h30 heure de Berlin serait la veille en temps universel :
        # lire les horodatages en UTC décalerait le jour de bourse.
        texte = reponse([horodatage(2026, 3, 5, heure=0)], [100.0])

        assert source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)[0].date == Date(2026, 3, 5)

    def test_les_jours_hors_de_la_periode_demandee_sont_ecartes(self):
        # La fenêtre envoyée au service est volontairement plus large d'un jour : ce qui
        # dépasse ne doit pas ressortir.
        texte = reponse(
            [horodatage(2026, 2, 27), horodatage(2026, 3, 2)],
            [99.0, 100.0],
        )

        serie = source(texte).serie(ACTIF, EN_EUROS, Date(2026, 3, 1), Date(2026, 3, 31))

        assert [un_cours.date for un_cours in serie] == [Date(2026, 3, 2)]

    def test_une_periode_sans_cotation_donne_une_liste_vide(self):
        texte = reponse([], [])

        assert source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN) == []


class TestGardeFous:
    def test_une_cotation_dans_une_autre_monnaie_est_refusee(self):
        # Le cas vérifié : l'ETF répond en euros à Xetra, en dollars à Londres. Rien n'est
        # converti (D-48), et le message dit quoi corriger.
        texte = reponse([horodatage(2026, 3, 4)], [146.91], devise="USD", place="LSE")

        with pytest.raises(DeviseInattendue) as erreur:
            source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert "USD" in str(erreur.value)
        assert "EUR" in str(erreur.value)
        assert "actifs.toml" in str(erreur.value)

    def test_une_devise_absente_est_refusee(self):
        texte = reponse([horodatage(2026, 3, 4)], [100.0], devise="")

        with pytest.raises(ReponseIncoherente, match="monnaie"):
            source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)

    def test_une_serie_mensuelle_est_refusee(self):
        # Le piège qui ne dit pas son nom : le champ de granularité annonce « 1d » alors que
        # les points sont mensuels. Valoriser là-dessus donnerait des chiffres plausibles.
        texte = reponse(
            [
                horodatage(2026, 1, 30),
                horodatage(2026, 2, 27),
                horodatage(2026, 3, 31),
            ],
            [100.0, 101.0, 102.0],
        )

        with pytest.raises(ReponseIncoherente) as erreur:
            source(texte).serie(ACTIF, EN_EUROS, Date(2026, 1, 1), Date(2026, 4, 1))

        assert "quotidien" in str(erreur.value)

    def test_un_week_end_ne_passe_pas_pour_du_mensuel(self):
        # Trois jours d'écart, c'est un week-end : la série reste quotidienne.
        texte = reponse(
            [horodatage(2026, 3, 6), horodatage(2026, 3, 9), horodatage(2026, 3, 10)],
            [100.0, 101.0, 102.0],
        )

        assert len(source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)) == 3

    def test_un_ticker_inconnu_dit_ou_le_corriger(self):
        texte = json.dumps(
            {
                "chart": {
                    "result": None,
                    "error": {
                        "code": "Not Found",
                        "description": "No data found, symbol may be delisted",
                    },
                }
            }
        )

        with pytest.raises(TickerInconnu, match="actifs.toml"):
            source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)

    def test_une_reponse_qui_n_est_pas_du_json_evoque_l_antivirus(self):
        # Vécu sur cette machine : un antivirus qui inspecte le trafic peut remplacer une
        # réponse par une page à lui. Le message doit mettre sur la piste.
        with pytest.raises(SourceInjoignable) as erreur:
            source("<html>Accès bloqué</html>").serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert "antivirus" in str(erreur.value)

    def test_une_reponse_sans_resultat_est_refusee(self):
        texte = json.dumps({"chart": {"result": [], "error": None}})

        with pytest.raises(SourceInjoignable):
            source(texte).serie(ACTIF, EN_EUROS, DEBUT, FIN)


class TestAdresseDemandee:
    def test_la_periode_est_bornee_par_des_dates_explicites(self):
        # Jamais de plage nommée : `range=max` renvoie du mensuel.
        adresses = []

        def ouvrir(adresse):
            adresses.append(adresse)
            return reponse([horodatage(2026, 3, 4)], [100.0])

        Yahoo(ouvrir=ouvrir).serie(ACTIF, EN_EUROS, DEBUT, FIN)

        adresse = adresses[0]
        assert "period1=" in adresse and "period2=" in adresse
        assert "interval=1d" in adresse
        assert "range=" not in adresse
        assert TICKER in adresse

    def test_un_ticker_est_echappe_dans_l_adresse(self):
        adresses = []

        def ouvrir(adresse):
            adresses.append(adresse)
            return reponse([], [])

        Yahoo(ouvrir=ouvrir).serie(ACTIF, Declaration("A B&C", "EUR"), DEBUT, FIN)

        assert "A%20B%26C" in adresses[0]


class TestErreursReseau:
    def _yahoo_qui_leve(self, monkeypatch, erreur):
        def urlopen(requete, timeout=None):
            raise erreur

        monkeypatch.setattr("urllib.request.urlopen", urlopen)
        return Yahoo()

    def test_une_limitation_de_debit_invite_a_reessayer(self, monkeypatch):
        erreur = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        yahoo = self._yahoo_qui_leve(monkeypatch, erreur)

        with pytest.raises(SourceInjoignable) as leve:
            yahoo.serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert "réessayez" in str(leve.value)
        assert "déjà enregistrés" in str(leve.value)

    def test_un_ticker_absent_du_service_est_reconnu(self, monkeypatch):
        erreur = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        yahoo = self._yahoo_qui_leve(monkeypatch, erreur)

        with pytest.raises(TickerInconnu):
            yahoo.serie(ACTIF, EN_EUROS, DEBUT, FIN)

    def test_un_reseau_injoignable_evoque_le_pare_feu(self, monkeypatch):
        yahoo = self._yahoo_qui_leve(monkeypatch, urllib.error.URLError("nom introuvable"))

        with pytest.raises(SourceInjoignable) as leve:
            yahoo.serie(ACTIF, EN_EUROS, DEBUT, FIN)

        assert "antivirus" in str(leve.value) or "pare-feu" in str(leve.value)

    def test_un_delai_depasse_le_dit(self, monkeypatch):
        yahoo = self._yahoo_qui_leve(monkeypatch, TimeoutError())

        with pytest.raises(SourceInjoignable, match="secondes"):
            yahoo.serie(ACTIF, EN_EUROS, DEBUT, FIN)


class TestRecherche:
    def _yahoo(self, resultats):
        """Une source qui répond selon l'adresse appelée : recherche, puis série."""

        def ouvrir(adresse):
            return resultats["recherche"] if "search" in adresse else resultats["serie"]

        return Yahoo(ouvrir=ouvrir)

    def test_une_proposition_porte_la_devise_venue_de_la_serie(self):
        # La recherche ne dit pas la devise : c'est le second appel qui la donne, et c'est lui
        # qui rend le piège visible dans le fichier de correspondance.
        recherche = json.dumps(
            {
                "quotes": [
                    {
                        "symbol": "AAAA.DE",
                        "exchange": "GER",
                        "exchDisp": "XETRA",
                        "longname": "ETF Exemple",
                    }
                ]
            }
        )
        yahoo = self._yahoo(
            {"recherche": recherche, "serie": reponse([horodatage(2026, 3, 4)], [100.0])}
        )

        proposition = yahoo.chercher(ACTIF)

        assert proposition.ticker == "AAAA.DE"
        assert proposition.devise == "EUR"
        assert proposition.place == "XETRA"
        assert proposition.nom == "ETF Exemple"
        assert proposition.douteuse is False

    def test_une_proposition_en_dollars_est_marquee_douteuse(self):
        recherche = json.dumps(
            {"quotes": [{"symbol": "BBBB.L", "exchDisp": "London", "shortname": "ETF"}]}
        )
        yahoo = self._yahoo(
            {
                "recherche": recherche,
                "serie": reponse([horodatage(2026, 3, 4)], [146.91], devise="USD", place="LSE"),
            }
        )

        proposition = yahoo.chercher(ACTIF)

        assert proposition.devise == "USD"
        assert proposition.douteuse is True

    def test_aucun_resultat_ne_donne_aucune_proposition(self):
        yahoo = self._yahoo({"recherche": json.dumps({"quotes": []}), "serie": "{}"})

        assert yahoo.chercher(ACTIF) is None

    def test_une_recherche_en_panne_ne_propose_rien(self):
        yahoo = Yahoo(ouvrir=lambda adresse: "<html>rien</html>")

        assert yahoo.chercher(ACTIF) is None
