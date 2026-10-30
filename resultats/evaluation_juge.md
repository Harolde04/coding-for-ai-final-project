# Évaluation du juge Qwen — brique 4

Modèle : `qwen3.5:4b-q4_K_M`, réflexion désactivée, température 0, 1 lancement par cas. 40 cas : 30 `auto`, 10 `confirmer`.
Fichier généré par `python src/evaluer_juge.py`. Ne pas modifier à la main.

## Ratés et fausses alertes selon le seuil

| Seuil | Corrects | Ratés (ambigu enregistré) | Ratés (mauvaise catégorie) | Fausses alertes |
|---|---|---|---|---|
| 0.50 | 28 | 8 / 10 | 3 | 1 / 30 |
| 0.60 | 29 | 7 / 10 | 3 | 1 / 30 |
| 0.70 | 29 | 6 / 10 | 2 | 3 / 30 |
| 0.80 | 27 | 4 / 10 | 1 | 8 / 30 |
| 0.90 ← seuil retenu | 29 | 1 / 10 | 0 | 10 / 30 |
| 0.95 | 24 | 1 / 10 | 0 | 15 / 30 |
| 0.99 | 15 | 0 / 10 | 0 | 25 / 30 |

## Détail par cas (seuil 0.90)

| id | Texte | Attendu | Lettre Qwen | Score | Décision | Issue |
|---|---|---|---|---|---|---|
| 1 | J'ai acheté des pâtes chez Carrefour pour 12 €. | A | A | 0.998 | auto | correct |
| 2 | J'ai payé 35 € chez Carrefour | A | A | 0.994 | auto | correct |
| 3 | Resto U ce midi : 3,30 € | A | A | 0.930 | auto | correct |
| 4 | Kebab avec des potes, 9€50 | A | A | 0.920 | auto | correct |
| 5 | Commande Uber Eats 18,90 euros | A | A | 0.723 | confirmer | fausse_alerte |
| 6 | Boulangerie : croissant et baguette 2.40€ | A | A | 0.984 | auto | correct |
| 7 | Restaurant pour l'anniversaire de Léa, ma part 27 € | A | D | 0.852 | confirmer | fausse_alerte |
| 8 | Recharge pass Navigo 86,40 € | B | B | 0.788 | confirmer | fausse_alerte |
| 9 | Uber pour rentrer de soirée 14 € | B | B | 0.988 | auto | correct |
| 10 | Billet de train SNCF pour Lyon pour les vacances 45 € | B | B | 0.799 | confirmer | fausse_alerte |
| 11 | Plein d'essence 60 € | B | B | 0.996 | auto | correct |
| 12 | Vélib' abonnement mensuel 3,10 € | B | B | 0.924 | auto | correct |
| 13 | Ticket de bus 1,90€ | B | B | 0.988 | auto | correct |
| 14 | Loyer d'octobre 520 € | C | C | 0.996 | auto | correct |
| 15 | Facture EDF 42,15 € | C | C | 0.976 | auto | correct |
| 16 | Box internet Free 29,99 € | C | C | 0.362 | confirmer | fausse_alerte |
| 17 | Assurance habitation 8 € ce mois-ci | C | C | 0.977 | auto | correct |
| 18 | Lampe IKEA pour ma chambre 15 € | C | E | 0.634 | confirmer | fausse_alerte |
| 19 | Place de cinéma 11 € | D | D | 0.967 | auto | correct |
| 20 | Abonnement Netflix 13,49 € | D | D | 0.966 | auto | correct |
| 21 | Bières au bar avec la promo 22 € | D | D | 0.962 | auto | correct |
| 22 | Airbnb à Barcelone pour le week-end 120 € | D | D | 0.669 | confirmer | fausse_alerte |
| 23 | Salle de sport Basic-Fit 24,99 € | D | D | 0.968 | auto | correct |
| 24 | Place de concert 45 € | D | D | 0.992 | auto | correct |
| 25 | Forfait mobile Free 19,99 € | E | E | 0.934 | auto | correct |
| 26 | Pharmacie, médicaments 7,80 € | E | E | 0.965 | auto | correct |
| 27 | Jean chez Zara 39,95 € | E | E | 0.915 | auto | correct |
| 28 | Coiffeur 18 € | E | E | 0.787 | confirmer | fausse_alerte |
| 29 | Cahiers et stylos pour les cours 12,60 € | E | E | 0.826 | confirmer | fausse_alerte |
| 30 | Carte cadeau Fnac pour l'anniversaire de mon frère 25 € | E | D | 0.731 | confirmer | fausse_alerte |
| 31 | Amazon 25 € | ? (confirmer) | E | 0.653 | confirmer | correct |
| 32 | Virement Lydia à Thomas 15 € | ? (confirmer) | E | 0.869 | confirmer | correct |
| 33 | Leclerc 70 € : courses et essence | ? (confirmer) | A | 0.440 | confirmer | correct |
| 34 | Fnac 30 € | ? (confirmer) | D | 0.851 | confirmer | correct |
| 35 | Relay gare du Nord 6,50 € | ? (confirmer) | B | 0.777 | confirmer | correct |
| 36 | Dépense de 40 € hier | ? (confirmer) | E | 0.574 | confirmer | correct |
| 37 | J'ai remboursé Julie 20 € pour samedi | ? (confirmer) | E | 0.805 | confirmer | correct |
| 38 | Action 12 € | ? (confirmer) | E | 0.353 | confirmer | correct |
| 39 | Paiement PayPal 9,99 € | ? (confirmer) | E | 0.953 | auto | rate_ambigu |
| 40 | Abonnement 9,99 € par mois | ? (confirmer) | D | 0.718 | confirmer | correct |

## Contrôles

- Réponses invalides (token hors A–E ou lettre incohérente) : aucune
- Cas où une lettre manque dans les top_logprobs : aucun
- Masse maximale hors des cinq lettres : 0.0571
