"""Réseau routier : intersections, routes et calcul d'itinéraires."""
from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass

from models.route import Route


@dataclass
class Intersection:
    identifiant: str
    x: float = 0.0   # coordonnées en km (pour la carte)
    y: float = 0.0


class ReseauRoutier:
    def __init__(self):
        self.intersections = {}
        self.routes = {}
        self.sortantes = defaultdict(list)   # intersection -> routes qui en partent
        self._cache_chemins = {}

    # --- construction -----------------------------------------------------
    def ajouter_intersection(self, identifiant, x=0.0, y=0.0):
        self.intersections[identifiant] = Intersection(identifiant, x, y)

    def ajouter_route(self, route):
        for noeud in (route.origine, route.destination):
            if noeud not in self.intersections:
                raise ValueError(f"Route {route.identifiant} : intersection inconnue '{noeud}'")
        if route.identifiant in self.routes:
            raise ValueError(f"Identifiant de route en double : {route.identifiant}")
        self.routes[route.identifiant] = route
        self.sortantes[route.origine].append(route)
        self._cache_chemins.clear()

    @classmethod
    def depuis_dict(cls, config, densite_max=60.0, bruit_vitesse=0.1):
        reseau = cls()
        for i in config["intersections"]:
            reseau.ajouter_intersection(i["id"], i.get("x", 0.0), i.get("y", 0.0))
        for r in config["routes"]:
            params = dict(longueur=r["longueur"], limite_vitesse=r["limite_vitesse"],
                          densite_max=r.get("densite_max", densite_max),
                          bruit_vitesse=bruit_vitesse)
            reseau.ajouter_route(Route(r["id"], r.get("nom", r["id"]),
                                       origine=r["origine"], destination=r["destination"], **params))
            if r.get("bidirectionnelle", False):
                reseau.ajouter_route(Route(r["id"] + "_R", r.get("nom", r["id"]) + " (retour)",
                                           origine=r["destination"], destination=r["origine"], **params))
        return reseau

    # --- itinéraires ------------------------------------------------------
    def chemin_plus_court(self, depart, arrivee):
        """Liste de routes du chemin le plus rapide à vitesse libre (None si inaccessible)."""
        if depart == arrivee:
            return []
        dist = {depart: 0.0}
        precedente = {}
        tas = [(0.0, depart)]
        while tas:
            d, u = heapq.heappop(tas)
            if u == arrivee:
                break
            if d > dist.get(u, float("inf")):
                continue
            for r in self.sortantes[u]:
                nd = d + r.temps_libre()
                if nd < dist.get(r.destination, float("inf")):
                    dist[r.destination] = nd
                    precedente[r.destination] = r
                    heapq.heappush(tas, (nd, r.destination))
        if arrivee not in precedente:
            return None
        chemin, noeud = [], arrivee
        while noeud != depart:
            r = precedente[noeud]
            chemin.append(r)
            noeud = r.origine
        return chemin[::-1]

    def prochaine_route(self, intersection, destination):
        """Première route à emprunter depuis `intersection` pour rejoindre `destination`."""
        cle = (intersection, destination)
        if cle not in self._cache_chemins:
            chemin = self.chemin_plus_court(intersection, destination)
            self._cache_chemins[cle] = chemin[0] if chemin else None
        return self._cache_chemins[cle]

    # --- état global ------------------------------------------------------
    @property
    def nb_vehicules(self):
        return sum(r.nb_vehicules for r in self.routes.values())

    def etat(self):
        """Résumé de l'état courant, route par route."""
        return {
            r.identifiant: {
                "nb_vehicules": r.nb_vehicules,
                "vitesse_moyenne": r.vitesse_moyenne(),
                "densite": r.densite,
                "occupation": r.taux_occupation,
            }
            for r in self.routes.values()
        }
