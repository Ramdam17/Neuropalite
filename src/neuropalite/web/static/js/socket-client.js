/**
 * Neuropalite WebSocket Client
 *
 * Connects to the Flask-SocketIO backend and dispatches incoming
 * events to the appropriate UI handlers (status, metrics, bands).
 */

const NeuropaliteSocket = (function () {
    let socket = null;

    function connect() {
        socket = io();

        socket.on('connect', function () {
            console.log('[Neuropalite] WebSocket connected');
            socket.emit('request_status');
        });

        socket.on('disconnect', function () {
            console.log('[Neuropalite] WebSocket disconnected');
        });

        // Muse device status updates
        socket.on('muse_status', function (data) {
            if (window.ConnectionStatus) {
                window.ConnectionStatus.update(data);
            }
        });

        // Alpha metric values
        socket.on('alpha_metrics', function (data) {
            if (window.ChartsManager) {
                window.ChartsManager.updateAlpha(data);
            }
        });

        // Frequency band power values
        socket.on('frequency_bands', function (data) {
            if (window.ChartsManager) {
                window.ChartsManager.updateBands(data);
            }
        });
    }

    function emit(event, data) {
        if (socket && socket.connected) {
            socket.emit(event, data);
        }
    }

    // Auto-connect on load
    document.addEventListener('DOMContentLoaded', connect);

    return { connect, emit };
})();
