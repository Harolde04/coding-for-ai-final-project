"""Assistant de budget : boucle d'agent avec outils (brique 1).

Qwen discute avec l'utilisateur et appelle trois outils écrits en Python :
- enregistrer_depense(montant, categorie)
- calculer_budget()
- definir_budget(montant)

Chaque étape (message, appel d'outil, résultat) est écrite dans une trace JSONL.

Usage : python src/assistant.py
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import garde_fous
import juge_qwen
from budget import NOMS, Registre

RACINE = Path(__file__).resolve().parent.parent
FICHIER_TRACE = RACINE / "resultats" / "traces_assistant.jsonl"
MAX_TOURS = 5

PROMPT_SYSTEME = """Tu es un assistant de budget pour un étudiant. Tu réponds en français, brièvement.
Catégories : A = Alimentation, B = Transport, C = Logement, D = Loisirs, E = Autres.
- Quand l'utilisateur décrit une dépense, appelle enregistrer_depense.
- Quand il demande son total, ses dépenses ou ce qu'il lui reste, appelle calculer_budget.
- Quand il donne son budget du mois, appelle definir_budget.
Ne calcule jamais toi-même : n'utilise que les chiffres renvoyés par les outils.
Si un outil refuse ou annule, explique-le à l'utilisateur sans inventer."""

OUTILS = [
    {"type": "function", "function": {
        "name": "enregistrer_depense",
        "description": "Enregistre la dépense que l'utilisateur vient de décrire.",
        "parameters": {"type": "object", "properties": {
            "montant": {"type": "number", "description": "montant en euros"},
            "categorie": {"type": "string", "enum": list(NOMS)},
        }, "required": ["montant", "categorie"]}}},
    {"type": "function", "function": {
        "name": "calculer_budget",
        "description": "Calcule le total des dépenses du mois, le total par catégorie et le budget restant.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "definir_budget",
        "description": "Fixe le budget mensuel de l'utilisateur.",
        "parameters": {"type": "object", "properties": {
            "montant": {"type": "number", "description": "budget du mois en euros"},
        }, "required": ["montant"]}}},
]


def appeler_ollama(messages, outils):
    corps = {"model": juge_qwen.MODELE, "messages": messages, "tools": outils, "think": False,
             "stream": False, "options": {"temperature": 0, "num_ctx": 8192}}
    requete = urllib.request.Request(juge_qwen.URL_OLLAMA, json.dumps(corps).encode("utf-8"),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=300) as reponse:
        return json.load(reponse)["message"]


def juger_avec_qwen(texte):
    return juge_qwen.lire_scores(juge_qwen.interroger_qwen(texte))


class Assistant:
    def __init__(self, registre, appeler_modele=appeler_ollama, juger=juger_avec_qwen,
                 demander=input, fichier_trace=FICHIER_TRACE):
        self.registre = registre
        self.appeler_modele = appeler_modele
        self.juger = juger
        self.demander = demander
        self.fichier_trace = Path(fichier_trace)
        self.messages = [{"role": "system", "content": PROMPT_SYSTEME}]
        self.dernier_message = ""

    # --- Trace ---------------------------------------------------------------

    def tracer(self, etape, **contenu):
        self.fichier_trace.parent.mkdir(parents=True, exist_ok=True)
        ligne = {"horodatage": datetime.now().isoformat(timespec="seconds"), "etape": etape, **contenu}
        with open(self.fichier_trace, "a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False, default=str) + "\n")

    # --- Outils --------------------------------------------------------------

    def enregistrer_depense(self, montant, categorie):
        # Le texte vient de l'utilisateur, pas du modèle : le modèle ne peut pas
        # réécrire la phrase pour faire passer un autre montant (règle G2).
        texte = self.dernier_message
        lecture = self.juger(texte)
        decision = garde_fous.decision_finale(texte, juge_qwen.decider(lecture))
        if categorie != lecture["lettre"]:
            decision = "confirmer"  # le modèle et le juge ne sont pas d'accord
        score = lecture["scores"].get(lecture["lettre"], 0.0) if lecture["lettre"] else 0.0
        self.tracer("juge", lettre=lecture["lettre"], score=round(score, 3),
                    regle_code=garde_fous.confirmation_obligatoire(texte), decision=decision)

        confirme = False
        if decision == "confirmer":
            proposee = categorie if categorie in NOMS else lecture["lettre"]
            reponse = self.demander(
                f"Je propose {proposee} ({NOMS.get(proposee, '?')}) pour « {texte} ». "
                "Entrée pour valider, une autre lettre A–E pour corriger, n pour annuler : "
            ).strip().upper()
            if reponse == "N":
                return {"statut": "annule", "motif": "l'utilisateur a annulé"}
            categorie = reponse if reponse in NOMS else proposee
            confirme = True

        try:
            depense = garde_fous.verifier_enregistrement(texte, montant, categorie, decision, confirme)
        except garde_fous.EnregistrementRefuse as refus:
            return {"statut": "refuse", "regle": refus.code, "motif": refus.motif}
        self.registre.ajouter(depense, confirme)
        return {"statut": "enregistre", "montant": str(depense["montant"]),
                "categorie": f"{categorie} {NOMS[categorie]}", "confirme_par_utilisateur": confirme}

    def calculer_budget(self):
        return self.registre.bilan()

    def definir_budget(self, montant):
        try:
            return {"statut": "budget_defini", "budget_mensuel": self.registre.definir_budget(montant)}
        except garde_fous.EnregistrementRefuse as refus:
            return {"statut": "refuse", "regle": refus.code, "motif": refus.motif}

    def executer_outil(self, nom, arguments):
        outils = {"enregistrer_depense": self.enregistrer_depense,
                  "calculer_budget": self.calculer_budget,
                  "definir_budget": self.definir_budget}
        if nom not in outils:
            return {"statut": "erreur", "motif": f"outil inconnu : {nom}"}
        try:
            return outils[nom](**arguments)
        except TypeError as erreur:  # arguments manquants ou en trop
            return {"statut": "erreur", "motif": str(erreur)}

    # --- Boucle --------------------------------------------------------------

    def repondre(self, message):
        self.dernier_message = message
        self.messages.append({"role": "user", "content": message})
        self.tracer("utilisateur", contenu=message)
        for _ in range(MAX_TOURS):
            reponse = self.appeler_modele(self.messages, OUTILS)
            self.messages.append(reponse)
            appels = reponse.get("tool_calls") or []
            if not appels:
                self.tracer("modele", contenu=reponse.get("content", ""))
                return reponse.get("content", "")
            for appel in appels:
                nom, arguments = appel["function"]["name"], appel["function"].get("arguments") or {}
                self.tracer("appel_outil", outil=nom, arguments=arguments)
                resultat = self.executer_outil(nom, arguments)
                self.tracer("resultat_outil", outil=nom, resultat=resultat)
                self.messages.append({"role": "tool", "tool_name": nom,
                                      "content": json.dumps(resultat, ensure_ascii=False)})
        self.tracer("arret", motif=f"plus de {MAX_TOURS} tours sans réponse")
        return "Désolé, je n'ai pas réussi à traiter cette demande."


def main():
    assistant = Assistant(Registre())
    print("Assistant budget (Qwen3.5-4B). Tapez « quitter » pour sortir.")
    while True:
        message = input("\nVous : ").strip()
        if message.lower() in {"quitter", "exit", "q"}:
            break
        if message:
            print(f"Assistant : {assistant.repondre(message)}")


if __name__ == "__main__":
    main()
