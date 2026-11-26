"""Images dessinées dans le style du logo : gros contours vert foncé, couleurs vives, fond vert clair."""
from __future__ import annotations

TRAIT = "#2E5E1A"   # contour vert foncé du logo
FOND = "#DDF2CC"    # fond vert clair
VERT = "#9BE283"    # portes du frigo
_S = f'stroke="{TRAIT}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"'

_OBJETS = {
    "tomate": (f'<circle cx="50" cy="56" r="31" fill="#E0412F" {_S}/>'
               f'<path d="M34 32 Q50 22 66 32 Q56 40 50 37 Q44 40 34 32Z" fill="#5BB33A" {_S}/>'
               '<path d="M36 52 Q38 44 46 42" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="4" stroke-linecap="round"/>'),
    "carotte": (f'<path d="M26 36 Q44 22 58 38 L90 92 L32 62 Q18 52 26 36Z" fill="#F28C28" {_S}/>'
                f'<path d="M30 26 Q18 12 26 4 M42 28 Q44 12 56 6 M52 34 Q64 20 74 22" fill="none" stroke="#5BB33A" stroke-width="6" stroke-linecap="round"/>'
                f'<path d="M44 46 L54 50 M52 62 L62 66" stroke="{TRAIT}" stroke-width="3" stroke-linecap="round"/>'),
    "pizza": (f'<path d="M10 22 Q50 4 90 22 L50 94 Z" fill="#F8D248" {_S}/>'
              f'<path d="M10 22 Q50 4 90 22 L85 31 Q50 15 15 31Z" fill="#C97B35" {_S}/>'
              f'<circle cx="40" cy="46" r="8" fill="#C8352B" {_S}/><circle cx="62" cy="44" r="8" fill="#C8352B" {_S}/>'
              f'<circle cx="51" cy="68" r="7" fill="#C8352B" {_S}/>'),
    "fromage": (f'<path d="M8 62 L88 34 L92 76 L8 76Z" fill="#F8D248" {_S}/>'
                f'<path d="M8 62 L40 70 L92 56" fill="none" stroke="{TRAIT}" stroke-width="3.5" stroke-linejoin="round"/>'
                f'<circle cx="30" cy="68" r="4" fill="#E8B92E"/><circle cx="62" cy="60" r="4.5" fill="#E8B92E"/><circle cx="76" cy="68" r="3.5" fill="#E8B92E"/>'),
    "brocoli": (f'<rect x="40" y="52" width="20" height="38" rx="8" fill="#B9E08A" {_S}/>'
                f'<circle cx="32" cy="46" r="18" fill="#4EA83A" {_S}/><circle cx="68" cy="46" r="18" fill="#4EA83A" {_S}/>'
                f'<circle cx="50" cy="32" r="19" fill="#5BB33A" {_S}/>'),
    "poisson": (f'<path d="M72 50 L94 30 L94 70Z" fill="#F29B7B" {_S}/>'
                f'<ellipse cx="46" cy="50" rx="36" ry="22" fill="#F5B7A0" {_S}/>'
                f'<circle cx="28" cy="44" r="4" fill="{TRAIT}"/>'
                f'<path d="M50 34 Q56 50 50 66 M62 38 Q67 50 62 62" fill="none" stroke="{TRAIT}" stroke-width="3" stroke-linecap="round"/>'),
    "poulet": (f'<path d="M50 62 L80 88" stroke="{TRAIT}" stroke-width="15" stroke-linecap="round"/>'
               '<path d="M50 62 L80 88" stroke="#F6EEDC" stroke-width="8" stroke-linecap="round"/>'
               f'<circle cx="82" cy="86" r="7" fill="#F6EEDC" {_S}/>'
               f'<path d="M14 40 Q14 12 42 14 Q70 16 66 46 Q62 72 36 66 Q14 62 14 40Z" fill="#D98A4A" {_S}/>'
               '<path d="M26 34 Q30 24 40 24" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="4" stroke-linecap="round"/>'),
    "oeuf": (f'<path d="M50 10 Q80 12 80 56 Q80 90 50 90 Q20 90 20 56 Q20 12 50 10Z" fill="#FFFFFF" {_S}/>'
             f'<circle cx="50" cy="56" r="16" fill="#F8C93A" {_S}/>'),
}


def _frigo(x=0, y=0, echelle=1.0) -> str:
    return (f'<g transform="translate({x} {y}) scale({echelle})">'
            f'<rect x="4" y="4" width="92" height="132" rx="14" fill="#E3F5D6" {_S}/>'
            f'<rect x="12" y="12" width="76" height="46" rx="10" fill="{VERT}" {_S}/>'
            f'<rect x="12" y="66" width="76" height="62" rx="10" fill="{VERT}" {_S}/>'
            f'<ellipse cx="20" cy="35" rx="2.6" ry="12" fill="#E3F5D6" {_S}/><ellipse cx="20" cy="97" rx="2.6" ry="16" fill="#E3F5D6" {_S}/>'
            '</g>')


def objet(nom: str, taille: int = 96) -> str:
    """Un seul dessin (tomate, carotte, pizza, fromage, brocoli, poisson, poulet, oeuf ou frigo)."""
    if nom == "frigo":
        return f'<svg aria-hidden="true" width="{taille * 0.72:.0f}" height="{taille}" viewBox="0 0 100 140">{_frigo()}</svg>'
    return f'<svg aria-hidden="true" width="{taille}" height="{taille}" viewBox="0 0 100 100">{_OBJETS[nom]}</svg>'


def _place(nom: str, x: float, y: float, echelle: float, angle: float = 0) -> str:
    return (f'<g transform="translate({x} {y}) rotate({angle} 50 50) scale({echelle})">{_OBJETS[nom]}</g>')


_PAR_CATEGORIE = {"veg": ("brocoli", "tomate"), "meat": ("poulet", "carotte"), "fish": ("poisson", "oeuf")}


def vignette(categorie: str = "veg", largeur: int = 340, hauteur: int = 150) -> str:
    """Image de remplacement pour une recette sans photo : 2 aliments sur fond vert clair."""
    a, b = _PAR_CATEGORIE.get(categorie, ("brocoli", "tomate"))
    cx, taille = largeur / 2, hauteur * 0.62
    e = taille / 100
    return (f'<svg aria-hidden="true" width="100%" height="{hauteur}" viewBox="0 0 {largeur} {hauteur}" preserveAspectRatio="xMidYMid slice">'
            f'<rect width="{largeur}" height="{hauteur}" fill="{FOND}"/>'
            f'{_place(a, cx - taille * 1.05, hauteur * 0.17, e * 1.15, -10)}{_place(b, cx + taille * 0.1, hauteur * 0.2, e, 12)}</svg>')


def scene_accueil(largeur: int = 340, hauteur: int = 200) -> str:
    """Grande image du logo : le frigo au centre, une pizza, des carottes et une tomate."""
    return (f'<svg aria-hidden="true" width="100%" viewBox="0 0 {largeur} {hauteur}" style="border-radius:20px;display:block">'
            f'<rect width="{largeur}" height="{hauteur}" fill="{FOND}"/>'
            f'{_place("pizza", -22, -8, 1.25, -18)}'
            f'{_frigo(112, 14, 1.18)}'
            f'{_place("carotte", 205, 78, 1.35, 8)}'
            f'{_place("tomate", 232, 6, 0.7, 0)}'
            f'{_place("fromage", 8, 118, 0.8, -6)}</svg>')


# ====================================================================== Plus de dessins (même style que le logo)
_OBJETS.update({
    "citron": (f'<path d="M12 50 Q16 22 50 22 Q84 22 88 50 Q84 78 50 78 Q16 78 12 50Z" fill="#F8E04A" {_S}/>'
               f'<path d="M6 50 L14 46 M94 50 L86 54" stroke="{TRAIT}" stroke-width="4" stroke-linecap="round"/>'
               '<path d="M30 40 Q38 32 48 32" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="4" stroke-linecap="round"/>'),
    "avocat": (f'<path d="M50 6 Q74 8 78 50 Q82 90 50 92 Q18 90 22 50 Q26 8 50 6Z" fill="#6DB33F" {_S}/>'
               f'<path d="M50 24 Q66 26 68 52 Q70 80 50 82 Q30 80 32 52 Q34 26 50 24Z" fill="#E6F0A8" {_S}/>'
               f'<circle cx="50" cy="60" r="14" fill="#9A5B2E" {_S}/>'),
    "champignon": (f'<rect x="40" y="48" width="20" height="38" rx="9" fill="#F6EEDC" {_S}/>'
                   f'<path d="M10 52 Q12 14 50 14 Q88 14 90 52Z" fill="#D9573E" {_S}/>'
                   '<circle cx="34" cy="36" r="5" fill="#fff"/><circle cx="58" cy="30" r="4.5" fill="#fff"/><circle cx="70" cy="42" r="4" fill="#fff"/>'),
    "ail": (f'<path d="M50 8 Q54 20 58 28 Q86 34 84 62 Q82 90 50 90 Q18 90 16 62 Q14 34 42 28 Q46 20 50 8Z" fill="#F6EEDC" {_S}/>'
            f'<path d="M50 30 Q40 60 50 88 M50 30 Q62 60 50 88" fill="none" stroke="{TRAIT}" stroke-width="3" stroke-linecap="round"/>'),
    "pain": (f'<path d="M12 54 Q10 22 50 22 Q90 22 88 54 L86 78 Q86 84 80 84 L20 84 Q14 84 14 78Z" fill="#E3A957" {_S}/>'
             f'<path d="M30 30 L40 44 M48 26 L58 42 M66 30 L74 44" fill="none" stroke="{TRAIT}" stroke-width="3.5" stroke-linecap="round"/>'),
    "lait": (f'<path d="M26 34 L50 12 L74 34 L74 88 L26 88Z" fill="#FFFFFF" {_S}/><path d="M26 34 L74 34" stroke="{TRAIT}" stroke-width="3.5"/>'
             f'<circle cx="50" cy="62" r="13" fill="#9BE283" {_S}/><path d="M44 62 L49 67 L57 57" fill="none" stroke="{TRAIT}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'),
    "pomme": (f'<path d="M50 28 Q22 18 16 50 Q14 84 40 90 Q50 92 50 90 Q50 92 60 90 Q86 84 84 50 Q78 18 50 28Z" fill="#E94B3C" {_S}/>'
              f'<path d="M50 28 Q52 16 62 10" fill="none" stroke="{TRAIT}" stroke-width="4" stroke-linecap="round"/>'
              f'<path d="M56 18 Q70 10 76 20 Q64 26 56 18Z" fill="#5BB33A" {_S}/>'),
    "poivron": (f'<path d="M30 30 Q50 18 70 30 Q90 40 84 66 Q78 90 62 90 Q50 84 38 90 Q22 90 16 66 Q10 40 30 30Z" fill="#F5C531" {_S}/>'
                f'<path d="M50 24 Q50 14 58 10" fill="none" stroke="#5BB33A" stroke-width="7" stroke-linecap="round"/>'
                '<path d="M30 44 Q28 56 34 66" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="4" stroke-linecap="round"/>'),
})


def mascotte(taille: int = 120, humeur: str = "content") -> str:
    """Le frigo du logo avec un visage : la mascotte de l'appli."""
    bouche = {"content": '<path d="M38 82 Q50 94 62 82" fill="#fff" stroke="%s" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>' % TRAIT,
              "surpris": '<ellipse cx="50" cy="86" rx="7" ry="8" fill="#fff" stroke="%s" stroke-width="3.5"/>' % TRAIT,
              "fier": '<path d="M36 80 Q50 98 64 80Z" fill="#fff" stroke="%s" stroke-width="3.5" stroke-linejoin="round"/>' % TRAIT}[humeur]
    return (f'<svg aria-hidden="true" width="{taille * 0.78:.0f}" height="{taille}" viewBox="0 0 100 128">'
            f'<rect x="6" y="4" width="88" height="120" rx="16" fill="#E3F5D6" {_S}/>'
            f'<rect x="14" y="12" width="72" height="42" rx="11" fill="{VERT}" {_S}/>'
            f'<rect x="14" y="62" width="72" height="54" rx="11" fill="{VERT}" {_S}/>'
            f'<circle cx="36" cy="32" r="5.5" fill="{TRAIT}"/><circle cx="64" cy="32" r="5.5" fill="{TRAIT}"/>'
            '<circle cx="38" cy="30" r="1.8" fill="#fff"/><circle cx="66" cy="30" r="1.8" fill="#fff"/>'
            f'<ellipse cx="26" cy="44" rx="5" ry="3" fill="#F5A593" opacity=".8"/><ellipse cx="74" cy="44" rx="5" ry="3" fill="#F5A593" opacity=".8"/>'
            f'{bouche}</svg>')


def _assiette(contenu: str) -> str:
    return (f'<circle cx="100" cy="72" r="58" fill="#FFFFFF" {_S}/><circle cx="100" cy="72" r="44" fill="#F2F7EC" stroke="{TRAIT}" stroke-width="2.5"/>{contenu}')


def _c(nom, x, y, e, a=0):
    return f'<g transform="translate({x} {y}) rotate({a} {50 * e} {50 * e}) scale({e})">{_OBJETS[nom]}</g>'


_PLATS = {
    "saumon": lambda: _assiette(
        f'<path d="M66 60 Q100 46 136 62 Q140 84 104 90 Q70 92 66 60Z" fill="#F5A38A" {_S}/>'
        f'<path d="M80 62 L92 84 M98 58 L110 86 M116 60 L124 82" stroke="#FBD1C2" stroke-width="4" stroke-linecap="round"/>'
        f'<path d="M62 84 Q52 70 66 66 Q70 78 62 84Z M66 94 Q76 100 84 92 Q74 86 66 94Z" fill="#5BB33A" {_S}/>') + _c("citron", 148, 76, 0.42, 14),
    "poulet": lambda: _assiette(_c("poulet", 64, 40, 0.78, -8)
                                + ''.join(f'<circle cx="{x}" cy="{y}" r="6" fill="#F28C28" {_S}/>' for x, y in [(130, 62), (140, 78), (122, 86)])
                                + ''.join(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#5BB33A"/>' for x, y in [(126, 48), (136, 52), (112, 94), (94, 98)])) + _c("tomate", 12, 60, 0.46, -10),
    "legumes": lambda: _assiette(
        f'<path d="M56 74 Q100 112 144 74Z" fill="#C97B35" {_S}/>'
        + ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" {_S}/>' for x, y, r, c in [(78, 62, 13, "#5BB33A"), (100, 54, 14, "#7ACB4E"), (122, 62, 13, "#5BB33A"), (90, 72, 8, "#E0412F"), (112, 72, 8, "#F5C531")])) + _c("carotte", 140, 74, 0.5, 20),
    "pates": lambda: _assiette(
        ''.join(f'<path d="M{60 + i * 4} {70 + i * 5} Q100 {52 + i * 3} {140 - i * 4} {70 + i * 5}" fill="none" stroke="#F2C94C" stroke-width="7" stroke-linecap="round"/>' for i in range(4))
        + f'<circle cx="100" cy="64" r="14" fill="#E0412F" {_S}/><path d="M92 56 Q100 44 108 56 Q100 62 92 56Z" fill="#5BB33A" {_S}/>') + _c("fromage", 8, 70, 0.5, -8),
    "soupe": lambda: (f'<path d="M34 70 Q34 124 100 124 Q166 124 166 70Z" fill="#FFFFFF" {_S}/>'
                      f'<ellipse cx="100" cy="70" rx="66" ry="14" fill="#F28C28" {_S}/>'
                      f'<path d="M80 54 Q74 40 82 30 M100 52 Q94 36 102 24 M120 54 Q114 42 122 32" fill="none" stroke="{TRAIT}" stroke-width="3.5" stroke-linecap="round" opacity=".55"/>'
                      '<ellipse cx="86" cy="68" rx="14" ry="3.5" fill="#fff" opacity=".35"/>') + _c("pain", 150, 62, 0.5, 8),
}
_ALIAS = {"fish": "saumon", "meat": "poulet", "veg": "legumes"}


def plat(kind: str = "saumon", largeur: int = 390, hauteur: int = 160) -> str:
    """Un plat dessiné dans une assiette, sur fond vert clair (kind : saumon, poulet, legumes, pates, soupe, ou veg/meat/fish)."""
    kind = _ALIAS.get(kind, kind)
    return (f'<svg aria-hidden="true" width="100%" height="{hauteur}" viewBox="0 0 200 140" preserveAspectRatio="xMidYMid slice" style="display:block">'
            f'<rect width="200" height="140" fill="{FOND}"/>{_PLATS[kind]()}</svg>')


# ====================================================================== Dessin le plus proche d'un aliment
_MOTS_ALIMENTS = [
    (("milk", "lait", "yogurt", "yoghurt", "cream", "crème"), "lait"),
    (("egg", "oeuf", "œuf"), "oeuf"),
    (("cheese", "fromage", "parmesan", "feta", "mozzarella"), "fromage"),
    (("tomato", "tomate"), "tomate"),
    (("carrot", "carotte"), "carotte"),
    (("chicken", "poulet", "turkey", "beef", "pork", "meat", "steak", "sausage", "ham", "bacon"), "poulet"),
    (("fish", "salmon", "cod", "tuna", "prawn", "shrimp", "poisson", "saumon"), "poisson"),
    (("broccoli", "spinach", "salad", "lettuce", "cabbage", "green", "kale", "herb", "basil", "parsley"), "brocoli"),
    (("bread", "pain", "toast", "baguette"), "pain"),
    (("lemon", "citron", "lime"), "citron"),
    (("avocado", "avocat"), "avocat"),
    (("mushroom", "champignon"), "champignon"),
    (("garlic", "ail", "onion", "oignon", "shallot"), "ail"),
    (("apple", "pomme", "pear", "peach"), "pomme"),
    (("pepper", "poivron", "chili", "paprika"), "poivron"),
    (("pizza", "tart", "quiche"), "pizza"),
]


def pour_aliment(nom: str, taille: int = 26) -> str | None:
    """Le dessin qui va le mieux avec cet aliment, ou None si on n'en a pas."""
    minuscule = nom.lower()
    for mots, dessin in _MOTS_ALIMENTS:
        if any(m in minuscule for m in mots):
            return objet(dessin, taille)
    return None
