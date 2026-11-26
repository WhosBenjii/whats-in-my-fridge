import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.pop("ANTHROPIC_API_KEY", None)

from core import ai, catalogue, comptes, db, filtres, reglages, scoring  # noqa: E402


def test_manches():
    assert scoring.manche_du_niveau(2) == 1
    assert scoring.manche_du_niveau(5) == 2
    assert scoring.manche_du_niveau(9) == 3


def test_points_et_gaspillage():
    assert scoring.points_plat(5, 3) == 56
    assert scoring.taux_gaspillage(8, 2) == 20.0
    assert scoring.taux_gaspillage(0, 0) == 0.0


def test_extraction_json():
    assert ai._extraire_json('Voici : [{"a": 1}] fin') == [{"a": 1}]
    assert ai._extraire_json('{"a": {"b": 2}}') == {"a": {"b": 2}}


def test_flux_demo_complet():
    aliments = ai.detecter_ingredients([])
    noms = [a["nom"] for a in aliments]
    plats = ai.proposer_plats(noms, ["Poêle"])
    assert plats and all(1 <= p["niveau_elaboration"] <= 10 for p in plats)
    recette = ai.creer_recette(plats[0], noms, ["Poêle"], 2)
    assert recette["sante"]["calories"] > 0 and recette["etapes"]


def test_competitions(tmp_path):
    chemin = str(tmp_path / "t.db")
    db.initialiser(chemin)
    db.enregistrer_plat("g", "Ana", "Omelette", 2, 3, 15, chemin=chemin)
    db.enregistrer_plat("g", "Ben", "Stuffed peppers", 8, 4, 70, chemin=chemin)
    db.enregistrer_gaspillage("g", "Ana", 5, 5, chemin)
    tournoi = db.classement_tournoi("g", chemin)
    assert tournoi[1][0]["pseudo"] == "Ana" and tournoi[3][0]["pseudo"] == "Ben"
    anti = db.classement_anti_gaspi("g", chemin=chemin)
    assert anti[0]["pseudo"] == "Ben"  # 0 % jeté contre 25 % pour Ana


def test_stats_profil_et_niveau(tmp_path):
    chemin = str(tmp_path / "t2.db")
    db.initialiser(chemin)
    db.enregistrer_plat("g", "Ana", "Omelette", 2, 3, 15, chemin=chemin)
    db.enregistrer_gaspillage("g", "Ana", 0, 1, chemin)
    stats = db.stats_joueur("g", "Ana", chemin)
    assert stats["repas"] == 1 and stats["sauves"] == 3 and stats["score"] == 75.0
    assert db.recettes_recentes("g", "Ana", chemin=chemin)[0]["temps_minutes"] == 15
    assert db.stats_joueur("g", "Inconnu", chemin)["score"] is None
    db.sauver_profil("g", "Ana", ["Oven"], ["Vegan"], ["Milk"], chemin=chemin)
    assert db.charger_profil("g", "Ana", chemin) == {"ustensiles": ["Oven"], "regimes": ["Vegan"], "allergies": ["Milk"]}
    assert db.charger_profil("g", "Zoe", chemin) is None
    assert scoring.niveau_joueur(300) == (2, 20)
    assert scoring.titre_selon_score(92) == "Zero-Waste Chef"
    assert scoring.kg_evites(5) == 1.0


def test_semaine():
    from datetime import date
    assert scoring.debut_de_semaine(date(2026, 11, 13)) == "2026-11-09"
    assert scoring.jours_restants_semaine(date(2026, 11, 13)) == 2


def test_frigo_et_catalogue(tmp_path):
    from core import catalogue
    chemin = str(tmp_path / "t.db")
    db.initialiser(chemin)
    db.preparer_frigo("g", "p", chemin)
    db.preparer_frigo("g", "p", chemin)  # deuxième appel : rien ne change
    aliments = db.lister_frigo("g", "p", chemin)
    assert len(aliments) == 14 and aliments[0]["nom"] == "Milk"
    db.ajouter_aliment("g", "p", "Pears", "3", "2030-01-01", chemin)
    assert db.retirer_par_noms("g", "p", ["milk", "pears"], chemin) == 2
    assert len(catalogue.RECETTES) == 33


def test_communaute_amis_et_partage(tmp_path):
    from core import communaute
    chemin = str(tmp_path / "c.db")
    db.initialiser(chemin)
    communaute.initialiser(chemin)
    communaute.enregistrer_joueur("Ben", chemin)
    assert communaute.ajouter_ami("Ben", "emma", chemin) == "ok"
    assert communaute.ajouter_ami("Ben", "nobody", chemin) == "inconnu"
    assert not communaute.partager("Ben", "Lucas", 1, "", chemin)          # pas amis : refusé
    assert communaute.partager("Ben", "Emma", 1, "try it", chemin)
    assert communaute.nb_non_lus("Emma", chemin) == 1
    communaute.marquer_lus("Emma", chemin)
    assert communaute.nb_non_lus("Emma", chemin) == 0
    nouvel = communaute.publier("Ben", "Soup", "d", "veg", 10, 2, [{"quantite": "1", "nom": "x"}], ["a"], None, None, chemin)
    assert communaute.lire_recette(nouvel, chemin)["titre"] == "Soup"


def test_filtres_selon_appareils_regime_et_allergies():
    """Les recettes proposées changent selon ce que l'utilisateur coche."""
    toutes = catalogue.RECETTES
    assert filtres.compter(toutes, ["Oven", "Pan", "Saucepan"], [], []) == len(toutes)
    # un végétarien ne voit plus la viande ni le poisson
    veg = filtres.compter(toutes, ["Oven", "Pan", "Saucepan"], ["Vegetarian"], [])
    assert 0 < veg < len(toutes)
    poulet = next(r for r in toutes if "chicken" in r["nom"].lower())
    assert filtres.verifier(poulet, ["Oven", "Pan", "Saucepan"], ["Vegetarian"], []) == (False, "Vegetarian")
    # sans four, les plats qui en ont besoin disparaissent avec la raison
    gratin = next(r for r in toutes if "gratin" in r["nom"].lower())
    ok, raison = filtres.verifier(gratin, ["Pan"], [], [])
    assert not ok and raison == "No oven"
    # allergie au poisson
    saumon = next(r for r in toutes if "salmon" in r["nom"].lower())
    assert filtres.verifier(saumon, ["Oven"], [], ["Fish"]) == (False, "Contains fish")


def test_liste_de_courses_et_semaine(tmp_path):
    chemin = str(tmp_path / "t4.db")
    db.initialiser(chemin)
    assert db.ajouter_course("g", "Ana", "Lemon", "for salmon", chemin) is True
    assert db.ajouter_course("g", "Ana", "lemon", chemin=chemin) is False  # pas de doublon
    article = db.lister_courses("g", "Ana", chemin)[0]
    db.cocher_course(article["id"], True, chemin)
    assert db.courses_vers_frigo("g", "Ana", chemin=chemin) == 1
    assert any(a["nom"] == "Lemon" for a in db.lister_frigo("g", "Ana", chemin))

    db.planifier("g", "Ana", "2026-11-17", "Ratatouille", "veg", chemin)
    assert db.lister_semaine("g", "Ana", chemin) in ({}, {"2026-11-17": {"nom_plat": "Ratatouille", "categorie": "veg"}})
    assert db.basculer_favori("g", "Ana", "Ratatouille", chemin) is True
    assert db.lister_favoris("g", "Ana", chemin) == ["Ratatouille"]
    assert db.basculer_favori("g", "Ana", "Ratatouille", chemin) is False


def test_dates_estimees_pendant_le_scan(tmp_path):
    """Chaque aliment reçoit sa propre durée de conservation, marquée « estimée »."""
    from core import peremption
    assert peremption.jours_estimes("Raw salmon fillet") == 2
    assert peremption.jours_estimes("Carrots") == 25
    assert peremption.jours_valides({"nom": "Milk", "jours": 4}) == 4
    assert peremption.jours_valides({"nom": "Milk", "jours": "pas un nombre"}) == 5

    chemin = str(tmp_path / "t5.db")
    db.initialiser(chemin)
    db.ajouter_depuis_scan("g", "Ana", [{"nom": "Leftover curry", "jours": 2, "note": "cooked"},
                                        {"nom": "Onions"}], chemin=chemin)
    frigo = {a["nom"]: a for a in db.lister_frigo("g", "Ana", chemin)}
    assert frigo["Leftover curry"]["estime"] == 1 and frigo["Leftover curry"]["note"] == "cooked"
    assert frigo["Leftover curry"]["expire"] < frigo["Onions"]["expire"]  # le reste part en premier
    db.corriger_date(frigo["Leftover curry"]["id"], "2030-01-01", chemin)
    corrige = next(a for a in db.lister_frigo("g", "Ana", chemin) if a["nom"] == "Leftover curry")
    assert corrige["estime"] == 0 and corrige["expire"] == "2030-01-01"


def test_comptes_et_limite_ia(tmp_path):
    """Inscription, connexion, session, limite de scans et suppression complète."""
    chemin = str(tmp_path / "t6.db")
    db.initialiser(chemin)
    comptes.initialiser(chemin)

    assert comptes.creer_compte("Ana@Test.com", "Ana", "motdepasse1", chemin)[0] == "ok"
    assert comptes.creer_compte("ana@test.com", "Autre", "motdepasse1", chemin)[0] == "pris"
    assert comptes.creer_compte("autre@test.com", "ana", "motdepasse1", chemin)[0] == "pseudo_pris"
    assert comptes.creer_compte("pas-un-email", "Zoe", "motdepasse1", chemin)[0] == "email"
    assert comptes.creer_compte("zoe@test.com", "Zoe", "court", chemin)[0] == "mdp"

    assert comptes.verifier("ana@test.com", "mauvais", chemin) is None
    compte = comptes.verifier("ANA@test.com", "motdepasse1", chemin)
    assert compte and compte["pseudo"] == "Ana"

    jeton = comptes.ouvrir_session("ana@test.com", chemin)
    assert comptes.compte_du_jeton(jeton, chemin)["pseudo"] == "Ana"
    assert comptes.compte_du_jeton("faux-jeton", chemin) is None
    comptes.fermer_session(jeton, chemin)
    assert comptes.compte_du_jeton(jeton, chemin) is None

    assert comptes.scans_du_jour("ana@test.com", chemin) == 0
    assert comptes.compter_scan("ana@test.com", chemin) == 1
    assert comptes.compter_scan("ana@test.com", chemin) == 2

    db.preparer_frigo("friends", "Ana", chemin)
    comptes.supprimer_compte("ana@test.com", "Ana", "friends", chemin)
    assert comptes.verifier("ana@test.com", "motdepasse1", chemin) is None
    assert db.lister_frigo("friends", "Ana", chemin) == []


def test_photos_preparees():
    """Les photos sont réduites et converties en JPEG avant d'aller à l'IA."""
    import io
    from PIL import Image
    from core import images
    grande = io.BytesIO()
    Image.new("RGB", (2400, 1800), (120, 180, 90)).save(grande, "PNG")
    octets, mime = images.preparer(grande.getvalue(), "image/png", "frigo.png")
    assert mime == "image/jpeg" and len(octets) < len(grande.getvalue())
    assert max(Image.open(io.BytesIO(octets)).size) <= images.COTE_MAX
    assert images.preparer(b"ceci n'est pas une image", "image/png", "x.png") is None
    assert "heic" in [f.lower() for f in images.FORMATS]


def test_robinet_de_l_ia(tmp_path, monkeypatch):
    """L'IA se coupe toute seule quand le budget gratuit est fini."""
    chemin = str(tmp_path / "t7.db")
    db.initialiser(chemin)
    comptes.initialiser(chemin)
    reglages.initialiser(chemin)

    monkeypatch.setenv("MAX_SCANS_TOTAL", "3")
    assert reglages.etat_ia(chemin)[0] is True
    for _ in range(3):
        comptes.compter_scan("ana@test.com", chemin)
    ok, raison, faits, maxi = reglages.etat_ia(chemin)
    assert not ok and faits == 3 and maxi == 3 and "budget" in raison

    monkeypatch.setenv("MAX_SCANS_TOTAL", "500")
    assert reglages.etat_ia(chemin)[0] is True
    reglages.bloquer_ia("Your credit balance is too low", chemin)
    assert reglages.etat_ia(chemin)[0] is False
    reglages.debloquer_ia(chemin)
    assert reglages.etat_ia(chemin)[0] is True

    # on reconnaît bien les erreurs « plus de crédit »
    assert ai.manque_de_credit(Exception("Your credit balance is too low to access the Anthropic API"))
    assert ai.manque_de_credit(Exception("429 rate_limit_error"))
    assert not ai.manque_de_credit(Exception("connection reset by peer"))

    # l'interrupteur général coupe tous les appels
    ai.forcer_demo(True)
    assert ai.mode_demo() is True
    ai.forcer_demo(False)
    assert ai.MODELE == "claude-haiku-5-5"
