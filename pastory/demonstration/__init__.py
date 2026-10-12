"""Le portefeuille de démonstration : montrer Pastory sans montrer un vrai portefeuille (D-107).

Un **export des transactions fictif**, au format officiel de Trade Republic
(docs/export-officiel.md), que Pastory lit ensuite comme n'importe quel export : il cherche
seul les cours, les frais des fonds et leur composition. La démonstration montre donc la vraie
chaîne, de bout en bout.

**Ce qui est inventé, ce qui ne l'est pas :**

- les **opérations** sont inventées : personne n'a passé ces ordres ni reçu ces dividendes. Les
  montants des plans, les quantités, les dates, les dividendes, les taxes, les taux de change
  et les lignes d'espèces sont des valeurs vraisemblables, rien de plus ;
- les **titres** sont réels et publics, choisis parmi les plus courants des plans d'épargne —
  jamais d'après un portefeuille réel ;
- les **prix d'achat** sont les vraies clôtures des jours choisis (`clotures.py`). Il le faut :
  Pastory ne retient une cotation que si elle retombe sur le prix payé (D-85). Un prix inventé
  ferait refuser le bon titre, et la démonstration ne montrerait que des trous.

**Seules les formes déjà vues sur de vrais fichiers sont écrites** (export-officiel §4.1) : achat,
vente, dividende d'action, versement sur le PEA, lignes d'espèces, et une ligne Saveback, qui
montre un type « non traité, affiché ». Aucun dividende de fonds : cette forme n'a jamais été vue.

**Rien ne se mêle aux vraies données.** La démonstration a son propre dossier personnel
(`emplacements.dossier_de_demonstration`), avec son export, son cache et sa configuration.
L'export y est **écrit par le programme** : aucun fichier de données n'entre dans git.
"""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Iterator, Mapping, MutableMapping
from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path

from pastory.config import emplacements

NOM_DU_FICHIER = "Exportation de transactions (démonstration).csv"

MENTION = "Données de démonstration"
"""Ce que l'écran porte en permanence, sur la couverture et sur chaque chapitre : personne ne
doit pouvoir prendre ce portefeuille pour un vrai."""

TITRE_DE_LA_FENETRE = "Pastory · démonstration"
"""Le titre de la fenêtre. Il diffère de celui du vrai portefeuille : c'est par lui que le
lanceur retrouve la bonne fenêtre quand les deux sont ouvertes."""

COLONNES = (
    "datetime",
    "date",
    "account_type",
    "category",
    "type",
    "asset_class",
    "name",
    "symbol",
    "shares",
    "price",
    "amount",
    "fee",
    "tax",
    "currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "description",
    "transaction_id",
    "counterparty_name",
    "counterparty_iban",
    "payment_reference",
    "mcc_code",
)
"""Les colonnes de l'export, dans sa variante à virgules (export-officiel §2)."""

PEA = "PEA"
CTO = "DEFAULT"

CENTIME = Decimal("0.01")
PRECISION_D_UN_PRIX = Decimal("0.0001")
PRECISION_D_UNE_QUANTITE = Decimal("0.000001")


@dataclass(frozen=True)
class Titre:
    code: str
    """L'ISIN, ou le code d'un crypto-actif."""
    nom: str
    classe: str
    """`asset_class` de l'export : `FUND`, `STOCK` ou `CRYPTO`."""
    ticker: str
    """La cotation en euros dont viennent les clôtures de `clotures.py`. Elle ne sert qu'au
    relevé (`scripts/releve_de_demonstration.py`) : Pastory, lui, cherche la sienne."""


MONDE = Titre("LU1681043599", "Amundi MSCI World Swap UCITS ETF EUR Acc", "FUND", "CW8.PA")
EMERGENTS = Titre(
    "FR0013412020",
    "Amundi PEA Émergent (MSCI Emerging) ESG Transition UCITS ETF Acc",
    "FUND",
    "PAEEM.PA",
)
ETATS_UNIS = Titre("IE00B5BMR087", "iShares Core S&P 500 UCITS ETF USD (Acc)", "FUND", "SXR8.DE")
OBLIGATIONS = Titre(
    "LU0290355717", "Xtrackers II Eurozone Government Bond UCITS ETF 1C", "FUND", "XGLE.DE"
)
MATIERES_PREMIERES = Titre(
    "IE00BDFL4P12", "iShares Diversified Commodity Swap UCITS ETF", "FUND", "SXRS.DE"
)
LUXE = Titre("FR0000121014", "LVMH Moët Hennessy Louis Vuitton", "STOCK", "MC.PA")
LOGICIEL = Titre("US5949181045", "Microsoft", "STOCK", "MSF.DE")
BITCOIN = Titre("BTC", "Bitcoin", "CRYPTO", "BTC-EUR")

TITRES = (
    MONDE, EMERGENTS, ETATS_UNIS, OBLIGATIONS, MATIERES_PREMIERES, LUXE, LOGICIEL, BITCOIN
)  # fmt: skip


@dataclass(frozen=True)
class Plan:
    """Un plan d'épargne : le même montant chaque mois, sans frais."""

    titre: Titre
    compte: str
    montant: Decimal
    premier_mois: tuple[int, int]
    dernier_mois: tuple[int, int]
    jour_du_mois: int
    heure: str

    def executions(self) -> Iterator[Date]:
        """Les jours **voulus** : le plan s'exécute ce jour-là, ou le premier jour coté après."""
        annee, mois = self.premier_mois
        while (annee, mois) <= self.dernier_mois:
            yield Date(annee, mois, self.jour_du_mois)
            annee, mois = (annee, mois + 1) if mois < 12 else (annee + 1, 1)


@dataclass(frozen=True)
class Ordre:
    """Un ordre ponctuel : 1 € de frais. Une quantité négative est une vente."""

    titre: Titre
    compte: str
    jour: Date
    quantite: int
    taxe_pour_cent: Decimal = Decimal("0")
    """La taxe sur les transactions financières, due à l'achat d'une grande action française."""


@dataclass(frozen=True)
class Dividende:
    titre: Titre
    jour: Date
    parts: int
    par_part: Decimal
    taxe_pour_cent: Decimal
    change: Decimal | None = None
    """Le nombre d'euros pour un dollar, quand le dividende est versé en dollars."""


DERNIER_MOIS = (2026, 9)

PLANS = (
    Plan(MONDE, PEA, Decimal("150"), (2023, 1), DERNIER_MOIS, 2, "09:15:02.418Z"),
    Plan(EMERGENTS, PEA, Decimal("50"), (2024, 1), DERNIER_MOIS, 2, "09:15:03.907Z"),
    Plan(ETATS_UNIS, CTO, Decimal("100"), (2023, 6), DERNIER_MOIS, 16, "09:15:02.655Z"),
    Plan(BITCOIN, CTO, Decimal("25"), (2024, 3), DERNIER_MOIS, 16, "12:00:04.120Z"),
)

TAXE_SUR_LES_TRANSACTIONS = Decimal("0.3")

ORDRES = (
    Ordre(LUXE, CTO, Date(2023, 3, 6), 2, TAXE_SUR_LES_TRANSACTIONS),
    Ordre(OBLIGATIONS, CTO, Date(2023, 9, 11), 5),
    Ordre(LOGICIEL, CTO, Date(2023, 10, 9), 3),
    Ordre(MATIERES_PREMIERES, CTO, Date(2024, 4, 8), 150),
    Ordre(LUXE, CTO, Date(2024, 6, 10), 1, TAXE_SUR_LES_TRANSACTIONS),
    Ordre(OBLIGATIONS, CTO, Date(2024, 11, 12), 3),
    Ordre(MATIERES_PREMIERES, CTO, Date(2025, 2, 10), 100),
    Ordre(LOGICIEL, CTO, Date(2025, 4, 14), 2),
    Ordre(LUXE, CTO, Date(2025, 5, 12), -1),
)

IMPOT_FRANCAIS = Decimal("30")
IMPOT_FRANCAIS_2026 = Decimal("31.4")
RETENUE_AMERICAINE = Decimal("15")

DIVIDENDES = (
    Dividende(LUXE, Date(2023, 4, 27), 2, Decimal("7.00"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2023, 12, 6), 2, Decimal("5.50"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2024, 4, 25), 2, Decimal("7.50"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2024, 12, 4), 3, Decimal("5.50"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2025, 4, 28), 3, Decimal("7.50"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2025, 12, 4), 2, Decimal("5.50"), IMPOT_FRANCAIS),
    Dividende(LUXE, Date(2026, 4, 28), 2, Decimal("7.50"), IMPOT_FRANCAIS_2026),
    *(
        Dividende(
            LOGICIEL,
            jour,
            parts,
            Decimal(par_part),
            RETENUE_AMERICAINE + (IMPOT_FRANCAIS_2026 if jour.year >= 2026 else IMPOT_FRANCAIS),
            Decimal(change),
        )
        for jour, parts, par_part, change in (
            (Date(2023, 12, 14), 3, "0.75", "0.92"),
            (Date(2024, 3, 14), 3, "0.75", "0.915"),
            (Date(2024, 6, 13), 3, "0.75", "0.93"),
            (Date(2024, 9, 12), 3, "0.75", "0.905"),
            (Date(2024, 12, 12), 3, "0.83", "0.95"),
            (Date(2025, 3, 13), 3, "0.83", "0.92"),
            (Date(2025, 6, 12), 5, "0.83", "0.87"),
            (Date(2025, 9, 11), 5, "0.83", "0.855"),
            (Date(2025, 12, 11), 5, "0.91", "0.86"),
            (Date(2026, 3, 12), 5, "0.91", "0.87"),
            (Date(2026, 6, 11), 5, "0.91", "0.865"),
            (Date(2026, 9, 10), 5, "0.91", "0.86"),
        )
    ),
)

SAVEBACK = (Date(2026, 8, 31), Decimal("15.00"))
"""Une ligne que Pastory ne traite pas encore, et qu'il affiche (règle 5)."""

ESPECES = (
    # (jour, heure, type, montant, nom) : des lignes d'espèces, pour que l'export ressemble à
    # un vrai. Pastory ne lit que leur type : il les compte, et ne suit pas les espèces (D-11).
    (Date(2023, 1, 1), "08:00:00.000Z", "TRANSFER_INSTANT_INBOUND", "2000.00", "Camille Fictif"),
    (Date(2023, 6, 14), "08:00:00.000Z", "TRANSFER_INSTANT_INBOUND", "1500.00", "Camille Fictif"),
    (Date(2024, 1, 15), "08:00:00.000Z", "TRANSFER_INBOUND", "3000.00", "Camille Fictif"),
    (Date(2024, 5, 3), "18:45:00.000Z", "CARD_TRANSACTION", "-4.20", "Boulangerie Fictive"),
    (Date(2024, 5, 31), "22:00:00.000Z", "INTEREST_PAYMENT", "3.12", ""),
    (Date(2025, 1, 10), "08:00:00.000Z", "TRANSFER_INSTANT_INBOUND", "2500.00", "Camille Fictif"),
    (Date(2025, 7, 19), "11:30:00.000Z", "CARD_TRANSACTION", "-27.90", "Librairie Fictive"),
    (Date(2025, 7, 31), "22:00:00.000Z", "INTEREST_PAYMENT", "2.47", ""),
    (Date(2026, 2, 6), "08:00:00.000Z", "TRANSFER_INBOUND", "2000.00", "Camille Fictif"),
    (Date(2026, 6, 21), "17:10:00.000Z", "CARD_TRANSACTION", "-12.50", "Café Fictif"),
)

IBAN_FICTIF = "FR7600000000000000000000000"


class CloturesIncompletes(Exception):
    """Le relevé des clôtures ne couvre pas le scénario : il est à refaire
    (`scripts/releve_de_demonstration.py`)."""


def jours_a_relever() -> dict[Titre, list[Date]]:
    """Pour chaque titre, les jours dont il faut la clôture : ceux des plans et des ordres."""
    jours: dict[Titre, list[Date]] = {titre: [] for titre in TITRES}
    for plan in PLANS:
        jours[plan.titre].extend(plan.executions())
    for ordre in ORDRES:
        jours[ordre.titre].append(ordre.jour)
    return {titre: sorted(set(voulus)) for titre, voulus in jours.items()}


def _releve() -> Mapping[str, Mapping[str, tuple[str, str]]]:
    from pastory.demonstration.clotures import CLOTURES

    return CLOTURES


def _cloture(releve, titre: Titre, voulu: Date) -> tuple[Date, Decimal]:
    """Le jour coté retenu pour un jour voulu, et sa clôture."""
    try:
        jour, cours = releve[titre.code][voulu.isoformat()]
    except KeyError:
        raise CloturesIncompletes(
            f"aucune clôture relevée pour {titre.nom} au {voulu.isoformat()}"
        ) from None
    return Date.fromisoformat(jour), Decimal(cours).quantize(PRECISION_D_UN_PRIX)


def _ligne(numero: int, **champs: str) -> dict[str, str]:
    valeurs = dict.fromkeys(COLONNES, "")
    valeurs["currency"] = "EUR"
    # Des identifiants qui ne ressemblent à aucun vrai : la même forme, des zéros partout.
    valeurs["transaction_id"] = f"00000000-0000-4000-8000-{numero:012d}"
    valeurs.update(champs)
    return valeurs


def _achat_ou_vente(
    titre: Titre, compte: str, jour: Date, heure: str, quantite: Decimal, cours: Decimal,
    description: str, frais: Decimal = Decimal("0"), taxe: Decimal = Decimal("0"),
) -> dict[str, str]:  # fmt: skip
    brut = (abs(quantite) * cours).quantize(CENTIME, ROUND_HALF_UP)
    achat = quantite > 0
    return {
        "datetime": f"{jour.isoformat()}T{heure}",
        "date": jour.isoformat(),
        "account_type": compte,
        "category": "TRADING",
        "type": "BUY" if achat else "SELL",
        "asset_class": titre.classe,
        "name": titre.nom,
        "symbol": titre.code,
        "shares": f"{quantite:.10f}",
        "price": f"{cours:.10f}",
        "amount": f"{-brut if achat else brut:.2f}",
        "fee": f"{-frais:.2f}" if frais else "",
        "tax": f"{-taxe:.2f}" if taxe else "",
        "description": description,
    }


def lignes(releve: Mapping[str, Mapping[str, tuple[str, str]]] | None = None) -> list[dict]:
    """Toutes les lignes de l'export fictif, de la plus récente à la plus ancienne."""
    releve = _releve() if releve is None else releve
    produites: list[dict[str, str]] = []

    versements_pea: dict[Date, Decimal] = {}
    for plan in PLANS:
        for voulu in plan.executions():
            jour, cours = _cloture(releve, plan.titre, voulu)
            quantite = (plan.montant / cours).quantize(PRECISION_D_UNE_QUANTITE, ROUND_DOWN)
            produites.append(
                _achat_ou_vente(
                    plan.titre, plan.compte, jour, plan.heure, quantite, cours,
                    f"Savings plan execution {plan.titre.code}",
                )  # fmt: skip
            )
            if plan.compte == PEA:
                versements_pea[jour] = versements_pea.get(jour, Decimal("0")) + plan.montant

    # Sur le PEA, chaque achat est précédé de son versement d'espèces (export-officiel §4.1) :
    # c'est le premier d'entre eux qui date l'ouverture du plan (D-86).
    for jour, montant in versements_pea.items():
        produites.append(
            {
                "datetime": f"{jour.isoformat()}T07:00:00.000Z",
                "date": jour.isoformat(),
                "account_type": PEA,
                "category": "CASH",
                "type": "TRANSFER_IN",
                "amount": f"{montant:.2f}",
                "description": "PEA deposit",
            }
        )

    for ordre in ORDRES:
        jour, cours = _cloture(releve, ordre.titre, ordre.jour)
        brut = abs(ordre.quantite) * cours
        sens = "Buy" if ordre.quantite > 0 else "Sell"
        produites.append(
            _achat_ou_vente(
                ordre.titre, ordre.compte, jour, "14:30:07.456789Z", Decimal(ordre.quantite),
                cours,
                f"{sens} trade {ordre.titre.code} {ordre.titre.nom}, "
                f"quantity: {abs(ordre.quantite)}",
                frais=Decimal("1"),
                taxe=(brut * ordre.taxe_pour_cent / 100).quantize(CENTIME, ROUND_HALF_UP),
            )  # fmt: skip
        )

    for dividende in DIVIDENDES:
        produites.append(_dividende(dividende))

    jour, montant = SAVEBACK
    produites.append(
        {
            "datetime": f"{jour.isoformat()}T20:00:00.000Z",
            "date": jour.isoformat(),
            "account_type": CTO,
            "category": "CASH",
            "type": "BENEFITS_SAVEBACK",
            "asset_class": ETATS_UNIS.classe,
            "name": ETATS_UNIS.nom,
            "symbol": ETATS_UNIS.code,
            "amount": f"{montant:.2f}",
            "description": "Saveback",
        }
    )

    for jour, heure, type_especes, montant, nom in ESPECES:
        virement = type_especes.startswith("TRANSFER")
        produites.append(
            {
                "datetime": f"{jour.isoformat()}T{heure}",
                "date": jour.isoformat(),
                "account_type": CTO,
                "category": "CASH",
                "type": type_especes,
                "name": nom,
                "amount": montant,
                "description": {
                    "CARD_TRANSACTION": f"Card payment at {nom}",
                    "INTEREST_PAYMENT": "Interest payment",
                }.get(type_especes, f"Incoming transfer from {nom}"),
                "counterparty_name": nom if virement else "",
                "counterparty_iban": IBAN_FICTIF if virement else "",
                "mcc_code": "5999" if type_especes == "CARD_TRANSACTION" else "",
            }
        )

    produites.sort(key=lambda champs: champs["datetime"], reverse=True)
    return [_ligne(numero, **champs) for numero, champs in enumerate(produites, start=1)]


def _dividende(dividende: Dividende) -> dict[str, str]:
    """Un dividende d'action : `amount` est le brut en euros, `tax` toute la retenue
    (export-officiel §5.3). En dollars, `original_amount × fx_rate = amount`."""
    dans_sa_devise = dividende.parts * dividende.par_part
    brut = dans_sa_devise * (dividende.change or Decimal("1"))
    taxe = brut * dividende.taxe_pour_cent / 100
    champs = {
        "datetime": f"{dividende.jour.isoformat()}T06:00:00.000Z",
        "date": dividende.jour.isoformat(),
        "account_type": CTO,
        "category": "CASH",
        "type": "DIVIDEND",
        "asset_class": dividende.titre.classe,
        "name": dividende.titre.nom,
        "symbol": dividende.titre.code,
        "shares": f"{Decimal(dividende.parts):.10f}",
        "amount": f"{brut:.6f}",
        "tax": f"{-taxe:.6f}",
        "description": f"Cash Dividend for ISIN {dividende.titre.code}",
    }
    if dividende.change is not None:
        champs |= {
            "original_amount": f"{dans_sa_devise:.6f}",
            "original_currency": "USD",
            "fx_rate": f"{dividende.change:.6f}",
        }
    return champs


def texte_csv(a_ecrire: list[dict[str, str]] | None = None) -> str:
    """L'export tel que la banque l'écrit : virgules, tous les champs entre guillemets."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, quoting=csv.QUOTE_ALL, lineterminator="\n")
    ecrivain.writerow(COLONNES)
    for valeurs in lignes() if a_ecrire is None else a_ecrire:
        ecrivain.writerow([valeurs[colonne] for colonne in COLONNES])
    return tampon.getvalue()


def ecrire(dossier_des_exports: Path) -> Path:
    """Écrit l'export fictif dans le dossier de dépôt de la démonstration. Le fichier n'est
    touché que si son contenu a changé — le scénario d'une version plus récente."""
    dossier_des_exports.mkdir(parents=True, exist_ok=True)
    chemin = dossier_des_exports / NOM_DU_FICHIER
    contenu = texte_csv().encode("utf-8")
    if not chemin.is_file() or chemin.read_bytes() != contenu:
        chemin.write_bytes(contenu)
    return chemin


def detourner(environnement: MutableMapping[str, str] | None = None) -> Path:
    """Fait du dossier personnel celui de la démonstration, **sans rien écrire**. C'est ce
    détournement, et lui seul, qui fait d'un lancement une démonstration
    (`emplacements.est_une_demonstration`). Rend ce dossier."""
    environnement = os.environ if environnement is None else environnement
    racine = emplacements.dossier_de_demonstration(environnement)
    environnement[emplacements.VARIABLE_EMPLACEMENT] = str(racine)
    return racine


def preparer(environnement: MutableMapping[str, str] | None = None) -> Path:
    """Fait de ce lancement une démonstration : le dossier personnel devient celui de la
    démonstration, et l'export fictif y est écrit. À appeler avant tout le reste.

    Rend le dossier personnel de la démonstration.
    """
    environnement = os.environ if environnement is None else environnement
    racine = detourner(environnement)
    ecrire(emplacements.dossier_exports(environnement))
    return racine
