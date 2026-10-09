import os

from core.simulateur import Simulateur
from out import affichage, export


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    sortie = os.path.join(base, "resultats")

    simu = Simulateur(fichier_config=os.path.join(base, "data", "config_reseau.json"))
    rapport = simu.lancer_simulation(
        n_tours=60, delta_t=60,            
        intervalle_affichage=10,          
        intervalle_export=15,              
        dossier_export=os.path.join(sortie, "etats"),
    )

    affichage.afficher_rapport(rapport)
    export.exporter_rapport_json(rapport, os.path.join(sortie, "rapport.json"))
    export.exporter_historique_csv(simu.historique, os.path.join(sortie, "historique.csv"))
    export.exporter_trajets_csv(simu.vehicules_termines, os.path.join(sortie, "trajets.csv"))
    affichage.tracer_graphiques(simu.analyseur, os.path.join(sortie, "graphiques.png"))
    affichage.tracer_carte(simu.reseau, simu.analyseur, os.path.join(sortie, "carte.png"))
    print(f"Résultats enregistrés dans : {sortie}")


if __name__ == "__main__":
    main()
