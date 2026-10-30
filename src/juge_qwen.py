"""Juge lu dans Qwen (brique 4) : catégorie A–E et score de confiance.

On demande à Qwen une seule lettre, réflexion désactivée, et on lit les
probabilités (logprobs) des cinq lettres sur ce premier token.

Attention : le score est la probabilité de la lettre **renormalisée parmi les
cinq lettres** A–E. C'est un score de décision, pas une probabilité calibrée :
les autres tokens possibles sont écartés. On garde leur masse (`masse_hors_lettres`)
pour savoir quand ce score n'est pas fiable.

Usage : python src/juge_qwen.py "J'ai payé 35 € chez Carrefour"
"""
import json
import math
import sys
import urllib.request

URL_OLLAMA = "http://localhost:11434/api/chat"
MODELE = "qwen3.5:4b-q4_K_M"
LETTRES = ("A", "B", "C", "D", "E")
SEUIL = 0.90

PROMPT_SYSTEME = """Tu classes une dépense d'étudiant dans une catégorie.
A = Alimentation (courses, supermarché, restaurant, livraison de repas)
B = Transport (transports en commun, VTC, taxi, essence, train, avion)
C = Logement (loyer, énergie, eau, internet du logement, meubles, assurance habitation)
D = Loisirs (cinéma, concert, bar, abonnements de divertissement, sport, hôtel de vacances)
E = Autres (santé, téléphone, vêtements, hygiène, cadeaux, fournitures, frais bancaires)
Réponds par une seule lettre : A, B, C, D ou E."""


def interroger_qwen(texte, url=URL_OLLAMA, modele=MODELE):
    """Envoie la dépense à Qwen et renvoie la réponse brute d'Ollama."""
    corps = {
        "model": modele,
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEME},
            {"role": "user", "content": texte},
        ],
        "think": False,
        "stream": False,
        "logprobs": True,
        "top_logprobs": 20,
        # Le modèle Ollama a presence_penalty = 1,5 par défaut : elle pénalise les
        # lettres déjà écrites dans le prompt APRÈS le calcul des logprobs, si bien
        # que Qwen peut renvoyer une lettre qui n'est pas la plus probable. On la coupe.
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 1,
                    "presence_penalty": 0, "repeat_penalty": 1.0},
    }
    requete = urllib.request.Request(
        url, json.dumps(corps).encode("utf-8"), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(requete, timeout=300) as reponse:
        return json.load(reponse)


def lire_scores(reponse):
    """Extrait la lettre renvoyée et le score des cinq lettres.

    Renvoie un dict :
    - token_renvoye : le token réellement produit par Qwen ;
    - lettre : ce token s'il est une des cinq lettres, sinon None ;
    - scores : probabilités des lettres renormalisées sur A–E (somme = 1) ;
    - lettres_manquantes : lettres absentes des top_logprobs ;
    - masse_hors_lettres : probabilité laissée aux autres tokens (<think>, F…) ;
    - coherent : la lettre renvoyée est bien celle qui a le meilleur score ;
    - valide : True seulement si le score est utilisable (lettre renvoyée et cohérente).
    """
    premier = reponse["logprobs"][0]
    token_renvoye = premier["token"]
    lettre = token_renvoye.strip() if token_renvoye.strip() in LETTRES else None

    # « A » et « A » précédé d'un espace sont deux tokens différents : on les additionne.
    probas = dict.fromkeys(LETTRES, 0.0)
    for candidat in premier["top_logprobs"]:
        cle = candidat["token"].strip()
        if cle in probas:
            probas[cle] += math.exp(candidat["logprob"])

    manquantes = [l for l in LETTRES if probas[l] == 0.0]
    masse_lettres = sum(probas.values())
    scores = {l: p / masse_lettres for l, p in probas.items()} if masse_lettres > 0 else probas

    coherent = lettre is not None and masse_lettres > 0 and lettre == max(scores, key=scores.get)

    return {
        "token_renvoye": token_renvoye,
        "lettre": lettre,
        "scores": scores,
        "lettres_manquantes": manquantes,
        "masse_hors_lettres": 1.0 - masse_lettres,
        "coherent": coherent,
        "valide": coherent,
    }


def decider(lecture, seuil=SEUIL):
    """« auto » si la lettre renvoyée a un score ≥ seuil, sinon « confirmer ».

    Une réponse invalide (token qui n'est pas une lettre, ou lettre qui n'est pas
    la plus probable) demande toujours confirmation.
    """
    if not lecture["valide"]:
        return "confirmer"
    return "auto" if lecture["scores"][lecture["lettre"]] >= seuil else "confirmer"


def main(argv):
    texte = " ".join(argv[1:]) or "J'ai payé 35 € chez Carrefour"
    lecture = lire_scores(interroger_qwen(texte))
    print(f"Dépense : {texte}")
    print(f"Token renvoyé : {lecture['token_renvoye']!r}  (valide : {lecture['valide']})")
    for l in LETTRES:
        print(f"  {l} : {lecture['scores'][l]:.3f}")
    print(f"Masse hors lettres : {lecture['masse_hors_lettres']:.4f}")
    print(f"Décision (seuil {SEUIL}) : {decider(lecture)}")


if __name__ == "__main__":
    main(sys.argv)
