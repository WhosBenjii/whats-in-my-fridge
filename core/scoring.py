"""Règles de points et de niveaux (simples et faciles à modifier)."""
from __future__ import annotations

from datetime import date, timedelta

MANCHES = {
    1: "Round 1 · Simple dishes (level 1 to 3)",
    2: "Round 2 · Intermediate dishes (level 4 to 6)",
    3: "Round 3 · Elaborate dishes (level 7 to 10)",
}

POINTS_PAR_NIVEAU_JOUEUR = 250  # points nécessaires pour monter d'un niveau
KG_PAR_ALIMENT_SAUVE = 0.2  # estimation : poids moyen d'un aliment sauvé


def manche_du_niveau(niveau: int) -> int:
    if niveau <= 3:
        return 1
    if niveau <= 6:
        return 2
    return 3


def points_plat(niveau: int, nb_ingredients_sauves: int) -> int:
    """Plus le plat est élaboré, plus il rapporte. Chaque aliment sauvé donne un bonus."""
    return niveau * 10 + nb_ingredients_sauves * 2


def taux_gaspillage(utilises: int, jetes: int) -> float:
    """Pourcentage d'aliments jetés. 0 % = aucun gaspillage."""
    total = utilises + jetes
    if total == 0:
        return 0.0
    return round(100 * jetes / total, 1)


def score_anti_gaspi(utilises: int, jetes: int) -> float:
    """Score affiché dans l'application : 100 % = rien de jeté."""
    return round(100 - taux_gaspillage(utilises, jetes), 1)


def titre_selon_score(score: float | None) -> str:
    if score is None:
        return "Newcomer"
    if score >= 90:
        return "Zero-Waste Chef"
    if score >= 75:
        return "Smart Cook"
    return "Apprentice Cook"


def niveau_joueur(points: int) -> tuple[int, int]:
    """Renvoie (niveau, pourcentage de progression vers le niveau suivant)."""
    niveau = 1 + points // POINTS_PAR_NIVEAU_JOUEUR
    progression = round(100 * (points % POINTS_PAR_NIVEAU_JOUEUR) / POINTS_PAR_NIVEAU_JOUEUR)
    return niveau, progression


def kg_evites(aliments_sauves: int) -> float:
    return round(aliments_sauves * KG_PAR_ALIMENT_SAUVE, 1)


def debut_de_semaine(aujourdhui: date | None = None) -> str:
    """Date (texte AAAA-MM-JJ) du lundi de la semaine en cours."""
    jour = aujourdhui or date.today()
    return (jour - timedelta(days=jour.weekday())).isoformat()


def jours_restants_semaine(aujourdhui: date | None = None) -> int:
    """Nombre de jours avant la fin du défi hebdomadaire (dimanche)."""
    jour = aujourdhui or date.today()
    return 6 - jour.weekday()
