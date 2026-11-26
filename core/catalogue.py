"""Les 33 idées de recettes (végétarien, viande, poisson) avec leur petite illustration dessinée."""
from __future__ import annotations

import base64
import functools
import math
import re
from pathlib import Path
import random

CATEGORIES = {"veg": "Vegetarian", "meat": "Meat", "fish": "Fish"}

_ASSIETTE = '<circle cx="40" cy="40" r="38" fill="#FFFFFF"/>'


def _svg(interieur: str, taille: int = 72) -> str:
    return f'<svg aria-hidden="true" width="{taille}" height="{taille}" viewBox="0 0 80 80">{_ASSIETTE}{interieur}</svg>'


def _soupe(fond, accent):
    points = "".join(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{accent}"/>'
                     for x, y in [(32, 30), (48, 32), (40, 50), (30, 48), (52, 46), (40, 28)])
    return (f'<circle cx="40" cy="40" r="31" fill="#EFEAE0"/><circle cx="40" cy="40" r="26" fill="{fond}"/>'
            f'<path d="M26 40 q14 -12 28 0" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="3" stroke-linecap="round"/>{points}')


def _morceaux(fond, couleurs, n=14, taille=3.2, graine=1):
    r, sortie = random.Random(graine), ""
    for i in range(n):
        a, d = r.random() * 6.283, r.random() ** 0.5 * 21
        x, y, c = 40 + d * math.cos(a), 40 + d * math.sin(a), couleurs[i % len(couleurs)]
        if i % 2 == 0:
            sortie += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{taille}" fill="{c}"/>'
        else:
            sortie += (f'<rect x="{x - taille:.1f}" y="{y - taille:.1f}" width="{2 * taille}" height="{2 * taille}" rx="1.2" '
                       f'fill="{c}" transform="rotate({int(r.random() * 90)} {x:.1f} {y:.1f})"/>')
    return f'<circle cx="40" cy="40" r="31" fill="#F3EEE3"/><circle cx="40" cy="40" r="27" fill="{fond}"/>{sortie}'


def _tarte(croute, garniture, dessus, graine=1):
    r, sortie = random.Random(graine), ""
    for i in range(8):
        a, d = r.random() * 6.283, r.random() ** 0.5 * 19
        x, y = 40 + d * math.cos(a), 40 + d * math.sin(a)
        sortie += (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="6" ry="3.2" fill="{dessus[i % len(dessus)]}" '
                   f'transform="rotate({int(r.random() * 180)} {x:.1f} {y:.1f})"/>')
    return f'<circle cx="40" cy="40" r="31" fill="{croute}"/><circle cx="40" cy="40" r="26" fill="{garniture}"/>{sortie}'


def _pile(dessus, bord, garniture=None):
    g = "".join(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{garniture}"/>'
                for x, y in [(30, 32), (50, 32), (28, 46), (52, 46), (40, 52)]) if garniture else ""
    return (f'<circle cx="40" cy="52" r="24" fill="{bord}"/><circle cx="40" cy="45" r="24" fill="{bord}"/>'
            f'<circle cx="40" cy="38" r="24" fill="{dessus}"/>{g}<rect x="34" y="33" width="12" height="8" rx="2" fill="#F6E27A"/>')


def _omelette():
    herbes = "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#4E9A6B"/>' for x, y in [(26, 40), (38, 32), (50, 38), (58, 43), (34, 43)])
    return f'<path d="M10 48 A30 26 0 0 1 70 48 Z" fill="#F2CF5B"/><path d="M10 48 H70" stroke="#E0B840" stroke-width="2"/>{herbes}'


def _sandwich():
    return ('<g transform="rotate(-12 40 40)"><rect x="17" y="21" width="46" height="38" rx="7" fill="#E3B766"/>'
            '<rect x="21" y="25" width="38" height="30" rx="5" fill="#F0CF8A"/><rect x="21" y="37" width="38" height="7" fill="#F5D76E"/></g>')


def _poivrons():
    p = "".join(f'<circle cx="{x}" cy="{y}" r="12" fill="#D9573E"/><circle cx="{x}" cy="{y}" r="6.5" fill="#F6EBC9"/>'
                f'<circle cx="{x}" cy="{y}" r="2" fill="#4E9A6B"/>' for x, y in [(29, 31), (52, 31), (40, 53)])
    return f'<circle cx="40" cy="40" r="31" fill="#F3EEE3"/>{p}'


def _boules(couleur):
    return (f'<circle cx="40" cy="40" r="31" fill="#F3EEE3"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="{couleur}"/>' for x, y in [(30, 32), (50, 32), (28, 50), (52, 50), (40, 41)]))


_V, _P, _G, _S = "#F7F1D9", "#F8E8DF", "#E3F1E9", "#F3EEE3"  # teintes de fond des cartes

# (catégorie, nom, minutes, illustration, teinte)
_RECETTES = [
    ("veg", "Vegetable omelette", 15, _omelette(), _V),
    ("veg", "Tomato and basil soup", 30, _soupe("#E2674A", "#4E9A6B"), _P),
    ("veg", "Ratatouille", 50, _morceaux("#F7F1E4", ["#7A3B6E", "#4E9A6B", "#D9573E", "#F0B24B"], 16, 3.4, 2), _G),
    ("veg", "Mushroom risotto", 40, _soupe("#F3E6C0", "#A8896A"), _S),
    ("veg", "Greek salad", 10, _morceaux("#F7F1E4", ["#D9573E", "#8DB86B", "#FFFFFF", "#5B3A5A"], 14, 3.6, 4), _G),
    ("veg", "Potato gratin", 60, _tarte("#C98B3C", "#F2D98B", ["#E8B04A", "#F7E7A9"], 5), _V),
    ("veg", "Zucchini fritters", 25, _morceaux("#FFFFFF", ["#B7C97A", "#9DB35E"], 6, 6.5, 6), _G),
    ("veg", "Lentil curry", 35, _soupe("#C9843A", "#F4E6B0"), _S),
    ("veg", "Shakshuka", 25, _soupe("#D9573E", "#F0C84B"), _P),
    ("veg", "Pumpkin soup", 40, _soupe("#E8913A", "#FFFFFF"), _P),
    ("veg", "Stuffed bell peppers", 70, _poivrons(), _S),
    ("veg", "French toast", 15, _pile("#D9A25A", "#E8C58A"), _V),
    ("veg", "Vegetable tart", 45, _tarte("#D9B26B", "#F4E6B0", ["#D9573E", "#4E9A6B", "#F0B24B"], 8), _G),
    ("veg", "Carrot and cumin soup", 30, _soupe("#EE9A45", "#4E9A6B"), _P),
    ("veg", "Egg fried noodles", 20, _morceaux("#F7F1E4", ["#E8C56A", "#F0C84B", "#4E9A6B"], 18, 2.6, 9), _V),
    ("veg", "Tabbouleh", 20, _morceaux("#F7F1E4", ["#4E9A6B", "#D9573E", "#E8D8A8"], 24, 2.4, 10), _G),
    ("veg", "Banana pancakes", 20, _pile("#E3B766", "#EBCB8A", "#F5E39A"), _S),
    ("meat", "Chicken and veggie stir-fry", 25, _morceaux("#F3E7CF", ["#F0D9A8", "#4E9A6B", "#D9573E", "#F0B24B"], 16, 3.4, 3), _S),
    ("meat", "Croque-monsieur", 15, _sandwich(), _V),
    ("meat", "Roast chicken and potatoes", 70, _morceaux("#F3E7CF", ["#C98B3C", "#E8B04A", "#F2D98B"], 12, 5, 13), _S),
    ("meat", "Spaghetti bolognese", 45, _soupe("#9C4B2E", "#F0C84B"), _P),
    ("meat", "Chili con carne", 50, _soupe("#A63A2A", "#F0C84B"), _P),
    ("meat", "Beef and vegetable stew", 90, _soupe("#7A4A30", "#E8913A"), _S),
    ("meat", "Pork chops with mushrooms", 30, _morceaux("#F7F1E4", ["#C98B6B", "#E8D8A8", "#A8896A"], 10, 5.5, 14), _V),
    ("meat", "Meatballs in tomato sauce", 40, _boules("#9C4B2E"), _P),
    ("fish", "Tuna pasta salad", 20, _morceaux("#F7F1E4", ["#E8C56A", "#D9573E", "#9DB35E", "#C9D4DC"], 18, 3.2, 7), _G),
    ("fish", "Baked salmon with lemon", 25, _morceaux("#F7F1E4", ["#F4A58A", "#F6E27A", "#4E9A6B"], 9, 5.5, 15), _P),
    ("fish", "Cod and vegetable tray bake", 35, _morceaux("#F7F1E4", ["#F4F1EA", "#D9573E", "#E8C56A", "#4E9A6B"], 14, 3.8, 11), _G),
    ("fish", "Potato and tuna fish cakes", 25, _boules("#D9B26B"), _V),
    ("fish", "Salmon and broccoli pasta", 25, _morceaux("#F3E6C0", ["#F4B8A0", "#4E9A6B"], 16, 3, 16), _P),
    ("fish", "Prawn fried rice", 20, _morceaux("#F7F1E4", ["#F6B08A", "#F0C84B", "#4E9A6B"], 18, 2.8, 12), _V),
    ("fish", "Fish soup", 50, _soupe("#E2674A", "#F4B8A0"), _P),
    ("fish", "Mussels in white wine", 25, _morceaux("#F3EEE3", ["#3B3F4A", "#F4B8A0", "#4E9A6B"], 12, 4.5, 17), _G),
]

RECETTES = [
    {"categorie": c, "nom": n, "minutes": m, "svg": _svg(i), "teinte": t, "niveau": min(10, max(1, m // 9 + 1))}
    for c, n, m, i, t in _RECETTES
]
assert len(RECETTES) == 33


DOSSIER_PHOTOS = Path(__file__).resolve().parent.parent / "images"


def slug(nom: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")


@functools.lru_cache(maxsize=128)
def photo(nom: str) -> str | None:
    """Renvoie une balise <img> si une photo existe dans images/, sinon None."""
    f = DOSSIER_PHOTOS / f"{slug(nom)}.jpg"
    if not f.exists():
        return None
    data = base64.b64encode(f.read_bytes()).decode()
    return f'<img alt="" src="data:image/jpeg;base64,{data}" style="width:100%;height:100%;object-fit:cover;display:block">'


def illustration(nom: str, taille: int = 72) -> tuple[str, str]:
    """Renvoie (svg, teinte) pour un plat ; une assiette vide si le plat n'est pas dans la liste."""
    for r in RECETTES:
        if r["nom"].lower() == nom.lower():
            if photo(nom):
                return photo(nom), r["teinte"]
            return r["svg"].replace('width="72" height="72"', f'width="{taille}" height="{taille}"'), r["teinte"]
    return _svg(_soupe("#B7C97A", "#4E9A6B"), taille), _G


def plat_depuis_recette(r: dict) -> dict:
    """Transforme une idée de la liste en « plat » comprenable par l'IA (même format que proposer_plats)."""
    return {"nom": r["nom"], "description": f'{CATEGORIES[r["categorie"]]} idea', "niveau_elaboration": r["niveau"],
            "temps_minutes": r["minutes"], "ingredients_utilises": [], "ingredients_manquants": []}
