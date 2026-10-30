"""Nettoyage du jeu MoneyData (brique 6).

Source : Firat, Vytia, Vasudeva, Jiang, Laramee, « MoneyVis: Open Bank Transaction
Data for Visualization and Beyond », EuroVis 2023. Mendeley Data
10.17632/dnxtg6n4rv.1, licence CC BY 4.0.

Usage : python src/nettoyage_moneydata.py [chemin/vers/laramee26openBankTransactionData.xlsx]

Produit dans data/ :
- moneydata_propre.csv  : dépenses gardées, avec leur lettre A–E ou « ? »
- moneydata_exclus.csv  : lignes retirées, avec leur motif
- journal_nettoyage.md  : ce qui a été retiré, converti et corrigé, avec les comptes
"""
import csv
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE / "data"
FICHIER_BRUT = RACINE / "laramee26openBankTransactionData.xlsx"

LETTRES = {"A", "B", "C", "D", "E"}

# Types de paiement où le libellé est le nom du bénéficiaire ou de l'émetteur.
TYPES_VIREMENT = {"FPO", "FPI", "TFR", "SO", "BGC"}
# Bénéficiaires de virement qui sont des organisations, pas des particuliers.
# En cas de doute, on masque : un nom d'entreprise caché coûte moins qu'un nom de personne publié.
ORGANISATIONS = re.compile(
    r"TRISTRAMS|REMOVALS|MOVING|UNI|GOOGLE|IISL|TRADING ?212|ESAVINGS|TAMBA"
    r"|LTD|LIMI|LLP|PLC|LEGAL|LEG$|SOLICITOR|ROTHERAS|GRINDEYS|ENERGY|WATER|WELSH WA"
    r"|BANK|BAN$|CREDIT|C C SWANSEA|PAYPAL|PROTECTION|ADVISORS|SHAREDEALING|STFC"
    r"|CARDIFF MET|WINDOW|ELECTRICAL|CRYSTAL CLEAR|^S\.?H\.?S\.?$|^REMUS$|^NCC ",
    re.IGNORECASE,
)
# Particuliers repérés à la main hors des types de virement.
PARTICULIERS_HORS_VIREMENT = {
    "ANTIGONI ABRAHMS", "CARL DAVENPORT", "L CATATE", "FB EDMUNDS",
    "PATRICIA A S LAW", "SALLY GOLDSTONE", "ROBERT RECORD", "R LAWRENCE",
}


def corriger_date(valeur):
    """Renvoie la vraie date d'une cellule.

    Le fichier mélange du texte « jj/mm/aaaa » et des dates Excel. Les dates
    Excel sont celles dont le jour était ≤ 12 : Excel a lu « 12/07/2022 »
    comme mois/jour, donc le 7 décembre. On remet jour et mois à leur place.
    """
    if isinstance(valeur, str):
        return datetime.strptime(valeur.strip(), "%d/%m/%Y").date()
    return date(valeur.year, valeur.day, valeur.month)


def normaliser_libelle(libelle):
    """Espaces multiples réduits à un seul : « LIDL GB  NOTTINGHA » → « LIDL GB NOTTINGHA »."""
    return re.sub(r"\s+", " ", str(libelle)).strip()


def normaliser_categorie(categorie):
    """« Groceries  » → « Groceries » ; cellule vide → « VIDE »."""
    if categorie is None or (isinstance(categorie, float) and pd.isna(categorie)):
        return "VIDE"
    return str(categorie).strip()


def charger_correspondance(chemin=DOSSIER_DATA / "correspondance_categories.csv"):
    with open(chemin, encoding="utf-8", newline="") as f:
        return {ligne["categorie_origine"]: ligne for ligne in csv.DictReader(f, delimiter=";")}


def charger_regles_commercants(chemin=DOSSIER_DATA / "regles_commercants.csv"):
    with open(chemin, encoding="utf-8", newline="") as f:
        regles = list(csv.DictReader(f, delimiter=";"))
    for regle in regles:
        regle["motif_compile"] = re.compile(regle["motif"], re.IGNORECASE)
    return regles


def classer(libelle, categorie, est_credit, type_paiement, correspondance, regles_commercants):
    """Décide du sort d'une ligne.

    Renvoie (lettre, provenance, regle, justification, possibles) où lettre vaut
    A–E, « ? » ou « EXCLU », provenance vaut « origine », « commercant » ou
    « non_identifie », et possibles liste les lettres à proposer à l'utilisateur
    (« B|D » pour un vélo, la lettre seule si elle est connue, vide si exclu).

    Ordre des décisions :
    1. crédit sur le compte ou retrait d'espèces → exclu ;
    2. commerçant identifié dans le libellé → notre correction ;
    3. catégorie d'origine homogène ou exclue → la lettre des auteurs ;
    4. catégorie d'origine mélangée → « ? ».
    """
    if est_credit:
        return "EXCLU", "origine", "R-N2", "crédit sur le compte", ""
    if type_paiement == "CPT":
        return "EXCLU", "origine", "R-N3", "retraits au distributeur", ""

    entree = correspondance.get(categorie)
    if entree is None:
        raise ValueError(f"catégorie d'origine inconnue : {categorie!r}")
    if entree["lettre"] == "EXCLU":
        return "EXCLU", "origine", entree["regle"], entree["commentaire"], ""

    for regle in regles_commercants:
        if regle["motif_compile"].search(libelle):
            if regle["lettre"] == entree["lettre"]:
                # Le commerçant confirme la catégorie des auteurs : la donnée était déjà connue.
                return entree["lettre"], "origine", entree["regle"], entree["commentaire"], entree["lettre"]
            if regle["lettre"] == "?":
                return "?", "non_identifie", regle["regle"], regle["justification"], regle["categories_possibles"]
            possibles = regle["lettre"] if regle["lettre"] in LETTRES else ""
            return regle["lettre"], "commercant", regle["regle"], regle["justification"], possibles

    if entree["lettre"] == "MELANGEE":
        return ("?", "non_identifie", entree["regle"],
                "catégorie d'origine mélangée, commerçant non identifié", "A|B|C|D|E")
    return entree["lettre"], "origine", entree["regle"], entree["commentaire"], entree["lettre"]


def est_particulier(libelle, type_paiement):
    if libelle in PARTICULIERS_HORS_VIREMENT:
        return True
    if type_paiement in TYPES_VIREMENT:
        return not ORGANISATIONS.search(libelle) and not re.fullmatch(r"[\d\W]+", libelle)
    return False


def nettoyer(chemin_brut):
    brut = pd.read_excel(chemin_brut, sheet_name=0)
    correspondance = charger_correspondance()
    regles_commercants = charger_regles_commercants()
    stats = Counter()
    stats["lignes_brutes"] = len(brut)

    pseudonymes = {}
    gardees, exclues = [], []
    for _, ligne in brut.iterrows():
        valeur_date = ligne["Transaction Date"]
        if not isinstance(valeur_date, str):
            stats["dates_jour_mois_inverses"] += 1
        libelle_brut = str(ligne["Transaction Description"])
        libelle = normaliser_libelle(libelle_brut)
        if libelle != libelle_brut:
            stats["libelles_espaces_corriges"] += 1
        categorie_brute = ligne["Category"]
        categorie = normaliser_categorie(categorie_brute)
        if pd.isna(categorie_brute):
            stats["categories_vides"] += 1
        elif categorie != categorie_brute:
            stats["categories_espaces_corriges"] += 1
        type_paiement = ligne["Transaction Type"] if pd.notna(ligne["Transaction Type"]) else "INCONNU"
        if type_paiement == "INCONNU":
            stats["types_vides"] += 1
        est_credit = pd.notna(ligne["Credit Amount"])
        montant = ligne["Credit Amount"] if est_credit else ligne["Debit Amount"]

        lettre, provenance, regle, justification, possibles = classer(
            libelle, categorie, est_credit, type_paiement, correspondance, regles_commercants
        )

        if est_particulier(libelle, type_paiement):
            # « R LAWRENCE 01MAR20 » et « R LAWRENCE » sont la même personne : même pseudonyme.
            personne = re.sub(r"\s+\d{2}[A-Z]{3}\d{2}$", "", libelle)
            libelle = pseudonymes.setdefault(personne, f"PARTICULIER_{len(pseudonymes) + 1:03d}")

        enregistrement = {
            "id_origine": int(ligne["Transaction Number"]),
            "date": corriger_date(valeur_date).isoformat(),
            "type": type_paiement,
            "libelle": libelle,
            "montant_gbp": f"{montant:.2f}",
            "categorie_origine": categorie,
        }
        if lettre == "EXCLU":
            exclues.append({**enregistrement, "sens": "credit" if est_credit else "debit",
                            "regle": regle, "motif": justification})
        else:
            gardees.append({**enregistrement, "categorie_finale": lettre,
                            "categories_possibles": possibles, "provenance": provenance,
                            "regle": regle, "justification": justification})

    stats["particuliers_pseudonymises"] = len(pseudonymes)
    return gardees, exclues, stats


def ecrire_csv(chemin, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(lignes)


def tableau(compteur, entete):
    lignes = [f"| {entete} | Lignes |", "|---|---|"]
    lignes += [f"| {cle} | {n} |" for cle, n in compteur.most_common()]
    return "\n".join(lignes)


def ecrire_journal(chemin, gardees, exclues, stats):
    corrections = Counter(
        (g["categorie_origine"], g["categorie_finale"], g["justification"])
        for g in gardees if g["provenance"] == "commercant"
        or (g["provenance"] == "non_identifie" and g["justification"] != "catégorie d'origine mélangée, commerçant non identifié")
    )
    texte = f"""# Journal de nettoyage — MoneyData

Fichier généré par `python src/nettoyage_moneydata.py`. Ne pas modifier à la main.

Source : Firat, Vytia, Vasudeva, Jiang, Laramee, *MoneyVis: Open Bank Transaction
Data for Visualization and Beyond*, EuroVis 2023 — Mendeley Data
10.17632/dnxtg6n4rv.1, licence CC BY 4.0. Montants en livres sterling (£), non convertis.

## 1. Bilan

| Étape | Lignes |
|---|---|
| Lignes du fichier brut | {stats['lignes_brutes']} |
| Lignes exclues (`moneydata_exclus.csv`) | {len(exclues)} |
| Dépenses gardées (`moneydata_propre.csv`) | {len(gardees)} |

## 2. Valeurs converties

| Correction | Lignes |
|---|---|
| Dates Excel avec jour et mois inversés, remis en ordre | {stats['dates_jour_mois_inverses']} |
| Libellés avec espaces multiples réduits | {stats['libelles_espaces_corriges']} |
| Catégories avec espace final (« Groceries  ») | {stats['categories_espaces_corriges']} |
| Catégories vides, notées VIDE | {stats['categories_vides']} |
| Types de paiement vides, notés INCONNU | {stats['types_vides']} |
| Particuliers remplacés par un pseudonyme (PARTICULIER_nnn) | {stats['particuliers_pseudonymises']} |

Écart avec la feuille de description des auteurs : le fichier utilise les codes
`DD` et `CPT`, la feuille annonce `D/D` et `C/P`. Les codes sont gardés tels quels.

## 3. Lignes retirées (par règle)

{tableau(Counter(e['regle'] + ' — ' + e['motif'] for e in exclues), 'Règle — motif')}

## 4. Catégorie finale des dépenses gardées

{tableau(Counter(g['categorie_finale'] for g in gardees), 'Lettre')}

## 5. D'où vient la catégorie (donnée connue ou corrigée)

{tableau(Counter(g['provenance'] for g in gardees), 'Provenance')}

- `origine` : lettre déduite de la catégorie donnée par les auteurs du jeu.
- `commercant` : **notre correction**, fondée sur l'identification du commerçant
  dans le libellé (`data/regles_commercants.csv`), pas sur une information de la banque.
- `non_identifie` : `?`, la ligne demandera une confirmation.

## 6. Corrections et mises en `?` décidées à partir du libellé

| Catégorie d'origine | Lettre finale | Justification | Lignes |
|---|---|---|---|
""" + "\n".join(f"| {o} | {l} | {j} | {n} |" for (o, l, j), n in corrections.most_common()) + "\n"
    chemin.write_text(texte, encoding="utf-8")


def main(argv):
    chemin_brut = Path(argv[1]) if len(argv) > 1 else FICHIER_BRUT
    gardees, exclues, stats = nettoyer(chemin_brut)
    ecrire_csv(DOSSIER_DATA / "moneydata_propre.csv", gardees)
    ecrire_csv(DOSSIER_DATA / "moneydata_exclus.csv", exclues)
    ecrire_journal(DOSSIER_DATA / "journal_nettoyage.md", gardees, exclues, stats)
    print(f"{len(gardees)} dépenses gardées, {len(exclues)} lignes exclues.")


if __name__ == "__main__":
    main(sys.argv)
