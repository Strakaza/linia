document.addEventListener('DOMContentLoaded', function () {
    const map = L.map('map', {
        center: [50.0516, 14.2514],
        zoom: 4.5,
        zoomControl: false,
        attributionControl: true
    });
    L.control.zoom({ position: 'topleft' }).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 20,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);
    let currentStopMarker = null;
    let stopMarkers = [];
    let hasRouteData = false;
    let cachedRoutes = [];
    let cachedStopInfo = null;
    let activeOperatorFilter = 'all';
    let activeSearchQuery = '';
    const searchInput = document.getElementById('mapSearchInput');
    const suggestionsDiv = document.getElementById('mapSuggestions');
    const searchSpinner = document.getElementById('mapSearchSpinner');
    const searchIcon = document.getElementById('mapSearchIcon');
    const routePanel = document.getElementById('routePanel');
    const routePanelBody = document.getElementById('routePanelBody');
    const routePanelTitle = document.getElementById('routePanelTitle');
    const routePanelClose = document.getElementById('routePanelClose');
    const operatorLegend = document.getElementById('operatorLegend');
    const routeLocalSearch = document.getElementById('routeLocalSearch');
    const filterPills = document.querySelectorAll('.filter-pill');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const toastContainer = document.getElementById('toastContainer');
    const reopenPanelBtn = document.getElementById('reopenPanelBtn');
    const tripDetailsPanel = document.getElementById('tripDetailsPanel');
    const tripPanelBody = document.getElementById('tripPanelBody');
    const tripPanelTitle = document.getElementById('tripPanelTitle');
    const tripPanelSubtitle = document.getElementById('tripPanelSubtitle');
    const tripPanelClose = document.getElementById('tripPanelClose');
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
        if (loadingText) loadingText.textContent = msg || 'Chargement...';
        if (loadingOverlay) loadingOverlay.classList.add('visible');
    }
    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.remove('visible');
    }
    function openRoutePanel() {
        routePanel.classList.add('visible');
        reopenPanelBtn.style.display = 'none';
    }
    function closeRoutePanel() {
        routePanel.classList.remove('visible');
        if (hasRouteData) {
            reopenPanelBtn.style.display = 'flex';
        }
    }
    routePanelClose.addEventListener('click', closeRoutePanel);
    reopenPanelBtn.addEventListener('click', openRoutePanel);
    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            activeOperatorFilter = pill.dataset.filter;
            renderFilteredRoutes();
        });
    });
    routeLocalSearch.addEventListener('input', (e) => {
        activeSearchQuery = e.target.value.toLowerCase().trim();
        renderFilteredRoutes();
    });
    function openTripPanel() {
        tripDetailsPanel.classList.add('visible');
    }
    function closeTripPanel() {
        tripDetailsPanel.classList.remove('visible');
    }
    tripPanelClose.addEventListener('click', closeTripPanel);
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
            if (response.ok) {
                renderSuggestions(data);
            } else {
                showToast(i18n.t('err_search'), 'error');
            }
        } catch (err) {
            showToast(i18n.t('err_connection'), 'error');
        } finally {
            searchSpinner.style.display = 'none';
            searchIcon.style.display = '';
        }
    }
    function renderSuggestions(suggestions) {
        suggestionsDiv.innerHTML = '';
        if (suggestions.length === 0) {
            suggestionsDiv.innerHTML = `<div class="suggestion-empty" style="padding:12px;text-align:center;color:#9aa0a6;font-size:13px;">${i18n.t('no_stop_found')}</div>`;
            suggestionsDiv.classList.add('visible');
            setTimeout(() => {
                if (suggestionsDiv.querySelector('.suggestion-empty')) {
                    suggestionsDiv.classList.remove('visible');
                }
            }, 2000);
            return;
        }
        suggestions.forEach(stop => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.textContent = stop.stop_name;
            item.addEventListener('click', function () {
                searchInput.value = stop.stop_name;
                suggestionsDiv.innerHTML = '';
                suggestionsDiv.classList.remove('visible');
                handleStopSelect(stop.stop_id, stop.stop_name);
            });
            suggestionsDiv.appendChild(item);
        });
        suggestionsDiv.classList.add('visible');
    }
    let tripLinePolyline = null;
    let highlightPolyline = null;
    function clearTripLayers() {
        if (tripLinePolyline) {
            map.removeLayer(tripLinePolyline);
            tripLinePolyline = null;
        }
        stopMarkers.forEach(m => map.removeLayer(m));
        stopMarkers = [];
        closeTripPanel();
        tripPanelBody.innerHTML = '';
    }
    function clearCurrentStopMarker() {
        if (currentStopMarker) {
            map.removeLayer(currentStopMarker);
            currentStopMarker = null;
        }
    }
    async function handleStopSelect(stopId, stopName) {
        if (!stopId) { showToast('ID arrêt manquant.', 'warning'); return; }
        clearPreviousData();
        showLoading("Chargement de l'arrêt...");
        const url = new URL(window.location);
        url.searchParams.set('stop_id', stopId);
        if (stopName) url.searchParams.set('stop_name', stopName);
        window.history.replaceState({}, '', url);
        try {
            const response = await fetch(`/api/stop_info/${encodeURIComponent(stopId)}`);
            const data = await response.json();
            if (response.ok) {
                updateMapForStop(data.stop_info);
                cachedRoutes = data.routes || [];
                cachedStopInfo = data.stop_info;
                renderFilteredRoutes();
            } else {
                showToast(data.error || "Arrêt non trouvé.", 'error');
            }
        } catch (err) {
            showToast('Erreur de connexion.', 'error');
        } finally {
            hideLoading();
        }
    }
    function clearPreviousData() {
        routePanelBody.innerHTML = '';
        closeRoutePanel();
        hasRouteData = false;
        reopenPanelBtn.style.display = 'none';
        operatorLegend.style.display = 'none';
        clearTripLayers();
        clearCurrentStopMarker();
        cachedRoutes = [];
        routeLocalSearch.value = '';
        activeSearchQuery = '';
        activeOperatorFilter = 'all';
        filterPills.forEach((p, i) => i === 0 ? p.classList.add('active') : p.classList.remove('active'));
    }
    function updateMapForStop(stopData) {
        if (!stopData) return;
        clearCurrentStopMarker();
        const el = document.createElement('div');
        el.className = 'planner-map-marker';
        const icon = L.divIcon({
            html: el,
            className: '',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });
        currentStopMarker = L.marker([stopData.stop_lat, stopData.stop_lon], { icon: icon })
            .bindPopup(stopData.stop_name)
            .addTo(map);
        currentStopMarker.openPopup();
        map.flyTo([stopData.stop_lat, stopData.stop_lon], 12, { duration: 1.25 });
    }
    function renderFilteredRoutes() {
        if (!cachedRoutes || cachedRoutes.length === 0) {
            routePanelBody.innerHTML = '<div class="route-empty-msg">Aucune ligne ne dessert cet arrêt.</div>';
            routePanelTitle.textContent = `Lignes — ${cachedStopInfo ? cachedStopInfo.stop_name : ''}`;
            operatorLegend.style.display = 'none';
            hasRouteData = false;
            openRoutePanel();
            return;
        }
        const stopName = cachedStopInfo ? cachedStopInfo.stop_name : i18n.t('this_stop');
        routePanelTitle.innerHTML = i18n.t('lines_from_stop_html', { stopName: stopName });
        operatorLegend.style.display = 'flex';
        hasRouteData = true;
        let filtered = cachedRoutes.filter(route => {
            const matchesOperator = activeOperatorFilter === 'all' || route.operator === activeOperatorFilter;
            const name = (route.display_name || '').toLowerCase();
            const matchesSearch = name.includes(activeSearchQuery);
            return matchesOperator && matchesSearch;
        }).sort((a, b) => {
            if (a.operator === 'flixbus' && b.operator !== 'flixbus') return -1;
            if (a.operator !== 'flixbus' && b.operator === 'flixbus') return 1;
            return 0;
        });
        if (filtered.length === 0) {
            routePanelBody.innerHTML = `<div class="route-empty-msg">${i18n.t('no_search_result')}</div>`;
            return;
        }
        let html = '<ul class="route-list">';
        filtered.forEach(route => {
            const opClass = route.operator
                ? `route-item--${route.operator.toLowerCase().replace(/_/g, '-')}`
                : 'route-item--unknown';
            const name = route.display_name || i18n.t('unnamed_line');
            html += `<li class="route-item ${opClass}" data-trip-id="${route.trip_id}">
                        <strong>${name}</strong>
                     </li>`;
        });
        html += '</ul>';
        routePanelBody.innerHTML = html;
        openRoutePanel();
        routePanelBody.querySelectorAll('.route-item').forEach(item => {
            item.addEventListener('click', handleRouteClick);
        });
    }
    async function highlightRouteOnMap(tripId) {
        try {
            const response = await fetch(`/api/trip_details/${encodeURIComponent(tripId)}`);
            const tripData = await response.json();
            if (!response.ok) return;
            let lineColor = tripData.operator === 'flixbus' ? '#73d700' : '#0070d2';
            let latlngs = [];
            if (tripData.stops && tripData.stops.length >= 2) {
                const geometry = await getRoadGeometry(tripData.stops);
                if (geometry && geometry.coordinates) {
                    latlngs = geometry.coordinates.map(c => [c[1], c[0]]);
                }
            }
            if (latlngs.length === 0 && tripData.shape_points && tripData.shape_points.length > 0) {
                latlngs = tripData.shape_points.map(p => [p[0], p[1]]);
            }
            if (latlngs.length === 0 && tripData.stops && tripData.stops.length >= 2) {
                latlngs = tripData.stops.map(s => [s.stop_lat, s.stop_lon]);
            }
            if (latlngs.length > 0) {
                clearHighlightLayer();
                highlightPolyline = L.polyline(latlngs, {
                    color: lineColor,
                    weight: 6,
                    opacity: 0.3,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);
            }
        } catch (e) {
            console.error('Hover highlight error:', e);
        }
    }
    function clearHighlightLayer() {
        if (highlightPolyline) {
            map.removeLayer(highlightPolyline);
            highlightPolyline = null;
        }
    }
    function populateTripPanel(tripData) {
        const opName = tripData.operator === 'flixbus' ? 'Flixbus' :
            tripData.operator === 'blablacar_bus' ? 'BlaBlaCar Bus' : i18n.t('unknown_operator');
        const routeName = tripData.display_name || tripData.route_long_name || tripData.trip_headsign || '';
        tripPanelTitle.textContent = i18n.t('trip_proposed_by', { operatorName: opName });
        tripPanelSubtitle.textContent = routeName;
        if (!tripData.stops || tripData.stops.length === 0) {
            tripPanelBody.innerHTML = `<div style="color:var(--text-muted);text-align:center;">${i18n.t('no_stop_available')}</div>`;
            return;
        }
        const params = new URLSearchParams(window.location.search);
        const currentStopId = params.get('stop_id');
        let html = '<ul class="timeline-list">';
        tripData.stops.forEach((stop, index) => {
            const isActive = currentStopId && (String(stop.stop_id) === String(currentStopId));
            let activeClass = '';
            if (isActive) {
                const isFlix = tripData.operator === 'flixbus';
                activeClass = isFlix ? 'active-flix' : 'active-blabla';
            }
            html += `<li class="timeline-item ${activeClass}" data-stop-id="${stop.stop_id || ''}" data-stop-name="${stop.stop_name}" style="cursor:pointer;">
                        <div class="timeline-dot"></div>
                        <div class="timeline-content">
                            <span class="timeline-city-name">${stop.stop_name}</span>
                        </div>
                     </li>`;
        });
        html += '</ul>';
        tripPanelBody.innerHTML = html;
        openTripPanel();
        const items = tripPanelBody.querySelectorAll('.timeline-item');
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                const sId = item.dataset.stopId;
                const sName = item.dataset.stopName;
                if (sId) {
                    handleStopSelect(sId, sName);
                }
            });
            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = 'var(--bg-hover)';
                const sId = item.dataset.stopId;
                if (!sId) return;
                const markerEl = document.querySelector(`.linia-map-marker[data-stop-id="${sId}"]`);
                if (markerEl) markerEl.classList.add('hovered');
            });
            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = '';
                const sId = item.dataset.stopId;
                if (!sId) return;
                const markerEl = document.querySelector(`.linia-map-marker[data-stop-id="${sId}"]`);
                if (markerEl) markerEl.classList.remove('hovered');
            });
        });
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
            console.error('OSRM Routing API error:', e);
        }
        return null;
    }
    async function handleRouteClick(event) {
        const tripId = event.currentTarget.dataset.tripId;
        if (!tripId) { showToast('ID trajet manquant.', 'error'); return; }
        showLoading('Chargement du trajet...');
        clearTripLayers();
        closeRoutePanel();
        try {
            const response = await fetch(`/api/trip_details/${encodeURIComponent(tripId)}`);
            const tripData = await response.json();
            if (!response.ok) {
                showToast(tripData.error || 'Erreur inconnue.', 'error');
                return;
            }
            populateTripPanel(tripData);
            let lineColor = tripData.operator === 'flixbus' ? '#73d700' : '#0070d2';
            let latlngs = [];
            const routeMarkersBounds = L.latLngBounds();
            if (tripData.stops && tripData.stops.length > 0) {
                tripData.stops.forEach(stop => {
                    const el = document.createElement('div');
                    el.className = 'linia-map-marker';
                    if (tripData.operator === 'flixbus') el.classList.add('op-flixbus');
                    else if (tripData.operator === 'blablacar_bus') el.classList.add('op-blablacar-bus');
                    el.dataset.stopId = stop.stop_id;
                    const icon = L.divIcon({
                        html: el,
                        className: '',
                        iconSize: [14, 14],
                        iconAnchor: [7, 7]
                    });
                    const marker = L.marker([stop.stop_lat, stop.stop_lon], { icon: icon })
                        .bindPopup(stop.stop_name)
                        .addTo(map);
                    stopMarkers.push(marker);
                    routeMarkersBounds.extend([stop.stop_lat, stop.stop_lon]);
                });
            }
            if (currentStopMarker) {
                routeMarkersBounds.extend(currentStopMarker.getLatLng());
            }
            if (tripData.stops && tripData.stops.length >= 2) {
                showLoading('Calcul de l\'itinéraire par la route...');
                const geometry = await getRoadGeometry(tripData.stops);
                if (geometry && geometry.coordinates) {
                    latlngs = geometry.coordinates.map(c => [c[1], c[0]]);
                }
            }
            if (latlngs.length === 0 && tripData.shape_points && tripData.shape_points.length > 0) {
                latlngs = tripData.shape_points.map(p => [p[0], p[1]]);
            }
            if (latlngs.length === 0 && tripData.stops && tripData.stops.length >= 2) {
                latlngs = tripData.stops.map(s => [s.stop_lat, s.stop_lon]);
            }
            if (latlngs.length > 0) {
                tripLinePolyline = L.polyline(latlngs, {
                    color: lineColor,
                    weight: 5,
                    opacity: 0.8,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);
                tripLinePolyline.on('click', () => openTripPanel());
                tripLinePolyline.on('mouseover', (e) => {
                    e.target.setStyle({ weight: 7 });
                    L.DomUtil.addClass(map.getContainer(), 'pointer-cursor');
                });
                tripLinePolyline.on('mouseout', (e) => {
                    e.target.setStyle({ weight: 5 });
                    L.DomUtil.removeClass(map.getContainer(), 'pointer-cursor');
                });
                latlngs.forEach(ll => routeMarkersBounds.extend(ll));
            }
            if (routeMarkersBounds.isValid()) {
                map.fitBounds(routeMarkersBounds, { padding: [40, 40], duration: 1 });
            }
        } catch (err) {
            console.error('Route interaction error:', err);
            showToast('Erreur lors du chargement du trajet.', 'error');
        } finally {
            hideLoading();
        }
    }
    async function drawPreloadedRoute(startId, endId, nameA, nameB) {
        showLoading("Chargement du trajet...");
        try {
            const [resA, resB] = await Promise.all([
                fetch(`/api/stop_info/${encodeURIComponent(startId)}`),
                fetch(`/api/stop_info/${encodeURIComponent(endId)}`)
            ]);

            if (!resA.ok || !resB.ok) {
                showToast("Erreur lors du chargement des villes.", "error");
                hideLoading();
                return;
            }
            const dataA = await resA.json();
            const dataB = await resB.json();
            const stopA = dataA.stop_info;
            const stopB = dataB.stop_info;

            const bounds = L.latLngBounds();

            [stopA, stopB].forEach((stop) => {
                const el = document.createElement('div');
                el.className = 'linia-map-marker';
                const icon = L.divIcon({ html: el, className: '', iconSize: [14, 14], iconAnchor: [7, 7] });
                const marker = L.marker([stop.stop_lat, stop.stop_lon], { icon: icon }).bindPopup(stop.stop_name).addTo(map);
                stopMarkers.push(marker);
                bounds.extend([stop.stop_lat, stop.stop_lon]);
            });

            const geometry = await getRoadGeometry([stopA, stopB]);
            if (geometry && geometry.coordinates) {
                const latlngs = geometry.coordinates.map(c => [c[1], c[0]]);
                tripLinePolyline = L.polyline(latlngs, {
                    color: '#73d700',
                    weight: 6,
                    opacity: 0.8,
                    lineJoin: 'round',
                    lineCap: 'round'
                }).addTo(map);
            } else {
                tripLinePolyline = L.polyline([[stopA.stop_lat, stopA.stop_lon], [stopB.stop_lat, stopB.stop_lon]], {
                    color: '#73d700',
                    weight: 6,
                    dashArray: '5, 10',
                    opacity: 0.8
                }).addTo(map);
            }

            if (bounds.isValid()) {
                map.fitBounds(bounds, { padding: [50, 50], duration: 1.2 });
            }
        } catch (e) {
            console.error('Route interaction error:', e);
            showToast('Erreur lors du chargement du trajet.', 'error');
        } finally {
            hideLoading();
        }
    }

    const initialParams = new URLSearchParams(window.location.search);
    const stopIdParam = initialParams.get('stop_id') || window.PRELOADED_STOP_ID;
    const stopNameParam = initialParams.get('stop_name') || window.PRELOADED_STOP_NAME;

    if (window.PRELOADED_START_ID && window.PRELOADED_END_ID) {
        drawPreloadedRoute(window.PRELOADED_START_ID, window.PRELOADED_END_ID, window.CITY_A_NAME, window.CITY_B_NAME);
    } else if (stopIdParam) {
        if (stopNameParam) searchInput.value = stopNameParam;
        handleStopSelect(stopIdParam, stopNameParam || '');
    }
});