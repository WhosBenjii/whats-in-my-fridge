"""Garder la personne connectée quand elle revient sur l'appli.

Le jeton de connexion est rangé dans un petit cookie du navigateur. Au retour,
l'appli le relit toute seule : pas besoin de retaper son e-mail et son mot de passe
pendant 30 jours. Le jeton ne reste pas dans l'adresse de la page.
"""
from __future__ import annotations

import streamlit as st

CLE = "fridge_jeton"
DUREE = 30 * 24 * 3600          # 30 jours, comme la session côté base


def _script(code: str) -> None:
    """Fait tourner un petit bout de JavaScript dans la page, sans rien afficher."""
    html = f"<script>(function(){{try{{const page=window.parent;{code}}}catch(e){{}}}})();</script>"
    if hasattr(st, "iframe"):
        st.iframe(html, height=1, width=1)
    else:                       # anciennes versions de Streamlit
        import streamlit.components.v1 as components
        components.html(html, height=0, width=0)


def memoriser(jeton: str) -> None:
    """Range le jeton dans le navigateur, pour les prochaines visites."""
    _script(f"page.document.cookie = {CLE!r} + '=' + {jeton!r} + "
            f"'; max-age={DUREE}; path=/; SameSite=Lax';")


def oublier() -> None:
    _script(f"page.document.cookie = {CLE!r} + '=; max-age=0; path=/; SameSite=Lax';")


def jeton_du_navigateur() -> str:
    """Le jeton que le navigateur a gardé, s'il y en a un."""
    try:
        return st.context.cookies.get(CLE, "") or ""
    except Exception:           # anciennes versions de Streamlit
        return ""


def nettoyer_adresse() -> None:
    """Enlève le jeton de l'adresse, pour qu'il ne traîne pas dans l'historique."""
    _script(
        """
        const adresse = new URL(page.location.href);
        if (adresse.searchParams.get('s')) {
          adresse.searchParams.delete('s');
          page.history.replaceState({}, '', adresse.toString());
        }
        """
    )