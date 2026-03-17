/**
 * Opalite Sparkles — Animated background particles
 *
 * Creates floating, fading sparkle particles behind the UI,
 * evoking the beauty of neural connectivity and synchrony.
 */

(function () {
    const container = document.getElementById('sparkles-container');
    if (!container) return;

    const SPARKLE_COUNT = 30;
    const COLORS = ['#E0FFFF', '#00CED1', '#FF6B9D', '#FF8C42'];

    function createSparkle() {
        const sparkle = document.createElement('div');
        sparkle.classList.add('sparkle');

        sparkle.style.left = Math.random() * 100 + '%';
        sparkle.style.top = Math.random() * 100 + '%';
        sparkle.style.background = COLORS[Math.floor(Math.random() * COLORS.length)];
        sparkle.style.animationDuration = (4 + Math.random() * 6) + 's';
        sparkle.style.animationDelay = Math.random() * 6 + 's';
        sparkle.style.width = (2 + Math.random() * 3) + 'px';
        sparkle.style.height = sparkle.style.width;

        container.appendChild(sparkle);
    }

    for (let i = 0; i < SPARKLE_COUNT; i++) {
        createSparkle();
    }
})();
