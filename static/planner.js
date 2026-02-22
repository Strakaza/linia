document.addEventListener('DOMContentLoaded', function () {
    const map = L.map('plannerMap', {
        center: [50.0, 10.0],
        zoom: 4,
        zoomControl: false,
        attributionControl: true,
        renderer: L.canvas()
    });
    L.control.zoom({ position: 'topleft' }).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 20,
        crossOrigin: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);
    const OP_COLORS = {
        flixbus: { main: '#73d700', hover: '#5cb800', label: 'Flixbus' },
        blablacar_bus: { main: '#0070d2', hover: '#0056a3', label: 'BlaBlaCar' },
        unknown: { main: '#9aa0a6', hover: '#6b7280', label: 'Inconnu' }
    };
    let itinerary = [];
    let markers = [];
    let suggestionMarkers = [];
    let connectedCities = [];
    let connectedFilterQuery = '';
    const searchInput = document.getElementById('plannerSearchInput');
    const suggestionsDiv = document.getElementById('plannerSuggestions');
    const searchSpinner = document.getElementById('plannerSearchSpinner');
    const searchIcon = document.getElementById('plannerSearchIcon');
    const timeline = document.getElementById('plannerTimeline');
    const undoBtn = document.getElementById('undoBtn');
    const resetBtn = document.getElementById('resetBtn');
    const shareBtn = document.getElementById('shareBtn');
    const generatePdfBtn = document.getElementById('generatePdfBtn');
    const saveBtn = document.getElementById('saveBtn');
    const loadBtn = document.getElementById('loadBtn');
    const loadInput = document.getElementById('loadItineraryInput');
    const connectedPanel = document.getElementById('connectedPanel');
    const connectedBody = document.getElementById('connectedBody');
    const connectedTitle = document.getElementById('connectedTitle');
    const connectedSubtitle = document.getElementById('connectedSubtitle');
    const connectedClose = document.getElementById('connectedClose');
    const connectedSearchInput = document.getElementById('connectedSearchInput');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const toastContainer = document.getElementById('toastContainer');
    const plannerBubble = document.getElementById('plannerBubble');
    const plannerBubbleContent = document.getElementById('plannerBubbleContent');
    const plannerBubbleText = document.getElementById('plannerBubbleText');
    const reopenConnectedBtn = document.getElementById('reopenConnectedBtn');
    const minimizeSidebarBtn = document.getElementById('minimizeSidebarBtn');
    const plannerSidebar = document.getElementById('plannerSidebar');
    function showToast(message, type = 'info', duration = 3500) {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, { once: true });
        }, duration);
    }
    function showLoading(msg) {
        if (loadingText) loadingText.textContent = msg || i18n.t('loading');
        if (loadingOverlay) loadingOverlay.classList.add('visible');
    }
    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.remove('visible');
    }
    let searchTimeout = null;
    searchInput.addEventListener('input', function () {
        const query = this.value.trim();
        clearTimeout(searchTimeout);
        if (query.length < 2) {
            suggestionsDiv.innerHTML = '';
            suggestionsDiv.classList.remove('visible');
            return;
        }
        searchTimeout = setTimeout(() => fetchSuggestions(query), 300);
    });
    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.classList.remove('visible');
        }
    });
    searchInput.addEventListener('focus', function () {
        if (suggestionsDiv.children.length > 0 && searchInput.value.trim().length >= 2) {
            suggestionsDiv.classList.add('visible');
        }
    });
    async function fetchSuggestions(query) {
        searchSpinner.style.display = 'inline-block';
        searchIcon.style.display = 'none';
        try {
            const response = await fetch(`/api/search_stops?query=${encodeURIComponent(query)}`);
            const data = await response.json();
            if (response.ok) renderSuggestions(data);
            else showToast(i18n.t('err_search'), 'error');
        } catch (err) {
            showToast(i18n.t('err_connection'), 'error');
        } finally {
            searchSpinner.style.display = 'none';
            searchIcon.style.display = '';
        }
    }
    function renderSuggestions(suggestions) {
        suggestionsDiv.innerHTML = '';
        if (!suggestions.length) {
            suggestionsDiv.innerHTML = `<div style="padding:12px;text-align:center;color:#9aa0a6;font-size:13px;">${i18n.t('no_stop_found')}</div>`;
            suggestionsDiv.classList.add('visible');
            return;
        }
        suggestions.forEach(stop => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = stop.stop_name;
            item.addEventListener('click', () => {
                searchInput.value = '';
                suggestionsDiv.innerHTML = '';
                suggestionsDiv.classList.remove('visible');
                addStopToItinerary(stop.stop_id, stop.stop_name);
            });
            suggestionsDiv.appendChild(item);
        });
        suggestionsDiv.classList.add('visible');
    }
    async function addStopToItinerary(stopId, stopName) {
        if (itinerary.length > 0 && itinerary[itinerary.length - 1].stop_id === stopId) {
            showToast('Cette ville est déjà la dernière étape.', 'warning');
            return;
        }
        if (itinerary.length > 0) {
            const isConnected = connectedCities.some(c => c.stop_id === stopId);
            if (!isConnected) {
                showToast(i18n.t('not_connected'), 'warning');
                return;
            }
        }
        showLoading('LOADING...');
        try {
            const infoResponse = await fetch(`/api/stop_info/${encodeURIComponent(stopId)}`);
            const infoData = await infoResponse.json();
            if (!infoResponse.ok) {
                showToast(infoData.error || 'Arrêt non trouvé.', 'error');
                hideLoading();
                return;
            }
            const stopInfo = infoData.stop_info;
            itinerary.push({
                stop_id: stopInfo.stop_id,
                stop_name: stopInfo.stop_name,
                stop_lat: parseFloat(stopInfo.stop_lat),
                stop_lon: parseFloat(stopInfo.stop_lon),
                operators: []
            });
            searchInput.placeholder = 'Ajouter une étape...';
            renderTimeline();
            await renderMapItinerary();
            await loadConnectedCities(stopInfo.stop_id, stopInfo.stop_name);
            updateButtons();
        } catch (err) {
            showToast('Erreur de connexion.', 'error');
            console.error(err);
            hideLoading();
        }
    }
    async function loadConnectedCities(stopId, stopName) {
        try {
            const response = await fetch(`/api/connected_stops/${encodeURIComponent(stopId)}`);
            const data = await response.json();
            if (response.ok) {
                connectedCities = data;
                connectedFilterQuery = '';
                if (connectedSearchInput) connectedSearchInput.value = '';
                connectedSubtitle.textContent = `${i18n.t('from')} ${stopName}`;
                connectedTitle.textContent = i18n.t('cities_connected_count', { count: data.length });
                renderConnectedCities();
                renderSuggestionMarkers(data);
                connectedPanel.classList.add('visible');
                if (window.innerWidth <= 768 && reopenConnectedBtn) {
                    reopenConnectedBtn.style.display = 'none';
                }
            } else {
                showToast(i18n.t('err_connection'), 'error');
            }
        } catch (err) {
            showToast(i18n.t('err_connection'), 'error');
            console.error(err);
        }
    }
    function getOperatorBadgesHTML(operators) {
        if (!operators || operators.length === 0) return '';
        return operators.map(op => {
            const info = OP_COLORS[op] || OP_COLORS.unknown;
            return `<span class="planner-op-badge planner-op-${op}" style="background:${info.main};">${info.label}</span>`;
        }).join('');
    }
    function renderConnectedCities() {
        let filtered = connectedCities;
        if (connectedFilterQuery) {
            filtered = connectedCities.filter(c =>
                c.stop_name.toLowerCase().includes(connectedFilterQuery)
            );
        }
        if (filtered.length === 0) {
            connectedBody.innerHTML = `<div class="planner-connected-empty">${i18n.t('no_result')}</div>`;
            return;
        }
        let html = '<ul class="planner-connected-list">';
        filtered.forEach(city => {
            const isInItinerary = itinerary.some(s => s.stop_id === city.stop_id);
            const dimClass = isInItinerary ? 'planner-city-visited' : '';
            const operators = city.operators || [];
            const primaryOp = operators[0] || 'unknown';
            const dotColor = (OP_COLORS[primaryOp] || OP_COLORS.unknown).main;
            html += `<li class="planner-city-item ${dimClass}" data-stop-id="${city.stop_id}" data-stop-name="${city.stop_name}" data-operators='${JSON.stringify(operators)}'>
                        <div class="planner-city-dot" style="background:${dotColor};"></div>
                        <span class="planner-city-name">${city.stop_name}</span>
                        <div class="planner-city-operators">
                            ${isInItinerary ? `<span class="planner-city-badge">${i18n.t('already_added')}</span>` : getOperatorBadgesHTML(operators)}
                        </div>
                     </li>`;
        });
        html += '</ul>';
        connectedBody.innerHTML = html;
        connectedBody.querySelectorAll('.planner-city-item').forEach(item => {
            item.addEventListener('click', () => {
                const sid = item.dataset.stopId;
                const sname = item.dataset.stopName;
                const ops = JSON.parse(item.dataset.operators || '[]');
                if (sid) {
                    addStopWithOperators(sid, sname, ops);
                }
            });
        });
    }
    function clearSuggestionMarkers() {
        suggestionMarkers.forEach(m => map.removeLayer(m));
        suggestionMarkers = [];
    }
    function renderSuggestionMarkers(stops) {
        clearSuggestionMarkers();
        const bounds = L.latLngBounds();
        let validPoints = 0;
        itinerary.forEach(stop => {
            if (stop.stop_lat && stop.stop_lon) {
                bounds.extend([stop.stop_lat, stop.stop_lon]);
                validPoints++;
            }
        });
        stops.forEach(stop => {
            if (!stop.stop_lat || !stop.stop_lon) return;
            const ops = stop.operators || [];
            let opsClass = 'suggestion-marker-unknown';
            if (ops.includes('flixbus') && ops.includes('blablacar_bus')) {
                opsClass = 'suggestion-marker-both';
            } else if (ops.includes('flixbus')) {
                opsClass = 'suggestion-marker-flix';
            } else if (ops.includes('blablacar_bus')) {
                opsClass = 'suggestion-marker-blabla';
            }
            const marker = L.marker([stop.stop_lat, stop.stop_lon], {
                icon: L.divIcon({
                    className: `planner-suggestion-marker ${opsClass}`,
                    iconSize: [12, 12],
                    iconAnchor: [6, 6]
                }),
                title: stop.stop_name
            }).addTo(map);
            marker.on('click', () => {
                addStopWithOperators(stop.stop_id, stop.stop_name, stop.operators);
            });
            suggestionMarkers.push(marker);
            bounds.extend([stop.stop_lat, stop.stop_lon]);
            validPoints++;
        });
        if (validPoints > 0 && bounds.isValid()) {
            map.stop();
        }
    }
    async function addStopWithOperators(stopId, stopName, operators) {
        if (itinerary.length > 0 && itinerary[itinerary.length - 1].stop_id === stopId) {
            showToast('Cette ville est déjà la dernière étape.', 'warning');
            return;
        }
        showLoading('LOADING...');
        try {
            const infoResponse = await fetch(`/api/stop_info/${encodeURIComponent(stopId)}`);
            const infoData = await infoResponse.json();
            if (!infoResponse.ok) {
                showToast(infoData.error || 'Arrêt non trouvé.', 'error');
                hideLoading();
                return;
            }
            const stopInfo = infoData.stop_info;
            itinerary.push({
                stop_id: stopInfo.stop_id,
                stop_name: stopInfo.stop_name,
                stop_lat: parseFloat(stopInfo.stop_lat),
                stop_lon: parseFloat(stopInfo.stop_lon),
                operators: operators
            });
            searchInput.placeholder = 'Ajouter une étape...';
            renderTimeline();
            await renderMapItinerary();
            await loadConnectedCities(stopInfo.stop_id, stopInfo.stop_name);
            updateButtons();
        } catch (err) {
            showToast('Erreur de connexion.', 'error');
            console.error(err);
            hideLoading();
        }
    }
    connectedSearchInput.addEventListener('input', (e) => {
        connectedFilterQuery = e.target.value.toLowerCase().trim();
        renderConnectedCities();
    });
    connectedClose.addEventListener('click', () => {
        connectedPanel.classList.remove('visible');
        if (window.innerWidth <= 768 && reopenConnectedBtn && itinerary.length > 0) {
            reopenConnectedBtn.style.display = 'flex';
        }
    });
    function renderTimeline() {
        if (itinerary.length === 0) {
            timeline.innerHTML = `
                <div class="planner-empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"
                        stroke-linecap="round" stroke-linejoin="round" style="opacity:0.3; margin-bottom:12px;">
                        <circle cx="12" cy="10" r="3"></circle>
                        <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z"></path>
                    </svg>
                    <p data-i18n="planner_empty">${i18n.t('planner_empty')}</p>
                </div>`;
            return;
        }
        let html = '<ul class="planner-timeline">';
        itinerary.forEach((stop, index) => {
            const isFirst = index === 0;
            const isLast = index === itinerary.length - 1;
            const stepLabel = isFirst ? i18n.t('step_start') : isLast && itinerary.length > 1 ? i18n.t('step_last') : `${i18n.t('step_generic')} ${index}`;
            let dotColorClass = 'planner-dot-default';
            if (isFirst) dotColorClass = 'planner-dot-start';
            else if (stop.operators && stop.operators.length > 0) {
                if (stop.operators.includes('flixbus') && stop.operators.includes('blablacar_bus')) {
                    dotColorClass = 'planner-dot-both';
                } else if (stop.operators.includes('flixbus')) {
                    dotColorClass = 'planner-dot-flix';
                } else if (stop.operators.includes('blablacar_bus')) {
                    dotColorClass = 'planner-dot-blabla';
                }
            }
            const operatorBadges = !isFirst && stop.operators ? getOperatorBadgesHTML(stop.operators) : '';
            html += `<li class="planner-timeline-item ${isFirst ? 'planner-step-first' : ''} ${isLast && itinerary.length > 1 ? 'planner-step-last' : ''}" 
                         data-index="${index}" style="animation-delay: ${index * 0.05}s;">
                        <div class="planner-timeline-dot ${dotColorClass}">
                            <span class="planner-step-number">${index + 1}</span>
                        </div>
                        <div class="planner-timeline-content">
                            <span class="planner-step-label">${stepLabel}</span>
                            <span class="planner-step-city">${stop.stop_name}</span>
                            ${operatorBadges ? `<div class="planner-step-operators">${operatorBadges}</div>` : ''}
                        </div>
                     </li>`;
        });
        html += '</ul>';
        timeline.innerHTML = html;
        timeline.scrollTop = timeline.scrollHeight;
    }
    async function getRoadGeometry(stops) {
        if (!stops || stops.length < 2) return null;
        const coords = stops.map(s => `${s.stop_lon},${s.stop_lat}`).join(';');
        const url = `https://router.project-osrm.org/route/v1/driving/${coords}?geometries=geojson&overview=full`;
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
                return data.routes[0].geometry;
            }
        } catch (e) {
            console.error('Road routing error:', e);
        }
        return null;
    }
    let mapPolylines = [];
    async function renderMapItinerary() {
        markers.forEach(m => map.removeLayer(m));
        markers = [];
        mapPolylines.forEach(p => map.removeLayer(p));
        mapPolylines = [];
        if (itinerary.length === 0) {
            hideLoading();
            return;
        }
        const bounds = L.latLngBounds();
        itinerary.forEach((stop, index) => {
            const el = document.createElement('div');
            el.className = 'planner-map-marker';
            if (index === 0) {
                el.classList.add('planner-marker-start');
            } else if (stop.operators && stop.operators.length > 0) {
                if (stop.operators.includes('flixbus') && !stop.operators.includes('blablacar_bus')) {
                    el.classList.add('planner-marker-flix');
                } else if (stop.operators.includes('blablacar_bus') && !stop.operators.includes('flixbus')) {
                    el.classList.add('planner-marker-blabla');
                }
            }
            const label = document.createElement('span');
            label.className = 'planner-marker-label';
            label.textContent = index + 1;
            el.appendChild(label);
            const icon = L.divIcon({
                html: el,
                className: '',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            });
            const marker = L.marker([stop.stop_lat, stop.stop_lon], { icon: icon }).addTo(map);
            markers.push(marker);
            bounds.extend([stop.stop_lat, stop.stop_lon]);
        });
        if (itinerary.length >= 2) {
            for (let i = 0; i < itinerary.length - 1; i++) {
                const startStop = itinerary[i];
                const endStop = itinerary[i + 1];
                const ops = endStop.operators || [];
                let lineColor = '#73d700';
                let polylineClass = '';
                const hasFlix = ops.includes('flixbus');
                const hasBla = ops.includes('blablacar_bus');
                if (hasFlix && hasBla) {
                    polylineClass = 'planner-mixed-polyline';
                } else if (hasBla) {
                    lineColor = '#0070d2';
                }
                const geometry = await getRoadGeometry([startStop, endStop]);
                if (geometry && geometry.coordinates) {
                    const latlngs = geometry.coordinates.map(c => [c[1], c[0]]);
                    const poly = L.polyline(latlngs, {
                        color: lineColor,
                        weight: 6,
                        opacity: 0.7,
                        lineJoin: 'round',
                        lineCap: 'round',
                        className: polylineClass
                    }).addTo(map);
                    mapPolylines.push(poly);
                    latlngs.forEach(ll => bounds.extend(ll));
                } else {
                    const latlngs = [[startStop.stop_lat, startStop.stop_lon], [endStop.stop_lat, endStop.stop_lon]];
                    const poly = L.polyline(latlngs, {
                        color: lineColor,
                        weight: 4,
                        dashArray: '5, 10',
                        opacity: 0.5,
                        className: polylineClass
                    }).addTo(map);
                    mapPolylines.push(poly);
                }
            }
        }
        if (bounds.isValid() && itinerary.length > 1) {
            map.fitBounds(bounds, { padding: [50, 50], duration: 1.2 });
        } else if (bounds.isValid() && itinerary.length === 1) {
            map.setView([itinerary[0].stop_lat, itinerary[0].stop_lon], 11, { animate: true, duration: 1.2 });
        }
        setTimeout(() => {
            hideLoading();
        }, 1500);
    }
    function updateMobileUI() {
        if (!plannerBubble) return;
        const textEl = plannerBubbleText || plannerBubbleContent;
        if (!textEl) return;

        if (itinerary.length === 0) {
            textEl.textContent = i18n.t('mobile_bubble_empty');
        } else {
            textEl.textContent = i18n.t('mobile_bubble_stops', { count: itinerary.length });
        }
    }
    function updateButtons() {
        const hasStops = itinerary.length > 0;
        undoBtn.disabled = !hasStops;
        resetBtn.disabled = !hasStops;
        saveBtn.disabled = !hasStops;
        if (shareBtn) shareBtn.disabled = !hasStops;
        generatePdfBtn.disabled = itinerary.length < 2;
        updateMobileUI();
        if (itinerary.length === 0) {
            connectedPanel.classList.remove('visible');
            if (reopenConnectedBtn) reopenConnectedBtn.style.display = 'none';
            // Block sidebar from being draggable when empty
            if (plannerSidebar) plannerSidebar.classList.add('drag-disabled');
        } else {
            // Show reopen button if panel is closed and we have an itinerary
            if (window.innerWidth <= 768 && reopenConnectedBtn && !connectedPanel.classList.contains('visible')) {
                reopenConnectedBtn.style.display = 'flex';
            }
            if (plannerSidebar) plannerSidebar.classList.remove('drag-disabled');
        }
    }
    undoBtn.addEventListener('click', () => {
        if (itinerary.length === 0) return;
        itinerary.pop();
        renderTimeline();
        renderMapItinerary();
        updateButtons();
        if (itinerary.length > 0) {
            const lastStop = itinerary[itinerary.length - 1];
            loadConnectedCities(lastStop.stop_id, lastStop.stop_name);
        } else {
            connectedPanel.classList.remove('visible');
            clearSuggestionMarkers();
            searchInput.placeholder = i18n.t('search_start');
        }
        showToast(i18n.t('toast_removed'), 'info');
    });
    resetBtn.addEventListener('click', () => {
        itinerary = [];
        renderTimeline();
        renderMapItinerary();
        updateButtons();
        connectedPanel.classList.remove('visible');
        clearSuggestionMarkers();
        searchInput.placeholder = i18n.t('search_start');
        showToast(i18n.t('toast_cleared'), 'info');
    });
    saveBtn.addEventListener('click', () => {
        if (itinerary.length === 0) return;
        const data = JSON.stringify(itinerary, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const name = itinerary.length > 0 ? itinerary[0].stop_name.replace(/[^a-z0-9]/gi, '-') : 'itinerary';
        a.download = `linia_trip_${name}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(i18n.t('toast_saved'), 'success');
    });
    const SHARE_COPIED_TEXTS = {
        fr: 'Lien copié !', en: 'Link copied!', de: 'Link kopiert!', es: '¡Enlace copiado!',
        pt: 'Link copiado!', nl: 'Link gekopieerd!', sq: 'Lidhja u kopjua!', ca: 'Enllaç copiat!',
        hr: 'Poveznica kopirana!', bg: 'Линкът е копиран!', da: 'Link kopieret!', et: 'Link kopeeritud!',
        fi: 'Linkki kopioitu!', el: 'Ο σύνδεσμος αντιγράφηκε!', hu: 'Link másolva!', hi: 'लिंक कॉपी हो गया!',
        lv: 'Saite nokopēta!', lt: 'Nuoroda nukopijuota!', lb: 'Link kopéiert!', mk: 'Линкот е копиран!',
        ro: 'Link copiat!', pl: 'Link skopiowany!', cs: 'Odkaz zkopírován!', sk: 'Odkaz skopírovaný!',
        sl: 'Povezava kopirana!', sv: 'Länk kopierad!', tr: 'Bağlantı kopyalandı!', uk: 'Посилання скопійовано!',
        ru: 'Ссылка скопирована!', be: 'Спасылка скапіравана!'
    };

    function showConfettiNotification() {
        const existing = document.getElementById('confettiNotification');
        if (existing) existing.remove();
        const lang = i18n.currentLang || 'fr';
        const text = SHARE_COPIED_TEXTS[lang] || SHARE_COPIED_TEXTS['fr'];
        const overlay = document.createElement('div');
        overlay.id = 'confettiNotification';
        overlay.className = 'confetti-overlay';
        const colors = ['var(--linia-orange)', 'var(--linia-purple)', 'var(--linia-teal)'];
        const colorHex = ['#CC5533', '#414288', '#008080'];
        let confettiHTML = '';
        for (let i = 0; i < 40; i++) {
            const color = colorHex[i % 3];
            const left = Math.random() * 100;
            const delay = Math.random() * 0.5;
            const size = 6 + Math.random() * 8;
            const rotation = Math.random() * 360;
            const drift = -50 + Math.random() * 100;
            const type = i % 3 === 0 ? 'circle' : (i % 3 === 1 ? 'rect' : 'diamond');
            confettiHTML += `<div class="confetti-particle confetti-${type}" style="left:${left}%;background:${color};width:${size}px;height:${size * (type === 'rect' ? 0.5 : 1)}px;animation-delay:${delay}s;--drift:${drift}px;--rotation:${rotation}deg;"></div>`;
        }
        overlay.innerHTML = `
            <div class="confetti-container">${confettiHTML}</div>
            <div class="confetti-modal">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--linia-teal)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <span class="confetti-text">${text}</span>
            </div>
        `;
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('visible'));
        setTimeout(() => {
            overlay.classList.remove('visible');
            overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
            setTimeout(() => overlay.remove(), 500);
        }, 2500);
    }

    const ITINERARY_LOADED_TEXTS = {
        fr: "Itinéraire chargé !", en: "Itinerary loaded!", de: "Route geladen!", es: "¡Itinerario cargado!",
        pt: "Itinerário carregado!", nl: "Route geladen!", sq: "Itinerari u ngarkua!", ca: "Itinerari carregat!",
        hr: "Ruta učitana!", bg: "Маршрутът е зареден!", da: "Rute indlæst!", et: "Marsruut laetud!",
        fi: "Reitti ladattu!", el: "Η διαδρομή φορτώθηκε!", hu: "Útvonal betöltve!", hi: "मार्ग लोड हो गया!",
        lv: "Maršruts ielādēts!", lt: "Maršrutas įkeltas!", lb: "Route gelueden!", mk: "Рутата е вчитана!",
        ro: "Itinerar încărcat!", pl: "Trasa załadowana!", cs: "Trasa načtena!", sk: "Trasa načítaná!",
        sl: "Pot naložena!", sv: "Rutt laddad!", tr: "Rota yüklendi!", uk: "Маршрут завантажено!",
        ru: "Маршрут загружен!", be: "Маршрут загружаны!"
    };

    if (shareBtn) {
        shareBtn.addEventListener('click', () => {
            if (itinerary.length === 0) {
                showToast(i18n.t('toast_empty_itinerary') || 'Ajoutez des villes pour partager.', 'warning');
                return;
            }
            const stopIds = itinerary.map(stop => stop.stop_id).join(',');
            const url = new URL(window.location.origin + window.location.pathname);
            url.searchParams.set('route', stopIds);
            const shareUrl = url.toString();
            const shareTitle = 'Linia — ' + itinerary.map(s => s.stop_name).join(' → ');

            function doCopy(text) {
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                try {
                    document.execCommand('copy');
                    showConfettiNotification();
                } catch (err) {
                    console.error('Fallback copy failed', err);
                }
                document.body.removeChild(ta);
            }

            // We prioritize clipboard + notification for immediate feedback
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(shareUrl).then(() => {
                    showConfettiNotification();
                }).catch(() => {
                    doCopy(shareUrl);
                });
            } else {
                doCopy(shareUrl);
            }

            // Silent fallback for native share sheet (mobile)
            if (navigator.share) {
                navigator.share({ title: shareTitle, text: shareTitle, url: shareUrl }).catch(() => { });
            }
        });
    }
    loadBtn.addEventListener('click', () => {
        loadInput.click();
    });
    loadInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const loadedItinerary = JSON.parse(event.target.result);
                if (Array.isArray(loadedItinerary)) {
                    itinerary = loadedItinerary;
                    renderTimeline();
                    renderMapItinerary();
                    updateButtons();
                    if (itinerary.length > 0) {
                        const last = itinerary[itinerary.length - 1];
                        loadConnectedCities(last.stop_id, last.stop_name);
                        searchInput.placeholder = i18n.t('search_step');
                    }
                    showToast(i18n.t('toast_loaded'), 'success');
                } else {
                    showToast(i18n.t('err_search'), 'error');
                }
            } catch (err) {
                console.error(err);
                showToast(i18n.t('err_connection'), 'error');
            }
        };
        reader.readAsText(file);
        e.target.value = '';
    });
    generatePdfBtn.addEventListener('click', async () => {
        if (itinerary.length < 2) {
            showToast('Ajoutez au moins 2 villes pour générer un PDF.', 'warning');
            return;
        }
        generatePdfBtn.disabled = true;
        showLoading(i18n.t('pdf_generating'));
        let pdfFinished = false;
        const timeoutHandle = setTimeout(() => {
            if (!pdfFinished) {
                pdfFinished = true;
                showToast(i18n.t('pdf_timeout'), 'warning');
                generatePDFFile(null);
            }
        }, 12000);
        try {
            await new Promise(r => setTimeout(r, 2000));
            map.invalidateSize();
            await new Promise(r => setTimeout(r, 300));
            const mapElement = document.getElementById('plannerMap');
            html2canvas(mapElement, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff',
                logging: false,
                scale: 2,
                onclone: (clonedDoc) => {
                    const clonedMap = clonedDoc.getElementById('plannerMap');
                    if (clonedMap) {
                        clonedMap.style.transform = 'none';
                        clonedMap.style.transition = 'none';
                        const internalContainer = clonedMap.querySelector('.leaflet-map-pane');
                        if (internalContainer) internalContainer.style.transform = 'none';
                    }
                }
            }).then(canvas => {
                if (pdfFinished) return;
                try {
                    const mapImage = canvas.toDataURL('image/png');
                    clearTimeout(timeoutHandle);
                    pdfFinished = true;
                    generatePDFFile(mapImage);
                } catch (dataErr) {
                    console.error('DataURL error:', dataErr);
                    clearTimeout(timeoutHandle);
                    pdfFinished = true;
                    generatePDFFile(null);
                }
            }).catch(err => {
                if (pdfFinished) return;
                console.error('Capture error:', err);
                clearTimeout(timeoutHandle);
                pdfFinished = true;
                showToast(i18n.t('pdf_canvas_err'), 'warning');
                generatePDFFile(null);
            }
            );
        } catch (err) {
            console.error('PDF generation error:', err);
            if (!pdfFinished) {
                clearTimeout(timeoutHandle);
                pdfFinished = true;
                showToast('Erreur lors de la génération du PDF.', 'error');
                hideLoading();
                generatePdfBtn.disabled = false;
            }
        }
    });
    function generatePDFFile(mapImage) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        const margin = 20;
        let y = 20;
        try {
            doc.setFontSize(28);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(115, 215, 0);
            doc.text('Linia', margin, y + 10);
            doc.setFontSize(10);
            doc.setTextColor(130, 130, 130);
            doc.setFont('helvetica', 'normal');
            const now = new Date();
            doc.text(`Généré le ${now.toLocaleDateString('fr-FR')}`, pageWidth - margin - 40, y + 5);
            y += 20;
            const contentWidth = pageWidth - (margin * 2);
            if (mapImage && mapImage.startsWith('data:image')) {
                const finalImgHeight = 100;
                doc.addImage(mapImage, 'PNG', margin, y, contentWidth, finalImgHeight);
                doc.setDrawColor(220, 220, 220);
                doc.rect(margin, y, contentWidth, finalImgHeight);
                y += finalImgHeight + 15;
            } else {
                y += 10;
            }
            doc.setFontSize(16);
            doc.setTextColor(50, 50, 50);
            doc.setFont('helvetica', 'bold');
            doc.text(`${itinerary.length} villes traversées`, margin, y);
            y += 8;
            doc.setFontSize(12);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(100, 100, 100);
            const startName = itinerary[0]?.stop_name || 'Départ';
            const endName = itinerary[itinerary.length - 1]?.stop_name || 'Arrivée';
            doc.text(String(`${startName} -> ${endName}`), margin, y);
            y += 15;
            itinerary.forEach((stop, index) => {
                if (y > 270) {
                    doc.addPage();
                    y = 20;
                }
                const isFirst = index === 0;
                const isLast = index === itinerary.length - 1;
                const operators = stop.operators || [];
                const circleX = margin + 4;
                const circleY = y;
                if (isFirst) {
                    doc.setFillColor(115, 215, 0);
                } else if (operators.includes('blablacar_bus') && !operators.includes('flixbus')) {
                    doc.setFillColor(0, 112, 210);
                } else {
                    doc.setFillColor(115, 215, 0);
                }
                doc.circle(circleX, circleY, 3.5, 'F');
                doc.setFontSize(7);
                doc.setFont('helvetica', 'bold');
                doc.setTextColor(255, 255, 255);
                const numStr = String(index + 1);
                doc.text(numStr, circleX - (numStr.length > 1 ? 2.5 : 1.5), circleY + 1.5);
                doc.setFontSize(12);
                doc.setFont('helvetica', isFirst || isLast ? 'bold' : 'normal');
                doc.setTextColor(40, 40, 40);
                const stopName = stop.stop_name ? String(stop.stop_name) : 'Ville inconnue';
                doc.text(stopName, margin + 14, y + 2);
                if (!isFirst && operators.length > 0) {
                    doc.setFontSize(9);
                    doc.setFont('helvetica', 'normal');
                    let opX = margin + 14;
                    doc.setTextColor(100, 100, 100);
                    doc.text("via ", opX, y + 7);
                    opX += 6;
                    const opsToPrint = [];
                    if (operators.includes('flixbus')) opsToPrint.push({ name: 'Flixbus', color: [115, 215, 0] });
                    if (operators.includes('blablacar_bus')) opsToPrint.push({ name: 'BlaBlaCar', color: [0, 112, 210] });
                    if (opsToPrint.length === 0) {
                        opsToPrint.push({ name: 'Bus', color: [100, 100, 100] });
                    }
                    opsToPrint.forEach((op, i) => {
                        doc.setTextColor(op.color[0], op.color[1], op.color[2]);
                        doc.text(String(op.name), opX, y + 7);
                        opX += doc.getTextWidth(String(op.name));
                        if (i < opsToPrint.length - 1) {
                            doc.setTextColor(150, 150, 150);
                            doc.text(" + ", opX, y + 7);
                            opX += doc.getTextWidth(" + ");
                        }
                    });
                }
                if (!isLast) {
                    doc.setDrawColor(200, 200, 200);
                    doc.setLineWidth(0.3);
                    doc.line(circleX, circleY + 4.5, circleX, circleY + 16);
                }
                y += 18;
            });
            const firstName = (itinerary[0]?.stop_name || 'Linia').replace(/[^a-zA-Z0-9]/g, '-');
            const lastName = (itinerary[itinerary.length - 1]?.stop_name || 'Fin').replace(/[^a-zA-Z0-9]/g, '-');
            doc.save(`Linia_Itineraire_${firstName}_${lastName}.pdf`);
            showToast(i18n.t('pdf_success'), 'success');
        } catch (pdfErr) {
            console.error('PDF construction error:', pdfErr);
            showToast('Erreur lors de l’assemblage du PDF.', 'error');
        } finally {
            hideLoading();
            generatePdfBtn.disabled = false;
        }
    }
    const disclaimerToggleBtn = document.getElementById('disclaimerToggleBtn');
    const plannerDisclaimer = document.getElementById('plannerDisclaimer');
    if (disclaimerToggleBtn && plannerDisclaimer) {
        disclaimerToggleBtn.addEventListener('click', () => {
            plannerDisclaimer.classList.toggle('collapsed');
            const isCollapsed = plannerDisclaimer.classList.contains('collapsed');
            const iconMinus = disclaimerToggleBtn.querySelector('.icon-minus');
            const iconPlus = disclaimerToggleBtn.querySelector('.icon-plus');
            if (iconMinus) iconMinus.style.display = isCollapsed ? 'none' : 'block';
            if (iconPlus) iconPlus.style.display = isCollapsed ? 'block' : 'none';
        });
    }

    if (typeof makePanelDraggable === 'function') {
        makePanelDraggable('plannerSidebar', 'plannerSidebarHeader');
        makePanelDraggable('connectedPanel', 'connectedHeader');
    }

    if (window.innerWidth <= 768) {
        if (plannerBubble) {
            plannerBubble.style.display = 'flex';
        }
        if (minimizeSidebarBtn) {
            minimizeSidebarBtn.style.display = '';
        }
    }

    if (plannerBubbleContent) {
        plannerBubbleContent.addEventListener('click', () => {
            if (itinerary.length === 0) {
                searchInput.focus();
                return;
            }
            plannerSidebar.classList.add('visible');
            plannerBubble.style.display = 'none';
        });
    }

    if (minimizeSidebarBtn) {
        minimizeSidebarBtn.addEventListener('click', () => {
            plannerSidebar.classList.remove('visible');
            if (window.innerWidth <= 768 && plannerBubble) {
                plannerBubble.style.display = 'flex';
            }
        });
    }

    if (reopenConnectedBtn) {
        reopenConnectedBtn.addEventListener('click', () => {
            if (itinerary.length > 0) {
                const lastStop = itinerary[itinerary.length - 1];
                loadConnectedCities(lastStop.stop_id, lastStop.stop_name);
            }
        });
    }

    async function loadSharedRoute() {
        const params = new URLSearchParams(window.location.search);
        const routeParam = params.get('route');
        if (!routeParam) return;
        const stopIds = routeParam.split(',').filter(id => id.trim());
        if (stopIds.length === 0) return;
        showLoading(i18n.t('loading') || 'Chargement...');
        try {
            for (let idx = 0; idx < stopIds.length; idx++) {
                const stopId = stopIds[idx].trim();
                const response = await fetch(`/api/stop_info/${encodeURIComponent(stopId)}`);
                const data = await response.json();
                if (!response.ok || !data.stop_info) continue;
                const stopInfo = data.stop_info;
                itinerary.push({
                    stop_id: stopInfo.stop_id,
                    stop_name: stopInfo.stop_name,
                    stop_lat: parseFloat(stopInfo.stop_lat),
                    stop_lon: parseFloat(stopInfo.stop_lon),
                    operators: []
                });
            }
            if (itinerary.length > 0) {
                renderTimeline();
                await renderMapItinerary();
                updateButtons();
                searchInput.placeholder = i18n.t('search_add_step') || 'Ajouter une étape...';
                const lastStop = itinerary[itinerary.length - 1];
                await loadConnectedCities(lastStop.stop_id, lastStop.stop_name);
                const lang = i18n.currentLang || 'fr';
                const msg = ITINERARY_LOADED_TEXTS[lang] || ITINERARY_LOADED_TEXTS['fr'];
                showToast(msg, 'success');
            }
        } catch (err) {
            console.error('Error loading shared route:', err);
            showToast(i18n.t('err_connection') || 'Erreur de connexion.', 'error');
        } finally {
            hideLoading();
        }
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete('route');
        window.history.replaceState({}, '', cleanUrl);
    }

    loadSharedRoute();
    updateButtons();
});
