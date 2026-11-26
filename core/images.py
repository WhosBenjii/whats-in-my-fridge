"""Prépare les photos avant de les envoyer à l'IA.

Deux choses :
- les iPhone enregistrent souvent en HEIC, que l'IA ne lit pas : on convertit en JPEG ;
- une photo de téléphone fait plusieurs méga-octets : on la réduit, c'est plus rapide
  et ça coûte moins cher.
"""
from __future__ import annotations

import io

COTE_MAX = 1400
FORMATS = ["jpg", "jpeg", "png", "webp", "heic", "heif"]

try:                       # permet de lire les photos d'iPhone
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_OK = True
except Exception:
    HEIC_OK = False


def est_heic(nom: str, mime: str) -> bool:
    return nom.lower().endswith((".heic", ".heif")) or "hei" in (mime or "").lower()


def preparer(octets: bytes, mime: str = "", nom: str = "") -> tuple[bytes, str] | None:
    """Renvoie (photo en JPEG, type) prête pour l'IA, ou None si on n'a pas pu la lire."""
    from PIL import Image

    try:
        image = Image.open(io.BytesIO(octets))
        image.load()
    except Exception:
        return None

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    cote = max(image.size)
    if cote > COTE_MAX:
        echelle = COTE_MAX / cote
        image = image.resize((int(image.width * echelle), int(image.height * echelle)), Image.LANCZOS)

    sortie = io.BytesIO()
    image.save(sortie, format="JPEG", quality=85, optimize=True)
    return sortie.getvalue(), "image/jpeg"


def message_heic() -> str:
    return ("This photo is in the iPhone HEIC format and the app cannot read it here. "
            "Install the reader with: pip install pillow-heif, or take the photo with the camera "
            "button below.")
