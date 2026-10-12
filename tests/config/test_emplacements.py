"""Les fichiers personnels vivent hors du dossier synchronisé (D-37)."""

from __future__ import annotations

from pathlib import Path

from pastory.config import emplacements


def test_l_emplacement_peut_etre_choisi_par_l_utilisateur(tmp_path: Path):
    environnement = {emplacements.VARIABLE_EMPLACEMENT: str(tmp_path / "ailleurs")}
    assert emplacements.dossier_personnel(environnement) == tmp_path / "ailleurs"


def test_sur_windows_les_fichiers_vont_dans_le_dossier_local(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(emplacements.sys, "platform", "win32")
    environnement = {"LOCALAPPDATA": str(tmp_path / "AppData" / "Local")}

    racine = emplacements.dossier_personnel(environnement)

    assert racine == tmp_path / "AppData" / "Local" / emplacements.NOM_APPLICATION
    # « Local » est justement la partie de AppData que OneDrive ne synchronise pas.
    assert "OneDrive" not in str(racine)


def test_les_trois_dossiers_sont_sous_la_racine(tmp_path: Path):
    environnement = {emplacements.VARIABLE_EMPLACEMENT: str(tmp_path)}

    dossiers = emplacements.tous_les_dossiers(environnement)

    assert set(dossiers) == {"racine", "exports", "cache", "configuration"}
    for nom, chemin in dossiers.items():
        assert chemin == tmp_path or chemin.parent == tmp_path, nom


def test_creer_dossiers_est_repetable(tmp_path: Path):
    environnement = {emplacements.VARIABLE_EMPLACEMENT: str(tmp_path / "personnel")}

    emplacements.creer_dossiers(environnement)
    dossiers = emplacements.creer_dossiers(environnement)

    assert all(chemin.is_dir() for chemin in dossiers.values())

