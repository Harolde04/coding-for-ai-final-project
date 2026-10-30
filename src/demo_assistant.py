"""Conversation de démonstration rejouable avec le vrai Qwen (preuve de la brique 1).

Usage : python src/demo_assistant.py

Repart d'un registre vide et écrit la trace complète dans
resultats/trace_demo_assistant.jsonl.
"""
from pathlib import Path

from assistant import RACINE, Assistant
from budget import Registre

FICHIER_TRACE = RACINE / "resultats" / "trace_demo_assistant.jsonl"
FICHIER_REGISTRE = RACINE / "resultats" / "registre_demo.json"

MESSAGES = [
    "Mon budget pour ce mois est de 600 €",
    "J'ai payé 35 € chez Carrefour",
    "Paiement PayPal 9,99 €",
    "J'ai payé -10 € au cinéma",
    "Combien il me reste ?",
]
# Réponses de l'utilisateur aux demandes de confirmation, dans l'ordre.
CONFIRMATIONS = ["D"]


def main():
    for fichier in (FICHIER_TRACE, FICHIER_REGISTRE):
        Path(fichier).unlink(missing_ok=True)
    confirmations = list(CONFIRMATIONS)

    def demander(question):
        reponse = confirmations.pop(0)
        print(f"  [confirmation] {question}{reponse}")
        return reponse

    assistant = Assistant(Registre(FICHIER_REGISTRE), demander=demander, fichier_trace=FICHIER_TRACE)
    for message in MESSAGES:
        print(f"\nVous : {message}")
        print(f"Assistant : {assistant.repondre(message)}")


if __name__ == "__main__":
    main()
