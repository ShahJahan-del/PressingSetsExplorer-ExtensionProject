document.addEventListener('DOMContentLoaded', () => {
    const setTypeSelect = document.getElementById('set-type-select');
    const rootSelect = document.getElementById('root-select');
    const distanceSelect = document.getElementById('distance-select');
    let network = null;

    setTypeSelect.addEventListener('change', () => {
        rootSelect.disabled = false;
        triggerSearch();
    });

    rootSelect.addEventListener('change', triggerSearch);
    distanceSelect.addEventListener('change', triggerSearch);

    function triggerSearch() {
        const type = setTypeSelect.value;
        const root = rootSelect.value;

        if (type && root) {
            updateExploration(type, root, distanceSelect.value);
        }
    }

    async function updateExploration(type, root, distance) {
        const response = await fetch(`/api/explore?type=${encodeURIComponent(type)}&root=${encodeURIComponent(root)}&distance=${distance}`);
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        // 1. Allumage des touches du piano
        document.querySelectorAll('.key').forEach(key => key.classList.remove('active'));
        data.pitches.forEach(pitch => {
            const key = document.querySelector(`.key[data-note="${pitch}"]`);
            if (key) key.classList.add('active');
        });

        // 2. Génération visuelle du Graphe
        const container = document.getElementById('network-container');

        const graphData = {
            nodes: new vis.DataSet(data.nodes),
            edges: new vis.DataSet(data.edges)
        };

        const options = {
            nodes: {
                shape: 'dot',
                font: { color: '#ffffff', size: 13, face: 'Segoe UI' },
                shadow: { enabled: true, color: 'rgba(0,0,0,0.3)', size: 5 }
            },
            edges: {
                color: { color: '#475569', highlight: '#4ea8de', hover: '#4ea8de' },
                smooth: { type: 'continuous', roundness: 0.4 },
                width: 2,
                hoverWidth: 3,
                font: {
                    color: '#56cfe1',
                    size: 11,
                    background: '#12161a',
                    face: 'Segoe UI',
                    align: 'middle' // Aligné pile au milieu de la ligne
                }
            },
            groups: {
                "Diatonic": { color: { background: '#1d4ed8', border: '#3b82f6' } },
                "Acoustic": { color: { background: '#0d9488', border: '#14b8a6' } },
                "Octatonic": { color: { background: '#b91c1c', border: '#ef4444' } },
                "Whole Tone": { color: { background: '#6d28d9', border: '#8b5cf6' } },
                "Hexatonic": { color: { background: '#be185d', border: '#ec4899' } },
                "Harmonic Minor": { color: { background: '#c2410c', border: '#f97316' } },
                "Harmonic Major": { color: { background: '#a16207', border: '#eab308' } }
            },
            physics: {
                solver: 'forceAtlas2Based',
                forceAtlas2Based: { gravitationalConstant: -150, centralGravity: 0.02, springLength: 100, springConstant: 0.08 },
                stabilization: { iterations: 150 }
            },
            interaction: { hover: true }
        };

        if (network !== null) {
            network.destroy();
        }
        network = new vis.Network(container, graphData, options);

        // --- REMPLACE UNIQUEMENT LES ÉCOUTEURS HOVER/BLUR À LA FIN DE static/js/main.js ---

        // Au survol : on injecte le texte au milieu de la ligne
        network.on("hoverEdge", function (params) {
            const edgeId = params.edge;
            const edgeData = graphData.edges.get(edgeId);

            if (edgeData && edgeData.textFull) {
                graphData.edges.update({
                    id: edgeId,
                    label: edgeData.textFull,
                    font: {
                        color: '#56cfe1',
                        size: 11,
                        background: '#12161a',
                        face: 'Segoe UI'
                    }
                });
            }
        });

        // Quand la souris quitte la ligne : EFFACEMENT TOTAL ET GARANTI
        network.on("blurEdge", function (params) {
            const edgeId = params.edge;
            graphData.edges.update({
                id: edgeId,
                label: "", // On vide le texte
                // On force la police à devenir transparente et invisible pour vider le cache de Vis.js
                font: {
                    color: 'rgba(0,0,0,0)',
                    background: 'rgba(0,0,0,0)',
                    size: 0
                }
            });
        });

        // Double-clic pour recentrer
        network.on("doubleClick", function (params) {
            if (params.nodes.length > 0) {
                const clickedNode = params.nodes[0];
                const match = clickedNode.match(/^([a-zA-Z\s]+)\s\[([A-G#b]+)\]$/);
                if (match) {
                    setTypeSelect.value = match[1];
                    rootSelect.value = match[2];
                    updateExploration(match[1], match[2], distanceSelect.value);
                }
            }
        });
    }
});