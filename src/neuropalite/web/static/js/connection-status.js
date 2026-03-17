/**
 * Neuropalite Connection Status UI
 *
 * Updates Muse status cards (connection state, battery, signal quality)
 * based on WebSocket events from the backend.
 */

window.ConnectionStatus = (function () {

    /**
     * Update all Muse device status cards.
     * @param {Object} data - { devices: { muse_1: {...}, muse_2: {...} } }
     */
    function update(data) {
        if (!data || !data.devices) return;

        updateDevice('muse_1', data.devices.muse_1, '1');
        updateDevice('muse_2', data.devices.muse_2, '2');
    }

    function updateDevice(deviceId, info, suffix) {
        if (!info) return;

        // Status dot
        const dot = document.getElementById('muse' + suffix + '-dot');
        if (dot) {
            dot.className = 'status-dot ' + info.status;
        }

        // Status text
        const statusText = document.getElementById('muse' + suffix + '-status');
        if (statusText) {
            statusText.textContent = info.status;
        }

        // Battery
        const battery = document.getElementById('muse' + suffix + '-battery');
        if (battery) {
            battery.textContent = info.battery >= 0
                ? Math.round(info.battery) + '%'
                : '—';
        }

        // Signal quality bars
        const signal = document.getElementById('muse' + suffix + '-signal');
        if (signal) {
            signal.className = 'signal-bars';
            if (info.signal_quality > 0.7) signal.classList.add('good');
            else if (info.signal_quality > 0.4) signal.classList.add('fair');
            else if (info.signal_quality > 0) signal.classList.add('poor');
        }
    }

    return { update };
})();
