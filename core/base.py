"""Où sont rangées les données.

Deux possibilités, le même code pour les deux :
- en local, un simple fichier (SQLite) dans le dossier data/ ;
- en ligne, une vraie base PostgreSQL (Supabase, Neon…), si la variable DATABASE_URL existe.

En ligne, les données ne s'effacent plus quand le serveur redémarre.
Les requêtes s'écrivent toujours à la mode SQLite (avec des « ? ») : on les traduit ici.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager

CHEMIN = os.getenv("FRIDGE_DB", os.path.join("data", "fridge.db"))


def adresse_postgres() -> str:
    """L'adresse de la base en ligne, si elle est configurée."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        try:
            import streamlit as st
            url = str(st.secrets.get("DATABASE_URL", ""))
        except Exception:
            url = ""
    return url


def en_ligne() -> bool:
    return bool(adresse_postgres())


# ------------------------------------------------------------------ traduction SQLite -> PostgreSQL
def _traduire(sql: str) -> str:
    ignorer = "INSERT OR IGNORE" in sql
    sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace(" COLLATE NOCASE", "")
    sql = re.sub(r"\bBLOB\b", "BYTEA", sql)
    sql = sql.replace("?", "%s")
    if ignorer and "ON CONFLICT" not in sql:
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return sql


class _Connexion:
    """Même façon de parler à la base, qu'elle soit en fichier ou en ligne."""

    def __init__(self, con, postgres: bool):
        self.con = con
        self.postgres = postgres

    def execute(self, sql: str, params=()):
        if not self.postgres:
            return self.con.execute(sql, params)
        cur = self.con.cursor()
        cur.execute(_traduire(sql), tuple(params))
        return cur

    def inserer(self, sql: str, params=()) -> int:
        """Ajoute une ligne et renvoie son numéro."""
        if not self.postgres:
            return self.con.execute(sql, params).lastrowid
        cur = self.con.cursor()
        cur.execute(_traduire(sql) + " RETURNING id", tuple(params))
        return cur.fetchone()["id"]

    def script(self, sql: str) -> None:
        """Crée plusieurs tables d'un coup."""
        if not self.postgres:
            self.con.executescript(sql)
            return
        self.con.cursor().execute(_traduire(sql))

    def tables(self) -> list[str]:
        """Les tables qui existent déjà (pour ne pas écrire dans une table absente)."""
        if not self.postgres:
            return [l["name"] for l in
                    self.con.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()]
        cur = self.con.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        return [l["table_name"] for l in cur.fetchall()]

    def colonnes(self, table: str) -> list[str]:
        """Les colonnes d'une table (pour les mises à jour de l'ancienne base)."""
        if not self.postgres:
            return [c["name"] for c in self.con.execute(f"PRAGMA table_info({table})").fetchall()]
        cur = self.con.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))
        return [l["column_name"] for l in cur.fetchall()]


@contextmanager
def connexion(chemin: str | None = None):
    """À utiliser partout : `with connexion() as con: con.execute(...)`.

    Si un chemin de fichier est donné (les tests), on reste sur SQLite.
    """
    url = "" if chemin else adresse_postgres()
    if url:
        import psycopg
        from psycopg.rows import dict_row

        con = psycopg.connect(url, row_factory=dict_row)
        try:
            yield _Connexion(con, True)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return

    chemin = chemin or CHEMIN
    dossier = os.path.dirname(chemin)
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    con = sqlite3.connect(chemin)
    con.row_factory = sqlite3.Row
    try:
        yield _Connexion(con, False)
        con.commit()
    finally:
        con.close()
