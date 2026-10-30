"""Tests à réponse connue pour la notation de la comparaison (brique 9)."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import comparer as c  # noqa: E402

CLAIR = {"montant_attendu": "35.00", "decision_attendue": "auto", "categorie_attendue": "A"}
AMBIGU = {"montant_attendu": "9.99", "decision_attendue": "confirmer", "categorie_attendue": "?"}


@pytest.mark.parametrize("cas, decision, categorie, montant, attendu", [
    (CLAIR, "auto", "A", Decimal("35.00"), True),
    (CLAIR, "auto", "B", Decimal("35.00"), False),       # mauvaise catégorie
    (CLAIR, "confirmer", "A", Decimal("35.00"), False),  # fausse alerte
    (CLAIR, "auto", "A", Decimal("3.50"), False),        # mauvais montant
    (CLAIR, "invalide", None, None, False),
    (AMBIGU, "confirmer", "E", Decimal("9.99"), True),
    (AMBIGU, "auto", "E", Decimal("9.99"), False),       # ambigu enregistré
    (AMBIGU, "confirmer", "E", Decimal("99.90"), False), # bonne décision, mauvais montant
])
def test_noter(cas, decision, categorie, montant, attendu):
    assert c.noter(cas, decision, categorie, montant) is attendu


def test_lecture_reponse_json_de_qwen_seul():
    assert c.decision_qwen_seul('{"montant": 35, "categorie": "A", "confirmation": false}') == ("auto", "A", Decimal("35.00"))
    assert c.decision_qwen_seul('{"montant": 9.99, "categorie": "E", "confirmation": true}')[0] == "confirmer"
    # Réponse réelle de Qwen : JSON entouré de balises Markdown.
    assert c.decision_qwen_seul('```json\n{\n  "montant": 3.30,\n  "categorie": "A",\n  "confirmation": false\n}\n```') \
        == ("auto", "A", Decimal("3.30"))
    assert c.decision_qwen_seul("pas du json") == ("invalide", None, None)
    assert c.decision_qwen_seul('{"categorie": "A"}') == ("invalide", None, None)


def test_systeme_lit_le_montant_dans_le_texte_et_applique_g5():
    lecture = {"lettre": "E", "scores": {"A": 0.01, "B": 0.01, "C": 0.01, "D": 0.02, "E": 0.95}, "valide": True}
    assert c.decision_systeme("Paiement PayPal 9,99 €", lecture) == ("confirmer", "E", Decimal("9.99"))
    assert c.decision_systeme("Pharmacie 7,80 €", lecture) == ("auto", "E", Decimal("7.80"))


def test_resume_moyenne_et_ecart_type():
    r = c.resumer([0.5, 0.75, 1.0])
    assert r["moyenne"] == pytest.approx(0.75)
    assert r["ecart_type"] == pytest.approx(0.25)
    assert (r["min"], r["max"]) == (0.5, 1.0)
