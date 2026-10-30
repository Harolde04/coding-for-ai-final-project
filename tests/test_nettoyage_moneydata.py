"""Tests à réponse connue pour le nettoyage de MoneyData (brique 6)."""
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

import nettoyage_moneydata as n  # noqa: E402

CORRESPONDANCE = n.charger_correspondance()
REGLES_COMMERCANTS = n.charger_regles_commercants()
REGLES_DOCUMENTEES = set(
    re.findall(r"\*\*(R-[A-ENX]\d)\*\*", (RACINE / "REGLES_METIER.md").read_text(encoding="utf-8"))
)


def classer(libelle, categorie, est_credit=False, type_paiement="DEB"):
    return n.classer(libelle, categorie, est_credit, type_paiement, CORRESPONDANCE, REGLES_COMMERCANTS)


# --- Dates ---------------------------------------------------------------

def test_date_texte_lue_jour_mois():
    assert n.corriger_date("13/07/2022") == date(2022, 7, 13)


def test_date_excel_inversee_est_remise_en_ordre():
    # « 12/07/2022 » lu par Excel comme le 7 décembre.
    assert n.corriger_date(datetime(2022, 12, 7)) == date(2022, 7, 12)


# --- Normalisation -------------------------------------------------------

def test_libelle_espaces_multiples():
    assert n.normaliser_libelle("LIDL GB  NOTTINGHA ") == "LIDL GB NOTTINGHA"


def test_categorie_espace_final_et_vide():
    assert n.normaliser_categorie("Groceries ") == "Groceries"
    assert n.normaliser_categorie(float("nan")) == "VIDE"


# --- Classement ----------------------------------------------------------

@pytest.mark.parametrize("libelle, categorie, attendu", [
    ("LIDL GB NOTTINGHA", "Groceries", ("A", "origine")),
    ("HOLLAND & BARRETT", "Groceries", ("E", "commercant")),      # Q6
    ("VIRGIN MEDIA PYMTS", "Bills", ("C", "commercant")),          # Q3
    ("CLUB LLOYDS FEE", "Bills", ("E", "commercant")),
    ("O2", "Other Shopping", ("E", "commercant")),
    ("IKEA ONLINE", "Other Shopping", ("C", "commercant")),
    ("PLUSNET PLC 0845 1", "Entertainment", ("C", "commercant")),  # erreur des auteurs
    ("REVOLUTION DE CUBA", "Dine Out", ("D", "commercant")),       # bar, pas repas
    ("HILTON", "Hotels", ("D", "origine")),                        # le commerçant confirme
    ("PRINCIPALITY BS", "Mortgage", ("C", "origine")),             # Q2
    ("DEZREZ LEGAL LTD", "Mortgage", ("?", "non_identifie")),      # pas une mensualité
    ("LV LIFE", "Insurance", ("E", "commercant")),                 # Q4
    ("ZURICH", "Insurance", ("?", "non_identifie")),               # R-X6
    ("ASSURANT INTER LTD", "Insurance", ("E", "commercant")),      # R-E6
    ("TV LICENCE MBP", "Bills", ("D", "commercant")),              # R-D4
    ("THE BIKE HUB", "Other Shopping", ("?", "non_identifie")),    # R-X5
    ("Amazon UK Marketpl", "Amazon", ("?", "non_identifie")),
    ("THE PLANT", "VIDE", ("?", "non_identifie")),                 # Q5
    ("EXPEDIA 7420654555", "Travel", ("?", "non_identifie")),
])
def test_classement_connu(libelle, categorie, attendu):
    lettre, provenance, _, _, _ = classer(libelle, categorie)
    assert (lettre, provenance) == attendu


@pytest.mark.parametrize("libelle, categorie, regle, possibles", [
    ("TV LICENCE MBP", "Bills", "R-D4", "D"),
    ("THE BIKE HUB", "Other Shopping", "R-X5", "B|D"),
    ("IZ *Nottingham Bik", "Other Shopping", "R-X5", "B|D"),       # libellé tronqué
    ("ASSURANT INTER LTD", "Insurance", "R-E6", "E"),             # règle tirée d'un document
    ("ZURICH", "Insurance", "R-X6", "C|E"),
    ("Amazon UK Marketpl", "Amazon", "R-X1", "A|B|C|D|E"),
])
def test_regle_et_categories_possibles(libelle, categorie, regle, possibles):
    _, _, regle_obtenue, _, possibles_obtenus = classer(libelle, categorie)
    assert (regle_obtenue, possibles_obtenus) == (regle, possibles)


def test_credit_exclu():
    assert classer("Amazon UK Marketpl", "Amazon", est_credit=True)[0] == "EXCLU"


def test_retrait_especes_exclu_meme_hors_categorie_cash():  # Q1
    lettre, _, regle, _, _ = classer("LNK ARRIVA TRAINS", "Travel", type_paiement="CPT")
    assert (lettre, regle) == ("EXCLU", "R-N3")


def test_epargne_exclue_meme_mal_categorisee():
    assert classer("SAVE THE CHANGE", "Insurance")[0] == "EXCLU"


def test_categorie_inconnue_refusee():
    with pytest.raises(ValueError):
        classer("X", "Catégorie inventée")


# --- Pseudonymisation ----------------------------------------------------

def test_particulier_masque_mais_pas_entreprise():
    assert n.est_particulier("MISS D WU", "FPO")
    assert not n.est_particulier("TRISTRAMS LETTINGS", "FPO")
    assert not n.est_particulier("LIDL GB NOTTINGHA", "DEB")


# --- Cohérence des tables de décision ------------------------------------

def test_tables_citent_des_regles_documentees():
    for entree in CORRESPONDANCE.values():
        assert entree["lettre"] in n.LETTRES | {"MELANGEE", "EXCLU"}
        assert entree["regle"] in REGLES_DOCUMENTEES, entree
    for regle in REGLES_COMMERCANTS:
        assert regle["lettre"] in n.LETTRES | {"?", "EXCLU"}
        assert regle["regle"] in REGLES_DOCUMENTEES, regle


# --- Bout en bout (seulement si le fichier brut est présent) -------------

@pytest.mark.skipif(not n.FICHIER_BRUT.exists(), reason="fichier brut MoneyData absent")
def test_nettoyage_complet():
    gardees, exclues, _ = n.nettoyer(n.FICHIER_BRUT)
    assert len(gardees) + len(exclues) == 6567
    toutes = sorted(gardees + exclues, key=lambda l: l["id_origine"])
    dates = [l["date"] for l in toutes]
    # Les transactions sont numérotées de la plus récente à la plus ancienne.
    assert dates == sorted(dates, reverse=True)
    assert all(g["categorie_finale"] in n.LETTRES | {"?"} for g in gardees)
    assert all(float(g["montant_gbp"]) > 0 for g in gardees)
    for g in gardees:
        possibles = g["categories_possibles"].split("|")
        if g["categorie_finale"] == "?":
            assert len(possibles) >= 2 and set(possibles) <= n.LETTRES, g
        else:
            assert possibles == [g["categorie_finale"]], g
    libelles = {l["libelle"] for l in toutes}
    assert not libelles & {"MISS D WU", "SHEILA SMITH", "R LAWRENCE"}
