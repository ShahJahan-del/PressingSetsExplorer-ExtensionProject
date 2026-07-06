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
    dual-pass pathfinding engine (Absolute vs. Mainland vs. Archipelago Relative)
    to reconstruct the optimal pathways for isolated sets.
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
    # ADVANCED PATHFINDING FOR ISOLATED ARCHIPELAGOS
    # -------------------------------------------------------------------------
    if unreached:
        print("\n🛑 ISOLATED SETS & RECONSTRUCTED ECO-PATHWAYS (Multi-Pass Optimization):")

        # 1. Generate the master universe map (57 stations)
        global_universe = uf.generate_complete_universe_graph(center_station, max_displaced_notes=1)
        mainland_nodes = [n for n in G.nodes() if G.nodes[n]['layer'] is not None]

        # 2. First Pass: Compute the absolute/mainland baseline for each isolated node
        baseline_routes = {}
        for node in unreached:
            best_anchor = center_station
            best_path = nx.shortest_path(global_universe, source=center_station, target=node)
            best_cost = len(best_path) - 1

            # Check if branching from another connected node is shorter
            for anchor in mainland_nodes:
                try:
                    path = nx.shortest_path(global_universe, source=anchor, target=node)
                    cost = len(path) - 1
                    if cost < best_cost:
                        best_cost = cost
                        best_path = path
                        best_anchor = anchor
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

            baseline_routes[node] = {
                "path": best_path,
                "cost": best_cost,
                "anchor": best_anchor,
                "is_relative": False
            }

        # 3. Second Pass: Scan isolated pairs to detect proximity clusters (Archipelagos)
        # We build a local graph of the isolated nodes to find internal components
        isolated_subgraph = nx.Graph()
        isolated_subgraph.add_nodes_from(unreached)

        for n1 in unreached:
            for n2 in unreached:
                if n1 != n2:
                    # If they are distance-1 neighbors in the global universe, bridge them
                    if global_universe.has_edge(n1, n2) or global_universe.has_edge(n2, n1):
                        isolated_subgraph.add_edge(n1, n2)

        archipelagos = list(nx.connected_components(isolated_subgraph))

        # 4. Third Pass: Optimize pathways within each archipelago
        final_routes = baseline_routes.copy()

        for archipelago in archipelagos:
            if len(archipelago) < 2:
                continue  # Skip truly solo isolated islands, baseline is already optimal

            # Find the best entry point (bridgehead) for the whole group
            best_bridgehead = None
            min_entry_cost = 999

            for node in archipelago:
                if baseline_routes[node]["cost"] < min_entry_cost:
                    min_entry_cost = baseline_routes[node]["cost"]
                    best_bridgehead = node

            # Rewrite routes for the other members of this archipelago to branch through the bridgehead
            for node in archipelago:
                if node == best_bridgehead:
                    continue  # The entry point keeps its optimal baseline route

                # Compute the internal relative shortcut within the archipelago
                relative_path = nx.shortest_path(global_universe, source=best_bridgehead, target=node)
                relative_cost = len(relative_path) - 1

                # If the local jump is tighter than building a whole route from the center, we pivot!
                if relative_cost < baseline_routes[node]["cost"]:
                    final_routes[node] = {
                        "path": relative_path,
                        "cost": relative_cost,
                        "anchor": best_bridgehead,
                        "is_relative": True
                    }

        # 5. Final Output Render with Voice-Leading calculations
        reconstructed_routes_data = {} # Pour l'API Web

        for node in unreached:
            route_data = final_routes[node]
            path_nodes = route_data["path"]

            # Reconstruct step-by-step voice leading along the computed path
            vl_steps = []
            for i in range(len(path_nodes) - 1):
                analysis = uf.calculate_harmonic_pathway(path_nodes[i], path_nodes[i+1])
                vl_label = ", ".join(analysis["voice_leading"])
                vl_steps.append(f"({vl_label})")

            # Format display string by interlacing nodes and their triggers
            steps_display = f"[{path_nodes[0]}]"
            for i in range(len(vl_steps)):
                steps_display += f" -> {vl_steps[i]} -> [{path_nodes[i+1]}]"

            print(f"  ├── [{node}]")
            if route_data["is_relative"]:
                print(f"  │    └── 🗺️ Relative Archipelago Route: {steps_display} ({route_data['cost']} local step(s))")
            else:
                print(f"  │    └── 🗺️ Absolute Mainland Route: {steps_display} ({route_data['cost']} global step(s))")

            # Sauvegarde des données utiles pour l'affichage graphique
            reconstructed_routes_data[node] = {
                "path": path_nodes,
                "is_relative": route_data["is_relative"],
                "cost": route_data["cost"]
            }

        return reconstructed_routes_data
    return {}


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

