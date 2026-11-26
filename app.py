"""What's in my Fridge — interface mobile claire (police Inter). Lancer avec : streamlit run app.py"""
from __future__ import annotations   # permet d'écrire « dict | None » même sur Python 3.9
import hashlib
import html
import math
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from core import (ai, catalogue, communaute, comptes, db, filtres, illustrations, images, mobile,
                  peremption, reglages, scoring, session)

st.set_page_config(page_title="What's in my Fridge", page_icon=":material/kitchen:", layout="centered",
                   initial_sidebar_state="collapsed")
# Le style de l'appli. On passe par st.html : le texte est envoyé tel quel au navigateur,
# sans passer par le markdown (qui coupait la feuille de style aux lignes vides).
_FICHIER_CSS = Path(__file__).parent / "style.css"
_CSS = _FICHIER_CSS.read_text(encoding="utf-8") if _FICHIER_CSS.exists() else ""
_CSS = "\n".join(l for l in _CSS.splitlines() if l.strip())
st.html(f"<style>{_CSS}</style>")
mobile.activer_mode_app()   # icône et plein écran quand l'appli est ajoutée à l'écran d'accueil
if len(_CSS) < 2000:
    st.error(f"style.css is missing or empty ({len(_CSS)} characters) — the app looks unstyled. "
             f"Put the full style.css next to app.py, here: {_FICHIER_CSS}")
db.initialiser()
communaute.initialiser()
comptes.initialiser()
reglages.initialiser()

# Le robinet de l'IA : si le budget gratuit est épuisé, on n'appelle plus l'IA du tout.
IA_OK, IA_RAISON, IA_FAITS, IA_MAX = reglages.etat_ia()
if not IA_OK:
    ai.forcer_demo(True)

# ----------------------------------------------------------------------- données fixes
APPAREILS = ["Oven", "Microwave", "Blender", "Hand mixer", "Wok", "Pressure cooker",
             "Air Fryer", "Barbecue", "Food processor", "Griddle", "Pan", "Saucepan"]
REGIMES = ["Vegetarian", "Vegan", "Gluten-free", "Lactose-free", "Halal", "Kosher"]
ALLERGIES = ["Milk", "Gluten", "Eggs", "Nuts", "Fish", "Shellfish"]
JOURS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LANGUES = ["English", "Français"]
SCANS_PAR_JOUR = 10          # protège la facture d'IA : 10 analyses par personne et par jour
# (nom de la page, icône Material, texte affiché). « Recipes » est une page cachée (accessible depuis Home / Frigo).
# 4 onglets + le gros bouton Scan au milieu. Profil, Compete et Bilan s'ouvrent depuis Home / Community.
NAV = [("Home", "home", "Home"), ("Fridge", "kitchen", "Fridge"), ("Scan", "photo_camera", "Scan"),
       ("Recipes", "restaurant", "Cook"), ("Community", "groups", "Community")]
TUILES = ["#F2F2EE", "#E3F1E9", "#F8E8DF", "#F7F1D9", "#F3EEE3"]
POINTS = ["#FFFFFF", "#4E9A6B", "#E8B08E", "#F0C84B", "#D9573E", "#C9B79C", "#EE9A45", "#F6E27A"]

for cle, valeur in {
    "page": "Home", "pseudo": "Benjamin", "groupe": "friends", "langue": "English", "portions": 2,
    "ustensiles": ["Oven", "Pan", "Saucepan"], "regimes": [], "profil_cle": None,
    "aliments": [], "plats": [], "plat_choisi": None, "recette": None, "recette_enregistree": False,
    "filtre_recettes": "All", "comm_detail": None, "pub_v": 0, "allergies": [],
    "cook_vue": "Ideas", "comm_vue": "Feed", "mon_frigo_vue": "Fridge", "etape": 0,
    "seulement_possible": True, "jour_a_remplir": None,
}.items():
    st.session_state.setdefault(cle, valeur)


def h(texte) -> str:
    """Protège le texte (venant de l'IA ou d'un ami) avant de l'insérer dans du HTML."""
    return html.escape(str(texte))


def choix_stable(texte: str, liste: list):
    return liste[int(hashlib.md5(texte.encode()).hexdigest(), 16) % len(liste)]


def initiales(nom: str) -> str:
    return h((nom.strip()[:1] or "?").upper())


# ----------------------------------------------------------------------- compte de la personne
def jeton_actuel() -> str:
    """Le jeton de connexion : en mémoire, dans l'adresse, ou gardé par le navigateur."""
    return (st.session_state.get("jeton")
            or st.query_params.get("s", "")
            or session.jeton_du_navigateur())


def connecter(jeton: str) -> None:
    st.session_state.jeton = jeton
    session.memoriser(jeton)              # le navigateur s'en souvient pour les prochaines visites
    st.query_params["s"] = jeton


def deconnecter():
    comptes.fermer_session(jeton_actuel())
    session.oublier()
    st.session_state.jeton = ""
    st.query_params.clear()
    for cle in ("compte", "profil_cle", "aliments", "plats", "recette", "plat_choisi"):
        st.session_state.pop(cle, None)
    st.session_state.page = "Home"


def page_connexion():
    """Écran d'accueil quand personne n'est connecté : créer un compte ou se connecter."""
    st.markdown(f'<div class="logoscene">{illustrations.scene_accueil()}'
                f'<div class="mascot bob">{illustrations.mascotte(84)}</div></div>'
                '<div class="big">Cook smarter.<br><span>Waste less.</span></div>'
                '<p class="muted">Scan your fridge, cook what is about to expire, '
                'and challenge your friends.</p>', unsafe_allow_html=True)

    vue = st.segmented_control(" ", ["Log in", "Create an account"], default="Log in",
                               key="w_connexion_vue", label_visibility="collapsed") or "Log in"
    if vue == "Create an account":
        with st.form("inscription", border=False):
            email = st.text_input("Email", placeholder="you@example.com")
            pseudo = st.text_input("Your name", placeholder="Benjamin",
                                   help="Your friends will see this name.")
            mdp = st.text_input("Password", type="password", placeholder="at least 8 characters")
            accepte = st.checkbox("I agree that my fridge photos and my name are stored to run the app.")
            if st.form_submit_button("Create my account", type="primary", width="stretch"):
                if not accepte:
                    st.error("Please tick the box to continue.")
                else:
                    etat, message = comptes.creer_compte(email, pseudo, mdp)
                    if etat != "ok":
                        st.error(message)
                    else:
                        connecter(comptes.ouvrir_session(email))
                        st.rerun()
    else:
        with st.form("connexion", border=False):
            email = st.text_input("Email", placeholder="you@example.com")
            mdp = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", width="stretch"):
                compte = comptes.verifier(email, mdp)
                if not compte:
                    st.error("Wrong email or password.")
                else:
                    connecter(comptes.ouvrir_session(compte["email"]))
                    st.rerun()

    st.caption("Your password is never stored as such. Your data stays yours: you can delete your "
               "account, and everything with it, at any time from your profile.")


_compte = comptes.compte_du_jeton(jeton_actuel())
if not _compte:
    if session.jeton_du_navigateur():
        session.oublier()      # le jeton gardé ne vaut plus rien : on fait de la place
    page_connexion()
    st.stop()

st.session_state.jeton = jeton_actuel()
session.memoriser(st.session_state.jeton)
session.nettoyer_adresse()     # le jeton ne reste pas dans l'adresse
st.session_state.compte = _compte
st.session_state.pseudo = _compte["pseudo"]
st.session_state.groupe = _compte.get("groupe") or "friends"


def page_intro():
    """Les trois écrans de présentation, montrés une seule fois après l'inscription."""
    etapes = [
        ("Scan your fridge", "One photo and the app finds what you have inside.", "frigo", "content"),
        ("Cook what you have", "Recipes that use the food about to expire, with your own appliances.",
         "plat", "content"),
        ("Challenge your friends", "Waste less than them, win points and badges.", "trophee", "fier"),
    ]
    i = min(st.session_state.get("intro_etape", 0), 2)
    titre, texte, dessin, humeur = etapes[i]
    visuel = (illustrations.plat("saumon", 350, 220) if dessin == "plat"
              else f'<span class="bob">{illustrations.objet("frigo", 170)}</span>' if dessin == "frigo"
              else f'<span class="bob">{illustrations.mascotte(170, "fier")}</span>')
    points = "".join(f'<span class="{"on" if n == i else ""}"></span>' for n in range(3))
    st.markdown(f'<div class="introimg">{visuel}</div>'
                f'<div class="big" style="margin-top:1rem">{h(titre)}</div>'
                f'<p class="muted">{h(texte)}</p><div class="dots">{points}</div>', unsafe_allow_html=True)

    gauche, droite = st.columns([1, 2])
    gauche.button("Skip", key="intro_skip", on_click=finir_intro, width="stretch")
    if i < 2:
        droite.button("Next", key="intro_next", on_click=etape_intro, width="stretch", type="primary",
                      icon=":material/arrow_forward:")
    else:
        droite.button("Start cooking", key="intro_go", on_click=finir_intro, width="stretch",
                      type="primary", icon=":material/check:")


def etape_intro():
    st.session_state.intro_etape = st.session_state.get("intro_etape", 0) + 1


def finir_intro():
    comptes.marquer_intro_vue(st.session_state.compte["email"])
    st.session_state.compte["vu_intro"] = 1
    st.session_state.intro_etape = 0


if not _compte.get("vu_intro"):
    page_intro()
    st.stop()

# Le profil (appareils, régimes) est mémorisé par pseudo + groupe.
_cle_profil = (st.session_state.pseudo, st.session_state.groupe)
if st.session_state.profil_cle != _cle_profil:
    _profil = db.charger_profil(*reversed(_cle_profil))
    if _profil:
        st.session_state.ustensiles, st.session_state.regimes = _profil["ustensiles"], _profil["regimes"]
        st.session_state.allergies = _profil.get("allergies", [])
    st.session_state.profil_cle = _cle_profil

pseudo, groupe, langue = st.session_state.pseudo, st.session_state.groupe, st.session_state.langue
db.preparer_frigo(groupe, pseudo)
communaute.enregistrer_joueur(pseudo)


# ----------------------------------------------------------------------- actions (boutons)
def aller_a(page):
    st.session_state.page = page


def nouveau_scan():
    for cle in ("aliments", "plats"):
        st.session_state[cle] = []
    st.session_state.pop("aliments_finaux", None)
    st.session_state.recette = None
    st.session_state.plat_choisi = None
    st.session_state.recette_enregistree = False


def sauver_profil():
    db.sauver_profil(st.session_state.groupe, st.session_state.pseudo,
                     st.session_state.ustensiles, st.session_state.regimes, st.session_state.allergies)





def basculer(nom_liste, valeur):
    """Coche ou décoche un appareil, un régime ou une allergie, puis enregistre le profil."""
    liste = st.session_state[nom_liste]
    if valeur in liste:
        liste.remove(valeur)
    else:
        liste.append(valeur)
    sauver_profil()


def menu_profil():
    """Le rond avec ton initiale, en haut à droite : tout ce qui te concerne est dedans."""
    with st.popover(initiales(pseudo), width="content", key="menuprofil"):
        st.markdown(f'<div class="menutitre">{h(pseudo)}</div>'
                    f'<div class="menusous">{h(communaute.code_ami(pseudo))}</div>', unsafe_allow_html=True)
        liens = [("Profile", "My profile", "person"), ("Recap", "My week", "insights"),
                 ("Community", "Challenges", "emoji_events"), ("Prefs", "My kitchen", "tune")]
        for page, texte, icone in liens:
            st.button(texte, key=f"menu_{page}_{texte}", on_click=ouvrir_depuis_menu, args=(page, texte),
                      width="stretch", icon=f":material/{icone}:")


def ouvrir_depuis_menu(page, texte):
    if texte == "Challenges":
        st.session_state.comm_vue = "Challenges"
    st.session_state.page = page


def entete(titre, sous_titre="", action=None):
    """Le haut de chaque page : le titre, un bouton d'action, puis le menu du profil."""
    largeurs = [5, 1, 1] if action else [6, 1]
    colonnes = st.columns(largeurs, vertical_alignment="center")
    sous = f'<p class="soustitre">{h(sous_titre)}</p>' if sous_titre else ""
    colonnes[0].markdown(f'<div class="title">{h(titre)}</div>{sous}', unsafe_allow_html=True)
    if action:
        texte, cle, fonction, args, icone, aide = action
        colonnes[1].button(texte, key=cle, on_click=fonction, args=args, icon=f":material/{icone}:",
                           type="primary", help=aide)
    with colonnes[-1]:
        menu_profil()


def sous_entete(titre, retour="Home", cle=""):
    """Haut des pages secondaires : flèche de retour à gauche, titre au centre."""
    gauche, milieu, droite = st.columns([1, 4, 1], vertical_alignment="center")
    gauche.button("", key=f"navback_{cle or titre}", on_click=aller_a, args=(retour,),
                  icon=":material/arrow_back:", help="Back")
    milieu.markdown(f'<div class="soustitrepage">{h(titre)}</div>', unsafe_allow_html=True)
    with droite:
        menu_profil()


def onglets(cle, options, defaut):
    """Trois onglets au maximum, toujours le même composant."""
    return st.segmented_control(" ", options, default=st.session_state.get(cle, defaut), key=f"w_{cle}",
                                label_visibility="collapsed", on_change=garder_vue, args=(cle,)) or st.session_state.get(cle, defaut)


def garder_vue(cle):
    st.session_state[cle] = st.session_state[f"w_{cle}"] or st.session_state[cle]


def grille_pastilles(options, nom_liste, prefixe):
    """Les cases à cocher : deux par ligne, même dessin pour appareils, régimes et allergies."""
    actifs = st.session_state[nom_liste]
    with st.container(key=f"grid_{prefixe}"):
        for debut in range(0, len(options), 2):
            for col, nom in zip(st.columns(2), options[debut:debut + 2]):
                coche = nom in actifs
                col.button(nom, key=f"{prefixe}_{'on' if coche else 'off'}_{nom}", on_click=basculer,
                           args=(nom_liste, nom), width="stretch",
                           icon=":material/check_circle:" if coche else ":material/radio_button_unchecked:")


def mes_choix() -> tuple[list, list, list]:
    return st.session_state.ustensiles, st.session_state.regimes, st.session_state.allergies


def maj_groupe():
    nouveau = st.session_state.w_groupe.strip().lower() or "friends"
    st.session_state.groupe = nouveau
    with db._connexion() as con:   # on garde le groupe sur le compte
        con.execute("UPDATE comptes SET groupe = ? WHERE email = ?", (nouveau, st.session_state.compte["email"]))
    st.session_state.compte["groupe"] = nouveau


def maj_langue():
    st.session_state.langue = st.session_state.w_langue


def maj_portions():
    st.session_state.portions = int(st.session_state.w_portions)


def noms_frigo() -> list[str]:
    """Les aliments du frigo, les plus pressés en premier (c'est avec eux qu'on cuisine d'abord)."""
    return [a["nom"] for a in db.lister_frigo(groupe, pseudo)]


def cuisiner_idee(idee: dict):
    """Depuis la liste des 33 idées : l'IA écrit la recette complète avec ce qu'il y a dans le frigo."""
    plat = catalogue.plat_depuis_recette(idee)
    dispo = noms_frigo()
    if ai.mode_demo():
        plat["ingredients_utilises"] = dispo[:3]
    try:
        recette = ai.creer_recette(plat, dispo, st.session_state.ustensiles, st.session_state.portions, langue)
    except Exception as erreur:
        if ai.manque_de_credit(erreur):
            reglages.bloquer_ia(str(erreur))
            ai.forcer_demo(True)
            st.session_state.erreur = ("The AI is paused: the free budget is used up. The app still works "
                                       "without it.")
        else:
            st.session_state.erreur = "Could not write the recipe. Try again in a moment."
        return
    st.session_state.plat_choisi, st.session_state.recette = plat, recette
    st.session_state.recette_enregistree = False
    st.session_state.page = "Scan"


# ----------------------------------------------------------------------- ÉCRAN : Home
def jours_avant(expire: str) -> int:
    return (date.fromisoformat(expire) - date.today()).days


def serie_jours() -> int:
    """Nombre de jours d'affilée (jusqu'à aujourd'hui) où tu as cuisiné."""
    jours = db.activite_semaine(groupe, pseudo)
    serie = 0
    for _, n in reversed(jours):
        if n <= 0:
            break
        serie += 1
    return serie


# Petits dessins (traits) pour les cartes de l'accueil
TRACES = {
    "plat": '<path d="M4 11h16v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3z"/><path d="M2 11h2M20 11h2"/>'
            '<path d="M8 7c0-1.5 1-1.5 1-3M12 7c0-1.5 1-1.5 1-3M16 7c0-1.5 1-1.5 1-3"/>',
    "flamme": '<path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z"/>',
}


def trait(nom: str, couleur: str, taille: int = 22) -> str:
    return (f'<svg aria-hidden="true" width="{taille}" height="{taille}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{couleur}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{TRACES[nom]}</svg>')


def carte_rapide(colonne, cle, page, valeur, texte, fond, couleur, icone=None, dessin=None):
    """Petite carte cliquable : le bouton est transparent et couvre toute la carte."""
    with colonne, st.container(key=f"qcard_{cle}"):
        visuel = dessin if dessin else trait(icone, couleur)
        st.markdown(f'<span class="qtile" style="background:{fond}">{visuel}</span>'
                    f'<b>{valeur}</b><small>{texte}</small>', unsafe_allow_html=True)
        st.button("Open", key=f"qgo_{cle}", on_click=aller_a, args=(page,))


def page_home():
    frigo = db.lister_frigo(groupe, pseudo)
    bientot = sum(1 for a in frigo if jours_avant(a["expire"]) <= 2)
    gauche, droite = st.columns([5, 1], vertical_alignment="center")
    gauche.markdown(f'<div class="topbar"><span class="date">{date.today().strftime("%A, %d %B")}</span>'
                    f'<span class="hi">Hey {h(pseudo)}</span></div>', unsafe_allow_html=True)
    with droite:
        menu_profil()

    with st.container(key="hero"):
        st.markdown(f'<span class="blob b1"></span><span class="blob b2"></span>'
                    f'<span class="mascot bob">{illustrations.mascotte(80)}</span>'
                    f'<span class="tagline">{len(frigo)} items in your fridge</span>'
                    '<div class="htitle">What are we<br>cooking tonight?</div>', unsafe_allow_html=True)
        st.button("Scan my fridge", key="home_scan", on_click=aller_a, args=("Scan",),
                  icon=":material/photo_camera:")

    colonnes = st.columns(3)
    carte_rapide(colonnes[0], "frigo", "Fridge", bientot, "expire soon", "#FBF0D5", "#A5770B",
                 dessin=illustrations.objet("tomate", 26))
    carte_rapide(colonnes[1], "idees", "Recipes", len(catalogue.RECETTES), "recipe ideas", "#E3F1E9", "#177A54",
                 icone="plat")
    carte_rapide(colonnes[2], "serie", "Recap", serie_jours(), "day streak", "#FDE8DC", "#E0601C",
                 icone="flamme")

    st.markdown('<div class="section">Recent</div>', unsafe_allow_html=True)
    recentes = db.recettes_recentes(groupe, pseudo)
    if recentes:
        cartes = ""
        for r in recentes:
            image, teinte = catalogue.illustration(r["nom_plat"])
            cartes += (f'<div class="rcard"><div class="rimg" style="background:{teinte}">{image}</div>'
                       f'<div class="rname">{h(r["nom_plat"])}</div><div class="rtime">{r["temps_minutes"]} min</div></div>')
        st.markdown(f'<div class="rscroll">{cartes}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="empty"><span class="bob">{illustrations.mascotte(64)}</span>'
                    '<div><b>No dish yet</b><p>Scan your fridge and cook your first recipe. '
                    'It will show up here.</p></div></div>', unsafe_allow_html=True)




# ----------------------------------------------------------------------- ÉCRAN : Cook (idées, semaine, gardées)
def planifier_idee(idee: dict, jour: str):
    db.planifier(groupe, pseudo, jour, idee["nom"], idee["categorie"])
    st.session_state.jour_a_remplir = None
    st.session_state.cook_vue = "My week"


def basculer_favori(nom_plat):
    db.basculer_favori(groupe, pseudo, nom_plat)


def carte_idee(colonne, idee, possible, raison, favori, jour=None):
    """Une carte de recette : photo (ou dessin), nom, temps, et pourquoi elle ne va pas."""
    with colonne, st.container(key=f"rc_{idee['nom']}"):
        classe = "rimg" if possible else "rimg off"
        etiquette = (f'<span class="rtag ok">Ready</span>' if possible
                     else f'<span class="rtag no">{h(raison)}</span>')
        st.markdown(f'<div class="rwrap"><div class="{classe}" style="background:{idee["teinte"]}">'
                    f'{catalogue.photo(idee["nom"]) or idee["svg"]}</div>{etiquette}</div>'
                    f'<div class="rname">{h(idee["nom"])}</div>'
                    f'<div class="rtime">{idee["minutes"]} min</div>', unsafe_allow_html=True)
        if jour:
            st.button("Plan this", key=f"plan_{idee['nom']}", on_click=planifier_idee, args=(idee, jour),
                      width="stretch")
        else:
            gauche, coeur = st.columns([3, 1], vertical_alignment="center")
            gauche.button("Cook this", key=f"cookidea_{idee['nom']}", on_click=cuisiner_idee, args=(idee,),
                          width="stretch", type="primary")
            coeur.button("", key=f"fav_{'on' if favori else 'off'}_{idee['nom']}", on_click=basculer_favori,
                         args=(idee["nom"],), help="Save this recipe",
                         icon=":material/favorite:" if favori else ":material/favorite_border:")


def page_recettes():
    entete("Cook")
    if "erreur" in st.session_state:
        st.error(st.session_state.pop("erreur"))
    vue = onglets("cook_vue", ["Ideas", "My week", "Saved"], "Ideas")
    {"Ideas": vue_idees, "My week": vue_semaine, "Saved": vue_favoris}[vue]()


def vue_idees():
    appareils, regimes, allergies = mes_choix()
    favoris = db.lister_favoris(groupe, pseudo)
    jour = st.session_state.jour_a_remplir
    if jour:
        st.info(f"Pick a dish for {date.fromisoformat(jour).strftime('%A %d')}.")
        st.button("Cancel", key="annule_jour", on_click=choisir_jour, args=(None,))

    filtre = st.segmented_control(" ", ["All", "Veggie", "Meat", "Fish"], default=st.session_state.filtre_recettes,
                                  key="w_filtre", label_visibility="collapsed") or "All"
    st.session_state.filtre_recettes = filtre
    categorie = {"Veggie": "veg", "Meat": "meat", "Fish": "fish"}.get(filtre)
    with st.container(key="filtrecarte"):
        st.markdown('<div class="ftext"><b>Only what I can cook</b>'
                    '<small>Uses your appliances, your diet and your allergies</small></div>',
                    unsafe_allow_html=True)
        st.toggle(" ", key="seulement_possible", label_visibility="collapsed")

    liste = [r for r in catalogue.RECETTES if categorie is None or r["categorie"] == categorie]
    etats = {r["nom"]: filtres.verifier(r, appareils, regimes, allergies) for r in liste}
    possibles = sum(1 for r in liste if etats[r["nom"]][0])
    if st.session_state.seulement_possible:
        liste = [r for r in liste if etats[r["nom"]][0]]
    st.markdown(f'<p class="muted"><b>{possibles} of {len(catalogue.RECETTES)} ideas</b> fit your kitchen today.</p>',
                unsafe_allow_html=True)

    for debut in range(0, len(liste), 2):
        for col, idee in zip(st.columns(2), liste[debut:debut + 2]):
            ok, raison = etats[idee["nom"]]
            carte_idee(col, idee, ok, raison, idee["nom"] in favoris, jour)
    if not liste:
        st.markdown('<p class="muted">Nothing fits yet. Turn off the filter or tick more appliances.</p>',
                    unsafe_allow_html=True)
    st.button("Change my kitchen", key="cook_prefs", on_click=aller_a, args=("Prefs",), width="stretch",
              icon=":material/tune:")


def choisir_jour(jour):
    st.session_state.jour_a_remplir = jour
    st.session_state.cook_vue = "Ideas" if jour else "My week"


def vue_semaine():
    semaine = db.lister_semaine(groupe, pseudo)
    frigo = db.lister_frigo(groupe, pseudo)
    pressants = [a["nom"] for a in frigo if jours_avant(a["expire"]) <= 3]
    st.markdown('<p class="muted">Planned around what expires first.</p>', unsafe_allow_html=True)
    for i in range(7):
        jour = (date.today() + timedelta(days=i)).isoformat()
        etiquette = date.fromisoformat(jour).strftime("%a %d")
        prevu = semaine.get(jour)
        ligne, action = st.columns([4, 1], vertical_alignment="center")
        if prevu:
            image, teinte = catalogue.illustration(prevu["nom_plat"], 40)
            ligne.markdown(f'<div class="dayrow"><span class="daytag">{etiquette}</span>'
                           f'<span class="dimg" style="background:{teinte}">{image}</span>'
                           f'<span class="dname">{h(prevu["nom_plat"])}</span></div>', unsafe_allow_html=True)
            action.button("", key=f"del_{jour}", on_click=db.deplanifier, args=(groupe, pseudo, jour),
                          icon=":material/close:")
        else:
            ligne.markdown(f'<div class="dayrow empty"><span class="daytag">{etiquette}</span>'
                           '<span class="dname muted">No meal yet</span></div>', unsafe_allow_html=True)
            action.button("", key=f"add_{jour}", on_click=choisir_jour, args=(jour,), icon=":material/add:")
    if pressants:
        st.markdown(f'<div class="tipbox"><span class="wiggle">{illustrations.mascotte(50)}</span>'
                    f'<div>Plan a meal with <b>{h(", ".join(pressants[:3]))}</b>: they expire within 3 days.</div>'
                    '</div>', unsafe_allow_html=True)


def vue_favoris():
    favoris = db.lister_favoris(groupe, pseudo)
    liste = [r for r in catalogue.RECETTES if r["nom"] in favoris]
    if not liste:
        st.markdown('<p class="muted">No saved recipe yet. Tap the heart on an idea to keep it here.</p>',
                    unsafe_allow_html=True)
        return
    appareils, regimes, allergies = mes_choix()
    for debut in range(0, len(liste), 2):
        for col, idee in zip(st.columns(2), liste[debut:debut + 2]):
            ok, raison = filtres.verifier(idee, appareils, regimes, allergies)
            carte_idee(col, idee, ok, raison, True)


# ----------------------------------------------------------------------- ÉCRAN : Fridge
def pastille(expire: str) -> tuple[str, str]:
    """Texte et couleur de la pastille : rouge = urgent, orange = cette semaine, vert = plus tard."""
    j = jours_avant(expire)
    joli = date.fromisoformat(expire).strftime("%b %d").replace(" 0", " ")
    if j < 0:
        return "Expired", "red"
    if j == 0:
        return "Today", "red"
    if j == 1:
        return "Tomorrow", "red"
    if j < 7:
        return joli, "amber"
    return joli, "green"


def ligne_aliment(a: dict) -> str:
    texte, couleur = pastille(a["expire"])
    tuile = choix_stable(a["nom"], TUILES)
    dessin = illustrations.pour_aliment(a["nom"], 28)
    visuel = dessin or f'<i style="background:{choix_stable(a["nom"] + "x", POINTS)}"></i>'
    detail = h(a["quantite"])
    if a.get("note"):
        detail += f' · {h(a["note"])}'
    marque = '<span class="estim">estimated</span>' if a.get("estime") else ""
    return (f'<div class="frow"><span class="ftile" style="background:{tuile}">{visuel}</span>'
            f'<div class="finfo"><b>{h(a["nom"])}</b><small>{detail}</small></div>'
            f'<span class="pills">{marque}<span class="pill {couleur}">{texte}</span></span></div>')


def page_frigo():
    aliments = db.lister_frigo(groupe, pseudo)
    urgents = [a for a in aliments if jours_avant(a["expire"]) <= 1]
    courses = [a for a in db.lister_courses(groupe, pseudo) if not a["coche"]]

    gauche, ajout, compte = st.columns([5, 1, 1], vertical_alignment="center")
    detail = f"{len(aliments)} items · {len(urgents)} to use first"
    if courses:
        detail += f" · {len(courses)} to buy"
    gauche.markdown(f'<div class="title">My fridge</div><p class="soustitre">{detail}</p>',
                    unsafe_allow_html=True)
    with compte:
        menu_profil()
    with ajout.popover("", icon=":material/add:", type="primary", key="addpop"):
        with st.form("ajout_aliment", border=False, clear_on_submit=True):
            nom = st.text_input("Food", placeholder="Tomatoes")
            quantite = st.text_input("Quantity", placeholder="3, 200 g, 1 L…")
            expire = st.date_input("Expiry date", value=date.today() + timedelta(days=5))
            if st.form_submit_button("Add to my fridge", width="stretch", type="primary") and nom.strip():
                db.ajouter_aliment(groupe, pseudo, nom, quantite, expire.isoformat())
                st.rerun()

    vue = onglets("mon_frigo_vue", ["Fridge", "Shopping list"], "Fridge")
    if vue == "Fridge" and aliments:
        st.caption("Dates marked « estimated » are a guess from the photo. Always look at the food and "
                   "the label, above all for meat and fish.")
    if vue == "Shopping list":
        vue_courses()
    else:
        vue_frigo(aliments, urgents)


def vue_courses():
    articles = db.lister_courses(groupe, pseudo)
    with st.form("ajout_course", border=False, clear_on_submit=True):
        ligne, bouton = st.columns([3, 1], vertical_alignment="bottom")
        nom = ligne.text_input("Add an item", placeholder="Olive oil", label_visibility="collapsed")
        if bouton.form_submit_button("Add", width="stretch", type="primary") and nom.strip():
            db.ajouter_course(groupe, pseudo, nom)
            st.rerun()

    if not articles:
        st.markdown(f'<div class="empty"><span class="bob">{illustrations.mascotte(56)}</span>'
                    '<div><b>Nothing to buy</b><p>Add an item above, or open a recipe: the ingredients '
                    'you are missing land here in one tap.</p></div></div>', unsafe_allow_html=True)
    for a in articles:
        case, texte, retirer = st.columns([1, 6, 1], vertical_alignment="center")
        coche = case.checkbox(" ", value=bool(a["coche"]), key=f"co_{a['id']}", label_visibility="collapsed")
        if coche != bool(a["coche"]):
            db.cocher_course(a["id"], coche)
            st.rerun()
        pour = f'<small>{h(a["pour"])}</small>' if a["pour"] else ""
        classe = "crow done" if a["coche"] else "crow"
        texte.markdown(f'<div class="{classe}"><b>{h(a["nom"])}</b>{pour}</div>', unsafe_allow_html=True)
        if retirer.button("", key=f"cx_{a['id']}", icon=":material/close:"):
            db.supprimer_course(a["id"])
            st.rerun()

    coches = [a for a in articles if a["coche"]]
    if coches:
        if st.button(f"Move {len(coches)} checked item(s) to my fridge", width="stretch", type="primary",
                     icon=":material/kitchen:"):
            n = db.courses_vers_frigo(groupe, pseudo)
            st.session_state.mon_frigo_vue = "Fridge"
            st.success(f"{n} item(s) added to your fridge.")
            st.rerun()


def vue_frigo(aliments, urgents):
    groupes = [("Use first", "Expires today or tomorrow", urgents),
               ("This week", "Expires in 2 to 6 days", [a for a in aliments if 2 <= jours_avant(a["expire"]) < 7]),
               ("Later", "Expires in more than a week", [a for a in aliments if jours_avant(a["expire"]) >= 7])]

    if urgents:
        noms = [a["nom"].lower() for a in urgents[:3]]
        liste = noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " and " + noms[-1]
        with st.container(key="banner"):
            st.markdown(f'<b>{h(liste.capitalize())} expire by tomorrow</b>'
                        '<span>Cook with them tonight so nothing goes to waste.</span>', unsafe_allow_html=True)
            st.button("See recipes", key="frigo_recettes", on_click=aller_a, args=("Recipes",), type="primary")

    if not aliments:
        st.markdown(f'<div class="empty"><span class="bob">{illustrations.mascotte(64)}</span>'
                    '<div><b>Your fridge is empty</b><p>Scan it with the green button, or add your food '
                    'one by one with the + above.</p></div></div>', unsafe_allow_html=True)
        gauche, droite = st.columns(2)
        gauche.button("Scan my fridge", key="vide_scan", on_click=aller_a, args=("Scan",), width="stretch",
                      type="primary", icon=":material/photo_camera:")
        if droite.button("Example fridge", key="vide_exemple", width="stretch",
                         icon=":material/science:", help="Fills your fridge with a few items, to try the app"):
            db.remplir_frigo_exemple(groupe, pseudo)
            st.rerun()
    for titre, sous_titre, liste in groupes:
        if liste:
            st.markdown(f'<div class="fhead"><b>{titre}</b><span>{sous_titre}</span></div>'
                        + "".join(ligne_aliment(a) for a in liste), unsafe_allow_html=True)

    if aliments:
        with st.expander("Fix an expiry date"):
            cible = st.selectbox("Item", [a["id"] for a in aliments], key="w_fixid",
                                 format_func=lambda i: next(a["nom"] for a in aliments if a["id"] == i))
            actuel = next(a for a in aliments if a["id"] == cible)
            nouvelle = st.date_input("Real expiry date", value=date.fromisoformat(actuel["expire"]), key="w_fixdate")
            if st.button("Save this date", width="stretch", type="primary"):
                db.corriger_date(cible, nouvelle.isoformat())
                st.rerun()
        with st.expander("Remove items"):
            choisis = st.multiselect("Items to remove", [a["id"] for a in aliments], key="w_retirer",
                                     format_func=lambda i: next(a["nom"] for a in aliments if a["id"] == i))
            if st.button("Remove", disabled=not choisis, width="stretch"):
                db.supprimer_aliments(groupe, pseudo, choisis)
                st.session_state.pop("w_retirer", None)
                st.rerun()


# ----------------------------------------------------------------------- ÉCRAN : Scan
def page_scan():
    if ai.mode_demo():
        st.caption("Demo mode: no AI key found, so the answers are examples.")
    if st.session_state.recette:
        return scan_recette()
    if st.session_state.plats:
        return scan_plats()
    if st.session_state.aliments:
        return scan_ingredients()

    st.markdown('<div class="title">Scan fridge</div>'
                '<p class="muted">Open the door and fit the whole shelf in the photo.</p>'
                '<div class="frame"><span class="corner tl"></span><span class="corner tr"></span>'
                '<span class="corner bl"></span><span class="corner br"></span>'
                f'<span class="fl f1 bob">{illustrations.objet("tomate", 56)}</span>'
                f'<span class="fl f2 bob2">{illustrations.objet("carotte", 64)}</span>'
                f'<span class="fmain">{illustrations.objet("frigo", 150)}</span></div>', unsafe_allow_html=True)
    fichiers = st.file_uploader("Upload one or more photos", type=images.FORMATS,
                                accept_multiple_files=True)
    photos, illisibles = [], []
    for f in fichiers or []:
        prete = images.preparer(f.getvalue(), f.type, f.name)
        (photos if prete else illisibles).append(prete or f.name)
    if st.toggle("Use the camera"):
        photo = st.camera_input("Frame the inside of your fridge", label_visibility="collapsed")
        if photo:
            prete = images.preparer(photo.getvalue(), photo.type, "camera.jpg")
            if prete:
                photos.append(prete)
    if illisibles:
        st.warning(images.message_heic() if not images.HEIC_OK
                   else f"Could not read: {', '.join(illisibles)}. Try another photo.")

    restants = SCANS_PAR_JOUR - comptes.scans_du_jour(st.session_state.compte["email"])
    budget_fini = not IA_OK and bool(ai.cle_api())
    if budget_fini:
        st.warning(f"{IA_RAISON} Add your food by hand with the + button in the Fridge tab — everything "
                   "else keeps working: recipes, shopping list, week plan and competitions.")
    elif restants <= 0:
        st.warning(f"You have used your {SCANS_PAR_JOUR} scans for today. Come back tomorrow, or add "
                   "your food by hand with the + button in the Fridge tab.")
    elif ai.cle_api():
        st.caption(f"{restants} scan(s) left today.")

    if st.button("Analyze with AI", width="stretch", type="primary", icon=":material/auto_awesome:",
                 disabled=budget_fini or restants <= 0 or (not photos and not ai.mode_demo())):
        with st.spinner("The AI is looking at your fridge…"):
            try:
                trouves = ai.detecter_ingredients(photos, langue)
            except Exception as erreur:
                if ai.manque_de_credit(erreur):     # plus de crédit : on coupe l'IA pour tout le monde
                    reglages.bloquer_ia(str(erreur))
                    ai.forcer_demo(True)
                    st.warning("AI scanning is now paused: the free budget is used up. Add your food by "
                               "hand with the + button in the Fridge tab.")
                else:
                    st.error("The AI could not read the photo. Try again in a moment, or take a clearer "
                             f"photo with more light. ({type(erreur).__name__})")
            else:
                comptes.compter_scan(st.session_state.compte["email"])
                nouveau_scan()
                st.session_state.aliments = trouves
                st.rerun()


def noms_aliments() -> list[str]:
    finaux = st.session_state.get("aliments_finaux", st.session_state.aliments)
    return [a["nom"] for a in finaux if a.get("nom")]


def scan_ingredients():
    puces = "".join(f'<span class="chipfound" style="animation-delay:{.4 + i * .3:.1f}s">{h(a.get("nom", ""))}'
                    f'{" · <b style=color:#177A54>" + h(a["quantite"]) + "</b>" if a.get("quantite") else ""}</span>'
                    for i, a in enumerate(st.session_state.aliments) if a.get("nom"))
    st.markdown(f'<div class="hero-mascot"><span class="bob">{illustrations.mascotte(150, "surpris")}</span></div>'
                f'<div class="title">{len(st.session_state.aliments)} ingredients found</div>'
                '<p class="muted">Fix the list if the AI made a mistake.</p>'
                f'<div>{puces}</div>', unsafe_allow_html=True)
    depart = pd.DataFrame([{"nom": a.get("nom", ""), "quantite": a.get("quantite", ""),
                            "jours": peremption.jours_valides(a), "note": a.get("note", "")}
                           for a in st.session_state.aliments])
    tableau = st.data_editor(
        depart, num_rows="dynamic", width="stretch", key="editeur_aliments",
        column_config={"nom": "Ingredient", "quantite": "Quantity",
                       "jours": st.column_config.NumberColumn("Days left", min_value=1, max_value=365,
                                                              help="Estimated by the AI. Change it if you know better."),
                       "note": st.column_config.TextColumn("Why", disabled=True)})
    st.session_state.aliments_finaux = [
        r for r in tableau.fillna("").to_dict("records") if str(r["nom"]).strip()]
    st.caption("Days left are estimated from what the AI sees: an opened pack or cooked leftovers keep less long.")

    if st.button("Find dishes", width="stretch", type="primary", icon=":material/auto_awesome:",
                 disabled=not st.session_state.aliments_finaux):
        with st.spinner("Looking for ideas…"):
            try:
                plats = ai.proposer_plats(noms_aliments(), st.session_state.ustensiles,
                                          ", ".join(st.session_state.regimes), langue=langue)
            except Exception as erreur:
                st.error(f"Could not suggest dishes: {erreur}")
            else:
                st.session_state.plats = plats
                st.rerun()
    if st.button("Add these to my fridge", width="stretch", icon=":material/add:",
                 disabled=not st.session_state.aliments_finaux):
        n = db.ajouter_depuis_scan(groupe, pseudo, st.session_state.aliments_finaux)
        st.success(f"{n} new item(s) added with their estimated expiry date.")
    st.button("New scan", key="reset_1", on_click=nouveau_scan, icon=":material/refresh:")


def scan_plats():
    st.markdown('<div class="title">What can we cook?</div>'
                '<p class="muted">From the simplest to the most elaborate.</p>', unsafe_allow_html=True)
    for i, plat in enumerate(st.session_state.plats):
        with st.container(key=f"dish_{i}"):
            manquants = plat.get("ingredients_manquants", [])
            st.markdown(
                f'<div class="level">LEVEL {int(plat["niveau_elaboration"])}/10</div>'
                f'<div class="dname">{h(plat["nom"])}</div>'
                f'<p class="muted">{h(plat.get("description", ""))}</p>'
                f'<div class="chips"><span class="chip">{int(plat.get("temps_minutes", 0))} min</span>'
                f'<span class="chip">{len(plat.get("ingredients_utilises", []))} from your fridge</span></div>'
                + (f'<p class="muted">Also needed: {h(", ".join(manquants))}</p>' if manquants else ""),
                unsafe_allow_html=True)
            if st.button("Cook this", key=f"cook_{i}", width="stretch", type="primary"):
                with st.spinner("Writing the recipe…"):
                    try:
                        recette = ai.creer_recette(plat, noms_aliments(), st.session_state.ustensiles,
                                                   st.session_state.portions, langue)
                    except Exception as erreur:
                        st.error(f"Could not write the recipe: {erreur}")
                    else:
                        st.session_state.plat_choisi = plat
                        st.session_state.recette = recette
                        st.session_state.recette_enregistree = False
                        st.rerun()

    def retour():
        st.session_state.plats = []
    st.button("Back to ingredients", key="back_1", on_click=retour, icon=":material/arrow_back:")


def aliments_utilises(recette: dict, plat: dict) -> list[str]:
    """Quels aliments du frigo ont servi ? Ceux du plat, plus ceux qui apparaissent dans la recette."""
    utilises = {n.lower() for n in plat.get("ingredients_utilises", [])}
    textes = [i["nom"].lower() for i in recette["ingredients"]]
    for nom in noms_frigo():
        if any(nom.lower() in t or t in nom.lower() for t in textes):
            utilises.add(nom.lower())
    return sorted(utilises)


def celebration(info: dict | None):
    """Écran « Bien cuisiné ! » : confettis, points, aliments sauvés et progression de niveau."""
    info = info or {"points": 0, "nom": "", "sauves": 0}
    stats = db.stats_joueur(groupe, pseudo)
    niveau, progression = scoring.niveau_joueur(stats["points"])
    couleurs = ["#9BE283", "#F5C531", "#E94B3C", "#177A54", "#F28C28", "#4FA3D1"]
    confettis = "".join(
        f'<span class="conf" style="--dx:{(i % 14 - 6.5) * 30}px;--dy:{-120 - (i % 6) * 55}px;'
        f'--rot:{(i * 97) % 720 - 360}deg;background:{couleurs[i % 6]};'
        f'animation-delay:{(i % 6) * .06:.2f}s;width:{8 + i % 4}px;height:{11 + i % 5}px"></span>'
        for i in range(44))
    st.markdown(
        f'<div class="celebrate">{confettis}<span class="bob" style="line-height:0;display:inline-block">{illustrations.mascotte(130, "fier")}</span>'
        f'<h2>Well cooked!</h2><p class="muted">{h(info["nom"])} is done. Nothing went to waste.</p>'
        f'<div class="kpis"><div><b>+{info["points"]}</b><small>points</small></div>'
        f'<div><b>{info["sauves"]}</b><small>ingredients saved</small></div>'
        f'<div><b>{scoring.kg_evites(info["sauves"])} kg</b><small>waste avoided</small></div></div>'
        f'<div class="profile" style="text-align:left"><div class="info" style="width:100%"><b>Level {niveau}</b>'
        f'<div class="bar" style="margin:.5rem 0 .2rem"><div style="width:{progression}%"></div></div>'
        f'<small>{progression}% to level {niveau + 1}</small></div></div></div>', unsafe_allow_html=True)
    gauche, droite = st.columns(2)
    gauche.button("See my week", key="vers_bilan", on_click=aller_a, args=("Recap",), width="stretch",
                  icon=":material/insights:")
    droite.button("Cook again", key="vers_cook", on_click=aller_a, args=("Recipes",), width="stretch",
                  type="primary", icon=":material/restaurant:")


def courses_depuis_recette(noms, titre):
    for n in noms:
        db.ajouter_course(groupe, pseudo, n, f"for {titre}")
    st.session_state.flash_courses = f"{len(noms)} item(s) added to your shopping list."


def demarrer_cuisson():
    st.session_state.etape = 0
    st.session_state.page = "Cooking"


def etape_suivante(pas):
    etapes = st.session_state.recette["etapes"]
    st.session_state.etape = max(0, min(len(etapes) - 1, st.session_state.etape + pas))


def page_cuisson():
    """Mode cuisson : une étape à la fois, en grand."""
    recette = st.session_state.recette
    if not recette:
        return aller_a("Recipes")
    etapes = recette["etapes"]
    i = min(st.session_state.etape, len(etapes) - 1)
    barres = "".join(f'<span class="{"on" if n <= i else ""}"></span>' for n in range(len(etapes)))
    minutes = re.findall(r"(\d+)\s*(?:min|minute)", etapes[i].lower())
    minuteur = (f'<div class="timer"><small>Timer</small><b>{int(minutes[0]):02d}:00</b></div>' if minutes else "")
    st.button("", key="fin_cuisson", on_click=aller_a, args=("Scan",), icon=":material/close:")
    st.markdown(f'<div class="progress">{barres}</div>'
                f'<div class="stepno">STEP {i + 1} OF {len(etapes)}</div>'
                f'<div class="bigstep">{h(etapes[i])}</div>{minuteur}', unsafe_allow_html=True)
    gauche, droite = st.columns(2)
    gauche.button("Back", key="cuis_prec", on_click=etape_suivante, args=(-1,), width="stretch",
                  disabled=i == 0, icon=":material/arrow_back:")
    if i < len(etapes) - 1:
        droite.button("Next step", key="cuis_suiv", on_click=etape_suivante, args=(1,), width="stretch",
                      type="primary", icon=":material/arrow_forward:")
    else:
        droite.button("Finish", key="cuis_fin", on_click=aller_a, args=("Scan",), width="stretch",
                      type="primary", icon=":material/check:")


def scan_recette():
    recette, plat = st.session_state.recette, st.session_state.plat_choisi
    if st.session_state.recette_enregistree:   # plat terminé : on montre la fête, rien d'autre
        return celebration(st.session_state.get("celebre"))
    image, teinte = catalogue.illustration(recette["titre"], 110)
    st.markdown(f'<div class="hero" style="background:{teinte}">{image}</div>'
                f'<div class="title">{h(recette["titre"])}</div>'
                f'<div class="chips"><span class="chip">{int(recette["portions"])} serving(s)</span>'
                f'<span class="chip">{int(recette["temps_preparation_minutes"])} min prep</span>'
                f'<span class="chip">{int(recette["temps_cuisson_minutes"])} min cooking</span></div>',
                unsafe_allow_html=True)

    texte = " ".join([recette["titre"]] + [i["nom"] for i in recette["ingredients"]]).lower()
    touchees = [a for a in st.session_state.allergies
                if any(m in texte for m in filtres.ALLERGENES.get(a, ()) + (a.lower(),))]
    if touchees:
        st.markdown(f'<div class="warn">Careful: this recipe may contain {h(", ".join(t.lower() for t in touchees))}. '
                    'Swap it or skip it.</div>', unsafe_allow_html=True)
    elif st.session_state.regimes:
        st.markdown(f'<div class="okline">Fits your {h(", ".join(r.lower() for r in st.session_state.regimes))} '
                    'choices.</div>', unsafe_allow_html=True)

    manquants = [i["nom"] for i in recette["ingredients"] if i.get("manquant")]
    s = recette["sante"]
    st.markdown('<div class="section">Nutrition (per serving)</div>'
                '<div class="nutri">'
                f'<div><b>{s["calories"]}</b><small>Calories (kcal)</small></div>'
                f'<div><b>{s["proteines_g"]} g</b><small>Protein</small></div>'
                f'<div><b>{s["glucides_g"]} g</b><small>Carbohydrates</small></div>'
                f'<div><b>{s["lipides_g"]} g</b><small>Fat</small></div>'
                f'<div><b>{s["fibres_g"]} g</b><small>Fiber</small></div>'
                f'<div><b>{s["sucres_g"]} g</b><small>Sugar</small></div>'
                '</div><p class="muted" style="margin-top:.5rem">Estimated by the AI. Not a substitute for medical advice.</p>',
                unsafe_allow_html=True)

    st.markdown('<div class="section">Ingredients</div>', unsafe_allow_html=True)
    dans_frigo = [n.lower() for n in noms_frigo()]
    absents = []
    for i in recette["ingredients"]:
        jai = any(n in i["nom"].lower() or i["nom"].lower() in n for n in dans_frigo)
        if not jai:
            absents.append(i["nom"])
        etat = '<span class="tag ok">In fridge</span>' if jai else '<span class="tag no">Missing</span>'
        st.markdown(f'<div class="frow" style="padding:.6rem .85rem"><div class="finfo"><b>{h(i["nom"])}</b>'
                    f'<small>{h(i["quantite"])}</small></div>{etat}</div>', unsafe_allow_html=True)
    if absents:
        st.button(f"Add {len(absents)} missing item(s) to my shopping list", key="vers_courses", width="stretch",
                  icon=":material/shopping_cart:", on_click=courses_depuis_recette, args=(absents, recette["titre"]))
    st.markdown('<div class="section">Steps</div>' + "".join(
        f'<div class="step"><div class="n">{n}</div><div>{h(e)}</div></div>'
        for n, e in enumerate(recette["etapes"], 1)), unsafe_allow_html=True)
    if recette.get("astuce_anti_gaspi"):
        st.markdown(f'<div class="tip">{h(recette["astuce_anti_gaspi"])}</div>', unsafe_allow_html=True)

    with st.popover("Share with the community", icon=":material/share:", width="stretch"):
        cat = st.selectbox("Category", list(communaute.CATEGORIES), format_func=communaute.CATEGORIES.get, key="w_cat_partage")
        if st.button("Publish this recipe", type="primary", width="stretch", key="publier_ia"):
            sante = {"calories": s["calories"], "proteines_g": s["proteines_g"], "glucides_g": s["glucides_g"],
                     "lipides_g": s["lipides_g"]}
            nouvel_id = communaute.publier(
                pseudo, recette["titre"], "Created from my fridge with the AI.", cat,
                int(recette["temps_preparation_minutes"]) + int(recette["temps_cuisson_minutes"]), int(recette["portions"]),
                [{"quantite": i["quantite"], "nom": i["nom"]} for i in recette["ingredients"]], recette["etapes"], sante)
            st.session_state.comm_detail, st.session_state.page = nouvel_id, "Community"
            st.rerun()

    st.button("Start cooking", key="go_cuisson", on_click=demarrer_cuisson, width="stretch", type="primary",
              icon=":material/play_arrow:")
    st.write("")
    if st.button("I cooked this", width="stretch", icon=":material/check_circle:"):
        utilises = aliments_utilises(recette, plat)
        points = db.enregistrer_plat(groupe, pseudo, plat["nom"], int(plat["niveau_elaboration"]),
                                     len(utilises), int(plat.get("temps_minutes", 0)))
        db.retirer_par_noms(groupe, pseudo, utilises)  # ces aliments ne sont plus dans le frigo
        st.session_state.recette_enregistree = True
        st.session_state.celebre = {"points": points, "nom": plat["nom"], "sauves": len(utilises)}
        st.rerun()

    def retour():
        st.session_state.recette = None
    gauche, droite = st.columns(2)
    gauche.button("Back", key="back_2", on_click=retour, icon=":material/arrow_back:", width="stretch")
    droite.button("New scan", key="reset_2", on_click=nouveau_scan, icon=":material/refresh:", width="stretch")


# ----------------------------------------------------------------------- ÉCRAN : Community
def ouvrir_recette(recette_id):
    st.session_state.comm_detail = recette_id
    st.session_state.page = "Community"


def retour_communaute():
    st.session_state.comm_detail = None


def image_recette(r: dict, hauteur: int = 150) -> str:
    """La photo de l'auteur si elle existe, sinon un dessin dans le style du logo."""
    adresse = communaute.image_en_html(r.get("image"))
    if adresse:
        return f'<img src="{adresse}" alt="" style="width:100%;height:{hauteur}px;object-fit:cover;display:block">'
    return illustrations.vignette(r["categorie"], hauteur=hauteur)


def page_communaute():
    if st.session_state.get("comm_detail"):
        return detail_recette(st.session_state.comm_detail)
    entete("Community", action=("", "go_upload", aller_a, ("Upload",), "add", "Share one of your recipes"))
    vue = onglets("comm_vue", ["Feed", "Friends", "Challenges"], "Feed")
    {"Feed": vue_decouvrir, "Friends": vue_amis, "Challenges": page_defis}[vue]()


def joli_jour(iso: str) -> str:
    """« today », « yesterday » ou « Nov 12 »."""
    try:
        jour = date.fromisoformat(iso)
    except ValueError:
        return iso
    ecart = (date.today() - jour).days
    if ecart <= 0:
        return "today"
    if ecart == 1:
        return "yesterday"
    if ecart < 7:
        return f"{ecart} days ago"
    return jour.strftime("%b %d").replace(" 0", " ")


def aimer_recette(recette_id):
    if communaute.aimer(recette_id, pseudo):
        st.session_state.vient_daimer = recette_id   # pour l'animation des petits cœurs


def vue_decouvrir():
    nouveaux = communaute.nb_non_lus(pseudo)
    if nouveaux:
        st.button(f"{nouveaux} new recipe(s) from your friends", key="vers_amis", width="stretch",
                  icon=":material/send:", on_click=garder_et_aller, args=("comm_vue", "Friends"))
    filtre = st.segmented_control(" ", ["All", "Friends", "Veggie", "Meat", "Fish"], default="All",
                                  key="w_comm_filtre", label_visibility="collapsed") or "All"
    categorie = {"Veggie": "veg", "Meat": "meat", "Fish": "fish"}.get(filtre)
    recettes = communaute.lister_recettes(categorie, pseudo=pseudo, amis_seulement=filtre == "Friends")
    if not recettes:
        st.markdown(f'<div class="empty"><span class="bob">{illustrations.mascotte(64)}</span>'
                    '<div><b>No recipe yet</b><p>Be the first: tap + at the top to share one of yours. '
                    'Recipes from your friends will show up here too.</p></div></div>',
                    unsafe_allow_html=True)
        st.button("Share a recipe", key="vide_upload", on_click=aller_a, args=("Upload",), width="stretch",
                  type="primary", icon=":material/add:")
    amis = communaute.lister_amis(pseudo)
    for r in recettes:
        with st.container(key=f"cr_{r['id']}"):
            badge = f'<span class="postbadge">{h(r["badge"])}</span>' if r.get("badge") else ""
            st.markdown(f'<div class="phead"><span class="av">{initiales(r["auteur"])}</span>'
                        f'<span class="pwho"><b>{h(r["auteur"])}</b>'
                        f'<small>{joli_jour(r["jour"])} · {r["minutes"]} min · {communaute.CATEGORIES[r["categorie"]]}</small>'
                        '</span></div>'
                        f'<div class="cimg">{badge}{image_recette(r)}</div>'
                        f'<div class="cbody"><b>{h(r["titre"])}</b>'
                        f'<p class="muted">{h(r["description"])}</p></div>', unsafe_allow_html=True)
            coeur, envoi, plus, ouvrir = st.columns([1, 1, 1, 2], vertical_alignment="center")
            if st.session_state.get("vient_daimer") == r["id"]:
                st.session_state.pop("vient_daimer")
                coeur.markdown('<div class="hearts">' + "".join(
                    f'<span style="--hx:{(i - 2) * 16}px;animation-delay:{i * .07:.2f}s">♥</span>'
                    for i in range(5)) + '</div>', unsafe_allow_html=True)
            coeur.button(str(r["coeurs"]), key=f"like_{'on' if r['aime'] else 'off'}_{r['id']}",
                         on_click=aimer_recette, args=(r["id"],), width="stretch",
                         icon=":material/favorite:" if r["aime"] else ":material/favorite_border:")
            with envoi.popover("", icon=":material/send:", width="stretch"):
                if amis:
                    a_qui = st.multiselect("Send to", amis, key=f"to_{r['id']}")
                    mot = st.text_input("Short message", key=f"msg_{r['id']}", placeholder="You will love this one!")
                    if st.button("Send", key=f"go_{r['id']}", type="primary", width="stretch", disabled=not a_qui):
                        for ami in a_qui:
                            communaute.partager(pseudo, ami, r["id"], mot)
                        st.success("Sent!")
                else:
                    st.caption("Add a friend first, in the Friends tab.")
            with plus.popover("", icon=":material/more_horiz:", width="stretch"):
                if r["auteur"].lower() == pseudo.lower():
                    if st.button("Delete my recipe", key=f"suppr_{r['id']}", width="stretch",
                                 icon=":material/delete:"):
                        communaute.supprimer_recette(r["id"], pseudo)
                        st.rerun()
                else:
                    motif = st.text_input("What is wrong?", key=f"mot_{r['id']}",
                                          placeholder="Not food, rude, dangerous…")
                    if st.button("Report", key=f"sig_{r['id']}", width="stretch", icon=":material/flag:"):
                        communaute.signaler(r["id"], pseudo, motif or "no reason given")
                        st.success("Thanks, we will look at it.")
            ouvrir.button("Cook this", key=f"voir_{r['id']}", on_click=ouvrir_recette, args=(r["id"],),
                          width="stretch", type="primary")


def garder_et_aller(cle, valeur):
    st.session_state[cle] = valeur


def page_upload():
    sous_entete("Share a recipe", "Community", "upload")
    vue_publier()


def vue_publier():
    if "flash_pub" in st.session_state:
        st.success(st.session_state.pop("flash_pub"))
    st.markdown('<p class="muted">Everyone in the community sees all the details, and you can send it to your '
                'friends.</p>', unsafe_allow_html=True)
    v = st.session_state.pub_v  # change après une publication : le formulaire repart vide, mais garde tout en cas d'erreur
    with st.form(f"publier_{v}", border=False):
        titre = st.text_input("Recipe name", key=f"pub_titre_{v}", placeholder="Grandma's tomato soup")
        photo = st.file_uploader("Photo of your dish (optional)", type=["jpg", "jpeg", "png", "webp"], key=f"pub_photo_{v}")
        c1, c2, c3 = st.columns(3)
        categorie = c1.selectbox("Type", list(communaute.CATEGORIES), format_func=communaute.CATEGORIES.get)
        minutes = c2.number_input("Minutes", 1, 600, 30)
        portions = c3.number_input("Servings", 1, 20, 2)
        description = st.text_area("Short description", key=f"pub_desc_{v}", placeholder="What makes this recipe special?", height=80)
        st.markdown('<div class="small-caps">Ingredients</div>', unsafe_allow_html=True)
        ingredients = st.data_editor(pd.DataFrame({"quantite": ["", "", ""], "nom": ["", "", ""]}), num_rows="dynamic",
                                     width="stretch", key=f"editeur_pub_{v}",
                                     column_config={"quantite": "Quantity", "nom": "Ingredient"})
        etapes = st.text_area("Steps (one per line)", key=f"pub_etapes_{v}", placeholder="Chop the onions.\nFry them for 5 minutes.", height=140)
        with st.expander("Nutrition per serving (optional)"):
            n1, n2 = st.columns(2)
            calories = n1.number_input("Calories (kcal)", 0, 3000, 0)
            proteines = n2.number_input("Protein (g)", 0, 300, 0)
            glucides = n1.number_input("Carbohydrates (g)", 0, 500, 0)
            lipides = n2.number_input("Fat (g)", 0, 300, 0)
        envoye = st.form_submit_button("Publish my recipe", type="primary", width="stretch")

    if envoye:
        lignes = ingredients.fillna("").to_dict("records")
        etapes_liste = etapes.splitlines()
        if not titre.strip() or not any(str(i["nom"]).strip() for i in lignes) or not any(e.strip() for e in etapes_liste):
            st.error("Please add a name, at least one ingredient and at least one step.")
            return
        image = communaute.reduire_image(photo.getvalue()) if photo else None
        sante = {"calories": calories, "proteines_g": proteines, "glucides_g": glucides, "lipides_g": lipides} if calories else {}
        nouvel_id = communaute.publier(pseudo, titre, description, categorie, minutes, portions, lignes, etapes_liste,
                                       sante, image)
        st.session_state.flash_pub = "Your recipe is published!"
        st.session_state.pub_v += 1
        st.session_state.page = "Community"
        ouvrir_recette(nouvel_id)
        st.rerun()


def vue_amis():
    amis = communaute.lister_amis(pseudo)
    messages = communaute.boite_reception(pseudo)

    mon_code = communaute.code_ami(pseudo)
    st.markdown(carte_code(mon_code, "Give this code to your friends so they can add you."), unsafe_allow_html=True)

    st.markdown('<div class="section">Add a friend</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    nom = c1.text_input("Friend code", key="w_ami", placeholder="Their code, e.g. emma-74",
                        label_visibility="collapsed")
    if c2.button("Add", width="stretch", type="primary", icon=":material/person_add:"):
        resultat = communaute.ajouter_par_code(pseudo, nom)
        reponses = {"ok": ("success", "Added! You can now send each other recipes."),
                    "soi": ("warning", "That is your own code!"), "deja": ("info", "You are already friends."),
                    "inconnu": ("error", "No player with this code. Check it, or ask them to open the app once.")}
        getattr(st, reponses[resultat][0])(reponses[resultat][1])
        if resultat == "ok":
            st.rerun()

    if messages:
        st.markdown(f'<div class="section">Sent to you <span class="muted">{len(messages)}</span></div>',
                    unsafe_allow_html=True)
        for m in messages:
            with st.container(key=f"inb_{m['id']}"):
                nouveau = '<span class="tag no">New</span>' if not m["lu"] else ""
                texte = f'<p class="muted">“{h(m["message"])}”</p>' if m["message"] else ""
                st.markdown(f'<div class="cbody"><div class="cmeta">From <b>{h(m["de"])}</b> · {m["jour"]} {nouveau}</div>'
                            f'<b>{h(m["titre"])}</b>{texte}</div>', unsafe_allow_html=True)
                st.button("Open recipe", key=f"ouvrir_{m['id']}", on_click=ouvrir_recette, args=(m["recette_id"],),
                          width="stretch")
        communaute.marquer_lus(pseudo)

    st.markdown(f'<div class="section">My friends <span class="muted">{len(amis)}</span></div>', unsafe_allow_html=True)
    if not amis:
        st.markdown(f'<div class="empty"><span class="bob">{illustrations.mascotte(56)}</span>'
                    '<div><b>No friends yet</b><p>Send your code to a friend. Once they add it, you can '
                    'send each other recipes and compete.</p></div></div>', unsafe_allow_html=True)
    for a in amis:
        ligne, bouton = st.columns([4, 1], vertical_alignment="center")
        stats_ami = db.stats_joueur(groupe, a)
        serie = len([1 for _, n in db.activite_semaine(groupe, a) if n])
        ligne.markdown(f'<div class="rank" style="margin:0"><div class="av">{initiales(a)}</div>'
                       f'<div class="who"><b>{h(a)}</b>'
                       f'<small>{serie} day(s) cooking · {stats_ami["repas"]} meals</small></div>'
                       f'<span class="codetag">{h(communaute.code_ami(a))}</span></div>', unsafe_allow_html=True)
        if bouton.button("", key=f"rm_{a}", icon=":material/person_remove:", help=f"Remove {a}"):
            communaute.retirer_ami(pseudo, a)
            st.rerun()

    proposes = communaute.suggestions(pseudo)
    if proposes:
        st.markdown('<div class="section">People in the app</div>', unsafe_allow_html=True)
        for p in proposes:
            ligne, bouton = st.columns([3, 2], vertical_alignment="center")
            ligne.markdown(f'<div class="rank" style="margin:0"><div class="av">{initiales(p)}</div>'
                           f'<div class="who"><b>{h(p)}</b></div></div>', unsafe_allow_html=True)
            if bouton.button("Add", key=f"sug_{p}", width="stretch"):
                communaute.ajouter_ami(pseudo, p)
                st.rerun()




MEDAILLES = {1: "gold", 2: "silver", 3: "bronze"}


def ligne_classement(rang: int, nom: str, titre: str, valeur: str, sous_titre: str) -> str:
    moi = nom == pseudo
    couleur = MEDAILLES.get(rang, "")
    return (f'<div class="rank{" me" if moi else ""}"><div class="medal {couleur}">{rang}</div>'
            f'<div class="av">{initiales(nom)}</div>'
            f'<div class="who"><b>{h(nom)}{" (you)" if moi else ""}</b><small>{h(titre)}</small></div>'
            f'<div class="pct"><b>{valeur}</b><small>{sous_titre}</small></div></div>')


def page_defis():
    """Les deux concours, dans l'onglet Challenges de Community."""
    stats = db.stats_joueur(groupe, pseudo)
    score = stats["score"] if stats["score"] is not None else 0
    st.markdown('<div class="chalcard"><div class="chead">'
                '<b>Least waste this week</b><span class="chip">ends Sunday</span></div>'
                f'<p>Your score: {score:.0f}% of your food used up.</p>'
                f'<div class="cbar"><div style="width:{min(100, score):.0f}%"></div></div></div>',
                unsafe_allow_html=True)
    vue = st.segmented_control(" ", ["Waste", "Tournament"], default="Waste",
                               key="vue_defis", label_visibility="collapsed") or "Waste"
    if vue == "Waste":
        vue_classement()
    else:
        vue_tournoi()


def vue_classement():
    classement = db.classement_anti_gaspi(groupe, depuis=scoring.debut_de_semaine())
    restant = scoring.jours_restants_semaine()
    fin = "Ends today" if restant == 0 else "Ends tomorrow" if restant == 1 else f"Ends in {restant} days"
    st.markdown(f'<div class="weekly"><div class="ico">♻</div><div><div class="tag">WEEKLY CHALLENGE</div>'
                f'<b>Zero waste in 7 days</b><span class="muted">{len(classement)} participant(s) · {fin}</span></div></div>'
                '<div class="small-caps">Anti-waste rankings</div>', unsafe_allow_html=True)

    if not classement:
        st.markdown(f'<div class="tipbox"><span class="wiggle">{illustrations.mascotte(50)}</span>'
                    '<div>Nobody has cooked this week yet. Cook one dish and you take the lead!</div></div>',
                    unsafe_allow_html=True)
        st.button("Find a recipe", key="chal_cook", on_click=aller_a, args=("Recipes",), width="stretch",
                  type="primary", icon=":material/restaurant:")
    st.markdown("".join(
        ligne_classement(r, j["pseudo"], scoring.titre_selon_score(j["score"]), f'{j["score"]:.0f}%',
                         f'{j["points"]} pts') for r, j in enumerate(classement, 1)), unsafe_allow_html=True)

    moi = next(((r, j) for r, j in enumerate(classement, 1) if j["pseudo"] == pseudo), None)
    if moi:
        rang, joueur = moi
        if rang == 1:
            message = "You lead the week! Keep it up."
        else:
            devant = classement[rang - 2]
            ecart = max(1, math.ceil(devant["score"] - joueur["score"] + 0.01))
            message = f"+{ecart}% and you overtake {h(devant['pseudo'])} this week!"
        st.markdown(f'<div class="scorebox"><div class="top"><span>Your anti-waste score</span>'
                    f'<b>{joueur["score"]:.0f}%</b></div><div class="bar"><div style="width:{joueur["score"]}%"></div></div>'
                    f'<span class="muted">{message}</span></div>', unsafe_allow_html=True)

    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    with st.expander("Log my week"):
        with st.form("gaspi", border=False):
            c1, c2 = st.columns(2)
            utilises = c1.number_input("Food items used", 0, 200, 0)
            jetes = c2.number_input("Food items thrown away", 0, 200, 0)
            if st.form_submit_button("Save", width="stretch", type="primary"):
                db.enregistrer_gaspillage(groupe, pseudo, int(utilises), int(jetes))
                st.session_state.flash = "Saved!"
                st.rerun()


def vue_tournoi():
    st.markdown('<p class="muted" style="margin-top:.8rem">Three rounds, from the simplest to the most elaborate. '
                'The more elaborate the dish, the more points it gives.</p>', unsafe_allow_html=True)
    classements = db.classement_tournoi(groupe)
    for manche, titre in scoring.MANCHES.items():
        st.markdown(f'<div class="small-caps">{h(titre)}</div>', unsafe_allow_html=True)
        if classements[manche]:
            st.markdown("".join(
                ligne_classement(r, j["pseudo"], f'{j["plats"]} dish(es) cooked', f'{j["points"]}', "points")
                for r, j in enumerate(classements[manche], 1)), unsafe_allow_html=True)
        else:
            st.markdown('<p class="muted">Nobody has cooked in this round yet.</p>', unsafe_allow_html=True)


# ----------------------------------------------------------------------- ÉCRAN : Recap (bilan de la semaine)
def page_bilan():
    stats = db.stats_joueur(groupe, pseudo)
    semaine = db.activite_semaine(groupe, pseudo)
    score = stats["score"] if stats["score"] is not None else 0
    maxi = max([n for _, n in semaine] + [1])
    meilleur = max(range(7), key=lambda i: semaine[i][1])
    barres = "".join(
        f'<div><i class="{"top" if i == meilleur and semaine[i][1] else ""}" style="height:{max(6, semaine[i][1] / maxi * 100):.0f}%;'
        f'animation-delay:{.3 + i * .1:.1f}s"></i>{semaine[i][0]}</div>' for i in range(7))
    reste = 390 - 390 * score / 100
    anneau = (f'<svg width="130" height="130" viewBox="0 0 150 150"><circle cx="75" cy="75" r="62" fill="none" stroke="#E3F1E9" stroke-width="14"/>'
              f'<circle cx="75" cy="75" r="62" fill="none" stroke="#177A54" stroke-width="14" stroke-linecap="round" stroke-dasharray="390" '
              f'stroke-dashoffset="{reste:.0f}" transform="rotate(-90 75 75)"><animate attributeName="stroke-dashoffset" from="390" '
              f'to="{reste:.0f}" dur="1.4s" fill="freeze"/></circle><text x="75" y="82" text-anchor="middle" font-family="Inter" '
              f'font-size="34" font-weight="600" fill="#0F1A14">{score:.0f}%</text></svg>')
    sous_entete("Your week", "Home", "recap")
    st.markdown(
        f'<div class="recap"><div class="ringbox"><div style="line-height:0">{anneau}</div><div><b style="font-size:1.1rem">'
        f'{"Great week!" if score >= 70 else "Keep going!"}</b><p class="muted" style="margin:.3rem 0">Your anti-waste score: how much of your food you used up.</p></div></div>'
        f'<div class="stats"><div class="stat"><b>{stats["repas"]}</b><small>Meals cooked</small></div>'
        f'<div class="stat"><b>{scoring.kg_evites(stats["sauves"])} kg</b><small>Waste avoided</small></div>'
        f'<div class="stat"><b>{stats["points"]}</b><small>Points</small></div></div>'
        f'<div class="barsbox"><b>Ingredients saved each day</b><div class="bars">{barres}</div></div>'
        f'<div class="tipbox"><span class="wiggle" style="line-height:0">{illustrations.mascotte(60)}</span>'
        '<div><b>Tip of the week</b><p class="muted" style="margin:.2rem 0 0">Freeze bread and spinach on day 3 to stop them from going bad.</p></div></div></div>',
        unsafe_allow_html=True)



# ----------------------------------------------------------------------- ÉCRAN : Profile
def carte_code(code: str, sous_titre: str) -> str:
    """La carte verte qui montre le code d'ami."""
    return (
        '<div style="display:flex;align-items:center;gap:.9rem;background:#E3F1E9;border-radius:20px;'
        'padding:1rem 1.1rem;margin:.5rem 0 .3rem">'
        '<div style="flex:1;display:flex;flex-direction:column;gap:.15rem">'
        '<span style="font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;'
        'color:#177A54">Your friend code</span>'
        f'<span style="font-size:1.45rem;font-weight:600;letter-spacing:-0.01em;color:#0F1A14">{h(code)}</span>'
        f'<span style="font-size:.78rem;color:#5F6B63">{h(sous_titre)}</span></div>'
        f'<span class="bob" style="line-height:0;flex:0 0 auto">{illustrations.mascotte(56)}</span></div>')


def badge(nom_dessin, texte, gagne):
    dessin = illustrations.objet(nom_dessin, 34)
    classe = "badge" if gagne else "badge off"
    return f'<div class="{classe}"><span class="bi">{dessin}</span><span>{h(texte)}</span></div>'


def page_profil():
    stats = db.stats_joueur(groupe, pseudo)
    niveau, progression = scoring.niveau_joueur(stats["points"])
    titre = scoring.titre_selon_score(stats["score"])
    repas, sauves = stats["repas"], stats["sauves"]
    euros = int(sauves * 1.4)
    sous_entete("Profile", "Home", "profil")
    st.markdown(f'<div class="profile"><div class="big-av">{initiales(pseudo)}</div><div class="info">'
                f'<b>{h(pseudo)}</b><div class="muted">{titre} · Level {niveau}</div>'
                f'<div class="bar" style="margin:.5rem 0 .2rem"><div style="width:{progression}%"></div></div>'
                f'<small>{progression}% to level {niveau + 1}</small></div></div>'
                '<div class="impact"><div class="ihead"><b>Your impact</b><span>since day one</span></div>'
                f'<div class="irow"><div><b>€{euros}</b><small>saved</small></div>'
                f'<div><b>{scoring.kg_evites(sauves)} kg</b><small>food saved</small></div>'
                f'<div><b>{scoring.kg_evites(sauves) * 2.5:.1f} kg</b><small>CO₂ avoided</small></div></div>'
                f'<div class="iline">{serie_jours()} day streak · {repas} meals cooked</div></div>',
                unsafe_allow_html=True)

    gagnes = [repas >= 1, serie_jours() >= 3, repas >= 10, sauves >= 20, repas >= 25, len(communaute.lister_amis(pseudo)) >= 1]
    noms = [("frigo", "First scan"), ("tomate", "3-day streak"), ("pizza", "10 meals"),
            ("brocoli", "20 items saved"), ("poisson", "Top chef"), ("fromage", "Sharing is caring")]
    st.markdown(f'<div class="section">Badges <span class="muted">{sum(gagnes)} of 6</span></div>'
                f'<div class="badges">{"".join(badge(n, t, g) for (n, t), g in zip(noms, gagnes))}</div>',
                unsafe_allow_html=True)

    st.markdown(carte_code(communaute.code_ami(pseudo), "Friends type this code to add you."), unsafe_allow_html=True)
    st.button("My kitchen", key="go_prefs", on_click=aller_a, args=("Prefs",), width="stretch",
              icon=":material/tune:")
    st.button("My week", key="go_recap2", on_click=aller_a, args=("Recap",), width="stretch",
              icon=":material/insights:")

    st.markdown('<div class="section">Settings</div>', unsafe_allow_html=True)
    st.selectbox("Recipe language", LANGUES, index=LANGUES.index(langue), key="w_langue", on_change=maj_langue)
    st.number_input("Servings", 1, 10, value=st.session_state.portions, key="w_portions", on_change=maj_portions)
    st.text_input("Friends group code", value=groupe, key="w_groupe", on_change=maj_groupe,
                  help="Your friends type the same code to play in the same competition.")

    st.markdown('<div class="section">Account</div>', unsafe_allow_html=True)
    compte = st.session_state.compte
    st.markdown(f'<p class="muted">Signed in as <b>{h(compte["email"])}</b></p>', unsafe_allow_html=True)

    with st.expander("Change my name"):
        nouveau = st.text_input("New name", value=pseudo, key="w_new_pseudo")
        if st.button("Save my name", key="save_pseudo", width="stretch", type="primary"):
            etat, message = comptes.changer_pseudo(compte["email"], nouveau)
            (st.success if etat == "ok" else st.error)(message)
            if etat == "ok":
                st.rerun()

    with st.expander("Change my password"):
        ancien = st.text_input("Current password", type="password", key="w_mdp_ancien")
        nouveau_mdp = st.text_input("New password", type="password", key="w_mdp_nouveau")
        if st.button("Save my password", key="save_mdp", width="stretch", type="primary"):
            etat, message = comptes.changer_mdp(compte["email"], ancien, nouveau_mdp)
            (st.success if etat == "ok" else st.error)(message)

    with st.expander("Send feedback"):
        texte = st.text_area("What works, what does not?", key="w_avis", height=100,
                             placeholder="The scan missed my yoghurts…")
        if st.button("Send", key="env_avis", width="stretch", type="primary", disabled=not texte.strip()):
            communaute.envoyer_avis(pseudo, texte)
            st.success("Thanks! Your message is on its way.")

    st.button("Privacy and data", key="go_privacy", on_click=aller_a, args=("Privacy",), width="stretch",
              icon=":material/shield:")
    st.button("Log out", key="deconnexion", on_click=deconnecter, width="stretch", icon=":material/logout:")

    if comptes.est_admin(compte):
        with st.expander("Admin: AI budget"):
            ok, raison, faits, maxi = reglages.etat_ia()
            st.markdown(f'<p class="muted">Scans used: <b>{faits}</b>'
                        + (f' of {maxi}' if maxi else '') + '<br>'
                        f'Model: <b>{ai.MODELE}</b> · about $0.0004 per scan<br>'
                        f'Status: <b>{"working" if ok else "paused"}</b>'
                        + (f'<br>{h(reglages.raison_blocage())}' if not ok else '')
                        + '</p>', unsafe_allow_html=True)
            if not ok and st.button("Turn the AI back on", key="debloque_ia", width="stretch"):
                reglages.debloquer_ia()
                st.rerun()

        with st.expander("Admin: reports and feedback"):
            signalements = communaute.lister_signalements()
            st.markdown(f'<div class="section">Reports ({len(signalements)})</div>', unsafe_allow_html=True)
            for sig in signalements:
                st.markdown(f'<p class="muted"><b>{h(sig["titre"] or "deleted recipe")}</b> by '
                            f'{h(sig["auteur"] or "?")} — reported by {h(sig["par"])}: '
                            f'{h(sig["motif"])}</p>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Delete the recipe", key=f"adm_del_{sig['id']}", width="stretch"):
                    communaute.supprimer_recette(sig["recette_id"], sig["auteur"] or "")
                    communaute.classer_signalement(sig["id"])
                    st.rerun()
                if c2.button("Keep it", key=f"adm_ok_{sig['id']}", width="stretch"):
                    communaute.classer_signalement(sig["id"])
                    st.rerun()
            avis = communaute.lister_avis()
            st.markdown(f'<div class="section">Feedback ({len(avis)})</div>', unsafe_allow_html=True)
            for a in avis[:20]:
                st.markdown(f'<p class="muted"><b>{h(a["pseudo"])}</b> · {a["jour"]}<br>{h(a["texte"])}</p>',
                            unsafe_allow_html=True)

    with st.expander("Delete my account"):
        st.markdown('<p class="muted">Everything goes: your fridge, your recipes, your points, your '
                    'friends. This cannot be undone.</p>', unsafe_allow_html=True)
        confirmation = st.text_input('Type DELETE to confirm', key="w_suppr")
        if st.button("Delete my account for good", key="suppr_compte", width="stretch",
                     disabled=confirmation.strip().upper() != "DELETE"):
            comptes.supprimer_compte(compte["email"], pseudo, groupe)
            deconnecter()
            st.rerun()


# ----------------------------------------------------------------------- ÉCRAN : Privacy
def page_confidentialite():
    sous_entete("Privacy and data", "Profile", "privacy")
    st.markdown(
        '<div class="section">What we keep</div>'
        '<p class="muted">Your email and your name, so you can log in and your friends can find you. '
        'The food in your fridge, the dishes you cook and your points. The recipes and photos you '
        'choose to publish.</p>'
        '<div class="section">Your fridge photos</div>'
        '<p class="muted">A photo you scan is sent to the AI to read what is inside, then thrown away. '
        'It is never published and never shown to anyone else.</p>'
        '<div class="section">Who sees what</div>'
        '<p class="muted">Your fridge and your shopping list are yours alone. Your name, your level and '
        'your score appear in the competition with the friends who share your group code. A recipe is '
        'visible to everyone only once you publish it.</p>'
        '<div class="section">Your rights</div>'
        '<p class="muted">You can change your name, see everything you have, and delete your account '
        'with all your data, from your profile. Nothing is sold, and there is no advertising.</p>'
        '<div class="section">Food safety</div>'
        '<p class="muted">Expiry dates and nutrition figures are estimates. Always look at the label, '
        'and at the food itself, before eating. The allergy filter helps, but it can be wrong: check '
        'the ingredients yourself.</p>', unsafe_allow_html=True)


# ----------------------------------------------------------------------- ÉCRAN : My kitchen (filtre les recettes)
def page_prefs():
    appareils, regimes, allergies = mes_choix()
    possible = filtres.compter(catalogue.RECETTES, appareils, regimes, allergies)
    sous_entete("My kitchen", "Profile", "prefs")
    st.markdown(f'<div class="tipbox"><span class="wiggle">{illustrations.mascotte(56)}</span>'
                f'<div>What you tick here changes the recipes you are shown. Right now: '
                f'<b>{possible} of {len(catalogue.RECETTES)}</b> ideas fit.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section">My appliances</div>', unsafe_allow_html=True)
    grille_pastilles(APPAREILS, "ustensiles", "app")
    st.markdown('<div class="section">My diet</div>', unsafe_allow_html=True)
    grille_pastilles(REGIMES, "regimes", "diet")
    st.markdown('<div class="section">Avoid (allergies)</div>', unsafe_allow_html=True)
    grille_pastilles(ALLERGIES, "allergies", "alg")
    st.caption("The app guesses allergens from the name of the dish, so it can be wrong. If an allergy "
               "is serious, read the ingredients yourself every time.")
    st.button("See my recipes", key="prefs_go_cook", on_click=aller_a, args=("Recipes",), width="stretch",
              type="primary", icon=":material/restaurant:")


# ----------------------------------------------------------------------- affichage
PAGES = {"Home": page_home, "Scan": page_scan, "Fridge": page_frigo, "Challenges": page_defis,
         "Profile": page_profil, "Recipes": page_recettes, "Community": page_communaute, "Recap": page_bilan,
         "Prefs": page_prefs, "Upload": page_upload, "Cooking": page_cuisson,
         "Privacy": page_confidentialite}
afficher_page = PAGES[st.session_state.page]
afficher_page()

with st.container(key="bottomnav"):
    for colonne, (nom, icone, texte) in zip(st.columns(len(NAV)), NAV):
        actif = st.session_state.page == nom
        colonne.button(texte, key=f"nav_{'on' if actif else 'off'}_{nom}", icon=f":material/{icone}:",
                       on_click=aller_a, args=(nom,), width="stretch")