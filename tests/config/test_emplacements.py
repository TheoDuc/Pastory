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


# --- L'ancien nom de l'application (D-74) -------------------------------------------
#
# L'application s'est appelée « DashBoard Trade Republic ». Sur une machine où elle
# tournait déjà, l'export, le cache et la configuration sont restés dans un dossier à
# l'ancien nom. Rien n'est déplacé automatiquement : l'ancien dossier est seulement
# signalé. Ces tests vérifient qu'il est trouvé, et surtout qu'il n'est pas inventé.


def test_l_ancien_dossier_est_signale_s_il_existe_encore(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(emplacements.sys, "platform", "win32")
    local = tmp_path / "AppData" / "Local"
    ancien = local / "DashBoardTradeRepublic"
    ancien.mkdir(parents=True)
    environnement = {"LOCALAPPDATA": str(local)}

    assert emplacements.anciens_dossiers_personnels(environnement) == [ancien]


def test_aucun_ancien_dossier_sur_une_installation_neuve(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(emplacements.sys, "platform", "win32")
    local = tmp_path / "AppData" / "Local"
    local.mkdir(parents=True)

    assert emplacements.anciens_dossiers_personnels({"LOCALAPPDATA": str(local)}) == []


def test_un_emplacement_choisi_a_la_main_n_a_pas_change_de_nom(tmp_path: Path, monkeypatch):
    """Qui choisit son dossier le nomme lui-même : il n'y a pas d'ancien nom à chercher."""
    monkeypatch.setattr(emplacements.sys, "platform", "win32")
    local = tmp_path / "AppData" / "Local"
    (local / "DashBoardTradeRepublic").mkdir(parents=True)
    environnement = {
        "LOCALAPPDATA": str(local),
        emplacements.VARIABLE_EMPLACEMENT: str(tmp_path / "ailleurs"),
    }

    assert emplacements.anciens_dossiers_personnels(environnement) == []


def test_un_fichier_du_nom_de_l_ancien_dossier_n_est_pas_un_dossier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(emplacements.sys, "platform", "win32")
    local = tmp_path / "AppData" / "Local"
    local.mkdir(parents=True)
    (local / "DashBoardTradeRepublic").write_text("ceci n'est pas un dossier", encoding="utf-8")

    assert emplacements.anciens_dossiers_personnels({"LOCALAPPDATA": str(local)}) == []
