/**
 * Neuropalite Charts Manager
 *
 * Manages Chart.js visualizations for frequency bands and alpha gauges.
 * Receives data from WebSocket events and updates the UI at ~30 Hz.
 */

window.ChartsManager = (function () {
    let bandsChart = null;

    const BAND_LABELS = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma'];
    const COLORS_A = 'rgba(255, 107, 157, 0.7)';  // rose coral
    const COLORS_B = 'rgba(255, 140, 66, 0.7)';    // orange warm

    function initBandsChart() {
        const ctx = document.getElementById('bands-chart');
        if (!ctx) return;

        bandsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: BAND_LABELS,
                datasets: [
                    {
                        label: 'Participant A',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: COLORS_A,
                        borderColor: 'rgba(255, 107, 157, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                    {
                        label: 'Participant B',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: COLORS_B,
                        borderColor: 'rgba(255, 140, 66, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: { duration: 200 },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(240, 248, 255, 0.06)' },
                        ticks: { color: 'rgba(240, 248, 255, 0.5)', font: { family: 'JetBrains Mono', size: 11 } },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: 'rgba(240, 248, 255, 0.7)', font: { family: 'Quicksand', size: 12 } },
                    },
                },
                plugins: {
                    legend: {
                        labels: {
                            color: 'rgba(240, 248, 255, 0.7)',
                            font: { family: 'Outfit', size: 12 },
                            usePointStyle: true,
                            pointStyle: 'circle',
                        },
                    },
                },
            },
        });
    }

    /**
     * Update alpha gauge bars and values.
     * @param {Object} data - { a: number, b: number } values in [0, 1]
     */
    function updateAlpha(data) {
        const gaugeA = document.getElementById('gauge-a');
        const gaugeB = document.getElementById('gauge-b');
        const valueA = document.getElementById('value-a');
        const valueB = document.getElementById('value-b');

        if (gaugeA && data.a !== undefined) {
            gaugeA.style.width = (data.a * 100) + '%';
            valueA.textContent = data.a.toFixed(2);
        }
        if (gaugeB && data.b !== undefined) {
            gaugeB.style.width = (data.b * 100) + '%';
            valueB.textContent = data.b.toFixed(2);
        }
    }

    /**
     * Update frequency bands bar chart.
     * @param {Object} data - { a: [5 values], b: [5 values] }
     */
    function updateBands(data) {
        if (!bandsChart) return;

        if (data.a) bandsChart.data.datasets[0].data = data.a;
        if (data.b) bandsChart.data.datasets[1].data = data.b;
        bandsChart.update('none');  // skip animation for real-time perf
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', initBandsChart);

    return { updateAlpha, updateBands };
})();
