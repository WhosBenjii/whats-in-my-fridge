"""Télécharge une VRAIE photo adaptée pour chaque recette, dans le dossier images/.

Utilisation :  export PIXABAY_API_KEY="ta_clé"   puis   python telecharger_photos.py
Pour refaire toutes les photos :  python telecharger_photos.py --tout

Pour chaque recette, on essaie plusieurs recherches, on regarde les mots-clés de chaque photo
et on garde la meilleure. Si aucune ne correspond vraiment, on ne télécharge rien :
l'appli garde alors le dessin (mieux qu'une fausse photo).
"""
import os
import re
import sys

import requests

from core.catalogue import DOSSIER_PHOTOS, RECETTES, slug

CLE = os.environ.get("PIXABAY_API_KEY")
if not CLE:
    sys.exit('Il manque la clé : export PIXABAY_API_KEY="ta_clé"')
DOSSIER_PHOTOS.mkdir(exist_ok=True)
TOUT_REFAIRE = "--tout" in sys.argv
MOTS_INUTILES = {"with", "and", "the", "of", "in", "on", "a", "de", "au", "aux", "et", "la", "le", "les", "du", "des"}
# Mots de recherche précis pour les plats difficiles (en plus de ceux calculés automatiquement)
RECHERCHES_FORCEES = {
    "Croque-monsieur": ["croque monsieur", "ham cheese toasted sandwich", "grilled ham and cheese sandwich"],
    "Vegetable tart": ["vegetable tart", "vegetable quiche", "savory tart"],
    "Potato and tuna fish cakes": ["tuna fish cakes", "fish cakes", "tuna patties"],
    "Cod and vegetable tray bake": ["baked cod fish", "cod fillet vegetables", "fish tray bake"],
    "Zucchini fritters": ["zucchini fritters", "courgette fritters", "zucchini pancakes"],
    "Egg fried noodles": ["egg fried noodles", "noodles with egg", "stir fried noodles"],
    "Shakshuka": ["shakshuka", "eggs in tomato sauce"],
    "Tabbouleh": ["tabbouleh", "tabouli salad", "parsley bulgur salad"],
    "Stuffed bell peppers": ["stuffed bell peppers", "stuffed peppers"],
    "Fish soup": ["fish soup", "seafood soup", "fish stew"],
    "Mussels in white wine": ["mussels white wine", "moules marinieres", "steamed mussels"],
    "Chicken and veggie stir-fry": ["chicken vegetable stir fry", "chicken stir fry"],
}
GENERIQUE = {"Veg": ["vegetarian meal", "vegetable dish"], "Mea": ["meat dish", "dinner plate meat"], "Fis": ["fish dish", "seafood plate"]}


def mots(texte: str) -> list[str]:
    return [m for m in re.findall(r"[a-zà-ÿ]+", texte.lower()) if len(m) > 2 and m not in MOTS_INUTILES]


def recherches(nom: str) -> list[str]:
    base = " ".join(mots(nom))
    return RECHERCHES_FORCEES.get(nom, []) + [f"{base} dish", base, f"{base} food", f"{base} recipe plate"]


def note(photo: dict, voulus: list[str]) -> float:
    """Plus la note est haute, plus la photo correspond au plat (on lit les mots-clés « tags »)."""
    tags = photo.get("tags", "").lower()
    score = sum(1 for m in voulus if m in tags) / max(1, len(voulus))
    if any(m in tags for m in ("food", "dish", "meal", "plate", "cooking", "dinner", "lunch")):
        score += 0.15
    if photo.get("imageWidth", 0) >= 1000:
        score += 0.05
    return score


def candidats(requetes: list[str]) -> list[dict]:
    """Toutes les photos trouvées par ces recherches (2 pages chacune), sans doublons."""
    vus, resultat = set(), []
    for q in requetes:
        for page in (1, 2):
            rep = requests.get("https://pixabay.com/api/", timeout=20, params={
                "key": CLE, "q": q, "image_type": "photo", "orientation": "horizontal", "category": "food",
                "per_page": 50, "page": page, "safesearch": "true", "order": "popular"})
            if rep.status_code == 400:  # page inexistante
                break
            rep.raise_for_status()
            for p in rep.json().get("hits", []):
                if p["id"] not in vus:
                    vus.add(p["id"]); resultat.append(p)
    return resultat


def meilleure_photo(nom: str, categorie: str):
    """Renvoie (photo, note, niveau). Niveau : 1 = très bonne, 2 = correcte, 3 = approximative, 4 = générique."""
    voulus = mots(nom)
    toutes = candidats(recherches(nom))
    classees = sorted(((note(p, voulus), p) for p in toutes), key=lambda x: -x[0])
    for seuil, niveau in ((0.95, 1), (0.6, 2), (0.35, 3)):
        if classees and classees[0][0] >= seuil:
            return classees[0][1], classees[0][0], niveau
    generiques = candidats(GENERIQUE[categorie])
    return (generiques[0], 0.0, 4) if generiques else (None, 0.0, 0)


ETIQUETTE = {1: "OK", 2: "OK (correcte)", 3: "APPROXIMATIVE, à vérifier", 4: "GÉNÉRIQUE, à remplacer si tu peux", 0: "RIEN TROUVÉ"}
for r in RECETTES:
    fichier = DOSSIER_PHOTOS / f"{slug(r['nom'])}.jpg"
    if fichier.exists() and not TOUT_REFAIRE:
        continue
    try:
        photo, s, niveau = meilleure_photo(r["nom"], r["categorie"][:3].capitalize())
        if not photo:
            print(f"RIEN TROUVÉ : {r['nom']} (le dessin reste). Mets la tienne dans images/{fichier.name}")
            continue
        img = requests.get(photo["webformatURL"], timeout=30)
        img.raise_for_status()
        fichier.write_bytes(img.content)
        print(f"{ETIQUETTE[niveau]} : {r['nom']} - mots-clés : {photo['tags']} - photo de {photo['user']}")
    except requests.RequestException as e:
        print("Erreur :", r["nom"], e)
