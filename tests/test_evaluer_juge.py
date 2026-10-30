"""Tests à réponse connue pour le comptage des ratés et fausses alertes (brique 4)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import evaluer_juge as e  # noqa: E402

CAS_CLAIR_A = {"texte": "Pâtes chez Carrefour 12 €", "decision_attendue": "auto", "categorie_attendue": "A"}
CAS_AMBIGU = {"texte": "Amazon 25 €", "decision_attendue": "confirmer", "categorie_attendue": "?"}


def lecture(lettre, score, valide=True):
    scores = dict.fromkeys("ABCDE", (1 - score) / 4)
    scores[lettre] = score
    return {"lettre": lettre, "scores": scores, "valide": valide}


@pytest.mark.parametrize("cas, lec, attendu", [
    (CAS_CLAIR_A, lecture("A", 0.95), "correct"),
    (CAS_CLAIR_A, lecture("A", 0.60), "fausse_alerte"),
    (CAS_CLAIR_A, lecture("B", 0.95), "rate_categorie"),
    (CAS_CLAIR_A, lecture("A", 0.95, valide=False), "fausse_alerte"),
    (CAS_AMBIGU, lecture("E", 0.60), "correct"),
    (CAS_AMBIGU, lecture("E", 0.95), "rate_ambigu"),
])
def test_issue(cas, lec, attendu):
    assert e.issue(cas, lec, seuil=0.80) == attendu


def test_compter_additionne_les_deux_sortes_de_rates():
    cas = [CAS_CLAIR_A, CAS_CLAIR_A, CAS_AMBIGU, CAS_AMBIGU]
    lectures = [lecture("B", 0.9), lecture("A", 0.5), lecture("E", 0.9), lecture("E", 0.5)]
    c = e.compter(cas, lectures, seuil=0.80)
    assert (c["rate_categorie"], c["fausse_alerte"], c["rate_ambigu"], c["correct"]) == (1, 1, 1, 1)
    assert c["rates"] == 2


def test_un_seuil_plus_haut_ne_diminue_jamais_les_fausses_alertes():
    cas = [CAS_CLAIR_A] * 3
    lectures = [lecture("A", s) for s in (0.55, 0.85, 0.97)]
    alertes = [e.compter(cas, lectures, s)["fausse_alerte"] for s in e.SEUILS]
    assert alertes == sorted(alertes)


def test_regles_du_code_transforment_un_rate_en_confirmation():
    cas = {"texte": "Paiement PayPal 9,99 €", "decision_attendue": "confirmer", "categorie_attendue": "?"}
    lec = lecture("E", 0.953)  # réponse réelle de Qwen sur ce cas
    assert e.issue(cas, lec, seuil=0.90) == "rate_ambigu"
    assert e.issue(cas, lec, seuil=0.90, avec_regles=True) == "correct"
