"""Dans quelle poche une opération a-t-elle eu lieu ? (D-10, D-16, D-40)

Aucune information de l'export ne donne directement la poche. Elle se reconstitue par trois
règles, dans cet ordre, la première qui répond l'emporte :

1. **l'utilisateur l'a déclarée** pour cet actif dans sa configuration : c'est un fait,
   pas une déduction ;
2. **le code de l'actif commence par `XF`** : c'est de la crypto (D-16). Déduction ;
3. **le compte espèces de l'opération a un rôle** : compte du PEA → PEA, compte courant →
   CTO (D-10). Déduction.

Si aucune ne répond, **la poche n'est pas inventée** : l'opération est signalée et l'export
s'arrête en disant quoi déclarer (D-40). Un classement par défaut mettrait des chiffres faux
dans la bonne colonne, ce qui est pire que pas de chiffre du tout.

Le libellé « Portfolio » (« PEA » ou « Brokerage ») n'est jamais une source : il ne figure
que sur les ordres ponctuels, et c'est un texte (D-09). Il sert de **contrôle** : un
désaccord avec le compte part au rapport.
"""

from __future__ import annotations

from dataclasses import dataclass

from dashboard_tr.adaptateurs.trade_republic import lexique
from dashboard_tr.adaptateurs.trade_republic.rapport import sur
from dashboard_tr.config.comptes import Configuration, RoleCompte
from dashboard_tr.pivot.operation import Poche, Provenance

PREFIXE_CRYPTO = "XF"
"""Un actif dont le code commence ainsi est rangé en crypto (D-16).

Règle **déduite d'un seul code** : les deux exports disponibles ne contiennent qu'un actif
crypto. Elle est donc signalée comme déduction et l'utilisateur peut la corriger, actif par
actif, dans la section `[poches]` de sa configuration (Q-12)."""

POCHE_PAR_ROLE: dict[RoleCompte, Poche] = {
    RoleCompte.COURANT: Poche.CTO,
    RoleCompte.PEA: Poche.PEA,
}


@dataclass(frozen=True)
class Resolution:
    """Le résultat : une poche, ou l'explication de ce qu'il manque pour la trouver."""

    poche: Poche | None = None
    provenance: Provenance | None = None
    motif: str | None = None
    """Ce que l'utilisateur doit déclarer, quand la poche n'a pas pu être établie."""
    desaccord: str | None = None
    """Un contrôle en désaccord avec la poche retenue. L'opération est produite quand même,
    et le désaccord part au rapport : c'est à l'utilisateur de trancher."""

    @property
    def trouvee(self) -> bool:
        return self.poche is not None


def est_crypto(actif: str) -> bool:
    return actif.upper().startswith(PREFIXE_CRYPTO)


def resoudre(
    actif: str,
    compte: str | None,
    configuration: Configuration,
    poche_affichee: str | None = None,
) -> Resolution:
    """Applique les trois règles, puis le contrôle du libellé « Portfolio ».

    `poche_affichee` est le texte de la ligne « Portfolio » quand il y en a une.
    """
    declaree = configuration.poches_corrigees.get(actif)
    if declaree is not None:
        return Resolution(declaree, Provenance.DONNEE)

    if est_crypto(actif):
        return _avec_controle(Poche.CRYPTO, Provenance.DEDUCTION, poche_affichee)

    role = configuration.role(compte)
    if role is not None:
        return _avec_controle(POCHE_PAR_ROLE[role], Provenance.DEDUCTION, poche_affichee)

    if compte is None:
        return Resolution(
            motif=(
                f"aucun compte n'est rattaché à cette opération, et l'actif {actif} n'a pas de "
                "poche déclarée : ajoutez-le dans la section [poches] de votre configuration"
            )
        )

    return Resolution(
        motif=(
            "le compte espèces de cette opération n'a pas encore de rôle : "
            "lancez « dashboard comptes » pour le nommer"
        )
    )


def _avec_controle(
    poche: Poche, provenance: Provenance, poche_affichee: str | None
) -> Resolution:
    """Compare la poche retenue au libellé affiché, sans jamais lui laisser le dernier mot."""
    if poche_affichee is None:
        return Resolution(poche, provenance)

    attendue = lexique.POCHES_AFFICHEES.get(poche_affichee.strip())
    if attendue is None:
        return Resolution(
            poche,
            provenance,
            desaccord=(
                # Le libellé est inconnu : justement le cas où l'on ne peut pas savoir ce
                # qu'il contient. Il passe donc par le garde-fou avant d'entrer au rapport.
                f"le libellé de poche {sur(poche_affichee)} n'est pas connu du "
                f"lexique ; la poche {poche.value} a été retenue à partir du compte"
            ),
        )

    if attendue != poche.value:
        return Resolution(
            poche,
            provenance,
            desaccord=(
                f"le compte indique la poche {poche.value}, mais l'écran affiche "
                f"« {poche_affichee} » ({attendue})"
            ),
        )

    return Resolution(poche, provenance)
