"""Le recoupement avec `account_transactions.csv` (D-42).

Le CSV donne en nombres ce que l'adaptateur doit lire dans des textes allemands. C'est le
filet qui aurait attrapé tout seul le piège du séparateur décimal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pastory.adaptateurs.trade_republic import recoupement_csv
from pastory.adaptateurs.trade_republic.lecture import Lecteur
from pastory.adaptateurs.trade_republic.rapport import Rapport
from pastory.config.comptes import Configuration, RoleCompte
from pastory.pivot.operation import Poche
from tests.adaptateurs.trade_republic import evenements_fictifs as fictifs

ENTETE = "Date;Type;Valeur;Note;ISIN;Parts;Frais;Impôts / Taxes;ISIN2;Parts2"

CONFIGURATION = Configuration(
    roles={
        fictifs.COMPTE_COURANT: RoleCompte.COURANT,
        fictifs.COMPTE_PEA: RoleCompte.PEA,
    },
    poches_corrigees={fictifs.ACTIF_ACTION_B: Poche.CTO},
)


def ecrire_csv(chemin: Path, lignes: list[str]) -> Path:
    chemin.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8")
    return chemin


def recouper(evenements, lignes_csv, tmp_path) -> Rapport:
    rapport = Lecteur(CONFIGURATION).lire(evenements)
    fichier = ecrire_csv(tmp_path / "account_transactions.csv", lignes_csv)
    recoupement_csv.recouper(rapport.operations, recoupement_csv.lire_csv(fichier), rapport)
    return rapport


def messages(rapport) -> list[str]:
    return [s.message for s in rapport.signalements if s.categorie == "recoupement CSV"]


class TestAccord:
    def test_des_valeurs_identiques_ne_produisent_aucun_signalement(self, tmp_path):
        rapport = recouper(
            [fictifs.plan_epargne()],
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2;0;;;"],
            tmp_path,
        )
        assert messages(rapport) == []

    def test_l_horodatage_est_rapproche_a_la_seconde(self, tmp_path):
        # Le JSON horodate à la milliseconde, le CSV tronque à la seconde. Sans cela, plus
        # rien ne se rapprocherait — et le rapport annoncerait, à tort, que toutes les
        # opérations manquent au CSV.
        evenement = fictifs.plan_epargne()
        evenement["timestamp"] = "2026-01-02T08:00:00.309+0000"

        rapport = recouper(
            [evenement],
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2;0;;;"],
            tmp_path,
        )
        assert messages(rapport) == []


class TestDesaccord:
    def test_une_quantite_differente_est_signalee(self, tmp_path):
        rapport = recouper(
            [fictifs.plan_epargne()],
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2000000;0;;;"],
            tmp_path,
        )
        assert any("quantité" in message for message in messages(rapport))

    def test_des_frais_differents_sont_signales(self, tmp_path):
        rapport = recouper(
            [fictifs.achat_pea()],
            [f"2026-02-10T09:30:00;Achat;-201,60;Note;{fictifs.ACTIF_ACTION};10;2,00;0,60;;"],
            tmp_path,
        )
        assert any("frais" in message for message in messages(rapport))

    def test_une_operation_absente_du_csv_est_signalee(self, tmp_path):
        rapport = recouper([fictifs.plan_epargne()], [], tmp_path)
        assert any("aucune ligne du CSV" in message for message in messages(rapport))

    def test_une_ligne_csv_sans_operation_est_signalee(self, tmp_path):
        rapport = recouper(
            [],
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2;0;;;"],
            tmp_path,
        )
        assert any("que la lecture n'a pas produite" in message for message in messages(rapport))


class TestAbsencesConnues:
    """Le CSV omet certaines opérations : ce sont des faits, pas des alertes (inventaire §8)."""

    def test_une_action_gagnee_absente_du_csv_n_alerte_pas(self, tmp_path):
        rapport = recouper([fictifs.action_gagnee()], [], tmp_path)
        assert messages(rapport) == []

    def test_une_distribution_de_capital_absente_du_csv_n_alerte_pas(self, tmp_path):
        # Le CSV la range parmi les « Dépôt », sans ISIN : elle n'y est pas rapprochable.
        rapport = recouper([fictifs.distribution_capital()], [], tmp_path)
        assert messages(rapport) == []


class TestLectureDuFichier:
    def test_les_lignes_qui_ne_concernent_pas_un_actif_sont_ignorees(self, tmp_path):
        fichier = ecrire_csv(
            tmp_path / "t.csv",
            [
                "2026-01-01T10:00:00;Dépôt;500;Un nom;;;;;;",
                "2026-01-03T10:00:00;Intérêts;1,20;Zinsen;;;;;;",
                f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2;0;;;",
            ],
        )
        assert len(recoupement_csv.lire_csv(fichier)) == 1

    def test_les_actions_gratuites_apparaissent_sous_le_libelle_split(self, tmp_path):
        fichier = ecrire_csv(
            tmp_path / "t.csv",
            [f"2026-03-01T09:00:00;SPLIT;0;Note;{fictifs.ACTIF_ACTION_B};3;;;;"],
        )
        lignes = recoupement_csv.lire_csv(fichier)
        assert len(lignes) == 1
        assert lignes[0].type_operation.value == "titres_recus"

    def test_une_colonne_illisible_est_signalee_au_lieu_d_etre_sautee(self, tmp_path):
        # Si le CSV changeait de forme — ici une quantité écrite à point décimal — avaler
        # l'erreur désarmerait le recoupement (D-42) au moment précis où il servirait :
        # plus aucune quantité ne serait comparée, et le rapport n'en dirait rien.
        fichier = ecrire_csv(
            tmp_path / "t.csv",
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2.5;0;;;"],
        )
        rapport = Rapport()
        recoupement_csv.lire_csv(fichier, rapport)

        assert any("illisible" in s.message for s in rapport.signalements)

    @pytest.mark.parametrize("valeur", ["", "   "])
    def test_une_case_vide_vaut_non_renseigne_et_non_zero(self, valeur, tmp_path):
        # Prendre une case vide pour un zéro inventerait un frais nul là où le CSV ne dit
        # rien, et effacerait un vrai désaccord.
        fichier = ecrire_csv(
            tmp_path / "t.csv",
            [f"2026-01-02T08:00:00;Achat;-50;Note;{fictifs.ACTIF_ETF};2;{valeur};;;"],
        )
        assert recoupement_csv.lire_csv(fichier)[0].frais is None
