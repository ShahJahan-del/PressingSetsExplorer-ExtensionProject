document.addEventListener('DOMContentLoaded', () => {
    const stationSelect = document.getElementById('station-select');
    const distanceSelect = document.getElementById('distance-select');

    // Étape A : Charger les 57 stations au démarrage pour remplir le menu
    async function initStationList() {
        const response = await fetch('/api/stations');
        const stations = await response.json();

        stationSelect.innerHTML = ''; // Nettoyage
        stations.forEach(station => {
            const opt = document.createElement('option');
            opt.value = station;
            opt.textContent = station;
            // On met Diatonic [D] par défaut
            if (station === "Diatonic [D]") opt.selected = true;
            stationSelect.appendChild(opt);
        });

        // Premier calcul une fois la liste prête
        updateExploration();
    }

    // Étape B : Mettre à jour l'allumage du piano et la carte des couches
    async function updateExploration() {
        const station = stationSelect.value;
        const distance = distanceSelect.value;

        if (!station) return;

        const response = await fetch(`/api/explore?station=${encodeURIComponent(station)}&distance=${distance}`);
        const data = await response.json();

        // 1. Allumage du piano
        document.querySelectorAll('.key').forEach(key => key.classList.remove('active'));
        data.pitches.forEach(pitch => {
            const key = document.querySelector(`.key[data-note="${pitch}"]`);
            if (key) key.classList.add('active');
        });

        // 2. Rendu des couches de distance
        const wrapper = document.getElementById('layers-wrapper');
        wrapper.innerHTML = '';

        Object.keys(data.neighbors_by_layer).forEach(layerNum => {
            const neighbors = data.neighbors_by_layer[layerNum];
            if (neighbors.length === 0) return;

            const layerBlock = document.createElement('div');
            layerBlock.className = 'layer-block';
            layerBlock.innerHTML = `<h3>🔹 DISTANCE LAYER ${layerNum} (${neighbors.length} stations)</h3>`;

            const grid = document.createElement('div');
            grid.className = 'grid-neighbors';

            neighbors.forEach(nb => {
                const card = document.createElement('div');
                card.className = 'neighbor-card';
                card.innerHTML = `
                    <h4>${nb.name}</h4>
                    <p class="vl"><strong>Triggers :</strong> ${nb.voice_leading}</p>
                    <p class="path-routing"><strong>Route :</strong> ${nb.path_steps}</p>
                    <button class="jump-btn" data-destination="${nb.name}">📍 Naviguer ici</button>
                `;
                grid.appendChild(card);
            });

            layerBlock.appendChild(grid);
            wrapper.appendChild(layerBlock);
        });

        // Événements de navigation par clic
        document.querySelectorAll('.jump-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dest = e.target.getAttribute('data-destination');
                stationSelect.value = dest;
                updateExploration();
            });
        });
    }

    // Écouteurs
    stationSelect.addEventListener('change', updateExploration);
    distanceSelect.addEventListener('change', updateExploration);

    // Lancement
    initStationList();
});