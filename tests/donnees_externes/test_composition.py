"""Le fournisseur de compositions : l'ordre des étages, et les refus lisibles (D-63, D-70).

L'ordre compte autant que le résultat : ce que l'utilisateur a déclaré l'emporte sur le cache, qui
l'emporte sur la source. C'est la porte de sortie promise par D-70, et elle ne sert à rien si la
source repasse devant.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import Configuration, Declaration, TypeActif
from pastory.donnees_externes.composition import (
    SOURCE_DECLAREE,
    Composition,
    CompositionIndisponible,
    FournisseurDeCompositions,
    Part,
    grouper_refus,
)
from pastory.donnees_externes.cours import SourceInjoignable

AUJOURD_HUI = Date(2026, 9, 27)
ETF = "XX0000000ETF"
ACTION = "XX0000000ACT"
CRYPTO = "BTC"


def composition(
    actif: str = ETF, source: str = "source de test", regle: str = "pays d'activité"
) -> Composition:
    return Composition(
        actif=actif,
        pays=(Part("US", Decimal("70")),),
        secteurs=(Part("technology", Decimal("60")),),
        classes=(Part("stock", Decimal("100")),),
        arrete_le=Date(2026, 8, 31),
        intitule_de_la_date="date annoncée par la source",
        source=source,
        recupere_le=AUJOURD_HUI,
        regle_de_pays=regle,
    )


class CacheFictif:
    def __init__(self, contenu: dict[str, Composition] | None = None) -> None:
        self.contenu = dict(contenu or {})
        self.ecritures: list[str] = []

    def lire(self, actif: str) -> Composition | None:
        return self.contenu.get(actif)

    def ecrire(self, une: Composition) -> None:
        self.contenu[une.actif] = une
        self.ecritures.append(une.actif)

    def oublier(self, actif: str | None = None) -> list[str]:
        if actif is None:
            oublies = sorted(self.contenu)
            self.contenu.clear()
            return oublies
        return [actif] if self.contenu.pop(actif, None) is not None else []


class SourceEtfFictive:
    nom = "source d'ETF de test"

    def __init__(self, table=None, erreur=None) -> None:
        self.table = table or {}
        self.erreur = erreur
        self.appels: list[str] = []

    def composition(self, actif: str) -> Composition:
        self.appels.append(actif)
        if self.erreur is not None:
            raise self.erreur
        if actif not in self.table:
            raise CompositionIndisponible(f"{actif} est inconnu de cette source")
        return self.table[actif]


class SourceActionFictive:
    nom = "source d'actions de test"

    def __init__(self) -> None:
        self.appels: list[tuple[str, str]] = []

    def composition(self, actif: str, ticker: str) -> Composition:
        self.appels.append((actif, ticker))
        return composition(actif, source=self.nom)


def config(**declarations: Declaration) -> Configuration:
    return Configuration(declarations=dict(declarations))


def etf_declare(**extra) -> Declaration:
    return Declaration(ticker="AAAA.DE", devise="EUR", type=TypeActif.ETF, **extra)


class TestLOrdreDesEtages:
    def test_la_declaration_de_l_utilisateur_l_emporte_sur_la_source(self):
        # D-70 : la porte de sortie quand la source se trompe. Elle passe **avant** tout.
        declaration = etf_declare(pays={"FR": Decimal("100")})
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=source,
            actifs=config(**{ETF: declaration}),
            aujourd_hui=AUJOURD_HUI,
        )

        trouvee = fournisseur.composition(ETF)

        assert trouvee.source == SOURCE_DECLAREE
        assert [(part.code, part.pour_cent) for part in trouvee.pays] == [("FR", Decimal("100"))]
        assert source.appels == []

    def test_le_cache_passe_avant_la_source(self):
        cache = CacheFictif({ETF: composition(source="depuis le cache")})
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=cache, source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        trouvee = fournisseur.composition(ETF)

        assert trouvee.source == "depuis le cache"
        assert source.appels == []

    def test_une_composition_gardee_sans_regle_de_pays_est_redemandee(self):
        """Le cache d'avant l'étape 9 ne gardait pas la règle de pays : une composition relue
        n'en avait plus. En ligne, elle est redemandée, et réécrite avec sa règle."""
        cache = CacheFictif({ETF: composition(source="depuis le cache", regle="")})
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=cache, source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        trouvee = fournisseur.composition(ETF)

        assert trouvee.regle_de_pays == "pays d'activité"
        assert source.appels == [ETF]
        assert cache.ecritures == [ETF]

    def test_si_la_source_ne_repond_pas_l_ancienne_est_gardee_sans_refus(self):
        cache = CacheFictif({ETF: composition(source="depuis le cache", regle="")})
        source = SourceEtfFictive({})
        fournisseur = FournisseurDeCompositions(
            cache=cache, source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        trouvee = fournisseur.composition(ETF)

        assert trouvee.source == "depuis le cache"
        assert fournisseur.refus == []

    def test_hors_ligne_elle_sert_telle_quelle(self):
        cache = CacheFictif({ETF: composition(source="depuis le cache", regle="")})
        fournisseur = FournisseurDeCompositions(
            cache=cache, actifs=config(**{ETF: etf_declare()}), hors_ligne=True
        )

        assert fournisseur.composition(ETF).source == "depuis le cache"

    def test_ce_qui_vient_de_la_source_est_mis_en_cache(self):
        cache = CacheFictif()
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=cache, source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        fournisseur.composition(ETF)

        assert cache.ecritures == [ETF]

    def test_un_actif_n_est_demande_qu_une_fois_meme_en_cas_d_echec(self):
        # Sans cela, un actif inconnu ferait un appel réseau par rubrique, puis un par jour
        # d'évolution.
        source = SourceEtfFictive({})
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        assert fournisseur.composition(ETF) is None
        assert fournisseur.composition(ETF) is None
        assert source.appels == [ETF]
        assert len(fournisseur.refus) == 1


class TestQuelleSourceEstInterrogee:
    def test_un_etf_va_a_la_source_des_fonds(self):
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        fournisseur.composition(ETF)

        assert source.appels == [ETF]

    def test_une_action_va_a_la_source_des_societes_avec_son_ticker(self):
        action = SourceActionFictive()
        declaration = Declaration(ticker="MC.PA", devise="EUR", type=TypeActif.ACTION)
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_action=action,
            actifs=config(**{ACTION: declaration}),
        )

        fournisseur.composition(ACTION)

        assert action.appels == [(ACTION, "MC.PA")]

    def test_une_crypto_recoit_un_motif_qui_rassure_au_lieu_d_alerter(self):
        # D-62 : ce message sera lu par quelqu'un qui n'a pas suivi la construction du projet.
        declaration = Declaration(ticker="BTC-EUR", devise="EUR", type=TypeActif.CRYPTO)
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), actifs=config(**{CRYPTO: declaration})
        )

        assert fournisseur.composition(CRYPTO) is None
        (refus,) = fournisseur.refus
        assert refus.categorie == "actif numérique"
        assert "n'est pas une donnée manquante" in refus.motif


class TestLesRefusSontLisibles:
    def test_un_actif_sans_reglages_est_dit_sans_type(self):
        fournisseur = FournisseurDeCompositions(cache=CacheFictif(), actifs=config())

        assert fournisseur.composition(ETF) is None
        (refus,) = fournisseur.refus
        assert refus.categorie == "type inconnu"

    def test_un_type_inconnu_dit_pourquoi_la_composition_n_est_pas_cherchee(self):
        declaration = Declaration(ticker="AAAA.DE", devise="EUR")
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), actifs=config(**{ETF: declaration})
        )

        assert fournisseur.composition(ETF) is None
        (refus,) = fournisseur.refus
        assert refus.categorie == "type inconnu"
        assert "pas au même endroit" in refus.motif
        assert "actifs.toml" not in refus.motif

    def test_une_source_injoignable_devient_un_refus_et_non_une_exception(self):
        source = SourceEtfFictive(erreur=SourceInjoignable("le service ne répond pas"))
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), source_etf=source, actifs=config(**{ETF: etf_declare()})
        )

        assert fournisseur.composition(ETF) is None
        (refus,) = fournisseur.refus
        assert refus.categorie == "source injoignable"

    def test_hors_ligne_le_cache_sert_mais_rien_n_est_demande(self):
        cache = CacheFictif({ETF: composition()})
        source = SourceEtfFictive({ETF: composition()})
        fournisseur = FournisseurDeCompositions(
            cache=cache,
            source_etf=source,
            actifs=config(**{ETF: etf_declare()}),
            hors_ligne=True,
        )

        assert fournisseur.composition(ETF) is not None
        assert source.appels == []

    def test_hors_ligne_sans_cache_le_motif_nomme_l_option(self):
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(), actifs=config(**{ETF: etf_declare()}), hors_ligne=True
        )

        assert fournisseur.composition(ETF) is None
        (refus,) = fournisseur.refus
        assert "--hors-ligne" in refus.motif

    def test_les_refus_se_regroupent_par_categorie(self):
        fournisseur = FournisseurDeCompositions(cache=CacheFictif(), actifs=config())
        fournisseur.composition("A")
        fournisseur.composition("B")

        groupes = grouper_refus(fournisseur.refus)

        assert [(categorie, len(refus)) for categorie, refus in groupes] == [
            ("type inconnu", 2)
        ]


class TestOublier:
    def test_oublier_vide_le_cache_et_la_memoire_de_l_execution(self):
        cache = CacheFictif({ETF: composition()})
        source = SourceEtfFictive({ETF: composition(source="reprise à la source")})
        fournisseur = FournisseurDeCompositions(
            cache=cache, source_etf=source, actifs=config(**{ETF: etf_declare()})
        )
        fournisseur.composition(ETF)

        oublies = fournisseur.oublier(ETF)

        assert oublies == [ETF]
        assert fournisseur.composition(ETF).source == "reprise à la source"


class TestUneCompositionDeclareeCompteDansLesClassesDActifs:
    """Sans cela, la porte de sortie de D-70 fabriquait le trou qu'elle est censée combler."""

    def test_un_actif_declare_a_la_main_pese_cent_pour_cent_en_actions(self):
        declaration = etf_declare(pays={"FR": Decimal("100")})
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            actifs=config(**{ETF: declaration}),
            aujourd_hui=AUJOURD_HUI,
        )

        trouvee = fournisseur.composition(ETF)

        assert [(part.code, part.pour_cent) for part in trouvee.classes] == [
            ("stock", Decimal("100"))
        ]


class TestLaSourceDeSecours:
    """L'étage ajouté par l'étape 8 bis (D-72, D-77).

    Deux sources n'ont ni la même nomenclature sectorielle ni la même règle de pays : basculer
    sur un secours **sans le dire** donnerait un total juste et une répartition fausse — 5
    points d'écart mesurés sur la technologie. Depuis l'étape 8 quater (D-80), le secours est
    essayé de lui-même, et c'est l'affichage de la source ligne par ligne qui protège ; une
    correction `secours = "aucun"` le refuse pour un actif.
    """

    def test_le_secours_est_essaye_de_lui_meme_pour_un_etf_non_couvert(self):
        principale = SourceEtfFictive(erreur=CompositionIndisponible("fonds à swap opaque"))
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=principale,
            actifs=config(**{ETF: etf_declare()}),
            secours={"amundi": secours},
        )
        trouvee = fournisseur.composition(ETF)

        assert trouvee.source == "secours de test"
        assert fournisseur.refus == []

    def test_un_secours_qui_ne_connait_pas_le_fonds_laisse_le_motif_de_la_principale(self):
        # Essayé de lui-même, le secours n'était pas attendu : son « aucun produit » n'apprend
        # rien, c'est le motif de la source principale qui compte.
        principale = SourceEtfFictive(erreur=CompositionIndisponible("fonds à swap opaque"))
        secours = SourceEtfFictive(erreur=CompositionIndisponible("aucun produit"))

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=principale,
            actifs=config(**{ETF: etf_declare()}),
            secours={"amundi": secours},
        )

        assert fournisseur.composition(ETF) is None
        (refus,) = fournisseur.refus
        assert refus.motif == "fonds à swap opaque"

    def test_un_secours_refuse_par_correction_n_est_pas_appele(self):
        principale = SourceEtfFictive(erreur=CompositionIndisponible("fonds à swap opaque"))
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=principale,
            actifs=config(**{ETF: etf_declare(secours="aucun")}),
            secours={"amundi": secours},
        )

        assert fournisseur.composition(ETF) is None
        assert secours.appels == []

    def test_le_secours_ne_sert_pas_une_action(self):
        # La source de secours décrit l'indice d'un fonds : elle n'a rien à dire d'une société.
        class SocieteInconnue:
            nom = "source d'actions de test"

            def composition(self, actif: str, ticker: str) -> Composition:
                raise CompositionIndisponible("société inconnue")

        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_action=SocieteInconnue(),
            actifs=config(**{ETF: Declaration(ticker="AAAA.PA", type=TypeActif.ACTION)}),
            secours={"amundi": secours},
        )

        assert fournisseur.composition(ETF) is None
        assert secours.appels == []

    def test_le_secours_est_employe_quand_l_actif_le_demande(self):
        principale = SourceEtfFictive(erreur=CompositionIndisponible("fonds à swap opaque"))
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=principale,
            actifs=config(**{ETF: etf_declare(secours="amundi")}),
            secours={"amundi": secours},
        )
        trouvee = fournisseur.composition(ETF)

        assert trouvee is not None
        assert trouvee.source == "secours de test"
        assert secours.appels == [ETF]
        assert fournisseur.refus == []

    def test_le_secours_n_est_pas_appele_quand_la_principale_repond(self):
        """Il est un recours, pas une seconde opinion : le mélange est le danger."""
        principale = SourceEtfFictive(table={ETF: composition(ETF, source="principale")})
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=principale,
            actifs=config(**{ETF: etf_declare(secours="amundi")}),
            secours={"amundi": secours},
        )

        assert fournisseur.composition(ETF).source == "principale"
        assert secours.appels == []

    def test_la_composition_de_secours_est_mise_en_cache(self):
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})
        cache = CacheFictif()

        FournisseurDeCompositions(
            cache=cache,
            source_etf=SourceEtfFictive(erreur=CompositionIndisponible("opaque")),
            actifs=config(**{ETF: etf_declare(secours="amundi")}),
            secours={"amundi": secours},
        ).composition(ETF)

        assert cache.ecritures == [ETF]

    def test_quand_les_deux_echouent_le_motif_nomme_les_deux(self):
        """Le motif du secours est celui qui est actionnable ; l'autre est rappelé."""
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=SourceEtfFictive(erreur=CompositionIndisponible("fonds à swap opaque")),
            actifs=config(**{ETF: etf_declare(secours="amundi")}),
            secours={"amundi": SourceEtfFictive(erreur=CompositionIndisponible("hors gamme"))},
        )

        assert fournisseur.composition(ETF) is None
        motif = fournisseur.refus[0].motif
        assert "hors gamme" in motif
        assert "fonds à swap opaque" in motif

    def test_un_secours_declare_mais_absent_est_dit_et_non_tu(self):
        """Hors ligne, par exemple. L'utilisateur doit savoir qu'il n'a pas été essayé."""
        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=SourceEtfFictive(erreur=CompositionIndisponible("opaque")),
            actifs=config(**{ETF: etf_declare(secours="amundi")}),
            secours={},
        )

        assert fournisseur.composition(ETF) is None
        assert "amundi" in fournisseur.refus[0].motif

    def test_la_declaration_a_la_main_passe_toujours_devant_le_secours(self):
        """D-70 reste la porte de sortie : elle l'emporte sur toute source, secours compris."""
        secours = SourceEtfFictive(table={ETF: composition(ETF, source="secours de test")})
        declaration = etf_declare(secours="amundi", pays={"FR": Decimal("100")})

        fournisseur = FournisseurDeCompositions(
            cache=CacheFictif(),
            source_etf=SourceEtfFictive(erreur=CompositionIndisponible("opaque")),
            actifs=config(**{ETF: declaration}),
            secours={"amundi": secours},
            aujourd_hui=AUJOURD_HUI,
        )
        trouvee = fournisseur.composition(ETF)

        assert trouvee is not None
        assert trouvee.source == SOURCE_DECLAREE
        assert secours.appels == []
