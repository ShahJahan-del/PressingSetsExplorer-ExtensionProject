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
    set_type = request.args.get('type')
    root_note = request.args.get('root')
    max_dist = int(request.args.get('distance', 1))

    if not set_type or not root_note:
        return jsonify({"error": "Paramètres incomplets"}), 400

    # 1. Correction des enharmonies pour correspondre aux clés de uf.all_stations
    enharmonic_mapping = {
        "D#": "Eb",
        "G#": "Ab",
        "A#": "Bb"
    }
    if root_note in enharmonic_mapping:
        root_note = enharmonic_mapping[root_note]

    # 2. Construction directe du nom de la station (les valeurs JS matchent désormais avec Python)
    station_name = f"{set_type} [{root_note}]"

    # 3. Vérification de sécurité standard
    if station_name not in uf.all_stations:
        return jsonify({"error": f"La station [{station_name}] n'existe pas."}), 404

    pitches = sorted(list(uf.all_stations[station_name]))

    # 1. Génération du graphe universel complet
    global_universe = uf.generate_complete_universe_graph(station_name, max_displaced_notes=1)

    # 2 & 3. Calcul dynamique et exact des distances réelles avec NetworkX
    try:
        lengths = nx.shortest_path_length(global_universe, source=station_name)
        valid_nodes = [node for node, dist in lengths.items() if dist <= max_dist]
        sub_graph = global_universe.subgraph(valid_nodes)
    except Exception:
        # Solution de secours si le graphe est déconnecté
        sub_graph = global_universe

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

@app.route('/api/identify', methods=['POST'])
def identify_sets():
    """Recherche les sets parents dont les notes reçues sont un subset."""
    data = request.get_json() or {}
    raw_pitches = data.get('pitches', [])

    # Mapping universel pour s'assurer de la correspondance numérique
    pitch_to_int = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
        "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
    }

    user_pitches = set(pitch_to_int[p] for p in raw_pitches if p in pitch_to_int)

    if not user_pitches:
        return jsonify({"matches": []})

    matches = []
    int_to_pitch = {0:"C", 1:"C#", 2:"D", 3:"D#", 4:"E", 5:"F", 6:"F#", 7:"G", 8:"G#", 9:"A", 10:"A#", 11:"B"}

    for station_name, station_pitches in uf.all_stations.items():
        # Conversion adaptative : gère les entiers et les chaînes
        station_pitches_ints = set()
        for p in station_pitches:
            if isinstance(p, int):
                station_pitches_ints.add(p)
            elif str(p).isdigit():
                station_pitches_ints.add(int(p))
            elif p in pitch_to_int:
                station_pitches_ints.add(pitch_to_int[p])

        if user_pitches.issubset(station_pitches_ints):
            missing_ints = sorted(list(station_pitches_ints - user_pitches))
            missing_pitches = [int_to_pitch.get(i, str(i)) for i in missing_ints]

            family = station_name.split(" [")[0]
            # Extraction propre de la racine d'origine de la station
            root = station_name.split("[")[1].replace("]", "")

            matches.append({
                "station_name": station_name,
                "family": family,
                "root": root,
                "missing": missing_pitches,
                "missing_count": len(missing_pitches)
            })

    matches = sorted(matches, key=lambda x: x['missing_count'])
    return jsonify({"matches": matches})

if __name__ == '__main__':
    app.run(debug=True)