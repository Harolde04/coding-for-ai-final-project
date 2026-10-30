"""Règles imposées par le code (brique 3).

Ce que le système ne doit JAMAIS faire, quoi que dise Qwen ou son prompt :

- G1 enregistrer un montant invalide (négatif, nul, absent, non numérique) ;
- G2 enregistrer un montant différent de celui écrit dans le texte ;
- G3 enregistrer une catégorie hors de A, B, C, D, E ;
- G4 enregistrer sans confirmation une dépense que le juge n'a pas jugée sûre ;
- G5 enregistrer sans confirmation un virement ou un paiement par intermédiaire
  (Lydia, PayPal, virement, remboursement), même si le score de Qwen est élevé :
  l'objet de la dépense est inconnu (règles R-X1 et R-X2).

Toute dépense passe par `verifier_enregistrement` avant d'être enregistrée.
Une règle enfreinte lève `EnregistrementRefuse`, avec son code (G1…G5).
"""
import re
from decimal import Decimal, InvalidOperation

LETTRES = ("A", "B", "C", "D", "E")

# Intermédiaires de paiement et transferts entre personnes (R-X1, R-X2).
TRANSFERT = re.compile(
    r"\b(lydia|paypal|paylib|wero|virement|vir[ée]|rembours\w*|western union)\b",
    re.IGNORECASE,
)

# « 9€50 » : euros et centimes de part et d'autre du symbole.
_MONTANT_COLLE = re.compile(r"(?<![\d,.])(-\s*)?(\d+)\s*€\s*(\d{2})\b")
# « 12 € », « 3,30 € », « 2.40€ », « 18,90 euros », « 1 200 € », « -10 € ».
_MONTANT = re.compile(
    r"(?<![\d,.])(-\s*)?(\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,](\d{1,2}))?\s*(?:€|euros?\b|eur\b)",
    re.IGNORECASE,
)


class EnregistrementRefuse(Exception):
    """Une règle du code bloque l'enregistrement."""

    def __init__(self, code, motif):
        super().__init__(f"{code} : {motif}")
        self.code = code
        self.motif = motif


def extraire_montant(texte):
    """Lit le montant en euros écrit dans le texte. Refuse s'il n'y en a pas
    exactement un, ou s'il est négatif ou nul."""
    trouves = []
    reste = texte
    for motif in (_MONTANT_COLLE, _MONTANT):
        for m in motif.finditer(reste):
            signe, entier, decimales = m.group(1), m.group(2), m.group(3)
            valeur = Decimal(re.sub(r"[ \u00a0]", "", entier) + "." + (decimales or "0").ljust(2, "0"))
            trouves.append(-valeur if signe else valeur)
        reste = motif.sub(" ", reste)  # « 9€50 » ne doit pas être relu comme « 9 € »
    if not trouves:
        raise EnregistrementRefuse("G1", "aucun montant en euros dans le texte")
    if len(trouves) > 1:
        raise EnregistrementRefuse("G1", f"plusieurs montants dans le texte : {trouves}")
    return valider_montant(trouves[0])


def valider_montant(valeur):
    """Convertit en Decimal à 2 décimales et refuse tout montant invalide."""
    if valeur is None or isinstance(valeur, bool) or (isinstance(valeur, str) and not valeur.strip()):
        raise EnregistrementRefuse("G1", "montant absent")
    try:
        montant = Decimal(str(valeur).strip().replace(",", "."))
    except InvalidOperation:
        raise EnregistrementRefuse("G1", f"montant non numérique : {valeur!r}") from None
    if not montant.is_finite():
        raise EnregistrementRefuse("G1", f"montant non numérique : {valeur!r}")
    if montant <= 0:
        raise EnregistrementRefuse("G1", f"montant négatif ou nul : {montant}")
    if montant != montant.quantize(Decimal("0.01")):
        raise EnregistrementRefuse("G1", f"plus de deux décimales : {montant}")
    return montant.quantize(Decimal("0.01"))


def confirmation_obligatoire(texte):
    """Renvoie le motif si le texte impose une confirmation (G5), sinon None."""
    m = TRANSFERT.search(texte)
    return f"transfert ou intermédiaire de paiement : « {m.group(0)} »" if m else None


def decision_finale(texte, decision_juge):
    """La décision du juge, sauf si le code impose une confirmation (G5)."""
    return "confirmer" if confirmation_obligatoire(texte) else decision_juge


def verifier_enregistrement(texte, montant_propose, categorie, decision_juge, confirme_par_utilisateur=False):
    """Seul point d'entrée vers l'enregistrement. Renvoie la dépense validée
    ou lève EnregistrementRefuse.

    - montant_propose : le montant que le modèle veut enregistrer ;
    - decision_juge : « auto » ou « confirmer » (brique 4) ;
    - confirme_par_utilisateur : True si l'utilisateur a validé la catégorie.
    """
    montant_texte = extraire_montant(texte)                      # G1
    montant = valider_montant(montant_propose)                    # G1
    if montant != montant_texte:                                  # G2
        raise EnregistrementRefuse("G2", f"montant proposé {montant} ≠ montant du texte {montant_texte}")
    if categorie not in LETTRES:                                  # G3
        raise EnregistrementRefuse("G3", f"catégorie hors A–E : {categorie!r}")
    if not confirme_par_utilisateur:
        if decision_juge != "auto":                               # G4
            raise EnregistrementRefuse("G4", "le juge demande une confirmation")
        motif = confirmation_obligatoire(texte)                   # G5
        if motif:
            raise EnregistrementRefuse("G5", motif)
    return {"texte": texte, "montant": montant, "categorie": categorie}
