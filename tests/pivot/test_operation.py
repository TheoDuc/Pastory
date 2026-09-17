"""Ce qu'une ligne pivot garantit (docs/format-pivot.md §1 et §2)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from dashboard_tr.pivot.operation import Provenance, jour_a_paris
from tests.pivot import exemples


class TestJourAParis:
    """Le jour d'une opération se lit en heure de Paris, pas en UTC (D-36)."""

    def test_une_operation_du_soir_reste_le_jour_meme(self):
        # 23 h 30 à Paris en hiver, c'est 22 h 30 UTC : c'est encore le 2 janvier.
        instant = datetime(2026, 1, 2, 22, 30, tzinfo=UTC)
        assert jour_a_paris(instant) == date(2026, 1, 2)

    def test_une_operation_de_fin_de_soiree_bascule_au_lendemain(self):
        # 23 h 30 UTC, c'est déjà 00 h 30 à Paris : l'opération appartient au 3 janvier.
        instant = datetime(2026, 1, 2, 23, 30, tzinfo=UTC)
        assert jour_a_paris(instant) == date(2026, 1, 3)

    def test_heure_d_ete(self):
        # En été, Paris a deux heures d'avance : 22 h 30 UTC, c'est le lendemain.
        instant = datetime(2026, 7, 1, 22, 30, tzinfo=UTC)
        assert jour_a_paris(instant) == date(2026, 7, 2)

    def test_un_horodatage_sans_fuseau_est_refuse(self):
        # Sinon le jour dépendrait du fuseau de la machine : deux ordinateurs ne
        # donneraient pas les mêmes chiffres à partir du même export.
        with pytest.raises(ValueError, match="fuseau"):
            jour_a_paris(datetime(2026, 6, 15, 23, 30))


class TestOperation:
    def test_une_operation_ne_se_modifie_pas_apres_coup(self):
        operation = exemples.achat_plan_epargne()
        with pytest.raises(dataclasses.FrozenInstanceError):
            operation.quantite = Decimal("99")  # type: ignore[misc]

    def test_la_provenance_ne_se_modifie_pas_non_plus(self):
        operation = exemples.achat_plan_epargne()
        with pytest.raises(TypeError):
            operation.provenance["quantite"] = Provenance.DONNEE  # type: ignore[index]

    def test_une_operation_ordinaire_est_complete(self):
        assert exemples.achat_ordre_ponctuel_pea().complete is True

    def test_un_prix_a_completer_rend_l_operation_incomplete(self):
        operation = exemples.titres_recus_prix_a_completer()
        assert operation.complete is False
        assert operation.est_a_completer("prix_unitaire") is True
        assert operation.est_a_completer("quantite") is False

    def test_la_devise_est_l_euro_par_defaut(self):
        assert exemples.achat_plan_epargne().devise == "EUR"

    def test_une_operation_peut_entrer_dans_un_ensemble(self):
        # Le moteur aura besoin de dédoublonner et de comparer des opérations.
        operations = {exemples.achat_plan_epargne(), exemples.achat_plan_epargne()}
        assert len(operations) == 1
