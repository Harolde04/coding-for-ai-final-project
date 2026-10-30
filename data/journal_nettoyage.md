# Journal de nettoyage — MoneyData

Fichier généré par `python src/nettoyage_moneydata.py`. Ne pas modifier à la main.

Source : Firat, Vytia, Vasudeva, Jiang, Laramee, *MoneyVis: Open Bank Transaction
Data for Visualization and Beyond*, EuroVis 2023 — Mendeley Data
10.17632/dnxtg6n4rv.1, licence CC BY 4.0. Montants en livres sterling (£), non convertis.

## 1. Bilan

| Étape | Lignes |
|---|---|
| Lignes du fichier brut | 6567 |
| Lignes exclues (`moneydata_exclus.csv`) | 2325 |
| Dépenses gardées (`moneydata_propre.csv`) | 4242 |

## 2. Valeurs converties

| Correction | Lignes |
|---|---|
| Dates Excel avec jour et mois inversés, remis en ordre | 2816 |
| Libellés avec espaces multiples réduits | 242 |
| Catégories avec espace final (« Groceries  ») | 5 |
| Catégories vides, notées VIDE | 24 |
| Types de paiement vides, notés INCONNU | 61 |
| Particuliers remplacés par un pseudonyme (PARTICULIER_nnn) | 46 |

Écart avec la feuille de description des auteurs : le fichier utilise les codes
`DD` et `CPT`, la feuille annonce `D/D` et `C/P`. Les codes sont gardés tels quels.

## 3. Lignes retirées (par règle)

| Règle — motif | Lignes |
|---|---|
| R-N1 — épargne | 1249 |
| R-N3 — retraits au distributeur | 460 |
| R-N2 — crédit sur le compte | 445 |
| R-N1 — placements | 151 |
| R-N2 — revenus et remboursements reçus | 15 |
| R-N2 — restitution de dépôt de garantie | 2 |
| R-N1 — plateforme d'investissement | 1 |
| R-N4 — transfert entre comptes | 1 |
| R-N1 — versement vers l'épargne | 1 |

## 4. Catégorie finale des dépenses gardées

| Lettre | Lignes |
|---|---|
| ? | 1559 |
| A | 918 |
| E | 723 |
| C | 525 |
| D | 301 |
| B | 216 |

## 5. D'où vient la catégorie (donnée connue ou corrigée)

| Provenance | Lignes |
|---|---|
| origine | 1592 |
| non_identifie | 1559 |
| commercant | 1091 |

- `origine` : lettre déduite de la catégorie donnée par les auteurs du jeu.
- `commercant` : **notre correction**, fondée sur l'identification du commerçant
  dans le libellé (`data/regles_commercants.csv`), pas sur une information de la banque.
- `non_identifie` : `?`, la ligne demandera une confirmation.

## 6. Corrections et mises en `?` décidées à partir du libellé

| Catégorie d'origine | Lettre finale | Justification | Lignes |
|---|---|---|---|
| Others | E | frais de change de la banque | 234 |
| Bills | C | fournisseur d'eau ou d'énergie | 172 |
| Bills | C | fournisseur internet du logement | 98 |
| Other Shopping | E | opérateur téléphonique | 84 |
| Bills | E | frais de tenue de compte | 84 |
| Bills | C | taxe locale du logement (council tax) | 70 |
| Insurance | E | assurance vie | 66 |
| Others | E | cotisation syndicale | 54 |
| Insurance | E | assurance téléphone mobile (source : Lloyds Bank) | 43 |
| Insurance | ? | type d'assurance inconnu | 28 |
| Other Shopping | ? | commerce généraliste sans article précisé | 26 |
| Other Shopping | E | enseigne de vêtements ou chaussures | 24 |
| Bills | D | redevance télévisuelle | 24 |
| Other Shopping | E | encre et fournitures d'imprimante | 20 |
| Bills | C | mensualité de crédit immobilier | 20 |
| Other Shopping | ? | achat de vélo sans indication d'usage | 15 |
| Groceries | E | magasin de compléments alimentaires | 14 |
| Other Shopping | C | meubles et équipement du logement | 12 |
| Others | ? | commerce généraliste sans article précisé | 12 |
| Dine Out | D | bar (pas un repas) | 11 |
| Other Shopping | E | enseigne d'hygiène et beauté | 10 |
| Services | E | cotisation syndicale | 9 |
| Travel | ? | agence de voyage : vol (B) ou hôtel (D) | 8 |
| Travel | E | frais de change de la banque | 7 |
| Travel | ? | banque étrangère : probablement un retrait, non vérifiable | 6 |
| Travel | D | hébergement en voyage | 5 |
| VIDE | D | service de vidéo | 5 |
| Others | C | entreprise de déménagement | 5 |
| Others | E | visa, nom de domaine ou don | 4 |
| Services | ? | commerce généraliste sans article précisé | 4 |
| Bills | E | opérateur téléphonique | 3 |
| Insurance | ? | frais juridiques : aucune règle ne les couvre | 3 |
| Other Shopping | E | boutique de cadeaux ou fleuriste | 3 |
| Travel | D | activité touristique | 2 |
| Mortgage | ? | frais juridiques : aucune règle ne les couvre | 2 |
| Entertainment | C | fournisseur internet du logement | 2 |
| Others | A | supermarché | 1 |
| Travel | ? | inscription à une conférence : aucune règle ne la couvre | 1 |
| VIDE | A | supermarché | 1 |
| Bills | ? | frais juridiques : aucune règle ne les couvre | 1 |
| VIDE | D | hébergement en voyage | 1 |
| Other Shopping | A | supermarché | 1 |
| Other Shopping | E | magasin de compléments alimentaires | 1 |
| Travel | E | visa, nom de domaine ou don | 1 |
