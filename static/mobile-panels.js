// mobile-panels.js
function makePanelDraggable(panelId, headerId) {
    const panel = document.getElementById(panelId);
    const header = document.getElementById(headerId);

    if (!panel || !header) return;

    let startY = 0;
    let currentY = 0;
    let initialHeight = 0;
    let isDragging = false;
    let maxVH = 87; // Allow the panel to go to 87% of screen height

    const getVH = () => window.innerHeight || document.documentElement.clientHeight;
    const snapPoints = [30, 50, 87]; // Updated snap point to 87%



    header.addEventListener('touchstart', (e) => {
        if (window.innerWidth > 768) return;
        if (panel.classList.contains('drag-disabled')) return;
        if (e.target.closest('button') || e.target.tagName === 'INPUT') return;

        startY = e.touches[0].clientY;
        initialHeight = (panel.offsetHeight / getVH()) * 100;
        isDragging = true;

        panel.style.transition = 'none'; // Remove transition while dragging
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;

        // Empêche le comportement par défaut du navigateur (comme le pull-to-refresh)
        if (e.cancelable) {
            e.preventDefault();
        }

        currentY = e.touches[0].clientY;
        const deltaY = startY - currentY; // positive if moving up
        const deltaVH = (deltaY / getVH()) * 100;

        let newHeight = initialHeight + deltaVH;

        if (newHeight < 20) newHeight = 20;
        if (newHeight > maxVH) newHeight = maxVH;

        panel.style.height = `${newHeight}vh`;
    }, { passive: false });

    document.addEventListener('touchend', () => {
        if (!isDragging) return;
        isDragging = false;

        panel.style.transition = 'height 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';

        const currentHeightVH = (panel.offsetHeight / getVH()) * 100;

        let closestSnap = snapPoints[0];
        let minDiff = Math.abs(currentHeightVH - snapPoints[0]);

        for (let i = 1; i < snapPoints.length; i++) {
            const diff = Math.abs(currentHeightVH - snapPoints[i]);
            if (diff < minDiff) {
                minDiff = diff;
                closestSnap = snapPoints[i];
            }
        }

        panel.style.height = `${closestSnap}vh`;
    });
}
