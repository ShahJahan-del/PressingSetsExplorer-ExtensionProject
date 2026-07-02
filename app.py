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

# À remplacer dans app.py

@app.route('/api/explore', methods=['GET'])
def explore_station():
    set_type = request.args.get('type')
    root_note = request.args.get('root')
    max_dist = int(request.args.get('distance', 1))

    if not set_type or not root_note:
        return jsonify({"error": "Paramètres incomplets"}), 400

    station_name = f"{set_type} [{root_note}]"

    if station_name not in uf.all_stations:
        return jsonify({"error": f"La station [{station_name}] n'existe pas."}), 404

    pitches = sorted(list(uf.all_stations[station_name]))

    # 1. Génération du graphe universel complet
    global_universe = uf.generate_complete_universe_graph(station_name, max_displaced_notes=1)

    # 2. Collecter tous les nœuds valides qui entrent dans la distance max
    valid_nodes = [station_name]
    for neighbor in global_universe.nodes():
        layer = global_universe.nodes[neighbor].get('layer')
        if layer and 1 <= layer <= max_dist:
            valid_nodes.append(neighbor)

    # 3. Extraire le sous-graphe exact contenant UNIQUEMENT ces nœuds
    # Cela permet de conserver TOUTES les liaisons existantes entre eux dans l'univers
    sub_graph = global_universe.subgraph(valid_nodes)

    nodes_data = []
    edges_data = []
    seen_pairs = set()

    for node in sub_graph.nodes():
        family = node.split(" [")[0]
        is_center = (node == station_name)

        nodes_data.append({
            "id": node,
            "label": node,
            "group": family,
            "value": 25 if is_center else 14,
            "borderWidth": 3 if is_center else 1
        })

        for neighbor in sub_graph.successors(node):
            pair_key = tuple(sorted([node, neighbor]))

            # --- À remplacer dans la section de boucle des liaisons de app.py ---

            # --- Section de boucle des liaisons dans app.py ---
        for neighbor in sub_graph.successors(node):
            pair_key = tuple(sorted([node, neighbor]))

            # --- Section de boucle des liaisons dans app.py ---
        for neighbor in sub_graph.successors(node):
            pair_key = tuple(sorted([node, neighbor]))

            if pair_key not in seen_pairs:
                step_analysis = uf.calculate_harmonic_pathway(node, neighbor)

                # On formate l'étiquette proprement : "NoteDeFrom ⇄ NoteDeTo"
                vl_labels = [label.replace("->", " ⇄ ") for label in step_analysis['voice_leading']]
                vl_text = ", ".join(vl_labels)

                edges_data.append({
                    "from": node,
                    "to": neighbor,
                    "label": "",           # Vide par défaut au centre
                    "textFull": vl_text,   # On stocke le texte propre ici
                    "arrows": ""
                })
                seen_pairs.add(pair_key)

    return jsonify({
        "center": station_name,
        "pitches": pitches,
        "nodes": nodes_data,
        "edges": edges_data
    })

if __name__ == '__main__':
    app.run(debug=True)