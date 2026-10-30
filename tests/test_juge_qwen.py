"""Tests à réponse connue pour la lecture des scores de Qwen (brique 4).

Ils utilisent de fausses réponses d'Ollama : ils tournent sans le modèle.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import juge_qwen as j  # noqa: E402


def fausse_reponse(token_renvoye, probas):
    """Réponse au format d'Ollama : un token et ses top_logprobs."""
    return {"logprobs": [{
        "token": token_renvoye,
        "top_logprobs": [{"token": t, "logprob": math.log(p)} for t, p in probas.items()],
    }]}


def test_reponse_normale():
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.90, "B": 0.04, "C": 0.03, "D": 0.02, "E": 0.01}))
    assert lecture["valide"] and lecture["lettre"] == "A"
    assert sum(lecture["scores"].values()) == pytest.approx(1.0)
    assert lecture["scores"]["A"] == pytest.approx(0.90)
    assert j.decider(lecture) == "auto"


def test_renormalisation_sur_les_cinq_lettres():
    # 10 % de la masse part sur <think> : le score de A est 0,72 / 0,90 = 0,80.
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.72, "<think>": 0.10, "B": 0.18}))
    assert lecture["scores"]["A"] == pytest.approx(0.80)
    assert lecture["masse_hors_lettres"] == pytest.approx(0.10)


def test_seuil_atteint_exactement_donne_auto():
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.80, "B": 0.20}))
    assert j.decider(lecture, seuil=0.80) == "auto"


def test_score_sous_le_seuil_demande_confirmation():
    lecture = j.lire_scores(fausse_reponse("E", {"A": 0.30, "E": 0.65, "D": 0.05}))
    assert lecture["valide"]
    assert j.decider(lecture) == "confirmer"


def test_token_think_est_invalide():
    lecture = j.lire_scores(fausse_reponse("<think>", {"<think>": 0.6, "A": 0.4}))
    assert not lecture["valide"] and lecture["lettre"] is None
    assert j.decider(lecture) == "confirmer"


def test_lettre_renvoyee_qui_n_est_pas_la_plus_probable_est_invalide():
    # Cas réel observé avec presence_penalty = 1,5 : Qwen renvoie A alors que E domine.
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.26, "E": 0.65, "D": 0.09}))
    assert not lecture["coherent"] and not lecture["valide"]
    assert j.decider(lecture, seuil=0.10) == "confirmer"


def test_lettres_manquantes_signalees():
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.95, "B": 0.05}))
    assert lecture["lettres_manquantes"] == ["C", "D", "E"]


def test_token_avec_espace_additionne():
    lecture = j.lire_scores(fausse_reponse("A", {"A": 0.50, " A": 0.30, "B": 0.20}))
    assert lecture["scores"]["A"] == pytest.approx(0.80)


def test_categories_identiques_partout():
    # Les lettres du juge sont celles des règles métier et des tests.
    assert set(j.LETTRES) == {"A", "B", "C", "D", "E"}
    for lettre, nom in zip(j.LETTRES, ["Alimentation", "Transport", "Logement", "Loisirs", "Autres"]):
        assert f"{lettre} = {nom}" in j.PROMPT_SYSTEME
