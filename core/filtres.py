"""Dit si une recette va avec les appareils, le régime et les allergies de l'utilisateur.

On devine les besoins d'une recette à partir de son nom et de sa catégorie :
- l'appareil (four, poêle, casserole, mixeur…) ;
- si elle contient de la viande ou du poisson ;
- les allergènes les plus courants (lait, gluten, œufs, fruits de mer, poisson, fruits à coque).
"""
from __future__ import annotations

# mot dans le nom de la recette -> appareil nécessaire
APPAREILS = {
    "Oven": ("gratin", "roast", "baked", "tart", "bake", "peppers", "shakshuka"),
    "Blender": ("soup",),
    "Pan": ("omelette", "fritters", "pancakes", "french toast", "stir-fry", "chops", "croque",
            "fried", "cakes", "risotto", "meatballs", "shakshuka"),
    "Saucepan": ("soup", "pasta", "curry", "stew", "chili", "noodles", "rice", "mussels", "bolognese", "sauce"),
}
# mot dans le nom -> allergène
ALLERGENES = {
    "Milk": ("gratin", "croque", "risotto", "cheese", "french toast", "pancakes", "greek salad"),
    "Gluten": ("pasta", "spaghetti", "noodles", "toast", "croque", "tart", "tabbouleh", "pancakes", "bolognese"),
    "Eggs": ("omelette", "shakshuka", "french toast", "pancakes", "fried noodles", "fried rice", "meatballs"),
    "Shellfish": ("prawn", "mussels"),
    "Fish": ("salmon", "cod", "tuna", "fish"),
    "Nuts": ("pesto",),
}
# régime -> ce qui est interdit (catégories de recettes)
INTERDITS = {
    "Vegetarian": ("meat", "fish"),
    "Vegan": ("meat", "fish"),
    "Halal": ("pork",),
    "Kosher": ("pork", "shellfish"),
}
PORC = ("pork", "bacon", "ham", "croque", "chorizo")
LAIT_OU_OEUF = ("Milk", "Eggs")


def _mots(recette: dict) -> str:
    return recette.get("nom", "").lower()


def appareils_necessaires(recette: dict) -> list[str]:
    """Les appareils dont la recette a besoin (au moins un suffit pour cuire : on prend le plus probable)."""
    nom = _mots(recette)
    trouves = [appareil for appareil, mots in APPAREILS.items() if any(m in nom for m in mots)]
    if not trouves:
        return []
    # Une soupe peut se faire sans mixeur : on ne garde le mixeur que s'il est seul.
    if "Blender" in trouves and len(trouves) > 1:
        trouves.remove("Blender")
    return trouves[:1]


def allergenes(recette: dict) -> list[str]:
    nom = _mots(recette)
    liste = [a for a, mots in ALLERGENES.items() if any(m in nom for m in mots)]
    if recette.get("categorie") == "fish" and "Fish" not in liste:
        liste.append("Fish")
    return liste


def contient_porc(recette: dict) -> bool:
    return any(m in _mots(recette) for m in PORC)


def verifier(recette: dict, appareils: list[str], regimes: list[str], allergies: list[str]) -> tuple[bool, str]:
    """Renvoie (est-ce que je peux la cuisiner, raison si non)."""
    for regime in regimes:
        interdits = INTERDITS.get(regime, ())
        if recette.get("categorie") in interdits or ("pork" in interdits and contient_porc(recette)):
            return False, regime
        if regime == "Vegan" and set(allergenes(recette)) & set(LAIT_OU_OEUF):
            return False, "Vegan"
        if regime == "Gluten-free" and "Gluten" in allergenes(recette):
            return False, "Gluten"
        if regime == "Lactose-free" and "Milk" in allergenes(recette):
            return False, "Milk"

    presents = set(allergenes(recette))
    for a in allergies:
        if a in presents:
            return False, f"Contains {a.lower()}"

    besoins = appareils_necessaires(recette)
    manquants = [a for a in besoins if a not in appareils]
    if manquants:
        return False, f"No {manquants[0].lower()}"
    return True, ""


def compter(recettes: list[dict], appareils: list[str], regimes: list[str], allergies: list[str]) -> int:
    return sum(1 for r in recettes if verifier(r, appareils, regimes, allergies)[0])
