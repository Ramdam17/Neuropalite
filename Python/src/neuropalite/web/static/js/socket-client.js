/**
 * Neuropalite WebSocket Client
 *
 * Connects to the Flask-SocketIO backend and dispatches incoming
 * events to the appropriate UI handlers (status, metrics, bands).
 * Also wires up control buttons and normalization selector.
 */

const NeuropaliteSocket = (function () {
    let socket = null;

    function connect() {
        socket = io();

        socket.on('connect', function () {
            console.log('[Neuropalite] WebSocket connected');
            socket.emit('request_status');
            updateLSLIndicator(true);
        });

        socket.on('disconnect', function () {
            console.log('[Neuropalite] WebSocket disconnected');
            updateLSLIndicator(false);
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

        // Normalization method changed
        socket.on('normalization_changed', function (data) {
            const radios = document.querySelectorAll('input[name="norm"]');
            radios.forEach(function (radio) {
                radio.checked = radio.value === data.method;
            });
        });

        // Calibration status
        socket.on('calibration_status', function (data) {
            const btn = document.getElementById('btn-baseline');
            if (!btn) return;
            if (data.active) {
                btn.textContent = 'Calibrating...';
                btn.disabled = true;
                btn.classList.add('btn-disabled');
            } else {
                btn.textContent = 'Start Baseline';
                btn.disabled = false;
                btn.classList.remove('btn-disabled');
            }
        });

        // Recording stopped
        socket.on('recording_stopped', function () {
            const btn = document.getElementById('btn-stop');
            if (btn) btn.textContent = 'Stopped';
        });

        // Export complete
        socket.on('export_complete', function (data) {
            console.log('[Neuropalite] Export complete:', data.path);
            const btn = document.getElementById('btn-export');
            if (btn) {
                btn.textContent = 'Exported!';
                setTimeout(function () { btn.textContent = 'Export Data (XDF)'; }, 3000);
            }
        });

        // Wire up control buttons
        wireControls();
    }

    function wireControls() {
        document.addEventListener('DOMContentLoaded', function () {
            // Baseline calibration button
            var btnBaseline = document.getElementById('btn-baseline');
            if (btnBaseline) {
                btnBaseline.addEventListener('click', function () {
                    emit('start_baseline', { duration: 30 });
                });
            }

            // Stop recording button
            var btnStop = document.getElementById('btn-stop');
            if (btnStop) {
                btnStop.addEventListener('click', function () {
                    emit('stop_recording');
                });
            }

            // Export data button
            var btnExport = document.getElementById('btn-export');
            if (btnExport) {
                btnExport.addEventListener('click', function () {
                    emit('export_data', { format: 'both' });
                });
            }

            // Normalization method selector
            var normRadios = document.querySelectorAll('input[name="norm"]');
            normRadios.forEach(function (radio) {
                radio.addEventListener('change', function () {
                    emit('set_normalization', { method: this.value });
                });
            });
        });
    }

    function updateLSLIndicator(connected) {
        var dot = document.getElementById('lsl-dot');
        var label = document.getElementById('lsl-label');
        if (dot) {
            dot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
        }
        if (label) {
            label.textContent = connected ? 'Active @ 10 Hz' : 'Inactive';
        }
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
