"""Combien de jours un aliment se garde, quand l'IA ne le dit pas.

Ce sont des durées habituelles, au frigo, pour un produit déjà ouvert ou frais.
En cas de doute, on prend la durée la plus courte : mieux vaut cuisiner trop tôt que jeter.
"""
from __future__ import annotations

# (mots dans le nom, nombre de jours)
DUREES = [
    (("leftover", "cooked", "rest of", "soup"), 2),
    (("fish", "salmon", "cod", "tuna", "prawn", "shrimp", "mussel", "mince", "ground beef"), 2),
    (("chicken", "pork", "beef", "lamb", "sausage", "bacon", "ham", "meat", "steak"), 3),
    (("salad", "lettuce", "spinach", "rocket", "herb", "basil", "parsley", "coriander", "mushroom",
      "berry", "berries", "strawberr", "raspberr"), 3),
    (("milk", "cream", "yoghurt", "yogurt", "juice", "tofu"), 5),
    (("tomato", "cucumber", "zucchini", "courgette", "pepper", "broccoli", "cauliflower", "green bean",
      "grape", "peach", "banana", "avocado", "bread"), 6),
    (("cheese", "butter", "egg", "ham slice", "olive", "pasta sauce", "hummus"), 14),
    (("carrot", "potato", "onion", "garlic", "cabbage", "apple", "orange", "lemon", "beet", "squash",
      "pumpkin", "rice", "pasta", "flour", "jam", "mustard", "ketchup"), 25),
]
PAR_DEFAUT = 5


def jours_estimes(nom: str) -> int:
    """Nombre de jours avant péremption, deviné d'après le nom de l'aliment."""
    minuscule = nom.lower()
    for mots, jours in DUREES:
        if any(m in minuscule for m in mots):
            return jours
    return PAR_DEFAUT


def jours_valides(aliment: dict) -> int:
    """Prend la durée donnée par l'IA si elle est crédible, sinon celle devinée par le nom."""
    try:
        jours = int(aliment.get("jours") or 0)
    except (TypeError, ValueError):
        jours = 0
    if 1 <= jours <= 365:
        return jours
    return jours_estimes(str(aliment.get("nom", "")))
