from __future__ import annotations
class Vehicule:
    def __init__(self, identifiant, route=None, position=0.0, vitesse=0.0,
                 origine=None, destination=None, temps_creation=0.0):
        self.identifiant = identifiant
        self.route = route              
        self.position = position        
        self.vitesse = vitesse          
        self.origine = origine          
        self.destination = destination  
        self.temps_creation = temps_creation
        self.temps_arrivee = None
        self.distance_parcourue = 0.0
        self.reste = 0.0                
        self.termine = False

    def avancer(self, delta_t, position_max=None):
        souhaitee = self.position + self.vitesse * delta_t / 3600.0
        nouvelle = souhaitee
        if position_max is not None:
            nouvelle = min(souhaitee, max(self.position, position_max))
        reel = nouvelle - self.position
        self.position = nouvelle
        self.distance_parcourue += reel
        return reel

    def changer_de_route(self, nouvelle_route, position=0.0):
        self.route = nouvelle_route
        self.position = position
        self.distance_parcourue += position
        self.reste = 0.0

    @property
    def temps_parcours(self):
        if self.temps_arrivee is None:
            return None
        return self.temps_arrivee - self.temps_creation

    def __repr__(self):
        nom = self.route.identifiant if self.route else "-"
        return (f"Vehicule({self.identifiant}, route={nom}, pos={self.position:.3f} km, "
                f"v={self.vitesse:.1f} km/h)")
