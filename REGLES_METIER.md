# Règles métier de classement des dépenses

Ces règles servent à étiqueter les cas de `data/cas_etiquetes.csv` (brique 4)
et, plus tard, à vérifier les décisions du modèle. Chaque cas cite la règle
qui justifie son étiquette.

**Principe général : on classe selon la nature de l'achat, pas selon le motif.**
Un billet de train reste du Transport même si c'est pour partir en vacances.

**Deuxième principe : on n'invente jamais une catégorie.** Si le texte ne permet
pas de savoir ce qui a été acheté, la catégorie attendue est `?` et la décision
attendue est `confirmer`.

**Troisième principe : une donnée corrigée n'est pas une donnée connue.**
Dans les données réelles (`data/moneydata_propre.csv`), chaque ligne indique
d'où vient sa catégorie : `origine` (catégorie donnée par les auteurs du jeu),
`commercant` (notre correction, fondée sur l'identification du commerçant
dans le libellé) ou `non_identifie` (`?`).

## Catégories

| Lettre | Catégorie     |
|--------|---------------|
| A      | Alimentation  |
| B      | Transport     |
| C      | Logement      |
| D      | Loisirs       |
| E      | Autres        |

## A — Alimentation

- **R-A1** Achat de nourriture ou de boisson non alcoolisée nommé explicitement
  (pâtes, pain, resto U, boulangerie, cantine).
- **R-A2** Grande surface alimentaire **sans précision** de l'article
  (Carrefour, Lidl, Auchan, Intermarché, Franprix, Monoprix) → Alimentation.
  *Règle par défaut assumée* : c'est l'usage dominant chez un étudiant.
  Ne s'applique pas si le texte mentionne un autre type d'achat (voir R-X3).
- **R-A3** Un repas reste un repas, même entre amis ou pour une occasion
  (restaurant, kebab, anniversaire au restaurant).
- **R-A4** Livraison de repas (Uber Eats, Deliveroo) → Alimentation, pas Transport.

## B — Transport

- **R-B1** Transports en commun : pass Navigo, ticket de bus ou de métro.
- **R-B2** Trajet individuel payé : VTC (Uber sans « Eats »), taxi, vélo ou
  trottinette en libre-service, essence, péage, parking.
- **R-B3** Train, car ou avion, quel que soit le motif du voyage.

## C — Logement (résidence principale uniquement)

- **R-C1** Loyer et charges locatives ; mensualité de **crédit immobilier**
  (pas les autres prêts ni les frais juridiques d'achat).
- **R-C2** Énergie et internet du logement : électricité, gaz, eau, box internet ;
  taxe locale liée au logement (council tax au Royaume-Uni).
- **R-C3** Assurance habitation, meubles, équipement, travaux et déménagement
  du logement.

## D — Loisirs

- **R-D1** Sorties : cinéma, concert, bar, boîte de nuit, musée.
  Un bar compte comme sortie (D), contrairement à un repas (R-A3).
- **R-D2** Abonnements de divertissement **nommés** : Netflix, Spotify,
  Disney+, salle de sport, jeux vidéo.
- **R-D3** Hébergement de vacances ou de week-end (hôtel, Airbnb) :
  ce n'est pas la résidence principale, donc pas du Logement.
- **R-D4** Redevance télévisuelle (TV Licence britannique) : elle donne accès
  à la télévision et aux contenus audiovisuels, comme Netflix (R-D2).

## E — Autres

- **R-E1** Santé : pharmacie, médecin, mutuelle, **compléments alimentaires**
  (magasins diététiques). Ce ne sont pas des courses ordinaires (R-A1/R-A2).
- **R-E2** Téléphone : forfait mobile, achat de téléphone
  (différent de la box internet du logement, R-C2).
- **R-E3** Achats personnels identifiés : vêtements, chaussures, hygiène et
  beauté, coiffeur, cadeaux, fournitures (y compris encre d'imprimante).
- **R-E4** Frais bancaires (frais de tenue de compte, frais de change) et
  assurances de personne (assurance vie, prévoyance).
- **R-E5** Cotisations et démarches : syndicat, visa, nom de domaine, dons.
- **R-E6** Assurance de téléphone mobile et d'appareils → Autres, pas Logement.
  **Règle obtenue dans un document, absente du fichier** : Lloyds Bank indique
  qu'Assurant General Insurance Limited fournit l'assurance téléphone mobile
  de ses comptes packagés (Club Lloyds, Silver, Gold, Platinum, Premier)
  — page « Gadget insurance », lloydsbank.com, consultée le 30/10/2026.
  Le compte MoneyData est un compte Club Lloyds Silver (frais `CLUB LLOYDS FEE`,
  `SILVER ACCOUNT`), donc les prélèvements ASSURANT sont classés en E.
  *Limite* : la page est actuelle, les prélèvements datent de 2015–2019 et
  leurs montants (21 à 40 £) ne sont pas les tarifs actuels ; le document
  établit ce que vend Assurant, pas le contrat exact de ce client.

## X — Confirmation obligatoire (catégorie attendue `?`)

- **R-X1** Marchand généraliste sans article précisé (Amazon, Fnac, Relay,
  Action, PayPal) : plusieurs catégories sont possibles.
- **R-X2** Transfert entre personnes (Lydia, virement, remboursement d'un ami) :
  on ne sait pas ce qui a été payé.
- **R-X3** Dépense mixte couvrant plusieurs catégories (« courses et essence ») :
  on demande à l'utilisateur de choisir ou de scinder.
- **R-X4** Aucune information sur l'objet de la dépense (« dépense de 40 € »,
  « abonnement » sans nom de service).
- **R-X5** Achat de vélo sans indication d'usage : on demande à l'utilisateur
  de choisir entre B (Transport) et D (Loisirs).
- **R-X6** Assurance dont le libellé ne précise pas la nature (ZURICH) : on demande à
  l'utilisateur de choisir entre C (assurance habitation, R-C3) et E (autre
  assurance, R-E4).

## N — Lignes exclues : ce ne sont pas des dépenses de consommation

Ces lignes sont retirées du jeu nettoyé et listées dans
`data/moneydata_exclus.csv` avec leur motif.

- **R-N1** Épargne et investissement (Save the Change, compte épargne,
  Trading 212) : l'argent reste à la personne.
- **R-N2** Crédits sur le compte : salaire, intérêts, remboursements reçus.
- **R-N3** Retraits d'espèces : on ne sait pas ce qui a été acheté ensuite,
  et les achats payés autrement pourraient être comptés deux fois.
- **R-N4** Transferts entre comptes de la même personne.

## Comment ces règles alimentent la brique 4

- `decision_attendue = auto` : la règle A–E suffit à trancher. Si le système
  demande quand même une confirmation, c'est une **fausse alerte**.
- `decision_attendue = confirmer` : règle R-X. Si le système enregistre
  automatiquement, c'est un **raté**.
- Un enregistrement automatique dans la mauvaise catégorie (cas `auto`)
  est aussi compté comme un **raté**.
