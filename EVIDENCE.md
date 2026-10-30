# Preuves par brique

## Brique 1 — Votre propre outil

**Ce que je montre.** Une boucle d'agent écrite à la main (`src/assistant.py`)
dans laquelle Qwen3.5-4B appelle trois outils Python que j'ai écrits, avec la
trace d'une vraie conversation : chaque appel, ses arguments et son résultat.

| Outil | Ce que fait le code |
|---|---|
| `enregistrer_depense(montant, categorie)` | relit le **message de l'utilisateur** (pas un texte réécrit par le modèle), interroge le juge (brique 4), demande confirmation si besoin, puis passe par les garde-fous G1–G5 (brique 3) avant d'écrire dans le registre |
| `calculer_budget()` | total, total par catégorie et budget restant du mois, calculés en `Decimal` par `src/budget.py` |
| `definir_budget(montant)` | fixe le budget mensuel ; un budget négatif est refusé (G1) |

Le modèle ne fait aucun calcul : le prompt le lui interdit, et surtout les
chiffres qu'il annonce viennent du résultat de `calculer_budget`.
Si le modèle de chat et le juge ne proposent pas la même catégorie, l'outil
demande une confirmation.

**Trace d'une vraie conversation** (`resultats/trace_demo_assistant.jsonl`) :

| Utilisateur | Appel d'outil par Qwen | Ce que fait le code | Résultat |
|---|---|---|---|
| « Mon budget pour ce mois est de 600 € » | `definir_budget(montant=600)` | — | budget 600.00 |
| « J'ai payé 35 € chez Carrefour » | `enregistrer_depense(montant=35, categorie="A")` | juge : A à 0,994 → `auto` | enregistré, sans question |
| « Paiement PayPal 9,99 € » | `enregistrer_depense(montant=9.99, categorie="E")` | juge : E à 0,953, mais G5 (PayPal) → confirmation ; l'utilisateur corrige en D | enregistré en D, confirmé |
| « J'ai payé -10 € au cinéma » | `enregistrer_depense(montant=-10, categorie="D")` | G1 | **refusé** : montant négatif |
| « Combien il me reste ? » | `calculer_budget()` | Python : 600 − 44,99 | restant **555.01** |

Réponse finale de Qwen : « Il vous reste 555,01 € sur votre budget de 600 €.
Vous avez dépensé un total de 44,99 €, soit 35 € pour l'alimentation et
9,99 € pour les loisirs. » — chiffres identiques au résultat de l'outil.

**Tests** (`tests/test_assistant.py`, avec un faux modèle qui rejoue des
réponses au format d'Ollama) : calcul du budget, registre qui survit à un
redémarrage, montant changé par le modèle refusé (G2), désaccord modèle/juge,
transfert, annulation, outil inconnu, arrêt après 5 tours, contenu de la trace.

**Fichiers.** `src/assistant.py`, `src/budget.py`, `src/demo_assistant.py`,
`resultats/trace_demo_assistant.jsonl`, `tests/test_assistant.py`.

**Commandes pour reproduire** (Ollama lancé) :

```bash
python src/demo_assistant.py   # conversation rejouable, réécrit la trace
python src/assistant.py        # conversation libre
python -m pytest tests/test_assistant.py
```

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

**Ce que je montre.** Mon système face à Qwen seul, sur 40 tâches à réponse
connue, 5 lancements chacun, avec moyenne, dispersion et un échec expliqué
à partir de sa trace.

**Les tâches.** Les 40 cas de `data/cas_etiquetes.csv`. Une tâche est réussie si
le montant retenu est exact **et** : cas clair → enregistrement automatique dans
la bonne catégorie ; cas ambigu → demande de confirmation.

**Les deux côtés** (mêmes réglages : Qwen3.5-4B, température 0,7, réflexion
désactivée, `presence_penalty` 0) :
- **Qwen seul** : prompt nu (les 5 catégories, sans mes règles) ; il répond en
  JSON `{montant, categorie, confirmation}` et décide de tout lui-même.
- **Mon système** : juge par logprobs + seuil 0,90 (brique 4), règle G5 et
  montant lu par Python (brique 3).

**Résultats** (`resultats/comparaison.md`, taux de réussite par lancement) :

| Côté | Toutes (40) | Claires (30) | Ambiguës (10) |
|---|---|---|---|
| Qwen seul | **58,0 % ± 2,1 %** (55,0–60,0) | 68,7 % ± 1,8 % | 26,0 % ± 8,9 % |
| Mon système | **74,5 % ± 1,1 %** (72,5–75,0) | 66,0 % ± 1,5 % | 100,0 % ± 0,0 % |

(moyenne ± écart-type sur 5 lancements, entre parenthèses min–max)

**Lecture.** Le gain vient entièrement des cas ambigus : Qwen seul ne demande
presque jamais confirmation (« Paiement PayPal 9,99 € » → `confirmation: false`
5 fois sur 5, avec une catégorie qui change : D trois fois, E deux fois),
mon système la demande toujours. Sur les cas clairs,
mon système fait un peu moins bien (66,0 % contre 68,7 %) : c'est le prix des
fausses alertes du seuil 0,90. Aucun des deux côtés ne s'est trompé de montant
(0 sur 200 pour Qwen seul).

**Un échec expliqué à partir de sa trace : tâche 10, « Billet de train SNCF
pour Lyon pour les vacances 45 € ».** Qwen seul la réussit 5 fois sur 5, mon
système 0 fois sur 5. Trace du juge (`resultats/traces_comparaison.jsonl`,
identique aux 5 lancements) :

```
token renvoyé : 'B'   cohérent : oui
scores : A 0.041   B 0.799   C 0.029   D 0.112   E 0.019
```

La catégorie est juste (B), mais le score 0,799 est sous le seuil 0,90 : le
système demande une confirmation inutile. Les 11 % donnés à D (Loisirs) viennent
du mot « vacances » : Qwen classe selon le motif du voyage, alors que ma règle
classe selon la nature de l'achat (principe général et R-B3). C'est une fausse
alerte, pas une erreur d'enregistrement : le coût est un clic.

**Deuxième échec, qui explique la dispersion du système : tâche 3, « Resto U ce
midi : 3,30 € », lancement 3.** Les logprobs ne dépendent pas de la température
(A 0,93 aux 5 lancements), mais le token tiré, lui, en dépend : à 0,7, Qwen a
tiré « D » (probabilité 5,8 %). Le contrôle de cohérence (lettre renvoyée ≠ lettre
la plus probable) a transformé la réponse en demande de confirmation. Toute la
dispersion de mon système vient de ce tirage ; elle disparaît à température 0,
qui est le réglage de l'assistant.

**Un défaut de mesure trouvé et corrigé.** Au premier calcul, Qwen seul n'avait
que 10,5 % de réussite : 161 réponses sur 200 étaient comptées « JSON invalide ».
Les traces montraient un JSON correct entouré de balises Markdown (Ollama
n'impose pas `format` quand la réflexion est désactivée). Le lecteur a été
corrigé et le score recalculé depuis les traces brutes, sans relancer Qwen
(`test_lecture_reponse_json_de_qwen_seul`).

**Limites.** Les mots-clés de G5 et le seuil 0,90 ont été choisis en connaissant
ces 40 cas : l'écart mesuré est optimiste pour mon système. 10 cas ambigus, c'est
peu. Le prompt de Qwen seul n'a pas été optimisé : un meilleur prompt réduirait
sans doute l'écart.

**Fichiers.** `src/comparer.py`, `resultats/traces_comparaison.jsonl`,
`resultats/comparaison.md`, `tests/test_comparer.py`.

**Commandes pour reproduire** (Ollama lancé) :

```bash
python src/comparer.py                  # 400 appels à Qwen, environ 10 minutes
python src/comparer.py --depuis-traces  # recalcule depuis les traces
python -m pytest tests/test_comparer.py
```
