# Journal d'usage de l'IA (exigence R3)

Ce journal retrace l'usage des assistants IA pendant le projet, selon le principe
du sujet : l'étudiant décide quoi construire, nettoyer et mesurer ; l'IA aide à
l'écrire et à le lancer ; le code est vérifié par des tests.

## Synthèse

- **Outils.** Claude (Claude Code, application de bureau) pour la conception,
  le code, les tests et la rédaction ; Qwen3.5-4B (Ollama) est le modèle du projet.
- **Export brut.** La conversation complète est dans `ai_log/conversation_assistant_depenses.txt`.
- **Répartition.** L'essentiel du code a été écrit par l'IA et gardé tel quel
  après relecture et tests (168 tests pytest). Les choix de règles métier, de
  données, de seuil et de méthode de mesure sont les miens : ils sont listés
  séance par séance dans « Mes décisions ».
- **Légende.** *Gardé tel quel* : proposé par l'IA, relu et conservé.
  *Décidé par moi* : choix que j'ai fait ou imposé. *Vérifié et corrigé* : défaut
  trouvé en testant, corrigé avant le commit ; chaque ligne indique qui l'a trouvé.
  Aucun de ces défauts n'a été trouvé par moi : ils ont tous été repérés et
  corrigés par l'IA, puis relus par moi. Mes propres vérifications (tests du juge
  et de l'assistant dans PowerShell, calcul du restant à la main) sont dans
  « Mes décisions ».

---

## Séance 1 — Cadrage, règles métier et 40 cas étiquetés

**Objectif.** Partir de ma proposition (assistant de dépenses étudiantes,
briques 1, 3, 4, 6, 9) et construire une base de cas étiquetés avec des règles
que je sais expliquer.

**Mes décisions.**
- Le sujet, les 5 briques, le seuil de départ à 0,80 et le principe « ne jamais
  inventer une catégorie quand l'information manque ».
- Commencer par 40 cas soigneusement étiquetés plutôt que 100 mal classés.
- **Garder la règle R-A2** (grande surface sans article précisé → Alimentation)
  comme une hypothèse assumée pour un étudiant, et non comme une vérité
  universelle ; elle ne s'applique pas si un achat non alimentaire est mentionné.
- Le plan pour lire les probabilités de Qwen : désactiver la réflexion, une seule
  lettre en sortie, récupérer les logprobs, vérifier le token renvoyé avant
  d'utiliser son score, et tester sur le vrai modèle avant de bâtir l'évaluation.
- Séparer les tests de montants invalides (brique 3) des 40 cas (brique 4).

**Gardé tel quel.**
- `REGLES_METIER.md` (règles R-A1 à R-X4), les 40 cas de `data/cas_etiquetes.csv`
  et `tests/test_cas_etiquetes.py`, rédigés par l'IA puis relus et validés.

**Vérifié et corrigé.**
- *(trouvé par l'IA)* Ma proposition listait 4 catégories sous « limitées à cinq »
  (E — Autres manquait) ; la liste A–E est la même partout et un test le vérifie.
- *(trouvé et corrigé par l'IA)* Premier CSV séparé par des virgules : les montants
  « 3,30 € » le cassaient ; passé au séparateur `;`.

## Séance 2 — Brique 6 : nettoyage de MoneyData

**Objectif.** Trouver de vraies données, les nettoyer et documenter chaque décision.

**Mes décisions.**
- **Le jeu de données** : MoneyData (Mendeley, CC BY 4.0), trouvé par moi.
- **Décider la correspondance des catégories avant tout code.**
- **Mes réponses Q1 à Q8** : exclure les retraits d'espèces (on ne sait pas ce
  qui a été acheté, risque de double comptage) ; crédit immobilier → C, distinct
  des autres prêts ; catégories mélangées corrigées **ligne par ligne** ;
  assurances classées selon leur nature ; lignes sans catégorie examinées une par
  une ; compléments alimentaires → E ; garder les livres sterling ; MoneyData sert
  surtout à la brique 6, les 40 cas à l'évaluation de Qwen.
- **Le principe « une donnée corrigée n'est pas une donnée connue »**, devenu la
  colonne `provenance` (`origine`, `commercant`, `non_identifie`).
- **R-D4** (TV Licence → D), **R-X5** (vélo → `?` entre B et D, les 15 lignes
  restent en `?` tant que l'usage est inconnu ; j'en attendais 14, la quinzième
  est le libellé tronqué `IZ *Nottingham Bik`), **R-X6** (assurance inconnue → `?`
  entre C et E).
- **La source Lloyds Bank** pour classer ASSURANT en E (règle R-E6, obtenue dans
  un document), avec sa limite (page actuelle, prélèvements 2015–2019).

**Gardé tel quel.**
- `src/nettoyage_moneydata.py`, les tables `data/correspondance_categories.csv`
  et `data/regles_commercants.csv`, le journal généré, README, EVIDENCE.md, `.gitignore`.
- La correction des dates inversées par Excel, vérifiée : les dates suivent ensuite
  exactement l'ordre des numéros de transaction (2015–2022).

**Vérifié et corrigé.**
- *(trouvé et corrigé par l'IA)* Le premier masquage des particuliers cachait
  aussi des entreprises (fournisseurs d'énergie, cabinets d'avocats) ; liste
  d'organisations élargie.
- *(trouvé et corrigé par l'IA)* Un commerçant qui confirme la catégorie des
  auteurs était marqué `commercant` : corrigé en `origine`, pour respecter mon
  principe de provenance.
- *(signalé par l'IA)* Le fichier Excel brut, qui contient de vrais noms, est
  exclu du dépôt (R1).

## Séance 3 — Brique 4 (juge Qwen) et brique 3 (règles imposées par le code)

**Objectif.** Lire un score dans Qwen, choisir un seuil, mesurer ratés et fausses
alertes ; empêcher par le code ce que le système ne doit jamais faire.

**Mes décisions.**
- Télécharger et utiliser le modèle exigé, Qwen3.5-4B Q4_K_M (j'avais seulement
  qwen3.5:2b).
- Tester le juge moi-même dans PowerShell avant l'évaluation complète.
- **Passer le seuil de 0,80 à 0,90** après la mesure : un raté fausse le budget en
  silence, une fausse alerte coûte un clic (0,80 : 5 ratés / 8 fausses alertes ;
  0,90 : 1 raté / 10 fausses alertes).

**Gardé tel quel.**
- `src/juge_qwen.py` (prompt du juge compris), `src/evaluer_juge.py`,
  `src/garde_fous.py` (règles G1 à G5) et leurs tests.

**Vérifié et corrigé.**
- *(trouvé et corrigé par l'IA, au premier test sur 3 cas)* Pour « Amazon 25 € »,
  Qwen renvoyait A alors que ses logprobs
  donnaient E à 0,65. Cause : `presence_penalty = 1,5` par défaut dans Ollama,
  appliquée après les logprobs. Pénalité mise à 0 et contrôle de cohérence ajouté
  (la lettre renvoyée doit être la plus probable).
- *(trouvé par l'IA)* Le token `<think>` apparaît encore parmi les candidats malgré la réflexion
  désactivée : le code vérifie le token renvoyé avant d'utiliser le score.

## Séance 4 — Brique 1 (assistant avec outils) et brique 9 (comparaison)

**Objectif.** Un assistant où Qwen appelle mes outils Python ; une comparaison
mesurée face à Qwen seul.

**Mes décisions.**
- **Méthode de la brique 9** : Qwen seul reçoit un prompt nu (les 5 catégories,
  sans mes règles) et décide de tout ; 5 lancements à température 0,7 pour les deux
  côtés, pour que la dispersion ait un sens.
- **Tester l'assistant moi-même** : budget 800 €, « J'ai payé 45 € chez Auchan »,
  PayPal (confirmation demandée, corrigé en D), « -10 € » refusé, restant 745,01 €
  vérifié à la main.
- Garder dans le dépôt la trace de cette séance de test.

**Gardé tel quel.**
- `src/assistant.py`, `src/budget.py`, `src/demo_assistant.py`, `src/comparer.py`
  et leurs tests ; les critères de réussite d'une tâche (montant exact ; bonne
  catégorie en automatique pour un cas clair ; confirmation pour un cas ambigu).

**Vérifié et corrigé.**
- *(choix de conception de l'IA, pas un défaut)* L'outil d'enregistrement relit
  le message de l'utilisateur et non le texte transmis par Qwen, pour que le
  modèle ne puisse pas changer le montant (G2).
- *(trouvé et corrigé par l'IA)* Premier calcul de la brique 9 : Qwen seul à 10,5 %, avec 161 réponses sur 200
  comptées « JSON invalide ». Les traces montraient un JSON correct entouré de
  balises Markdown. Lecteur corrigé, score recalculé depuis les traces brutes :
  Qwen seul 58,0 % ± 2,1 %, mon système 74,5 % ± 1,1 %.
- *(erreur de l'IA, corrigée par l'IA elle-même)* Une phrase d'EVIDENCE.md disait
  « PayPal → D 5 fois sur 5 » pour Qwen seul ; vérifiée dans les traces : D trois
  fois, E deux fois. Phrase corrigée.

**Échecs expliqués à partir des traces** (détail dans EVIDENCE.md) : le billet
SNCF « pour les vacances » (B à 0,799, sous le seuil, D tiré à 11 % par le mot
« vacances ») et Resto U au lancement 3 (lettre D tirée à température 0,7,
rattrapée par le contrôle de cohérence).
