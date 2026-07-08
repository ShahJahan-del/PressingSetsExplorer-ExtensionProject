from flask import Flask, render_template, jsonify, request
import utility_functions as uf
import networkx as nx
import piece_analyzer as pa

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

    # On utilise directement le dictionnaire de référence de utility_functions
    user_pitches = set(uf.NOTE_TO_INT[p] for p in raw_pitches if p in uf.NOTE_TO_INT)

    if not user_pitches:
        return jsonify({"matches": []})

    matches = []

    for station_name, station_pitches in uf.all_stations.items():
        # Plus besoin de deviner le type : station_pitches contient de purs entiers (Point 3)
        if user_pitches.issubset(station_pitches):
            missing_ints = sorted(list(station_pitches - user_pitches))

            # Harmonisation visuelle stricte via le dictionnaire global INT_TO_NOTE (Point 4)
            missing_pitches = [uf.INT_TO_NOTE.get(i, str(i)) for i in missing_ints]

            family = station_name.split(" [")[0]
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

import random

@app.route('/api/analyze', methods=['POST'])
def analyze_piece():
    data = request.get_json() or {}
    center_station = data.get('center')
    active_sets = data.get('sets', [])

    if not center_station or not active_sets:
        return jsonify({"error": "Paramètres manquants"}), 400

    # 1. Calcul du graphe local de la pièce
    try:
        analysis_graph = pa.build_piece_harmonic_graph(center_station, active_sets, max_step_distance=1)
    except Exception as e:
        return jsonify({"error": f"Erreur build_piece_harmonic_graph: {str(e)}"}), 500

    if not analysis_graph:
        return jsonify({"error": "Le moteur d'analyse n'a généré aucun graphe."}), 500

    # 2. Récupération du rapport d'archipels
    archipelago_routes = {}
    try:
        archipelago_routes = pa.print_analytical_report(analysis_graph, center_station)
    except Exception as e:
        print(f"⚠️ Note: print_analytical_report a levé une exception: {e}")

    nodes_data = []
    edges_data = []
    seen_pairs = set()

    # Palette de couleurs uniques pour différencier chaque route de secours
    def generate_random_color():
        return f"#{random.randint(80, 220):02x}{random.randint(80, 220):02x}{random.randint(80, 220):02x}"

    # 3. Formatage ultra-sécurisé des nœuds
    for node in analysis_graph.nodes():
        node_str = str(node)
        family = node_str.split(" [")[0] if " [" in node_str else "Unknown"
        is_center = (node_str == str(center_station))

        node_definition = {
            "id": node_str,
            "label": node_str,
            "group": family, # Laisse Vis.js appliquer le code couleur natif défini côté client
            "value": 25 if is_center else 14
        }

        # Ajout d'une bordure distincte pour le centre macro-harmonique
        if is_center:
            node_definition["borderWidth"] = 4
            node_definition["color"] = { "border": "#bef264" }

        nodes_data.append(node_definition)

    # 4. Formatage ultra-sécurisé des liaisons directes du morceau (Ligne unifiée, sans flèche graphique)
    MAIN_MESH_COLOR = "#84cc16"
    for node in analysis_graph.nodes():
        for neighbor in analysis_graph.successors(node):
            node_str = str(node)
            neighbor_str = str(neighbor)
            pair_key = tuple(sorted([node_str, neighbor_str]))

            if pair_key not in seen_pairs:
                try:
                    raw_vl = analysis_graph[node][neighbor].get('voice_leading', [])
                    if isinstance(raw_vl, list):
                        vl_labels = [str(item).replace("->", " ⇄ ") for item in raw_vl]
                        vl_text = ", ".join(vl_labels)
                    else:
                        vl_text = str(raw_vl).replace("->", " ⇄ ")
                except Exception:
                    vl_text = "⇄"

                edges_data.append({
                    "from": node_str,
                    "to": neighbor_str,
                    "label": "",
                    "textFull": vl_text,
                    "arrows": "", # Aucune flèche graphique sur la ligne (géré textuellement par ⇄)
                    "dashes": False,
                    "color": {"color": MAIN_MESH_COLOR}
                })
                seen_pairs.add(pair_key)

    # 5. Extraction sécurisée des routes de secours multiples (Point 8)
    if isinstance(archipelago_routes, dict):
        for isolated_node, route_info in archipelago_routes.items():
            if not isinstance(route_info, dict) or "all_paths" not in route_info:
                continue

            # Une couleur unique pour tout cet archipel
            route_color = generate_random_color()

            # On trace CHAQUE chemin ex-æquo trouvé par le moteur
            for path in route_info["all_paths"]:
                if not path or len(path) < 2:
                    continue

                for i in range(len(path) - 1):
                    u_node, v_node = path[i], path[i+1]
                    u_str, v_str = str(u_node), str(v_node)
                    pair_key = tuple(sorted([u_str, v_str]))

                    # Si ce pont n'est pas déjà affiché dans le maillage principal
                    if pair_key not in seen_pairs:
                        try:
                            analysis = uf.calculate_harmonic_pathway(u_node, v_node)
                            raw_pont_vl = analysis.get('voice_leading', [])
                            pont_vl = ", ".join(raw_pont_vl)
                        except:
                            pont_vl = "⇄"

                        if u_str not in [n["id"] for n in nodes_data]:
                            nodes_data.append({"id": u_str, "label": u_str, "group": u_str.split(" [")[0], "value": 11, "shape": "diamond"})
                        if v_str not in [n["id"] for n in nodes_data]:
                            nodes_data.append({"id": v_str, "label": v_str, "group": v_str.split(" [")[0], "value": 11, "shape": "diamond"})

                        edges_data.append({
                            "from": u_str,
                            "to": v_str,
                            "label": "",
                            "textFull": pont_vl,
                            "arrows": "",
                            "dashes": True,
                            "color": {"color": route_color}
                        })
                        # Note : on ne l'ajoute pas à seen_pairs ici pour permettre à deux routes alternatives
                        # de traverser le même pont si nécessaire sans s'effacer !

    return jsonify({
        "center": str(center_station),
        "nodes": nodes_data,
        "edges": edges_data
    })


if __name__ == '__main__':
    app.run(debug=True)