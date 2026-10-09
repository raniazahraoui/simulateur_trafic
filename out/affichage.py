"""Affichage console et graphiques (matplotlib)."""
from __future__ import annotations

import os


def _plt(montrer):
    import matplotlib
    if not montrer:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _fmt(valeur, unite="", chiffres=1):
    return "n/a" if valeur is None else f"{valeur:.{chiffres}f}{unite}"


# --- console ---------------------------------------------------------------
def afficher_etat(instantane):
    """Ligne de suivi d'un état intermédiaire."""
    print(f"[t={instantane['temps_min']:5.1f} min] "
          f"en circulation: {instantane['nb_vehicules']:3d} | "
          f"en attente: {instantane['nb_en_attente']:3d} | "
          f"arrivés: {instantane['nb_termines']:3d} | "
          f"vitesse moy.: {_fmt(instantane['vitesse_moyenne'], ' km/h')}")


def afficher_rapport(rapport):
    print("\n" + "=" * 62)
    print(f" RAPPORT DE SIMULATION ({rapport['duree_simulee_min']:.0f} min simulées)")
    print("=" * 62)

    b = rapport.get("bilan")
    if b:
        print(f" Véhicules créés: {b['vehicules_crees']} | arrivés: {b['vehicules_arrives']} | "
              f"en circulation: {b['vehicules_en_circulation']} | en attente: {b['vehicules_en_attente']}")

    print(f"\n Vitesse moyenne globale : {_fmt(rapport['vitesse_moyenne_globale'], ' km/h')}")

    tp = rapport["temps_parcours"]
    print(f" Temps de parcours ({tp['nb_trajets']} trajets) : moyen {_fmt(tp['moyen_min'], ' min')}, "
          f"médian {_fmt(tp['median_min'], ' min')}, min {_fmt(tp['min_min'], ' min')}, "
          f"max {_fmt(tp['max_min'], ' min')}")

    print("\n Route      Vitesse moy.   Occupation moy.")
    print(" " + "-" * 42)
    for rid, vit in rapport["vitesses_par_route"].items():
        print(f" {rid:<8} {_fmt(vit, ' km/h'):>12} {rapport['occupation_par_route'][rid]:>14.0%}")

    zones = rapport["zones_congestion"]
    print(f"\n Zones de congestion (occupation ≥ {rapport['seuil_congestion']:.0%}) :")
    if not zones:
        print("   aucune")
    for z in zones:
        print(f"   {z['route']:<6} {z['nom']:<22} congestionnée {z['part_temps_congestionnee']:.0%} du temps "
              f"(max {z['occupation_max']:.0%})")
    print("=" * 62 + "\n")


# --- graphiques ------------------------------------------------------------
def tracer_graphiques(analyseur, fichier="resultats/graphiques.png", montrer=False):
    plt = _plt(montrer)
    temps, nb, vit = analyseur.serie_temporelle()
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0, 0].plot(temps, nb, color="tab:blue")
    axes[0, 0].set(title="Véhicules en circulation", xlabel="Temps (min)", ylabel="Véhicules")

    t_ok = [t for t, v in zip(temps, vit) if v is not None]
    v_ok = [v for v in vit if v is not None]
    axes[0, 1].plot(t_ok, v_ok, color="tab:green")
    axes[0, 1].set(title="Vitesse moyenne du réseau", xlabel="Temps (min)", ylabel="km/h")

    occ = analyseur.occupation_moyenne_par_route()
    routes = list(occ)
    couleurs = ["tab:red" if occ[r] >= analyseur.seuil_congestion else "tab:gray" for r in routes]
    axes[1, 0].bar(routes, [occ[r] * 100 for r in routes], color=couleurs)
    axes[1, 0].axhline(analyseur.seuil_congestion * 100, ls="--", color="k", lw=1)
    axes[1, 0].set(title="Occupation moyenne par route", ylabel="% de la capacité")
    axes[1, 0].tick_params(axis="x", rotation=45)

    durees = analyseur.durees_parcours()
    if durees:
        axes[1, 1].hist(durees, bins=15, color="tab:orange", edgecolor="white")
    axes[1, 1].set(title="Temps de parcours", xlabel="Minutes", ylabel="Trajets")

    fig.tight_layout()
    return _sortie(fig, plt, fichier, montrer)


def tracer_carte(reseau, analyseur, fichier="resultats/carte.png", montrer=False):
    """Carte du réseau : chaque route est colorée selon son occupation moyenne."""
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    plt = _plt(montrer)
    occ = analyseur.occupation_moyenne_par_route()
    cmap = cm.get_cmap("RdYlGn_r") if hasattr(cm, "get_cmap") else plt.colormaps["RdYlGn_r"]
    norm = mcolors.Normalize(vmin=0, vmax=1)

    fig, ax = plt.subplots(figsize=(9, 5))
    for rid, r in reseau.routes.items():
        a, b = reseau.intersections[r.origine], reseau.intersections[r.destination]
        dx, dy = b.x - a.x, b.y - a.y
        norme = (dx * dx + dy * dy) ** 0.5 or 1.0
        ox, oy = dy / norme * 0.07, -dx / norme * 0.07   # décalage pour séparer les deux sens
        ax.annotate("", xy=(b.x + ox, b.y + oy), xytext=(a.x + ox, a.y + oy),
                    arrowprops=dict(arrowstyle="-|>", lw=3, color=cmap(norm(occ[rid])),
                                    shrinkA=14, shrinkB=14))
    for i in reseau.intersections.values():
        ax.scatter(i.x, i.y, s=420, color="white", edgecolor="black", zorder=3)
        ax.text(i.x, i.y, i.identifiant, ha="center", va="center", fontweight="bold", zorder=4)
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="Occupation moyenne")
    ax.set(title="Carte du réseau : congestion moyenne par route", xlabel="km", ylabel="km")
    ax.set_aspect("equal")
    ax.margins(0.1)
    fig.tight_layout()
    return _sortie(fig, plt, fichier, montrer)


def _sortie(fig, plt, fichier, montrer):
    if fichier:
        dossier = os.path.dirname(fichier)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        fig.savefig(fichier, dpi=130)
    if montrer:
        plt.show()
    plt.close(fig)
    return fichier
