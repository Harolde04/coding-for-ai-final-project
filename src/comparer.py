"""Comparaison mesurée : mon système face à Qwen seul (brique 9).

Tâches : les 40 cas de data/cas_etiquetes.csv (réponse connue).
Une tâche est réussie si :
- le montant retenu est exact, et
- cas clair (`auto`)       : enregistrement automatique dans la bonne catégorie ;
- cas ambigu (`confirmer`) : une confirmation est demandée.

Deux côtés, mêmes réglages (température 0,7, réflexion désactivée,
presence_penalty 0), N_LANCEMENTS lancements chacun :
- « qwen_seul »   : prompt nu (les 5 catégories, sans règles), réponse JSON
                    {montant, categorie, confirmation} ; Qwen décide de tout ;
- « systeme »     : juge par logprobs + seuil 0,90 (brique 4), règle G5 et montant
                    lu par Python (brique 3).

Usage :
  python src/comparer.py                 # interroge Qwen (≈ 10 minutes)
  python src/comparer.py --depuis-traces # recalcule à partir des traces
"""
import json
import statistics
import sys
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

import garde_fous
import juge_qwen
from evaluer_juge import charger_cas

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "resultats"
FICHIER_TRACES = DOSSIER / "traces_comparaison.jsonl"
FICHIER_RAPPORT = DOSSIER / "comparaison.md"
N_LANCEMENTS = 5
TEMPERATURE = 0.7
SYSTEMES = ("qwen_seul", "systeme")

PROMPT_SEUL = """Tu aides un étudiant à suivre ses dépenses.
Catégories : A = Alimentation, B = Transport, C = Logement, D = Loisirs, E = Autres.
Pour la dépense donnée, réponds en JSON avec :
- montant : le montant en euros ;
- categorie : la lettre de la catégorie ;
- confirmation : true si tu n'es pas sûr de la catégorie et qu'il faut demander à l'utilisateur, sinon false."""

FORMAT_SEUL = {
    "type": "object",
    "properties": {
        "montant": {"type": "number"},
        "categorie": {"type": "string", "enum": list(juge_qwen.LETTRES)},
        "confirmation": {"type": "boolean"},
    },
    "required": ["montant", "categorie", "confirmation"],
}


# --- Les deux côtés --------------------------------------------------------

def interroger_qwen_seul(texte):
    corps = {"model": juge_qwen.MODELE, "think": False, "stream": False, "format": FORMAT_SEUL,
             "messages": [{"role": "system", "content": PROMPT_SEUL}, {"role": "user", "content": texte}],
             "options": {"temperature": TEMPERATURE, "num_ctx": 4096, "presence_penalty": 0, "repeat_penalty": 1.0}}
    requete = urllib.request.Request(juge_qwen.URL_OLLAMA, json.dumps(corps).encode("utf-8"),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=300) as reponse:
        return json.load(reponse)["message"]["content"]


def decision_qwen_seul(sortie):
    """Lit la réponse JSON de Qwen seul → (decision, categorie, montant).

    Avec think=False, Ollama n'impose pas toujours `format` : Qwen entoure alors
    son JSON de balises Markdown (```json … ```). On lit l'objet entre la
    première « { » et la dernière « } » pour ne pas compter ça comme un échec.
    """
    try:
        donnees = json.loads(sortie[sortie.index("{"):sortie.rindex("}") + 1])
        montant = Decimal(str(donnees["montant"])).quantize(Decimal("0.01"))
        decision = "confirmer" if donnees["confirmation"] else "auto"
        return decision, donnees["categorie"], montant
    except (ValueError, KeyError, TypeError, InvalidOperation):  # ValueError : pas d'accolade ou JSON invalide
        return "invalide", None, None


def decision_systeme(texte, lecture):
    """Décision du système à partir de la lecture du juge → (decision, categorie, montant)."""
    try:
        montant = garde_fous.extraire_montant(texte)
    except garde_fous.EnregistrementRefuse:
        return "refuse", lecture["lettre"], None
    decision = garde_fous.decision_finale(texte, juge_qwen.decider(lecture))
    return decision, lecture["lettre"], montant


# --- Notation --------------------------------------------------------------

def noter(cas, decision, categorie, montant):
    """True si la tâche est réussie (voir la docstring du module)."""
    if montant is None or montant != Decimal(cas["montant_attendu"]):
        return False
    if cas["decision_attendue"] == "confirmer":
        return decision == "confirmer"
    return decision == "auto" and categorie == cas["categorie_attendue"]


def resumer(taux):
    return {"moyenne": statistics.mean(taux), "ecart_type": statistics.stdev(taux) if len(taux) > 1 else 0.0,
            "min": min(taux), "max": max(taux)}


# --- Lancement et rapport --------------------------------------------------

def lancer(cas_liste):
    lignes = []
    with open(FICHIER_TRACES, "w", encoding="utf-8") as traces:
        for lancement in range(1, N_LANCEMENTS + 1):
            for cas in cas_liste:
                sortie = interroger_qwen_seul(cas["texte"])
                lecture = juge_qwen.lire_scores(juge_qwen.interroger_qwen(cas["texte"], temperature=TEMPERATURE))
                for systeme, brut, (decision, categorie, montant) in (
                    ("qwen_seul", sortie, decision_qwen_seul(sortie)),
                    ("systeme", lecture, decision_systeme(cas["texte"], lecture)),
                ):
                    ligne = {"lancement": lancement, "systeme": systeme, "id": cas["id"], "texte": cas["texte"],
                             "sortie_brute": brut, "decision": decision, "categorie": categorie,
                             "montant": str(montant) if montant is not None else None,
                             "reussi": noter(cas, decision, categorie, montant)}
                    traces.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                    lignes.append(ligne)
            print(f"lancement {lancement}/{N_LANCEMENTS} terminé")
    return lignes


def charger_traces(cas_liste):
    """Relit les traces et recalcule décision et réussite à partir des sorties brutes,
    pour qu'une correction du lecteur ou de la notation ne demande pas de relancer Qwen."""
    cas_par_id = {cas["id"]: cas for cas in cas_liste}
    lignes = []
    with open(FICHIER_TRACES, encoding="utf-8") as f:
        for brut in f:
            ligne = json.loads(brut)
            cas = cas_par_id[ligne["id"]]
            if ligne["systeme"] == "qwen_seul":
                decision, categorie, montant = decision_qwen_seul(ligne["sortie_brute"])
            else:
                decision, categorie, montant = decision_systeme(cas["texte"], ligne["sortie_brute"])
            ligne.update(decision=decision, categorie=categorie,
                         montant=str(montant) if montant is not None else None,
                         reussi=noter(cas, decision, categorie, montant))
            lignes.append(ligne)
    return lignes


def taux_par_lancement(lignes, systeme, ids=None):
    taux = []
    for lancement in range(1, N_LANCEMENTS + 1):
        choisies = [l for l in lignes if l["systeme"] == systeme and l["lancement"] == lancement
                    and (ids is None or l["id"] in ids)]
        taux.append(sum(l["reussi"] for l in choisies) / len(choisies))
    return taux


def ecrire_rapport(cas_liste, lignes):
    ids_auto = {c["id"] for c in cas_liste if c["decision_attendue"] == "auto"}
    ids_conf = {c["id"] for c in cas_liste if c["decision_attendue"] == "confirmer"}
    texte = ["# Comparaison mesurée — brique 9", "",
             f"Modèle : `{juge_qwen.MODELE}`. {len(cas_liste)} tâches, {N_LANCEMENTS} lancements par côté, "
             f"température {TEMPERATURE}. Fichier généré par `python src/comparer.py`.", "",
             "## Taux de réussite par lancement", "",
             "| Côté | Tâches | Moyenne | Écart-type | Min | Max |", "|---|---|---|---|---|---|"]
    for systeme in SYSTEMES:
        for nom, ids in (("toutes (40)", None), ("claires (30)", ids_auto), ("ambiguës (10)", ids_conf)):
            r = resumer(taux_par_lancement(lignes, systeme, ids))
            texte.append(f"| {systeme} | {nom} | {r['moyenne']:.1%} | {r['ecart_type']:.1%} "
                         f"| {r['min']:.1%} | {r['max']:.1%} |")

    texte += ["", f"## Réussites par tâche (sur {N_LANCEMENTS} lancements)", "",
              "| id | Texte | Attendu | Qwen seul | Système |", "|---|---|---|---|---|"]
    for cas in cas_liste:
        compte = {s: sum(l["reussi"] for l in lignes if l["systeme"] == s and l["id"] == cas["id"]) for s in SYSTEMES}
        attendu = cas["categorie_attendue"] if cas["decision_attendue"] == "auto" else "confirmer"
        texte.append(f"| {cas['id']} | {cas['texte']} | {attendu} | {compte['qwen_seul']}/{N_LANCEMENTS} "
                     f"| {compte['systeme']}/{N_LANCEMENTS} |")

    montants_faux = sum(1 for l in lignes if l["systeme"] == "qwen_seul" and l["montant"] is not None
                        and Decimal(l["montant"]) != Decimal(next(c["montant_attendu"] for c in cas_liste if c["id"] == l["id"])))
    invalides = sum(1 for l in lignes if l["decision"] == "invalide")
    texte += ["", "## Contrôles", "",
              f"- Montants faux de Qwen seul : {montants_faux} sur {len(cas_liste) * N_LANCEMENTS}",
              f"- Réponses JSON invalides de Qwen seul : {invalides}", ""]
    FICHIER_RAPPORT.write_text("\n".join(texte), encoding="utf-8")


def main(argv):
    DOSSIER.mkdir(exist_ok=True)
    cas_liste = charger_cas()
    lignes = charger_traces(cas_liste) if "--depuis-traces" in argv else lancer(cas_liste)
    ecrire_rapport(cas_liste, lignes)
    for systeme in SYSTEMES:
        r = resumer(taux_par_lancement(lignes, systeme))
        print(f"{systeme:>10} : {r['moyenne']:.1%} ± {r['ecart_type']:.1%} (min {r['min']:.1%}, max {r['max']:.1%})")


if __name__ == "__main__":
    main(sys.argv)
