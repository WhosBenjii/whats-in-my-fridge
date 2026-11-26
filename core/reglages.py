"""Le robinet de l'IA : combien on a déjà consommé, et comment couper.

But : ne jamais dépasser le budget. Deux sécurités :
1. un nombre total de scans pour toute l'appli (MAX_SCANS_TOTAL) ;
2. une coupure automatique dès que l'IA répond « plus de crédit ».
"""
from __future__ import annotations

import os
from datetime import date

from .base import connexion

MAX_PAR_DEFAUT = 200          # scans au total pour toute l'appli, tant que rien n'est réglé


def initialiser(chemin: str | None = None) -> None:
    with connexion(chemin) as con:
        con.script(
            """
            CREATE TABLE IF NOT EXISTS reglages (
                cle TEXT PRIMARY KEY,
                valeur TEXT NOT NULL
            );
            """
        )


def _lire(cle: str, defaut: str = "", chemin=None) -> str:
    with connexion(chemin) as con:
        ligne = con.execute("SELECT valeur FROM reglages WHERE cle = ?", (cle,)).fetchone()
    return ligne["valeur"] if ligne else defaut


def _ecrire(cle: str, valeur: str, chemin=None) -> None:
    with connexion(chemin) as con:
        con.execute("INSERT INTO reglages (cle, valeur) VALUES (?,?) "
                    "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", (cle, valeur))


def maximum_total() -> int:
    """Nombre de scans autorisés en tout (réglage MAX_SCANS_TOTAL)."""
    brut = os.getenv("MAX_SCANS_TOTAL", "")
    if not brut:
        try:
            import streamlit as st
            brut = str(st.secrets.get("MAX_SCANS_TOTAL", ""))
        except Exception:
            brut = ""
    try:
        return max(0, int(brut))
    except ValueError:
        return MAX_PAR_DEFAUT


def total_scans(chemin=None) -> int:
    """Tous les scans faits depuis le début, par tout le monde."""
    with connexion(chemin) as con:
        if "usage_ia" not in con.tables():
            return 0
        ligne = con.execute("SELECT COALESCE(SUM(nombre), 0) AS n FROM usage_ia").fetchone()
    return int(ligne["n"] or 0)


def bloquer_ia(raison: str, chemin=None) -> None:
    """Coupe l'IA pour tout le monde (plus de crédit, budget atteint…)."""
    _ecrire("ia_bloquee", f"{date.today().isoformat()} | {raison[:200]}", chemin)


def debloquer_ia(chemin=None) -> None:
    with connexion(chemin) as con:
        con.execute("DELETE FROM reglages WHERE cle = ?", ("ia_bloquee",))


def raison_blocage(chemin=None) -> str:
    """Vide si l'IA marche, sinon la date et la raison de la coupure."""
    return _lire("ia_bloquee", "", chemin)


def etat_ia(chemin=None) -> tuple[bool, str, int, int]:
    """(l'IA est-elle utilisable, pourquoi pas, scans faits, maximum)."""
    faits, maxi = total_scans(chemin), maximum_total()
    raison = raison_blocage(chemin)
    if raison:
        return False, "AI scanning is paused: the free budget is used up.", faits, maxi
    if maxi and faits >= maxi:
        return False, "AI scanning is paused: the app reached its free budget.", faits, maxi
    return True, "", faits, maxi
