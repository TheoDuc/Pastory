"""La ligne de commande : elle doit répondre, et dire ce qui n'existe pas encore."""

from __future__ import annotations

import pytest

from dashboard_tr import cli


def test_la_version_repond(capsys):
    with pytest.raises(SystemExit) as sortie:
        cli.main(["--version"])

    assert sortie.value.code == 0
    assert "dashboard" in capsys.readouterr().out


def test_sans_commande_l_aide_s_affiche(capsys):
    assert cli.main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_les_emplacements_s_affichent(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_TR_DOSSIER", str(tmp_path / "personnel"))

    assert cli.main(["emplacements"]) == 0
    affichage = capsys.readouterr().out
    assert "exports" in affichage
    assert "pas encore créé" in affichage


@pytest.mark.parametrize(
    ("commande", "etape"),
    [("rafraichir", "étape 2"), ("exporter-pivot", "étape 2"), ("ouvrir", "étape 9")],
)
def test_une_commande_pas_encore_ecrite_dit_a_quelle_etape_elle_arrive(commande, etape, capsys):
    assert cli.main([commande]) == 1
    assert etape in capsys.readouterr().err
