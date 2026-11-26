"""Comptes : inscription, connexion, rester connecté, suppression du compte.

Le mot de passe n'est jamais enregistré tel quel : on garde seulement une empreinte
(pbkdf2) impossible à relire à l'envers.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import date, datetime, timedelta

from .base import connexion

TOURS = 240_000          # nombre de tours de calcul : plus c'est long, plus c'est dur à casser
JOURS_SESSION = 30
EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


def email_admin() -> str:
    """L'adresse qui voit les signalements et les avis (réglage ADMIN_EMAIL)."""
    import os
    adresse = os.getenv("ADMIN_EMAIL", "")
    if not adresse:
        try:
            import streamlit as st
            adresse = str(st.secrets.get("ADMIN_EMAIL", ""))
        except Exception:
            adresse = ""
    return adresse.strip().lower()


def est_admin(compte: dict | None) -> bool:
    return bool(compte) and (compte.get("admin") or _propre(compte.get("email", "")) == email_admin())


def initialiser(chemin: str | None = None) -> None:
    with connexion(chemin) as con:
        con.script(
            """
            CREATE TABLE IF NOT EXISTS comptes (
                email TEXT PRIMARY KEY,
                pseudo TEXT NOT NULL,
                empreinte TEXT NOT NULL,
                sel TEXT NOT NULL,
                groupe TEXT NOT NULL DEFAULT 'friends',
                cree_le TEXT NOT NULL,
                admin INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                jeton TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                expire TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_ia (
                email TEXT NOT NULL,
                jour TEXT NOT NULL,
                nombre INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (email, jour)
            );
            """
        )
        if "vu_intro" not in con.colonnes("comptes"):
            con.execute("ALTER TABLE comptes ADD COLUMN vu_intro INTEGER NOT NULL DEFAULT 0")


# ------------------------------------------------------------------ mots de passe
def _empreinte(mdp: str, sel: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", mdp.encode(), bytes.fromhex(sel), TOURS).hex()


def _propre(email: str) -> str:
    return email.strip().lower()


def creer_compte(email: str, pseudo: str, mdp: str, chemin=None) -> tuple[str, str]:
    """Renvoie (résultat, message). Résultat : ok, email, pseudo, mdp, pris, pseudo_pris."""
    email, pseudo = _propre(email), pseudo.strip()
    if not EMAIL_OK.match(email):
        return "email", "This email address does not look right."
    if len(pseudo) < 2:
        return "pseudo", "Your name needs at least 2 letters."
    if len(mdp) < 8:
        return "mdp", "Your password needs at least 8 characters."

    sel = secrets.token_hex(16)
    with connexion(chemin) as con:
        if con.execute("SELECT 1 FROM comptes WHERE email = ?", (email,)).fetchone():
            return "pris", "An account already exists with this email. Log in instead."
        if con.execute("SELECT 1 FROM comptes WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)).fetchone():
            return "pseudo_pris", "This name is already taken. Pick another one."
        con.execute(
            "INSERT INTO comptes (email, pseudo, empreinte, sel, groupe, cree_le, admin) VALUES (?,?,?,?,?,?,0)",
            (email, pseudo, _empreinte(mdp, sel), sel, "friends", date.today().isoformat()))
    return "ok", "Account created."


def verifier(email: str, mdp: str, chemin=None) -> dict | None:
    """Renvoie le compte si le mot de passe est bon, sinon None."""
    email = _propre(email)
    with connexion(chemin) as con:
        ligne = con.execute("SELECT * FROM comptes WHERE email = ?", (email,)).fetchone()
    if not ligne:
        return None
    ligne = dict(ligne)
    attendu = _empreinte(mdp, ligne["sel"])
    if not hmac.compare_digest(attendu, ligne["empreinte"]):
        return None
    return ligne


def ouvrir_session(email: str, chemin=None) -> str:
    """Crée un jeton qui garde la personne connectée pendant 30 jours."""
    jeton = secrets.token_urlsafe(32)
    expire = (datetime.now() + timedelta(days=JOURS_SESSION)).isoformat(timespec="seconds")
    with connexion(chemin) as con:
        con.execute("INSERT INTO sessions (jeton, email, expire) VALUES (?,?,?)", (jeton, _propre(email), expire))
    return jeton


def compte_du_jeton(jeton: str, chemin=None) -> dict | None:
    if not jeton:
        return None
    with connexion(chemin) as con:
        ligne = con.execute(
            "SELECT c.* FROM sessions s JOIN comptes c ON c.email = s.email "
            "WHERE s.jeton = ? AND s.expire > ?", (jeton, datetime.now().isoformat(timespec="seconds"))).fetchone()
    return dict(ligne) if ligne else None


def fermer_session(jeton: str, chemin=None) -> None:
    with connexion(chemin) as con:
        con.execute("DELETE FROM sessions WHERE jeton = ?", (jeton,))


def changer_pseudo(email: str, pseudo: str, chemin=None) -> tuple[str, str]:
    pseudo = pseudo.strip()
    if len(pseudo) < 2:
        return "pseudo", "Your name needs at least 2 letters."
    with connexion(chemin) as con:
        pris = con.execute("SELECT email FROM comptes WHERE LOWER(pseudo) = LOWER(?)", (pseudo,)).fetchone()
        if pris and _propre(pris["email"]) != _propre(email):
            return "pseudo_pris", "This name is already taken."
        con.execute("UPDATE comptes SET pseudo = ? WHERE email = ?", (pseudo, _propre(email)))
    return "ok", "Name changed."


def changer_mdp(email: str, ancien: str, nouveau: str, chemin=None) -> tuple[str, str]:
    if not verifier(email, ancien, chemin):
        return "ancien", "Your current password is not right."
    if len(nouveau) < 8:
        return "mdp", "The new password needs at least 8 characters."
    sel = secrets.token_hex(16)
    with connexion(chemin) as con:
        con.execute("UPDATE comptes SET empreinte = ?, sel = ? WHERE email = ?",
                    (_empreinte(nouveau, sel), sel, _propre(email)))
    return "ok", "Password changed."


def supprimer_compte(email: str, pseudo: str, groupe: str, chemin=None) -> None:
    """Efface le compte et TOUT ce qui va avec (demande de la loi européenne)."""
    email = _propre(email)
    with connexion(chemin) as con:
        presentes = set(con.tables())

        def effacer(table, sql, params):
            if table in presentes:
                con.execute(sql, params)

        for table in ("frigo", "frigo_init", "plats_cuisines", "gaspillage", "profils", "courses",
                      "planning", "favoris"):
            effacer(table, f"DELETE FROM {table} WHERE groupe = ? AND pseudo = ?", (groupe, pseudo))
        effacer("amis", "DELETE FROM amis WHERE LOWER(pseudo) = LOWER(?) OR LOWER(ami) = LOWER(?)",
                (pseudo, pseudo))
        effacer("partages", "DELETE FROM partages WHERE LOWER(de) = LOWER(?) OR LOWER(a) = LOWER(?)",
                (pseudo, pseudo))
        effacer("jaime", "DELETE FROM jaime WHERE LOWER(pseudo) = LOWER(?)", (pseudo,))
        effacer("signalements", "DELETE FROM signalements WHERE LOWER(par) = LOWER(?)", (pseudo,))
        effacer("avis", "DELETE FROM avis WHERE LOWER(pseudo) = LOWER(?)", (pseudo,))
        effacer("recettes_communaute", "DELETE FROM recettes_communaute WHERE LOWER(auteur) = LOWER(?)",
                (pseudo,))
        effacer("joueurs", "DELETE FROM joueurs WHERE LOWER(pseudo) = LOWER(?)", (pseudo,))
        con.execute("DELETE FROM sessions WHERE email = ?", (email,))
        con.execute("DELETE FROM usage_ia WHERE email = ?", (email,))
        con.execute("DELETE FROM comptes WHERE email = ?", (email,))


# ------------------------------------------------------------------ limite d'utilisation de l'IA
def scans_du_jour(email: str, chemin=None) -> int:
    with connexion(chemin) as con:
        ligne = con.execute("SELECT nombre FROM usage_ia WHERE email = ? AND jour = ?",
                            (_propre(email), date.today().isoformat())).fetchone()
    return ligne["nombre"] if ligne else 0


def compter_scan(email: str, chemin=None) -> int:
    """Ajoute un scan au compteur du jour et renvoie le total."""
    email, jour = _propre(email), date.today().isoformat()
    with connexion(chemin) as con:
        con.execute("INSERT INTO usage_ia (email, jour, nombre) VALUES (?,?,1) "
                    "ON CONFLICT(email, jour) DO UPDATE SET nombre = usage_ia.nombre + 1", (email, jour))
        ligne = con.execute("SELECT nombre FROM usage_ia WHERE email = ? AND jour = ?", (email, jour)).fetchone()
    return ligne["nombre"] if ligne else 1


def marquer_intro_vue(email: str, chemin=None) -> None:
    with connexion(chemin) as con:
        con.execute("UPDATE comptes SET vu_intro = 1 WHERE email = ?", (_propre(email),))
