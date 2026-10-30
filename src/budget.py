"""Registre des dépenses et calcul du budget (brique 1).

Tous les calculs sont faits ici, en Decimal, jamais par le modèle.
Le registre est un fichier JSON local (`donnees/registre.json`, hors du dépôt :
ce sont des données personnelles).
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import garde_fous

RACINE = Path(__file__).resolve().parent.parent
FICHIER_REGISTRE = RACINE / "donnees" / "registre.json"

NOMS = {"A": "Alimentation", "B": "Transport", "C": "Logement", "D": "Loisirs", "E": "Autres"}


class Registre:
    def __init__(self, chemin=FICHIER_REGISTRE):
        self.chemin = Path(chemin)
        if self.chemin.exists():
            contenu = json.loads(self.chemin.read_text(encoding="utf-8"))
        else:
            contenu = {"budget_mensuel": None, "depenses": []}
        self.budget_mensuel = contenu["budget_mensuel"]
        self.depenses = contenu["depenses"]

    def sauvegarder(self):
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        contenu = {"budget_mensuel": self.budget_mensuel, "depenses": self.depenses}
        self.chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")

    def definir_budget(self, montant):
        """Fixe le budget mensuel. Un budget négatif, nul ou non numérique est refusé (G1)."""
        self.budget_mensuel = str(garde_fous.valider_montant(montant))
        self.sauvegarder()
        return self.budget_mensuel

    def ajouter(self, depense, confirme_par_utilisateur, jour=None):
        """Ajoute une dépense déjà validée par garde_fous.verifier_enregistrement."""
        self.depenses.append({
            "date": (jour or date.today()).isoformat(),
            "texte": depense["texte"],
            "montant": str(depense["montant"]),
            "categorie": depense["categorie"],
            "confirme_par_utilisateur": confirme_par_utilisateur,
        })
        self.sauvegarder()

    def bilan(self, mois=None):
        """Total, total par catégorie et budget restant pour un mois (« 2026-10 »),
        par défaut le mois en cours."""
        mois = mois or date.today().isoformat()[:7]
        du_mois = [d for d in self.depenses if d["date"].startswith(mois)]
        par_categorie = {lettre: Decimal("0.00") for lettre in NOMS}
        for d in du_mois:
            par_categorie[d["categorie"]] += Decimal(d["montant"])
        total = sum(par_categorie.values(), Decimal("0.00"))
        restant = Decimal(self.budget_mensuel) - total if self.budget_mensuel else None
        return {
            "mois": mois,
            "nombre_depenses": len(du_mois),
            "total": str(total),
            "par_categorie": {f"{l} {NOMS[l]}": str(v) for l, v in par_categorie.items() if v},
            "budget_mensuel": self.budget_mensuel,
            "budget_restant": str(restant) if restant is not None else None,
        }
