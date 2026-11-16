(async () => {
    const status = document.getElementById('radar-status');
    const button = document.getElementById('radar-play');
    if (typeof L === 'undefined') {
        status.textContent = 'Map unavailable. Check the internet connection.';
        button.disabled = true;
        return;
    }

    const map = L.map('radar-map', {maxZoom: 7}).setView([56.2, 14.0], 7);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 7,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · <a href="https://www.rainviewer.com/">RainViewer</a>'
    }).addTo(map);
    L.circleMarker([55.705, 13.191], {
        radius: 7, color: '#fff', weight: 2,
        fillColor: '#e11919', fillOpacity: 1
    }).addTo(map).bindTooltip('Lund', {
        permanent: true, direction: 'right', className: 'lund-label'
    });

    let layers = [];
    let frame = 0;
    let playing = true;
    let unavailable = false;

    function showFrame(index) {
        if (!layers.length) return;
        layers[frame].layer.setOpacity(0);
        frame = index;
        layers[frame].layer.setOpacity(0.65);
        if (!unavailable) {
            status.textContent = new Date(layers[frame].time * 1000)
                .toLocaleTimeString('sv-SE', {hour: '2-digit', minute: '2-digit'});
        }
    }

    async function refreshRadar() {
        try {
            const response = await fetch('https://api.rainviewer.com/public/weather-maps.json');
            if (!response.ok) throw new Error('Radar unavailable');
            const data = await response.json();
            // Four recent frames keep tile requests modest on the home display.
            const frames = data.radar?.past?.slice(-4);
            if (!frames?.length) throw new Error('No radar frames');
            const host = new URL(data.host);
            if (host.protocol !== 'https:' || !host.hostname.endsWith('.rainviewer.com')) {
                throw new Error('Unexpected radar server');
            }
            const nextLayers = frames.map(item => ({
                time: item.time,
                layer: L.tileLayer(`${host.origin}${item.path}/256/{z}/{x}/{y}/2/1_1.png`, {
                    maxZoom: 7, opacity: 0, zIndex: 300
                })
            }));
            layers.forEach(item => map.removeLayer(item.layer));
            layers = nextLayers;
            unavailable = false;
            layers.forEach(item => {
                item.layer.on('tileerror', () => {
                    unavailable = true;
                    status.textContent = 'Radar tiles unavailable. Retrying shortly.';
                });
                item.layer.addTo(map);
            });
            frame = 0;
            showFrame(layers.length - 1);
        } catch (_) {
            unavailable = true;
            status.textContent = 'Radar unavailable. Retrying shortly.';
        }
    }

    button.addEventListener('click', () => {
        playing = !playing;
        button.textContent = playing ? 'Pause' : 'Play';
        button.setAttribute('aria-pressed', String(playing));
    });
    await refreshRadar();
    setInterval(() => {
        if (playing && !document.hidden && layers.length) showFrame((frame + 1) % layers.length);
    }, 1800);
    setInterval(refreshRadar, 10 * 60 * 1000);
})();
