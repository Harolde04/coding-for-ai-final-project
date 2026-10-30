# Comparaison mesurée — brique 9

Modèle : `qwen3.5:4b-q4_K_M`. 40 tâches, 5 lancements par côté, température 0.7. Fichier généré par `python src/comparer.py`.

## Taux de réussite par lancement

| Côté | Tâches | Moyenne | Écart-type | Min | Max |
|---|---|---|---|---|---|
| qwen_seul | toutes (40) | 58.0% | 2.1% | 55.0% | 60.0% |
| qwen_seul | claires (30) | 68.7% | 1.8% | 66.7% | 70.0% |
| qwen_seul | ambiguës (10) | 26.0% | 8.9% | 10.0% | 30.0% |
| systeme | toutes (40) | 74.5% | 1.1% | 72.5% | 75.0% |
| systeme | claires (30) | 66.0% | 1.5% | 63.3% | 66.7% |
| systeme | ambiguës (10) | 100.0% | 0.0% | 100.0% | 100.0% |

## Réussites par tâche (sur 5 lancements)

| id | Texte | Attendu | Qwen seul | Système |
|---|---|---|---|---|
| 1 | J'ai acheté des pâtes chez Carrefour pour 12 €. | A | 5/5 | 5/5 |
| 2 | J'ai payé 35 € chez Carrefour | A | 5/5 | 5/5 |
| 3 | Resto U ce midi : 3,30 € | A | 5/5 | 4/5 |
| 4 | Kebab avec des potes, 9€50 | A | 0/5 | 5/5 |
| 5 | Commande Uber Eats 18,90 euros | A | 5/5 | 0/5 |
| 6 | Boulangerie : croissant et baguette 2.40€ | A | 5/5 | 5/5 |
| 7 | Restaurant pour l'anniversaire de Léa, ma part 27 € | A | 2/5 | 0/5 |
| 8 | Recharge pass Navigo 86,40 € | B | 3/5 | 0/5 |
| 9 | Uber pour rentrer de soirée 14 € | B | 5/5 | 5/5 |
| 10 | Billet de train SNCF pour Lyon pour les vacances 45 € | B | 5/5 | 0/5 |
| 11 | Plein d'essence 60 € | B | 5/5 | 5/5 |
| 12 | Vélib' abonnement mensuel 3,10 € | B | 5/5 | 5/5 |
| 13 | Ticket de bus 1,90€ | B | 5/5 | 5/5 |
| 14 | Loyer d'octobre 520 € | C | 5/5 | 5/5 |
| 15 | Facture EDF 42,15 € | C | 5/5 | 5/5 |
| 16 | Box internet Free 29,99 € | C | 0/5 | 0/5 |
| 17 | Assurance habitation 8 € ce mois-ci | C | 5/5 | 5/5 |
| 18 | Lampe IKEA pour ma chambre 15 € | C | 0/5 | 0/5 |
| 19 | Place de cinéma 11 € | D | 5/5 | 5/5 |
| 20 | Abonnement Netflix 13,49 € | D | 5/5 | 5/5 |
| 21 | Bières au bar avec la promo 22 € | D | 5/5 | 5/5 |
| 22 | Airbnb à Barcelone pour le week-end 120 € | D | 0/5 | 0/5 |
| 23 | Salle de sport Basic-Fit 24,99 € | D | 5/5 | 5/5 |
| 24 | Place de concert 45 € | D | 5/5 | 5/5 |
| 25 | Forfait mobile Free 19,99 € | E | 2/5 | 5/5 |
| 26 | Pharmacie, médicaments 7,80 € | E | 5/5 | 5/5 |
| 27 | Jean chez Zara 39,95 € | E | 0/5 | 5/5 |
| 28 | Coiffeur 18 € | E | 1/5 | 0/5 |
| 29 | Cahiers et stylos pour les cours 12,60 € | E | 0/5 | 0/5 |
| 30 | Carte cadeau Fnac pour l'anniversaire de mon frère 25 € | E | 0/5 | 0/5 |
| 31 | Amazon 25 € | confirmer | 4/5 | 5/5 |
| 32 | Virement Lydia à Thomas 15 € | confirmer | 1/5 | 5/5 |
| 33 | Leclerc 70 € : courses et essence | confirmer | 3/5 | 5/5 |
| 34 | Fnac 30 € | confirmer | 0/5 | 5/5 |
| 35 | Relay gare du Nord 6,50 € | confirmer | 0/5 | 5/5 |
| 36 | Dépense de 40 € hier | confirmer | 2/5 | 5/5 |
| 37 | J'ai remboursé Julie 20 € pour samedi | confirmer | 1/5 | 5/5 |
| 38 | Action 12 € | confirmer | 2/5 | 5/5 |
| 39 | Paiement PayPal 9,99 € | confirmer | 0/5 | 5/5 |
| 40 | Abonnement 9,99 € par mois | confirmer | 0/5 | 5/5 |

## Contrôles

- Montants faux de Qwen seul : 0 sur 200
- Réponses JSON invalides de Qwen seul : 0
