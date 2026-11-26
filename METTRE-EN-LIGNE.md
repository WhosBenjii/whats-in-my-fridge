# Mettre l'appli sur ton téléphone

Deux étapes : d'abord l'appli va en ligne (gratuit), ensuite tu l'ajoutes à ton écran d'accueil.
Compte 15 minutes la première fois.

---

## Étape 1 — Essai rapide sur le Wi-Fi de chez toi (facultatif)

Lance l'appli sur ton Mac :

```
streamlit run app.py
```

Le terminal affiche deux adresses. Prends la deuxième, la **Network URL**
(du genre `http://192.168.2.4:8501`) et tape-la dans Safari sur ton téléphone.

Ça ne marche que chez toi, avec le Mac allumé. Pour avoir l'appli partout, passe à l'étape 2.

---

## Étape 2 — Mettre l'appli en ligne (gratuit)

### 2.1 Créer un compte GitHub

Va sur **github.com** et crée un compte gratuit, si tu n'en as pas déjà un.

### 2.2 Envoyer le code sur GitHub

Dans le Terminal, dans le dossier du projet :

```
git init
git add .
git commit -m "Premiere version de l'appli"
```

Sur github.com, clique sur **New repository**, appelle-le `whats-in-my-fridge`,
laisse-le en **Private** si tu veux, et clique **Create repository**.
GitHub affiche alors deux lignes à copier, du genre :

```
git remote add origin https://github.com/TON-NOM/whats-in-my-fridge.git
git branch -M main
git push -u origin main
```

Colle-les dans le Terminal. Ton code est en ligne.

Le fichier `.gitignore` empêche d'envoyer ta base de données, tes clés et ton dossier `.venv`.
Tes clés d'IA ne partent donc jamais sur GitHub.

### 2.3 Créer la base de données en ligne (pour que rien ne s'efface)

1. Va sur **supabase.com**, crée un compte gratuit, puis **New project**.
2. Choisis un mot de passe de base de données et garde-le.
3. Une fois le projet prêt : **Connect** en haut, puis l'onglet **Connection string**,
   section **Transaction pooler**. Copie l'adresse, qui ressemble à :

```
postgresql://postgres.abcdefgh:TON-MOT-DE-PASSE@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

Remplace `TON-MOT-DE-PASSE` par celui de l'étape 2. Tu colleras cette adresse à l'étape suivante,
dans les Secrets, sous le nom `DATABASE_URL`.

Sans cette adresse, l'appli marche quand même : elle utilise un fichier local, mais les données
repartent à zéro à chaque redémarrage du serveur.

### 2.4 Lancer l'appli sur Streamlit Cloud

1. Va sur **share.streamlit.io** et connecte-toi avec ton compte GitHub.
2. Clique **Create app**, puis **Deploy a public app from GitHub**.
3. Choisis ton dépôt `whats-in-my-fridge`, branche `main`, fichier `app.py`.
4. Avant de cliquer **Deploy**, ouvre **Advanced settings** → **Secrets** et colle :

```
ANTHROPIC_API_KEY = "sk-ant-ta-cle-ici"
MAX_SCANS_TOTAL = "200"
DATABASE_URL = "postgresql://postgres.abcdefgh:TON-MOT-DE-PASSE@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
ADMIN_EMAIL = "ton.email@exemple.com"
```

`ADMIN_EMAIL` est l'adresse de ton compte dans l'appli : c'est elle qui verra les signalements
et les avis des utilisateurs, dans la page Profile.

5. Clique **Deploy** et attends deux minutes.

Tu obtiens une adresse du genre `https://whats-in-my-fridge.streamlit.app`.
Elle marche sur n'importe quel téléphone, partout, et tes amis peuvent l'ouvrir.

Sans clé d'IA, l'appli fonctionne quand même : elle passe en mode démo avec des exemples.

---

## Étape 3 — L'icône sur l'écran d'accueil

### Sur iPhone
1. Ouvre l'adresse dans **Safari** (pas Chrome).
2. Bouton **Partager** (le carré avec la flèche).
3. **Sur l'écran d'accueil**, puis **Ajouter**.

### Sur Android
1. Ouvre l'adresse dans **Chrome**.
2. Menu (les trois points) → **Installer l'application**.

Tu as maintenant l'icône du frigo sur ton écran. L'appli s'ouvre en plein écran,
sans la barre du navigateur. Personne ne voit la différence avec une appli de l'App Store.

---

## Ce qu'il faut savoir

**Les données.** Avec `DATABASE_URL` réglé (étape 2.3), tout est gardé : frigo, comptes, amis,
points, recettes. Sans cette adresse, l'appli repart à zéro à chaque redémarrage du serveur.

**L'appli se met en veille** après quelques jours sans visite. La première ouverture prend
alors une trentaine de secondes, le temps qu'elle se réveille.

**Chacun son compte.** Les gens créent un compte avec leur e-mail et un mot de passe. Chacun ne
voit que son frigo. Ils peuvent supprimer leur compte et toutes leurs données depuis la page Profile.

**Ta facture d'IA est protégée, trois fois.**
1. 10 scans par personne et par jour (`SCANS_PAR_JOUR` dans `app.py`).
2. Un budget total pour toute l'appli : `MAX_SCANS_TOTAL` dans les Secrets. À 200 scans avec le
   modèle Haiku, ça représente environ 8 centimes. Quand le total est atteint, le bouton « Analyze
   with AI » se désactive tout seul pour tout le monde.
3. Si l'IA répond « plus de crédit », l'appli coupe l'IA d'elle-même et affiche un message clair.
   Rien ne plante : on ajoute ses aliments à la main, et tout le reste continue de marcher.

Tu peux voir où ça en est, et rallumer l'IA, dans Profile → **Admin: AI budget** (visible seulement
par le compte indiqué dans `ADMIN_EMAIL`).

Mets quand même un plafond de dépense sur ton compte Anthropic :
**platform.claude.com/settings/spend-limits**.

**Pour mettre à jour l'appli** : tu modifies le code chez toi, puis :

```
git add .
git commit -m "Ce que j'ai changé"
git push
```

Streamlit Cloud remet l'appli à jour tout seul, en une minute.
