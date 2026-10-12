"""L'assemblage : pour chaque réglage, la correction, sinon la valeur trouvée, sinon le trou.

C'est ici, et seulement ici, que se décide ce qui s'applique. Trois sources se rencontrent :

- **ce que dit la banque** (`CeQueDitLaBanque`) : le type de chaque actif (D-82), la date
  d'ouverture proposée pour le PEA ;
- **ce que les sources extérieures ont trouvé** (`EnLigne`) : la cotation, les frais courants,
  le contenu — déjà contrôlés par `pastory/reglages/recherche` ;
- **les corrections de l'utilisateur** (`actifs.toml`, `fiscalite.toml`), qui l'emportent.

Le résultat, `Reglages`, sert deux fois : il rend la `Configuration` effective que les cours, les
coûts et les compositions lisent, et il garde l'origine de chaque valeur pour qu'elle soit
montrée là où elle sert (D-80, règle 1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal

from pastory.config.actifs import (
    Configuration,
    ContenuActif,
    Declaration,
    TypeActif,
)
from pastory.config.fiscalite import ConfigurationFiscale
from pastory.moteur.fiscalite import anniversaire
from pastory.pivot.operation import Poche
from pastory.reglages import (
    SOURCE_CORRECTION_ACTIFS,
    SOURCE_CORRECTION_FISCALITE,
    CeQueDitLaBanque,
    Cotation,
    MouvementPea,
    Origine,
    Reglage,
    Sens,
    Trou,
    Trouvee,
)

TROU_HORS_LIGNE = Trou(
    "aucune recherche n'a été faite : l'application a été lancée sans accès au réseau, et rien "
    "n'avait été trouvé auparavant pour cet actif."
)

TROU_TER_SANS_SOURCE = Trou(
    "aucune source consultée ne publie les frais courants de ce fonds. Ses frais courants "
    "estimés ne sont pas comptés ; tout le reste l'est."
)

RESERVE_PEA = (
    "c'est le premier versement du plan en cours que montrent vos exports. Si votre PEA a été "
    "ouvert dans une autre banque puis transféré, ou si vos exports ne remontent pas à son "
    "ouverture, la vraie date est plus ancienne, et l'impôt estimé est alors trop élevé."
)


@dataclass(frozen=True)
class EnLigne:
    """Ce que les sources extérieures ont trouvé pour un actif, contrôle compris.

    `None` veut dire « sans objet » : un TER pour un actif qui n'est pas un ETF, un contenu que
    rien n'annonce (la source de composition décidera alors, comme avant).
    """

    cotation: Trouvee[Cotation] | Trou = TROU_HORS_LIGNE
    ter: Trouvee[Decimal] | Trou | None = None
    contenu: Trouvee[ContenuActif] | Trou | None = None


@dataclass(frozen=True)
class ReglagesDUnActif:
    """Tout ce qui a été retenu pour un actif, et d'où ça vient."""

    actif: str
    poches: frozenset[Poche]
    cotation: Reglage[Cotation]
    type: Reglage[TypeActif]
    ter: Reglage[Decimal] | None
    """`None` : sans objet, l'actif n'est pas un ETF (seul un ETF prélève des frais courants)."""

    contenu: Reglage[ContenuActif] | None
    """`None` : rien ne l'annonce, et la source de composition décidera (D-71)."""

    nom: str | None = None
    correction: Declaration | None = None
    """La ligne d'`actifs.toml`, pour ce qui ne se trouve jamais seul (spread propre, pays et
    secteurs saisis, refus du secours)."""

    def declaration(self) -> Declaration:
        """La déclaration effective, que les cours, les coûts et les compositions lisent."""
        correction = self.correction or Declaration()
        cotation = self.cotation.valeur
        contenu, source_du_contenu, date_du_contenu = None, None, None
        if self.contenu is not None and isinstance(self.contenu.retenu, Trouvee):
            retenu = self.contenu.retenu
            # Un contenu « actions » trouvé ne s'applique pas : il ferait passer le fonds avant
            # sa composition, et lui ferait perdre ses pays et ses secteurs. Corrigé à la main, il
            # s'applique comme avant (D-71).
            if retenu.origine.corrigee or retenu.valeur is not ContenuActif.ACTIONS:
                contenu = retenu.valeur
            if not retenu.origine.corrigee:
                source_du_contenu, date_du_contenu = retenu.origine.source, retenu.origine.date
        return Declaration(
            ticker=cotation.ticker if cotation is not None else None,
            devise=cotation.devise if cotation is not None else Declaration().devise,
            type=self.type.valeur,
            ter_pour_cent=self.ter.valeur if self.ter is not None else None,
            spread_pour_cent=correction.spread_pour_cent,
            contenu=contenu,
            source_du_contenu=source_du_contenu,
            date_du_contenu=date_du_contenu,
            pays=correction.pays,
            secteurs=correction.secteurs,
            secours=correction.secours,
        )

    def reglages(self) -> list[tuple[str, Reglage]]:
        """Les réglages de l'actif, nommés, dans l'ordre où ils s'affichent."""
        liste: list[tuple[str, Reglage]] = [("cotation", self.cotation), ("type", self.type)]
        if self.ter is not None:
            liste.append(("frais courants", self.ter))
        if self.contenu is not None:
            liste.append(("contenu", self.contenu))
        return liste


@dataclass(frozen=True)
class Reglages:
    """Les réglages de tout le portefeuille."""

    actifs: Mapping[str, ReglagesDUnActif] = field(default_factory=dict)
    premier_versement_pea: Reglage[Date] | None = None
    """`None` : sans objet, aucun actif n'est détenu sur un PEA."""

    orphelines: tuple[str, ...] = ()
    """Les actifs corrigés dans `actifs.toml` qu'aucun export ne contient."""

    corrections_ecartees: tuple[str, ...] = ()
    """Les corrections fiscales écrites mais **non appliquées** à ce portefeuille, chacune
    avec sa raison (D-109) : une date de PEA sans nom alors qu'il y a plusieurs
    portefeuilles, ou écrite pour un portefeuille qui n'existe plus."""

    retraits_pea: tuple[Date, ...] = ()
    """Les sorties d'espèces du PEA depuis son ouverture : chacune contredit l'hypothèse
    « aucun retrait passé » sur laquelle repose l'impôt estimé du PEA (D-59, D-87)."""

    def configuration(self) -> Configuration:
        """La configuration effective. Les corrections orphelines n'y entrent pas : elles ne
        désignent aucun actif détenu, et sont signalées à part."""
        return Configuration(
            declarations={
                actif: reglages.declaration() for actif, reglages in self.actifs.items()
            },
            sans_cotation={
                actif: reglages.cotation.trou.motif
                for actif, reglages in self.actifs.items()
                if reglages.cotation.trou is not None
            },
        )

    @property
    def date_pea(self) -> Date | None:
        return self.premier_versement_pea.valeur if self.premier_versement_pea else None

    def trous(self) -> list[tuple[str, str, Trou]]:
        """`(actif, réglage, trou)` pour tout ce qui n'a pas été trouvé : le critère de
        l'étape (D-80). La date du PEA y figure sous l'actif « PEA »."""
        trous = [
            (actif, nom, reglage.trou)
            for actif, reglages in sorted(self.actifs.items())
            for nom, reglage in reglages.reglages()
            if reglage.trou is not None
        ]
        if self.premier_versement_pea is not None and self.premier_versement_pea.trou:
            trous.append(("PEA", "date d'ouverture", self.premier_versement_pea.trou))
        return trous


def assembler(
    banque: CeQueDitLaBanque,
    en_ligne: Mapping[str, EnLigne],
    corrections: Configuration,
    fiscalite: ConfigurationFiscale | None = None,
    duree_avant_retrait_libre: int = 5,
    corrections_ecartees: tuple[str, ...] = (),
) -> Reglages:
    """Le réglage retenu pour chaque actif de l'export, et pour la date d'ouverture du PEA.

    `duree_avant_retrait_libre` : en années, la durée avant laquelle un retrait clôt le PEA.
    `cli.py` la passe depuis `parametres/fiscalite.toml`, où elle est datée et sourcée (D-58).
    """
    actifs = {
        actif: _un_actif(actif, banque, en_ligne.get(actif, EnLigne()), corrections)
        for actif in sorted(banque.poches)
    }
    date_pea: Reglage[Date] | None = None
    retraits: tuple[Date, ...] = ()
    if any(Poche.PEA in poches for poches in banque.poches.values()):
        date_pea, retraits = _date_pea(
            banque, fiscalite or ConfigurationFiscale(), duree_avant_retrait_libre
        )
    return Reglages(
        actifs=actifs,
        premier_versement_pea=date_pea,
        orphelines=tuple(sorted(corrections.actifs_declares - set(banque.poches))),
        retraits_pea=retraits,
        corrections_ecartees=corrections_ecartees,
    )


def _un_actif(
    actif: str, banque: CeQueDitLaBanque, en_ligne: EnLigne, corrections: Configuration
) -> ReglagesDUnActif:
    correction = corrections.declaration(actif)
    corrige = correction or Declaration()

    cotation = _fusionner(
        Cotation(corrige.ticker, corrige.devise) if corrige.ticker else None,
        en_ligne.cotation,
        egal=lambda a, b: (a.ticker, a.devise) == (b.ticker, b.devise),
    )
    type_actif = _fusionner(corrige.type, _type_selon_la_banque(actif, banque))

    ter: Reglage[Decimal] | None = None
    if type_actif.valeur is TypeActif.ETF:
        # Seul un ETF prélève des frais courants : pour tout autre actif, le TER est sans objet,
        # même écrit dans le fichier (c'était déjà la règle, D-17).
        ter = _fusionner(corrige.ter_pour_cent, en_ligne.ter or TROU_TER_SANS_SOURCE)

    contenu: Reglage[ContenuActif] | None = None
    if corrige.contenu is not None or en_ligne.contenu is not None:
        contenu = _fusionner(
            corrige.contenu, en_ligne.contenu or Trou("aucune source ne l'annonce.")
        )

    return ReglagesDUnActif(
        actif=actif,
        poches=banque.poches.get(actif, frozenset()),
        cotation=cotation,
        type=type_actif,
        ter=ter,
        contenu=contenu,
        nom=banque.noms.get(actif),
        correction=correction,
    )


def _type_selon_la_banque(actif: str, banque: CeQueDitLaBanque) -> Trouvee[TypeActif] | Trou:
    """Le type que donne la banque (D-82), s'il est unique."""
    types = banque.types.get(actif, frozenset())
    if len(types) == 1:
        (seul,) = types
        return Trouvee(
            seul,
            Origine(
                source=f"{banque.source} (colonne asset_class)",
                date=banque.date,
                controle="la banque donne le même type sur toutes les opérations de l'actif",
            ),
        )
    if not types:
        return Trou("la banque ne donne pas le type de cet actif.")
    noms = ", ".join(sorted(un_type.value for un_type in types))
    return Trou(
        f"la banque donne plusieurs types pour cet actif ({noms}) : aucun n'est retenu. Sans "
        "type, son spread estimé n'est pas compté, et sa composition n'est pas cherchée."
    )


@dataclass(frozen=True)
class HistoireDuPea:
    """Ce que les mouvements d'espèces du PEA disent du plan en cours (D-86)."""

    ouverture: Date | None
    """Le premier crédit du plan en cours, ou `None` s'il n'y en a pas."""

    clotures: tuple[Date, ...] = ()
    """Les sorties d'espèces avant cinq ans : chacune a clos le plan d'alors."""

    retraits: tuple[Date, ...] = ()
    """Les sorties d'espèces après cinq ans : le plan continue, mais l'hypothèse « aucun
    retrait passé » de D-59 est fausse."""


def lire_l_histoire_du_pea(
    mouvements: tuple[MouvementPea, ...], duree_avant_retrait_libre: int
) -> HistoireDuPea:
    """Le plan commence au premier crédit d'espèces ; un retrait avant `duree_avant_retrait_libre`
    ans le clôt, et le crédit suivant en ouvre un nouveau (CMF art. L. 221-32).

    C'est le cas vu chez le propriétaire, le 2026-10-05 : une prime d'ouverture, une sortie
    d'espèces six jours plus tard (le plan fermé), une seconde prime le même jour (le plan
    rouvert), puis les versements. La date retenue est celle de la réouverture, et c'est celle
    que le propriétaire a confirmée. Rien n'est lu des montants (D-11).
    """
    ouverture: Date | None = None
    clotures: list[Date] = []
    retraits: list[Date] = []
    for mouvement in mouvements:
        if mouvement.sens is Sens.ENTREE:
            if ouverture is None:
                ouverture = mouvement.jour
        elif ouverture is not None:
            if mouvement.jour < anniversaire(ouverture, duree_avant_retrait_libre):
                clotures.append(mouvement.jour)
                ouverture = None
            else:
                retraits.append(mouvement.jour)
    return HistoireDuPea(ouverture, tuple(clotures), tuple(retraits))


def _date_pea(
    banque: CeQueDitLaBanque, fiscalite: ConfigurationFiscale, duree_avant_retrait_libre: int
) -> tuple[Reglage[Date], tuple[Date, ...]]:
    """La date d'ouverture du PEA, contrôlée, et les retraits qui la suivent (D-59, D-86)."""
    histoire = lire_l_histoire_du_pea(banque.mouvements_pea, duree_avant_retrait_libre)
    derniere_cloture = histoire.clotures[-1] if histoire.clotures else None
    trouvee: Trouvee[Date] | Trou
    if histoire.ouverture is None:
        trouvee = Trou(
            "aucun versement sur le PEA en cours dans vos exports : son ancienneté, qui décide "
            "de l'impôt, n'est pas connue. L'impôt estimé du PEA n'est pas calculé."
        )
    else:
        # Un titre entré sur le PEA avant l'ouverture retenue, et après la dernière clôture,
        # n'a pu entrer que dans un plan que l'export ne montre pas.
        orphelins = [
            jour
            for jour in banque.jours_operations_pea
            if jour < histoire.ouverture
            and (derniere_cloture is None or jour > derniere_cloture)
        ]
        if orphelins:
            trouvee = Trou(
                f"des titres sont entrés sur le PEA le {orphelins[0].isoformat()}, avant le "
                f"premier versement que montrent vos exports ({histoire.ouverture.isoformat()}) : "
                "le plan est plus ancien que vos exports, et sa date d'ouverture n'est pas "
                "connue. L'impôt estimé du PEA n'est pas calculé."
            )
        else:
            controle = "aucun titre n'est entré sur le PEA avant ce premier crédit"
            if histoire.clotures:
                controle += (
                    "; un plan précédent a été clos par un retrait le "
                    + ", le ".join(jour.isoformat() for jour in histoire.clotures)
                    + " (un retrait avant cinq ans clôt le plan)"
                )
            trouvee = Trouvee(
                histoire.ouverture,
                Origine(
                    source=f"{banque.source} (premier versement sur le PEA en cours)",
                    date=banque.date,
                    controle=controle,
                    reserve=RESERVE_PEA,
                ),
            )
    reglage = _fusionner(
        fiscalite.premier_versement_pea, trouvee, source=SOURCE_CORRECTION_FISCALITE
    )
    retenue = reglage.valeur
    if retenue is None:
        return reglage, ()
    if not reglage.retenu.origine.corrigee:
        # La sortie qui a clos un plan précédent, le jour même d'une réouverture, n'est pas un
        # retrait du plan en cours : l'histoire lue l'a déjà rangée parmi les clôtures.
        return reglage, histoire.retraits
    return reglage, tuple(
        mouvement.jour
        for mouvement in banque.mouvements_pea
        if mouvement.sens is Sens.SORTIE and mouvement.jour > retenue
    )


def _fusionner[T](
    corrige: T | None,
    trouve: Trouvee[T] | Trou,
    egal: Callable[[T, T], bool] = lambda a, b: a == b,
    source: str = SOURCE_CORRECTION_ACTIFS,
) -> Reglage[T]:
    """La correction l'emporte ; la valeur trouvée qu'elle remplace est gardée si elle diffère."""
    if corrige is None:
        return Reglage(trouve)
    ecarte = (
        trouve if isinstance(trouve, Trouvee) and not egal(trouve.valeur, corrige) else None
    )
    return Reglage(Trouvee(corrige, Origine(source=source, corrigee=True)), ecarte)
