"""Communauté : recettes publiées par les joueurs, amis, et recettes envoyées entre amis."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from datetime import date

from . import db

CATEGORIES = {"veg": "Vegetarian", "meat": "Meat", "fish": "Fish"}


def initialiser(chemin: str | None = None) -> None:
    with db._connexion(chemin) as con:
        con.script(
            """
            CREATE TABLE IF NOT EXISTS joueurs (pseudo TEXT PRIMARY KEY COLLATE NOCASE);
            CREATE TABLE IF NOT EXISTS amis (
                pseudo TEXT NOT NULL COLLATE NOCASE,
                ami TEXT NOT NULL COLLATE NOCASE,
                PRIMARY KEY (pseudo, ami)
            );
            CREATE TABLE IF NOT EXISTS recettes_communaute (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auteur TEXT NOT NULL,
                titre TEXT NOT NULL,
                description TEXT NOT NULL,
                categorie TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                portions INTEGER NOT NULL,
                ingredients TEXT NOT NULL,
                etapes TEXT NOT NULL,
                sante TEXT NOT NULL,
                image BLOB,
                jour TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS signalements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recette_id INTEGER NOT NULL,
                par TEXT NOT NULL,
                motif TEXT NOT NULL,
                jour TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS avis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pseudo TEXT NOT NULL,
                texte TEXT NOT NULL,
                jour TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jaime (
                recette_id INTEGER NOT NULL,
                pseudo TEXT NOT NULL COLLATE NOCASE,
                PRIMARY KEY (recette_id, pseudo)
            );
            CREATE TABLE IF NOT EXISTS partages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                de TEXT NOT NULL,
                a TEXT NOT NULL COLLATE NOCASE,
                recette_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                jour TEXT NOT NULL,
                lu INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        # Pas de faux joueurs ni de fausses recettes : la communauté commence vide.


def charger_exemples(chemin=None) -> None:
    """Ajoute trois joueurs et leurs recettes, pour une démonstration. Jamais appelé tout seul."""
    with db._connexion(chemin) as con:
        if con.execute("SELECT COUNT(*) AS n FROM joueurs").fetchone()["n"] == 0:
            _exemples(con)


def _exemples(con) -> None:
    """Quelques joueurs et recettes d'exemple, pour une démonstration."""
    for nom in ("Emma", "Lucas", "Sofia"):
        con.execute("INSERT OR IGNORE INTO joueurs (pseudo) VALUES (?)", (nom,))
    exemples = [
        ("Emma", "Lemon salmon with spinach", "Quick weeknight dinner that uses up spinach and a lemon.", "fish", 25, 2,
         [("2 fillets", "Salmon"), ("200 g", "Spinach"), ("1", "Lemon"), ("1 tbsp", "Olive oil"), ("2 cloves", "Garlic")],
         ["Heat the oil in a pan and cook the garlic for 30 seconds.", "Add the salmon, skin side down, and cook 5 minutes.",
          "Turn the fish, add the spinach and a squeeze of lemon.", "Cook 3 more minutes, season and serve."],
         {"calories": 380, "proteines_g": 34, "glucides_g": 4, "lipides_g": 24}),
        ("Lucas", "Fridge-clean-out fried rice", "Leftover rice, any vegetables and an egg. Ready in 15 minutes.", "veg", 15, 2,
         [("300 g", "Cooked rice"), ("2", "Eggs"), ("1 cup", "Mixed vegetables"), ("2 tbsp", "Soy sauce")],
         ["Fry the vegetables in a hot pan for 3 minutes.", "Push them aside, scramble the eggs.",
          "Add the rice and soy sauce and stir for 4 minutes."],
         {"calories": 410, "proteines_g": 15, "glucides_g": 60, "lipides_g": 11}),
        ("Sofia", "Garlic chicken and peppers", "One tray in the oven, almost no dishes.", "meat", 40, 3,
         [("500 g", "Chicken breast"), ("2", "Bell peppers"), ("3 cloves", "Garlic"), ("2 tbsp", "Olive oil")],
         ["Heat the oven to 200 °C.", "Cut everything in pieces and mix with the oil and garlic on a tray.",
          "Bake for 30 minutes, turning once."],
         {"calories": 340, "proteines_g": 38, "glucides_g": 9, "lipides_g": 17}),
    ]
    for auteur, titre, desc, cat, minutes, portions, ingr, etapes, sante in exemples:
        con.execute(
            "INSERT INTO recettes_communaute (auteur, titre, description, categorie, minutes, portions, ingredients, "
            "etapes, sante, image, jour) VALUES (?,?,?,?,?,?,?,?,?,NULL,?)",
            (auteur, titre, desc, cat, minutes, portions,
             json.dumps([{"quantite": q, "nom": n} for q, n in ingr]), json.dumps(etapes), json.dumps(sante),
             date.today().isoformat()))


# ------------------------------------------------------------------ joueurs et amis
def code_ami(pseudo: str) -> str:
    """Code court et stable pour un joueur, du genre « benjamin-07 ». On le donne à ses amis."""
    propre = re.sub(r"[^a-z0-9]+", "", pseudo.lower()) or "player"
    numero = int(hashlib.sha1(pseudo.lower().encode()).hexdigest(), 16) % 100
    return f"{propre[:12]}-{numero:02d}"


def joueur_par_code(code: str, chemin=None) -> str | None:
    """Retrouve le joueur à qui appartient ce code."""
    cherche = code.strip().lower()
    with db._connexion(chemin) as con:
        joueurs = [l["pseudo"] for l in con.execute("SELECT pseudo FROM joueurs").fetchall()]
    for j in joueurs:
        if code_ami(j) == cherche or j.lower() == cherche:
            return j
    return None


def ajouter_par_code(pseudo, code, chemin=None) -> str:
    """Ajoute un ami à partir de son code. Mêmes réponses que ajouter_ami, plus 'inconnu'."""
    trouve = joueur_par_code(code, chemin)
    if not trouve:
        return "inconnu"
    return ajouter_ami(pseudo, trouve, chemin)


def enregistrer_joueur(pseudo, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("INSERT OR IGNORE INTO joueurs (pseudo) VALUES (?)", (pseudo,))


def ajouter_ami(pseudo, ami, chemin=None) -> str:
    """Renvoie 'ok', 'soi', 'inconnu' ou 'deja'. L'amitié marche dans les deux sens."""
    ami = ami.strip()
    if not ami:
        return "inconnu"
    if ami.lower() == pseudo.lower():
        return "soi"
    with db._connexion(chemin) as con:
        ligne = con.execute("SELECT pseudo FROM joueurs WHERE LOWER(pseudo) = LOWER(?)", (ami,)).fetchone()
        if not ligne:
            return "inconnu"
        vrai_nom = ligne["pseudo"]
        if con.execute("SELECT 1 FROM amis WHERE LOWER(pseudo) = LOWER(?) AND LOWER(ami) = LOWER(?)", (pseudo, vrai_nom)).fetchone():
            return "deja"
        con.execute("INSERT OR IGNORE INTO amis (pseudo, ami) VALUES (?, ?)", (pseudo, vrai_nom))
        con.execute("INSERT OR IGNORE INTO amis (pseudo, ami) VALUES (?, ?)", (vrai_nom, pseudo))
    return "ok"


def retirer_ami(pseudo, ami, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("DELETE FROM amis WHERE (LOWER(pseudo) = LOWER(?) AND LOWER(ami) = LOWER(?)) "
                    "OR (LOWER(pseudo) = LOWER(?) AND LOWER(ami) = LOWER(?))",
                    (pseudo, ami, ami, pseudo))


def lister_amis(pseudo, chemin=None) -> list[str]:
    with db._connexion(chemin) as con:
        return [l["ami"] for l in con.execute("SELECT ami FROM amis WHERE LOWER(pseudo) = LOWER(?) ORDER BY ami", (pseudo,))]


def suggestions(pseudo, limite=5, chemin=None) -> list[str]:
    """Joueurs qui ne sont pas encore tes amis."""
    amis = {a.lower() for a in lister_amis(pseudo, chemin)} | {pseudo.lower()}
    with db._connexion(chemin) as con:
        tous = [l["pseudo"] for l in con.execute("SELECT pseudo FROM joueurs ORDER BY pseudo")]
    return [p for p in tous if p.lower() not in amis][:limite]


# ------------------------------------------------------------------ recettes
def reduire_image(octets: bytes, cote_max: int = 700) -> bytes | None:
    """Réduit la photo envoyée (JPEG) pour que la base reste légère. Renvoie None si ce n'est pas une image."""
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(octets)).convert("RGB")
        image.thumbnail((cote_max, cote_max))
        sortie = io.BytesIO()
        image.save(sortie, "JPEG", quality=82)
        return sortie.getvalue()
    except Exception:
        return None


def image_en_html(octets: bytes | None) -> str | None:
    """Adresse « data: » qu'on peut mettre dans une balise <img>."""
    if not octets:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(octets).decode()


def publier(auteur, titre, description, categorie, minutes, portions, ingredients, etapes, sante=None,
            image: bytes | None = None, chemin=None) -> int:
    ingredients = [{"quantite": str(i.get("quantite", "")).strip(), "nom": str(i.get("nom", "")).strip()}
                   for i in ingredients if str(i.get("nom", "")).strip()]
    etapes = [e.strip() for e in etapes if e.strip()]
    with db._connexion(chemin) as con:
        return con.inserer(
            "INSERT INTO recettes_communaute (auteur, titre, description, categorie, minutes, portions, ingredients, "
            "etapes, sante, image, jour) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (auteur, titre.strip(), description.strip(), categorie, int(minutes), int(portions),
             json.dumps(ingredients), json.dumps(etapes), json.dumps(sante or {}), image, date.today().isoformat()))


def _vers_dict(ligne) -> dict:
    r = dict(ligne)
    r["ingredients"] = json.loads(r["ingredients"])
    r["etapes"] = json.loads(r["etapes"])
    r["sante"] = json.loads(r["sante"])
    return r


def lister_recettes(categorie=None, chemin=None, pseudo=None, amis_seulement=False) -> list[dict]:
    """Les recettes de la communauté, avec le nombre de cœurs et ce que j'ai aimé."""
    conditions, params = [], []
    if categorie:
        conditions.append("categorie = ?")
        params.append(categorie)
    if amis_seulement and pseudo:
        amis = lister_amis(pseudo, chemin)
        if not amis:
            return []
        conditions.append("LOWER(auteur) IN (%s)" % ",".join(["LOWER(?)"] * len(amis)))
        params += amis
    filtre = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with db._connexion(chemin) as con:
        lignes = con.execute(f"SELECT * FROM recettes_communaute {filtre} ORDER BY id DESC", params).fetchall()
        coeurs = {r["recette_id"]: r["n"] for r in
                  con.execute("SELECT recette_id, COUNT(*) AS n FROM jaime GROUP BY recette_id").fetchall()}
        miens = {r["recette_id"] for r in
                 con.execute("SELECT recette_id FROM jaime WHERE LOWER(pseudo) = LOWER(?)", (pseudo or "",)).fetchall()}
    recettes = []
    for l in lignes:
        r = _vers_dict(l)
        r["coeurs"] = coeurs.get(r["id"], 0)
        r["aime"] = r["id"] in miens
        recettes.append(r)
    if recettes:
        vedette = max(recettes, key=lambda r: r["coeurs"])
        if vedette["coeurs"] >= 1:
            vedette["badge"] = "Top of the week"
    return recettes


def aimer(recette_id, pseudo, chemin=None) -> bool:
    """Met ou enlève un cœur. Renvoie True si la recette est maintenant aimée."""
    with db._connexion(chemin) as con:
        deja = con.execute("SELECT 1 FROM jaime WHERE recette_id = ? AND pseudo = ?",
                           (recette_id, pseudo)).fetchone()
        if deja:
            con.execute("DELETE FROM jaime WHERE recette_id = ? AND pseudo = ?", (recette_id, pseudo))
            return False
        con.execute("INSERT INTO jaime (recette_id, pseudo) VALUES (?,?)", (recette_id, pseudo))
    return True


def nb_coeurs(recette_id, chemin=None) -> int:
    with db._connexion(chemin) as con:
        return con.execute("SELECT COUNT(*) AS n FROM jaime WHERE recette_id = ?", (recette_id,)).fetchone()["n"]


def lire_recette(recette_id, chemin=None) -> dict | None:
    with db._connexion(chemin) as con:
        ligne = con.execute("SELECT * FROM recettes_communaute WHERE id = ?", (recette_id,)).fetchone()
    return _vers_dict(ligne) if ligne else None


def supprimer_recette(recette_id, auteur, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("DELETE FROM recettes_communaute WHERE id = ? AND LOWER(auteur) = LOWER(?)", (recette_id, auteur))


# ------------------------------------------------------------------ partage entre amis
def partager(de, a, recette_id, message="", chemin=None) -> bool:
    """Envoie une recette à un ami. Refusé si vous n'êtes pas amis."""
    if a.lower() not in {x.lower() for x in lister_amis(de, chemin)}:
        return False
    with db._connexion(chemin) as con:
        con.execute("INSERT INTO partages (de, a, recette_id, message, jour) VALUES (?,?,?,?,?)",
                    (de, a, recette_id, message.strip(), date.today().isoformat()))
    return True


def boite_reception(pseudo, chemin=None) -> list[dict]:
    with db._connexion(chemin) as con:
        lignes = con.execute(
            "SELECT p.id, p.de, p.message, p.jour, p.lu, p.recette_id, r.titre, r.categorie "
            "FROM partages p JOIN recettes_communaute r ON r.id = p.recette_id "
            "WHERE LOWER(p.a) = LOWER(?) ORDER BY p.id DESC", (pseudo,)).fetchall()
    return [dict(l) for l in lignes]


def nb_non_lus(pseudo, chemin=None) -> int:
    with db._connexion(chemin) as con:
        return con.execute("SELECT COUNT(*) AS n FROM partages WHERE LOWER(a) = LOWER(?) AND lu = 0", (pseudo,)).fetchone()["n"]


def marquer_lus(pseudo, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("UPDATE partages SET lu = 1 WHERE LOWER(a) = LOWER(?)", (pseudo,))


# ------------------------------------------------------------------ signalements et avis
def signaler(recette_id, par, motif, chemin=None) -> None:
    """Quelqu'un signale une recette : elle arrive dans la liste de l'administrateur."""
    with db._connexion(chemin) as con:
        con.execute("INSERT INTO signalements (recette_id, par, motif, jour) VALUES (?,?,?,?)",
                    (recette_id, par, motif.strip()[:300], date.today().isoformat()))


def lister_signalements(chemin=None) -> list[dict]:
    with db._connexion(chemin) as con:
        lignes = con.execute(
            "SELECT s.id, s.recette_id, s.par, s.motif, s.jour, r.titre, r.auteur "
            "FROM signalements s LEFT JOIN recettes_communaute r ON r.id = s.recette_id "
            "ORDER BY s.id DESC").fetchall()
    return [dict(l) for l in lignes]


def classer_signalement(signalement_id, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("DELETE FROM signalements WHERE id = ?", (signalement_id,))


def envoyer_avis(pseudo, texte, chemin=None) -> None:
    with db._connexion(chemin) as con:
        con.execute("INSERT INTO avis (pseudo, texte, jour) VALUES (?,?,?)",
                    (pseudo, texte.strip()[:1000], date.today().isoformat()))


def lister_avis(chemin=None) -> list[dict]:
    with db._connexion(chemin) as con:
        return [dict(l) for l in con.execute("SELECT * FROM avis ORDER BY id DESC").fetchall()]