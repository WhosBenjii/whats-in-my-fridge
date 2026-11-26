# What's in my Fridge

Application anti-gaspillage : tu scannes ton frigo, l'IA reconnaît les aliments, l'appli te propose
des recettes avec ce que tu as, et tu te mesures à tes amis.

Écrite en Python avec Streamlit. Fonctionne sur téléphone, et peut s'ajouter à l'écran d'accueil
comme une vraie appli.

---

## Lancer l'appli

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dans PyCharm : ouvre le **Terminal** en bas (pas le bouton Run vert, qui ne convient pas à
Streamlit), vérifie que la ligne commence par `(.venv)`, puis tape les deux commandes.

Au premier lancement, crée ton compte avec un e-mail et un mot de passe.

**Sans clé d'IA**, l'appli marche en mode démo : elle répond avec des exemples, sans rien envoyer
sur internet et sans rien coûter.

---

## Les écrans

| Écran | Ce qu'il fait |
|---|---|
| **Home** | Ton prénom, la grande carte verte, le bouton Scan, trois chiffres (aliments qui périment, idées de recettes, jours d'affilée), tes plats récents |
| **Fridge** | Ce qu'il te reste, rangé par urgence, avec les dates estimées. Deuxième onglet : la liste de courses |
| **Scan** (le bouton rond du milieu) | Photo → aliments trouvés avec leur durée de conservation → idées de plats → recette complète avec la nutrition |
| **Cook** | Les 33 recettes filtrées selon tes appareils, ton régime et tes allergies. Plus la semaine à planifier et les recettes gardées |
| **Community** | Le fil des recettes partagées (cœurs, envoi à un ami), tes amis avec leur code, et les deux concours |
| **Le rond en haut à droite** | Ton profil, ta semaine, les concours, ta cuisine (appareils, régime, allergies), tes réglages et ton compte |

---

## Les fichiers

| Fichier | À quoi il sert |
|---|---|
| `app.py` | Tous les écrans de l'appli |
| `style.css` | Le design : couleurs, boutons, animations |
| `core/base.py` | La base de données : fichier SQLite en local, PostgreSQL en ligne |
| `core/db.py` | Frigo, plats cuisinés, points, courses, semaine, favoris |
| `core/comptes.py` | Comptes, mots de passe, sessions, limite d'IA par personne |
| `core/reglages.py` | Le robinet de l'IA : budget total et coupure automatique |
| `core/ai.py` | Tout ce qui parle à l'IA (Claude) |
| `core/catalogue.py` | Les 33 recettes |
| `core/filtres.py` | Quelles recettes vont avec tes appareils, ton régime, tes allergies |
| `core/peremption.py` | Combien de temps se garde chaque aliment |
| `core/communaute.py` | Recettes partagées, amis, cœurs, signalements, avis |
| `core/illustrations.py` | Les dessins dans le style du logo, et la mascotte |
| `core/images.py` | Photos d'iPhone (HEIC) et réduction avant l'IA |
| `core/mobile.py` | L'icône et le plein écran sur le téléphone |
| `core/scoring.py` | Les règles de points et de niveaux |
| `telecharger_photos.py` | Télécharge une photo libre pour chaque recette |
| `tests/test_projet.py` | 15 tests automatiques |

---

## Les réglages

Tous facultatifs. En local, ce sont des variables d'environnement ; en ligne, ils vont dans les
« Secrets » de Streamlit Cloud. Le modèle est dans `.streamlit/secrets.toml.exemple`.

| Réglage | À quoi il sert |
|---|---|
| `ANTHROPIC_API_KEY` | La clé de l'IA. Sans elle : mode démo |
| `DATABASE_URL` | La base PostgreSQL en ligne. Sans elle : fichier local qui s'efface au redémarrage du serveur |
| `MAX_SCANS_TOTAL` | Budget : nombre total de scans pour toute l'appli (200 par défaut) |
| `ADMIN_EMAIL` | Le compte qui voit les signalements, les avis et le budget d'IA |
| `PIXABAY_API_KEY` | Pour télécharger les photos des recettes |
| `CLAUDE_MODEL` | Le modèle utilisé (`claude-haiku-5-5` par défaut, le moins cher) |

---

## Combien ça coûte

Avec Haiku, un scan revient à environ **0,04 centime**. Trois sécurités empêchent toute surprise :

1. 10 scans par personne et par jour (`SCANS_PAR_JOUR` dans `app.py`) ;
2. un budget total pour toute l'appli (`MAX_SCANS_TOTAL`) ;
3. une coupure automatique dès que l'IA répond « plus de crédit ».

Quand l'IA est coupée, tout le reste continue de marcher : frigo, recettes, courses, semaine,
mode cuisson, communauté, concours.

---

## Les tests

```bash
python -m pytest -q tests
```

---

## Mettre l'appli en ligne et sur ton téléphone

Tout est expliqué pas à pas dans **METTRE-EN-LIGNE.md**.
