"""Petite base de données locale (fichier SQLite) : amis, compétitions, profils."""
from __future__ import annotations

import json
from datetime import date, timedelta

from . import peremption, scoring
from .base import CHEMIN, connexion as _connexion  # noqa: F401  (utilisé par les autres fichiers)


def initialiser(chemin: str | None = None) -> None:
    with _connexion(chemin) as con:
        con.script(
            """
            CREATE TABLE IF NOT EXISTS plats_cuisines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                jour TEXT NOT NULL,
                nom_plat TEXT NOT NULL,
                niveau INTEGER NOT NULL,
                manche INTEGER NOT NULL,
                ingredients_sauves INTEGER NOT NULL,
                points INTEGER NOT NULL,
                temps_minutes INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS gaspillage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                jour TEXT NOT NULL,
                utilises INTEGER NOT NULL,
                jetes INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS frigo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                nom TEXT NOT NULL,
                quantite TEXT NOT NULL,
                expire TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS frigo_init (
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                PRIMARY KEY (groupe, pseudo)
            );
            CREATE TABLE IF NOT EXISTS profils (
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                ustensiles TEXT NOT NULL,
                regimes TEXT NOT NULL,
                PRIMARY KEY (groupe, pseudo)
            );
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                nom TEXT NOT NULL,
                pour TEXT NOT NULL DEFAULT '',
                coche INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS planning (
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                jour TEXT NOT NULL,
                nom_plat TEXT NOT NULL,
                categorie TEXT NOT NULL DEFAULT 'veg',
                PRIMARY KEY (groupe, pseudo, jour)
            );
            CREATE TABLE IF NOT EXISTS favoris (
                groupe TEXT NOT NULL,
                pseudo TEXT NOT NULL,
                nom_plat TEXT NOT NULL,
                PRIMARY KEY (groupe, pseudo, nom_plat)
            );
            """
        )
        # Mises à jour des bases créées par une ancienne version
        colonnes = con.colonnes("plats_cuisines")
        if "temps_minutes" not in colonnes:
            con.execute("ALTER TABLE plats_cuisines ADD COLUMN temps_minutes INTEGER NOT NULL DEFAULT 0")
        _colonnes_frigo(con)
        _colonne_allergies(con)


# ------------------------------------------------------------------ enregistrements
def enregistrer_plat(groupe, pseudo, nom_plat, niveau, ingredients_sauves, temps_minutes=0, *, chemin=None) -> int:
    manche = scoring.manche_du_niveau(niveau)
    points = scoring.points_plat(niveau, ingredients_sauves)
    aujourdhui = date.today().isoformat()
    with _connexion(chemin) as con:
        con.execute(
            "INSERT INTO plats_cuisines (groupe, pseudo, jour, nom_plat, niveau, manche, "
            "ingredients_sauves, points, temps_minutes) VALUES (?,?,?,?,?,?,?,?,?)",
            (groupe, pseudo, aujourdhui, nom_plat, niveau, manche, ingredients_sauves, points, temps_minutes),
        )
        # Cuisiner un plat compte aussi comme « aliments utilisés » pour le concours anti-gaspi.
        con.execute(
            "INSERT INTO gaspillage (groupe, pseudo, jour, utilises, jetes) VALUES (?,?,?,?,0)",
            (groupe, pseudo, aujourdhui, ingredients_sauves),
        )
    return points


def enregistrer_gaspillage(groupe, pseudo, utilises, jetes, chemin=None) -> None:
    with _connexion(chemin) as con:
        con.execute(
            "INSERT INTO gaspillage (groupe, pseudo, jour, utilises, jetes) VALUES (?,?,?,?,?)",
            (groupe, pseudo, date.today().isoformat(), utilises, jetes),
        )


# ------------------------------------------------------------------ lectures
def classement_tournoi(groupe, chemin=None) -> dict[int, list[dict]]:
    """Pour chaque manche : la liste des joueurs triés par points."""
    resultat = {m: [] for m in scoring.MANCHES}
    with _connexion(chemin) as con:
        lignes = con.execute(
            "SELECT manche, pseudo, SUM(points) AS points, COUNT(*) AS plats "
            "FROM plats_cuisines WHERE groupe = ? GROUP BY manche, pseudo "
            "ORDER BY manche, points DESC",
            (groupe,),
        ).fetchall()
    for ligne in lignes:
        resultat[ligne["manche"]].append(
            {"pseudo": ligne["pseudo"], "points": ligne["points"], "plats": ligne["plats"]}
        )
    return resultat


def classement_anti_gaspi(groupe, depuis: str | None = None, chemin=None) -> list[dict]:
    """Du joueur qui gaspille le moins à celui qui gaspille le plus.

    depuis : date (AAAA-MM-JJ) à partir de laquelle on compte, par exemple le lundi de la semaine.
    """
    filtre, params = "", [groupe]
    if depuis:
        filtre, params = " AND jour >= ?", [groupe, depuis]
    with _connexion(chemin) as con:
        gaspi = con.execute(
            "SELECT pseudo, SUM(utilises) AS utilises, SUM(jetes) AS jetes "
            f"FROM gaspillage WHERE groupe = ?{filtre} GROUP BY pseudo",
            params,
        ).fetchall()
        points = {
            l["pseudo"]: l["points"]
            for l in con.execute(
                f"SELECT pseudo, SUM(points) AS points FROM plats_cuisines WHERE groupe = ?{filtre} GROUP BY pseudo",
                params,
            )
        }
    joueurs = []
    for l in gaspi:
        if l["utilises"] + l["jetes"] == 0:
            continue
        joueurs.append(
            {
                "pseudo": l["pseudo"],
                "utilises": l["utilises"],
                "jetes": l["jetes"],
                "taux_gaspillage": scoring.taux_gaspillage(l["utilises"], l["jetes"]),
                "score": scoring.score_anti_gaspi(l["utilises"], l["jetes"]),
                "points": points.get(l["pseudo"], 0),
            }
        )
    return sorted(joueurs, key=lambda j: (-j["score"], -j["points"]))


def stats_joueur(groupe, pseudo, chemin=None) -> dict:
    """Chiffres de la page d'accueil et du profil (depuis le début)."""
    with _connexion(chemin) as con:
        plats = con.execute(
            "SELECT COUNT(*) AS repas, COALESCE(SUM(ingredients_sauves),0) AS sauves, "
            "COALESCE(SUM(points),0) AS points FROM plats_cuisines WHERE groupe = ? AND pseudo = ?",
            (groupe, pseudo),
        ).fetchone()
        gaspi = con.execute(
            "SELECT COALESCE(SUM(utilises),0) AS utilises, COALESCE(SUM(jetes),0) AS jetes "
            "FROM gaspillage WHERE groupe = ? AND pseudo = ?",
            (groupe, pseudo),
        ).fetchone()
    total = gaspi["utilises"] + gaspi["jetes"]
    return {
        "repas": plats["repas"],
        "sauves": plats["sauves"],
        "points": plats["points"],
        "score": scoring.score_anti_gaspi(gaspi["utilises"], gaspi["jetes"]) if total else None,
    }


def recettes_recentes(groupe, pseudo, limite=6, chemin=None) -> list[dict]:
    with _connexion(chemin) as con:
        lignes = con.execute(
            "SELECT nom_plat, temps_minutes, niveau FROM plats_cuisines "
            "WHERE groupe = ? AND pseudo = ? ORDER BY id DESC LIMIT ?",
            (groupe, pseudo, limite),
        ).fetchall()
    return [dict(l) for l in lignes]


# ------------------------------------------------------------------ profils
def _colonnes_frigo(con) -> None:
    """Ajoute « estime » et « note » aux bases créées avant cette version."""
    colonnes = con.colonnes("frigo")
    if "estime" not in colonnes:
        con.execute("ALTER TABLE frigo ADD COLUMN estime INTEGER NOT NULL DEFAULT 0")
    if "note" not in colonnes:
        con.execute("ALTER TABLE frigo ADD COLUMN note TEXT NOT NULL DEFAULT ''")


def _colonne_allergies(con) -> None:
    """Ajoute la colonne « allergies » aux bases créées avant cette version."""
    colonnes = con.colonnes("profils")
    if "allergies" not in colonnes:
        con.execute("ALTER TABLE profils ADD COLUMN allergies TEXT NOT NULL DEFAULT '[]'")


def sauver_profil(groupe, pseudo, ustensiles, regimes, allergies=None, chemin=None) -> None:
    with _connexion(chemin) as con:
        _colonne_allergies(con)
        con.execute(
            "INSERT INTO profils (groupe, pseudo, ustensiles, regimes, allergies) VALUES (?,?,?,?,?) "
            "ON CONFLICT(groupe, pseudo) DO UPDATE SET ustensiles = excluded.ustensiles, "
            "regimes = excluded.regimes, allergies = excluded.allergies",
            (groupe, pseudo, json.dumps(ustensiles), json.dumps(regimes), json.dumps(allergies or [])),
        )


def charger_profil(groupe, pseudo, chemin=None) -> dict | None:
    with _connexion(chemin) as con:
        _colonne_allergies(con)
        ligne = con.execute(
            "SELECT ustensiles, regimes, allergies FROM profils WHERE groupe = ? AND pseudo = ?", (groupe, pseudo)
        ).fetchone()
    if not ligne:
        return None
    return {"ustensiles": json.loads(ligne["ustensiles"]), "regimes": json.loads(ligne["regimes"]),
            "allergies": json.loads(ligne["allergies"] or "[]")}


# ------------------------------------------------------------------ frigo (stock + dates de péremption)
def _exemples_frigo() -> list[tuple[str, str, int]]:
    """Aliments d'exemple (nom, quantité, jours avant péremption) pour un frigo tout neuf."""
    return [
        ("Milk", "1 L", 0), ("Spinach", "200 g", 1), ("Chicken breast", "400 g", 1),
        ("Cooked rice", "200 g", 2), ("Salmon fillet", "2 pieces", 2), ("Tomatoes", "3", 3),
        ("Mushrooms", "250 g", 3), ("Yogurt", "4 pots", 6), ("Bell peppers", "2", 6),
        ("Eggs", "6", 11), ("Grated cheese", "100 g", 12), ("Carrots", "500 g", 14),
        ("Onions", "4", 18), ("Butter", "250 g", 27),
    ]


def corriger_date(article_id, expire, chemin=None) -> None:
    """L'utilisateur corrige une date : elle n'est plus « estimée »."""
    with _connexion(chemin) as con:
        con.execute("UPDATE frigo SET expire = ?, estime = 0 WHERE id = ?", (expire, article_id))


def preparer_frigo(groupe, pseudo, chemin=None) -> None:
    """Rien à faire : un nouveau venu commence avec un frigo vide, c'est le sien."""
    return None


def remplir_frigo_exemple(groupe, pseudo, chemin=None) -> int:
    """Remplit le frigo avec des aliments d'exemple, seulement si la personne le demande."""
    with _connexion(chemin) as con:
        deja = con.execute("SELECT 1 FROM frigo_init WHERE groupe = ? AND pseudo = ?", (groupe, pseudo)).fetchone()
        if deja:
            return 0
        con.execute("INSERT INTO frigo_init (groupe, pseudo) VALUES (?,?)", (groupe, pseudo))
        exemples = _exemples_frigo()
        for nom, quantite, jours in exemples:
            con.execute(
                "INSERT INTO frigo (groupe, pseudo, nom, quantite, expire, estime, note) "
                "VALUES (?,?,?,?,?,1,'example')",
                (groupe, pseudo, nom, quantite, (date.today() + timedelta(days=jours)).isoformat()),
            )
    return len(exemples)


def lister_frigo(groupe, pseudo, chemin=None) -> list[dict]:
    """Tous les aliments, du plus pressé (date la plus proche) au moins pressé."""
    with _connexion(chemin) as con:
        lignes = con.execute(
            "SELECT id, nom, quantite, expire, estime, note FROM frigo "
            "WHERE groupe = ? AND pseudo = ? ORDER BY expire, nom",
            (groupe, pseudo),
        ).fetchall()
    return [dict(l) for l in lignes]


def ajouter_aliment(groupe, pseudo, nom, quantite, expire, chemin=None, *, estime=False, note="") -> None:
    with _connexion(chemin) as con:
        con.execute(
            "INSERT INTO frigo (groupe, pseudo, nom, quantite, expire, estime, note) VALUES (?,?,?,?,?,?,?)",
            (groupe, pseudo, nom.strip(), quantite.strip() or "1", expire, 1 if estime else 0, note),
        )


def ajouter_depuis_scan(groupe, pseudo, aliments, chemin=None) -> int:
    """Ajoute les aliments vus par l'IA, chacun avec sa propre durée de conservation estimée."""
    existants = {a["nom"].lower() for a in lister_frigo(groupe, pseudo, chemin)}
    ajoutes = 0
    for a in aliments:
        nom = str(a.get("nom", "")).strip()
        if nom and nom.lower() not in existants:
            jours = peremption.jours_valides(a)
            ajouter_aliment(groupe, pseudo, nom, str(a.get("quantite", "")),
                            (date.today() + timedelta(days=jours)).isoformat(), chemin,
                            estime=True, note=str(a.get("note", ""))[:60])
            existants.add(nom.lower())
            ajoutes += 1
    return ajoutes


def supprimer_aliments(groupe, pseudo, ids, chemin=None) -> None:
    with _connexion(chemin) as con:
        for i in ids:
            con.execute("DELETE FROM frigo WHERE id = ? AND groupe = ? AND pseudo = ?", (i, groupe, pseudo))


def retirer_par_noms(groupe, pseudo, noms, chemin=None) -> int:
    """Quand on a cuisiné un plat, on enlève du frigo les aliments utilisés."""
    bas = {n.lower() for n in noms}
    ids = [a["id"] for a in lister_frigo(groupe, pseudo, chemin) if a["nom"].lower() in bas]
    supprimer_aliments(groupe, pseudo, ids, chemin)
    return len(ids)


def activite_semaine(groupe, pseudo, chemin=None) -> list[tuple[str, int]]:
    """Aliments utilisés pour cuisiner chaque jour des 7 derniers jours (du plus ancien au plus récent)."""
    jours = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    with _connexion(chemin) as con:
        lignes = con.execute(
            "SELECT jour, COALESCE(SUM(ingredients_sauves),0) AS n FROM plats_cuisines "
            "WHERE groupe = ? AND pseudo = ? AND jour >= ? GROUP BY jour",
            (groupe, pseudo, jours[0].isoformat())).fetchall()
    par_jour = {l["jour"]: l["n"] for l in lignes}
    return [(j.strftime("%a")[:1], par_jour.get(j.isoformat(), 0)) for j in jours]


# ------------------------------------------------------------------ liste de courses
def ajouter_course(groupe, pseudo, nom, pour="", chemin=None) -> bool:
    """Ajoute un article s'il n'y est pas déjà. Renvoie True si c'est nouveau."""
    nom = nom.strip()
    if not nom:
        return False
    with _connexion(chemin) as con:
        deja = con.execute("SELECT 1 FROM courses WHERE groupe=? AND pseudo=? AND LOWER(nom)=LOWER(?)",
                           (groupe, pseudo, nom)).fetchone()
        if deja:
            return False
        con.execute("INSERT INTO courses (groupe, pseudo, nom, pour) VALUES (?,?,?,?)", (groupe, pseudo, nom, pour))
    return True


def lister_courses(groupe, pseudo, chemin=None) -> list[dict]:
    with _connexion(chemin) as con:
        lignes = con.execute("SELECT id, nom, pour, coche FROM courses WHERE groupe=? AND pseudo=? "
                             "ORDER BY coche, id", (groupe, pseudo)).fetchall()
    return [dict(l) for l in lignes]


def cocher_course(article_id, valeur, chemin=None) -> None:
    with _connexion(chemin) as con:
        con.execute("UPDATE courses SET coche=? WHERE id=?", (1 if valeur else 0, article_id))


def supprimer_course(article_id, chemin=None) -> None:
    with _connexion(chemin) as con:
        con.execute("DELETE FROM courses WHERE id=?", (article_id,))


def courses_vers_frigo(groupe, pseudo, jours=7, chemin=None) -> int:
    """Met les articles cochés dans le frigo et les retire de la liste."""
    expire = (date.today() + timedelta(days=jours)).isoformat()
    with _connexion(chemin) as con:
        lignes = con.execute("SELECT id, nom FROM courses WHERE groupe=? AND pseudo=? AND coche=1",
                             (groupe, pseudo)).fetchall()
        for l in lignes:
            con.execute("INSERT INTO frigo (groupe, pseudo, nom, quantite, expire) VALUES (?,?,?,?,?)",
                        (groupe, pseudo, l["nom"], "1", expire))
            con.execute("DELETE FROM courses WHERE id=?", (l["id"],))
    return len(lignes)


# ------------------------------------------------------------------ planning de la semaine
def planifier(groupe, pseudo, jour, nom_plat, categorie="veg", chemin=None) -> None:
    with _connexion(chemin) as con:
        con.execute("INSERT INTO planning (groupe, pseudo, jour, nom_plat, categorie) VALUES (?,?,?,?,?) "
                    "ON CONFLICT(groupe, pseudo, jour) DO UPDATE SET nom_plat=excluded.nom_plat, "
                    "categorie=excluded.categorie", (groupe, pseudo, jour, nom_plat, categorie))


def deplanifier(groupe, pseudo, jour, chemin=None) -> None:
    with _connexion(chemin) as con:
        con.execute("DELETE FROM planning WHERE groupe=? AND pseudo=? AND jour=?", (groupe, pseudo, jour))


def lister_semaine(groupe, pseudo, chemin=None) -> dict:
    """{date ISO: {nom_plat, categorie}} pour les 7 prochains jours."""
    debut = date.today().isoformat()
    fin = (date.today() + timedelta(days=6)).isoformat()
    with _connexion(chemin) as con:
        lignes = con.execute("SELECT jour, nom_plat, categorie FROM planning WHERE groupe=? AND pseudo=? "
                             "AND jour BETWEEN ? AND ?", (groupe, pseudo, debut, fin)).fetchall()
    return {l["jour"]: {"nom_plat": l["nom_plat"], "categorie": l["categorie"]} for l in lignes}


# ------------------------------------------------------------------ recettes gardées
def basculer_favori(groupe, pseudo, nom_plat, chemin=None) -> bool:
    """Ajoute ou retire des favoris. Renvoie True si c'est maintenant un favori."""
    with _connexion(chemin) as con:
        deja = con.execute("SELECT 1 FROM favoris WHERE groupe=? AND pseudo=? AND nom_plat=?",
                           (groupe, pseudo, nom_plat)).fetchone()
        if deja:
            con.execute("DELETE FROM favoris WHERE groupe=? AND pseudo=? AND nom_plat=?", (groupe, pseudo, nom_plat))
            return False
        con.execute("INSERT INTO favoris (groupe, pseudo, nom_plat) VALUES (?,?,?)", (groupe, pseudo, nom_plat))
    return True


def lister_favoris(groupe, pseudo, chemin=None) -> list[str]:
    with _connexion(chemin) as con:
        lignes = con.execute("SELECT nom_plat FROM favoris WHERE groupe=? AND pseudo=?", (groupe, pseudo)).fetchall()
    return [l["nom_plat"] for l in lignes]