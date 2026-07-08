import networkx as nx
from collections import deque
import utility_functions as uf

def build_piece_harmonic_graph(center_station, active_set_list, max_step_distance=1):
    """
    Builds a localized graph restricted ONLY to the pitch sets present in the piece.
    Maps out the smoothest pathways back to the chosen macro-harmonic center.
    """
    # Safeguard against spelling discrepancies (e.g., user inputs Db but atlas registered C#)
    ENHARMONIC_MAP = {
        "C#": "C#", "Db": "C#", "D#": "Eb", "Eb": "Eb",
        "G#": "Ab", "Ab": "Ab", "A#": "Bb", "Bb": "Bb", "F#": "F#", "Gb": "F#"
    }

    def normalize_name(name):
        try:
            # We split from the right side of '[' to isolate the full set type name
            set_type = name.split('[')[0].strip()
            root = name.split('[')[1].split(']')[0].strip()
            clean_root = ENHARMONIC_MAP.get(root, root)
            return f"{set_type} [{clean_root}]"
        except:
            return name

    clean_center = normalize_name(center_station)
    clean_active_list = [normalize_name(s) for s in active_set_list]

    if clean_center not in clean_active_list:
        clean_active_list.append(clean_center)

    # Infrastructure check
    for s in clean_active_list:
        if s not in uf.all_stations:
            print(f"⚠️ Error: '{s}' is not a valid station in the 57-set atlas.")
            return None

    # Graph Initialization
    G = nx.DiGraph()
    for station in clean_active_list:
        G.add_node(station, layer=None)

    G.nodes[clean_center]['layer'] = 0
    queue = deque([clean_center])
    visited = {clean_center: 0}

    # --- REPLACE THE WHILE LOOP INSIDE build_piece_harmonic_graph (piece_analyzer.py) ---
    while queue:
        current_st = queue.popleft()
        current_layer = visited[current_st]

        for potential_next in clean_active_list:
            if potential_next == current_st:
                continue

            src_pitches = uf.all_stations[current_st]
            tgt_pitches = uf.all_stations[potential_next]

            pivots_count = len(src_pitches.intersection(tgt_pitches))
            min_size = min(len(src_pitches), len(tgt_pitches))

            # We strictly mirror the universal rule from utility_functions
            if pivots_count >= (min_size - max_step_distance):
                if potential_next not in visited:
                    visited[potential_next] = current_layer + 1
                    G.nodes[potential_next]['layer'] = current_layer + 1
                    queue.append(potential_next)

                if visited[potential_next] == current_layer + 1 or potential_next in visited:
                    analysis = uf.calculate_harmonic_pathway(current_st, potential_next)
                    G.add_edge(current_st, potential_next,
                               voice_leading=analysis["voice_leading"],
                               pivots=analysis["pivots"])

    return G

# --- CONCEPTUAL LOGIC TO IMPLEMENT IN PIECE_ANALYZER ---

def resolve_isolated_archipelagos(isolated_nodes, connected_nodes, global_graph):
    """
    1. Computes absolute shortest paths from center for all isolated nodes.
    2. Checks internal proximity between isolated nodes to form 'archipelagos'.
    3. Finds the optimal 'bridgehead' (entry point) to connect the archipelago.
    4. Compares with regional shortcuts from any already connected node.
    """
    # Create a local graph of connections ONLY between isolated nodes
    archipelago_graph = nx.Graph()
    for n1 in isolated_nodes:
        archipelago_graph.add_node(n1)
        for n2 in isolated_nodes:
            if n1 != n2:
                # Check if they are micro-neighbors (distance 1) in the global map
                if global_graph.has_edge(n1, n2) or global_graph.has_edge(n2, n1):
                    archipelago_graph.add_edge(n1, n2)

    # Extract isolated groups (e.g., ['Diatonic [F#]', 'Diatonic [C#]'])
    sub_clusters = list(nx.connected_components(archipelago_graph))

    # For each cluster, we determine the best entry point from the "mainland"
    for cluster in sub_clusters:
        best_entry_on_mainland = None
        best_target_in_cluster = None
        min_total_cost = 999

        # Test every entry point from the piece's connected nodes to any node in the cluster
        for mainland_node in connected_nodes:
            for cluster_node in cluster:
                try:
                    path = nx.shortest_path(global_graph, source=mainland_node, target=cluster_node)
                    cost = len(path) - 1
                    if cost < min_total_cost:
                        min_total_cost = cost
                        best_entry_on_mainland = mainland_node
                        best_target_in_cluster = cluster_node
                except nx.NetworkXNoPath:
                    continue

        # NOW WE COMPARE:
        # If min_total_cost to the cluster checkpoint is smaller than the absolute path from center,
        # or if it's equal but anchors to a more significant local cluster, we branch from there!

def print_analytical_report(G, center_station):
    """
    Outputs a text map of the connected harmonic layers, then executes a
    dual-pass pathfinding engine. Renders ALL tied shortest paths (Point 8).
    """
    print(f"\n🎼 --- HARMONIC ANALYSIS REPORT (Center: {center_station}) ---")

    unreached = []
    nodes_by_layer = {}

    # Sort connected nodes by their discovery layer
    for node in G.nodes():
        layer = G.nodes[node]['layer']
        if layer is None:
            unreached.append(node)
        else:
            if layer not in nodes_by_layer:
                nodes_by_layer[layer] = []
            nodes_by_layer[layer].append(node)

    # Display the structured mainland network
    for layer in sorted(nodes_by_layer.keys()):
        print(f"\n🔹 DISTANCE LAYER {layer}")
        for node in nodes_by_layer[layer]:
            print(f"  ├── [{node}]")
            incoming_edges = G.in_edges(node, data=True)
            for u, v, data in incoming_edges:
                vl_str = ", ".join(data['voice_leading'])
                print(f"  │    └── Connected from [{u}] via ({vl_str})")

    # -------------------------------------------------------------------------
    # ADVANCED PATHFINDING FOR ISOLATED ARCHIPELAGOS (MULTIPLE PATHS FIX - Point 8)
    # -------------------------------------------------------------------------
    reconstructed_routes_data = {}

    if unreached:
        print("\n🛑 ISOLATED SETS & RECONSTRUCTED ECO-PATHWAYS:")

        # 1. Generate the master universe map (57 stations)
        global_universe = uf.generate_complete_universe_graph(center_station, max_displaced_notes=1)
        mainland_nodes = [n for n in G.nodes() if G.nodes[n]['layer'] is not None]

        # 2. Compute baseline routes supporting multiple equal paths
        for node in unreached:
            best_anchor = center_station

            # Récupération de TOUS les chemins les plus courts ex-æquo
            all_paths = list(nx.all_shortest_paths(global_universe, source=center_station, target=node))
            best_cost = len(all_paths[0]) - 1

            # Check if branching from another connected node offers shorter paths
            for anchor in mainland_nodes:
                try:
                    paths = list(nx.all_shortest_paths(global_universe, source=anchor, target=node))
                    cost = len(paths[0]) - 1
                    if cost < best_cost:
                        best_cost = cost
                        all_paths = paths
                        best_anchor = anchor
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

            # On prend la première route stable comme principale pour l'affichage console,
            # mais on sauvegarde la structure complète pour l'API graphique.
            chosen_path = all_paths[0]

            print(f"  ├── [{node}] (Trouvé {len(all_paths)} routes optimales ex-æquo)")

            reconstructed_routes_data[node] = {
                "path": chosen_path,
                "all_paths": all_paths, # On transmet la liste de TOUTES les variantes ex-æquo
                "cost": best_cost,
                "anchor": best_anchor
            }

    return reconstructed_routes_data


if __name__ == "__main__":
    ravel_center = "Diatonic [D]"
    ravel_piece_sets = [
        "Diatonic [D]",
        "Octatonic [C]",
        "Acoustic [C]",
        "Acoustic [Eb]",
        "Diatonic [G]",
        "Diatonic [A]",
        "Diatonic [F#]",
        "Diatonic [C#]",
        "Harmonic Minor [B]"
    ]

    print("⏳ Analyzing piece vector macro-harmonics...")
    analysis_graph = build_piece_harmonic_graph(ravel_center, ravel_piece_sets, max_step_distance=1)

    if analysis_graph:
        print_analytical_report(analysis_graph, ravel_center)

