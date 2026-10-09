# Simulateur de trafic routier

Simulateur orienté objet d'un réseau routier : routes, intersections et véhicules qui circulent
entre une origine et une destination. Il produit des statistiques (vitesses, congestion, temps de
parcours), des fichiers CSV/JSON et des visualisations (graphiques et carte du réseau).

## Sommaire

1. [Installation](#installation)
2. [Utilisation](#utilisation)
3. [Structure du projet](#structure-du-projet)
4. [Configuration du réseau](#configuration-du-réseau)
5. [Modèle de simulation](#modèle-de-simulation)
6. [Résultats produits](#résultats-produits)
7. [Tests](#tests)
8. [Limites et pistes d'amélioration](#limites-et-pistes-damélioration)

## Installation

Prérequis : Python 3.9 ou plus récent.

```bash
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Dépendances : `matplotlib` (graphiques) et `pytest` (tests).

## Utilisation

```bash
python main.py
```

Cela lance une simulation de 60 pas d'une minute, affiche l'état du réseau toutes les 10 minutes
simulées, puis le rapport final, et écrit les résultats dans `resultats/`.

Utilisation depuis du code :

```python
from core.simulateur import Simulateur
from out import affichage, export

simu = Simulateur(fichier_config="data/config_reseau.json")
rapport = simu.lancer_simulation(n_tours=60, delta_t=60)   # 60 minutes, pas de 1 min

affichage.afficher_rapport(rapport)
export.exporter_rapport_json(rapport, "resultats/rapport.json")
affichage.tracer_carte(simu.reseau, simu.analyseur, "resultats/carte.png")
```

`lancer_simulation(n_tours, delta_t, intervalle_affichage=None, intervalle_export=None, dossier_export=None)` :

| Paramètre | Rôle |
|---|---|
| `n_tours` | Nombre de pas de simulation |
| `delta_t` | Durée d'un pas, en secondes |
| `intervalle_affichage` | Affiche l'état en console tous les N tours |
| `intervalle_export` + `dossier_export` | Écrit un JSON de l'état tous les N tours |

La méthode retourne le rapport statistique sous forme de dictionnaire.

## Structure du projet

```
simulateur_trafic/
├── main.py                  Point d'entrée
├── conftest.py              Permet à pytest de trouver les modules
├── requirements.txt
├── data/
│   └── config_reseau.json   Paramètres, intersections et routes
├── models/
│   ├── vehicule.py          Classe Vehicule
│   ├── route.py             Classe Route
│   └── reseau.py            Classes ReseauRoutier et Intersection
├── core/
│   ├── simulateur.py        Classe Simulateur (boucle principale)
│   └── analyseur.py         Classe Analyseur (statistiques)
├── out/
│   ├── affichage.py         Console, graphiques, carte
│   └── export.py            CSV et JSON
├── tests/
│   └── test_simulateur.py   17 tests unitaires
└── resultats/               Créé à l'exécution
```

### Rôle des classes

| Classe | Fichier | Responsabilité |
|---|---|---|
| `Vehicule` | `models/vehicule.py` | Position, vitesse, route actuelle, origine et destination. `avancer()` et `changer_de_route()`. |
| `Route` | `models/route.py` | Longueur, limite de vitesse, véhicules présents. `ajouter_vehicule()` et `mettre_a_jour_vehicules()`. |
| `ReseauRoutier` | `models/reseau.py` | Intersections et routes, chargement depuis le JSON, calcul du plus court chemin. |
| `Simulateur` | `core/simulateur.py` | Boucle de simulation, génération du trafic, transferts entre routes, historique. |
| `Analyseur` | `core/analyseur.py` | Vitesses moyennes, zones de congestion, temps de parcours. |

## Configuration du réseau

Tout le scénario est décrit dans `data/config_reseau.json`.

```json
{
  "parametres": {
    "taux_apparition": 22.0,
    "seed": 42,
    "densite_max": 15.0,
    "seuil_congestion": 0.5,
    "bruit_vitesse": 0.1
  },
  "intersections": [{"id": "A", "x": 0.0, "y": 1.5}],
  "routes": [
    {"id": "AB", "nom": "Avenue Nord 1", "origine": "A", "destination": "B",
     "longueur": 2.0, "limite_vitesse": 50, "bidirectionnelle": true}
  ]
}
```

### Paramètres généraux

| Clé | Unité | Signification |
|---|---|---|
| `taux_apparition` | véhicules/min | Nombre moyen de véhicules créés par minute |
| `seed` | - | Graine du générateur aléatoire (mêmes valeurs, mêmes résultats) |
| `densite_max` | véhicules/km | Densité à partir de laquelle une route est saturée |
| `seuil_congestion` | 0 à 1 | Taux d'occupation à partir duquel une route est dite congestionnée |
| `bruit_vitesse` | fraction | Variation aléatoire de la vitesse de chaque véhicule (±10 % ici) |

### Intersections et routes

- Une intersection a un `id` et des coordonnées `x`, `y` en km (utilisées pour la carte).
- Une route a un `id`, un `nom`, une `origine`, une `destination`, une `longueur` (km) et une
  `limite_vitesse` (km/h).
- `"bidirectionnelle": true` crée aussi la route inverse, d'identifiant `<id>_R`.
- `densite_max` peut être redéfinie pour une route donnée (la Rue Centrale est plus étroite).

### Régler le niveau de trafic

Le comportement du réseau change fortement avec `taux_apparition` (avec les autres valeurs de
l'exemple) :

| `taux_apparition` | Comportement |
|---|---|
| 14 | Circulation fluide, aucune congestion |
| 22 | Congestion partielle sur quelques routes (valeur par défaut) |
| 30 et plus | Réseau presque bloqué, files d'attente à l'entrée |

## Modèle de simulation

### Unités

Distances en km, vitesses en km/h, temps en secondes dans le code et en minutes dans les rapports.

### Déroulement d'un tour

Chaque appel de la boucle dans `Simulateur.lancer_simulation` exécute cinq étapes :

1. **Génération** : un nombre de véhicules proportionnel à `taux_apparition × delta_t` est créé,
   chacun avec une origine et une destination tirées au hasard.
2. **Entrée** : chaque véhicule tente d'entrer sur la première route de son itinéraire. S'il n'y a
   pas de place, il attend dans une file. Cette attente compte dans son temps de parcours.
3. **Déplacement** : chaque route met à jour ses véhicules (voir ci-dessous).
4. **Transferts** : les véhicules arrivés en bout de route passent à la route suivante ou, s'ils sont
   à destination, terminent leur trajet. Si la route suivante est pleine, ils restent bloqués en bout
   de route, ce qui fait remonter les files.
5. **Instantané** : l'état de chaque route est ajouté à l'historique.

### Déplacement sur une route

- **Vitesse cible** : `limite × max(0,1 ; 1 − densité / densité_max)`, multipliée par un facteur
  aléatoire `1 ± bruit_vitesse`. La vitesse baisse donc quand la route se remplit.
- **Distance parcourue** : `vitesse × delta_t / 3600` km.
- **Pas de dépassement** : les véhicules sont traités du plus avancé au dernier et gardent au moins
  7 m (`Route.GAP_MIN`) avec celui qui les précède.
- **Report de distance** : si un véhicule dépasse la fin de la route pendant un pas, la distance
  restante est reportée sur la route suivante, pour ne pas perdre de temps à chaque intersection.
- **Vitesse effective** : la vitesse enregistrée est celle réellement obtenue, donc freinée ou nulle
  pour un véhicule gêné. C'est elle qui sert aux statistiques.

### Itinéraires

Chaque véhicule suit le chemin le plus rapide à vitesse libre (algorithme de Dijkstra, poids =
`longueur / limite_vitesse`). Les itinéraires sont calculés une fois puis mis en cache dans
`ReseauRoutier.prochaine_route`. Ils ne tiennent pas compte de la congestion.

### Statistiques

| Indicateur | Définition |
|---|---|
| Taux d'occupation | `densité / densité_max`, borné à 1 |
| Vitesse moyenne | Moyenne des vitesses effectives, pondérée par le nombre de véhicules présents à chaque pas |
| Zone de congestion | Route dont le taux d'occupation atteint `seuil_congestion` ; on indique la part du temps pendant laquelle c'est le cas |
| Temps de parcours | De la création du véhicule à son arrivée (attente d'entrée comprise), pour les trajets terminés |

## Résultats produits

`python main.py` écrit dans `resultats/` :

| Fichier | Contenu |
|---|---|
| `rapport.json` | Rapport complet : vitesses, occupations, zones de congestion, temps de parcours, bilan |
| `historique.csv` | Une ligne par pas et par route (véhicules, vitesse, densité, occupation) |
| `trajets.csv` | Une ligne par véhicule arrivé (origine, destination, durée, distance) |
| `etats/etat_XXXX.json` | États intermédiaires exportés pendant la simulation |
| `graphiques.png` | Véhicules en circulation, vitesse moyenne, occupation par route, histogramme des temps de parcours |
| `carte.png` | Carte du réseau, chaque route colorée selon son occupation moyenne |

### Exemple (configuration fournie, seed 42, 60 minutes)

- 1320 véhicules créés, 1031 arrivés à destination.
- Vitesse moyenne globale : 18,6 km/h.
- Temps de parcours : 9,1 min en moyenne, 6,0 min en médiane, 29 min au maximum.
- Zones les plus congestionnées : Boulevard Est (`CF`, `CF_R`) et Avenue Nord 1 (`AB`).
- La vitesse moyenne du réseau passe d'environ 37 km/h à 12 km/h entre la 10e et la 60e minute.

## Tests

```bash
pytest
```

Les 17 tests couvrent :

- le déplacement d'un véhicule et le changement de route ;
- l'ajout de véhicules, le refus quand l'entrée est occupée, l'absence de dépassement ;
- la baisse de vitesse avec la densité et l'arrivée en bout de route ;
- le chargement de la configuration, les routes bidirectionnelles et le plus court chemin ;
- la conservation des véhicules (créés = en circulation + en attente + arrivés) ;
- la reproductibilité à graine égale et le respect des limites de vitesse ;
- la cohérence des temps de parcours avec le temps à vitesse libre ;
- la détection de la congestion et le cas sans données ;
- les exports CSV et JSON.

## Limites et pistes d'amélioration

Limites du modèle actuel :

- une seule voie par sens, sans dépassement ;
- pas de feux tricolores : le débit aux intersections n'est limité que par la place disponible sur la
  route suivante ;
- itinéraires fixes, qui ne s'adaptent pas à la congestion ;
- pas de temps assez grossier (60 s) : les temps de parcours sont précis à environ une minute.

Pistes d'amélioration :

- ajouter des feux ou des priorités aux intersections ;
- recalculer les itinéraires en fonction de la congestion ;
- introduire des types de véhicules (voiture, bus, camion) et des heures de pointe ;
- charger un réseau réel (par exemple depuis OpenStreetMap).
