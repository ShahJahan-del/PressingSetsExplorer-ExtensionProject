import itertools

# =============================================================================
# 1. DATABASE AND GEOMETRICAL CONFIGURATION
# =============================================================================

# The 7 fundamental Pressing Sets (intervals relative to the root)
SET_STRUCTURES = {
    "Diatonic": [0, 2, 4, 5, 7, 9, 11],
    "Acoustic": [0, 2, 4, 6, 7, 9, 10],
    "Harmonic Minor": [0, 2, 3, 5, 7, 8, 11],
    "Harmonic Major": [0, 2, 4, 5, 7, 8, 11],
    "Whole Tone": [0, 2, 4, 6, 8, 10],
    "Octatonic": [0, 1, 3, 4, 6, 7, 9, 10],
    "Hexatonic": [0, 1, 4, 5, 8, 9]
}

NOTE_TO_INT = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
    'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
}

# 12 standardized display names for root sweep
ROOT_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

INT_TO_NOTE = {
    0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"
}


def get_absolute_pitches(set_name, root_note):
    """Calculates the set of absolute pitch-classes (0-11) for a given station."""
    intervals = SET_STRUCTURES[set_name]
    root_int = NOTE_TO_INT[root_note.strip()]
    return frozenset([(root_int + x) % 12 for x in intervals])

# =============================================================================
# 2. GENERATING THE UNIQUE STATIONS ATLAS
# =============================================================================

# We build the dictionary of all valid unique stations, accounting for symmetries
# (e.g., Whole Tone C and Whole Tone D are the same pitch-class set collection)
all_stations = {}
seen_pitch_collections = {}

for set_name in SET_STRUCTURES.keys():
    # Sweep numerically through the 12 semi-tones
    for root_int in range(12):
        note_letter = ROOT_NAMES[root_int]

        intervals = SET_STRUCTURES[set_name]
        absolute_pitches = frozenset([(root_int + x) % 12 for x in intervals])

        symmetry_key = (set_name, absolute_pitches)

        # Filter out geometric duplicates (symmetries) while retaining unique structural transpositions
        if symmetry_key not in seen_pitch_collections:
            station_name = f"{set_name} [{note_letter}]"
            all_stations[station_name] = absolute_pitches
            seen_pitch_collections[symmetry_key] = station_name

print(f"Topological universe initialized: {len(all_stations)} unique geometrical stations generated.")

# =============================================================================
# 3. TOPOLOGICAL ADJACENCY ENGINE
# =============================================================================

def generate_concentric_harmonic_network(source_name, max_layers=3, max_displaced_notes=1):
    """
    Explores the universe in concentric waves starting from a central station (Layer 0).
    Layer 1 contains direct neighbors, Layer 2 contains neighbors of neighbors, etc.
    Returns a dictionary of paths mapped by layers for easy graph building.
    """
    if source_name not in all_stations:
        return {}

    # Structure to hold our network layout
    network_by_layers = {0: [source_name]}
    visited = {source_name: 0} # Maps station -> layer index

    # To keep track of the physical edges (the train tracks) for the future visual graph
    connections = []

    for current_layer in range(max_layers):
        next_layer_stations = []
        current_stations = network_by_layers[current_layer]

        for current_st in current_stations:
            # Scan the entire universe to find valid outgoing steps
            for potential_next in all_stations.keys():
                if potential_next == current_st:
                    continue

                # Measure physical smoothness
                analysis = calculate_harmonic_pathway(current_st, potential_next)
                if len(analysis["voice_leading"]) <= max_displaced_notes:

                    # If we haven't discovered this station yet
                    if potential_next not in visited:
                        visited[potential_next] = current_layer + 1
                        next_layer_stations.append(potential_next)

                    # If this connection belongs to the next layer, log the track
                    if visited[potential_next] == current_layer + 1:
                        connections.append({
                            "from": current_st,
                            "to": potential_next,
                            "layer_from": current_layer,
                            "layer_to": current_layer + 1,
                            "trigger": analysis["voice_leading"]
                        })

        if not next_layer_stations:
            break # No more connected stations in the universe

        network_by_layers[current_layer + 1] = sorted(list(set(next_layer_stations)))

    return network_by_layers, connections

import networkx as nx
import matplotlib.pyplot as plt

def generate_complete_universe_graph(source_name, max_displaced_notes=1):
    """
    Explores the entire 57-station universe starting from a center.
    Uses the generalized cardinality-tolerant smoothness formula.
    """
    G = nx.DiGraph()
    G.add_node(source_name, layer=0)

    visited = {source_name: 0}
    queue = [source_name]

    while queue:
        current_st = queue.pop(0)
        current_layer = visited[current_st]

        for potential_next in all_stations.keys():
            if potential_next == current_st:
                continue

            src_pitches = all_stations[current_st]
            tgt_pitches = all_stations[potential_next]

            # Calculate common tones (pivots)
            pivots_count = len(src_pitches.intersection(tgt_pitches))

            # Generalized minimal displacement rule (Max pivots allowed)
            min_size = min(len(src_pitches), len(tgt_pitches))
            allowed_pivots = min_size - max_displaced_notes

            if pivots_count >= allowed_pivots:
                if potential_next not in visited:
                    visited[potential_next] = current_layer + 1
                    G.add_node(potential_next, layer=current_layer + 1)
                    queue.append(potential_next)

                if visited[potential_next] == current_layer + 1 or potential_next in visited:
                    G.add_edge(current_st, potential_next, weight=pivots_count)

    return G

def calculate_harmonic_pathway(source_name, target_name):
    """
    Analyzes the structural pathway between two stations.
    Maps out exact common tones and minimal voice-leading displacements.
    FORMATTED AS: (Note1, Note2 ⇄ TargetNote) (Points 1 & 2)
    """
    source_pitches = all_stations[source_name]
    target_pitches = all_stations[target_name]

    # Common tones (Pivots)
    common = source_pitches.intersection(target_pitches)
    pivots_list = [INT_TO_NOTE[n] for n in sorted(list(common))]

    # Notes that move
    departing_pitches = sorted(list(source_pitches - target_pitches))
    arriving_pitches = sorted(list(target_pitches - source_pitches))

    displacements = []

    # Si des notes bougent, on crée un seul tuple global ultra-propre
    if departing_pitches or arriving_pitches:
        deps_str = ", ".join([INT_TO_NOTE[p] for p in departing_pitches])
        arrs_str = ", ".join([INT_TO_NOTE[p] for p in arriving_pitches])

        # Gestion des cas particuliers (si un côté est vide lors d'un gros saut de cardinalité)
        if not deps_str: deps_str = "Ø"
        if not arrs_str: arrs_str = "Ø"

        displacements.append(f"({deps_str} ⇄ {arrs_str})")

    return {
        "pivots_count": len(common),
        "pivots": pivots_list,
        "voice_leading": displacements  # Renvoie par exemple ['(C#, Bb ⇄ B)']
    }

def scan_all_pathways(source_name, max_displaced_notes=2):
    """Finds all smooth pathways filtered by number of moving notes."""
    pathways = []
    for target_name in all_stations.keys():
        if target_name == source_name: continue

        analysis = calculate_harmonic_pathway(source_name, target_name)
        if len(analysis["voice_leading"]) <= max_displaced_notes:
            pathways.append({
                "target": target_name,
                "pivots_count": analysis["pivots_count"],
                "pivots": analysis["pivots"],
                "voice_leading": analysis["voice_leading"]
            })
    # Sort with the smoothest transitions first
    pathways.sort(key=lambda x: len(x["voice_leading"]))
    return pathways

# =============================================================================
# 4. EXECUTION DEMO / UNIT TEST
# =============================================================================

from pyvis.network import Network

if __name__ == "__main__":
    center_station = "Diatonic [C]"

    # 1. We keep max_displaced_notes=1 to see the absolute purest single-semitone tracks
    # Change to =2 if you want to discover the remaining "isolated islands" of the universe!
    max_step_distance = 1

    print(f"🔮 Generating the complete universe graph from center: {center_station}...")
    G = generate_complete_universe_graph(center_station, max_displaced_notes=max_step_distance)

    # 2. Initialize PyVis Interactive Network
    # We use a dark theme similar to your app screenshots for better visibility
    net = Network(height="850px", width="100%", bgcolor="#222222", font_color="white", directed=True)

    # 3. Add Nodes with Custom Colors, Sizes and Tooltips
    for node in G.nodes():
        # Visual color coding for each harmonic world
        if "Diatonic" in node: color = "#1f77b4"
        elif "Acoustic" in node: color = "#d62728"
        elif "Harmonic Minor" in node: color = "#bcbd22"
        elif "Harmonic Major" in node: color = "#9467bd"
        elif "Whole Tone" in node: color = "#ff7f0e"
        elif "Octatonic" in node: color = "#2ca02c"
        else: color = "#7f7f7f"

        # Make the center station look like a massive main hub
        size = 40 if node == center_station else 15
        border_width = 4 if node == center_station else 1

        # Text display: inside the bubble and upon hovering (tooltip)
        display_label = node.replace(" ", "\n")
        absolute_notes = list(all_stations[node])
        absolute_notes_letters = [INT_TO_NOTE[n] for n in sorted(absolute_notes)]
        hover_info = f"Station: {node}\nPitches: {', '.join(absolute_notes_letters)}"

        net.add_node(node, label=display_label, title=hover_info, color=color, size=size, borderWidth=border_width)

    # 4. Add Edges with Real-Time Voice-Leading Data
    for source, target in G.edges():
        # Calculate the exact voice leading triggers to put on the track line
        analysis = calculate_harmonic_pathway(source, target)
        vl_label = ", ".join(analysis["voice_leading"])
        pivots_label = ", ".join(analysis["pivots"])

        # Tooltip when mouse hovers over the connection line
        edge_hover = f"Voice-Leading: {vl_label}\nCommon Tones: {pivots_label}"

        net.add_edge(source, target, label=vl_label, title=edge_hover, color="#555555", width=1, arrowStrikethrough=False)

    # 5. Physics configuration to allow smooth scrolling and node dragging without chaos
    net.set_options("""
    var options = {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -4000,
          "centralGravity": 0.3,
          "springLength": 150,
          "springConstant": 0.04
        },
        "minVelocity": 0.75
      }
    }
    """)

    # 6. Save and Launch in your default web browser
    output_html = "debussy_universe_graph.html"
    print(f"✅ Interactive map compiled into '{output_html}'!")
    print("🚀 Opening your browser... Drag nodes around to disentangle the paths!")
    net.show(output_html, notebook=False)
    pyvis_options = {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -10000,
                "centralGravity": 0.1,
                "springLength": 250,
                "springConstant": 0.02
            },
            "minVelocity": 0.75
        }
    }
    net.options.update(pyvis_options)