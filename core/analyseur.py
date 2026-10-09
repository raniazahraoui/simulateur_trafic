
from __future__ import annotations

import statistics


class Analyseur:
    def __init__(self, historique, vehicules_termines, reseau, seuil_congestion=0.5):
        self.historique = historique
        self.vehicules_termines = vehicules_termines
        self.reseau = reseau
        self.seuil_congestion = seuil_congestion

    # --- vitesses ---------------------------------------------------------
    def vitesses_moyennes_par_route(self):
  
        resultat = {}
        for rid in self.reseau.routes:
            total, poids = 0.0, 0
            for snap in self.historique:
                r = snap["routes"][rid]
                if r["nb_vehicules"] > 0:
                    total += r["vitesse_moyenne"] * r["nb_vehicules"]
                    poids += r["nb_vehicules"]
            resultat[rid] = total / poids if poids else None
        return resultat

    def vitesse_moyenne_globale(self):
        total, poids = 0.0, 0
        for snap in self.historique:
            for r in snap["routes"].values():
                if r["nb_vehicules"] > 0:
                    total += r["vitesse_moyenne"] * r["nb_vehicules"]
                    poids += r["nb_vehicules"]
        return total / poids if poids else None

    # --- congestion -------------------------------------------------------
    def zones_congestion(self, seuil=None):
        
        seuil = self.seuil_congestion if seuil is None else seuil
        zones = []
        n = len(self.historique)
        for rid, route in self.reseau.routes.items():
            occ = [snap["routes"][rid]["occupation"] for snap in self.historique]
            part = sum(1 for o in occ if o >= seuil) / n if n else 0.0
            if part > 0:
                zones.append({
                    "route": rid,
                    "nom": route.nom,
                    "occupation_moyenne": sum(occ) / n,
                    "occupation_max": max(occ),
                    "part_temps_congestionnee": part,
                })
        zones.sort(key=lambda z: (z["part_temps_congestionnee"], z["occupation_moyenne"]), reverse=True)
        return zones

    def occupation_moyenne_par_route(self):
        n = len(self.historique)
        return {rid: (sum(s["routes"][rid]["occupation"] for s in self.historique) / n if n else 0.0)
                for rid in self.reseau.routes}

    # --- temps de parcours ------------------------------------------------
    def durees_parcours(self):
        """Durées des trajets terminés, en minutes."""
        return [v.temps_parcours / 60.0 for v in self.vehicules_termines]

    def temps_parcours(self):
        durees = self.durees_parcours()
        if not durees:
            return {"nb_trajets": 0, "moyen_min": None, "median_min": None,
                    "min_min": None, "max_min": None}
        return {
            "nb_trajets": len(durees),
            "moyen_min": statistics.mean(durees),
            "median_min": statistics.median(durees),
            "min_min": min(durees),
            "max_min": max(durees),
        }

    # --- séries temporelles ----------------------------------------------
    def serie_temporelle(self):
        temps = [s["temps_min"] for s in self.historique]
        nb = [s["nb_vehicules"] for s in self.historique]
        vit = [s["vitesse_moyenne"] for s in self.historique]
        return temps, nb, vit

    # --- rapport ----------------------------------------------------------
    def rapport(self):
        return {
            "duree_simulee_min": self.historique[-1]["temps_min"] if self.historique else 0.0,
            "vitesse_moyenne_globale": self.vitesse_moyenne_globale(),
            "vitesses_par_route": self.vitesses_moyennes_par_route(),
            "occupation_par_route": self.occupation_moyenne_par_route(),
            "zones_congestion": self.zones_congestion(),
            "temps_parcours": self.temps_parcours(),
            "seuil_congestion": self.seuil_congestion,
        }
