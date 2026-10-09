import json
import os
import random

import pytest

from core.analyseur import Analyseur
from core.simulateur import Simulateur
from models.reseau import ReseauRoutier
from models.route import Route
from models.vehicule import Vehicule
from out import export

CONFIG = os.path.join(os.path.dirname(__file__), "..", "data", "config_reseau.json")


# --- Vehicule -------------------------------------------------------------
def test_vehicule_avance_a_la_bonne_distance():
    v = Vehicule("V1", vitesse=60.0)
    reel = v.avancer(60)              # 60 km/h pendant 1 min = 1 km
    assert reel == pytest.approx(1.0)
    assert v.position == pytest.approx(1.0)


def test_vehicule_borne_par_position_max():
    v = Vehicule("V1", vitesse=100.0)
    v.avancer(60, position_max=0.5)
    assert v.position == pytest.approx(0.5)


def test_changer_de_route_remet_la_position():
    r = Route("R", "R", 1.0, 50, "A", "B")
    v = Vehicule("V1", position=0.9)
    v.changer_de_route(r, 0.1)
    assert v.route is r and v.position == pytest.approx(0.1)


# --- Route ----------------------------------------------------------------
def test_ajout_vehicule_et_refus_si_entree_occupee():
    r = Route("R", "R", 2.0, 50, "A", "B")
    assert r.ajouter_vehicule(Vehicule("V1"))
    assert not r.ajouter_vehicule(Vehicule("V2"))   # trop proche de V1 à l'entrée
    assert r.nb_vehicules == 1


def test_pas_de_depassement():
    r = Route("R", "R", 50.0, 50, "A", "B", bruit_vitesse=0.0)
    devant, derriere = Vehicule("devant"), Vehicule("derriere")
    r.ajouter_vehicule(devant, position=1.0)
    r.ajouter_vehicule(derriere, position=0.5)
    for _ in range(10):
        r.mettre_a_jour_vehicules(60, random.Random(0))
        assert derriere.position < devant.position
    assert devant.position <= r.longueur


def test_vitesse_diminue_avec_la_densite():
    libre = Route("L", "L", 1.0, 50, "A", "B", densite_max=20)
    dense = Route("D", "D", 1.0, 50, "A", "B", densite_max=20)
    for i in range(10):
        dense.ajouter_vehicule(Vehicule(f"V{i}"), position=0.09 * i + 0.05)
    assert dense.vitesse_cible() < libre.vitesse_cible()


def test_vehicule_arrive_en_bout_de_route():
    r = Route("R", "R", 0.5, 60, "A", "B", bruit_vitesse=0.0)
    v = Vehicule("V1")
    r.ajouter_vehicule(v)
    arrives = r.mettre_a_jour_vehicules(60)     # 1 km parcourable > 0.5 km
    assert arrives == [v]
    assert v.reste == pytest.approx(v.vitesse * 60 / 3600 - 0.5)   # distance au-delà de la fin
    assert v.reste > 0


# --- Reseau ---------------------------------------------------------------
def test_chargement_config_et_routes_bidirectionnelles():
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    reseau = ReseauRoutier.depuis_dict(cfg)
    assert len(reseau.intersections) == 6
    assert len(reseau.routes) == 14
    assert "AB" in reseau.routes and "AB_R" in reseau.routes


def test_chemin_plus_court():
    with open(CONFIG, encoding="utf-8") as f:
        reseau = ReseauRoutier.depuis_dict(json.load(f))
    chemin = reseau.chemin_plus_court("A", "F")
    assert chemin[0].origine == "A" and chemin[-1].destination == "F"
    assert all(a.destination == b.origine for a, b in zip(chemin, chemin[1:]))
    assert reseau.chemin_plus_court("A", "A") == []


def test_route_vers_intersection_inconnue_refusee():
    reseau = ReseauRoutier()
    reseau.ajouter_intersection("A")
    with pytest.raises(ValueError):
        reseau.ajouter_route(Route("R", "R", 1, 50, "A", "Z"))


# --- Simulateur / Analyseur -------------------------------------------------
def test_simulation_conserve_les_vehicules():
    simu = Simulateur(fichier_config=CONFIG)
    rapport = simu.lancer_simulation(n_tours=60, delta_t=60)
    b = rapport["bilan"]
    assert b["vehicules_crees"] == (b["vehicules_en_circulation"] + b["vehicules_en_attente"]
                                    + b["vehicules_arrives"])
    assert len(simu.historique) == 60
    assert simu.historique[-1]["temps_min"] == pytest.approx(60.0)


def test_simulation_reproductible_avec_la_meme_graine():
    r1 = Simulateur(fichier_config=CONFIG).lancer_simulation(30, 60)
    r2 = Simulateur(fichier_config=CONFIG).lancer_simulation(30, 60)
    assert r1 == r2


def test_vitesses_respectent_les_limites():
    simu = Simulateur(fichier_config=CONFIG)
    simu.lancer_simulation(40, 60)
    for snap in simu.historique:
        for rid, r in snap["routes"].items():
            if r["vitesse_moyenne"] is not None:
                assert 0 <= r["vitesse_moyenne"] <= simu.reseau.routes[rid].limite_vitesse + 1e-6


def test_temps_de_parcours_au_moins_le_temps_libre():
    simu = Simulateur(fichier_config=CONFIG)
    simu.lancer_simulation(60, 60)
    assert simu.vehicules_termines
    for v in simu.vehicules_termines:
        chemin = simu.reseau.chemin_plus_court(v.origine, v.destination)
        libre = sum(r.temps_libre() for r in chemin) * 3600
        # marges : bruit de vitesse (+10 %) et entrée étalée sur au plus un pas de 60 s
        assert v.temps_parcours >= libre * 0.9 - 60


def test_analyseur_detecte_la_congestion():
    cfg = {
        "parametres": {"taux_apparition": 30, "seed": 1, "densite_max": 10, "seuil_congestion": 0.4},
        "intersections": [{"id": "A"}, {"id": "B"}],
        "routes": [{"id": "AB", "origine": "A", "destination": "B", "longueur": 1.0,
                    "limite_vitesse": 20, "bidirectionnelle": True}],
    }
    simu = Simulateur(config=cfg)
    rapport = simu.lancer_simulation(30, 60)
    assert rapport["zones_congestion"]
    assert rapport["zones_congestion"][0]["part_temps_congestionnee"] > 0


def test_analyseur_sans_donnees():
    simu = Simulateur(fichier_config=CONFIG)
    a = Analyseur([], [], simu.reseau)
    assert a.vitesse_moyenne_globale() is None
    assert a.temps_parcours()["nb_trajets"] == 0


# --- Export ---------------------------------------------------------------
def test_exports(tmp_path):
    simu = Simulateur(fichier_config=CONFIG)
    rapport = simu.lancer_simulation(10, 60, intervalle_export=5, dossier_export=str(tmp_path / "etats"))
    f_json = export.exporter_rapport_json(rapport, str(tmp_path / "rapport.json"))
    f_csv = export.exporter_historique_csv(simu.historique, str(tmp_path / "hist.csv"))
    f_trajets = export.exporter_trajets_csv(simu.vehicules_termines, str(tmp_path / "trajets.csv"))
    assert json.load(open(f_json, encoding="utf-8"))["bilan"] == rapport["bilan"]
    assert len(open(f_csv, encoding="utf-8").read().splitlines()) == 1 + 10 * len(simu.reseau.routes)
    assert os.path.exists(f_trajets)
    assert sorted(os.listdir(tmp_path / "etats")) == ["etat_0005.json", "etat_0010.json"]
