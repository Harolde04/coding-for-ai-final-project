"""Évaluation du juge Qwen sur les 40 cas étiquetés (brique 4).

Usage :
  python src/evaluer_juge.py                 # interroge Qwen et enregistre les traces
  python src/evaluer_juge.py --depuis-traces # recalcule à partir des traces enregistrées

Produit :
- resultats/traces_juge.jsonl  : une ligne par cas, avec la réponse de Qwen
- resultats/evaluation_juge.md : ratés et fausses alertes pour plusieurs seuils

Définitions (REGLES_METIER.md, section « Comment ces règles alimentent la brique 4 ») :
- raté : le système enregistre automatiquement alors qu'il ne fallait pas,
  soit parce que le cas demandait une confirmation (raté « ambigu »),
  soit parce que la catégorie enregistrée est fausse (raté « catégorie ») ;
- fausse alerte : le système demande une confirmation sur un cas clair.
"""
import csv
import json
import sys
from pathlib import Path

import garde_fous
import juge_qwen

RACINE = Path(__file__).resolve().parent.parent
FICHIER_CAS = RACINE / "data" / "cas_etiquetes.csv"
DOSSIER_RESULTATS = RACINE / "resultats"
FICHIER_TRACES = DOSSIER_RESULTATS / "traces_juge.jsonl"
FICHIER_RAPPORT = DOSSIER_RESULTATS / "evaluation_juge.md"
SEUILS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99)


def charger_cas(chemin=FICHIER_CAS):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def issue(cas, lecture, seuil, avec_regles=False):
    """Classe le résultat d'un cas : « correct », « rate_ambigu », « rate_categorie »
    ou « fausse_alerte ». avec_regles : appliquer aussi les règles du code (brique 3)."""
    decision = juge_qwen.decider(lecture, seuil)
    if avec_regles:
        decision = garde_fous.decision_finale(cas["texte"], decision)
    if cas["decision_attendue"] == "confirmer":
        return "correct" if decision == "confirmer" else "rate_ambigu"
    if decision == "confirmer":
        return "fausse_alerte"
    return "correct" if lecture["lettre"] == cas["categorie_attendue"] else "rate_categorie"


def compter(cas_liste, lectures, seuil, avec_regles=False):
    comptes = dict.fromkeys(("correct", "rate_ambigu", "rate_categorie", "fausse_alerte"), 0)
    for cas, lecture in zip(cas_liste, lectures):
        comptes[issue(cas, lecture, seuil, avec_regles)] += 1
    comptes["rates"] = comptes["rate_ambigu"] + comptes["rate_categorie"]
    return comptes


def interroger_tous(cas_liste):
    lectures = []
    with open(FICHIER_TRACES, "w", encoding="utf-8") as traces:
        for cas in cas_liste:
            reponse = juge_qwen.interroger_qwen(cas["texte"])
            lecture = juge_qwen.lire_scores(reponse)
            trace = {"id": cas["id"], "texte": cas["texte"], "modele": reponse.get("model"),
                     "lecture": lecture, "logprobs_brutes": reponse["logprobs"][0]}
            traces.write(json.dumps(trace, ensure_ascii=False) + "\n")
            lectures.append(lecture)
            print(f"{cas['id']:>2} {lecture['token_renvoye']!r:>6} "
                  f"{lecture['scores'].get(lecture['lettre'] or 'A', 0):.3f}  {cas['texte']}")
    return lectures


def charger_traces():
    with open(FICHIER_TRACES, encoding="utf-8") as f:
        return [json.loads(ligne)["lecture"] for ligne in f]


def ecrire_rapport(cas_liste, lectures):
    n_auto = sum(c["decision_attendue"] == "auto" for c in cas_liste)
    n_conf = len(cas_liste) - n_auto
    lignes = [
        "# Évaluation du juge Qwen — brique 4", "",
        f"Modèle : `{juge_qwen.MODELE}`, réflexion désactivée, température 0, "
        f"1 lancement par cas. {len(cas_liste)} cas : {n_auto} `auto`, {n_conf} `confirmer`.",
        "Fichier généré par `python src/evaluer_juge.py`. Ne pas modifier à la main.", "",
        "## Ratés et fausses alertes selon le seuil", "",
        "| Seuil | Corrects | Ratés (ambigu enregistré) | Ratés (mauvaise catégorie) | Fausses alertes |",
        "|---|---|---|---|---|",
    ]
    for seuil in SEUILS:
        c = compter(cas_liste, lectures, seuil)
        marque = " ← seuil retenu" if seuil == juge_qwen.SEUIL else ""
        lignes.append(f"| {seuil:.2f}{marque} | {c['correct']} | {c['rate_ambigu']} / {n_conf} "
                      f"| {c['rate_categorie']} | {c['fausse_alerte']} / {n_auto} |")

    lignes += ["", "## Avec les règles imposées par le code (brique 3)", "",
               "La règle G5 de `src/garde_fous.py` impose une confirmation pour tout virement "
               "ou paiement par intermédiaire, quel que soit le score de Qwen.", "",
               "| Seuil | Qwen seul : ratés / fausses alertes | Qwen + règles du code : ratés / fausses alertes |",
               "|---|---|---|"]
    for seuil in SEUILS:
        seul = compter(cas_liste, lectures, seuil)
        regles = compter(cas_liste, lectures, seuil, avec_regles=True)
        lignes.append(f"| {seuil:.2f} | {seul['rates']} / {seul['fausse_alerte']} "
                      f"| {regles['rates']} / {regles['fausse_alerte']} |")

    lignes += ["", f"## Détail par cas (seuil {juge_qwen.SEUIL:.2f}, Qwen seul)", "",
               "| id | Texte | Attendu | Lettre Qwen | Score | Décision | Issue |",
               "|---|---|---|---|---|---|---|"]
    for cas, lecture in zip(cas_liste, lectures):
        attendu = cas["categorie_attendue"] if cas["decision_attendue"] == "auto" else "? (confirmer)"
        score = lecture["scores"][lecture["lettre"]] if lecture["lettre"] else 0.0
        lignes.append(f"| {cas['id']} | {cas['texte']} | {attendu} | {lecture['token_renvoye']} "
                      f"| {score:.3f} | {juge_qwen.decider(lecture)} | {issue(cas, lecture, juge_qwen.SEUIL)} |")

    invalides = [c["id"] for c, l in zip(cas_liste, lectures) if not l["valide"]]
    manquantes = [c["id"] for c, l in zip(cas_liste, lectures) if l["lettres_manquantes"]]
    masse_max = max(l["masse_hors_lettres"] for l in lectures)
    lignes += ["", "## Contrôles", "",
               f"- Réponses invalides (token hors A–E ou lettre incohérente) : {invalides or 'aucune'}",
               f"- Cas où une lettre manque dans les top_logprobs : {manquantes or 'aucun'}",
               f"- Masse maximale hors des cinq lettres : {masse_max:.4f}", ""]
    FICHIER_RAPPORT.write_text("\n".join(lignes), encoding="utf-8")


def main(argv):
    DOSSIER_RESULTATS.mkdir(exist_ok=True)
    cas_liste = charger_cas()
    lectures = charger_traces() if "--depuis-traces" in argv else interroger_tous(cas_liste)
    ecrire_rapport(cas_liste, lectures)
    for seuil in SEUILS:
        c = compter(cas_liste, lectures, seuil)
        r = compter(cas_liste, lectures, seuil, avec_regles=True)
        print(f"seuil {seuil:.2f} : {c['rates']} ratés ({c['rate_ambigu']} ambigus, "
              f"{c['rate_categorie']} catégorie), {c['fausse_alerte']} fausses alertes"
              f"  |  avec règles du code : {r['rates']} ratés, {r['fausse_alerte']} fausses alertes")


if __name__ == "__main__":
    main(sys.argv)
