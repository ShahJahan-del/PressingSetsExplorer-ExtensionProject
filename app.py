from flask import Flask, render_template, jsonify, request
import utility_functions as uf
import networkx as nx

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stations', methods=['GET'])
def get_all_stations():
    """Renvoie la liste brute des 57 stations pour alimenter le menu HTML."""
    return jsonify(sorted(list(uf.all_stations.keys())))

@app.route('/api/explore', methods=['GET'])
def explore_station():
    station_name = request.args.get('station', 'Diatonic [D]')
    max_dist = int(request.args.get('distance', 1)) # Récupère la distance choisie (1, 2, 3...)

    if station_name not in uf.all_stations:
        return jsonify({"error": "Station introuvable"}), 404

    pitches = sorted(list(uf.all_stations[station_name]))

    # 1. Calcul de TOUT le graphe universel depuis ce centre
    global_graph = uf.generate_complete_universe_graph(station_name, max_displaced_notes=1)

    # 2. Filtrage des voisins par couches (jusqu'à la distance max demandée)
    neighbors_by_layer = {}
    for layer in range(1, max_dist + 1):
        neighbors_by_layer[layer] = []

    for neighbor in global_graph.nodes():
        layer = global_graph.nodes[neighbor].get('layer')
        if layer and 1 <= layer <= max_dist:
            # On calcule le chemin pour avoir la conduite des voix globale
            path = nx.shortest_path(global_graph, source=station_name, target=neighbor)

            # Reconstruction du voice-leading pas à pas
            vl_steps = []
            for i in range(len(path) - 1):
                step_analysis = uf.calculate_harmonic_pathway(path[i], path[i+1])
                vl_steps.append(f"({', '.join(step_analysis['voice_leading'])} )")

            neighbors_by_layer[layer].append({
                "name": neighbor,
                "distance": layer,
                "path_steps": " -> ".join(path),
                "voice_leading": " -> ".join(vl_steps)
            })

    # 3. Extraction basique des modes (Rotations cycliques du set)
    # On génère les 7 rotations (ou moins selon la taille du set)
    modes_detected = []
    # Logique optionnelle à affiner : pour l'instant on liste les intervalles structurels
    intervals = [pitches[i] - pitches[0] for i in range(len(pitches))]

    return jsonify({
        "name": station_name,
        "pitches": pitches,
        "intervals": intervals,
        "neighbors_by_layer": neighbors_by_layer
    })

if __name__ == '__main__':
    app.run(debug=True)