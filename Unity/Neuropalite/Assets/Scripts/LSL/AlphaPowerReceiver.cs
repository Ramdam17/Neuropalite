using UnityEngine;
using LSL;

/// <summary>
/// Receives alpha power values from a single LSL stream.
///
/// Uses liblsl directly (not AFloatInlet) for full control over
/// connection state detection and reconnection logic.
///
/// Attach as a child of LSLManager. Configure the stream name
/// in the Inspector (e.g., "AlphaPower_P1").
/// </summary>
public class AlphaPowerReceiver : MonoBehaviour
{
    [Header("Stream Configuration")]
    [SerializeField]
    [Tooltip("Name of the LSL stream to resolve (e.g., AlphaPower_P1)")]
    private string streamName = "AlphaPower_P1";

    [SerializeField]
    [Tooltip("Expected stream type")]
    private string streamType = "EEG";

    [Header("Timing")]
    [SerializeField]
    [Tooltip("Seconds without data before status drops from Receiving to Connected")]
    private float dataTimeout = 2.0f;

    [SerializeField]
    [Tooltip("Seconds between reconnection attempts when disconnected")]
    private float resolveInterval = 3.0f;

    [SerializeField]
    [Tooltip("Timeout in seconds for stream resolution")]
    private double resolveTimeout = 2.0;

    // --- Public read-only state ---
    public ConnectionState State { get; private set; } = ConnectionState.Disconnected;
    public float LatestAlphaValue { get; private set; }
    public float LastReceiveTime { get; private set; }
    public string StreamName => streamName;

    /// <summary>
    /// Configure the stream name programmatically (before first Update).
    /// Use this when creating receivers from code rather than the Inspector.
    /// </summary>
    public void Initialize(string name, string type = "EEG")
    {
        streamName = name;
        streamType = type;
    }

    // --- Events ---
    public System.Action<ConnectionState> OnStateChanged;
    public System.Action<float> OnAlphaReceived;

    // --- Private ---
    private StreamInlet _inlet;
    private float[] _sampleBuffer = new float[1]; // single channel
    private float _lastResolveAttempt;
    private ConnectionState _previousState = ConnectionState.Disconnected;

    private void Update()
    {
        if (_inlet == null)
        {
            TryResolve();
        }
        else
        {
            PullSamples();
            UpdateState();
        }
    }

    private void OnDestroy()
    {
        DisposeInlet();
    }

    /// <summary>
    /// Attempt to find and connect to the target LSL stream.
    /// Throttled by resolveInterval to avoid spamming the network.
    /// </summary>
    private void TryResolve()
    {
        if (Time.time - _lastResolveAttempt < resolveInterval)
            return;

        _lastResolveAttempt = Time.time;

        try
        {
            // resolve_stream is more reliable than ContinuousResolver
            // across network boundaries (see LSL4Unity issue #30)
            StreamInfo[] results = LSL.LSL.resolve_stream(
                "name", streamName, 1, resolveTimeout
            );

            if (results.Length > 0)
            {
                _inlet = new StreamInlet(results[0]);

                int channels = _inlet.info().channel_count();
                if (channels != 1)
                {
                    Debug.LogWarning(
                        $"[AlphaPowerReceiver] Stream '{streamName}' has {channels} channels, " +
                        $"expected 1. Using first channel only."
                    );
                }
                _sampleBuffer = new float[channels];
                SetState(ConnectionState.Connected);
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"[AlphaPowerReceiver] Exception during resolve: {e.GetType().Name}: {e.Message}");
        }
    }

    /// <summary>
    /// Pull available samples from the inlet (non-blocking).
    /// </summary>
    private void PullSamples()
    {
        try
        {
            // Non-blocking pull (timeout: 0) — critical for Unity main thread
            double timestamp = _inlet.pull_sample(_sampleBuffer, 0.0);

            if (timestamp != 0.0)
            {
                LatestAlphaValue = _sampleBuffer[0];
                LastReceiveTime = Time.time;
                OnAlphaReceived?.Invoke(LatestAlphaValue);
            }
        }
        catch (LostException)
        {
            Debug.LogWarning($"[AlphaPowerReceiver] Stream '{streamName}' lost.");
            DisposeInlet();
            SetState(ConnectionState.Disconnected);
        }
    }

    /// <summary>
    /// Update connection state based on data freshness.
    /// </summary>
    private void UpdateState()
    {
        if (_inlet == null)
        {
            SetState(ConnectionState.Disconnected);
            return;
        }

        float timeSinceLastData = Time.time - LastReceiveTime;

        if (LastReceiveTime > 0 && timeSinceLastData <= dataTimeout)
        {
            SetState(ConnectionState.Receiving);
        }
        else
        {
            SetState(ConnectionState.Connected);
        }
    }

    private void SetState(ConnectionState newState)
    {
        if (newState != _previousState)
        {
            State = newState;
            _previousState = newState;
            OnStateChanged?.Invoke(newState);

            Debug.Log($"[AlphaPowerReceiver] '{streamName}' → {newState}");
        }
        else
        {
            State = newState;
        }
    }

    private void DisposeInlet()
    {
        if (_inlet != null)
        {
            _inlet.Dispose();
            _inlet = null;
        }
    }
}
