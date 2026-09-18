"""Le dictionnaire des libellés : une clé (section, libellé), et une écriture déclarée.

Ces tests protègent la propriété qui rend le reste sûr : **le lexique ne peut pas se
contredire**. Un synonyme ajouté avec la mauvaise écriture doit faire échouer le chargement,
pas produire des quantités fausses.
"""

from __future__ import annotations

import pytest

from dashboard_tr.adaptateurs.trade_republic import lexique
from dashboard_tr.adaptateurs.trade_republic.lexique import (
    LIBELLES,
    Entree,
    Notion,
    Section,
)
from dashboard_tr.adaptateurs.trade_republic.nombres import Convention


class TestUnLibelleSeulNeSuffitPas:
    def test_aktien_designe_des_parts_ou_des_euros_selon_la_section(self):
        parts = lexique.entree(Section.APERCU, "Aktien")
        euros = lexique.entree(Section.TRANSACTION, "Aktien")

        assert parts is not None and parts.notion is Notion.QUANTITE
        assert euros is not None and euros.notion is Notion.VALEUR_DES_TITRES

    def test_la_quantite_ne_s_ecrit_pas_pareil_selon_la_section(self):
        # C'est le piège central de l'étape 2, figé ici pour qu'il ne revienne pas.
        assert (
            lexique.convention(Section.DETAIL_TRANSACTION, Notion.QUANTITE)
            is Convention.VIRGULE_DECIMALE
        )
        assert lexique.convention(Section.AFFAIRE, Notion.QUANTITE) is Convention.POINT_DECIMAL
        assert lexique.convention(Section.APERCU, Notion.QUANTITE) is Convention.POINT_DECIMAL


class TestDeuxLangues:
    @pytest.mark.parametrize(
        ("allemand", "francais", "section"),
        [
            ("Gebühr", "Frais", Section.APERCU),
            ("Steuer", "Taxe", Section.APERCU),
            ("Summe", "Total", Section.APERCU),
            ("Bruttoertrag", "Produit brut", Section.AFFAIRE),
        ],
    )
    def test_les_deux_langues_donnent_la_meme_notion(self, allemand, francais, section):
        assert lexique.entree(section, allemand) == lexique.entree(section, francais)

    def test_les_sections_sont_reconnues_dans_les_deux_langues(self):
        assert lexique.section_connue("Übersicht") is Section.APERCU
        assert lexique.section_connue("Aperçu") is Section.APERCU

    def test_un_libelle_inconnu_ne_renvoie_rien(self):
        assert lexique.entree(Section.APERCU, "Sonderrabatt") is None
        assert lexique.section_connue("Du hast 50,00 € gespart") is None


class TestCoherenceDuLexique:
    def test_le_lexique_se_contredirait_il_qu_il_refuserait_de_se_charger(self, monkeypatch):
        # Un synonyme ajouté avec la mauvaise écriture est l'erreur la plus facile à commettre
        # en étendant le lexique, et la plus difficile à repérer ensuite dans les chiffres.
        contradictoire = dict(LIBELLES)
        contradictoire[(Section.AFFAIRE, "Actions (autre écriture)")] = Entree(
            Notion.QUANTITE, Convention.VIRGULE_DECIMALE
        )
        monkeypatch.setattr(lexique, "LIBELLES", contradictoire)

        with pytest.raises(ValueError, match="incohérent"):
            lexique._conventions_par_notion()

    def test_le_lexique_livre_se_charge_sans_contradiction(self):
        assert lexique._conventions_par_notion() == lexique.CONVENTIONS

    def test_toute_notion_numerique_declare_son_ecriture(self):
        for (section, libelle), entree in LIBELLES.items():
            if entree.convention is None:
                continue
            assert lexique.convention(section, entree.notion) is not None, libelle
