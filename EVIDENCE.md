# Preuves par brique

## Brique 1 — Votre propre outil

*À venir.*

## Brique 3 — Une règle imposée par le code

**Ce que je montre.** Cinq choses que le système ne doit jamais faire, bloquées
par `src/garde_fous.py` et non par le prompt. Toute dépense passe par
`verifier_enregistrement`, qui lève `EnregistrementRefuse` avec le code de la
règle enfreinte. Chaque règle a des tests qui essaient de l'enfreindre.

| Règle | Jamais… | Exemples d'attaques bloquées (tests) |
|---|---|---|
| G1 | un montant invalide | `-10 €`, `0 €`, pas de montant, « douze euros », deux montants, montant proposé `"NaN"`, `"inf"`, `"35.001"`, `None` |
| G2 | un montant différent de celui du texte | texte « 35 € », modèle propose `53`, `350`, `34.99` |
| G3 | une catégorie hors A–E | `"F"`, `"?"`, `"Alimentation"`, `None` |
| G4 | enregistrer sans confirmation quand le juge hésite | « Amazon 25 € », décision `confirmer`, pas de confirmation |
| G5 | enregistrer automatiquement un virement ou paiement par intermédiaire | « Paiement PayPal 9,99 € » avec décision `auto` |

**Le montant est lu par Python, pas par Qwen.** `extraire_montant` lit le
montant en euros dans le texte (« 3,30 € », « 9€50 », « 18,90 euros »,
« 1 200 € ») et refuse s'il n'y en a pas exactement un. Testé sur les 40 cas
étiquetés : 40 montants lus correctement.

**Effet mesuré sur les 40 cas** (`resultats/evaluation_juge.md`, mêmes traces
que la brique 4) : au seuil 0,90, Qwen seul fait 1 raté (« Paiement PayPal
9,99 € », score 0,953) ; avec G5, 0 raté, sans fausse alerte de plus. Au seuil
0,80 : 5 ratés → 2.

**Limite.** Les mots-clés de G5 (Lydia, PayPal, virement, rembours…) ont été
choisis en connaissant les 40 cas : le gain mesuré est optimiste. Une dépense
mixte (« courses et essence », R-X3) n'est pas couverte par le code.

**Fichiers.** `src/garde_fous.py`, `tests/test_garde_fous.py`,
`src/evaluer_juge.py` (option `avec_regles`), `tests/test_evaluer_juge.py`.

**Commande pour reproduire.**

```bash
python -m pytest tests/test_garde_fous.py -v
python src/evaluer_juge.py --depuis-traces
```

## Brique 4 — Un modèle de décision

**Ce que je montre.** Un juge lu dans Qwen3.5-4B : un score par catégorie,
un seuil choisi à partir des mesures, et ses ratés et fausses alertes sur
40 cas étiquetés à la main.

**Le score.** Qwen répond par une seule lettre A–E (réflexion désactivée,
température 0). On lit les logprobs des cinq lettres sur ce premier token et on
les renormalise sur A–E. C'est un score de décision, **pas une probabilité
calibrée** : les autres tokens sont écartés (au plus 5,7 % de la masse sur les
40 cas). Le code vérifie avant d'utiliser le score que le token renvoyé est une
lettre et qu'il est bien la lettre la plus probable ; sinon : confirmation.

**Un défaut trouvé en testant.** Le modèle Ollama applique par défaut
`presence_penalty = 1.5`, après le calcul des logprobs : Qwen renvoyait « A »
pour « Amazon 25 € » alors que ses logprobs donnaient E à 0,65 contre A à 0,26.
Pénalité mise à 0, et contrôle de cohérence ajouté
(`test_lettre_renvoyee_qui_n_est_pas_la_plus_probable_est_invalide`).

**Les cas étiquetés.** `data/cas_etiquetes.csv` : 40 cas (30 clairs `auto`,
10 ambigus `confirmer`), chacun justifié par une règle de `REGLES_METIER.md`.
- Raté : enregistrement automatique d'un cas ambigu, ou dans la mauvaise catégorie.
- Fausse alerte : demande de confirmation sur un cas clair.

**Résultats** (`resultats/evaluation_juge.md`, 1 lancement par cas) :

| Seuil | Ratés : ambigu enregistré | Ratés : mauvaise catégorie | Fausses alertes |
|---|---|---|---|
| 0,70 | 6 / 10 | 2 | 3 / 30 |
| 0,80 | 4 / 10 | 1 | 8 / 30 |
| **0,90 (retenu)** | **1 / 10** | **0** | **10 / 30** |
| 0,95 | 1 / 10 | 0 | 15 / 30 |

**Choix du seuil : 0,90.** Le seuil prévu au départ était 0,80. Je l'ai remonté
après la mesure : un raté fausse le budget en silence, une fausse alerte coûte
un clic. Passer de 0,80 à 0,90 retire 4 ratés pour 2 fausses alertes de plus ;
au-delà, 0,95 ajoute 5 fausses alertes sans retirer de raté.

**Le raté restant.** « Paiement PayPal 9,99 € » : Qwen répond E avec 0,953.
Le score mesure l'hésitation entre lettres, pas l'absence d'information : Qwen
ne peut pas répondre « je ne sais pas ». Ce cas relève d'une règle imposée par
le code (brique 3), pas d'un seuil.

**Limites.** Le seuil est choisi sur les mêmes 40 cas que ceux qui le mesurent :
le résultat est optimiste. Avec 10 cas ambigus, un écart d'un ou deux ratés
reste fragile.

**Fichiers.** `src/juge_qwen.py`, `src/evaluer_juge.py`,
`resultats/traces_juge.jsonl` (réponse brute de Qwen par cas),
`resultats/evaluation_juge.md`, `tests/test_juge_qwen.py`, `tests/test_evaluer_juge.py`.

**Commandes pour reproduire** (Ollama lancé, `ollama pull qwen3.5:4b-q4_K_M`) :

```bash
python src/evaluer_juge.py                  # interroge Qwen, environ 1 minute
python src/evaluer_juge.py --depuis-traces  # recalcule sans Qwen
python -m pytest tests/test_juge_qwen.py tests/test_evaluer_juge.py
```

## Brique 6 — Données sales, décisions écrites

**Ce que je montre.** De vraies transactions bancaires, nettoyées par un script,
avec un journal qui compte chaque ligne retirée, chaque valeur convertie et
chaque libellé corrigé, et une colonne qui distingue la donnée connue de la
donnée corrigée.

**Les données.** MoneyData : 6 567 transactions réelles et anonymisées d'un
compte bancaire britannique (2015–2022). Firat, Vytia, Vasudeva, Jiang,
Laramee, *MoneyVis: Open Bank Transaction Data for Visualization and Beyond*,
EuroVis 2023 — Mendeley Data 10.17632/dnxtg6n4rv.1, licence CC BY 4.0.

**Ce que le nettoyage a trouvé et corrigé** (comptes dans `data/journal_nettoyage.md`) :

| Problème | Lignes | Décision |
|---|---|---|
| Dates Excel avec jour et mois inversés (« 12/07/2022 » lu comme le 7 décembre) | 2 816 | remises en ordre ; vérifié : les dates suivent alors exactement l'ordre des numéros de transaction |
| Épargne, placements, crédits, retraits d'espèces | 2 325 | exclues avec leur motif (R-N1 à R-N4) → `data/moneydata_exclus.csv` |
| Catégories des auteurs mélangées (Bills, Other Shopping, Insurance…) | — | reclassées ligne par ligne d'après le commerçant (`data/regles_commercants.csv`) |
| Erreurs d'étiquetage des auteurs (PLUSNET en Entertainment, un bar en Dine Out…) | — | corrigées, provenance `commercant` |
| Catégorie avec espace final, catégories vides, types vides | 5 / 24 / 61 | normalisées |
| Noms de particuliers dans les libellés | 46 personnes | remplacés par `PARTICULIER_nnn` |

**Donnée connue ou corrigée.** Chaque dépense gardée porte une `provenance` :
`origine` (catégorie des auteurs), `commercant` (notre correction, fondée sur
le nom du commerçant, pas sur une information de la banque) ou `non_identifie`
(`?`, avec les `categories_possibles` à proposer à l'utilisateur).

**Règle que le fichier ne dit pas, et sa source : R-E6 (document Lloyds Bank).**
Le fichier classe les 43 prélèvements `ASSURANT INTER LTD` en « Insurance »,
sans dire de quelle assurance il s'agit (habitation → C, ou autre → E).
La page « Gadget insurance » de Lloyds Bank
(https://www.lloydsbank.com/current-accounts/packaged-bank-accounts/gadget-insurance.html,
consultée le 30/10/2026) indique qu'Assurant General Insurance Limited fournit
l'assurance téléphone mobile des comptes packagés Lloyds. Le compte MoneyData
est un compte Club Lloyds Silver (frais `CLUB LLOYDS FEE`, `SILVER ACCOUNT`) :
ces 43 lignes passent donc de `?` à E. Limite assumée : la page est actuelle
et les prélèvements datent de 2015–2019, avec des montants différents des
tarifs actuels. Le document établit ce que vend Assurant, pas le contrat exact
de ce client. Faute de document équivalent, les 28 lignes `ZURICH` restent en
`?` (R-X6). Test : `test_classement_connu` et `test_regle_et_categories_possibles`.

**Fichiers.** `src/nettoyage_moneydata.py`, `data/correspondance_categories.csv`,
`data/regles_commercants.csv`, `REGLES_METIER.md`, `data/journal_nettoyage.md`,
`data/moneydata_propre.csv`, `data/moneydata_exclus.csv`,
`tests/test_nettoyage_moneydata.py`.

**Commande pour reproduire** (après avoir téléchargé le fichier brut, voir README) :

```bash
python src/nettoyage_moneydata.py
python -m pytest tests/test_nettoyage_moneydata.py
```

## Brique 9 — Une comparaison mesurée

*À venir.*
