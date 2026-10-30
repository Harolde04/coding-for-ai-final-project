# Preuves par brique

## Brique 1 — Votre propre outil

*À venir.*

## Brique 3 — Une règle imposée par le code

*À venir.*

## Brique 4 — Un modèle de décision

*À venir.* Jeu étiqueté prêt : `data/cas_etiquetes.csv` (40 cas, 30 `auto`,
10 `confirmer`), règles dans `REGLES_METIER.md`.

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
