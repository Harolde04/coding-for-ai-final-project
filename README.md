# Assistant intelligent de gestion des dépenses étudiantes

Un assistant qui comprend une dépense écrite en langage naturel
(« J'ai payé 35 € chez Carrefour »), la classe dans une catégorie, demande
une confirmation quand il n'est pas sûr, et calcule en Python le total des
dépenses et le budget restant. Le modèle de langage propose ; le code vérifie.

Projet final du cours *Coding for AI & Data Science* (PGE3, 2026–2027).
Modèle : Qwen3.5-4B (Q4_K_M) en local. Briques choisies : 1, 3, 4, 6 et 9
(détail et preuves dans [EVIDENCE.md](EVIDENCE.md)).

## Catégories

| Lettre | Catégorie |
|---|---|
| A | Alimentation |
| B | Transport |
| C | Logement |
| D | Loisirs |
| E | Autres |

Les règles de classement sont dans [REGLES_METIER.md](REGLES_METIER.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Modèle

Installer [Ollama](https://ollama.com), puis :

```bash
ollama pull qwen3.5:4b-q4_K_M
python src/juge_qwen.py "J'ai payé 35 € chez Carrefour"
```

Le juge renvoie une catégorie, son score et la décision (`auto` si le score
est ≥ 0,90, sinon `confirmer`). Évaluation sur les 40 cas étiquetés :

```bash
python src/evaluer_juge.py
```

## Utiliser l'assistant

```bash
python src/assistant.py
```

Exemple : « Mon budget pour ce mois est de 600 € », puis
« J'ai payé 35 € chez Carrefour », puis « Combien il me reste ? ».
Les dépenses sont gardées dans `donnees/registre.json` (hors du dépôt).
Conversation de démonstration rejouable : `python src/demo_assistant.py`.

## Données réelles (brique 6)

Le fichier brut n'est pas dans le dépôt : il contient des noms de particuliers.

1. Ouvrir https://data.mendeley.com/datasets/dnxtg6n4rv/1
   (Firat, Vytia, Vasudeva, Jiang, Laramee, EuroVis 2023 — licence CC BY 4.0).
2. Télécharger `laramee26openBankTransactionData.xlsx`.
3. Le placer à la racine du projet, puis lancer :

```bash
python src/nettoyage_moneydata.py
```

Le script produit `data/moneydata_propre.csv`, `data/moneydata_exclus.csv`
et `data/journal_nettoyage.md`. Ces trois fichiers sont déjà dans le dépôt
(noms de particuliers remplacés par des pseudonymes).

## Tests

```bash
python -m pytest
```

Sans le fichier brut, le test de bout en bout du nettoyage est sauté ;
tous les autres tournent.

## Organisation

| Chemin | Contenu |
|---|---|
| `REGLES_METIER.md` | règles de classement, citées par chaque étiquette |
| `data/cas_etiquetes.csv` | 40 cas étiquetés à la main (briques 4 et 9) |
| `data/correspondance_categories.csv` | catégories MoneyData → A–E |
| `data/regles_commercants.csv` | corrections fondées sur le commerçant |
| `src/nettoyage_moneydata.py` | nettoyage des données réelles |
| `tests/` | tests pytest |
