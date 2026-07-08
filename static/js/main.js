document.addEventListener('DOMContentLoaded', () => {
    const setTypeSelect = document.getElementById('set-type-select');
    const rootSelect = document.getElementById('root-select');
    const distanceSelect = document.getElementById('distance-select');

    // =========================================================================
    // VARIABLES ET CONFIGURATIONS GLOBALES DES 3 RÉSEAUX PERSISTANTS (Point 9)
    // =========================================================================
    let networkExplore = null;
    let networkAnalyze = null;
    let networkCompose = null;
    let currentMode = 'exploration';
    let isAutomaticUpdate = false;

    // Configuration visuelle unifiée pour Vis.js
    const globalOptions = {
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

    // =========================================================================
    // FONCTIONS DE DESSIN PERSISTANTES PAR ONGLET (Isolation complète)
    // =========================================================================

    const symmetricLabels = {
        "Octatonic [C]": "Octatonic [0,1]",
        "Octatonic [C#]": "Octatonic [1,2]",
        "Octatonic [Db]": "Octatonic [1,2]",
        "Octatonic [D]": "Octatonic [2,3]",
        "Whole Tone [C]": "Whole Tone [0]",
        "Whole Tone [C#]": "Whole Tone [1]",
        "Whole Tone [Db]": "Whole Tone [1]",
        "Hexatonic [C]": "Hexatonic [0,1]",
        "Hexatonic [C#]": "Hexatonic [1,2]",
        "Hexatonic [Db]": "Hexatonic [1,2]",
        "Hexatonic [D]": "Hexatonic [2,3]",
        "Hexatonic [Eb]": "Hexatonic [3,4]"
    };

    // Nettoie et harmonise les textes affichés sur les nœuds du graphe
    function cleanNodeLabel(label) {
        if (!label) return label;

        // 1. Convertit les dièses résiduels en bémols pour le visuel
        const sharpToFlatNodes = { "C#": "Db", "D#": "Eb", "G#": "Ab", "A#": "Bb" };
        let cleaned = label;
        Object.keys(sharpToFlatNodes).forEach(sharp => {
            if (cleaned.includes(`[${sharp}]`)) {
                cleaned = cleaned.replace(`[${sharp}]`, `[${sharpToFlatNodes[sharp]}]`);
            }
        });

        // 2. Remplace par le code de transposition symétrique compact si existant
        if (symmetricLabels[cleaned]) {
            return symmetricLabels[cleaned];
        }
        return cleaned;
    }

    function drawExplorationGraph(data) {
        const container = document.getElementById('network-explore-container');
        const harmonizedNodes = data.nodes.map(node => {
            let newNode = { ...node };
            newNode.label = cleanNodeLabel(newNode.label); // Applique le formatage harmonisé sur le texte visible
            return newNode;
        });

        // Les données passées à Vis.js utilisent les labels nettoyés mais gardent les edges/ids originaux intacts
        const graphData = {
            nodes: new vis.DataSet(harmonizedNodes),
            edges: new vis.DataSet(data.edges)
        };

        // On recrée l'instance uniquement pour l'exploration sans toucher aux autres onglets
        networkExplore = new vis.Network(container, graphData, globalOptions);

        // Au survol : on injecte le texte au milieu de la ligne
        networkExplore.on("hoverEdge", function (params) {
            const edgeId = params.edge;
            const edgeData = graphData.edges.get(edgeId);
            if (edgeData && edgeData.textFull) {
                graphData.edges.update({
                    id: edgeId,
                    label: edgeData.textFull,
                    font: { color: '#56cfe1', size: 11, background: '#12161a', face: 'Segoe UI' }
                });
            }
        });

        // Quand la souris quitte la ligne : EFFACEMENT TOTAL ET GARANTI
        networkExplore.on("blurEdge", function (params) {
            graphData.edges.update({
                id: params.edge,
                label: "", // On vide le texte
                // On force la police à devenir transparente et invisible pour vider le cache de Vis.js
                font: { color: 'rgba(0,0,0,0)', background: 'rgba(0,0,0,0)', size: 0 }
            });
        });

        // Double-clic pour recentrer (Point 10)
        networkExplore.on("doubleClick", function (params) {
            if (params.nodes.length > 0) {
                const clickedNode = params.nodes[0];
                const match = clickedNode.match(/^([a-zA-Z\s]+)\s\[([A-G#b0-9,]+)\]$/);
                if (match) {
                    let family = match[1];
                    let root = match[2];

                    // Traduction inverse Dièse -> Bémol pour forcer la synchronisation stricte de l'IHM (Point 4)
                    const sharpToFlat = { "D#": "Eb", "G#": "Ab", "A#": "Bb", "C#": "Db" };
                    if (sharpToFlat[root]) root = sharpToFlat[root];

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
    }

    function drawAnalysisGraph(data) {
        const container = document.getElementById('network-analyze-container');
        const harmonizedNodes = data.nodes.map(node => {
            let newNode = { ...node };
            newNode.label = cleanNodeLabel(newNode.label); // Harmonise aussi les stations du morceau
            return newNode;
        });

        const graphData = {
            nodes: new vis.DataSet(harmonizedNodes),
            edges: new vis.DataSet(data.edges)
        };

        // Configuration légèrement modifiée pour l'analyse (arêtes plus fines pour lisibilité)
        const analysisOptions = JSON.parse(JSON.stringify(globalOptions));
        analysisOptions.edges.width = 1.2;

        networkAnalyze = new vis.Network(container, graphData, analysisOptions);

        // Affichage du Voice leading au survol des chemins du morceau
        networkAnalyze.on("hoverEdge", function (p) {
            const eId = p.edge;
            const eData = graphData.edges.get(eId);
            if (eData && eData.textFull) {
                graphData.edges.update({
                    id: eId,
                    label: eData.textFull,
                    font: { color: '#56cfe1', size: 11, background: '#12161a', face: 'Segoe UI' }
                });
            }
        });

        networkAnalyze.on("blurEdge", function (p) {
            graphData.edges.update({
                id: p.edge,
                label: "",
                font: { color: 'rgba(0,0,0,0)', size: 0 }
            });
        });
    }

    // =========================================================================
    // LOGIQUE DIATONIQUE / SYMETRIQUE (SÉLECTEURS)
    // =========================================================================

    // Les 12 transpositions chromatiques standard affichées pour l'utilisateur
    const standardRoots = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

    // Les transpositions limitées mappées sur les vraies clés de ton dictionnaire Python
    const symmetricRoots = {
        "Octatonic": [{ value: "C", text: "Oct(0,1)" }, { value: "C#", text: "Oct(1,2)" }, { value: "D", text: "Oct(2,3)" }],
        "Whole Tone": [{ value: "C", text: "WT0" }, { value: "C#", text: "WT1" }],
        "Hexatonic": [{ value: "C", text: "Hex(0,1)" }, { value: "C#", text: "Hex(1,2)" }, { value: "D", text: "Hex(2,3)" }, { value: "Eb", text: "Hex(3,4)" }]
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
                opt.value = root.value; opt.textContent = root.text;
                rootSelect.appendChild(opt);
            });
        } else {
            standardRoots.forEach(note => {
                const opt = document.createElement('option');
                opt.value = note; opt.textContent = note;
                rootSelect.appendChild(opt);
            });
        }
    }

    setTypeSelect.addEventListener('change', () => { if (!isAutomaticUpdate) { updateRootOptions(setTypeSelect.value); rootSelect.disabled = false; triggerSearch(); } });
    rootSelect.addEventListener('change', () => { if (!isAutomaticUpdate) triggerSearch(); });
    distanceSelect.addEventListener('change', () => { if (!isAutomaticUpdate) triggerSearch(); });

    function triggerSearch() {
        const type = setTypeSelect.value; const root = rootSelect.value;
        if (type && root) updateExploration(type, root, distanceSelect.value);
    }

    // =========================================================================
    // ÉCOUTEUR GLOBAL RESTRUCTURÉ ET UNIQUE DU CHANGEMENT D'ONGLET (Point 9)
    // =========================================================================
    document.querySelectorAll('.tab-button, .nav-btn').forEach(button => {
        button.addEventListener('click', function() {
            const tabTarget = this.dataset.tab || this.getAttribute('data-tab');

            // 1. Gestion visuelle globale des boutons actifs
            document.querySelectorAll('.tab-button, .nav-btn').forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // 2. Masquage absolu des conteneurs physiques de graphes Vis.js
            document.getElementById('network-explore-container').style.display = 'none';
            document.getElementById('network-analyze-container').style.display = 'none';
            document.getElementById('network-compose-container').style.display = 'none';

            // Récupération des blocs de commandes pour synchronisation IHM
            const exploreBlock = document.getElementById('controls-exploration');
            const analyzeBlock = document.getElementById('controls-analysis');
            const modesContainer = document.getElementById('collection-modes-container');
            const legend = document.querySelector('.analysis-legend-container');

            // 3. Activation spécifique de la vue selon l'onglet cible (Persistance préservée)
            if (tabTarget === 'explore') {
                currentMode = 'exploration';
                document.getElementById('network-explore-container').style.display = 'block';
                if (exploreBlock) exploreBlock.style.display = 'block';
                if (analyzeBlock) analyzeBlock.style.display = 'none';
                if (legend) legend.style.display = 'none';
            }
            else if (tabTarget === 'analyze') {
                currentMode = 'analysis';
                document.getElementById('network-analyze-container').style.display = 'block';
                if (exploreBlock) exploreBlock.style.display = 'none';
                if (analyzeBlock) analyzeBlock.style.display = 'block';
                if (modesContainer) modesContainer.style.display = 'none'; // Masque les modes simples en analyse
                if (legend) legend.style.display = 'block';
                updateAnalysisDropdown();
            }
            else if (tabTarget === 'compose') {
                currentMode = 'composition';
                document.getElementById('network-compose-container').style.display = 'block';
            }
        });
    });

    // =========================================================================
    // ROUTAGE DES DONNÉES APIS VERS LES BONS RESEAUX
    // =========================================================================
    async function updateExploration(type, root, distance) {
        // RECONVERSION EN DIÈSE POUR L'API PYTHON (Point 4)
        // Si l'IHM envoie un bémol, on le remet en dièse pour que le serveur trouve la station
        const flatToSharpApi = { "Db": "C#", "Eb": "D#", "Ab": "G#", "Bb": "A#" };
        let apiRoot = flatToSharpApi[root] || root;

        // On utilise apiRoot à la place de root dans le fetch :
        const response = await fetch(`/api/explore?type=${encodeURIComponent(type)}&root=${encodeURIComponent(apiRoot)}&distance=${distance}`);
        const data = await response.json();
        if (data.error) { alert(data.error); return; }

        // 1. Allumage des touches du piano
        document.querySelectorAll('.key').forEach(key => key.classList.remove('active'));
        data.pitches.forEach(pitch => {
            // L'API renvoyant des chiffres purs, on cible directement l'attribut numérique data-note
            const keyEl = document.querySelector(`.key[data-note="${pitch}"]`);
            if (keyEl) keyEl.classList.add('active');
        });

        // 2. Génération visuelle isolée du Graphe d'Exploration
        drawExplorationGraph(data);

        // 3. Déclenche l'affichage du panneau des modes correspondant au choix actuel
        displayCollectionModes(type, root);
    }

    // =========================================================================
    // LOGIQUE DE COMMANDE DU MODE ANALYSE (COMPOSITION DU MORCEAU)
    // =========================================================================
    let analysisSetsArray = [];

    // Synchronisation du menu déroulant du Centre Macro-Harmonique
    function updateAnalysisDropdown() {
        const selectCenter = document.getElementById('analysis-center-select');
        if (!selectCenter) return;
        selectCenter.innerHTML = '';
        if (analysisSetsArray.length === 0) {
            selectCenter.innerHTML = '<option value="" disabled selected>Ajoutez des sets...</option>';
            return;
        }
        analysisSetsArray.forEach(setStr => {
            const opt = document.createElement('option');
            opt.value = setStr; opt.textContent = setStr;
            selectCenter.appendChild(opt);
        });
    }

    // Rendu visuel des badges du morceau
    function refreshAnalysisBadges() {
        const pool = document.getElementById('analysis-sets-pool');
        if (!pool) return;
        pool.innerHTML = '';
        if (analysisSetsArray.length === 0) {
            pool.innerHTML = '<span style="color: #64748b; font-style: italic; font-size: 13px;">Aucun set ajouté. Utilisez les listes ou le piano pour composer le morceau.</span>';
            return;
        }
        analysisSetsArray.forEach((setStr, index) => {
            const badge = document.createElement('span');
            badge.style.cssText = "background-color: #334155; color: #f8fafc; padding: 6px 12px; border-radius: 4px; font-size: 12px; display: inline-flex; align-items: center; gap: 8px; border: 1px solid #475569; font-family: sans-serif;";
            badge.innerHTML = `${setStr} <span class="remove-target-btn" data-idx="${index}" style="color: #ef4444; cursor: pointer; font-weight: bold; font-size: 14px; margin-left: 4px;">&times;</span>`;
            pool.appendChild(badge);
        });

        // Événement de suppression unitaire
        document.querySelectorAll('.remove-target-btn').forEach(b => {
            b.addEventListener('click', (e) => {
                analysisSetsArray.splice(parseInt(e.target.getAttribute('data-idx')), 1);
                refreshAnalysisBadges(); updateAnalysisDropdown();
            });
        });
    }

    // Action : Bouton Ajouter le set actuel
    const btnAdd = document.getElementById('btn-add-current');
    if (btnAdd) {
        btnAdd.addEventListener('click', () => {
            const currentType = setTypeSelect.value; const currentRoot = rootSelect.value;
            if (!currentType || !currentRoot) { alert("Veuillez d'abord sélectionner un Set valide (via les menus ou en double-cliquant sur la topologie)."); return; }
            const formatName = `${currentType} [${currentRoot}]`;
            if (!analysisSetsArray.includes(formatName)) {
                analysisSetsArray.push(formatName); refreshAnalysisBadges(); updateAnalysisDropdown();
            }
        });
    }

    // Action : Bouton Effacer tout
    const btnClear = document.getElementById('btn-clear-analysis');
    if (btnClear) btnClear.addEventListener('click', () => { analysisSetsArray = []; refreshAnalysisBadges(); updateAnalysisDropdown(); });

    // Action : Calcul et dessin de la topologie du morceau (Fetch /api/analyze)
    const btnRun = document.getElementById('btn-run-analysis');
    if (btnRun) {
        btnRun.addEventListener('click', async () => {
            const centerTonal = document.getElementById('analysis-center-select').value;
            if (!centerTonal) { alert("Sélectionnez le centre macro-harmonique (le repère de votre morceau)."); return; }
            if (analysisSetsArray.length < 2) { alert("Ajoutez au moins 2 sets à la liste pour pouvoir analyser les transitions."); return; }

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ center: centerTonal, sets: analysisSetsArray })
                });
                const data = await res.json();
                if (data.error) { alert(data.error); return; }

                // Appel du dessin isolé dans l'onglet Analyse
                drawAnalysisGraph(data);

            } catch (err) {
                console.error("Détail du plantage JavaScript :", err);
                alert(`Erreur lors de la communication avec l'API d'analyse : ${err.message}`);
            }
        });
    }

    // =========================================================================
    // INTERFACES SECONDAIRES ET COMPOSANTS FLUIDES (SUBSETS & MODES)
    // =========================================================================

    function displayKeyboardMatches(matches) {
        const matchesContainer = document.getElementById('keyboard-matches-container');
        const matchesList = document.getElementById('matches-list');
        const matchCountSpan = document.getElementById('match-count');

        matchesList.innerHTML = '';
        if (matches.length === 0) {
            matchesList.innerHTML = '<li style="color: #64748b; padding: 5px;">Aucun set ne contient toutes ces notes simultanément.</li>';
            matchCountSpan.innerText = "0"; matchesContainer.style.display = 'block'; return;
        }

        matchCountSpan.innerText = matches.length;
        matches.forEach(m => {
            const li = document.createElement('li');
            li.style.cssText = "display: flex; align-items: center; margin-bottom: 8px; color: #94a3b8; font-size: 13px; font-family: Segoe UI, sans-serif;";
            const missingText = m.missing.length > 0 ? `— missing ${m.missing.join(', ')}` : '— Complet ! Exact Match !';
            li.innerHTML = `
                <span style="margin-right: 10px;">• Subset of</span>
                <button class="match-btn" data-family="${m.family}" data-root="${m.root}" style="background-color: #84cc16; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 13px;">
                    ${m.station_name}
                </button>
                <span style="margin-left: 10px; color: #64748b;">${missingText}</span>
            `;
            matchesList.appendChild(li);
        });

        // Écouteur des boutons de la liste de suggestions d'identification
        document.querySelectorAll('.match-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const family = btn.getAttribute('data-family');
                let root = btn.getAttribute('data-root');

                // Harmonisation Dièse -> Bémol (Point 4)
                const sharpToFlat = { "D#": "Eb", "G#": "Ab", "A#": "Bb", "C#": "Db" };
                if (sharpToFlat[root]) root = sharpToFlat[root];

                isAutomaticUpdate = true; setTypeSelect.value = family; updateRootOptions(family);
                rootSelect.disabled = false; rootSelect.value = root; isAutomaticUpdate = false;
                matchesContainer.style.display = 'none';

                updateExploration(family, root, distanceSelect.value);
            });
        });
        matchesContainer.style.display = 'block';
    }

    // =========================================================================
    // AFFICHAGE HARMONISÉ DES MODES DE LA COLLECTION (Points 4 & 6)
    // =========================================================================
    function displayCollectionModes(family, root) {
        const container = document.getElementById('collection-modes-container');
        const badgeDiv = document.getElementById('selected-collection-badge');
        const modesList = document.getElementById('modes-list');

        // Traduction visuelle si c'est un set symétrique pour l'affichage du badge
        if (["Octatonic", "Whole Tone", "Hexatonic"].includes(family)) {
            const symNames = {
                "C": family === "Whole Tone" ? "0" : "0,1",
                "C#": family === "Whole Tone" ? "1" : "1,2",
                "Db": family === "Whole Tone" ? "1" : "1,2",
                "D": family === "Whole Tone" ? "0" : "2,3", // D revient à WT0 cycliquement
                "Eb": "3,4"
            };
            shortName = symNames[root] || root;
        }

        // Point 4 : Harmonisation stricte du Badge avec la nomenclature unifiée partout [Famille [Racine]]
        badgeDiv.innerHTML = `
            <span style="background-color: #84cc16; color: #ffffff; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                ${family} [${shortName}]
            </span>
        `;

        modesList.innerHTML = '';

        if (familyModes[family]) {
            // Point 6 : Récupération des notes actuellement actives (allumées) sur le piano pour trouver la vraie lettre du mode
            const activeNotes = Array.from(document.querySelectorAll('.key.active')).map(k => k.innerText.trim());

            // Dictionnaire de conversion de sécurité des dièses en bémols pour le visuel des modes
            const sharpToFlatDisplay = { "C#": "Db", "D#": "Eb", "F#": "F#", "G#": "Ab", "A#": "Bb" };

            // C'est un set asymétrique : on boucle sur ses modes pour générer les degrés
            familyModes[family].forEach((modeName, index) => {
                const li = document.createElement('li');
                li.style.cssText = "display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: #94a3b8; font-size: 14px;";

                // Si les notes ne sont pas encore lues sur le piano, on prend la racine par défaut, sinon la vraie note de l'index diatonique
                let modeRootLetter = (activeNotes && activeNotes[index]) ? activeNotes[index] : root;

                // TRADUCTION VISUELLE ET HARMONISATION : Si la note extraite du piano contient un dièse, on la transforme en bémol pour l'affichage
                if (sharpToFlatDisplay[modeRootLetter]) {
                    modeRootLetter = sharpToFlatDisplay[modeRootLetter];
                }

                // Injection du code HTML avec la fondamentale du mode en gras et en bémol (ex: Db Major/Ionian)
                li.innerHTML = `
                    <span><span style="color: #475569; margin-right: 8px;">▪</span> <strong>${modeRootLetter}</strong> ${modeName}</span>
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
                        PLAY
                    </button>
                `;
                modesList.appendChild(li);
            });
        } else {
            // C'est un set symétrique (Octatonic, Whole Tone, Hexatonic) à transpositions limitées
            const li = document.createElement('li');
            li.style.cssText = "color: #64748b; font-style: italic; padding: 10px 0;";
            li.innerText = "Cette collection est symétrique (à transpositions limitées) et ne possède pas de modes distincts exploitables de manière diatonique.";
            modesList.appendChild(li);
        }

        container.style.display = 'block';
    }

    // =========================================================================
    // INITIALISATION DYNAMIQUE DE LA PALETTE DE COULEURS INTERACTIVE (Point 7)
    // =========================================================================
    const pickersContainer = document.getElementById('color-pickers-container');
    if (pickersContainer) {
        Object.keys(globalOptions.groups).forEach(family => {
            const wrapper = document.createElement('div');
            wrapper.style.cssText = "display: flex; align-items: center; gap: 4px; color: #94a3b8; font-size: 11px; font-weight: 500;";

            const defaultColor = globalOptions.groups[family].color.background;

            wrapper.innerHTML = `
                <input type="color" class="family-color-input" data-family="${family}" value="${defaultColor}" title="${family}" style="border:none; width:18px; height:18px; cursor:pointer; background:none; padding:0;">
                <span>${family.substring(0, 3).toUpperCase()}</span>
            `;
            pickersContainer.appendChild(wrapper);
        });

        // Écouteur sur chaque changement de couleur pour mettre à jour les réseaux à la volée
        document.querySelectorAll('.family-color-input').forEach(input => {
            input.addEventListener('input', function() {
                const family = this.dataset.family;
                const newColor = this.value;

                globalOptions.groups[family].color.background = newColor;
                globalOptions.groups[family].color.border = newColor;

                // Application immédiate aux instances de graphes existantes
                if (networkExplore) networkExplore.setOptions({ groups: globalOptions.groups });
                if (networkAnalyze) networkAnalyze.setOptions({ groups: globalOptions.groups });
            });
        });
    }
});