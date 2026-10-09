
from __future__ import annotations

import random

EPS = 1e-9


class Route:
    GAP_MIN = 0.007 

    def __init__(self, identifiant, nom, longueur, limite_vitesse, origine, destination,
                 densite_max=60.0, bruit_vitesse=0.1):
        if longueur <= 0 or limite_vitesse <= 0 or densite_max <= 0:
            raise ValueError(f"Route {identifiant} : longueur, limite et densité doivent être > 0")
        self.identifiant = identifiant
        self.nom = nom
        self.longueur = float(longueur)              
        self.limite_vitesse = float(limite_vitesse)  
        self.origine = origine                       
        self.destination = destination               
        self.densite_max = float(densite_max)        
        self.bruit_vitesse = bruit_vitesse
        self.vehicules = []

    @property
    def nb_vehicules(self):
        return len(self.vehicules)

    @property
    def densite(self):
        return self.nb_vehicules / self.longueur

    @property
    def taux_occupation(self):
        return min(1.0, self.densite / self.densite_max)

    def temps_libre(self) : 
        return self.longueur / self.limite_vitesse

    def vitesse_cible(self):
       
        facteur = max(0.1, 1.0 - self.densite / self.densite_max)
        return self.limite_vitesse * facteur

    def vitesse_moyenne(self):
        if not self.vehicules:
            return None
        return sum(v.vitesse for v in self.vehicules) / len(self.vehicules)

 
    def _position_max_entree(self):
        if not self.vehicules:
            return self.longueur
        derniere = min(v.position for v in self.vehicules) - self.GAP_MIN
        return derniere if derniere >= 0 else None

    def peut_accepter(self):
        return self._position_max_entree() is not None

    def ajouter_vehicule(self, vehicule, position=0.0):
        pos_max = self._position_max_entree()
        if pos_max is None:
            return False
        vehicule.changer_de_route(self, min(position, pos_max, self.longueur))
        vehicule.vitesse = min(vehicule.vitesse, self.limite_vitesse)
        self.vehicules.append(vehicule)
        return True

    def retirer_vehicule(self, vehicule):
        if vehicule in self.vehicules:
            self.vehicules.remove(vehicule)

    def mettre_a_jour_vehicules(self, delta_t, rng=None):
        if not self.vehicules:
            return []
        rng = rng or random
        base = self.vitesse_cible()
        self.vehicules.sort(key=lambda v: v.position, reverse=True)
        limite = self.longueur
        arrives = []
        for v in self.vehicules:
            facteur = 1.0 + rng.uniform(-self.bruit_vitesse, self.bruit_vitesse)
            cible = min(self.limite_vitesse, base * facteur)
            v.vitesse = cible
            souhaitee = v.position + cible * delta_t / 3600.0
            reel = v.avancer(delta_t, position_max=limite)
            if limite == self.longueur and souhaitee > self.longueur + EPS:
                v.reste = souhaitee - self.longueur   # continue sur la route suivante
            else:
                v.reste = 0.0
                v.vitesse = reel * 3600.0 / delta_t   # vitesse effective (freinée)
            if v.position >= self.longueur - EPS:
                arrives.append(v)
            # un véhicule qui quitte la route ne gêne plus ceux qui le suivent
            limite = self.longueur if v.reste > 0 else v.position - self.GAP_MIN
        return arrives

    def retasser(self):

        self.vehicules.sort(key=lambda v: v.position, reverse=True)
        limite = self.longueur
        for v in self.vehicules:
            v.position = max(0.0, min(v.position, limite))
            limite = v.position - self.GAP_MIN

    def __repr__(self):
        return (f"Route({self.identifiant}: {self.origine}->{self.destination}, "
                f"{self.longueur} km, {self.limite_vitesse} km/h, {self.nb_vehicules} veh)")
