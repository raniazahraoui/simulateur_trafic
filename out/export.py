"""Export des résultats en CSV et JSON."""
from __future__ import annotations

import csv
import json
import os


def _preparer(fichier):
    dossier = os.path.dirname(fichier)
    if dossier:
        os.makedirs(dossier, exist_ok=True)


def exporter_historique_csv(historique, fichier):
    """Une ligne par (tour, route) : nombre de véhicules, vitesse, densité, occupation."""
    _preparer(fichier)
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["temps_min", "route", "nb_vehicules", "vitesse_moyenne_kmh",
                    "densite_veh_km", "occupation"])
        for snap in historique:
            for rid, r in snap["routes"].items():
                vit = "" if r["vitesse_moyenne"] is None else round(r["vitesse_moyenne"], 2)
                w.writerow([round(snap["temps_min"], 2), rid, r["nb_vehicules"], vit,
                            round(r["densite"], 3), round(r["occupation"], 3)])
    return fichier


def exporter_trajets_csv(vehicules_termines, fichier):
    """Une ligne par véhicule arrivé à destination."""
    _preparer(fichier)
    with open(fichier, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vehicule", "origine", "destination", "creation_min", "arrivee_min",
                    "temps_parcours_min", "distance_km"])
        for v in vehicules_termines:
            w.writerow([v.identifiant, v.origine, v.destination,
                        round(v.temps_creation / 60, 2), round(v.temps_arrivee / 60, 2),
                        round(v.temps_parcours / 60, 2), round(v.distance_parcourue, 3)])
    return fichier


def exporter_rapport_json(rapport, fichier):
    _preparer(fichier)
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    return fichier


def exporter_etat_json(instantane, fichier):
    """État intermédiaire du réseau à un instant donné."""
    return exporter_rapport_json(instantane, fichier)
