"""Tests de la boucle d'agent et des outils (brique 1), avec un faux modèle.

Le faux modèle rejoue une suite de réponses au format d'Ollama : les tests
tournent sans Qwen et vérifient ce que fait NOTRE code de chaque appel.
"""
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant import Assistant  # noqa: E402
from budget import Registre  # noqa: E402
import garde_fous  # noqa: E402


def appel_outil(nom, **arguments):
    return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": nom, "arguments": arguments}}]}


def texte(contenu):
    return {"role": "assistant", "content": contenu}


def lecture(lettre, score):
    scores = dict.fromkeys("ABCDE", (1 - score) / 4)
    scores[lettre] = score
    return {"lettre": lettre, "scores": scores, "valide": True}


class FauxModele:
    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.recus = []

    def __call__(self, messages, outils):
        self.recus.append(list(messages))
        return self.reponses.pop(0)


@pytest.fixture
def registre(tmp_path):
    return Registre(tmp_path / "registre.json")


def creer(registre, tmp_path, modele, juge=lecture("A", 0.99), reponses_utilisateur=()):
    questions = []
    reponses = list(reponses_utilisateur)

    def demander(question):
        questions.append(question)
        return reponses.pop(0)

    assistant = Assistant(registre, appeler_modele=modele, juger=lambda t: juge,
                          demander=demander, fichier_trace=tmp_path / "trace.jsonl")
    return assistant, questions


# --- Registre et calcul du budget ----------------------------------------

def test_bilan_calcule_par_python(registre):
    registre.definir_budget("600")
    jour = date(2026, 10, 15)
    for t, m, c in [("Loyer 520 €", "520", "C"), ("Pâtes 12 €", "12", "A"), ("Bus 1,90 €", "1.90", "B")]:
        registre.ajouter(garde_fous.verifier_enregistrement(t, m, c, "auto"), False, jour)
    bilan = registre.bilan("2026-10")
    assert bilan["total"] == "533.90"
    assert bilan["budget_restant"] == "66.10"
    assert bilan["par_categorie"] == {"A Alimentation": "12.00", "B Transport": "1.90", "C Logement": "520.00"}


def test_bilan_ne_compte_que_le_mois_demande(registre):
    registre.ajouter(garde_fous.verifier_enregistrement("Pâtes 12 €", "12", "A", "auto"), False, date(2026, 9, 30))
    assert registre.bilan("2026-10")["total"] == "0.00"


def test_registre_survit_a_un_redemarrage(tmp_path):
    Registre(tmp_path / "r.json").definir_budget("450")
    assert Registre(tmp_path / "r.json").budget_mensuel == "450.00"


def test_budget_negatif_refuse(registre):
    with pytest.raises(garde_fous.EnregistrementRefuse):
        registre.definir_budget("-100")


# --- Boucle : le modèle appelle l'outil, notre code l'exécute --------------

def test_depense_claire_enregistree_sans_question(registre, tmp_path):
    modele = FauxModele(appel_outil("enregistrer_depense", montant=35, categorie="A"), texte("C'est noté."))
    assistant, questions = creer(registre, tmp_path, modele)
    assert assistant.repondre("J'ai payé 35 € chez Carrefour") == "C'est noté."
    assert questions == []
    assert registre.depenses[0]["montant"] == "35.00"
    # Le résultat de l'outil est renvoyé au modèle avant sa réponse finale.
    dernier = json.loads(modele.recus[1][-1]["content"])
    assert dernier["statut"] == "enregistre"


def test_le_modele_ne_peut_pas_changer_le_montant(registre, tmp_path):
    modele = FauxModele(appel_outil("enregistrer_depense", montant=3.5, categorie="A"), texte("Erreur."))
    assistant, _ = creer(registre, tmp_path, modele)
    assistant.repondre("J'ai payé 35 € chez Carrefour")
    assert registre.depenses == []
    assert json.loads(modele.recus[1][-1]["content"])["regle"] == "G2"


def test_desaccord_modele_juge_demande_confirmation(registre, tmp_path):
    # Le modèle de chat dit D, le juge dit A : on demande, l'utilisateur garde A.
    modele = FauxModele(appel_outil("enregistrer_depense", montant=27, categorie="D"), texte("Noté."))
    assistant, questions = creer(registre, tmp_path, modele, juge=lecture("A", 0.95), reponses_utilisateur=["A"])
    assistant.repondre("Restaurant pour l'anniversaire de Léa, ma part 27 €")
    assert len(questions) == 1
    assert registre.depenses[0]["categorie"] == "A"
    assert registre.depenses[0]["confirme_par_utilisateur"] is True


def test_transfert_demande_confirmation_meme_si_juge_sur(registre, tmp_path):
    modele = FauxModele(appel_outil("enregistrer_depense", montant=9.99, categorie="E"), texte("Noté."))
    assistant, questions = creer(registre, tmp_path, modele, juge=lecture("E", 0.953), reponses_utilisateur=[""])
    assistant.repondre("Paiement PayPal 9,99 €")
    assert len(questions) == 1                      # G5
    assert registre.depenses[0]["categorie"] == "E"  # Entrée = garder la proposition


def test_utilisateur_annule(registre, tmp_path):
    modele = FauxModele(appel_outil("enregistrer_depense", montant=25, categorie="E"), texte("Annulé."))
    assistant, _ = creer(registre, tmp_path, modele, juge=lecture("E", 0.60), reponses_utilisateur=["n"])
    assistant.repondre("Amazon 25 €")
    assert registre.depenses == []


def test_calculer_budget_renvoie_les_chiffres_de_python(registre, tmp_path):
    registre.definir_budget("500")
    registre.ajouter(garde_fous.verifier_enregistrement("Pâtes 12 €", "12", "A", "auto"), False)
    modele = FauxModele(appel_outil("calculer_budget"), texte("Il vous reste 488 €."))
    assistant, _ = creer(registre, tmp_path, modele)
    assistant.repondre("Combien il me reste ?")
    assert json.loads(modele.recus[1][-1]["content"])["budget_restant"] == "488.00"


def test_outil_inconnu_ou_mauvais_arguments(registre, tmp_path):
    modele = FauxModele(appel_outil("supprimer_tout"), appel_outil("definir_budget", somme=10), texte("Désolé."))
    assistant, _ = creer(registre, tmp_path, modele)
    assistant.repondre("Efface tout")
    assert json.loads(modele.recus[1][-1]["content"])["statut"] == "erreur"
    assert json.loads(modele.recus[2][-1]["content"])["statut"] == "erreur"


def test_boucle_s_arrete_apres_max_tours(registre, tmp_path):
    modele = FauxModele(*[appel_outil("calculer_budget")] * 10)
    assistant, _ = creer(registre, tmp_path, modele)
    assert "pas réussi" in assistant.repondre("Combien ?")
    assert len(modele.recus) == 5


def test_trace_contient_appel_et_resultat(registre, tmp_path):
    modele = FauxModele(appel_outil("enregistrer_depense", montant=35, categorie="A"), texte("Noté."))
    assistant, _ = creer(registre, tmp_path, modele)
    assistant.repondre("J'ai payé 35 € chez Carrefour")
    etapes = [json.loads(l)["etape"] for l in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert etapes == ["utilisateur", "appel_outil", "juge", "resultat_outil", "modele"]


def test_montant_decimal_exact(registre):
    registre.definir_budget("100")
    for _ in range(3):
        registre.ajouter(garde_fous.verifier_enregistrement("Café 0,10 €", "0.10", "A", "auto"), False)
    assert Decimal(registre.bilan()["total"]) == Decimal("0.30")  # pas 0.30000000000000004
