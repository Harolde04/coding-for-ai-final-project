"""Brique 3 : chaque test essaie d'enfreindre une règle et doit se faire bloquer."""
import csv
import sys
from decimal import Decimal
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

import garde_fous as g  # noqa: E402
from garde_fous import EnregistrementRefuse  # noqa: E402

with open(RACINE / "data" / "cas_etiquetes.csv", encoding="utf-8", newline="") as f:
    CAS = list(csv.DictReader(f, delimiter=";"))


def bloque(code, *args, **kwargs):
    with pytest.raises(EnregistrementRefuse) as erreur:
        g.verifier_enregistrement(*args, **kwargs)
    assert erreur.value.code == code, erreur.value


# --- Lecture du montant dans le texte -------------------------------------

@pytest.mark.parametrize("cas", CAS, ids=lambda c: c["id"])
def test_montant_lu_dans_les_40_cas(cas):
    assert g.extraire_montant(cas["texte"]) == Decimal(cas["montant_attendu"])


@pytest.mark.parametrize("texte, attendu", [
    ("Loyer 1 200 €", "1200.00"),
    ("Loyer 1 200 €", "1200.00"),   # espace insécable
    ("Café 2 EUR", "2.00"),
    ("Kebab 9€50", "9.50"),
])
def test_formats_de_montant(texte, attendu):
    assert g.extraire_montant(texte) == Decimal(attendu)


# --- G1 : jamais de montant invalide -------------------------------------

@pytest.mark.parametrize("texte", [
    "Remboursement reçu -10 €",          # négatif
    "Échantillon gratuit 0 €",           # nul
    "J'ai pris un café",                 # absent
    "Courses pour douze euros",          # en lettres : non lu, donc absent
    "2 tickets à 1,90 € et un café 3 €", # deux montants : lequel ?
])
def test_g1_montant_du_texte_invalide(texte):
    bloque("G1", texte, "10", "A", "auto")


@pytest.mark.parametrize("montant_propose", [
    None, "", "   ", "douze", "NaN", "inf", "-35", "0", "35.001", True,
])
def test_g1_montant_propose_invalide(montant_propose):
    bloque("G1", "J'ai payé 35 € chez Carrefour", montant_propose, "A", "auto")


# --- G2 : jamais un montant différent du texte ---------------------------

@pytest.mark.parametrize("montant_propose", ["53", "3.5", "350", 34.99])
def test_g2_montant_different_du_texte(montant_propose):
    bloque("G2", "J'ai payé 35 € chez Carrefour", montant_propose, "A", "auto")


@pytest.mark.parametrize("montant_propose", ["35", "35,00", 35, Decimal("35.0")])
def test_g2_meme_montant_sous_une_autre_forme_accepte(montant_propose):
    depense = g.verifier_enregistrement("J'ai payé 35 € chez Carrefour", montant_propose, "A", "auto")
    assert depense["montant"] == Decimal("35.00")


# --- G3 : jamais de catégorie hors A–E -----------------------------------

@pytest.mark.parametrize("categorie", ["F", "?", "a", "Alimentation", "", None])
def test_g3_categorie_inventee(categorie):
    bloque("G3", "J'ai payé 35 € chez Carrefour", "35", categorie, "auto")


# --- G4 : jamais sans confirmation quand le juge hésite ------------------

def test_g4_juge_hesitant_sans_confirmation():
    bloque("G4", "Amazon 25 €", "25", "E", "confirmer")


def test_g4_juge_hesitant_puis_utilisateur_confirme():
    depense = g.verifier_enregistrement("Amazon 25 €", "25", "E", "confirmer", confirme_par_utilisateur=True)
    assert depense["categorie"] == "E"


# --- G5 : jamais de transfert enregistré automatiquement -----------------

@pytest.mark.parametrize("texte, montant", [
    ("Paiement PayPal 9,99 €", "9.99"),          # raté réel de la brique 4 (score 0,953)
    ("Virement Lydia à Thomas 15 €", "15"),
    ("J'ai remboursé Julie 20 € pour samedi", "20"),
    ("Viré 30 € à Paul", "30"),
])
def test_g5_transfert_avec_juge_sur_de_lui(texte, montant):
    bloque("G5", texte, montant, "E", "auto")


def test_g5_transfert_confirme_par_utilisateur_accepte():
    depense = g.verifier_enregistrement("Paiement PayPal 9,99 €", "9.99", "D", "auto", confirme_par_utilisateur=True)
    assert depense["categorie"] == "D"


def test_decision_finale_ecrase_le_juge_sur_un_transfert():
    assert g.decision_finale("Paiement PayPal 9,99 €", "auto") == "confirmer"
    assert g.decision_finale("Ticket de bus 1,90€", "auto") == "auto"


# --- Le chemin normal reste ouvert ---------------------------------------

def test_depense_claire_enregistree():
    depense = g.verifier_enregistrement("J'ai payé 35 € chez Carrefour", "35", "A", "auto")
    assert depense == {"texte": "J'ai payé 35 € chez Carrefour", "montant": Decimal("35.00"), "categorie": "A"}
