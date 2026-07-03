document.addEventListener('DOMContentLoaded', () => {
    const setTypeSelect = document.getElementById('set-type-select');
    const rootSelect = document.getElementById('root-select');
    const distanceSelect = document.getElementById('distance-select');
    let network = null;
    let isAutomaticUpdate = false;
    const noteMap = {
        "0": "C", "1": "C#", "2": "D", "3": "D#", "4": "E", "5": "F",
        "6": "F#", "7": "G", "8": "G#", "9": "A", "10": "A#", "11": "B"
    };

    // Les 12 transpositions chromatiques standard affichées pour l'utilisateur
    const standardRoots = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

    // Les transpositions limitées mappées sur les vraies clés de ton dictionnaire Python
    const symmetricRoots = {
        "Octatonic": [
            { value: "C", text: "Oct(0,1)" },
            { value: "C#", text: "Oct(1,2)" },
            { value: "D", text: "Oct(2,3)" }
        ],
        "Whole Tone": [
            { value: "C", text: "WT0" },
            { value: "C#", text: "WT1" }
        ],
        "Hexatonic": [
            { value: "C", text: "Hex(0,1)" },
            { value: "C#", text: "Hex(1,2)" },
            { value: "D", text: "Hex(2,3)" },
            { value: "Eb", text: "Hex(3,4)" }
        ]
    };

    // Liste des modes pour chaque famille asymétrique (ordonnés par degré)
    const familyModes = {
        "Diatonic": ["Major/Ionian", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Aeolian", "Locrian"],
        "Acoustic": ["Acoustic (Lydian b7)", "Major Locrian", "Altered b6", "Melodic Minor", "Dorian b2", "Lydian Augmented", "Bartok/Lydian Dominant"],
        "Harmonic Minor": ["Harmonic Minor", "Locrian ♮6", "Ionian ♯5", "Dorian ♯4", "Phrygian Dominant", "Lydian ♯2", "Ultralocrian"],
        "Harmonic Major": ["Harmonic Major", "Dorian b5", "Phrygian b4", "Lydian b3", "Mixolydian b2", "Lydian Augmented ♯2", "Locrian bb7"]
    };

    // Injecte dynamiquement les bonnes options de transposition dans le menu déroulant
    function updateRootOptions(setType) {
        rootSelect.innerHTML = '<option value="" disabled selected>-- Transposition --</option>';

        if (symmetricRoots[setType]) {
            symmetricRoots[setType].forEach(root => {
                const opt = document.createElement('option');
                opt.value = root.value;
                opt.textContent = root.text;
                rootSelect.appendChild(opt);
            });
        } else {
            standardRoots.forEach(note => {
                const opt = document.createElement('option');
                opt.value = note;
                opt.textContent = note;
                rootSelect.appendChild(opt);
            });
        }
    }

    setTypeSelect.addEventListener('change', () => {
        if (isAutomaticUpdate) return;
        updateRootOptions(setTypeSelect.value);
        rootSelect.disabled = false;
        triggerSearch();
    });

    rootSelect.addEventListener('change', () => {
        if (isAutomaticUpdate) return;
        triggerSearch();
    });

    distanceSelect.addEventListener('change', () => {
        if (isAutomaticUpdate) return;
        triggerSearch();
    });

    function triggerSearch() {
        const type = setTypeSelect.value;
        const root = rootSelect.value;

        if (type && root) {
            updateExploration(type, root, distanceSelect.value);
        }
    }

    // À AJOUTER APRÈS LA FONCTION triggerSearch() :
    document.querySelectorAll('.key').forEach(key => {
        key.addEventListener('click', () => {
            // Si on était en mode "Mise à jour automatique", on ignore le clic parasite
            if (isAutomaticUpdate) return;

            key.classList.toggle('active');

            // Traduction des touches actives en vraies notes textuelles
            const activePitches = Array.from(document.querySelectorAll('.key.active'))
                                       .map(k => noteMap[k.getAttribute('data-note')]);

            // MODIFICATION DANS L'ÉCOUTEUR DE CLIC DU PIANO :
            if (activePitches.length >= 3) {
                isAutomaticUpdate = true;
                setTypeSelect.value = "";
                rootSelect.value = "";
                rootSelect.disabled = true;
                isAutomaticUpdate = false;

                fetch('/api/identify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pitches: activePitches })
                })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('keyboard-matches-container').style.display = 'block';
                    displayKeyboardMatches(data.matches);
                });
            } else if (activePitches.length > 0 && activePitches.length < 3) {
                const matchesContainer = document.getElementById('keyboard-matches-container');
                const matchesList = document.getElementById('matches-list');
                const matchCountSpan = document.getElementById('match-count');

                matchCountSpan.innerText = "0";
                matchesList.innerHTML = '<li style="color: #64748b; padding: 5px; font-style: italic;">Veuillez sélectionner au moins 3 notes pour identifier les collections parentes.</li>';
                matchesContainer.style.display = 'block';
            } else {
                document.getElementById('keyboard-matches-container').style.display = 'none';
            }
        });
    });

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
            // L'API renvoyant des chiffres, on cible directement l'attribut data-note
            const keyEl = document.querySelector(`.key[data-note="${pitch}"]`);
            if (keyEl) keyEl.classList.add('active');
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
                    color: 'rgba(0,0,0,0)',
                    size: 0,
                    background: 'rgba(0,0,0,0)',
                    face: 'Segoe UI',
                    align: 'middle'
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
                const match = clickedNode.match(/^([a-zA-Z\s]+)\s\[([A-G#b0-9,]+)\]$/);
                if (match) {
                    let family = match[1];
                    let root = match[2];

                    // Traduction inverse Bémol -> Dièse pour forcer la synchronisation de l'IHM
                    const flatToSharp = { "Eb": "D#", "Ab": "G#", "Bb": "A#" };
                    if (flatToSharp[root]) {
                        root = flatToSharp[root];
                    }

                    isAutomaticUpdate = true;
                    setTypeSelect.value = family;
                    updateRootOptions(family); // Régénère le bon set d'options (standards ou limitées)
                    rootSelect.disabled = false;
                    rootSelect.value = root;
                    isAutomaticUpdate = false;

                    updateExploration(family, root, distanceSelect.value);
                }
            }
        });

        // Déclenche l'affichage du panneau des modes correspondant au choix actuel
        displayCollectionModes(type, root);
    }

    function displayKeyboardMatches(matches) {
        const matchesContainer = document.getElementById('keyboard-matches-container');
        const matchesList = document.getElementById('matches-list');
        const matchCountSpan = document.getElementById('match-count');

        matchesList.innerHTML = '';
        if (matches.length === 0) {
            matchesList.innerHTML = '<li style="color: #64748b; padding: 5px;">Aucun set ne contient toutes ces notes simultanément.</li>';
            matchCountSpan.innerText = "0";
            matchesContainer.style.display = 'block';
            return;
        }

        matchCountSpan.innerText = matches.length;

        matches.forEach(m => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.alignItems = 'center';
            li.style.marginBottom = '8px';
            li.style.fontFamily = 'Segoe UI, sans-serif';
            li.style.color = '#94a3b8';

            const missingText = m.missing.length > 0 ? `— missing ${m.missing.join(', ')}` : '— Complet ! Exact Match !';

            li.innerHTML = `
                <span style="margin-right: 10px;">• Subset of</span>
                <button class="match-btn" data-family="${m.family}" data-root="${m.root}" style="
                    background-color: #84cc16;
                    color: #ffffff;
                    border: none;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 13px;">
                    ${m.station_name}
                </button>
                <span style="margin-left: 10px; font-size: 13px; color: #64748b;">${missingText}</span>
            `;
            matchesList.appendChild(li);
        });

        // Écouteur des boutons de la liste
        document.querySelectorAll('.match-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const family = btn.getAttribute('data-family');
                let root = btn.getAttribute('data-root');

                // Traduction inverse Bémol -> Dièse pour forcer la synchronisation de l'IHM
                const flatToSharp = { "Eb": "D#", "Ab": "G#", "Bb": "A#" };
                if (flatToSharp[root]) {
                    root = flatToSharp[root];
                }

                isAutomaticUpdate = true;
                setTypeSelect.value = family;
                updateRootOptions(family); // Régénère les transpositions adaptées
                rootSelect.disabled = false;
                rootSelect.value = root;
                isAutomaticUpdate = false;

                matchesContainer.style.display = 'none';

                updateExploration(family, root, distanceSelect.value);
                displayCollectionModes(family, root); // Force la mise à jour des modes
            });
        });

        matchesContainer.style.display = 'block';
    }

function displayCollectionModes(family, root) {
        const container = document.getElementById('collection-modes-container');
        const badgeDiv = document.getElementById('selected-collection-badge');
        const modesList = document.getElementById('modes-list');

        // 1. Affichage du Badge Vert de la collection
        // Traduction visuelle si c'est un set symétrique pour l'affichage du badge
        let shortName = root;
        if (["Octatonic", "Whole Tone", "Hexatonic"].includes(family)) {
            const symNames = { "C": "0,1", "C#": "1,2", "D": "2,3", "Eb": "3,4" };
            shortName = symNames[root] || root;
        }

        badgeDiv.innerHTML = `
            <span style="background-color: #84cc16; color: #ffffff; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                ${shortName} ${family.substring(0, 3).toUpperCase()}
            </span>
            <span style="color: #64748b; margin-left: 10px; font-size: 14px;">(${root} ${family})</span>
        `;

        // 2. Génération de la liste des modes
        modesList.innerHTML = '';

        if (familyModes[family]) {
            // C'est un set asymétrique : on boucle sur ses modes
            familyModes[family].forEach((modeName, index) => {
                const li = document.createElement('li');
                li.style.display = 'flex';
                li.style.justifyContent = 'space-between';
                li.style.alignItems = 'center';
                li.style.marginBottom = '10px';
                li.style.color = '#94a3b8';
                li.style.fontSize = '14px';

                li.innerHTML = `
                    <span><span style="color: #475569; margin-right: 8px;">▪</span> ${modeName}</span>
                    <button class="play-mode-btn" data-degree="${index}" style="
                        background-color: #ffffff;
                        color: #0f172a;
                        border: 1px solid #cbd5e1;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-weight: 500;
                        cursor: pointer;
                        font-size: 12px;
                        transition: all 0.2s;">
                        PLAY THIS MODE
                    </button>
                `;
                modesList.appendChild(li);
            });
        } else {
            // C'est un set symétrique (Octatonic, Whole Tone, Hexatonic)
            const li = document.createElement('li');
            li.style.color = '#64748b';
            li.style.fontStyle = 'italic';
            li.style.padding = '10px 0';
            li.innerText = "Cette collection est symétrique (à transpositions limitées) et ne possède pas de modes distincts exploitables de manière diatonique.";
            modesList.appendChild(li);
        }

        // Rendre le conteneur visible
        container.style.display = 'block';
    }
});

