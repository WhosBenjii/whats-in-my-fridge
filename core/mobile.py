"""Transforme l'appli en « appli de téléphone » quand on l'ajoute à l'écran d'accueil.

Sur iPhone (Safari : Partager → Sur l'écran d'accueil) et sur Android (Chrome : Installer
l'application), le téléphone a besoin de quelques informations dans la page :
une icône, un nom, une couleur et le mode plein écran. C'est ce que ce fichier ajoute.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st

DOSSIER = Path(__file__).resolve().parent.parent / "assets"
NOM = "What's in my Fridge"
COULEUR = "#177A54"      # couleur de la barre du téléphone
FOND = "#F6F7F5"         # couleur de l'écran de démarrage


def _image(nom: str) -> str:
    """L'image en texte (base64), pour la glisser directement dans la page."""
    fichier = DOSSIER / nom
    if not fichier.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(fichier.read_bytes()).decode()


def activer_mode_app() -> None:
    """À appeler une fois au démarrage de l'appli."""
    icone, grande = _image("icone-180.png"), _image("icone-512.png")
    if not icone:
        return

    manifeste = {
        "name": NOM,
        "short_name": "Fridge",
        "start_url": ".",
        "display": "standalone",       # plein écran, sans la barre du navigateur
        "background_color": FOND,
        "theme_color": COULEUR,
        "icons": [
            {"src": icone, "sizes": "180x180", "type": "image/png"},
            {"src": grande or icone, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    lien_manifeste = "data:application/manifest+json;base64," + base64.b64encode(
        json.dumps(manifeste).encode()).decode()

    script = f"""
<script>
(function () {{
  const page = window.parent.document;

  function baliseMeta(nom, valeur) {{
    let e = page.querySelector(`meta[name="${{nom}}"]`);
    if (!e) {{ e = page.createElement("meta"); e.setAttribute("name", nom); page.head.appendChild(e); }}
    e.setAttribute("content", valeur);
  }}
  function baliseLien(relation, adresse, extra) {{
    let e = page.querySelector(`link[rel="${{relation}}"]`);
    if (!e) {{ e = page.createElement("link"); e.setAttribute("rel", relation); page.head.appendChild(e); }}
    e.setAttribute("href", adresse);
    if (extra) Object.entries(extra).forEach(([k, v]) => e.setAttribute(k, v));
  }}

  // iPhone : icône, nom sous l'icône, plein écran
  baliseLien("apple-touch-icon", {icone!r}, {{sizes: "180x180"}});
  baliseMeta("apple-mobile-web-app-capable", "yes");
  baliseMeta("apple-mobile-web-app-title", {NOM!r});
  baliseMeta("apple-mobile-web-app-status-bar-style", "default");
  // Android : installation depuis Chrome
  baliseMeta("mobile-web-app-capable", "yes");
  baliseMeta("theme-color", {COULEUR!r});
  baliseLien("manifest", {lien_manifeste!r});

  // Laisser la place à l'encoche et à la barre du bas de l'iPhone
  const vue = page.querySelector('meta[name="viewport"]');
  if (vue && !vue.content.includes("viewport-fit")) {{
    vue.setAttribute("content", vue.content + ", viewport-fit=cover");
  }}
  page.title = {NOM!r};
}})();
</script>
"""
    if hasattr(st, "iframe"):          # Streamlit récent
        st.iframe(script, height=1, width=1)
    else:                               # anciennes versions
        import streamlit.components.v1 as components
        components.html(script, height=0, width=0)
