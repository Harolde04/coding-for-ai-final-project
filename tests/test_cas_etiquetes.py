"""Vérifie la cohérence du jeu de 40 cas étiquetés (brique 4)."""
import csv
import re
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER_CAS = RACINE / "data" / "cas_etiquetes.csv"
FICHIER_REGLES = RACINE / "REGLES_METIER.md"
CATEGORIES = {"A", "B", "C", "D", "E"}


def charger_cas():
    with FICHIER_CAS.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def regles_documentees():
    return set(re.findall(r"\*\*(R-[A-ENX]\d)\*\*", FICHIER_REGLES.read_text(encoding="utf-8")))


def test_quarante_cas_ids_uniques():
    cas = charger_cas()
    assert len(cas) == 40
    assert [int(c["id"]) for c in cas] == list(range(1, 41))


def test_montants_strictement_positifs():
    for c in charger_cas():
        assert float(c["montant_attendu"]) > 0, c["id"]


def test_cas_auto_ont_une_seule_categorie():
    for c in charger_cas():
        if c["decision_attendue"] == "auto":
            assert c["categorie_attendue"] in CATEGORIES, c["id"]
            assert c["categories_possibles"] == c["categorie_attendue"], c["id"]
            assert not c["regle"].startswith("R-X"), c["id"]


def test_cas_confirmer_n_inventent_pas_de_categorie():
    for c in charger_cas():
        if c["decision_attendue"] == "confirmer":
            assert c["categorie_attendue"] == "?", c["id"]
            possibles = c["categories_possibles"].split("|")
            assert len(possibles) >= 2 and set(possibles) <= CATEGORIES, c["id"]
            assert c["regle"].startswith("R-X"), c["id"]


def test_chaque_regle_citee_est_documentee():
    documentees = regles_documentees()
    for c in charger_cas():
        assert c["regle"] in documentees, (c["id"], c["regle"])


def test_le_montant_attendu_apparait_dans_le_texte():
    # Normalise "3,30" / "9€50" / "2.40" pour vérifier qu'on n'a pas fait de faute de frappe.
    for c in charger_cas():
        texte = c["texte"].replace("€", ".").replace(",", ".")
        montant = float(c["montant_attendu"])
        nombres = [float(n.rstrip(".")) for n in re.findall(r"\d+(?:\.\d+)?", texte)]
        assert montant in nombres, (c["id"], c["texte"])


def test_les_deux_decisions_sont_representees():
    decisions = Counter(c["decision_attendue"] for c in charger_cas())
    assert decisions["auto"] >= 10 and decisions["confirmer"] >= 10
    categories = Counter(c["categorie_attendue"] for c in charger_cas())
    assert all(categories[lettre] >= 5 for lettre in CATEGORIES)
