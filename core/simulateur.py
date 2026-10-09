from __future__ import annotations

import json
import os
import random

from core.analyseur import Analyseur
from models.reseau import ReseauRoutier
from models.vehicule import Vehicule
from out import affichage, export

PARAMETRES_DEFAUT = {
    "taux_apparition": 6.0,    
    "seed": None,
    "densite_max": 60.0,       
    "seuil_congestion": 0.5,   
    "bruit_vitesse": 0.1,
}


class Simulateur:
    def __init__(self, fichier_config=None, config=None):
        if config is None:
            if fichier_config is None:
                raise ValueError("Fournir `fichier_config` ou `config`")
            with open(fichier_config, encoding="utf-8") as f:
                config = json.load(f)
        self.config = config
        self.parametres = {**PARAMETRES_DEFAUT, **config.get("parametres", {})}
        self.rng = random.Random(self.parametres["seed"])
        self.reseau = ReseauRoutier.depuis_dict(
            config,
            densite_max=self.parametres["densite_max"],
            bruit_vitesse=self.parametres["bruit_vitesse"],
        )
        self.temps = 0.0                 
        self.historique = []             
        self.vehicules_termines = []
        self.file_attente = []           
        self.nb_crees = 0
        self.analyseur = None

    
    def _generer_trafic(self, delta_t):
        lam = self.parametres["taux_apparition"] * delta_t / 60.0
        n = int(lam) + (1 if self.rng.random() < lam - int(lam) else 0)
        noeuds = [i for i in self.reseau.intersections if self.reseau.sortantes[i]]
        for _ in range(n):
            origine = self.rng.choice(noeuds)
            destination = self.rng.choice([d for d in self.reseau.intersections if d != origine])
            if self.reseau.prochaine_route(origine, destination) is None:
                continue
            self.nb_crees += 1
            self.file_attente.append(Vehicule(
                f"V{self.nb_crees:05d}", origine=origine, destination=destination,
                temps_creation=self.temps))

    def _faire_entrer_vehicules(self, delta_t):
        restants = []
        for v in self.file_attente:
            route = self.reseau.prochaine_route(v.origine, v.destination)
            position = self.rng.uniform(0.0, route.vitesse_cible() * delta_t / 3600.0)
            if not route.ajouter_vehicule(v, position=position):
                restants.append(v)
        self.file_attente = restants

    def _mettre_a_jour_reseau(self, delta_t):
        arrivees = []
        routes = list(self.reseau.routes.values())
        self.rng.shuffle(routes)
        for route in routes:
            arrivees.extend(route.mettre_a_jour_vehicules(delta_t, self.rng))

    
        arrivees.sort(key=lambda v: v.reste, reverse=True)
        temps_fin = self.temps + delta_t
        routes_bloquees = set()
        for v in arrivees:
            ancienne = v.route
            if v.destination == ancienne.destination:
                ancienne.retirer_vehicule(v)
                v.termine = True
                v.temps_arrivee = temps_fin
                self.vehicules_termines.append(v)
                continue
            suivante = self.reseau.prochaine_route(ancienne.destination, v.destination)
            if suivante.ajouter_vehicule(v, position=v.reste):
                ancienne.retirer_vehicule(v)
            else:
                
                v.vitesse = 0.0
                v.reste = 0.0
                v.position = ancienne.longueur
                routes_bloquees.add(ancienne)
        for route in routes_bloquees:
            route.retasser()

    def _instantane(self):
        total = self.reseau.nb_vehicules
        somme = sum(r.vitesse_moyenne() * r.nb_vehicules
                    for r in self.reseau.routes.values() if r.nb_vehicules)
        return {
            "temps_min": self.temps / 60.0,
            "nb_vehicules": total,
            "nb_en_attente": len(self.file_attente),
            "nb_termines": len(self.vehicules_termines),
            "vitesse_moyenne": somme / total if total else None,
            "routes": self.reseau.etat(),
        }

    # --- API principale ---------------------------------------------------
    def lancer_simulation(self, n_tours, delta_t, intervalle_affichage=None,
                          intervalle_export=None, dossier_export=None):
        for tour in range(1, n_tours + 1):
            self._generer_trafic(delta_t)
            self._faire_entrer_vehicules(delta_t)
            self._mettre_a_jour_reseau(delta_t)
            self.temps += delta_t

            instantane = self._instantane()
            self.historique.append(instantane)

            if intervalle_affichage and tour % intervalle_affichage == 0:
                affichage.afficher_etat(instantane)
            if intervalle_export and dossier_export and tour % intervalle_export == 0:
                export.exporter_etat_json(
                    instantane, os.path.join(dossier_export, f"etat_{tour:04d}.json"))

        self.analyseur = Analyseur(self.historique, self.vehicules_termines, self.reseau,
                                   self.parametres["seuil_congestion"])
        rapport = self.analyseur.rapport()
        rapport["bilan"] = {
            "vehicules_crees": self.nb_crees,
            "vehicules_en_circulation": self.reseau.nb_vehicules,
            "vehicules_en_attente": len(self.file_attente),
            "vehicules_arrives": len(self.vehicules_termines),
        }
        return rapport
