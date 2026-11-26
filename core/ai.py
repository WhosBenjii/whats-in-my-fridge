"""Tout ce qui parle à l'intelligence artificielle (Claude).

Si aucune clé n'est trouvée (variable ANTHROPIC_API_KEY), l'application passe
en « mode démo » : elle répond avec des exemples fixes, sans rien envoyer sur
internet. Pratique pour tester l'application sans payer.
"""
from __future__ import annotations

import base64
import json
import os

# Haiku : le modèle le moins cher. Un scan coûte environ 0,04 centime.
MODELE = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

# Interrupteur général : quand il est à True, l'appli n'appelle plus l'IA du tout.
_FORCE_DEMO = False

# Mots qui veulent dire « plus de crédit » ou « trop de demandes » dans la réponse d'erreur.
MOTS_CREDIT = ("credit balance", "insufficient", "billing", "payment", "quota", "spend limit",
               "enforced_spend_limit_reached", "rate_limit", "429", "too low")


def cle_api() -> str:
    """La clé de l'IA : variable d'environnement en local, « Secrets » sur Streamlit Cloud."""
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        try:
            import streamlit as st
            cle = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:      # pas de fichier secrets : on reste en mode démo
            cle = ""
    return cle


def forcer_demo(valeur: bool = True) -> None:
    """Coupe (ou rallume) tous les appels à l'IA pour cette session."""
    global _FORCE_DEMO
    _FORCE_DEMO = bool(valeur)


def mode_demo() -> bool:
    return _FORCE_DEMO or not cle_api()


def manque_de_credit(erreur: Exception) -> bool:
    """Dit si l'erreur veut dire « plus de crédit » ou « limite atteinte »."""
    texte = f"{type(erreur).__name__} {erreur}".lower()
    return any(mot in texte for mot in MOTS_CREDIT)


def _client():
    import anthropic

    return anthropic.Anthropic(api_key=cle_api())


def _extraire_json(texte: str):
    """Récupère le premier bloc JSON (liste ou objet) dans la réponse."""
    debuts = [i for i in (texte.find("{"), texte.find("[")) if i >= 0]
    if not debuts:
        raise ValueError("No JSON found in the AI answer")
    debut = min(debuts)
    fin = max(texte.rfind("}"), texte.rfind("]"))
    return json.loads(texte[debut : fin + 1])


def _demander(contenu: list, consigne: str, langue: str):
    reponse = _client().messages.create(
        model=MODELE,
        max_tokens=4000,
        system=(
            consigne
            + f" Write every text value in {langue}. "
            "Answer only with valid JSON, with no text around it. Keep the JSON keys exactly as given."
        ),
        messages=[{"role": "user", "content": contenu}],
    )
    texte = "".join(b.text for b in reponse.content if b.type == "text")
    return _extraire_json(texte)


# ---------------------------------------------------------------- 1. Scanner
def detecter_ingredients(photos: list[tuple[bytes, str]], langue: str = "English") -> list[dict]:
    """photos = liste de (octets_de_l_image, type_mime). Renvoie les aliments vus."""
    if mode_demo():
        return [
            {"nom": "Eggs", "quantite": "6", "jours": 21, "note": "unopened box"},
            {"nom": "Tomatoes", "quantite": "3", "jours": 5, "note": "ripe"},
            {"nom": "Grated cheese", "quantite": "100 g", "jours": 7, "note": "bag already open"},
            {"nom": "Bell pepper", "quantite": "1", "jours": 8, "note": ""},
            {"nom": "Milk", "quantite": "50 cl", "jours": 4, "note": "opened bottle"},
            {"nom": "Leftover rice", "quantite": "200 g", "jours": 2, "note": "cooked leftovers"},
            {"nom": "Onions", "quantite": "2", "jours": 30, "note": ""},
        ]
    contenu = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(octets).decode()},
        }
        for octets, mime in photos
    ]
    contenu.append(
        {
            "type": "text",
            "text": "List every food item and ingredient you can see. For each one, estimate how many days "
            "it can still be kept from today, using what you see (packaging opened or not, how ripe it looks, "
            "cooked leftovers, fresh meat or fish). Format: "
            '[{"nom": "ingredient name", "quantite": "short estimate, e.g. 3, 500 g, 1 bottle", '
            '"jours": 5, "note": "a few words saying why, e.g. opened pack, looks very ripe"}]',
        }
    )
    return _demander(
        contenu,
        "You are an anti food-waste cooking assistant looking at photos of a fridge or a pantry. "
        "Ignore anything that is not food. Be careful with your shelf-life estimates: when in doubt, "
        "give the shorter number of days. Raw meat and fish: 1 to 2 days. Cooked leftovers: 2 to 3 days. "
        "Leafy greens and berries: 3 to 4 days. Milk once opened: 3 to 5 days. Hard cheese, eggs, root "
        "vegetables: 2 to 4 weeks.",
        langue,
    )


# ------------------------------------------------------------ 2. Idées de plats
def proposer_plats(
    ingredients: list[str],
    ustensiles: list[str],
    regime: str = "",
    nombre: int = 5,
    langue: str = "English",
) -> list[dict]:
    if mode_demo():
        base = ingredients[:3] or ["what is left"]
        return [
            {
                "nom": "Fridge omelette",
                "description": "Quick, everything in one pan.",
                "ingredients_utilises": base,
                "ingredients_manquants": ["salt", "pepper"],
                "temps_minutes": 15,
                "niveau_elaboration": 2,
            },
            {
                "nom": "Veggie fried rice",
                "description": "Perfect to finish the leftover rice.",
                "ingredients_utilises": base,
                "ingredients_manquants": ["oil", "soy sauce"],
                "temps_minutes": 25,
                "niveau_elaboration": 4,
            },
            {
                "nom": "Tomato and cheese gratin",
                "description": "Baked in the oven, very comforting.",
                "ingredients_utilises": base,
                "ingredients_manquants": ["mixed herbs"],
                "temps_minutes": 45,
                "niveau_elaboration": 6,
            },
            {
                "nom": "Rice-stuffed peppers",
                "description": "Longer, but beautiful to serve.",
                "ingredients_utilises": base,
                "ingredients_manquants": ["spices"],
                "temps_minutes": 70,
                "niveau_elaboration": 8,
            },
        ][:nombre]
    return _demander(
        [
            {
                "type": "text",
                "text": (
                    f"Available ingredients: {', '.join(ingredients)}.\n"
                    f"Available appliances and utensils: {', '.join(ustensiles) or 'basic ones'}.\n"
                    f"Dietary preferences: {regime or 'none'}.\n"
                    f"Suggest {nombre} dishes, from the simplest to the most elaborate. "
                    "Use as many of the available ingredients as possible. Never suggest a dish that "
                    "needs an appliance missing from the list. Format: "
                    '[{"nom": "", "description": "one sentence", '
                    '"ingredients_utilises": [], "ingredients_manquants": [], '
                    '"temps_minutes": 0, "niveau_elaboration": 1}] '
                    "(niveau_elaboration: integer from 1 = very simple to 10 = very elaborate)."
                ),
            }
        ],
        "You are a chef who fights food waste. Use simple words.",
        langue,
    )


# ------------------------------------------------- 3. Recette + données de santé
def creer_recette(
    plat: dict, ingredients: list[str], ustensiles: list[str], portions: int = 2, langue: str = "English"
) -> dict:
    if mode_demo():
        return {
            "titre": plat["nom"],
            "portions": portions,
            "temps_preparation_minutes": 10,
            "temps_cuisson_minutes": max(plat.get("temps_minutes", 20) - 10, 5),
            "ingredients": [{"nom": n, "quantite": "100 g"} for n in plat["ingredients_utilises"]]
            + [{"nom": n, "quantite": "1 pinch"} for n in plat.get("ingredients_manquants", [])],
            "etapes": [
                "Wash and cut the vegetables.",
                "Heat the pan with a little oil.",
                "Add the ingredients and cook while stirring.",
                "Taste, season, then serve hot.",
            ],
            "astuce_anti_gaspi": "Keep clean peelings to make a stock.",
            "sante": {
                "calories": 420,
                "proteines_g": 22,
                "glucides_g": 35,
                "lipides_g": 20,
                "fibres_g": 5,
                "sucres_g": 6,
            },
        }
    return _demander(
        [
            {
                "type": "text",
                "text": (
                    f"Chosen dish: {plat['nom']} ({plat.get('description', '')}).\n"
                    f"Available ingredients: {', '.join(ingredients)}.\n"
                    f"Available appliances and utensils: {', '.join(ustensiles) or 'basic ones'}.\n"
                    f"Number of servings: {portions}.\n"
                    "Write the full recipe with precise quantities. "
                    "Also give the estimated health values PER SERVING. Format: "
                    '{"titre": "", "portions": 0, "temps_preparation_minutes": 0, '
                    '"temps_cuisson_minutes": 0, '
                    '"ingredients": [{"nom": "", "quantite": ""}], "etapes": [""], '
                    '"astuce_anti_gaspi": "", '
                    '"sante": {"calories": 0, "proteines_g": 0, "glucides_g": 0, '
                    '"lipides_g": 0, "fibres_g": 0, "sucres_g": 0}}'
                ),
            }
        ],
        "You are a chef and a dietitian. Use simple words and short steps.",
        langue,
    )
